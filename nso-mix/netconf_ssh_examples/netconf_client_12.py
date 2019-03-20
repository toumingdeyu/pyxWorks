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

### Highest AUTH priority have cmdline parameters, then external yaml file, last internal netconf_auth_data_yaml
netconf_auth_data_yaml='''
netconf_user: pnemec
netconf_password:
netconf_ipaddress: 127.0.0.1
netconf_ssh_port: 22224
'''

usage_text='''NETCONF CLIENT {}, created by {}, {}
for more info please type: python netconf_client_07.py -h

MAKING OF PRECHECK FILE:
python {}

MAKING OF POST CHECK:
python {} -cwf file.xml
'''.format(sys.argv[0],ScriptAuthor,ScriptVersion,sys.argv[0],sys.argv[0])

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
parser.add_argument("-xo", "--xpathoutputcomparison",action="store_true", default=False, help="xpath output format for difference comparison (default is xmlpath format)")
parser.add_argument("-cwf", "--comparewithfile", action="store", default='',help="compare with xml file")
parser.add_argument("-v", "--verbose",action="store_true", default=False, help="set verbose mode")
aargs = parser.parse_args()
if aargs.verbose: print('\nINPUT_PARAMS:',parser.parse_args())
if len(sys.argv)<2: print(usage_text)


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


