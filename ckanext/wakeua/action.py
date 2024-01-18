from ckan.logic import side_effect_free, get_or_bust
import ckanext.datastore.backend as datastore_backend
import ckan.plugins.toolkit as toolkit
from ckanext.wakeua import logic as logic


@side_effect_free
def list_datastore_resources(context, data_dict):
    resource_ids = datastore_backend.get_all_resources_ids_in_datastore()
    return resource_ids


@side_effect_free
def export_resource_data(context, data_dict):
    """Return the given CKAN resource data converted to a format.

    :param id: the ID of the resource
    :format id: string

    :returns: the package data converted to the desired format
    :rtype: string
    """
    return _export(context, data_dict)


def _export(context, data_dict):

    resource_id = get_or_bust(data_dict, 'id')

    resource_metadata = toolkit.get_action('resource_show')(context, {'id': resource_id})
    (toolkit.check_access('datastore_info', context, data_dict))

    format = data_dict.get("format", "rdf_segittur")

    # TODO get datastore info - action
    datastore_info = toolkit.get_action('datastore_info')(context, data_dict)

    converted_resource = logic.convert_resource_data(format, resource_metadata, datastore_info)

    return converted_resource

