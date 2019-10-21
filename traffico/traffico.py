#!/usr/bin/python

###!/usr/bin/python36

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
import cgitb; cgitb.enable()
import requests
from mako.template import Template
from mako.lookup import TemplateLookup

### DELAY BETWEEN OVERLOAD BIT AND BGP SHUT ###
SLEEPSEC = 120



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
                            help = "target router to access")
        parser.add_argument("--shut",
                            action = 'store_true', dest = "shut",
                            default = None,
                            help = "switch-off bgp traffic")
        parser.add_argument("--noshut",
                            action = 'store_true', dest = "noshut",
                            default = None,
                            help = "switch-on bgp traffic")
        parser.add_argument("--sim",
                            action = "store_true", dest = 'sim',
                            default = None,
                            help = "config simulation mode")
        parser.add_argument("--cfg",
                            action = "store_true", dest = 'show_config_only',
                            default = None,
                            help = "show config only, do not push data to device")
        parser.add_argument("--wait",
                            action = "store", dest = 'delay',
                            default = '120',
                            help = "delay in seconds [between overload bit set and bgp off / between bgp on overload bit clean], 120sec by default")
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
                #time.sleep(0.5)
        ### CLI MODE ###
        else: print(msg)        

    @staticmethod
    def uprint(text, tag = None, tag_id = None, color = None, name = None, jsonprint = None, log = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name, print_per_tag = copy.deepcopy(text), str(), str()
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
                elif 'YELLOW' in color.upper():  text_color = CGI_CLI.bcolors.YELLOW
            ### CLI_MODE ###    
            print(text_color + print_name + print_text + CGI_CLI.bcolors.ENDC)
        del print_text
        if CGI_CLI.cgi_active:
            if tag: CGI_CLI.print_chunk('</%s>'%(tag))
            else: CGI_CLI.print_chunk('<br/>');
            ### PRINT PER TAG ###
            CGI_CLI.print_chunk(print_per_tag)    
        ### LOGGING ###
        if CGI_CLI.logfilename and log:
            with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                CGI_CLI.fp.write(print_name + log_text + '\n')
                del log_text


    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, color = None):
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
                    if isinstance(data_item.get('radio'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                                ('script_action',radiobutton,radiobutton.replace('_',' ')))
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
                                if re.search(r'\[[0-9a-zA-Z]+\-[0-9a-zA-Z\-\.\@\_]+\]', ''.join(command_outputs[-1:])):
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
                            ### ALL HUAWEI VERSIONS NEED SAVE !!! ###
                            command_outputs.append(RCMD.run_command('save', conf = False, \
                                sim_all = sim_config, printall = printall))
                            command_outputs.append(RCMD.run_command('yes', conf = False, \
                                sim_all = sim_config, printall = printall))
                ### CHECK CONF OUTPUTS #########################################
                if (conf or RCMD.conf):
                    RCMD.config_problem = None
                    for rcmd_output in command_outputs:
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
        timeout_counter, timeout_counter2 = 0, 0
        # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
        if chan.recv_ready(): flush_buffer = chan.recv(9999)
        time.sleep(0.1)
        chan.send(send_data + '\n')
        time.sleep(0.2)
        while not exit_loop:
            if chan.recv_ready():
                # workarround for discontious outputs from routers
                timeout_counter = 0
                buff = chan.recv(9999)
                buff_read = buff.decode("utf-8").replace('\x0d','').replace('\x07','').\
                    replace('\x08','').replace(' \x1b[1D','')
                output += buff_read
            else: time.sleep(0.1); timeout_counter += 1
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
                # 30 SECONDS COMMAND TIMEOUT
                if (timeout_counter) > 30*10: exit_loop=True; break
                # 10 SECONDS --> This could be a new PROMPT
                elif (timeout_counter) > 10*10 and not exit_loop2:
                    chan.send('\n')
                    time.sleep(0.1)
                    while(not exit_loop2):
                        if chan.recv_ready():
                            buff = chan.recv(9999)
                            buff_read = buff.decode("utf-8").replace('\x0d','')\
                               .replace('\x07','').replace('\x08','').replace(' \x1b[1D','')
                            output2 += buff_read
                        else: time.sleep(0.1); timeout_counter2 += 1
                        try: new_last_line = output2.splitlines()[-1].strip()
                        except: new_last_line = str()
                        if last_line_orig and new_last_line and last_line_orig == new_last_line:
                            if printall: CGI_CLI.uprint('NEW_PROMPT: %s' % (last_line_orig), color = 'cyan')
                            new_prompt = last_line_orig; exit_loop=True;exit_loop2=True; break
                        # WAIT UP TO 5 SECONDS
                        if (timeout_counter2) > 5*10: exit_loop2 = True; break
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
                if 'iosxr-' in output or 'Cisco IOS XR Software' in output: router_os = 'ios-xr'
                elif 'Cisco IOS-XE software' in output: router_os = 'ios-xe'
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
    def run_command(cmd_line = None, logfilename = None, printall = None):
        os_output, cmd_list = str(), None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_line:
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line))
                LCMD.fp.write('LOCAL_COMMAND: ' + cmd_line + '\n')
                try: os_output = subprocess.check_output(str(cmd_line), shell=True).decode("utf-8")
                except (subprocess.CalledProcessError) as e:
                    if printall: CGI_CLI.uprint(str(e))
                    LCMD.fp.write(str(e) + '\n')
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    LCMD.fp.write(exc_text + '\n')
                if os_output and printall: CGI_CLI.uprint(os_output)
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
                    try: os_output = subprocess.check_output(str(cmd_line), shell=True).decode("utf-8")
                    except (subprocess.CalledProcessError) as e:
                        if printall: CGI_CLI.uprint(str(e))
                        LCMD.fp.write(str(e) + '\n')
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
                        edict = {}; eval(compile(cmd_data.replace('\n', '\\n'), '<string>', 'exec'), globals(), edict)
                    else: edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
                except Exception as e:
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None


    @staticmethod
    def exec_command_try_except(cmd_data = None, logfilename = None, printall = None, escape_newline = None):
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
                                (cmd_data.replace('\n', '\\n').split('=')[0].strip().split('[')[0],cmd_data.split('=')[0].strip(), \
                                cmd_data.replace('\n', '\\n').split('=')[1].strip(), cmd_data.split('=')[0].strip())
                        else:
                            cmd_ex_data = 'global %s\ntry: %s = %s \nexcept: %s = None' % \
                                (cmd_data.split('=')[0].strip().split('[')[0],cmd_data.split('=')[0].strip(), \
                                cmd_data.split('=')[1].strip(), cmd_data.split('=')[0].strip())
                    else: cmd_ex_data = cmd_data
                    if printall: CGI_CLI.uprint("EXEC: \n%s" % (cmd_ex_data))
                    LCMD.fp.write('EXEC: \n' + cmd_ex_data + '\n')
                    ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                    edict = {}; eval(compile(cmd_ex_data, '<string>', 'exec'), globals(), edict)
                    #CGI_CLI.uprint("%s" % (eval(cmd_data.split('=')[0].strip())))
                except Exception as e:
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None




