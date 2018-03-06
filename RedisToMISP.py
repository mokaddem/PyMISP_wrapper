#!/usr/bin/env python3

from pymisp import PyMISP
from PyMISPHelper import PyMISPHelper, PyMISPError, flag_MISPKeys
import redis, argparse, time, json, threading, sys

e=t=None # animation thread

class RedisToMISPException(Exception):
    def __init__(self, message):
        super(RedisToMISPException, self).__init__(message)
        self.message = message

class NoValidKey(RedisToMISPException):
    pass

def processing_animation(e, refresh_rate=5):
    i = 0
    while True:
        if e.is_set():
            return
        i += 1
        print("/-\|"[i%4], end="\r", sep="")
        sys.stdout.flush()
        time.sleep(1.0/float(refresh_rate))

def beautyful_sleep_undefined(sleep):
    length = 20
    sleeptime = float(sleep) / float(length)
    for i in range(length):
        blength = (i+1 if i < 3 else (3-(i-length) if i > length else 3))
        temp_string = '|'*((i if i < length else length)+1-blength) + '|'*blength + ' '*(length-i)
        print('sleeping [{}]'.format(temp_string), end='\r', sep='')
        sys.stdout.flush()
        time.sleep(sleeptime)

def beautyful_sleep(sleep):
    length = 20
    sleeptime = float(sleep) / float(length)
    for i in range(length):
        temp_string = '|'*i + ' '*(length-i-1)
        print('sleeping [{}]'.format(temp_string), end='\r', sep='')
        sys.stdout.flush()
        time.sleep(sleeptime)


class RedisToMISP:
    SUFFIX_SIGH = '_sighting'
    SUFFIX_ATTR = '_attribute'
    SUFFIX_OBJ = '_object'
    SUFFIX_LIST = [SUFFIX_SIGH, SUFFIX_ATTR, SUFFIX_OBJ]

    def __init__(self, host, port, db, keynames, PyMISPHelper, sleep=1, event_id=None, daily_event_name=None):
        global e, t
        e = threading.Event()
        t = threading.Thread(name="processing-animation", target=processing_animation, args=(e,))
        t.start()

        self.host = host
        self.port = port
        self.db = db
        self.keynames = []
        for k in keynames:
            for s in self.SUFFIX_LIST:
                self.keynames.append(k+s)
        self.sleep = sleep
        self.event_id = event_id
        self.event_name = daily_event_name

        self.serv = redis.StrictRedis(self.host, self.port, self.db, decode_responses=True)
        self.pymisphelper = PyMISPHelper

        if event_id is None:
            self.pymisphelper.daily_mode(daily_event_name)

    def consume(self):
        while True:
            for key in self.keynames:
                while True:
                    data = self.pop(key)
                    if data is None:
                        break
                    try:
                        self.perform_action(key, data)
                    except Exception as e:
                        print('Error', e)
            beautyful_sleep(5)

    def pop(self, key):
        popped = self.serv.rpop(key)
        if popped is None:
            return None
        try:
            popped = json.loads(popped)
        except ValueError as e:
            pass
        except ValueError as e:
            pass
        return popped


    def perform_action(self, key, data):
        global e, t
        e = threading.Event()
        t = threading.Thread(name="processing-animation", target=processing_animation, args=(e,))
        # sighting
        if key.endswith(self.SUFFIX_SIGH):
            self.print_processing(self.SUFFIX_SIGH, t)
            self.pymisphelper.add_sighting_per_json(data)

        # attribute
        elif key.endswith(self.SUFFIX_ATTR):
            self.print_processing(self.SUFFIX_ATTR, t)
            self.pymisphelper.add_attribute_per_json(data, event_id=self.event_id)

        # object
        elif key.endswith(self.SUFFIX_OBJ):
            self.print_processing(self.SUFFIX_OBJ, t)
            self.pymisphelper.add_object_per_json(data, event_id=self.event_id)

        else:
            raise NoValidKey("Can't define action to perform")
        e.set()
        t.join()

    def validate_key(self, k):
        return self.SUFFIX_SIGH in k or self.SUFFIX_ATTR in k or self.SUFFIX_OBJ in k

    def print_processing(self, key, t):
        key = key.lstrip('_')
        print('Adding %s' % key + ' '*20) # fill to overwrite already progressbar character
        t.start()

