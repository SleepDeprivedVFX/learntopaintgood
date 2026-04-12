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
import pprint
import socketio
from ... import alias_bridge
from ...utils.exceptions import ClientAlreadyConnected


class AliasEventsServerNamespace(socketio.Namespace):
    """
    Server namespace for handling Alias callback events.

    Like the AliasServerNamespace, only a single client is allowed to connect to this
    namespace. The AliasBridge creates a client sio with this namespace to handle forwarding
    Alias callbacks events to the connected client.
    """

    _NAME = "alias-events"

    def __init__(self):
        """Initialize the namespace."""

        self.__client_sid = None

        super().__init__(self.get_namespace())

    # ----------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def get_namespace(cls):
        """Return the namespace string."""
        return f"/{cls._NAME}"

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

    # Event callback methods for namespace
    # ----------------------------------------------------------------------------------------

    def trigger_event(self, event, sid, *args):
        """
        Catch all events and dispatch.

        Find the method associated with the event (e.g. "on_{event_name}") and execute it.

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

    def on_shutdown(self, sid):
        """
        Shutdown the server.

        This event was received from the alias-events client (from the AliasBridge), so the
        AliasBridge will take care of cleaning up the Alias data model. This method just needs
        to forward the shutdown event to all other clients (than the alias-events client).

        :param sid: The session id of the client that triggered the event.
        :type sid: str
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        # Emit event to shutdown all clients in namespaces other than this one.
        self._emit("shutdown")

    def on_restart(self, sid, data):
        """
        Restart the all clients connected to the server.

        This will restart clients in other namespaces. The events client that triggered the
        restart will not be restarted.

        :param sid: The session id of the client that triggered the event.
        :type sid: str
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        # Emit event to shutdown all clients in namespaces other than this one.
        self.on_shutdown(sid)

        # Restart all clients (excluding this events client)
        for namespace in self.server.namespace_handlers:
            if namespace != self.namespace:
                alias_bridge.AliasBridge().restart_client(namespace)

    def on_alias_event_callback(self, sid, data):
        """
        An Alias callback event received.

        Emit an event to all other namespaces to forward the Alias event to the client(s),
        such that the client can execute the corresponding callback function for the Alias
        event, on the client side.

        :param sid: The session id of the client that triggered the event.
        :type sid: str
        """

        if self.client_sid is None or sid != self.client_sid:
            return

        self._log_message(sid, f"Alias Event Callback {data}")

        # Emit event to forward the Alias callback event to all other clients connected to the
        # server (on different namespaces).
        callback_event = data.pop("callback_event")
        self._emit(callback_event, data=data)

    # ----------------------------------------------------------------------------------------
    # Protected methods

    def _log_message(self, sid, msg, level=logging.INFO):
        """Convenience function to log a message."""

        log_msg = f"Server [client={sid}, namespace={self.namespace}] {msg}"
        self.server.logger.log(level, log_msg)

    def _emit(self, *args, **kwargs):
        """Emit event to all other namespaces, except this one."""

        for namespace in self.server.namespace_handlers:
            if namespace != self.namespace:
                kwargs["namespace"] = namespace
                self._log_message(
                    None, f"Forwarding event {args[0]} to namespace {namespace}"
                )
                self.emit(*args, **kwargs)
