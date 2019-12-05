#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, traceback
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
                            help = "sw release number with or without dots, i.e. 653 or 6.5.3")
        parser.add_argument("--OTI_tar",
                            action = 'store_true', dest = "OTI.tar_file",
                            default = None,
                            help = "copy/check OTI.tar file")
        parser.add_argument("--SMU_tar",
                            action = 'store_true', dest = "SMU.tar_files",
                            default = None,
                            help = "copy/check SMU.tar files")
        parser.add_argument("--check_files_only",
                            action = 'store_true', dest = "check_device_sw_files_only",
                            default = None,
                            help = "check existing device sw release files only, do not copy new tar files")
        parser.add_argument("--backup_configs",
                            action = 'store_true', dest = "backup_configs_to_device_disk",
                            default = None,
                            help = "backup configs to device hdd")
        parser.add_argument("--force_rewrite",
                            action = 'store_true', dest = "force_rewrite_sw_files_on_device",
                            default = None,
                            help = "force rewrite sw release files on device disk")
        parser.add_argument("--delete_files",
                            action = 'store_true', dest = "delete_device_sw_files_on_end",
                            default = None,
                            help = "delete device sw release files on end after sw upgrade")
        # parser.add_argument("--sim",
                            # action = "store_true", dest = 'sim',
                            # default = None,
                            # help = "config simulation mode")
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
                    if isinstance(data_item.get('radio_script_action'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s %s'%\
                                ('script_action',radiobutton,radiobutton.replace('_',' '), \
                                list_separator if list_separator else str()))
                    elif isinstance(data_item.get('radio'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s %s'%\
                                (radiobutton,radiobutton,radiobutton.replace('_',' '), \
                                list_separator if list_separator else str()))
                    else:
                        CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                            (data_item.get('radio'),data_item.get('radio'),data_item.get('radio','').replace('_',' ')))
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
        do_not_final_print = None, commit_text = None):
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
            except Exception as e: CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
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
                    if 'CSR1000' in outputs: RCMD.router_version = 'ASR1K'
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
        chunked = None, timeout_sec = 500):
        os_output, cmd_list, timer_counter_100ms = str(), None, 0
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_line:
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line),\
                                 color = 'blue')
                LCMD.fp.write('LOCAL_COMMAND: ' + cmd_line + '\n')
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
                    if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line))
                    LCMD.fp.write('LOCAL_COMMAND: ' + cmd_line + '\n')
                    try: os_output = subprocess.check_output(str(cmd_line), stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                    except (subprocess.CalledProcessError) as e:
                        os_output = str(e.output.decode("utf-8"))
                        if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                        LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                    except:
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                        LCMD.fp.write(exc_text + '\n')
                    if os_output and printall: CGI_CLI.uprint(os_output)
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

def do_scp_command(USERNAME = None, PASSWORD = None, file_to_copy = None, \
    device_path = None ,local_path = None, printall = None):
    if USERNAME and PASSWORD and file_to_copy and device_path and local_path:
        os.environ['SSHPASS'] = PASSWORD
        device_file = '%s/%s' % (device_path, file_to_copy)
        local_file = os.path.join(local_path, file_to_copy)
        if not printall: CGI_CLI.uprint('  %s  ' % (file_to_copy), no_newlines = True)
        show_progress_string = ''
        local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s%s' \
            % (local_file, USERNAME, device, device_file, show_progress_string)
        scp_result = LCMD.run_command(cmd_line = local_command,
            printall = printall, chunked = True)
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
        return scp_result
    else: return str()

##############################################################################

def get_local_subdirectories(brand_raw = None, type_raw = None):
    brand_subdir, type_subdir, file_types = str(), str(), []
    if brand_raw and type_raw:
        brand_subdir = brand_raw.upper()
        if 'ASR9K' in type_raw.upper():
            type_subdir = 'ASR9K'
            file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
        elif 'NCS' in type_raw.upper():
            type_subdir = 'NCS'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'ASR1001' in type_raw.upper():
            type_subdir = 'ASR1K/ASR1001X/IOS_XE'
            file_types = ['asr1001x*.bin']
        elif 'ASR1002-X' in type_raw.upper():
            type_subdir = 'ASR1K/ASR1002X/IOS_XE'
            file_types = ['asr1002x*.bin']
        elif 'ASR1002-HX' in type_raw.upper():
            type_subdir = 'ASR1K/ASR1002HX/IOS_XE'
            file_types = ['asr100*.bin']
        elif 'CRS' in type_raw.upper():
            type_subdir = 'CRS'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'C29' in type_raw.upper():
            type_subdir = 'C2900'
            file_types = ['c2900*.bin']
        elif '2901' in type_raw.upper():
            type_subdir = 'C2900'
            file_types = ['c2900*.bin']
        elif 'C35' in type_raw.upper():
            type_subdir = 'C3500'
            file_types = ['c35*.bin']
        elif 'C36' in type_raw.upper():
            type_subdir = 'C3600'
            file_types = ['c36*.bin']
        elif 'C37' in type_raw.upper():
            type_subdir = 'C3700'
            file_types = ['c37*.bin']
        elif 'C38' in type_raw.upper():
            type_subdir = 'C3800'
            file_types = ['c38*.bin']
        elif 'ISR43' in type_raw.upper():
            type_subdir = 'C4321'
            file_types = ['isr43*.bin']
        elif 'C45' in type_raw.upper():
            type_subdir = 'C4500'
            file_types = ['cat45*.bin']
        elif 'MX480' in type_raw.upper():
            type_subdir = 'MX/MX480'
            file_types = ['junos*.img.gz']
        elif 'NE40' in type_raw.upper():
            type_subdir = 'V8R10'
            file_types = []
    return brand_subdir, type_subdir, file_types

##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)
USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True)
#CGI_CLI.print_args()
##############################################################################

