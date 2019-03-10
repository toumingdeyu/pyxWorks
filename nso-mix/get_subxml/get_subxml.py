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
#from bs4 import BeautifulSoup
#from xml.dom.minidom import parseString
#from xml.etree import ElementTree
import collections

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python %s nameOfInputFile.xml xml_key xml_value/- k/v(= get key/value)" % (ScriptName))
  sys.exit(1)
else:
  xml_value=str()
  get_value=False
  xml_key=str()
  fileName=args[0]
  if len(sys.argv)>=3: xml_key=args[1]
  if len(sys.argv)>=4 and args[2]!='-': xml_value=args[2]
  if len(sys.argv)>=5 and args[3] in ['k','key']: get_value=False
  if len(sys.argv)>=5 and args[3] in ['v','value']: get_value=True


### GET_xml_ELEMENT ===========================================================
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
          key_content=xml_data.get(key)
          print('   D:',key,', SUB_TYPE:',type(key_content))
          try: something_doubledot_key=str(key).split(':')[1]
          except: something_doubledot_key='element_never_exists'
          if xml_key and (str(xml_key)==str(key) or str(xml_key)==str(something_doubledot_key)):
            if xml_value and str(xml_value)==str(key_content):
              if get_value: xml_reference=str(key_content);break
              else: dictionary={};dictionary[key]=key_content;xml_reference=dictionary;break
            elif not xml_value:
              if get_value: xml_reference=str(key_content);break
              else: dictionary={};dictionary[key]=key_content;xml_reference=dictionary;break
          if type(key_content)==dict or type(key_content)==collections.OrderedDict: xml_deeper_references.append(key_content)
          elif type(key_content)==list:
            for sub_xml in key_content:
              if type(sub_xml)==dict or type(sub_xml)==collections.OrderedDict: xml_deeper_references.append(sub_xml)
    return xml_reference,xml_deeper_references
  ### SUBFUNCTION --------------------------------------------------------------
  def get_xml_element_reference_one_level_down(xml_data,xml_key=None,xml_value=None):
    xml_reference=None
    xml_deeper_references=[]
    print('TYPE:',type(xml_data))
    if type(xml_data)==list:
      for dict_data in xml_data:
        print(' L:')
        xml_reference,add_xml_deeper_references=get_xml_dictionary_reference(dict_data,xml_key,xml_value)
        if len(add_xml_deeper_references)>0: xml_deeper_references=xml_deeper_references+add_xml_deeper_references
    elif type(xml_data)==dict or type(xml_data)==collections.OrderedDict:
      xml_reference,add_xml_deeper_references=get_xml_dictionary_reference(xml_data,xml_key,xml_value)
      if len(add_xml_deeper_references)>0: xml_deeper_references=xml_deeper_references+add_xml_deeper_references
    return xml_reference,xml_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  print('LOOKING_FOR:',xml_key ,':', xml_value, ', GET_VALUE:',get_value,'\n')
  xml_reference_found=None
  references=[]
  references.append(xml_data)
  while not xml_reference_found and len(references)>0:
    xml_reference_found,add_references=get_xml_element_reference_one_level_down(references[0],xml_key,xml_value)
    references.remove(references[0])
    references=references+add_references
  del references
  return xml_reference_found
  ### END OF GET_xml_ELEMENT ==================================================

### MAIN =======================================================================
def main():

### usefull tips for ELEMENTREE LIB
#   with io.open(fileName) as xml_file:
#     xml_et = ElementTree.parse(xml_file)
#     root = xml_et.getroot()
#
#     print(root.tag.split('}')[1] if '}' in root.tag else root.tag, root.text.replace('\n','').replace(' ',''))
#   for child in root:
#     print(child.tag.split('}')[1] if '}' in child.tag else child.tag, child.text.replace('\n','').replace(' ',''))
#     #print(child.tag, child.text)
#
#   print(ElementTree.tostring(root, encoding='utf8').decode('utf8'))

  with io.open(fileName) as xml_file: xml_raw_data = xmltodict.parse(xml_file.read())
  if xml_raw_data:
    sub_xml=get_xml_element(xml_raw_data,xml_key,xml_value,get_value)
    if get_value: print(50*'-','\nVALUE:',sub_xml)
    else: print(50*'-','\nSUBXML:',sub_xml)
    if sub_xml and not get_value:
      ### WRITE FILE WITH TIMESTAMP ==============================================
      now = datetime.datetime.now()
      timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
      with open(fileName+'_'+xml_key+'_'+timestring+'.xml', 'w', encoding='utf8') as outfile:
        outfile.write(xmltodict.unparse(sub_xml))
        outfile.close()

if __name__ == "__main__":
    main()
