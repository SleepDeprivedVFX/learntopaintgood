#!/usr/bin/env python

# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from __future__ import print_function
import sys

sys.dont_write_bytecode = True

import argparse
import os
import re
import shutil
import subprocess

# global placeholder for when we import sgtk
sgtk = None
logger = None

# bundle cache dir name within the built plugin
BUNDLE_CACHE_DIR = "bundle_cache"

# the build script located in the core repo
CORE_BUILD_SCRIPT = os.path.join("developer", "build_plugin.py")


def main():
    """Wraps all the steps to build the Alias plugin."""

    # parse and validate the command line args
    args = _validate_args(_parse_args())

    # first step is to build the plugin
    _build_plugin(args)

    # remove the bundle cache unless specified
    if not args["bundle_cache"]:
        _remove_bundle_cache(args)

    # add a version file to the built plugin
    _write_version_file(args)

    # do a final pass on the plugin directory before bundling it up
    _clean_plugin_dir(args)

    logger.info("Build successful.")


def _build_plugin(args):
    """
    First step is to build the plugin itself.

    Adds the plugin output dir to the args dict.
    """

    # construct the full plugin output directory
    plugin_build_dir = os.path.abspath(
        os.path.join(args["output_dir"], args["extension_name"])
    )

    command = [
        sys.executable,
        os.path.join(args["core"], CORE_BUILD_SCRIPT),
        args["plugin_dir"],
        plugin_build_dir,
    ]

    # execute the build script
    logger.info("Plugin build command: %s" % (command,))
    logger.info("Executing plugin build command...")
    status = subprocess.call(command)

    # check the return status
    if status:
        logger.error("Error building the plugin.")
        raise Exception("There was a problem building the plugin.")

    # add the full ext dir path to the args dict
    args["plugin_build_dir"] = plugin_build_dir
    logger.info("Built plugin: %s" % (args["plugin_build_dir"],))


def _clean_plugin_dir(args):
    """
    Ensure the plugin dir is in a clean state before bundling.

    NOTE: Once signed, nothing in the plugin directory can be modified, so
    do any and all work to ensure it is in it's ready state.
    """

    # remove all .pyc files recursively
    logger.info("Cleaning built plugin directory...")
    from sgtk.util.filesystem import safe_delete_file

    for (root, dir_names, file_names) in os.walk(args["plugin_build_dir"]):
        for file_name in file_names:
            if file_name.endswith(".pyc"):
                full_path = os.path.join(root, file_name)
                logger.info("Removing pyc file: %s" % (full_path,))
                safe_delete_file(full_path)


def _parse_args():
    """
    Define the parser and return the parsed args.
    """

    parser = argparse.ArgumentParser(
        description="Build and package an Alias plugin for the framework."
    )

    parser.add_argument(
        "--core",
        "-c",
        metavar="/path/to/tk-core",
        help="The path to tk-core to use when building the toolkit plugin.",
        required=True,
    )

    parser.add_argument(
        "--plugin_name",
        "-p",
        metavar="name",
        help="The name of the framework plugin to build. Ex: 'basic'.",
        required=True,
    )

    parser.add_argument(
        "--extension_name",
        "-e",
        metavar="name",
        help="The name of the output plugin bundle. Ex: 'com.sg.basic.alias'",
        required=True,
    )

    parser.add_argument(
        "--bundle_cache",
        "-b",
        action="store_true",
        help=(
            "If supplied, include the 'bundle_cache' directory in the build "
            "plugin. If not, it is removed after the build."
        ),
    )

    parser.add_argument(
        "--version",
        "-v",
        metavar="v#.#.#",
        help=(
            "The version to attached to the built plugin. If not specified, "
            "the version will be set to 'dev' and will override any version "
            "of the plugin at launch/install time. The current version "
            "can be found in the .version file that lives next to the "
            "existing plugin bundle."
        ),
    )

    parser.add_argument(
        "--output_dir",
        "-o",
        metavar="/path/to/output/plugin",
        help=(
            "If supplied, output the built plugin bundle here. If not supplied, "
            "the plugin will be built in the framework directory at the top "
            "level."
        ),
    )

    return parser.parse_args()


def _remove_bundle_cache(args):
    """Remove the built plugin bundle cache."""

    logger.info("Removing bundle cache from built plugin...")
    bundle_cache_dir = os.path.join(args["plugin_build_dir"], BUNDLE_CACHE_DIR)
    try:
        shutil.rmtree(bundle_cache_dir)
    except Exception:
        logger.warning("Failed to remove bundle cache from plugin bundle.")


