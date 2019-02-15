#!/usr/bin/env python

import os
import sys
import json
import yaml
import requests
import urllib3
import copy
import optparse

nso_device='ios'

TheDevice = {
    "device": {
        "name": "ios",
        "address": "127.0.0.1",
        "port": 10022,
        "state": {
            "admin-state": "unlocked"
        },
        "authgroup": "default",
        "device-type": {
            "cli": {
                "ned-id": "tailf-ned-cisco-ios-id:cisco-ios"
            }
        }
    }
}

### print response =============================================================
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
  if nso_auth_data:
    auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
    ### RESTCONF definitions ---------------------------------------------------
    restconf_base_uri = "%s://%s:%s/restconf"%(nso_auth_data.get('nso_protocol',''),nso_auth_data.get('nso_ipaddress',''), nso_auth_data.get('nso_port',''))
    restconf_data_base_uri = "%s/data"%(restconf_base_uri)
    restconf_operations_base_uri = "%s/operations"%(restconf_base_uri)
    restconf_headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-data+json'}

    config = { 'config' : {} }

    ### FETCH HOST KEYS ========================================================
    uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/ssh/fetch-host-keys"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('POST',uri,response)

    ### SYNC-FROM NSO ==========================================================
    uri = restconf_data_base_uri + "/devices/device=" + nso_device + "/sync-from"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('POST',uri,response)


    ### DEVICE READ FROM NSO ===================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=config'
    response = requests.get(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('GET',uri,response)

    print(response.text)
    ### COPY RECEIVED DATA =====================================================
    received_json=copy.deepcopy(response.text)

#     ### DEVICE OPTIONS TO NSO ====================================================
#     uri = restconf_operations_base_uri + '/devices/device=' + nso_device
#     response = requests.options(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error(uri,response)
#
#     ### DEVICE WRITE TO NSO ====================================================
#     uri = restconf_operations_base_uri + '/devices/device=' + nso_device + '/config/'
#     response = requests.post(uri, auth=auth, headers=restconf_headers, data=json.dumps(TheDevice))
#     print_response_and_end_on_error(uri,response)


    ### ENCAPSULATE DATA =======================================================
    config['config'].update(TheDevice)
    #config['config'].update(json.dumps(received_json, indent=2))
    print('*'*80)
    print(json.dumps(config, indent=2))

    ### DEVICE WRITE TO NSO ====================================================
    with requests.Session() as s:
      s.auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
      s.headers.update(restconf_headers)
      s.verify = False
      uri = restconf_operations_base_uri + '/devices/device=' + nso_device
      response = s.post(uri, json=TheDevice)
      print_response_and_end_on_error('POST',uri,response)


    ### SYNC-TO NSO ============================================================
    uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/sync-to"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('POST',uri,response)

if __name__ == "__main__":
    main()
