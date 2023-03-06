
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
        translated_field = field.get(lang_code, None)
        if not translated_field:
            translated_field = field.get(default_lang, None)
        if translated_field is not None:
            return translated_field
    return field


def wakeua_get_translated(data_dict, field):
    if isinstance(data_dict.get(field, ""), dict) or isinstance(data_dict.get(field, []), str):
        return wakeua_force_translate(data_dict.get(field, ""))
    else:
        return h.get_translated(data_dict, field)


def wakeua_force_translate(text):
    return wakeua_extract_lang_value(to_json_dict_safe(text))


def wakeua_markdown_extract(text, extract_length=190):
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


def wakeua_list_dict_filter(list_, search_field, output_field, value):
    print("** wakeua_list_dict_filter", list_, search_field, output_field, value)
    for item in list_:
        if item.get(search_field) == value:
            output_value = wakeua_force_translate(item.get(output_field, value))
            if output_value == item.get(output_field):
                if output_value.rsplit('-', 1)[-1] in config.get('ckan.locale_order', ["es"]):
                    output_value = wakeua_tag_display_name(output_value)
            return output_value
    if len(list_) == 0 and value.rsplit('-', 1)[-1] in config.get('ckan.locale_order', ["es"]):
        return value.rsplit('-', 1)[0]
    return value


def wakeua_render_markdown(data, auto_link=True, allow_html=False):
    if not data:
        return ''
    if isinstance(data, dict):
        return h.render_markdown(wakeua_extract_lang_value(data), auto_link, allow_html)
    else:
        return h.render_markdown(data, auto_link, allow_html)


def wakeua_tag_display_name(name):
    return name.rsplit('-', 1)[0]


def wakeua_extract_tags(tags):
    langs = config.get('ckan.locale_order') or ["es"]

    # get all languages tags
    new_tags = [tag for tag in tags if tag.get("name", "").rsplit('-', 1)[-1] not in langs]

    # get translated tags
    lang_code = toolkit.request.environ['CKAN_LANG']
    suffix = "-" + lang_code
    sel_tags = [tag for tag in tags if tag.get("name", "").endswith(suffix)] # translated tag

    for tag in sel_tags:
        tag["display_name"] = wakeua_tag_display_name(tag["name"])
        new_tags += [tag]

    return new_tags


def wakeua_get_facet_items_dict(facet, search_facets=None, limit=None, exclude_active=False):
    facet_items_dict = h.get_facet_items_dict(facet, search_facets, limit, exclude_active)
    if facet in ["tags", "schemaorg_tags"]:
        return wakeua_extract_tags(facet_items_dict)
    return facet_items_dict


def wakeua_get_vocabulary_tags(vocabulary):
    try:
        vocabulary_codes = toolkit.get_action('tag_list')(
                data_dict={'vocabulary_id': vocabulary})
        return vocabulary_codes
    except toolkit.ObjectNotFound:
        return None


def wakeua_show_dataset_vocabulary_tags(data):
    tags = []

    for tag_string in data.split(','):
        if tag_string.rsplit('-',1)[-1] == toolkit.request.environ['CKAN_LANG']:
            new_tag = {"name": tag_string, "display_name": tag_string.rsplit('-', 1)[0]}
            tags += [new_tag]
    print("wakeua_show_dataset_vocabulary_tags DATA", data, tags)
    return tags
