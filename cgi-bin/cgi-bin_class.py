#!/usr/bin/python

import sys, os, io, paramiko, json, copy, html
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
###import cgitb; cgitb.enable()
import requests


class CGI_CLI_handle():
    """
    CGI_handle - Simple class for handling CGI parameters and 
                 clean (debug) printing to HTML/CLI    
       Notes:  - In case of cgi_parameters_error - http[500] is raised, 
                 but at least no appache timeout occurs...
    """ 
    # import collections, cgi, six
    # import cgitb; cgitb.enable()
    def __init__(self):
        self.debug = True
        self.START_EPOCH = time.time()
        self.cgi_parameters_error = None
        self.cgi_active = None
        self.data, self.submit_form, self.username, self.password = \
            self.read_cgibin_get_post_form()
        if self.submit_form or len(self.data)>0: self.cgi_active = True
        if self.cgi_active:
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (self.submit_form if self.submit_form else 'No submit'))
        # if self.cgi_parameters_error:
            # import cgitb; cgitb.enable()   
            # print("Content-type:text/html\n\n")
            # print("<html><head><title>%s</title></head><body>" % 
                # (self.submit_form if self.submit_form else 'No submit'))         
            # self.uprint('\nNO INSERTED CGI PARAMETERS!\n')
        
    def __del__(self):
        self.uprint('\nEND[script runtime = %d sec]. '%(time.time() - self.START_EPOCH))
        if self.cgi_active: print("</body></html>")
        
    def read_cgibin_get_post_form(self):
        data, submit_form, username, password = collections.OrderedDict(), '', '', ''
        try: form = cgi.FieldStorage()
        except: 
            form = collections.OrderedDict()
            self.cgi_parameters_error = True
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

    def uprint(self, text, tag = None):
        if self.debug: 
            if self.cgi_active:
                if tag and 'h' in tag: print('<%s>'%(tag))
                if tag and 'p' in tag: print('<p>')
                if isinstance(text, six.string_types): 
                    text = str(text.replace('\n','<br/>').replace(' ','&nbsp;'))
                else: text = str(text)   
            print(text)
            if self.cgi_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    def __repr__(self):
        if self.cgi_active:
            try: print_string = 'CGI_args=' + json.dumps(self.data) + ' <br/>'
            except: print_string = 'CGI_args=' + ' <br/>'                
        else: print_string = 'CLI_args=%s \n' % (str(sys.argv[1:]))  
        return print_string        
            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
gci_instance = CGI_CLI_handle()
print(repr(gci_instance))
#print(str(gci_instance))

CGI_CLI_handle.uprint(gci_instance,'aaa')
gci_instance.uprint('aaa')          
gci_instance.uprint(['aaa2','aaa3'])
gci_instance.uprint({'aaa4':'aaa5'}, tag = 'h1')
#cgi.print_environ()








