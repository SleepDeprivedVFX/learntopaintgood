# Copyright (c) 2024 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

# NOTE: remove invoker entirely when all support Alias versions have
# `addAsyncTask` functionality (>= 2026.0)

from .exceptions import QtModuleNotFound, QtAppInstanceNotFound


QtCore = None
QtCore5 = None
qt_app = None

# Determine the Qt version to import.
# Alias < 2025.0 uses Qt5/PySide2, Alias >= 2025.0 uses Qt6/PySide6
# We will know we have the correct Qt version once we have imported the QtCore module and
# have access to the qt app instance. First try import PySide2:
try:
    from PySide2 import QtCore

    QtCore5 = QtCore
    qt_app = QtCore.QCoreApplication.instance()
except Exception:
    pass

# Check if Qt was import successfully, if not try PySide6.
if not (QtCore and qt_app):
    if QtCore:
        # Reset QtCore if it was previously imported
        del QtCore
        QtCore = None
    try:
        from PySide6 import QtCore

        qt_app = QtCore.QCoreApplication.instance()
    except Exception:
        pass

# Verify that Qt was imported, and the qt app is accessible
if not (QtCore or QtCore5):
    raise QtModuleNotFound("Failed to import Qt for Python.")

if not qt_app:
    if QtCore:
        raise QtAppInstanceNotFound(
            f"Qt App instance not found for Qt {QtCore.__version__}"
        )
    else:
        raise QtAppInstanceNotFound(
            f"Qt App instance not found for Qt {QtCore5.__version__}"
        )
