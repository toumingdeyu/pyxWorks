#!/usr/bin/python
### use python3

import sys
import os
import io
import optparse
import json
import yaml
import xmltodict
import requests
import base64
from requests.auth import HTTPBasicAuth

#curl -i -X POST http://localhost:8080/api/operations/devices/device/c0/sync-from -u admin:admin
#url= "http://192.168.56.101:8080/restconf/data/services"
url= "http://192.168.56.101:8080/api/running/devices"


### commandline argumets handling
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 3:
  print("SYNTAX: python %s nsouser nsopassword" % (ScriptName))
  sys.exit(1)
else:
  nsouser=args[0]
  nsopasswd=args[1]

### Read XML file
def read_XML_file():
  xml=''
  with open(fileName, 'r') as f:
    str=f.read()
    variables = xmltodict.parse(str)
  return variables

## read JSON file
def read_JSON_file():
  variables={}
  with io.open(fileName) as json_file:
    variables = json.load(json_file)
  return variables

## Write YAML file
def write_YAML_file(variables):
  with io.open(fileName+'.yaml', 'w', encoding='utf8') as outfile:
    yaml.dump(variables, outfile, default_flow_style=False, allow_unicode=True)

### Read YAML file
def read_YAML_file():
  with open(fileName, 'r') as stream:
    variables = yaml.load(stream)
    return variables

### Write JSON file
def write_JSON_file(variables):
  with io.open(fileName+'.json', 'w', encoding='utf8') as outfile:
    json.dump(variables, outfile,  indent=4)

### get HTTP response
def get_response(url):
#   import urllib.request, json
#   request = urllib.request(url)
#   base64string = base64.b64encode('%s:%s' % (nsouser, nsopasswd))
#   request.add_header("Authorization", "Basic %s" % base64string)
#   result = urllib.urlopen(request)
#   print(result)
# #   with urllib.request.urlopen(url, auth=(nsouser, nsopasswd)) as url:
# #     data = json.loads(url.read().decode())
# #     print(data)

  response = requests.get(url,auth=(nsouser, nsopasswd))
  #if response.status_code != 200: raise ApiError('GET /tasks/ {}'.format(response.status_code))
  print('-'*80)
  print(response.headers)
  print('-'*80)
  print(response.text)
  print('-'*80)
#   try:
#     print(response.json())
#   except:
#      variables = xmltodict.parse(response.text)
#      print(variables)
#      print('-'*80)
#      print(json.dump(variables))
#   print('-'*80)


### main -----------------------------------------------------------------------
def main(argv):
  #print(read_JSON_file())
  #write_YAML_file(read_JSON_file())
  #print(read_YAML_file())
  #write_JSON_file(read_YAML_file())
  get_response(url)

if __name__ == "__main__":
  main(sys.argv[1:])