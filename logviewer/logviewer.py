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
    ### IF UNIX COLORS OCCURS, FILE IS ALREADY COLORED ########################
    if text and '\033[' in text:
        color_text = str()
        for line in text.splitlines():
            line = line.strip().replace(bcolors.DEFAULT,'').\
                replace(bcolors.HEADER,'').replace(bcolors.BOLD,'').\
                replace(bcolors.UNDERLINE,'').replace(bcolors.ENDC,'')

            ### ONLY ONE P TAG PER LINE #######################################
            color = 'black'
            if '\033[' in line:
                if bcolors.CYAN in line:
                    color = 'cyan'
                    line = line.replace(bcolors.CYAN,'')
                if bcolors.MAGENTA in line:
                    color = 'magenta'
                    line = line.replace(bcolors.MAGENTA,'')
                if bcolors.BLUE in line:
                    color = 'blue'
                    line = line.replace(bcolors.BLUE,'')
                if bcolors.GREEN in line:
                    color = 'limegreen'
                    line = line.replace(bcolors.GREEN,'')
                if bcolors.YELLOW in line:
                    color = 'orange'
                    line = line.replace(bcolors.YELLOW,'')
                if bcolors.RED in line:
                    color = 'red'
                    line = line.replace(bcolors.RED,'')
                if bcolors.GREY in line:
                    color = 'gray'
                    line = line.replace(bcolors.GREY,'')
                color_text += '<p style="color:%s;">%s</p>' % (color,line)
            else: color_text += line + '\n'
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
                color_text += '<p style="color:limegreen;">%s</p>' % (line)
            elif 'CONFIGURATION PROBLEM FOUND:' in line \
                or ' FAILED!' in line:
                color_text += '<p style="color:red;">%s</p>' % (line)
            elif 'PROBLEM[' in line:
                color_text += '<p style="color:magenta;">%s</p>' % (line)
            elif '==> ' in line or ' --> ' in line:
                color_text += '<p style="color:blue;">%s</p>' % (line)
            else: color_text += line + '\n'
    return color_text


def get_os_output(cmd_line = None):
    os_output = str()
    if cmd_line:
        os_output = subprocess.check_output(str(cmd_line), \
            stderr=subprocess.STDOUT, shell=True).decode("utf-8")
    return os_output


def print_logviewer_links(directory = None):
    file_list = []
    if directory: file_list = get_os_output('ls %s' % (directory)).split()

    iptac_server = get_os_output(cmd_line = 'hostname').strip()

    if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
    else: urllink = 'https://%s/cgi-bin/' % (iptac_server)

    print('<h1>Directory %s file(s):</h1>\n' % (directory))

    for logfilename in file_list:
        if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, directory + '/' + logfilename)
        else: logviewer = './logviewer.py?logfile=%s' % (directory + '/' + logfilename)
        print('<p style="color:blue;"><a href="%s" target="_blank" style="text-decoration: none">%s</a></p>\n' \
            % (logviewer, logfilename))


###############################################################################
#
# def BEGIN MAIN
#
###############################################################################

if __name__ != "__main__": sys.exit(0)
try:
    logfile, form, file_opened, dir1, dir2 = None, None, None, None, None

    try: form = cgi.FieldStorage()
    except: pass
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable == "logfile": logfile = value
        if variable == "dir1": dir1 = True
        if variable == "dir2": dir2 = True

    print("Content-type:text/html")
    print("Status: %s %s\r\n\r\n\r\n" % ('200',""))

    ### DISPLAY HTML MENU #####################################################
    if not logfile:
        if dir1 or dir2:
            if dir1: print_logviewer_links('/var/PrePost')
            if dir2: print_logviewer_links('/var/www/cgi-bin/logs')
            sys.exit(0)
        else:
            i_pyfile = sys.argv[0]
            try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
            except: i_pyfile = i_pyfile.strip()
            print('<html><head></head><body><form action = "/cgi-bin/%s">Insert logfile: <input type="text" name="logfile"><br/>' % (i_pyfile))
            print('<input type="checkbox" name="dir1" value="on"> ls /var/PrePost<br/>')
            print('<input type="checkbox" name="dir2" value="on"> ls /var/www/cgi-bin/logs<br/>')
            print('<input id="OK" type="submit" name="submit" value="OK">')
            print('</form></html></body>')
            sys.exit(0)

    ### LOGFILE SECURITY ######################################################
    if not logfile:
        print('<html><head></head><body><pre>' + 'Logfile is not inserted.' \
            + '</pre></html></body>')
        sys.exit(0)
    elif 'LOG' in str(logfile).upper() or 'HTM' in str(logfile).upper() \
        or '-PRE' in str(logfile).upper() or '-POST' in str(logfile).upper(): pass
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