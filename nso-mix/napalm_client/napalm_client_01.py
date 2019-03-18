#!/home/pnemec/Python-3.7.2/python
#!/usr/bin/python36
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
#from lxml import etree
import difflib
from xml.etree import ElementTree
import napalm

warnings.simplefilter("ignore", DeprecationWarning)

### Highest AUTH priority have cmdline parameters, then external yaml file, last internal napalm_auth_data_yaml
napalm_auth_data_yaml='''
username: pnemec
password:
address: 127.0.0.1
port: 22222
'''

usage_text='''NAPALM CLIENT {}, created by {}, {}
for more info please type: python napalm_client_07.py -h

MAKING OF PRECHECK FILE:
python {}

MAKING OF POST CHECK:
python {} -cwf file.xml
'''.format(sys.argv[0],ScriptAuthor,ScriptVersion,sys.argv[0],sys.argv[0])

urllib3.disable_warnings()
now = datetime.datetime.now()
timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)

### ARGPARSE ###################################################################
supported_device_list = ["base", "eos", "ios", "iosxr", "junos", "nxos", "nxos_ssh"]
ScriptName=sys.argv[0]
parser = argparse.ArgumentParser()


parser.add_argument("-y", "--yamlauthfile", action="store", default='',help="yaml auth file (username,password,address,port)")
parser.add_argument("-usr", "--username", action="store", default='',help="override/insert napalm username")
parser.add_argument("-pwd", "--password", action="store", default='',help="override/insert napalm password")
parser.add_argument("-url", "--address", action="store", default='',help="override/insert napalm url/ip address")
parser.add_argument("-p", "--port", action="store", default='',help="override/insert napalm port")
parser.add_argument("-dt", "--devicetype", action="store", default='base',choices=supported_device_list,help="FORCE device type [%s], by default is auto-detected."%','.join(supported_device_list))
parser.add_argument("-v", "--verbose",action="store_true", default=False, help="set verbose mode")
aargs = parser.parse_args()
if aargs.verbose: print('\nINPUT_PARAMS:',parser.parse_args())
if len(sys.argv)<2: print(usage_text)


### RECOGNISE DEVICE TYPE ======================================================
# def get_device_type(nhost,nport,nusername,npassword):
#   device_type=None
#   with manager.connect_ssh(host=nhost,port=nport,username=nusername,password=npassword,
#                            device_params=None,timeout=10,allow_agent=False,
#                            look_for_keys=False,hostkey_verify=False ) as m:
#     if aargs.verbose: print('CAPABILITIES:',list(m.server_capabilities))
#     for c in m.server_capabilities:
#       #if 'TAILF-NCS' in c.upper(): device_type='nso'; break;
#       if 'JUNIPER' in c.upper(): device_type='junos'; break;
#       if 'NX-OS' in c.upper(): device_type='nexus'; break;
#       if 'Cisco-IOS-XR' in c: device_type='csr'; break;
#       if 'HUAWEI' in c.upper(): device_type='huawei'; break;
#     print('DEVICE_TYPE:',device_type)
#     return device_type




CMD_IOS_XE_CMDS = [
        "show version",
        "show running-config",
        "show isis neighbors",
        "show mpls ldp neighbor",
        "show ip interface brief",
        "show ip route summary",
        "show crypto isakmp sa",
        "show crypto ipsec sa count",
        "show crypto eli" ]
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
        "show inventory" ]
JUNOS_CMDS = [
          "show version",
		"show system software",
		"show configuration | display xml",
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
        "show system users" ]



### MAIN =======================================================================
def main():
  file_name=str()
  device_params=None
  napalm_auth_data=None
  ### AUTHORIZATION - READ YAML napalm AUTH FILE OR INPUT PARAMETERS-----------
  if aargs.yamlauthfile:
    with open(aargs.yamlauthfile, 'r') as stream: napalm_auth_data = yaml.load(stream)
  if not napalm_auth_data: napalm_auth_data = yaml.load(napalm_auth_data_yaml)
  naddress=napalm_auth_data.get('address','')
  nport=napalm_auth_data.get('port','')
  nusername=napalm_auth_data.get('username','')
  npassword=napalm_auth_data.get('password','')
  ### OVERDIDE/INSERT INPUT PARAMETERS -----------------------------------------
  if aargs.username: nusername=aargs.username
  if aargs.password: npassword=aargs.password
  if aargs.address:  naddress=aargs.address
  if aargs.port:     nport=aargs.port
  ### NAPALM CONNECT ----------------------------------------------------------
  print('DEVICE_TYPE:',aargs.devicetype,' , HOST:',naddress,', PORT:',nport,', USER:',nusername,', PASSWORD:', 'YES' if npassword else '-')
  if naddress and nport and nusername and npassword:
    driver = napalm.get_network_driver(aargs.devicetype)
    device = driver(hostname=naddress, username=nusername,password=npassword,timeout=30,optional_args={'port': nport})
    device.open()
    retrieve_list=[u'all',u'running',u'candidate',u'startup']
    #print(device.get_facts())
    print(device.get_config(retrieve=u'running'))
    #print(device.cli(u'show version and haiku'))
    device.close()


#   ### --------------------------------------------------------------------------
if __name__ == "__main__": main()
