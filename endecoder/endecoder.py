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
import cgitb; cgitb.enable()
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
    text_to_encode, form, file_opened, dir1, dir2 = None, None, None, None, None

    try: form = cgi.FieldStorage()
    except: pass
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable == "text_to_encode": text_to_encode = value

    print("Content-type:text/html")
    print("Status: %s %s\r\n\r\n\r\n" % ('200',""))
    print('<html><head></head><body>')

    ### DISPLAY HTML MENU #####################################################
    if not text_to_encode:
        i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        print('<form action = "/cgi-bin/%s">Insert text_to_encode: <input type="text" name="text_to_encode"><br/>' % (i_pyfile))
        print('<input id="OK" type="submit" name="submit" value="OK">')
    else:
        text_encoded = text_to_encode.encode('base64','strict');
        print("'%s'.encode('base64','strict') ---> '%s'<br/>" %(text_to_encode,text_encoded))

        text_decoded = text_encoded.decode('base64','strict')
        print("'%s'.decode('base64','strict') ---> '%s'<br/>" %(text_encoded,text_decoded))

    print('</html></body>')
except SystemExit: pass
except:
    traceback_found = True
    print(traceback.format_exc())