###############################################################################
def generate_file_name(prefix = None, USERNAME = None, suffix = None , directory = None):
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


def find_last_shut_logfile(prefix = None, USERNAME = None, suffix = None, directory = None, \
    latest = None , printall = None):
    shut_file = str()
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(DIR,'logs')
    if not prefix: use_prefix = str()
    else: use_prefix = prefix
    if latest:
        list_shut_files = glob.glob(os.path.join(LOGDIR, use_prefix.replace(':','_').replace('.','_')) \
            + '*' + sys.argv[0].replace('.py','').replace('./','').replace(':','_').replace('.','_').replace('\\','/').split('/')[-1] \
            + '*' + '-' + suffix)
    else:
        list_shut_files = glob.glob(os.path.join(LOGDIR, use_prefix.replace(':','_').replace('.','_')) \
            + '*' + sys.argv[0].replace('.py','').replace('./','').replace(':','_').replace('.','_').replace('\\','/').split('/')[-1] \
            + '*' + USERNAME + '-' + suffix)
    if len(list_shut_files) == 0:
        CGI_CLI.uprint( " ... Can't find any shut session log file!", color = 'magenta')
    else:
        most_recent_shut = list_shut_files[0]
        for item in list_shut_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_shut)):
                most_recent_shut = item
        shut_file = most_recent_shut
    if printall and shut_file: CGI_CLI.uprint('FOUND LAST SHUT LOGFILE: %s' % (str(shut_file)), color = 'blue')
    return shut_file


