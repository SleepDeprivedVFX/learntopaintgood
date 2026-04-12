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
import json

from .proxy_wrapper import AliasClientObjectProxyWrapper
from ..utils.exceptions import AliasClientJSONEncoderError


class AliasClientJSON:
    """A custom json module to handle serializing data for an Alias socketio client."""

    @staticmethod
    def encoder_class():
        """Return the encoder class used by this JSON module."""
        return AliasClientJSONEncoder

    @staticmethod
    def decoder_class():
        """Return the decoder class used by this JSON module."""
        return AliasClientJSONDecoder

    @staticmethod
    def dumps(obj, *args, **kwargs):
        """Serialize obj to a JSON formatted str."""
        return json.dumps(obj, cls=AliasClientJSON.encoder_class(), *args, **kwargs)

    @staticmethod
    def loads(obj, *args, **kwargs):
        """Deserialize obj instance containing a JSON document to a Python object."""
        return json.loads(obj, cls=AliasClientJSON.decoder_class(), *args, **kwargs)


class AliasClientJSONEncoder(json.JSONEncoder):
    """A custom encoder for an Alias socketio client to send data to the Alias server."""

    def __init__(self, *args, **kwargs):
        """Initialize the encoder."""

        super(AliasClientJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        """Return a serializable object for obj."""

        if isinstance(obj, AliasClientObjectProxyWrapper):
            return obj.sanitize()

        if isinstance(obj, set):
            return {
                "__type__": "set",
                "__value__": list(obj),
            }

        if inspect.isclass(obj):
            return {"__class_name__": obj.__name__}

        if inspect.isfunction(obj) or inspect.ismethod(obj):
            # Functions must be registered in the AliasSocketIoClient. Since the client io
            # cannot be accessed here, functions must be encoded before getting to this stage.
            raise AliasClientJSONEncoderError("Functions should already be encoded.")

        return super(AliasClientJSONEncoder, self).default(obj)


class AliasClientJSONDecoder(json.JSONDecoder):
    """A custom decoder for an Alias socketio client to recieve data from the Alias server."""

    def __init__(self, *args, **kwargs):
        """Initialize the decoder."""

        super(AliasClientJSONDecoder, self).__init__(
            object_hook=self.object_hook, *args, **kwargs
        )

    def object_hook(self, obj):
        """Decode the JSON serialized object obj to a Python object."""

        if isinstance(obj, dict):
            if "__exception_class_name__" in obj:
                # Deserialize an error returned by the server
                exception_class_name = obj["__exception_class_name__"]
                exception_class = type(exception_class_name, (Exception,), {})
                exception_instance = exception_class(
                    obj.get("__msg__", "Alias Python API error")
                )
                return exception_instance

            if obj.get("__type__") == "set":
                # Deserialize a set object
                return set(obj.get("__value__"))

        # Attempt to deserialize the object into an Alias object proxy wrapper
        proxy_obj = AliasClientObjectProxyWrapper.create_proxy(obj)
        if proxy_obj is not None:
            return proxy_obj

        # Return the object as is.
        return obj
