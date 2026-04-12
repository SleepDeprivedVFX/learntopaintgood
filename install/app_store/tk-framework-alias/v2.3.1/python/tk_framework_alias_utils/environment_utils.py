from typing import Optional
import os
import sys


TOOLKIT_PLUGIN_NAME = "com.sg.basic.alias"


# --------------------------------------------------------------------------------------------
# User App Data directory paths


def get_alias_app_data_dir():
    """
    Get the user specific root directory for the Alias plugin installation.

    This is for Windows only.

    The plugin will be installed inside the user's Alias AppData folder.

    :return: The file path to the user's Alias App Data folder.
    """

    # The plugin install directory is OS-specific
    if sys.platform == "win32":
        app_data = os.getenv("APPDATA")
    else:
        raise Exception("This plugin only runs on Windows.")

    return os.path.join(app_data, "Autodesk", "Alias", "ShotGrid")


def get_alias_plugin_dir():
    """Return the directory containing the Alias plugin installation."""

    return os.path.join(get_alias_app_data_dir(), "plugin")


def get_plugin_install_dir():
    """Return the file path to the Alias plugin installation for the user."""

    return os.path.join(get_alias_plugin_dir(), TOOLKIT_PLUGIN_NAME)


def get_python_dir(major_version, minor_version):
    """
    Get the base Alis Python install directory for the user.

    :param major_version: The python major version to install for.
    :type major_version: int
    :param minor_version: The python minor version to install for.
    :type minor_version: int

    :return: The file path to the user's Alias AppData Python directory.
    :rtype: str
    """

    return os.path.join(
        get_alias_app_data_dir(), "Python", f"Python{major_version}{minor_version}"
    )


def get_python_install_dir(major_version, minor_version):
    """
    Get the directory to install python for the user.

    If the necessary python version is not found for the current user, the framework can
    install this version for the user.

    :param major_version: The python major version to install for.
    :type major_version: int
    :param minor_version: The python minor version to install for.
    :type minor_version: int

    :return: The file path the user's Alias AppData Python install directory.
    :rtype: str
    """

    return os.path.join(get_python_dir(major_version, minor_version), "install")


def get_python_install_exe(major_version, minor_version):
    """
    Get the path to the python executable that the Alias Plugin should use.

    It is important that the version of Python that the Alias Plugin uses can install the
    version of PySide2 that matches the Qt version used by Alias.

    :param major_version: The python major version to get the executable for.
    :type major_version: int
    :param minor_version: The python minor version to get the executable for.
    :type minor_version: int

    :return: The file path to the python executable.
    :rtype: str
    """

    return os.path.join(
        get_python_install_dir(major_version, minor_version), "python.exe"
    )


def get_python_packages_dir(major_version, minor_version):
    """
    Get the directory to install python packages for the user.

    :param major_version: The python major version to install for.
    :type major_version: int
    :param minor_version: The python minor version to install for.
    :type minor_version: int

    :return: The file path the python install directory.
    :rtype: str
    """

    return os.path.join(get_python_dir(major_version, minor_version), "packages")


def get_installed_python_packages_dir(major_version, minor_version):
    """
    Get the directory to install the 'dist' python packages for the user.

    :param major_version: The python major version to install for.
    :type major_version: int
    :param minor_version: The python minor version to install for.
    :type minor_version: int

    :return: The file path the python install directory.
    :rtype: str
    """

    return os.path.join(get_python_packages_dir(major_version, minor_version), "pkgs")


def get_python_qt_ext_dir(py_major_version, py_minor_version, alias_version=None):
    """
    Get the directory to install python Qt extension packages for the user.

    If `alias_version` is provided, the file path to the qt extensions for the
    specified Alias version will be returned, else the base directory for qt
    extensions for all Alias versions will be returned.

    :param py_major_version: The python major version for the qt extensions.
    :type py_major_version: int
    :param py_minor_version: The python minor version for the qt extensions.
    :type py_minor_version: int
    :param alias_version: The Alias version for the qt extensions.
    :type alias_version: str

    :return: The file path the python install directory.
    :rtype: str
    """

    qt_ext_dir = os.path.join(
        get_python_packages_dir(py_major_version, py_minor_version),
        "qt",
    )
    if alias_version:
        return os.path.join(qt_ext_dir, alias_version, "qt_extensions")
    return qt_ext_dir


# --------------------------------------------------------------------------------------------
# Framework directory paths


def get_framework_python_path():
    """Return the normalized file path to the root python directory."""

    # Relative to this file location
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
        )
    )


# --------------------------------------------------------------------------------------------
# Framework 'dist' directory paths


def get_dist_dir():
    """Return the normalized path to the framework directory containing all distribution files."""

    # Relative to this file location
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            "dist",
        )
    )


