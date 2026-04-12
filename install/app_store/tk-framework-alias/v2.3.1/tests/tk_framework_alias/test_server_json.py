# Copyright (c) 2021 Autoiesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import pytest
import inspect
import json
import types

from tk_framework_alias.server.socketio import server_json
from tk_framework_alias.server.socketio import api_request
from tk_framework_alias.server.api import alias_api
from tk_framework_alias.server import alias_bridge
from tk_framework_alias.server.utils.exceptions import AliasServerJSONDecoderError


####################################################################################################
# fixtures
####################################################################################################


@pytest.fixture()
def json_encoder():
    """Fixture to return an instance of the AliasServerJSONEncoder class."""

    return server_json.AliasServerJSONEncoder()


####################################################################################################
# tk_framework_alias server_json AliasServerJSONEncoder
####################################################################################################


@pytest.mark.parametrize(
    "value",
    [
        (set()),
        (set({1})),
        (set({1, 2, 3})),
        (set({"1", "2", "2"})),
        ({1}),
        ({1, 2, 3}),
        ({"1", "2", "2"}),
    ],
)
def test_json_encode_set(value):
    """Test the AliasServerJSONEncoder default method to encode set objects."""

    result = server_json.AliasServerJSON.dumps(value)
    expected = json.dumps({"__type__": "set", "__value__": list(value)})
    assert result == expected


def test_json_encode_property():
    """Test the AliasServerJSONEncoder default method to encode property objects."""

    class MyClass:
        @property
        def my_class_property(self):
            pass

    result = server_json.AliasServerJSON.dumps(MyClass.my_class_property)
    expected = json.dumps(
        {
            "__property_name__": None,
        }
    )
    assert result == expected


def test_json_encode_exception():
    """Test the AliasServerJSONEncoder default method to encode Exception objects."""

    msg = "test exception"
    my_exception = Exception(msg)

    result = server_json.AliasServerJSON.dumps(my_exception)
    expected = json.dumps(
        {
            "__exception_class_name__": "Exception",
            "__msg__": msg,
            "__traceback__": None,
        }
    )
    assert result == expected


def test_json_encode_method():
    """Test the AliasServerJSONEncoder default method to encode method objects."""

    class MyClass:
        def my_class_method(self):
            pass

    my_class_obj = MyClass()

    result = server_json.AliasServerJSON.dumps(my_class_obj.my_class_method)
    expected = json.dumps(
        {
            "__function_name__": my_class_obj.my_class_method.__name__,
            "__is_method__": True,
        }
    )
    assert result == expected


def test_json_encode_function():
    """Test the AliasServerJSONEncoder default method to encode function objects."""

    def my_func():
        pass

    result = server_json.AliasServerJSON.dumps(my_func)
    expected = json.dumps(
        {
            "__function_name__": my_func.__name__,
            "__is_method__": False,
        }
    )
    assert result == expected


@pytest.mark.parametrize(
    "class_type",
    [
        (alias_api.AlDagNode),
        (alias_api.AlLayer),
        (alias_api.AlCoordinateSystem),
    ],
)
def test_json_encode_class_type(json_encoder, class_type):
    """
    Test the AliasServerJSONEncoder default method to encode class objects.

    Note that this test calls the encoder default method directly instead of using the json
    module dumps method. This is because all class members would also need to be encoded,
    which makes this test more complex. Instead of encoding all members, ensure that there
    are tests for each object type to be encoded.
    """

    members = inspect.getmembers(class_type)
    class_members = []
    for member_name, member_value in members:
        if inspect.isclass(member_value):
            class_name = member_value.__name__
            value = {
                "__module_name__": member_value.__module__,
                "__class_name__": class_name,
                "__members__": None,
            }
        else:
            value = member_value
        class_members.append((member_name, value))

    result = json_encoder.default(class_type)
    expected = {
        "__module_name__": class_type.__module__,
        "__class_name__": class_type.__name__,
        "__members__": class_members,
    }
    assert result == expected


@pytest.mark.parametrize(
    "enum",
    [
        (alias_api.AlMessageType.StageActive),
        (alias_api.AlStatusCode.Success),
        (alias_api.AlStatusCode.Failure),
        (alias_api.AlObjectType.DagNodeType),
        (alias_api.AlDisplayModeType.BoundingBox),
    ],
)
def test_json_encode_alias_api_enum(enum):
    """Test the AliasServerJSONEncoder default method to encode Alias API enum objects."""

    result = server_json.AliasServerJSON.dumps(enum)
    expected = json.dumps(
        {
            "__class_name__": enum.__class__.__name__,
            "__enum_name__": enum.name,
            "__enum_value__": enum.value,
        }
    )
    assert result == expected


