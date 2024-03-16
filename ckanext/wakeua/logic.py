import json
from contextlib import contextmanager
from ckan.plugins.toolkit import (abort, get_action)
from ckanext.datastore import helpers as datastore_helpers

from rdflib import Graph, Literal, RDF, URIRef, BNode
from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS

from unidecode import unidecode
import re

from logging import getLogger

log = getLogger(__name__)

PAGINATE_BY = 32000
PREDICATOR_SEP  = '/'

# Create an RDF URI node to use as the subject for multiple triples
BASEURI = "https://tdata.dlsi.ua.es/recurso/turismo/"

def get_id(ontology_dict):
    id_predicate = None
    prefix = None
    ontology = None
    id_prefix = None
    for k, v in ontology_dict.items():
        if v['info'].get('function') == "str_to_id":
            id_predicate = k[1]
            prefix = v['info'].get('prefix').lower().strip()
            ontology = k[0]
            id_prefix = id_predicate.split(':')[1].lower().strip()

    return id_prefix, id_predicate, prefix, ontology

def convert_resource_data(resource_id, file_format, context, response, offset, limit, sort, search_params):

    resource_metadata = get_action('resource_show')(context, {'id': resource_id})
    package_metadata = get_action('package_show')(context, {'id': resource_metadata['package_id']})

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

    with rdf_writer(result[u'fields'], resource_metadata, package_metadata, datastore_info, response) as wr:
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
def rdf_segittur_writer(fields, resource_metadata, package_metadata, datastore_info, response):
    # Create a Graph
    g = Graph()

    # build ontology based dictionary
    ontology_dict = {}
    for field in datastore_info:
        if len(field.get('info', {}).get('ontology', '')) > 0:
            try:
                ontology_infos = json.loads(field.get('info', {}).get('ontology', '').replace("'", '"'))
                field_name = field['id']
                for info in ontology_infos:
                    ontology = info.get('ontology')
                    predicate = info.get('predicate')
                    prefix = info.get('predicate')
                    if ontology and prefix and predicate:
                        ontology_dict[(ontology, predicate)] = {'id': field_name, 'info': info}

            except Exception as e:
                log.warn("WARN: could not parse JSON from ontology info on field data: " + str(field) + "\n" + str(e))

    prefixes = []
    for key, item in ontology_dict.items():
        prefix = item['info'].get('prefix')
        predicate = item['info'].get('predicate')
        if  prefix and predicate:
            if len(predicate.split(PREDICATOR_SEP)) > 1:
                namespace_uri = BASEURI + prefix + '#'
            else:
                namespace_uri = item['info']['ontology']
            namespace = Namespace(namespace_uri)
            prefixes += [(prefix, Namespace(namespace_uri))]

    id_prefix, id_predicate, prefix, ontology = get_id(ontology_dict)
    prefixes += [(id_prefix, Namespace(BASEURI + id_prefix + '#'))]

    for prefix, namespace in set(prefixes):
        g.bind(prefix, namespace)

    yield RDFSegitturWriter(response.stream, [f[u'id'] for f in fields], ontology_dict, resource_metadata, package_metadata, g)


