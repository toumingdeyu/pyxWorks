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
import xmltodict
from bs4 import BeautifulSoup
from xml.dom.minidom import parseString
from xml.etree import ElementTree
import collections

urllib3.disable_warnings()

auth=None
restconf_headers_list=['application/yang-data+json','application/yang-data+xml']
force_restconf_header=None

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python %s nameOfInputFile.json json/xml" % (ScriptName))
  sys.exit(1)
else:
  fileName=args[0]
  if len(sys.argv)>=3:
    for header in restconf_headers_list:
      if args[1] in header: force_restconf_header=header


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
        try: something_doubledot_key=str(key).split(':')[1]
        except: something_doubledot_key='element_never_exists'
        if json_key and (str(json_key)==str(key) or str(json_key)==str(something_doubledot_key)):
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
        #print(' L:')
        json_reference,add_json_deeper_references=get_json_dictionary_reference(dict_data,json_key,json_value)
        if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    elif type(json_data)==dict:
      json_reference,add_json_deeper_references=get_json_dictionary_reference(json_data,json_key,json_value)
      if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    return json_reference,json_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  #print('LOOKING_FOR:',json_key ,':', json_value, ', GET_VALUE:',get_value,'\n')
  json_reference_found=None
  references=[]
  references.append(json_data)
  while not json_reference_found and len(references)>0:
    json_reference_found,add_references=get_json_element_reference_one_level_down(references[0],json_key,json_value)
    references.remove(references[0])
    references=references+add_references
  del references
  return json_reference_found
  ### END OF GET_JSON_ELEMENT ==================================================

### GET_XML_ELEMENT ===========================================================
def get_xml_element(xml_data,xml_key=None,xml_value=None,get_value=False):
  """
  FUNCTION: get_xml_element_reference
  parameters: xml_data  - xml data structure
              xml_key   - optional wanted key
              xml_value - optional wanted value
              get_value  - optional , if True returns xml_value instead of reference
  returns: xml_reference_found - None or xml reference when element was found
  """
  ### SUBFUNCTION --------------------------------------------------------------
  def get_xml_dictionary_reference(xml_data,xml_key=None,xml_value=None):
    xml_reference=None
    xml_deeper_references=[]
    if type(xml_data)==dict or type(xml_data)==collections.OrderedDict:
      for key in xml_data.keys():
        if not '@xmlns' in key:
          #print('   D:',key,', SUB_TYPE:',type(xml_data.get(key)))
          try: something_doubledot_key=str(key).split(':')[1]
          except: something_doubledot_key='element_never_exists'
          if xml_key and (str(xml_key)==str(key) or str(xml_key)==str(something_doubledot_key)):
            if xml_value and str(xml_value)==str(xml_data.get(key)):
              if get_value: xml_reference=str(xml_data.get(key));break
              else: dictionary={};dictionary[key]=xml_data.get(key);xml_reference=dictionary;break
            elif not xml_value:
              if get_value: xml_reference=str(xml_data.get(key));break
              else: dictionary={};dictionary[key]=xml_data.get(key);xml_reference=dictionary;break
          if type(xml_data.get(key))==dict or type(xml_data)==collections.OrderedDict: xml_deeper_references.append(xml_data.get(key))
          elif type(xml_data.get(key))==list:
            for sub_xml in xml_data.get(key):
              if type(sub_xml)==dict or type(xml_data)==collections.OrderedDict: xml_deeper_references.append(sub_xml)
    return xml_reference,xml_deeper_references
  ### SUBFUNCTION --------------------------------------------------------------
  def get_xml_element_reference_one_level_down(xml_data,xml_key=None,xml_value=None):
    xml_reference=None
    xml_deeper_references=[]
    #print('TYPE:',type(xml_data))
    if type(xml_data)==list:
      for dict_data in xml_data:
        #print(' L:')
        xml_reference,add_xml_deeper_references=get_xml_dictionary_reference(dict_data,xml_key,xml_value)
        if len(add_xml_deeper_references)>0: xml_deeper_references=xml_deeper_references+add_xml_deeper_references
    elif type(xml_data)==dict or type(xml_data)==collections.OrderedDict:
      xml_reference,add_xml_deeper_references=get_xml_dictionary_reference(xml_data,xml_key,xml_value)
      if len(add_xml_deeper_references)>0: xml_deeper_references=xml_deeper_references+add_xml_deeper_references
    return xml_reference,xml_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  #print('LOOKING_FOR:',xml_key ,':', xml_value, ', GET_VALUE:',get_value,'\n')
  xml_reference_found=None
  references=[]
  references.append(xml_data)
  while not xml_reference_found and len(references)>0:
    xml_reference_found,add_references=get_xml_element_reference_one_level_down(references[0],xml_key,xml_value)
    references.remove(references[0])
    references=references+add_references
  del references
  return xml_reference_found
  ### END OF GET_XML_ELEMENT ==================================================

### ----------------------------------------------------------------------------
def dict2xml(dictionary):
  return xmltodict.unparse(dictionary)

