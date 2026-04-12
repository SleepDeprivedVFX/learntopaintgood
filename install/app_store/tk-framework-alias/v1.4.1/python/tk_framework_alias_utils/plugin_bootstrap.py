# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys


def toolkit_plugin_bootstrap(
    pipeline_config_id, entity_type, entity_id, hostname, port, namespace
):
    """
    Business logic for bootstrapping toolkit as a plugin.

    :param plugin_root_path: Path to the root of the plugin
    """

    from environment_utils import get_plugin_install_dir
    import log

    # Set env var for ToolkitManager
    os.environ["SHOTGUN_ENTITY_TYPE"] = entity_type
    os.environ["SHOTGUN_ENTITY_ID"] = entity_id
    # Set env var for AliasEngine (tk-alias)
    os.environ["SHOTGRID_ALIAS_HOST"] = hostname
    os.environ["SHOTGRID_ALIAS_PORT"] = port
    os.environ["SHOTGRID_ALIAS_NAMESPACE"] = namespace
    # Indicate we want the Alias Engine to run in GUI mode
    os.environ["TK_ALIAS_HAS_UI"] = "1"
    os.environ["TK_ALIAS_OPEN_MODEL"] = "0"

    # Note: the sgtk_plugin_basic_alias module is created as part of the plugin build process.
    plugin_root_path = get_plugin_install_dir()
    sys.path.insert(0, os.path.join(plugin_root_path, "python"))
    from sgtk_plugin_basic_alias import manifest

    tk_core_python_path = manifest.get_sgtk_pythonpath(plugin_root_path)
    sys.path.insert(0, tk_core_python_path)
    import sgtk

    logger = sgtk.LogManager.get_logger(__name__)
    logger.debug("Imported sgtk core from '%s'" % tk_core_python_path)

    # ---- setup logging
    log_handler = log.get_sgtk_logger(sgtk)
    logger.debug("Added bootstrap log hander to root logger...")

    # TODO  For standalone workflows, need to handle authentication here
    #       this includes workflows for logging in and out (see maya plugin).
    #       For now, assume that we are correctly authenticated.
    #       Also, need to check that the SHOTGUN_SITE env var matches
    #       the currently logged in site.

    # ---- set up the toolkit bootstrap manager
    toolkit_mgr = sgtk.bootstrap.ToolkitManager()
    # run the default init which sets plugin id, base config and bundle cache path
    logger.debug("Initializing Toolkit Manager: %s" % toolkit_mgr)
    manifest.initialize_manager(toolkit_mgr, plugin_root_path)

    # Set the pipeline configuration id to use, if given
    if pipeline_config_id:
        toolkit_mgr.pipeline_configuration = int(pipeline_config_id)

    entity = toolkit_mgr.get_entity_from_environment()
    logger.debug("Will launch the engine with entity: %s" % entity)

    logger.info("Bootstrapping toolkit...")
    try:
        toolkit_mgr.bootstrap_engine("tk-alias", entity=entity)
    except Exception as e:
        logger.exception("Error bootstrapping toolkit: %s" % e)
        return -1

    # ---- tear down logging
    sgtk.LogManager().root_logger.removeHandler(log_handler)
    logger.debug("Removed bootstrap log handler from root logger...")

    logger.info("Toolkit Bootstrapped!")

    # core may have been swapped. import sgtk
    import sgtk

    # get a handle on the newly bootstrapped engine
    engine = sgtk.platform.current_engine()

    # After engine bootstrapped, import qt (engine will set up the qt module)
    from sgtk.platform.qt import QtGui
    from sgtk.platform.engine_logging import ToolkitEngineHandler

    # Create the Qt app
    app_name = "Flow Production Tracking for Alias"
    app = QtGui.QApplication([app_name])
    app.setApplicationName(app_name)
    app.setQuitOnLastWindowClosed(False)
    QtGui.QApplication.instance().aboutToQuit.connect(
        lambda: QtGui.QApplication.processEvents()
    )

    # Finish the engine initialization that requries the Qt app instance to be created, but before
    # the event loop starts.
    engine.post_qt_init()

    # Log message to Alias prompt indicating that Flow Production Tracking is ready
    engine.alias_py.log_to_prompt("Flow Production Tracking initialized")

    # This will block and not return until Flow Production Tracking app exits.
    ret = app.exec_()
    logger.info("ShotGrid QApplication exited with return code: %s" % ret)

    # Clean up Flow Production Tracking components
    root_logger = sgtk.LogManager().root_logger
    handlers = list(root_logger.handlers)
    while handlers:
        handler = handlers.pop()
        if isinstance(handler, ToolkitEngineHandler):
            root_logger.removeHandler(handler)

    # Get the engine again before clean up, our reference may be stale.
    engine = sgtk.platform.current_engine()
    if engine:
        logger.info("Destroying Toolkit...")
        engine.destroy()

    logger.info("Plugin bootstrap exiting")
    return ret


if __name__ == "__main__":
    """
    Bootstrap the Flow Production Tracking Alias Engine application.

    This script calls the `bootstrap_engine` method with the script args to do the work.

    The exepcted arguments are:
        1. this script name
        2. host name of a running socketio server
        3. port of the running socketio server
        4. namespace of the running socketio server.
        5. the pipeline config id to bootstrap with

    Before this script is called, it is expected that a socketio server is running on the
    given host, port and the namespace is a valid namespace for the server.

    It is designed, but not limited, to be called from the AliasPy plugin (found in
    tk-framework-alias). The AliasPy plugin will start a socketio server running on the given
    host and port, and has the given namespace. The path to this script is given to the plugin
    via the enviroment variable `ALIAS_PLUGIN_CLIENT_EXECPATH`, which allows the plugin to
    execute this script in a new process, giving the server info for this script to use to
    connect to the running server.
    """

    args = sys.argv[1:]
    ret = toolkit_plugin_bootstrap(*args)
    sys.exit(ret)
