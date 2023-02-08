import ckan.lib.base as base
from flask import Blueprint

def get_blueprints(name, module):
    # Create Blueprint for plugin
    blueprint = Blueprint(name, module)

    blueprint.add_url_rule(
        u"/legal-notice",
        u"legal_notice",
        legal_notice
    )

    return blueprint


def legal_notice():
    return base.render('wakeua/legal_notice.html')