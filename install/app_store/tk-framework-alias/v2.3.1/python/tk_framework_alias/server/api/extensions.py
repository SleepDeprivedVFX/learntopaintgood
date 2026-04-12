# Copyright (c) 2025 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import importlib.util
import types
from typing import Callable

from . import alias_api


class AliasApiExtensionsBase:
    """Base class for defining extension functions to the Alias API module."""

    # NOTE: placeholder for base extension functions
    # def log_to_prompt_extension(self):
    #     """Placeholder function to demonstrate an extension function."""

    #     alias_api.log_to_prompt(
    #         "This is an extension function to the Alias API defined in python"
    #     )


def create_alias_api_class(base_class: type, new_name: str):
    """
    Create a new class type that inherits from the base class.

    :param base_class: The class to inherit from.
    :param new_name: The name of the new class.

    :return: The new class type.
    """

    class_dict = {"__module__": "alias_api"}
    for name, value in base_class.__dict__.items():
        if not name.startswith("__") or name in ("__init__", "__doc__"):
            class_dict[name] = value
    return type(new_name, base_class.__bases__, class_dict)


def create_method_wrapper(func: Callable, method_class_name: str) -> Callable:
    """
    Create a wrapper for a function such that it can be used as a method.

    :param func: The function to wrap.
    :param method_class_name: The name of the class that the method belongs to.

    :return: The wrapped function.
    """

    def method_wrapper(self, *args, **kwargs):
        return func(*args, **kwargs)

    # Preserve function metadata
    method_wrapper.__name__ = func.__name__
    method_wrapper.__doc__ = func.__doc__
    method_wrapper.__qualname__ = f"{method_class_name}.{func.__name__}"

    return method_wrapper


def get_alias_api_extensions_class_type(api_extensions_path: str) -> type:
    """
    Create a class type 'AliasApiExtensions' containing extension functions
    for the Alias API module.

    The 'AliasApiExtensions' class type will be created from the base class
    'AliasApiExtensionsBase' and will include any user-defined functions
    defined in the file specified by `api_extensions_path`.

    :param api_extensions_path: The file path to load user-defined Alias API
        extension functions.

    :return: The class type object named 'AliasApiExtensions'.
    """

    # Create a new class type to combine base api extension
    # functions with the user provided custom api functions
    AliasApiExtensionsClassType = create_alias_api_class(
        AliasApiExtensionsBase, "AliasApiExtensions"
    )

    # If no path is provided, return the base extensions
    if not api_extensions_path:
        return AliasApiExtensionsClassType

    # If the path is a directory, recursively get all python files in it
    if os.path.isdir(api_extensions_path):
        # Recursively get all .py files in the directory and subdirectories
        py_files = []
        for root, dirs, files in os.walk(api_extensions_path):
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
    else:
        py_files = [api_extensions_path]

    # Load each file as a module and add its functions to the AliasApiExtensions class
    for file_path in py_files:
        if not os.path.isfile(file_path):
            continue

        file_name = os.path.basename(file_path)
        module_name = os.path.splitext(file_name)[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Could not load spec from {file_path}")

        # Get the module from the file path spec and inject the alias_api
        # into the module's globals so that the class methods have access to
        # alias_api
        module = importlib.util.module_from_spec(spec)
        module.__dict__["alias_api"] = alias_api
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ImportError(
                f"Failed to execute module {module_name} from {file_path}: {e}"
            )

        # Add the user-defined functions as methods to the AliasApiExtensions class
        for module_attr_name in dir(module):
            module_attr = getattr(module, module_attr_name)
            if not callable(module_attr) or module_attr_name.startswith("_"):
                continue
            # Create the wrapped method and add it to the AliasApiExtensions class
            method_func = create_method_wrapper(
                module_attr, AliasApiExtensionsClassType.__name__
            )
            setattr(AliasApiExtensionsClassType, module_attr_name, method_func)

    return AliasApiExtensionsClassType


def add_alias_api_extensions_to_module(
    api_extensions_path: str, module: types.ModuleType
) -> None:
    """
    Add the AliasApiExtensions class type to the given module.

    This function will create the AliasApiExtensions class type and add it
    to the module as 'AliasApiExtensions' attribute, making it available for use
    in the module.

    :param api_extensions_path: The file path to load user-defined Alias API
                                extension functions.
    :param module: The module to add the AliasApiExtensions class type to.
    """

    # Create the AliasApiExtensions class type and assign it to the module
    module.AliasApiExtensions = get_alias_api_extensions_class_type(api_extensions_path)