### handle_http_requests START =================================================
def handle_requests(request_type,uri,datatosend=str(),debug=True,ignorefail=False):
  ### PRINT RESPONSE + ignorefail=True/False option ============================
  def print_response_and_end_on_error(method,uri,response,ignorefail=False):
    print('='*80)
    print(method,uri,'  |',response.status_code,'|')
    print('RESPONSE_HEADERS:',print(response.headers))
    print('RESPONSE:',)
    print('-'*80,'\n')
    print(response.text)
    print('-'*80,'\n')
    if not ignorefail and int(response.status_code)>=400: sys.exit(0)
  ### function start -----------------------------------------------------------
  if (restconf_headers and auth):
    with requests.Session() as session:
      session.auth = auth
      session.headers.update(restconf_headers)
      session.verify = False
      if request_type.upper() in 'GET':
        response = session.get(url=str(uri))
      elif request_type.upper() in 'POST':
        response = session.post(url=str(uri), data=str(datatosend))
      elif request_type.upper() in 'PUT':
        response = session.put(url=str(uri), data=str(datatosend))
      elif request_type.upper() in 'PATCH':
        response = session.patch(url=str(uri), data=str(datatosend))
      elif request_type.upper() in 'DELETE':
        response = session.delete(uri)
      if debug: print_response_and_end_on_error(request_type.upper(),uri,response,ignorefail=ignorefail)
      return response.text
  else:
    print('!!! restconf_headers and/or auth missing !!!')
    return None
  ### handle_http_requests END -------------------------------------------------

### MAIN =======================================================================
def main():
  global restconf_headers
  global auth
  ### READ YAML NSO AUTH FILE --------------------------------------------------
  with open('./nso_auth_data.yaml', 'r') as stream: nso_auth_data = yaml.load(stream)
  if nso_auth_data:
    ### RESTCONF definitions ---------------------------------------------------
    auth = (nso_auth_data.get('nso_user','admin'), nso_auth_data.get('nso_password','admin'))
    if force_restconf_header: restconf_headers = {'accept': force_restconf_header, 'content-type': force_restconf_header}
    else: restconf_headers = {'accept': nso_auth_data.get('headers',''), 'content-type': nso_auth_data.get('headers','')}
    restconf_base_uri = "%s://%s:%s/restconf"%(nso_auth_data.get('nso_protocol',''),nso_auth_data.get('nso_ipaddress',''), nso_auth_data.get('nso_port',''))
    restconf_data_base_uri = "%s/data"%(restconf_base_uri)
    restconf_operations_base_uri = "%s/operations"%(restconf_base_uri)

  ### READ JSON FILE -----------------------------------------------------------
  if '.json' in fileName:
    with io.open(fileName) as json_file: json_raw_data = json.load(json_file)
    if json_raw_data:
      nso_device=get_json_element(json_raw_data,'name',get_value=True)
      print('DEVICE =',nso_device)
      json_device_data=get_json_element(json_raw_data,'config')
      if 'json' in restconf_headers.get('content-type'):
        device_data=json.dumps(json_device_data)
        print('HEADERS:',restconf_headers,'\nDATA:',device_data)
      elif 'xml' in restconf_headers.get('content-type'):
        device_data=dict2xml(json_device_data)
        xml_root_element = ElementTree.fromstring(device_data)
        #xml_root_element.set("xmlns", "http://tail-f.com/ned/cisco-ios-xr")
        device_data=parseString(ElementTree.tostring(xml_root_element)).toxml()
        device_data_pretty = BeautifulSoup(device_data, 'xml').prettify()
        print('HEADERS:',restconf_headers,'\nDATA:',device_data_pretty)
  elif '.xml' in fileName:
    with io.open(fileName) as xml_file: xml_raw_data = xmltodict.parse(xml_file.read())
    if xml_raw_data:
      nso_device=get_xml_element(xml_raw_data,'name',get_value=True)
      print('DEVICE =',nso_device)
      xml_device_data=get_xml_element(xml_raw_data,'config')
      if 'xml' in restconf_headers.get('content-type'):
        device_data=xmltodict.unparse(xml_device_data)
        print('HEADERS:',restconf_headers,'\nDATA:',device_data)
      elif 'json' in restconf_headers.get('content-type'):
        device_data=json.dumps(xml_raw_data)
        print('HEADERS:',restconf_headers,'\nDATA:',device_data)

  #exit(0)

  if nso_auth_data:

    ### DEVICE WRITE TO NSO ====================================================
    uri = restconf_data_base_uri + '/devices/device=' + nso_device + '/config/'
    handle_requests('PATCH',uri,device_data)

#     ### FETCH HOST KEYS ========================================================
#     uri = restconf_operations_base_uri + "/devices/device=" + nso_device + "/ssh/fetch-host-keys"
#     handle_requests('POST',uri)
#
#     ### SYNC-FROM NSO ==========================================================
#     uri = restconf_data_base_uri + "/devices/device=" + nso_device + "/sync-from"
#     handle_requests('POST',uri,ignorefail=True)
#     ### SYNC-TO NSO ============================================================
#     uri = restconf_data_base_uri + "/devices/device=" + nso_device + "/sync-to"
#     handle_requests('POST',uri)

if __name__ == "__main__": main()
