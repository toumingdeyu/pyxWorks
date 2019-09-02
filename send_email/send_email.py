#!/usr/bin/python

import sys, os, io, paramiko, json, copy, html
import cgi
import cgitb; cgitb.enable()
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
import requests


def send_me_email(subject='testmail', email_body = str(), file_name = None, email_address = None, username = None):
    def send_unix_email_body(mail_command):
        email_success = None
        try: 
            forget_it = subprocess.check_output(mail_command, shell=True)
            CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by command[%s] with result(%s)...'\
                %(subject,sugested_email_address,mail_command,forget_it), color = 'blue')
            email_success = True    
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by command[%s], PROBLEM=[%s]\n"\
                % (mail_command,str(e)) ,color = 'red')
        return email_success        
                
    if not 'WIN32' in sys.platform.upper():
        if username: my_account = username        
        else: my_account = subprocess.check_output('whoami', shell=True)
        ### WITH APACHE USER IS INSERTED USER NOT LOGGED IN SO FINGER WILL NOT WORK
        ### my_finger_line = subprocess.check_output('finger | grep "%s"'%(my_account.strip()), shell=True)
        ### my_name = my_finger_line.splitlines()[0].split()[1]
        ### my_surname = my_finger_line.splitlines()[0].split()[2]
        
        ### GETENT .. output='pnemec:x:3844:1003:Peter Nemec IPTAC Slovakia:/home/pnemec:/bin/bash'
        try: my_finger_line = ' '.join((subprocess.check_output('getent passwd "%s"'% \
            (my_account.strip()), shell=True)).split(':')[4].split()[:2])
        except: my_finger_line = None
        my_name = my_finger_line.splitlines()[0].split()[0]
        my_surname = my_finger_line.splitlines()[0].split()[1]

        try: ldap_email_address = subprocess.check_output(\
                'ldapsearch -LLL -x uid=%s mail' % (my_account), shell=True).\
                split('mail:')[1].splitlines()[0].strip()
        except: ldap_email_address = None
        
        if email_address: sugested_email_address = email_address
        elif ldap_email_address: sugested_email_address = ldap_email_address
        else: sugested_email_address = '%s.%s@orange.com' % (my_name, my_surname)
        
        if file_name: mail_command = 'echo | mutt -s "%s" -a %s -- %s' % \
                          (subject,file_name,sugested_email_address)
        else: mail_command = 'echo | mutt -s "%s" -- %s' % (subject,sugested_email_address)
        email_sent = send_unix_email_body(mail_command)
        if not email_sent:
            ### UUENCODE does not provide attaching fo files
            ### mail_command = 'uuencode %s %s | mail -s "%s" %s' % \
            ###     (file_name,file_name,subject,sugested_email_address)         
            mail_command = 'mail -s "%s" %s' % (subject,sugested_email_address)
            send_unix_email_body(mail_command)
    else:
        ### NEEDED 'pip install pywin32'
        if not 'win32com.client' in sys.modules: import win32com.client
        olMailItem, email_application = 0, 'Outlook.Application'
        try:
            ol = win32com.client.Dispatch(email_application)
            msg = ol.CreateItem(olMailItem)
            msg.To, msg.Subject, msg.Body = email_address, subject, email_body
            msg.Attachments.Add(file_name)
            msg.Send()
            ol.Quit()
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by application[%s], PROBLEM=[%s]\n"\
                % (email_application,str(e)) ,color = 'red')            


class CGI_CLI(object):
    """
    CGI_handle - Simple statis class for handling CGI parameters and 
                 clean (debug) printing to HTML/CLI    
       Notes:  - In case of cgi_parameters_error - http[500] is raised, 
                 but at least no appache timeout occurs...
    """ 
    # import collections, cgi, six
    # import cgitb; cgitb.enable()
     
    debug = True
    initialized = None
    START_EPOCH = time.time()
    cgi_parameters_error = None
    cgi_active = None
    
    @staticmethod        
    def __cleanup__():
        CGI_CLI.uprint('\nEND[script runtime = %d sec]. '%(time.time() - CGI_CLI.START_EPOCH))
        if CGI_CLI.cgi_active: print("</body></html>")

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor 
        --> Register __cleanup__ in system
        """
        if not 'atexit' in sys.modules: import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi():
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.initialized = True 
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), '', '', ''   
        try: form = cgi.FieldStorage()
        except: 
            form = collections.OrderedDict()
            CGI_CLI.cgi_parameters_error = True
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["submit","username","password"]: 
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
        if CGI_CLI.submit_form or len(CGI_CLI.data)>0: CGI_CLI.cgi_active = True
        if CGI_CLI.cgi_active:
            if not 'cgitb' in sys.modules: import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        if not 'atexit' in sys.modules: import atexit; atexit.register(CGI_CLI.__cleanup__)
        return None

    @staticmethod 
    def oprint(text, tag = None):
        if CGI_CLI.debug: 
            if CGI_CLI.cgi_active:
                if tag and 'h' in tag: print('<%s>'%(tag))
                if tag and 'p' in tag: print('<p>')
                if isinstance(text, six.string_types): 
                    text = str(text.replace('\n','<br/>').replace(' ','&nbsp;'))
                else: text = str(text)   
            print(text)
            if CGI_CLI.cgi_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod 
    def uprint(text, tag = None, color = None, name = None, jsonprint = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name = copy.deepcopy(text), str()
        if CGI_CLI.debug:
            if jsonprint:
                if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                    try: print_text = json.dumps(text, indent = 4)
                    except: pass   
            if name==True:
                if not 'inspect.currentframe' in sys.modules: import inspect
                callers_local_vars = inspect.currentframe().f_back.f_locals.items()
                var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
                if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
            elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '
            
            print_text = str(print_text)
            if CGI_CLI.cgi_active:
                if tag and 'h' in tag: print('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
                if color or tag and 'p' in tag: tag = 'p'; print('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
                if isinstance(print_text, six.string_types): 
                    print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                        replace('>','&gt;').replace('\n','<br/>').replace(' ','&nbsp;')) 
            print(print_name + print_text)
            del print_text
            if CGI_CLI.cgi_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod
    def print_args():
        if CGI_CLI.cgi_active:
            try: print_string = 'CGI_args = ' + json.dumps(CGI_CLI.data) 
            except: print_string = 'CGI_args = '                 
        else: print_string = 'CLI_args = %s' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string        


            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
#CGI_CLI()
CGI_CLI.init_cgi()
CGI_CLI.print_args()

send_me_email(subject = 'testmail', file_name = None, username = CGI_CLI.username if CGI_CLI.username else None)





