
def convert_resource_data(format, resource_metadata, datastore_info):

    if format == 'rdf_segittur':
        return convert_segittur(format, resource_metadata, datastore_info)
    else:
        return None


def convert_segittur(format, resource_metadata, datastore_info):
    rdf_content = ""

    header = [  "@prefix skos: <http://www.w3.org/2008/05/skos#> .",
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
                "@prefix turismo: <https://ontologia.segittur.es/turismo/modelo-v1-0-0.owl#> .",
                "@prefix hotel: <https://tdata.dlsi.ua.es/recurso/turismo/hotel#> .",
                "@prefix tc: <https://tdata.dlsi.ua.es/recurso/turismo/temporaryClosure#> .",
                "@prefix accoCap: <https://tdata.dlsi.ua.es/recurso/turismo/accommodationCapacity#> .",
                "@prefix location: <https://tdata.dlsi.ua.es/recurso/turismo/location#> ."]

    rdf_content += "\n".join(header) + "\n\n"

    return rdf_content