def cisco_xr_parse_bgp_summary(text, LOCAL_AS_NUMBER):
    previous_line, ext_v4_list, ext_v6_list = str(), [], []
    try:
        temp_splited = (copy.deepcopy(text)).split("St/PfxRcd")[1].strip().splitlines()
        for line in temp_splited:
            if line.strip() == str(): continue
            if len(line.split()) == 1 and ('.' in line or ':' in line):
                previous_line = line; continue
            if previous_line: line, previous_line = previous_line + line, str()
            ### COLUMN10 IS DE FACTO SECOND WORD OF COLUMN9
            try: column10 = line.split()[10]
            except: column10 = str()
            try:
                if not LOCAL_AS_NUMBER in line.split()[2] and "." in line.split()[0]:
                    ext_v4_list.append([line.split()[0],line.split()[9] + column10])
                if not LOCAL_AS_NUMBER in line.split()[2] and ":" in line.split()[0]:
                    ext_v6_list.append([line.split()[0],line.split()[9] + column10])
            except: pass
        del temp_splited
    except: pass
    ### RETURNS LIST IN LISTS [PEER,STATUS] ###
    return ext_v4_list, ext_v6_list


def huawei_parse_bgp_summary(text, LOCAL_AS_NUMBER):
    previous_line, ext_v4_list, ext_v6_list = str(), [], []
    try:
        temp_splited = (copy.deepcopy(text)).split("PrefRcv")[1].strip().splitlines()
        for line in temp_splited:
            if line.strip() == str(): continue
            if len(line.split()) == 1 and ('.' in line or ':' in line):
                previous_line = line; continue
            if previous_line: line, previous_line = previous_line + line, str()
            try:
                if not LOCAL_AS_NUMBER in line.split()[2] and "." in line.split()[0]:
                    ext_v4_list.append([line.split()[0], line.split()[7]])
                if not LOCAL_AS_NUMBER in line.split()[2] and ":" in line.split()[0]:
                    ext_v6_list.append([line.split()[0], line.split()[7]])
            except: pass
        del temp_splited
    except: pass
    ### RETURNS LIST IN LISTS [PEER,STATUS] ###
    return ext_v4_list, ext_v6_list


def return_bgp_data_json():
    return json.dumps(bgp_data, indent=2)


def read_bgp_data_json_from_logfile(filename = None, printall = None):
    bgp_data_loaded, text = None, None
    with open(filename,"r") as fp:
        text = fp.read()
    if text:
        try: bgp_data_json_text = text.split('EVAL: return_bgp_data_json()')[1]
        except: bgp_data_json_text = str()
        if bgp_data_json_text:
            try:
                bgp_data_loaded = json.loads(bgp_data_json_text, object_pairs_hook = collections.OrderedDict)
            except: pass
            #print("LOADED_BGP_DATA: ",bgp_data_loaded)
            if printall: CGI_CLI.uprint("\nLOADED JSON BGP_DATA: ")
            if printall: CGI_CLI.uprint(json.dumps(bgp_data_loaded, indent=2))
    return bgp_data_loaded


##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)
##############################################################################

USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True)
#CGI_CLI.print_args()
LCMD.init()
device = CGI_CLI.data.get("device")

SCRIPT_ACTION, bgp_data, bgp_config = str(), {}, []