@pytest.mark.parametrize(
    "alias_object",
    [
        (alias_api.create_layer("MyLayer")),
        (alias_api.create_layer_folder("MyFolder")),
        (alias_api.create_shader()),
        (alias_api.create_layered_shader()),
        (alias_api.create_switch_shader()),
        (alias_api.create_orthographic_camera(alias_api.AlWindow.AlViewType.Top)),
        (alias_api.create_perspective_camera()),
    ],
)
def test_json_encode_alias_api_object(alias_object):
    """Test the AliasServerJSONEncoder default method to encode Alias API objects."""

    instance_id = id(alias_object)

    result = server_json.AliasServerJSON.dumps(alias_object)
    expected = json.dumps(
        {
            "__module_name__": alias_object.__module__,
            "__class_name__": alias_object.__class__.__name__,
            "__instance_id__": instance_id,
        }
    )
    assert result == expected

    # Check that the object was added to the data model
    data_model = alias_bridge.AliasBridge().alias_data_model
    instance = data_model.get_instance(instance_id)
    assert instance is alias_object


def test_json_encode_mapping_proxy_type():
    """Test the AliasServerJSONEncoder default method to encode MappingProxyType objects."""

    dict_value = {"1": 1, "2": 2, 3: "3"}
    mp = types.MappingProxyType(dict_value)
    expected = json.dumps(dict_value)
    result = server_json.AliasServerJSON.dumps(mp)
    assert result == expected


def test_json_encode_module_spec():
    """Test the AliasServerJSONEncoder default method to encode ModuleSpec objects."""

    module_spec = alias_api.__spec__
    result = server_json.AliasServerJSON.dumps(module_spec)
    assert result == "null"


def test_json_encode_extension_file_loader():
    """Test the AliasServerJSONEncoder default method to encode ExtensionFileLoader objects."""

    loader = alias_api.__spec__.loader
    result = server_json.AliasServerJSON.dumps(loader)
    assert result == "null"


def test_json_encode_getsetdescriptor():
    """Test the AliasServerJSONEncoder default method to encode getsetdescriptor objects."""

    getsetdescriptor = alias_api.AliasPythonException.__cause__
    result = server_json.AliasServerJSON.dumps(getsetdescriptor)
    expected = json.dumps(
        {
            "__property_name__": "__cause__",
        }
    )
    assert result == expected


def test_json_encode_memberdescriptor():
    """Test the AliasServerJSONEncoder default method to encode memberdescriptor objects."""

    memberdescriptor = alias_api.AliasPythonException.__suppress_context__
    result = server_json.AliasServerJSON.dumps(memberdescriptor)
    expected = json.dumps(
        {
            "__property_name__": "__suppress_context__",
        }
    )
    assert result == expected


def test_json_encode_callable():
    """Test the AliasServerJSONEncoder default method to encode callable objects."""

    callable_obj = alias_api.AlGroupNode.__dir__
    result = server_json.AliasServerJSON.dumps(callable_obj)
    expected = json.dumps(
        {
            "__function_name__": callable_obj.__name__,
            "__is_method__": False,
        }
    )
    assert result == expected


def test_json_encode_callable_instancemethod():
    """Test the AliasServerJSONEncoder default method to encode callable objects."""

    instance_method = alias_api.AlGroupNode.as_dag_node_ptr
    result = server_json.AliasServerJSON.dumps(instance_method)
    expected = json.dumps(
        {
            "__function_name__": instance_method.__name__,
            "__is_method__": True,
        }
    )
    assert result == expected


def test_json_encode_module(json_encoder):
    """
    Test the AliasServerJSONEncoder default method for module objects.

    Note, this test is similar to the test_json_encode_class_type, as it call the json
    encoder default method to encode instead of the module dumps method. See the
    test_json_encode_class_type for more details on why.
    """

    result = json_encoder.default(alias_api)
    expected = {
        "__module_name__": alias_api.__name__,
        "__members__": inspect.getmembers(alias_api),
    }
    assert result == expected


def test_json_encode_error():
    """Test the AliasServerJSONEncoder default method for object that is not handled."""

    class ServerJSONCantHandleThisClass:
        pass

    obj = ServerJSONCantHandleThisClass()

    result = server_json.AliasServerJSON.dumps(obj)

    result_to_dict = json.loads(result)
    assert result_to_dict["__exception_class_name__"] == "TypeError"
    assert (
        result_to_dict["__msg__"]
        == f"Object of type {type(obj).__name__} is not JSON serializable"
    )

    # Check that the traceback is a list of strings reporting the stack trace
    assert isinstance(result_to_dict["__traceback__"], list)
    assert len(result_to_dict["__traceback__"]) > 0
    assert isinstance(result_to_dict["__traceback__"][0], str)


####################################################################################################
# tk_framework_alias server_json AliasServerJSONDecoder
####################################################################################################


