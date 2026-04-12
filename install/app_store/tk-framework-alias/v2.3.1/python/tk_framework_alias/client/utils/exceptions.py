# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.


class AliasClientException(Exception):
    """Custom exception for reporting Alias client errors."""


class AliasClientNotFound(AliasClientException):
    """Custom exception for reporting Alias client not found."""


class AliasClientJSONEncoderError(AliasClientException):
    """Custom exception for reporting Alias client JSON encoder errors."""


class AliasClientBatchRequestError(AliasClientException):
    """Custom exception for reporting Alias client api batch request errors."""


class AliasClientNotConnected(ConnectionError):
    """Custom exception for reporting Alias client not connected."""
