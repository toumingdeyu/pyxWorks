#!/usr/bin/python
# Author: Peter Nemec , 25.4.2018
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

parser=optparse.OptionParser(version="1.0.0", description="")
(options, args) = parser.parse_args()

if not args or len(sys.argv) -1 != 1:
  print("python %s nameOfInputFile" % (ScriptName))
  sys.exit(1)
else:
  frName=args[0]

def main(argv):
  WordList=[]
  FirstOccuranceDictionary={}
  try:
    fr = open(frName, "r")
  except:
    print('File %s is not readable or not exists!'%(frName))

  line=0
  for lineText in fr.readlines():
    line=line+1
    wordsInLine=lineText.split()
    RepeatingLineSequence=''
    for word in wordsInLine:
        if word in WordList:
          RepeatingLineSequence=RepeatingLineSequence+'%s '%(word)
          ##print("    Repeat '%s' on line %d (first on line %s)."%(word,line,FirstOccuranceDictionary.get(word)))
        else:
          WordList.append(word)
          FirstOccuranceDictionary[word]=line
    if len(RepeatingLineSequence.split())>1:
      printString='Repeating Word Sequence on line %s: [ %s]' %(line,RepeatingLineSequence)
      print(printString)
  fr.close()

if __name__ == "__main__":
  main(sys.argv[1:])
