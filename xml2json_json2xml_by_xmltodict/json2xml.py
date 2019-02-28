#!/usr/bin/python
### use python3

import sys
import os
import io
import optparse
import json
import yaml
import lxml
#from lxml import etree, objectify
import xmltodict 



### commandline argumets handling
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s nameOfInputFile" % (ScriptName))
  sys.exit(1)
else:
  fileName=args[0]

### read JSON file
def read_JSON_file():
  variables={}
  with io.open(fileName) as json_file:
    variables = json.load(json_file)
  return variables

### Write YAML file
def write_YAML_file(variables):
  with io.open(fileName+'.yaml', 'w', encoding='utf8') as outfile:
    yaml.dump(variables, outfile, default_flow_style=False, allow_unicode=True)

### Read YAML file
def read_YAML_file():
  with open(fileName, 'r') as stream:
    variables = yaml.load(stream)
    return variables

### Write JSON file
def write_JSON_file(variables):
  with io.open(fileName+'.json', 'w', encoding='utf8') as outfile:
    json.dump(variables, outfile,  indent=4)

### Read XML file
def read_XML_file():
  xml=''
  with open(fileName, 'r') as f:
    str=f.read()
    variables = xmltodict.parse(str)
  return variables

### Write XML file
def write_XML_file(variables):
  with io.open(fileName+'.xml', 'w', encoding='utf8') as outfile:
    outfile.write(xmltodict.unparse(variables))

### main -----------------------------------------------------------------------
def main(argv):
  #print(read_JSON_file())
  #write_YAML_file(read_JSON_file())
  print(read_JSON_file())
  write_XML_file(read_JSON_file())
  ### conversion from ordered dictionary to yaml does not work ok, because ordered dicts are interpreted as tuples/lists in yaml
  #write_YAML_file(read_XML_file())

if __name__ == "__main__":
  main(sys.argv[1:])