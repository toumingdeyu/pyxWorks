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

devicemodes=['all','config','nonconfig']
devicemode=devicemodes[1]

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python %s nameOfInputFile.json all|config|nonconfig" % (ScriptName))
  sys.exit(1)
else:
  fileName=args[0]
  if len(sys.argv)==3 and args[1] in devicemodes: devicemode=args[1]

### PRINT RESPONSE + ignorefail=True/False option ==============================
def print_response_and_end_on_error(method,uri,response,ignorefail=False):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    if not ignorefail and int(response.status_code)>=400: sys.exit(0)

### MAIN =======================================================================
def main():
  ### READ YAML NSO AUTH FILE --------------------------------------------------
  with open('./nso_auth_data.yaml', 'r') as stream: nso_auth_data = yaml.load(stream)
  with io.open(fileName) as json_file: json_raw_data = json.load(json_file)
  if nso_auth_data and json_raw_data:
    json_deeper_data=json_raw_data
    ### UNPACKING OF DICTIONARIES TILL 'device' LEVEL is FOUND =================
    while not ('device' in json_deeper_data or 'tailf-ncs:device' in json_deeper_data):
      json_even_deeper_data=json_deeper_data.get(list(json_deeper_data.keys())[0],'')
      json_deeper_data=json_even_deeper_data
    ### DEVICE NAME PARSE-OUT --------------------------------------------------
    if 'device' in json_deeper_data:
      json_device_data = json_deeper_data
      if json_device_data.get('device'):
        if type(json_device_data.get('device'))==list:
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
    ### DEVICE NAME PARSE-OUT IN CASE OF tailf-ncs:device ----------------------
    elif 'tailf-ncs:device' in json_deeper_data:
      json_device_data = json_deeper_data
      if json_device_data.get('tailf-ncs:device'):
        if type(json_device_data.get('tailf-ncs:device'))==list:
          try:
            nso_device=json_device_data.get('tailf-ncs:device','')[0].get('name','')
            print('device name=%s'%(nso_device))
          except:
            print('Problem to get device name from json file!')
            sys.exit(0)
        else:
          try:
            nso_device=json_device_data.get('tailf-ncs:device','').get('name','')
            print('device name=%s'%(nso_device))
          except:
            print('Problem to get device name from json file!')
            sys.exit(0)
    ### END OF DEVICE NAME PARSE-OUT -------------------------------------------
    else: sys.exit(0)

    #json_device_data=json_device_data.get(list(json_device_data.keys())[0],'')
    #print(json_device_data)

    ### RESTCONF definitions ---------------------------------------------------
    auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
    restconf_base_uri = "%s://%s:%s/restconf"%(nso_auth_data.get('nso_protocol',''),nso_auth_data.get('nso_ipaddress',''), nso_auth_data.get('nso_port',''))
    restconf_data_base_uri = "%s/data"%(restconf_base_uri)
    restconf_operations_base_uri = "%s/operations"%(restconf_base_uri)
    restconf_headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-data+json'}

    nonconfig_dict_encapsulation = { 'nonconfig' : {} }
    config_dict_encapsulation = { 'config' : {} }
    all_dict_encapsulation = { 'all' : {} }

    all_dict_encapsulation['all'].update(json_device_data)
    config_dict_encapsulation['config'].update(json_device_data)
    nonconfig_dict_encapsulation['nonconfig'].update(json_device_data)


    #print(config_dict_encapsulation)

#     ### FETCH HOST KEYS ========================================================
#     uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/ssh/fetch-host-keys"
#     response = requests.post(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('POST',uri,response)

#     ### DEVICE READ FROM NSO ===================================================
#     uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=config'
#     response = requests.get(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('GET',uri,response)

    if devicemode==devicemodes[0]:
      print(all_dict_encapsulation)
      ### DEVICE WRITE TO NSO ====================================================
      uri = restconf_data_base_uri + '/devices/device=' + nso_device + '/all/'
      response = requests.patch(uri, auth=auth, headers=restconf_headers, data=json.dumps(all_dict_encapsulation))
      print_response_and_end_on_error('PATCH',uri,response)

    if devicemode==devicemodes[1]:
      print(config_dict_encapsulation)
      ### DEVICE WRITE TO NSO ====================================================
      uri = restconf_data_base_uri + '/devices/device=' + nso_device + '/config/'
      response = requests.patch(uri, auth=auth, headers=restconf_headers, data=json.dumps(config_dict_encapsulation))
      print_response_and_end_on_error('PATCH',uri,response)

    if devicemode==devicemodes[2]:
      print(nonconfig_dict_encapsulation)
      ### DEVICE WRITE TO NSO ====================================================
      uri = restconf_data_base_uri + '/devices/device=' + nso_device + '/nonconfig/'
      response = requests.patch(uri, auth=auth, headers=restconf_headers, data=json.dumps(nonconfig_dict_encapsulation))
      print_response_and_end_on_error('PATCH',uri,response)

#     ### DEVICE READ FROM NSO ===================================================
#     uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=config'
#     response = requests.get(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('GET',uri,response)

if __name__ == "__main__":
    main()
