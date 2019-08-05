#!/usr/bin/python

import sys, os, io, paramiko, json , copy
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




class CGI_print():    
    def __init__(self):
        self.debug = True
        self.START_EPOCH = time.time()
        self.gci_active = None
        self.data, self.submit_form, self.username, self.password = \
            self.read_cgibin_get_post_form()
        if self.submit_form or len(self.data)>0: self.gci_active = True
        if self.gci_active:
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (self.submit_form if self.submit_form else 'No submit'))
        
    def __del__(self):
        self.print_html('\nEND[script runtime = %d sec]. '%(time.time() - self.START_EPOCH))
        if self.gci_active: print("</body></html>")
        
    def read_cgibin_get_post_form(self):
        # import collections, cgi
        # import cgitb; cgitb.enable()
        data, submit_form, username, password = collections.OrderedDict(), '', '', ''
        form = cgi.FieldStorage()
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["submit","username","password"]: 
                data[variable] = value
            if variable == "submit": submit_form = value
            if variable == "username": username = value
            if variable == "password": password = value
        return data, submit_form, username, password

    def print_GCI_data(self):
        if self.gci_active and self.debug:  
            for key, value in self.data.items(): 
                self.print_html("CGI_DATA[%s:%s] \n" % (str(key), str(value)))


    def print_html(self, text):
        if self.debug: 
            if self.gci_active: 
                if isinstance(text, six.string_types): 
                    text = text.replace('\n','<br/>')
            print(text)
            if self.gci_active: print('<br/>');

    def print_html_paragraph(self, text):
        if self.debug: 
            if self.gci_active: 
                print('<p>')
                if isinstance(text, six.string_types): 
                    text = text.replace('\n','<br/>')    
            print(text);
            if self.gci_active: print('</p>')
            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
gci_instance = CGI_print()
gci_instance.print_GCI_data()

#print_html('LOGDIR[%s] \n'%(LOGDIR))
CGI_print.print_html(gci_instance,'aaa')
gci_instance.print_html('aaa') 
#gci_instance.print_html(aaa)          
gci_instance.print_html(['aaa2','aaa3'])




