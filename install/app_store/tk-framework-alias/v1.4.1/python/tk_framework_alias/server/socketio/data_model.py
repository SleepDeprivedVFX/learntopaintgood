# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import threading

from ..api import alias_api

# NOTE do we need to worry about cleaning up the registry in case it gets huge?


class AliasDataModel:
    """
    A class to manage Alias objects created server side and passed to clients.

    The data model is responsible for storing all Alias objects that are created through the
    server api, and providing unique ids for objects such that they can be passed back and
    forth between a client and the server. The Alias objects themselves cannot be passed to
    a client because it is a complex object that is JSON serializable. So to pass an Alias
    object to a client, a unique id is given to the client, which the client can use to make
    subsequent api requests to get data from the object.

    For example:
        - Client makes api request to create an Alias layer
        - Server creates the layer, generates a unique id and stores it in the registry
        - Server returns the unique id for the created layer to the Client
        - Client makes api request to get layer name by passing layer unique id to server
        - Server looks up the layer by id in the registry, makes api request to get the name
        - Server returns the layer name to the Client

    The data model also stores and keeps track of Alias event callbacks. Any time a message
    event is registered to Alias to trigger a Python callback, this event-callback must be
    stored in the registry. This is because callback function objects cannot be passed from
    the client to the server, so to trigger the Python callback on the client-side, the server
    must keep a mapping of callback ids to events, such that it can forward the event to the
    client, which then can execute the desired callback.
    """

    def __init__(self):
        """Initialize the data model."""

        self.__lock = threading.Lock()
        self.__registry = {}
        self.__events_registry = {}

    def destroy(self):
        """
        Destroy the data model. Clear the instance and events registries.

        To ensure events are cleaned up properly, any events in the registry will be removed
        from Alias.
        """

        self.__lock.acquire()
        try:
            # Clear the instance registry
            self.__registry.clear()

            # Remove all callbacks and clear the events registry
            for event in self.__events_registry:
                alias_api.remove_message_handlers(event)
            self.__events_registry.clear()

        finally:
            self.__lock.release()

    def get_instance(self, instance_id):
        """
        Return the instance object for the given id from the registry.

        :param instance_id: The id of the instance to get.
        :type intance_id: int

        :return: The instance.
        :rtype: any
        """

        self.__lock.acquire()
        try:
            return self.__registry.get(instance_id)
        finally:
            self.__lock.release()

    def register_instance(self, instance):
        """
        Store the instance in the registry.

        :param instance: The instance object to register.
        :type instance: any

        :return: The id generated for the instance to register it.
        :rtype: int
        """

        self.__lock.acquire()
        try:
            # NOTE think about the unique id...
            instance_id = id(instance)
            self.__registry[instance_id] = instance
            return instance_id
        finally:
            self.__lock.release()

    def unregister_instance(self, instance_id):
        """
        Remove the instance from the registry.

        :param intance_id: The id of the instance to remove.
        :type instance_id: int
        """

        self.__lock.acquire()
        try:
            del self.__registry[instance_id]
        finally:
            self.__lock.release()

    def get_event_callbacks(self, event_id):
        """
        Return the list of callbacks registered for this event.

        :param event_id: The id of the event to get callbacks for.
        :type event_id: alia_api.AlMessageType

        :return: The callbacks for the event.
        :rtype: List[str]
        """

        self.__lock.acquire()
        try:
            return self.__events_registry.get(event_id)
        finally:
            self.__lock.release()

    def register_event(self, event_id, event_callback_id):
        """
        Store the Alias event callback in the events registry.

        :param event_id: The event to register the callback to.
        :type event_id: alias_api.AlMessageType
        :param event_callback_id: The id for the callback to register.
        :type event_callback_id: str
        """

        self.__lock.acquire()
        try:
            self.__events_registry.setdefault(event_id, []).append(event_callback_id)
        finally:
            self.__lock.release()

    def unregister_event(self, event_id, event_callback_id=None):
        """
        Remove the Alias event callback from the events registry.

        If the callback id is not given, all callbacks will be removed for the event.

        :param event_id: The event that the callback is registered to.
        :type event_id: alias_api.AlMessageType
        :param event_callback_id: The id for the callback to unregister.
        :type event_callback_id: str
        """

        self.__lock.acquire()
        try:
            if event_id not in self.__events_registry:
                # The event does not have any callbacks registered.
                return

            if event_callback_id is None:
                # Remove all callbacks for the event
                del self.__events_registry[event_id]
            else:
                # Remove the specific event callback
                self.__events_registry[event_id].remove(event_callback_id)

        except ValueError:
            # Attempted to remove an event callback that does not exist.
            # should we log a warning?
            pass

        finally:
            self.__lock.release()
