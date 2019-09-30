#!/usr/bin/python

import json, collections, six
import sys, os
from cerberus import Validator


def load_json(path, file_name, dict = None):
    """Open json file return dictionary."""
    try:
        if dict:
            json_data = json.load(open(path + file_name))
        else:    
            json_data = json.load(open(path + file_name),object_pairs_hook=collections.OrderedDict)
    except Exception as e: print('PROBLEM[' + str(e) + ']')
    return json_data

data = load_json('', 'ipx_cfg.json', dict = True)
print(json.dumps(data, indent = 2))

### SCHEMA - CHECK ONLY LISTED DATA, IGNORE UNKNOWN #######
v = Validator({}, allow_unknown=True)

v.schema = {
    'vlan_id': {'required': True, 'type': 'string'},
    'peer_address': {'required': True, "type": "string", "regex": "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$"},
    'rd': {'required': True, "type": "string", "regex": "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\:[0-9]+$"},
    'circuit_id': {'required': True, "type": "string", "regex": "^[A-Z]+[0-9]+$"}   
}

#v.allow_unknown = {'type': 'string'}

### v.validate({'an_unknown_field': 'john'})

if v.validate(data):
    print('\nVALID')
else:
    print('\nINVALID')
    print(v.errors)
    




