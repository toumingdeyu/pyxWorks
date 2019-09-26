#!/usr/bin/python36

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
import ipaddress

from mako.template import Template
from mako.lookup import TemplateLookup
import cgi
import cgitb; cgitb.enable()
import requests
#import interactive
#python 2.7 problem - hack 'pip install esptool'
import netmiko
if int(sys.version_info[0]) == 3: import pymysql
else: import mysql.connector

import cgitb; cgitb.enable()
import binascii

step1_string = 'Submit step 1'
step2_string = 'Submit step 2'

try:    WORKDIR         = os.environ['HOME']
except: WORKDIR         = str(os.path.dirname(os.path.abspath(__file__)))
if WORKDIR: LOGDIR      = os.path.join(WORKDIR,'logs')

try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()

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

class nocolors:
        DEFAULT    = ''
        WHITE      = ''
        CYAN       = ''
        MAGENTA    = ''
        HEADER     = ''
        OKBLUE     = ''
        BLUE       = ''
        YELLOW     = ''
        GREEN      = ''
        OKGREEN    = ''
        WARNING    = ''
        RED        = ''
        FAIL       = ''
        GREY       = ''
        ENDC       = ''
        BOLD       = ''
        UNDERLINE  = ''



###############################################################################
#
# Function and Class
#
###############################################################################

def read_data_json_from_logfile(filename = None, printall = None):
    data_loaded, text = collections.OrderedDict(), None
    if filename:
        with open(filename,"r") as fp:
            text = fp.read()
        if text:
            try: data_json_text = text.split('EVAL_COMMAND: return_bgp_data_json()')[1]
            except: data_json_text = str()
            if data_json_text:
                try:
                    data_loaded = json.loads(data_json_text, \
                        object_pairs_hook = collections.OrderedDict)
                except: pass
                #print("LOADED_data: ",data_loaded)
                if printall: print("\nLOADED JSON data: ")
                if printall: print(json.dumps(data_loaded, indent=2))
    return data_loaded


def generate_file_name(prefix = None, suffix = None , directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(WORKDIR,'logs')
    if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
    if os.path.exists(LOGDIR):
        if not prefix: filename_prefix = os.path.join(LOGDIR,'device')
        else: filename_prefix = prefix
        if not suffix: filename_suffix = 'log'
        else: filename_suffix = suffix
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,sys.argv[0].replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/')\
            .split('/')[-1],USERNAME,filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath         


def dict_to_json_string(dict_data = None, indent = None):
    if not indent: indent = 4 
    try: json_data = json.dumps(dict_data, indent = indent)
    except: json_data = ''
    return json_data

def get_variable_name(var):
    import inspect
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    var_list = [var_name for var_name, var_val in callers_local_vars if var_val is var]
    return str(','.join(var_list))

def get_json_with_variable_name(dict_data = None, indent = None):
    return '\n' + get_variable_name(data) + ' = ' + dict_to_json_string(data) + '\n'


def find_last_logfile():
    most_recent_logfile = None
    log_file_name=os.path.join(LOGDIR,huawei_device_name.replace(':','_'). \
        replace('.','_').upper()) + '*' + USERNAME + '*vrp-' + vpn_name + \
        "*" + step1_string.replace(' ','_') + "*"
    log_filenames = glob.glob(log_file_name)
    if len(log_filenames) == 0:
        CGI_CLI.uprint(" ... Can't find any proper (%s) log file.\n"%(log_file_name))
    else:    
        most_recent_logfile = log_filenames[0]
        for item in log_filenames:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_logfile)):
                most_recent_logfile = item
    return most_recent_logfile


def find_duplicate_keys_in_dictionaries(data1, data2):
    duplicate_keys_list = None
    if data1 and data2:
        list1 = list(data1.keys())
        list2 = list(data2.keys())
        for item in list2:
            if item in list1:
                if not duplicate_keys_list: duplicate_keys_list = []
                duplicate_keys_list.append(list1)
    return duplicate_keys_list