def get_python_dist_dir(major_version, minor_version):
    """
    Return the framework directory containing the Python distribution files.

    :param major_version: The Python major version to get the distribution for.
    :type major_version: int
    :param minor_version: The Python minor version to get the distribution for.
    :type minor_version: int

    :return: The normalized path to the framework Python distribution files.
    :rtype: str
    """

    python_folder_name = f"Python{major_version}{minor_version}"
    dist_base_path = get_dist_dir()
    return os.path.normpath(
        os.path.join(
            dist_base_path,
            "Python",
            python_folder_name,
        )
    )


def get_python_dist_install_dir(major_version, minor_version):
    """
    Return the directory containing the embedable Python install files.

    :param major_version: The python major version to get the install for.
    :type major_version: int
    :param minor_version: The python minor version to get the install for.
    :type minor_version: int

    :return: The file path containing the install files.
    :rtype: str
    """

    python_dist_path = get_python_dist_dir(major_version, minor_version)
    return os.path.normpath(os.path.join(python_dist_path, "install"))


def get_python_dist_packages_dir(major_version, minor_version):
    """
    Get the directory containing the local pre-installed packages.

    :param major_version: The python major version to get the packages for.
    :type major_version: int
    :param minor_version: The python minor version to get the packages for.
    :type minor_version: int

    :return: The packages file path.
    :rtype: str
    """

    python_dist_path = get_python_dist_dir(major_version, minor_version)
    return os.path.normpath(os.path.join(python_dist_path, "packages"))


def get_python_dist_packages_zip(major_version, minor_version):
    """
    Get the framework distribution for the Python standard modules.

    :param major_version: The python major version to get the zip for.
    :type major_version: int
    :param minor_version: The python minor version to get the zip for.
    :type minor_version: int

    :return: The packages zip file path.
    :rtype: str
    """

    packages_path = get_python_dist_packages_dir(major_version, minor_version)
    return os.path.normpath(os.path.join(packages_path, "pkgs.zip"))


def get_python_dist_qt_ext_dir(py_major_version, py_minor_version):
    """
    Get the framework distribution directory containing the Qt extension modules.

    This is the base directory for Qt extensions for all Alias versions.

    :param py_major_version: The python major version to get the qt extensions for.
    :type py_major_version: int
    :param py_minor_version: The python minor version to get the qt extensions for.
    :type py_minor_version: int

    :return: The base Qt extensions directory for all Alias versions.
    :rtype: str
    """

    python_dist_path = get_python_dist_packages_dir(py_major_version, py_minor_version)
    return os.path.normpath(os.path.join(python_dist_path, "qt"))


def get_python_dist_qt_ext_zip(py_major_version, py_minor_version, alias_version):
    """
    Get the framework distribution zip folder containing the Qt extension modules.

    :param py_major_version: The python major version to get the zip for.
    :type py_major_version: int
    :param py_minor_version: The python minor version to get the zip for.
    :type py_minor_version: int

    :return: The Qt extensions zip file for the specified Alias version.
    :rtype: str
    """

    qt_dist_path = get_python_dist_qt_ext_dir(py_major_version, py_minor_version)
    return os.path.normpath(
        os.path.join(qt_dist_path, alias_version, "qt_extensions.zip")
    )


def get_alias_dist_dir(alias_version, python_major_version, python_minor_version):
    """
    Return the directory containing the Alias distribution files.

    This directory contains the Alias .plugin and Alias Python API .pyd files. The directory
    is determined based on the requested Alias and Python versions.

    :param alias_version: The Alias version to look up the directory by.
    :type alias_version: str
    :param python_major_version: The python major version to look up the directory by.
    :type python_major_version: int
    :param python_minor_version: The python minor verison to look up the directory by.
    :type python_minor_version: int

    :return: The file path to the Alias distribution directory.
    :rtype: str
    """

    from .utils import version_cmp

    # First try to get the folder directly matching the running version of Alias
    python_folder_name = f"python{python_major_version}.{python_minor_version}"
    dist_base_path = get_dist_dir()
    base_folder_path = os.path.normpath(
        os.path.join(
            dist_base_path,
            "Alias",
            python_folder_name,
        )
    )
    dist_folder_path = os.path.join(base_folder_path, alias_version)
    if os.path.exists(dist_folder_path):
        return dist_folder_path

    # Alias distribution not found for exact version, fallback to the next supported version.
    alias_dist_versions = sorted(os.listdir(base_folder_path))
    last_version = alias_dist_versions[0]
    if version_cmp(alias_version, last_version) < 0:
        return None  # requested version does not meet minimum supported vesrion
    # Go through all supported versions, get the highest supported version that is not higher
    # than the requested version.
    for cur_version in alias_dist_versions[1:]:
        if version_cmp(alias_version, cur_version) < 0:
            return os.path.join(base_folder_path, last_version)
        last_version = cur_version

    # The requested version is higher than all supported versions, return the highest
    # supported version available.
    return os.path.join(base_folder_path, last_version)


