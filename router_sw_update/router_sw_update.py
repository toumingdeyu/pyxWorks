#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, traceback, logging
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
    js_reload_button = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""

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
        parser.add_argument("--check_files_only",
                            action = 'store_true', dest = "check_device_sw_files_only",
                            default = None,
                            help = "check existing device sw release files only, do not copy new tar files")
        parser.add_argument("--backup_configs",
                            action = 'store_true', dest = "backup_configs_to_device_disk",
                            default = None,
                            help = "backup configs to device hdd")
        #parser.add_argument("--force_rewrite",
        #                    action = 'store_true', dest = "force_rewrite_sw_files_on_device",
        #                    default = None,
        #                    help = "force rewrite sw release files on device disk")
        parser.add_argument("--delete",
                            action = 'store_true', dest = "delete_device_sw_files_on_end",
                            default = None,
                            help = "delete device sw release files on end after sw upgrade")
        # parser.add_argument("--sim",
                            # action = "store_true", dest = 'sim',
                            # default = None,
                            # help = "config simulation mode")
        parser.add_argument("--slow",
                            action = 'store_true', dest = "slow_scp_mode",
                            default = None,
                            help = "slow_scp_mode")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
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
    def init_cgi(chunked = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.chunked = None
        ### TO BE PLACED - BEFORE HEADER ###
        CGI_CLI.chunked_transfer_encoding_string = "Transfer-Encoding: chunked\r\n"
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
        ### DECIDE - CLI OR CGI MODE #######################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent:
            CGI_CLI.cgi_active = True
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active: CGI_CLI.data = vars(CGI_CLI.args)
        if CGI_CLI.cgi_active:
            CGI_CLI.chunked = chunked
            sys.stdout.write("%sContent-type:text/html\r\n" %
                (CGI_CLI.chunked_transfer_encoding_string if CGI_CLI.chunked else str()))
            sys.stdout.flush()
            CGI_CLI.print_chunk("\r\n\r\n<html><head><title>%s</title></head><body>" %
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
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
    def uprint(text, tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        log = None, no_newlines = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name, print_per_tag = copy.deepcopy(text), str(), str()
        if jsonprint:
            if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = json.dumps(text, indent = 4)
                except Exception as e: CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']')
        if name==True:
            if not 'inspect.currentframe' in sys.modules: import inspect
            callers_local_vars = inspect.currentframe().f_back.f_locals.items()
            var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
            if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
        elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '

        print_text = str(print_text)
        log_text   = str(copy.deepcopy((print_text)))
        if CGI_CLI.cgi_active:
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT
            if color and not tag: tag = 'p';
            if tag: CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"'%(color) if color else 'black'))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                    replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
            CGI_CLI.print_chunk(print_name + print_text)
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
                print(text_color + print_name + print_text + CGI_CLI.bcolors.ENDC)
        del print_text
        if CGI_CLI.cgi_active:
            if tag: CGI_CLI.print_chunk('</%s>'%(tag))
            elif not no_newlines: CGI_CLI.print_chunk('<br/>');
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
            if CGI_CLI.cgi_active: CGI_CLI.print_chunk('<br/><a href = "./%s">RELOAD</a>' % (pyfile))

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
        print_string += 'CGI_CLI.USERNAME[%s], CGI_CLI.PASSWORD[%s]\n' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No')
        print_string += 'remote_addr[%s], ' % dict(os.environ).get('REMOTE_ADDR','')
        print_string += 'browser[%s]\n' % dict(os.environ).get('HTTP_USER_AGENT','')
        print_string += 'CGI_CLI.cgi_active[%s]\n' % (str(CGI_CLI.cgi_active))
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_CLI.data[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4)))
            except: pass
        else: print_string += 'CLI_args = %s\nCGI_CLI.data = %s' % (str(sys.argv[1:]), str(json.dumps(CGI_CLI.data,indent = 4)))
        CGI_CLI.uprint(print_string)
        return print_string

    @staticmethod
    def print_env():
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', jsonprint = True)



##############################################################################


