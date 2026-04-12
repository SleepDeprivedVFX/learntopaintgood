# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.


class Singleton(type):
    """A singleton class."""

    # Keep track of which singleton class types have an object already created.
    _intances = {}

    def __call__(cls, *args, **kwargs):
        """Intercept the new method to ensure only one instance of this type is created."""

        if cls not in cls._intances:
            cls._intances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._intances[cls]
