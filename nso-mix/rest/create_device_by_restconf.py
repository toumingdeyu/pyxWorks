#!/usr/bin/env python

import os
import sys
import json
import requests
import urllib3
import copy

nso_protocol='http'
nso_ipaddress='192.168.56.101'
nso_port='8080'
nso_user='localnso'
nso_password='1234!'
nso_device='iosxr'

TheDevice = {
    "device": {
        "name": "ios2",
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

def print_response_and_end_on_error(method,uri,response):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    if int(response.status_code)>=400: sys.exit(0)

def main():
    auth = (nso_user, nso_password)

    ### REST definitions -------------------------------------------------------
    rest_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/api/running"
    rest_headers = {'Content-Type': 'application/vnd.yang.data+json'}
    restc_get_headers = {'accept': 'application/vnd.yang.data+json'}

    ### RESTCONF definitions ---------------------------------------------------
    restconf_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/restconf"
    restconf_data_base_uri = restconf_base_uri + "/data"
    restconf_operations_base_uri = restconf_base_uri + "/operations"
    restconf_headers = {'Content-Type': 'application/yang-data+json'}
    restconf_get_headers = {'accept': 'application/yang-data+json'}

    headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-data+json'}
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
    response = requests.get(uri, auth=auth, headers=restconf_get_headers)
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
      s.auth = (nso_user, nso_password)
      s.headers.update(headers)
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
