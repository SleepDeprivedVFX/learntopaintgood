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
import shutil

HookBaseClass = sgtk.get_hook_baseclass()


class UploadVersionPlugin(HookBaseClass):
    """
    Plugin for sending quicktimes and images to Flow Production Tracking for review.
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        if hasattr(self, "plugin_icon"):
            return self.plugin_icon

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(self.disk_location, "icons", "review.png")

    @property
    def description(self):
        """Return the description for the plugin."""
        return "Translate file to LMV and upload to Flow Production Tracking."

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        # inherit the settings from the base publish plugin
        base_settings = super(UploadVersionPlugin, self).settings or {}

        # settings specific to this class
        upload_version_settings = {
            "3D Version": {
                "type": "bool",
                "default": True,
                "description": "Generate a 3D Version instead of a 2D one?",
            },
            "Upload": {
                "type": "bool",
                "default": False,
                "description": "Upload content to Flow Production Tracking?",
            },
        }

        # update the base settings
        base_settings.update(upload_version_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return [
            "file.alias",
            "file.vred",
            "file.catpart",
            "file.igs",
            "file.jt",
            "file.stp",
            "file.motionbuilder",
        ]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        if settings.get("3D Version").value is True:
            self.plugin_icon = os.path.join(self.disk_location, "icons", "3d_model.png")

        return {"accepted": True, "checked": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        path = item.get_property("path")
        if not path:
            self.logger.error("No path found for item")
            return False

        framework_lmv = self.load_framework("tk-framework-lmv_v0.x.x")
        if not framework_lmv:
            self.logger.error("Could not run LMV translation: missing ATF framework")
            return False

        translator = framework_lmv.import_module("translator")
        lmv_translator = translator.LMVTranslator(path, self.parent.sgtk, item.context)
        lmv_translator_path = lmv_translator.get_translator_path()
        if not lmv_translator_path:
            self.logger.error(
                "Missing translator for VRED. VRED must be installed locally to run LMV translation."
            )
            return False

        # Store the translator in the item properties so it can be used later
        item.properties["lmv_translator"] = lmv_translator

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # create the Version in Flow Production Tracking
        super(UploadVersionPlugin, self).publish(settings, item)

        # generate the Version content: LMV file or simple 2D thumbnail
        if settings.get("3D Version").value is True:
            self.logger.debug("Creating LMV files from source file")
            # translate the file to lmv and upload the corresponding package to the Version
            (
                package_path,
                output_directory,
            ) = self._translate_file_to_lmv(item)
            self.logger.debug("Uploading LMV file to Flow Production Tracking")
            self.parent.shotgun.update(
                entity_type="Version",
                entity_id=item.properties["sg_version_data"]["id"],
                data={"sg_translation_type": "LMV"},
            )
            self.parent.shotgun.upload(
                entity_type="Version",
                entity_id=item.properties["sg_version_data"]["id"],
                path=package_path,
                field_name="sg_uploaded_movie",
            )
            # delete the temporary folder on disk
            self.logger.debug("Deleting temporary folder")
            shutil.rmtree(output_directory)

        thumbnail_path = item.get_thumbnail_as_path()
        if thumbnail_path:
            self.parent.shotgun.upload_thumbnail(
                entity_type="Version",
                entity_id=item.properties["sg_version_data"]["id"],
                path=thumbnail_path,
            )

    def _translate_file_to_lmv(self, item):
        """
        Translate the current Alias file as an LMV package in order to upload it to Flow Production Tracking as a 3D Version

        :param item: Item to process
        :returns:
            - The path to the LMV zip file
            - The path to the LMV thumbnail
            - The path to the temporary folder where the LMV files have been processed
        """

        lmv_translator = item.properties["lmv_translator"]
        lmv_translator.translate()

        # package it up
        self.logger.info("Packaging LMV files")
        package_path, _ = lmv_translator.package(
            svf_file_name=str(item.properties["sg_version_data"]["id"]),
        )

        return package_path, lmv_translator.output_directory