class RCMD(object):

    @staticmethod
    def connect(device = None, cmd_data = None, username = None, password = None, \
        use_module = 'paramiko', logfilename = None, timeout = 60, conf = None, \
        sim_config = None, disconnect = None, printall = None, \
        do_not_final_print = None, commit_text = None, silent_fail = None):
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
            RCMD.CMD = []
            RCMD.output, RCMD.fp = None, None
            RCMD.device = device
            RCMD.ssh_connection = None
            RCMD.TIMEOUT = timeout
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
            RCMD.KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']
            try: RCMD.DEVICE_HOST = device.split(':')[0]
            except: RCMD.DEVICE_HOST = str()
            try: RCMD.DEVICE_PORT = device.split(':')[1]
            except: RCMD.DEVICE_PORT = '22'
            if printall: CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.')
            RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
            if RCMD.router_type in RCMD.KNOWN_OS_TYPES and printall:
                CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type))
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
                    '%s%s#'%(RCMD.device.upper(),'(config-router)')  ]
                RCMD.TERM_LEN_0 = "terminal length 0"
                RCMD.EXIT = "exit"
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
            ### START SSH CONNECTION AGAIN #####################################
            try:
                if RCMD.router_type and RCMD.use_module == 'netmiko':
                    RCMD.ssh_connection = netmiko.ConnectHandler(device_type = RCMD.router_type, \
                        ip = RCMD.DEVICE_HOST, port = int(RCMD.DEVICE_PORT), \
                        username = RCMD.USERNAME, password = RCMD.PASSWORD)
                elif RCMD.router_type and RCMD.use_module == 'paramiko':
                    RCMD.client = paramiko.SSHClient()
                    RCMD.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    RCMD.client.connect(RCMD.DEVICE_HOST, port=int(RCMD.DEVICE_PORT), \
                        username=RCMD.USERNAME, password=RCMD.PASSWORD,look_for_keys=False)
                    RCMD.ssh_connection = RCMD.client.invoke_shell()
                    RCMD.ssh_connection.settimeout(RCMD.TIMEOUT)
                    RCMD.output, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,RCMD.TERM_LEN_0)
                    RCMD.output2, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,"")
                    RCMD.output += RCMD.output2
                ### WORK REMOTE  =============================================
                command_outputs = RCMD.run_commands(RCMD.CMD)
                ### ==========================================================
            except Exception as e:
                if not silent_fail: CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
            finally:
                if disconnect: RCMD.disconnect()
        else: CGI_CLI.uprint('DEVICE NOT INSERTED!', color = 'magenta')
        return command_outputs

    @staticmethod
    def run_command(cmd_line = None, printall = None, conf = None, sim_config = None, sim_all = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        sim_all  - simulate execution of all commands, not only config commands
                   used for ommit save/write in normal mode
        sim_config - simulate config commands
        """
        last_output, sim_mark = str(), str()
        if RCMD.ssh_connection and cmd_line:
            if ((sim_config or RCMD.sim_config) and (conf or RCMD.conf)) or sim_all: sim_mark = '(SIM)'
            else:
                if RCMD.use_module == 'netmiko':
                    last_output = RCMD.ssh_connection.send_command(cmd_line)
                elif RCMD.use_module == 'paramiko':
                    last_output, new_prompt = RCMD.ssh_send_command_and_read_output( \
                        RCMD.ssh_connection, RCMD.DEVICE_PROMPTS, cmd_line, printall = printall)
                    if new_prompt: RCMD.DEVICE_PROMPTS.append(new_prompt)
            if printall or RCMD.printall:
                CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line, color = 'blue')
                CGI_CLI.uprint(last_output, color = 'gray')
            else: CGI_CLI.uprint(' . ', no_newlines = True)
            if RCMD.fp: RCMD.fp.write('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line + '\n' + last_output + '\n')
        return last_output

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None, \
        do_not_final_print = None , commit_text = None, submit_result = None):
        """
        FUNCTION: run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        conf     - True/False, go to config mode
        sim_config - simulate config commands
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
                            CGI_CLI.uprint(str(last_output), color = 'gray')
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
                            conf = conf, sim_config = sim_config, printall = printall))
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
        if RCMD.ssh_connection:
            if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
            elif RCMD.use_module == 'paramiko': RCMD.client.close()
            if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DONE.' % (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT))
            RCMD.ssh_connection = None

    @staticmethod
    def disconnect():
        RCMD.output, RCMD.fp = None, None
        if RCMD.ssh_connection:
            if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
            elif RCMD.use_module == 'paramiko': RCMD.client.close()
            if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DISCONNECTED.' % (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT))
            RCMD.ssh_connection = None

    @staticmethod
    def ssh_send_command_and_read_output(chan,prompts,send_data=str(),printall=True):
        output, output2, new_prompt = str(), str(), str()
        exit_loop, exit_loop2 = False, False
        timeout_counter_100msec, timeout_counter_100msec_2 = 0, 0
        # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
        if chan.recv_ready(): flush_buffer = chan.recv(9999)
        time.sleep(0.1)
        chan.send(send_data + '\n')
        time.sleep(0.2)
        while not exit_loop:
            if chan.recv_ready():
                ### WORKARROUND FOR DISCONTINIOUS OUTPUT FROM ROUTERS ###
                timeout_counter_100msec = 0
                buff = chan.recv(9999)
                buff_read = buff.decode("utf-8").replace('\x0d','').replace('\x07','').\
                    replace('\x08','').replace(' \x1b[1D','')
                output += buff_read
            else: time.sleep(0.1); timeout_counter_100msec += 1
            # FIND LAST LINE, THIS COULD BE PROMPT
            try: last_line, last_line_orig = output.splitlines()[-1].strip(), output.splitlines()[-1].strip()
            except: last_line, last_line_orig = str(), str()
            # FILTER-OUT '(...)' FROM PROMPT IOS-XR/IOS-XE
            if RCMD.router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
                try:
                    last_line_part1 = last_line.split('(')[0]
                    last_line_part2 = last_line.split(')')[1]
                    last_line = last_line_part1 + last_line_part2
                except: last_line = last_line
            # FILTER-OUT '[*','[~','-...]' FROM VRP
            elif RCMD.router_type in ["vrp",'huawei']:
                try:
                    last_line_part1 = '[' + last_line.replace('[~','[').replace('[*','[').split('[')[1].split('-')[0]
                    last_line_part2 = ']' + last_line.replace('[~','[').replace('[*','[').split('[')[1].split(']')[1]
                    last_line = last_line_part1 + last_line_part2
                except: last_line = last_line
            # IS ACTUAL LAST LINE PROMPT ? IF YES , GO AWAY
            for actual_prompt in prompts:
                if output.endswith(actual_prompt) or \
                    last_line and last_line.endswith(actual_prompt):
                        exit_loop=True; break
            else:
                ### INTERACTIVE QUESTION --> GO AWAY FAST !!! ###
                if last_line.strip().endswith('?') or last_line.strip().endswith('[confirm]'): exit_loop = True; break
                ### 30 SECONDS COMMAND TIMEOUT
                elif (timeout_counter_100msec) > 30*10: exit_loop = True; break
                ### 10 SECONDS --> This could be a new PROMPT
                elif (timeout_counter_100msec) > 10*10 and not exit_loop2:
                    ### TRICK IS IF NEW PROMPT OCCURS, HIT ENTER ... ###
                    ### ... AND IF OCCURS THE SAME LINE --> IT IS NEW PROMPT!!! ###
                    chan.send('\n')
                    time.sleep(0.1)
                    while(not exit_loop2):
                        if chan.recv_ready():
                            buff = chan.recv(9999)
                            buff_read = buff.decode("utf-8").replace('\x0d','')\
                               .replace('\x07','').replace('\x08','').replace(' \x1b[1D','')
                            output2 += buff_read
                        else: time.sleep(0.1); timeout_counter_100msec_2 += 1
                        try: new_last_line = output2.splitlines()[-1].strip()
                        except: new_last_line = str()
                        if last_line_orig and new_last_line and last_line_orig == new_last_line:
                            if printall: CGI_CLI.uprint('NEW_PROMPT: %s' % (last_line_orig), color = 'cyan')
                            new_prompt = last_line_orig; exit_loop=True;exit_loop2=True; break
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
            time.sleep(0.3)
            while not (last_line and last_but_one_line and last_line == last_but_one_line):
                buff = chan.recv(9999)
                if len(buff)>0:
                    if debug: CGI_CLI.uprint('LOOKING_FOR_PROMPT:',last_but_one_line,last_line)
                    output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                              replace('\x1b[K','').replace('\n{master}\n','')
                    if '--More--' or '---(more' in buff.strip():
                        chan.send('\x20')
                        if debug: CGI_CLI.uprint('SPACE_SENT.')
                        time.sleep(0.3)
                    try: last_line = output.splitlines()[-1].strip().replace('\x20','')
                    except: last_line = 'dummyline1'
                    try:
                        last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
                        if len(last_but_one_line) == 0:
                            ### vJunos '\x20' --> '\n\nprompt' workarround
                            last_but_one_line = output.splitlines()[-3].strip().replace('\x20','')
                    except: last_but_one_line = 'dummyline2'
            prompt = output.splitlines()[-1].strip()
            if debug: CGI_CLI.uprint('DETECTED PROMPT: \'' + prompt + '\'')
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
                output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                          replace('\x1b[K','').replace('\n{master}\n','')
                if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
                if debug: CGI_CLI.uprint('BUFFER:' + buff)
                try: last_line = output.splitlines()[-1].strip()
                except: last_line = str()
                for actual_prompt in prompts:
                    if output.endswith(actual_prompt) or \
                        last_line and last_line.endswith(actual_prompt): exit_loop = True
            return output
        # Detect function start
        #asr1k_detection_string = 'CSR1000'
        #asr9k_detection_string = 'ASR9K|IOS-XRv 9000'
        router_os, prompt = str(), str()
        client = paramiko.SSHClient()
        #client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(RCMD.DEVICE_HOST, port = int(RCMD.DEVICE_PORT), \
                username = RCMD.USERNAME, password = RCMD.PASSWORD)
            chan = client.invoke_shell()
            chan.settimeout(RCMD.TIMEOUT)
            # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
            # \n\n get prompt as last line
            prompt = ssh_raw_detect_prompt(chan, debug=debug)
            #test if this is HUAWEI VRP
            if prompt and not router_os:
                command = 'display version | include (Huawei)\n'
                output = ssh_raw_read_until_prompt(chan, command, [prompt], debug=debug)
                if 'Huawei Versatile Routing Platform Software' in output: router_os = 'vrp'
            #test if this is CISCO IOS-XR, IOS-XE or JUNOS
            if prompt and not router_os:
                command = 'show version\n'
                output = ssh_raw_read_until_prompt(chan, command, [prompt], debug=debug)
                if 'iosxr-' in output or 'Cisco IOS XR Software' in output:
                    router_os = 'ios-xr'
                    if 'ASR9K' in output or 'IOS-XRv 9000' in output: RCMD.router_version = 'ASR9K'
                elif 'Cisco IOS-XE software' in output:
                    router_os = 'ios-xe'
                    if 'CSR1000' in output: RCMD.router_version = 'ASR1K'
                elif 'JUNOS OS' in output: router_os = 'junos'
            if prompt and not router_os:
                command = 'uname -a\n'
                output = ssh_raw_read_until_prompt(chan, command, [prompt], debug=debug)
                if 'LINUX' in output.upper(): router_os = 'linux'
            if not router_os:
                CGI_CLI.uprint("\nCannot find recognizable OS in %s" % (output), color = 'magenta')
        except Exception as e: CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']' , color = 'magenta')
        finally: client.close()
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
                if not chunked and os_output and printall: CGI_CLI.uprint(os_output, color = 'gray')
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
                    if os_output and printall: CGI_CLI.uprint(os_output, color = 'gray')
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
                    if printall: CGI_CLI.uprint(str(local_output))
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
            except Exception as e: print(e)
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
            except Exception as e: print(e)
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


