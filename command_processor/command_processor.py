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
#import cgitb; cgitb.enable()
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
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        return None

    @staticmethod 
    def uprint(text, tag = None):
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
    def print_args():
        if CGI_CLI.cgi_active:
            try: print_string = 'CGI_args=' + json.dumps(CGI_CLI.data) + ' <br/>'
            except: print_string = 'CGI_args=' + ' <br/>'                
        else: print_string = 'CLI_args=%s \n' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string        


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


class CMD_PROC():
    @staticmethod
    def init(device = None, cmd_lists = None, username = None, password = None, \
        use_module = 'paramiko', logfilename = None, timeout = 60):
        import atexit; atexit.register(CMD_PROC.__cleanup__)
        if device:
            CMD_PROC.ssh_connection = None
            CMD_PROC.TIMEOUT = timeout
            CMD_PROC.use_module = use_module
            CMD_PROC.logfilename = logfilename
            CMD_PROC.USERNAME = username
            CMD_PROC.PASSWORD = password
            CMD_PROC.router_prompt = None
            try: CMD_PROC.DEVICE_HOST = device.split(':')[0]
            except: CMD_PROC.DEVICE_HOST = str()
            try: CMD_PROC.DEVICE_PORT = device.split(':')[1]
            except: CMD_PROC.DEVICE_PORT = '22'
            CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, CMD_PROC.DEVICE_HOST, CMD_PROC.DEVICE_PORT)+24 * '.')
            CMD_PROC.router_type, CMD_PROC.router_prompt = CMD_PROC.detect_router_by_ssh()
            if not router_type in KNOWN_OS_TYPES:
                CGI_CLI.uprint('%sUNSUPPORTED DEVICE TYPE: %s , BREAK!%s' % \
                    (bcolors.MAGENTA, CMD_PROC.router_type, bcolors.ENDC))
            else: CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (CMD_PROC.router_type))
            ####################################################################
            if CMD_PROC.router_type == 'cisco_ios':
                CMD_PROC.CMD = cmd_lists.CMD_IOS_XE
                CMD_PROC.DEVICE_PROMPTS = [ \
                    '%s%s#'%(args.device.upper(),''), \
                    '%s%s#'%(args.device.upper(),'(config)'), \
                    '%s%s#'%(args.device.upper(),'(config-if)'), \
                    '%s%s#'%(args.device.upper(),'(config-line)'), \
                    '%s%s#'%(args.device.upper(),'(config-router)')  ]
                CMD_PROC.TERM_LEN_0 = "terminal length 0"
                CMD_PROC.EXIT = "exit"
            elif CMD_PROC.router_type == 'cisco_xr':
                CMD_PROC.CMD = cmd_lists.CMD_IOS_XR
                CMD_PROC.DEVICE_PROMPTS = [ \
                    '%s%s#'%(args.device.upper(),''), \
                    '%s%s#'%(args.device.upper(),'(config)'), \
                    '%s%s#'%(args.device.upper(),'(config-if)'), \
                    '%s%s#'%(args.device.upper(),'(config-line)'), \
                    '%s%s#'%(args.device.upper(),'(config-router)')  ]
                CMD_PROC.TERM_LEN_0 = "terminal length 0"
                CMD_PROC.EXIT = "exit"
            elif CMD_PROC.router_type == 'juniper':
                CMD_PROC.CMD = cmd_lists.CMD_JUNOS
                CMD_PROC.DEVICE_PROMPTS = [ \
                     USERNAME + '@' + args.device.upper() + '> ', # !! Need the space after >
                     USERNAME + '@' + args.device.upper() + '# ' ]
                CMD_PROC.TERM_LEN_0 = "set cli screen-length 0"
                CMD_PROC.EXIT = "exit"
            elif CMD_PROC.router_type == 'huawei' :
                CMD_PROC.CMD = cmd_lists.CMD_VRP
                CMD_PROC.DEVICE_PROMPTS = [ \
                    '<' + args.device.upper() + '>',
                    '[' + args.device.upper() + ']',
                    '[~' + args.device.upper() + ']',
                    '[*' + args.device.upper() + ']' ]
                CMD_PROC.TERM_LEN_0 = "screen-length 0 temporary"     #"screen-length disable"
                CMD_PROC.EXIT = "quit"
            elif CMD_PROC.router_type == 'linux':
                CMD = cmd_lists.CMD_LINUX
                CMD_PROC.DEVICE_PROMPTS = [ ]
                CMD_PROC.TERM_LEN_0 = ''     #"screen-length disable"
                CMD_PROC.EXIT = "exit"
            else: CMD_PROC.CMD = cmd_lists.CMD_LOCAL
            # ADD PROMPT TO PROMPTS LIST
            if CMD_PROC.router_prompt: CMD_PROC.DEVICE_PROMPTS.append(CMD_PROC.router_prompt)
            ### START SSH CONNECTION AGAIN #####################################
            try:
                if CMD_PROC.use_module == 'netmiko':
                    CMD_PROC.ssh_connection = netmiko.ConnectHandler(device_type = router_type, \
                        ip = CMD_PROC.DEVICE_HOST, port = int(CMD_PROC.DEVICE_PORT), \
                        username = CMD_PROC.USERNAME, password = CMD_PROC.PASSWORD)
                elif CMD_PROC.use_module == 'paramiko':
                    CMD_PROC.client = paramiko.SSHClient()
                    CMD_PROC.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    CMD_PROC.client.connect(CMD_PROC.DEVICE_HOST, port=int(CMD_PROC.DEVICE_PORT), \
                        username=CMD_PROC.USERNAME, password=CMD_PROC.PASSWORD,look_for_keys=False)
                    CMD_PROC.ssh_connection = CMD_PROC.client.invoke_shell()
                    CMD_PROC.ssh_connection.settimeout(TIMEOUT)
                    CMD_PROC.output, CMD_PROC.forget_it = CMD_PROC.ssh_send_command_and_read_output(CMD_PROC.ssh_connection,CMD_PROC.DEVICE_PROMPTS,CMD_PROC.TERM_LEN_0)
                    CMD_PROC.output2, CMD_PROC.forget_it = CMD_PROC.ssh_send_command_and_read_output(CMD_PROC.ssh_connection,CMD_PROC.DEVICE_PROMPTS,"")
                    CMD_PROC.output += CMD_PROC.output2
                ### WORK REMOTE or LOCAL =======================================
                if not CMD_PROC.logfilename:
                    if 'WIN32' in sys.platform.upper(): CMD_PROC.logfilename = 'nul'
                    else: CMD_PROC.logfilename = '/dev/null'
                with open(CMD_PROC.logfilename,"w+") as fp:
                    if CMD_PROC.output and not printcmdtologfile: fp.write(CMD_PROC.output)
                    ### process commands #######################################
                    for cmd_line_items in CMD_PROC.CMD:
                        pass



            except () as e:
                print(bcolors.FAIL + " ... EXCEPTION: (%s)" % (e) + bcolors.ENDC )
                sys.exit()
            except:
                CGI_CLI.uprint(bcolors.MAGENTA + " ... Connection error: %s " % (str(sys.exc_info()[:-1])) + bcolors.ENDC )
                sys.exit()
            finally:
                if CMD_PROC.ssh_connection:
                    if CMD_PROC.use_module == 'netmiko': ssh_connection.disconnect()
                    elif CMD_PROC.use_module == 'paramiko': client.close()

    @staticmethod
    def __cleanup__():
        if CMD_PROC.ssh_connection:
            if CMD_PROC.use_module == 'netmiko': CMD_PROC.ssh_connection.disconnect()
            elif CMD_PROC.use_module == 'paramiko': client.close()
        CGI_CLI.uprint('DEVICE %s:%s DONE.' % (CMD_PROC.DEVICE_HOST, CMD_PROC.DEVICE_PORT))

    @staticmethod
    def detect_router_by_ssh(debug = False):
        # detect device prompt
        def ssh_detect_prompt(chan, debug = False):
            output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
            chan.send('\t \n\n')
            while not (last_line and last_but_one_line and last_line == last_but_one_line):
                if debug: print('FIND_PROMPT:',last_but_one_line,last_line)
                buff = chan.recv(9999)
                output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                          replace('\x1b[K','').replace('\n{master}\n','')
                if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
                if debug: print('BUFFER:' + buff)
                try: last_line = output.splitlines()[-1].strip().replace('\x20','')
                except: last_line = 'dummyline1'
                try: last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
                except: last_but_one_line = 'dummyline2'
            prompt = output.splitlines()[-1].strip()
            if debug: CGI_CLI.uprint('DETECTED PROMPT: \'' + prompt + '\'')
            return prompt
        # bullet-proof read-until function , even in case of ---more---
        def ssh_read_until_prompt_bulletproof(chan,command,prompts,debug = False):
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
        router_os = str()
        client = paramiko.SSHClient()
        #client.load_system_host_keys()
        #client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(CMD_PROC.DEVICE_HOST, port = int(CMD_PROC.DEVICE_PORT), \
                username = CMD_PROC.USERNAME, password = CMD_PROC.PASSWORD)
            chan = client.invoke_shell()
            chan.settimeout(TIMEOUT)
            # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
            # \n\n get prompt as last line
            prompt = ssh_detect_prompt(chan, debug=False)
            #test if this is HUAWEI VRP
            if prompt and not router_os:
                command = 'display version | include (Huawei)\n'
                output = ssh_read_until_prompt_bulletproof(chan, command, [prompt], debug=debug)
                if 'Huawei Versatile Routing Platform Software' in output: router_os = 'vrp'
            #test if this is CISCO IOS-XR, IOS-XE or JUNOS
            if prompt and not router_os:
                command = 'show version\n'
                output = ssh_read_until_prompt_bulletproof(chan, command, [prompt], debug=debug)
                if 'iosxr-' in output or 'Cisco IOS XR Software' in output: router_os = 'ios-xr'
                elif 'Cisco IOS-XE software' in output: router_os = 'ios-xe'
                elif 'JUNOS OS' in output: router_os = 'junos'
            if prompt and not router_os:
                command = 'uname -a\n'
                output = ssh_read_until_prompt_bulletproof(chan, command, [prompt], debug=debug)
                if 'LINUX' in output.upper(): router_os = 'linux'
            if not router_os:
                CGI_CLI.uprint(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (output) + bcolors.ENDC)
        except (socket.timeout, paramiko.AuthenticationException) as e:
            CGI_CLI.uprint(bcolors.MAGENTA + " ... Connection closed: %s " % (e) + bcolors.ENDC )
            sys.exit()
        except:
            CGI_CLI.uprint(bcolors.MAGENTA + " ... Connection error: %s " % (str(sys.exc_info()[:-1])) + bcolors.ENDC )
            sys.exit()
        finally: client.close()
        netmiko_os = str()
        if router_os == 'ios-xe': netmiko_os = 'cisco_ios'
        if router_os == 'ios-xr': netmiko_os = 'cisco_xr'
        if router_os == 'junos': netmiko_os = 'juniper'
        if router_os == 'linux': netmiko_os = 'linux'
        if router_os == 'vrp': netmiko_os = 'huawei'
        return netmiko_os, prompt


    @staticmethod
    def run_remote_command(cli_line):
        if use_module == 'netmiko':
            last_output = ssh_connection.send_command(cli_line)
        elif use_module == 'paramiko':
            last_output, new_prompt = ssh_send_command_and_read_output( \
                ssh_connection,DEVICE_PROMPTS,cli_line,printall=printall)
            if new_prompt: DEVICE_PROMPTS.append(new_prompt)




            
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
if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): bcolors = nocolors


device = 'aaa'
cmd_list = ['b','a']
CMD_PROC.init(device, cmd_list)








