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

warnings.simplefilter("ignore", DeprecationWarning)

netconf_auth_data_yaml='''
netconf_user: pnemec
netconf_password:
netconf_ipaddress: 127.0.0.1
netconf_ssh_port: 22224
'''

usage_text='''NETCONF CLIENT {}, created by {}, {}
for more info please type: python netconf_client_07.py -h
'''.format(sys.argv[0],ScriptAuthor,ScriptVersion)

urllib3.disable_warnings()
now = datetime.datetime.now()
timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)

### ARGPARSE ###################################################################
ScriptName=sys.argv[0]
parser = argparse.ArgumentParser()

parser.add_argument("-y", "--yamlauthfile", action="store", default='',help="yaml auth file (netconf_user,netconf_password,netconf_ipaddress,netconf_ssh_port)")
parser.add_argument("-usr", "--netconfusername", action="store", default='',help="override/insert netconf username")
parser.add_argument("-pwd", "--netconfpassword", action="store", default='',help="override/insert netconf password")
parser.add_argument("-url", "--netconfaddress", action="store", default='',help="override/insert netconf url/ip address")
parser.add_argument("-p", "--netconfport", action="store", default='',help="override/insert netconf port")
parser.add_argument("-dt", "--devicetype", action="store", default='',choices=['j','c','n','h','junos','csr','nexus','huawei'],help="FORCE device type [(j)unos,(c)sr,(n)exus,(h)uawei], by default is auto-detected.")
parser.add_argument("-gca", "--getcapabilities",action="store_true", default=False, help="get capabilities to file")
parser.add_argument("-grc", "--getrunningconfig",action="store_true", default=False, help="get running-config to file")
parser.add_argument("-gcc", "--getcandidateconfig",action="store_true", default=False, help="get candidate-config to file")
parser.add_argument("-gcm", "--getcommands",action="store_true", default=False, help="get commands to xml file (working only on junos)")
parser.add_argument("-rpc", "--getrpc",action="store_true", default=False, help="get rpc answer to xml file (working only on junos)")
parser.add_argument("-g", "--getdata",action="store_true", default=False, help="get xml data to file (needed -x xpath)")
parser.add_argument("-x", "--xpathexpression", action="store", default=str(),help="xpath filter expression i.e.( -x /netconf-state[@xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring']/schemas) (please use ' instead of \")")
parser.add_argument("-cwf", "--comparewithfile", action="store", default='',help="compare with xml file")
parser.add_argument("-v", "--verbose",action="store_true", default=False, help="set verbose mode")
aargs = parser.parse_args()
if aargs.verbose: print('\nINPUT_PARAMS:',parser.parse_args())
if len(sys.argv)<2: print(usage_text);exit(0)


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
          if type(xml_data.get(key))==dict or type(xml_data.get(key))==collections.OrderedDict: xml_deeper_references.append(xml_data.get(key))
          elif type(xml_data.get(key))==list:
            for sub_xml in xml_data.get(key):
              if type(sub_xml)==dict or type(sub_xml)==collections.OrderedDict: xml_deeper_references.append(sub_xml)
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


### GET_XML_XPATHS =============================================================
def get_xml_xpaths(xml_data):
  """
  FUNCTION: get_xml_xpaths()
  parameters: xml_data   - xml data structure
  returns:    xpath_list - lists of all xpaths found in xml_data
  """
  ### SUBFUNCTION --------------------------------------------------------------
  def get_xml_dictionary_subreferences(tuple_data):
    xml_deeper_references=[]
    parrent_xpath=tuple_data[0]
    xml_data=tuple_data[1]
    if type(xml_data)==dict or type(xml_data)==collections.OrderedDict:
      for key in xml_data.keys():
        #if not (str(key)[0]=='@' or str(key)[0]=='#'):   ###ARGUMENTS
          key_content=xml_data.get(key)
          if type(key_content) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'/'+key,key_content))
          elif type(key_content)==list:
            for ii,sub_xml in enumerate(key_content,start=0):
              if type(sub_xml) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'/'+key+'['+str(ii)+']',sub_xml))
          elif isinstance(key_content,str):
            if '#text' in key: xml_deeper_references.append((parrent_xpath+'="'+key_content+'"',key_content))
            else: xml_deeper_references.append((parrent_xpath+'/'+key+'="'+key_content+'"',key_content))
    return xml_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  references=[]
  xpath_list=[]
  references.append(('',xml_data))
  while len(references)>0:
    add_references=get_xml_dictionary_subreferences(references[0])
    xpath_list.append(references[0][0])
    references.remove(references[0])
    references=references+add_references
  del references
  return xpath_list
  ### END OF GET_XML_XPATHS ====================================================


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
    print('DEVICE_TYPE:',device_type)
    return device_type


