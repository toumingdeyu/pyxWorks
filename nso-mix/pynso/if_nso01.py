#!/usr/bin/python
### use python3

import sys
import optparse
from pprint import pprint
from pynso.client import NSOClient
from pynso.datastores import DatastoreType

### commandline argumets handling
ScriptName=sys.argv[0]
#print(ScriptName)
parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()
if not args or len(sys.argv) != 2:
  print("SYNTAX: python %s NSOpassword" % (ScriptName))
  sys.exit(1)
else:
  password=args[0]


### main -----------------------------------------------------------------------
def main(argv):
  # Setup a client - pynso.client.NSOClient(host, username, password, port=8080, ssl=False)
  #client = NSOClient('127.0.0.1', 'localnso', 'password...',port=8080, ssl=False)
  client = NSOClient('192.168.56.101', 'localnso', password , ssl=False)

  # Get information about the API
  print('--- Getting API version number -------------------------------')
  pprint(client.info()['version'])

  # Get the information about the running datastore
  print('--- Getting the contents of the running datastore ---------------------')
  pprint(client.get_datastore(DatastoreType.RUNNING))

  # Get a data path
  print('--- Getting a specific data path: snmp:snmp namespace and the agent data object ---')
  pprint(client.get_data(DatastoreType.RUNNING, ('snmp:snmp', 'agent')))

if __name__ == "__main__":
  main(sys.argv[1:])