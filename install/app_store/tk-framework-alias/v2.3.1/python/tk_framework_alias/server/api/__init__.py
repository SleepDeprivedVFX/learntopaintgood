# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.

import importlib.util
import os
import sys
from ..utils.exceptions import AliasPythonApiImportError

from tk_framework_alias_utils import environment_utils

# Python module names for specific Alias modes
OPEN_ALIAS_API_NAME = "alias_api"
OPEN_MODEL_API_NAME = "alias_api_om"


def get_alias_version():
    """Return the Alias version."""

    # Get the Alias version from the environment variable
    version = environment_utils.get_alias_version()
    if not version:
        msg = "Alias version is not set. Set the environment variable ALIAS_PLUGIN_CLIENT_ALIAS_VERSION (e.g. 2022.2)."
        raise AliasPythonApiImportError(msg)

    return version


def get_module_path(module_name, alias_version):
    """Return the file path to the Alias Python API module to use."""

    api_folder_path = environment_utils.get_alias_dist_dir(
        alias_version, sys.version_info.major, sys.version_info.minor
    )
    if not api_folder_path or not os.path.exists(api_folder_path):
        raise AliasPythonApiImportError(
            "Failed to get Alias Python API module path for Alias {alias_version} and Python {py_version}".format(
                alias_version=alias_version, py_version=sys.version
            )
        )

    module_path = os.path.normpath(
        os.path.join(
            api_folder_path,
            "{}.pyd".format(module_name),
        )
    )
    if not os.path.exists(module_path):
        return None

    return module_path


def get_alias_api_module():
    """
    Import the right Alias Python API module according to the criteria:
        - the version of Alias
        - the execution mode (interactive vs non-interactive)

    The Alias Python API supports Python >= 3
    """

    # Determine the module name based on if running in OpenAlias or OpenModel
    # If the executable is Alias, then it is OpenAlias, else OpenModel.
    is_open_model = os.path.basename(sys.executable) != "Alias.exe"
    module_name = OPEN_MODEL_API_NAME if is_open_model else OPEN_ALIAS_API_NAME
    alias_version = get_alias_version()
    module_path = get_module_path(module_name, alias_version)
    if not module_path:
        return None

    # Find and create the module spec object for the Alias Python API
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec:
        raise AliasPythonApiImportError(
            "Could not find the Alias Python API module {}".format(module_path)
        )

    try:
        # module_from_spec will add the api module to the sys.modules
        api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_module)
    except Exception as e:
        info_msg = (
            "Running: Alias v{alias_version}, Python v{py_major}.{py_minor}.{py_micro}.\n\n"
            "Attempted to import Alias Python API {apa_name}.pyd from: {apa_path}\n\n"
            "Failed import may be caused by a mismatch between the running Alias or Python version and "
            "the versions used to compile the Alias Python API."
        ).format(
            apa_name=module_name,
            apa_path=module_path,
            alias_version=alias_version,
            py_major=sys.version_info.major,
            py_minor=sys.version_info.minor,
            py_micro=sys.version_info.micro,
        )
        raise AliasPythonApiImportError(
            "{error}\n\n{info}".format(error=str(e), info=info_msg)
        )

    return api_module


#
# Get the Alias API module and and make it available through this api module global variable
# 'alias_api', e.g. api.alias_api
#
if hasattr(os, "add_dll_directory"):
    # For Python >= 3.9, ensure that the DLL path is in the search path by using the os method
    # add_dll_directory. Starting in 3.9, the sys.path is no longer used to find DLLs.
    alias_bin_path = os.environ.get("ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH")
    if not alias_bin_path:
        raise AliasPythonApiImportError(
            "Couldn't get Alias bin path: set the environment variable ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH."
        )
    alias_dll_path = os.path.dirname(alias_bin_path)
    with os.add_dll_directory(alias_dll_path):
        alias_api = get_alias_api_module()
else:
    alias_api = get_alias_api_module()
