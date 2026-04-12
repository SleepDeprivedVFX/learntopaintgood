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
import threading
from ..api import alias_api


# NOTE: remove this function and the invoker entirely when all supported Alias
# versions have `addAsyncTask` functionality (>= 2026.0)
def execute_in_main_thread(func):
    """
    Decorator function to ensure function is executed in main thread.

    This could be replaced with using the Alias API AlAsyncTask addAsyncTask function. Thex
    addAsyncTask function would execute the api function in the main thread synchronoushly
    with Alias events. Though, this requires refactoring Alias API requests to work in an
    asynchronous way.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Use the Alias API `add_async_task` to execute the api request
            # through the Alias application events queue (which will be on the
            # main thread). If the `add_async_task` function is not available,
            # then we will use the invoker to execute the function in the main
            # thread.
            if hasattr(alias_api, "add_async_task"):
                return func(*args, **kwargs)

            # We need to create the invoker each time, because it gets moved to the main thread, at
            # which point the inovker is no longer safe to access from the thread executing to
            # invoke the function with the invoker
            invoker = create_invoker()
            return invoker.invoke(func, *args, **kwargs)
        except Exception as error:
            # Return (instead of raise) the error to pass it back to the client
            return error

    return wrapper


def create_invoker():
    """Create an object used to invoke function calls on the main thread when called from a different thread."""

    # Import Qt at the time when needed to ensure Alias has initialized the Qt app (instead of
    # importing at the global scope).
    from .qt import QtCore, qt_app

    class Invoker(QtCore.QObject):
        """
        Invoker class - implements a mechanism to execute a function with arbitrary
        args in the main thread.
        """

        def __init__(self):
            """
            Construction
            """
            QtCore.QObject.__init__(self)
            self._lock = threading.Lock()
            self._fn = None
            self._res = None

        def invoke(self, fn, *args, **kwargs):
            """
            Invoke the specified function with the specified args in the main thread

            :param fn:          The function to execute in the main thread
            :param *args:       Args for the function
            :param **kwargs:    Named arguments for the function
            :returns:           The result returned by the function
            """
            # acquire lock to ensure that the function and result are not overwritten
            # by syncrounous calls to this method from different threads
            self._lock.acquire()
            try:
                self._fn = lambda: fn(*args, **kwargs)
                self._res = None

                # invoke the internal _do_invoke method that will actually run the function.  Note that
                # we are unable to pass/return arguments through invokeMethod as this isn't properly
                # supported by PySide.
                QtCore.QMetaObject.invokeMethod(
                    self, "_do_invoke", QtCore.Qt.BlockingQueuedConnection
                )

                return self._res
            finally:
                self._lock.release()

        @QtCore.Slot()
        def _do_invoke(self):
            """Execute the function."""
            self._res = self._fn()

    # Make sure that the invoker exists in the main thread:
    invoker = Invoker()
    invoker.moveToThread(qt_app.thread())

    return invoker