##################################################################################

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
    def cli_parser():
        ######## Parse program arguments ##################################
        parser = argparse.ArgumentParser(
                            description = "Script %s v.%s" % (sys.argv[0], CGI_CLI.VERSION()),
                            epilog = "e.g: \n" )
        parser.add_argument("--version",
                            action = 'version', version = CGI_CLI.VERSION())
        parser.add_argument("--username",
                            action = "store", dest = 'username', default = str(),
                            help = "specify router user login") 
        parser.add_argument("--password",
                            action = "store", dest = 'password', default = str(),
                            help = "specify router password (test only...)")
        parser.add_argument("--getpass",
                            action = "store_true", dest = 'getpass', default = None,
                            help = "insert router password interactively getpass.getpass()")                                                        
        parser.add_argument("--pe_device",
                            action = "store", dest = 'pe_device',
                            default = str(),
                            help = "target pe router to check")
        parser.add_argument("--gw_device",
                            action = "store", dest = 'gw_device',
                            default = str(),
                            help = "target gw router to check")                    
        args = parser.parse_args()
        return args
    
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
    def init_cgi(interaction = None, os_environ_set = None):
        """ os_environ_set - (=None/False) php/ajax bug workarround, 
                             (=True) - http500 cgi.FieldStorage() workarround
        """
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.initialized = True 
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), '', '', ''
        if os_environ_set:    
            # WORKARROUND FOR VOID QUERY_STRING CAUSING HTTP500
            CGI_CLI.query_string = dict(os.environ).get('QUERY_STRING','CLI_MODE')
            if CGI_CLI.query_string != str() or \
                ('?' in dict(os.environ).get('REQUEST_URI',None) and \
                '=' in dict(os.environ).get('REQUEST_URI',None)):
                try: form = cgi.FieldStorage()
                except:      
                    form = collections.OrderedDict()
                    CGI_CLI.cgi_parameters_error = True
            else:                 
                form = collections.OrderedDict()
                CGI_CLI.cgi_active = True
                CGI_CLI.data = collections.OrderedDict()
        else:        
            ## PROBLEM - AJAX DOES NOT FILL VARIABLES QUERY_STRING, REQUEST_URI   
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
            print("Content-type:text/html")
            #print("Status: %s %s\r\n" % ('222',"afafff"))
            #print("Retry-After: 300")
            print("\r\n\r\n<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        if not 'atexit' in sys.modules: import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM CGI/CLI
        CGI_CLI.args = CGI_CLI.cli_parser()               
        try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
        except: CGI_CLI.PASSWORD        = str()
        try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
        except: CGI_CLI.USERNAME        = str()
        if CGI_CLI.args.username:        
            CGI_CLI.USERNAME = CGI_CLI.args.username
            CGI_CLI.PASSWORD = str()
            if interaction or CGI_CLI.args.getpass: CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
            elif CGI_CLI.args.password: CGI_CLI.password = CGI_CLI.args.password                
        if CGI_CLI.username: CGI_CLI.USERNAME = CGI_CLI.username
        if CGI_CLI.password: CGI_CLI.PASSWORD = CGI_CLI.password
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): bcolors = nocolors
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        CGI_CLI.cgi_save_files()        
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

    @staticmethod 
    def cgi_save_files():
        for key in CGI_CLI.data:
            if 'file[' in key: 
                filename = key.replace('file[','').replace(']','')
                if filename:
                    use_filename = filename.replace('/','\\') if 'WIN32' in sys.platform.upper() else filename
                    dir_path = os.path.dirname(use_filename)
                    if os.path.exists(dir_path):
                        file_content = CGI_CLI.data.get('file[%s]'%(filename),None)
                        if file_content:
                            try:                        
                                with open(use_filename, 'wb') as file:
                                    file.write(CGI_CLI.data.get('file[%s]'%(filename)))
                                    CGI_CLI.uprint('The file "' + use_filename + '" was uploaded.')
                            except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')   

    @staticmethod 
    def uprint(text, tag = None, tag_id = None, color = None, name = None, jsonprint = None):
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
                ### WORKARROUND FOR COLORING OF SIMPLE TEXT
                if color and not tag: tag = 'p'; 
                if tag: print('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"'%(color) if color else 'black'))
                if isinstance(print_text, six.string_types):
                    print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                        replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                        replace('\n','<br/>'))
            print(print_name + print_text)
            del print_text
            if CGI_CLI.cgi_active: 
                if tag: print('</%s>'%(tag))
                else: print('<br/>');

    @staticmethod 
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, color = None):
        """ formprint() - print simple HTML form
            form_data - string, just html raw OR list or dict values = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
                      - value in dictionary means cgi variable name / printed componenet value            
        """
        def subformprint(data_item):
            if isinstance(data_item, six.string_types): print(data_item)
            elif isinstance(data_item, (dict,collections.OrderedDict)):
                if data_item.get('raw',None): print(data_item.get('raw'))
                elif data_item.get('textcontent',None): 
                    print('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4"></textarea>'%\
                        (data_item.get('textcontent')))
                elif data_item.get('text'):
                    print('%s: <input type = "text" name = "%s"><br />'%\
                        (data_item.get('text','').replace('_',' '),data_item.get('text')))
                elif data_item.get('radio'):    
                    print('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                        (data_item.get('radio'),data_item.get('radio'),data_item.get('radio','').replace('_',' ')))
                elif data_item.get('checkbox'):
                    print('<input type = "checkbox" name = "%s" value = "on" /> %s'%\
                        (data_item.get('checkbox'),data_item.get('checkbox','').replace('_',' ')))
                elif data_item.get('dropdown'):
                    print('<select name = "dropdown[%s]">'%(data_item.get('dropdown')))
                    for option in data_item.get('dropdown').split(','):
                        print('<option value = "%s" selected>%s</option>')%(option,option)
                    print('</select>')
                elif data_item.get('file'):
                   print('Upload file: <input type = "file" name = "file[%s]" />'%(data_item.get('file').replace('\\','/')))  
                elif data_item.get('submit'):    
                    print('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%\
                        (data_item.get('submit'),data_item.get('submit')))

   
        ### START OF FORMPRINT ###
        formtypes = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
        i_submit_button = None if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            print('<br/>');
            if tag and 'h' in tag: print('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
            if color or tag and 'p' in tag: tag = 'p'; print('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
            print('<form action = "/cgi-bin/%s" enctype = "multipart/form-data" action = "save_file.py" method = "post">'%\
                (i_pyfile))
            ### RAW HTML ###
            if isinstance(form_data, six.string_types): print(form_data)
            ### STRUCT FORM DATA = LIST ###
            elif isinstance(form_data, (list,tuple)):
                for data_item in form_data: subformprint(data_item)
            ### JUST ONE DICT ###    
            elif isinstance(form_data, (dict,collections.OrderedDict)): subformprint(form_data)               
            if i_submit_button: subformprint({'submit':i_submit_button})
            print('</form>')
            if tag and 'p' in tag: print('</p>')
            if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod
    def VERSION(path_to_file = str(os.path.abspath(__file__))):
        if 'WIN32' in sys.platform.upper():
            file_time = os.path.getmtime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            file_time = stat.st_mtime
        return time.strftime("%y.%m.%d_%H:%M",time.gmtime(file_time)) 

    @staticmethod
    def print_args():
        from platform import python_version
        print_string = 'python[%s]\n' % (str(python_version()))
        print_string += 'version[%s]\n' % (CGI_CLI.VERSION())
        print_string += 'file[%s]\n' % (sys.argv[0])
        print_string += 'USERNAME[%s], PASSWORD[%s]\n' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No')
        print_string += 'remote_addr[%s]\n' % dict(os.environ).get('REMOTE_ADDR','')
        print_string += 'browser[%s]\n' % dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_args[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4)))
            except: pass                 
        else: print_string += 'CLI_args = %s' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string

    @staticmethod
    def print_env():        
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', jsonprint = True)



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
    def cli_parser():
        ######## Parse program arguments ##################################
        parser = argparse.ArgumentParser(
                            description = "Script %s v.%s" % (sys.argv[0], CGI_CLI.VERSION()),
                            epilog = "e.g: \n" )
        parser.add_argument("--version",
                            action = 'version', version = CGI_CLI.VERSION())
        parser.add_argument("--username",
                            action = "store", dest = 'username', default = str(),
                            help = "specify router user login") 
        parser.add_argument("--password",
                            action = "store", dest = 'password', default = str(),
                            help = "specify router password (test only...)")
        parser.add_argument("--getpass",
                            action = "store_true", dest = 'getpass', default = None,
                            help = "insert router password interactively getpass.getpass()")
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "target router to check")
        parser.add_argument("--printall",action = "store_true", default = None,
                            help = "print all lines, changes will be coloured")                            
        # parser.add_argument("--pe_device",
                            # action = "store", dest = 'pe_device',
                            # default = str(),
                            # help = "target pe router to check")
        # parser.add_argument("--gw_device",
                            # action = "store", dest = 'gw_device',
                            # default = str(),
                            # help = "target gw router to check")                    
        args = parser.parse_args()
        return args
    
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
    def init_cgi(interaction = None):
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
        ### GAIN USERNAME AND PASSWORD FROM CGI/CLI
        CGI_CLI.args = CGI_CLI.cli_parser()               
        try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
        except: CGI_CLI.PASSWORD        = str()
        try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
        except: CGI_CLI.USERNAME        = str()
        if CGI_CLI.args.username:        
            CGI_CLI.USERNAME = CGI_CLI.args.username
            CGI_CLI.PASSWORD = str()
            if interaction or CGI_CLI.args.getpass: CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
            elif CGI_CLI.args.password: CGI_CLI.password = CGI_CLI.args.password                
        if CGI_CLI.username: CGI_CLI.USERNAME = CGI_CLI.username
        if CGI_CLI.password: CGI_CLI.PASSWORD = CGI_CLI.password
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): bcolors = nocolors
        CGI_CLI.uprint('USERNAME[%s], PASSWORD[%s]' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No'))        
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

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
    def VERSION(path_to_file = str(os.path.abspath(__file__))):
        if 'WIN32' in sys.platform.upper():
            file_time = os.path.getmtime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            file_time = stat.st_mtime
        return time.strftime("%y.%m.%d_%H:%M",time.gmtime(file_time)) 

    @staticmethod
    def print_args():
        from platform import python_version
        print_string = 'python[%s], ' % (str(python_version()))
        print_string += 'file[%s], ' % (sys.argv[0])
        print_string += 'version[%s], ' % (CGI_CLI.VERSION())
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_args = %s' % (json.dumps(CGI_CLI.data)) 
            except: pass                 
        else: print_string += 'CLI_args = %s' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string


class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled
                    
    def __init__(self, host = None, user = None, password = None, database = None):    
        if int(sys.version_info[0]) == 3 and not 'pymysql.connect' in sys.modules: import pymysql
        elif int(sys.version_info[0]) == 2 and not 'mysql.connector' in sys.modules: import mysql.connector
        default_ipxt_data_collector_delete_columns = ['id','last_updated']
        self.sql_connection = None
        try: 
            if CGI_CLI.initialized: pass
            else: CGI_CLI.init_cgi(); CGI_CLI.print_args()
        except: pass
        try:
            if int(sys.version_info[0]) == 3:
                ### PYMYSQL DISABLE AUTOCOMMIT BY DEFAULT !!!
                self.sql_connection = pymysql.connect( \
                    host = host, user = user, password = password, \
                    database = database, autocommit = True)
            else: 
                self.sql_connection = mysql.connector.connect( \
                    host = host, user = user, password = password,\
                    database = database, autocommit = True)
                       
            #CGI_CLI.uprint("SQL connection is open.")    
        except Exception as e: print(e)           
    
    def __del__(self):
        if self.sql_connection and self.sql_connection.is_connected():
            self.sql_connection.close()            
            #CGI_CLI.uprint("SQL connection is closed.")

    def sql_is_connected(self):
        if self.sql_connection: 
            if int(sys.version_info[0]) == 3 and self.sql_connection.open:
                return True
            elif int(sys.version_info[0]) == 2 and self.sql_connection.is_connected():
                return True
        return None
        
    def sql_read_all_table_columns(self, table_name):
        columns = None
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s';"%(table_name))
                records = cursor.fetchall()
                columns = [item[3] for item in records]
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return columns 

    def sql_read_sql_command(self, sql_command):
        '''NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE'''
        records = None
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute(sql_command)
                records = cursor.fetchall()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
            ### FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
        return records 

    def sql_write_sql_command(self, sql_command):
        if self.sql_is_connected(): 
            if int(sys.version_info[0]) == 3:
                cursor = self.sql_connection.cursor()
            elif int(sys.version_info[0]) == 2:        
                cursor = self.sql_connection.cursor(prepared=True)
            try: 
                cursor.execute(sql_command)
                ### DO NOT COMMIT IF AUTOCOMMIT IS SET 
                if not self.sql_connection.autocommit: self.sql_connection.commit()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return None

    def sql_write_table_from_dict(self, table_name, dict_data, update = None):  ###'ipxt_data_collector'
       if self.sql_is_connected():
           existing_sql_table_columns = self.sql_read_all_table_columns(table_name) 
           if existing_sql_table_columns:
               columns_string, values_string = str(), str()
               ### ASSUMPTION: LIST OF COLUMNS HAS CORRECT ORDER!!!
               for key in existing_sql_table_columns:
                   if key in list(dict_data.keys()):
                        if len(columns_string) > 0: columns_string += ','
                        if len(values_string) > 0: values_string += ','
                        ### WRITE KEY/COLUMNS_STRING
                        columns_string += '`' + key + '`'
                        ### BE AWARE OF DATA TYPE
                        if isinstance(dict_data.get(key,""), (list,tuple)):
                            item_string = str()
                            for item in dict_data.get(key,""):
                                ### LIST TO COMMA SEPARATED STRING
                                if isinstance(item, (six.string_types)):
                                    if len(item_string) > 0: item_string += ','
                                    item_string += item
                                ### DICTIONARY TO COMMA SEPARATED STRING    
                                elif isinstance(item, (dict,collections.OrderedDict)):
                                    for i in item:
                                        if len(item_string) > 0: item_string += ','
                                        item_string += item.get(i,"")
                            values_string += "'" + item_string + "'"
                        elif isinstance(dict_data.get(key,""), (six.string_types)):
                            values_string += "'" + str(dict_data.get(key,"")) + "'"
                        else:
                            values_string += "'" + str(dict_data.get(key,"")) + "'"
               ### FINALIZE SQL_STRING - INSERT
               if not update:
                   sql_string = """INSERT INTO `%s` (%s) VALUES (%s);""" \
                       % (table_name,columns_string,values_string)   
                   if columns_string:
                       self.sql_write_sql_command("""INSERT INTO `%s`
                           (%s) VALUES (%s);""" %(table_name,columns_string,values_string))
               else:
                   sql_string = """UPDATE `%s` (%s) VALUES (%s);""" \
                       % (table_name,columns_string,values_string)   
                   if columns_string:
                       self.sql_write_sql_command("""UPDATE `%s`
                           (%s) VALUES (%s);""" %(table_name,columns_string,values_string))                        
       return None                
   
    def sql_read_table_last_record(self, select_string = None, from_string = None, where_string = None):
        """NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE"""
        check_data = None
        if not select_string: select_string = '*'
        #SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id) FROM ipxt_data_collector \
        #WHERE username='mkrupa' AND device_name='AUVPE3'); 
        if self.sql_is_connected():
            if from_string:
                if where_string:
                    sql_string = "SELECT %s FROM %s WHERE id=(SELECT max(id) FROM %s WHERE %s);" \
                        %(select_string, from_string, from_string, where_string)
                else:
                    sql_string = "SELECT %s FROM %s WHERE id=(SELECT max(id) FROM %s);" \
                        %(select_string, from_string, from_string)
                check_data = self.sql_read_sql_command(sql_string)                          
        return check_data

    def sql_read_last_record_to_dict(table_name = None, from_string = None, \
        select_string = None, where_string = None, delete_columns = None):
        """sql_read_last_record_to_dict - MAKE DICTIONARY FROM LAST TABLE RECORD 
           NOTES: -'table_name' is alternative name to 'from_string'
                  - it always read last record dependent on 'where_string'
                    which contains(=filters by) username,device_name,vpn_name                  
        """
        dict_data = collections.OrderedDict()
        table_name_or_from_string = None
        if not select_string: select_string = '*'
        if table_name:  table_name_or_from_string = table_name
        if from_string: table_name_or_from_string = from_string     
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_last_record( \
            from_string = table_name_or_from_string, \
            select_string = select_string, where_string = where_string)
        if columns_list and data_list: 
            dict_data = collections.OrderedDict(zip(columns_list, data_list[0]))
        if delete_columns:
            for column in delete_columns:   
                try:
                    ### DELETE NOT VALID (AUXILIARY) TABLE COLUMNS
                    del dict_data[column]
                except: pass  
        return dict_data      

    def sql_read_table_records(self, select_string = None, from_string = None, where_string = None):
        """NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE"""
        check_data = None
        if not select_string: select_string = '*'
        #SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id) FROM ipxt_data_collector \
        #WHERE username='mkrupa' AND device_name='AUVPE3'); 
        if self.sql_is_connected():
            if from_string:
                if where_string:
                    sql_string = "SELECT %s FROM %s WHERE %s;" \
                        %(select_string, from_string, where_string)
                else:
                    sql_string = "SELECT %s FROM %s;" \
                        %(select_string, from_string )
                check_data = self.sql_read_sql_command(sql_string)                          
        return check_data

    def sql_read_records_to_dict_list(table_name = None, from_string = None, \
        select_string = None, where_string = None, delete_columns = None):
        """sql_read_last_record_to_dict - MAKE DICTIONARY FROM LAST TABLE RECORD 
           NOTES: -'table_name' is alternative name to 'from_string'
                  - it always read last record dependent on 'where_string'
                    which contains(=filters by) username,device_name,vpn_name                  
        """
        dict_data, dict_list = collections.OrderedDict(), []
        table_name_or_from_string = None
        if not select_string: select_string = '*'
        if table_name:  table_name_or_from_string = table_name
        if from_string: table_name_or_from_string = from_string     
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_records( \
            from_string = table_name_or_from_string, \
            select_string = select_string, where_string = where_string)
        if columns_list and data_list:
            for line_list in data_list:
                dict_data = collections.OrderedDict(zip(columns_list, line_list))
                dict_list.append(dict_data)
        if delete_columns:
            for column in delete_columns:   
                try:
                    ### DELETE NOT VALID (AUXILIARY) TABLE COLUMNS
                    del dict_data[column]
                except: pass     
        return dict_list


###############################################################################
pre_GW_vrf_definition_templ = """vrf definition LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 description Local vrf for tunnel ${cgi_data.get('vlan-id','UNKNOWN')} - ${cgi_data.get('vpn','UNKNOWN')}
<% 
big_rd = ''.join([ str(item.get('as_id','')) for item in private_as_test if item.get('cust_name','')==cgi_data.get('customer_name',"UNKNOWN") ])
rd3 = '0' 
if big_rd: rd4 = str(big_rd)
else: rd4 = '0'
if big_rd and int(big_rd) > 256: 
  rd3 = str(int(int(big_rd)/256)) 
  rd4 = str(int(big_rd)%256)
%>
  rd 0.0.${rd3}.${rd4}:${cgi_data.get('vlan-id','UNKNOWN')}
 !
"""

pre_GW_tunnel_interface_templ = """interface Tunnel${cgi_data.get('vlan-id','UNKNOWN')}
 description ${cgi_data.get('customer_name','UNKNOWN')} :IPXT @${cgi_data.get('bgp-peer-address','UNKNOWN')} - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 vrf forwarding LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 ip flow monitor ICX sampler ICX input
 ip address 193.251.244.167 255.255.255.254
 no ip redirects
 no ip proxy-arp
 ip mtu 1420
 logging event link-status
 tunnel source 193.251.245.106
 tunnel mode ipsec ipv4
 tunnel destination 78.110.224.70
 tunnel protection ipsec profile ${(cgi_data.get('customer_name','UNKNOWN')).upper()}-IPXT
! 
"""

pre_GW_interface_tovards_huawei_templ = """interface GigabitEthernet0/0/2
 description ${cgi_data.get('huawei-router','UNKNOWN')} from ${cgi_data.get('ipsec-gw-router','UNKNOWN')} @XXX.XXX.XXX.XXX - w/ IPSEC Customers FIB${cgi_data.get('ld-number','UNKNOWN')} - Backbone
!
interface GigabitEthernet0/0/2.${cgi_data.get('vlan-id','UNKNOWN')}
 description ${(cgi_data.get('customer_name','UNKNOWN'))} :IPXT @172.25.10.24 - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 encapsulation dot1Q ${cgi_data.get('vlan-id','UNKNOWN')}
 vrf forwarding LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 ip flow monitor ICX sampler ICX input
 ip address 172.25.10.25 255.255.255.254
 no ip redirects
 no ip proxy-arp
!
"""

pre_GW_router_bgp_templ = """router bgp 2300
 address-family ipv4 vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
  neighbor ${cgi_data.get('vpn','UNKNOWN')} peer-group
  neighbor ${cgi_data.get('vpn','UNKNOWN')} remote-as ${cgi_data.get('bgp-customer-as','UNKNOWN')}
  neighbor ${cgi_data.get('vpn','UNKNOWN')} ebgp-multihop 5
  neighbor ${cgi_data.get('vpn','UNKNOWN')} update-source Tunnel${cgi_data.get('vlan-id','UNKNOWN')}
  neighbor ${cgi_data.get('vpn','UNKNOWN')} send-community both
  neighbor ${cgi_data.get('vpn','UNKNOWN')} maximum-prefix 1000 90
  neighbor 172.25.10.24 remote-as 2300
  neighbor 172.25.10.24 activate
  neighbor 172.25.10.24 send-community both
  neighbor 193.251.244.166 peer-group ${cgi_data.get('vpn','UNKNOWN')}
  neighbor 193.251.244.166 activate
 exit-address-family
 !
"""
################################################################################
def generate_verification_GW_router_config(data = None):
    config_string = str()
    
    mytemplate = Template(pre_GW_vrf_definition_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'    

    mytemplate = Template(pre_GW_tunnel_interface_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n' 

    mytemplate = Template(pre_GW_interface_tovards_huawei_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n' 

    mytemplate = Template(pre_GW_router_bgp_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
        
    return config_string
###############################################################################


pre_PE_bundl_eether_interface_templ = """interface ${''.join([ str(item.get('int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}
 description TESTING ${cgi_data.get('ipsec-gw-router','UNKNOWN')} from ${cgi_data.get('pe-router','UNKNOWN')} :IPXT ASN${cgi_data.get('bgp-customer-as','UNKNOWN')} @XXX.XXX.XXX.XXX - For IPXT over IPSEC FIB${cgi_data.get('ld-number','UNKNOWN')} - Custom
 no ipv4 address
 carrier-delay up 3 down 0
 load-interval 30
!
"""

def generate_verification_PE_router_config(dict_data = None):
    config_string = str()

    mytemplate = Template(pre_PE_bundl_eether_interface_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
     
    return config_string 
    
###############################################################################



###############################################################################
### PREPARATION GW
###############################################################################

GW_preparation_interconnect_interface_templ = """interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
 encapsulation dot1Q ${cgi_data.get('vlan-id','UNKNOWN')}
 description TESTING ${cgi_data.get('customer_name','UNKNOWN')} @${cgi_data.get('pe-ip-address','UNKNOWN')} - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 vrf forwarding LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 ip address ${cgi_data.get('gw-ip-address','UNKNOWN')} 255.255.255.254
 no ip redirects
 no ip proxy-arp
!
"""

def generate_preparation_GW_router_config(data = None):
    config_string = str()     

    mytemplate = Template(GW_preparation_interconnect_interface_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'      
       
    return config_string
    
###############################################################################

    
    
###############################################################################
### MIGRATON GW
###############################################################################

GW_migration_shutdown_templ = """
router bgp 2300
address-family ipv4 vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
neighbor ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
neighbor ${''.join([ str(item.get('gw_peer_address_ibgp','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
!
interface ${''.join([ str(item.get('gw_subinterface','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
shutdown
!
"""

GW_migration_check_vrf_and_crypto_templ = """!
vrf definition LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 description Local vrf for tunnel ${cgi_data.get('vlan-id','UNKNOWN')} - ${cgi_data.get('vpn','UNKNOWN')}
<% 
big_rd = ''.join([ str(item.get('as_id','')) for item in private_as_test if item.get('cust_name','')==cgi_data.get('customer_name',"UNKNOWN") ])
rd3 = '0' 
if big_rd: rd4 = str(big_rd)
else: rd4 = '0'
if big_rd and int(big_rd) > 256: 
  rd3 = str(int(int(big_rd)/256)) 
  rd4 = str(int(big_rd)%256)
%>
 rd 0.0.${rd3}.${rd4}:${cgi_data.get('vlan-id','UNKNOWN')}
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
!
!
"""

GW_migration_tunnel_interface_templ = """interface Tunnel${cgi_data.get('vlan-id','UNKNOWN')}
 no shutdown
 description TESTING ${cgi_data.get('customer_name','UNKNOWN')} @${cgi_data.get('bgp-peer-address','UNKNOWN')} - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 vrf forwarding LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 ip address ${''.join([ str(item.get('ip_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} 255.255.255.254
 no ip redirects
 no ip proxy-arp
 ip mtu 1420
 logging event link-status
 load-interval 30
 carrier-delay msec 0
 tunnel source ${''.join([ str(item.get('loc_tun_addr','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}
 tunnel destination ${cgi_data.get('ipsec-tunnel-dest','UNKNOWN')}
 tunnel protection ipsec profile ${cgi_data.get('vpn','UNKNOWN')}
!
"""

GW_migration_port_channel_interface_templ = """interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}
 no shutdown
 description TESTING ${cgi_data.get('pe-router','UNKNOWN')} from ${cgi_data.get('ipsec-gw-router','UNKNOWN')} @${cgi_data.get('gw-ip-address','UNKNOWN')} - For IPXT over IPSEC FIB${cgi_data.get('ld-number','UNKNOWN')} - Custom
 mtu 4470
 no ip address
 no ip redirects
 no ip proxy-arp
 logging event link-status
 load-interval 30
 carrier-delay msec 0
!
"""

GW_migration_interconnect_interface_templ = """interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
 encapsulation dot1Q ${cgi_data.get('vlan-id','UNKNOWN')}
 description TESTING ${cgi_data.get('customer_name','UNKNOWN')} @${cgi_data.get('pe-ip-address','UNKNOWN')} - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 vrf forwarding LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
 ip address ${cgi_data.get('gw-ip-address','UNKNOWN')} 255.255.255.254
 no ip redirects
 no ip proxy-arp
!
"""
# GW_migration_customer_router_templ = """!<% list = cgi_data.get('ipv4-acl','').split(',') %>
# ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} 0.0.0.0 0.0.0.0 ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('pe-ip-address','UNKNOWN')} 
# ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} 255.255.255.255 Tunnel${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('bgp-peer-address','UNKNOWN')}
# % for i in range(int(len(list)/2)):
# <%
# input_mask = cgi_data.get('ipv4-acl','').split(',')[2*i+1]
# if input_mask: wildchard_mask = '255.255.255.255'
# elif input_mask == '': wildchard_mask = '255.255.255.255'
# elif '.' in input_mask:
  # wildchard_list = []
  # wildchard_mask = ''
  # for mask_part in input_mask.split('.'):    
    # try: wildchard_list.append(str(int(mask_part)^255))
    # except: wildchard_list.append('255')
  # for i_order in range(4):
    # try: wildchard_mask += wildchard_list[i_order]
    # except: wildchard_mask += '255'
    # if i_order<3: wildchard_mask += '.'  
# #wildchard_mask = '.'.join([ str(int(mask_item)^255) for mask_item in cgi_data.get('ipv4-acl','').split(',')[2*i+1].split('.') if '.' in cgi_data.get('ipv4-acl','').split(',')[2*i+1] and not "" in mask_item ])}
# %>
# ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('ipv4-acl','').split(',')[2*i]} ${wildchard_mask} Tunnel${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('bgp-peer-address','UNKNOWN')}
# % endfor
# !
# """


GW_migration_customer_router_templ = """!<% list = cgi_data.get('ipv4-acl','').split(',') %>
ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} 0.0.0.0 0.0.0.0 ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('pe-ip-address','UNKNOWN')} 
% for i in range(int(len(list)/2)):
<%
avoid_address = ''.join([ str(item.get('ip_address_customer','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])
input_mask = cgi_data.get('ipv4-acl','').split(',')[2*i+1]
if input_mask: wildchard_mask = '255.255.255.255'
elif input_mask == '': wildchard_mask = '255.255.255.255'
elif '.' in input_mask:
  wildchard_list = []
  wildchard_mask = ''
  for mask_part in input_mask.split('.'):    
    try: wildchard_list.append(str(int(mask_part)^255))
    except: wildchard_list.append('255')
  for i_order in range(4):
    try: wildchard_mask += wildchard_list[i_order]
    except: wildchard_mask += '255'
    if i_order<3: wildchard_mask += '.'  
#wildchard_mask = '.'.join([ str(int(mask_item)^255) for mask_item in cgi_data.get('ipv4-acl','').split(',')[2*i+1].split('.') if '.' in cgi_data.get('ipv4-acl','').split(',')[2*i+1] and not "" in mask_item ])}
%>
% if avoid_address and avoid_address != cgi_data.get('ipv4-acl','').split(',')[2*i]:
ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('ipv4-acl','').split(',')[2*i]} ${wildchard_mask} Tunnel${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('bgp-peer-address','UNKNOWN')}
% endif
% endfor
!
"""

GW_migration_unshut_if_templ = """!
interface ${''.join([ str(item.get('gw_subinterface','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
no shut
!
bgp 2300
ipv4-family vpn-instance ${''.join([ str(item.get('vrf_name','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
undo peer ${''.join([ str(item.get('ip_address_customer','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} ignore
!
"""

def generate_migration_GW_router_config(data = None):
    config_string = str()

    mytemplate = Template(GW_migration_shutdown_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n' 

    mytemplate = Template(GW_migration_check_vrf_and_crypto_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'  
    
    # mytemplate = Template(GW_migration_tunnel_interface_templ,strict_undefined=True)
    # config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n') + '\n'      

    # mytemplate = Template(GW_migration_port_channel_interface_templ,strict_undefined=True)
    # config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n') + '\n'      
    
    # mytemplate = Template(GW_migration_interconnect_interface_templ,strict_undefined=True)
    # config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n') + '\n'   

    mytemplate = Template(GW_migration_customer_router_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    # mytemplate = Template(GW_migration_unshut_if_templ,strict_undefined=True)
    # config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n') + '\n'
       
    return config_string

###############################################################################



###############################################################################
### PREPARATION PE
###############################################################################

PE_preparation_vrf_config_templ = """!
vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
 description ${cgi_data.get('vpn','UNKNOWN')}.${cgi_data.get('customer_name','UNKNOWN')}.IPXT
 address-family ipv4 unicast
 import route-target
% for item in ''.join([ str(item.get('rt_import','')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ]).split(','):
  ${item}
% endfor  
 exit
 export route-target
% for item in ''.join([ str(item.get('rt_export','')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ]).split(','): 
  ${item}
% endfor  
  exit
 exit
!
"""
 
PE_preparation_acl_config_templ = """!<% rule_num = 20; list = cgi_data.get('ipv4-acl','').split(',') %>
ipv4 access-list ${cgi_data.get('vpn','UNKNOWN')}-IN
 10 permit ipv4 ${cgi_data.get('pe-ip-address','')} 0.0.0.1 any
% for i in range(int(len(list)/2)):
 ${rule_num} permit ipv4 ${cgi_data.get('ipv4-acl','').split(',')[2*i]} ${cgi_data.get('ipv4-acl','').split(',')[2*i+1] if cgi_data.get('ipv4-acl','').split(',')[2*i+1] != '0' else '0.0.0.0'} any<% rule_num += 10 %>
% endfor
 1000 deny ipv4 any any
!
"""

PE_preparation_prefix_config_templ = """!
prefix-set ${cgi_data.get('vpn','UNKNOWN')}-IN
<%
import ipaddress 
splitted_list = cgi_data.get('ipv4-acl','').split(',') 
netlines = []
for i in range(int(len(splitted_list)/2)): 
    if splitted_list[2*i] == ''.join([ str(item.get('gw_peer_address_ibgp','')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ]):
        net = None
    else:
        try:    
            if splitted_list[2*i+1] == "0": net = splitted_list[2*i]+"/32" 
            else:
                try: net = ipaddress.ip_network(splitted_list[2*i]+'/'+splitted_list[2*i+1], strict=True)
                except: net = splitted_list[2*i] + '/32'
        except: net = splitted_list[2*i]+"/32"                
    if net: netlines.append(str(net) + ' le 32,')
try: netlines[-1] = netlines[-1].replace(',','')
except: pass
%>
% for item in netlines:
${item}
% endfor 
end-set
!
"""

PE_preparation_policy_map_templ = """!
policy-map IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
 class class-default
  service-policy IPXT.COS-IN
  police rate ${cgi_data.get('int-bw','UNKNOWN')} mbps 
end-policy-map
! 
policy-map IPXT.${cgi_data.get('customer_name','UNKNOWN')}-OUT
 class class-default
  service-policy IPXT.COS-OUT
  shape average ${cgi_data.get('int-bw','UNKNOWN')} mbps
 ! 
end-policy-map
! 
!
"""

PE_preparation_interface_description_templ = """interface ${''.join([ str(item.get('int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}
 description TESTING ${cgi_data.get('ipsec-gw-router','UNKNOWN')} from ${cgi_data.get('pe-router','UNKNOWN')} :IPXT ASN${cgi_data.get('bgp-customer-as','UNKNOWN')} @XXX.XXX.XXX.XXX - For IPXT over IPSEC FIB${cgi_data.get('ld-number','UNKNOWN')} - Custom
 no ipv4 address
 carrier-delay up 3 down 0
 load-interval 30
!
"""

PE_preparation_customer_interface_templ = """interface ${''.join([ str(item.get('int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
 encapsulation dot1Q ${cgi_data.get('vlan-id','UNKNOWN')}
 description TESTING ${cgi_data.get('customer_name','UNKNOWN')} :IPXT ASN${cgi_data.get('bgp-customer-as','UNKNOWN')} @${cgi_data.get('gw-ip-address','UNKNOWN')} - IPX ${cgi_data.get('ld-number','UNKNOWN')} TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('int-bw','UNKNOWN')}000
 vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')} 
 ipv4 address ${cgi_data.get('pe-ip-address','UNKNOWN')} 255.255.255.254
 flow ipv4 monitor ICX sampler ICX ingress
 ipv4 access-group ${cgi_data.get('vpn','UNKNOWN')}-IN ingress
 service-policy input ${cgi_data.get('vpn','UNKNOWN')}-IN
 service-policy output ${cgi_data.get('vpn','UNKNOWN')}-OUT
!
"""

PE_preparation_customer_policy_templ = """!
route-policy ${cgi_data.get('vpn','UNKNOWN')}-IN
  if not destination in ${cgi_data.get('vpn','UNKNOWN')}-IN then
   drop
  endif
  if community matches-any (2300:80) then
    set local-preference 80
    set community (${''.join([ str(item.get('bgp_community_1','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}) 
    set community (${''.join([ str(item.get('bgp_community_2','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}) additive
  elseif community matches-any (2300:90) then
    set local-preference 90
    set community (${''.join([ str(item.get('bgp_community_1','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])})
    set community (${''.join([ str(item.get('bgp_community_2','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}) additive
  else
    set local-preference 100
    set community (${''.join([ str(item.get('bgp_community_1','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])})
    set community (${''.join([ str(item.get('bgp_community_2','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}) additive
  endif
end-policy 
!
"""

PE_preparation_bgp_config_templ = """!
router bgp 2300<% try: is_number = int(cgi_data.get('bgp-hop-count',''))
except: is_number = None %>
 neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  remote-as ${cgi_data.get('bgp-customer-as','UNKNOWN')}
% if cgi_data.get('bgp-md5','') and cgi_data.get('bgp-md5','UNKNOWN') != 'dummy_value': 
  password clear ${cgi_data.get('bgp-md5','')}
% endif   
% if is_number and cgi_data.get('bgp-hop-count','') and cgi_data.get('bgp-hop-count','') != 'dummy_value': 
  ebgp-multihop ${cgi_data.get('bgp-hop-count','UNKNOWN')}
% endif  
  advertisement-interval 0
  address-family ipv4 unicast
   send-community-ebgp
   route-policy DENY-ALL in<% try: is_number = ''.join([ str(item.get('pref_limit','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])
except: is_number = None %>    
% if is_number and cgi_data.get('bgp-max-pref','') and cgi_data.get('bgp-max-pref','') != 'dummy_value': 
  maximum-prefix ${cgi_data.get('bgp-max-pref','')} 90
% endif    
   route-policy DENY-ALL out
   soft-reconfiguration inbound
  !
 vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')} 
<% 
big_rd = ''.join([ str(item.get('as_id','')) for item in private_as_test if item.get('cust_name','')==cgi_data.get('customer_name',"UNKNOWN") ])
rd3 = '0' 
if big_rd: rd4 = str(big_rd)
else: rd4 = '0'
if big_rd and int(big_rd) > 256: 
  rd3 = str(int(int(big_rd)/256)) 
  rd4 = str(int(big_rd)%256)
%>
  rd 0.0.${rd3}.${rd4}:${cgi_data.get('vlan-id','UNKNOWN')}
  address-family ipv4 unicast
   redistribute connected route-policy NO-EXPORT-INTERCO
  !
  neighbor ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
   use neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  !
 !
!
"""

PE_preparation_static_route_config_templ = """!
router static
 vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')} 
  address-family ipv4 unicast
  ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}/32 ${''.join([ str(item.get('int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('gw-ip-address','UNKNOWN')}
!
!
"""
   
def generate_preparation_PE_router_config(dict_data = None):
    config_string = str()

    mytemplate = Template(PE_preparation_vrf_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
    
    mytemplate = Template(PE_preparation_acl_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
    
    mytemplate = Template(PE_preparation_prefix_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    mytemplate = Template(PE_preparation_policy_map_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    mytemplate = Template(PE_preparation_customer_interface_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    mytemplate = Template(PE_preparation_customer_policy_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    mytemplate = Template(PE_preparation_bgp_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    mytemplate = Template(PE_preparation_static_route_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string 

###############################################################################



###############################################################################
### MIGRATION PE
###############################################################################   

# PE_migration_bgp_config_templ = """!
# router bgp 2300
 # neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  # remote-as ${cgi_data.get('bgp-customer-as','UNKNOWN')}
  # ebgp-multihop 5
  # advertisement-interval 0
  # address-family ipv4 unicast
   # send-community-ebgp
   # route-policy ${cgi_data.get('vpn','UNKNOWN')}-IN in
   # maximum-prefix 10 90
   # route-policy PASS-ALL out
   # soft-reconfiguration inbound
  # !
 # !
# !
# """

PE_migration_bgp_config_templ = """!
router bgp 2300
 neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  address-family ipv4 unicast
  route-policy ${cgi_data.get('vpn','UNKNOWN')}-IN in 
  route-policy PASS-ALL out
 !
!
"""

def generate_migration_PE_router_config(dict_data = None):
    config_string = str()

    mytemplate = Template(PE_migration_bgp_config_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string 

###############################################################################
    
    
###############################################################################
### MIGRATION OLD_PE
###############################################################################   

old_PE_migration_shut_if_templ = """!
interface ${''.join([ str(item.get('old_pe_interface','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
shutdown
!
bgp 2300
ipv4-family vpn-instance ${''.join([ str(item.get('vrf_name','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
peer ${''.join([ str(item.get('ip_address_customer','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} ignore
!
"""

def generate_migration_OLD_PE_router_shut_config(dict_data = None):
    config_string = str()

    mytemplate = Template(old_PE_migration_shut_if_templ,strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################




###############################################################################
### UNDO PREPARATION PE
###############################################################################
 
undo_preparation_PE_undo_templ = """!
no vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
!
no ipv4 access-list IPXT.${cgi_data.get('customer_name','UNKNOWN').replace('.','@')}-IN
!
no prefix-set IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
!
no policy-map IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
!
no policy-map IPXT.${cgi_data.get('customer_name','UNKNOWN')}-OUT
!
no interface ${''.join([ str(item.get('int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
!
no route-policy IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
!
router bgp 2300
no neighbor-group IPXT.${cgi_data.get('customer_name','UNKNOWN')}
no vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
!
router static
no vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
!
!
"""

def generate_undo_preparation_PE_config(dict_data = None):
    config_string = str()

    mytemplate = Template(undo_preparation_PE_undo_templ, strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################



###############################################################################
### UNDO PREPARATION GW
###############################################################################

undo_preparation_GW_undo_templ = """!
no interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
!
"""

def generate_undo_preparation_GW_config(dict_data = None):
    config_string = str()

    mytemplate = Template(undo_preparation_GW_undo_templ, strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################


###############################################################################
### UNDO MIGRATION PE
###############################################################################

undo_migration_PE_undo_templ = """!
router bgp 2300
neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
address-family ipv4 unicast
route-policy DENY-ALL in
route-policy DENY-ALL out
!
!
"""

def generate_undo_migration_PE_config(dict_data = None):
    config_string = str()

    mytemplate = Template(undo_migration_PE_undo_templ, strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################


###############################################################################
### UNDO MIGRATION GW
###############################################################################

# undo_migration_GW_undo_templ = """
# !
# router bgp 2300
# address-family ipv4 vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
# neighbor ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
# neighbor ${''.join([ str(item.get('gw_peer_address_ibgp','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
# !
# interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
# no shutdown
# !
# !
# !<% list = cgi_data.get('ipv4-acl','').split(',') %>
# ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} 0.0.0.0 0.0.0.0 ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('pe-ip-address','UNKNOWN')} 
# ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} 255.255.255.255 ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('pe-ip-address','UNKNOWN')} 
# % for i in range(int(len(list)/2)):
# <%
# input_mask = cgi_data.get('ipv4-acl','').split(',')[2*i+1]
# if input_mask: wildchard_mask = '255.255.255.255'
# elif input_mask == '': wildchard_mask = '255.255.255.255'
# elif '.' in input_mask:
  # wildchard_list = []
  # wildchard_mask = ''
  # for mask_part in input_mask.split('.'):    
    # try: wildchard_list.append(str(int(mask_part)^255))
    # except: wildchard_list.append('255')
  # for i_order in range(4):
    # try: wildchard_mask += wildchard_list[i_order]
    # except: wildchard_mask += '255'
    # if i_order<3: wildchard_mask += '.'  
# #wildchard_mask = '.'.join([ str(int(mask_item)^255) for mask_item in cgi_data.get('ipv4-acl','').split(',')[2*i+1].split('.') if '.' in cgi_data.get('ipv4-acl','').split(',')[2*i+1] and not "" in mask_item ])}
# %>
# no ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('ipv4-acl','').split(',')[2*i]} ${wildchard_mask} Tunnel${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('bgp-peer-address','UNKNOWN')}
# % endfor
# !
# """

undo_migration_GW_undo_templ = """
!
router bgp 2300
address-family ipv4 vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')}
neighbor ${''.join([ str(item.get('peer_address','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
neighbor ${''.join([ str(item.get('gw_peer_address_ibgp','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} shutdown
!
interface ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')}
no shutdown
!
!
!<% list = cgi_data.get('ipv4-acl','').split(',') %>
ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} 0.0.0.0 0.0.0.0 ${''.join([ str(item.get('ipsec_int_id','UNKNOWN')) for item in ipsec_ipxt_table if item.get('ipsec_rtr_name','UNKNOWN')==cgi_data.get('ipsec-gw-router',"UNKNOWN") ])}.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('pe-ip-address','UNKNOWN')} 
% for i in range(int(len(list)/2)):
<%
input_mask = cgi_data.get('ipv4-acl','').split(',')[2*i+1]
if input_mask: wildchard_mask = '255.255.255.255'
elif input_mask == '': wildchard_mask = '255.255.255.255'
elif '.' in input_mask:
  wildchard_list = []
  wildchard_mask = ''
  for mask_part in input_mask.split('.'):    
    try: wildchard_list.append(str(int(mask_part)^255))
    except: wildchard_list.append('255')
  for i_order in range(4):
    try: wildchard_mask += wildchard_list[i_order]
    except: wildchard_mask += '255'
    if i_order<3: wildchard_mask += '.'  
#wildchard_mask = '.'.join([ str(int(mask_item)^255) for mask_item in cgi_data.get('ipv4-acl','').split(',')[2*i+1].split('.') if '.' in cgi_data.get('ipv4-acl','').split(',')[2*i+1] and not "" in mask_item ])}
%>
no ip route vrf LOCAL.${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('ipv4-acl','').split(',')[2*i]} ${wildchard_mask} Tunnel${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('bgp-peer-address','UNKNOWN')}
% endfor
!
"""

def generate_undo_migration_GW_config(dict_data = None):
    config_string = str()

    mytemplate = Template(undo_migration_GW_undo_templ, strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################


###############################################################################
### UNDO MIGRATION GW
###############################################################################

undo_migration_OLD_PE_undo_templ = """!
interface ${''.join([ str(item.get('old_pe_interface','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
no shutdown
!
bgp 2300
ipv4-family vpn-instance ${''.join([ str(item.get('vrf_name','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])}
undo peer ${''.join([ str(item.get('ip_address_customer','UNKNOWN')) for item in ipxt_data_collector if item.get('session_id','UNKNOWN')==cgi_data.get('session_id',"UNKNOWN") ])} ignore
!
"""

def generate_undo_migration_OLD_PE_config(dict_data = None):
    config_string = str()

    mytemplate = Template(undo_migration_OLD_PE_undo_templ, strict_undefined=True)
    config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

    return config_string     
        
###############################################################################


def send_me_email(subject = str(), email_body = str(), file_name = None, attachments = None, \
        email_address = None, cc = None, bcc = None, username = None):
    def send_unix_email_body(mail_command):
        email_success = None
        try: 
            forget_it = subprocess.check_output(mail_command, shell=True)
            CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by COMMAND=[%s] with RESULT=[%s]...'\
                %(subject,sugested_email_address,mail_command,forget_it), color = 'blue')
            email_success = True    
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by COMMAND=[%s], PROBLEM=[%s]\n"\
                % (mail_command,str(e)) ,color = 'red')
        return email_success        
    ### FUCTION send_me_email START ----------------------------------------                    
    email_sent, sugested_email_address = None, str()
    if username: my_account = username        
    else: my_account = subprocess.check_output('whoami', shell=True).strip()    
    if email_address: sugested_email_address = email_address    
    if not 'WIN32' in sys.platform.upper():        
        try: 
            ldapsearch_output = subprocess.check_output('ldapsearch -LLL -x uid=%s mail' % (my_account), shell=True)
            ldap_email_address = ldapsearch_output.decode("utf-8").split('mail:')[1].splitlines()[0].strip()
        except: ldap_email_address = None        
        if ldap_email_address: sugested_email_address = ldap_email_address
        else:
            try: 
                my_getent_line = ' '.join((subprocess.check_output('getent passwd "%s"'% \
                    (my_account.strip()), shell=True)).split(':')[4].split()[:2])
                my_name = my_getent_line.splitlines()[0].split()[0]
                my_surname = my_getent_line.splitlines()[0].split()[1]
                sugested_email_address = '%s.%s@orange.com' % (my_name, my_surname)    
            except: pass        

        ### UNIX - MAILX ----------------------------------------------------
        mail_command = 'echo \'%s\' | mailx -s "%s" ' % (email_body,subject)
        if cc:
            if isinstance(cc, six.string_types): mail_command += '-c %s' % (cc)
            if cc and isinstance(cc, (list,tuple)): mail_command += ''.join([ '-c %s ' % (bcc_email) for bcc_email in bcc ])
        if bcc:
            if isinstance(bcc, six.string_types): mail_command += '-b %s' % (bcc)
            if bcc and isinstance(bcc, (list,tuple)): mail_command += ''.join([ '-b %s ' % (bcc_email) for bcc_email in bcc ])    
        if file_name and isinstance(file_name, six.string_types) and os.path.exists(file_name): 
            mail_command += '-a %s ' % (file_name)
        if attachments:
            if isinstance(attachments, (list,tuple)): 
                mail_command += ''.join([ '-a %s ' % (attach_file) for attach_file in attachments if os.path.exists(attach_file) ])      
            if isinstance(attachments, six.string_types) and os.path.exists(attachments):
                mail_command += '-a %s ' % (attachments)
        mail_command += '%s' % (sugested_email_address)            
        email_sent = send_unix_email_body(mail_command)

    if 'WIN32' in sys.platform.upper():
        ### NEEDED 'pip install pywin32'
        #if not 'win32com.client' in sys.modules: import win32com.client
        import win32com.client
        olMailItem, email_application = 0, 'Outlook.Application'
        try:
            ol = win32com.client.Dispatch(email_application)
            msg = ol.CreateItem(olMailItem)
            if email_address:
                msg.Subject, msg.Body = subject, email_body
                if email_address:
                    if isinstance(email_address, six.string_types): msg.To = email_address
                    if email_address and isinstance(email_address, (list,tuple)): 
                        msg.To = ';'.join([ eadress for eadress in email_address if eadress != "" ])                
                if cc:
                    if isinstance(cc, six.string_types): msg.CC = cc
                    if cc and isinstance(cc, (list,tuple)): 
                        msg.CC = ';'.join([ eadress for eadress in cc if eadress != "" ])
                if bcc:
                    if isinstance(bcc, six.string_types): msg.BCC = bcc
                    if bcc and isinstance(bcc, (list,tuple)): 
                        msg.BCC = ';'.join([ eadress for eadress in bcc if eadress != "" ])             
                if file_name and isinstance(file_name, six.string_types) and os.path.exists(file_name): 
                    msg.Attachments.Add(file_name)
                if attachments:
                    if isinstance(attachments, (list,tuple)): 
                        for attach_file in attachments:
                            if os.path.exists(attach_file): msg.Attachments.Add(attach_file)      
                    if isinstance(attachments, six.string_types) and os.path.exists(attachments):
                        msg.Attachments.Add(attachments)
               
            msg.Send()
            ol.Quit()
            CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by APPLICATION=[%s].'\
                %(subject,sugested_email_address,email_application), color = 'blue')
            email_sent = True    
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by APPLICATION=[%s], PROBLEM=[%s]\n"\
                % (email_application,str(e)) ,color = 'red')            
    return email_sent



##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)

configtext = str() 

### CGI-BIN READ FORM ############################################
CGI_CLI()
CGI_CLI.init_cgi()

if CGI_CLI.username: USERNAME = CGI_CLI.username 
if CGI_CLI.password: PASSWORD =  CGI_CLI.password

script_action = CGI_CLI.submit_form.replace(' ','_') if CGI_CLI.submit_form else 'unknown_action' 
device_name = CGI_CLI.data.get('device','')
huawei_device_name = CGI_CLI.data.get('huawei-router-name','')
vpn_name = CGI_CLI.data.get('vpn','')

### START OF DATA PROCESSING ###
config_data = collections.OrderedDict()
data = collections.OrderedDict()
cgi_data = copy.deepcopy(CGI_CLI.data)
data['cgi_data'] = cgi_data

### JUST OMMIT READING FROM LOGFILE BECAUSE OF WEB FORM POSSIBILITY OF DATA EDITING  
### bgp_data = copy.deepcopy(read_data_json_from_logfile(find_last_logfile()))
### data['bgp_data'] = bgp_data

sql_inst = sql_interface(host='localhost', user='cfgbuilder', password='cfgbuildergetdata', database='rtr_configuration')
data['private_as_test'] = sql_inst.sql_read_records_to_dict_list(from_string = 'private_as_test' , where_string = "cust_name = '%s'" % (cgi_data.get('customer_name','UNKNOWN')))
data['ipsec_ipxt_table'] = sql_inst.sql_read_records_to_dict_list(from_string = 'ipsec_ipxt_table', where_string = "ipsec_rtr_name = '%s'" % (cgi_data.get('ipsec-gw-router','UNKNOWN')))
data['ipxt_data_collector'] = sql_inst.sql_read_records_to_dict_list(from_string = 'ipxt_data_collector', where_string = "session_id = '%s'" % (cgi_data.get('session_id','UNKNOWN')))

### PRINT OF ALL DATA IN STRUCTURE DATA
CGI_CLI.uprint(get_json_with_variable_name(data))

    
if data:
    gw_verification_config_text = generate_verification_GW_router_config(data)
    pe_verification_config_text = generate_verification_PE_router_config(data)

    gw_preparation_config_text = generate_preparation_GW_router_config(data)
    pe_preparation_config_text = generate_preparation_PE_router_config(data)
    
    gw_migration_config_text = generate_migration_GW_router_config(data)
    pe_migration_config_text = generate_migration_PE_router_config(data)

    old_pe_migration_config_text_shut = generate_migration_OLD_PE_router_shut_config(data)

    
    undo_pe_preparation_config   = generate_undo_preparation_PE_config(data)
    undo_gw_preparation_config   = generate_undo_preparation_GW_config(data)   
    undo_pe_migration_config     = generate_undo_migration_PE_config(data)
    undo_gw_migration_config     = generate_undo_migration_GW_config(data)
    undo_old_pe_migration_config = generate_undo_migration_OLD_PE_config(data)
    
    CGI_CLI.uprint('\nGW ROUTER (%s) VERIFICATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(gw_verification_config_text)    
    CGI_CLI.uprint('\nPE ROUTER (%s) VERIFICATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(pe_verification_config_text)

    CGI_CLI.uprint('\nGW ROUTER (%s) PREPARATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(gw_preparation_config_text)    
    CGI_CLI.uprint('\nPE ROUTER (%s) PREPARATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(pe_preparation_config_text)

    CGI_CLI.uprint('\nGW ROUTER (%s) MIGRATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(gw_migration_config_text)    
    CGI_CLI.uprint('\nPE ROUTER (%s) MIGRATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(pe_migration_config_text)

    CGI_CLI.uprint('\nOLD PE ROUTER (%s) MIGRATION-CONFIG SHUT: \n' %(data['cgi_data'].get('huawei-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(old_pe_migration_config_text_shut)  

    CGI_CLI.uprint('\nPE ROUTER (%s) ROLLBACK-PREPARATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(undo_pe_preparation_config)
    CGI_CLI.uprint('\nGW ROUTER (%s) ROLLBACK-PREPARATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')    
    CGI_CLI.uprint(undo_gw_preparation_config)
    CGI_CLI.uprint('\nPE ROUTER (%s) ROLLBACK-MIGRATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')    
    CGI_CLI.uprint(undo_pe_migration_config)
    CGI_CLI.uprint('\nGW ROUTER (%s) ROLLBACK-MIGRATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')    
    CGI_CLI.uprint(undo_gw_migration_config)     
    CGI_CLI.uprint('\nOLD PE ROUTER (%s) ROLLBACK-MIGRATION-CONFIG SHUT: \n' %(data['cgi_data'].get('huawei-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(undo_old_pe_migration_config) 

     
    # describe ipxt_configurations;
    # +------------------------+--------------+------+-----+---------+----------------+
    # | Field                  | Type         | Null | Key | Default | Extra          |
    # +------------------------+--------------+------+-----+---------+----------------+
    # | id                     | int(11)      | NO   | PRI | NULL    | auto_increment |
    # | username               | varchar(20)  | NO   |     | NULL    |                |
    # | device_name            | varchar(15)  | NO   |     | NULL    |                |
    # | session_id             | varchar(255) | NO   |     | NULL    |                |
    # | pe_config_preparation  | text         | YES  |     | NULL    |                |
    # | pe_config_migration    | text         | YES  |     | NULL    |                |
    # | pe_config_verification | text         | YES  |     | NULL    |                |
    # | gw_config_preparation  | text         | YES  |     | NULL    |                |
    # | gw_config_migration    | text         | YES  |     | NULL    |                |
    # | gw_config_verification | text         | YES  |     | NULL    |                |
    # | pe_preparation_done    | varchar(10)  | NO   |     | NULL    |                |
    # | gw_preparation_done    | varchar(10)  | NO   |     | NULL    |                |
    # | pe_migration_done      | varchar(10)  | NO   |     | NULL    |                |
    # | gw_migration_done      | varchar(10)  | NO   |     | NULL    |                |
    # +------------------------+--------------+------+-----+---------+----------------+

 
    # | rollback_oldpe_migration     | text         | YES  |     | NULL    |                |
    # | rollback_gw_migration        | text         | YES  |     | NULL    |                |
    # | rollback_pe_migration        | text         | YES  |     | NULL    |                |
    # | rollback_gw_preparation      | text         | YES  |     | NULL    |                |
    # | rollback_pe_preparation      | text         | YES  |     | NULL    |                | 

    
    config_data['session_id'] = data['cgi_data'].get('session_id','UNKNOWN')
    config_data['username'] = CGI_CLI.username
    config_data['device_name'] = data['cgi_data'].get('huawei-router','UNKNOWN')
    
    config_data['gw_preparation_done'] = 'no'
    config_data['pe_preparation_done'] = 'no'
    config_data['gw_migration_done'] = 'no'
    config_data['pe_migration_done'] = 'no'    
    
    config_data['gw_config_verification'] = gw_verification_config_text
    config_data['pe_config_verification'] = pe_verification_config_text     
    
    config_data['gw_config_preparation'] = gw_preparation_config_text
    config_data['pe_config_preparation'] = pe_preparation_config_text          
    
    config_data['gw_config_migration'] = gw_migration_config_text
    config_data['pe_config_migration'] = pe_migration_config_text  
    
    config_data['old_pe_config_migration_shut'] = old_pe_migration_config_text_shut     

    config_data['rollback_pe_preparation'] = undo_pe_preparation_config 
    config_data['rollback_gw_preparation'] = undo_gw_preparation_config      
    config_data['rollback_pe_migration'] = undo_pe_migration_config    
    config_data['rollback_gw_migration'] = undo_gw_migration_config     
    config_data['rollback_oldpe_migration'] = undo_old_pe_migration_config 
    
    sql_inst.sql_write_table_from_dict('ipxt_configurations', config_data) 

    CGI_CLI.uprint('\nCONFIGS READ FROM SQL: \n', tag = 'h1')
    config_data_read_from_sql = sql_inst.sql_read_last_record_to_dict(from_string = 'ipxt_configurations')    
    CGI_CLI.uprint(config_data_read_from_sql, name = True, jsonprint = True, color = 'blue')
        
    ### MAKE LOGFILE STEP2 + SEND EMAIL    
    if CGI_CLI.cgi_active and data:
        logfilename = data['cgi_data'].get('session_id',None).replace('Submit_step_1','Submit_step_2').strip()
        cfgfilename = logfilename.replace('Submit_step_2-log','config')
        if logfilename:
            try: dummy = subprocess.check_output('rm -rf %s' % (logfilename), shell=True)
            except: pass
            with open(logfilename,"w") as fp:
                fp.write('DATA = ' + get_json_with_variable_name(data) + "\n\n\n")
                fp.write('\nGW ROUTER (%s) VERIFICATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper())+ 60*'-' + '\n\n')
                fp.write(gw_verification_config_text)    
                fp.write('\nPE ROUTER (%s) VERIFICATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper())+ 60*'-' + '\n\n')
                fp.write(pe_verification_config_text)
                fp.write('\n\n')
                configtext = 'IPSEC GW ROUTER (%s) PREPARATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()) + 60*'-' + '\n\n'
                configtext += gw_preparation_config_text
                configtext += '\n\nPE ROUTER (%s) PREPARATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()) + 60*'-' + '\n\n'
                configtext += pe_preparation_config_text 
                configtext += '\n\nIPSEC GW ROUTER (%s) MIGRATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()) + 60*'-' + '\n'
                configtext += gw_migration_config_text
                configtext += '\n\nPE ROUTER (%s) MIGRATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()) + 60*'-' + '\n'
                configtext += pe_migration_config_text
                configtext += '\n\nOLD PE ROUTER (%s) MIGRATION-CONFIG SHUT: \n' %(data['cgi_data'].get('huawei-router','UNKNOWN').upper()) + 60*'-' + '\n\n'
                configtext += old_pe_migration_config_text_shut
                configtext += '\n\nPE ROUTER (%s) ROLLBACK-PREPARATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()) + 60*'-' + '\n\n'
                configtext += undo_pe_preparation_config
                configtext += '\n\nGW ROUTER (%s) ROLLBACK-PREPARATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()) + 60*'-' + '\n\n'  
                configtext += undo_gw_preparation_config
                configtext += '\n\nPE ROUTER (%s) ROLLBACK-MIGRATION-CONFIG: \n' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()) + 60*'-' + '\n\n'    
                configtext += undo_pe_migration_config
                configtext += '\n\nGW ROUTER (%s) ROLLBACK-MIGRATION-CONFIG: \n' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()) + 60*'-' + '\n\n'   
                configtext += undo_gw_migration_config    
                configtext += '\n\nOLD PE ROUTER (%s) ROLLBACK-MIGRATION-CONFIG SHUT: \n' %(data['cgi_data'].get('huawei-router','UNKNOWN').upper()) + 60*'-' + '\n\n'
                configtext += undo_old_pe_migration_config                 
                fp.write(configtext)
            ### MAKE READABLE for THE OTHERS
            try: dummy = subprocess.check_output('chmod +r %s' % (logfilename), shell=True)
            except: pass
           
        if cfgfilename:
            try: dummy = subprocess.check_output('rm -rf %s' % (cfgfilename), shell=True)
            except: pass
            with open(cfgfilename,"w") as fp:
                fp.write(configtext)
            ### MAKE READABLE for THE OTHERS
            try: dummy = subprocess.check_output('chmod +r %s' % (cfgfilename), shell=True)
            except: pass
            
        if logfilename and cfgfilename and os.path.exists(logfilename) and os.path.exists(cfgfilename):           
            send_me_email(subject = cfgfilename.replace('\\','/').split('/')[-1], \
                attachments = [logfilename,cfgfilename], email_body = configtext, username = USERNAME)
            