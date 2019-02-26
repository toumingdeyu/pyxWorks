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

devicemodes=['all','config','nonconfig']
devicemode=devicemodes[1]
restconf_headers_list=['application/yang-data+json','application/yang-data+xml']
force_restconf_header=restconf_headers_list[1]

### commandline argumets handling ==============================================
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python  %s  nameOfDevice  all|config(=default)|nonconfig  json(=default)|xml" % (ScriptName))
  sys.exit(1)
else:
  nso_device=args[0]
  if len(sys.argv)>=3 and args[1] in devicemodes: devicemode=args[1]
  if len(sys.argv)>=4:
    for header in restconf_headers_list:
      if args[2] in header: force_restconf_header=header
print('DEVICE:',nso_device,'DEVICE_MODE:',devicemode,'HEADERS:',force_restconf_header )

### PRINT RESPONSE + ignorefail=True/False option ==============================
def print_response_and_end_on_error(method,uri,response,ignorefail=False):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    print('-'*80)
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
    restconf_headers = {'accept': force_restconf_header, 'content-type': force_restconf_header}

    ### DEVICE READ FROM NSO ===================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content='+devicemode
    response = requests.get(uri, auth=auth, headers=restconf_headers)
    print_response_and_end_on_error('GET',uri,response)

    ### WRITE FILE WITH TIMESTAMP ==============================================
    now = datetime.datetime.now()
    timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
    if 'xml' in force_restconf_header: filetype='xml'
    else: filetype='json'
    with open(nso_device+'_'+devicemode+'_'+timestring+'.'+filetype, 'w', encoding='utf8') as outfile:
      outfile.write(response.text)
      outfile.close()

if __name__ == "__main__": main()
