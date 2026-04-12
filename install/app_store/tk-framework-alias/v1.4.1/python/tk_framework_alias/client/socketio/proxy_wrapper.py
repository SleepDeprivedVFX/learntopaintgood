# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import inspect
import threading
import types

from ..utils.exceptions import AliasClientNotConnected, AliasClientNotFound


class AliasClientObjectProxyWrapper:
    """
    Wrapper class for Alias data received from the server.

    Alias data will be sent from the socketio server to the client. To handle the Alias data,
    it will be encoded and decoded by a JSON module. This class is used to wrap the Alias data
    received by the server, for the client to handle.
    """

    # Store any Alias modules that have been created on the client side (here) that exist on
    # the server side. Currently there should only ever be one module, the 'alias_api', but in
    # the future there could be more api modules to add here.
    __modules = {}
    __module_lock = threading.Lock()

    # Store any Alias types that have been created on the client side (here), so that these
    # types do not need to be created each time the client recieves an object, as well as
    # then being able to compare object types for equality
    __types_by_module = {}
    __types_by_module_lock = threading.Lock()

    def __init__(self, data, module=None, attribute_name=None):
        """Initialize the proxy wrapper object."""

        # The raw data received from the server
        self.__data = data or {}

        # The module that this wrapper object belongs to
        self.__module = module

        # If this wrapper represents an attribute from a module, this is the module attribute
        # name for the wrapper object.
        self.__attribute_name = attribute_name

        # If this wrapper represents a module or class object, these are the memebrs of the
        # module or class as a JSON object.
        self.__members = data.get("__members__") or []

    # -------------------------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def get_module(cls, module_name):
        """Return the module for the given name."""

        with cls.__module_lock:
            return cls.__modules.get(module_name)

    @classmethod
    def store_module(cls, module_name, module):
        """Store the module in the registry by the given name."""

        with cls.__module_lock:
            cls.__modules[module_name] = module

    @classmethod
    def get_type(cls, module_name, type_name):
        """Return the type for the given module and type name."""

        with cls.__types_by_module_lock:
            return cls.__types_by_module.get(module_name, {}).get(type_name)

    @classmethod
    def store_type(cls, module_name, type_name, type_obj):
        """Store the type in the registry by the given module and type name."""

        with cls.__types_by_module_lock:
            cls.__types_by_module.setdefault(module_name, {})[type_name] = type_obj

    @classmethod
    def required_data(cls):
        """
        Abstract class method.

        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        raise NotImplementedError("Subclass must implement this method")

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

    @classmethod
    def create_proxy(cls, data):
        """
        Factory method to create an AliasClientObjectProxyWrapper object.

        A subclass of the AliasClientObjectProxyWrapper will be created based on the data.

        :return: The proxy wrapper object.
        :rtype: AliasClientObjectProxyWrapper
        """

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            if subclass.needs_wrapping(data):
                return subclass._create_proxy(data)

        return None

    @classmethod
    def _create_proxy(cls, data):
        """
        Factory method to create an instance that is a proxy for the Alias data object.

        This is the default method, which will just create a new instance of the class (or
        subclass). Override this method to create a mroe specific proxy object, that is not
        just an instane of the class.

        :param data: The Alias data to create a proxy for on our client side.
        :type data: Any

        :return: A proxy instance.
        :rtype: AliasClientObjectProxyWrapper
        """

        return cls(data)

    # -------------------------------------------------------------------------------------------------------
    # Properties

    @property
    def data(self):
        """Get the raw Alias data returned by the server, which is used to create the client proxy objects."""
        return self.__data

    @property
    def module(self):
        """Get the module this proxy wrapper object belongs to."""
        return self.__module

    @property
    def attribute_name(self):
        """Get the module attribute name this proxy wrapper object represents."""
        return self.__attribute_name

    # -------------------------------------------------------------------------------------------------------
    # Public methods

    def create_object(self, module, object_name):
        """
        Create an object from the proxy data to represent an Alias data object.

        :param module: The module that this proxy belongs to. The module is used to send api
            requests to retrieve the Alias data from the server.
        :type module: AliasClientObjectModuleProxy
        :param object_name: The name of the object being created.
        :tyep object_name: str

        :return: The object created from the proxy data to represent an Alias data object.
        :rtype: Any
        """

        self._init(module, object_name)
        return self._create_object()

    def sanitize(self):
        """Return the JSON serializable dictionary for this proxy object."""

        return self.data

    # -------------------------------------------------------------------------------------------------------
    # Protected methods

    def _init(self, module, attribute_name):
        """
        Initialize the proxy wrapper object for the given module.

        This must be called before the object can be created from the proxy (e.g. _create_object).
        """

        self.__module = module

        # Initialize the attribute name for this proxy object. At the time of creating the
        # proxy, the attribute name is not available. It is only known once the module calls
        # to create it the attribute from this proxy object.
        self.__attribute_name = attribute_name

    def _create_object(self):
        """
        Create an object from the proxy data to represent an Alias data object.

        Default is to just return the proxy object itself. Override to provide a custom
        object.

        :return: The object created from the proxy data to represent an Alias data object.
        :rtype: Any
        """

        return self

    def _get_attributes(self):
        """Return a dictionary of attribtues for this object."""

        attrs = {}

        for attr_name, attr_data in self.__members:
            if isinstance(attr_data, AliasClientObjectProxyWrapper):
                attrs[attr_name] = attr_data.create_object(self.module, attr_name)
            else:
                attrs[attr_name] = attr_data

        return attrs


class AliasClientModuleProxyWrapper(AliasClientObjectProxyWrapper):
    """
    A proxy wrapper for the Alias python modules.

    This class is responsible for taking a dictionary describing a python module (that lives
    on the server), and re-creating that module such that it can be interacted with as if it
    existed on the client side.

    The reason for this set up is to allow for seamless access to the Alias Python API, and
    minimal maintenance. The Alias Python API must be imported on the server side, in the same
    process as Alias, in order to communicate with the running instance of Alias. Since the
    client is running in a separate process, it does not have access to the Alias Python API.
    So we create this proxy module, such that it can be used in the same as when it is
    imported as usual. The way it achieves this is by creating a dynamic module with the same
    attributes as the original module, and intercepts any data accesses and instead creates a
    socketio call to retrieve the data from the server, which makes the actual api request.
    """

    def __init__(self, module_data):
        """Initialize"""

        super(AliasClientModuleProxyWrapper, self).__init__(module_data, module=self)

        self.__module_name = module_data["__module_name__"]
        self.__sio = None

    # -------------------------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__module_name__",
                "__members__",
            ]
        )

    # -------------------------------------------------------------------------------------------------------
    # Properties

    @property
    def sio(self):
        """Get the socketio client that this module uses to send and receive messages with Alias."""
        return self.__sio

    # -------------------------------------------------------------------------------------------------------
    # Public methods

    def get_or_create_module(self, sio):
        """
        Get or create the module from the proxy data.

        The first time this method is called, it will dynamically create a module from the
        proxy data. A module will be created with the specified name, and its attributes will
        be created and added to the module.

        If the module already has been created, it will just return that module.

        :return: The module object.
        :rtype: The type defined by the '__module_name'
        """

        self.__sio = sio
        module = self.get_module(self.__module_name)

        if not module:
            # Create the new module, and set its attributes
            module = types.ModuleType(self.__module_name)

            module_attrs = self._get_attributes()
            module.__dict__.update(module_attrs)

            # Store the module
            self.store_module(self.__module_name, module)

        return module

    def send_request(self, request_name, request_data):
        """
        Send an api request to the server to retrieve the module data.

        This is the method that allows the proxy module to actually retrieve the data from
        the server, to access Alias data. It will make the api request using the socketio
        communication.

        :param request_name: The api request name (e.g. function name)
        :type request_name: str
        :param request_data: The api request payload
        :typ request_data: dict

        :return: The return value of executing the api request.
        :rtype: Any
        """

        if not self.sio:
            raise AliasClientNotFound(
                "Alias client not found. Cannot send api request."
            )

        if not self.sio.connected:
            raise AliasClientNotConnected(
                "Alias client is not connected. Cannot send api reqest."
            )

        # Sanitize special case arguments before passing to api request.
        if request_data:
            if "__function_args__" in request_data:
                args = []
                for arg in request_data.get("__function_args__", []):
                    args.append(self.__sanitize_arg(arg))
                request_data["__function_args__"] = args

            if "__function_kwargs__" in request_data:
                kwargs = {}
                for name, arg in request_data.get("__function_kwargs__", {}).items():
                    kwargs[name] = self.__sanitize_arg(arg)
                request_data["__function_kwargs__"] = kwargs

        # Emit non-blocking GUI request (to avoid deadlocks with Alias) and wait for the event result.
        return self.sio.emit_threadsafe_and_wait(request_name, request_data)

    # -------------------------------------------------------------------------------------------------------
    # Private methods

    def __sanitize_arg(self, arg):
        """
        Sanitize the argument before passing it as an api request argument.

        Most arguments do not need special handling at this stage, since the api request
        arguments will be encoded by the socketio client JSON encoder class; however, there
        are certain cases in which at the time of encoding, not all necessary data is available
        to encode the argument.

        Special case handling for:
          functions: functions may be passed as callbacks, but since the function object
                     itself cannot be passed, a unique id is generated to lookup the
                     function when the callback is triggered. To store the function, we
                     need the socketio client object, which is not available at the time of
                     encoding.

        :param arg: The argument to sanitize.
        :type arg: Any
        """

        if inspect.isfunction(arg) or inspect.ismethod(arg):
            # Generate a unique id for functions to pass in the api request, so that when it
            # is invoked, we can look it up by the id to.
            if self.sio.has_callback(arg):
                callback_id = self.sio.get_callback_id(arg)
            else:
                callback_id = self.sio.set_callback(arg)

            # Return a dictionary specific to describing a callback function.
            return {"__callback_function_id__": callback_id}

        # No sanitizing necessary, just return the argument as is.
        return arg


class AliasClientPropertyProxyWrapper(AliasClientObjectProxyWrapper):
    """A proxy wrapper for Alias api intance properties."""

    def __get__(self, instance, owner):
        """
        Override this method to redirect the property get method.

        This proxy wrapper instead will make a request to the server to get the property data,
        since the object of this property lives on the server.
        """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.attribute_name,
        }
        return self.module.send_request(self.attribute_name, data)

    def __set__(self, instance, value):
        """
        Override this method to redirect the property set method.

        This proxy wrapper instead will make a request to the server to set the property data,
        since the object of this property lives on the server.
        """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.attribute_name,
            "__property_value__": value,
        }
        return self.module.send_request(self.attribute_name, data)

    # -------------------------------------------------------------------------------------------------------
    # Class methods

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__property_name__",
            ]
        )


class AliasClientFunctionProxyWrapper(AliasClientObjectProxyWrapper):
    """A proxy wrapper for Alias api functions."""

    def __init__(self, data):
        """Initialize"""

        super(AliasClientFunctionProxyWrapper, self).__init__(data)

        self.__func_name = data.get("__function_name__")
        self.__is_instance_method = data.get("__is_method__", False)

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__function_name__",
                "__is_method__",
            ]
        )

    def _create_object(self):
        """
        Create a function from the proxy data to represent a function in the Alias api.

        :return: The function object.
        :rtype: function
        """

        if self.__is_instance_method:
            return self.__get_method()
        return self.__get_function()

    def __get_method(self):
        """
        Return a function that acts as a method that sends an api request from the proxy data."""

        def __method(instance, *args, **kwargs):
            data = {
                "__instance_id__": instance.unique_id,
                "__function_name__": self.__func_name,
                "__function_args__": args,
                "__function_kwargs__": kwargs,
            }
            return self.module.send_request(self.__func_name, data)

        return __method

    def __get_function(self):
        """Return a function that sends an api request from the proxy data."""

        def __function(*args, **kwargs):
            data = {
                "__function_name__": self.__func_name,
                "__function_args__": args,
                "__function_kwargs__": kwargs,
            }
            return self.module.send_request(self.__func_name, data)

        return __function


class AliasClientClassProxyWrapper(AliasClientObjectProxyWrapper):
    """A proxy wrapper for Alias api classes."""

    def __init__(self, data):
        """Initialize"""

        super(AliasClientClassProxyWrapper, self).__init__(data)

        self.__class_name = self.data["__class_name__"]

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__module_name__",
                "__class_name__",
                "__members__",
            ]
        )

    def _create_object(self):
        """
        Create an object from the proxy data to represent a class type in Alias api.

        Inspect the data to create and return the Alias api class type, as a subclass
        of this class.

        :return: The class type object.
        :rtype: AliasClientClassProxyWrapper
        """

        class_attrs = self._get_attributes()
        return type(self.__class_name, (self.__class__,), class_attrs)


class AliasClientEnumProxyWrapper(AliasClientObjectProxyWrapper):
    """A proxy wrapper for Alias enum objects."""

    def __init__(self, data):
        """Initialize the enum object."""

        super(AliasClientEnumProxyWrapper, self).__init__(data)

        self.__name = data.get("__enum_name__")
        self.__value = data.get("__enum_value__")

    def __eq__(self, other):
        """
        Override equality operator for convenience.

        This allows enum objects to be compared without directly accessing their value
        property. This provides easier backward compatibility for Alias Python API usage
        within Toolkit (e.g. before socket communication).
        """

        if type(other) == type(self):
            return self.value == other.value
        return False

    def __hash__(self):
        """
        Override the hash function to allow enum to be hashable.

        With override the equality operator, we must not override the hash function to allow
        enum objects to still be hashable.

        Generate a unique hash value based on the enum type and value.
        """

        tuple_value = (self.__class__, self.value)
        return hash(tuple_value)

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__module_name__",
                "__class_name__",
                "__enum_name__",
                "__enum_value__",
            ]
        )

    @classmethod
    def _create_proxy(cls, data):
        """
        Override the base class method.

        Create an enum instance to represent an enum in Alias. Inspect the data to re-create
        the Alias enum type (as a subclass of this class).

        :param data: The data to create the proxy from.
        :type data: dict

        :return: An instance representing an Alias object.
        :rtype: AliasClientEnumProxyWrapper
        """

        enum_module_name = data["__module_name__"]
        enum_class_name = data["__class_name__"]
        enum_type = cls.get_type(enum_module_name, enum_class_name)
        if not enum_type:
            enum_type = type(enum_class_name, (cls,), {})
            cls.store_type(enum_module_name, enum_class_name, enum_type)

        return enum_type(data)

    @property
    def name(self):
        """Get the name of the enum."""
        return self.__name

    @property
    def value(self):
        """Get the value of the enum."""
        return self.__value


class AliasClientObjectProxy(AliasClientObjectProxyWrapper):
    """A proxy wrapper for intances of Alias objects."""

    def __init__(self, data):
        """Initialize"""

        super(AliasClientObjectProxy, self).__init__(data)

        self.__unique_id = self.data["__instance_id__"]

    @classmethod
    def required_data(cls):
        """
        Return the set of required data dictionary keys to create an intance of this class.

        :return: The set of required keys.
        :rtype: set
        """

        return set(
            [
                "__module_name__",
                "__class_name__",
                "__instance_id__",
            ]
        )

    @classmethod
    def _create_proxy(cls, data):
        """
        Override the base class method.

        Create an object instance to represent an Alias object. Inspect the data to re-create
        the Alias object data type. The goal is to create an object that can seamlessly be
        used as if it were the actual Alias object create from Alias.

        :param data: The data to create the proxy from.
        :type data: dict

        :return: An instance representing an Alias object.
        :rtype: AliasClientObjectProxy
        """

        proxy_module_name = data["__module_name__"]
        module = AliasClientObjectProxyWrapper.get_module(proxy_module_name)
        if not module:
            raise Exception("Module not found")
        proxy_type_name = data["__class_name__"]
        proxy_type = cls.get_type(proxy_module_name, proxy_type_name)
        if not proxy_type:
            lookup_type = getattr(module, proxy_type_name)
            proxy_attributes = lookup_type.__dict__
            proxy_attributes = {
                k: v for k, v in proxy_attributes.items() if not k.startswith("__")
            }
            proxy_type = type(proxy_type_name, (cls,), proxy_attributes)
            cls.store_type(proxy_module_name, proxy_type_name, proxy_type)

        # Return an actual instance of the proxy type, not just the type object (like other classes do)
        return proxy_type(data)

    @property
    def unique_id(self):
        """Return the unique id for this object."""
        return self.__unique_id
