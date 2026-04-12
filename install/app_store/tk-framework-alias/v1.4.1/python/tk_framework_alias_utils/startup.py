# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging
import os
import sys
import tempfile
import traceback
import shutil
import zipfile
import pprint
import subprocess
import zipfile

from . import environment_utils
from .utils import version_cmp, encrypt_to_str, verify_file


def get_plugin_environment(
    alias_version,
    alias_exec_path,
    client_name,
    client_exe_path=None,
    client_python_exe=None,
    server_python_exe=None,
    pipeline_config_id=None,
    entity_type=None,
    entity_id=None,
    hostname=None,
    port=None,
    debug="0",
    new_process=False,
):
    """
    Return a dictionary containing the env vars required to launch the plugin.

    Environment:
        ALIAS_PLUGIN_CLIENT_NAME - name used to uniquely identify the Alias client app
        ALIAS_PLUGIN_CLIENT_EXECPATH - path to python script to start the client app
        ALIAS_PLUGIN_CLIENT_PYTHON - the path to the python exe to run the python script
        ALIAS_PLUGIN_CLIENT_DEBUG - indicate debug mode on or off
        ALIAS_PLUGIN_CLIENT_ALIAS_VERSION - the Alias version the client is requesting
        ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH - the path to the Alias exe
        ALIAS_PLUGIN_SERVER_PYTHON - The Alias Plugin should use this version of Python to
            embed in the same process as Alias. To ensure the Alias Plugin uses the correct
            Python version, Alias can be launched from a Python script where the Python
            version is this one.
        ALIAS_PLUGIN_CLIENT_PYTHON - The Python version that the client should use. This
            version of Python will be used when creating a new process to execute the client.
        ALIAS_PLUGIN_CLIENT_NEW_PROCESS - "1" if the client should execute in a separate
            process than Alias, else "0"
        ALIAS_PLUGIN_CLIENT_SHOTGRID_PIPELINE_CONFIG_ID - For Flow Production Tracking clients, the id of the
            pipeline configuration can be set for the Toolkit Manager to bootstrap the engine
        ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_TYPE - For Flow Production Tracking clients, the entity type can be
            set for the Toolkit Manager to bootstrap the engine
        ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_ID - For Flow Production Tracking clients, the entity id can be set
            for the Toolkit Manager to bootstrap the engine
        ALIAS_PLUGIN_CLIENT_SIO_HOSTNAME - the host for the socketio server to connect to
        ALIAS_PLUGIN_CLIENT_SIO_PORT - the port number for the socketio server to connect to

    :param alias_version: The Alias version that the plugin is running with.
    :type alias_version: str
    :param client_name: The name of the client. This will be used by the plugin to set up a
        communication channel with Alias.
    :type client_name: str
    :param client_exe_path: The path to the python script used by the plugin to start the
        client application.
    :type client_exe_path: str
    :param python_exe: Option to specify a python.exe to run the client app with. Defaults
        to the sys.executable
    :type python_exe: str
    :param debug: Set to "1" to run in debug mode, else "0" for non-debug mode.
    :type debug: str

    :return: The plugin environment.
    :rtype: dict
    """

    env = {
        "ALIAS_PLUGIN_CLIENT_PYTHON": client_python_exe or sys.executable,
        "ALIAS_PLUGIN_CLIENT_NAME": client_name,
        "ALIAS_PLUGIN_CLIENT_DEBUG": debug,
        "ALIAS_PLUGIN_CLIENT_ALIAS_VERSION": alias_version,
        "ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH": alias_exec_path,
        "ALIAS_PLUGIN_CLIENT_NEW_PROCESS": "1" if new_process else "0",
    }

    if server_python_exe is not None:
        env["ALIAS_PLUGIN_SERVER_PYTHON"] = server_python_exe

    if client_exe_path is not None:
        env["ALIAS_PLUGIN_CLIENT_EXECPATH"] = encrypt_to_str(client_exe_path)

    if pipeline_config_id is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_PIPELINE_CONFIG_ID"] = str(pipeline_config_id)

    if entity_type is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_TYPE"] = str(entity_type)

    if entity_id is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_ID"] = str(entity_id)

    if hostname is not None:
        env["ALIAS_PLUGIN_CLIENT_SIO_HOSTNAME"] = str(hostname)

    if port is not None:
        env["ALIAS_PLUGIN_CLIENT_SIO_PORT"] = str(port)

    return env


