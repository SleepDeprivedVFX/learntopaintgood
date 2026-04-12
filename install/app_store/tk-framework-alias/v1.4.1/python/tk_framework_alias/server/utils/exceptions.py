# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.


# AliasBridge exceptions
# ----------------------------------------------------------------------------------------


class AliasBridgeException(Exception):
    """Exception for AliasBridge errors."""


class ClientAlreadyRegistered(AliasBridgeException):
    """Exception for AliasBridge when attempting to register a client that is already registered."""


class ClientNameReservered(AliasBridgeException):
    """Exception for AliasBridge when attempting to register a client whose name is in the reserved list."""


class ClientBootstrapMethodNotSupported(AliasBridgeException):
    """Exception for AliasBridge when attempting to register a client whose name is in the reserved list."""


class ServerAlreadyRunning(AliasBridgeException):
    """Exception for AliasBridge when attempting to connect to server when it is already running."""


# AliasServerNamespace exceptions
# ----------------------------------------------------------------------------------------


class ClientAlreadyConnected(Exception):
    """Exception for AliasServerNamespace errors."""


# AliasServerJSON exceptions
# ----------------------------------------------------------------------------------------


class AliasServerJSONDecoderError(Exception):
    """Exception for Alias server JSON decoder errors."""


# AliasPythonApi exceptions
# ----------------------------------------------------------------------------------------


class AliasPythonApiImportError(Exception):
    """Exception for Alias Python API import errors."""


# AliasApiRequest exceptions
# ----------------------------------------------------------------------------------------


class AliasApiRequestException(Exception):
    """Exception for Alias API request errors."""


class AliasApiRequestNotValid(AliasApiRequestException):
    """Exception for Alias API request not valid error."""


class AliasApiRequestNotSupported(AliasApiRequestException):
    """Exception for Alias API request not supported error."""


class AliasApiPostProcessRequestError(AliasApiRequestException):
    """Exception for Alias API request post process error."""


# Qt exceptions
# ----------------------------------------------------------------------------------------


class QtImportError(Exception):
    """Base Exception for errors related to importing the Qt framework module."""


class QtModuleNotFound(QtImportError):
    """
    Exception thrown when Qt was imported without error but a specific Qt module was not found.

    If Qt was imported without error but a specific Qt module was not found, then this
    indicates that the error is due to the Qt version used by Alias and the PySide version used
    by the framework are not compatibile. To avoid this Qt version mismatch error, the PySide
    version should match the version that Alias is running with.
    """


class QtAppInstanceNotFound(QtImportError):
    """
    Exception thrown when Qt was imported and modules found wihtout error but the Qt app
    instance was not found.

    Alias creates the Qt app instance that this framework will interact with. The Qt app is
    shared between C++ and Python.

    This error may occur for developers when running in Debug mode with Alias, and there are
    no debug symbols available for PySide.
    """
