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
import json

from tk_framework_alias.client.socketio import client_json
from tk_framework_alias.client.socketio import proxy_wrapper
from tk_framework_alias.client.utils.exceptions import AliasClientJSONEncoderError


####################################################################################################
# tk_framework_alias client_json AliasClientJSONEncoder
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
    """Test the AliasClientJSONEncoder default method to encode set objects."""

    result = client_json.AliasClientJSON.dumps(value)
    expected = json.dumps({"__type__": "set", "__value__": list(value)})
    assert result == expected


def test_json_encode_function():
    """Test the AliasClientJSONEncoder default method to encode function objects."""

    def my_func():
        pass

    with pytest.raises(AliasClientJSONEncoderError):
        client_json.AliasClientJSON.dumps(my_func)


def test_json_encode_class_type():
    """Test the AliasClientJSONEncoder default method to encode class objects."""

    class MyClassToEncode:
        pass

    result = client_json.AliasClientJSON.dumps(MyClassToEncode)
    expected = json.dumps(
        {
            "__class_name__": "MyClassToEncode",
        }
    )
    assert result == expected


def test_json_encode_alias_client_module_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientModuleProxyWrapper object."""

    module_data = {
        "__module_name__": "alias_api",
        "__members__": [],
    }
    module_proxy = proxy_wrapper.AliasClientModuleProxyWrapper(module_data)

    expected = json.dumps(module_data)
    result = client_json.AliasClientJSON.dumps(module_proxy)
    assert result == expected


def test_json_encode_alias_client_property_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientPropertyProxy object."""

    data = {
        "__property_name__": "test_prop",
    }
    proxy = proxy_wrapper.AliasClientPropertyProxyWrapper(data)

    expected = json.dumps(data)
    result = client_json.AliasClientJSON.dumps(proxy)
    assert result == expected


def test_json_encode_alias_client_function_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientFunctionProxy object."""

    data = {
        "__function_name__": "test_func",
        "__is_method__": False,
    }
    proxy = proxy_wrapper.AliasClientFunctionProxyWrapper(data)

    expected = json.dumps(data)
    result = client_json.AliasClientJSON.dumps(proxy)
    assert result == expected


def test_json_encode_alias_client_class_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientClassProxyWrapper object."""

    data = {
        "__class_name__": "my_class",
        "__members__": [],
    }
    proxy = proxy_wrapper.AliasClientClassProxyWrapper(data)

    expected = json.dumps(data)
    result = client_json.AliasClientJSON.dumps(proxy)
    assert result == expected


def test_json_encode_alias_client_enum_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientEnumProxyWrapper object."""

    data = {
        "__class_name__": "my_enum_class",
        "__enum_name__": "my_enum",
        "__enum_value__": 1,
    }
    proxy = proxy_wrapper.AliasClientEnumProxyWrapper(data)

    expected = json.dumps(data)
    result = client_json.AliasClientJSON.dumps(proxy)
    assert result == expected


def test_json_encode_alias_client_object_proxy():
    """Test the AliasClientJSONEncoder default method to encode an AliasClientObjectProxy object."""

    data = {
        "__instance_id__": 1,
    }
    proxy = proxy_wrapper.AliasClientObjectProxy(data)

    expected = json.dumps(data)
    result = client_json.AliasClientJSON.dumps(proxy)
    assert result == expected


####################################################################################################
# tk_framework_alias client_json AliasClientJSONDecoder
####################################################################################################


def test_json_decode_set():
    """Test the AliasClientJSONDecoder object_hook method to decode an api request."""

    set_value = [1, 2, 3]
    value = json.dumps(
        {
            "__type__": "set",
            "__value__": [1, 2, 3],
        }
    )

    result = client_json.AliasClientJSON.loads(value)
    assert result == set(set_value)


def test_json_decode_exception():
    """Test the AliasClientJSONDecoder object_hook method to decode an exception object."""

    class MyException(Exception):
        pass

    msg = "A test exception"
    value = json.dumps(
        {
            "__exception_class_name__": MyException.__name__,
            "__msg__": msg,
            "__traceback__": None,
        }
    )

    result = client_json.AliasClientJSON.loads(value)

    assert isinstance(result, Exception)
    assert result.__class__.__name__ == MyException.__name__
    assert str(result) == msg


def test_json_decode_alias_module():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__module_name__": "alias_api",
        "__members__": [],
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientModuleProxyWrapper)
    assert result.module == result
    assert result.data == data


def test_json_decode_alias_property():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__property_name__": None,
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientPropertyProxyWrapper)
    assert result.data == data


def test_json_decode_alias_class():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__module_name__": "alias_api",
        "__class_name__": "my_class",
        "__members__": [],
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientClassProxyWrapper)
    assert result.data == data


def test_json_decode_alias_function():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__function_name__": "my_func",
        "__is_method__": False,
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientFunctionProxyWrapper)
    assert result.data == data


def test_json_decode_alias_enum():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__class_name__": "some_enum_class",
        "__enum_name__": "some_enum",
        "__enum_value__": 2,
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientEnumProxyWrapper)
    assert result.data == data


def test_json_decode_alias_object():
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    import alias_api_om

    proxy_wrapper.AliasClientObjectProxyWrapper.store_module("alias_api", alias_api_om)

    data = {
        "__module_name__": "alias_api",
        "__class_name__": "AlObjectType",
        "__instance_id__": 28,
    }
    json_data = json.dumps(data)

    result = client_json.AliasClientJSON.loads(json_data)

    assert isinstance(result, proxy_wrapper.AliasClientObjectProxy)
    assert result.__class__.__name__ == "AlObjectType"
    assert result.data == data
    assert result.unique_id == 28
