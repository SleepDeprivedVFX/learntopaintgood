# Copyright (c) 2023 Autodesk.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk.

import os
import sgtk
import shutil
import subprocess
import tempfile

logger = sgtk.platform.get_logger(__name__)


class LMVTranslator:
    """A class to translate files to be consumed by the Flow Production Tracking 3D LMV Viewer."""

    def __init__(self, path, tk, context):
        """
        Class constructor.

        :param path: Path to the source file we want to perform operations on.
        """
        self.__source_path = path
        self.__tk = tk
        self.__context = context
        self.__output_directory = None
        self.__svf_path = None

    ################################################################################################
    # static methods

    def get_translators_by_file_type():
        """
        Return a mapping of file types to translator engine.

        The translator engine is the name of the engine that has the necessary tools to
        translate the file type.
        """

        return {
            ".wire": "tk-alias",
            ".CATPart": "tk-alias",
            ".jt": "tk-alias",
            ".igs": "tk-alias",
            ".stp": "tk-alias",
            ".fbx": "tk-alias",
            ".vpb": "tk-vred",
        }

    def get_translator_relative_paths():
        """
        Return a mapping of translator engine to the relative path of the translator executable.

        The path return is relative to the engine's software executable location.
        """

        return {
            "tk-alias": os.path.join("LMVExtractor", "atf_lmv_extractor.exe"),
            "tk-vred": os.path.join("LMV", "viewing-vpb-lmv.exe"),
        }

    def find_translator_path(tk, context, engine_name, translator_executable_path):
        """
        Find the translator executable path relative to the engine's software location.

        :param context: The Toolkit context used to create an engine launcher that can
            determine the engine software location.
        :type context: sgtk.Context
        :param engine_name: The name of the engine.
        :type engine_name: str
        :param extractor_path: The relative file path from the engine's software location, to
            the thumbnail extractor executable.
        :type extractor_path: str

        :return: The thumbnail extractor executable path relative to the engine's software
            location.
        :rtype: str
        """

        # Create the engine laucnher in order to discover the engine's software location
        launcher = sgtk.platform.create_engine_launcher(tk, context, engine_name)
        software_versions = launcher.scan_software()
        if not software_versions:
            return None

        # Iterate through the software versions starting from the latest version, and return
        # the first thumbnail extractor executable path found
        for software_version in reversed(software_versions):
            software_exe_path = software_version.path
            root_dir = os.path.dirname(software_exe_path)
            translator_path = os.path.join(root_dir, translator_executable_path)
            if os.path.exists(translator_path):
                return translator_path

        # No translator executable path found
        return None

    ################################################################################################
    # properties

    @property
    def source_path(self):
        """
        Path of the file used as source for all the translations.

        :returns: The file path as a string
        """
        return self.__source_path

    @property
    def output_directory(self):
        """
        Path to the directory where all the translated files will be stored.

        :returns: The directory path as a string
        """
        return self.__output_directory

    ################################################################################################
    # public methods

    def translate(self, output_directory=None):
        """
        Run the translation to convert the source file to a bunch of files needed by the 3D Viewer.

        :param output_directory: Path to the directory we want to translate the file to. If no path is supplied, a
                                temporary one will be used
        :param use_framework_translator: True will use the translator shipped with the framework, else
                                         False (default) will use a translator based on the type of file to
                                         translate and the current engine running.
        :returns: The path to the directory where all the translated files have been written.
        """

        self.__output_directory = output_directory

        translator_path = self.get_translator_path()
        logger.debug(
            "Using LMV Tanslator: {translator}".format(translator=translator_path)
        )

        if self.output_directory is None:
            # generate all the files and folders needed for the translation
            self.__output_directory = tempfile.mkdtemp(prefix="lmv_")
        output_path = os.path.join(
            self.output_directory, os.path.basename(self.source_path)
        )

        index_file_path = os.path.join(self.output_directory, "index.json")
        open(index_file_path, "w").close()

        # copy the source file to the temporary location and run the translation
        logger.debug("Copying source file to temporary folder")
        shutil.copyfile(self.source_path, output_path)

        logger.debug("Running translation process")
        cmd = [translator_path, index_file_path, output_path]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_output, _ = p.communicate()

        if p.returncode != 0:
            raise Exception(p_output)

        return self.output_directory

    def package(self, svf_file_name=None, thumbnail_path=None):
        """
        Package all the translated files into a zip file and extract the LMV thumbnail if needed

        :param svf_file_name: If supplied, rename the svf file according to the given name
        :param thumbnail_path: If supplied, use this thumbnail as LMV thumbnail. Otherwise, try to extract the thumbnail
                               from the source file
        :return: The path to the zip file and the path to the thumbnail shipped with the LMV file
        """

        if not self.output_directory or not os.path.isdir(self.output_directory):
            raise Exception(
                "Couldn't package the LMV files: no file seems to have been created"
            )

        output_dir_path = os.path.join(self.output_directory, "output")

        # rename the svf file if needed
        if svf_file_name:
            logger.debug("Renaming SVF file")
            source_path = self.__get_svf_path()
            target_path = os.path.join(
                output_dir_path, "1", "{}.svf".format(svf_file_name)
            )
            if os.path.isfile(target_path):
                raise Exception(
                    "Couldn't rename svf file: target path %s already exists"
                    % target_path
                )
            os.rename(source_path, target_path)
            self.__svf_path = target_path
        else:
            svf_file_name = os.path.splitext(os.path.basename(self.source_path)[0])

        if thumbnail_path:
            images_dir_path = os.path.join(output_dir_path, "images")
            if not os.path.exists(images_dir_path):
                os.makedirs(images_dir_path)
            package_thumbnail_path = os.path.join(
                images_dir_path, "{}.jpg".format(svf_file_name)
            )
            shutil.copyfile(thumbnail_path, package_thumbnail_path)
        else:
            package_thumbnail_path = None

        # zip the package
        logger.debug("Making archive from LMV files")
        zip_path = shutil.make_archive(
            base_name=os.path.join(self.output_directory, svf_file_name),
            format="zip",
            root_dir=output_dir_path,
        )

        return zip_path, package_thumbnail_path

    def get_translator_path(self):
        """
        Get the path to the translator we have to use according to the file extension

        :return: The path to the translator.
        :rtype: str
        """

        _, ext = os.path.splitext(self.source_path)
        current_engine = sgtk.platform.current_engine()

        translator_engine = LMVTranslator.get_translators_by_file_type().get(ext)
        if not translator_engine:
            raise Exception("LMV translation does not support file type: {ext}")

        translator_relative_path = LMVTranslator.get_translator_relative_paths().get(
            translator_engine
        )
        if not translator_relative_path:
            raise Exception(
                "Mising translator information for engine: {translator_engine}"
            )

        # First try a shortcut to get the translator executable path from the current engine
        if current_engine.name == translator_engine and hasattr(
            current_engine, "executable_path"
        ):
            root_dir = os.path.dirname(current_engine.executable_path)
            translator_path = os.path.join(root_dir, translator_relative_path)
            if os.path.exists(translator_path):
                return translator_path

        # Did not find translator from current engine. Check for local installations of
        # the engine's DCC to find the translator
        translator_path = LMVTranslator.find_translator_path(
            self.__tk,
            self.__context,
            translator_engine,
            translator_relative_path,
        )
        if not os.path.exists(translator_path):
            raise Exception("Couldn't find translator for Alias.")
        return translator_path

    ########################################################################################
    # private methods

    def __get_svf_path(self):
        """
        Get the SFV file path according to the output directory

        :return: The path to the SFV file
        """

        if not self.__svf_path:
            svf_file_name = "{}.svf".format(
                os.path.splitext(os.path.basename(self.source_path))[0]
            )
            svf_path = os.path.join(self.output_directory, "output", "1", svf_file_name)
            if not os.path.isfile(svf_path):
                raise Exception("Couldn't find svf file %s" % svf_path)
            self.__svf_path = svf_path

        return self.__svf_path