def get_plugin_filename(alias_version, python_major_version, python_minor_version):
    """Return the name of the plugin for the Alias version."""

    if version_cmp(alias_version, "2024") >= 0:
        # Alias >= 2024.0
        return f"alias_py{python_major_version}.{python_minor_version}"

    if version_cmp(alias_version, "2022.2") >= 0:
        # Alias >= 2022.2
        return "shotgrid"

    # Alias < 2022.2
    return "shotgun"


def get_plugin_file_path(alias_version, python_major_version, python_minor_version):
    """
    Get the file path to the plugin file given the python and alias version.

    :param alias_version: Find the plugin for this Alias version
    :type alias_version: str
    :param python_major_version: Find the plugin for this python major version.
    :type python_major_version: int
    :param python_minor_version: Find the plugin for this python minor version.
    :type python_minor_version: int

    :return: The file path to the plugin file.
    :rtype: str
    """

    plugin_folder_path = environment_utils.get_alias_dist_dir(
        alias_version, python_major_version, python_minor_version
    )
    if plugin_folder_path is None:
        raise Exception(
            f"Alias Plugin folder not found for Alias {alias_version} Python {python_major_version}.{python_minor_version}"
        )

    plugin_filename = get_plugin_filename(
        alias_version, python_major_version, python_minor_version
    )
    plugin_file_path = os.path.normpath(
        os.path.join(
            plugin_folder_path,
            "{}.plugin".format(plugin_filename),
        )
    )
    if plugin_file_path is None or not os.path.exists(plugin_file_path):
        raise Exception(
            f"Alias Plugin not found for Alias {alias_version} Python {python_major_version}.{python_minor_version}"
        )

    return plugin_file_path


def __ensure_toolkit_plugin_up_to_date(logger):
    """
    Ensure the basic Alias plugin is up to date.

    Install the plugin to the OS-specific location defined by the environment utils, if it
    does not exist. If it does exist, check that the installed plugin version is up to date
    with the pre-built plugin in the framework. This requires the framework itself to build
    the plugin bundle and ensure itself reflects the latest version.
    """

    import sgtk
    from sgtk.util.filesystem import ensure_folder_exists

    # Get the directory where the Alias plugin is installed. This directory must exist before
    # attempting to install the plugin
    alias_plugin_dir = environment_utils.get_alias_plugin_dir()
    logger.debug(f"Alias plugin directory: {alias_plugin_dir}")
    if not os.path.exists(alias_plugin_dir):
        logger.debug(f"Alias plugin directory does not exist - creating it.")
        ensure_folder_exists(alias_plugin_dir)

    # Get the path to the pre-built plugin from the framework
    plugin_name = environment_utils.TOOLKIT_PLUGIN_NAME
    bundled_plugin_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "dist",
            "Toolkit",
            "plugin",
            plugin_name,
        )
    )
    if not os.path.exists(bundled_plugin_path):
        raise sgtk.TankError(f"Could not find bundled plugin: {bundled_plugin_path}")

    # Ensure that the plugin is installed in the specified directory
    installed_plugin_dir = environment_utils.get_plugin_install_dir()
    if not os.path.exists(installed_plugin_dir):
        logger.debug(f"Installing Alias plugin: {installed_plugin_dir}")
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    # ---- already installed, check for update

    version_file = f"{plugin_name}.version"

    # Get the version from the installed plugin's build_version.txt file
    installed_version_file_path = os.path.join(installed_plugin_dir, version_file)
    if not os.path.exists(installed_version_file_path):
        logger.debug(
            f"Could not find installed version file {installed_version_file_path}. Reinstalling"
        )
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    # ---- found installation, get plugin versions

    # Get the version of the bundled plugin from the framework
    bundled_version_file_path = os.path.abspath(
        os.path.join(bundled_plugin_path, version_file)
    )
    if not os.path.exists(bundled_version_file_path):
        raise sgtk.TankError(
            f"Could not find bundled version file: {bundled_version_file_path}"
        )

    # Get the bundled version from the version file
    with open(bundled_version_file_path, "r") as bundled_version_file:
        bundled_version = bundled_version_file.read().strip()
    logger.debug(f"Bundled plugin version: {bundled_version}")

    # Get the installed version from the installed version info file
    logger.debug(f"The installed version file path: {installed_version_file_path}")
    installed_version = None
    with open(installed_version_file_path, "r") as installed_version_file:
        logger.debug("Extracting the version from the installed plugin")
        installed_version = installed_version_file.read().strip()

    if installed_version is None:
        logger.debug(
            "Could not determine version of the installed plugin. Reinstalling"
        )
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    logger.debug(f"Installed plugin version: {installed_version}")

    # ---- comparing plugin versions

    from sgtk.util.version import is_version_older

    if bundled_version != "dev" and installed_version != "dev":
        if bundled_version == installed_version or is_version_older(
            bundled_version, installed_version
        ):
            # The bundled version is the same or older. or it is a 'dev' build
            # which means always install that one.
            logger.debug("Installed plugin is up to date with the bundled build.")
            return

    # ---- plugin in framework is newer, update the installation

    if bundled_version == "dev":
        logger.debug("Installing the bundled 'dev' version of the plugin.")
    else:
        logger.debug("Bundled plugin is newer than the installed plugin. Updating...")

    __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)


