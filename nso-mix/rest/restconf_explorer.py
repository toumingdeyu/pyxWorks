#!/usr/bin/env python

import json
import requests

nso_protocol='http'
nso_ipaddress='192.168.56.101'
nso_port='8080'
nso_user='localnso'
nso_password='1234!'
nso_device='ios2'

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

    ### REST definitions
    rest_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/api/running"
    rest_headers = {'Content-Type': 'application/vnd.yang.data+json'}
    restc_get_headers = {'accept': 'application/vnd.yang.data+json'}

    ### RESTCONF definitions
    restconf_base_uri = nso_protocol + "://" + nso_ipaddress + ":" + nso_port + "/restconf"
    restconf_data_base_uri = restconf_base_uri + "/data"
    restconf_operations_base_uri = restconf_base_uri + "/operations"
    restconf_headers = {'Content-Type': 'application/yang-data+json'}
    restconf_get_headers = {'accept': 'application/yang-data+json'}

    #http://localhost:8080/restconf/operations?content=config
    uri=restconf_base_uri + '?content=all'
    response = requests.get(uri, auth=auth, headers=restconf_get_headers)
    print('='*80)
    print('GET',uri,' | ',response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)

    #http://localhost:8080/restconf/data?content=config
    uri=restconf_data_base_uri + '?content=config'
    response = requests.get(uri, auth=auth, headers=restconf_get_headers)
    print('='*80)
    print('GET',uri,' | ',response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)

    #http://localhost:8080/restconf/data?content=nonconfig
    uri=restconf_data_base_uri + '?content=nonconfig'
    response = requests.get(uri, auth=auth, headers=restconf_get_headers)
    print('='*80)
    print('GET',uri,' | ',response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)

    #http://localhost:8080/restconf/operations?content=all
#     uri=restconf_data_base_uri + '?content=all'
#     response = requests.get(uri, auth=auth, headers=restconf_get_headers)
#     print('='*80)
#     print('GET',uri,' | ',response)
#     print('-'*80)
#     print(response.headers)
#     print('-'*80)
#     print(response.text)

    #http://localhost:8080/restconf/operations?content=config
    uri=restconf_operations_base_uri + '?content=all'
    response = requests.get(uri, auth=auth, headers=restconf_get_headers)
    print('='*80)
    print('GET',uri,' | ',response)
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)

if __name__ == "__main__":
    main()
