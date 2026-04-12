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
import socketio
from .events_namespace import AliasEventsServerNamespace


class AliasEventsClientNamespace(socketio.ClientNamespace):
    """
    Namespace for the Alias Events client.

    This client namespace is meant to be used with the AliasEventsServerNamespace.
    """

    def __init__(self):
        """Initialize the namespace."""

        namespace = AliasEventsServerNamespace.get_namespace()
        super(AliasEventsClientNamespace, self).__init__(namespace)

    # ----------------------------------------------------------------------------------------
    # Event callback methods for namespace

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

    # ----------------------------------------------------------------------------------------
    # Protected methods

    def _log_message(self, msg, level=logging.INFO):
        """Convenience function to log a message."""

        log_msg = f"Client [sid={self.client.sid}, namespace={self.namespace}] {msg}"
        self.client.logger.log(level, log_msg)
