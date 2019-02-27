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
from xml.dom.minidom import parseString
from xml.etree import ElementTree

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



### MAIN =======================================================================
def main():
#         device_data=dict2xml(json_device_data)
#         xml_root_element = ElementTree.fromstring(device_data)
#         #xml_root_element.set("xmlns", "http://tail-f.com/ned/cisco-ios-xr")
#         device_data=parseString(ElementTree.tostring(xml_root_element)).toxml()
#         device_data_pretty = BeautifulSoup(device_data, 'xml').prettify()
#         print('HEADERS:',restconf_headers,'\nDATA:',device_data_pretty)


  with io.open(fileName) as xml_file:
    xml_et = ElementTree.parse(xml_file)
    root = xml_et.getroot()

    print(root.tag.split('}')[1] if '}' in root.tag else root.tag, root.text.replace('\n','').replace(' ',''))
  for child in root:
    print(child.tag.split('}')[1] if '}' in child.tag else child.tag, child.text.replace('\n','').replace(' ',''))
    #print(child.tag, child.text)

  print(ElementTree.tostring(root, encoding='utf8').decode('utf8'))


#     if get_value: print(50*'-','\nVALUE:',sub_xml)
#     else: print(50*'-','\nSUBXML:',sub_xml)
#     if sub_xml and not get_value:
#       ### WRITE FILE WITH TIMESTAMP ==============================================
#       now = datetime.datetime.now()
#       timestring='%04d%02d%02d_%02d%02d%02d'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
#       with open(fileName+'_'+xml_key+'_'+timestring+'.xml', 'w', encoding='utf8') as outfile:
#         json.dump(sub_xml, outfile,  indent=2)
#         outfile.close()

if __name__ == "__main__":
    main()
