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

### COMMANDLINE ARGUMETS HANDLING ==============================================
ScriptName=sys.argv[0]
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) < 2:
  print("SYNTAX: python %s nameOfInputFile.json json_key json_value/- k/v(= get key/value)" % (ScriptName))
  sys.exit(1)
else:
  json_value=None
  get_value=False
  json_key=None
  fileName=args[0]
  if len(sys.argv)>=3: json_key=args[1]
  if len(sys.argv)>=4 and args[2]!='-': json_value=args[2]
  if len(sys.argv)>=5 and args[4] in ['k','key']: get_value=False
  if len(sys.argv)>=5 and args[4] in ['v','value']: get_value=True

### GET_JSON_ELEMENT ===========================================================
def get_json_element(json_data,json_key=None,json_value=None,get_value=False):
  """
  FUNCTION: get_json_element_reference
  parameters: json_data  - json data structure
              json_key   - optional wanted key
              json_value - optional wanted value
              get_value  - optional , if True returns json_value instead of reference
  returns: json_reference_found - None or json reference when element was found
  """
  ### SUBFUNCTION --------------------------------------------------------------
  def get_json_dictionary_reference(json_data,json_key=None,json_value=None):
    json_reference=None
    json_deeper_references=[]
    if type(json_data)==dict:
      for key in json_data.keys():
        print('   D:',key,', SUB_TYPE:',type(json_data.get(key)))
        if json_key and (json_key==key or ':'+str(json_key) in str(key)):
          if json_value and str(json_value)==str(json_data.get(key)):
            if get_value: json_reference=str(json_data.get(key));break
            else: dictionary={};dictionary[key]=json_data.get(key);json_reference=dictionary;break
          elif not json_value:
            if get_value: json_reference=str(json_data.get(key));break
            else: dictionary={};dictionary[key]=json_data.get(key);json_reference=dictionary;break
        if type(json_data.get(key))==dict: json_deeper_references.append(json_data.get(key))
        elif type(json_data.get(key))==list:
          for sub_json in json_data.get(key):
            if type(sub_json)==dict: json_deeper_references.append(sub_json)
    return json_reference,json_deeper_references
  ### SUBFUNCTION --------------------------------------------------------------
  def get_json_element_reference_one_level_down(json_data,json_key=None,json_value=None):
    json_reference=None
    json_deeper_references=[]
    print('TYPE:',type(json_data))
    if type(json_data)==list:
      for dict_data in json_data:
        print(' L:')
        json_reference,add_json_deeper_references=get_json_dictionary_reference(dict_data,json_key,json_value)
        if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    elif type(json_data)==dict:
      json_reference,add_json_deeper_references=get_json_dictionary_reference(json_data,json_key,json_value)
      if len(add_json_deeper_references)>0: json_deeper_references=json_deeper_references+add_json_deeper_references
    return json_reference,json_deeper_references
  ### FUNCTION -----------------------------------------------------------------
  json_reference_found=None
  references=[]
  references.append(json_data)
  while not json_reference_found and len(references)>0:
    json_reference_found,add_references=get_json_element_reference_one_level_down(references[0],json_key,json_value)
    references.remove(references[0])
    references=references+add_references
  del references
  print(50*'-','\nFOUND:',json_key ,':', json_value, '\nGET_VALUE:',get_value)
  return json_reference_found
  ### END OF GET_JSON_ELEMENT ==================================================

### MAIN =======================================================================
def main():
  with io.open(fileName) as json_file: json_raw_data = json.load(json_file)
  if json_raw_data:
    sub_json=get_json_element(json_raw_data,json_key,json_value,get_value)

    if sub_json:
      ### WRITE FILE WITH TIMESTAMP ==============================================
      now = datetime.datetime.now()
      timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
      with open(fileName+'_'+json_key+'_'+timestring+'.json', 'w', encoding='utf8') as outfile:
        json.dump(sub_json, outfile,  indent=2)
        outfile.close()

if __name__ == "__main__":
    main()
