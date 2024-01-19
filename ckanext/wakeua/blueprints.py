from flask import Blueprint, make_response
from ckan.plugins.toolkit import (request, abort, ObjectNotFound)
import ckan.lib.base as base
import ckan.model as model
import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as dict_fns
from ckanext.datastore.blueprint import dump_schema
from ckanext.wakeua.logic import convert_resource_data

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

    data, errors = dict_fns.validate(request.args.to_dict(), dump_schema())

    if errors:
        abort(
            400, u'\n'.join(
                u'{0}: {1}'.format(k, u' '.join(e)) for k, e in errors.items()
            )
        )

    context = {
        'model': model,
        'session': model.Session,
        'user': toolkit.g.user
    }

    response = make_response()
    response.headers[u'content-type'] = (b'application/x-turtle; charset=utf-8')
    response.headers[u'Content-Disposition'] = 'attachment; filename=' + resource_id + '_' + file_format + '.rdf'

    try:
        convert_resource_data(
            resource_id,
            file_format,
            context,
            response,
            offset=data[u'offset'],
            limit=data.get(u'limit'),
            sort=data[u'sort'],
            search_params={
                k: v
                for k, v in data.items()
                if k in [
                    u'filters', u'q', u'distinct', u'plain', u'language',
                    u'fields'
                ]
            }
        )
    except ObjectNotFound:
        abort(404, _(u'DataStore resource not found'))
    return response
