#!/usr/bin/python

import sys, os, paramiko
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


TODAY            = datetime.datetime.now()
VERSION          = str(TODAY.year)[2:] + '.' + str(TODAY.month) + '.' + str(TODAY.day)
HELP             = "\nTry ' --help' for more information\n"

UNKNOW_HOST     = 'Name or service not known'
TIMEOUT         = 60
try:    HOMEDIR         = os.environ['HOME']
except: HOMEDIR         = str()
try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()

print('HOMEDIR: '+HOMEDIR)

local_outout = str()

###############################################################################
#
# Generic list of commands
#
###############################################################################


# IOS-XE is only for IPsec GW
CMD_IOS_XE = [
            ('sh int loopback 200 | i 172'),
            {'call_function': 'parse_ipv4_from_text', 'if_void_local_output':'stop'},
            'conf t',
            'interface loopback 200',
            'ipv6 address __local_outout__/128',
            'commi',
            'exit'
            'sh int loopback 200 | i __local_outout__'
             ]
CMD_IOS_XR = [
            ('sh int loopback 200 | i 172'),
            {'call_function': 'parse_ipv4_from_text', 'if_void_local_output':'stop'},
            'conf',
            'interface loopback 200',
            'ipv6 address __local_outout__/128',
            'commi',
            'exit'
            'sh int loopback 200 | i __local_outout__'
             ]
CMD_JUNOS = [
            ('show configuration interfaces lo0 | match 172'),
            {'call_function': 'parse_ipv4_from_text', 'if_void_local_output':'stop'},
             'conf',

             'exit'
            ]
CMD_VRP = [
            ('disp current-configuration interface LoopBack 200 | include 172'),
            {'call_function': 'parse_ipv4_from_text', 'if_void_local_output':'stop'},
            'sys',

            'quit'
          ]


###############################################################################
#
# Function and Class
#
###############################################################################


# detect device prompt
def ssh_detect_prompt(chan, debug = False):
    output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
    chan.send('\t \n\n')
    while not (last_line and last_but_one_line and last_line == last_but_one_line):
        if debug: print('FIND_PROMPT:',last_but_one_line,last_line)
        buff = chan.recv(9999)
        output += buff.replace('\r','').replace('\x07','').replace('\x08','').\
                  replace('\x1b[K','').replace('\n{master}\n','')
        if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
        if debug: print('BUFFER:' + buff)
        try: last_line = output.splitlines()[-1].strip().replace('\x20','')
        except: last_line = 'dummyline1'
        try: last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
        except: last_but_one_line = 'dummyline2'
    print('DETECTED PROMPT: \'' + last_line + '\'')
    return last_line


# bullet-proof read-until function , even in case of ---more---
def ssh_read_until_prompt_bulletproof(chan,command,prompt,debug=False):
    output, buff, last_line = str(), str(), 'dummyline1'
    # avoid of echoing commands on ios-xe by timeout 1 second
    flush_buffer = chan.recv(9999)
    del flush_buffer
    chan.send(command)
    time.sleep(1)
    while not last_line == prompt:
        if debug: print('LAST_LINE:',prompt,last_line)
        buff = chan.recv(9999)
        output += buff.replace('\r','').replace('\x07','').replace('\x08','').\
                  replace('\x1b[K','').replace('\n{master}\n','')
        if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
        if debug: print('BUFFER:' + buff)
        try: last_line = output.splitlines()[-1].strip().replace('\x20','')
        except: last_line = str()
    return output

