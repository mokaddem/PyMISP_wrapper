#!/usr/bin/env python3

from pymisp import PyMISP
from PyMISPHelper import PyMISPHelper, PyMISPError, flag_MISPKeys
import redis, argparse, time, json

class RedisToMISPException(Exception):
    def __init__(self, message):
        super(RedisToMISPException, self).__init__(message)
        self.message = message

class NoValidKey(RedisToMISPException):
    pass

class RedisToMISP:
    PREFIX_SIGH = '_sighting'
    PREFIX_ATTR = '_attribute'
    PREFIX_OBJ = '_object'

    def __init__(self, host, port, db, keynames, PyMISPHelper, sleep=1, event_id=None, daily_event_name=None):
        self.host = host
        self.port = port
        self.db = db
        self.keynames = [ k for k in keynames if self.validate_key(k) ]
        if len(self.keynames) == 0:
            raise NoValidKey('No valid key found. Key usage: *_[sighting/attribute/object]')
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
                    self.perform_action(key, data)
            self.beautyful_sleep()

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

    def publish(self, key, data):
        if not self.validate_key(key):
            raise NoValidKey('Not a valid key. Key usage: *_[sighting/attribute/object]')
        self.serv.lpush(key, data)


    def perform_action(self, key, data):
        if key.endswith(self.PREFIX_SIGH):
            self.print_processing(self.PREFIX_SIGH)
            self.pymisphelper.push_MISP_sightings(data)
        elif key.endswith(self.PREFIX_ATTR):
            self.print_processing(self.PREFIX_ATTR)
            event_id = self.pymisphelper.get_event_id()
            self.pymisphelper.push_MISP_attributes(data, event_id=event_id)
        elif key.endswith(self.PREFIX_OBJ):
            self.print_processing(self.PREFIX_OBJ)
            misp_object_type = data['mispObjectType']
            del data['mispObjectType']
            self.pymisphelper.add_object(misp_object_type, data, event_id=self.event_id)
        else:
            raise NoValidKey("Can't define action to perform")

    def validate_key(self, k):
        return self.PREFIX_SIGH in k or self.PREFIX_ATTR in k or self.PREFIX_OBJ in k

    def beautyful_sleep(self):
        refresh = 5
        mult = self.sleep*refresh
        for i in range(mult+4):
            sleeptime = float(self.sleep) / mult
            blength = (i+1 if i < 3 else (3-(i-mult) if i > mult else 3))
            temp_string = ' '*((i if i < mult else mult)+1-blength) + '|'*blength + ' '*(mult-i)
            print('sleeping [{}]'.format(temp_string), end='\r', sep='')
            time.sleep(sleeptime)

    def print_processing(self, key):
        print('Processing %s' % key)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--host",  type=str, default='127.0.0.1',
                        help="The redis host")
    parser.add_argument("-p", "--port",  type=int, default=6379,
                        help="The redis port")
    parser.add_argument("-n", "--db",  type=int, default=0,
                        help="The redis DB number")
    parser.add_argument("-k", "--keynamepop", type=str, nargs='+', required=True,
            help="The keynames to POP element from. Each keyname must have at least one of the following ending: '_sighting', '_attribute', '_object'.")
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
    parser.add_argument("--eventname", type=str, default="unamed_daily_event",
                        help="The daily event name to be used in MISP. (e.g. honeypot_1, will produce each day an event of the form honeypot_1 dd-mm-yyyy")
    parser.add_argument("--eventid", type=int, default=None,
                        help="The MISP event id in which to put data. Overwrite dailymode")

    args = parser.parse_args()

    if args.eventid is not None:
        args.dailymode = False
        args.eventname = ''

    try:
        pymisp = PyMISP(args.url, args.mispkey, args.verifycert)
    except PyMISPError as e:
        print(e)
    PyMISPHelper = PyMISPHelper(pymisp, mode_type=args.dailymode, daily_event_name=args.eventname)


    redisToMISP = RedisToMISP(args.host, args.port, args.db, args.keynamepop, PyMISPHelper, sleep=args.sleep, event_id=args.eventid, daily_event_name=args.eventname)
    redisToMISP.consume()