def _validate_args(args):
    """
    Validate the parsed args. Will raise if there are errors.

    Sets up the logger if core can be imported.

    Adds some additional values based on supplied args including the framework
    directory, plugin path, etc.

    Returns a dictionary of the parsed arguments of the following form:

        {
            'core': '/path/to/tk-core',
            'extension_name': 'extesion.name.here',
            'bundle_cache': True,
            'plugin_name': 'plugin_name',
            'version': 'v1.0.0',
            'output_dir': '/path/to/output/dir',
            'framework_dir': '/path/to/the/framework/repo',
            'plugin_dir': '/path/to/the/framework/plugin',
        }
    """

    # convert the args namespace to a dict
    args = vars(args)

    if args["core"]:
        args["core"] = os.path.expanduser(args["core"])
    if args["output_dir"]:
        args["output_dir"] = os.path.expanduser(args["output_dir"])

    # ensure core path exists and build script is there
    if not os.path.exists(args["core"]):
        raise Exception("Supplied core path does not exist: %s" % (args["core"],))

    # make sure we can import core
    try:
        sgtk_dir = os.path.join(args["core"], "python")
        sys.path.insert(0, sgtk_dir)  # make sure this one is found first
        import sgtk as imported_sgtk

        global sgtk
        sgtk = imported_sgtk
    except Exception as e:
        raise Exception("Error import supplied core: %s" % (e,))

    # setup the logger for use from here on out
    try:
        # set up std toolkit logging to file
        sgtk.LogManager().initialize_base_file_handler(
            "tk-framework-alias_build_plugin"
        )

        # set up output of all sgtk log messages to stdout
        sgtk.LogManager().initialize_custom_handler()

        global logger
        logger = sgtk.LogManager.get_logger("build_plugin")

    except Exception as e:
        raise Exception("Error creating toolkit logger: %s" % (e,))

    logger.info("Validating command line arguments...")

    # ensure the core plugin build script exists
    logger.info("Finding plugin build script...")
    build_script = os.path.join(args["core"], CORE_BUILD_SCRIPT)
    if not os.path.exists(build_script):
        raise Exception(
            "Could not find plugin build script in supplied core: %s" % (build_script,)
        )

    # ensure the plugin name is valid
    logger.info("Ensuring valid plugin build names...")
    from sgtk.util.filesystem import create_valid_filename

    args["extension_name"] = create_valid_filename(args["extension_name"])
    logger.info("Extension name: %s" % (args["extension_name"]))

    # make sure version is valid
    logger.info("Verifying supplied version...")
    if args["version"]:
        if not re.match(r"^v\d+\.\d+\.\d+$", args["version"]):
            raise Exception(
                "Supplied version doesn't match the format 'v#.#.#'. Supplied: %s"
                % (args["version"],)
            )
    else:
        args["version"] = "dev"

    # get the full path to the framework repo
    logger.info("Populating the framework directory...")
    args["framework_dir"] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)
    )

    # ensure the plugin can be found in the framework
    logger.info("Validating plugin name...")
    # plugin_dir = os.path.join(args["framework_dir"], "plugin", "basic")
    plugin_dir = os.path.join(args["framework_dir"], "plugin", "Toolkit", "basic")
    if not os.path.exists(plugin_dir):
        raise Exception(
            "Could not find plugin '%s' in framework." % (args["plugin_name"],)
        )
    args["plugin_dir"] = plugin_dir

    # if output dir defined, ensure it exists. populate args with framework dir
    # if not.
    logger.info("Determining output directory...")
    if args["output_dir"]:
        if not os.path.exists(args["output_dir"]):
            from sgtk.util.filesystem import ensure_folder_exists

            ensure_folder_exists(args["output_dir"])
    else:
        args["output_dir"] = args["framework_dir"]

    # return the validate args
    logger.info("Command line arguments validated.")
    return args


def _write_version_file(args):
    """
    Write a file to the built plugin directory containing the specified version.

    Also write the file to the top-level of the framework repo to make it possible
    to easily compare during install.
    """

    # the file to create with the specified version
    bundle_version_file_path = os.path.join(
        args["plugin_build_dir"], "%s.%s" % (args["extension_name"], "version")
    )

    # write the file
    logger.info("Writing build version info file...")
    with open(bundle_version_file_path, "w") as bundle_version_file:
        bundle_version_file.write(args["version"])


if __name__ == "__main__":

    exit_code = 1
    try:
        exit_code = main()
    except Exception as e:
        print("ERROR: %s" % (e,))
    else:
        logger.info("Plugin successfully built!")

    sys.exit(exit_code)