# --------------------------------------------------------------------------------------------
# Convenience functions for the framework


def get_framework_python_qt_site_packages_path(
    py_major_version, py_minor_version, alias_version
):
    """
    Get the directory to the Qt extension packages for the specified Python and Alias version.

    :param py_major_version: The python major version to get the packages for.
    :type py_major_version: int
    :param py_minor_version: The python minor version to get the packages for.
    :type py_minor_version: int
    :param alias_version: The Alias version to get the packages for.
    :type alias_version: str

    :return: The file path to the Qt extension package.
    :rtype: str
    """

    from .utils import version_cmp

    # Check the framework distribution folder for Qt extension packages
    if not alias_version:
        return

    alias_qt_ext_path = get_python_qt_ext_dir(
        py_major_version, py_minor_version, alias_version
    )
    if os.path.exists(alias_qt_ext_path):
        return alias_qt_ext_path

    # Alias version not found, try to find the next closest version
    qt_ext_path = get_python_qt_ext_dir(py_major_version, py_minor_version)
    if not os.path.exists(qt_ext_path):
        return

    alias_dist_versions = sorted(os.listdir(qt_ext_path))
    if not alias_dist_versions:
        return

    last_version = alias_dist_versions[0]
    if version_cmp(alias_version, last_version) < 0:
        return  # requested version does not meet minimum supported vesrion

    # Go through all supported versions, get the highest supported version that is not higher
    # than the requested version.
    for cur_version in alias_dist_versions[1:]:
        if version_cmp(alias_version, cur_version) < 0:
            return get_python_qt_ext_dir(
                py_major_version, py_minor_version, last_version
            )
        last_version = cur_version


def get_framework_python_site_packages_paths(
    py_major_version, py_minor_version, alias_version=None
):
    """
    Get the list of python packages paths to the modules that the framework requires.

    :param py_major_version: The python major version to get the executable for.
    :type py_major_version: int
    :param py_minor_version: The python minor version to get the executable for.
    :type py_minor_version: int
    :param alias_version: The Alias version to get the packages for.
    :type alias_version: str

    :return: The file paths to the python site packages.
    :rtype: List[str]
    """

    alias_version = alias_version or get_alias_version()
    package_paths = []

    # Check for the user app data packages (installed dynamically with pip)
    installed_packages_path = os.path.join(
        get_python_install_dir(py_major_version, py_minor_version),
        "Lib",
        "site-packages",
    )
    if os.path.exists(installed_packages_path):
        package_paths.append(installed_packages_path)

    # Check the user local install directory for the 'dist' packages
    installed_dist_packages_path = get_installed_python_packages_dir(
        py_major_version, py_minor_version
    )
    if os.path.exists(installed_dist_packages_path):
        package_paths.append(installed_dist_packages_path)

    # Check the framework distribution folder for Qt extension packages
    alias_qt_ext_path = get_framework_python_qt_site_packages_path(
        py_major_version, py_minor_version, alias_version
    )
    if alias_qt_ext_path and os.path.exists(alias_qt_ext_path):
        package_paths.append(alias_qt_ext_path)

    return package_paths


def get_alias_api_cache_file_path(
    filename: str,
    alias_version: str,
    python_version: str,
    file_ext: Optional[str] = "json",
) -> str:
    """
    Return the file path to the cached api .json file.

    The cache is for the specified Alias and Python version.

    :param filename: The cache file name.
    :param alias_version: The Alias version to get the cache for.
    :param python_version: The python version to get the cache for.
    :param file_ext: The file extension for the cache file, defaults to 'json'.

    :return: The file name for the embeddable python package.
    """

    return os.path.join(
        get_alias_app_data_dir(),
        "api",
        f"{filename}{alias_version}_py{python_version}.{file_ext}",
    )


def get_python_embed_package_name(major_version, minor_version):
    """
    Return the name of the embeddable python package.

    :param major_version: The python major version to get the package for.
    :type major_version: int
    :param minor_version: The python minor version to get the package for.
    :type minor_version: int

    :return: The file name for the embeddable python package.
    :rtype: str
    """

    return f"python-{major_version}.{minor_version}-embed-amd64"


def get_framework_supported_python_versions():
    """
    Return the Python versions that the framework supports.

    The versions returned will be in the format of a tuple, where (1) is the Python major
    version and (2) is the Python minor version.

    :return: The supported Python versions for the framework.
    :rtype: List[Tuple[int,int]]
    """

    return [
        (3, 7),
        (3, 9),
        (3, 10),
        (3, 11),
    ]


def get_alias_version():
    """Convenience function to get the Alias version set in the environment."""

    return os.environ.get("ALIAS_PLUGIN_CLIENT_ALIAS_VERSION")
