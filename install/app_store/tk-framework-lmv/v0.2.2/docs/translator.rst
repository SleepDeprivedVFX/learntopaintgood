LMV Translation
###############

.. currentmodule:: translator

Introduction
============

The :class:`LMVTranslator` class helps you translate files to a file format readable by ShotGrid
3D Viewer. It also offers the possibility to extract a thumbnail from the source file.

Sample Code: Upload file to ShotGrid Version
--------------------------------------------
Here is a simple piece of code to create the zip file which will be uploaded to ShotGrid in order
to be read by the 3D Viewer::

    # source_path = "/path/to/file.wire"

    # here we assume that the version is already created in ShotGrid and we have it ID
    version_id = 1234

    # create an instance of LMVExtractor, translate the file and package the output files
    lmv_extractor = LMVExtractor(source_path)
    lmv_extractor.translate()

    # use the version id as the svf file name otherwise the 3D Viewer couldn't be able to read
    # the media file
    package_path, _ = lmv_extractor.package(svf_file_name=version_id)

    # finally, upload the file to the Version and change the Translation type to LMV
    sg.upload("Version", version_id, path=package_path, field_name="sg_uploaded_movie")
    sg.update("Version", version_id, data={"sg_translation_type": "LMV"})


Sample Code: Create a thumbnail from a source file
---------------------------------------------------
It's also possible to extract a thumbnail from the source file using the LMV conversion::

    # source_path = "/path/to/file.wire"

    # we need to translate the file in order to extract the thumbnail
    lmv_extractor = LMVExtractor(source_path)
    lmv_extractor.translate()

    # we can then extract the thumbnail properly
    thumbnail_path = lmv_extractor.extract_thumbnail()

LMVTranslator
=====================================================

.. autoclass:: LMVTranslator
    :members:
