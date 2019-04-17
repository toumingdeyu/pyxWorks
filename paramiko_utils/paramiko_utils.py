#!/usr/bin/python

import sys, os, io, paramiko, json
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

if sys.version_info >= (3,0):
    import netmiko


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

TODAY            = datetime.datetime.now()
VERSION          = str(TODAY.year)[2:] + '.' + str(TODAY.month) + '.' + str(TODAY.day)
HELP             = "\nTry ' --help' for more information\n"

UNKNOW_HOST     = 'Name or service not known'
TIMEOUT         = 60
try:    HOMEDIR         = os.environ['HOME']
except: HOMEDIR         = str(os.path.dirname(os.path.abspath(__file__)))
try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()

print('HOMEDIR/WORKDIR: '+HOMEDIR)

set_ipv6line = str()
converted_ipv4 = str()
###############################################################################
#
# Generic list of commands
#
###############################################################################


# IOS-XE is only for IPsec GW
CMD_IOS_XE = [
			'show version',
            'show version'

              ]
CMD_IOS_XR = [
            'show version',
            'show version',

             ]
CMD_JUNOS = [
            'show version',
            'show version',

             ]
CMD_VRP = [
            'display version',
            'display version'
          ]
CMD_LINUX = [
            'who',
            'whoami',
            'free -m',
            'lspci'
            ]
###############################################################################
#
# Function and Class
#
###############################################################################




# huawei does not respond to snmp
def detect_router_by_ssh(device, debug = False):
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
        if debug: print('DETECTED PROMPT: \'' + prompt + '\'')
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
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try: PARAMIKO_HOST = device.split(':')[0]
    except: PARAMIKO_HOST = str()
    try: PARAMIKO_PORT = device.split(':')[1]
    except: PARAMIKO_PORT = '22'

    try:
        #connect(self, hostname, port=22, username=None, password=None, pkey=None, key_filename=None, timeout=None, allow_agent=True, look_for_keys=True, compress=False)
        client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), username=USERNAME, password=PASSWORD)
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
            print(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (output) + bcolors.ENDC)

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.MAGENTA + " ... Connection closed: %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    return router_os, prompt


def ssh_send_command_and_read_output(chan,prompts,send_data=str(),printall=True):
    output, exit_loop, timeout_counter = str(), False, 0
    # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
    if chan.recv_ready(): flush_buffer = chan.recv(9999)
    chan.send(send_data + '\n')
    time.sleep(0.1)
    if printall: print("%sCOMMAND: %s%s%s" % (bcolors.GREEN,bcolors.YELLOW,send_data,bcolors.ENDC))
    while not exit_loop:
        if chan.recv_ready():
            buff = chan.recv(9999)
            buff_read = buff.decode("utf-8").replace('\x0d','').replace('\x07','').\
                replace('\x08','').replace(' \x1b[1D','')
            output += buff_read
            if printall: print("%s%s%s" % (bcolors.GREY,buff_read,bcolors.ENDC))
        else: time.sleep(0.1); timeout_counter += 1
        # FIND LAST LINE, THIS COULD BE PROMPT
        try: last_line = output.splitlines()[-1].strip()
        except: last_line = str()
        # FILTER-OUT '(...)' FROM PROMPT IOS-XR/IOS-XE
        if router_type in ["ios-xr","ios-xe"]:
            try:
                last_line_part1 = last_line.split('(')[0]
                last_line_part2 = last_line.split(')')[1]
                last_line = last_line_part1 + last_line_part2
            except: last_line = last_line
        # FILTER-OUT '[*','[~','-...]' FROM VRP
        elif router_type == "vrp":
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
            # 30SECONDS COMMAND TIMEOUT
            seconds = 30
            if (timeout_counter) > seconds*10: exit_loop=True; break
    return output

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

######## Parse program arguments #########
parser = argparse.ArgumentParser(
                description = "Script to perform add ipv6 to lo200 check",
                epilog = "e.g: \n")

parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device',
                    default = str(),
                    help = "target router to check")
parser.add_argument("--os",
                    action = "store", dest="router_type",
                    choices = ["ios-xr", "ios-xe", "junos", "vrp"],
                    help = "router operating system type")
parser.add_argument("--cmd", action = 'store', dest = "cmd_file", default = None,
                    help = "specify a file with a list of commands to execute")
parser.add_argument("--user",
                    action = "store", dest = 'username', default = str(),
                    help = "specify router user login")
parser.add_argument("--pass",
                    action = "store", dest = 'password', default = str(),
                    help = "specify router user password")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = False,
                    help = "print mode with no colors.")
args = parser.parse_args()

if args.nocolors: bcolors = nocolors
device_list = [args.device]

####### Set USERNAME if needed
if args.username: USERNAME = args.username
if not USERNAME:
    print(bcolors.MAGENTA + " ... Please insert your username by cmdline switch --user username !" + bcolors.ENDC )
    sys.exit(0)

# SSH (default)
if not PASSWORD:
    if args.password: PASSWORD = args.password
    else:             PASSWORD = getpass.getpass("TACACS password: ")

