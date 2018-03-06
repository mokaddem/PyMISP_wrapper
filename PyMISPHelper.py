#!/usr/bin/env python3

from pymisp.tools.abstractgenerator import AbstractMISPObjectGenerator
from pymisp.exceptions import PyMISPError
from pymisp import PyMISP, MISPAttribute
import pymisp

from CowrieMISPObject import CowrieMispObject

try:
    from MISPKeys import misp_url, misp_key
    flag_MISPKeys = True
except ImportError:
    flag_MISPKeys = False

import json, datetime, time, argparse


class PyMISPHelperError(Exception):
    def __init__(self, message):
        super(PyMISPHelperError, self).__init__(message)
        self.message = message
class MissingID(PyMISPHelperError):
    pass
class NotInEventMode(PyMISPHelperError):
    pass
class MISPObjectHasNoName(PyMISPHelperError):
    pass


class PyMISPHelper:
    MODE_NORMAL = 1
    MODE_DAILY = 2

    def __init__(self, pymisp, mode_type=MODE_NORMAL, daily_event_name='unset_daily_event_name', verbose=False):
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
        >>> pymisp = PyMISP(misp_url, misp_key)
        >>> pm = PyMISPHelper(pymisp)
        >>> pm.daily_mode("honeypot_1")
        >>> pm.add_attribute("ip-src", "9.9.9.9", category="Network activity")
        >>> pm.add_attribute_per_json(json.dumps({"type": "ip-src", "value": "8.9.9.9", "category": "Network activity"}))
        >>> pm.add_object("cowrie", {"session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet"})
        >>> pm.add_object_per_json(json.dumps({"name": "cowrie", "session": "session_id", "username": "root", "password": "root", "protocol": "ssh"}))
        >>> pm.add_sighting(uuid="5a9e6785-2400-4b6a-a707-4581950d210f")
        >>> pm.add_sighting_per_json({"uuid": "5a9e6bdf-9220-4b8f-ad23-4703950d210f"})
        """

        self.pymisp = pymisp
        self.mode_type = mode_type
        self.current_date = None # Avoid querying MISP every time an attribute is added
        self.verbose = verbose
        if self.mode_type == self.MODE_DAILY:
            daily_mode(daily_event_name)

        # Map object_name with their constructor
        self.dico_object = {
                'cowrie': CowrieMispObject
        }

    def log(self, msg):
        if self.verbose:
            print(msg)

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

    def fetch_daily_event_id(self):
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
                self.log('Found: ' + info + '->' + e_id)
                self.current_date = datetime.date.today()
                return int(e_id)
        created_event = self.create_daily_event()['Event']
        new_id = created_event['id']
        self.log('New event created: ' + new_id)
        self.current_date = datetime.date.today()
        return int(new_id)

    def create_daily_event(self, distribution=0, threat_level_id=3, analysis=0, date=None, published=False, orgc_id=None, org_id=None, sharing_group_id=None):
        """
        Create the daily event id on MISP
        """
        today = datetime.date.today()
        distribution = distribution # [0-3]
        info = self.daily_event_name.format(today)
        analysis = analysis # [0-2]
        threat_level_id = threat_level_id # [1-4]
        published = published
        org_id = org_id
        orgc_id = orgc_id
        sharing_group_id = sharing_group_id
        date = date
        event = self.pymisp.new_event(distribution=distribution, threat_level_id=threat_level_id,
                    analysis=analysis, info=info, date=date,
                    published=published, orgc_id=orgc_id, org_id=org_id, sharing_group_id=sharing_group_id)
        return event

    def get_daily_event_id(self):
        """
        Return the correct event id if daily mode is activated
        """
        if self.mode_type == self.MODE_DAILY:
            if self.current_date != datetime.date.today(): #refresh id
                self.eventID_to_push = self.fetch_daily_event_id()
            return self.eventID_to_push
        else:
            raise NotInEventMode('Daily mode not activated')


    # OBJECT
    def add_object(self, name, dict_values, event_id=None):
        """
        Add an object to MISP
        Parameters
        ----------
        name : str
            The MISP object name (also name of the object template)
        dict_values : dict | AbstractMISPObjectGenerator
            The values to populate the MISP object or the MISPObject itself
        event_id : int
            The event id where the object will be added to. If not provided and the MODE_DAILY is not enable it will throw an error
        """

        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")
        elif self.mode_type == self.MODE_DAILY and event_id is None:
            event_id = self.get_daily_event_id()

        templateID = self.get_object_template(name)

        if type(dict_values) is dict:
            MISP_ObjectConstructor = self.dico_object[name]
            MISP_Object = MISP_ObjectConstructor(dict_values)
        elif isinstance(dict_values, AbstractMISPObjectGenerator) and dict_values.name == name:
            MISP_Object = dict_values
        else:
            self.log("Type error")
            return

        r = self.pymisp.add_object(event_id, templateID, MISP_Object)
        if 'errors' in r:
            print(r)

    def add_object_per_json(self, data, event_id=None):
        """
        Add an object to MISP from a JSON or dict
        Parameters:
        -----------
        data : JSON (str) | dict
            The data containing information on the MISP object. Must contain the field 'name'
        event_id : int
            The event id where the attribute will be added to
        """
        if type(data) is str:
            dict_data = json.loads(data)
        elif type(data) is dict:
            dict_data = data
        else:
            self.log('Type error!')
            return

        # get object name
        try:
            name = dict_data['name']
            del dict_data['name']
        except IndexError as e:
            raise MISPObjectHasNoName("Supplied JSON does not contain name field.")

        self.add_object(name, dict_data, event_id=event_id)


    # SIGHTING
    def add_sighting(self, value=None, uuid=None, id=None, source=None, type=0, timestamp=None, **kargs):
        """
        Make a single sighting
        Parameters:
        -----------
        values : str
           Value of the attribute the sighting is related too
        uuid : str
           UUID of the attribute to update
        id : str
           ID of the attriute to update
        source : str
           Source of the sighting
        type : int
           Type of the sighting (0: normal sighting, 1: false positive sighting)
        timestamp : int
           Timestamp associated to the sighting
        """

        r = self.pymisp.sighting(value=value, uuid=uuid, id=id, source=source, type=type, timestamp=timestamp, **kargs)
        if 'errors' in r:
            print(r)

    def add_sighting_per_json(self, data):
        """
        Make a sighting
        Parameters
        ----------
        json_file : JSON (str) | dict
            Contain information about the sighting
        """
        if type(data) is str:
            dict_data = json.loads(data)
        elif type(data) is dict:
            dict_data = data
        else:
            self.log('Type error!')
            return

        self.add_sighting(**dict_data)


    # ATTRIBUTE
    def add_attribute(self, type_value, value, event_id=None, category=None, to_ids=False, comment=None, distribution=None, proposal=False, **kargs):
        """
        Add an attribute to MISP
        Parameters:
        -----------
        type_value : str
            The type of the value
        value : str
            The value of the attribute
        event_id : int
            The event id where the attribute will be added to
        """
        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")
        elif self.mode_type == self.MODE_DAILY and event_id is None:
            event_id = self.get_daily_event_id()
        event = self.pymisp.get_event(event_id)

        r = self.pymisp.add_named_attribute(event, type_value=type_value, value=value, category=category, to_ids=to_ids, comment=comment, distribution=distribution, proposal=proposal, **kargs)
        if 'errors' in r:
            print(r)

    def add_attribute_per_json(self, data, event_id=None, proposal=False):
        """
        Push an attribute to MISP from a JSON or dict
        Parameters
        ----------
        data : JSON (str) | dict
            The data containing information on the MISP attribute (Required: type, value)
        event_id : int
            The event id where the attribute will be added to
        proposal : bool
            True or False based on whether the attributes should be proposed or directly save
        """

        if self.mode_type == self.MODE_NORMAL and event_id is None:
            raise PyMISPHelperError("Trying to push an object without supplying an event id")
        elif self.mode_type == self.MODE_DAILY and event_id is None:
            event_id = self.get_daily_event_id()
        event = self.pymisp.get_event(event_id)

        if type(data) is str:
            dict_data = json.loads(data)
        elif type(data) is dict:
            dict_data = data
        else:
            self.log('Type error!')
            return

        type_value = dict_data['type']
        value = dict_data['value']
        del dict_data['type']
        del dict_data['value']
        self.add_attribute(type_value, value, **dict_data)
        

    # OTHERS
    def get_object_template(self, name):
            """
            Get the template id for the given MISP object name
            Parameters
            ----------
            name : str
                The name of the MISP object
            """
            try:
                templateID = [x['ObjectTemplate']['id'] for x in self.pymisp.get_object_templates_list() if x['ObjectTemplate']['name'] == name][0]
                return templateID
    
            except IndexError:
                valid_types = ", ".join([x['ObjectTemplate']['name'] for x in self.pymisp.get_object_templates_list()])
                print("Template for type %s not found! Valid types are: %s" % (self.name, valid_types))
    
