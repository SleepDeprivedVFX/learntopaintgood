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
import socket

from tk_framework_alias.server import alias_bridge
from tk_framework_alias.server.api import alias_api
from tk_framework_alias.server.socketio.namespaces import (
    events_namespace,
    server_namespace,
)
from tk_framework_alias.server.utils import exceptions


####################################################################################################
# fixtures
####################################################################################################


@pytest.fixture()
def bridge():
    """Fixture to return an instance of the AliasClientJSONEncoder class."""

    # Create the bridge
    bridge = alias_bridge.AliasBridge()

    # Yield to let the test run
    yield bridge

    # Tear down after test has finished
    bridge.stop_server()


@pytest.fixture()
def sock():
    """
    Fixture to return a socket binded and listening on a host and port.

    This fixture helps test resiliency of the Alias server to connect when the host and port
    are already in use by this socket.
    """

    # Set up the socket to bind to the host and port
    host = "127.0.0.1"
    port = 6789
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(1)

    yield sock

    # Tear down
    sock.close()


@pytest.fixture()
def client(client_exe_path):
    """Fixture to return a dictionary containing client data."""

    return {
        "name": "test_client",
        "exe_path": client_exe_path,
        "info": {
            "intarg": 1,
            "list_arg": [1, 2, 3],
            "str_arg": "test",
        },
    }


####################################################################################################
# tk_framework_alias alias_bridge.py AliasBridge
####################################################################################################


def test_bridge_singleton():
    """Test the AliasBridge object instantiation."""

    bridge = alias_bridge.AliasBridge()
    another_bridge = alias_bridge.AliasBridge()
    assert bridge == another_bridge


def test_bridge_start_server(bridge):
    """Test the AliasBridge start_server method."""

    success = bridge.start_server()

    assert success
    assert bridge.alias_events_client_sio.connected
    assert len(bridge.alias_events_client_sio.connection_namespaces) == 1
    assert (
        bridge.alias_events_client_sio.connection_namespaces[0]
        == events_namespace.AliasEventsServerNamespace.get_namespace()
    )

    bridge.stop_server()


def test_bridge_start_server_on_address(bridge):
    """Test the AliasBridge start_server method."""

    host = "127.0.0.1"
    port = 8383
    success = bridge.start_server(host, port)

    assert success
    assert bridge.alias_events_client_sio.connected
    assert len(bridge.alias_events_client_sio.connection_namespaces) == 1
    assert (
        bridge.alias_events_client_sio.connection_namespaces[0]
        == events_namespace.AliasEventsServerNamespace.get_namespace()
    )

    server_url = f"http://{host}:{port}"
    assert bridge.alias_events_client_sio.connection_url == server_url


def test_bridge_start_server_again(bridge):
    """Test the AliasBridge start_server method."""

    success = bridge.start_server()
    assert success

    second_time_success = bridge.start_server()
    assert second_time_success

    with pytest.raises(exceptions.ServerAlreadyRunning) as error:
        bridge.start_server("new_host", 9999)
        assert str(error).startswith("Server already running on")


def test_bridge_stop_server(bridge):
    """Test the AliasBridge stop_server method."""

    success = bridge.start_server()
    assert success

    # Add instnace to data model registry
    layer = alias_api.create_layer("MyLayer")
    instance_id = bridge.alias_data_model.register_instance(layer)
    assert bridge.alias_data_model.get_instance(instance_id)

    # Add event to data model registry
    event_id = alias_api.AlMessageType.StageActive
    callback_id = 1
    bridge.alias_data_model.register_event(event_id, callback_id)
    assert bridge.alias_data_model.get_event_callbacks(event_id)

    bridge.stop_server()
    assert not bridge.alias_events_client_sio.connected

    # Ensure data model was destroyed
    assert not bridge.alias_data_model.get_instance(instance_id)
    assert not bridge.alias_data_model.get_event_callbacks(event_id)

    # Test reconnecting to a different port
    new_port = 7777
    success = bridge.start_server(port=new_port)
    assert success
    server_url = f"http://127.0.0.1:{new_port}"
    assert bridge.alias_events_client_sio.connection_url == server_url


