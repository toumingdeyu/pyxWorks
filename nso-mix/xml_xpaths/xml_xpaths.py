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
import datetime
import xmltodict
import collections

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python %s nameOfInputFile.xml" % (ScriptName))
  sys.exit(1)
else:
  xml_value=str()
  get_value=False
  xml_key=str()
  fileName=args[0]
  if len(sys.argv)>=3: xml_key=args[1]


### GET_xml_ELEMENT ===========================================================
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
  ### END OF GET_xml_ELEMENT ==================================================


### MAIN =======================================================================
def main():
  with io.open(fileName) as xml_file: aaa=xml_file.read();xml_raw_data = xmltodict.parse(aaa) #,process_namespaces=True)  #item_depth=2, item_callback=handle_artist
  if xml_raw_data:
    xml_xpaths=get_xml_xpaths(xml_raw_data)
    print('\n'.join(xml_xpaths))
    if xml_xpaths:
      now = datetime.datetime.now()
      timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
      with open(fileName+'_'+timestring+'.xpaths', 'w', encoding='utf8') as outfile:
        outfile.write('\n'.join(xml_xpaths))

if __name__ == "__main__":
    main()
