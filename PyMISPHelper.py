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

    def __init__(self, pymisp, mode_type=MODE_NORMAL, daily_event_name='unset_daily_event_name'):
        """
        Create a PyMISP interface to easily add attributes, objects or sightings to events especially for events that should be generated on a daily basis
        Parameters:
        -----------
        pymisp : PyMISP
            A valid PyMISP object
        mode_type : int
            The mode in which this object will behave: 
            MODE_NORMAL will require an event_id for most of the operations
            MODE_DAILY will query MISP to get the correct event ID related with daily_event_name
        daily_event_name : str
            The name of the daily event. (It will have the following format on MISP: daily_event_name YYYY-MM-DD)
        Examples:
        ---------
        >>> pmhelper = PyMISPHelper(pymisp)
        >>> pmhelper.daily_mode("honeypot_1") # switch to daily mode, so that every addition of attr. or obj. will be pushed to the correct event name
        >>> pmhelper.add_attributes("ip-src", "8.8.8.8", category="Network Activity") # add an attribute to MISP, as daily mode is activated, no need to supply an event id
        >>> pmhelper.push_MISP_attributes({"attribute_type": "ip-src", "value": "8.8.8.8", "category": "Network Activity"}) # exactly the same as the previous line
        >>> pmhelper.add_object("cowrie", {"session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet"}) # add an object to MISP, again no need to give an event id
        >>> pmhelper.add_sightings(["8.8.8.8", "9.9.9.9"], timestamp=time.time()) # perform a sighting on 8.8.8.8 and 9.9.9.9 
        >>> pmhelper.push_MISP_sightings({"values": ["8.8.8.8", "9.9.9.9"], "timestamp": time.time()}) # exactly the same as the previous line
        """

        self.pymisp = pymisp
        self.mode_type = mode_type
        self.current_date = None # Avoid querying MISP every time an attribute is added
        if self.mode_type == self.MODE_DAILY:
            daily_mode(daily_event_name)

        # Map object_name with their constructor
        self.dico_object = {
                'cowrie': CowrieMispObject
        }


    def normal_mode():
        """
        Switch to normal mode
        """
        self.mode_type = self.MODE_NORMAL

    # DAILY 
    def daily_mode(self, daily_event_name):
        """
        Switch to daily mode
        Daily mode can be use to automatically create and get daily event for a given name.
        Parameters:
        -----------
        daily_event_name : str
            The name of the daily event. (It will have the following format on MISP: daily_event_name YYYY-MM-DD)
        """
        self.current_date = None
        self.daily_event_name = daily_event_name+' {}' # used by format
        self.mode_type = self.MODE_DAILY
        self.eventID_to_push = self.get_daily_event_id()

    def get_all_related_events(self):
        """
        Fetch all the event info fom MISP matching the daily event name
        """
        to_search = self.daily_event_name.format("")
        results = self.pymisp.search_index(eventinfo=to_search)
        events = []
        for e in results['response']:
            events.append({'id': e['id'], 'org_id': e['org_id'], 'info': e['info']})
        return events

    def get_daily_event_id(self):
        """
        Query MISP to get the correct event id
        """
        if self.mode_type != self.MODE_DAILY:
            raise NotInEventMode('Daily mode is disabled. Switch to daily mode required to access this function')
        to_match = self.daily_event_name.format(datetime.date.today())
        events = self.get_all_related_events()
        for dic in events:
            info = dic['info']
            e_id = dic['id']
            if info == to_match:
                print('Found: ', info, '->', e_id)
                self.current_date = datetime.date.today()
                return int(e_id)
        created_event = self.create_daily_event()['Event']
        new_id = created_event['id']
        print('New event created:', new_id)
        self.current_date = datetime.date.today()
        return int(new_id)

    def create_daily_event(self):
        """
        Create the daily event id on MISP
        """
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

    def get_daily_event_id(self):
        """
        Return the correct event id if daily mode is activated
        """
        if self.mode_type == self.MODE_DAILY:
            if self.current_date != datetime.date.today(): #refresh id
                self.eventID_to_push = self.get_daily_event_id()
            return self.eventID_to_push
        else:
            return None


    # HELPERS
    def add_object(self, misp_object_type, values, event_id=None):
        """
        Add an object to MISP
        Create the correct MISP object depending on the provided misp_object_type
        Parameters
        ----------
        misp_object_type : str
            The misp object name (also name of the object template)
        values : dict
            The needed values to populate the object
        event_id : int
            The event id where the object will be added to. If not provided and the MODE_DAILY is not enable it will throw an error
        """

        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")

        mispObjectConstructor = self.dico_object[misp_object_type]
        mispObject = mispObjectConstructor(values)
        if event_id is None: # Prioritize argument instead
            event_id = self.get_daily_event_id()
        self.push_MISP_object(event_id, misp_object_type, mispObject)

    def add_sightings(self, values, uuid=None, id=None, source=None, type=0, timestamp=int(time.time())):
        """
        Make a sightings on the provided attribute values
        Parameters:
        -----------
        values : list or str
           The value(s) to sight
        """
        MISP_Sighting = MISPSighting(values, uuid=None, id=None, source=None, type=0, timestamp=int(time.time()))
        self.push_MISP_sightings(MISP_Sighting.get_dico())

    def add_attributes(self, attribute_type, value, event_id=None, category=None, to_ids=False, comment=None, distribution=None, proposal=False):
        """
        Add an attribute to MISP
        Parameters:
        -----------
        attribute_type : str
            The type of the attribute
        value : str
            The value of the attribute
        event_id : int
            The event id where the attribute will be added to
        """
        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")

        MISP_Attribute = MISPAttribute(event_id, attribute_type, value, category=category, to_ids=to_ids, comment=comment, distribution=distribution, proposal=proposal)
        if event_id is None: # Prioritize parameters
            event_id = self.get_daily_event_id()
        self.push_MISP_attributes(MISP_Attribute.get_dico(), event_id=event_id)


    # PUBLISHERS
    def push_MISP_object(self, event_id, misp_object_type, mispObject):
        """
        Push an object to MISP
        From the MISP Object, compare with local object template definitions and then push it to MISP
        Parameters
        ----------
        event_id : int
            The event id where the object will be added to
        misp_object_type : str
            The misp object name (also name of the object template)
        mispObject : AbstractMISPObjectGenerator
            The Misp  object with its attributes added
        """
        try:
            templateID = [x['ObjectTemplate']['id'] for x in self.pymisp.get_object_templates_list() if x['ObjectTemplate']['name'] == misp_object_type][0]
            r = self.pymisp.add_object(event_id, templateID, mispObject)
            if 'errors' in r:
                print(r)

        except IndexError:
            valid_types = ", ".join([x['ObjectTemplate']['name'] for x in self.pymisp.get_object_templates_list()])
            print("Template for type %s not found! Valid types are: %s" % (self.mispTYPE, valid_types))

    def push_MISP_attributes(self, attribute_dico, event_id=None):
        """
        Push an attribute to MISP
        From a dictionnary, push the attribute to MISP
        Parameters
        ----------
        event_id : int
            The event id where the attribute will be added to
        attribute dico : dict
            A dictionnary defining value of the attribute to be added. (Required: aatribute_type, value)
        """
        
        # check dict validy
        if MISPAttribute.check_validity(attribute_dico):
            print('Attribute dictionnary is not valid - required fields {}'.format(MISPAttribute.required_fields))
            return

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

    def push_MISP_sightings(self, sightings):
        """
        Make a sightings on the provided attribute
        Push sightings (from dict or list)
        Parameters
        ----------
        sighting_list : list or dict
            The list or dict containing the sighting(s) to make
        """
        r = self.pymisp.set_sightings(sighting_list)
        if 'errors' in r:
            print(r)

