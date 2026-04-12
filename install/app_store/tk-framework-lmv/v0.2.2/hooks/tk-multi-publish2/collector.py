# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.

    This collector hook is used to collect individual files that are browsed or
    dragged and dropped into the Publish2 UI. It can also be subclassed by other
    collectors responsible for creating items for a file to be published such as
    the current Maya session file.

    This plugin centralizes the logic for collecting a file, including
    determining how to display the file for publishing (based on the file
    extension).

    In addition to creating an item to publish, this hook will set the following
    properties on the item::

        path - The path to the file to publish. This could be a path
            representing a sequence of files (including a frame specifier).

        sequence_paths - If the item represents a collection of files, the
            plugin will populate this property with a list of files matching
            "path".

    """

    @property
    def common_file_info(self):
        """
        A dictionary of file type info that allows the basic collector to
        identify common production file types and associate them with a display
        name, item type, and config icon.

        The dictionary returned is of the form::

            {
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                ...
            }

        See the collector source to see the default values returned.

        Subclasses can override this property, get the default values via
        ``super``, then update the dictionary as necessary by
        adding/removing/modifying values.
        """

        # inherit the settings from the base publish plugin
        base_file_info = super(BasicSceneCollector, self).common_file_info or {}

        automotive_file_info = {
            "Wref File": {
                "extensions": ["wref"],
                "icon": self._get_icon_path("alias.png"),
                "item_type": "file.wref",
            },
            "Catpart File": {
                "extensions": ["CATPart"],
                "icon": self._get_icon_path("catia.png"),
                "item_type": "file.catpart",
            },
            "Jt File": {
                "extensions": ["jt"],
                "icon": self._get_icon_path("jt.png"),
                "item_type": "file.jt",
            },
            "Stp File": {
                "extensions": ["stp", "step"],
                "icon": self._get_icon_path("stp.png"),
                "item_type": "file.stp",
            },
            "Igs File": {
                "extensions": ["igs", "iges"],
                "icon": self._get_icon_path("igs.png"),
                "item_type": "file.stp",
            },
        }
        # update the base settings
        base_file_info.update(automotive_file_info)

        return base_file_info

    def _get_icon_path(self, icon_name):
        """
        Helper to get the full path to an icon.

        By default, the app's ``hooks/icons`` folder will be searched.
        Additional search paths can be provided via the ``icons_folders`` arg.

        :param icon_name: The file name of the icon. ex: "alembic.png"
        :param icons_folders: A list of icons folders to find the supplied icon
            name.

        :returns: The full path to the icon of the supplied name, or a default
            icon if the name could not be found.
        """

        found_icon_path = None

        icon_path = os.path.join(self.disk_location, "icons", icon_name)
        if os.path.exists(icon_path):
            found_icon_path = icon_path

        # supplied file name doesn't exist. return the default file.png image
        if not found_icon_path:
            found_icon_path = super(BasicSceneCollector, self)._get_icon_path(icon_name)

        return found_icon_path
