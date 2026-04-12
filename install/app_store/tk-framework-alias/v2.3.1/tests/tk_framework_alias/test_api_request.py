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

from tk_framework_alias.server.socketio import api_request
from tk_framework_alias.server.api import alias_api
from tk_framework_alias.server import alias_bridge
from tk_framework_alias.server.utils.exceptions import AliasApiRequestNotValid


####################################################################################################
# tk_framework_alias api_request.py AliasApiRequestWrapper
####################################################################################################


def test_api_request_function_validate():
    """Test the AliasApiRequestFunctionWrapper object."""

    func_data = {
        "__function_name__": alias_api.create_shader.__name__,
        "__function_args__": [],
        "__function_kwargs__": {},
    }
    func_wrapper = api_request.AliasApiRequestFunctionWrapper(func_data)

    with pytest.raises(AliasApiRequestNotValid):
        func_wrapper.validate("bad request")

    assert func_wrapper.validate("create_shader")


def test_api_request_function_execute():
    """Test the AliasApiRequestFunctionWrapper object."""

    layer_name = "ExecuteThatFunction"
    func_data = {
        "__function_name__": alias_api.create_layer.__name__,
        "__function_args__": [layer_name],
        "__function_kwargs__": {},
    }
    func_wrapper = api_request.AliasApiRequestFunctionWrapper(func_data)

    with pytest.raises(AliasApiRequestNotValid):
        func_wrapper.execute("bad request")

    result = func_wrapper.execute("create_layer")
    assert isinstance(result, alias_api.AlLayer)
    assert result.name == layer_name


def test_api_request_instance_method_execute():
    """Test the AliasApiRequestFunctionWrapper object."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    layer = alias_api.create_layer("AnotherLayer")
    instance_id = data_model.register_instance(layer)

    func_data = {
        "__function_name__": layer.is_folder.__name__,
        "__function_args__": [],
        "__function_kwargs__": {},
        "__instance_id__": instance_id,
    }
    func_wrapper = api_request.AliasApiRequestFunctionWrapper(func_data)

    result = func_wrapper.execute("is_folder")
    assert not result


def test_api_request_function_new_execute():
    """Test the AliasApiRequestFunctionWrapper object."""

    class_type = alias_api.Stage
    stage_name = "MyStage"
    stage_path = "path/to/my/stage"
    func_data = {
        "__function_name__": "__new__",
        "__function_args__": [class_type, stage_name, stage_path],
        "__function_kwargs__": {},
    }
    func_wrapper = api_request.AliasApiRequestFunctionWrapper(func_data)

    result = func_wrapper.execute("__new__")
    assert isinstance(result, class_type)
    assert result.name == stage_name
    assert result.path == stage_path


def test_api_request_property_getter_validate():
    """Test the AliasApiRequestPropertyGetterWrapper object."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    layer = alias_api.create_layer("LayerToTestGetterValidate")
    instance_id = data_model.register_instance(layer)

    data = {
        "__instance_id__": instance_id,
        "__property_name__": "number",
    }
    wrapper = api_request.AliasApiRequestPropertyGetterWrapper(data)

    with pytest.raises(AliasApiRequestNotValid):
        wrapper.validate("bad property")

    assert wrapper.validate("number")


def test_api_request_property_getter_execute():
    """Test the AliasApiRequestPropertyGetterWrapper object."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    layer = alias_api.create_layer("LayerToTestGetterExec")
    instance_id = data_model.register_instance(layer)

    data = {
        "__instance_id__": instance_id,
        "__property_name__": "number",
    }
    wrapper = api_request.AliasApiRequestPropertyGetterWrapper(data)

    with pytest.raises(AliasApiRequestNotValid):
        wrapper.execute("bad property")

    result = wrapper.execute("number")
    assert result == layer.number


def test_api_request_property_setter_validate():
    """Test the AliasApiRequestPropertyGetterWrapper object."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    layer = alias_api.create_layer("LayerToTestSetterValidate")
    instance_id = data_model.register_instance(layer)
    property_value = True

    data = {
        "__instance_id__": instance_id,
        "__property_name__": "symmetric",
        "__property_value__": property_value,
    }
    wrapper = api_request.AliasApiRequestPropertySetterWrapper(data)

    with pytest.raises(AliasApiRequestNotValid):
        wrapper.validate("bad property")

    assert wrapper.validate("symmetric")


def test_api_request_property_setter_execute():
    """Test the AliasApiRequestPropertyGetterWrapper object."""

    data_model = alias_bridge.AliasBridge().alias_data_model
    layer = alias_api.create_layer("LayerToTestSetterExec")
    layer.symmetric = False
    instance_id = data_model.register_instance(layer)
    new_value = True

    data = {
        "__instance_id__": instance_id,
        "__property_name__": "symmetric",
        "__property_value__": new_value,
    }
    wrapper = api_request.AliasApiRequestPropertySetterWrapper(data)

    with pytest.raises(AliasApiRequestNotValid):
        wrapper.execute("bad property")

    wrapper.execute("symmetric")
    assert layer.symmetric == new_value
