# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from functools import wraps
from typing import Callable, Any

from .exceptions import AliasClientNotConnected


def check_server_result(func: Callable) -> Any:
    """
    A decorator function to check a value returned by a socketio server.

    It takes a function that is an AliasSocketIoClient method (or a function that passes an
    AliasSocketIoClient object as the first argument) and returns a function that executes the
    main function and handles any errors before returning the result of the main function.

    This is meant to be used to check values returned from calling the socketio client methods
    'call' and 'emit', and handle any server errors.

    :param func: The main function to execute. This should be an AliasSocketIoClient method,
        or a function that passes an AliasSocketIoClient as the first argument.

    :return: The value returned by func.
    """

    @wraps(func)
    def wrapper(client, *args, **kwargs):
        result = func(client, *args, **kwargs)
        if isinstance(result, Exception):
            return client._handle_server_error(result)
        return result

    return wrapper


def check_client_connection(func: Callable) -> Any:
    """
    A decorator function to check if the client is connected to the server.

    It takes a function that is an AliasSocketIoClient method (or a function that passes an
    AliasSocketIoClient object as the first argument) and returns a function that executes the
    main function only if the client is connected to the server.

    This is meant to be used to check if the client is connected to the server before executing
    a function that requires a connection.

    :param func: The main function to execute. This should be an AliasSocketIoClient method,
        or a function that passes an AliasSocketIoClient as the first argument.

    :return: The value returned by func.
    """

    @wraps(func)
    def wrapper(client, *args, **kwargs):
        if not client.connected:
            raise AliasClientNotConnected(
                (
                    "Client disconnected from server and cannot send request. "
                    "Client will automatically attempt to reconnect, but if "
                    "the issue persists you can reload the Alias FPT Plugin "
                    "from the Alias Utilities > Plug-in Manager to try and "
                    "resolve the problem."
                )
            )
        return func(client, *args, **kwargs)

    return wrapper
