import json
from contextlib import contextmanager
from ckan.plugins.toolkit import (abort, get_action)
from ckanext.datastore import helpers as datastore_helpers

from logging import getLogger

log = getLogger(__name__)

PAGINATE_BY = 32000


def convert_resource_data(resource_id, file_format, context, response, offset, limit, sort, search_params):

    resource_metadata = get_action('resource_show')(context, {'id': resource_id})

    # get datastore info
    datastore_info = datastore_helpers.datastore_dictionary(resource_id)
    records_format =  u'lists'

    def result_page(offs, lim):
        return get_action(u'datastore_search')(
            None,
            dict({
                u'resource_id': resource_id,
                u'limit': PAGINATE_BY
                if limit is None else min(PAGINATE_BY, lim),
                u'offset': offs,
                u'sort': sort,
                u'records_format': records_format,
                u'include_total': False,
            }, **search_params)
        )

    result = result_page(offset, limit)

    if result[u'limit'] != limit:
        # `limit` (from PAGINATE_BY) must have been more than
        # ckan.datastore.search.rows_max, so datastore_search responded with a
        # limit matching ckan.datastore.search.rows_max. So we need to paginate
        # by that amount instead, otherwise we'll have gaps in the records.
        paginate_by = result[u'limit']
    else:
        paginate_by = PAGINATE_BY

    if file_format == 'rdf_segittur':
        rdf_writer = rdf_segittur_writer
    else:
        abort(404, _(u'RDF format unknown'))

    with rdf_writer(result[u'fields'], resource_metadata, datastore_info, response) as wr:
        while True:
            if limit is not None and limit <= 0:
                break
            records = result[u'records']

            wr.write_records(records)

            if len(records) < paginate_by:
                break

            offset += paginate_by
            if limit is not None:
                limit -= paginate_by
                if limit <= 0:
                    break

            result = result_page(offset, limit)


@contextmanager
def rdf_segittur_writer(fields, resource_metadata, datastore_info, response):

    header = [  "@prefix skos: <http://www.w3.org/2008/05/skos#> .",
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
                "@prefix turismo: <https://ontologia.segittur.es/turismo/modelo-v1-0-0.owl#> .",
                "@prefix hotel: <https://tdata.dlsi.ua.es/recurso/turismo/hotel#> .",
                "@prefix tc: <https://tdata.dlsi.ua.es/recurso/turismo/temporaryClosure#> .",
                "@prefix accoCap: <https://tdata.dlsi.ua.es/recurso/turismo/accommodationCapacity#> .",
                "@prefix location: <https://tdata.dlsi.ua.es/recurso/turismo/location#> ."]

    response.stream.write("\n".join(header) + "\n\n")

    # build ontology based dictionary
    ontology_dict = {}
    for field in datastore_info:
        if len(field.get('info', {}).get('ontology', '')) > 0:
            try:
                ontology_infos = json.loads(field.get('info', {}).get('ontology', '').replace("'", '"'))
                field_name = field['id']
                for info in ontology_infos:
                    ontology  = info.get('ontology')
                    predicate  = info.get('predicate')
                    if ontology=='segittur_rdf' and predicate:
                        ontology_dict[predicate] = {'id': field_name, 'info': info}

            except Exception as e:
                log.warn("WARN: could not parse JSON from ontology info on field data: " + str(field) + "\n" + str(e))

    yield RDFSegitturWriter(response.stream, [f[u'id'] for f in fields], ontology_dict, resource_metadata)


class RDFSegitturWriter(object):

    def __init__(self, response, columns, ontology_dict, resource_metadata):
        self.response = response
        self.columns = columns
        self.ontology_dict = ontology_dict
        self.resource_metadata = resource_metadata

    def _record_to_dict(self, record):
        record_dict = {}
        index = 0
        for column in self.columns:
            record_dict[column] =  record[index]
            index += 1
        return record_dict

    def _transform_value(self, value, function):
        if not function:
            if value:
                return value.strip()
            else:
                return value
        elif function == 'str_to_id':
            return(value.upper().strip().replace(' ', '_'))
        elif function == 'cast_to_int':
            return (int(value.strip()))
        else:
            raise Exception("Not implemented: " + str(function))

    def _record_to_turtle(self, record):
        turtle = ""

        # identifier (MANDATORY)
        if self.ontology_dict.get("turismo:Hotel"):
            id_field = self.ontology_dict.get("turismo:Hotel")['id']
            function = self.ontology_dict.get("turismo:Hotel")['info'].get('function')
            value = str(record['_id']) + '_' + self._transform_value(record[id_field], function)
            turtle += "hotel:" + value + " a turismo:Hotel;\n"
        # elif with other ids
        else:
            # fail
            return None

        # hotel stars name
        for tag in ["turismo:stars", "turismo:name", "skos:prefLabel"]:
            if self.ontology_dict.get(tag):
                id_field = self.ontology_dict.get(tag)['id']
                function = self.ontology_dict.get(tag)['info'].get('function')
                value = self._transform_value(record[id_field], function)
                if  isinstance(value, str):
                    value = '"' + value + '"'
                turtle += '    ' + tag + ' ' + str(value) + ';\n'

        return turtle

    def write_records(self, records):
        for r in records:
            try:
                record = self._record_to_dict(r)
                turtle_text = self._record_to_turtle(record)
                if turtle_text:
                    self.response.write(turtle_text)
                    self.response.write(b'\n')
            except Exception as e:
                log.warn("Error converting record id " + str(record.get('_id', '??')) + ", Exception: " + str(e))
