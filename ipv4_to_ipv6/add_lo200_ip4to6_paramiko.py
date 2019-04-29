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

set_ipv6line = str()
converted_ipv4 = str()
###############################################################################
#
# Generic list of commands
#
###############################################################################


CMD_IOS_XE = [
			'sh run int loopback 200 | i /128',
            {'call_function': 'stop_if_ipv6_found','input':'last_output', 'if_output_is_void':'exit'},
            'sh run int loopback 200 | i 172',
            {'call_function': 'parse_ipv4_from_text','input':'last_output', 'output':'converted_ipv4','if_output_is_void':'exit'},
            'conf t',
            'interface loopback 200',
            ('ipv6 address', {'variable':'converted_ipv4'}, '/128'),
            'exit',
			'exit',
			'write',
            'sh int loopback 200 | i /128'
              ]
CMD_IOS_XR = [
            'sh run int loopback 200 | i /128',
            {'call_function': 'stop_if_ipv6_found', 'input':'last_output', 'if_output_is_void':'exit'},
			'sh run int loopback 200 | i 172',
            {'call_function': 'parse_ipv4_from_text','input':'last_output', 'output':'converted_ipv4','if_output_is_void':'exit'},
            'conf',
			'interface loopback 200',
            ('ipv6 address ', {'variable':'converted_ipv4'}, '/128'),
            'router isis PAII',
            'interface Loopback200',
            'address-family ipv6 unicast',
            'commi',
            'exit',
			'exit',
            'sh int loopback 200 | i /128'
             ]
CMD_JUNOS = [
            'show configuration interfaces lo0 | match /128',
            {'call_function': 'stop_if_two_ipv6_found', 'if_output_is_void':'exit'},
            'show configuration interfaces lo0 | display set | match 128',
            #{'call_function': 'parse_whole_set_line_from_text', 'if_output_is_void':'exit'},
			'show configuration interfaces lo0 | match 172.25.4',
            {'call_function': 'parse_ipv4_from_text','input':'last_output', 'output':'converted_ipv4','if_output_is_void':'exit'},
             'configure private',
             #'__var_set_ipv6line__',
             ('set interfaces lo0 unit 0 family inet6 address ', {'variable':'converted_ipv4'}, '/128'),
             'show configuration interfaces lo0 | match /128',
    		 'commi',
    		 'exit',
             'show configuration interfaces lo0 | match /128',
             ]
CMD_VRP = [
            'disp current-configuration interface LoopBack 200 | include /128',
            {'call_function': 'stop_if_ipv6_found', 'input':'last_output', 'if_output_is_void':'exit'},
			'disp current-configuration interface LoopBack 200 | include 172',
            {'call_function': 'parse_ipv4_from_text', 'input':'last_output', 'output':'converted_ipv4','if_output_is_void':'exit'},
            'sys',
			'interface loopback 200',
            'ipv6 enable',
			('ipv6 address ', {'variable':'converted_ipv4'}, '/128'),
            'isis ipv6 enable 5511',
			'commit',
            'quit',
			'quit',
            'disp current-configuration interface LoopBack 200 | include /128'
          ]