### GET_JUNOS_PRODUCTMODEL_AND_OSVERSION =======================================
def get_junos_productmodel_and_osversion(m,recognised_dev_type):
  product_model=str()
  os_version=str()
  if recognised_dev_type=='junos':
    result=m.command(command='show version', format='xml')
    ddata=xmltodict.parse(str(result))
    product_model=ddata['rpc-reply']['software-information']['product-model']
    os_version=ddata['rpc-reply']['software-information']['junos-version']
    print('MODEL:',product_model,', OS_VERSION:',os_version)
  return product_model,os_version


### GET_XMLSTRING_FROM_XPATH ===================================================
def get_xmlstring_from_xpath(xpathexpression):
  ### trick1 = [cc=value] --> /cc=value , trick2 argument parsing= '[@' --> ' @@@@' and </ .split(' @@@@')[0]> ,trick3 @@@@ to ignore 1..2x@ in http/email
  xml_string=str()
  if xpathexpression:
    if aargs.verbose: print('XPATH_ORIGINAL:',xpathexpression)
    xpath_list=str(xpathexpression).split('/')[1:] if '/' in str(xpathexpression) else [str(xpathexpression)]
    if aargs.verbose: print('XPATH_TAG_LIST:',xpath_list)
    last_xml_element='<%s>\n<%s>%s</%s>\n<%s>'%(xpath_list[-1].split('[')[0],xpath_list[-1].split('[')[1].split('=')[0],xpath_list[-1].split('=')[1].replace('"','').replace("'",'').replace(']',''),xpath_list[-1].split('[')[1].split('=')[0],xpath_list[-1].split('[')[0]) if '=' in xpath_list[-1] else '<%s/>'%(xpath_list[-1])
    xml_string=last_xml_element
    if aargs.verbose: print('LAST_ELEMENT:',last_xml_element)
    for element in xpath_list[::-1][1:]:
      if '[@' in element:
        xpath_tag=element.split('[@')[0]
        xpath_argument=' '+element.split('[@')[1].split(']')[0] if '[@' in element else str()
        xml_string='<'+xpath_tag+xpath_argument.replace("'",'"')+'>\n'+xml_string+'\n</'+xpath_tag+'>'
      elif '=' in element:   pass
        #xml_string='<%s>%s</%s>'%(element.split('[')[1].split('=')[0],element.split('=')[1].replace('"','').replace("'",''),element.split('[')[1].split('=')[0])
        #xml_string='<'+element.replace("'",'"')+'>\n'+xml_string+'\n</'+element+'>'
      elif '[' in element:
        position=int(element.split('[')[1].split(']')[0])
        xml_string='<'+element.split('[')[0]+'>\n'+xml_string+'\n</'+element.split('[')[0]+'>'
        if position>0:
          for i in range(position): xml_string='<'+element.split('[')[0]+'>\n'+'</'+element.split('[')[0]+'>\n'+xml_string
  return str(xml_string)
### ----------------------------------------------------------------------------


### COMPARE_XML_XPATH_FILES ====================================================
def compare_xml_xpath_files(file_name,comparewithfile=None):
  ### XML to XPATHS - CREATED NOW ----------------------------------------------
  if file_name and not 'capabilities' in file_name:
    with io.open(file_name) as xml_file:
      try: xml_raw_data = xmltodict.parse(xml_file.read())
      except: xml_raw_data=None;print('Problem to parse file {} to XML.'.format(file_name))
      if xml_raw_data:
        xml_xpaths=get_xml_xpaths(xml_raw_data)
        if aargs.verbose: print('\n'.join(xml_xpaths))
        if xml_xpaths:
          with open(file_name+'.xpaths', 'w', encoding='utf8') as outfile:
            outfile.write('\n'.join(xml_xpaths))
            print('Creating '+file_name+'.xpaths file.')
  ### XML to XPATHS - CWF ------------------------------------------------------
  if comparewithfile:
    with io.open(comparewithfile) as xml_file:
      try: xml_raw_data = xmltodict.parse(xml_file.read())
      except: xml_raw_data=None;print('Problem to parse file {} to XML.'.format(aargs.comparewithfile))
      if xml_raw_data:
        xml_xpaths=get_xml_xpaths(xml_raw_data)
        if aargs.verbose: print('\n'.join(xml_xpaths))
        if xml_xpaths:
          with open(comparewithfile+'.xpaths', 'w', encoding='utf8') as outfile:
            outfile.write('\n'.join(xml_xpaths))
            print('Creating '+comparewithfile+'.xpaths file.')
  ### DO TEXT FILE DIFF --------------------------------------------------------
  if comparewithfile and file_name:
    with open(comparewithfile+'.xpaths', 'r') as pre:
      with open(file_name+'.xpaths', 'r') as post:
        with open('file-diff_'+timestring+'.diff', 'w', encoding='utf8') as outfile:
          print('Creating file-diff_'+timestring+'.diff file.')
          print_string='\nPRE='+comparewithfile+', POST='+file_name+' FILE-DIFF:'+'\n'+80*('=')+'\n'
          print(print_string);outfile.write(print_string)
          diff = difflib.unified_diff(pre.readlines(),post.readlines(),fromfile='PRE',tofile='POST',n=0)
          for line in diff: print(line.replace('\n',''));outfile.write(line)
          print_string='\n'+80*('=')+'\n';print(print_string);outfile.write(print_string)
  ### --------------------------------------------------------------------------


