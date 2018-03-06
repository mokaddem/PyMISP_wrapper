# PyMISP-wrapper
A simple PyMISP wrapper designed to ease the addition of commonly used operations on daily generated event. 

## PyMISPHelper

### Examples
```
# create helper object (pymisp is a valid PyMISP instance)
>>> pmhelper = PyMISPHelper(pymisp)

# switch to daily mode, so that every addition of attr. or obj. will be pushed to the correct event name
>>> pmhelper.daily_mode("honeypot_1")

# add an attribute to MISP, as daily mode is activated, no need to supply an event id
>>> pmhelper.add_attributes("ip-src", "8.8.8.8", category="Network activity")

# exactly the same as the previous line
>>> pmhelper.add_attribute_per_json(json.dumps({"type": "ip-src", "value": "8.8.8.8", "category": "Network activity"}))

# add an object to MISP, again there is no need to give an event id
>>> pmhelper.add_object("cowrie", {"session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet"})

# exactly the same as the previous line
>>> cowrie_obj = CowrieMispObject({"session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet"})
>>> pmhelper.add_object("cowrie", cowrie_obj)

# exactly the same as the previous line
>>> pmhelper.add_object_per_json(json.dumps({"name": "cowrie", "session": "session_id", "username": "root", "password": "root", "protocol": "ssh"}))

# perform a sighting on attribute uuid ... 
>>> pmhelper.add_sighting(uuid="5a9e6785-2400-4b6a-a707-4581950d210f")

# exactly the same as the previous line
>>> pmhelper.add_sighting_per_json(json.dumps({"uuid": "5a9e6785-2400-4b6a-a707-4581950d210f"}))
```


## RedisToMISP
``RedisToMISP`` can be used to 
- Pop items from redis and performs the requested action like adding an attribute, adding an object or making a sighting. Or,
- Easily push data to redis

### Redis feeder example

```
# create helper object
>>> helper = MISPItemToRedis("redis_list_keyname")

# push a attribute to redis
>>> helper.push_attribute("ip-src", "8.8.8.8", category="Network activity")

# push an object to redis
>>> helper.push_object({ "name": "cowrie", "session": "session_id", "username": "admin", "password": "admin", "protocol": "telnet" })

# push a sighting to redis
>>> helper.push_sighting(uuid="5a9e9e26-fe40-4726-8563-5585950d210f")
```

### Redis consumer example

```
usage: RedisToMISP.py [-h] [--host HOST] [-p PORT] [-n DB] -k KEYNAMEPOP
                      [KEYNAMEPOP ...] --eventname EVENTNAME [-s SLEEP]
                      [-u URL] [--mispkey MISPKEY] [--verifycert]
                      [--dailymode] [--eventid EVENTID]
                      [--keynameError KEYNAMEERROR]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           The redis host
  -p PORT, --port PORT  The redis port
  -n DB, --db DB        The redis DB number
  -k KEYNAMEPOP [KEYNAMEPOP ...], --keynamePop KEYNAMEPOP [KEYNAMEPOP ...]
                        The keynames to POP element from.
  --eventname EVENTNAME
                        The daily event name to be used in MISP. (e.g.
                        honeypot_1, will produce each day an event of the form
                        honeypot_1 yyyy-mm-dd
  -s SLEEP, --sleep SLEEP
                        Redis pooling time
  -u URL, --url URL     The MISP URL to connect to
  --mispkey MISPKEY     The MISP API key
  --verifycert          Should the certificate be verified
  --dailymode           By enabling this mode, all push to redis will be
                        stored in the daily event
  --eventid EVENTID     The MISP event id in which to put data. Overwrite
                        dailymode
  --keynameError KEYNAMEERROR
                        The redis list keyname in which to put items that
                        generated an error
```