for device in device_list:
    if device:
        router_prompt = None
        try: PARAMIKO_HOST = device.split(':')[0]
        except: PARAMIKO_HOST = str()
        try: PARAMIKO_PORT = device.split(':')[1]
        except: PARAMIKO_PORT = '22'
        print('\nDEVICE %s (host=%s, port=%s) START.........................'\
            %(device,PARAMIKO_HOST, PARAMIKO_PORT))

        ####### Figure out type of router OS
        if not args.router_type:
            router_type , router_prompt = detect_router_by_ssh(device,debug = False)
            print('DETECTED ROUTER_TYPE: %s, PROMPT: \'%s\'' % (router_type,router_prompt))
        else:
            router_type = args.router_type
            print('FORCED ROUTER_TYPE: ' + router_type)

        ######## Create logs directory if not existing  #########
        if not os.path.exists(os.path.join(HOMEDIR,'logs')): os.makedirs(os.path.join(HOMEDIR,'logs'))
        filename_prefix = os.path.join(HOMEDIR,'logs',device)
        filename_suffix = 'log'
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,now.second,filename_suffix)

        ######## Find command list file (optional)
        list_cmd, line_list= [], []
        if args.cmd_file:
            if not os.path.isfile(args.cmd_file):
                print(bcolors.MAGENTA + " ... Can't find command file: %s " + bcolors.ENDC) \
                        % args.cmd_file
                sys.exit()
            else:
                with open(args.cmd_file) as cmdf:
                    list_cmd = cmdf.read().replace('\x0d','').splitlines()

        # Collect pre/post check information
        if router_type == "ios-xe":
            CMD = list_cmd if len(list_cmd)>0 else CMD_IOS_XE
            DEVICE_PROMPTS = [ \
                '%s%s#'%(args.device.upper(),''), \
                '%s%s#'%(args.device.upper(),'(config)'), \
                '%s%s#'%(args.device.upper(),'(config-if)'), \
                '%s%s#'%(args.device.upper(),'(config-line)'), \
                '%s%s#'%(args.device.upper(),'(config-router)')  ]
            TERM_LEN_0 = "terminal length 0\n"
            EXIT = "exit\n"
        elif router_type == "ios-xr":
            CMD = list_cmd if len(list_cmd)>0 else CMD_IOS_XR
            DEVICE_PROMPTS = [ \
                '%s%s#'%(args.device.upper(),''), \
                '%s%s#'%(args.device.upper(),'(config)'), \
                '%s%s#'%(args.device.upper(),'(config-if)'), \
                '%s%s#'%(args.device.upper(),'(config-line)'), \
                '%s%s#'%(args.device.upper(),'(config-router)')  ]
            TERM_LEN_0 = "terminal length 0\n"
            EXIT = "exit\n"
        elif router_type == "junos":
            CMD = list_cmd if len(list_cmd)>0 else CMD_JUNOS
            DEVICE_PROMPTS = [ \
                 USERNAME + '@' + args.device.upper() + '> ', # !! Need the space after >
                 USERNAME + '@' + args.device.upper() + '# ' ]
            TERM_LEN_0 = "set cli screen-length 0\n"
            EXIT = "exit\n"
        elif router_type == "vrp":
            CMD = list_cmd if len(list_cmd)>0 else CMD_VRP
            DEVICE_PROMPTS = [ \
                '<' + args.device.upper() + '>',
                '[' + args.device.upper() + ']',
                '[~' + args.device.upper() + ']',
                '[*' + args.device.upper() + ']' ]
            TERM_LEN_0 = "screen-length 0 temporary\n"     #"screen-length disable\n"
            EXIT = "quit\n"
        elif router_type == "linux":
            CMD = list_cmd if len(list_cmd)>0 else CMD_LINUX
            DEVICE_PROMPTS = [ ]
            TERM_LEN_0 = ''     #"screen-length disable\n"
            EXIT = "exit\n"
        else:
            CMD = list_cmd if len(list_cmd)>0 else []
            DEVICE_PROMPTS = [ ]
            TERM_LEN_0 = ''     #"screen-length disable\n"
            EXIT = "exit\n"

        # ADD PROMPT TO PROMPTS LIST
        if router_prompt: DEVICE_PROMPTS.append(router_prompt)

        print(" ... Connecting (SSH) to %s" % device)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), \
                           username=USERNAME, password=PASSWORD)
            chan = client.invoke_shell()
            chan.settimeout(TIMEOUT)
            output = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,TERM_LEN_0)
            output += ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,"")
            with open(filename,"w") as fp:
                fp.write(output)
                for cli_items in CMD:
                    try:
                        item = cli_items[0] if type(cli_items) == list else cli_items
                        # py2to3 compatible test if type == string
                        if isinstance(item, six.string_types):
                            fp.write('COMMAND: %s\n'%(item))
                            output = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,item)
                            fp.write(output+'\n')

                        # hack: use dictionary for running local python code functions
                        elif isinstance(item, dict):
                            try:
                                local_function = item.get('call_function','')
                                local_outout = locals()[local_function](output)
                                print("%sCALL_LOCAL_FUNCTION: %s'%s' = %s(output)\n%s" % \
                                    (bcolors.GREEN,bcolors.YELLOW,local_outout,local_function,bcolors.ENDC))
                                if local_outout == str() and \
                                    item.get('if_void_local_output') == 'stop':
                                    print("%sSTOP (VOID LOCAL OUTPUT).%s" % \
                                    (bcolors.RED,bcolors.ENDC))
                                    break;
                            except: local_outout = str()
                        else:
                            print('%sUNSUPPORTED_TYPE %s of %s!%s' % \
                                (bcolors.MAGENTA,type(item),item,bcolors.ENDC))
                    except: pass

        except (socket.timeout, paramiko.AuthenticationException) as e:
            print(bcolors.FAIL + " ... Connection closed. %s " % (e) + bcolors.ENDC )
            sys.exit()
        finally: client.close()
        if os.path.exists(filename): print('%s file created.'%filename)
        print('\nDEVICE %s DONE.'%(device))
print('\nEND.')