### NCCLIENT_CAPABILITIES ======================================================
def ncclient_capabilities(m,recognised_dev_type):
  if aargs.verbose: print('CAPABILITIES:',list(m.server_capabilities))
  ### WRITE CAPABILITIES TO FILE -----------------------------------------
  if aargs.getcapabilities:
    file_name=str(recognised_dev_type)+'_capabilities_'+timestring+'.cap'
    with open(file_name, 'w', encoding='utf8') as outfile:
      for c in m.server_capabilities: outfile.write(str(c)+'\n')
      print('Writing capabilities to file:',file_name)
      return file_name
  return str()
### END OF NCCLIENT_CAPABILITIES -----------------------------------------------


### NCCLIENT_COMMANDS ==========================================================
def ncclient_commands(m,recognised_dev_type):
#   CMD_IOS_XE_CMDS = [
#           "show version",
#           "show running-config",
#           "show isis neighbors",
#           "show mpls ldp neighbor",
#           "show ip interface brief",
#           "show ip route summary",
#           "show crypto isakmp sa",
#           "show crypto ipsec sa count",
#           "show crypto eli" ]
#   CMD_IOS_XR_CMDS = [
#           "show system verify report",
#           "show version",
#           "show running-config",
#           "admin show running-config",
#           "show processes cpu | utility head count 3",
#           "show isis interface brief",
#           "show isis neighbors | utility cut -d " " -f -27",
#           "show mpls ldp neighbor brief",
#           "show interface brief",
#           "show bgp sessions",
#           "show route summary",
#           "show l2vpn xconnect group group1",
#           "admin show platform",
#           "show inventory" ]
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
  ### GET (JUNOS) COMMANDS -----------------------------------------------------
  if aargs.getcommands:
    file_name=str(recognised_dev_type)+'_commands_'+timestring+'.xml'
    if recognised_dev_type=='junos': CMDS=JUNOS_CMDS
#     elif recognised_dev_type=='csr': CMDS=CMD_IOS_XR_CMDS
#     else: CMDS=CMD_IOS_XE_CMDS
    if CMDS:
      with open(file_name, 'w', encoding='utf8') as outfile:
        outfile.write('<xmlfile name="'+file_name+'">\n')
        for command in CMDS:
          result=m.command(command=command, format='xml')
          print('COMMAND: '+command)
          if aargs.verbose: print(str(result)+'\n')
          outfile.write('\n<command cmd="'+command+'">\n'+str(result)+'</command>\n')
        outfile.write('</xmlfile>\n')
        return file_name
  return str()
### END OF NCCLIENT_COMMANDS ---------------------------------------------------


### NCCLIENT_GETCONFIG =========================================================
def ncclient_getconfig(m,recognised_dev_type):
  if (aargs.getrunningconfig or aargs.getcandidateconfig):
    if aargs.xpathexpression: rx_config = m.get_config(source='candidate' if aargs.getcandidateconfig else 'running',filter=('xpath',aargs.xpathexpression)).data_xml
    else: rx_config=m.get_config(source='candidate' if aargs.getcandidateconfig else 'running').data_xml
    if aargs.verbose: print('\n%s_CONFIG:\n'%(('candidate' if aargs.getcandidateconfig else 'running').upper() ),
                            str(rx_config) if '\n' in rx_config else xml.dom.minidom.parseString(str(rx_config)).toprettyxml())
    file_name=str(recognised_dev_type)+('_candidate' if aargs.getcandidateconfig else '_running')+'_config_'+timestring+'.xml'
    with open(file_name, 'w', encoding='utf8') as outfile:
      outfile.write(str(rx_config)) if '\n' in rx_config else outfile.write(xml.dom.minidom.parseString(str(rx_config)).toprettyxml())
      print('Writing %s-config %s to file:'%('candidate' if aargs.getcandidateconfig else 'running','XPATH='+aargs.xpathexpression if aargs.xpathexpression else ''),file_name)
      return file_name
  return str()