class MISPItemToRedis:
    SUFFIX_SIGH = '_sighting'
    SUFFIX_ATTR = '_attribute'
    SUFFIX_OBJ = '_object'
    SUFFIX_LIST = [SUFFIX_SIGH, SUFFIX_ATTR, SUFFIX_OBJ]

    def __init__(self, keyname, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.keyname = keyname
        self.serv = redis.StrictRedis(self.host, self.port, self.db)

    def push_json(self, jdata, keyname, action):
        all_action = [s.lstrip('_') for s in self.SUFFIX_LIST]
        if action not in all_action:
            print('Error: Invalid action. (Allowed: {})'.format(all_action))
        key = keyname + '_' + action
        self.serv.lpush(key, jdata)

    def push_attribute(self, type_value, value, category=None, to_ids=False, comment=None, distribution=None, proposal=False, **kwargs):
        to_push = {}
        to_push['type'] = type_value
        to_push['value'] = value
        if category is not None:
            to_push['category'] = category
        if to_ids is not None:
            to_push['to_ids'] = to_ids
        if comment is not None:
            to_push['comment'] = comment
        if distribution is not None:
            to_push['distribution'] = distribution
        if proposal is not None:
            to_push['proposal'] = proposal
        for k, v in kwargs.items():
            to_push[k] = v
        key = self.keyname + self.SUFFIX_ATTR
        self.serv.lpush(key, json.dumps(to_push)) 

    def push_attribute_obj(self, MISP_Attribute, keyname):
        key = keyname + self.SUFFIX_ATTR
        jdata = MISP_Attribute.to_json()
        self.serv.lpush(key, jdata)

    def push_object(self, dict_values):
        # check that 'name' field is present
        if 'name' not in dict_values:
            print("Error: JSON must contain the field 'name'")
        key = self.keyname + self.SUFFIX_OBJ
        self.serv.lpush(key, json.dumps(dict_values)) 

    def push_object_obj(self, MISP_Object, keyname):
        key = keyname + self.SUFFIX_OBJ
        jdata = MISP_Object.to_json()
        self.serv.lpush(key, jdata)

    def push_sighting(self, value=None, uuid=None, id=None, source=None, type=0, timestamp=None, **kargs):
        to_push = {}
        if value is not None:
            to_push['value'] = value
        if uuid is not None:
            to_push['uuid'] = uuid
        if id is not None:
            to_push['id'] = id
        if source is not None:
            to_push['source'] = source
        if type is not None:
            to_push['type'] = type
        if timestamp is not None:
            to_push['timestamp'] = timestamp

        for k, v in kargs.items():
            if v is not None:
                to_push[k] = v
        key = self.keyname + self.SUFFIX_SIGH
        self.serv.lpush(key, json.dumps(to_push)) 

    def push_sighting_obj(self, MISP_Sighting, keyname):
        key = keyname + self.SUFFIX_SIGH
        jdata = MISP_Sighting.to_json()
        self.serv.lpush(key, jdata)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--host",  type=str, default='127.0.0.1',
                        help="The redis host")
    parser.add_argument("-p", "--port",  type=int, default=6379,
                        help="The redis port")
    parser.add_argument("-n", "--db",  type=int, default=0,
                        help="The redis DB number")
    parser.add_argument("-k", "--keynamePop", type=str, nargs='+', required=True,
            help="The keynames to POP element from.")
    parser.add_argument("-s", "--sleep", type=int, default=1,
                        help="The time between each check")

    # PyMISPHelper
    if flag_MISPKeys:
        from MISPKeys import misp_url, misp_key

    parser.add_argument("-u", "--url",  type=str, required=not flag_MISPKeys, default=misp_url,
                        help="The MISP URL to connect to")
    parser.add_argument("--mispkey",  type=str, required=not flag_MISPKeys, default=misp_key,
                        help="The MISP API key")
    parser.add_argument("--verifycert", action="store_true", default=True,
                        help="Should the certificate be verified")
    parser.add_argument("--dailymode", action="store_true",
                        help="By enabling this mode, all push to redis will be stored in the daily event")
    parser.add_argument("--eventname", type=str, required=True,
                        help="The daily event name to be used in MISP. (e.g. honeypot_1, will produce each day an event of the form honeypot_1 dd-mm-yyyy")
    parser.add_argument("--eventid", type=int, default=None,
                        help="The MISP event id in which to put data. Overwrite dailymode")
    parser.add_argument("--keynameError", type=str, default='RedisToMisp_Error',
                        help="The redis list keyname in which to put items that generated an error")

    args = parser.parse_args()

    if args.eventid is not None:
        args.dailymode = False
        args.eventname = ''

    try:
        pymisp = PyMISP(args.url, args.mispkey, args.verifycert)
    except PyMISPError as e:
        print(e)
    PyMISPHelper = PyMISPHelper(pymisp, mode_type=args.dailymode, daily_event_name=args.eventname)


    redisToMISP = RedisToMISP(args.host, args.port, args.db, args.keynamePop, PyMISPHelper, sleep=args.sleep, event_id=args.eventid, daily_event_name=args.eventname)
    try:
        redisToMISP.consume()
    except (KeyboardInterrupt, SystemExit):
        e.set()
        t.join()