def __install_plugin(plugin_path, install_dir, logger):
    """
    Install the plugin.

    Steps to install:
        1. First, back up the existing installation before removing it, if it exists.
        2. Ensure the bundled plugin to install exists.
        3. Copy the bundled plugin to the installation directory.
        4. If the install fails at any point, restore the back up, if created.

    :param plugin_path: The path to the framework pre-built plugin bundle.
    :type plugin_path: str
    :param install_dir: The plugin installation directory.
    :type install_dir: str
    """

    import sgtk
    from sgtk.util.filesystem import (
        backup_folder,
        copy_folder,
        move_folder,
    )

    # Move the installed plugin bundle to the backup directory
    if os.path.exists(install_dir):
        backup_plugin_dir = tempfile.mkdtemp()
        logger.debug(f"Backing up installed plugin to: {backup_plugin_dir}")
        try:
            backup_folder(install_dir, backup_plugin_dir)
        except Exception:
            shutil.rmtree(backup_plugin_dir)
            raise sgtk.TankError("Unable to create backup during plugin update.")

        # Now remove the installed plugin
        logger.debug("Removing the installed plugin bundle...")
        try:
            shutil.rmtree(install_dir)
        except Exception:
            # Error occured during install - try to restore the backup
            move_folder(backup_plugin_dir, install_dir)
            raise sgtk.TankError("Unable to remove the old plugin during update.")

    logger.debug(f"Installing bundled plugin: {plugin_path} to {install_dir}")

    # Ensure the bundled plugin exists
    if not os.path.exists(plugin_path):
        # Error occured during install - try to restore the backup
        move_folder(backup_plugin_dir, install_dir)
        raise sgtk.TankError(f"Expected plugin bundle does not exist: {plugin_path}")

    # Install the plugin bundle by copying the pre-built plugin to the installation directory
    copy_folder(plugin_path, install_dir)

    # Install was successful, remove the backup
    try:
        logger.debug("Install success. Removing the backed up plugin bundle.")
        shutil.rmtree(backup_plugin_dir)
    except Exception:
        pass