device_expected_GB_free = 0.2

SCRIPT_ACTIONS_LIST = [
#'copy_tar_files','do_sw_upgrade',
]

active_menu_list, active_menu = [ None,'select_router_type','select_routers','copy_to_routers'], 0

##############################################################################

device_free_space = 0
SCRIPT_ACTION = None
ACTION_ITEM_FOUND = None
type_subdir = str()
remote_sw_release_dir_exists = None

asr1k_detection_string = 'CSR1000'
asr9k_detection_string = 'ASR9K|IOS-XRv 9000'

###############################################################################

device = CGI_CLI.data.get("device",None)
if device: device = device.upper()

### GET sw_release FROM cli ###################################################
sw_release = CGI_CLI.data.get('sw_release',str()).replace('.','')

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
selected_release_string = 'release_'
if not sw_release:
    for key in CGI_CLI.data.keys():
        try: value = str(key)
        except: value = str()
        if selected_release_string in value:
            sw_release = value.replace(selected_release_string,str())
            active_menu = 3
            break


### SQL INIT ##################################################################
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
device_types = []
if device_types_list_in_list:
    device_types_set = set([ dev_type[0] for dev_type in device_types_list_in_list ])
    device_types = list(device_types_set)
    device_types.sort()

### FIND SELECTED DEVICE TYPE #################################################
router_type_id_string, router_id_string = "___", '__'
selected_device_type = str()
for key in CGI_CLI.data.keys():
    ### DEVICE NAME IS IN '____KEY' ###
    try: value = str(key)
    except: value = str()
    if router_type_id_string in value:
        selected_device_type = value.replace('_','')
        active_menu = 2


### GAIN SUBDIRS FROM OTI_ALL_TABLE WHERE HARDWARE = SELECTED_DEVICE_TYPE ###
brand_raw, type_raw , brand_subdir, type_subdir = str(), str() , str(), str()
sw_release_list, default_sw_release, sw_file_types_list = [], str(), []
if selected_device_type:
    for router_dict in data['oti_all_table']:
        if selected_device_type == router_dict.get('hardware',str()):
            brand_raw = router_dict.get('vendor',str())
            type_raw  = router_dict.get('hardware',str())
            brand_subdir, type_subdir, sw_file_types_list = get_local_subdirectories(\
                brand_raw = brand_raw, type_raw = type_raw)
            break

    ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
    LOCAL_SW_SUBTYPE_DIR = os.path.abspath(os.path.join(os.sep,'home',\
        'tftpboot',brand_subdir, type_subdir))
    try:
        sw_release_list_raw = [ str(subdir) for subdir in os.listdir(LOCAL_SW_SUBTYPE_DIR) ]
    except: pass
    #except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']', color = 'magenta')
    ### TRICK = DIRECTORY (with or without dots) MUST BE A NUMBER ###
    for release in sw_release_list_raw:
        try:
            forget_it = int(release.replace('.',''))
            sw_release_list.append(release)
        except: pass
    if len(sw_release_list) > 0:
        sw_release_list.sort(reverse = True)
        default_sw_release = sw_release_list[0]


