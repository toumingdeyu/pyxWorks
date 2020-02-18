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


def html_escape(text = None, pre_tag = None):
    escaped_text = str()
    if text and not pre_tag:
        escaped_text = str(text.replace('&','&amp;').\
            replace('<','&lt;').replace('>','&gt;').\
            replace(' ','&nbsp;').\
            replace('"','&quot;').replace("'",'&apos;').\
            replace('\n','<br/>'))
    elif text and pre_tag:
        ### OMMIT SPACES,QUOTES AND NEWLINES ##############################
        escaped_text = str(text.replace('&','&amp;').\
            replace('<','&lt;').replace('>','&gt;'))
    return escaped_text


###############################################################################
#
# def BEGIN MAIN
#
###############################################################################

if __name__ != "__main__": sys.exit(0)
try:
    logfile, form, file_opened = None, None, None

    try: form = cgi.FieldStorage()
    except: pass
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable == "logfile": logfile = value

    ### if form: ###
    print("Content-type:text/html")
    print("Status: %s %s\r\n" % ('200',""))
    print("\r\n\r\n")

    ### LOGFILE SECURITY ###
    if not 'LOG' in logfile.upper():
        print('<pre>' + 'Inserted file is not logfile.' + '</pre>')
        sys.exit(0)

    if logfile:
        try:
            with open(logfile,"r") as file:
                file_opened = True
                logfile_content = file.read()
                if '<html>' in logfile_content:
                    print(logfile_content)
                else:
                    print('<pre>' + html_escape(logfile_content, pre_tag = True) + '</pre>')
        except: pass
        if not file_opened: print('<pre>' + 'Logfile %s not found.' % (logfile) + '</pre>')
    else: print('<pre>' + 'No logfile inserted.' + '</pre>')

except SystemExit: pass
except:
    traceback_found = True
    print(traceback.format_exc())