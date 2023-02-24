import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import os
from ckan.lib.webassets_tools import add_public_path
from ckan.lib.plugins import DefaultTranslation
import ckanext.wakeua.blueprints as blueprints
from ckanext.wakeua import validators as v
from ckanext.wakeua import helpers as wh


class WakeuaPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITranslation, inherit=True)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.IGroupController, inherit=True)

    LANGS = config.get('ckan.locale_order') or ["es"]

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public', 'wakeua')

        asset_path = os.path.join(
            os.path.dirname(__file__), 'public'
        )
        add_public_path(asset_path, '/')

    def before_view(self, pkg_dict):

        for key, value in pkg_dict.items():
            if key not in ['spatial']:
                json_value = wh.to_json_dict_safe(value)
                if isinstance(json_value, dict):
                    translated_field = wh.wakeua_extract_lang_value(json_value)
                    if translated_field:
                        pkg_dict[key] = translated_field

        # resources
        for resource in pkg_dict.get('resources', []):
            for key, value in resource.items():
                if key not in ['tracking_summary']:
                    resource[key] = wh.wakeua_extract_lang_value(value)

        return pkg_dict

    # ITranslation
    def i18n_directory(self):
        i18n_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'i18n'
        )
        return i18n_path

    # IBlueprint
    def get_blueprint(self):
        return blueprints.get_blueprints(self.name, self.__module__)

    # IValidators
    def get_validators(self):
        return {
            'wakeua_multilingual_text_output': v.wakeua_multilingual_text_output,
            'wakeua_parse_json': v.wakeua_parse_json,
        }

    # ITemplateHelpers
    def get_helpers(self):
        """
        Provide template helper functions
        """
        return {
            'dataset_display_name': wh.wakeua_dataset_display_name,
            'resource_display_name': wh.wakeua_resource_display_name,
            'get_translated': wh.wakeua_get_translated,
            'wakeua_extract_lang_value': wh.wakeua_extract_lang_value,
            'wakeua_force_translate': wh.wakeua_force_translate,
            'markdown_extract': wh.wakeua_markdown_extract,
            'truncate': wh.wakeua_truncate,
            'link_to': wh.wakeua_link_to,
        }
