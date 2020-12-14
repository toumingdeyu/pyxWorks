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

### https://gist.github.com/Zearin/2f40b7b9cfc51132851a ###

def makedecor(function_to_decorate):
    def wrapper(*args, **kwargs):
        print('BEFORE')
        print('function_name = ' + function_to_decorate.__name__, args, kwargs)
        function_to_decorate(*args, **kwargs)
        print('AFTER')
    return wrapper


def decorated_function(*args, **kwargs):
    print('decorated function execution.', args, kwargs)
    print(kwargs.get('a'))


logging.raiseExceptions = False


if __name__ != "__main__": sys.exit(0)
try:

    decorated_function = makedecor(decorated_function)  

    decorated_function("aaa", a=1, b=3)


except SystemExit: pass
except:
    traceback_found = traceback.format_exc()
    print(str(traceback_found))


