#!/usr/bin/env python3

from pymisp.tools.abstractgenerator import AbstractMISPObjectGenerator
from pymisp import PyMISP

import datetime

class CowrieMispObject(AbstractMISPObjectGenerator):
    def __init__(self, dico_val, **kargs):
        self._dico_val = dico_val
        self.name = "cowrie"

        super(CowrieMispObject, self).__init__('cowrie', **kargs)
        self.generate_attributes()

    def generate_attributes(self):
        skip_list = ['time', 'duration', 'isError', 'ttylog']
        for object_relation, value in self._dico_val.items():
            if object_relation in skip_list or 'log_' in object_relation:
                continue

            # cast to datetime
            if object_relation == 'timestamp':
                # Date already in ISO format, removing trailing Z
                value = value.rstrip('Z')

            if isinstance(value, dict):
                self.add_attribute(object_relation, **value)
            else:
                self.add_attribute(object_relation, value=value)
