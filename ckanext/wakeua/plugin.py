import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import os
from ckan.lib.webassets_tools import add_public_path
from ckan.lib.plugins import DefaultTranslation
import ckanext.wakeua.blueprints as blueprints


class WakeuaPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITranslation, inherit=True)
    plugins.implements(plugins.IBlueprint)


    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public', 'wakeua')

        asset_path = os.path.join(
            os.path.dirname(__file__), 'public'
        )
        add_public_path(asset_path, '/')

    # ITranslation
    def i18n_directory(self):
        i18n_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'i18n'
        )
        return i18n_path

    # IDatasetForm
    def _modify_package_schema(self, schema):
        schema.update({
            'spatial': [toolkit.get_validator('ignore_missing'),
                        toolkit.get_converter('convert_to_extras')
                        ]
        })
        return schema

    def create_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(WakeuaPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(WakeuaPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(WakeuaPlugin, self).show_package_schema()
        schema.update({
            'spatial': [toolkit.get_converter('convert_from_extras'),
                        toolkit.get_validator('ignore_missing')
                        ]
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    # IBlueprint
    def get_blueprint(self):
        return blueprints.get_blueprints(self.name, self.__module__)
