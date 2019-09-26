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
        disconnect = None, printall = None):
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
    def run_command(cmd_line = None, printall = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        """
        last_output = str()
        if not printall: printall = RCMD.printall
        if RCMD.ssh_connection and cmd_line:
            if RCMD.use_module == 'netmiko':
                last_output = RCMD.ssh_connection.send_command(cmd_line)
            elif RCMD.use_module == 'paramiko':
                last_output, new_prompt = RCMD.ssh_send_command_and_read_output( \
                    RCMD.ssh_connection, RCMD.DEVICE_PROMPTS, cmd_line, printall = printall)
                if new_prompt: RCMD.DEVICE_PROMPTS.append(new_prompt)
            if RCMD.fp: RCMD.fp.write('REMOTE_COMMAND: ' + cmd_line + '\n' + last_output + '\n')    
        return last_output 

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None):
        """
        FUNCTION: run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT, 
                 - list of strings or string, OS TYPE DEPENDENT    
        conf     - True/False, go to config mode        
        """
        command_outputs = str()
        if not printall: printall = RCMD.printall
        if not conf: conf = RCMD.conf

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
                command_outputs = []
                ### CONFIG MODE FOR NETMIKO ################################
                if conf and RCMD.use_module == 'netmiko':                
                    RCMD.ssh_connection.send_config_set(cmd_list)
                else:    
                    ### CONFIG MODE FOR PARAMIKO ###############################
                    conf_output = ''                    
                    if conf and RCMD.use_module == 'paramiko':    
                        if RCMD.router_type=='cisco_ios': conf_output = RCMD.run_command('config t')
                        elif RCMD.router_type=='cisco_xr': conf_output = RCMD.run_command('config t')
                        elif RCMD.router_type=='juniper': conf_output = RCMD.run_command('configure')
                        elif RCMD.router_type=='huawei': conf_output = RCMD.run_command('system-view')
                    if conf_output: command_outputs.append('CONFIG: ' + conf_output)    
                    ### PROCESS COMMANDS #######################################
                    for cmd_line in cmd_list:
                        command_outputs.append(RCMD.run_command(cmd_line))
                    ### EXIT FROM CONFIG MODE FOR PARAMIKO #####################    
                    if conf and RCMD.use_module == 'paramiko':
                        ### COMMIT SECTION -------------------------------------
                        commit_output = ""                    
                        if RCMD.router_type=='cisco_ios': pass
                        elif RCMD.router_type=='cisco_xr': commit_output = RCMD.run_command('commit')
                        elif RCMD.router_type=='juniper': commit_output = RCMD.run_command('commit')
                        elif RCMD.router_type=='huawei': commit_output = RCMD.run_command('save')
                        if commit_output: command_outputs.append('COMMIT: ' + commit_output)
                        if 'Failed to commit' in commit_output:
                            if RCMD.router_type=='cisco_xr': 
                                failed_output = RCMD.run_command('show configuration failed'),
                                command_outputs.append('FAILED_COMMIT: ' + failed_output)
                                #show commit changes diff
                                #commit show-error
                        ### EXIT SECTION ---------------------------------------
                        if RCMD.router_type=='cisco_ios': RCMD.run_command('exit') 
                        elif RCMD.router_type=='cisco_xr': RCMD.run_command('exit')
                        elif RCMD.router_type=='juniper': RCMD.run_command('exit')
                        elif RCMD.router_type=='huawei': RCMD.run_command('return')                   
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
        chan.send(send_data + '\n')
        time.sleep(0.3)
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
        columns, lines = [], []
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute(sql_command)
                records = cursor.fetchall()
                ### OUTPUTDATA STRUCTURE IS: '[(SQL_LINE1),...]' --> records[0] = UNPACK []
                ### WORKARROUND FOR BYTEARRAYS WHICH ARE NOT JSONIZABLE
                for line in records:
                    for item in line:
                        try: new_item = item.decode('utf-8')
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
    
    # def get_one_from_list(list_of_dictionaries, number = None):
        # return_value = {}
        # if number: list_order = number
        # else: list_order = 0
        # try: return_value = list_of_dictionaries[list_order]
        # except: return_value = list_of_dictionaries
        # return return_value    

    # def dict_deep_get(dictionary, *keys):
    #     return reduce(lambda d, key: d.get(key, None) if isinstance(d, (dict,collections.OrderedDict) else None, keys, dictionary)


def do_precheck(rcmd_outputs = None, checklist = None, cmd_list = None):
    """
    precheck fails if:
    contains: string or list of strings(items and)
    or
    not_in: not_string or not_list of strings(items and)
    """
    precheck_problem, i = False, 0
    for output in rcmd_outputs:
        try:
            try: command = str(cmd_list[i])
            except: command = '---'
            if isinstance(checklist[i], (dict,collections.OrderedDict)):
                CGI_CLI.uprint('CMD: ' + command + '        CHECK IF:' + str(checklist[i]), color = 'blue')
                CGI_CLI.uprint(output, color = 'black')
                if checklist[i].get('contains'):
                    contains_value = checklist[i].get('contains')
                    if isinstance(contains_value, (list,tuple)):
                        for item in contains_value:
                            sub_check_ok = True
                            if item in output.replace(command,''): pass 
                            else:
                                sub_check_ok = False
                        if sub_check_ok: CGI_CLI.uprint('CHECK OK.\n',color = 'green')
                        else:
                            precheck_problem = True                            
                            CGI_CLI.uprint('CHECK FAILED.\n', color = 'red')                                         
                    if isinstance(contains_value, six.string_types): 
                        if checklist[i].get('contains') in output.replace(command,''): CGI_CLI.uprint('CHECK OK.\n',color = 'green')
                        else:
                            precheck_problem = True                            
                            CGI_CLI.uprint('CHECK FAILED.\n', color = 'red')                           
                if checklist[i].get('not_in'):
                    not_in_value = checklist[i].get('not_in')                            
                    if isinstance(not_in_value, (list,tuple)):
                        for item in not_in_value:
                            sub_check_ok = True
                            if not item in output.replace(command,''): pass 
                            else:
                                sub_check_ok = False
                        if sub_check_ok: CGI_CLI.uprint('CHECK OK.\n',color = 'green')
                        else:
                            precheck_problem = True                            
                            CGI_CLI.uprint('CHECK FAILED.\n', color = 'red')                                                        
                    if isinstance(not_in_value, six.string_types): 
                        if not checklist[i].get('not_in') in output.replace(command,''): CGI_CLI.uprint('CHECK OK.\n',color = 'green')
                        else: 
                            precheck_problem = True 
                            CGI_CLI.uprint('CHECK FAILED.\n', color = 'red')
        except Exception as e: CGI_CLI.uprint('PRE-CHECK_PROBLEM[' + str(e) + ']')
        i += 1
    return precheck_problem

            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
CGI_CLI()
USERNAME, PASSWORD = CGI_CLI.init_cgi()

rcmd_data1 = {
    'cisco_ios':['show version'],
    'cisco_xr':['show version'],
    'juniper':['show version'],
    'huawei':['display version'],
    'linux':['uname'],
}

lcmd_data2 = {
    'windows':['whoami'],
    'unix':['whoami'],
}


new_pe_router, ipsec_gw_router, old_huawei_router, config = str(), str(), str(), str()

if CGI_CLI.cgi_active:    
    sql_inst = sql_interface(host='localhost', user='cfgbuilder', \
        password='cfgbuildergetdata', database='rtr_configuration')

    cgi_data = copy.deepcopy(CGI_CLI.data)        
    data = collections.OrderedDict()    
    data["cgi_data"] = cgi_data

    collector_list = sql_inst.sql_read_records_to_dict_list(from_string = 'ipxt_data_collector', where_string = "session_id = '%s'" % (cgi_data.get('session_id','UNKNOWN')))
    try: data["ipxt_data_collector"] = collector_list[0]
    except: data["ipxt_data_collector"] = collections.OrderedDict()
    
    try: old_huawei_router = data["ipxt_data_collector"].get("device_name",str())
    except: old_huawei_router = str()

    gw_pe_list = sql_inst.sql_read_records_to_dict_list(from_string = 'ipxt_gw_pe', where_string = "old_pe_router = '%s'" % (old_huawei_router))
    try: data["ipxt_gw_pe"] = gw_pe_list[0]
    except: data["ipxt_gw_pe"] = collections.OrderedDict()
    
    try: new_pe_router = data["ipxt_gw_pe"].get('new_pe_router',str())
    except: new_pe_router = str()

    try: ipsec_gw_router = data["ipxt_gw_pe"].get('ipsec_gw_router',str())
    except: ipsec_gw_router = str()

    ipsec_ipxt_table_list = sql_inst.sql_read_records_to_dict_list(from_string = 'ipsec_ipxt_table', where_string = "ipsec_rtr_name = '%s'" % (ipsec_gw_router))
    try: data["ipsec_ipxt_table"] = ipsec_ipxt_table_list[0]
    except: data["ipsec_ipxt_table"] = collections.OrderedDict()   
    
    try: config_data = sql_inst.sql_read_records_to_dict_list(from_string = 'ipxt_configurations', \
        where_string = "session_id = '%s'" % (CGI_CLI.data.get('session_id','')))[0]
    except: config_data = collections.OrderedDict()   

    PE_preparation_precheck = {'cisco_xr':[\
        'show access-list %s-IN' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN')),
        'show vrf %s' %(data['ipxt_data_collector'].get('vrf_name','UNKNOWN').replace('.','@')),
        'show rpl prefix-set %s-IN' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN')), 
        'show policy-map list %s-OUT' % (data['ipxt_data_collector'].get('customer_name','UNKNOWN')),
        'show policy-map list %s-IN' % (data['ipxt_data_collector'].get('customer_name','UNKNOWN')),
        'show interface %s.%s' % (data['ipsec_ipxt_table'].get('int_id','UNKNOWN'),data['ipxt_data_collector'].get('vlan_id','UNKNOWN')),
        'sh flow exporter-map ICX',
        'show flow monitor-map ICX',
        'show sampler-map ICX',
        'sh run | i IPXT.COS-OUT',
        'sh run | i IPXT.COS-IN',
        'show class-map GOLD',
        'show class-map SILVER',
        'sh running-config | i route-policy %s-IN' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN')),
        'show bgp neighbor-group %s configuration' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN')),
        'sh running-config | i route-policy DENY-ALL',
        'sh running-config | i route-policy NO-EXPORT-INTERCO',
        'show static vrf %s topology' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN').replace('.','@'))
        ]}

    checklist_PE_preparation_precheck = {'cisco_xr':[\
        {'contains':'No such access-list %s-IN' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN'))},
        {'not_in':'%s' %(data['ipxt_data_collector'].get('vrf_name','UNKNOWN').replace('.','@'))},
        {'contains':'The prefix-set (%s-IN) does not appear to exist' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN'))}, 
        {'contains':'Policymap \'%s-OUT\' of type \'qos\' not found' % (data['ipxt_data_collector'].get('customer_name','UNKNOWN'))},
        {'contains':'Policymap \'%s-IN\' of type \'qos\' not found' % (data['ipxt_data_collector'].get('customer_name','UNKNOWN'))},
        {'contains':'Interface not found (%s.%s)' % (data['ipsec_ipxt_table'].get('int_id','UNKNOWN'),data['ipxt_data_collector'].get('vlan_id','UNKNOWN'))},
        {'contains':'Flow Exporter Map : ICX'},
        {'contains':'Flow Monitor Map : ICX'},
        {'contains':'Sampler Map : ICX'},
        {'contains':'policy-map IPXT.COS-OUT'},
        {'contains':'policy-map IPXT.COS-IN'},
        {'contains':'1) ClassMap: GOLD    Type: qos'},
        {'contains':'1) ClassMap: SILVER    Type: qos'},
        {'not_in':'route-policy %s-IN' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN'))},
        {'not_in':'%s' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN'))},
        {'contains':['route-policy DENY-ALL']},
        {'contains':'route-policy NO-EXPORT-INTERCO'},
        {'contains':'No routes in this topology'}
        ]}
        
    GW_preparation_precheck = {'cisco_ios':[\
        'show vrf LOCAL.%s' %(data['ipxt_data_collector'].get('vlan_id','UNKNOWN')), 
        'show interface %s.%s' % (data['ipsec_ipxt_table'].get('ipsec_int_id','UNKNOWN'),data['ipxt_data_collector'].get('vlan_id','UNKNOWN'))
        ]}
        
    checklist_GW_preparation_precheck = {'cisco_ios':[\
        {'contains':'LOCAL.%s' % (data['ipxt_data_collector'].get('vlan_id','UNKNOWN'))},
        {'contains':"% Invalid input detected at '^' marker."}
        ]}        

    PE_migration_precheck = {'cisco_xr':[\
        'show bgp neighbor-group %s configuration' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN')), 
        'sh running-config | i route-policy PASS-ALL'
        ]}
        
    checklist_PE_migration_precheck = {'cisco_xr':[\
        {'contains':'neighbor-group %s' % (data['ipxt_data_collector'].get('vrf_name','UNKNOWN'))},
        {'contains':"route-policy PASS-ALL"}
        ]} 

    GW_migration_precheck = {'cisco_ios':[\
        'sh run | i ip route vrf LOCAL.%s' % (data['ipxt_data_collector'].get('vlan_id','UNKNOWN')), 
        ]}
        
    checklist_GW_migration_precheck = {'cisco_ios':[\
        {'not_in':'ip route vrf LOCAL.%s' % (data['ipxt_data_collector'].get('vlan_id','UNKNOWN'))},
        ]}         
 

    PE_OLD_migration_precheck = {'huawei':[
        'display interface %s' % (data['ipxt_data_collector'].get('old_pe_interface','UNKNOWN'))
        ]}
        
    checklist_PE_OLD_migration_precheck = {'huawei':[
        {'not_in':'%s current state : Administratively DOWN' % (data['ipxt_data_collector'].get('old_pe_interface','UNKNOWN'))},
        ]} 

    PE_OLD_migration_postcheck = {'huawei':[
        'display interface %s' % (data['ipxt_data_collector'].get('old_pe_interface','UNKNOWN'))
        ]}
        
    checklist_PE_OLD_migration_postcheck = {'huawei':[
        {'contains':'%s current state : Administratively DOWN' % (data['ipxt_data_collector'].get('old_pe_interface','UNKNOWN'))},
        ]} 
        
    device, conf ,config, result_str, checklist = str(), None, str(), str(), str()    
    if CGI_CLI.submit_form == 'Submit PE preparation precheck':
        result_str = 'PE PREPARATION CONFIGURATION PRECHECK'
        device = copy.deepcopy(new_pe_router)
        config = '\n'.join(PE_preparation_precheck.get('cisco_xr',str()))
        checklist = checklist_PE_preparation_precheck.get('cisco_xr',[])
        conf = False
    elif CGI_CLI.submit_form == 'Submit GW preparation precheck':
        result_str = 'GW PREPARATION CONFIGURATION PRECHECK'
        device = copy.deepcopy(ipsec_gw_router)
        config = '\n'.join(GW_preparation_precheck.get('cisco_ios',str()))
        checklist = checklist_GW_preparation_precheck.get('cisco_ios',[])
        conf = False
    # elif CGI_CLI.submit_form == 'Submit OLD PE preparation precheck':
        # result_str = 'PE-OLD PREPARATION CONFIGURATION PRECHECK'
        # device = copy.deepcopy(ipsec_gw_router)
        # conf = False
    elif CGI_CLI.submit_form == 'Submit PE migration precheck':
        result_str = 'PE MIGRATION CONFIGURATION PRECHECK'
        device = copy.deepcopy(new_pe_router)
        config = '\n'.join(PE_migration_precheck.get('cisco_xr',str()))
        checklist = checklist_PE_migration_precheck.get('cisco_xr',[])        
        conf = False
    elif CGI_CLI.submit_form == 'Submit GW migration precheck':
        result_str = 'PE MIGRATION CONFIGURATION PRECHECK'
        device = copy.deepcopy(ipsec_gw_router)
        config = '\n'.join(GW_migration_precheck.get('cisco_ios',str()))
        checklist = checklist_GW_migration_precheck.get('cisco_ios',[])       
        conf = False
    elif CGI_CLI.submit_form == 'Submit OLD PE migration precheck':
        result_str = 'PE-OLD MIGRATION CONFIGURATION PRECHECK'
        device = copy.deepcopy(old_huawei_router)        
        config = '\n'.join(PE_OLD_migration_precheck.get('huawei',str()))
        checklist = checklist_PE_OLD_migration_precheck.get('huawei',[]) 
        conf = False        
    elif CGI_CLI.submit_form == 'Submit PE preparation':
        result_str = 'PE PREPARATION CONFIGURATION COMMIT'
        device = copy.deepcopy(new_pe_router)
        config = config_data.get("pe_config_preparation",str())
        conf = True
    elif CGI_CLI.submit_form == 'Submit GW preparation':
        result_str = 'GW PREPARATION CONFIGURATION COMMIT'    
        device = copy.deepcopy(ipsec_gw_router)
        config = config_data.get("gw_config_preparation",str())
        conf = True
    elif CGI_CLI.submit_form == 'Submit PE migration':
        result_str = 'PE MIGRATION CONFIGURATION COMMIT'
        device = copy.deepcopy(new_pe_router)
        config = config_data.get("pe_config_migration",str())
        conf = True
    elif CGI_CLI.submit_form == 'Submit GW migration':
        result_str = 'GW MIGRATION CONFIGURATION COMMIT'    
        device = copy.deepcopy(ipsec_gw_router)
        config = config_data.get("gw_config_migration",str())
        conf = True
    elif CGI_CLI.submit_form == 'Submit OLD PE shutdown':
        result_str = 'PE-OLD MIGRATION CONFIGURATION COMMIT'    
        device = copy.deepcopy(old_huawei_router)
        config = config_data.get("old_pe_config_migration_shut",str())
        conf = True        
    elif CGI_CLI.submit_form == 'Rollback GW preparation':
        result_str = 'GW PREPARATION ROLLBACK CONFIGURATION COMMIT'    
        device = copy.deepcopy(ipsec_gw_router)
        config = config_data.get("rollback_gw_preparation",str())
        conf = True     
    elif CGI_CLI.submit_form == 'Rollback PE preparation':
        result_str = 'PE PREPARATION ROLLBACK CONFIGURATION COMMIT'     
        device = copy.deepcopy(new_pe_router)
        config = config_data.get("rollback_pe_preparation",str())
        conf = True 
    elif CGI_CLI.submit_form == 'Rollback GW migration':
        result_str = 'GW MIGRATION ROLLBACK CONFIGURATION COMMIT'
        device = copy.deepcopy(ipsec_gw_router)
        config = config_data.get("rollback_gw_migration",str())
        conf = True     
    elif CGI_CLI.submit_form == 'Rollback PE migration':
        result_str = 'PE MIGRATION ROLLBACK CONFIGURATION COMMIT'    
        device = copy.deepcopy(new_pe_router)
        config = config_data.get("rollback_pe_migration",str())
        conf = True 
    elif CGI_CLI.submit_form == 'Rollback OLD PE shutdown':
        result_str = 'PE-OLD MIGRATION ROLLBACK CONFIGURATION COMMIT'    
        device = copy.deepcopy(old_huawei_router)
        config = config_data.get("rollback_oldpe_migration",str())
        conf = True           
    else:
        CGI_CLI.uprint('SUBMIT (%s) BUTTON NOT RECOGNIZED!' % (CGI_CLI.submit_form),tag = 'h1', color = 'red')
        sys.exit(0)
        
    ### WRITE CONFIG TO ROUTER ######################################################
    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()

    CGI_CLI.print_args()
    #CGI_CLI.print_env()
    CGI_CLI.uprint(data, jsonprint = True, color = 'blue')
    CGI_CLI.uprint(config_data, jsonprint = True)     
    #CGI_CLI.uprint(PE_precheck, name = True, jsonprint = True)
    #CGI_CLI.uprint(checklist_PE_precheck, name = True, jsonprint = True)
    CGI_CLI.uprint(str(CGI_CLI.submit_form), tag = 'h1', color = 'blue')
    CGI_CLI.uprint('PE = %s, GW = %s, OLD_PE = %s'%(new_pe_router,ipsec_gw_router,old_huawei_router), tag = 'h3', color = 'black')     
    CGI_CLI.uprint('DEVICE = %s, config_mode(%s) , SERVER = %s'%(device,str(conf),str(iptac_server)), tag = 'h1')    
    CGI_CLI.uprint('\nCONFIG:\n------------\n\n%s'%(config))


    ### TEST_ONLY DELETION FROM CONFIG    
    if iptac_server == 'iptac5' and conf == True: config = config.replace('flow ipv4 monitor ICX sampler ICX ingress','')

    splitted_config = copy.deepcopy(config)
    try: splitted_config = str(splitted_config.decode("utf-8")).splitlines()
    except: splitted_config = []

    data_to_write = {
        'cisco_ios':splitted_config,
        'cisco_xr':splitted_config,
        'juniper':splitted_config,
        'huawei':splitted_config,
        'linux':[],
    }

    if device:
        rcmd_outputs = RCMD.connect(device = device, cmd_data = splitted_config, \
            username = CGI_CLI.username, password = CGI_CLI.password, conf = conf)
        CGI_CLI.uprint('\n'.join(rcmd_outputs) , color = 'blue')         
        RCMD.disconnect()
        
        config_problem = False
        if conf:
            for rcms_output in rcmd_outputs: 
                if 'INVALID INPUT' in rcms_output.upper() or 'INCOMPLETE COMMAND' in rcms_output.upper():
                    config_problem = True
                    CGI_CLI.uprint('\nCONFIGURATION PROBLEM FOUND:', color = 'red')
                    CGI_CLI.uprint('%s' % (rcms_output), color = 'darkorchid')
            try:        
                if 'FAILED' in rcmd_outputs[-1].upper() or 'ERROR' in rcmd_outputs[-1].upper() or config_problem:
                    CGI_CLI.uprint('%s FAILED!' % (result_str), tag = 'h1', tag_id = 'submit-result', color = 'red')
                else: CGI_CLI.uprint('%s SUCCESSFULL.' % (result_str), tag = 'h1', tag_id = 'submit-result', color = 'green')    
            except: pass
        else:
            CGI_CLI.uprint('\nPRECHECK:\n------------------\n',tag = 'h1', color = 'blue')            
            precheck_problem = True 
            if checklist and config:            
                splitted_config = copy.deepcopy(config).splitlines()
                precheck_problem = do_precheck(rcmd_outputs, checklist, splitted_config)
            if precheck_problem: CGI_CLI.uprint('%s FAILED!' % (result_str), tag = 'h1', tag_id = 'submit-result', color = 'red')
            else: CGI_CLI.uprint('%s SUCCESSFULL.' % (result_str), tag = 'h1', tag_id = 'submit-result', color = 'green')           