def test_json_decode_api_request_function():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    func_name = "create_shader"
    func_args = []
    func_kwargs = {}
    value = json.dumps(
        {
            "__function_name__": func_name,
            "__function_args__": func_args,
            "__function_kwargs__": func_kwargs,
        }
    )

    result = server_json.AliasServerJSON.loads(value)

    assert isinstance(result, api_request.AliasApiRequestFunctionWrapper)
    assert result.instance == alias_api
    assert result.func_name == func_name
    assert result.func_args == func_args
    assert result.func_kwargs == func_kwargs


def test_json_decode_api_request_function_with_args():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    func_name = "create_layer"
    func_args = [1, 2, 3]
    func_kwargs = {"arg1": 1, "arg2": 2}
    value = json.dumps(
        {
            "__function_name__": func_name,
            "__function_args__": func_args,
            "__function_kwargs__": func_kwargs,
        }
    )

    result = server_json.AliasServerJSON.loads(value)

    assert isinstance(result, api_request.AliasApiRequestFunctionWrapper)
    assert result.instance == alias_api
    assert result.func_name == func_name
    assert result.func_args == func_args
    assert result.func_kwargs == func_kwargs


def test_json_decode_api_request_instance_method():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    instance = alias_api.create_layer("TestLayer")
    instance_id = data_model.register_instance(instance)

    func_name = "create_shader"
    func_args = []
    func_kwargs = {}
    value = json.dumps(
        {
            "__function_name__": func_name,
            "__function_args__": func_args,
            "__function_kwargs__": func_kwargs,
            "__instance_id__": instance_id,
        }
    )

    result = server_json.AliasServerJSON.loads(value)

    assert isinstance(result, api_request.AliasApiRequestFunctionWrapper)
    assert result.instance == instance
    assert result.func_name == func_name
    assert result.func_args == func_args
    assert result.func_kwargs == func_kwargs


def test_json_decode_api_request_property_getter():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request to get a property."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    instance = alias_api.create_layer("TestLayer")
    instance_id = data_model.register_instance(instance)
    name = "property_name"
    value = json.dumps(
        {
            "__instance_id__": instance_id,
            "__property_name__": name,
        }
    )

    result = server_json.AliasServerJSON.loads(value)

    assert isinstance(result, api_request.AliasApiRequestPropertyGetterWrapper)
    assert result.instance == instance
    assert result.property_name == name


def test_json_decode_api_request_property_setter():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request to get a property."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    instance = alias_api.create_layer("TestLayer")
    instance_id = data_model.register_instance(instance)
    property_value = "property_name"
    property_value = "test value"
    value = json.dumps(
        {
            "__instance_id__": instance_id,
            "__property_name__": property_value,
            "__property_value__": property_value,
        }
    )

    result = server_json.AliasServerJSON.loads(value)

    assert isinstance(result, api_request.AliasApiRequestPropertySetterWrapper)
    assert result.instance == instance
    assert result.property_name == property_value
    assert result.property_value == property_value


def test_json_decode_alias_instance():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    instance = alias_api.create_layer("TestLayer")
    data_model = alias_bridge.AliasBridge().alias_data_model
    instance_id = data_model.register_instance(instance)
    value = json.dumps(
        {
            "__instance_id__": instance_id,
        }
    )
    result = server_json.AliasServerJSON.loads(value)
    assert result is instance


def test_json_decode_alias_instance_not_found():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    instance = alias_api.create_layer("TestLayerNotFound")
    data_model = alias_bridge.AliasBridge().alias_data_model
    instance_id = data_model.register_instance(instance)
    data_model.unregister_instance(instance_id)
    value = json.dumps(
        {
            "__instance_id__": instance_id,
        }
    )
    with pytest.raises(AliasServerJSONDecoderError):
        server_json.AliasServerJSON.loads(value)


def test_json_decode_alias_api_class():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    class_type = alias_api.AlAnnotationLocator
    value = json.dumps(
        {
            "__class_name__": "AlAnnotationLocator",
        }
    )
    result = server_json.AliasServerJSON.loads(value)
    assert result is class_type


def test_json_decode_alias_api_enum():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    enum = alias_api.AlMessageType.PostRetrieve
    value = json.dumps(
        {
            "__class_name__": "AlMessageType",
            "__enum_name__": "PostRetrieve",
            "__enum_value__": int(enum),
        }
    )
    result = server_json.AliasServerJSON.loads(value)
    assert result is enum


def test_json_decode_callback_function():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    value = json.dumps(
        {
            "__callback_function_id__": "callback_id",
        }
    )
    result = server_json.AliasServerJSON.loads(value)
    assert inspect.isfunction(result)


def test_json_decode_set():
    """Test the AliasServerJSONDecoder object_hook method to decode an api request."""

    set_value = [1, 2, 3]
    value = json.dumps(
        {
            "__type__": "set",
            "__value__": [1, 2, 3],
        }
    )
    result = server_json.AliasServerJSON.loads(value)
    assert result == set(set_value)
