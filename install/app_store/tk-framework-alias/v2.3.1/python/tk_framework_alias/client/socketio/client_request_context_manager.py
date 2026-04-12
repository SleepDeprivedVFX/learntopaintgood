# Copyright (c) 2024 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from typing import Optional

from .proxy_wrapper import AliasClientModuleProxyWrapper
from ..utils.exceptions import AliasClientBatchRequestError


class ClientRequestContextManager:
    """
    A context manager to handle executing multiple requests at once.

    The purpose of executing multiple requests at once is to reduce the number
    of socketio requests that are sent to the server. This is useful when
    multiple requests are made in quick succession, and it is more efficient to
    send them all at once.
    """

    def __init__(
        self,
        api_module_proxy: AliasClientModuleProxyWrapper,
        is_async: Optional[bool] = False,
    ):
        """
        Initialize the context manager.

        :param AliasClientModuleProxyWrapper api_module_proxy: The Alias api proxy module.
        :param is_async:
        """

        self.__api_module_proxy = api_module_proxy
        self.__is_async = is_async
        self.__result = []

    @property
    def result(self):
        """The result of the batched requests."""
        return self.__result

    def __enter__(self):
        """
        Enter the context manager.

        Set the Alias api proxy module to batched mode. This will defer requests
        until we signal to execute all at once, when we exit the context
        manager.
        """

        if self.__api_module_proxy:
            # Start batched mode: defer requests until we signal to execute all at
            # once
            self.__api_module_proxy.batch_requests(True)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager.

        Execute all deferred requests and store the result.
        """

        if not self.__api_module_proxy:
            return

        # Frist, get the number of pending requests, so that we can check that
        # the result is returned successfully
        num_requests = self.__api_module_proxy.num_pending_requests

        # Execute batched requests. Result is expected to be a list of values,
        # one for each request made.
        self.__result = self.__api_module_proxy.batch_requests(
            False, is_async=self.__is_async
        )

        # No result will be returned when executing async
        if self.__is_async:
            return

        # Check that the result was returned successfully
        if self.__result is None:
            self.__result = []
            raise AliasClientBatchRequestError("Expected a result but None returned.")
        elif len(self.__result) != num_requests:
            raise AliasClientBatchRequestError(
                f"Expected {num_requests} results, but got {len(self.__result)} results."
            )
