#!/usr/bin/python
# Author: Peter Nemec , 22.2.2018 , v1.0.1 strip
import sys
import os
import optparse
import fileinput
import glob
import datetime
import time
import socket
import platform
import stat
import string
import subprocess
import re
import pdb

ScriptName=sys.argv[0]

parser=optparse.OptionParser(version="1.0.1", description="")
(options, args) = parser.parse_args()

if not args or len(sys.argv) -1 != 1:
  print("python %s nameOfFileToUCMStableFormat" % (ScriptName))
  sys.exit(1)
else:
  frName=args[0]

def main(argv):
  HeaderColumn=" |_. "
  BobyColumn=" | "
  LineEnd=" | "
  try:
    fr = open(frName, "r")
    i=0
    for line in fr.readlines():
      if i==0:
        print("%s%s%s"%(HeaderColumn,line.replace("\t",HeaderColumn).replace("\n","").replace("    ",""),LineEnd))
      else:
        print("%s%s%s"%(BobyColumn,line.replace("\t",BobyColumn).replace("\n","").replace("    ",""),LineEnd))
      i=i+1
    fr.close()
  except:
    print('File %s is not readable or not exists!'%(frName))
if __name__ == "__main__":
  main(sys.argv[1:])
