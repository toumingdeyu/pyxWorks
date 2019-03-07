#!/home/pnemec/Python-3.7.2/python
#!/usr/bin/python36
#/home/pnemec/Python-3.7.2/Tools/msi
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

from lxml import etree
from xmldiff import formatting
from xmldiff import main as xdmain
import difflib


netconf_auth_data_yaml='''
netconf_user: pnemec
netconf_password:
netconf_ipaddress: 127.0.0.1
netconf_ssh_port: 22222
'''

usage_text='''
BASIC EXAMPLE OF NETCONF CLIENT...

'''
urllib3.disable_warnings()


### ARGPARSE ###################################################################
ScriptName=sys.argv[0]
print('AppName:',ScriptName,', created by',ScriptAuthor,',',ScriptVersion,'\n')
parser = argparse.ArgumentParser()

parser.add_argument("-cwf", "--comparewithfile", action="store", default='',help="compare with xml file")
#parser.add_argument("-if", "--inputfile", action="store", default='',help="input xml file")
#parser.add_argument("-wrc", "--writerunningconfig",action="store_true", default=False, help="write file to device running-config ")
parser.add_argument("-cwr", "--comparewithrollback", action="store", default='',help="compare config with number of rollbacks")
parser.add_argument("-x", "--xpathexpression", action="store", default='/',help="xpath expression")
parser.add_argument("-gca", "--getcapabilities",action="store_true", default=False, help="get capabilities to file")
parser.add_argument("-grc", "--getrunningconfig",action="store_true", default=False, help="get running-config to file")
parser.add_argument("-gall", "--getall",action="store_true", default=False, help="get all to file")
parser.add_argument("-dt", "--devicetype", action="store", default='',choices=['j','c','n','h','junos','csr','nexus','huavei'],help="force device type [(j)unos,(c)sr,(n)exus,(h)uavei]")
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
  now = datetime.datetime.now()
  timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
  device_params=None
  netconf_auth_data=None
  if aargs.devicetype in ['j','c','n','h','junos','csr','nexus','huawei']:
    device_params={'name':aargs.devicetype} if len(aargs.devicetype)>1 else None
    device_params={'name':'junos'} if not device_params and aargs.devicetype=='j' else None
    device_params={'name':'csr'} if not device_params and aargs.devicetype=='c' else None
    device_params={'name':'nexus'} if not device_params and aargs.devicetype=='n' else None
    device_params={'name':'huawei'} if not device_params and aargs.devicetype=='h' else None
    device_params={'name': 'default'} if not device_params else {'name': 'default'}
  ### READ YAML NETCONF AUTH FILE ----------------------------------------------
  #with open('./netconf_auth_data.yaml', 'r') as stream: netconf_auth_data = yaml.load(stream)
  if not netconf_auth_data: netconf_auth_data = yaml.load(netconf_auth_data_yaml)
  if netconf_auth_data:
    with manager.connect_ssh(host=netconf_auth_data.get('netconf_ipaddress'),
                             port=netconf_auth_data.get('netconf_ssh_port'),
                             username=netconf_auth_data.get('netconf_user'),
                             password=netconf_auth_data.get('netconf_password'),
                             device_params=device_params,
                             timeout=10,
                             allow_agent=False, look_for_keys=False,
                             hostkey_verify=False ) as m:
        print('CONNECTED:',m.connected)
        if aargs.verbose:
          print('CAPABILITIES:')
          for c in m.server_capabilities: print(c)
        ### WRITE CAPABILITIES TO FILE -----------------------------------------
        if aargs.getcapabilities:
          file_name='capabilities_'+timestring+'.xml'
          with open(file_name, 'w', encoding='utf8') as outfile:
            for c in m.server_capabilities: outfile.write(str(c)+'\n')
            print('Writing capabilities to file:',file_name)

        ### COMPARE CONFIG WITH ROLLBACK =======================================
        #https://programtalk.com/vs2/?source=python/9054/ncclient/examples/juniper/command-jnpr.py
        if aargs.comparewithrollback:
          compare_config = m.compare_configuration(rollback=int(aargs.comparewithrollback))
          print(compare_config.tostring)


        ### GET RUNNING CONFIG =================================================
        if aargs.getrunningconfig or aargs.comparewithfile:
          running_config = m.get_config('running').data_xml
          if aargs.verbose: print('\nRUNNING_CONFIG:\n',xml.dom.minidom.parseString(str(running_config)).toprettyxml())
          file_name='running_config_'+timestring+'.xml'
          with open(file_name, 'w', encoding='utf8') as outfile:
            if '\n' in running_config: outfile.write(str(running_config))
            else: outfile.write(xml.dom.minidom.parseString(str(running_config)).toprettyxml())
            print('Writing running-config to file:',file_name)
          ### DO FILE DIFF -----------------------------------------------------
          if aargs.comparewithfile:
            with open(aargs.comparewithfile, 'r') as pre:
              with open(file_name, 'r') as post:
                diff = difflib.unified_diff(pre.readlines(),post.readlines(),fromfile='PRE',tofile='POST',n=0)
                for line in diff: print(line.replace('\n',''))


#https://programtalk.com/python-examples/ncclient.manager.connect/

        ### GET ALL ============================================================
        if aargs.getall:
          #reply = connection.get(filter='<nc:filter type="xpath" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:tm="http://example.net/turing-machine" select="/tm:turing-machine/transition-function/delta" />')
          #filter=('subtree', "<interfaces-state/>")
          #https://ncclient.readthedocs.io/en/latest/manager.html#filter-params
          #rpc_reply = m.get(filter=('subtree', "<interfaces-state/>"))
          #data = m.get(filter=('xpath', aargs.xpathexpression))
          #data = m.get(filter='<nc:filter type="xpath" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:tm="http://example.net/turing-machine" select="/tm:turing-machine/transition-function/delta" />')

          data = m.get(filter=('subtree', "<interfaces-state/>"))
          if aargs.verbose: print('\nXPATH:\n',xml.dom.minidom.parseString(str(data)).toprettyxml())
          file_name='all_'+timestring+'.xml'
          if '\n' in running_config:
            with open(file_name, 'w', encoding='utf8') as outfile:
              outfile.write(str(data))
              print('Writing all to file:',file_name)
          else:
            with open(file_name, 'w', encoding='utf8') as outfile:
              outfile.write(xml.dom.minidom.parseString(str(data)).toprettyxml())
              print('Writing all to file:',file_name)






#         ### WRITE RUNNING CONFIG TO DEVICE =====================================
#         if aargs.writerunningconfig and aargs.inputfile:
#           assert(":url" in m.server_capabilities)
#           with m.locked("running"):
#             now = datetime.datetime.now()
#             timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
#             file_name='running_config_'+timestring+'.xml'
#             m.copy_config(source="running", target="file:///"+'bckp_'+file_name)
#             m.copy_config(source="file:///"+aargs.inputfile , target="running")
#             print('Writing running-config(%s) to device(%s).'%(file_name,netconf_auth_data.get('netconf_ipaddress')))
#           exit(0)

#         # MAKE DICTIONARY from config
#         conf_json = xmltodict.parse(str(running_config))
#         print('DEVICE:',conf_json['rpc-reply']["data"]["devices"]['device'])

if __name__ == "__main__": main()