def ensure_toolkit_plugin_up_to_date(logger):
    """
    Ensure that the Alias plugin is installed and up to date.

    The basic.alias plugin needs to be installed in order to launch the Alias engine. The
    framework will provide a pre-built plugin bundle in the repo plugin/build folder. This
    plugin bundle will be installed for the user at runtime by copying the bundle from the
    framework to the users's Alias AppData folder. The framework will pre-build the plugin
    using the build_extension.py script from the repo dev folder.

    :param logger: Set a logger object to capture output from this operation.
    :type logger: Logger
    """

    import sgtk

    if "SHOTGRID_ALIAS_DISABLE_AUTO_INSTALL" in os.environ:
        # Skip plugin installation altogether
        return

    logger.debug("Ensuring Alias plugin is up-to-date...")
    try:
        __ensure_toolkit_plugin_up_to_date(logger)
    except Exception:
        exc = traceback.format_exc()
        raise sgtk.TankError(
            "There was a problem ensuring the Alias integration plugin "
            "was up-to-date with your toolkit engine. If this is a "
            "recurring issue please contact us via %s. "
            "The specific error message encountered was:\n'%s'."
            % (
                sgtk.support_url,
                exc,
            )
        )


def get_plugin_lst(alias_version, python_major_version, python_minor_version, logger):
    """
    Create the .lst file used to launch the alias_py plugin on Alias start up.

    The .lst file can be used, for example:

        Alias.exe -a as -P "path\\to\\plugin.lst"

    The .lst file will be created in a temp directory.

    Default to getting the plugin for Python 3.7 since Alias is currently on Qt 5.15.0,
    which only supports Python < 3.9. Until the PySide2 is no longer required to invoke
    functions in the main thread, the Python must include PySide2 version that matches
    the version used by Alias.

    :param alias_version: The Alias version string to run the plugin with.
    :type alias_version: str
    :param python_major_version: Option to specify the python major version to install the
        plugin for. Defaults to use the python version defined by sys.version_info.
    :type python_major_version: int
    :param python_minor_version: Option to specify the python minor version to install the
        plugin for. Defaults to use the python version defined by sys.version_info.
    :type python_minor_version: int

    :return: The file path to the .lst file.
    :rtype: str
    """

    if python_major_version is None:
        python_major_version = sys.version_info.major
    if python_minor_version is None:
        python_minor_version = sys.version_info.minor

    # Get the path to the .plugin file
    plugin_file_path = get_plugin_file_path(
        alias_version, python_major_version, python_minor_version
    )
    if alias_version not in plugin_file_path:
        logger.warning(
            f"Did not find Alias plugin for version {alias_version}. Falling back to plugin {plugin_file_path}"
        )
    else:
        logger.debug(f"Successfully found Alias plugin {plugin_file_path}")

    # Create or overwrite the lst file with the plugin file path found
    lst_file = os.path.join(tempfile.gettempdir(), "alias_plugins.lst")
    with open(lst_file, "w") as fp:
        fp.write("{}\n".format(plugin_file_path))

    return lst_file


def ensure_python_c_extension_packages_installed(python_version=None, logger=None):
    """
    Ensure python C extension packages are unzipped and installed for user.

    This routine will ensure C extensions are installed for the given python version, or for
    all supported Ptyhon versions

    :param logger: Set a logger object to capture output from this operation.
    :type logger: Logger

    :return: True if the packages have beene installed, else False.
    :rtype: bool
    """

    if logger is None:
        logger = logging.getLogger(__file__)
        logger.setLevel(logging.DEBUG)

    python_versions = environment_utils.get_framework_supported_python_versions()
    if python_version:
        if python_version not in python_versions:
            # The requested version is not supported
            return False
        python_versions = [python_version]

    for major_version, minor_version in python_versions:
        framework_c_ext_zip = environment_utils.get_python_dist_c_ext_zip(
            major_version, minor_version
        )
        if not os.path.exists(framework_c_ext_zip):
            logger.debug(f"No C extensions found to install {framework_c_ext_zip}")
            continue

        python_packages_path = environment_utils.get_python_packages_dir(
            major_version, minor_version
        )
        if not os.path.exists(python_packages_path):
            logger.debug(f"Creating Python packages directory {python_packages_path}")
            os.makedirs(python_packages_path)

        install_c_ext_path = environment_utils.get_python_c_ext_dir(
            major_version, minor_version
        )
        install_c_ext_zip_path = f"{install_c_ext_path}.zip"
        if os.path.exists(install_c_ext_zip_path):
            if verify_file(framework_c_ext_zip, install_c_ext_zip_path):
                logger.debug(
                    "C extensions already up to date at {install_c_ext_zip_path}."
                )
                continue  # Packages already exist and no change.

        if os.path.exists(install_c_ext_path):
            shutil.rmtree(install_c_ext_path)

        # Copy the zip folder. This will be used to check if updates are needed based on file
        # modifiation timestamp
        logger.debug(f"Coying C extension zip package to {install_c_ext_zip_path}")
        shutil.copyfile(framework_c_ext_zip, install_c_ext_zip_path)
        # Now extract the files
        logger.debug("Unzipping C extension packages...")
        with zipfile.ZipFile(install_c_ext_zip_path, "r") as zip_ref:
            zip_ref.extractall(install_c_ext_path)

    return True


