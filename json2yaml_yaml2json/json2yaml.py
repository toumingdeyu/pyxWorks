#!/usr/bin/python
### use python3

import sys
import os
import io
import optparse
import json
import yaml

### commandline argumets handling
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()

if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s nameOfInputFile.json" % (ScriptName))
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


### main -----------------------------------------------------------------------
def main(argv):
  print(read_JSON_file())
  write_YAML_file(read_JSON_file())

if __name__ == "__main__":
  main(sys.argv[1:])