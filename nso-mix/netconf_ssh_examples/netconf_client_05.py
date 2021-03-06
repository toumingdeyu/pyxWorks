#!/home/pnemec/Python-3.7.2/python
#!/usr/bin/python36
#/home/pnemec/Python-3.7.2/Tools/msi
ScriptAuthor='peter.nemec@orange.com'
ScriptVersion='v1.00'

import io
import os
import sys
import warnings
import json
import yaml
import requests
import urllib3
import copy
import argparse
import xmltodict
import collections
import datetime
import xml.dom.minidom
from ncclient import manager
from lxml import etree
from xmldiff import formatting
from xmldiff import main as xdmain
import difflib

warnings.simplefilter("ignore", DeprecationWarning)

netconf_auth_data_yaml='''
netconf_user: pnemec
netconf_password:
netconf_ipaddress: 127.0.0.1
netconf_ssh_port: 22224
'''

# NSO     2022  V_NSO   22221
# IOS-XR  22    OAKPE3  22222
# IOS-XE  22    NYKPE5  22223
# JUNOS   22    SINCR5  22224
# IOS-XE  830   NYKPE5  22225
# IOS-XE  22    ABIGW1  22226
# IOS-XE  830   ABIGW1  22227

usage_text='''
BASIC EXAMPLE OF NETCONF CLIENT...

'''
urllib3.disable_warnings()


### ARGPARSE ###################################################################
ScriptName=sys.argv[0]
print('AppName:',ScriptName,', created by',ScriptAuthor,',',ScriptVersion,'\n')
parser = argparse.ArgumentParser()

#parser.add_argument("-if", "--inputfile", action="store", default='',help="input xml file")
#parser.add_argument("-wrc", "--writerunningconfig",action="store_true", default=False, help="write file to device running-config ")
parser.add_argument("-y", "--yamlauthfile", action="store", default='',help="yaml auth file (netconf_user,netconf_password,netconf_ipaddress,netconf_ssh_port)")
parser.add_argument("-nusr", "--netconfusername", action="store", default='',help="override/insert netconf username")
parser.add_argument("-npwd", "--netconfpassword", action="store", default='',help="override/insert netconf password")
parser.add_argument("-naddr", "--netconfaddress", action="store", default='',help="override/insert netconf url/ip address")
parser.add_argument("-p", "--netconfport", action="store", default='',help="override/insert netconf port")
parser.add_argument("-dt", "--devicetype", action="store", default='',choices=['j','c','n','h','junos','csr','nexus','huawei'],help="force device type [(j)unos,(c)sr,(n)exus,(h)uawei]")
parser.add_argument("-gca", "--getcapabilities",action="store_true", default=False, help="get capabilities to file")
parser.add_argument("-grc", "--getrunningconfig",action="store_true", default=False, help="get running-config to file")
parser.add_argument("-gcc", "--getcandidateconfig",action="store_true", default=False, help="get candidate-config to file")
parser.add_argument("-cwf", "--comparewithfile", action="store", default='',help="compare with xml file")
#parser.add_argument("-cwr", "--comparewithrollback", action="store", default='',help="compare config with number of rollbacks")
parser.add_argument("-x", "--xpathexpression", action="store", default=str(),help="xpath expression")
parser.add_argument("-g", "--getdata",action="store_true", default=False, help="get data to file")
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