def test_bridge_address_in_use(bridge, sock):
    """
    Test the AliasBridge to start the server.

    Test when the address is already in use, server should retry to then connect to the next
    available port.
    """

    # Get the host and port that is already in use.
    host, port = sock.getsockname()

    # Default max_retries should at least be 1
    success = bridge.start_server(host=host, port=port)
    assert success

    expected_port = port + 1
    server_url = f"http://{host}:{expected_port}"
    assert bridge.alias_events_client_sio.connection_url == server_url


def test_bridge_address_in_use_no_retry(bridge, sock):
    """
    Test the AliasBridge to start the server.

    Test when the address is already in use and no retries allowed.
    """

    # Get the host and port that is already in use.
    host, port = sock.getsockname()

    with pytest.raises(exceptions.AliasBridgeException) as connection_error:
        bridge.start_server(host=host, port=port, max_retries=0)
        assert str(connection_error) == "Failed to open server socket."


def test_bridge_register_client_namespace_reservered(bridge):
    """
    Test the AliasBridge register_client_namespace method.

    Should raise and error when attempting to use a reserved name.
    """

    reserved_client_name = "events"

    with pytest.raises(exceptions.ClientNameReservered) as client_error:
        bridge.register_client_namespace(reserved_client_name, "/path", {})
        assert (
            str(client_error)
            == "Client name 'events' is reserved. Use a different name."
        )


def test_bridge_register_client_namespace(bridge):
    """Test the AliasBridge register_client_namespace method."""

    name = "my_client"
    exe_path = "/a/path/to/client.exe"
    info = {"test_info": "text", "other_data": [1, 2, 3]}

    client = bridge.register_client_namespace(name, exe_path, info)
    assert client["name"] == name
    assert client["exe_path"] == exe_path
    assert client["info"] == info
    assert client["namespace"] == f"/alias-{name}"

    namespace_by_client = bridge.get_client_by_namespace(client["namespace"])
    assert client == namespace_by_client


def test_bridge_get_client_by_namespace_not_exist(bridge):
    """Test the AliasBridge register_client_namespace method."""

    client = bridge.get_client_by_namespace("bad_namespace")
    assert client == {}


def test_bridge_register_client_namespace_already_registered(bridge):
    """
    Test the AliasBridge register_client_namespace method.

    Should raise and error when attempting to register a client that has already been
    registered.
    """

    name = "my_client"
    exe_path = "/a/path/to/client.exe"
    info = {"test_info": "text", "other_data": [1, 2, 3]}

    bridge.register_client_namespace(name, exe_path, info)
    with pytest.raises(exceptions.ClientAlreadyRegistered):
        bridge.register_client_namespace(name, exe_path, info)


def test_bridge_bootstrap_client_server_not_ready(bridge):
    """Test the AliasBridge bootstrap_client method."""

    success = bridge.bootstrap_client("bad_client", "/path/client.exe")
    assert not success


def test_bridge_bootstrap_client(bridge, client):
    """Test the AliasBridge bootstrap_client method."""

    name = client["name"]
    exe_path = client["exe_path"]
    info = client["info"]

    # First the server needs to be running to bootstrap the client
    bridge.start_server()

    # Run the client bootstrap. This will register the a namespace for this client to use.
    success = bridge.bootstrap_client(name, exe_path, info)
    assert success

    # Get the namespace handler registered for this client. We will use the handler to check
    # if the client successfully bootstrapped and connected to the server.
    ns = f"/alias-{name}"
    ns_handler = bridge.sio.namespace_handlers.get(ns)
    assert ns_handler
    assert isinstance(ns_handler, server_namespace.AliasServerNamespace)

    # There should be no clients connected yet
    assert ns_handler.client_sid is None

    # Wait for client to connect. Try up to 30 times, waiting a second each time.
    count = 0
    max_retries = 30
    while not ns_handler.client_sid and count < max_retries:
        bridge.sio.sleep(1)
        count += 1

    # Now we should have a single client connected from running the bootstrap.
    assert ns_handler.client_sid is not None
