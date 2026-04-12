# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from typing import Optional

import json
import os
import logging
import socketio
import threading

from .client_json import AliasClientJSON
from ..utils.decorators import check_server_result, check_client_connection
from ..utils.exceptions import AliasClientException
from tk_framework_alias_utils import utils as framework_utils


class AliasSocketIoClient(socketio.Client):
    """
    A socketio client to communicate with Alias.

    The client establishes which JSON module to use for encoding the data that is sent from
    this client to the server, and decoding the data sent from the server to this client. The
    default JSON module used is the AliasClientJSON.

    Callback functions that are passed to the Alias api, through the socketio server, require
    special handling by the client. Function objects cannot be passed to the server, since
    they are not JSON-serializable, so the client will create unique ids for callback
    functions that will be sent and received from the server to trigger callback functions on
    the client side.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the client."""

        if "json" not in kwargs:
            # Default to the Alias client JSON if not provided.
            self.__json = AliasClientJSON
            kwargs["json"] = self.__json
        else:
            self.__json = None

        # If no logger specified, provide a default logger that will write to the Alisa plugin
        # install directory (as specified n the environment utils).
        logger = None
        if kwargs.get("logger") is None:
            logger = framework_utils.get_logger(self.__class__.__name__, "sio_client")
            kwargs["logger"] = logger

        if kwargs.get("engineio_logger") is None:
            kwargs["engineio_logger"] = logger or framework_utils.get_logger(
                self.__class__.__name__, "sio_client"
            )

        # The connection timeout in seconds
        self.__timeout = kwargs.pop("timeout", 20)
        kwargs["request_timeout"] = self.__timeout

        super().__init__(*args, **kwargs)

        # The callbacks registry. Callback functions passed to the server are stored in the
        # client by their id, such that they can be looked up and executed when the server
        # triggers the callback.
        self.__callbacks = {}
        # A lock to ensure callbacks are accessed thread-safely
        self.__callback_lock = threading.Lock()

        # A lock to ensure events are emitted thread-safely
        self.__message_queue_lock = threading.Lock()

        # A list of namespaces that are registered to this client.
        self.__namespaces = []
        # The default namespace to use for this client (e.g. if no namespace is given on
        # emitting an event, this default namespace is used).
        self._default_namespace = None

    # -------------------------------------------------------------------------------------------------------
    # Properties

    @property
    def default_namespace(self):
        """Get the default namespace used to emit events to the server."""
        return self._default_namespace

    # -------------------------------------------------------------------------------------------------------
    # Public methods

    def get_json_encoder(self):
        """Get the JSON encoder class used to handle serializing data with the server."""

        if self.__json is AliasClientJSON:
            return self.__json.encoder_class()
        return None

    def get_json_decoder(self):
        """Get the JSON decoder class used to handle serializing data with the server."""

        if self.__json is AliasClientJSON:
            return self.__json.decoder_class()
        return None

    def add_namespace(self, namespace_handler):
        """Register a namespace handler and add it to the list of namespaces for this client."""

        self.__namespaces.append(namespace_handler.namespace)
        self.register_namespace(namespace_handler)

    def start(self, hostname, port):
        """
        Start the socketio client by connecting to the server.

        :param hostname: The host name to connect to.
        :type hostname: str
        :param port: The port number to connect to.
        :type port: int
        """

        if self.connected:
            self.disconnect()

        # TODO secure https
        url = f"http://{hostname}:{port}"
        self.connect(
            url,
            namespaces=self.__namespaces,
            wait_timeout=self.__timeout,
        )

    def cleanup(self):
        """
        Clean up the client resources.

        This may be useful to call when the client is disconnected from the server.

        By default, nothing is done. Override this method to do any custom clean up.
        """

        pass

    #####################################################################################
    # Methods to handle callback functions

    def get_callback_id(self, callback):
        """
        Return a unique identifier for the callback function.

        :param callback: The callback function to generate an id for.
        :type callback: function

        :return: A unique id for the callback.
        :rtype: str
        """

        # Generate a unique id for the function. Use the id() function to make the id
        # unique, but append the function name for a more human readable id.
        return f"{id(callback)}.{callback.__name__}"

    def has_callback(self, callback):
        """
        Return True if there is a callback registered already for the given callback.

        :param callback: The callback to check if registered.
        :type callback: function

        :return: True if the callback is already registered, else False.
        :rtype: bool
        """

        callback_id = self.get_callback_id(callback)
        with self.__callback_lock:
            return callback_id in self.__callbacks

    def get_callback(self, callback_id):
        """
        Return the callback function for the id.

        :param callback_id: The unique id to get the callback for.
        :type callback_id: str
        """

        with self.__callback_lock:
            return self.__callbacks.get(callback_id)

    def set_callback(self, callback):
        """
        Register the callback to the client.

        :param callback: The callback to register.
        :type callback: function
        """

        callback_id = self.get_callback_id(callback)
        with self.__callback_lock:
            self.__callbacks[callback_id] = callback
        return callback_id

    #####################################################################################
    # Methods to emitting events

    @check_server_result
    @check_client_connection
    def call_threadsafe(self, *args, **kwargs):
        """
        Emit an event to the server and wait for the response in a thread-safe way.

        :param args: The args to pass to the socketio Client.call method.
        :type args: List
        :param kwargs: The key-word arguments to pass to the socketio Client.call method.
        :type kwargs: dict

        :return: The server response for the emitted event.
        :rtype: any
        """

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            return self.call(*args, **kwargs)

    @check_server_result
    @check_client_connection
    def emit_threadsafe_and_wait(self, *args, **kwargs):
        """
        Call the emit method in a thread-safe and non-GUI blocking way.

        This differs from `call_threadsafe` by using the `Client.emit` method with a callback
        to get the server response. While waiting for the callback to be triggered, client
        events are processed to avoid blocking the GUI. The `call_threadsafe` method will
        block the GUI.

        :param args: The args to pass to the socketio Client.emit method.
        :type args: List
        :param kwargs: The key-word arguments to pass to the socketio Client.emit method.
        :type kwargs: dict

        :return: The server response for the emitted event.
        :rtype: any
        """

        # Set up the response object that will get updated once the api request has returned
        # from the server.
        response = {
            "ack": False,  # The request was acknowledged (finished)
            "result": None,  # The request result
        }

        # Add the event callback to pass to the sio emit method, which will call this function
        # once the server returns.
        kwargs["callback"] = self._get_request_callback(response)

        # Emit the event
        self.emit_threadsafe(*args, **kwargs)

        # Wait for the callback to set the event result
        self._wait_for_response(response)

        # Check that client is still connected. It is possible that it timed out
        # waiting for the server response, in which case it will disconnect.
        if not self.connected and not response.get("ack"):
            # Common reasons for disconnection: client timed out waiting for the server
            # response, or client message size was too large for the server to handle.
            request_name = args[0] if args else "unknown"
            request_data = args[1] if len(args) > 1 else {}
            msg_data = self.__json.dumps(request_data)
            msg_size = len(msg_data) if msg_data else 0
            error_message = (
                "Client disconnected while waiting for the server response. "
                "Server will finish executing the request, and the client will "
                "attempt to reconnect once the server is ready.\n"
                f"Client attempted to emit event {request_name} with message size {msg_size} bytes."
            )
            self.logger.log(logging.ERROR, error_message)
            raise AliasClientException(error_message)

        # Return the result from the server
        return response.get("result")

    @check_server_result
    @check_client_connection
    def emit_threadsafe(self, *args, **kwargs):
        """
        Call the emit method in a thread-safe way.

        This method does not wait for the server response.

        :param args: The args to pass to the socketio Client.emit method.
        :type args: List
        :param kwargs: The key-word arguments to pass to the socketio Client.emit method.
        :type kwargs: dict
        """

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            self.emit(*args, **kwargs)

    def _handle_server_error(self, error):
        """
        Handle the server error given.

        By default, the error will be raised. Override this method to provide custom handling
        of server errors.

        :param error: The server error.
        :type error: Exception
        """

        raise (error)

    #####################################################################################
    # Methods to emit specific events

    def get_alias_api_module_proxy(self, api_extensions_path: Optional[str] = None):
        """
        Get the Alias Python API module proxy.

        This method will attempt to first load the module from a cache file, if it exists and
        is not stale. Otherwise, it will make a server request to get the api module.

        The actual Alias Python API module (.pyd) file lives on the server, so this method
        will get the api module as a JSON object from the server, and create a proxy module
        that can be used on the client side here, as if it were the actual api module itself.

        :param api_extensions_path: Path to a file containing only functions that will be loaded
            by the server and added as extensions to the Alias Python API module. They will be
            available through the alias_api by the class AliasApiExtensions.

        :return: The Alias Python API module proxy.
        :rtype: AliasClientModuleProxyWrapper
        """

        # The server will JSON-serialize the Alias Python API module to a local
        # file on disk. The server will return the path to this file for this
        # client to read and load the module from. This is done to avoid sending
        # the entire module over the network, which can be slow.
        module_filepath = self.call_threadsafe(
            "load_alias_api", api_extensions_path, timeout=self.__timeout
        )
        if not os.path.exists(module_filepath):
            raise AliasClientException(
                f"Alias Python API module file not found at: {module_filepath}"
            )
        with open(module_filepath, "r") as fp:
            module_proxy = json.load(fp, cls=self.get_json_decoder())
            self.logger.log(logging.DEBUG, module_proxy)
            return module_proxy

    def get_alias_api(self, api_extensions_path: Optional[str] = None):
        """
        Get the Alias Python API module.

        This method will attempt to first load the module from a cache file, if it exists and
        is not stale. Otherwise, it will make a server request to get the api module.

        The actual Alias Python API module (.pyd) file lives on the server, so this method
        will get the api module as a JSON object from the server, and create a proxy module
        that can be used on the client side here, as if it were the actual api module itself.

        :param api_extensions_path: Path to a file containing only functions that will be loaded
            by the server and added as extensions to the Alias Python API module. They will be
            available through the alias_api by the class AliasApiExtensions.

        :return: The Alias Python API module.
        :rtype: module
        """

        module_proxy = self.get_alias_api_module_proxy(
            api_extensions_path=api_extensions_path
        )
        return module_proxy.get_or_create_module(self)

    # -------------------------------------------------------------------------------------------------------
    # Protected methods

    def _get_request_callback(self, response):
        """
        Return a function that can be passed as a callback to handle a socketio event callback.

        :param response: The response object to pass to the callback to set with the event result data.
        :type response: dict

        :return: The callback function.
        :rtype: function
        """

        def __request_callback(*result):
            """Callback invoked when emit finished. The result is the return value of the api request."""
            if len(result) == 1:
                response["result"] = result[0]
            else:
                response["result"] = result
            response["ack"] = True

        return __request_callback

    def _wait_for_response(self, response):
        """
        Wait for the server to set the response object.

        Override this default method to do any processing while waiting for the server to
        return the response value. For example, a client may need to ensure the GUI is not
        blocking if Alias needs to perform GUI events during the api request.

        This routine will return once it receieves a response from the server,
        of if the client disconnects from the server. If the client
        disconnects, the response object will indicate the request was not
        acknowledged.

        The response object is a dictionary with two key-values:

            ack:
                type: bool
                description: True if the response has been acknowledged and result is set,
                             else False if the server has not completed the api request.
            result:
                type: any
                description: The return value from the server api request.

        :param response: The response object that will be set with the server result once the
            server completes the api request.
        :type response: dict
        """

        while not response.get("ack", False) and self.connected:
            self._process_events()

    def _process_events(self):
        """
        Process GUI events.

        By default, do nothing. Override this method to provide event processing handling
        specific to the running application.
        """

        pass