### ROUTER-TYPE MENU PART #####################################################
table_rows = 5
counter = 0
router_type_menu_list = ['<h2>Select router type:</h2>',
    '<div align="left">', '<table style="width:70%">']
for router_type in device_types:
    if counter == 0: router_type_menu_list.append('<tr>')
    router_type_menu_list.append('<td>')
    router_type_menu_list.append({'radio':'%s%s' % (router_type_id_string,router_type)})
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
device_list = []
for key in CGI_CLI.data.keys():
    ### DEVICE NAME IS IN '__KEY' ###
    try: value = str(key)
    except: value = str()
    if router_id_string in value: device_list.append(value.replace('_',''))
if device:
    if ',' in device:
        added_device_list = [ splitted_device.strip() for splitted_device in device.split(',') ]
        if len(added_device_list) > 0: device_list += added_device_list
    else: device_list.append(device)
del device

### GAIN VENDOR + HARDWARE FROM DEVICE LIST "AGAIN" ###########################
if len(device_list)>0:
    for router_dict in data['oti_all_table']:
        if device_list[0] and device_list[0].upper() == router_dict.get('rtr_name',str()).upper():
            brand_raw = router_dict.get('vendor',str())
            type_raw  = router_dict.get('hardware',str())
            brand_subdir, type_subdir, sw_file_types_list = get_local_subdirectories(\
                brand_raw = brand_raw, type_raw = type_raw)
            break

    ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
    LOCAL_SW_SUBTYPE_DIR = os.path.abspath(os.path.join(os.sep,'home',\
        'tftpboot',brand_subdir, type_subdir))
    try:
        sw_release_list_raw = [ str(subdir) for subdir in os.listdir(LOCAL_SW_SUBTYPE_DIR) ]
    except: pass
    #except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']', color = 'magenta')
    ### TRICK = DIRECTORY (with or without dots) MUST BE A NUMBER ###
    if len(sw_release_list) == 0:
        for release in sw_release_list_raw:
            try:
                forget_it = int(release.replace('.',''))
                sw_release_list.append(release)
            except: pass
        if len(sw_release_list) > 0:
            sw_release_list.sort(reverse = True)
            default_sw_release = sw_release_list[0]

###############################################################################




