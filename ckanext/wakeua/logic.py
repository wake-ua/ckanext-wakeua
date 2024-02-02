import json
from contextlib import contextmanager
from ckan.plugins.toolkit import (abort, get_action)
from ckanext.datastore import helpers as datastore_helpers

from rdflib import Graph, Literal, RDF, URIRef, BNode
from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS

from logging import getLogger

log = getLogger(__name__)

PAGINATE_BY = 32000

# Create an RDF URI node to use as the subject for multiple triples
TURISMO = Namespace("https://ontologia.segittur.es/turismo/modelo-v1-0-0.owl#")
HOTEL = Namespace("https://tdata.dlsi.ua.es/recurso/turismo/hotel#")
ACCO_CAP = Namespace("https://tdata.dlsi.ua.es/recurso/turismo/accommodationCapacity#")
LOCATION = Namespace("https://tdata.dlsi.ua.es/recurso/turismo/location#")


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

    g.bind("skos", SKOS)
    g.bind("turismo", TURISMO)
    g.bind("hotel", HOTEL)
    g.bind("acco_cap", ACCO_CAP)
    g.bind("location", LOCATION)

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

    yield RDFSegitturWriter(response.stream, [f[u'id'] for f in fields], ontology_dict, resource_metadata, package_metadata, g)


class RDFSegitturWriter(object):

    def __init__(self, stream, columns, ontology_dict, resource_metadata, package_metadata, graph):
        self.stream = stream
        self.columns = columns
        self.ontology_dict = ontology_dict
        self.resource_metadata = resource_metadata
        self.package_metadata = package_metadata
        self.graph = graph

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
            try:
                transformed_value = int(value.strip())
                return transformed_value
            except ValueError as v:
                log.warn('Could not convert value to int: "' + str(value.strip()) + '" Exception: ' + str (v))
                return None
        elif function == 'match_hotel_speciality':
            value_fix = ' '.join([t for t in value.strip().lower().split(' ') if t])
            if value_fix in ['rural', 'casa rural']:
                return TURISMO.ruralHotel
            return None
        else:
            raise Exception("Not implemented: " + str(function))

    def _get_tag(self, tag, record):
        if self.ontology_dict.get(tag):
            field = self.ontology_dict.get(tag)['id']
            function = self.ontology_dict.get(tag)['info'].get('function')
            value = self._transform_value(record[field], function)
            if value is not None:
                return value
        return None

    def _add_record_to_graph(self, record):

        identifier = None
        hotel = None

        # identifier (MANDATORY)
        if self.ontology_dict.get("turismo:Hotel"):
            id_field = self.ontology_dict.get("turismo:Hotel")['id']
            function = self.ontology_dict.get("turismo:Hotel")['info'].get('function')
            value = str(record['_id']) + '_' + self._transform_value(record[id_field], function)
            identifier = value

            # generate hotel:6_CV_H00108_A a turismo:Hotel;
            hotel = URIRef(HOTEL[identifier])
            self.graph.add((hotel, RDF.type, TURISMO.Hotel))

        # elif with other ids
        else:
            # fail
            return None

        # hotel stars name
        ref_base_predicates =  {"turismo:stars": TURISMO.stars,
                                "turismo:name": TURISMO.name,
                                "skos:prefLabel": SKOS.prefLabel,
                                "turismo:hotelSpecialty": TURISMO.hotelSpecialty}

        for tag, rdf_predicate in ref_base_predicates.items():
            rdf_value = self._get_tag(tag, record)
            if rdf_value is not None:
                if type(rdf_value) in [str, int, float, bool]:
                    self.graph.add((hotel, rdf_predicate, Literal(rdf_value)))
                else:
                    self.graph.add((hotel, rdf_predicate, rdf_value))

        # accomodation capacity
        max_capacity = self._get_tag("turismo:maximumCapacity", record)
        num_rooms = self._get_tag("turismo:numberOfRooms", record)
        if max_capacity or num_rooms:
            accoCap = URIRef(ACCO_CAP[identifier])
            self.graph.add((hotel, TURISMO.accommodationCapacity, accoCap))
            self.graph.add((accoCap, RDF.type, TURISMO.AccommodationCapacity))
            if max_capacity:
                self.graph.add((accoCap, TURISMO.maximumCapacity, Literal(max_capacity)))
            if num_rooms:
                self.graph.add((accoCap, TURISMO.numberOfRooms, Literal(num_rooms)))

        # location
        # TODO turismo:province <http://datos.gob.es/recurso/sector-publico/territorio/Provincia/Alicante>;
        #  #OJO, range es xsd:String

        location = URIRef(LOCATION[identifier])
        self.graph.add((hotel, TURISMO.hasLocation, location))
        self.graph.add((location, RDF.type, TURISMO.Location))
        self.graph.add((location, TURISMO.country, Literal("España")))

        aut_community = None
        org_ac_dict = {c: "Comunitat Valenciana" for c in ['gva', 'alcoi', 'torrent', 'sagunto', 'valencia', 'dipcas']}
        if self.package_metadata['organization']['name'] in org_ac_dict.keys():
            aut_community = org_ac_dict[self.package_metadata['organization']['name']]
        if aut_community:
            self.graph.add((location, TURISMO.autonomousCommunity, Literal(aut_community)))

        ref_location_predicates = {"turismo:city": TURISMO.city,
                                   "turismo:county": TURISMO.county,
                                   "turismo:postalCode": TURISMO.postalCode,
                                   "turismo:streetAddress": TURISMO.streetAddress,
                                   "turismo:province": TURISMO.province,
                                   }

        for tag, rdf_predicate in ref_location_predicates.items():
            rdf_value = self._get_tag(tag, record)
            if rdf_value:
                self.graph.add((location, rdf_predicate, Literal(rdf_value)))

        return

    def write_records(self, records):
        # TODO Write record-by-record to RDF (write header an footer outside of this function)
        count = 0
        for r in records:
            try:
                record = self._record_to_dict(r)
                self._add_record_to_graph(record)
                count += 1

            except Exception as e:
                log.warn("Error converting #" + str(count)+ " record with id " + str(record.get('_id', '??'))
                         + ", Exception: " + str(e))
        self.stream.write(self.graph.serialize(format='ttl'))
