#!/usr/bin/env python3

from pymisp.tools.abstractgenerator import AbstractMISPObjectGenerator
from pymisp.exceptions import PyMISPError
from pymisp import PyMISP

from CowrieMISPObject import CowrieMispObject
from MISPSighting import MISPSighting
from MISPAttribute import MISPAttribute

try:
    from MISPKeys import misp_url, misp_key
    flag_MISPKeys = True
except ImportError:
    flag_MISPKeys = False

import json, datetime, time, argparse
from pprint import pprint


class PyMISPHelperError(Exception):
    def __init__(self, message):
        super(PyMISPHelperError, self).__init__(message)
        self.message = message
class MissingID(PyMISPHelperError):
    pass
class NotInEventMode(PyMISPHelperError):
    pass


class PyMISPHelper:
    MODE_NORMAL = 1
    MODE_DAILY = 2

    def __init__(self, pymisp, mode_type=MODE_NORMAL, daily_event_name='unset_keyname'):
        self.pymisp = pymisp
        self.mode_type = mode_type
        self.currentID_date = None
        if self.mode_type == self.MODE_DAILY:
            daily_mode(daily_event_name)
        self.dico_object = {
                'cowrie': CowrieMispObject
        }


    def normal_mode():
        self.mode_type = self.MODE_NORMAL

    # DAILY 
    def daily_mode(self, daily_event_name):
        self.currentID_date = None
        self.daily_event_name = daily_event_name+' {}' # used for format
        self.mode_type = self.MODE_DAILY
        self.eventID_to_push = self.get_daily_event_id()

    def get_all_related_events(self):
        to_search = self.daily_event_name.format("")
        results = self.pymisp.search_index(eventinfo=to_search)
        events = []
        for e in results['response']:
            events.append({'id': e['id'], 'org_id': e['org_id'], 'info': e['info']})
        return events

    def get_daily_event_id(self):
        if self.mode_type != self.MODE_DAILY:
            raise NotInEventMode('Daily mode is disabled. Switch to daily mode before calling this function')
        to_match = self.daily_event_name.format(datetime.date.today())
        events = self.get_all_related_events()
        for dic in events:
            info = dic['info']
            e_id = dic['id']
            if info == to_match:
                print('Found: ', info, '->', e_id)
                self.currentID_date = datetime.date.today()
                return int(e_id)
        created_event = self.create_daily_event()['Event']
        new_id = created_event['id']
        print('New event created:', new_id)
        self.currentID_date = datetime.date.today()
        return int(new_id)

    def create_daily_event(self):
        today = datetime.date.today()
        distribution = 0 # [0-3]
        info = self.daily_event_name.format(today)
        analysis = 0 # [0-2]
        threat = 3 # [1-4]
        published = False
        org_id = None
        orgc_id = None
        sharing_group_id = None
        date = None
        event = self.pymisp.new_event(distribution, threat,
                    analysis, info, date,
                    published, orgc_id, org_id, sharing_group_id)
        return event

    def get_event_id(self):
        if self.mode_type == self.MODE_DAILY:
            if self.currentID_date != datetime.date.today(): #refresh id
                self.eventID_to_push = self.get_daily_event_id()
            return self.eventID_to_push
        else:
            return None


    # PUSH HELPERS
    def add_object(self, misp_object_type, values, event_id=None):
        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")
        mispObjectConstructor = self.dico_object[misp_object_type]
        mispObject = mispObjectConstructor(values)
        if event_id is None:
            event_id = self.get_event_id()
        self.push_MISP_object(event_id, misp_object_type, mispObject)

    def add_sightings(self, values, uuid=None, id=None, source=None, type=0, timestamp=int(time.time())):
        MISP_Sighting = MISPSighting(values, uuid=None, id=None, source=None, type=0, timestamp=int(time.time()))
        self.push_MISP_sightings(MISP_Sighting)

    def add_attributes(self, attribute_type, value, event_id=None, category=None, to_ids=False, comment=None, distribution=None, proposal=False):
        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")

                                    
        if event_id is None:
            event_id = self.get_event_id()
        MISP_Attribute = MISPAttribute(event_id, attribute_type, value, category=category, to_ids=to_ids, comment=comment, distribution=distribution, proposal=proposal)
        self.push_MISP_attributes(MISP_Attribute, event_id=event_id)


    # PUBLISHERS
    def push_MISP_object(self, event_id, misp_object_type, mispObject):
        try:
            templateID = [x['ObjectTemplate']['id'] for x in self.pymisp.get_object_templates_list() if x['ObjectTemplate']['name'] == misp_object_type][0]
            r = self.pymisp.add_object(event_id, templateID, mispObject)
            if 'errors' in r:
                print(r)

        except IndexError:
            valid_types = ", ".join([x['ObjectTemplate']['name'] for x in self.pymisp.get_object_templates_list()])
            print("Template for type %s not found! Valid types are: %s" % (self.mispTYPE, valid_types))

    def push_MISP_attributes(self, attribute_dico, event_id=None):
        event_id = event_id if event_id is not None else attribute_dico['event_id'] # prioritize arguments instead of dico field

        r = self.pymisp.add_named_attribute(
                event_id,
                attribute_dico['attribute_type'],
                attribute_dico['value'],
                category=attribute_dico.get('category', None),
                to_ids=attribute_dico.get('to_ids', False),
                comment=attribute_dico.get('comment', None),
                distribution=attribute_dico.get('distribution', None),
                proposal=attribute_dico.get('proposal', False))
        if 'errors' in r:
            print(r)

    def push_MISP_sightings(self, sighting_list):
        r = self.pymisp.set_sightings(sighting_list)
        if 'errors' in r:
            print(r)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    # if MISPKeys.py is not present, makes url and key required
    parser.add_argument("-u", "--url",  type=str, required=not flag_MISPKeys, default=misp_url,
                        help="The MISP URL to connect to")
    parser.add_argument("-k", "--key",  type=str, required=not flag_MISPKeys, default=misp_key,
                        help="The MISP API key")
    parser.add_argument("--verifycert", action="store_true", default=True,
                        help="Should the certificate be verified")
    parser.add_argument("--eventmode", action="store_true",
                        help="By enabling this mode, all push to redis will be stored in the daily event")
    parser.add_argument("--keyname", type=str,
                        help="The daily event name to be used in MISP. (e.g. honeypot_1, will produce each day an event of the form honeypot_1_dd-mm-yyyy")
    args = parser.parse_args()

    try:
            pymisp = PyMISP(args.url, args.key, args.verifycert)
    except PyMISPError as e:
            print(e)
    PyMISPHelper = PyMISPHelper(pymisp, mode_type=args.eventmode, daily_event_name=args.keyname)