### RECOGNISE DEVICE TYPE ======================================================
def get_device_type(nhost,nport,nusername,npassword):
  device_type=None
  with manager.connect_ssh(host=nhost,port=nport,username=nusername,password=npassword,
                           device_params=None,timeout=10,allow_agent=False,
                           look_for_keys=False,hostkey_verify=False ) as m:
    if aargs.verbose: print('CAPABILITIES:',list(m.server_capabilities))
    for c in m.server_capabilities:
      #if 'TAILF-NCS' in c.upper(): device_type='nso'; break;
      if 'JUNIPER' in c.upper(): device_type='junos'; break;
      if 'NX-OS' in c.upper(): device_type='nexus'; break;
      if 'Cisco-IOS-XR' in c: device_type='csr'; break;
      if 'HUAWEI' in c.upper(): device_type='huawei'; break;
    print('RECOGNISED DEVICE TYPE:',device_type)
    return device_type

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
  ### AUTHORIZATION - READ YAML NETCONF AUTH FILE OR INPUT PARAMETERS-----------
  if aargs.yamlauthfile:
    with open(aargs.yamlauthfile, 'r') as stream: netconf_auth_data = yaml.load(stream)
  if not netconf_auth_data: netconf_auth_data = yaml.load(netconf_auth_data_yaml)
  nhost=netconf_auth_data.get('netconf_ipaddress','')
  nport=netconf_auth_data.get('netconf_ssh_port','')
  nusername=netconf_auth_data.get('netconf_user','')
  npassword=netconf_auth_data.get('netconf_password','')
  ### OVERDIDE/INSERT INPUT PARAMETERS -----------------------------------------
  if aargs.netconfusername: nusername=aargs.netconfusername
  if aargs.netconfpassword: npassword=aargs.netconfpassword
  if aargs.netconfaddress: nhost=aargs.netconfaddress
  if aargs.netconfport: nport=aargs.netconfport
  ### NETCONF CONNECT ----------------------------------------------------------
  print('HOST:',nhost,'PORT:',nport,'USER:',nusername,'PASSWORD:', 'YES' if npassword else '-')
  if nhost and nport and nusername and npassword:
    recognised_dev_type=get_device_type(nhost,nport,nusername,npassword)
    if not aargs.devicetype and recognised_dev_type: device_params={'name':recognised_dev_type}
    with manager.connect_ssh(host=nhost,port=nport,username=nusername,password=npassword,
                             device_params=device_params,timeout=10,allow_agent=False,
                             look_for_keys=False,hostkey_verify=False ) as m:
        print('CONNECTED:',m.connected)
        if aargs.verbose: print('CAPABILITIES:',list(m.server_capabilities))
        ### WRITE CAPABILITIES TO FILE -----------------------------------------
        if aargs.getcapabilities:
          file_name='capabilities_'+timestring+'.txt'
          with open(file_name, 'w', encoding='utf8') as outfile:
            for c in m.server_capabilities: outfile.write(str(c)+'\n')
            print('Writing capabilities to file:',file_name)

