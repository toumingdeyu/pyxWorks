#!/usr/bin/env python
ScriptAuthor='peter.nemec@orange.com'
ScriptVersion='v1.00'

import io
import os
import sys
import json
import yaml
import requests
import urllib3
import copy
import argparse
import xmltodict
#from bs4 import BeautifulSoup
#from xml.dom.minidom import parseString
#from xml.etree import ElementTree
import collections
import datetime
import xml.dom.minidom
from ncclient import manager

usage_text='''
BASIC EXAMPLE OF NETCONF CLIENT...

'''
urllib3.disable_warnings()


### ARGPARSE ###################################################################
ScriptName=sys.argv[0]
print('AppName:',ScriptName,', created by',ScriptAuthor,',',ScriptVersion,'\n')
parser = argparse.ArgumentParser()
#parser.add_argument("-a", "--action", action="store",choices=['c','r','p','d','create', 'read', 'patch', 'delete'], default='read',
#                    help="action [c(reate), r(ead)[=default], p(atch), d(elete)]")
parser.add_argument("-v", "--verbose",action="store_true", default=False, help="set verbose mode")
aargs = parser.parse_args()
if aargs.verbose or len(sys.argv)<2: print('USAGE:',usage_text,'\nINPUT_PARAMS:',parser.parse_args())


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

### MAIN =======================================================================
def main():
  ### READ YAML NSO AUTH FILE --------------------------------------------------
  with open('./netconf_auth_data.yaml', 'r') as stream: netconf_auth_data = yaml.load(stream)
  if netconf_auth_data:

    m = manager.connect(host=netconf_auth_data.get('netconf_ipaddress'),
                        port=netconf_auth_data.get('netconf_ssh_port'),
                        username=netconf_auth_data.get('netconf_user'),
                        password=netconf_auth_data.get('netconf_password'))

    if aargs.verbose: print('CONNECTED:',m.connected)

    #GET CAPABILITIES
    print('CAPABILITIES:')
    for c in m.server_capabilities:
      if aargs.verbose: print(c)

    # GET RUNNING-CONFIG
    running_config = m.get_config('running')
    if aargs.verbose: print(xml.dom.minidom.parseString(str(running_config)).toprettyxml())

    # MAKE DICTIONARY from config
    conf_json = xmltodict.parse(str(running_config))
    print('DEVICE:',conf_json['rpc-reply']["data"]["devices"]['device'])

    m.close_session()

if __name__ == "__main__": main()
