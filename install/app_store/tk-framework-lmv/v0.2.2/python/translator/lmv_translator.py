# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import base64
import os
import sgtk
import shutil
import subprocess
import tempfile

logger = sgtk.platform.get_logger(__name__)


class LMVTranslator(object):
    """
    A LMVTranslator instance is used to translate a source file to something readable by ShotGrid 3D Viewer.
    It also offers the possibility to extract a thumbnail from this source file.
    """

    # file extensions that can be used by Alias tools to extract data
    ALIAS_VALID_EXTENSION = [".wire", ".CATPart", ".jt", ".igs", ".stp", ".fbx"]

    # file extensions that can be used by VRED tools to extract data
    VRED_VALID_EXTENSION = [".vpb"]

    def __init__(self, path):
        """
        Class constructor.

        :param path: Path to the source file we want to perform operations on.
        """
        self.__source_path = path
        self.__output_directory = None
        self.__svf_path = None

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

    def translate(self, output_directory=None, use_framework_translator=False):
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

        # get the translator path
        translator_path = self.__get_translator_path(use_framework_translator)
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

        # extract the thumbnails
        thumbnail_path = self.extract_thumbnail(thumbnail_path)

        # zip the package
        logger.debug("Making archive from LMV files")
        zip_path = shutil.make_archive(
            base_name=os.path.join(self.output_directory, svf_file_name),
            format="zip",
            root_dir=output_dir_path,
        )

        return zip_path, thumbnail_path

    def extract_thumbnail(self, thumbnail_source_path=None):
        """
        Extract the thumbnail from the source file

        :param thumbnail_source_path: Optional path to the thumbnail we want to use as source image. If no path is
                                      supplied by the user, try to extract the image from the source file
        :return: The path to the LMV thumbnail
        """

        if not self.output_directory or not os.path.isdir(self.output_directory):
            raise Exception(
                "Couldn't extract thumbnails from LMV: no file seems to have been created"
            )

        output_dir_path = os.path.join(self.output_directory, "output")
        svf_file_name = os.path.splitext(os.path.basename(self.__get_svf_path()))[0]

        # get the thumbnail data
        if thumbnail_source_path:
            with open(thumbnail_source_path, "rb") as fp:
                thumbnail_data = fp.read()
        else:
            thumbnail_data = self.get_thumbnail_data()

        # write the thumbnails on disk
        logger.debug("Writing thumbnail on disk")
        if thumbnail_data:
            images_dir_path = os.path.join(output_dir_path, "images")
            if not os.path.exists(images_dir_path):
                os.makedirs(images_dir_path)
            tmp_image_path = os.path.join(
                images_dir_path, "{}.jpg".format(svf_file_name)
            )
            with open(tmp_image_path, "wb") as fp:
                fp.write(thumbnail_data)

            return tmp_image_path

    def get_thumbnail_data(self):
        """
        Get the thumbnail binary data

        :return: The thumbnail binary data
        """

        _, ext = os.path.splitext(self.source_path)

        # if the source file is a wire file, we can try to directly read the SVF file to get the thumbnail data
        if ext == ".wire":
            thumbnail_data = self.__get_thumbnail_data_from_wire_file()
            if not thumbnail_data:
                thumbnail_data = self.__get_thumbnail_data_from_command_line()
        else:
            thumbnail_data = self.__get_thumbnail_data_from_command_line()

        return thumbnail_data

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

    def __get_thumbnail_data_from_command_line(self):
        """
        Run the command line to get thumbnail data

        :return: The thumbnail binary data
        """

        # get the command line to extract data from the thumbnail and execute it
        logger.debug("Running thumbnail extractor process")
        (
            thumbnail_extractor_cmd,
            output_path,
        ) = self.__get_thumbnail_extractor_command_line()
        p = subprocess.Popen(
            thumbnail_extractor_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        p_output, _ = p.communicate()

        if p.returncode != 0:
            raise Exception(p_output)

        with open(output_path, "rb") as fp:
            thumbnail_data = fp.read()

        return thumbnail_data

    def __get_thumbnail_data_from_wire_file(self):
        """
        Read the source file data to extract the thumbnail binary data

        :return: The thumbnail binary data
        """

        thumbnail_data = []

        with open(self.source_path, "rb") as fp:
            line = fp.readline()
            while line and line != "thumbnail JPEG\n":
                line = fp.readline()
            if not line:
                return thumbnail_data
            line = fp.readline()
            while line != "thumbnail end\n":
                thumbnail_data.append(line.replace("Th ", ""))
                line = fp.readline()

        return base64.b64decode("".join(thumbnail_data))

    def __get_translator_path(self, use_framework_translator=False):
        """
        Get the path to the translator we have to use according to the file extension

        :param use_framework_translator: True will get the translator path to the executable shipped with the
                                         framework, else False (default) will first look for the translator based
                                         on the file type and current engine that is running.
        :returns: The path to the translator
        """

        if use_framework_translator:
            # Don't try to determine the best translator to use, just use the one shipped with this framework
            root_dir = self.__get_resources_folder_path()
            return os.path.join(root_dir, "LMVExtractor", "atf_lmv_extractor.exe")

        # Determine which translator to use based on the file to be translated and the current engine.
        _, ext = os.path.splitext(self.source_path)

        # Alias case
        if ext in self.ALIAS_VALID_EXTENSION:

            # If we are running this code inside Alias, use the Alias extractor instead of the one shipped with this
            # framework to be sure to use the latest version
            current_engine = sgtk.platform.current_engine()
            if current_engine.name == "tk-alias":
                software_extractor = os.path.join(
                    current_engine.alias_bindir, "LMVExtractor", "atf_lmv_extractor.exe"
                )
                if os.path.exists(software_extractor):
                    return software_extractor

            # Fallback to the translator shipped with this framework
            root_dir = self.__get_resources_folder_path()
            return os.path.join(root_dir, "LMVExtractor", "atf_lmv_extractor.exe")

        # VRED case
        if ext in self.VRED_VALID_EXTENSION:
            root_dir = self.__get_resources_folder_path()
            return os.path.join(root_dir, "LMV", "viewing-vpb-lmv.exe")

        # Other file formats not currently supported
        raise ValueError("Couldn't find translator path: unknown file extension")

    def __get_thumbnail_extractor_command_line(self):
        """
        Get the command line used to extract thumbnail data according to file extension as well as the output path

        :returns:
            - The command line and it arguments as a list
            - The thumbnail output path
        """

        root_dir = self.__get_resources_folder_path()
        _, ext = os.path.splitext(self.source_path)

        # Alias case
        if ext in self.ALIAS_VALID_EXTENSION:
            svf_path = self.__get_svf_path()
            tmp_dir = os.path.normpath(
                os.path.join(
                    os.path.dirname(svf_path),
                    "..",
                    "..",
                    "images_{}".format(os.path.splitext(os.path.basename(svf_path))[0]),
                )
            )
            # be sure the tmp directory is created
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            cmd = [
                os.path.join(root_dir, "SVFThumbnailExtractor", "svf_thumb.exe"),
                svf_path,
                "-outpath=%s" % tmp_dir,
                "-size=1280",
                "-depth=2",
                "-passes=4",
            ]
            output_path = os.path.join(tmp_dir, "01_thumb_1280x1280.png")

        # VRED case
        elif ext in self.VRED_VALID_EXTENSION:
            output_path = tempfile.NamedTemporaryFile(
                suffix=".jpg", prefix="sgtk_thumb", delete=False
            ).name
            cmd = [
                os.path.join(root_dir, "VREDThumbnailExtractor", "extractMetaData.exe"),
                "--icv",
                output_path,
                self.source_path,
            ]

        else:
            raise ValueError(
                "Couldn't find thumbnail extractor path: unknown file extension"
            )

        return cmd, output_path

    @staticmethod
    def __get_resources_folder_path():
        """
        Get the resources folder path of the current framework

        :return: The path to the resources folder
        """
        return os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources"
            )
        )
