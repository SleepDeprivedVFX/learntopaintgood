# Copyright (c) 2021 Autoiesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import pytest
import os
import sys

from tk_framework_alias_utils import startup


####################################################################################################
# tk_framework_alias_utils startup.py Test Cases
####################################################################################################


def test_get_plugin_environment():
    """Test the startup.py get_plugin_environment function."""

    alias_version = "2024.0"
    alias_exe_path = "path/to/alias.exe"
    client_name = "shotgrid"
    client_exe_path = "path/to/shotgrid/bootstrap.py"
    debug = "1"

    result = startup.get_plugin_environment(
        alias_version, alias_exe_path, client_name, client_exe_path, debug=debug
    )

    assert result["ALIAS_PLUGIN_CLIENT_ALIAS_VERSION"] == alias_version
    assert result["ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH"] == alias_exe_path
    assert result["ALIAS_PLUGIN_CLIENT_NAME"] == client_name
    assert result["ALIAS_PLUGIN_CLIENT_EXECPATH"] == client_exe_path
    assert result["ALIAS_PLUGIN_CLIENT_DEBUG"] == debug
    assert result["ALIAS_PLUGIN_CLIENT_PYTHON"] == sys.executable


def test_get_plugin_environment_default_args():
    """Test the startup.py get_plugin_environment function default args."""

    alias_version = "2024.0"
    alias_exe_path = "path/to/alias.exe"
    client_name = "shotgrid"
    client_exe_path = "path/to/shotgrid/bootstrap.py"

    result = startup.get_plugin_environment(
        alias_version, alias_exe_path, client_name, client_exe_path
    )

    assert result["ALIAS_PLUGIN_CLIENT_DEBUG"] == "0"


def test_get_plugin_dir():
    """Test the startup.py get_plugin_dir function."""

    plugin_dir = startup.get_plugin_dir()

    assert plugin_dir is not None
    assert os.path.exists(plugin_dir)


@pytest.mark.parametrize(
    "python_major_version,python_minor_version,alias_version",
    [
        # List all supported plugins to ensure they can be found
        (3, 7, "2024.0"),
        (3, 9, "2024.0"),
    ],
)
def test_get_plugin_file_path(
    python_major_version, python_minor_version, alias_version
):
    """Test the startup.py get_plugin_file_path function."""

    plugin_file_path = startup.get_plugin_file_path(
        alias_version, python_major_version, python_minor_version
    )

    assert plugin_file_path is not None
    assert os.path.exists(plugin_file_path)


def test_ensure_plugin_installed():
    """Test the startup.py ensure_plugin_installed function."""

    python_major_version = 3
    python_minor_version = 7
    alias_version = "2024.0"

    plugin_file_path = startup.get_plugin_file_path(
        alias_version, python_major_version, python_minor_version
    )
    lst_file = startup.ensure_plugin_installed(
        alias_version, python_major_version, python_minor_version
    )

    assert lst_file is not None
    assert os.path.exists(lst_file)

    with open(lst_file, "r") as fp:
        lines = fp.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == plugin_file_path

    # Clean up the temp file .lst file that was created
    os.remove(lst_file)
    assert not os.path.exists(lst_file)
