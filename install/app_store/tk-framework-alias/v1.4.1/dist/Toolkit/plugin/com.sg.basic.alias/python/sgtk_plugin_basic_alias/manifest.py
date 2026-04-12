# this file was auto generated.


base_configuration = "sgtk:descriptor:app_store?name=tk-config-basic"
plugin_id = "basic.alias"


# system generated parameters
BUILD_DATE = "20230525_161934"
BUILD_GENERATION = 2


def get_sgtk_pythonpath(plugin_root):
    """
    Auto generated helper method which returns the
    path to the core bundled with the plugin.

    For more information, see the documentation.
    """
    import os

    return os.path.join(
        plugin_root, "bundle_cache", "app_store", "tk-core", "v0.20.16", "python"
    )


def initialize_manager(manager, plugin_root):
    """
    Auto generated helper method which initializes
    a toolkit manager with common plugin parameters.

    For more information, see the documentation.
    """
    import os

    manager.base_configuration = "sgtk:descriptor:app_store?name=tk-config-basic"
    manager.plugin_id = "basic.alias"
    bundle_cache_path = os.path.join(plugin_root, "bundle_cache")
    manager.bundle_cache_fallback_paths = [bundle_cache_path]
    return manager


# end of file.