# huawei does not respond to snmp
def detect_router_by_ssh(debug = False):
    router_os = str()
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(args.device, username=USERNAME, password=PASSWORD)
        chan = client.invoke_shell()
        chan.settimeout(TIMEOUT)
        # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
        # \n\n get prompt as last line
        prompt = ssh_detect_prompt(chan, debug=False)

        #test if this is HUAWEI VRP
        if prompt and not router_os:
            command = 'display version | include (Huawei)\n'
            output = ssh_read_until_prompt_bulletproof(chan, command, prompt, debug=debug)
            if 'Huawei Versatile Routing Platform Software' in output: router_os = 'vrp'

        #test if this is CISCO IOS-XR, IOS-XE or JUNOS
        if prompt and not router_os:
            command = 'show version\n'
            output = ssh_read_until_prompt_bulletproof(chan, command, prompt, debug=debug)
            if 'iosxr-' in output or 'Cisco IOS XR Software' in output: router_os = 'ios-xr'
            elif 'Cisco IOS-XE software' in output: router_os = 'ios-xe'
            elif 'JUNOS OS' in output: router_os = 'junos'
            else:
                print(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (retvalue) + bcolors.ENDC)
                sys.exit(0)

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.MAGENTA + " ... Connection closed: %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    return router_os


def ssh_read_until(channel,prompt,conf_promt):
    output = ''
    while not (output.endswith(prompt) or output.endswith(conf_promt)):
        buff = chan.recv(9999)
        output += buff.replace('\x0d','').replace('\x07','').replace('\x08','').\
                  replace(' \x1b[1D','')
    return output


def ipv4_to_ipv6(ipv4address):
    ip4to6, ip6to4 = str(), str()
    try: v4list = ipv4address.split('/')[0].split('.')
    except: v4list = []
    if len(v4list) == 4:
        try:
            if int(v4list[0])<256 and int(v4list[1])<256 and int(v4list[2])<256 \
                and int(v4list[3])<256 and int(v4list[0])>=0 and \
                int(v4list[1])>=0 and int(v4list[2])>=0 and int(v4list[3])>=0:
                ip4to6 = '0:0:0:0:0:FFFF:%02X%02X:%02X%02X' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
                ip6to4 = '2002:%02x%02x:%02x%02x:0:0:0:0:0' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
        except: pass
    return ip4to6, ip6to4

def ipv4_to_ipv6_obs(ipv4address):
    ip4to6, ip6to4 = str(), str()
    try: v4list = ipv4address.split('/')[0].split('.')
    except: v4list = []
    if len(v4list) == 4:
        try:
            if int(v4list[0])<256 and int(v4list[1])<256 and int(v4list[2])<256 \
                and int(v4list[3])<256 and int(v4list[0])>=0 and \
                int(v4list[1])>=0 and int(v4list[2])>=0 and int(v4list[3])>=0:
                ip4to6 = 'fd00:0:0:5511::%02x%02x:%02x%02x' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
                ip6to4 = '2002:%02x%02x:%02x%02x:0:0:0:0:0' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
        except: pass
    return ip4to6, ip6to4

def parse_ipv4_from_text(text):
    try: ipv4=text.split('address')[1].split()[0].replace(';','')
    except: ipv4 = str()
    return ipv4_to_ipv6_obs(ipv4)[0]


##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

# print(globals()['ipv4_to_ipv6'])
# m=locals()['parse_ipv4_from_text']
# print(m)
# print(m('xxxxx address 1.1.1.1/44 kdslja ijada'))
#
# exit(0)


######## Parse program arguments #########
parser = argparse.ArgumentParser(
                description = "Script to perform add ipv6 to lo200 check",
                epilog = "e.g: \n")

parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device',
                    required = True,
                    help = "target router to check")
parser.add_argument("--os",
                    action = "store", dest="router_type",
                    choices = ["ios-xr", "ios-xe", "junos", "vrp"],
                    help = "router operating system type")
parser.add_argument("--cmd", action = 'store', dest = "cmd_file", default = None,
                    help = "specify a file with a list of commands to execute")
parser.add_argument("--user",
                    action = "store", dest = 'username',
                    help = "specify router user login")

args = parser.parse_args()

####### Set USERNAME if needed
if args.username != None: USERNAME = args.username

####### Figure out type of router OS
if not args.router_type:
    router_type = detect_router_by_ssh(debug = False)
    print('DETECTED ROUTER_TYPE: ' + router_type)
