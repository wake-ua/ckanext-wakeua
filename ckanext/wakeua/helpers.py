import json
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import ckan.lib.helpers as h


def wakeua_dataset_display_name(package_or_package_dict):

    if isinstance(package_or_package_dict, dict):

        return wakeua_extract_lang_value(package_or_package_dict['title']) or \
            package_or_package_dict['name']
    else:
        # FIXME: we probably shouldn't use the same functions for
        # package dicts and real package objects
        return wakeua_extract_lang_value(package_or_package_dict.title) or package_or_package_dict.name


def wakeua_resource_display_name(resource_dict):
    name = wakeua_get_translated(resource_dict, 'name')
    description = wakeua_get_translated(resource_dict, 'description')
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60
        if len(description) > max_len:
            description = description[:max_len] + '...'
        return description
    else:
        return _("Unnamed resource")


def wakeua_extract_lang_value(field):
    if isinstance(field, dict):
        LANGS = config.get('ckan.locale_order') or ["es"]
        lang_code = toolkit.request.environ['CKAN_LANG']
        default_lang = LANGS.split(' ')[0]

        translated_field = field.get(lang_code, "")
        if not translated_field:
            translated_field = field.get(default_lang, None)
        if translated_field is not None:
            return translated_field
    return field


def wakeua_get_translated(data_dict, field):
    if isinstance(data_dict.get(field, ""), dict):
        return wakeua_extract_lang_value(data_dict.get(field, ""))
    else:
        return h.get_translated(data_dict, field)


def wakeua_force_translate(text):
    return wakeua_extract_lang_value(to_json_dict_safe(text))


def wakeua_markdown_extract(text, extract_length=190):
    ''' return the plain text representation of markdown encoded text.  That
    is the texted without any html tags.  If extract_length is 0 then it
    will not be truncated.'''
    if not text:
        return ''

    if isinstance(text, dict):
        return h.markdown_extract(wakeua_extract_lang_value(text), extract_length)
    else:
        return h.markdown_extract(text, extract_length)


def wakeua_truncate(text, length=30, indicator='...', whole_word=False):
    string_text = wakeua_extract_lang_value(to_json_dict_safe(text))
    return h.truncate(string_text, length, indicator, whole_word)


def to_json_dict_safe(text_input):
    if isinstance(text_input, str):
        if text_input.startswith('{'):
            try:
                json_dict = json.loads(text_input)
            except ValueError as e:
                return text_input
            return json_dict
    return text_input


def wakeua_link_to(label, url, **attrs):
    string_label = wakeua_extract_lang_value(to_json_dict_safe(label))
    return h.link_to(string_label, url, **attrs)
