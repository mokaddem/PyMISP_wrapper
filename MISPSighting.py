from time import time as now

"""
values can be either one value or a list of values,
type represent the sighting type: 0=Default, 1=False positive
"""

class MISPSighting:
    def __init__(values, uuid=None, id=None, source=None, type=0, timestamp=int(now())):
        self.sighting_dico = {}
        if not isinstance(values, list):
            values = [values]
        self.sighting_dico['values'] = values
        self.sighting_dico['timestamp'] = timestamp
    
        if uuid is not None:
            self.sighting_dico['uuid'] = uuid
        if id is not None:
            self.sighting_dico['id'] = id
        if source is not None:
            self.sighting_dico['source'] = source
    
    def get_dico(self):
        return self.sighting_dico