### END OF NCCLIENT_GETCONFIG --------------------------------------------------


### NCCLIENT_GET ===============================================================
def nccclient_get(m,recognised_dev_type):
  get_filter=None  #ios-xe returns text encapsulated by xml

  IETF_XMLNS_BASE = 'urn:ietf:params:xml:ns:netconf:base:1.0'
  IETF_XMLNS_NM = 'urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring'
  IETF_XMLNS_IF="urn:ietf:params:xml:ns:yang:ietf-interfaces"

#   filter_root_tag='netconf-state'
#   filter_arguments='xmlns="{}"'.format(IETF_XMLNS_NM)
#   filter_tag='schemas'
#
#   get_configurable_filter='''<filter type="subtree">\n<{} {}>\n<{}/>\n</{}>\n</filter>'''.format(filter_root_tag,filter_arguments,filter_tag,filter_root_tag)
#
#   get_schemas_filter='''<filter type="subtree">
# <netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
# <schemas/>
# </netconf-state>
# </filter>'''
#
#   get_interfaces_filter='''<filter type="subtree">
# <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
# </interfaces>
# </filter>'''
#
#
#   get_configurable_filter='''
#   <filter type="subtree">
#       <isis xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-clns-isis-oper">
#         <instances>
#           <instance>
#             <instance-name>PAII</instance-name>
#               <neighbors/>
#           </instance>
#         </instances>
#       </isis>
#   </filter>
# '''
#

# <get>
#   <filter type="subtree">
#       <isis xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-clns-isis-oper">
#         <instances>
#           <instance>
#             <instance-name>PAII</instance-name>
#               <neighbors/>
#           </instance>
#         </instances>
#       </isis>
#   </filter>
# </get>

  xr='''<isis xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-clns-isis-oper">
<instances>
  <instance>
    <instance-name>PAII</instance-name>
      <neighbors/>
  </instance>
</instances>
</isis>
'''
  #get_filter=('subtree',str(xr))

  if aargs.xpathexpression:
    ### -x /netconf-state[@xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring']/schemas
    subfilter=get_xmlstring_from_xpath(aargs.xpathexpression)
    filter_xmlns_argument=subfilter.split('xmlns=')[1].split('>')[0].replace(' ','').replace('"','') if 'xmlns=' in subfilter else str()
    get_configurable_filter=('subtree',str(subfilter))  #.encode(encoding='UTF-8',errors='strict'))
  else:
    filter_root_tag='netconf-state'
    filter_xmlns_argument='urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring'
    filter_tag='schemas'
    subfilter='''<{} xmlns="{}">\n<{}/>\n</{}>'''.format(filter_root_tag,filter_xmlns_argument,filter_tag,filter_root_tag)
    get_configurable_filter=('subtree',str(subfilter))
  ###---------------------------------------------------------------------------
  None if filter_xmlns_argument in str(list(m.server_capabilities)) else print('WARNING: xmlns="',filter_xmlns_argument,'" not FOUND in DEVICE CAPABILITIES!')
  ###---------------------------------------------------------------------------
  if aargs.getdata:
    ### ios-xe needs filter None and then returns text encapsulated by xml
    if not get_filter:
      get_filter=get_configurable_filter if recognised_dev_type else None
    print('GET_FILTER:',str(get_filter))
    rx_data = m.get(filter=get_filter) if not aargs.xpathexpression else m.get(filter=get_filter)
    if aargs.verbose: print('GET_FILTER:',str(get_filter),'\nRECIEVED_DATA:\n',str(rx_data))
    file_name=str(recognised_dev_type)+'_data_get_'+timestring+'.xml'
    with open(file_name, 'w', encoding='utf8') as outfile:
      outfile.write(str(rx_data))
      print('Writing get data to file:',file_name)
      return file_name
  return str()
### END OF NCCLIENT_GET --------------------------------------------------------


