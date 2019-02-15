#!/usr/bin/env python

import os
import sys
import json
import yaml
import requests
import urllib3
import copy
import optparse

### commandline argumets handling ==============================================
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s nameOfDeviceToDelete" % (ScriptName))
  sys.exit(1)
else:
  nso_device=args[0]

### PRINT RESPONSE + ignorefail=True/False option ==============================
def print_response_and_end_on_error(method,uri,response,ignorefail=False):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    if not ignorefail and int(response.status_code)>=400: sys.exit(0)

### main =======================================================================
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

    ### DELETE DEVICE FROM NSO =================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device
    response = requests.delete(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('DELETE',uri,response)

if __name__ == "__main__": main()
