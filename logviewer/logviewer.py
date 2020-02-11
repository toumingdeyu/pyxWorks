#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, logging
import traceback
import getopt
import getpass
import telnetlib
import time, datetime
import difflib
import subprocess
import re
import argparse
import glob
import socket
import six
import collections

import cgi
#import cgitb; cgitb.enable()
import requests
from mako.template import Template
from mako.lookup import TemplateLookup



###############################################################################
#
# def BEGIN MAIN
#
###############################################################################

if __name__ != "__main__": sys.exit(0)
try:
    logfile, form = None, None

    try: form = cgi.FieldStorage()
    except: pass
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable == "logfile": logfile = value

    if form:
        print("Content-type:text/html")
        print("Status: %s %s\r\n" % ('200',""))
        print("\r\n\r\n")

    if logfile:
        with open(logfile,"r") as file:
            logfile_content = file.read()
            if '<html>' in logfile_content:
                print(logfile_content)
            else: print('<pre>' + logfile_content + '</pre>')

except SystemExit: pass
except:
    traceback_found = True
    print(traceback.format_exc())