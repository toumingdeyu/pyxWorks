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



class CGI_CLI(object):
    """
    class CGI_handle - Simple statis class for handling CGI parameters and
                       clean (debug) printing to HTML/CLI
    INTERFACE FUNCTIONS:
    CGI_CLI.init_cgi() - init CGI_CLI class
    CGI_CLI.print_args(), CGI_CLI.print_env() - debug printing
    CGI_CLI.uprint() - printing CLI/HTML text
    CGI_CLI.formprint() - printing of HTML forms
    """
    # import collections, cgi, six
    # import cgitb; cgitb.enable()

    ### TO BE PLACED - IN BODY ###
    JS_RELOAD_BUTTON = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""

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
                            help = "forced to insert router password interactively getpass.getpass()")
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "Target router to access. (Optionable device list separated ba comma, i.e. --device DEVICE1,DEVICE2)")
        parser.add_argument("--sw_release",
                            action = "store", dest = 'sw_release',
                            default = str(),
                            help = "sw release number with or without dots, i.e. 653 or 6.5.3, or alternatively sw release filename")
        parser.add_argument("--files",
                            action = "store", dest = 'sw_files',
                            default = str(),
                            help = "--files OTI.tar,SMU,pkg,bin")
        parser.add_argument("--check_only",
                            action = 'store_true', dest = "check_device_sw_files_only",
                            default = None,
                            help = "check existing device sw release files only, do not copy new tar files")
        parser.add_argument("--backup_configs",
                            action = 'store_true', dest = "backup_configs_to_device_disk",
                            default = None,
                            help = "backup configs to device hdd")
        parser.add_argument("--force",
                           action = 'store_true', dest = "force_rewrite_sw_files_on_device",
                           default = None,
                           help = "force rewrite sw release files on device disk")
        parser.add_argument("--delete",
                            action = 'store_true', dest = "delete_device_sw_files_on_end",
                            default = None,
                            help = "delete device sw release files on end after sw upgrade")
        parser.add_argument("--nobackupre",
                            action = 'store_true', dest = "ignore_missing_backup_re_on_junos",
                            default = None,
                            help = "ignore missing backup re on junos")
        # parser.add_argument("--sim",
                            # action = "store_true", dest = 'sim',
                            # default = None,
                            # help = "config simulation mode")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
        parser.add_argument("--timestamps",
                            action = "store_true", dest = 'timestamps',
                            default = None,
                            help = "print all lines with timestamps")
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():
        ### CGI_CLI.uprint('\nEND[script runtime = %d sec]. '%(time.time() - CGI_CLI.START_EPOCH))
        CGI_CLI.html_selflink('OK')
        if CGI_CLI.cgi_active: CGI_CLI.print_chunk("</body></html>")

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(chunked = None, css_style = None, newline = None, timestamp = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.http_status = 200
        CGI_CLI.http_status_text = 'OK'
        CGI_CLI.chunked = chunked
        CGI_CLI.timestamp = timestamp
        CGI_CLI.CSS_STYLE = css_style if css_style else str()
        ### TO BE PLACED - BEFORE HEADER ###
        CGI_CLI.newline = '\r\n' if not newline else newline
        CGI_CLI.chunked_transfer_encoding_line = \
            "Transfer-Encoding: chunked%s" % (CGI_CLI.newline) if CGI_CLI.chunked else str()
        ### HTTP/1.1 ???
        CGI_CLI.status_line = \
            "Status: %s %s%s" % (CGI_CLI.http_status, CGI_CLI.http_status_text, CGI_CLI.newline)
        CGI_CLI.content_type_line = 'Content-type:text/html; charset=utf-8%s' % (CGI_CLI.newline)
        CGI_CLI.cgi_active = None
        CGI_CLI.initialized = True
        getpass_done = None
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), str(), str(), str()
        form, CGI_CLI.data = collections.OrderedDict(), collections.OrderedDict()
        CGI_CLI.logfilename = None
        try: form = cgi.FieldStorage()
        except: pass
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["submit","username","password"]:
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
        ### DECIDE - CLI OR CGI MODE ##########################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent:
            CGI_CLI.cgi_active = True
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active: CGI_CLI.data = vars(CGI_CLI.args)
        if CGI_CLI.cgi_active:
            sys.stdout.write("%s%s%s" %
                (CGI_CLI.chunked_transfer_encoding_line,
                CGI_CLI.content_type_line,
                CGI_CLI.status_line))
            sys.stdout.flush()
            ### CHROME NEEDS 2NEWLINES TO BE ALREADY CHUNKED !!! ##############
            CGI_CLI.print_chunk("%s%s<!DOCTYPE html><html><head><title>%s</title>%s</head><body>" %
                (CGI_CLI.newline, CGI_CLI.newline,
                CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit', \
                '<style>%s</style>' % (CGI_CLI.CSS_STYLE) if CGI_CLI.CSS_STYLE else str()))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM ENVIRONMENT BY DEFAULT ###
        try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
        except: CGI_CLI.PASSWORD        = str()
        try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
        except: CGI_CLI.USERNAME        = str()
        ### GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI ###
        if CGI_CLI.args.password: CGI_CLI.password = CGI_CLI.args.password
        if CGI_CLI.args.username:
            CGI_CLI.USERNAME = CGI_CLI.args.username
            if not CGI_CLI.args.password:
                CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
                getpass_done = True
        ### FORCE GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI GETPASS ###
        if CGI_CLI.args.getpass and not getpass_done:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
        ### GAIN/OVERWRITE USERNAME AND PASSWORD FROM CGI ###
        if CGI_CLI.username: CGI_CLI.USERNAME = CGI_CLI.username
        if CGI_CLI.password: CGI_CLI.PASSWORD = CGI_CLI.password
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): CGI_CLI.bcolors = CGI_CLI.nocolors
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
                            except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']', color = 'magenta')

    @staticmethod
    def set_logfile(logfilename = None):
        """
        set_logfile()            - uses LCMD.logfilename or RCMD.logfilename,
        set_logfile(logfilename) - uses inserted logfilename
        """
        actual_logfilename, CGI_CLI.logfilename = None, None
        try:
            if not (LCMD.logfilenam == 'nul' or LCMD.logfilename == '/dev/null'):
                actual_logfilename = LCMD.logfilename
        except: pass
        try:
            if not (RCMD.logfilenam == 'nul' or RCMD.logfilename == '/dev/null'):
               actual_logfilename = RCMD.logfilename
        except: pass
        if logfilename: actual_logfilename = logfilename
        if actual_logfilename == 'nul' or actual_logfilename == '/dev/null' \
            or not actual_logfilename: pass
        else: CGI_CLI.logfilename = actual_logfilename

    @staticmethod
    def print_chunk(msg=""):
        ### sys.stdout.write is printing without \n , print adds \n == +1BYTE ###
        if CGI_CLI.chunked and CGI_CLI.cgi_active:
            if len(msg)>0:
                sys.stdout.write("\r\n%X\r\n%s" % (len(msg), msg))
                sys.stdout.flush()
        ### CLI MODE ###
        else: print(msg)

    @staticmethod
    def uprint(text = str(), tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        log = None, no_newlines = None, start_tag = None, end_tag = None, raw = None, timestamp = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
           timestamp = True - locally allow (CGI_CLI.timestamp = True has priority)
           timestamp = 'no' - locally disable even if CGI_CLI.timestamp == True
        """
        print_text, print_name, print_per_tag = copy.deepcopy(text), str(), str()
        if jsonprint:
            if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = json.dumps(text, indent = 4)
                except Exception as e: CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']')
        if name == True:
            if not 'inspect.currentframe' in sys.modules: import inspect
            callers_local_vars = inspect.currentframe().f_back.f_locals.items()
            var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
            if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
        elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '

        print_text = str(print_text)
        log_text   = str(copy.deepcopy((print_text)))

        ### GENERATE TIMESTAMP STRING , 'NO' = NO EVERYTIME EVEN IF GLOBALLY IS ALLOWED ###
        timestamp_string = str()
        if timestamp or CGI_CLI.timestamp:
            timestamp_yes = True
            try:
                if str(timestamp).upper() == 'NO': timestamp_yes = False
            except: pass
            if timestamp_yes:
                timestamp_string = '@%s[%.2fs] ' % \
                    (datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'), time.time() - CGI_CLI.START_EPOCH)

        if CGI_CLI.cgi_active and not raw:
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT
            if color and not (tag or start_tag): tag = 'p';
            if tag: CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            elif start_tag: CGI_CLI.print_chunk('<%s%s%s>'%(start_tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                    replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
            CGI_CLI.print_chunk(timestamp_string + print_name + print_text)
        elif CGI_CLI.cgi_active and raw:
            CGI_CLI.print_chunk(print_text)
        else:
            text_color = str()
            if color:
                if 'RED' in color.upper():       text_color = CGI_CLI.bcolors.RED
                elif 'MAGENTA' in color.upper(): text_color = CGI_CLI.bcolors.MAGENTA
                elif 'GREEN' in color.upper():   text_color = CGI_CLI.bcolors.GREEN
                elif 'BLUE' in color.upper():    text_color = CGI_CLI.bcolors.BLUE
                elif 'CYAN' in color.upper():    text_color = CGI_CLI.bcolors.CYAN
                elif 'GREY' in color.upper():    text_color = CGI_CLI.bcolors.GREY
                elif 'GRAY' in color.upper():    text_color = CGI_CLI.bcolors.GREY
                elif 'YELLOW' in color.upper():  text_color = CGI_CLI.bcolors.YELLOW
            ### CLI_MODE ###
            if no_newlines:
                sys.stdout.write(text_color + print_name + print_text + CGI_CLI.bcolors.ENDC)
                sys.stdout.flush()
            else:
                print(text_color + print_name + timestamp_string + print_text + CGI_CLI.bcolors.ENDC)
        del print_text
        if CGI_CLI.cgi_active and not raw:
            if tag:
                CGI_CLI.print_chunk('</%s>' % (tag))
                ### USER DEFINED TAGS DOES NOT PROVIDE NEWLINES!!! ############
                if tag in ['debug','warning']: CGI_CLI.print_chunk('<br/>');
            elif end_tag: CGI_CLI.print_chunk('</%s>' % (end_tag))
            elif not no_newlines: CGI_CLI.print_chunk('<br/>')
            ### PRINT PER TAG ###
            CGI_CLI.print_chunk(print_per_tag)
        ### LOGGING ###
        if CGI_CLI.logfilename and log:
            with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                CGI_CLI.fp.write(print_name + log_text + '\n')
                del log_text


    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, \
        color = None, list_separator = None):
        """ formprint() - print simple HTML form
            form_data - string, just html raw OR list or dict values = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
                      - value in dictionary means cgi variable name / printed componenet value
        """
        def subformprint(data_item):
            if isinstance(data_item, six.string_types):  CGI_CLI.print_chunk(data_item)
            elif isinstance(data_item, (dict,collections.OrderedDict)):
                if data_item.get('raw',None): CGI_CLI.print_chunk(data_item.get('raw'))
                elif data_item.get('textcontent',None):
                    CGI_CLI.print_chunk('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4">%s</textarea>'%\
                        (data_item.get('textcontent'), data_item.get('text','')))
                elif data_item.get('text'):
                    CGI_CLI.print_chunk('%s: <input type = "text" name = "%s"><br />'%\
                        (data_item.get('text','').replace('_',' '),data_item.get('text')))
                elif data_item.get('password'):
                    CGI_CLI.print_chunk('%s: <input type = "password" name = "%s"><br />'%\
                        (data_item.get('password','').replace('_',' '),data_item.get('password')))
                elif data_item.get('radio'):
                    ### 'RADIO':'NAME__VALUE' ###
                    if isinstance(data_item.get('radio'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            try:
                                value = radiobutton.split('__')[1]
                                name = radiobutton.split('__')[0]
                            except: value, name = radiobutton, 'radio'
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s %s'%\
                                (name,value,value.replace('_',' '), \
                                list_separator if list_separator else str()))
                    else:
                        try:
                            value = data_item.get('radio').split('__')[1]
                            name = data_item.get('radio').split('__')[0]
                        except: value, name = data_item.get('radio'), 'radio'
                        CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                            (name,value,value.replace('_',' ')))
                elif data_item.get('checkbox'):
                    CGI_CLI.print_chunk('<input type = "checkbox" name = "%s" value = "on" /> %s'%\
                        (data_item.get('checkbox'),data_item.get('checkbox','').replace('_',' ')))
                elif data_item.get('dropdown'):
                    if len(data_item.get('dropdown').split(','))>0:
                        CGI_CLI.print_chunk('<select name = "dropdown[%s]">'%(data_item.get('dropdown')))
                        for option in data_item.get('dropdown').split(','):
                            CGI_CLI.print_chunk('<option value = "%s">%s</option>'%(option,option))
                        CGI_CLI.print_chunk('</select>')
                elif data_item.get('file'):
                   CGI_CLI.print_chunk('Upload file: <input type = "file" name = "file[%s]" />'%(data_item.get('file').replace('\\','/')))
                elif data_item.get('submit'):
                    CGI_CLI.print_chunk('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%\
                        (data_item.get('submit'),data_item.get('submit')))

        ### START OF FORMPRINT ###
        formtypes = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
        i_submit_button = None if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            CGI_CLI.print_chunk('<br/>');
            if tag and 'h' in tag: CGI_CLI.print_chunk('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
            if color or tag and 'p' in tag: tag = 'p'; CGI_CLI.print_chunk('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
            CGI_CLI.print_chunk('<form action = "/cgi-bin/%s" enctype = "multipart/form-data" action = "save_file.py" method = "post">'%\
                (i_pyfile))
            ### RAW HTML ###
            if isinstance(form_data, six.string_types): CGI_CLI.print_chunk(form_data)
            ### STRUCT FORM DATA = LIST ###
            elif isinstance(form_data, (list,tuple)):
                for data_item in form_data: subformprint(data_item)
            ### JUST ONE DICT ###
            elif isinstance(form_data, (dict,collections.OrderedDict)): subformprint(form_data)
            if i_submit_button: subformprint({'submit':i_submit_button})
            CGI_CLI.print_chunk('</form>')
            if tag and 'p' in tag: CGI_CLI.print_chunk('</p>')
            if tag and 'h' in tag: CGI_CLI.print_chunk('</%s>'%(tag))


    @staticmethod
    def html_selflink(submit_button = None):
        if (submit_button and str(submit_button) == str(CGI_CLI.submit_form)) or not CGI_CLI.submit_form:
            i_pyfile = sys.argv[0]
            try: pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
            except: pyfile = i_pyfile.strip()
            if CGI_CLI.cgi_active:
                CGI_CLI.print_chunk('<p id="scriptend"></p>')
                CGI_CLI.print_chunk('<br/><a href = "./%s">PAGE RELOAD</a>' % (pyfile))

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
        print_string += 'version[%s], ' % (CGI_CLI.VERSION())
        print_string += 'file[%s]\n' % (sys.argv[0])
        print_string += 'CGI_CLI.USERNAME[%s], CGI_CLI.PASSWORD[%s]\n' % \
            (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No')
        print_string += 'remote_addr[%s], ' % dict(os.environ).get('REMOTE_ADDR','')
        print_string += 'browser[%s]\n' % dict(os.environ).get('HTTP_USER_AGENT','')
        print_string += 'CGI_CLI.cgi_active[%s], CGI_CLI.submit_form[%s], CGI_CLI.chunked[%s]\n' % \
            (str(CGI_CLI.cgi_active), str(CGI_CLI.submit_form), str(CGI_CLI.chunked))
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_CLI.data[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4)))
            except: pass
        else: print_string += 'CLI_args = %s\nCGI_CLI.data = %s' % (str(sys.argv[1:]), str(json.dumps(CGI_CLI.data,indent = 4)))
        CGI_CLI.uprint(print_string, tag = 'debug')
        return print_string

    @staticmethod
    def print_env():
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', tag = 'debug', jsonprint = True)


##############################################################################


class RCMD(object):

    @staticmethod
    def connect(device = None, cmd_data = None, username = None, password = None, \
        use_module = 'paramiko', logfilename = None, \
        connection_timeout = 600, cmd_timeout = 30, \
        conf = None, sim_config = None, disconnect = None, printall = None, \
        do_not_final_print = None, commit_text = None, silent_mode = None, \
        disconnect_timeout = 2):
        """ FUNCTION: RCMD.connect(), RETURNS: list of command_outputs
        PARAMETERS:
        device     - string , device_name/ip_address/device_name:PORT_NUMBER/ip_address:PORT_NUMBER
        cmd_data  - dict, {'cisco_ios':[..], 'cisco_xr':[..], 'juniper':[..], 'huawei':[], 'linux':[..]}
        username   - string, remote username
        password   - string, remote password
        use_module - string, paramiko/netmiko
        disconnect - True/False, immediate disconnect after RCMD.connect and processing of cmd_data
        logfilename - strng, name of logging file
        conf        - True/False, go to config mode
        NOTES:
        1. cmd_data is DEVICE TYPE INDEPENDENT and will be processed after device detection
        2. only 1 instance of static class RCMD could exists
        """
        import atexit; atexit.register(RCMD.__cleanup__)
        command_outputs = str()
        RCMD.ssh_connection = None
        RCMD.CMD = []
        if device:
            RCMD.silent_mode = silent_mode
            RCMD.DISCONNECT_TIMEOUT = disconnect_timeout
            RCMD.CMD = []
            RCMD.output, RCMD.fp = None, None
            RCMD.device = device
            RCMD.ssh_connection = None
            RCMD.CONNECTION_TIMEOUT = int(connection_timeout)
            RCMD.CMD_TIMEOUT = int(cmd_timeout)
            RCMD.use_module = use_module
            RCMD.logfilename = logfilename
            RCMD.USERNAME = username
            RCMD.PASSWORD = password
            RCMD.router_prompt = None
            RCMD.printall = printall
            RCMD.router_type = None
            RCMD.router_version = None
            RCMD.conf = conf
            RCMD.sim_config = sim_config
            RCMD.huawei_version = 0
            RCMD.config_problem = None
            RCMD.commit_text = commit_text
            RCMD.do_not_final_print = do_not_final_print
            RCMD.drive_string = str()
            RCMD.KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']
            try: RCMD.DEVICE_HOST = device.split(':')[0]
            except: RCMD.DEVICE_HOST = str()
            try: RCMD.DEVICE_PORT = device.split(':')[1]
            except: RCMD.DEVICE_PORT = '22'
            if printall: CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.', color = 'gray')
            try:
                ### ONE_CONNECT DETECTION #####################################
                RCMD.client = paramiko.SSHClient()
                RCMD.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                RCMD.client.connect(RCMD.DEVICE_HOST, port=int(RCMD.DEVICE_PORT), \
                    username=RCMD.USERNAME, password=RCMD.PASSWORD, \
                    banner_timeout = 10, \
                    ### AUTH_TIMEOUT MAKES PROBLEMS ON IPTAC1 ###
                    #auth_timeout = 10, \
                    timeout = RCMD.CONNECTION_TIMEOUT, \
                    look_for_keys = False)
                RCMD.ssh_connection = RCMD.client.invoke_shell()
                if RCMD.ssh_connection:
                    RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
                    if not RCMD.router_type: CGI_CLI.uprint('DEVICE_TYPE NOT DETECTED!', color = 'red')
                    elif RCMD.router_type in RCMD.KNOWN_OS_TYPES and printall:
                        CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type), \
                            color = 'gray')
            except Exception as e:
                if not RCMD.silent_mode:
                    CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
            finally:
                if disconnect: RCMD.disconnect()
            ### EXIT IF NO CONNECTION ##########################################
            if not RCMD.ssh_connection: return command_outputs
            ####################################################################
            if RCMD.router_type == 'cisco_ios':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('cisco_ios',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '%s%s#'%(RCMD.device.upper(),''), \
                    '%s%s#'%(RCMD.device.upper(),'(config)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-if)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-line)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-router)')  ]
                RCMD.TERM_LEN_0 = "terminal length 0"
                RCMD.EXIT = "exit"
                RCMD.drive_string = 'bootflash:'
            elif RCMD.router_type == 'cisco_xr':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('cisco_xr',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '%s%s#'%(RCMD.device.upper(),''), \
                    '%s%s#'%(RCMD.device.upper(),'(config)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-if)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-line)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-router)'), \
                    'sysadmin#' ]
                RCMD.TERM_LEN_0 = "terminal length 0"
                RCMD.EXIT = "exit"
                RCMD.drive_string = 'harddisk:'
            elif RCMD.router_type == 'juniper':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('juniper',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                     USERNAME + '@' + RCMD.device.upper() + '> ', # !! Need the space after >
                     USERNAME + '@' + RCMD.device.upper() + '# ' ]
                RCMD.TERM_LEN_0 = "set cli screen-length 0"
                RCMD.EXIT = "exit"
                ### MOST PROBABLE IS THAT RE0 IS ALONE OR MASTER ##############
                RCMD.drive_string = 're0:'
            elif RCMD.router_type == 'huawei':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('huawei',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '<' + RCMD.device.upper() + '>',
                    '[' + RCMD.device.upper() + ']',
                    '[~' + RCMD.device.upper() + ']',
                    '[*' + RCMD.device.upper() + ']' ]
                RCMD.TERM_LEN_0 = "screen-length 0 temporary"     #"screen-length disable"
                RCMD.EXIT = "quit"
                RCMD.drive_string = 'cfcard:'
            elif RCMD.router_type == 'linux':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('linux',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ ]
                RCMD.TERM_LEN_0 = ''     #"screen-length disable"
                RCMD.EXIT = "exit"
            else: RCMD.CMD = []
            # ADD PROMPT TO PROMPTS LIST
            if RCMD.router_prompt: RCMD.DEVICE_PROMPTS.append(RCMD.router_prompt)
            ### START SSH CONNECTION AGAIN ####################################
            try:
                if RCMD.router_type and RCMD.use_module == 'netmiko':
                    ### PARAMIKO IS ALREADY CONNECTED, SO DISCONNECT FIRST ####
                    RCMD.disconnect()
                    RCMD.ssh_connection = netmiko.ConnectHandler(device_type = RCMD.router_type, \
                        ip = RCMD.DEVICE_HOST, port = int(RCMD.DEVICE_PORT), \
                        username = RCMD.USERNAME, password = RCMD.PASSWORD)
                elif RCMD.router_type and RCMD.use_module == 'paramiko':
                    ### PARAMIKO IS ALREADY CONNECTED #########################
                    RCMD.output, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,RCMD.TERM_LEN_0)
                    RCMD.output2, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,"")
                    RCMD.output += RCMD.output2
                ### WORK REMOTE  ==============================================
                command_outputs = RCMD.run_commands(RCMD.CMD)
                ### ===========================================================
            except Exception as e:
                if not RCMD.silent_mode:
                    CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
            finally:
                if disconnect: RCMD.disconnect()
        else: CGI_CLI.uprint('DEVICE NOT INSERTED!', color = 'magenta')
        return command_outputs

    @staticmethod
    def run_command(cmd_line = None, printall = None, conf = None, \
        long_lasting_mode = None, autoconfirm_mode = None, \
        sim_config = None, sim_all = None, ignore_prompt = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        sim_all  - simulate execution of all commands, not only config commands
                   used for ommit save/write in normal mode
        sim_config - simulate config commands
        long_lasting_mode - max connection timeout, no cmd timeout, no prompt discovery
        autoconfirm_mode - in case of interactivity send 'Y\n' on huawei ,'\n' on cisco
        """
        last_output, sim_mark = str(), str()
        if RCMD.ssh_connection and cmd_line:
            if ((sim_config or RCMD.sim_config) and (conf or RCMD.conf)) or sim_all: sim_mark = '(SIM)'
            if printall or RCMD.printall:
                CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line, color = 'blue')
            if not sim_mark:
                if RCMD.use_module == 'netmiko':
                    last_output = RCMD.ssh_connection.send_command(cmd_line)
                elif RCMD.use_module == 'paramiko':
                    last_output, new_prompt = RCMD.ssh_send_command_and_read_output( \
                        RCMD.ssh_connection, RCMD.DEVICE_PROMPTS, cmd_line, \
                        long_lasting_mode = long_lasting_mode, \
                        autoconfirm_mode = autoconfirm_mode, \
                        ignore_prompt = ignore_prompt, \
                        printall = printall)
                    if new_prompt: RCMD.DEVICE_PROMPTS.append(new_prompt)
            if printall or RCMD.printall:
                if not long_lasting_mode: CGI_CLI.uprint(last_output, color = 'gray', timestamp = 'no')
            elif not RCMD.silent_mode:
                if not long_lasting_mode: CGI_CLI.uprint(' . ', no_newlines = True)
            if RCMD.fp: RCMD.fp.write('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line + '\n' + last_output + '\n')
        return last_output

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None, \
        do_not_final_print = None , commit_text = None, submit_result = None , \
        long_lasting_mode = None, autoconfirm_mode = None, ignore_prompt = None):
        """
        FUNCTION: run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        conf     - True/False, go to config mode
        sim_config - simulate config commands
        long_lasting_mode - max connection timeout, no cmd timeout, no prompt discovery
        autoconfirm_mode - in case of interactivity send 'Y\n' on huawei ,'\n' on cisco
        """
        command_outputs = str()
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if RCMD.router_type=='cisco_ios': cmd_list = cmd_data.get('cisco_ios',[])
            elif RCMD.router_type=='cisco_xr': cmd_list = cmd_data.get('cisco_xr',[])
            elif RCMD.router_type=='juniper': cmd_list = cmd_data.get('juniper',[])
            elif RCMD.router_type=='huawei': cmd_list = cmd_data.get('huawei',[])
            elif RCMD.router_type=='linux': cmd_list = cmd_data.get('linux',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []

        if RCMD.ssh_connection and len(cmd_list)>0:
            ### WORK REMOTE ================================================
            if not RCMD.logfilename:
                if 'WIN32' in sys.platform.upper(): RCMD.logfilename = 'nul'
                else: RCMD.logfilename = '/dev/null'
            with open(RCMD.logfilename,"a+") as RCMD.fp:
                if RCMD.output: RCMD.fp.write(RCMD.output)
                command_outputs, sim_mark = [], str()
                ### CONFIG MODE FOR NETMIKO ####################################
                if (conf or RCMD.conf) and RCMD.use_module == 'netmiko':
                    if (sim_config or RCMD.sim_config): sim_mark, last_output = '(SIM)', str()
                    else:
                        ### PROCESS COMMANDS - PER COMMAND LIST! ###############
                        last_output = RCMD.ssh_connection.send_config_set(cmd_list)
                        if printall or RCMD.printall:
                            CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + str(cmd_list), color = 'blue')
                            CGI_CLI.uprint(str(last_output), color = 'gray', timestamp = 'no')
                        if RCMD.fp: RCMD.fp.write('REMOTE_COMMANDS' + sim_mark + ': ' \
                            + str(cmd_list) + '\n' + str(last_output) + '\n')
                        command_outputs = [last_output]
                elif RCMD.use_module == 'paramiko':
                    ### CONFIG MODE FOR PARAMIKO ###############################
                    conf_output = ''
                    if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':
                        if RCMD.router_type=='cisco_ios': conf_output = RCMD.run_command('config t', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='cisco_xr': conf_output = RCMD.run_command('config t', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='juniper': conf_output = RCMD.run_command('configure exclusive', \
                            conf = conf, sim_config = sim_config , printall = printall)
                        elif RCMD.router_type=='huawei':
                            version_output = RCMD.run_command('display version | include software', \
                                conf = False, sim_config = sim_config, printall = printall)
                            try: RCMD.huawei_version = float(version_output.split('VRP (R) software, Version')[1].split()[0].strip())
                            except: RCMD.huawei_version = 0
                            conf_output = RCMD.run_command('system-view', \
                                conf = conf, sim_config = sim_config, printall = printall)
                    if conf_output: command_outputs.append(conf_output)
                    ### PROCESS COMMANDS - PER COMMAND #########################
                    for cmd_line in cmd_list:
                        command_outputs.append(RCMD.run_command(cmd_line, \
                            conf = conf, sim_config = sim_config, printall = printall,
                            long_lasting_mode = long_lasting_mode, \
                            ignore_prompt = ignore_prompt, \
                            autoconfirm_mode = autoconfirm_mode))
                    ### EXIT FROM CONFIG MODE FOR PARAMIKO #####################
                    if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':
                        ### GO TO CONFIG TOP LEVEL SECTION ---------------------
                        ### CISCO_IOS/XE has end command exiting from config ###
                        if RCMD.router_type=='cisco_xr':
                            for repeat_times in range(10):
                                if '(config-' in ''.join(command_outputs[-1]):
                                    command_outputs.append(RCMD.run_command('exit', \
                                        conf = conf, sim_config = sim_config, printall = printall))
                                else: break
                        ### JUNOS - HAS (HOPEFULLY) NO CONFIG LEVELS ###
                        elif RCMD.router_type=='huawei':
                            for repeat_times in range(10):
                                ### NEW HUAWEI has [~ or [* in config mode ###
                                if re.search(r'\[[0-9a-zA-Z\~\*]+\-[0-9a-zA-Z\-\.\@\_]+\]', ''.join(command_outputs[-1:])):
                                    command_outputs.append(RCMD.run_command('quit', \
                                        conf = conf, sim_config = sim_config, printall = printall))
                                else: break
                        ### COMMIT SECTION -------------------------------------
                        commit_output = ""
                        if RCMD.router_type=='cisco_ios': pass
                        elif RCMD.router_type=='cisco_xr':
                            command_outputs.append(RCMD.run_command('commit', \
                                conf = conf, sim_config = sim_config, printall = printall))
                            if 'Failed to commit' in ''.join(command_outputs[-1:]):
                                ### ALTERNATIVE COMMANDS: show commit changes diff, commit show-error
                                command_outputs.append(RCMD.run_command('show configuration failed', \
                                    conf = conf, sim_config = sim_config, printall = printall))
                        elif RCMD.router_type=='juniper': command_outputs.append(RCMD.run_command('commit and-quit', \
                            conf = conf, sim_config = sim_config, printall = printall))
                        elif RCMD.router_type=='huawei' and RCMD.huawei_version >= 7:
                            commit_output = command_outputs.append(RCMD.run_command('commit', \
                                conf = conf, sim_config = sim_config, printall = printall))
                        ### EXIT CONFIG SECTION --------------------------------
                        if RCMD.router_type=='cisco_ios': command_outputs.append(RCMD.run_command('end', \
                            conf = conf, sim_config = sim_config, printall = printall))
                        elif RCMD.router_type=='cisco_xr': command_outputs.append(RCMD.run_command('exit', \
                            conf = conf, sim_config = sim_config, printall = printall))
                        ### JUNOS IS ALREADY OUT OF CONFIG ###
                        elif RCMD.router_type=='huawei':
                            command_outputs.append(RCMD.run_command('quit', conf = conf, \
                                sim_config = sim_config, printall = printall))
                        ### NVRAM WRITE/SAVE SECTION - NO CONFIG MODE! ---------
                        if RCMD.router_type=='cisco_ios':
                            command_outputs.append(RCMD.run_command('write', conf = False, \
                                sim_all = sim_config, printall = printall))
                        elif RCMD.router_type=='huawei':
                            ### ALL HUAWEI ROUTERS NEED SAVE ###
                            command_outputs.append(RCMD.run_command('save', conf = False, \
                                sim_all = sim_config, printall = printall))
                            command_outputs.append(RCMD.run_command('yes', conf = False, \
                                sim_all = sim_config, printall = printall))
                ### CHECK CONF OUTPUTS #########################################
                if (conf or RCMD.conf):
                    RCMD.config_problem = None
                    CGI_CLI.uprint('\nCHECKING COMMIT ERRORS...', tag = 'h1', color = 'blue')
                    for rcmd_output in command_outputs:
                        CGI_CLI.uprint(' . ', no_newlines = True)
                        if 'INVALID INPUT' in rcmd_output.upper() \
                            or 'INCOMPLETE COMMAND' in rcmd_output.upper() \
                            or 'FAILED TO COMMIT' in rcmd_output.upper() \
                            or 'UNRECOGNIZED COMMAND' in rcmd_output.upper() \
                            or 'ERROR:' in rcmd_output.upper() \
                            or 'SYNTAX ERROR' in rcmd_output.upper():
                            RCMD.config_problem = True
                            CGI_CLI.uprint('\nCONFIGURATION PROBLEM FOUND:', color = 'red')
                            CGI_CLI.uprint('%s' % (rcmd_output), color = 'darkorchid')
                    ### COMMIT TEXT ###
                    if not (do_not_final_print or RCMD.do_not_final_print):
                        text_to_commit = str()
                        if not commit_text and not RCMD.commit_text: text_to_commit = 'COMMIT'
                        elif commit_text: text_to_commit = commit_text
                        elif RCMD.commit_text: text_to_commit = RCMD.commit_text
                        if submit_result:
                            if RCMD.config_problem:
                                CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = 'h1', tag_id = 'submit-result', color = 'red')
                            else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = 'h1', tag_id = 'submit-result', color = 'green')
                        else:
                            if RCMD.config_problem:
                                CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = 'h1', color = 'red')
                            else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = 'h1', color = 'green')
        return command_outputs

    @staticmethod
    def __cleanup__():
        RCMD.output, RCMD.fp = None, None
        try:
            if RCMD.ssh_connection:
                if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
                elif RCMD.use_module == 'paramiko': RCMD.client.close()
                if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DONE.' % \
                    (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT), color = 'gray')
                RCMD.ssh_connection = None
        except: pass

    @staticmethod
    def disconnect():
        RCMD.output, RCMD.fp = None, None
        try:
            if RCMD.ssh_connection:
                if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
                elif RCMD.use_module == 'paramiko': RCMD.client.close()
                if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DISCONNECTED.' % \
                    (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT), color = 'gray')
                RCMD.ssh_connection = None
                time.sleep(RCMD.DISCONNECT_TIMEOUT)
        except: pass

    @staticmethod
    def ssh_send_command_and_read_output(chan, prompts, \
        send_data = str(), long_lasting_mode = None, \
        autoconfirm_mode = None, ignore_prompt = None, \
        printall = True):
        '''
        autoconfirm_mode = True ==> CISCO - '\n', HUAWEI - 'Y\n'
        '''
        output, output2, new_prompt = str(), str(), str()
        exit_loop, exit_loop2 = False, False
        timeout_counter_100msec, timeout_counter_100msec_2 = 0, 0

        ### FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERED ###
        if chan.recv_ready(): flush_buffer = chan.recv(9999)
        time.sleep(0.1)
        chan.send(send_data + '\n')
        time.sleep(0.1)

        ### MAIN WHILE LOOP ###################################################
        while not exit_loop:
            if chan.recv_ready():
                ### WORKARROUND FOR DISCONTINIOUS OUTPUT FROM ROUTERS ###
                timeout_counter_100msec = 0
                buff = chan.recv(9999)
                try:
                    buff_read = str(buff.decode(encoding='utf-8').\
                        replace('\x0d','').replace('\x07','').\
                        replace('\x08','').replace(' \x1b[1D','').replace(u'\u2013',''))
                    output += buff_read
                except:
                    CGI_CLI.uprint('BUFF_ERR[%s][%s]'%(buff,type(buff)), color = 'red')
                    CGI_CLI.uprint(traceback.format_exc(), color = 'magenta')
            else:
                buff_read = str()
                time.sleep(0.1);
                timeout_counter_100msec += 1

                ### LONG LASTING COMMAND = ONLY CONNECTION TIMEOUT WILL BE APPLIED ###
                if long_lasting_mode:
                    if timeout_counter_100msec%100: pass
                    elif CGI_CLI.cgi_active:
                        ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ###
                        CGI_CLI.uprint("<script>console.log('10sec...');</script>", raw = True)
                    if timeout_counter_100msec + 100 >= RCMD.CONNECTION_TIMEOUT*10:
                        CGI_CLI.uprint("LONG LASTING COMMAND TIMEOUT!", color = 'red')
                        exit_loop = True
                        break
                continue

            ### FIND LAST LINE (STRIPPED), THIS COULD BE PROMPT ###
            last_line_edited = str()
            try: last_line_original = output.splitlines()[-1].strip()
            except: last_line_original = str()

            # FILTER-OUT '(...)' FROM PROMPT IOS-XR/IOS-XE ###
            if RCMD.router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
                try:
                    last_line_part1 = last_line_original.split('(')[0]
                    last_line_part2 = last_line_original.split(')')[1]
                    last_line_edited = last_line_part1 + last_line_part2
                except:
                    if 'sysadmin' in last_line_original and '#' in last_line_original:
                        last_line_edited = 'sysadmin#'
                    else: last_line_edited = last_line_original

            ### PRINT LONG LASTING OUTPUTS PER PARTS ##########################
            if printall and long_lasting_mode and buff_read and not RCMD.silent_mode:
                CGI_CLI.uprint('%s' % (buff_read), color = 'gray', no_newlines = True)

            # IS ACTUAL LAST LINE PROMPT ? IF YES , GO AWAY
            for actual_prompt in prompts:
                if output.strip().endswith(actual_prompt) or \
                    (last_line_edited and last_line_edited.endswith(actual_prompt)) or \
                    (last_line_original and last_line_original.endswith(actual_prompt)):
                        #CGI_CLI.uprint(prompts)
                        exit_loop=True; break
            else:
                continue_while_loop = False
                dialog_list = ['?', '[Y/N]:', '[confirm]', '? [no]:']
                for dialog_line in dialog_list:
                    if last_line_original.strip().endswith(dialog_line) or \
                        last_line_edited.strip().endswith(dialog_line):
                        if autoconfirm_mode:
                            ### AUTO-CONFIRM MODE ###
                            time.sleep(0.2)
                            if RCMD.router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
                                chan.send('\n')
                            elif RCMD.router_type in ["vrp",'huawei']:
                                chan.send('Y\n')
                            time.sleep(0.5)
                            continue_while_loop = True
                            break
                        else:
                            ### INTERACTIVE QUESTION --> GO AWAY ###
                            time.sleep(0.1)
                            continue_while_loop = True
                            exit_loop = True
                            break

                ### CONTINUE WHILE LOOP ###
                if continue_while_loop: continue

                ### LONG LASTING COMMAND = ONLY CONNECTION TIMEOUT WILL BE APPLIED ###
                if long_lasting_mode:
                    if timeout_counter_100msec%100: pass
                    elif CGI_CLI.cgi_active:
                        ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ###
                        CGI_CLI.uprint("<script>console.log('10s...');</script>", raw = True)
                    if timeout_counter_100msec + 100 > RCMD.CONNECTION_TIMEOUT*10:
                        CGI_CLI.uprint("LONG LASTING COMMAND TIMEOUT!!", color = 'red')
                        exit_loop = True
                        break
                else:
                    ### IGNORE NEW PROMPT AND GO AWAY ###
                    if ignore_prompt:
                        time.sleep(1)
                        exit_loop = True
                        break

                    ### 30 SECONDS COMMAND TIMEOUT ###
                    if timeout_counter_100msec > RCMD.CMD_TIMEOUT*10: exit_loop = True; break
                    ### 10 SECONDS --> This could be a new PROMPT ###
                    elif timeout_counter_100msec > 10*10 and not exit_loop2:
                        ### TRICK IS IF NEW PROMPT OCCURS, HIT ENTER ... ###
                        ### ... AND IF OCCURS THE SAME LINE --> IT IS NEW PROMPT!!! ###
                        chan.send('\n')
                        time.sleep(0.5)
                        while(not exit_loop2):
                            if chan.recv_ready():
                                buff = chan.recv(9999)
                                buff_read = str(buff.decode(encoding='utf-8').\
                                    replace('\x0d','').replace('\x07','').\
                                    replace('\x08','').replace(' \x1b[1D','').replace(u'\u2013',''))
                                output2 += buff_read
                            else: time.sleep(0.1); timeout_counter_100msec_2 += 1
                            try: new_last_line = output2.splitlines()[-1].strip()
                            except: new_last_line = str()
                            if last_line_original and new_last_line and last_line_original == new_last_line:
                                if printall: CGI_CLI.uprint('NEW_PROMPT: %s' % (last_line_original), color = 'cyan')
                                new_prompt = last_line_original; exit_loop=True;exit_loop2=True; break
                            # WAIT UP TO 5 SECONDS
                            if (timeout_counter_100msec_2) > 5*10: exit_loop2 = True; break
        return output, new_prompt

    @staticmethod
    def ssh_raw_detect_router_type(debug = None):
        ### DETECT DEVICE PROMPT FIRST
        def ssh_raw_detect_prompt(chan, debug = debug):
            output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
            flush_buffer = chan.recv(9999)
            del flush_buffer
            chan.send('\t \n\n')
            time.sleep(0.2)
            while not (last_line and last_but_one_line and last_line == last_but_one_line):
                buff = chan.recv(9999)
                if len(buff)>0:
                    if debug: CGI_CLI.uprint('LOOKING_FOR_PROMPT:',last_but_one_line,last_line, color = 'grey')
                    try:
                        output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                            replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                    except: pass
                    if '--More--' or '---(more' in buff.strip():
                        chan.send('\x20')
                        if debug: CGI_CLI.uprint('SPACE_SENT.', color = 'blue')
                        time.sleep(0.1)
                    try: last_line = output.splitlines()[-1].strip().replace('\x20','')
                    except: last_line = 'dummyline1'
                    try:
                        last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
                        if len(last_but_one_line) == 0:
                            ### vJunos '\x20' --> '\n\nprompt' workarround
                            last_but_one_line = output.splitlines()[-3].strip().replace('\x20','')
                    except: last_but_one_line = 'dummyline2'
            prompt = output.splitlines()[-1].strip()
            if debug: CGI_CLI.uprint('DETECTED PROMPT: \'' + prompt + '\'', color = 'yellow')
            return prompt
        # bullet-proof read-until function , even in case of ---more---
        def ssh_raw_read_until_prompt(chan,command,prompts,debug = debug):
            output, buff, last_line, exit_loop = str(), str(), 'dummyline1', False
            # avoid of echoing commands on ios-xe by timeout 1 second
            flush_buffer = chan.recv(9999)
            del flush_buffer
            chan.send(command)
            time.sleep(0.3)
            output, exit_loop = '', False
            while not exit_loop:
                if debug: CGI_CLI.uprint('LAST_LINE:',prompts,last_line)
                buff = chan.recv(9999)
                try:
                    output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                        replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                except: pass
                if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
                if debug: CGI_CLI.uprint('BUFFER:' + buff, color = 'grey')
                try: last_line = output.splitlines()[-1].strip()
                except: last_line = str()
                for actual_prompt in prompts:
                    if output.endswith(actual_prompt) \
                        or (last_line and last_line.endswith(actual_prompt)) \
                        or actual_prompt in last_line: exit_loop = True
            return output
        # Detect function start
        #asr1k_detection_string = 'CSR1000'
        #asr9k_detection_string = 'ASR9K|IOS-XRv 9000'
        router_os, prompt = str(), str()

        ### 1-CONNECTION ONLY, connection opened in RCMD.connect ###
        # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
        # \n\n get prompt as last line
        prompt = ssh_raw_detect_prompt(RCMD.ssh_connection, debug=debug)
        ### test if this is HUAWEI VRP
        if prompt and not router_os:
            command = 'display version | include (Huawei)\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'Huawei Versatile Routing Platform Software' in output: router_os = 'vrp'
        ### JUNOS
        if prompt and not router_os:
            command = 'show version | match Software\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'JUNOS' in output: router_os = 'junos'

        ### test if this is CISCO IOS-XR, IOS-XE or JUNOS
        if prompt and not router_os:
            command = 'show version | include Software\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'iosxr-' in output or 'Cisco IOS XR Software' in output:
                router_os = 'ios-xr'
                if 'ASR9K' in output or 'IOS-XRv 9000' in output: RCMD.router_version = 'ASR9K'
            elif 'Cisco IOS-XE software' in output or 'Cisco IOS XE Software' in output:
                router_os = 'ios-xe'
                if 'CSR1000' in output: RCMD.router_version = 'ASR1K'

        if prompt and not router_os:
            command = 'uname -a\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'LINUX' in output.upper(): router_os = 'linux'
        if not router_os:
            CGI_CLI.uprint("\nCannot find recognizable OS in %s" % (output), color = 'magenta')
        netmiko_os = str()
        if router_os == 'ios-xe': netmiko_os = 'cisco_ios'
        if router_os == 'ios-xr': netmiko_os = 'cisco_xr'
        if router_os == 'junos': netmiko_os = 'juniper'
        if router_os == 'linux': netmiko_os = 'linux'
        if router_os == 'vrp': netmiko_os = 'huawei'
        return netmiko_os, prompt