### NCCCLIENT_RPC ==============================================================
def nccclient_rpc(m,recognised_dev_type):
  ### RPC XML FILTER -----------------------------------------------------
  #rpc_filter = """<get-chassis-inventory><detail/></get-chassis-inventory>"""
  #rpc_filter='''<get-interface-information><detail/></get-interface-information>'''
  #'get-system-inventory'

  # OMG: https://www.juniper.net/documentation/en_US/junos12.3/information-products/topic-collections/junos-xml-ref-oper/index.html
  tag_list = ['get-interface-information','get-chassis-inventory']
  file_name=str(recognised_dev_type)+'_rpc_'+timestring+'.xml'
  with open(file_name, 'w', encoding='utf8') as outfile:
    outfile.write('<xmlfile name="'+file_name+'">\n')
    for tag in tag_list:
      rpc_filter='''<{}><detail/></{}>'''.format(tag,tag)
      result = m.rpc(rpc_filter)
      print('RPC: '+tag)
      if aargs.verbose: print(str(result)+'\n')
      outfile.write('\n<rpc rpc_tag="'+tag+'">\n'+str(result)+'</command>\n')
    outfile.write('</xmlfile>\n')
    return file_name
  return str()
### END OF NCCCLIENT_RPC -------------------------------------------------------

### NCCLIENT_READ_ALL ==========================================================
def ncclient_read_all(m,recognised_dev_type):
  isis_data=str()
  rx_config=m.get_config('running').data_xml
  print('GET_CONFIG(RUNNING):\n'+str(rx_config)+'\n') if aargs.verbose else print('GET_CONFIG(RUNNING).')
  if recognised_dev_type=='junos':
    tag='get-isis-adjacency-information'
    rpc_filter='''<{}><detail/></{}>'''.format(tag,tag)
    isis_data = m.rpc(rpc_filter)
    print('RPC: '+tag+'\n'+str(isis_data)+'\n') if aargs.verbose else print('RPC: '+tag)
  elif recognised_dev_type=='csr':
    isis_filter='''<filter type="subtree">
    <isis xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-clns-isis-oper">
      <instances>
        <instance>
          <instance-name>{}</instance-name>
            <neighbors/>
        </instance>
      </instances>
    </isis>
</filter>'''.format('PAII')
    isis_data = m.get(filter=isis_filter)
    print('GET_FILTER:\n'+str(isis_data)) if aargs.verbose else print('GET_FILTER.')
  ### make xml headers and write filtered data to file -------------------------
  rx_config_filtered=str(rx_config).split('?>')[1] if '?>' in str(rx_config) else str(rx_config)
  isis_data_filtered=str(isis_data).split('?>')[1] if '?>' in str(isis_data) else str(isis_data)
  file_name=str(recognised_dev_type)+'_all_'+timestring+'.xml'
  with open(file_name, 'w', encoding='utf8') as outfile:
    outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n<xmlfile xmlfilename="'+file_name+'">\n')
    outfile.write(str(rx_config_filtered)+'\n'+str(isis_data_filtered)+'\n</xmlfile>')
    print('Creating '+file_name+' file.')
    return file_name
  return str()
###-----------------------------------------------------------------------------

### MAIN =======================================================================
def main():
  file_name=str()
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
  if aargs.netconfaddress:  nhost=aargs.netconfaddress
  if aargs.netconfport:     nport=aargs.netconfport
  ### NETCONF CONNECT ----------------------------------------------------------
  print('HOST:',nhost,', PORT:',nport,', USER:',nusername,', PASSWORD:', 'YES' if npassword else '-')
  if nhost and nport and nusername and npassword:
    recognised_dev_type=get_device_type(nhost,nport,nusername,npassword)
    if not aargs.devicetype and recognised_dev_type: device_params={'name':recognised_dev_type}
    with manager.connect_ssh(host=nhost,port=nport,username=nusername,password=npassword,
                             device_params=device_params,timeout=30,allow_agent=False,
                             look_for_keys=False,hostkey_verify=False ) as m:
        print('CONNECTED  :',m.connected)
        get_junos_productmodel_and_osversion(m,recognised_dev_type)
        if aargs.getcapabilities: ncclient_capabilities(m,recognised_dev_type)
        if aargs.getrpc: file_name=nccclient_rpc(m,recognised_dev_type)
        if aargs.getdata: file_name=nccclient_get(m,recognised_dev_type)
        if aargs.getrunningconfig or aargs.getcandidateconfig: file_name=ncclient_getconfig(m,recognised_dev_type)
        if aargs.getcommands: file_name=ncclient_commands(m,recognised_dev_type)
        if not file_name: file_name=ncclient_read_all(m,recognised_dev_type)
        if aargs.comparewithfile: compare_xml_xpath_files(file_name,aargs.comparewithfile)
  ### --------------------------------------------------------------------------
  if aargs.verbose and aargs.xpathexpression: print('DEBUG_XPATH:\n'+get_xmlstring_from_xpath(aargs.xpathexpression))
  ### --------------------------------------------------------------------------
if __name__ == "__main__": main()
