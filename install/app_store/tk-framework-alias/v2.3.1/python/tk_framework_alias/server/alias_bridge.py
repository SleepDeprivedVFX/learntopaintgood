# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging
import os
import subprocess
import requests
import sys
import threading
import pprint

# Third party pacakges included in dist/pkgs.zip
import socketio
import eventlet

from .socketio.data_model import AliasDataModel
from .socketio.server_json import AliasServerJSON
from .socketio.namespaces.server_namespace import AliasServerNamespace
from .socketio.namespaces.events_namespace import AliasEventsServerNamespace
from .socketio.namespaces.events_client_namespace import (
    AliasEventsClientNamespace,
)
from .utils.singleton import Singleton
from .utils.exceptions import (
    AliasBridgeException,
    ClientAlreadyRegistered,
    ServerAlreadyRunning,
    ClientNameReservered,
    ClientBootstrapMethodNotSupported,
)

from tk_framework_alias_utils import utils as framework_utils


class AliasBridge(metaclass=Singleton):
    """
    A class to handle communication with Alias.

    The AliasBridge is responsible for starting a socketio server that listens for Alias
    clients to connect to, in order to communicate with a running instance of Alias. The
    server can execute Alias API requests such that external clients can interact with Alias.
    """

    def __init__(self):
        """Initialize the bridge."""

        # Default server socket params
        self.__default_hostname = "127.0.0.1"
        self.__default_port = 8000
        self.__max_retry_count = 25
        self.__server_socket = None
        self.__proxy_trust_env = bool(
            os.environ.get("ALIAS_PLUGIN_CLIENT_PROXY_TRUST_ENV")
        )

        # Track the clients registered to the socketio server
        self.__clients = {}

        # The Alias data model to store Alias api objects, to allow passing api objects back
        # and forth between the server and its clients.
        self.__data_model = AliasDataModel()

        # Create the SocketIO server, long-polling is the default transport but websocket
        # transport will be used if possible. The logger will capture stdout (e.g. print()
        # statements will be written to the logger).
        server_sio_logger = framework_utils.StdoutCaptureLogger.get_logger(
            self.__class__.__name__, "sio_server"
        )
        self.__server_sio = socketio.Server(
            aysnc_mode="eventlet",
            logger=server_sio_logger,
            engineio_logger=server_sio_logger,
            ping_timeout=60 * 5,
            ping_interval=30,
            json=AliasServerJSON,
            max_http_buffer_size=1000000
            * 5,  # 5MB max buffer size for incoming messages
        )
        self.__log(
            f"Server-side max HTTP buffer size: {self.__server_sio.eio.max_http_buffer_size} bytes"
        )

        # Create a SocketIO client to handle Alias events triggered in the main thread, which
        # can then forward events to the server in the thread that the server is executing in.
        # Register a server namespace to specifically handle Alias events emitted from this
        # events client.
        # These are special client/server namespaces, do not use the register_client_namespace
        # for these.
        client_sio_logger = framework_utils.get_logger(
            self.__class__.__name__, "sio_client"
        )

        # Set up kwargs to pass to socketio Client
        client_kwargs = {
            "logger": client_sio_logger,
            "engineio_logger": client_sio_logger,
        }
        if not self.__proxy_trust_env:
            # Set up a session object to ignore any proxy settings specified in
            # environment variables
            session = requests.Session()
            session.trust_env = False
            client_kwargs["http_session"] = session

        # Create the client to handle Alias events
        self.__alias_events_client_sio = socketio.Client(**client_kwargs)
        self.__alias_events_client_sio.register_namespace(AliasEventsClientNamespace())
        self.__server_sio.register_namespace(AliasEventsServerNamespace())

        # Create the WSGI middleware for the SocketIO server
        self.__app = socketio.WSGIApp(self.__server_sio, static_files={})

    # Properties
    # ----------------------------------------------------------------------------------------

    @property
    def sio(self):
        """Get the Alias socketio server."""
        return self.__server_sio

    @property
    def alias_data_model(self):
        """Get the Alias Data Model to access Alias objects."""
        return self.__data_model

    @property
    def alias_events_client_sio(self):
        """Get the client socketio that can be used to emit Alias events to the server."""
        return self.__alias_events_client_sio

    # Public methods
    # ----------------------------------------------------------------------------------------

    def start_server(self, host=None, port=None, max_retries=None):
        """
        Start the server to communicate between Alias and Flow Production Tracking.

        This will create a new thread to serve the WSGI server application to listen for
        client connections to the socketio server.

        :param host: The host name to open the socket server on.
        :type host: str
        :param port: The port number to open the socket server on.
        :type port: int
        :param max_retries: The number of retries to create the socket server.
        :type max_retries: int

        :raises ServerAlreadyRunning: If the bridge has already started a server.
        :raises AliasBridgeException: If the socket failed to be created.

        :return: True if the server started successfully, else False.
        :rtype: bool
        """

        self.__log("Starting server...")

        if self.__server_socket:
            # Already started
            host_in_use, port_in_use = self.__server_socket.getsockname()
            if host is not None and host != host_in_use:
                raise ServerAlreadyRunning(
                    "Server already running on {host_in_use}:{port_in_use}. Server must be stopped first."
                )
            if port is not None and port != port_in_use:
                raise ServerAlreadyRunning(
                    "Server already running on {host_in_use}:{port_in_use}. Server must be stopped first."
                )
            return True

        # First, find an open port on the host for the server socket to listen on.
        self.__server_socket = self.__open_server_socket(host, port, max_retries)
        if not self.__server_socket:
            raise AliasBridgeException("Failed to open server socket.")

        # Start the SocketIO server in a new thread using Python standard threds. Set the
        # thread as a daemon so that the Python program will not wait for this thread to exit.
        th = threading.Thread(target=self.__serve_app)
        th.daemon = True
        th.start()

        # Connect the Alias socketio client to the server. This must be called after the server has started.
        server_host, server_port = self.__server_socket.getsockname()
        self.alias_events_client_sio.connect(
            f"http://{server_host}:{server_port}",
            namespaces=[AliasEventsServerNamespace.get_namespace()],
            wait_timeout=20,
        )

        if not self.alias_events_client_sio.connected:
            raise Exception("Alias events client failed to connect")

        return True

    def stop_server(self):
        """
        Stop the server socket.

        The shutdown must be emitted from the alias events client because this function is
        executed from the main thread, but the socketio server can only be accessed from the
        single thread that it was created in. By emitting an event from the client, the server
        will receive the shutdown event in the correct thread.
        """

        self.__log("Stopping server...")

        # Destroy the server scope, this will remove any event handlers registered. Do this
        # before shutting down clients so that their shutdown does not trigger any events.
        self.alias_data_model.destroy()

        # Emit event to shut down all other clients connected to the server.
        if self.alias_events_client_sio and self.alias_events_client_sio.connected:
            self.alias_events_client_sio.call(
                "shutdown", namespace=AliasEventsServerNamespace.get_namespace()
            )
            self.alias_events_client_sio.disconnect()

        # Clean up the server socket
        if self.__server_socket:
            self.__server_socket.close()
            self.__server_socket = None

        # Clean up the clients
        self.__clients.clear()

    def get_client_by_namespace(self, namespace):
        """
        Find the client for the given namespace.

        :param namespace: The namespace to find which client is registered to it.
        :type namespace: str

        :return: The client registered to the namespace.
        :rtype: dict
        """

        return next(
            (
                client_data
                for client_data in self.__clients.values()
                if client_data["namespace"] == namespace
            ),
            {},
        )

    def register_client_namespace(self, client_name, client_info):
        """
        Register a new client.

        A client is unique by the `client_name`. A socketio.Namespace will be created for the
        client and registered to the server.

        If the client already has been registered, the client data will be returned.

        :param client_name: The name of the client application being registered.
        :type client_name: str
        :param client_exe_path: The file path to the Python script to execute in a new process
            that will handle bootstrapping the client being registered.
        :type client_exe_path: str
        :param client_info: (optional) Additional info about the client being registered.
        :type client_info: dict

        :raises ClientAlreadyRegistered: If a client is already registered for the given name.
        :raises ClientNameReserved: If the client name is in reserve.

        :return: The client that was registered.
        :rtype: dict
        """

        self.__log(f"Registering client namespace: {client_name}\n{client_info}")

        if self.__clients.get(client_name):
            raise ClientAlreadyRegistered("Client already registered")

        namespace_handler = AliasServerNamespace(client_name)
        if namespace_handler.namespace == AliasEventsServerNamespace.get_namespace():
            raise ClientNameReservered(
                "Client name '{client_name}' is reserved. Use a different name."
            )

        self.__server_sio.register_namespace(namespace_handler)

        client = {
            "name": client_name,
            "info": client_info,
            "namespace": namespace_handler.namespace,
        }
        self.__clients[client_name] = client

        return client

    def bootstrap_client(self, client, client_info=None):
        """
        Bootstrap the Alias client.

        This method does not start the server; if the client process needs to connect to the
        sever on bootstrap, the server should already be started to ensure it is ready for the
        client to connect to. If the server is not ready, False is returned.

        :param client_name: The name of the client to bootstrap.
        :type client_name: str
        :param client_exe_path: The file path to the Python script to execute in a new process
            that will handle bootstrapping the client application.
        :type client_exe_path: str
        :param client_info: (optional) Additional information about the client.
        :type client_info: dict

        :return: True if the subprocess to bootstrap the client was successfully launched,
            else False. Note that this method cannot detect if the client successfully
            bootstrapped, only that the process was created to bootstrap the client.
        :rtype: bool
        """

        self.__log(f"Bootstrapping client: {client}")

        # Check if the server is ready to have a client connect to it.
        if not self.__server_socket:
            return False

        hostname, port = self.__server_socket.getsockname()

        # Check if the client is already registered. Clients are unique by name.
        if not isinstance(client, dict):
            client_name = client
            client = self.__clients.get(client_name)

        if not client:
            # Get client info from the environment and register it.

            # NOTE uncomment to allow client to run from python script.
            # Warning that the framework attempts to encrypt and decrypt the executable path
            # for security, however it does not have a secure place to store the key, so for
            # this reason it is currently turned off. Ideally we can store an encryption key
            # in the Flow Production Tracking database or a key vault. For Flow Production Tracking clients, this is not an
            # issue because the toolkit manager should be used to start the Flow Production Tracking engine.
            #
            # client_info = client_info or {}
            # client_exec_path = os.environ.get("ALIAS_PLUGIN_CLIENT_EXECPATH")
            # if client_exec_path:
            #     client_info["exec_path"] = client_exec_path

            # Check for Flow Production Tracking specific client info. Flow Production Tracking clients do not provide a
            # bootstrap executable path, instead the plugin_bootstrap.py script is used
            # from within the framework.
            pipeline_config_id = os.environ.get(
                "ALIAS_PLUGIN_CLIENT_SHOTGRID_PIPELINE_CONFIG_ID"
            )
            entity_type = os.environ.get("ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_TYPE")
            entity_id = os.environ.get("ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_ID")
            # A client is considered a Flow Production Tracking client if it provides an entity type and id.
            # The pipeline configuration is optional, since an unmanaged pipeline could be in
            # use. In that case, the default will be the latet basic config in the app store.
            if entity_type is not None and entity_id is not None:
                client_info["shotgrid"] = {
                    "pipeline_config_id": pipeline_config_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            client = self.register_client_namespace(client_name, client_info)

        # Get the python interpreter to use from the environment, fallback to checking the
        # current interpreter if not set.
        python_exe = os.environ.get("ALIAS_PLUGIN_CLIENT_PYTHON")
        if not python_exe:
            if os.path.basename(sys.executable) != "python.exe":
                # We may be embedded, in which case the exe will be the running application instaed of
                # the python exe
                # Try to construct the python exe from the exec prefix
                python_exe = os.path.join(sys.exec_prefix, "python.exe")
                if not os.path.exists(python_exe):
                    # Fall back to the sys.executable, in could be a specific pythonXY.exe
                    python_exe = sys.executable
            else:
                python_exe = sys.executable

        # Get the client executable and args
        shotgrid_info = client["info"].get("shotgrid")
        if shotgrid_info:
            # Bootstrap using Flow Production Tracking manager
            pipeline_config_id = shotgrid_info["pipeline_config_id"] or ""
            entity_type = shotgrid_info["entity_type"]
            entity_id = shotgrid_info["entity_id"]
            plugin_bootstrap_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    os.path.pardir,
                    os.path.pardir,
                    "tk_framework_alias_utils",
                    "plugin_bootstrap.py",
                )
            )
            args = [
                python_exe,
                plugin_bootstrap_path,
                pipeline_config_id,
                entity_type,
                entity_id,
                hostname,
                str(port),
                client["namespace"],
            ]
        else:
            # NOTE uncomment to allow client to run from python script.
            # # Bootstrap by running the client executable
            # client_exe_path = framework_utils.decrypt_from_str(
            #     client["info"].get("exec_path")
            # )
            # if not client_exe_path:
            #     return False

            # args = [
            #     python_exe,
            #     client_exe_path,
            #     hostname,
            #     str(port),
            #     client["namespace"],
            # ]
            raise ClientBootstrapMethodNotSupported(
                """
                Bootstrapping Alias client via executable path is currently not supported. Only Flow Production Tracking clients supported.
                Client info: {client_info}
            """.format(
                    client_info=pprint.pformat(client_info)
                )
            )

        # Copy the env variables to start the new process with
        startup_env = os.environ.copy()

        # Set up the startup info for opening the new process.
        si = subprocess.STARTUPINFO()
        # Only show the console window when in debug mode.
        if os.environ.get("ALIAS_PLUGIN_CLIENT_DEBUG") != "1":
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Start the client in a new a process, don't wait for it to finish.
        self.__log(f"Executing subprocess: {args}")
        subprocess.Popen(args, env=startup_env, startupinfo=si)

        return True

    def restart_client(self, client_namespace):
        """
        Re-bootstrap the client for the given namespace.

        :param client_namespace: Restart the client applicatino registered to the namespace.
        :type client_namespace: str
        """

        self.__log(f"Restarting client {client_namespace}...")

        client = self.get_client_by_namespace(client_namespace)
        if not client:
            return

        return self.bootstrap_client(client)

    # Private methods
    # ----------------------------------------------------------------------------------------

    def __open_server_socket(self, hostname, port, max_retries):
        """
        Open a server socket and return the socket object.

        If `max_retries` is given, the server socket will attempted to be opened on the given
        port number, and if it fails to open (e.g. port already in use) then it will increment
        the given port number by one and try again, until the maximum number of retries are
        attempted. This means that the server socket may not be opened on the specified port.

        :param hostname: The server socket address host name to connect to.
        :type hostname: str
        :param port: The server socket address port number to conenct to.
        :type port: int
        :param max_retries: The number of attempts to make to open the server befor failing.
        :type max_retries: int

        :return: The listening green socket object. None if failed to open.
        :rtype: The socket object.
        """

        hostname = hostname or self.__default_hostname
        port = port if port is not None and port >= 0 else self.__default_port
        max_retry_count = (
            max_retries
            if max_retries is not None and max_retries >= 0
            else self.__max_retry_count
        )
        server_socket = None
        retry_count = 0
        while server_socket is None and retry_count <= max_retry_count:
            try:
                # Open the server socket to start listening on
                # TODO use eventlet.wrap_ssl to create a secure socket layer. For now this is
                # ok since the socket connections will only be on localhost (is this true?)
                return eventlet.listen((hostname, port))
            except OSError:
                # Address is already in use, try the next port.
                port += 1
                retry_count += 1

        # Failed to open the server socket
        return None

    def __serve_app(self):
        """
        Using eventlet, start the WSGI server application to listen for client connections.

        This will allow the server app to start handling requests from the server socket.

        This call is blocking, should be started in a separate thread.
        """

        # Start the WSGI server to start handling requests from the server socket
        #
        # NOTE eventlet is not compatible with Python standard threads. There are issues trying
        # to use eventlet.monkey_patch, so we will need to ensure that the server acts as if it
        # is single threaded (e.g. can only access the socketio server from the thread it was
        # created in).
        wsgi_logger = framework_utils.get_logger(self.__class__.__name__, "wsgi")
        try:
            eventlet.wsgi.server(self.__server_socket, self.__app, log=wsgi_logger)
        except Exception as e:
            wsgi_logger.error(f"Failed to start WSGI server: {e}")
        wsgi_logger.info("WSGI server exited")

    def __log(self, msg, level=logging.INFO):
        """
        Log a message to the logger.

        :param msg: The message to log.
        :type msg: str
        :param level: The log level to log the message at.
        :type level: int
        """

        self.__server_sio.logger.log(level, msg)