class RDFSegitturWriter(object):

    def __init__(self, stream, columns, ontology_dict, resource_metadata, package_metadata, graph):
        self.stream = stream
        self.columns = columns
        self.ontology_dict = ontology_dict
        self.resource_metadata = resource_metadata
        self.package_metadata = package_metadata
        self.graph = graph
        self.namespaces_dict = {p: Namespace(n) for p,n in self.graph.namespaces()}

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
            norm_value = re.sub('[^A-Za-z0-9_\-]+', '', unidecode(value.strip().replace(' ', '_')))
            return(norm_value.upper())
        elif function == 'cast_to_int':
            try:
                transformed_value = int(value.strip())
                return transformed_value
            except ValueError as v:
                log.warn('Could not convert value to int (retrying float): "' + str(value.strip()) + '" Exception: ' + str (v))
                try:
                    transformed_value = float(value.strip())
                    return round(transformed_value)
                except ValueError as v:
                    log.warn('Could not convert value to int or float: "' + str(value.strip()) + '" Exception: ' + str(v))
                    return None
        elif function == 'stars_to_int':
            try:
                text_value = (value.upper().split(' ESTRELLA')[0].strip())
                stars_count = ['UNA', 'DOS', 'TRES', 'CUATRO', 'CINCO']
                stars_map_dict = {k: stars_count.index(k)+1 for k in stars_count}
                return stars_map_dict[text_value]
            except Exception as v:
                try:
                    text_value = value.strip().lower().replace('e', '')
                    transformed_value = int(text_value)
                    return transformed_value
                except ValueError as v:
                    log.warn('Could not convert stars to int: "' + str(value.strip()) + '" Exception: ' + str(v))
                    return None
        elif function == 'str_to_coordinate_1' or function == 'str_to_coordinate_2':
            try:
                values = [float(v.strip()) for v in value.split(',')]
                if function == 'str_to_coordinate_1':
                    return values[0]
                else:
                    return values[1]
            except ValueError as v:
                log.warn('Could not convert value to float: "' + str(value.strip()) + '" Exception: ' + str(v))
                return None
        elif function == 'match_hotel_speciality':
            value_fix = ' '.join([t for t in value.strip().lower().split(' ') if t])
            if value_fix in ['rural', 'casa rural']:
                return self.namespaces_dict['turismo']['ruralHotel']
            return None
        else:
            raise Exception("Not implemented: " + str(function))

    def _get_tag(self, ontology, tag, record):
        key = (ontology, tag)
        if self.ontology_dict.get(key):
            field = self.ontology_dict.get(key)['id']
            function = self.ontology_dict.get(key)['info'].get('function')
            value = self._transform_value(record[field], function)
            if value is not None:
                return value
        return None

    def _add_record_to_graph(self, record, count):

        identifier = None
        entity = None

        # identifier (MANDATORY)
        entity_name, id_predicate, id_prefix, id_ontology = get_id(self.ontology_dict)
        if id_predicate:
            id_field = self.ontology_dict.get((id_ontology, id_predicate))['id']
            function = self.ontology_dict.get((id_ontology, id_predicate))['info'].get('function')
            identifier = str(count + 1) + '_' + self._transform_value(record[id_field], function)

            # generate hotel:6_CV_H00108_A a turismo:Hotel;
            namespace_id = self.namespaces_dict[entity_name]
            namespace_parent = self.namespaces_dict[id_prefix]
            entity = URIRef(namespace_id[identifier])
            self.graph.add((entity, RDF.type, namespace_parent[id_predicate.split(":")[1].strip()]))

        else:
            # fail
            log.warn("No ontology id predicate defined")
            return None

        # default add location
        location = URIRef(self.namespaces_dict['location'][identifier])
        self.graph.add((entity, self.namespaces_dict['turismo']['hasLocation'], location))
        self.graph.add((location, RDF.type, self.namespaces_dict['turismo']['Location']))
        self.graph.add((location, self.namespaces_dict['turismo']['country'], Literal("España")))
        aut_community = None
        org_ac_dict = {c: "Comunitat Valenciana" for c in ['gva', 'alcoi', 'torrent', 'sagunto', 'valencia', 'dipcas']}
        organization = self.package_metadata['organization']['name']
        if organization in org_ac_dict.keys():
            aut_community = org_ac_dict[organization]
        if aut_community:
            self.graph.add((location, self.namespaces_dict['turismo']['autonomousCommunity'], Literal(aut_community)))
        province_dict = {'alcoi': 'Alicante', 'torrent': 'Valencia', 'sagunto': 'Valencia',
                         'valencia': 'Valencia', 'dipcas': 'Castellon'}
        if organization in province_dict.keys():
            province = province_dict[organization]
            if province:
                self.graph.add((location, self.namespaces_dict['turismo']['province'], Literal(province)))
        city_dict = {'alcoi': 'Alcoi', 'torrent': 'Torrent', 'sagunto': 'Sagunto'}
        if organization in city_dict.keys():
            city = city_dict[organization]
            if province:
                self.graph.add((location, self.namespaces_dict['turismo']['city'], Literal(city)))

        # get other rfd predicates
        for k, v in self.ontology_dict.items():
            ontology, predicate = k
            if ontology != id_ontology or predicate != id_predicate:
                #TODO MAke this work for arbitrary parent levels
                if len(predicate.split(PREDICATOR_SEP)) == 3:
                    predicate_list = predicate.split('/')
                    parent_name = v['info']['prefix']
                    verb = predicate_list[0].split(':')
                    parent = predicate_list[1].split(':')
                    parent_entity = URIRef(self.namespaces_dict[parent_name][identifier])
                    child_predicate = predicate_list[2]
                elif len(predicate.split(PREDICATOR_SEP)) == 1:
                    parent = None
                    parent_entity = entity
                    child_predicate = predicate
                else:
                    log.warn("Possibly wrong predicate " + predicate)
                    continue

                child = child_predicate.split(':')

                rdf_value = self._get_tag(ontology, predicate, record)
                prefix = v['info']['prefix']

                rdf_predicate = self.namespaces_dict[prefix][child[1].strip()]
                if rdf_value is not None and rdf_value != "":
                    if parent is not None:
                        self.graph.add((entity, self.namespaces_dict[verb[0]][verb[1]], parent_entity))
                        self.graph.add((parent_entity, RDF.type, self.namespaces_dict[parent[0]][parent[1]]))

                    if type(rdf_value) in [str, int, float, bool]:
                        self.graph.add((parent_entity, rdf_predicate, Literal(rdf_value)))
                    else:
                        self.graph.add((parent_entity, rdf_predicate, rdf_value))
        return

    def write_records(self, records):
        # TODO Write record-by-record to RDF (write header an footer outside of this function)
        count = 0
        for r in records:
            try:
                record = self._record_to_dict(r)
                self._add_record_to_graph(record, count)
                count += 1
            except Exception as e:
                log.warn("Error converting #" + str(count)+ " record with id " + str(record.get('_id', '??'))
                         + ", Exception: " + str(e))
        self.stream.write(self.graph.serialize(format='ttl'))
