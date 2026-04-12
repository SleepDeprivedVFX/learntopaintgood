# Copyright (c) 2024 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from .exceptions import QtImportError, QtModuleNotFound, QtAppInstanceNotFound


QtCore = None
qt_app = None

# Determine the Qt version to import.
# Alias < 2025.0 uses Qt 5.15.0, Alias >= 2025.0 uses Qt 6.2.10.
# We will know we have the correct Qt version once we have imported the QtCore module and
# have access to the qt app instance. First try import PySide2:
try:
    # Alias < 2025.0 uses Qt 5.15.0
    from PySide2 import QtCore

    if QtCore:
        qt_app = QtCore.QCoreApplication.instance()
except Exception:
    raise QtImportError("Failed to import PySide2")

# Check if Qt was import successfully, if not try PySide6.
if not QtCore or not qt_app:
    if QtCore:
        # Reset QtCore if it was previously imported
        del QtCore
        QtCore = None
    try:
        # Alias >= 2025.0 uses Qt 6.2.10
        from PySide6 import QtCore

        if QtCore:
            qt_app = QtCore.QCoreApplication.instance()
    except Exception:
        raise QtImportError("Failed to import PySide6")

# Verify that QtCore module was imported and exists, and the qt app is accessible
if not QtCore:
    raise QtModuleNotFound("QtCore module not found")
if not qt_app:
    raise QtAppInstanceNotFound(
        f"Qt App instance not found for Qt {QtCore.__version__}"
    )