def __ensure_python_packages_up_to_date(
    python_exe, major_version, minor_version, logger
):
    """Ensure python packages are up to date."""

    python_dist_dir = environment_utils.get_python_dist_dir(
        major_version, minor_version
    )
    lib_dir = os.path.join(os.path.dirname(python_exe), "Lib")
    dist_dir = os.path.join(lib_dir, "site-packages")
    if not os.path.exists(dist_dir):
        os.mkdir(dist_dir)
    logger.debug(f"Ensuring python packages up to date in {dist_dir}...")

    # Pip install everything and capture everything that was installed.
    requirements_txt = os.path.join(python_dist_dir, "requirements.txt")
    frozen_requirements_txt = os.path.join(lib_dir, "frozen_requirements.txt")
    logger.debug(f"Run pip install requirements from {requirements_txt}")
    subprocess.run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_txt,
            "--no-compile",
            "--target",
            dist_dir,
            # "--upgrade",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    logger.debug(f"Run pip freeze requirements to {frozen_requirements_txt}")
    subprocess.run(
        [python_exe, "-m", "pip", "freeze", "--path", dist_dir],
        stdout=open(frozen_requirements_txt, "w"),
        check=True,
    )


def ensure_python_installed(
    major_version, minor_version, logger, install_python_packages=False
):
    """Ensure that the Python version is installed."""

    from sgtk.util.filesystem import ensure_folder_exists

    logger.debug(f"Ensuring Python {major_version}.{minor_version} installed...")

    # Check if python is installed and up to date
    python_install = environment_utils.get_python_install_exe(
        major_version, minor_version
    )
    python_dir = environment_utils.get_python_dir(major_version, minor_version)
    python_install_dir = environment_utils.get_python_install_dir(
        major_version, minor_version
    )
    python_dist_dir = environment_utils.get_python_dist_install_dir(
        major_version, minor_version
    )
    version_txt = os.path.join(python_dist_dir, "embed_version.txt")
    installed_version_txt = os.path.join(python_dir, "embed_version.txt")
    pth_filename = f"python{major_version}{minor_version}._pth"
    pth_filepath = os.path.join(python_install_dir, pth_filename)

    if not os.path.exists(pth_filepath):
        update = True
    else:
        if not os.path.exists(version_txt):
            logger.error(
                "Missing version file in distribution to check if python up to date."
            )
            update = True
        else:
            if not os.path.exists(installed_version_txt):
                logger.error(
                    "Missing version file in installation to check if python up to date."
                )
                update = True
            else:
                current_version = None
                with open(version_txt, "r") as dist_fp:
                    current_version = dist_fp.read().strip()

                installed_version = None
                with open(installed_version_txt, "r") as installed_fp:
                    installed_version = installed_fp.read().strip()

                if (
                    current_version is None
                    or installed_version is None
                    or current_version != installed_version
                ):
                    update = True
                else:
                    # Versions were found and are matching. No update required.
                    update = False

    embed_package_name = environment_utils.get_python_embed_package_name(
        major_version, minor_version
    )
    if update:
        logger.error("Python not installed or out of date - installing")

        if os.path.exists(python_install_dir):
            shutil.rmtree(python_install_dir)
        ensure_folder_exists(python_install_dir)

        embeddable_package_zip = os.path.join(
            python_dist_dir, f"{embed_package_name}.zip"
        )
        if not os.path.exists(embeddable_package_zip):
            raise Exception(
                f"Requires Python {major_version}.{minor_version}. Cannot find embeddable package to install {embeddable_package_zip}."
            )

        # Install the embeddable package to user app data folder.
        logger.debug(
            f"Installing required Python {major_version}.{minor_version} to {python_install_dir}"
        )
        with zipfile.ZipFile(embeddable_package_zip, "r") as zip_ref:
            zip_ref.extractall(python_install_dir)

        # Install additional packages
        if install_python_packages:
            __ensure_python_packages_up_to_date(
                python_install, major_version, minor_version, logger
            )

        # Copy the version file to the installation.
        shutil.copyfile(version_txt, installed_version_txt)

    # Ensure the framework python path is added to the ._pth file
    original_pth_filepath = os.path.join(python_install_dir, f"{pth_filename}.original")
    if os.path.exists(original_pth_filepath):
        logger.debug(f"Re-creating _pth file {pth_filepath}")
        if os.path.exists(pth_filepath):
            # The original ._pth has already been modified. Remove the modified _pth first.
            os.remove(pth_filepath)
        # Re-create the _pth file to modify
        shutil.copyfile(original_pth_filepath, pth_filepath)
    else:
        # The _pth file has not been modified yet. Make a back up of it before modifying.
        logger.debug(f"Creating _pth backup file {original_pth_filepath}")
        shutil.copyfile(pth_filepath, original_pth_filepath)

    logger.debug(f"Updating {pth_filepath}...")
    framework_python_path = environment_utils.get_framework_python_path()
    logger.debug(f"Adding framework python path {framework_python_path}")
    with open(pth_filepath, "a") as fp:
        # Ensure new line first
        fp.write("\n")
        fp.write(framework_python_path)

    logger.debug(f"Using python {python_install}")
    return python_install