class LCMD(object):

    @staticmethod
    def init(logfilename = None, printall = None):
        LCMD.initialized = True
        if logfilename: LCMD.logfilename = logfilename
        else:
            if 'WIN32' in sys.platform.upper(): LCMD.logfilename = 'nul'
            else: LCMD.logfilename = '/dev/null'
        LCMD.printall = printall

    @staticmethod
    def init_log_and_print(logfilename = None, printall = None):
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(logfilename = logfilename, printall = printall)
        ### LOCAL PRINTALL AND LOGFILENAME OVERWRITES GLOBAL
        if not printall: printall = LCMD.printall
        if not logfilename: logfilename = LCMD.logfilename
        return logfilename, printall

    @staticmethod
    def run_command(cmd_line = None, logfilename = None, printall = None,
        chunked = None, timeout_sec = 5000):
        os_output, cmd_list, timer_counter_100ms = str(), None, 0
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_line:
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue')
                LCMD.fp.write('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
                try:
                    if chunked:
                        os_output, timer_counter_100ms = str(), 0
                        CommandObject = subprocess.Popen(cmd_line,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT, shell=True)
                        while CommandObject.poll() is None:
                            stdoutput = str(CommandObject.stdout.readline())
                            while stdoutput:
                                if stdoutput:
                                    os_output += copy.deepcopy(stdoutput) + '\n'
                                    if printall:
                                        CGI_CLI.uprint(stdoutput.strip(), color = 'gray')
                                stdoutput = str(CommandObject.stdout.readline())
                            time.sleep(0.1)
                            timer_counter_100ms += 1
                            if timer_counter_100ms > timeout_sec * 10:
                                CommandObject.terminate()
                                break
                    else:
                        os_output = subprocess.check_output(str(cmd_line), \
                            stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                except (subprocess.CalledProcessError) as e:
                    os_output = str(e.output.decode("utf-8"))
                    if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                    LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    LCMD.fp.write(exc_text + '\n')
                if not chunked and os_output and printall: CGI_CLI.uprint(os_output, color = 'gray', timestamp = 'no')
                LCMD.fp.write(os_output + '\n')
        return os_output

    @staticmethod
    def run_paralel_commands(cmd_data = None, logfilename = None, printall = None, \
        timeout_sec = 5000, custom_text = None, check_exitcode = None):
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        commands_ok = None
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            commands_ok = True
            with open(logfilename,"a+") as LCMD.fp:
                ### START LOOP ###
                CommandObjectList = []
                for cmd_line in cmd_list:
                    os_output = str()
                    try:
                        actual_CommandObject = subprocess.Popen(cmd_line, \
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        CommandObjectList.append(actual_CommandObject)
                        if printall: CGI_CLI.uprint("LOCAL_COMMAND_(START)[%s]: %s" % (str(actual_CommandObject), str(cmd_line)), color = 'blue')
                        LCMD.fp.write('LOCAL_COMMAND_(START)[%s]: %s' % (str(actual_CommandObject), str(cmd_line)) + '\n')
                    except (subprocess.CalledProcessError) as e:
                        os_output = str(e.output.decode("utf-8"))
                        if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                        LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                        commands_ok = False
                    except:
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                        LCMD.fp.write(exc_text + '\n')
                        commands_ok = False
                if not printall:
                    CGI_CLI.uprint("%s: %d   " % (str(custom_text) if custom_text else "RUNNING LOCAL_COMMANDS", len(CommandObjectList)), no_newlines = True)
                ### LOOP WAITING END ###
                timer_counter_100ms = 0
                while len(CommandObjectList)>0:
                    for actual_CommandObject in CommandObjectList:
                        timer_counter_100ms += 1
                        time.sleep(0.1)
                        outputs = str()
                        actual_poll = actual_CommandObject.poll()
                        if actual_poll is None: pass
                        else:
                            StdOutText, StdErrText = actual_CommandObject.communicate()
                            outputs = '\n'.join([StdOutText.decode(), StdErrText.decode()])
                            ExitCode = actual_CommandObject.returncode
                            if check_exitcode and ExitCode != 0: commands_ok = False
                            if printall: CGI_CLI.uprint("LOCAL_COMMAND_(END)[%s]: %s\n%s" % (str(actual_CommandObject), str(cmd_line), outputs), color = 'gray')
                            LCMD.fp.write('LOCAL_COMMAND_(END)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                            CommandObjectList.remove(actual_CommandObject)
                            continue
                        if timer_counter_100ms % 10 == 0:
                            if printall: CGI_CLI.uprint("%d LOCAL_COMMAND%s RUNNING." % (len(CommandObjectList), 'S are' if len(CommandObjectList) > 1 else ' is'))
                            else: CGI_CLI.uprint(" %d   " % (len(CommandObjectList)), no_newlines = True)
                        if timer_counter_100ms % 300 == 0: CGI_CLI.uprint('\n')
                        if timer_counter_100ms > timeout_sec * 10:
                            if printall: CGI_CLI.uprint("LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s" % (str(actual_CommandObject), str(cmd_line), outputs), color = 'red')
                            LCMD.fp.write('LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                            actual_CommandObject.terminate()
                            CommandObjectList.remove(actual_CommandObject)
                            commands_ok = False
            if not printall: CGI_CLI.uprint("\n")
        return commands_ok

    @staticmethod
    def run_commands(cmd_data = None, logfilename = None, printall = None):
        """
        FUNCTION: LCMD.run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        """
        os_outputs =  None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            os_outputs = []
            with open(logfilename,"a+") as LCMD.fp:
                for cmd_line in cmd_list:
                    os_output = str()
                    if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue')
                    LCMD.fp.write('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
                    try: os_output = subprocess.check_output(str(cmd_line), stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                    except (subprocess.CalledProcessError) as e:
                        os_output = str(e.output.decode("utf-8"))
                        if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                        LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                    except:
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                        LCMD.fp.write(exc_text + '\n')
                    if os_output and printall: CGI_CLI.uprint(os_output, color = 'gray', timestamp = 'no')
                    LCMD.fp.write(os_output + '\n')
                    os_outputs.append(os_output)
        return os_outputs

    @staticmethod
    def eval_command(cmd_data = None, logfilename = None, printall = None):
        """
        NOTE: by default - '\\n' = insert newline to text, '\n' = interpreted line
        """
        local_output = None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EVAL: %s" % (cmd_data))
                try:
                    local_output = eval(cmd_data)
                    if printall: CGI_CLI.uprint(str(local_output), color= 'gray', timestamp = 'no')
                    LCMD.fp.write('EVAL: ' + cmd_data + '\n' + str(local_output) + '\n')
                except Exception as e:
                    if printall:CGI_CLI.uprint('EVAL_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EVAL_PROBLEM[' + str(e) + ']\n', color = 'magenta')
        return local_output

    @staticmethod
    def exec_command(cmd_data = None, logfilename = None, printall = None, escape_newline = None):
        """
        NOTE:
              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EXEC: %s" % (cmd_data))
                LCMD.fp.write('EXEC: ' + cmd_data + '\n')
                ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                try:
                    if escape_newline:
                        edict = {}; eval(compile(cmd_data.replace('\n', '\\n'),\
                            '<string>', 'exec'), globals(), edict)
                    else: edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
                except Exception as e:
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None


    @staticmethod
    def exec_command_try_except(cmd_data = None, logfilename = None, \
        printall = None, escape_newline = None):
        """
        NOTE: This method can access global variable, expects '=' in expression,
              in case of except assign value None

              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                try:
                    if '=' in cmd_data:
                        if escape_newline:
                            cmd_ex_data = 'global %s\ntry: %s = %s \nexcept: %s = None' % \
                                (cmd_data.replace('\n', '\\n').split('=')[0].\
                                strip().split('[')[0],cmd_data.split('=')[0].strip(), \
                                cmd_data.replace('\n', '\\n').split('=')[1].strip(), \
                                cmd_data.split('=')[0].strip())
                        else:
                            cmd_ex_data = 'global %s\ntry: %s = %s \nexcept: %s = None' % \
                                (cmd_data.split('=')[0].strip().split('[')[0], \
                                cmd_data.split('=')[0].strip(), \
                                cmd_data.split('=')[1].strip(), \
                                cmd_data.split('=')[0].strip())
                    else: cmd_ex_data = cmd_data
                    if printall: CGI_CLI.uprint("EXEC: \n%s" % (cmd_ex_data))
                    LCMD.fp.write('EXEC: \n' + cmd_ex_data + '\n')
                    ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                    edict = {}; eval(compile(cmd_ex_data, '<string>', 'exec'), globals(), edict)
                    #CGI_CLI.uprint("%s" % (eval(cmd_data.split('=')[0].strip())))
                except Exception as e:
                    if printall: CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', \
                                     color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None


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
        except Exception as e: CGI_CLI.uprint(str(e))

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
        columns = []
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try:
                cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s';"%(table_name))
                records = cursor.fetchall()
                ### 4TH COLUMN IS COLUMN NAME
                ### OUTPUTDATA STRUCTURE IS: '[(SQL_RESULT)]' --> records[0] = UNPACK []
                for item in records:
                    try: new_item = item[3].decode('utf-8')
                    except: new_item = item[3]
                    columns.append(new_item)
            except Exception as e: CGI_CLI.uprint(str(e))
            try: cursor.close()
            except: pass
        return columns

    def sql_read_sql_command(self, sql_command):
        '''NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE'''
        lines = []
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try:
                cursor.execute(sql_command)
                records = cursor.fetchall()
                ### OUTPUTDATA STRUCTURE IS: '[(SQL_LINE1),...]' --> records[0] = UNPACK []
                ### WORKARROUND FOR BYTEARRAYS WHICH ARE NOT JSONIZABLE
                for line in records:
                    columns = []
                    for item in line:
                        try: new_item = item.decode('utf-8')
                        except:
                           try: new_item = str(item)
                           except: new_item = item
                        columns.append(new_item)
                    lines.append(columns)
            except Exception as e: CGI_CLI.uprint(str(e))
            try: cursor.close()
            except: pass
            ### FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
        return lines

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
            except Exception as e: CGI_CLI.uprint(str(e))
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

    def sql_read_table_records(self, select_string = None, from_string = None, \
        where_string = None, order_by = None):
        """NOTES: - FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
                  - order_by - needed to append ASC|DESC on end of string"""
        check_data = None
        if not select_string: select_string = '*'
        #SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id) FROM ipxt_data_collector \
        #WHERE username='mkrupa' AND device_name='AUVPE3');
        if self.sql_is_connected():
            if from_string:
                sql_string = "SELECT %s FROM %s%s%s;" % (select_string, from_string, \
                    ' WHERE %s' % (where_string) if where_string else str(), \
                    ' ORDER BY %s' % (order_by) if order_by else str() \
                    )
                check_data = self.sql_read_sql_command(sql_string)
        return check_data

    def sql_read_records_to_dict_list(table_name = None, from_string = None, \
        select_string = None, where_string = None, order_by = None, \
        delete_columns = None):
        """sql_read_last_record_to_dict - MAKE DICTIONARY FROM LAST TABLE RECORD
           NOTES: -'table_name' is alternative name to 'from_string'
                  - it always read last record dependent on 'where_string'
                    which contains(=filters by) username,device_name,vpn_name
                  - order_by - needed to append ASC|DESC on end of string
        """
        dict_data, dict_list = collections.OrderedDict(), []
        table_name_or_from_string = None
        if not select_string: select_string = '*'
        if table_name:  table_name_or_from_string = table_name
        if from_string: table_name_or_from_string = from_string
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_records( \
            from_string = table_name_or_from_string, \
            select_string = select_string, where_string = where_string,
            order_by = order_by)
        ### COLUMNS ARE IN SELECT STRING IF SELECT STRING EXISTS ##############
        if select_string != '*':
            columns_list = [ column.strip() for column in select_string.split(',') ]
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




##############################################################################

def display_interface(header_text = None, interface_list = None, color = None):
    if len(interface_list) > 0: CGI_CLI.uprint(header_text, color = color)
    for interface in interface_list:
        isis_interface, description = interface
        CGI_CLI.uprint('%s  -  %s' %(isis_interface, description), color = color)
    if len(interface_list) > 0: CGI_CLI.uprint(' ')

##############################################################################
#
# def CONFIG TEMPLATES
#
##############################################################################

xr_config_header ='''!
router isis PAII
!
''' 

xr_config_interface_part ='''% for isis_interface, description in isis_interface_fail_list:
 interface ${isis_interface}
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
% endfor
''' 

##############################################################################
#
# def BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)
try:
    CSS_STYLE = """
debug {
  background-color: lightgray;
}

warning {
  color: red;
  background-color: yellow;
}
"""

    goto_webpage_end_by_javascript = str()

    logfilename = str()
    logging.raiseExceptions=False
    USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True, css_style = CSS_STYLE)

    device_list = []
    devices_string = CGI_CLI.data.get("device",str())
    if devices_string:
        if ',' in devices_string:
            device_list = [ dev_mix_case.upper() for dev_mix_case in devices_string.split(',') ]
        else: device_list = [devices_string.upper()]

    CGI_CLI.uprint('ISIS check (v.%s)' % (CGI_CLI.VERSION()), tag = 'h1', color = 'blue')

    printall = CGI_CLI.data.get("printall")
    CGI_CLI.timestamp = CGI_CLI.data.get("timestamps")
    if printall: CGI_CLI.print_args()


    ### HTML MENU SHOWS ONLY IN CGI MODE ###
    if CGI_CLI.cgi_active and not CGI_CLI.submit_form:
        CGI_CLI.formprint([{'text':'device'},'<br/>',{'text':'username'},'<br/>',\
            {'password':'password'},'<br/>',{'checkbox':'printall'},'<br/>','<br/>'],\
            submit_button = 'OK', pyfile = None, tag = None, color = None)

    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()
    if CGI_CLI.cgi_active and not (USERNAME and PASSWORD):
        if iptac_server == 'iptac5': USERNAME, PASSWORD = 'iptac', 'paiiUNDO'

    for device in device_list:

        ### REMOTE DEVICE OPERATIONS ######################################
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                connection_timeout = 60, disconnect_timeout = 0.1, \
                printall = printall, logfilename = logfilename)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                continue

            rcmds_0 = {
                'cisco_ios':['show bgp summary'],
                'cisco_xr':["show bgp summary"],
                'juniper':['show configuration protocols bgp | match local-as']
            }

            CGI_CLI.uprint('Check Internal AS on %s' % (device), \
                no_newlines = None if printall else True)
            rcmds_0_outputs = RCMD.run_commands(rcmds_0, printall = printall)
            CGI_CLI.uprint('\n')

            if 'local AS number 2300' in rcmds_0_outputs[0] or 'local-as 2300' in rcmds_0_outputs[0]:
                RCMD.disconnect()
                CGI_CLI.uprint('This is IMN Router (Internal AS 2300).\n')
                sys.exit(0)
            elif 'local AS number 5511' in rcmds_0_outputs[0] or 'local-as 5511' in rcmds_0_outputs[0]: pass
            else:
                RCMD.disconnect()
                CGI_CLI.uprint('This is not OTI Router (unknown Internal AS).\n')
                sys.exit(0)

            rcmds_1 = {
                'cisco_ios':['show interfaces description | i Custom'],
                'cisco_xr':["show int description | utility egrep 'Custom|Peer|peer|Content'"],
                'juniper':['show interfaces descriptions | match Custom']
            }

            CGI_CLI.uprint('Read interfaces on %s' % (device), \
                no_newlines = None if printall else True)
            rcmds_1_outputs = RCMD.run_commands(rcmds_1, printall = printall)
            CGI_CLI.uprint('\n')

            isis_interface_list = []

            if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                ### SELECT DOTTED = BE and SUBINTERFACES FROM OUTPUT ###
                for line in rcmds_1_outputs[0].splitlines():
                    if line.strip() and 'CUSTOM' in line.upper() and not 'L2VPN' in line.upper():
                        if line.split()[-1] == 'MET' or line.split()[-1] == 'UTC': continue
                        if line.split()[0] == 'show': continue
                        if line.strip() in RCMD.DEVICE_PROMPTS: continue
                        if 'TESTING' in line.upper() or 'ETHNOW-TEST' in line.upper(): continue
                        if 'OLD' in line.upper(): continue
                        if not 'BE' in line.split()[0].upper() and 'LAG' in line.upper(): continue

                        ### DOTTED INTERFACES FIRST ###
                        if '.' in line.split()[0]:
                            if len(isis_interface_list) == 0:
                                isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                            else:
                                is_in_isis_interface_list = False
                                for interface_string in isis_interface_list:
                                    if line.split()[0] in interface_string: is_in_isis_interface_list = True
                                    else: pass
                                if not is_in_isis_interface_list:
                                    isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                                    continue

                ### SELECT INTERFACES IF SUBINTERFACES ARE NOT IN LIST ###
                for line in rcmds_1_outputs[0].splitlines():
                    if line.strip() and 'CUSTOM' in line.upper() and not 'L2VPN' in line.upper():
                        if line.split()[-1] == 'MET' or line.split()[-1] == 'UTC': continue
                        if line.split()[0] == 'show': continue
                        if line.strip() in RCMD.DEVICE_PROMPTS: continue
                        if 'TESTING' in line.upper() or 'ETHNOW-TEST' in line.upper(): continue
                        if 'OLD' in line.upper(): continue
                        if not 'BE' in line.split()[0].upper() and 'LAG' in line.upper(): continue

                        ### UNDOTTED INTERFACES LAST ###
                        if not '.' in line.split()[0]:
                            if len(isis_interface_list) == 0:
                                isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                            else:
                                is_in_isis_interface_list = False
                                for interface_string in isis_interface_list:
                                    if line.split()[0] in interface_string: is_in_isis_interface_list = True
                                    else: pass
                                if not is_in_isis_interface_list:
                                    isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                                    continue

            if RCMD.router_type == 'juniper':
                ### SELECT BE and SUBINTERFACES FROM OUTPUT ###
                for line in rcmds_1_outputs[0].splitlines():
                    if line.strip() and 'CUSTOM' in line.upper() and not 'L2VPN' in line.upper():
                        if line == '{master}': continue
                        if line.strip() and len(line.split())> 0 and line.split()[0] == 'show': continue
                        if line.strip() in RCMD.DEVICE_PROMPTS: continue
                        if 'TESTING' in line.upper() or 'ETHNOW-TEST' in line.upper(): continue
                        if 'OLD' in line.upper() or 'LAG' in line.upper(): continue

                        ### DOTTED INTERFACES FIRST ###
                        if '.' in line.split()[0]:
                            if len(isis_interface_list) == 0:
                                isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                            else:
                                is_in_isis_interface_list = False
                                for interface_string in isis_interface_list:
                                    if line.split()[0] in interface_string: is_in_isis_interface_list = True
                                    else: pass
                                if not is_in_isis_interface_list:
                                    isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                                    continue

                ### SELECT INTERFACES IF SUBINTERFACES ARE NOT IN LIST ###
                for line in rcmds_1_outputs[0].splitlines():
                    if line.strip() and 'CUSTOM' in line.upper() and not 'L2VPN' in line.upper():
                        if line == '{master}': continue
                        if line.strip() and len(line.split())> 0 and line.split()[0] == 'show': continue
                        if line.strip() in RCMD.DEVICE_PROMPTS: continue
                        if 'TESTING' in line.upper() or 'ETHNOW-TEST' in line.upper(): continue
                        if 'OLD' in line.upper() or 'LAG' in line.upper(): continue

                        ### UNDOTTED INTERFACES LAST ###
                        if not '.' in line.split()[0]:
                            if len(isis_interface_list) == 0:
                                isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                            else:
                                is_in_isis_interface_list = False
                                for interface_string in isis_interface_list:
                                    if line.split()[0] in interface_string: is_in_isis_interface_list = True
                                    else: pass
                                if not is_in_isis_interface_list:
                                    isis_interface_list.append([line.split()[0], ' '.join(line.split()[3:])])
                                    continue

            if RCMD.router_type == 'huawei': pass


            rcmds_2 = {
                'cisco_ios':[],
                'cisco_xr':[],
                'juniper':[]
            }

            for isis_interface, description in isis_interface_list:
                rcmds_2['cisco_ios'].append('show isis interface %s' % (isis_interface))
                rcmds_2['cisco_xr'].append('show isis interface %s' % (isis_interface))
                rcmds_2['juniper'].append('show isis interface %s' % (isis_interface))


            CGI_CLI.uprint('Read interface isis on %s' % (device), \
                no_newlines = None if printall else True)
            rcmds_2_outputs = RCMD.run_commands(rcmds_2, printall = printall)
            CGI_CLI.uprint('\n')

            isis_interface_ok_list, isis_interface_fail_list, isis_interface_warning_list = [], [], []

            if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                for interface, rcmd_2_output in zip(isis_interface_list,rcmds_2_outputs):
                    isis_interface, description = interface
                    if '(Intf passive in IS-IS cfg)' in rcmd_2_output:
                        isis_interface_ok_list.append(interface)
                    elif '% No IS-IS instances are configured to use':
                        isis_interface_fail_list.append(interface)
                    else: isis_interface_warning_list.append(interface)

            if RCMD.router_type == 'juniper':
                for interface, rcmd_2_output in zip(isis_interface_list,rcmds_2_outputs):
                    isis_interface, description = interface
                    if 'Level 2 DR' in rcmd_2_output or 'Passive' in rcmd_2_output:
                        isis_interface_ok_list.append(interface)
                    else: isis_interface_fail_list.append(interface)

            ### PRINTOUTS ###
            if printall:
                CGI_CLI.uprint(isis_interface_list, name = True , jsonprint = True)
                CGI_CLI.uprint(isis_interface_fail_list, name = True , jsonprint = True)
                CGI_CLI.uprint(isis_interface_warning_list, name = True , jsonprint = True)
                CGI_CLI.uprint(isis_interface_ok_list, name = True , jsonprint = True)
            
            display_interface(header_text = '%s interface(s) with ISIS PROBLEM:' % (device), interface_list = isis_interface_fail_list, color = 'red')
            display_interface(header_text = '%s interface(s) with ISIS WARNING:' % (device), interface_list = isis_interface_warning_list, color = 'yellow')     
            display_interface(header_text = '%s interface(s) with ISIS OK:' % (device), interface_list = isis_interface_ok_list, color = 'green')


            data = {}
            data['isis_interface_fail_list'] = isis_interface_fail_list
            
            config_to_apply = str()
            if RCMD.router_type == 'cisco_xr':                
                mytemplate = Template(xr_config_header,strict_undefined=True)
                config_to_apply += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
                                
                mytemplate = Template(xr_config_interface_part,strict_undefined=True)
                config_to_apply += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'

            if isis_interface_fail_list:
                CGI_CLI.uprint('\nREPAIR CONFIG:\n\n%s' % (config_to_apply), color = 'blue')
 

            RCMD.disconnect()
except SystemExit: pass
except: CGI_CLI.uprint(traceback.format_exc(), tag = 'h3',color = 'magenta')