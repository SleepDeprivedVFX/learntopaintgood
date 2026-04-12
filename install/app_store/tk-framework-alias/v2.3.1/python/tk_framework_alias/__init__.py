# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

# First add our third-party package paths to sys.path
import sys
from tk_framework_alias_utils.environment_utils import (
    get_framework_python_site_packages_paths,
)

for p in get_framework_python_site_packages_paths(
    sys.version_info.major, sys.version_info.minor
):
    sys.path.insert(0, p)

from . import client
from . import server