def ensure_plugin_ready(
    alias_version,
    alias_exec_path,
    client_name,
    pipeline_config_id=None,
    entity_type=None,
    entity_id=None,
    debug=None,
    logger=None,
):
    """
    Do the necessary work to ensure the Alias plugin can be loaded with Alias at launch.

    Starting in Alias 2024.0, Qt is now used for Alias UI. This conflicts with Flow Production Tracking Qt
    because Alias is a QtQuick/QML application, while Flow Production Tracking is a QWidget application.
    QWidgets cannot be created within an application using QtQuick/QML, so Flow Production Tracking must
    run in a separate process than Alias. Thus, the Alias plugin for Alias 2024 and later
    differs quite a bit from Alias before 2024.0:

    For Alias < 2024.0:
        - Flow Production Tracking will run in the same process as Alias, which means the Qt application is
          shared between Alias and Flow Production Tracking. Alias does not use Qt, so effectively Flow Production Tracking
          owns it
        - Alias will be launched with the -P param to specify the Alias Plugin to load at
          start up with Alias
        - The Alias Plugin will embed Python and call the tk-alias `start_engine` method to
          start up Flow Production Tracking

    For Alias >= 2024.0:
        - Flow Production Tracking will run in a separate process than Alias; Alias will have its own Qt
          application (in QtQuick/QML) and Flow Production Tracking will have its own Qt application (in
          QWidgets)
        - Alias will be launched with the -P param to specify the Alias Plugin to load at
          startup with Alias
        - The Alias Plugin will embed Python to start a socketio server to handle communication
          between Alias and Flow Production Tracking, as well as use the Toolkit Manager to bootstrap the
          Flow Production Tracking Alias Engine
        - The Python version used when embedding in the Alias process must be have installed
          a PySide2 version that matches the Qt version that Alias is using (5.15.0). For this
          reason, the framework may need to install a specific Python version in order to have
          a matching PySide2 version (e.g. PySide2 5.15.0 requires < Python 3.9)

    :param alias_version: The Alias version that the plugin will run with.
    :type alias_version: str
    :param alias_exec_path: The file path to the Alias executable.
    :type alias_exec_path: str
    :param client_name: A name of the application that is launching Alias with the plugin.
    :type client_name: str
    :param pipeline_configuration_id: If the client is running within Flow Production Tracking, set the id of
        the pipeline configuration used by the Toolkit Manager to bootstrap the engine from the
        plugin.
    :type pipeline_config_id: int
    :param entity_type: If the client is running within Flow Production Tracking, set the entity type used by
        the Toolkit Manager to bootstrap the engine from the plugin.
    :type entity_type: str
    :param entity_id: If the client is running within Flow Production Tracking, set the entity id used by
        the Toolkit Manager to bootstrap the engine from the plugin.
    :type entity_id: int
    :param debug: Set to True to turn on debugging for the plugin, else False.
    :type debug: bool
    :param logger: Set a logger object to capture output from this operation.
    :type logger: Logger
    """

    debug = debug or "0"

    if logger is None:
        logger = logging.getLogger(__file__)
        logger.setLevel(logging.DEBUG)

    if version_cmp(alias_version, "2024.0") >= 0:
        # Alias >= 2024.0
        # Client will run in a new process, separate from Alias.
        new_process = True

        # Check the basic.alias Toolkit plugin is installed and up to date. This is used by
        # the Alias Plugin to bootstrap the Flow Production Tracking Alias Engine.
        ensure_toolkit_plugin_up_to_date(logger)

        # Alias 2024.0 is running with Qt 5.15.0, which means the PySide2 version used by the
        # version of Python that is embedded by the Alias Plugin must also be 5.15.0. Since
        # PySide2 5.15.0 requires Python < 3.9, we will force Python 3.7 to be used by the
        # Alias Plugin (which is done by setting the server python)
        py_major_version = 3
        py_minor_version = 7
        install_python_packages = os.environ.get(
            "SHOTGRID_ALIAS_INSTALL_PYTHON_PACKAGES"
        ) in ("1", "true", "True")
        server_python_exe = ensure_python_installed(
            py_major_version,
            py_minor_version,
            logger,
            install_python_packages=install_python_packages,
        )
    else:
        # Alias < 2024.0
        # Client will run in the same process as Alias.
        new_process = False

        # The Python version used by the Alias Plugin will be the current Python version,
        # though the framework will still need to ensure the necesary python packages are
        # insatlled
        py_major_version = sys.version_info.major
        py_minor_version = sys.version_info.minor
        # Do not set the server python, this is not used by Alias < 2024.0
        server_python_exe = None

    # Ensure C extension packages installed for user. Install for all supported Python
    # versions, just in case the python version the framework runs with is different that
    # the current running version.
    ensure_python_c_extension_packages_installed(logger=logger)

    # Get the file path to the .lst file that contains the file path to the Alias Plugin to
    # load at startup with Alias.
    plugin_lst_path = get_plugin_lst(
        alias_version,
        py_major_version,
        py_minor_version,
        logger,
    )
    if not plugin_lst_path:
        raise Exception("The plugin .lst file not found for Alias {alias_version}.")
    logger.debug(f"Alias Plugin List file path {plugin_lst_path}")

    # Get the dictionary of environment variables that are needed by the Alias Plugin
    plugin_env = get_plugin_environment(
        alias_version,
        alias_exec_path,
        client_name,
        pipeline_config_id=pipeline_config_id,
        entity_type=entity_type,
        entity_id=entity_id,
        debug=debug,
        server_python_exe=server_python_exe,
        new_process=new_process,
    )
    logger.debug(f"Alias Plugin environment\n{pprint.pformat(plugin_env)}")

    return (plugin_lst_path, plugin_env)
