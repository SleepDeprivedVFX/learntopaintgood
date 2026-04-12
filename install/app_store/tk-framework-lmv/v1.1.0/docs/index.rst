The Flow Production Tracking LMV Framework
##########################################

With the introduction of the 3D Viewer inside Flow Production Tracking, we now have the possibility to review
3D files directly inside the web interface.

The Flow Production Tracking LMV Framework contains a collection of libraries and tools to make it possible
to build the zip package required to view the 3D model in the web interface.

This functionality is currently used by the Autodesk Alias and Autodesk VRED Flow Production Tracking Integrations
to support Design Studio workflows.

Once the zip package is built, the ``sg_translation_type`` field on the Version must be set to **LMV**.
The zip file must then be uploaded to Flow Production Tracking using the ``sg_uploaded_movie`` field on the Version.

.. warning::
    Currently the zip file and its' contents must be named with the Version ID for the 3D Viewer to be able to
    find the media file.

.. image:: images/version_fields.png

.. note::
    Currently these file formats are compatible with the LMV translation:
        * .wire
        * .igs
        * .CATPart
        * .stp
        * .jt
        * .fbx
        * .vpb

Contents:

.. toctree::
   :maxdepth: 2

   translator
