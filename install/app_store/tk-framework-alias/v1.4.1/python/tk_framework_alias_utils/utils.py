# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import hashlib
import os
import logging
import logging.handlers

from . import environment_utils


def version_cmp(version1, version2):
    """
    Compare the version strings.

    :param version1: A version string to compare against version2 e.g. 2022.2
    :param version2: A version string to compare against version1 e.g. 2021.3.1

    :return: The result of the comparison:
         1 - version1 is greater than version2
         0 - version1 and version2 are equal
        -1 - version1 is less than version2
    :rtype: int
    """

    # This will split both the versions by the '.' char to get the major, minor, patch values
    arr1 = version1.split(".")
    arr2 = version2.split(".")
    n = len(arr1)
    m = len(arr2)

    # Converts to integer from string
    arr1 = [int(i) for i in arr1]
    arr2 = [int(i) for i in arr2]

    # Compares which list is bigger and fills the smaller list with zero (for unequal
    # delimeters)
    if n > m:
        for i in range(m, n):
            arr2.append(0)
    elif m > n:
        for i in range(n, m):
            arr1.append(0)

    # Returns 1 if version1 is greater
    # Returns -1 if version2 is greater
    # Returns 0 if they are equal
    for i in range(len(arr1)):
        if arr1[i] > arr2[i]:
            return 1
        elif arr2[i] > arr1[i]:
            return -1
    return 0


def get_key():
    """Return a key that can be used for encryption."""

    from cryptography.fernet import Fernet

    key_location = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "config",
        )
    )

    # First, try to get the existing key
    key = None
    if os.path.exists(key_location):
        with open(key_location, "r") as fp:
            key = fp.read()
        if key:
            key = key.encode()

    if not key:
        # No key found, generate a new one.
        # NOTE this requires write access to the config file location. This will fail if the user
        # does not have permission. TODO the key should be stored in a database or key vault.
        key = Fernet.generate_key()
        key_as_str = key.decode()
        with open(key_location, "w+") as fp:
            fp.write(key_as_str)

    return Fernet(key)


def encrypt_to_str(value):
    """
    Encrypt the value.

    :param value: The value to encrypt.
    :type value: str

    :return: The value encrypted.
    :rtype: str
    """

    fernet = get_key()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_from_str(value):
    """
    Decrypt the value.

    :param value: The value to decrypt.
    :type value: str

    :return: The decrypted value.
    :rtype: str
    """

    fernet = get_key()
    value_as_bytes = value.encode()
    decrypted = fernet.decrypt(value_as_bytes)
    return decrypted.decode()


def get_logger(
    log_module,
    log_name,
    log_level=logging.DEBUG,
    rotate_when="D",
    rotate_interval=1,
    rotate_backups=7,
):
    """
    Return a rotating event logger.

    The default log rotation is set to rotate each day, and a full week (7 days) of logs will
    be kept on disk.

    :param log_module: The module that this logger will be used for. This is used to create
        the logger name identifier.
    :param log_module: str
    :param log_name: The name used to create the logger name identifier, as well as the log
        file, e.g. {log_name}.log
    :param log_name: str
    :param log_level: The lowest logging level that this logger will handle. Default is debug.
    :param log_level: int (e.g. logging.INFO)
    :param rotate_when: When the log file will be rotated (see
        logging.handlers.TimedRotatingFileHandler for possible values). Default is days.
    :param rotate_when: str
    :param rotate_interval: The interval at which files are rotated. Default is 1.
    :param rotate_interval: int
    :param rotate_backups: The number of backup log files kept. Default is 7.
    :param rotate_backups: int

    :return: The logger object.
    :rtype: Logger
    """

    name = f"{log_module}.{log_name}"
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Ensure that the log file directory exists on local disk
    log_dir = os.path.join(
        environment_utils.get_alias_plugin_dir(),
        "log",
    )
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Add a rotating file handler to write log messages to file on disk
    log_file_path = os.path.join(log_dir, f"{log_name}.log")
    fh = logging.handlers.TimedRotatingFileHandler(
        log_file_path,
        when=rotate_when,
        interval=rotate_interval,
        backupCount=rotate_backups,
    )
    fh.setLevel(log_level)
    logger.addHandler(fh)

    return logger


def get_md5_hex_string(file_name):
    """Return the hex string using MD5."""

    hash_md5 = hashlib.md5()
    with open(file_name, "rb") as fp:
        for chunk in iter(lambda: fp.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def verify_file(src_file, verify_to_file):
    """Return True if the file to verify is the same as the source, using MD5."""

    src_hex = get_md5_hex_string(src_file)
    file_hex = get_md5_hex_string(verify_to_file)
    return src_hex == file_hex
