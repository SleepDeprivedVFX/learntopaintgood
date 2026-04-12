#!/usr/bin/env python3
# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import subprocess
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile
import shutil


def zip_recursively(zip_file, root_dir, folder_name):
    """Zip the files at the given folder recursively."""

    path = root_dir / folder_name
    if path.is_dir():
        # for root, _, files in os.walk(root_dir / folder_name):
        for root, _, files in os.walk(path):
            for f in files:
                full_file_path = Path(os.path.join(root, f))
                zip_file.write(full_file_path, full_file_path.relative_to(root_dir))
    else:
        zip_file.write(path, path.relative_to(root_dir))


def modify_pyside(pyside_path):
    """
    Modify the PySide package such that it only includes the necessary files.

    This function supports modifying PySide versions:
        - PySide2
        - PySide6
    """

    # Required files by name.
    required_files = [
        "QtCore.pyd",
        "QtCore.pyi",
        "Qt5Core.dll",  # PySide2
        "Qt6Core.dll",  # PySide6
    ]
    # Required files by file type extension. Files may be ignored if they fall into one of the
    # specified ignore patterns, even if they are one of these required file types
    required_file_types = [
        ".dll",
        ".lib",
        ".py",
    ]
    # Ignore files that start with these prefixes, unless they are in the 'required_files'
    ignore_files_startswith = ["Qt"]

    # First create a temp directory to create the stripped down PySide package
    with TemporaryDirectory() as pyside_temp_dir:
        # Add all required files
        for required_file in required_files:
            src_path = os.path.join(pyside_path, required_file)
            if not os.path.exists(src_path):
                # Some required files may be skipped due to version differences
                print(f"\tSkipping {required_file}")
                continue
            dst_path = os.path.join(pyside_temp_dir, required_file)
            shutil.copyfile(src_path, dst_path)

        # Go through the PySide top-level directory and add all files with the required file
        # type, unless it falls into one of the ignore patterns, or is already copied over.
        for file_name in os.listdir(pyside_path):
            # Check ignore patterns
            ignore = False
            for startswith_pattern in ignore_files_startswith:
                if file_name.startswith(startswith_pattern):
                    ignore = True
                    break
            if ignore:
                continue

            # Check the file extension
            _, ext = os.path.splitext(file_name)
            if ext not in required_file_types:
                continue

            # Check if it already exists
            dst_path = os.path.join(pyside_temp_dir, file_name)
            if os.path.exists(dst_path):
                continue

            # Copy the file to the new PySide package
            src_path = os.path.join(pyside_path, file_name)
            shutil.copyfile(src_path, dst_path)

        # Remove the original PySide package
        shutil.rmtree(pyside_path)
        # Copy the temp package to the original path
        shutil.copytree(pyside_temp_dir, pyside_path)


def install_common_python_packages(python_dist_dir):
    """
    Install common Python packages.

    :param python_dist_dir: The path containing the package requirements.txt
        file, and where to install the packages.
    :type python_dist_dir: str
    """

    if not os.path.exists(python_dist_dir):
        print(f"Cannot find Python distribution folder {python_dist_dir}")
        return

    with TemporaryDirectory() as temp_dir:
        print("Installing common Python packages...")

        temp_dir_path = Path(temp_dir)

        requirements_txt = os.path.join(python_dist_dir, "requirements.txt")
        if not os.path.exists(requirements_txt):
            raise Exception(f"Cannot find requirements file {requirements_txt}")

        packages_dist_dir = os.path.join(python_dist_dir, "packages")
        if not os.path.exists(packages_dist_dir):
            os.makedirs(packages_dist_dir)

        frozen_requirements_txt = os.path.join(
            packages_dist_dir, "frozen_requirements.txt"
        )

        # Pip install everything and capture everything that was installed.
        subprocess.run(
            [
                "python",
                "-m",
                "pip",
                "install",
                "-r",
                requirements_txt,
                "--no-compile",
                # The combination of --target and --upgrade forces pip to install
                # all packages to the temporary directory, even if an already existing
                # version is installed
                "--target",
                temp_dir,
                "--upgrade",
            ]
        )
        subprocess.run(
            ["python", "-m", "pip", "freeze", "--path", temp_dir],
            stdout=open(frozen_requirements_txt, "w"),
        )

        # Quickly compute the number of requirements we have.
        nb_dependencies = len([_ for _ in open(frozen_requirements_txt, "rt")])

        # Figure out if those packages were installed as single file packages or folders.
        package_names = [
            package_name
            for package_name in os.listdir(temp_dir)
            if "info" not in package_name and package_name != "bin"
        ]

        # Make sure we found as many Python packages as there
        # are packages listed inside frozen_requirements.txt
        # assert len(package_names) == nb_dependencies
        assert len(package_names) >= nb_dependencies

        # Write out the zip file for python packages. Compress the zip file with ZIP_DEFLATED. Note
        # that this requires zlib to decompress when importing. Compression also causes import to
        # be slower, but the file size is simply too large to not be compressed
        pkgs_zip_path = os.path.join(packages_dist_dir, "pkgs.zip")
        pkgs_zip = zipfile.ZipFile(pkgs_zip_path, "w", zipfile.ZIP_DEFLATED)

        for package_name in package_names:
            print(f"Zipping {package_name}...")
            zip_recursively(pkgs_zip, temp_dir_path, package_name)


