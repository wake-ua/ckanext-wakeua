import json
from ckanext.fluent import validators as vf


def wakeua_multilingual_text_output(value):
    """
    Return stored json representation as a multilingual dict, if
    value is already a dict just pass it through.
    """
    if isinstance(value, dict):
        return value
    return wakeua_parse_json(value)


def wakeua_parse_json(value, default_value=None):
    try:
        return json.loads(value)
    except (ValueError, TypeError, AttributeError):
        if default_value is not None:
            return default_value
        return value


def wakeua_tags_output(value):
    if isinstance(value, list):
        return vf.fluent_tags_output({})
    if isinstance(value, dict):
        return value
    return value
