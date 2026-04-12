# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from ..api import alias_api

from .. import alias_bridge
from ..utils.exceptions import AliasApiRequestNotValid


class AliasApiRequestWrapper:
    """
    Base abstract class to wrap data to make an Alias API request.

    This class is mainly used by the AliasServerJSON module to decode incoming data from a
    client, to make an Alias api request from the client data.

    Supported api requests:
        1. module function (e.g. alias_api.get_layers())
        2. instance methods (e.g. layer.is_folder())
        3. instance property getter (e.g. layer.symmetric)
        4. instance property setter (e.g. layer.symmetric = True)
    """

    # ----------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def create_wrapper(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            if subclass.needs_wrapping(data):
                return subclass(data)

        return None

    @classmethod
    def required_data(cls):
        """
        Abstract class method.

        Return the set of required data dictionary keys to create an instance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        raise NotImplementedError("Subclass must implement")

    @classmethod
    def needs_wrapping(cls, value):
        """
        Check if the value represents an object that needs to be wrapped by this proxy class.

        :param value: The value to check if needs wrapping.
        :type value: any

        :return: True if the value should be wrapped by this class, else False.
        :rtype: bool
        """

        raise NotImplementedError("Subclass must implement")

    @classmethod
    def _create(cls, data):
        """
        Create and return a new object of this type from the given data, if possible.

        :param data: The data to create the object from.
        :type data: dict

        :return: An instance of this class.
        :rtype: AliasApiRequestWrapper
        """

        raise NotImplementedError("Subclass must implement")

    # ----------------------------------------------------------------------------------------
    # Public methods

    def validate(self, request_name):
        """
        Validate the request against this wrapper.

        :param request_name: The name of the api request.
        :type request_name: str
        """

        raise NotImplementedError("Subclass must implement")

    def execute(self, request_name):
        """
        Execute the api request for this wrapper object.

        :param request: The api request name.
        :type request: str
        """

        raise NotImplementedError("Subclass must implement")


class AliasApiRequestFunctionWrapper(AliasApiRequestWrapper):
    """
    A wrapper for Alias API functions.

    This includes module-level functions, class functions and instance methods.
    """

    def __init__(self, data):
        """Initialize the wrapper data."""

        self.__func_name = data["__function_name__"]
        self.__func_args = data["__function_args__"]
        self.__func_kwargs = data["__function_kwargs__"]

        self.__instance = None
        instance_id = data.get("__instance_id__")
        if instance_id:
            # This is an instance method, or class method
            data_model = alias_bridge.AliasBridge().alias_data_model
            self.__instance = data_model.get_instance(instance_id)

        if self.__instance is None:
            # This is a module-level function
            self.__instance = alias_api

    def __str__(self) -> str:
        """Return a string representation for the Alias Api request object."""

        try:
            arg_list = []
            if self.func_args:
                args_str = ", ".join([str(a) for a in self.func_args])
                arg_list.append(args_str)

            if self.func_kwargs:
                kwarg_list = ", ".join(
                    [f"{k}={v}" for k, v in self.func_kwargs.items()]
                )
                arg_list.append(kwarg_list)

            full_args_str = ", ".join(arg_list)

            func_str = f"{self.func_name}({full_args_str})"
            if not self.instance:
                return func_str
            if hasattr(self.instance, "__name__"):
                return f"{self.instance.__name__}.{func_str}"
            if hasattr(self.instance, "__class__"):
                return f"{self.instance.__class__.__name__}.{func_str}"
            return f"{self.instance}.{func_str}"
        except:
            # Do not fail on trying to return a string representation.
            return super(AliasApiRequestFunctionWrapper, self).__str__()

    # ----------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an instance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__function_name__",
                "__function_args__",
                "__function_kwargs__",
            ]
        )

    @classmethod
    def needs_wrapping(cls, value):
        """
        Check if the value represents an object that needs to be wrapped by this proxy class.

        :param value: The value to check if needs wrapping.
        :type value: any

        :return: True if the value should be wrapped by this class, else False.
        :rtype: bool
        """

        return cls.required_data().issubset(set(value.keys()))

    # ----------------------------------------------------------------------------------------
    # Properties

    @property
    def instance(self):
        """
        Get the instance that this function belongs to.

        If this function is an instance method, the instance will be an Alias object. If the
        function is a global function, the instance will be the Alias Python API module.
        """
        return self.__instance

    @property
    def func_name(self):
        """Get the name of the function."""
        return self.__func_name

    @property
    def func_args(self):
        """Get the arguments to be passed to the function."""
        return self.__func_args

    @property
    def func_kwargs(self):
        """Get the key-word arguments to be passed to the function."""
        return self.__func_kwargs

    # ----------------------------------------------------------------------------------------
    # Public methods

    def validate(self, request_name):
        """
        Return True if the request corresponds to this function.

        The request corresponds to the function if the request name matches the function name.

        :param request_name: The name of the request.
        :type request_name: str

        :return: True if request is valid, else raises AliasApiRequestNotValid exception.
        :rtype: bool
        """

        if request_name != self.__func_name:
            raise AliasApiRequestNotValid(
                f"Requested '{request_name}' but should be '{self.func_name}'"
            )
        return True

    def execute(self, request_name):
        """
        Execute the Alias API request to execute the api function.

        :param request_name: The api request name.
        :type request_name: str

        :return: The return value api function.
        :rtype: any
        """

        self.validate(request_name)

        if self.func_name == "__new__":
            # NOTE pybind11 does not support calling cls.__new__(cls, args, kwargs)
            # until the python api is updated to provide a trampoline class to allow
            # calling __new__ method, we will just intercept this method and call the
            # constructor directly
            class_instance = self.func_args[0]
            args = self.func_args[1:]
            return class_instance(*args, *self.func_kwargs)
        else:
            # Execute the function to make the Alias API request.
            method = getattr(self.instance, self.func_name)
            return method(*self.func_args, **self.func_kwargs)


class AliasApiRequestPropertyGetterWrapper(AliasApiRequestWrapper):
    """A wrapper for Alias API instance property getters."""

    def __init__(self, data):
        """Initialize the wrapper data."""

        data_model = alias_bridge.AliasBridge().alias_data_model
        instance_id = data["__instance_id__"]

        self.__instance = data_model.get_instance(instance_id)
        self.__property_name = data["__property_name__"]

    def __str__(self) -> str:
        """Return a string representation for the Alias Api request object."""

        if hasattr(self.instance, "__name__"):
            return f"{self.instance.__name__}.{self.property_name}"

        if hasattr(self.instance, "__class__"):
            return f"{self.instance.__class__.__name__}.{self.property_name}"

        return f"{self.instance}.{self.property_name}"

    # ----------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an instance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__instance_id__",
                "__property_name__",
            ]
        )

    @classmethod
    def needs_wrapping(cls, value):
        """
        Check if the value represents an object that needs to be wrapped by this proxy class.

        :param value: The value to check if needs wrapping.
        :type value: any

        :return: True if the value should be wrapped by this class, else False.
        :rtype: bool
        """

        return cls.required_data() == set(value.keys())

    # ----------------------------------------------------------------------------------------
    # Properties

    @property
    def instance(self):
        """Get the id of the instance that this class corresponds to."""
        return self.__instance

    @property
    def property_name(self):
        """Get the id of the instance that this class corresponds to."""
        return self.__property_name

    # ----------------------------------------------------------------------------------------
    # Public methods

    def validate(self, request_name):
        """
        Return True if the request corresponds to this property.

        The request corresponds to the function if the request name matches the property name.

        :param request_name: The name of the request.
        :type request_name: str

        :return: True if request is valid, else raises AliasApiRequestNotValid exception.
        :rtype: bool
        """

        if request_name != self.property_name:
            raise AliasApiRequestNotValid(
                f"Requested '{request_name}' but should be '{self.property_name}'"
            )
        return True

    def execute(self, request_name):
        """
        Execute the Alias API request to get the value of the property this object wraps.

        :param request_name: The api request name.
        :type request_name: str

        :return: The property value
        :rtype: any
        """

        self.validate(request_name)
        return getattr(self.instance, self.property_name)


class AliasApiRequestPropertySetterWrapper(AliasApiRequestWrapper):
    """A wrapper for making an Alias API request to set a property value."""

    def __init__(self, data):
        """Initialize the data."""

        data_model = alias_bridge.AliasBridge().alias_data_model
        instance_id = data["__instance_id__"]

        self.__instance = data_model.get_instance(instance_id)
        self.__property_name = data["__property_name__"]
        self.__property_value = data["__property_value__"]

    def __str__(self) -> str:
        """Return a string representation for the Alias Api request object."""

        if hasattr(self.instance, "__name__"):
            return (
                f"{self.instance.__name__}.{self.property_name} = {self.property_value}"
            )

        if hasattr(self.instance, "__class__"):
            return f"{self.instance.__class__.__name__}.{self.property_name} = {self.property_value}"

        return f"{self.instance}.{self.property_name} = {self.property_value}"

    # ----------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an instance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__instance_id__",
                "__property_name__",
                "__property_value__",
            ]
        )

    @classmethod
    def needs_wrapping(cls, value):
        """
        Check if the value represents an object that needs to be wrapped by this proxy class.

        :param value: The value to check if needs wrapping.
        :type value: any

        :return: True if the value should be wrapped by this class, else False.
        :rtype: bool
        """

        return cls.required_data() == set(value.keys())

    # ----------------------------------------------------------------------------------------
    # Properties

    @property
    def instance(self):
        """Get the instance that this property belongs to."""
        return self.__instance

    @property
    def property_name(self):
        """Get the name of this property."""
        return self.__property_name

    @property
    def property_value(self):
        """Get the value to set on this property."""
        return self.__property_value

    # ----------------------------------------------------------------------------------------
    # Public methods

    def validate(self, request_name):
        """
        Return True if the request corresponds to this property.

        The request corresponds to the function if the request name matches the property name.

        :param request_name: The name of the request.
        :type request_name: str

        :return: True if request is valid, else raises AliasApiRequestNotValid exception.
        :rtype: bool
        """

        if request_name != self.property_name:
            raise AliasApiRequestNotValid(
                f"Requested '{request_name}' but should be '{self.property_name}'"
            )
        return True

    def execute(self, request_name):
        """
        Execute the Alias API request to set the value of the property this object wraps.

        No value is returned.

        :param request_name: The api request name.
        :type request_name: str
        """

        self.validate(request_name)
        setattr(self.instance, self.property_name, self.property_value)