###############################################################################

def generate_logfilename(prefix = None, USERNAME = None, suffix = None, \
    directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(DIR,'logs')
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

##############################################################################

def do_scp_command(USERNAME = None, PASSWORD = None, device = None, \
    local_file = None, device_file = None , printall = None):
    if USERNAME and PASSWORD and local_file and device_file:
        os.environ['SSHPASS'] = PASSWORD
        if not printall: CGI_CLI.uprint(' copying %s    ' % (device_file), no_newlines = True)
        local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s' \
            % (local_file, USERNAME, device, device_file)
        scp_result = LCMD.run_command(cmd_line = local_command,
            printall = printall, chunked = True)
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
        return scp_result
    else: return str()

###############################################################################

def do_scp_all_files(true_sw_release_files_on_server = None, device_list = None, \
    USERNAME = None, PASSWORD = None , drive_string = None, printall = None):
    result = True
    os.environ['SSHPASS'] = PASSWORD
    for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server:
        cp_cmd_list = []
        ### ONLY 1 SCP CONNECTION PER ROUTER ###
        for device in device_list:
            local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s' \
                % (os.path.join(directory, file), USERNAME, device, \
                '%s%s' % (drive_string, os.path.join(dev_dir, file)))
            cp_cmd_list.append(local_command)
        #if printall: CGI_CLI.uprint("SCP COMMANDS:\n"+'\n'.join(cp_cmd_list))
        os.environ['SSHPASS'] = PASSWORD
        copy_commands = {'unix':cp_cmd_list}
        partial_result = LCMD.run_paralel_commands(copy_commands, \
            custom_text='copying file(s) %s, (file size %.2fMB) to device(s) %s' % (file, float(fsize)/1048576, ','.join(device_list)) , printall = printall)
        if not partial_result: result = False
        time.sleep(1)
    ### SECURITY REASONS ###
    os.environ['SSHPASS'] = '-'
    return result

###############################################################################

def do_scp_one_file_to_more_devices(true_sw_release_file_on_server = None, \
    device_list = None, USERNAME = None, PASSWORD = None , drive_string = None, \
    printall = None):
    if true_sw_release_file_on_server and len(device_list)>0:
        os.environ['SSHPASS'] = PASSWORD
        directory,dev_dir,file,md5,fsize = true_sw_release_file_on_server
        cp_cmd_list = []
        ### ONLY 1 SCP CONNECTION PER ROUTER ###
        for device in device_list:
            local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s 1>/dev/null 2>/dev/null &' \
                % (os.path.join(directory, file), USERNAME, device, \
                '%s%s' % (drive_string, os.path.join(dev_dir, file)))
            os.system(local_command)
            CGI_CLI.uprint('scp start file %s, (file size %.2fMB) to device %s' % \
                (file, float(fsize)/1048576, device))
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
    return None

###############################################################################

def do_sftp_command(USERNAME = None, PASSWORD = None, device = None,\
    local_file = None, device_file = None , printall = None):
    if USERNAME and PASSWORD and local_file and device_file:
        os.environ['SSHPASS'] = PASSWORD
        if not printall: CGI_CLI.uprint(' copying %s    ' % (device_file), no_newlines = True)

        local_path, forget_it = os.path.split(local_file)
        remote_path, filename = os.path.split(device_file)

        local_command = '''cd %s
sshpass -e sftp -oStrictHostKeyChecking=no %s@%s << !
progress
cd %s
put %s | zenity --progress --auto-close
bye
!
''' % (local_path, USERNAME, device, remote_path, filename)

        sftp_result = LCMD.run_command(cmd_line = local_command,
            printall = printall, chunked = True)
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
        return sftp_result
    else: return str()

sftp_sx1 = '''
sftp -o StrictHostKeyChecking=no  user@ftpsite.com << !
 progress
 cd offload
 put /media/*/*.tgz |zenity --progress --auto-close
 bye
'''

sftp_ex2 = '''
export SSHPASS=your-password-here
sshpass -e sftp -oBatchMode=no -b - sftp-user@remote-host << !
   cd incoming
   put your-log-file.log
   bye
!
'''

##############################################################################

def get_existing_sw_release_list(brand_subdir = None, type_subdir = None):
    sw_release_list, sw_release_list_raw, default_sw_release = [], [], str()

    if brand_subdir and type_subdir:
        ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
        LOCAL_SW_SUBTYPE_DIR = os.path.abspath(os.path.join(os.sep,'home',\
            'tftpboot',brand_subdir, type_subdir))
        try:
            sw_release_list_raw = [ str(subdir) for subdir in os.listdir(LOCAL_SW_SUBTYPE_DIR) ]
        except: pass
        for release in sw_release_list_raw:
            try:
                ### TRICK:DIRECTORY (with or without dots) MUST BE A NUMBER ###
                if os.path.isdir(os.path.join(LOCAL_SW_SUBTYPE_DIR,release)):
                    forget_it = int(release.replace('.',''))
                    sw_release_list.append(release)
                ### MAYBE DIRECTORIES ARE NOT DONE, SO CHECK FILES ###
                elif os.path.isfile(os.path.join(LOCAL_SW_SUBTYPE_DIR,release)):
                    for actual_file_type_with_subdir in sw_file_types_list:
                        actual_file_type_subdir, actual_file_name = os.path.split(actual_file_type_with_subdir)
                        ### PROBLEM ARE '*' IN FILE NAME ###
                        for part_of_name in actual_file_name.split('*'):
                            if part_of_name.upper() in release.upper():
                                sw_release_list.append(release)
            except: pass
        if len(sw_release_list) > 0:
            sw_release_set = set(sw_release_list)
            del sw_release_list
            sw_release_list = list(sw_release_set)
            del sw_release_set
            sw_release_list.sort(reverse = True)
            default_sw_release = sw_release_list[0]
    return sw_release_list, default_sw_release

##############################################################################

def does_directory_exist_by_ls_l(directory, printall = None):
    ### BUG: os.path.exists RETURNS ALLWAYS FALSE, SO I USE OS ls -l ######
    ls_all_result = LCMD.run_commands({'unix':['ls -l %s' % (directory)]}, printall = printall)
    if 'No such file or directory' in ls_all_result[0] \
        or not 'total ' in ls_all_result[0]:
        return False
    return True

##############################################################################

def get_local_subdirectories(brand_raw = None, type_raw = None):
    brand_subdir, type_subdir_on_server, file_types = str(), str(), []
    type_subdir_on_device = str()
    if brand_raw and type_raw:
        brand_subdir = brand_raw.upper()
        if 'ASR9K' in type_raw.upper():
            type_subdir_on_server = 'ASR9K'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
        elif 'NCS' in type_raw.upper():
            type_subdir_on_server = 'NCS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'ASR1001' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1001X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1001x*.bin','asr100*.pkg','ROMMON/*.pkg']
        elif 'ASR1002-X' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1002x*.bin','asr100*.pkg','ROMMON/*.pkg']
        elif 'ASR1002-HX' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002HX/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr100*.bin','asr100*.pkg','ROMMON/*.pkg']
        elif 'CRS' in type_raw.upper():
            type_subdir_on_server = 'CRS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'C29' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            file_types = ['c2900*.bin']
        elif '2901' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            file_types = ['c2900*.bin']
        elif 'C35' in type_raw.upper():
            type_subdir_on_server = 'C3500'
            file_types = ['c35*.bin']
        elif 'C36' in type_raw.upper():
            type_subdir_on_server = 'C3600'
            file_types = ['c36*.bin']
        elif 'C37' in type_raw.upper():
            type_subdir_on_server = 'C3700'
            file_types = ['c37*.bin']
        elif 'C38' in type_raw.upper():
            type_subdir_on_server = 'C3800'
            file_types = ['c38*.bin']
        elif 'ISR43' in type_raw.upper():
            type_subdir_on_server = 'C4321'
            file_types = ['isr43*.bin']
        elif 'C45' in type_raw.upper():
            type_subdir_on_server = 'C4500'
            file_types = ['cat45*.bin']
        elif 'MX480' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            file_types = ['junos*.img.gz', '*.tgz']
        elif 'NE40' in type_raw.upper():
            type_subdir_on_server = 'V8R10'
            file_types = []
    return brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types

##############################################################################

def does_run_scp_processes(my_pid_only = None, printall = None):
    scp_list = []
    split_string = 'scp -v -o StrictHostKeyChecking=no'
    #my_ps_result = LCMD.run_commands({'unix':["ps -ef | grep `whoami`"]},
    #    printall = printall)
    my_ps_result = LCMD.run_commands({'unix':["ps -ef"]},
        printall = printall)
    if my_ps_result:
        for line in str(my_ps_result[0]).splitlines():
            if split_string in line and not 'sshpass' in line:
                try:
                    files_string = line.split(split_string)[1].strip()
                    server_file = files_string.split()[0]
                    device_user = files_string.split()[1].split('@')[0]
                    device = files_string.split()[1].split('@')[1].split(':')[0]
                    device_file = files_string.split()[1].split(device+':/')[1]
                    pid = line.split()[1]
                    ppid = line.split()[2]
                    scp_list.append([server_file, device_file, device, device_user, pid, ppid])
                except: pass
    return scp_list

##############################################################################

def does_run_script_processes(my_pid_only = None, printall = None):
    running_pid_list = []
    try:
        split_string = sys.argv[0].split('/')[-1]
    except: split_string = None
    my_pid = str(os.getpid())
    my_ps_result = LCMD.run_commands({'unix':["ps -ef | grep -v grep"]},
        printall = printall)
    if my_ps_result:
        for line in str(my_ps_result[0]).splitlines():
            if split_string and split_string in line:
                try:
                    if my_pid != line.split()[1]:
                        running_pid_list.append(line.split()[1])
                        CGI_CLI.uprint('WARNING: Running %s process PID = %s !' % \
                            (split_string, line.split()[1]), tag = 'h2', color = 'magenta')
                except: pass
    return running_pid_list

###############################################################################

def check_percentage_of_copied_files(scp_list = [], USERNAME = None, \
    PASSWORD = None, printall = None):
    problem_to_connect_list = []
    for server_file, device_file, device, device_user, pid, ppid in scp_list:
        if device:
            time.sleep(2)
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, logfilename = None, silent_fail = True)
            if RCMD.ssh_connection:
                dir_device_cmd = {
                    'cisco_ios':['dir %s' % (device_file)],
                    'cisco_xr':['dir %s' % (device_file)],
                    'juniper':[],
                    'huawei':[]
                }
                dir_one_output = RCMD.run_commands(dir_device_cmd, printall = printall)
                CGI_CLI.uprint('\n')
                device_filesize_in_bytes = 0
                if RCMD.router_type == 'cisco_xr':
                    ### dir file gets output without 'harddisk:/'!!! ###
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split(':/')[1] in line:
                                try: device_filesize_in_bytes = float(line.split()[3])
                                except: pass
                        except: pass
                if RCMD.router_type == 'cisco_ios':
                    ### dir file gets output without any path ###
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split('/')[-1] in line:
                                try: device_filesize_in_bytes = float(line.split()[2])
                                except: pass
                        except: pass
                server_filesize_in_bytes = float(os.stat(server_file).st_size)
                CGI_CLI.uprint('Device %s file %s    %.2f%% copied.' % (device, device_file, \
                    float(100*device_filesize_in_bytes/server_filesize_in_bytes)), color = 'blue')
                RCMD.disconnect()
                time.sleep(2)
            else:
                CGI_CLI.uprint('Device %s file %s still copying...' % (device, device_file) , color = 'blue')
                problem_to_connect_list.append(device)
    return problem_to_connect_list
    
##############################################################################

def check_files_on_devices(device_list = None, true_sw_release_files_on_server = None, \
    USERNAME = None, PASSWORD = None, logfilename = None, printall = None):
    all_files_on_all_devices_ok = None
    needed_to_copy_files_per_device_list = []
    for device in device_list:
        if device:
            CGI_CLI.uprint('\nDevice %s checks:\n' % (device), tag = 'h2', color = 'blue')
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, logfilename = logfilename)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)

            ### DEVICE DRIVE STRING ###############################################
            drive_string = str()
            if RCMD.router_type == 'cisco_xr': drive_string = 'harddisk:'
            if RCMD.router_type == 'cisco_ios': drive_string = 'bootflash:'

            ### CHECK FILE(S) AND MD5(S) FIRST ################################
            CGI_CLI.uprint('checking existing device file(s) and md5(s)', \
                no_newlines = None if printall else True)
            xr_md5_cmds, xe_md5_cmds = [], []
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                xr_md5_cmds.append('show md5 file /%s%s' % (drive_string, os.path.join(dev_dir, file)))
                xe_md5_cmds.append('verify /md5 %s%s' % (drive_string, os.path.join(dev_dir, file)))
            rcmd_md5_outputs = RCMD.run_commands({'cisco_ios':xe_md5_cmds,'cisco_xr':xr_md5_cmds}, printall = printall)
            for files_list,rcmd_md5_output in zip(true_sw_release_files_on_server,rcmd_md5_outputs):
                directory, dev_dir, file, md5, fsize = files_list
                find_list = re.findall(r'[0-9a-fA-F]{32}', rcmd_md5_output.strip())
                if len(find_list) == 1:
                    md5_on_device = find_list[0]
                    if md5_on_device == md5:
                        md5_ok = True

            ### SHOW DEVICE DIRECTORY #########################################
            redundant_dev_dir_list = [ dev_dir for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server ]
            dev_dir_set = set(redundant_dev_dir_list)
            unique_device_directory_list = list(dev_dir_set)
            xe_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) for dev_dir in unique_device_directory_list ]
            xr_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) for dev_dir in unique_device_directory_list ]
            dir_device_cmds = {
                'cisco_ios':xe_device_dir_list,
                'cisco_xr':xr_device_dir_list,
                'juniper':[],
                'huawei':[]
            }
            rcmd_dir_outputs = RCMD.run_commands(dir_device_cmds, printall = printall)
            CGI_CLI.uprint('\n')
            all_md5_ok, all_files_per_device_ok = None, None
            missing_or_bad_files_per_device = []
            for unique_dir,unique_dir_outputs in zip(unique_device_directory_list,rcmd_dir_outputs):
                all_md5_ok, all_files_per_device_ok = True, True
                for files_list,rcmd_md5_output in zip(true_sw_release_files_on_server,rcmd_md5_outputs):
                    directory, dev_dir, file, md5, fsize = files_list
                    if unique_dir == dev_dir:
                        file_found_on_device = False
                        for line in unique_dir_outputs.splitlines():
                            try: possible_file_name = line.split()[-1].strip()
                            except: possible_file_name = str()
                            if file == possible_file_name: file_found_on_device = True
                        if file_found_on_device and md5_ok: pass
                        else: missing_or_bad_files_per_device.append([directory, dev_dir, file, md5, fsize])                     
            needed_to_copy_files_per_device_list.append([device,missing_or_bad_files_per_device])
            time.sleep(2)
    ### PRINT NEEDED FILES TO COPY ############################################
    at_least_some_files_need_to_copy = None
    for device,missing_or_bad_files_per_device in needed_to_copy_files_per_device_list:
        if len(missing_or_bad_files_per_device) != 0: 
            at_least_some_files_need_to_copy = True
    if at_least_some_files_need_to_copy:
        if CGI_CLI.data.get('check_device_sw_files_only'):
            CGI_CLI.uprint('Device    Checked_file:', tag = 'h2', color = 'red')    
        else:    
            CGI_CLI.uprint('Device    File_to_copy:', tag = 'h2', color = 'blue')
    else: 
        CGI_CLI.uprint('Sw release %s file(s) on devices %s - CHECK OK.' % \
            (sw_release, ', '.join(device_list)), tag = 'h1', color='green')
        all_files_on_all_devices_ok = True    
        ### CHECK IF EXIT OR NOT ##############################################    
        if CGI_CLI.data.get('backup_configs_to_device_disk') \
            or CGI_CLI.data.get('delete_device_sw_files_on_end'): pass       
        else: sys.exit(0)    
    for device,missing_or_bad_files_per_device in needed_to_copy_files_per_device_list:
        for directory, dev_dir, file, md5, fsize in missing_or_bad_files_per_device:
            if CGI_CLI.data.get('check_device_sw_files_only'):
                CGI_CLI.uprint('%s    %s' % \
                    (device,drive_string+os.path.join(dev_dir, file)), color = 'red')
            else:    
                CGI_CLI.uprint('%s    %s' % \
                    (device,drive_string+os.path.join(dev_dir, file)), color = 'blue')
    if not all_files_on_all_devices_ok and CGI_CLI.data.get('check_device_sw_files_only'): 
        CGI_CLI.uprint('SW RELEASE FILES - CHECK FAILED!' , tag = 'h1', color = 'red')
        sys.exit(0)
    return all_files_on_all_devices_ok, needed_to_copy_files_per_device_list     


##############################################################################
#
# def BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)
logging.raiseExceptions=False
USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True)
printall = CGI_CLI.data.get("printall")
if printall: CGI_CLI.print_args()

##############################################################################

CGI_CLI.uprint('ROUTER SW UPGRADE TOOL (v.%s)' % (CGI_CLI.VERSION()), tag = 'h1', color = 'blue')
CGI_CLI.uprint('PID=%s ' % (os.getpid()), color = 'blue')

does_run_script_processes()

scp_list = does_run_scp_processes(printall = False)
if len(scp_list)>0:
    CGI_CLI.uprint('WARNING: Running scp copy...', tag = 'h2', color = 'magenta')
    for server_file, device_file, device, device_user, pid, ppid in scp_list:
        if device:
            CGI_CLI.uprint('USER=%s, DEVICE=%s, FILE=%s, COPYING_TO=%s, PID=%s, PPID=%s' % \
                (device_user, device, server_file, device_file, pid, ppid), color = 'magenta')

##############################################################################


### def GLOBAL CONSTANTS #####################################################
device_expected_GB_free = 0

SCRIPT_ACTIONS_LIST = [
#'copy_tar_files','do_sw_upgrade',
]

active_menu_list, active_menu = [ None,'select_router_type','select_routers','copy_to_routers'], 0

asr1k_detection_string = 'CSR1000'
asr9k_detection_string = 'ASR9K|IOS-XRv 9000'

### GLOBAL VARIABLES ##########################################################

device_free_space = 0
SCRIPT_ACTION = None
ACTION_ITEM_FOUND = None
type_subdir = str()
remote_sw_release_dir_exists = None
total_size_of_files_in_bytes = 0
device_list = []
device_types = []
true_sw_release_files_on_server = []
needed_to_copy_files_per_device_list = []

###############################################################################
devices_string = CGI_CLI.data.get("device",str())
if devices_string:
    if ',' in devices_string:
        device_list = [ dev_mix_case.upper() for dev_mix_case in devices_string.split(',') ]
    else: device_list = [devices_string.upper()]

### GET sw_release FROM cli ###################################################
sw_release = CGI_CLI.data.get('sw_release',str())
try: device_expected_GB_free = float(CGI_CLI.data.get('device_disk_free_GB',device_expected_GB_free))
except: pass
iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()
if CGI_CLI.cgi_active and not (USERNAME and PASSWORD):
    if iptac_server == 'iptac5': USERNAME, PASSWORD = 'iptac', 'paiiUNDO'

### GENERATE selected_sw_file_types_list ######################################
selected_sw_file_types_list = []
selected_files_types_string = '_file(s)'
for key in CGI_CLI.data.keys():
    try: value = str(key)
    except: value = str()
    if selected_files_types_string in value:
        selected_sw_file_types_list.append(value.replace(selected_files_types_string,str()))
        active_menu = 3

### GET sw_release FROM CGI ###################################################
selected_release_string = 'soft_release'
if not sw_release:
    for key in CGI_CLI.data.keys():
        try: value = CGI_CLI.data.get(key)
        except: value = None
        if selected_release_string == key and value:
            sw_release = value
            active_menu = 3
            break

### def SQL INIT ##############################################################
sql_inst = sql_interface(host='localhost', user='cfgbuilder', \
    password='cfgbuildergetdata', database='rtr_configuration')

### SQL READ ALL HARDVARE TYPES ###############################################
device_types_list_in_list = sql_inst.sql_read_table_records( \
    select_string = 'hardware',\
    from_string = 'oti_all_table',\
    order_by = 'hardware')

### SQL READ ALL DEVICES IN NETWORK ###########################################
data = collections.OrderedDict()
data['oti_all_table'] = sql_inst.sql_read_records_to_dict_list( \
    select_string = 'vendor, hardware, software, rtr_name, network',\
    from_string = 'oti_all_table',\
    order_by = 'vendor, hardware, rtr_name ASC')


### DO SORTED DEVICE TYPE LIST ################################################
if device_types_list_in_list:
    device_types_set = set([ dev_type[0] for dev_type in device_types_list_in_list ])
    device_types = list(device_types_set)
    device_types.sort()

### FIND SELECTED DEVICE TYPE #################################################
router_type_id_string, router_id_string = "router_type", '__'
selected_device_type = str()
for key in CGI_CLI.data.keys():
    ### DEVICE NAME IS IN 'router_type__VALUE' ###
    try: value = CGI_CLI.data.get(key)
    except: value = None
    if router_type_id_string == key and value:
        selected_device_type = value.replace('_','')
        active_menu = 2

### GAIN SUBDIRS FROM OTI_ALL_TABLE WHERE HARDWARE = SELECTED_DEVICE_TYPE ###
brand_raw, type_raw , brand_subdir, type_subdir = str(), str() , str(), str()
sw_release_list, default_sw_release, sw_file_types_list = [], str(), []
type_subdir_on_device, sw_release_list_raw = str(), []
if selected_device_type:
    for router_dict in data['oti_all_table']:
        if selected_device_type == router_dict.get('hardware',str()):
            brand_raw = router_dict.get('vendor',str())
            type_raw  = router_dict.get('hardware',str())
            brand_subdir, type_subdir,type_subdir_on_device, sw_file_types_list = \
                get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)
            break

    ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
    sw_release_list, default_sw_release = get_existing_sw_release_list(brand_subdir, type_subdir)


### ROUTER-TYPE MENU PART #####################################################
table_rows = 5
counter = 0
router_type_menu_list = ['<h2>Select router type:</h2>',
    '<div align="left">', '<table style="width:70%">']
for router_type in device_types:
    if counter == 0: router_type_menu_list.append('<tr>')
    router_type_menu_list.append('<td>')
    router_type_menu_list.append({'radio':'%s__%s' % (router_type_id_string,router_type)})
    counter += 1
    router_type_menu_list.append('</td>')
    if counter + 1 > table_rows:
        router_type_menu_list.append('</tr>')
        counter = 0
if counter != 0: router_type_menu_list.append('</tr>')
router_type_menu_list.append('</table>')
router_type_menu_list.append('</div>')

### ROUTER MENU PART ##########################################################
table_rows = 5
counter = 0
router_menu_list = ['<h2>%s routers:</h2>'% (selected_device_type),
    '<div align="left">', '<table style="width:70%">']
for router_dict in data['oti_all_table']:
    if selected_device_type and \
        selected_device_type in router_dict.get('hardware',str()):
        if counter == 0: router_menu_list.append('<tr>')
        router_menu_list.append('<td>')
        router_menu_list.append({'checkbox':'%s%s' % \
            (router_id_string,router_dict.get('rtr_name',str()))})
        counter += 1
        router_menu_list.append('</td>')
        if counter + 1 > table_rows:
            router_menu_list.append('</tr>')
            counter = 0
if counter != 0: router_menu_list.append('</tr>')
router_menu_list.append('</table>')
router_menu_list.append('</div>')

### APPEND DEVICE LIST ########################################################
for key in CGI_CLI.data.keys():
    ### DEVICE NAME IS IN '__KEY' ###
    try: value = str(key)
    except: value = str()
    if router_id_string in value: device_list.append(value.replace('_',''))

### GAIN VENDOR + HARDWARE FROM DEVICE LIST "AGAIN" ###########################
if len(device_list)>0:
    for router_dict in data['oti_all_table']:
        if device_list[0] and device_list[0].upper() == router_dict.get('rtr_name',str()).upper():
            brand_raw = router_dict.get('vendor',str())
            type_raw  = router_dict.get('hardware',str())
            brand_subdir, type_subdir, type_subdir_on_device, sw_file_types_list = \
                get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)
            if printall: CGI_CLI.uprint('READ_FROM_DB: [router=%s, vendor=%s, hardware=%s]' % \
                (device_list[0], brand_raw, type_raw))
            break

    ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
    if len(sw_release_list) == 9:
        sw_release_list, default_sw_release = get_existing_sw_release_list(brand_subdir, type_subdir)

###############################################################################




### SHOW HTML MENU SHOWS ONLY IN CGI/HTML MODE ################################
if CGI_CLI.cgi_active and (not CGI_CLI.submit_form or active_menu == 2):
    ### DISPLAY ROUTER-TYPE MENU ##############################################
    if active_menu == 0:
        main_menu_list = router_type_menu_list + ['<br/>', {'checkbox':'printall'} ]
    ### def DISPLAY SELECT ROUTER MENU ########################################
    elif active_menu == 2:
        main_menu_list = router_menu_list + \
        ['<p>Additional device(s) (optional) [list separator=,]:</p>',\
        {'text':'device'}, '<br/>', \
        '<h3>SW RELEASE (required) [default=%s]:</h3>' % (default_sw_release)]

        if len(sw_release_list) > 0:
            release_sw_release_list = [ "%s__%s" % (selected_release_string, release) for release in sw_release_list ]
            main_menu_list.append({'radio':release_sw_release_list})
        else:
            main_menu_list.append('<h3 style="color:red">NO SW RELEASE VERSIONS AVAILABLE on server %s!</h3>' % (iptac_server))

        main_menu_list.append('<h3>FILES TO COPY (required):</h3>')
        for sw_file in sw_file_types_list:
            main_menu_list.append({'checkbox':sw_file + '_file(s)'})
            main_menu_list.append('<br/>')
        if len(sw_file_types_list) == 0:
            main_menu_list.append('<h3 style="color:red">NO FILE TYPES SPECIFIED!</h3>')

        main_menu_list += ['<h3>DEVICE DISK FREE (optional) [default &gt %.2f GB]:</h3>'%(device_expected_GB_free),\
        {'text':'device_disk_free_GB'}, '<br/>',\
        '<h3>LDAP authentication (required):</h3>',{'text':'username'}, \
        '<br/>', {'password':'password'}, '<br/>','<br/>']

        if len(SCRIPT_ACTIONS_LIST)>0: main_menu_list.append({'radio':[ 'script_action__' + action for action in SCRIPT_ACTIONS_LIST ]})

        main_menu_list += ['<br/>','<h3>Options:</h3>', \
            {'checkbox':'check_device_sw_files_only'},'<br/>',\
            #{'checkbox':'slow_scp_mode'},'<br/>',\
            {'checkbox':'display_scp_percentage_only'},'<br/>',\
            #{'checkbox':'force_rewrite_sw_files_on_device'},'<br/>',\
            {'checkbox':'backup_configs_to_device_disk'},'<br/>',\
            {'checkbox':'delete_device_sw_files_on_end'},'<br/>',\
            '<br/>', {'checkbox':'printall'}]

    CGI_CLI.formprint( main_menu_list + ['<br/>','<br/>'], submit_button = 'OK', \
        pyfile = None, tag = None, color = None , list_separator = '&emsp;')

    ### SHOW HTML MENU AND EXIT ###############################################
    sys.exit(0)
else:
    ### READ SCRIPT ACTION ###
    for item in SCRIPT_ACTIONS_LIST:
        if CGI_CLI.data.get(item):
            SCRIPT_ACTION = copy.deepcopy(item)
            break
    else:
        if CGI_CLI.data.get("script_action"):
            SCRIPT_ACTION = CGI_CLI.data.get("script_action")

### def DISPLAY PERCENTAGE OF SCP #############################################
if CGI_CLI.data.get('display_scp_percentage_only'):
    scp_list = does_run_scp_processes(printall = False)
    if len(scp_list)>0 and USERNAME and PASSWORD:
        check_percentage_of_copied_files(scp_list, USERNAME, PASSWORD, printall)
    sys.exit(0)

### SET DEFAULT (HIGHEST) SW RELEASE IF NOT SET ###############################
if not sw_release and default_sw_release: sw_release = default_sw_release

### def LOGFILENAME GENERATION ################################################
logfilename = generate_logfilename(prefix = ('_'.join(device_list)).upper(), \
    USERNAME = USERNAME, suffix = str(SCRIPT_ACTION) + '.log')
logfilename = None

### def PRINT BASIC INFO ##########################################################
CGI_CLI.uprint('server = %s' % (iptac_server))
if len(device_list) > 0: CGI_CLI.uprint('device(s) = %s' % (', '.join(device_list)))
if sw_release: CGI_CLI.uprint('sw release = %s' % (sw_release))
if device_expected_GB_free: 
    CGI_CLI.uprint('expected disk free = %s GB' % (device_expected_GB_free))
if len(selected_sw_file_types_list)>0: 
    CGI_CLI.uprint('sw file types = %s' % (', '.join(selected_sw_file_types_list) ))
if logfilename: CGI_CLI.uprint('logfile=%s' % (logfilename))    

###############################################################################
if CGI_CLI.data.get('sw_files'):
    ft_string = CGI_CLI.data.get('sw_files')
    ft_list = ft_string.split(',') if ',' in ft_string else [ft_string]

    for ft_item in ft_list:
        selected_sw_file_types_list += [ filetype for filetype in sw_file_types_list if ft_item in filetype ]

###############################################################################


if len(selected_sw_file_types_list) == 0:
    CGI_CLI.uprint('PLEASE SPECIFY SW FILE TYPE(S) TO COPY.', tag = 'h2', color = 'red')
    sys.exit(0)

if not sw_release:
    CGI_CLI.uprint('PLEASE SPECIFY SW_RELEASE.', tag = 'h2',color = 'red')
    sys.exit(0)

if len(device_list) == 0:
    CGI_CLI.uprint('DEVICE NAME(S) NOT INSERTED!', tag = 'h2', color = 'red')
    sys.exit(0)

###############################################################################

if type_subdir and brand_subdir and sw_release:
    CGI_CLI.uprint('Server %s checks:\n' % (iptac_server), tag = 'h2', color = 'blue')

    ### def CHECK LOCAL SW DIRECTORIES ########################################
    directory_list = []
    for actual_file_type in selected_sw_file_types_list:
        actual_file_type_subdir, forget_it = os.path.split(actual_file_type)

        dir_sw_version_subdir = os.path.abspath(os.path.join(os.sep,'home',\
            'tftpboot',brand_subdir, type_subdir, sw_release.replace('.',''), actual_file_type_subdir)).strip()

        dir_sw_version_subdir_dotted = os.path.abspath(os.path.join(os.sep,'home',\
            'tftpboot',brand_subdir, type_subdir, sw_release, actual_file_type_subdir)).strip()

        dir_without_sw_version_subdir = os.path.abspath(os.path.join(os.sep,'home',\
            'tftpboot',brand_subdir, type_subdir, actual_file_type_subdir)).strip()

        ### BUG: os.path.exists RETURNS ALLWAYS FALSE, SO I USE OS ls -l ######
        dir_sw_version_subdir_exists = does_directory_exist_by_ls_l(dir_sw_version_subdir, printall = printall)
        dir_sw_version_subdir_dotted_exists = does_directory_exist_by_ls_l(dir_sw_version_subdir_dotted, printall = printall)
        dir_without_sw_version_subdir_exists = does_directory_exist_by_ls_l(dir_without_sw_version_subdir, printall = printall)

        if not dir_sw_version_subdir_exists and not dir_without_sw_version_subdir_exists:
            CGI_CLI.uprint('Path for %s NOT FOUND!' % (actual_file_type), color = 'red')
            sys.exit(0)

        if dir_sw_version_subdir_exists: directory_list.append(dir_sw_version_subdir)
        elif dir_sw_version_subdir_dotted_exists: directory_list.append(dir_sw_version_subdir_dotted)
        elif dir_without_sw_version_subdir_exists: directory_list.append(dir_without_sw_version_subdir)

    ### CHECK LOCAL SERVER FILES EXISTENCY ################################
    for directory,actual_file_type in zip(directory_list,selected_sw_file_types_list):
        forget_it, actual_file_name = os.path.split(actual_file_type)
        actual_file_type_subdir, forget_it = os.path.split(actual_file_type)
        if sw_release in directory:
            device_directory = os.path.abspath(os.path.join(os.sep, \
                type_subdir_on_device, sw_release.replace('.',''), actual_file_type_subdir))
        else:
            ### FILES ON DEVICE WILL BE IN DIRECTORY WITHOUT SW_RELEASE IF SW_RELEASE SUDBIR DOES NOT EXISTS ON SERVER, BECAUSE THEN SW_RELEASE IS FILENAME ###
            device_directory = os.path.abspath(os.path.join(os.sep,type_subdir_on_device, actual_file_type_subdir))
        local_results = LCMD.run_commands({'unix':['ls -l %s' % (directory)]}, printall = printall)
        no_such_files_in_directory = True
        for line in local_results[0].splitlines():
            ### PROBLEM ARE '*' IN FILE NAME ###
            all_file_name_parts_found = True
            for part_of_name in actual_file_name.split('*'):
                if part_of_name.upper() in line.upper(): pass
                else: all_file_name_parts_found = False
            if all_file_name_parts_found:
                no_such_files_in_directory = False
                true_file_name = line.split()[-1].strip()
                local_oti_checkum_string = LCMD.run_commands({'unix':['md5sum %s' % \
                    (os.path.join(directory,true_file_name))]}, printall = printall)
                md5_sum = local_oti_checkum_string[0].split()[0].strip()
                filesize_in_bytes = os.stat(os.path.join(directory,true_file_name)).st_size
                ### MAKE TRUE FILE LIST ###
                true_sw_release_files_on_server.append([directory,device_directory,true_file_name,md5_sum,filesize_in_bytes])
        if no_such_files_in_directory:
            CGI_CLI.uprint('%s file(s) NOT FOUND in %s!' % (actual_file_name,directory), color = 'red')
            sys.exit(0)
    CGI_CLI.uprint('File(s),    md5 checksum(s),    device folder(s),    filesize:\n%s' % \
        ('\n'.join([ '%s/%s    %s    %s    %.2fMB' % (directory,file,md5,dev_dir,float(fsize)/1048576) for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server ])))

    ### CALCULATE NEEDED DISK SPACE ###########################################
    for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server:
        total_size_of_files_in_bytes += fsize
    CGI_CLI.uprint('\ndisk space needed = %.2F MB' % (float(total_size_of_files_in_bytes)/1048576), color = 'blue')

### def MAKE ALL SUB-DIRECTORIES ONE BY ONE ###########################
redundant_dev_dir_list = [ dev_dir for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server ]
dev_dir_set = set(redundant_dev_dir_list)
unique_device_directory_list = list(dev_dir_set)

### CHECK EXISTING FILES ON DEVICES ###########################################
all_files_on_all_devices_ok, needed_to_copy_files_per_device_list = \
    check_files_on_devices(device_list = device_list, \
    true_sw_release_files_on_server = true_sw_release_files_on_server, \
    USERNAME = USERNAME, PASSWORD = PASSWORD, logfilename = logfilename, \
    printall = printall)



if CGI_CLI.data.get('check_device_sw_files_only'): pass
elif not all_files_on_all_devices_ok:

    ### def CHECK DISK SPACE ON DEVICE ############################################
    for device in device_list:
        if device:
            CGI_CLI.uprint('\nDevice %s disk space checks:\n' % (device), tag = 'h2', color = 'blue')
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, logfilename = logfilename)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)

            ### DEVICE DRIVE STRING ###############################################
            drive_string = str()
            if RCMD.router_type == 'cisco_xr': drive_string = 'harddisk:'
            if RCMD.router_type == 'cisco_ios': drive_string = 'bootflash:'
            
            check_disk_space_cmds = {
                ### some ios = enable, ask password, 'show bootflash:' , exit
                'cisco_ios':[' ','show bootflash:',' ','show version | in (%s)' % (asr1k_detection_string)],
                'cisco_xr':['show filesystem',
                    'show version | in "%s"' % (asr9k_detection_string),
                    ],
                'juniper':['show system storage'],
                'huawei':['display device | include PhyDisk','display disk information']
            }
            CGI_CLI.uprint('checking disk space', \
                no_newlines = None if printall else True)
            rcmd_check_disk_space_outputs = RCMD.run_commands(check_disk_space_cmds)
            CGI_CLI.uprint('\n')

            if RCMD.router_type == 'cisco_ios':
                try: device_free_space = float(rcmd_check_disk_space_outputs[1].\
                         split('bytes available')[0].splitlines()[-1].strip())
                except: pass
            elif RCMD.router_type == 'cisco_xr':
                try: device_free_space = float(rcmd_check_disk_space_outputs[0].\
                         split('harddisk:')[0].splitlines()[-1].split()[1].strip())
                except: pass
            elif RCMD.router_type == 'juniper': pass
            elif RCMD.router_type == 'huawei': pass

            CGI_CLI.uprint('disk free space = %.2f MB' % (float(device_free_space)/1048576) , color = 'blue')

            ### SOME GB FREE EXPECTED (1MB=1048576, 1GB=1073741824) ###
            if device_free_space < (device_expected_GB_free * 1073741824):
                CGI_CLI.uprint('Disk space - CHECK FAIL!', color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)
            else: CGI_CLI.uprint('Disk space - CHECK OK.', color = 'green')

            xr_device_mkdir_list = []
            for dev_dir in unique_device_directory_list:
                up_path = str()
                for dev_sub_dir in dev_dir.split('/'):
                    if dev_sub_dir:
                        xr_device_mkdir_list.append('mkdir %s%s' % \
                            (drive_string, os.path.join(up_path,dev_sub_dir)))
                        xr_device_mkdir_list.append('\r\n')
                        up_path = os.path.join(up_path, dev_sub_dir)

            mkdir_device_cmds = {
                'cisco_ios':xr_device_mkdir_list,
                'cisco_xr':xr_device_mkdir_list,
                'juniper':[],
                'huawei':[]
            }
            CGI_CLI.uprint('making directories', \
                no_newlines = None if printall else True)
            forget_it = RCMD.run_commands(mkdir_device_cmds)
            CGI_CLI.uprint('\n')
            RCMD.disconnect()
            time.sleep(2)



    
### def FILE SCP COPYING ######################################################
if CGI_CLI.data.get('check_device_sw_files_only'): pass
elif not all_files_on_all_devices_ok:
    time.sleep(2)
    #CGI_CLI.uprint('Slow scp mode selected.', tag = 'h2', color = 'blue')
    scp_list = does_run_scp_processes(printall = False)
    for true_sw_release_file_on_server in true_sw_release_files_on_server:
        directory,dev_dir,file,md5,fsize = true_sw_release_file_on_server
        ### IF SCP_LIST IS VOID COPY ALL ###
        if len(scp_list) == 0:
            do_scp_one_file_to_more_devices(true_sw_release_file_on_server, device_list, \
                USERNAME, PASSWORD, drive_string = drive_string, printall = printall)
            time.sleep(3)
        ### IF SCP_LIST IS NOT VOID CHECK AND COPY ONLY NOT RUNNING ###
        for server_file, device_file, scp_device, device_user, pid, ppid in scp_list:
            CGI_CLI.uprint('%s=%s, %s=%s' %(scp_device, device_list, device_file, os.path.join(dev_dir, file)))
            if scp_device in device_list and device_file == os.path.join(dev_dir, file):
                CGI_CLI.uprint('FILE %s is already copying to device %s, ommiting new scp copying!' % \
                    (device_file, device))
            else:
                do_scp_one_file_to_more_devices(true_sw_release_file_on_server, device_list, \
                    USERNAME, PASSWORD, drive_string = drive_string, printall = printall)
                time.sleep(2)
        ### DO SCP LIST AGAIN AND WAIT TILL END OF YOUR SCP SESSIONS ###
        actual_scp_devices_in_scp_list = True
        scp_list = does_run_scp_processes(printall = False)
        while actual_scp_devices_in_scp_list:
            actual_scp_devices_in_scp_list = False
            scp_list = does_run_scp_processes(printall = False)
            for server_file, device_file, scp_device, device_user, pid, ppid in scp_list:
                if scp_device in device_list: actual_scp_devices_in_scp_list = True
            if len(scp_list) > 0:
                check_percentage_of_copied_files(scp_list, USERNAME, PASSWORD, printall)
            else: break
            time.sleep(5)


### def CONNECT TO DEVICE AGAIN ###############################################
if all_files_on_all_devices_ok: pass
else:
    time.sleep(3)
    ### CHECK EXISTING FILES ON DEVICES AGAIN #################################
    all_files_on_all_devices_ok, needed_to_copy_files_per_device_list = \
        check_files_on_devices(device_list = device_list, \
        true_sw_release_files_on_server = true_sw_release_files_on_server, \
        USERNAME = USERNAME, PASSWORD = PASSWORD, logfilename = logfilename, \
        printall = printall)

### def ADITIONAL DEVICE ACTIONS ##################################################
if CGI_CLI.data.get('backup_configs_to_device_disk') \
    or CGI_CLI.data.get('delete_device_sw_files_on_end'):
    for device in device_list:

        ### REMOTE DEVICE OPERATIONS ##############################################
        if device:
            CGI_CLI.uprint('\nFinal device %s actions:\n' % (device), tag = 'h2', color = 'blue')
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, logfilename = logfilename)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)

            ### DEVICE DRIVE STRING ###############################################
            drive_string = str()
            if RCMD.router_type == 'cisco_xr': drive_string = 'harddisk:'
            if RCMD.router_type == 'cisco_ios': drive_string = 'bootflash:'


            ### CHECK LOCAL SERVER AND DEVICE HDD FILES #######################
            if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                ### def BACKUP NORMAL AND ADMIN CONFIG ########################
                if CGI_CLI.data.get('backup_configs_to_device_disk'):
                    actual_date_string = time.strftime("%Y-%m%d-%H:%M",time.gmtime(time.time()))
                    backup_config_rcmds = {
                        'cisco_ios':[
                        'copy running-config %s%s-config.txt' % (drive_string, actual_date_string),
                        '\n',
                        ],
                        'cisco_xr':[
                        'copy running-config %s%s-config.txt' % (drive_string, actual_date_string),
                        '\n',
                        'admin',
                        'copy running-config %sadmin-%s-config.txt' %(drive_string, actual_date_string),
                        '\n',
                        'exit']
                    }
                    CGI_CLI.uprint('backup configs', no_newlines = \
                        None if printall else True)
                    forget_it = RCMD.run_commands(backup_config_rcmds, printall = printall)
                    CGI_CLI.uprint('\n')

                ### def DELETE TAR FILES ON END ###############################
                if CGI_CLI.data.get('delete_device_sw_files_on_end'):
                    del_files_cmds = {'cisco_xr':[],'cisco_ios':[]}

                    for unique_dir in unique_device_directory_list:
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                del_files_cmds['cisco_xr'].append( \
                                    'del /%s%s' % (drive_string, os.path.join(dev_dir, file)))
                                del_files_cmds['cisco_xr'].append('\n')
                                del_files_cmds['cisco_xr'].append('\n')

                                del_files_cmds['cisco_ios'].append( \
                                    'del %s%s' % (drive_string, os.path.join(dev_dir, file)))
                                del_files_cmds['cisco_ios'].append('\n')
                                del_files_cmds['cisco_ios'].append('\n')

                    CGI_CLI.uprint('deleting sw release files', no_newlines = \
                        None if printall else True)
                    forget_it = RCMD.run_commands(del_files_cmds, printall = printall)

                    ### CHECK FILES DELETION ##################################
                    check_dir_files_cmds = {'cisco_xr':[],'cisco_ios':[]}
                    for unique_dir in unique_device_directory_list:
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                check_dir_files_cmds['cisco_xr'].append( \
                                    'dir /%s%s' % (drive_string, dev_dir))

                                check_dir_files_cmds['cisco_ios'].append( \
                                    'dir %s%s' % (drive_string, dev_dir))
                    time.sleep(0.5)
                    dir_outputs_after_deletion = RCMD.run_commands(check_dir_files_cmds, \
                        printall = printall)
                    CGI_CLI.uprint('\n')
                    file_not_deleted = False
                    for unique_dir in unique_device_directory_list:
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                if file in dir_outputs_after_deletion[0]:
                                    CGI_CLI.uprint(file, color = 'red')
                                    CGI_CLI.uprint(dir_outputs_after_deletion[3], color = 'blue')
                                    file_not_deleted = True
                    if file_not_deleted: CGI_CLI.uprint('DELETE PROBLEM!', color = 'red')
                    else: CGI_CLI.uprint('Delete file(s) - CHECK OK.', color = 'green')

            ### DISCONNECT ####################################################
            RCMD.disconnect()

del sql_inst






