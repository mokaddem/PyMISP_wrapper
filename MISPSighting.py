from time import time as now

"""
values can be either one value or a list of values,
type represent the sighting type: 0=Default, 1=False positive
"""

def MISPSighting(values, uuid=None, id=None, source=None, type=0, timestamp=int(now())):
    sighting_dico = {}
    if not isinstance(values, list):
        values = [values]
    sighting_dico['values'] = values
    sighting_dico['timestamp'] = timestamp

    if uuid is not None:
        sighting_dico['uuid'] = uuid
    if id is not None:
        sighting_dico['id'] = id
    if source is not None:
        sighting_dico['source'] = source

    return sighting_dico
