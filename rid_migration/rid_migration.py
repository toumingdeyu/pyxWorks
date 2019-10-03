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
                            help = "target router to access")
        parser.add_argument("--rollback",
                            action = "store_true", dest = 'rollback',
                            default = None,
                            help = "do rollback")    
        parser.add_argument("--sim",
                            action = "store_true", dest = 'sim',
                            default = None,
                            help = "config simulation mode")                             
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
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(interaction = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.cgi_active = None
        CGI_CLI.initialized = True
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), '', '', ''
        form, CGI_CLI.data = collections.OrderedDict(), collections.OrderedDict()
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
            print("Content-type:text/html")
            print("\r\n\r\n<html><head><title>%s</title></head><body>" %
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM CGI/CLI
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
                    print('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4">%s</textarea>'%\
                        (data_item.get('textcontent'), data_item.get('text','')))
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
                        print('<option value = "%s" selected>%s</option>'%(option,option))
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


class RCMD(object):

    @staticmethod
    def connect(device = None, cmd_data = None, username = None, password = None, \
        use_module = 'paramiko', logfilename = None, timeout = 60, conf = None, \
        sim_config = None, disconnect = None, printall = None):
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
            RCMD.KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']
            try: RCMD.DEVICE_HOST = device.split(':')[0]
            except: RCMD.DEVICE_HOST = str()
            try: RCMD.DEVICE_PORT = device.split(':')[1]
            except: RCMD.DEVICE_PORT = '22'
            CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.')
            RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
            if not RCMD.router_type in RCMD.KNOWN_OS_TYPES:
                CGI_CLI.uprint('%sUNSUPPORTED DEVICE TYPE: \'%s\', BREAK!%s' % \
                    (bcolors.MAGENTA, RCMD.router_type, bcolors.ENDC))
            else: CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type))
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
            except Exception as e: CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']')    
            finally:
                if disconnect: RCMD.disconnect()
        else: CGI_CLI.uprint('DEVICE NOT INSERTED!')
        return command_outputs        

    @staticmethod
    def run_command(cmd_line = None, printall = None, conf = None, sim_config = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        """
        last_output, sim_mark = str(), str()
        if RCMD.ssh_connection and cmd_line:
            if (sim_config or RCMD.sim_config) and (conf or RCMD.conf): sim_mark = '(SIM)'
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
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None):
        """
        FUNCTION: run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT, 
                 - list of strings or string, OS TYPE DEPENDENT    
        conf     - True/False, go to config mode        
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
                elif RCMD.use_module == 'paramiko':    
                    ### CONFIG MODE FOR PARAMIKO ###############################
                    conf_output = ''                    
                    if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':    
                        if RCMD.router_type=='cisco_ios': conf_output = RCMD.run_command('config t', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='cisco_xr': conf_output = RCMD.run_command('config t', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='juniper': conf_output = RCMD.run_command('configure', \
                            conf = conf, sim_config = sim_config , printall = printall)
                        elif RCMD.router_type=='huawei': conf_output = RCMD.run_command('system-view', \
                            conf = conf, sim_config = sim_config, printall = printall)
                    if conf_output: command_outputs.append(conf_output)    
                    ### PROCESS COMMANDS - PER COMMAND #########################
                    for cmd_line in cmd_list:
                        command_outputs.append(RCMD.run_command(cmd_line, \
                            conf = conf, sim_config = sim_config, printall = printall))
                    ### EXIT FROM CONFIG MODE FOR PARAMIKO #####################    
                    if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':
                        ### COMMIT SECTION -------------------------------------
                        commit_output = ""                    
                        if RCMD.router_type=='cisco_ios': pass
                        elif RCMD.router_type=='cisco_xr': commit_output = RCMD.run_command('commit', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='juniper': commit_output = RCMD.run_command('commit', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='huawei': commit_output = RCMD.run_command('save', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        if commit_output: command_outputs.append(commit_output)
                        if 'Failed to commit' in commit_output:
                            if RCMD.router_type=='cisco_xr': 
                                failed_output = RCMD.run_command('show configuration failed', \
                                    conf = conf, sim_config = sim_config, printall = printall),
                                command_outputs.append(failed_output)
                                ### ALTERNATIVE COMMANDS: show commit changes diff, commit show-error
                        ### EXIT SECTION ---------------------------------------
                        if RCMD.router_type=='cisco_ios': RCMD.run_command('exit', \
                            conf = conf, sim_config = sim_config, printall = printall) 
                        elif RCMD.router_type=='cisco_xr': RCMD.run_command('exit', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='juniper': RCMD.run_command('exit', \
                            conf = conf, sim_config = sim_config, printall = printall)
                        elif RCMD.router_type=='huawei': RCMD.run_command('return', \
                            conf = conf, sim_config = sim_config, printall = printall)                   
        return command_outputs                   

    @staticmethod
    def __cleanup__():
        RCMD.output, RCMD.fp = None, None
        if RCMD.ssh_connection:
            if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
            elif RCMD.use_module == 'paramiko': RCMD.client.close()
            CGI_CLI.uprint('DEVICE %s:%s DONE.' % (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT))
            RCMD.ssh_connection = None
            
    @staticmethod
    def disconnect():
        RCMD.output, RCMD.fp = None, None
        if RCMD.ssh_connection:
            if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
            elif RCMD.use_module == 'paramiko': RCMD.client.close()
            CGI_CLI.uprint('DEVICE %s:%s DISCONNECTED.' % (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT))
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
                            if printall: print('%sNEW_PROMPT: %s%s' % (bcolors.CYAN,last_line_orig,bcolors.ENDC))
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
                    if debug: print('LOOKING_FOR_PROMPT:',last_but_one_line,last_line)                
                    output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                              replace('\x1b[K','').replace('\n{master}\n','')
                    if '--More--' or '---(more' in buff.strip(): 
                        chan.send('\x20')
                        if debug: print('SPACE_SENT.')
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
                if debug: print('LAST_LINE:',prompts,last_line)
                buff = chan.recv(9999)
                output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                          replace('\x1b[K','').replace('\n{master}\n','')
                if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
                if debug: print('BUFFER:' + buff)
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
                CGI_CLI.uprint(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (output) + bcolors.ENDC)
        except Exception as e: CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']')
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
                    CGI_CLI.uprint(exc_text)
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
                        CGI_CLI.uprint(exc_text)
                        LCMD.fp.write(exc_text + '\n')                
                    if os_output and printall: CGI_CLI.uprint(os_output)
                    LCMD.fp.write(os_output + '\n')
                    os_outputs.append(os_output)
        return os_outputs

    @staticmethod
    def eval_command(cmd_data = None, logfilename = None, printall = None):
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
                    LCMD.fp.write('EVAL_PROBLEM[' + str(e) + ']\n')
        return local_output
        
    @staticmethod
    def exec_command(cmd_data = None, logfilename = None, printall = None):
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)): 
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EXEC: %s" % (cmd_data))
                LCMD.fp.write('EXEC: ' + cmd_data + '\n')
                ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                try:
                    edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
                except Exception as e: 
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')                    
        return None


    @staticmethod
    def exec_command_try_except(cmd_data = None, logfilename = None, printall = None):
        """
        NOTE: This method can access global variable, expects '=' in expression, 
              in case of except assign value None
        """
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)): 
            with open(logfilename,"a+") as LCMD.fp:
                try:
                    if '=' in cmd_data:
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
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')                
        return None




            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
USERNAME, PASSWORD = CGI_CLI.init_cgi()
CGI_CLI.print_args()

device = None
if CGI_CLI.data.get("device"):
    device = CGI_CLI.data.get("device")

# rcmd_data = {
    # 'cisco_ios':[],
    # 'cisco_xr':[],
    # 'juniper':[],
    # 'huawei':[],
    # 'linux':[],
# }
# lcmd_data = {
    # 'windows':['whoami'],
    # 'unix':['whoami'],
# }

xr_config = """!
interface Loopback10  
% for item in loopback_0_config:
${item}
% endfor
!
!
interface Loopback0
 no ipv4 address
 no ipv6 address 
% for item in loopback_200_config:
${item}
% endfor
!
!
no interface Loopback200
!
!
no logging source-interface Loopback0
logging source-interface Loopback10
!
domain lookup source-interface Loopback10
!
tacacs source-interface Loopback10 vrf default
!
snmp-server trap-source Loopback10
!
ftp client source-interface Loopback10
!
ntp
 source Loopback10
!
flow exporter-map ICX
 source Loopback10
!
tftp client source-interface Loopback10
!
ssh client source-interface Loopback10
!
!
router isis PAII
!
 !
 interface Loopback10
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
  no interface Loopback200
 !
!
router bgp 5511
% for item in neighbor_groups:
neighbor-group ${item}
 update-source Loopback10 
% endfor
!
!
router isis PAII
 address-family ipv4 unicast
  mpls traffic-eng router-id Loopback0
 !
!
!
router bgp 5511
 bgp router-id ${loopback_200_address}
! 
"""

undo_xr_config = """!
interface Loopback0 
% for item in loopback_0_config:
${item}
% endfor
!
!
!
interface Loopback200
% for item in loopback_200_config:
${item}
% endfor
!
!
no interface Loopback10
!
no logging source-interface Loopback10
logging source-interface Loopback0
!
domain lookup source-interface Loopback0
!
tacacs source-interface Loopback0 vrf default
!
snmp-server trap-source Loopback0
!
ftp client source-interface Loopback0
!
ntp
 source Loopback0
!
flow exporter-map ICX
 source Loopback0
!
tftp client source-interface Loopback0
!
ssh client source-interface Loopback0
!
!
router isis PAII
!
no interface Loopback10
 !
 interface Loopback200
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
router bgp 5511
% for item in neighbor_groups:
neighbor-group ${item}
 update-source Loopback0 
% endfor
!
!
router isis PAII
 address-family ipv4 unicast
  mpls traffic-eng router-id Loopback0
!
!
!
router bgp 5511
 bgp router-id ${loopback_200_address}
!
"""

if device:
    rcmd_outputs = RCMD.connect(device, username = USERNAME, password = PASSWORD)
    
    if RCMD.router_type == 'cisco_xr':
        if not CGI_CLI.data.get('rollback'):
            collector_cmd = {'cisco_xr':['sh run interface loopback 0','sh run interface loopback 200',
            "show running-config router bgp | utility egrep 'neighbor-group|update-source' | exclude use neighbor-group"]}

            rcmd_outputs = RCMD.run_commands(collector_cmd, printall = True)
    
            loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface Loopback0\n')[1].replace('Loopback0','Loopback10').strip().split('!')[0] + '!').splitlines()
            loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface Loopback200\n')[1].replace('Loopback200','Loopback0').strip().split('!')[0] + '!').splitlines()
            try:    loopback_200_address = rcmd_outputs[1].split('ipv4 address')[1].split()[0].strip()
            except: loopback_200_address = str()
            try: 
                neighbor_groups = re.findall(r'neighbor-group\s+[0-9a-zA-Z\-\.\@\_]+$\s+update-source Loopback0', rcmd_outputs[2], re.MULTILINE)
                neighbor_groups = [ item.splitlines()[0].replace('neighbor-group','').strip() for item in neighbor_groups ] 
            except: neighbor_groups = []

            data = {}        
            data['loopback_0_config']    = loopback_0_config
            data['loopback_200_config']  = loopback_200_config
            data['neighbor_groups']      = neighbor_groups
            data['loopback_200_address'] = loopback_200_address

            CGI_CLI.uprint(data, name = True, jsonprint = True, color = 'blue')
            CGI_CLI.uprint('\n\n')

            config_string = str()
            mytemplate = Template(xr_config,strict_undefined=True)
            config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
        else:
            ### UNDO/ROLLBACK ###
            collector_cmd = {'cisco_xr':['sh run interface loopback 10','sh run interface loopback 0',
            "show running-config router bgp | utility egrep 'neighbor-group|update-source' | exclude use neighbor-group"]}

            rcmd_outputs = RCMD.run_commands(collector_cmd, printall = True)
            
            loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface Loopback10\n')[1].replace('Loopback10','Loopback0').strip().split('!')[0] + '!').splitlines()
            loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface Loopback0\n')[1].replace('Loopback0','Loopback200').strip().split('!')[0] + '!').splitlines()
            try:    loopback_200_address = rcmd_outputs[1].split('ipv4 address')[1].split()[0].strip()
            except: loopback_200_address = str()
            try: 
                neighbor_groups = re.findall(r'neighbor-group\s+[0-9a-zA-Z\-\.\@\_]+$\s+update-source Loopback10', rcmd_outputs[2], re.MULTILINE)
                neighbor_groups = [ item.splitlines()[0].replace('neighbor-group','').strip() for item in neighbor_groups ] 
            except: neighbor_groups = []

            data = {}        
            data['loopback_0_config']    = loopback_0_config
            data['loopback_200_config']  = loopback_200_config
            data['neighbor_groups']      = neighbor_groups
            data['loopback_200_address'] = loopback_200_address

            CGI_CLI.uprint(data, name = True, jsonprint = True, color = 'blue')
            CGI_CLI.uprint('\n\n')

            config_string = str()
            mytemplate = Template(undo_xr_config,strict_undefined=True)
            config_string += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'        



        ### PUSH CONFIG TO DEVICE ##########################################################
        CGI_CLI.uprint('CONFIG:\n', tag = 'h1', color = 'blue') 
        CGI_CLI.uprint(config_string)    

        splitted_config = copy.deepcopy(config_string)
        try: splitted_config = str(splitted_config.decode("utf-8")).splitlines()
        except: splitted_config = [] 

        rcmd_outputs = RCMD.run_commands(cmd_data = splitted_config, conf = True, printall = True, sim_config = CGI_CLI.data.get('sim',None))        
        
        config_problem = None
        for rcmd_output in rcmd_outputs: 
            if 'INVALID INPUT' in rcmd_output.upper() or 'INCOMPLETE COMMAND' in rcmd_output.upper():
                config_problem = True
                CGI_CLI.uprint('\nCONFIGURATION PROBLEM FOUND:', color = 'red')
                CGI_CLI.uprint('%s' % (rcmd_output), color = 'darkorchid')
        try:        
            if 'FAILED' in rcmd_outputs[-1].upper() or 'ERROR' in rcmd_outputs[-1].upper() or config_problem:
                CGI_CLI.uprint('COMMIT FAILED!' , tag = 'h1', tag_id = 'submit-result', color = 'red')
            else: CGI_CLI.uprint('COMMIT SUCCESSFULL.' , tag = 'h1', tag_id = 'submit-result', color = 'green')    
        except: pass
                
    RCMD.disconnect()