else:
    router_type = args.router_type
    print('FORCED ROUTER_TYPE: ' + router_type)

######## Create logs directory if not existing  #########
if not os.path.exists(HOMEDIR + '/logs'): os.makedirs(HOMEDIR + '/logs')
filename_prefix = HOMEDIR + "/logs/" + args.device
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
    DEVICE_PROMPT = args.device.upper() + '#'
    DEVICE_PROMPT_CONF = args.device.upper() + '(config)#'
    TERM_LEN_0 = "terminal length 0\n"
    EXIT = "exit\n"

elif router_type == "ios-xr":
    CMD = list_cmd if len(list_cmd)>0 else CMD_IOS_XR
    DEVICE_PROMPT = args.device.upper() + '#'
    DEVICE_PROMPT_CONF = args.device.upper() + '(config)#'
    TERM_LEN_0 = "terminal length 0\n"
    EXIT = "exit\n"

elif router_type == "junos":
    CMD = list_cmd if len(list_cmd)>0 else CMD_JUNOS
    DEVICE_PROMPT = USERNAME + '@' + args.device.upper() + '> ' # !! Need the space after >
    DEVICE_PROMPT_CONF = USERNAME + '@' + args.device.upper() + '# '
    TERM_LEN_0 = "set cli screen-length 0\n"
    EXIT = "exit\n"

elif router_type == "vrp":
    CMD = list_cmd if len(list_cmd)>0 else CMD_VRP
    DEVICE_PROMPT = '<' + args.device.upper() + '>'
    DEVICE_PROMPT_CONF = '[' + args.device.upper() + ']'
    TERM_LEN_0 = "screen-length 0 temporary\n"     #"screen-length disable\n"
    EXIT = "quit\n"

# SSH (default)
if not PASSWORD: PASSWORD = getpass.getpass("TACACS password: ")

print " ... Connecting (SSH) to %s" % args.device
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(args.device, username=USERNAME, password=PASSWORD)
    chan = client.invoke_shell()
    chan.settimeout(TIMEOUT)
    while not chan.recv_ready(): time.sleep(1)
    output = ssh_read_until(chan,DEVICE_PROMPT,DEVICE_PROMPT_CONF)
    chan.send(TERM_LEN_0 + '\n')
    output = ssh_read_until(chan,DEVICE_PROMPT,DEVICE_PROMPT_CONF)
    # router prompt needed as file header
    chan.send('\n')
    output = ssh_read_until(chan,DEVICE_PROMPT,DEVICE_PROMPT_CONF)
    with open(filename,"w") as fp:
        fp.write(output)
        print(output)
        for cli_items in CMD:
            try:
                item = cli_items[0] if type(cli_items) == list else cli_items
                if isinstance(item, basestring):
                    output = str()
                    item = item.replace('__local_outout__',local_outout)
                    chan.send(item + '\n')
                    print "COMMAND: %s" % item
                    output = ssh_read_until(chan,DEVICE_PROMPT,DEVICE_PROMPT_CONF)
                    print(output)
                    fp.write(output)
                # hack: use dictionary for running local python code functions
                elif isinstance(item, dict):
                    try:
                        local_function = item.get('call_function','')
                        local_outout = locals()[local_function](output)
                        print("CALL_LOCAL_FUNCTION: '%s' = %s(output)\n'" % \
                            (local_outout,local_function))
                        if local_outout == str() and \
                            item.get('if_void_local_output') == 'stop': break;
                    except: local_outout = str()
                else:
                    print('UNSUPPORTED_TYPE %s of %s!' % (type(item),item))
            except: pass

except (socket.timeout, paramiko.AuthenticationException) as e:
    print(bcolors.FAIL + " ... Connection closed. %s " % (e) + bcolors.ENDC )
    sys.exit()
finally: client.close()


subprocess.call(['ls','-l',filename])
print '\n ==> COMPLETE !'