### TEST WORKARROUND ###
if CGI_CLI.cgi_active and not (USERNAME and PASSWORD):
    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()
    if iptac_server == 'iptac5': USERNAME, PASSWORD = 'iptac', 'paiiUNDO'

### HTML MENU SHOWS ONLY IN CGI MODE ###
if CGI_CLI.cgi_active and not CGI_CLI.submit_form:
    CGI_CLI.uprint('TRAFFIC OFF/ON TOOL:\n', tag = 'h1', color = 'blue')
    CGI_CLI.formprint([{'text':'device'},'<br/>',{'text':'username'},'<br/>',\
        {'password':'password'},'<br/>',{'text':'delay'},'<br/>',\
        {'radio':['shut','noshut']},'<br/>',\
        {'checkbox':'sim'},'<br/>',{'checkbox':'printall'},'<br/>',\
        {'checkbox':'show_config_only'},'<br/>','<br/>'], \
        submit_button = 'OK', pyfile = None, tag = None, color = None)
    ### NOT NEEDED TO DO ANY MORE ###
    sys.exit(0)
else:
    ### READ SCRIPT ACTION ###
    if (CGI_CLI.data.get("script_action") or CGI_CLI.data.get("shut") or CGI_CLI.data.get("noshut")):
        if CGI_CLI.data.get("script_action"): SCRIPT_ACTION = CGI_CLI.data.get("script_action")
        elif CGI_CLI.data.get("shut"):        SCRIPT_ACTION = 'shut'
        elif  CGI_CLI.data.get("noshut"):     SCRIPT_ACTION = 'noshut'
    else:
        CGI_CLI.uprint('Please specify --shut or --noshut ... ', color = 'magenta')
        sys.exit(0)

### LOGFILENAME GENERATION ###
logfilename = generate_file_name(prefix = device, USERNAME = USERNAME, suffix = SCRIPT_ACTION + '-log')




### LAST RED ASKING MESSAGE BEFORE ACTION ###
if CGI_CLI.cgi_active or CGI_CLI.data.get("show_config_only"): pass
else: 
    if CGI_CLI.data.get("shut"):
        if not 'WIN32' in sys.platform.upper():
            CGI_CLI.uprint("You are about to shut down all the BGP sessions on %s do you want to continue? (Y/N) [Enter]:", color = 'red')
            continue_or_not = LCMD.run_command('read var;echo $var')
            if continue_or_not.strip().upper() != "Y": sys.exit(0)
    elif CGI_CLI.data.get("noshut"):
        if not 'WIN32' in sys.platform.upper():
            CGI_CLI.uprint("You are about to switch-on all the BGP sessions on %s do you want to continue? (Y/N) [Enter]:", color = 'red')
            continue_or_not = LCMD.run_command('read var;echo $var')
            if continue_or_not.strip().upper() != "Y": sys.exit(0)


