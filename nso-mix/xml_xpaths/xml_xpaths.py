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




### MAIN =======================================================================
def main():
  with io.open(fileName) as xml_file: aaa=xml_file.read();xml_raw_data = xmltodict.parse(aaa) #,process_namespaces=True)  #item_depth=2, item_callback=handle_artist
  if xml_raw_data:
    xml_xpaths=get_xpath_from_xmlstring(xml_raw_data)
    print('\n'.join(xml_xpaths))
    if xml_xpaths:
      now = datetime.datetime.now()
      timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
      with open(fileName+'_'+timestring+'.xpaths', 'w', encoding='utf8') as outfile:
        outfile.write('\n'.join(xml_xpaths))

if __name__ == "__main__":
    main()