#         ### COMPARE CONFIG WITH ROLLBACK =======================================
#         #https://programtalk.com/vs2/?source=python/9054/ncclient/examples/juniper/command-jnpr.py
#         if aargs.comparewithrollback:
#           compare_config = m.compare_configuration(rollback=aargs.comparewithrollback)
#           print(compare_config.tostring)

        ### GET RUNNING CONFIG =================================================
        if (aargs.getrunningconfig or aargs.getcandidateconfig) and aargs.comparewithfile:
          if aargs.xpathexpression: rx_config = m.get_config(source='candidate' if aargs.getcandidateconfig else 'running',filter=('xpath',aargs.xpathexpression)).data_xml
          else: rx_config=m.get_config(source='candidate' if aargs.getcandidateconfig else 'running').data_xml
          if aargs.verbose: print('\n%s_CONFIG:\n'%(('candidate' if aargs.getcandidateconfig else 'running').upper() ),
                                  str(rx_config) if '\n' in rx_config else xml.dom.minidom.parseString(str(rx_config)).toprettyxml())
          file_name=('candidate' if aargs.getcandidateconfig else 'running')+'_config_'+timestring+'.xml'
          with open(file_name, 'w', encoding='utf8') as outfile:
            outfile.write(str(rx_config)) if '\n' in rx_config else outfile.write(xml.dom.minidom.parseString(str(rx_config)).toprettyxml())
            print('Writing %s-config %s to file:'%('candidate' if aargs.getcandidateconfig else 'running','XPATH='+aargs.xpathexpression if aargs.xpathexpression else ''),file_name)
          ### DO FILE DIFF -----------------------------------------------------
          if aargs.comparewithfile:
            with open(aargs.comparewithfile, 'r') as pre:
              with open(file_name, 'r') as post:
                with open('file-diff_'+timestring+'.txt', 'w', encoding='utf8') as outfile:
                  print_string='\nPRE='+aargs.comparewithfile+', POST='+file_name+' FILE-DIFF:'+'\n'+80*('-')+'\n'
                  print(print_string);outfile.write(print_string)
                  diff = difflib.unified_diff(pre.readlines(),post.readlines(),fromfile='PRE',tofile='POST',n=0)
                  for line in diff: print(line.replace('\n',''));outfile.write(line)
                  print_string='\n'+80*('-')+'\n';print(print_string);outfile.write(print_string)


        #https://programtalk.com/python-examples/ncclient.manager.connect/
        ### GET DATA ===========================================================
        if aargs.getdata:
          rx_data = m.get() if not aargs.xpathexpression else m.get(filter=('xpath',aargs.xpathexpression))
          if aargs.verbose: print('\nRECIEVED_DATA%s:\n'%(('(XPATH='+aargs.xpathexpression+')' if aargs.xpathexpression else '').upper() ),
                                  str(rx_config) if '\n' in rx_config else xml.dom.minidom.parseString(str(rx_config)).toprettyxml())
          file_name='data'+aargs.xpathexpression.replace('/','_')+'_get_'+timestring+'.xml'
          with open(file_name, 'w', encoding='utf8') as outfile:
            outfile.write(str(rx_data)) #if '\n' in rx_data else outfile.write(xml.dom.minidom.parseString(str(rx_data)).toprettyxml())
            print('Writing data %s to file:'%('(XPATH='+aargs.xpathexpression+')' if aargs.xpathexpression else ''),file_name)

        ### COMMAND LISTS ------------------------------------------------------
        CMD_IOS_XE_CMDS = [
                "show version",
                "show running-config",
                "show isis neighbors",
                "show mpls ldp neighbor",
                "show ip interface brief",
                "show ip route summary",
                "show crypto isakmp sa",
                "show crypto ipsec sa count",
                "show crypto eli"
                ]

        CMD_IOS_XR_CMDS = [
                "show system verify report",
                "show version",
                "show running-config",
                "admin show running-config",
                "show processes cpu | utility head count 3",
                "show isis interface brief",
                "show isis neighbors | utility cut -d " " -f -27",
                "show mpls ldp neighbor brief",
                "show interface brief",
                "show bgp sessions",
                "show route summary",
                "show l2vpn xconnect group group1",
                "admin show platform",
                "show inventory"
                ]

        JUNOS_CMDS = [
                "show version",
      			"show system software",
      			"show configuration",
      			"show interfaces terse",
      			"show isis adjacency",
      			"show ldp session brief",
      			"show ldp neighbor",
      			"show bgp summary",
      			"show rsvp neighbor",
      			"show pim neighbors",
      			"show l2vpn connections summary",
      			"show chassis routing-engine",
      			"show chassis fpc",
      			"show chassis fpc pic-status",
      			"show chassis power",
      			"show system alarms",
                "show system users",
        		]

        ### JUNOS TEXT-DIFFERENCE ==============================================
        file_name=str(recognised_dev_type)+'_all_'+timestring+'.txt'
        if recognised_dev_type=='junos': CMDS=JUNOS_CMDS
        elif recognised_dev_type=='csr': CMDS=CMD_IOS_XR_CMDS
        else: CMDS=CMD_IOS_XE_CMDS
        ### --------------------------------------------------------------------
        if CMDS:
          with open(file_name, 'w', encoding='utf8') as outfile:
            for command in CMDS:
              result=m.command(command=command, format='text')
              print('COMMAND: '+command)
              if aargs.verbose: print(str(result)+'\n')
              outfile.write('\nCOMMAND: '+command+'\n'+str(result)+'\n')
          ### DO FILE DIFF -----------------------------------------------------
          if aargs.comparewithfile:
            with open(aargs.comparewithfile, 'r') as pre:
              with open(file_name, 'r') as post:
                with open('file-diff_'+timestring+'.txt', 'w', encoding='utf8') as outfile:
                  print_string='\nPRE='+aargs.comparewithfile+', POST='+file_name+' FILE-DIFF:'+'\n'+80*('-')+'\n'
                  print(print_string);outfile.write(print_string)
                  diff = difflib.unified_diff(pre.readlines(),post.readlines(),fromfile='PRE',tofile='POST',n=0)
                  for line in diff: print(line.replace('\n',''));outfile.write(line)
                  print_string='\n'+80*('-')+'\n';print(print_string);outfile.write(print_string)
        ### END OF JUNOS TEXT-DIFFERENCE =======================================




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
