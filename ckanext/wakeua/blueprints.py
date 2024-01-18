from flask import Blueprint, make_response
import ckan.lib.base as base
import ckan.model as model
import ckan.plugins.toolkit as toolkit

from logging import getLogger

log = getLogger(__name__)


def get_blueprints(name, module):
    # Create Blueprint for plugin
    blueprint = Blueprint(name, module)

    blueprint.add_url_rule(
        u"/legal-notice",
        u"legal_notice",
        legal_notice
    )

    blueprint.add_url_rule(
        u"/dataset/wakeua_export_resource_data/<resource_id>/<file_format>",
        u"wakeua_export_resource_data",
        wakeua_export_resource_data
    )

    return blueprint


def legal_notice():
    return base.render('wakeua/legal_notice.html')

def wakeua_export_resource_data(resource_id, file_format):
    context = {
        'model': model,
        'session': model.Session,
        'user': toolkit.g.user
    }

    content_type = "application/x-turtle" #application/x-turtle

    headers = {u'Content-Disposition': 'attachment; filename=' + resource_id + '_' + file_format + '.rdf',
               u'Content-Type': content_type}

    try:
        converted_resource = toolkit.get_action(
            'wakeua_export_resource_data')(
            context,
            {'id': resource_id, 'file_format': file_format}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset/Resource not found')

    return make_response(converted_resource, 200, headers)

    return