### SHOW HTML MENU SHOWS ONLY IN CGI/HTML MODE ################################
CGI_CLI.uprint('ROUTER SW UPGRADE TOOL', tag = 'h1', color = 'blue')
if CGI_CLI.cgi_active and (not CGI_CLI.submit_form or active_menu == 2):
    ### DISPLAY ROUTER-TYPE MENU ##############################################
    if active_menu == 0:
        main_menu_list = router_type_menu_list
    ### DISPLAY SELEDT ROUTER MENU ############################################
    elif active_menu == 2:
        main_menu_list = router_menu_list + \
        ['<p>Additional device(s) (optional) [list separator=,]:</p>',\
        {'text':'device'}, '<br/>', \
        '<h3>SW RELEASE (required) [default=%s]:</h3>' % (default_sw_release)]

        release_sw_release_list = [ selected_release_string + release for release in sw_release_list ]

        if len(release_sw_release_list) > 0:
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

        if len(SCRIPT_ACTIONS_LIST)>0: main_menu_list.append({'radio':SCRIPT_ACTIONS_LIST})

        main_menu_list += ['<br/>','<h3>Options:</h3>', \
            {'checkbox':'check_device_sw_files_only'},\
            '<br/>', {'checkbox':'force_rewrite_sw_files_on_device'},'<br/>',\
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

### SET DEFAULT (HIGHEST) SW RELEASE IF NOT SET ###############################
if not sw_release and default_sw_release: sw_release = default_sw_release

### PRINT BASIC INFO ##########################################################
CGI_CLI.uprint('server = %s\ndevice(s) = %s\nsw_release = %s\nexpected_disk_free_GB = %s\nsw_file_types = %s' % \
    (iptac_server, ', '.join(device_list) , sw_release, device_expected_GB_free, \
    ', '.join(selected_sw_file_types_list) if len(selected_sw_file_types_list)>0 else str()
    ))


###############################################################################

if len(selected_sw_file_types_list) == 0:
    CGI_CLI.uprint('PLEASE SPECIFY SW FILE TYPE(s) TO COPY.', color = 'red')
    sys.exit(0)

if not sw_release:
    CGI_CLI.uprint('PLEASE SPECIFY SW_RELEASE.', color = 'red')
    sys.exit(0)

if len(device_list) == 0:
    CGI_CLI.uprint('DEVICE NAME(S) NOT INSERTED!', tag = 'h1', color = 'red')
    sys.exit(0)

###############################################################################

if type_subdir and brand_subdir:
    CGI_CLI.uprint('SERVER %s CHECKS:\n' % (iptac_server), tag = 'h2', color = 'blue')

    # ### GENERATE FILE NAMES ###############################################
    # tar_file = '%s-iosxr-px-k9-%s.tar' % \
        # (type_subdir,'.'.join([ char for char in sw_release.encode() ]))
    # OTI_tar_file = '%s-iosxr-px-k9-%s.OTI.tar' % \
        # (type_subdir.lower(),'.'.join([ char for char in sw_release.encode() ]))
    # SMU_tar_files = '%s-px-%s.' % \
        # (type_subdir.lower(),'.'.join([ char for char in sw_release.encode() ]))

    # ### CHECK LOCAL SW DIRECTORIES ########################################
    # LOCAL_SW_RELEASE_DIR = os.path.abspath(os.path.join(os.sep,'home',\
        # 'tftpboot',brand_subdir, type_subdir, sw_release))
    # LOCAL_SW_RELEASE_SMU_DIR = os.path.abspath(os.path.join(os.sep,'home',\
        # 'tftpboot',brand_subdir, type_subdir, sw_release, 'SMU'))

    #directory_list = [LOCAL_SW_RELEASE_DIR, LOCAL_SW_RELEASE_SMU_DIR]

    ### CHECK LOCAL SW DIRECTORIES ########################################
    directory_list = []
    for actual_file_type in selected_sw_file_types_list:
        actual_file_type_subdir, forget_it = os.path.split(actual_file_type)
        directory_list.append(os.path.abspath(os.path.join(os.sep,'home',\
        'tftpboot',brand_subdir, type_subdir, sw_release, actual_file_type_subdir)))

    nonexistent_directories = ', '.join([ directory for directory in directory_list if not os.path.exists(directory) ])

    CGI_CLI.uprint('checking[%s]' % (', '.join(directory_list)))

    if nonexistent_directories:
        CGI_CLI.uprint('missing[%s]' % \
            (nonexistent_directories if nonexistent_directories else str()), color = 'red')
        CGI_CLI.uprint('directories - CHECK FAIL!', tag='h2', color = 'red')
        sys.exit(0)
    else: CGI_CLI.uprint('directories - CHECK OK.', color = 'green')

    ### CHECK LOCAL SERVER FILES EXISTENCY ################################
    true_sw_release_files_on_server = []
    for directory,actual_file_type in zip(directory_list,selected_sw_file_types_list):
        forget_it, actual_file_name = os.path.split(actual_file_type)
        local_results = LCMD.run_commands({'unix':['ls -l %s' % (directory)]})
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
                    (os.path.join(directory,true_file_name))]})
                md5_sum = local_oti_checkum_string[0].split()[0].strip()                
                true_sw_release_files_on_server.append([directory,true_file_name,md5_sum])
        if no_such_files_in_directory:         
            CGI_CLI.uprint('%s file(s) NOT FOUND in %s!' % (actual_file_name,directory), color = 'red')
            sys.exit(0)            
    CGI_CLI.uprint('File(s) FOUND:\n%s' % \
        ('\n'.join([ str(directory+file+4*' '+md5) for directory,file,md5 in true_sw_release_files_on_server ])))        
    sys.exit(0)            









    ### SERVER MD5 CHECKS #################################################
    if true_OTI_tar_file_on_server:
        local_oti_checkum_string = LCMD.run_commands({'unix':['md5sum %s' % \
            (os.path.join(LOCAL_SW_RELEASE_DIR,true_OTI_tar_file_on_server))]})
        md5_true_OTI_tar_file_on_server = local_oti_checkum_string[0].split()[0].strip()

    else: md5_true_OTI_tar_file_on_server = str()

    md5_true_SMU_tar_files_on_server = []
    if len(true_SMU_tar_files_on_server) > 0:
        for file in true_SMU_tar_files_on_server:
            checkum_string = LCMD.run_commands({'unix':['md5sum %s' % \
                (os.path.join(LOCAL_SW_RELEASE_SMU_DIR,file))]})
            md5_true_SMU_tar_files_on_server.append(checkum_string[0].split()[0].strip())

    if CGI_CLI.data.get('OTI.tar_file'):
        CGI_CLI.uprint('OTI.tar file MD5 %s' % \
            (md5_true_OTI_tar_file_on_server + \
            ' FOUND.' if md5_true_OTI_tar_file_on_server else 'NOT FOUND.'),\
            color = ('green' if md5_true_OTI_tar_file_on_server else 'red'))

    if CGI_CLI.data.get('SMU.tar_files'):
        CGI_CLI.uprint('SMU.tar files MD5 %s' % \
            (', '.join(md5_true_SMU_tar_files_on_server) + \
            ' FOUND.' if len(md5_true_SMU_tar_files_on_server)>0 else 'NOT FOUND.'),\
            color = ('green' if len(md5_true_SMU_tar_files_on_server)>0 else 'red'))