CMD_LINUX = [
            'hostname',
            ('echo ', {'variable':'last_output'}),
            ('echo ', {'variable':'notexistent'},{'if_output_is_void':'exit'}),
            'free -m'
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
        output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
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
def ssh_read_until_prompt_bulletproof(chan,command,prompts,debug=False):
    output, buff, last_line, exit_loop = str(), str(), 'dummyline1', False
    # avoid of echoing commands on ios-xe by timeout 1 second
    flush_buffer = chan.recv(9999)
    del flush_buffer
    chan.send(command)
    time.sleep(1)
    output, exit_loop = '', False
    while not exit_loop:
        if debug: print('LAST_LINE:',prompts,last_line)
        buff = chan.recv(9999)
        output += buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                  replace('\x1b[K','').replace('\n{master}\n','')
        if '--More--' or '---(more' in buff.strip(): chan.send('\x20')
        if debug: print('BUFFER:' + buff)
        try: last_line = output.splitlines()[-1].strip().replace('\x20','')
        except: last_line = str()
        for actual_prompt in prompts:
            if output.endswith(actual_prompt) or actual_prompt in last_line: exit_loop = True
    return output

# huawei does not respond to snmp
def detect_router_by_ssh(device, debug = False):
    router_os = str()
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(device, username=USERNAME, password=PASSWORD)
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
            else:
                print(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (output) + bcolors.ENDC)
                sys.exit(0)

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.MAGENTA + " ... Connection closed: %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    return router_os


def ssh_read_until(chan,prompts):
    output, exit_loop = '', False
    while not exit_loop:
        buff = chan.recv(9999)
        output += buff.decode("utf-8").replace('\x0d','').replace('\x07','').replace('\x08','').\
            replace(' \x1b[1D','')
            #line.split('(config')[0]
        for actual_prompt in prompts:
            if output.endswith(actual_prompt): exit_loop=True; break
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
    #global converted_ipv4
    try: ipv4 = text.split('address')[1].split()[0].replace(';','')
    except: ipv4 = str()
    converted_ipv4 = ipv4_to_ipv6_obs(ipv4)[0]
    return converted_ipv4

def stop_if_ipv6_found(text):
    try: ipv6 = text.split('address')[1].split()[0].replace(';','')
    except: ipv6 = str()
    if ipv6: return str()
    else: return "NOT_FOUND"

def stop_if_two_ipv6_found(text):
    try: ipv6 = text.split('address')[1].split()[0].replace(';','')
    except: ipv6 = str()
    try: ipv6two = text.split('address')[2].split()[0].replace(';','')
    except: ipv6two = str()
    if ipv6 and ipv6two: return str()
    else: return "NOT_FOUND"

def parse_whole_set_line_from_text(text):
    #global set_ipv6line
    try: set_text = text.split('set')[1].split('\n')[0]
    except: set_text = str()
    if set_text: set_ipv6line = 'set' + set_text + ' primary\n'
    else: set_ipv6line = str()
    return set_ipv6line

# def parse_json_file_and_get_oti_routers_list():
#     oti_routers = []
#     json_filename = '/home/dpenha/perl_shop/NIS9TABLE_BLDR/node_list.json'
#     with io.open(json_filename) as json_file: json_raw_data = json.load(json_file)
#     if json_raw_data:
#         for router in json_raw_data['results']:
#            if router['namings']['type']=='OTI':
#                oti_routers.append(router['name'])
#     return oti_routers

def parse_json_file_and_get_oti_routers_list():
    oti_routers, json_raw_data = [], str()
    json_filename = '/usr/local/iptac/oti_all.pl'
    with io.open(json_filename,'r') as json_file:
        data = json_file.read()
        data_converted = data.split('%oti_all =')[1].replace("'",'"')\
            .replace('=>',':').replace('(','{').replace(')','}').replace(';','')
        data_converted='{\n  "OTI_ALL" : ' + data_converted + '\n}'
        json_raw_data = json.loads(data_converted)
    if json_raw_data:
        for router in json_raw_data['OTI_ALL']:
            if '172.25.4' in json_raw_data['OTI_ALL'][router]['LSRID']: oti_routers.append(router)
    return oti_routers


def run_remote_and_local_commands(CMD, logfilename = None, printall = None, printcmdtologfile = None):
    ssh_connection, output= None, None
    try:
        try: ssh_connection = netmiko.ConnectHandler(device_type = router_type, \
                 ip = DEVICE_HOST, port = int(DEVICE_PORT), \
                 username = USERNAME, password = PASSWORD)
        except:
            global DEVICE_PROMPTS
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(DEVICE_HOST, port=int(DEVICE_PORT), \
                           username=USERNAME, password=PASSWORD)
            chan = client.invoke_shell()
            chan.settimeout(TIMEOUT)
            output, forget_it = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,TERM_LEN_0)
            output2, forget_it = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,"")
            output += output2

        if not logfilename:
            if 'LINUX' in platform.system().upper(): logfilename = '/dev/null'
            else: logfilename = 'nul'
        with open(logfilename,"w") as fp:
            if output and not printcmdtologfile: fp.write(output)
            dictionary_of_pseudovariables = {}
            for cli_items in CMD:
                cli_line = str()
                # list,tupple,strins are remote device commands
                if isinstance(cli_items, six.string_types) or \
                    isinstance(cli_items, list) or isinstance(cli_items, tuple):
                    if isinstance(cli_items, six.string_types): cli_line = cli_items
                    if isinstance(cli_items, list) or isinstance(cli_items, tuple):
                        for cli_item in cli_items:
                           if isinstance(cli_item, dict): cli_line += dictionary_of_pseudovariables.get(cli_item.get('variable',''),'')
                           else: cli_line += cli_item
                    print(bcolors.GREEN + "COMMAND: %s" % (cli_line) + bcolors.ENDC )
                    try: last_output = ssh_connection.send_command(cli_line)
                    except:
                        last_output, new_prompt = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,cli_line)
                        if new_prompt: DEVICE_PROMPTS.append(new_prompt)
                    last_output = last_output.replace('\x0d','')
                    if printall: print(bcolors.GREY + "%s" % (last_output) + bcolors.ENDC )
                    if printcmdtologfile: fp.write('COMMAND: ' + cli_line + '\n'+last_output+'\n')
                    else: fp.write(last_output)
                    dictionary_of_pseudovariables['last_output'] = last_output.rstrip()
                    for cli_item in cli_items:
                        if isinstance(cli_item, dict) and \
                            last_output.strip() == str() and \
                            cli_item.get('if_output_is_void','') in ['exit','quit','stop']:
                            if printall: print("%sSTOP (VOID OUTPUT).%s" % \
                                (bcolors.RED,bcolors.ENDC))
                            return None
                # HACK: use dictionary for running local python code functions
                elif isinstance(cli_items, dict):
                    if cli_items.get('call_function',''):
                        local_function = cli_items.get('call_function','')
                        local_input = dictionary_of_pseudovariables.get('input','')
                        output_to_pseudovariable = dictionary_of_pseudovariables.get('output','')
                        local_output = locals()[local_function](local_input)
                        if output_to_pseudovariable:
                            dictionary_of_pseudovariables[output_to_pseudovariable] = local_output
                        if printall: print("%sCALL_LOCAL_FUNCTION: %s'%s' = %s(%s)\n%s" % \
                            (bcolors.GREEN,bcolors.YELLOW,local_output,local_function,local_input,bcolors.ENDC))
                        if local_output.strip() == str() and \
                            cli_items.get('if_output_is_void') in ['exit','quit','stop']:
                            if printall: print("%sSTOP (VOID LOCAL OUTPUT).%s" % \
                                (bcolors.RED,bcolors.ENDC))
                            return None
                    elif cli_items.get('local_command',''):
                        local_process = cli_items.get('local_command','')
                        local_input = dictionary_of_pseudovariables.get('input','')
                        output_to_pseudovariable = dictionary_of_pseudovariables.get('output','')
                        local_output = subprocess.call(local_process+' '+local_input if local_input else local_process, shell=True)
                        if output_to_pseudovariable:
                            dictionary_of_pseudovariables[output_to_pseudovariable] = local_output
                        if printall: print("%sLOCAL_COMMAND: %s'%s' = %s(%s)\n%s" % \
                            (bcolors.GREEN,bcolors.YELLOW,local_output,local_function,local_input,bcolors.ENDC))
                        if local_output.strip() == str() and \
                            cli_items.get('if_output_is_void') in ['exit','quit','stop']:
                            if printall: print("%sSTOP (VOID LOCAL OUTPUT).%s" % \
                                (bcolors.RED,bcolors.ENDC))
                            return None
                elif printall: print('%sUNSUPPORTED_TYPE %s of %s!%s' % \
                            (bcolors.MAGENTA,type(item),str(cli_items),bcolors.ENDC))
    except () as e:
        print(bcolors.FAIL + " ... EXCEPTION: (%s)" % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        try:
            if ssh_connection: ssh_connection.disconnect()
        except: client.close()
    return None



##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

# print(parse_json_file_and_get_oti_routers_list())
# sys.exit(0)

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
                    default = str(),
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
parser.add_argument("--alloti",
                    action = 'store_true', dest = "alloti", default = False,
                    help = "do action on all oti routers")

args = parser.parse_args()

if args.alloti: device_list = parse_json_file_and_get_oti_routers_list()
else: device_list = [args.device]


####### Set USERNAME if needed
if args.username != None: USERNAME = args.username
if not USERNAME:
    print(bcolors.MAGENTA + " ... Please insert your username by cmdline switch --user username !" + bcolors.ENDC )
    sys.exit(0)

# SSH (default)
if not PASSWORD: PASSWORD = getpass.getpass("TACACS password: ")

for device in device_list:
    if device:
        print('\nDEVICE %s START.........................................'%(device))
        ####### Figure out type of router OS
        if not args.router_type:
            router_type = detect_router_by_ssh(device,debug = False)
            print('DETECTED ROUTER_TYPE: ' + router_type)
        else:
            router_type = args.router_type
            print('FORCED ROUTER_TYPE: ' + router_type)

        ######## Create logs directory if not existing  #########
        if not os.path.exists(HOMEDIR + '/logs'): os.makedirs(HOMEDIR + '/logs')
        filename_prefix = HOMEDIR + "/logs/" + device
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
                '%s%s#'%(args.device.upper(),'(config-isis)'), \
                '%s%s#'%(args.device.upper(),'(config-isis-if)'), \
                '%s%s#'%(args.device.upper(),'(config-isis-if-af)'), \
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
                '[*' + args.device.upper() + ']',
                '[~' + args.device.upper() + '-LoopBack200]',
                '[*' + args.device.upper() + '-LoopBack200]',
                '[' + args.device.upper() + '-LoopBack200]',
                  ]
            TERM_LEN_0 = "screen-length 0 temporary\n"     #"screen-length disable\n"
            EXIT = "quit\n"

        run_remote_and_local_commands(CMD, logfilename = None, printall = True, printcmdtologfile = None)

        print('\nDEVICE %s DONE.'%(device))
print('\nEND.')

