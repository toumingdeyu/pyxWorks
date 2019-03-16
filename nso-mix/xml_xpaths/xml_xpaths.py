#!/usr/bin/env python

import io
import os
import sys
import json
import yaml
import requests
import urllib3
import copy
import argparse
import datetime
import xmltodict
import collections

### COMMANDLINE ARGUMETS HANDLING ==============================================
now = datetime.datetime.now()
timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
ScriptName=sys.argv[0]
parser = argparse.ArgumentParser()
parser.add_argument("-x", "--xpathexpression", action="store", default=str(),help="xpath filter expression i.e.( -x /netconf-state[@xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring']/schemas) (please use ' instead of \")")
parser.add_argument("-f", "--xmlfile", action="store", default='',help="input xml file")
parser.add_argument("-v", "--verbose",action="store_true", default=False, help="set verbose mode")
aargs = parser.parse_args()
if aargs.verbose: print('\nINPUT_PARAMS:',parser.parse_args())
if len(sys.argv)==1: print('HELP: python %s -h'%(sys.argv[0]))

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
    references=references+add_references
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




### MAIN =======================================================================
def main():
  if aargs.xmlfile:
    with io.opena(aargs.xmlfile) as xml_file: aaa=xml_file.read();xml_raw_data = xmltodict.parse(aaa) #,process_namespaces=True)  #item_depth=2, item_callback=handle_artist
    if xml_raw_data:
      xml_xpaths=get_xpath_from_xmlstring(xml_raw_data)
      print('\n'.join(xml_xpaths))
      if xml_xpaths:
        with open(fileName+'_'+timestring+'.xpaths', 'w', encoding='utf8') as outfile:
          outfile.write('\n'.join(xml_xpaths))
  ### --------------------------------------------------------------------------
  if aargs.xpathexpression: print('DEBUG_XPATH:\n'+get_xmlstring_from_xpath(aargs.xpathexpression))
  ### --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
