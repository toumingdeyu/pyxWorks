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

### https://stackoverflow.com/questions/884410/how-to-return-a-function-value-with-decorator-and-thread
import threading

# Callable that stores the result of calling the given callable f.
class ResultCatcher:
    def __init__(self, f):
        self.f = f
        self.val = None

    def __call__(self, *args, **kwargs):
        self.val = self.f(*args, **kwargs)

def threaded(f):
    def decorator(*args,**kargs):
        # Encapsulate f so that the return value can be extracted.
        retVal = ResultCatcher(f)

        th = threading.Thread(target=retVal, args=args)
        th.start()
        th.join()

        # Extract and return the result of executing f.
        return retVal.val

    decorator.__name__ = f.__name__
    return decorator

@threaded
def add_item(a, b):
    return a + b

print(add_item(2, 2))


