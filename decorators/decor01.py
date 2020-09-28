#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, logging, traceback
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


def makedecor(function_to_decorate):
    def wrapper(*args, **kwargs):
        print('aaaaaaa')
        print(args)
        print(kwargs)
        function_to_decorate(*args, **kwargs)
        print('bbbbb')
    return wrapper


def decorated_function():
    print 'I am the decorated function.'


logging.raiseExceptions = False


if __name__ != "__main__": sys.exit(0)
try:

    decorated_function = makedecor(decorated_function)  

    decorated_function()


except SystemExit: pass
except:
    traceback_found = traceback.format_exc()
    print(str(traceback_found))


