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


def check_server_result(func):
    """
    A decorator function to check a value returned by a socketio server.

    It takes a function that is an AliasSocketIoClient method (or a function that passes an
    AliasSocketIoClient object as the first argument) and returns a function that executes the
    main function and handles any errors before returning the result of the main function.

    This is meant to be used to check values returned from calling the socketio client methods
    'call' and 'emit', and handle any server errors.

    :param func: The main function to execute. This should be an AliasSocketIoClient method,
        or a function that passes an AliasSocketIoClient as the first argument.
    :type func: function

    :return: The value returned by func.
    :rtype: any
    """

    @wraps(func)
    def wrapper(client, *args, **kwargs):
        try:
            result = func(client, *args, **kwargs)
        except Exception as error:
            result = error

        if isinstance(result, Exception):
            return client._handle_server_error(result)
        return result

    return wrapper
