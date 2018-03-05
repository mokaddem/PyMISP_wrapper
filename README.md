# PyMISP-wrapper
A simple PyMISP wrapper designed to ease the addition of commonly used operations on daily generated event. 

## PyMISPHelper

### Examples
```
>>> pmhelper = PyMISPHelper(pymisp)

# switch to daily mode, so that every addition of attr. or obj. will be pushed to the correct event name
>>> pmhelper.daily_mode("honeypot_1")

# add an attribute to MISP, as daily mode is activated, no need to supply an event id
>>> pmhelper.add_attributes("ip-src", "8.8.8.8", category="Network Activity")

# exactly the same as the previous line
>>> pmhelper.push_MISP_attributes({"attribute_type": "ip-src", "value": "8.8.8.8", "category": "Network Activity"})

# add an object to MISP, again no need to give an event id
>>> pmhelper.add_object("cowrie", {"session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet"})

# perform a sighting on 8.8.8.8 and 9.9.9.9 
>>> pmhelper.add_sightings(["8.8.8.8", "9.9.9.9"], timestamp=time.time())

# exactly the same as the previous line
>>> pmhelper.MISP_sightings({"values": ["8.8.8.8", "9.9.9.9"], "timestamp": time.time()})
```

## RedisToMISP
``RedisToMISP`` Pops items from redis and performs the requested action like adding an attribute, adding an object or making a sighting.
```
usage: RedisToMISP.py [-h] [--host HOST] [-p PORT] [-n DB] -k KEYNAMEPOP
                      [KEYNAMEPOP ...] [-s SLEEP] [-u URL] [--mispkey MISPKEY]
                      [--verifycert] [--dailymode] [--eventname EVENTNAME]
                      [--eventid EVENTID]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           The redis host
  -p PORT, --port PORT  The redis port
  -n DB, --db DB        The redis DB number
  -k KEYNAMEPOP [KEYNAMEPOP ...], --keynamepop KEYNAMEPOP [KEYNAMEPOP ...]
                        The keynames to POP element from. Each keyname must
                        have at least one of the following ending:
                        '_sighting', '_attribute', '_object'.
  -s SLEEP, --sleep SLEEP
                        The time between each check
  -u URL, --url URL     The MISP URL to connect to
  --mispkey MISPKEY     The MISP API key
  --verifycert          Should the certificate be verified
  --dailymode           By enabling this mode, all push to redis will be
                        stored in the daily event
  --eventname EVENTNAME
                        The daily event name to be used in MISP. (e.g.
                        honeypot_1, will produce each day an event of the form
                        honeypot_1 dd-mm-yyyy
  --eventid EVENTID     The MISP event id in which to put data. Overwrite
                        dailymode
```
