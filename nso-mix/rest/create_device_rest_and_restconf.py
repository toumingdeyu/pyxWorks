#!/usr/bin/env python

import json
import requests

nso_protocol='http'
nso_ipaddress='192.168.56.101'
nso_port='8080'
nso_user='localnso'
nso_password='1234!'
nso_device='ios1'

TheDevice = {
    "device": {
        "name": "ios1",
        "address": "127.0.0.1",
        "port": 10021,
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

def main():
    auth = (nso_user, nso_password)
    rest_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/api/running"
    restconf_data_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/restconf/data"
    restconf_oper_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/restconf/operations"
    rest_headers = {'Content-Type': 'application/vnd.yang.data+json'}
    restconf_headers = {'Content-Type': 'application/yang-data+json'}


    uri=rest_base_uri + '/devices/device/'+nso_device
    response = requests.put(uri, auth=auth, headers=rest_headers, data=json.dumps(TheDevice))
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    uri=restconf_data_base_uri + '/devices/device='+nso_device
    response = requests.put(uri, auth=auth, headers=restconf_headers, data=json.dumps(TheDevice))
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)


    uri=rest_base_uri + "/devices/device/" + nso_device + "/ssh/_operations/fetch-host-keys"
    response = requests.post(uri, auth=auth, headers=rest_headers)
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    uri=restconf_oper_base_uri + "/devices/device=ios3/ssh/fetch-host-keys"
    response = requests.post(uri, auth=auth, headers=restconf_headers)
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)


    uri=rest_base_uri + "/devices/device/" + nso_device + "/_operations/sync-from"
    response = requests.post(uri, auth=auth, headers=rest_headers)
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    uri=restconf_oper_base_uri + "/devices/device=" + nso_device + "/sync-from"
    resp = requests.post(uri, auth=auth, headers=restconf_headers)
    print('='*80)
    print(uri,response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)


if __name__ == "__main__":
    main()
