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


### UNIX TEXT COLORS ##########################################################
class bcolors:
        DEFAULT    = '\033[99m'
        WHITE      = '\033[97m'
        CYAN       = '\033[96m'
        MAGENTA    = '\033[95m'
        HEADER     = '\033[95m'
        OKBLUE     = '\033[94m'
        BLUE       = '\033[94m'
        YELLOW     = '\033[93m'
        GREEN      = '\033[92m'
        OKGREEN    = '\033[92m'
        WARNING    = '\033[93m'
        RED        = '\033[91m'
        FAIL       = '\033[91m'
        GREY       = '\033[90m'
        ENDC       = '\033[0m'
        BOLD       = '\033[1m'
        UNDERLINE  = '\033[4m'


### HTML ESCAPE - TEXT TO HTML ################################################
def html_escape(text = None, pre_tag = None):
    escaped_text = str()
    if text and not pre_tag:
        escaped_text = str(text.replace('&','&amp;').\
            replace('<','&lt;').replace('>','&gt;').\
            replace(' ','&nbsp;').\
            replace('"','&quot;').replace("'",'&apos;').\
            replace('\n','<br/>'))
    elif text and pre_tag:
        ### OMMIT SPACES,QUOTES AND NEWLINES ##################################
        escaped_text = str(text.replace('&','&amp;').\
            replace('<','&lt;').replace('>','&gt;'))
    return escaped_text


### CONVERT UNIX COLORS TO HTML COLORS ########################################
def unix_colors_to_html_colors(text = None):
    color_text = text
    if text and '\033[' in text:
        color_text = color_text.replace(bcolors.DEFAULT,'')
        color_text = color_text.replace(bcolors.HEADER,'')
        color_text = color_text.replace(bcolors.WHITE,'')
        color_text = color_text.replace(bcolors.ENDC,'</p>')
        color_text = color_text.replace(bcolors.CYAN,'<p style="color:%s;">' % ('cyan'))
        color_text = color_text.replace(bcolors.MAGENTA,'<p style="color:%s;">' % ('magenta'))
        color_text = color_text.replace(bcolors.BLUE,'<p style="color:%s;">' % ('blue'))
        color_text = color_text.replace(bcolors.OKBLUE,'<p style="color:%s;">' % ('blue'))
        color_text = color_text.replace(bcolors.GREEN,'<p style="color:%s;">' % ('green'))
        color_text = color_text.replace(bcolors.OKGREEN,'<p style="color:%s;">' % ('green'))
        color_text = color_text.replace(bcolors.YELLOW,'<p style="color:%s;">' % ('yellow'))
        color_text = color_text.replace(bcolors.WARNING,'<p style="color:%s;">' % ('yellow'))
        color_text = color_text.replace(bcolors.RED,'<p style="color:%s;">' % ('red'))
        color_text = color_text.replace(bcolors.FAIL,'<p style="color:%s;">' % ('red'))
        color_text = color_text.replace(bcolors.GREY,'<p style="color:%s;">' % ('gray'))
        color_text = color_text.replace(bcolors.BOLD,'')
        color_text = color_text.replace(bcolors.UNDERLINE,'')
    return color_text


### HTML COLORIZER OF NONE COLURED LOGFILES ###################################
def html_colorizer(text = None):
    color_text = text
    ### IF UNIX COLORS OCCURS, FILE IS ALREADY COLORED ########################
    if text and not '\033[' in text:
        color_text = str()
        for line in text.splitlines():
            if 'REMOTE_COMMAND:' in line or 'LOCAL_COMMAND:' in line \
                or 'EVAL:' in line or 'EXEC:' in line \
                or 'CHECKING COMMIT ERRORS.' in line:
                color_text += '<p style="color:blue;">%s</p>' % (line)
            elif ' SUCCESSFULL.' in line:
                color_text += '<p style="color:green;">%s</p>' % (line)
            elif 'CONFIGURATION PROBLEM FOUND:' in line \
                or ' FAILED!' in line:
                color_text += '<p style="color:red;">%s</p>' % (line)
            else: color_text += line + '\n'
    return color_text


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

    print("Content-type:text/html")
    print("Status: %s %s\r\n\r\n\r\n" % ('200',""))

    ### LOGFILE SECURITY ######################################################
    if not logfile:
        print('<html><head></head><body><pre>' + 'Logfile is not inserted.' \
            + '</pre></html></body>')
        sys.exit(0)
    elif 'LOG' in str(logfile).upper() or 'HTM' in str(logfile).upper(): pass
    else:
        print('<html><head></head><body><pre>' + 'Inserted file is not logfile.' \
            + '</pre></html></body>')
        sys.exit(0)

    try:
        with open(logfile,"r") as file:
            file_opened = True
            logfile_content = file.read()
            if '<html>' in logfile_content:
                print(logfile_content)
            else:
                print('<html><head></head><body><pre>' + \
                    unix_colors_to_html_colors(html_colorizer(html_escape(logfile_content, pre_tag = True))) \
                    + '</pre></html></body>')
    except: pass

    if not file_opened:
        print('<html><head></head><body><pre>' + 'Logfile %s not found.' % \
            (logfile) + '</pre></html></body>')

except SystemExit: pass
except:
    traceback_found = True
    print(traceback.format_exc())