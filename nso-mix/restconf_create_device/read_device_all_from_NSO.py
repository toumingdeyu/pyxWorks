#!/usr/bin/env python

import io
import os
import sys
import json
import yaml
import requests
import urllib3
import optparse
import datetime

### commandline argumets handling ==============================================
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s nameOfDevice" % (ScriptName))
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

    ### DEVICE READ FROM NSO ===================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=all'
    response = requests.get(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('GET',uri,response)

    ### WRITE FILE WITH TIMESTAMP ==============================================
    now = datetime.datetime.now()
    timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
    with open(nso_device+'_all_'+timestring+'.json', 'w', encoding='utf8') as outfile:
      #json.dump(response.text, outfile,  indent=4)
      outfile.write(response.text)
      outfile.close()

if __name__ == "__main__": main()
