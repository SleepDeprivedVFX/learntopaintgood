# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from typing import Optional
import filecmp
import logging
import json
import pprint
import os
import shutil
import socketio
import zipfile
import tempfile

from tk_framework_alias_utils import environment_utils

from ... import alias_bridge
from ...api import alias_api
from ...api.extensions import (
    add_alias_api_extensions_to_module,
)
from ..api_request import AliasApiRequestWrapper
from ..server_json import AliasServerJSON
from ...utils.invoker import execute_in_main_thread
from ...utils.exceptions import (
    AliasApiRequestException,
    AliasApiRequestNotSupported,
    AliasApiPostProcessRequestError,
    ClientAlreadyConnected,
)


class AliasServerNamespace(socketio.Namespace):
    """
    Server namespace for handling communication between Alias and a client.

    Each Alias client must have a unique AliasServerNamespace set up for it. The namespace
    handler only allows one client to connect to it, to ensure the communication between the
    Alias server and client are not mixed up if there are multiple clients connected to Alias.

    An AliasServerNamespace is unique by its namespace name.
    """

    _NAME = "alias"

    def __init__(self, sub_namespace=None):
        """Initialize the namespace."""

        # Keep track of the connected client. Only allow one client connected to each
        # AliasServerNamespace instance. To connect another client, use a different namespace.
        self.__client_sid = None

        # Construct the namespace string for this handler
        namespace = f"/{self._NAME}"
        if sub_namespace:
            namespace = f"{namespace}-{sub_namespace}"

        super().__init__(namespace)

    # ----------------------------------------------------------------------------------------
    # Properties

    @property
    def client_sid(self):
        """
        Get the session id of the connected client.

        This namespace class only allows one client to connect to it at a time. If multiple
        clients are needed, use a namespace for each client.
        """
        return self.__client_sid

    # ----------------------------------------------------------------------------------------
    # Event callback methods for namespace

    def trigger_event(self, event, sid, *args):
        """
        Catch all events and dispatch.

        First try to call the method associated with the event (e.g. "on_{event_name}"). If no
        method exists for the event, treat the event as an Alias API request and execute it.

        If the event is an Alias API request, the event will be the api function, and the args
        will hold the data used to determine how to execute the api function (e.g. module
        function or instance method, and arguments to pass).

        :param event: The event triggered.
        :type event: str
        :param sid: The session id of the client that triggered the event.
        :type sid: str
        :param *args: The data list to pass on to the event handler method.
        :type *args: List[any]

        :return: The return value of the method executed for this event.
        :rtype: any
        """

        # First, check if there is a method defined for this specific event.
        event_method_name = f"on_{event}"
        if hasattr(self, event_method_name):
            event_method = getattr(self, event_method_name)
            if callable(event_method):
                return event_method(sid, *args)

        # No event method found, treat this event as an api request.
        return self._trigger_api_event(event, sid, *args)

    def on_connect(self, sid, environ):
        """
        A connect event triggered.

        :param sid: The session id for the connected client.
        :type sid: str
        :param environ: The environment data for the client.
        :type environ: dict
        """

        if self.client_sid is not None:
            msg = "Client already connected to this name namespace '{self.namespace}'. Use a different namespace"
            self._log_message(sid, msg, logging.ERROR)
            raise ClientAlreadyConnected(msg)

        self.__client_sid = sid
        self._log_message(sid, f"Client connected\n{pprint.pformat(environ)}")

    def on_connect_error(self, data):
        """
        A connect error event triggered.

        :param data: Information related to the error.
        :type data: any
        """

        self._log_message(None, f"Client connection failed\n{data}")

    def on_disconnect(self, sid):
        """
        A disconnect error event triggered.

        :param sid: The session id of the client that triggered the event.
        :type sid: str
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        self.__client_sid = None
        self._log_message(sid, "Client disconnected")

    def on_restart(self, sid):
        """
        Restart the client.

        :param sid: The session id of the client that triggered the event.
        :type sid: str
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        # Reset the client id, since it will be disconnected and re-connected again.
        self.__client_sid = None

        # First destroy the scope
        data_model = alias_bridge.AliasBridge().alias_data_model
        data_model.destroy()

        # Emit event back to the client to shutdown (though do not wait for it, else this will
        # hang the server), then re-bootstrap the client.
        self.emit("shutdown", namespace=self.namespace)

        self._log_message(sid, f"Restarting client: {self.namespace}", logging.INFO)
        alias_bridge.AliasBridge().restart_client(self.namespace)

    def on_get_alias_api(self, sid):
        """
        Get the Alias API module.

        The module will be JSON-serialized and returned to the client.

        :param sid: The client session id that made the request.
        :type sid: str

        :return: The Alias API Python module.
        :rtype: module
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        return alias_api

    def on_load_alias_api(
        self, sid: str, api_extensions_path: Optional[str] = None
    ) -> str:
        """
        Load the Alias API and JSON-serialize the module to file on disk.

        This is an alternative method to getting the Alias API module
        and returning the module directly to the client. In this method, the
        module is JSON-serialized, saved locally to disk, and the file path
        to the JSON-serialized module is returned to the client. The client
        can then load the JSON-serialized module from the file.

        This is a more efficient way for the client to obtain the Alias API
        module because the module data is not sent over the network, which will
        only become slower as the Alias API module grows (e.g. new functionality
        is added).

        :param sid: The client session id that made the request.
        :param api_extensions_path: Path to a file containing only functions
            that will be loaded and added as extensions to the Alias Python API
            module. They will be available through the alias_api by the class
            AliasApiExtensions.

        :return: The file path to the JSON-serialized Alias API module.
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        # Get the directory and path to the Alias API cached file. The cache
        # file name will have format:
        # {alias_api_module_name}{alias_version}_{python_version}.json
        api_info = self.on_get_alias_api_info(sid)
        api_filename, api_ext = os.path.splitext(
            os.path.basename(api_info["file_path"])
        )
        cache_filepath = environment_utils.get_alias_api_cache_file_path(
            api_filename, api_info["alias_version"], api_info["python_version"]
        )
        cache_dir = os.path.dirname(cache_filepath)
        os.makedirs(cache_dir, exist_ok=True)

        # Get the path to the Alias API module (.pyd) that was used to create
        # the cache. The cache module file name will have format:
        # {alias_api_module_name}{alias_version}_{python_version}.pyd
        base_cache_module_filename, _ = os.path.splitext(
            os.path.basename(cache_filepath)
        )
        cache_module_filename = f"{base_cache_module_filename}.{api_ext}"
        cache_module_filepath = os.path.join(cache_dir, cache_module_filename)

        # Get any Alias API extensions that should be loaded with the API.
        add_alias_api_extensions_to_module(api_extensions_path, alias_api)

        # Get the cached extensions (if any)
        cache_extensions_zip_filepath = environment_utils.get_alias_api_cache_file_path(
            "api_extensions_cache",
            api_info["alias_version"],
            api_info["python_version"],
            file_ext="zip",
        )
        has_cached_extensions = os.path.exists(cache_extensions_zip_filepath)
        cache_extensions_dir = os.path.dirname(cache_extensions_zip_filepath)
        os.makedirs(cache_extensions_dir, exist_ok=True)

        # Check if the extensions have changed
        extensions_updated = False
        if api_extensions_path and os.path.exists(api_extensions_path):
            # Create a temporary zip file to compare with the current cache
            temp_zip_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            temp_zip_file_path = temp_zip_file.name
            temp_zip_file.close()
            try:
                # Create the zip file
                with zipfile.ZipFile(
                    temp_zip_file_path, "w", zipfile.ZIP_DEFLATED
                ) as zipf:
                    if os.path.isdir(api_extensions_path):
                        for root, dirs, files in os.walk(api_extensions_path):
                            for f in files:
                                file_path = os.path.join(root, f)
                                arcname = os.path.relpath(
                                    file_path, api_extensions_path
                                )
                                zipf.write(file_path, arcname)
                    else:
                        zipf.write(
                            api_extensions_path, os.path.basename(api_extensions_path)
                        )

                # Compare with current cache; update if cache doesn't exist or differs
                extensions_updated = not has_cached_extensions or not filecmp.cmp(
                    temp_zip_file_path, cache_extensions_zip_filepath
                )

                # If extensions have changed, overwrite the cache
                if extensions_updated:
                    shutil.copyfile(temp_zip_file_path, cache_extensions_zip_filepath)

            finally:
                # Clean up the temporary file
                if os.path.exists(temp_zip_file_path):
                    os.unlink(temp_zip_file_path)
        elif has_cached_extensions:
            # If there is a cached extensions zip file, but no api extensions path,
            # then the extensions have been removed, so update the cache.
            extensions_updated = True

        # Check if the cache is up-to-date. If not, create a new cache. Creating
        # a new cache is expensive and should only be done if the api or
        # extensions have changed
        if (
            not os.path.exists(cache_filepath)
            or not os.path.exists(cache_module_filepath)
            or not filecmp.cmp(api_info["file_path"], cache_module_filepath)
            or extensions_updated
        ):
            try:
                # Create the Alias API cache
                with open(cache_filepath, "w") as fp:
                    json.dump(alias_api, fp=fp, cls=AliasServerJSON.encoder_class())
            except Exception as e:
                error_message = (
                    f"Failed to create Alias API cache file {cache_filepath}: {e}"
                )
                self._log_message(
                    sid,
                    error_message,
                    logging.ERROR,
                )
                raise AliasApiRequestException(error_message)

            # Copy the module to the cache folder in order to determine next time if the
            # cache requies an update
            shutil.copyfile(api_info["file_path"], cache_module_filepath)

        # Return the path to the Alias API cache file
        return cache_filepath

    def on_get_alias_api_info(self, sid):
        """
        Get the Alias API module info.

        :param sid: The client session id that requested the info.
        :type sid: str

        :return: The information about the Alias API Python module.
        :rtype: dict
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        api_filepath = alias_api.__file__
        last_modified = os.stat(api_filepath).st_mtime

        return {
            "version": alias_api.__version__,
            "alias_version": alias_api.__alias_version__,
            "python_version": alias_api.__python_version__,
            "file_path": api_filepath,
            "last_modified": last_modified,
        }

    def on_alias_api_last_modified(self, sid):
        """
        Get the last modified time of the Alias API Python module.

        :param sid: The client session id that requested the info.
        :type sid: str

        :return: The time of last modification of the Alias API Python module file.
        :rtype: int
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        api_filepath = alias_api.__file__
        return os.stat(api_filepath).st_mtime

    def on_server_info(self, sid):
        """
        Get the server information.

        The server information will contain info about the Alias API module it uses to
        retrieve Alias data, and information that the server has about the client that
        made this request.

        :param sid: The client session id that requested the info.
        :type sid: str

        :return: The server information.
        :rtype: dict
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        api_info = self.on_get_alias_api_info(sid)
        client_info = (
            alias_bridge.AliasBridge()
            .get_client_by_namespace(self.namespace)
            .get("info")
        )
        return {
            "api": api_info,
            "client": client_info,
        }

    # ----------------------------------------------------------------------------------------
    # Protected methods

    def _log_message(self, sid, msg, level=logging.INFO):
        """Convenience function to log a message."""

        log_msg = f"Server [client={sid}, namespace={self.namespace}] {msg}"
        self.server.logger.log(level, log_msg)

    def _trigger_api_event(self, event, sid, *args):
        """
        An Alias API event was triggered by the client.

        Execute the Alias API request from the given data. The event should match an api
        function (e.g. module function, instance method), and the data contains all the
        necesasry information to execute the api request.

        :param event: The event corresponding to an api request.
        :type event: str
        :param sid: The session id of the client that triggered the event.
        :type sid: str
        :param *args: The data list to pass on to the event handler method.
        :type *args: List[any]

        :return: The return value of the api request.
        :rtype: any
        """

        # Before executing the api request, ensure that the session id is valid.
        if self.client_sid is None or sid != self.client_sid:
            return

        # Get the request data from the args
        request = args[0] if args else None

        # For multiple requests, create a wrapper to ensure all requests are
        # invoked in a single Qt event
        if isinstance(request, list):
            request = AliasApiRequestWrapper.create_wrapper(request)

        # Execute the request(s)
        self._log_message(None, f"Executing Alias API request: {request}", logging.INFO)
        result = self._execute_request(event, request)

        try:
            # Do any post processing after the request has been made.
            self._post_process_request(event, request, result)
        except Exception as post_process_error:
            self._log_message(
                sid,
                f"Alias API request post process error\n{post_process_error}",
                logging.ERROR,
            )
            return AliasApiPostProcessRequestError(post_process_error)

        return result

    @execute_in_main_thread
    def _execute_request(self, request_name, request):
        """
        Execute the Alias API request.

        The request object holds all the necessary information to execute the api request.

        :param request_name: The api request name.
        :type request_name: str
        :param request: The data to execute the api request.
        :type request: AliasApiRequestWrapper

        :return: The return value of the api request. If an exception is thrown, the exception
            object is returned.
        :rtype: any
        """

        if not isinstance(request, AliasApiRequestWrapper):
            # Do not raise, just return the exception to be sent back to the client
            msg = f"Alias API request not supported: {request}"
            self._log_message(None, msg, logging.ERROR)
            return AliasApiRequestNotSupported(msg)

        try:
            # Execute and return the api result
            return request.execute(request_name)
        except AliasApiRequestException as api_error:
            # Return an api request error
            self._log_message(
                None, f"Alias API request error\n{api_error}", logging.ERROR
            )
            return api_error
        except alias_api.AliasPythonException as c_error:
            self._log_message(
                None,
                f"C++ exception occurred while executing request {request_name}\n{c_error}",
                logging.ERROR,
            )
            return AliasApiRequestException(c_error)
        except Exception as general_error:
            # Report a general error that occurred trying to execute the api request.
            self._log_message(
                None,
                f"Error occurred attempting to execute request {request_name}\n{general_error}",
                logging.ERROR,
            )
            return AliasApiRequestException(general_error)

    def _post_process_request(self, event, data, result):
        """
        Post process the return value of an api request.

        This method currently provides special handling for Alias event callbacks. On adding
        a message event handler, the Alias event and client callback id will be registered in
        the Alias Data Model. This allows the socketio server to forward Alias events to the
        client, such that the client can execute the client callback on the client side. On
        remove message event handlers, the Alias Data Model is updated such that events are no
        longer forwarded to the client.

        NOTE this method assume the only way to register and remove a message handler is
        through these Alias API methods:

            add_message_handler
            remove_message_handler
            remove_message_handlers

        If there are other ways to add/remove message handlers, this method needs to be
        updated.
        """

        if isinstance(result, Exception):
            # Do not process post request if there was an error executing the request
            return

        if event == "add_message_handler":
            if result:
                alias_event_id = data.func_args[0]
                event_callback_id = result[1]
                data_model = alias_bridge.AliasBridge().alias_data_model
                data_model.register_event(alias_event_id, event_callback_id)
            else:
                # raise exception?
                return

        elif event == "remove_message_handler":
            alias_event_id = data.func_args[0]
            event_callback_id = data.func_args[1]
            data_model = alias_bridge.AliasBridge().alias_data_model
            data_model.unregister_event(alias_event_id, event_callback_id)

        elif event == "remove_message_handlers":
            alias_event_id = data.func_args[0]
            data_model = alias_bridge.AliasBridge().alias_data_model
            data_model.unregister_event(alias_event_id)
