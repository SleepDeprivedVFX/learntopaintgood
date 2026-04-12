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

from tk_framework_alias.server.socketio.data_model import AliasDataModel
from tk_framework_alias.server.api import alias_api
from tk_framework_alias.server import alias_bridge
from tk_framework_alias.server.utils.exceptions import AliasApiRequestNotValid


####################################################################################################
# fixtures
####################################################################################################


@pytest.fixture()
def data_model():
    """Fixture to return an instance of the AliasDataModel class."""

    return AliasDataModel()


####################################################################################################
# tk_framework_alias data_model.py AliasDataModel
####################################################################################################


def test_data_model_register_instance(data_model):
    """Test the AliasDataModel register_instance method."""

    shader = alias_api.create_shader()

    shader_id = data_model.register_instance(shader)
    result = data_model.get_instance(shader_id)

    assert result is shader


def test_data_model_unregister_instance(data_model):
    """Test the AliasDataModel unregister_instance method."""

    shader = alias_api.create_shader()

    shader_id = data_model.register_instance(shader)
    result = data_model.get_instance(shader_id)
    assert result is shader

    data_model.unregister_instance(shader_id)
    result = data_model.get_instance(shader_id)
    assert result is None


def test_data_model_register_event(data_model):
    """Test the AliasDataModel register_instance method."""

    event_id = alias_api.AlMessageType.StageActive
    callback_id = 1

    data_model.destroy()
    data_model.register_event(event_id, callback_id)

    callbacks = data_model.get_event_callbacks(event_id)
    assert callbacks == [callback_id]


def test_data_model_unregister_event(data_model):
    """Test the AliasDataModel unregister_instance method."""

    event_id = alias_api.AlMessageType.StageActive
    callback_id = 1

    data_model.destroy()
    data_model.register_event(event_id, callback_id)

    callbacks = data_model.get_event_callbacks(event_id)
    assert callbacks == [callback_id]

    data_model.unregister_event(event_id, callback_id)
    callbacks = data_model.get_event_callbacks(event_id)
    assert callbacks == []


def test_data_model_register_events_many(data_model):
    """Test the AliasDataModel register_instance method."""

    event_1_id = alias_api.AlMessageType.StageActive
    event_2_id = alias_api.AlMessageType.PostRetrieve
    event_3_id = alias_api.AlMessageType.LayerAdded
    callback_1_1_id = 1.0
    callback_1_2_id = 1.1
    callback_2_id = 2.0
    callback_3_1_id = 3.0
    callback_3_2_id = 3.2
    callback_3_3_id = 3.3

    data_model.destroy()

    data_model.register_event(event_1_id, callback_1_1_id)
    data_model.register_event(event_1_id, callback_1_2_id)
    data_model.register_event(event_2_id, callback_2_id)
    data_model.register_event(event_3_id, callback_3_1_id)
    data_model.register_event(event_3_id, callback_3_2_id)
    data_model.register_event(event_3_id, callback_3_3_id)

    callbacks_1 = data_model.get_event_callbacks(event_1_id)
    assert len(callbacks_1) == 2
    assert callback_1_1_id in callbacks_1
    assert callback_1_2_id in callbacks_1

    callbacks_2 = data_model.get_event_callbacks(event_2_id)
    assert len(callbacks_2) == 1
    assert callback_2_id in callbacks_2

    callbacks_3 = data_model.get_event_callbacks(event_3_id)
    assert len(callbacks_3) == 3
    assert callback_3_1_id in callbacks_3
    assert callback_3_2_id in callbacks_3
    assert callback_3_3_id in callbacks_3

    data_model.unregister_event(event_1_id, callback_1_2_id)
    callbacks_1 = data_model.get_event_callbacks(event_1_id)
    assert len(callbacks_1) == 1
    assert callback_1_1_id in callbacks_1
    assert callback_1_2_id not in callbacks_1

    data_model.unregister_event(event_3_id)
    callbacks_3 = data_model.get_event_callbacks(event_3_id)
    assert callbacks_3 is None


def test_data_model_destroy(data_model):
    """Test the AliasDataModel destroy method."""

    instance_ids = []
    for _ in range(5):
        instance = alias_api.create_shader()
        iid = data_model.register_instance(instance)
        instance_ids.append(iid)

    event_1_id = alias_api.AlMessageType.StageActive
    event_2_id = alias_api.AlMessageType.LayerAdded
    callback_ids = []
    for callback_id in range(5):
        data_model.register_event(event_1_id, callback_id)
        data_model.register_event(event_2_id, callback_id)
        callback_ids.append(callback_id)

    data_model.destroy()

    for iid in instance_ids:
        instance = data_model.get_instance(iid)
        assert instance is None

    event_1_callbacks = data_model.get_event_callbacks(event_1_id)
    assert event_1_callbacks is None

    event_2_callbacks = data_model.get_event_callbacks(event_2_id)
    assert event_2_callbacks is None
