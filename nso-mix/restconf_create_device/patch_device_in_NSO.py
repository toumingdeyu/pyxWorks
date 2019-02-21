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

### PRINT RESPONSE + ignorefail=True/False option ==============================
def print_response_and_end_on_error(method,uri,response,ignorefail=False):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('-'*80)
    print(response.headers)
    print('-'*80)
    print(response.text)
    if not ignorefail and int(response.status_code)>=400: sys.exit(0)

### GET_JSON_ELEMENT ===========================================================
def get_json_element(json_data,json_key=None,json_value=None,get_value=False):
  """
  FUNCTION: get_json_element_reference
  parameters: json_data  - json data structure
              json_key   - optional wanted key
              json_value - optional wanted value
              get_value  - optional , if True returns json_value instead of reference
  returns: json_reference_found - None or json reference when element was found
  """
  ### SUBFUNCTION --------------------------------------------------------------
  def get_json_dictionary_reference(json_data,json_key=None,json_value=None):
    json_reference=None
    json_deeper_references=[]
    if type(json_data)==dict:
      for key in json_data.keys():
        #print('   D:',key,', SUB_TYPE:',type(json_data.get(key)))
        if json_key and (json_key==key or ':'+str(json_key) in str(key)):
          if json_value and str(json_value)==str(json_data.get(key)):
            if get_value: json_reference=str(json_data.get(key));break
            else: dictionary={};dictionary[key]=json_data.get(key);json_reference=dictionary;break
          elif not json_value:
            if get_value: json_reference=str(json_data.get(key));break
            else: dictionary={};dictionary[key]=json_data.get(key);json_reference=dictionary;break
        if type(json_data.get(key))==dict: json_deeper_references.append(json_data.get(key))
        elif type(json_data.get(key))==list:
          for sub_json in json_data.get(key):
            if type(sub_json)==dict: json_deeper_references.append(sub_json)
    return json_reference,json_deeper_references
  ### SUBFUNCTION --------------------------------------------------------------
  def get_json_element_reference_one_level_down(json_data,json_key=None,json_value=None):
    json_reference=None
    json_deeper_references=[]
    #print('TYPE:',type(json_data))
    if type(json_data)==list:
      for dict_data in json_data:
        print(' L:')
        json_reference,add_json_deeper_references=get_json_dictionary_reference(dict_data,json_key,json_value)
        if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    elif type(json_data)==dict:
      json_reference,add_json_deeper_references=get_json_dictionary_reference(json_data,json_key,json_value)
      if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    return json_reference,json_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  json_reference_found=None
  references=[]
  references.append(json_data)
  while not json_reference_found and len(references)>0:
    json_reference_found,add_references=get_json_element_reference_one_level_down(references[0],json_key,json_value)
    references.remove(references[0])
    references=references+add_references
  del references
  #print(50*'-','\nFOUND:',json_key ,':', json_value, '\nGET_VALUE:',get_value)
  return json_reference_found
  ### END OF GET_JSON_ELEMENT ==================================================

### MAIN =======================================================================
def main():
  ### READ YAML NSO AUTH FILE --------------------------------------------------
  with open('./nso_auth_data.yaml', 'r') as stream: nso_auth_data = yaml.load(stream)
  if nso_auth_data:
    ### RESTCONF definitions ---------------------------------------------------
    auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
    restconf_base_uri = "%s://%s:%s/restconf"%(nso_auth_data.get('nso_protocol',''),nso_auth_data.get('nso_ipaddress',''), nso_auth_data.get('nso_port',''))
    restconf_data_base_uri = "%s/data"%(restconf_base_uri)
    restconf_operations_base_uri = "%s/operations"%(restconf_base_uri)
    restconf_headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-data+json'}        #, 'charset=utf-8'}
    restconf_patch_headers = {'accept': 'application/yang-data+json', 'content-type': 'application/yang-patch+json'} #, 'charset=utf-8' }

  ### READ JSON FILE -----------------------------------------------------------
  with io.open(fileName) as json_file: json_raw_data = json.load(json_file)
  if nso_auth_data and json_raw_data:
    nso_device=get_json_element(json_raw_data,'name',get_value=True)
    print('DEVICE =',nso_device)
    json_device_data=get_json_element(json_raw_data,'device')

#     ### FETCH HOST KEYS ========================================================
#     uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/ssh/fetch-host-keys"
#     response = requests.post(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('POST',uri,response)

#     ### DEVICE READ FROM NSO ===================================================
#     uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=config'
#     response = requests.get(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('GET',uri,response)

    ### DEVICE WRITE TO NSO ====================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device
    response = requests.patch(uri, auth=auth, headers=restconf_headers, data=json.dumps(json_device_data))
    print_response_and_end_on_error('PATCH',uri,response)

#     ### DEVICE READ FROM NSO ===================================================
#     uri = restconf_data_base_uri + '/devices/device=' + nso_device + '?content=config'
#     response = requests.get(uri, auth=auth, headers=restconf_headers)
#     print_response_and_end_on_error('GET',uri,response)

if __name__ == "__main__":
    main()