### FOR LOOP PER DEVICE #######################################################
for device in device_list:
    ### LOGFILENAME GENERATION ################################################
    logfilename = generate_logfilename(prefix = device.upper(), \
        USERNAME = USERNAME, suffix = str(SCRIPT_ACTION) + '.log')
    logfilename = None

    ### REMOTE DEVICE OPERATIONS ##############################################
    if device:
        CGI_CLI.uprint('\nDEVICE %s CHECKS:\n' % (device), tag = 'h2', color = 'blue')
        RCMD.connect(device, username = USERNAME, password = PASSWORD, \
            printall = CGI_CLI.data.get("printall"), logfilename = logfilename)

        if not RCMD.ssh_connection:
            CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
            RCMD.disconnect()
            if len(device_list) > 1: continue
            else: sys.exit(0)

        ### CHECK HDD/FLASH SPACE ON DEVICE ###################################
        ### RUN INITIAL DATA COLLECTION #######################################
        collector_cmds = {
            ### some ios = enable, ask password, 'show bootflash:' , exit
            'cisco_ios':['show bootflash:','show version | in (%s)' % (asr1k_detection_string)],
            'cisco_xr':['show filesystem',
                'show version | in "%s"' % (asr9k_detection_string),
                ### DIR NOT EXISTS: 'dir : harddisk:/aaaa : Path does not exist'
                ### VOID DIR: 'No files in directory'
                ### SUBDIR EXISTS: '441 drw-r--r-- 2 4096 Nov 20 08:43 bbb'
                'dir harddisk:/IOS-XR/%s' % (sw_release),
                'dir harddisk:/IOS-XR/%s/SMU' % (sw_release),
                ### NOTHING DIR HAPPENS IF EXISTS - 'mkdir: cannot create directory 'harddisk:/aaa': directory exists'
                ### CREATE DIR: 'Created dir harddisk:/aaa/bbb'
                ### 'mkdir' - ENTER IS INSTEAD OF YES ###
                'mkdir harddisk:/IOS-XR',
                '\r\n',
                'mkdir harddisk:/IOS-XR/%s' % (sw_release),
                '\r\n',
                'mkdir harddisk:/IOS-XR/%s/SMU' % (sw_release),
                '\r\n',
                ],
            'juniper':['show system storage'],
            'huawei':['display device | include PhyDisk','display disk information']
        }
        CGI_CLI.uprint('collecting data', \
            no_newlines = None if CGI_CLI.data.get("printall") else True)
        rcmd_collector_outputs = RCMD.run_commands(collector_cmds)
        CGI_CLI.uprint(' ', no_newlines = True if CGI_CLI.data.get("printall") else None)

        if RCMD.router_type == 'cisco_ios':
            try: device_free_space = float(rcmd_collector_outputs[0].\
                     split('bytes available')[0].splitlines()[-1].strip())
            except: pass
        elif RCMD.router_type == 'cisco_xr':
            try: device_free_space = float(rcmd_collector_outputs[0].\
                     split('harddisk:')[0].splitlines()[-1].split()[1].strip())
            except: pass
        elif RCMD.router_type == 'juniper': pass
        elif RCMD.router_type == 'huawei': pass

        CGI_CLI.uprint('disk free space = %s bytes' % (str(device_free_space)) , color = 'blue')

        ### SOME GB FREE EXPECTED (1MB=1048576, 1GB=1073741824) ###
        if device_free_space < (device_expected_GB_free * 1073741824):
            CGI_CLI.uprint('disk space - CHECK FAIL!', color = 'red')
            RCMD.disconnect()
            if len(device_list) > 1: continue
            else: sys.exit(0)
        else: CGI_CLI.uprint('disk space - CHECK OK.', color = 'green')


        ### CHECK LOCAL SERVER AND DEVICE HDD FILES ###########################
        if RCMD.router_type == 'cisco_xr':

            ### CHECK DEVICE HDD FILES EXISTENCY ##############################
            ### ELIMINATE PROBLEM = POSSIBLE ERROR CASE-MIX IN FILE NAMES #####
            ### GET DEVICE CASE-CORRECT FILE NAMES ############################
            ### COPY/SCP FILES TO ROUTER ######################################
            if not CGI_CLI.data.get('check_device_sw_files_only') or \
                CGI_CLI.data.get('force_rewrite_sw_files_on_device'):
                CGI_CLI.uprint('copy sw release file(s), (WARNING: IT COULD TAKE LONGER TIME!)', no_newlines = \
                    None if CGI_CLI.data.get("printall") else True)

                if CGI_CLI.data.get('OTI.tar_file'):
                    true_OTI_tar_file_on_device, true_SMU_tar_files_on_device = None, []
                    for line in rcmd_collector_outputs[2].splitlines():
                        if OTI_tar_file.upper() in line.upper():
                            true_OTI_tar_file_on_device = line.split()[-1].strip()
                            break
                    if not true_OTI_tar_file_on_device or \
                        CGI_CLI.data.get('force_rewrite_sw_files_on_device'):
                        scp_cmd = do_scp_command(USERNAME, PASSWORD, true_OTI_tar_file_on_server,
                            'harddisk:/IOS-XR/%s' % (sw_release),LOCAL_SW_RELEASE_DIR,
                            printall = CGI_CLI.data.get("printall"))


                if CGI_CLI.data.get('SMU.tar_files'):
                    true_OTI_tar_file_on_device, true_SMU_tar_files_on_device = None, []
                    for line in rcmd_collector_outputs[3].splitlines():
                        if SMU_tar_files.upper() in line.upper() and '.tar'.upper() in line.upper():
                            true_SMU_tar_files_on_device.append(line.split()[-1].strip())
                    if len(true_SMU_tar_files_on_device)==0 or \
                        CGI_CLI.data.get('force_rewrite_sw_files_on_device'):
                        for smu_file in true_SMU_tar_files_on_server:
                            scp_cmd = do_scp_command(USERNAME, PASSWORD, smu_file,
                                'harddisk:/IOS-XR/%s/SMU' % (sw_release),LOCAL_SW_RELEASE_SMU_DIR,
                                printall = CGI_CLI.data.get("printall"))



            ### READ EXISTING FILES ON DEVICE - AFTER COPYING TO DEVICE #######
            read2_cmds = {
                'cisco_xr':[
                    'dir harddisk:/IOS-XR/%s' % (sw_release),
                    'dir harddisk:/IOS-XR/%s/SMU' % (sw_release),
                    ],
            }
            rcmd_read2_outputs = RCMD.run_commands(read2_cmds)
            CGI_CLI.uprint(' ', no_newlines = True if CGI_CLI.data.get("printall") else None)

            ### GET DEVICE CASE-CORRECT FILE NAMES - AFTER COPYING TO DEVICE ##
            true_OTI_tar_file_on_device, true_SMU_tar_files_on_device = None, []
            for line in rcmd_read2_outputs[0].splitlines():
                if OTI_tar_file.upper() in line.upper():
                    true_OTI_tar_file_on_device = line.split()[-1].strip()
                    break
            for line in rcmd_read2_outputs[1].splitlines():
                if SMU_tar_files.upper() in line.upper() and '.tar'.upper() in line.upper():
                    true_SMU_tar_files_on_device.append(line.split()[-1].strip())

            if CGI_CLI.data.get('OTI.tar_file'):
                if not true_OTI_tar_file_on_device:
                    CGI_CLI.uprint('OTI.tar file NOT FOUND!', color = 'red')
                    RCMD.disconnect()
                    sys.exit(0)
                else:
                    CGI_CLI.uprint('OTI.tar file %s' % \
                        (true_OTI_tar_file_on_device + \
                        ' FOUND.' if true_OTI_tar_file_on_device else 'NOT FOUND.'),\
                        color = ('green' if true_OTI_tar_file_on_device else 'red'))

            if CGI_CLI.data.get('SMU.tar_files'):
                if len(true_SMU_tar_files_on_device)==0:
                    CGI_CLI.uprint('SMU files NOT FOUND!', color = 'red')
                    RCMD.disconnect()
                    sys.exit(0)
                else:
                    CGI_CLI.uprint('SMU.tar files %s' % \
                        (', '.join(true_SMU_tar_files_on_device) + \
                        ' FOUND.' if len(true_SMU_tar_files_on_device)>0 else 'NOT FOUND.'),\
                        color = ('green' if len(true_SMU_tar_files_on_device)>0 else 'red'))


            ### MD5 CHECKS ON DEVICE/ROUTER ###################################
            ### READ EXISTING FILES ON DEVICE - AFTER COPYING TO DEVICE #######
            read3_cmds = {'cisco_xr':[]}
            if true_OTI_tar_file_on_device:
                read3_cmds = {
                    'cisco_xr':['show md5 file /harddisk:/IOS-XR/%s/%s' % \
                    (sw_release,true_OTI_tar_file_on_device)]}

            for file in true_SMU_tar_files_on_device:
                read3_cmds['cisco_xr'].append('show md5 file /harddisk:/IOS-XR/%s/SMU/%s' % \
                    (sw_release,file))

            CGI_CLI.uprint('checking md5', no_newlines = \
                None if CGI_CLI.data.get("printall") else True)
            rcmd_read3_outputs = RCMD.run_commands(read3_cmds)
            CGI_CLI.uprint(' ', no_newlines = True if CGI_CLI.data.get("printall") else None)

            ### MD5 CHECKSUM IS 32BYTES LONG ###
            md5_true_OTI_tar_file_on_device = str()
            md5_true_SMU_tar_files_on_device = []
            if not true_OTI_tar_file_on_device:
                for output in rcmd_read3_outputs:
                    find_list = re.findall(r'[0-9a-fA-F]{32}', output.strip())
                    if len(find_list)==1:
                        md5_true_SMU_tar_files_on_device.append(find_list[0])
            else:
                for output in rcmd_read3_outputs[1:]:
                    find_list = re.findall(r'[0-9a-fA-F]{32}', output.strip())
                    if len(find_list)==1:
                        md5_true_SMU_tar_files_on_device.append(find_list[0])

            OTI_tar_md5_check_OK, SMU_tar_md5_check_OK = None, None
            if CGI_CLI.data.get('OTI.tar_file'):
                if true_OTI_tar_file_on_device and md5_true_SMU_tar_files_on_device and \
                    true_OTI_tar_file_on_device == true_OTI_tar_file_on_server and \
                    md5_true_SMU_tar_files_on_device == md5_true_SMU_tar_files_on_server:
                    CGI_CLI.uprint('OTI.tar MD5 file - CHECK OK.', color = 'green')
                    OTI_tar_md5_check_OK = True

            if CGI_CLI.data.get('SMU.tar_files'):
                for md5_on_server, md5_on_device in \
                    zip(md5_true_SMU_tar_files_on_device,md5_true_SMU_tar_files_on_server):
                    if md5_on_server and md5_on_device and md5_on_server == md5_on_device:
                        CGI_CLI.uprint('SMU.tar MD5 files - CHECK OK.', color = 'green')
                        SMU_tar_md5_check_OK = True

            if CGI_CLI.data.get('OTI.tar_file') and not OTI_tar_md5_check_OK:
                CGI_CLI.uprint('OTI.tar MD5 file - CHECK FAIL!', color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)

            if CGI_CLI.data.get('SMU.tar_files') and not SMU_tar_md5_check_OK:
                CGI_CLI.uprint('SMU.tar MD5 files - CHECK FAIL!', color = 'red')
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)

            CGI_CLI.uprint('tar files - CHECK OK.', tag='h1', color = 'green')
            if CGI_CLI.data.get('check_device_sw_files_only'):
                RCMD.disconnect()
                if len(device_list) > 1: continue
                else: sys.exit(0)


            ## BACKUP NORMAL AND ADMIN CONFIG ################################
            if CGI_CLI.data.get('backup_configs_to_device_disk'):
                actual_date_string = time.strftime("%Y-%m%d-%H:%M",time.gmtime(time.time()))
                backup_config_rcmds = {'cisco_xr':[
                'copy running-config harddisk:%s-config.txt' % (actual_date_string),
                '\n',
                'admin',
                'copy running-config harddisk:admin-%s-config.txt' %(actual_date_string),
                '\n',
                'exit'
                ]}
                CGI_CLI.uprint('backup configs', no_newlines = \
                    None if CGI_CLI.data.get("printall") else True)
                forget_it = RCMD.run_commands(backup_config_rcmds)
                CGI_CLI.uprint(' ', no_newlines = True if CGI_CLI.data.get("printall") else None)

            ### DELETE TAR FILES ON END #######################################
            if CGI_CLI.data.get('delete_device_sw_files_on_end'):
                del_files_cmds = {'cisco_xr':[]}

                if CGI_CLI.data.get('OTI.tar_file') and true_OTI_tar_file_on_device:
                    del_files_cmds = {'cisco_xr':['del /harddisk:/IOS-XR/%s/%s' % \
                        (sw_release,true_OTI_tar_file_on_device),'\n']}

                if CGI_CLI.data.get('SMU.tar_files'):
                    for file in true_SMU_tar_files_on_device:
                        del_files_cmds['cisco_xr'].append('del /harddisk:/IOS-XR/%s/SMU/%s' % \
                            (sw_release,file))
                        del_files_cmds['cisco_xr'].append('\n')

                del_files_cmds['cisco_xr'].append('dir harddisk:/IOS-XR/%s' % (sw_release))
                del_files_cmds['cisco_xr'].append('dir harddisk:/IOS-XR/%s/SMU' % (sw_release))

                CGI_CLI.uprint('deleting sw release files', no_newlines = \
                    None if CGI_CLI.data.get("printall") else True)
                forget_it = RCMD.run_commands(del_files_cmds)
                CGI_CLI.uprint(' ', no_newlines = True if CGI_CLI.data.get("printall") else None)

        ### DISCONNECT ########################################################
        RCMD.disconnect()
    else:
        if CGI_CLI.cgi_active and CGI_CLI.submit_form:
            CGI_CLI.uprint('DEVICE NAME NOT INSERTED!', tag = 'h1', color = 'red')

del sql_inst