### DEVICE ACCESS #############################################################
if device:
    CGI_CLI.uprint('DEVICE = %s' % (str(device)), tag = 'h1', color = 'blue')

    ### DEVICE AUTODETECT + CONNECT TO DEVICE ###
    rcmd_outputs = RCMD.connect(device, username = USERNAME, password = PASSWORD, \
        logfilename = logfilename)
    CGI_CLI.set_logfile()

    ### END IF NO ROUTER TYPE ###
    if not RCMD.router_type:
        RCMD.disconnect()
        sys.exit(0)

    ### READ SHUT LOGFILE ###
    if logfilename and SCRIPT_ACTION == 'noshut':
        last_shut_file = find_last_shut_logfile(prefix = device, USERNAME = USERNAME, suffix = 'shut-log', \
            printall = CGI_CLI.data.get("printall"))
        if not last_shut_file:
            RCMD.disconnect()
            sys.exit(0)
        bgp_data = read_bgp_data_json_from_logfile(last_shut_file, printall = CGI_CLI.data.get("printall"))
        if not bgp_data:
            CGI_CLI.uprint( " ... Please insert valid shut session log! \nFile " + last_shut_file + \
                " \ndoes not contain return_bgp_data_json !", color = 'red', tag = 'h1', log = True)
            RCMD.disconnect()
            sys.exit(0)

    ### ROUTER TYPE + SIM PRINT ###
    CGI_CLI.uprint("ROUTER_TYPE: %s %s" % (RCMD.router_type, \
        '\nSIMULATION MODE = ON' if CGI_CLI.data.get("sim") else str()), color = 'blue', log = True)

    ### COLLECTOR CONFIG ###
    collector_cmds = {
        'cisco_ios':['show bgp summary',
                     'show bgp ipv6 unicast summary',
                     'show bgp vpnv4 unicast summary',
                     'show bgp vrf all summary'
                    ],

        'cisco_xr': ['show bgp summary',
                     'show bgp ipv6 unicast summary',
                     'show bgp vpnv4 unicast summary',
                     'show bgp vrf all summary'
                    ],

        'juniper':  ['show bgp neighbor | match "Group:|Peer:" | except "NLRI|Restart"',
                     'show bgp group summary',
                     'show configuration protocols bgp | display set | match neighbor',
                    ],

        'huawei':   ['display bgp peer',
                     'display bgp ipv6 peer'
                    ]
    }

    ### RUN START COLLETING OF DATA ###
    rcmd_outputs = RCMD.run_commands(collector_cmds, printall = CGI_CLI.data.get("printall"))

    ### FIND LOCAL AS NUMBER ###
    LOCAL_AS_NUMBER = None
    if RCMD.router_type == 'cisco_ios':
        pass
    if RCMD.router_type == 'cisco_xr':
        try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("local AS number")[1].splitlines()[0].strip()
        except: pass
        if not LOCAL_AS_NUMBER:
            try: LOCAL_AS_NUMBER = rcmd_outputs[2].split("local AS number")[1].splitlines()[0].strip()
            except: pass
    elif RCMD.router_type == 'juniper':
        try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("Local:")[1].splitlines()[0].split('AS')[1].strip()
        except: pass
    elif RCMD.router_type == 'huawei':
        try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("Local AS number :")[1].splitlines()[0].strip()
        except: pass

    if LOCAL_AS_NUMBER:
        CGI_CLI.uprint(LOCAL_AS_NUMBER, name = True , color = 'blue', log = True)
    else:
        CGI_CLI.uprint("PROBLEM TO PARSE LOCAL AS NUMBER!" , color = 'red', tag = 'h1',  log = True)
        RCMD.disconnect()
        sys.exit(0)


    ### GET eBGP PEERS + VPNs or GROUPS + PEERs ###############################


    ### CISCO_IOS #############################################################
    if RCMD.router_type == 'cisco_ios':
        CGI_CLI.uprint('NOT IMPLEMENTED YET !', tag ='h1', color = 'red', log = True)

    ### CISCO_XR ##############################################################
    elif RCMD.router_type == 'cisco_xr':
        bgp_config.append('router bgp %s' % (LOCAL_AS_NUMBER))

        ### OTI ###
        if LOCAL_AS_NUMBER == '5511':
            ipv4_list, dummy = cisco_xr_parse_bgp_summary(rcmd_outputs[0], LOCAL_AS_NUMBER)
            dummy, ipv6_list = cisco_xr_parse_bgp_summary(rcmd_outputs[1], LOCAL_AS_NUMBER)

            if SCRIPT_ACTION == 'shut':
                if len(ipv4_list)>0: bgp_data["OTI_EXT_IPS_V4"] = ipv4_list
                if len(ipv6_list)>0: bgp_data["OTI_EXT_IPS_V6"] = ipv6_list
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V4",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('neighbor %s shutdown' % neighbor)
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V6",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('neighbor %s shutdown' % neighbor)

            elif SCRIPT_ACTION == 'noshut':
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V4",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('no neighbor %s shutdown' % neighbor)
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V6",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('no neighbor %s shutdown' % neighbor)

        ### IMN ###
        if LOCAL_AS_NUMBER == '2300':
            if SCRIPT_ACTION == 'shut':
                vrf_name, ipv4_struct = str(), []
                try:
                    for vrf_part in rcmd_outputs[3].split('VRF: ')[1:]:
                        vrf_name = vrf_part.splitlines()[0].split()[0]
                        ipv4_list, dummy = cisco_xr_parse_bgp_summary(vrf_part,LOCAL_AS_NUMBER)
                        if ipv4_list: ipv4_struct.append([vrf_name,ipv4_list])
                except: pass

                # vrf_name, ipv6_struct = str(), []
                # try:
                    # for vrf_part in rcmd_outputs[3].split('VRF: ')[1:]:
                        # vrf_name = vrf_part.splitlines()[0].split()[0]
                        # dummy, ipv6_list = cisco_xr_parse_bgp_summary(vrf_part,LOCAL_AS_NUMBER)
                        # if ipv6_list: ipv6_struct.append([vrf_name,ipv6_list])
                # except: pass

                if SCRIPT_ACTION == 'shut':
                    if ipv4_struct: bgp_data["OTI_EXT_GROUP_IPS_V4"] = ipv4_struct
                    #if ipv6_struct: bgp_data["OTI_EXT_GROUP_IPS_V6"] = ipv6_struct
                elif SCRIPT_ACTION == 'noshut':
                    pass

                for group,neighbor_status in bgp_data.get("OTI_EXT_GROUP_IPS_V4",[]):
                    bgp_config.append('vrf %s' %(group))
                    for  neighbor, status in neighbor_status:
                        if not "ADMIN" in status.upper(): bgp_config.append('neighbor %s shutdown' % neighbor)
                # for group,neighbor_status in bgp_data.get("OTI_EXT_GROUP_IPS_V6",[]):
                    # bgp_config.append('vrf %s' %(group))
                    # for  neighbor, status in neighbor_status:
                        # if not "ADMIN" in status.upper(): bgp_config.append('neighbor %s shutdown' % neighbor)

            elif SCRIPT_ACTION == 'noshut':
                for group,neighbor_status in bgp_data.get("OTI_EXT_GROUP_IPS_V4",[]):
                    bgp_config.append('vrf %s' %(group))
                    for  neighbor, status in neighbor_status:
                        if not "ADMIN" in status.upper(): bgp_config.append('no neighbor %s shutdown' % neighbor)
                # for group,neighbor_status in bgp_data.get("OTI_EXT_GROUP_IPS_V6",[]):
                    # bgp_config.append('vrf %s' %(group))
                    # for  neighbor, status in neighbor_status:
                        # if not "ADMIN" in status.upper(): bgp_config.append('no neighbor %s shutdown' % neighbor)


    ### JUNOS #################################################################
    elif RCMD.router_type == 'juniper':
        try: junos_ext_groups = [ group.split()[-1].strip().encode(encoding="UTF-8") for group in rcmd_outputs[1].split("External ")[0:-1] ]
        except: junos_ext_groups = []

        ### OTI ###
        if LOCAL_AS_NUMBER == '5511':
            if SCRIPT_ACTION == 'shut':
                active_junos_ext_groups = []
                for group in junos_ext_groups:
                    for line in rcmd_outputs[2].splitlines():
                        if group in line and 'deactivate' not in line:
                            try: neighbor = line.split('neighbor')[1].strip()
                            except: neighbor = str()
                            if neighbor: active_junos_ext_groups.append([group,neighbor])
                bgp_data["JUNOS_EXT_GROUP_NEIGHBORS"] = active_junos_ext_groups
                for group,neighbor in bgp_data.get("JUNOS_EXT_GROUP_NEIGHBORS",[]):
                    bgp_config.append('deactivate protocols bgp group %s neighbor %s' % (group, neighbor))
            elif SCRIPT_ACTION == 'noshut':
                for group,neighbor in bgp_data.get("JUNOS_EXT_GROUP_NEIGHBORS",[]):
                    bgp_config.append('activate protocols bgp group %s neighbor %s' % (group, neighbor))
        ### IMN ###
        if LOCAL_AS_NUMBER == '2300':
            CGI_CLI.uprint('NOT IMPLEMENTED YET !', tag ='h1', color = 'red', log = True)


    ### HUAWEI ################################################################
    elif RCMD.router_type == 'huawei':
        ipv4_list, dummy = huawei_parse_bgp_summary(rcmd_outputs[0], LOCAL_AS_NUMBER)
        dummy, ipv6_list = huawei_parse_bgp_summary(rcmd_outputs[1], LOCAL_AS_NUMBER)
        bgp_config.append('bgp %s' % (LOCAL_AS_NUMBER))

        ### OTI ###
        if LOCAL_AS_NUMBER == '5511':
            if SCRIPT_ACTION == 'shut':
                if len(ipv4_list)>0: bgp_data["OTI_EXT_IPS_V4"] = ipv4_list
                if len(ipv6_list)>0: bgp_data["OTI_EXT_IPS_V6"] = ipv6_list
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V4",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('peer %s ignore' % neighbor)
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V6",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('peer %s ignore' % neighbor)

            elif SCRIPT_ACTION == 'noshut':
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V4",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('undo peer %s ignore' % neighbor)
                for neighbor,status in bgp_data.get("OTI_EXT_IPS_V6",[]):
                    if not "ADMIN" in status.upper(): bgp_config.append('undo peer %s ignore' % neighbor)

        ### IMN ###
        if LOCAL_AS_NUMBER == '2300':
            CGI_CLI.uprint('NOT IMPLEMENTED YET !', tag ='h1', color = 'red', log = True)


    ### VOID CONFIG END #######################################################
    if bgp_config == [] or bgp_data == {}:
        CGI_CLI.uprint('VOID CONFIG, END!', tag = 'h1' , color = 'red', log = True)
        LCMD.eval_command('return_bgp_data_json()', logfilename = logfilename)
        RCMD.disconnect()
        sys.exit(0)
    elif CGI_CLI.data.get("printall"):
        CGI_CLI.uprint(bgp_data, name = 'bgp_data', jsonprint = True, log = True)


    ### OVERLOAD BIT SET/UNSET CONFIGS ########################################
    overload_bit_set_config   = {'cisco_ios':['router isis PAII', 'set-overload-bit'],
                                 'cisco_xr' :['router isis PAII', 'set-overload-bit'],
                                 'huawei'   :['isis %s' % (LOCAL_AS_NUMBER), 'set-overload','Y'],
                                 'juniper'  :['delete protocols isis overload timeout 240',
                                     'set protocols isis overload']
                                }

    overload_bit_unset_config = {'cisco_ios':['router isis PAII', 'no set-overload-bit'],
                                 'cisco_xr' :['router isis PAII', 'no set-overload-bit'],
                                 'huawei'   :['isis %s' % (LOCAL_AS_NUMBER), 'undo set-overload',
                                     'set-overload on-startup 240'],
                                 'juniper'  :['delete protocols isis overload',
                                     'set protocols isis overload timeout 240']
                                }


    ### PRINT SET OVERLOAD BIT CONFIG #########################################
    if SCRIPT_ACTION == 'shut':
        CGI_CLI.uprint('\n%s CONFIG:\n' % ('SET OVERLOAD BIT'), color = 'blue', \
        tag = 'h1', log = True)
        CGI_CLI.uprint('%s\n\n' % ('\n'.join(overload_bit_set_config.get(RCMD.router_type,[]))), \
            color = 'blue', log = True)


    ### PRINT CONFIG ##########################################################
    CGI_CLI.uprint('\n%s CONFIG:\n' % (SCRIPT_ACTION.upper()), color = 'blue', \
        tag = 'h1', log = True)
    CGI_CLI.uprint('%s\n\n' % ('\n'.join(bgp_config)), color = 'blue', log = True)


    ### PRINT CLEAR OVERLOAD BIT CONFIG #######################################
    if SCRIPT_ACTION == 'noshut':
        CGI_CLI.uprint('\n%s CONFIG:\n' % ('CLEAR OVERLOAD BIT'), color = 'blue', \
        tag = 'h1', log = True)
        CGI_CLI.uprint('%s\n\n' % ('\n'.join(overload_bit_unset_config.get(RCMD.router_type,[]))), \
            color = 'blue', log = True)


    ### SHOW CONFIG ONLY END ##################################################
    if CGI_CLI.data.get("show_config_only"):
        LCMD.eval_command('return_bgp_data_json()', logfilename = logfilename)
        RCMD.disconnect()
        sys.exit(0)


    ### SHUT ACTION ###########################################################
    if SCRIPT_ACTION == 'shut':
        CGI_CLI.uprint('Setting overload bit...', log = True)
        RCMD.run_commands(overload_bit_set_config, conf = True, sim_config = CGI_CLI.data.get("sim"), \
            printall = CGI_CLI.data.get("printall"))

        if not CGI_CLI.data.get("sim"):
            CGI_CLI.uprint('Waiting...', log = True)
            for i in range(int(int(CGI_CLI.data.get("delay") if CGI_CLI.data.get("delay") else int(SLEEPSEC))/10)):
                CGI_CLI.uprint('%s0 sec...' % (str(i+1)), log = True)
                time.sleep(10)



        CGI_CLI.uprint('Writing config...', log = True)
        RCMD.run_commands(bgp_config, conf = True, sim_config = CGI_CLI.data.get("sim"), \
            printall = CGI_CLI.data.get("printall"))


    ### NOSHUT ACTION #########################################################
    elif SCRIPT_ACTION == 'noshut':
        CGI_CLI.uprint('Writing config...', log = True)
        RCMD.run_commands(bgp_config, conf = True, sim_config = CGI_CLI.data.get("sim"), \
            printall = CGI_CLI.data.get("printall"))

        if not CGI_CLI.data.get("sim"):
            CGI_CLI.uprint('Waiting...', log = True)
            for i in range(int(int(CGI_CLI.data.get("delay") if CGI_CLI.data.get("delay") else int(SLEEPSEC))/10)):
                CGI_CLI.uprint('%s0 sec...' % (str(i+1)), log = True)
                time.sleep(10)

        CGI_CLI.uprint('Clearing overload bit...', log = True)
        RCMD.run_commands(overload_bit_unset_config, conf = True, sim_config = CGI_CLI.data.get("sim"), \
            printall = CGI_CLI.data.get("printall"))


    ### FINAL_CHECK ###########################################################
    if LOCAL_AS_NUMBER == '5511':
        check_config = {'cisco_ios':['show bgp summary','show bgp ipv6 unicast summary'],
                        'cisco_xr' :['show bgp summary','show bgp ipv6 unicast summary'],
                        'huawei'   :['display bgp peer','display bgp ipv6 peer'],
                        'juniper'  :['show configuration protocols bgp']
                       }

    elif LOCAL_AS_NUMBER == '2300':
        check_config = {'cisco_ios':['show bgp vpnv4 unicast summary','show bgp vrf all summary'],
                        'cisco_xr': ['show bgp vpnv4 unicast summary','show bgp vrf all summary'],
                       }

    CGI_CLI.uprint('\nFINAL MANUAL CHECK:', tag = 'h1', color = 'blue', log = True)
    rcmd_outputs = RCMD.run_commands(check_config, printall = True)


    ### WRITE JSON TO END OF FILE #############################################
    LCMD.eval_command('return_bgp_data_json()', logfilename = logfilename)


    ### DISCONNECT + END ###
    if logfilename and os.path.exists(logfilename): CGI_CLI.uprint('%s file created.' % (logfilename))
    RCMD.disconnect()
else: CGI_CLI.uprint('DEVICE NAME NOT INSERTED!', tag = 'h1', color = 'red')

