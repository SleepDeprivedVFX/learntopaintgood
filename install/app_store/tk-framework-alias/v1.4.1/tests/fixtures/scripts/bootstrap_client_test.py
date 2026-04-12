# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import os
import sys


def bootstrap_client(hostname, port, client_namespace):
    """
    To test the AliasBridge.bootstrap_client method, use this function.

    This will create a socketio client and connect to the server. The unit test can validate
    that the bootstrap was successful by checking that the client connected to the server.

    :param hostname: The host name of the server that the Alias Engine should connect to, to
        communicate with Alias.
    :type hostname: str
    :param port: The server port to connect to.
    :type port: str
    :param shotgrid_namespace: The server namespace to connect to.
    :type shotgrid_namespace: str

    :return: 0 for success else 1
    :rtype: int
    """

    base_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "python",
        )
    )
    tk_framework_alias = os.path.abspath(os.path.join(base_dir, "tk_framework_alias"))
    sys.path.insert(0, base_dir)
    sys.path.insert(1, tk_framework_alias)

    from tk_framework_alias.client.socketio.client import AliasSocketIoClient
    from tk_framework_alias.client.socketio.client_namespace import AliasClientNamespace

    client = AliasSocketIoClient()
    namespace_handler = AliasClientNamespace(client_namespace)
    client.add_namespace(namespace_handler)
    client.start(hostname, port)

    return 0


if __name__ == "__main__":
    """Script to use for testing bootstrapping a client from the AliasBridge class."""

    # import debugpy
    # debugpy.listen(5678)
    # debugpy.wait_for_client()

    args = sys.argv[1:]
    ret = bootstrap_client(*args)
    sys.exit(ret)
