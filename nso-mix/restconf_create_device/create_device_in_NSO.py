#!/usr/bin/env python

import io
import os
import sys
import json
import yaml
import requests
import urllib3
import copy
import optparse

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s nameOfInputFile.json" % (ScriptName))
  sys.exit(1)
else:
  fileName=args[0]

### PRINT RESPONSES ============================================================
def print_response_and_end_on_error(method,uri,response):
  print('='*80)
  print(method,uri,'  |',response.status_code,'|')
  print('-'*80)
  print(response.headers)
  print('-'*80)
  print(response.text)
  if int(response.status_code)>=400: sys.exit(0)

### MAIN =======================================================================
def main():
  ### READ YAML NSO AUTH FILE --------------------------------------------------
  with open('./nso_auth_data.yaml', 'r') as stream: nso_auth_data = yaml.load(stream)
  with io.open(fileName) as json_file: json_raw_data = json.load(json_file)
  if nso_auth_data and json_raw_data:
    json_deeper_data=json_raw_data
    ### UNPACKING OF DICTIONARIES TILL 'device' LEVEL is FOUND =================
    while 'device' not in json_deeper_data:
      json_even_deeper_data=json_deeper_data.get(list(json_deeper_data.keys())[0],'')
      json_deeper_data=json_even_deeper_data
    ### DEVICE NAME PARSE-OUT --------------------------------------------------
    if 'device' in json_deeper_data:
      json_device_data = json_deeper_data
      if type(json_device_data.get('device',''))==list:
        try:
          nso_device=json_device_data.get('device','')[0].get('name','')
          print('device name=%s'%(nso_device))
        except:
          print('Problem to get device name from json file!')
          sys.exit(0)
      else:
        try:
          nso_device=json_device_data.get('device','').get('name','')
          print('device name=%s'%(nso_device))
        except:
          print('Problem to get device name from json file!')
          sys.exit(0)
    else: sys.exit(0)

    ### RESTCONF definitions ---------------------------------------------------
    auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
    restconf_base_uri = "%s://%s:%s/restconf"%(nso_auth_data.get('nso_protocol',''),nso_auth_data.get('nso_ipaddress',''), nso_auth_data.get('nso_port',''))
    restconf_data_base_uri = "%s/data"%(restconf_base_uri)
    restconf_operations_base_uri = "%s/operations"%(restconf_base_uri)
    restconf_headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-data+json'}

    ### DEVICE WRITE TO NSO ====================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device
    response = requests.put(uri, auth=auth, headers=restconf_headers, data=json.dumps(json_device_data))
    print_response_and_end_on_error('PUT',uri,response)

    ### FETCH HOST KEYS ========================================================
    uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/ssh/fetch-host-keys"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('POST',uri,response)

    ### SYNC-FROM NSO ==========================================================
    uri = restconf_data_base_uri + "/devices/device=" + nso_device + "/sync-from"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('POST',uri,response)

if __name__ == "__main__": main()
