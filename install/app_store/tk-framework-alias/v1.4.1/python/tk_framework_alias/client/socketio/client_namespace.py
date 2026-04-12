# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import logging
import socketio


class AliasClientNamespace(socketio.ClientNamespace):
    """
    Namespace for a client to communicate with Alias.

    This namespace is meant to be registered to an AliasSocketIoClient.
    """

    # ----------------------------------------------------------------------------------------
    # Event callback methods for namespace

    def trigger_event(self, event, *args):
        """
        Catch and handle all server events.

        Look up the method for the event, if it is found, the event method is executed. An
        event method is defined as "on_{event_name}". If an event method is not found, then
        next check if the event is a callback event. If a callback function is found for the
        event, the callback function is executed.

        :param event: The event received.
        :type event: str
        :param args: The arguments passed from the server for this event.
        :type args: List
        """

        # Look up the method for the event
        event_method_name = f"on_{event}"
        if hasattr(self, event_method_name):
            event_method = getattr(self, event_method_name)
            if callable(event_method):
                return event_method(*args)

        # No specific event found, check if this is a callback from Alias.
        callback_function = self.client.get_callback(event)
        if callback_function:
            return self._handle_callback(callback_function, *args)

    def on_connect(self):
        """Connect event."""

        self._log_message("Connection established")

    def on_connect_error(self, data):
        """
        Connect error event.

        :param data: Information related to the error.
        :type data: any
        """

        self._log_message(f"Connection failed\n{data}")

    def on_disconnect(self):
        """Disconnect event."""

        self._log_message("Disconnected from server")
        self.client.cleanup()

    def on_shutdown(self):
        """Shutdown event."""

        try:
            # Disconnect from the server.
            self.disconnect()
        except:
            # Do nothing, the server may have already dropped.
            pass

    # ----------------------------------------------------------------------------------------
    # Protected methods

    def _handle_callback(self, callback_func, data=None):
        """
        Handle a callback event triggered by the server.

        :param callback_func: The callback function to execute.
        :type callback_func: function
        :param data: A dictionary containing the arguments to pass to the function.
        :type data: dict (required keys: args, kwargs)

        :return: The return value of the callback function.
        :rtype: any
        """

        data = data or {}
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})

        self.client.logger.debug(
            f"Executing callback function {callback_func.__name__}"
        )
        return callback_func(*args, **kwargs)

    def _log_message(self, msg, level=logging.INFO):
        """Convenience function to log a message."""

        log_msg = f"Client [sid={self.client.sid}, namespace={self.namespace}] {msg}"
        self.client.logger.log(level, log_msg)