def install_qt_packages(python_dist_dir):
    """
    Install Qt packages.

    :param python_dist_dir: The path containing the Qt directory with the
        package requirements.txt file, and where to install the packages.
    :type python_dist_dir: str
    """

    qt_dist_dir = os.path.join(python_dist_dir, "qt")
    if not os.path.exists(qt_dist_dir):
        print(f"No Qt extensions to install")
        return

    # We expect the qt directory to contain a list of directories, named by Alias version
    for alias_version in os.listdir(qt_dist_dir):
        alias_version_dir_path = os.path.join(qt_dist_dir, alias_version)
        if not os.path.isdir(alias_version_dir_path):
            continue

        print(f"Installing Qt packages for Alias {alias_version}...")

        with TemporaryDirectory() as qt_temp_dir:
            qt_temp_dir_path = Path(qt_temp_dir)

            requirements_txt = os.path.join(alias_version_dir_path, "requirements.txt")
            if not os.path.exists(requirements_txt):
                raise Exception(f"Cannot find requirements file {requirements_txt}")

            qt_packages_dist_dir = os.path.join(
                python_dist_dir, "packages", "qt", alias_version
            )
            if not os.path.exists(qt_packages_dist_dir):
                os.makedirs(qt_packages_dist_dir)

            frozen_requirements_txt = os.path.join(
                qt_packages_dist_dir, "frozen_requirements.txt"
            )

            # Pip install Qt packages from requirements and capture everything that was installed.
            subprocess.run(
                [
                    "python",
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    requirements_txt,
                    "--no-compile",
                    # The combination of --target and --upgrade forces pip to install
                    # all packages to the temporary directory, even if an already existing
                    # version is installed
                    "--target",
                    qt_temp_dir,
                    "--upgrade",
                ]
            )
            subprocess.run(
                ["python", "-m", "pip", "freeze", "--path", qt_temp_dir],
                stdout=open(frozen_requirements_txt, "w"),
            )

            # Quickly compute the number of requirements we have.
            nb_dependencies = len([_ for _ in open(frozen_requirements_txt, "rt")])

            # Figure out if those packages were installed as single file packages or folders.
            package_names = [
                package_name
                for package_name in os.listdir(qt_temp_dir)
                if "info" not in package_name and package_name != "bin"
            ]

            # Make sure we found both PySide and shiboken packages
            assert len(package_names) == 2

            qt_extension_modules = [
                "PySide2",
                "shiboken2",
                "PySide6",
                "shiboken6",
            ]

            # Write out the zip file for qt c extension pacakges. These are handled separately, since they
            # need to be unzipped at runtime in order to be imported, AND it will vary depending on the
            # Alias version
            qt_extension_zip_path = os.path.join(
                qt_packages_dist_dir, "qt_extensions.zip"
            )
            qt_ext_zip = zipfile.ZipFile(
                qt_extension_zip_path, "w", zipfile.ZIP_DEFLATED
            )

            for package_name in package_names:
                print(f"Zipping {package_name}...")

                full_package_path = qt_temp_dir_path / package_name

                if package_name.startswith("PySide"):
                    # Special handling for PySide packages to limit the package size. Only the QtCore
                    # module is needed, so this package will be stripped down to only include the
                    # necessary files
                    modify_pyside(full_package_path)

                if package_name in qt_extension_modules:
                    # Qt extensions are also C extension modules, but they need to be handled separately
                    # in order to support mulitple Qt versions for Alias
                    zip_recursively(qt_ext_zip, qt_temp_dir_path, package_name)
                else:
                    print(f"Unexpected package: {package_name}")


#
# Script body
#
python_dist_dir = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        "dist",
        "Python",
        f"Python{sys.version_info.major}{sys.version_info.minor}",
    )
)
install_common_python_packages(python_dist_dir)
install_qt_packages(python_dist_dir)
