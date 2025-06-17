from collections.abc import Mapping
from rest_framework.views import exception_handler
from rest_framework import status


def flatten_errors(errors):
    flattened = {}

    for key, value in errors.items():
        if isinstance(value, Mapping):
            print("1")
            flattened[key] = flatten_errors(value)
        elif isinstance(value, list):
            print("2")
            flattened[key] = value[0]
        else:
            print("3")
            flattened[key] = value

    return flattened


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response and response.status_code == status.HTTP_400_BAD_REQUEST:
        response.data = flatten_errors(response.data)

    return response
