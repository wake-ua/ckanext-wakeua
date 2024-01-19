from ckan.logic import side_effect_free, get_or_bust
import ckanext.datastore.backend as datastore_backend
import ckan.plugins.toolkit as toolkit
from ckanext.wakeua import logic as logic


@side_effect_free
def list_datastore_resources(context, data_dict):
    resource_ids = datastore_backend.get_all_resources_ids_in_datastore()
    return resource_ids