### GET_XPATH_FROM_XMLSTRING ===================================================
def get_xpath_from_xmlstring(xml_data):
  """
  FUNCTION: get_xpath_from_xmlstring()
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
        key_content=xml_data.get(key)
        if type(key_content) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'/'+key,key_content))
        elif type(key_content)==list:
          for ii,sub_xml in enumerate(key_content,start=0):
            if type(sub_xml) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'/'+key+'['+str(ii)+']',sub_xml))
        elif isinstance(key_content,str):
          if '#text' in key: xml_deeper_references.append((parrent_xpath+'="'+key_content+'"',key_content))
          elif str(key)[0]=='@': xml_deeper_references.append((parrent_xpath+'['+key+'="'+key_content+'"]',key_content))
          else: xml_deeper_references.append((parrent_xpath+'/'+key+'="'+key_content+'"',key_content))
        elif key_content==None: xml_deeper_references.append((parrent_xpath+'/'+key,None))
    return xml_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  references=[]
  xpath_list=[]
  references.append(('',xml_data))
  while len(references)>0:
    add_references=get_xml_dictionary_subreferences(references[0])
    xpath_list.append(references[0][0])
    references.remove(references[0])
    references=add_references+references
  del references
  return xpath_list
### ----------------------------------------------------------------------------


### GET_XMLSTRING_FROM_XPATH ===================================================
def get_xmlstring_from_xpath(xpathexpression):
  xml_string=str()
  if xpathexpression:
    if aargs.verbose: print('XPATH_ORIGINAL:',xpathexpression)
    xpath_list=str(xpathexpression).replace(']','').split('/')[1:] if '/' in str(xpathexpression) else [str(xpathexpression)]
    if aargs.verbose: print('XPATH_TAG_LIST:',xpath_list)
    xml_string=str()
    if aargs.verbose: print('REVERSED_LIST:',xpath_list[::-1])
    for element in xpath_list[::-1]:
      if '[@' in element:
        xpath_tag=element.split('[@')[0]
        xpath_argument=' '+element.split('[@')[1] if '[@' in element else str()
        xml_string='<{}{}>\n{}\n</{}>'.format(xpath_tag, xpath_argument.replace("'",'"'),xml_string , xpath_tag)
      elif '=' in element:
        xml_string='<{}>{}</{}>{}'.format(element.split('=')[0], element.replace("'",'').replace('"','').split('=')[1], element.split('=')[0], '\n'+xml_string if xml_string else str())
      else: xml_string='<{}>\n{}\n</{}>'.format(element,xml_string,element) if xml_string else '<{}/>'.format(element)
  return str(xml_string)
### ----------------------------------------------------------------------------


### GET_XMLPATH_FROM_XMLSTRING =============================================================
def get_xmlpath_from_xmlstring(xml_data):
  """
  FUNCTION: get_xmlpath_from_xmlstring()
  parameters: xml_data   - xml data structure
  returns:    xmlpath_list - lists of all xpaths found in xml_data
  """
  ### SUBFUNCTION --------------------------------------------------------------
  def get_xml_dictionary_subreferences(tuple_data):
    xml_deeper_references=[]
    parrent_xpath=tuple_data[0]
    xml_data=tuple_data[1]
    if type(xml_data)==dict or type(xml_data)==collections.OrderedDict:
      for key in xml_data.keys():
        key_content=xml_data.get(key)
        if type(key_content) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'<'+key+'>',key_content))
        elif type(key_content)==list:
          for ii,sub_xml in enumerate(key_content,start=0):
            if type(sub_xml) in [dict,collections.OrderedDict]: xml_deeper_references.append((parrent_xpath+'<'+key+'['+str(ii)+']>',sub_xml))
        elif isinstance(key_content,str):
          if '#text' in key: xml_deeper_references.append((parrent_xpath+key_content+'</'+parrent_xpath.split('<')[-1],key_content))
          elif str(key)[0]=='@': xml_deeper_references.append((str(parrent_xpath[:-1])+' '+str(key[1:])+'="'+key_content+'">',key_content))
          else: xml_deeper_references.append((parrent_xpath+'<'+key+'>'+key_content+'</'+key+'>',key_content))
        elif key_content==None: xml_deeper_references.append((parrent_xpath+'<'+key+'/>',None))
    return xml_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  references=[]
  xpath_list=[]
  references.append(('',xml_data))
  while len(references)>0:
    add_references=get_xml_dictionary_subreferences(references[0])
    xpath_list.append(references[0][0])
    references.remove(references[0])
    references=add_references+references
  del references
  return xpath_list
### ----------------------------------------------------------------------------


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
###-----------------------------------------------------------------------------

###-----------------------------------------------------------------------------
def string_file_difference(old_isis_list,new_isis_list):
  '''
  The head of line is
  '-' for missing line,
  '+' for added line and
  '!' for line that is different.
  RED for something going Down or something missing.
  ORANGE for something going Up or something new (not present in pre-check)
  '''
  class bcolors:
    HEADER='\033[95m'
    OKBLUE='\033[94m'
    OKGREEN='\033[92m'
    GREEN='\033[92m'
    WARNING='\033[93m'
    RED='\033[91m'
    FAIL='\033[91m'
    ENDC='\033[0m'
    BOLD='\033[1m'
    UNDERLINE='\033[4m'

  if old_isis_list and new_isis_list:
    new_isis_address_list=[isis_address for isis_address,dummy1,dummy2 in new_isis_list]
    old_isis_address_list=[isis_address for isis_address,dummy1,dummy2 in old_isis_list]
    lost_isis_items=[item for item in old_isis_address_list if item not in new_isis_address_list]
    new_isis_items=[item for item in new_isis_address_list if item not in old_isis_address_list]
    print('ADJACENCY STATE:')
    for old_isis_address,old_isis_interface,old_isis_state in old_isis_list:
      if old_isis_address in lost_isis_items:
        print('%s  -  %s  %s  %s'%(bcolors.RED,old_isis_address,old_isis_interface,old_isis_state))
    for new_isis_address,new_isis_interface,new_isis_state in new_isis_list:
      ### new addressess
      if new_isis_address in new_isis_items:
        if 'DOWN' in new_isis_state.upper(): print('%s  +  %s  %s  %s'%(bcolors.RED,new_isis_address,new_isis_interface,new_isis_state))
        else: print('%s  +  %s  %s  %s'%(bcolors.WARNING,new_isis_address,new_isis_interface,new_isis_state))
      ### isis are the same
      elif (new_isis_address,new_isis_interface,new_isis_state) in old_isis_list:
        if 'DOWN' in new_isis_state.upper(): print('%s     %s  %s  %s'%(bcolors.RED,new_isis_address,new_isis_interface,new_isis_state))
        else: print('%s     %s  %s  %s'%(bcolors.GREEN,new_isis_address,new_isis_interface,new_isis_state))
      ### different isis
      else:
        if 'DOWN' in new_isis_state.upper(): print('%s  !  %s  %s  %s'%(bcolors.RED,new_isis_address,new_isis_interface,new_isis_state))
        else: print('%s  !  %s  %s  %s'%(bcolors.WARNING,new_isis_address,new_isis_interface,new_isis_state))
###-----------------------------------------------------------------------------

###-----------------------------------------------------------------------------
def decode_isis_adjacency(filename,recognised_dev_type):
  out_tuple_list=[]
  ### SHOW UP/DOWN ISIS STATES -------------------------------------------------
  with io.open(filename) as xml_file:
    try: xml_raw_data = xmltodict.parse(xml_file.read())
    except: xml_raw_data=None;print('Problem to parse file {} to XML.'.format(file_name))
  if recognised_dev_type=='junos':
    for adjacency in xml_raw_data['xmlfile']['get_isis_adjacency']['rpc-reply']['isis-adjacency-information']['isis-adjacency']:
      out_tuple_list.append((adjacency['system-name'],adjacency['interface-name'],adjacency['adjacency-state']))
  elif recognised_dev_type=='csr':
    for adjacency in xml_raw_data['xmlfile']['get_isis_adjacency']['rpc-reply']['data']['isis']['instances']['instance']['neighbors']['neighbor']:
      out_tuple_list.append((adjacency['system-id'],adjacency['interface-name'],adjacency['neighbor-state']))
  return out_tuple_list
###-----------------------------------------------------------------------------


### COMPARE_XML_XPATH_FILES ====================================================
def compare_xml_xpath_files(file_name,comparewithfile=None,recognised_dev_type=None):
  file_suffix='.xpt' if aargs.xpathoutputcomparison else '.xmp'
  ### XML to XPATHS - CREATED NOW ----------------------------------------------
  if file_name and not 'capabilities' in file_name:
    with io.open(file_name) as xml_file:
      try: xml_raw_data = xmltodict.parse(xml_file.read())
      except: xml_raw_data=None;print('Problem to parse file {} to XML.'.format(file_name))
      if xml_raw_data:
        xml_xpaths=get_xpath_from_xmlstring(xml_raw_data) if aargs.xpathoutputcomparison else get_xmlpath_from_xmlstring(xml_raw_data)
        if aargs.verbose: print('\n'.join(xml_xpaths))
        if xml_xpaths:
          with open(file_name+file_suffix, 'w', encoding='utf8') as outfile:
            outfile.write('\n'.join(xml_xpaths))
            print('Creating '+file_name+file_suffix+' file.')
  ### XML to XPATHS - CWF ------------------------------------------------------
  if comparewithfile:
    with io.open(comparewithfile) as xml_file:
      try: xml_raw_data = xmltodict.parse(xml_file.read())
      except: xml_raw_data=None;print('Problem to parse file {} to XML.'.format(aargs.comparewithfile))
      if xml_raw_data:
        xml_xpaths=get_xpath_from_xmlstring(xml_raw_data) if aargs.xpathoutputcomparison else get_xmlpath_from_xmlstring(xml_raw_data)
        if aargs.verbose: print('\n'.join(xml_xpaths))
        if xml_xpaths:
          with open(comparewithfile+file_suffix, 'w', encoding='utf8') as outfile:
            outfile.write('\n'.join(xml_xpaths))
            print('Creating '+comparewithfile+file_suffix+' file.')
  ### DO TEXT FILE DIFF --------------------------------------------------------
  if comparewithfile and file_name:
    with open(comparewithfile+file_suffix, 'r') as pre:
      with open(file_name+file_suffix, 'r') as post:
        with open('file-diff_'+timestring+'.diff', 'w', encoding='utf8') as outfile:
          print('Creating file-diff_'+timestring+'.diff file.')
          print_string='\nPRE='+comparewithfile+file_suffix+'\nPOST='+file_name+file_suffix+'\nRAW-FILE-DIFF:'+'\n'+80*('=')+'\n'
          print(print_string); outfile.write(print_string)
          diff = difflib.unified_diff(pre.readlines(),post.readlines(),fromfile='PRE',tofile='POST',n=0)
          for line in diff: print(line.replace('\n',''));outfile.write(line)
          print_string='\n'+80*('=')+'\n';print(print_string);outfile.write(print_string)
  ### SHOW UP/DOWN ISIS STATES -------------------------------------------------
  old_isis_state=decode_isis_adjacency(comparewithfile,recognised_dev_type)
  new_isis_state=decode_isis_adjacency(file_name,recognised_dev_type)
  print(string_file_difference(old_isis_state,new_isis_state)  )
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
    ###-------------------------------------------------------------------------
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
    ###-------------------------------------------------------------------------
  ### make xml headers and write filtered data to file -------------------------
  rx_config_filtered=str(rx_config).split('?>')[1] if '?>' in str(rx_config) else str(rx_config)
  isis_data_filtered=str(isis_data).split('?>')[1] if '?>' in str(isis_data) else str(isis_data)
  file_name=str(recognised_dev_type)+'_all_'+timestring+'.xml'
  with open(file_name, 'w', encoding='utf8') as outfile:
    outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n<xmlfile xmlfilename="'+file_name+'">\n<get_config>\n')
    outfile.write(str(rx_config_filtered)+'\n</get_config>\n<get_isis_adjacency>\n'+str(isis_data_filtered)+'\n</get_isis_adjacency>\n</xmlfile>')
    print('\nCreating '+file_name+' file.\n')
    print('ISIS ADJACENCY STATE:')
    print(decode_isis_adjacency(file_name,recognised_dev_type))
    return file_name
  return str()
###-----------------------------------------------------------------------------


### MAIN =======================================================================
def main():

#   l1=[('SINPE55', 'ge-1/0/2.0', 'Up'), ('PASCR6', 'so-0/0/0.1', 'Up'), ('LONCR1', 'so-0/2/0.0', 'Up'), ('PASCR7', 'xe-1/2/1.0', 'Up'), ('SINCR4', 'xe-1/2/3.0', 'Up'), ('PASCR7', 'xe-1/2/4.0', 'Up'), ('SINCR4', 'xe-2/2/2.0', 'Up'), ('SINPE4', 'xe-2/2/3.0', 'Up'), ('PASCR7', 'xe-2/2/4.0', 'Up'), ('SINCR4', 'xe-2/2/5.0', 'Up')]
#   l2=[('SINPE5', 'ge-1/0/2.0', 'Up'), ('PASCR6', 'so-0/0/0.0', 'Up'), ('LONCR1', 'so-0/2/0.0', 'Up'), ('PASCR7', 'xe-1/2/1.0', 'Down'), ('SINCR4', 'xe-1/2/3.0', 'Up'), ('PASCR7', 'xe-1/2/4.0', 'Up'), ('SINCR4', 'xe-2/2/2.0', 'Up'), ('SINPE4', 'xe-2/2/3.0', 'Up'), ('PASCR7', 'xe-2/2/4.0', 'Up'), ('SINCR4', 'xe-2/2/5.0', 'Up')]
#   string_file_difference(l1,l2)
#   exit(0)

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
        if aargs.comparewithfile: compare_xml_xpath_files(file_name,aargs.comparewithfile,recognised_dev_type)
  ### --------------------------------------------------------------------------
  if aargs.verbose and aargs.xpathexpression: print('\nDEBUG_XPATH to XML:\n'+get_xmlstring_from_xpath(aargs.xpathexpression))
  ### --------------------------------------------------------------------------
if __name__ == "__main__": main()
