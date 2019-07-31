#!/usr/bin/python36

import sys, os, io, paramiko, json , copy
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
import mysql.connector
from mako.template import Template
from mako.lookup import TemplateLookup
import cgi
import cgitb; cgitb.enable()
import requests
#import interactive
#python 2.7 problem - hack 'pip install esptool'
import netmiko


step1_string = 'Submit step 1'
step2_string = 'Submit step 2'


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

START_EPOCH      = time.time()
TODAY            = datetime.datetime.now()
script_name      = sys.argv[0]
TIMEOUT          = 60

remote_connect = True

KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']

try:    WORKDIR         = os.environ['HOME']
except: WORKDIR         = str(os.path.dirname(os.path.abspath(__file__)))
if WORKDIR: LOGDIR      = os.path.join(WORKDIR,'logs')

try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()
try:    EMAIL_ADDRESS   = os.environ['NEWR_EMAIL']
except: EMAIL_ADDRESS   = str()

default_problemline_list   = []
default_ignoreline_list    = [r' MET$', r' UTC$']
default_linefilter_list    = []
default_compare_columns    = []
default_printalllines_list = []

###############################################################################
#
# Generic list of commands
#
###############################################################################


# IOS-XE is only for IPsec GW
CMD_IOS_XE = []

CMD_IOS_XR = [

]

CMD_JUNOS = []

CMD_VRP = []

CMD_LINUX = []

CMD_LOCAL = []


###############################################################################
bgp_data = collections.OrderedDict()


###############################################################################
#
# Function and Class
#
###############################################################################

### UNI-tools ###
def return_indexed_list(data_list = None):
    if data_list and isinstance(data_list, (list,tuple)):
        return zip(range(len(data_list)),data_list)
    return []


def get_first_row_after(text = None, split_text = None, delete_text = None, split_text_index = None):
    output = str()
    if text:
        try:
            if split_text_index == None: output = text.strip().split(split_text)[1].split()[0].strip()
            else: output = text.strip().split(split_text)[int(split_text_index)+1].split()[0].strip()
            if delete_text: output = output.replace(delete_text,'')
        except: pass
    return output


def get_first_row_before(text = None, split_text = None, delete_text = None, split_text_index = None):
    output = str()
    if text:
        try:
            if split_text_index == None: output = text.strip().split(split_text)[0].split()[-1].strip()
            else: output = text.strip().split(split_text)[int(split_text_index)].split()[-1].strip()
            if delete_text: output = output.replace(delete_text,'')
        except: pass
    return output

def does_text_contains_string(text = None, contains_string = None):
    output = str()
    if text and contains_text:
        if contains_string in text: output = contains_string
    return output

def return_bgp_data_json():
    return json.dumps(bgp_data, indent=2)


def read_bgp_data_json_from_logfile(filename = None, printall = None):
    bgp_data_loaded, text = None, None
    with open(filename,"r") as fp:
        text = fp.read()
    if text:
        try: bgp_data_json_text = text.split('EVAL_COMMAND: return_bgp_data_json()')[1]
        except: bgp_data_json_text = str()
        if bgp_data_json_text:
            try:
                bgp_data_loaded = json.loads(bgp_data_json_text, object_pairs_hook = collections.OrderedDict)
            except: pass
            #print("LOADED_BGP_DATA: ",bgp_data_loaded)
            if printall: print("\nLOADED JSON BGP_DATA: ")
            if printall: print(json.dumps(bgp_data_loaded, indent=2))
    return bgp_data_loaded


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

    try: DEVICE_HOST = device.split(':')[0]
    except: DEVICE_HOST = str()
    try: DEVICE_PORT = device.split(':')[1]
    except: DEVICE_PORT = '22'

    try:
        #connect(self, hostname, port=22, username=None, password=None, pkey=None, key_filename=None, timeout=None, allow_agent=True, look_for_keys=True, compress=False)
        client.connect(DEVICE_HOST, port=int(DEVICE_PORT), username=USERNAME, password=PASSWORD)
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

    netmiko_os = str()
    if router_os == 'ios-xe': netmiko_os = 'cisco_ios'
    if router_os == 'ios-xr': netmiko_os = 'cisco_xr'
    if router_os == 'junos': netmiko_os = 'juniper'
    if router_os == 'linux': netmiko_os = 'linux'
    if router_os == 'vrp': netmiko_os = 'huawei'
    #return netmiko_os
    #return router_os, prompt
    return netmiko_os, prompt


def ssh_send_command_and_read_output(chan,prompts,send_data=str(),printall=True):
    output, output2, new_prompt = str(), str(), str()
    exit_loop, exit_loop2 = False, False
    timeout_counter, timeout_counter2 = 0, 0
    # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
    if chan.recv_ready(): flush_buffer = chan.recv(9999)
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
        if router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
            try:
                last_line_part1 = last_line.split('(')[0]
                last_line_part2 = last_line.split(')')[1]
                last_line = last_line_part1 + last_line_part2
            except: last_line = last_line
        # FILTER-OUT '[*','[~','-...]' FROM VRP
        elif router_type in ["vrp",'huawei']:
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
            if '172.25.4' in json_raw_data['OTI_ALL'][router]['LSRID']:
                oti_routers.append(router)
    return oti_routers


# def parse_json_file_and_get_oti_routers_list():
#     oti_routers = []
#     json_filename = '/home/dpenha/perl_shop/NIS9TABLE_BLDR/node_list.json'
#     with io.open(json_filename) as json_file: json_raw_data = json.load(json_file)
#     if json_raw_data:
#         for router in json_raw_data['results']:
#            if router['namings']['type']=='OTI':
#                oti_routers.append(router['name'])
#     return oti_routers


def run_remote_and_local_commands(CMD, logfilename = None, printall = None, \
    printcmdtologfile = None, debug = None,use_module = 'paramiko'):
    ### RUN_COMMAND - REMOTE or LOCAL ------------------------------------------
    def run_command(ssh_connection,cmd_line_items,loop_item=None,run_remote = None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile,use_module = use_module):
        global glob_vars, DEVICE_PROMPTS
        cli_line, name_of_output_variable, simulate_command, sim_text = str(), None, None, str()
        print_output = None
        ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE/LOCAL DEVICE COMMANDS
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if isinstance(cmd_line_items, six.string_types): cli_line = cmd_line_items
            elif isinstance(cmd_line_items, (list,tuple)):
                for cli_item in cmd_line_items:
                    if isinstance(cli_item, dict):
                        if cli_item.get('output_variable',''):
                            name_of_output_variable = cli_item.get('output_variable','')
                        elif cli_item.get('eval',''):
                            cli_line += str(eval(cli_item.get('eval','')))
                        elif cli_item.get('sim',''):
                            simulate_command = True
                            if str(eval(cli_item.get('sim',''))).upper()=='ON' or \
                              str(cli_item.get('sim','')).upper()=='ON': simulate_command = True
                            else: simulate_command = None
                            if simulate_command: sim_text = '(SIM)'
                        elif cli_item.get('print_output',''):
                            print_output = True if str(cli_item.get('print_output','')).upper()=='ON' else None
                    else: cli_line += str(cli_item)
            if run_remote:
                if printall: print(bcolors.GREEN + "REMOTE_COMMAND%s: %s" % (sim_text,cli_line) + bcolors.ENDC )
                if simulate_command: last_output = str()
                else:
                    if use_module == 'netmiko':
                        last_output = ssh_connection.send_command(cli_line)
                    elif use_module == 'paramiko':
                        last_output, new_prompt = ssh_send_command_and_read_output( \
                            ssh_connection,DEVICE_PROMPTS,cli_line,printall=printall)
                        if new_prompt: DEVICE_PROMPTS.append(new_prompt)
            else:
                if printall: print(bcolors.CYAN + "LOCAL_COMMAND%s: %s" % (sim_text,cli_line) + bcolors.ENDC )
                ### LOCAL COMMAND - SUBPROCESS CALL
                if simulate_command: last_output = str()
                else:
                    try: last_output = subprocess.check_output(str(cli_line),shell=True)
                    except: last_output = str()

            ### FILTER LAST_OUTPUT
            if isinstance(last_output, six.string_types):
                try:
                    last_output = last_output.decode("utf-8").replace('\x07','').\
                        replace('\x08','').replace('\x0d','').replace('\x1b','').replace('\x1d','')
                except:
                     last_output = last_output.replace('\x07','').\
                        replace('\x08','').replace('\x0d','').replace('\x1b','').replace('\x1d','')
                ### NETMIKO-BUG (https://github.com/ktbyers/netmiko/issues/1200)
                if len(str(cli_line))>80 and run_remote:
                    first_bugged_line = last_output.splitlines()[0]
                    #print('NOISE:',first_bugged_line)
                    last_output = last_output.replace(first_bugged_line+'\n','')
                    if(last_output.strip() == first_bugged_line): last_output = str()

            if printall: print(bcolors.GREY + "%s" % (last_output) + bcolors.ENDC )
            elif print_output: print(bcolors.YELLOW + "%s" % (last_output) + bcolors.ENDC )
            if printcmdtologfile:
                if run_remote: fp.write('REMOTE_COMMAND'+sim_text+': ' + cli_line + '\n'+last_output+'\n')
                else: fp.write('LOCAL_COMMAND'+sim_text+': ' + str(cli_line) + '\n'+str(last_output)+'\n')
            else: fp.write(last_output)
            ### Result will be allways string, so rstrip() could be done
            glob_vars['last_output'] = last_output.rstrip()
            if name_of_output_variable:
                glob_vars[name_of_output_variable] = last_output.rstrip()
        return None
    ### EVAL_COMMAND -----------------------------------------------------------
    def eval_command(ssh_connection,cmd_line_items,loop_item=None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars, DEVICE_PROMPTS
        cli_line, name_of_output_variable, print_output = str(), None, None
        ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE/LOCAL DEVICE COMMANDS
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if isinstance(cmd_line_items, six.string_types): cli_line = cmd_line_items
            elif isinstance(cmd_line_items, (list,tuple)):
                for cli_item in cmd_line_items:
                    if isinstance(cli_item, dict):
                        if cli_item.get('output_variable',''):
                            name_of_output_variable = cli_item.get('output_variable','')
                        elif cli_item.get('eval',''):
                            cli_line += str(eval(cli_item.get('eval','')))
                        elif cli_item.get('print_output',''):
                            print_output = True if str(cli_item.get('print_output','')).upper()=='ON' else None
                    else: cli_line += str(cli_item)
            if printall: print(bcolors.CYAN + "EVAL_COMMAND: %s" % (cli_line) + bcolors.ENDC )
            try: local_output = eval(cli_line)
            except: local_output = str()
            if printall: print(bcolors.GREY + str(local_output) + bcolors.ENDC )
            elif print_output: print(bcolors.YELLOW + str(local_output) + bcolors.ENDC )
            if printcmdtologfile: fp.write('EVAL_COMMAND: ' + cli_line + '\n' + str(local_output) + '\n')
            if name_of_output_variable:
                glob_vars[name_of_output_variable] = local_output
            glob_vars['last_output'] = local_output
        return None
    ### EXEC_COMMAND -----------------------------------------------------------
    def exec_command(ssh_connection,cmd_line_items,loop_item=None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars, global_env
        cli_line, name_of_output_variable, print_output = str(), None, None
        ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE/LOCAL DEVICE COMMANDS
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if isinstance(cmd_line_items, six.string_types): cli_line = cmd_line_items
            elif isinstance(cmd_line_items, (list,tuple)):
                for cli_item in cmd_line_items:
                    if isinstance(cli_item, dict):
                        if cli_item.get('output_variable',''):
                            name_of_output_variable = cli_item.get('output_variable','')
                        elif cli_item.get('eval',''):
                            cli_line += str(eval(cli_item.get('eval','')))
                        elif cli_item.get('print_output',''):
                            print_output = True if str(cli_item.get('print_output','')).upper()=='ON' else None
                    else: cli_line += str(cli_item)
            if printall or print_output: print(bcolors.CYAN + "EXEC_COMMAND: %s" % (cli_line) + bcolors.ENDC )
            ### EXEC CODE for PYTHON>v2.7.9
            # code_object = compile(cli_line, 'sumstring', 'exec')
            # local_env = {}
            # for item in eval('dir()'): local_env[item] = eval(item)
            # exec(code_object,global_env,local_env)
            ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
            edict = {}; eval(compile(cli_line, '<string>', 'exec'), globals(), edict)
            if printcmdtologfile: fp.write('EXEC_COMMAND: ' + cli_line + '\n')
        return None
    ### IF_FUNCTION (simple eval) ----------------------------------------------
    def if_function(ssh_connection,cmd_line_items,loop_item=None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars
        cli_line, name_of_output_variable, success = str(), None, False
        if isinstance(cmd_line_items, (int,float,six.string_types)):
            condition_eval_text = cmd_line_items
            ret_value = eval(str(condition_eval_text))
            if ret_value: success = True
            else: success = False
            if printall: print(bcolors.CYAN + "IF_CONDITION(%s)" % (condition_eval_text) + " --> " +\
                str(success).upper() + bcolors.ENDC )
            if printcmdtologfile: fp.write('IF_CONDITION(%s): ' % (condition_eval_text) +\
                 " --> "+ str(success).upper() + '\n')
        return success
    ### MAIN_DO_STEP -----------------------------------------------------------
    def main_do_step(cmd_line_items,loop_item=None):
        command_range=10
        global glob_vars, DEVICE_PROMPTS
        condition_result = True
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if run_command(ssh_connection,cmd_line_items,loop_item,run_remote = True): return None
        if isinstance(cmd_line_items, (dict)):
            if cmd_line_items.get('pre_if_remote_command','') and remote_connect:
                if run_command(ssh_connection,cmd_line_items.get('pre_if_remote_command',''),loop_item,run_remote = True): return None
            if cmd_line_items.get('pre_if_local_command',''):
                if run_command(ssh_connection,cmd_line_items.get('pre_if_local_command',''),loop_item): return None
            if cmd_line_items.get('pre_if_exec',''):
                if exec_command(ssh_connection,cmd_line_items.get('pre_if_exec',''),loop_item): return None
            if cmd_line_items.get('pre_if_eval',''):
                if eval_command(ssh_connection,cmd_line_items.get('pre_if_eval',''),loop_item): return None
            if cmd_line_items.get('if',''):
                condition_result = if_function(ssh_connection,cmd_line_items.get('if',''),loop_item)
            if condition_result:
                if cmd_line_items.get('remote_command','') and remote_connect:
                    if run_command(ssh_connection,cmd_line_items.get('remote_command',''),loop_item,run_remote = True): return None
                for i in range(command_range):
                    if cmd_line_items.get('remote_command_'+str(i),'') and remote_connect:
                        if run_command(ssh_connection,cmd_line_items.get('remote_command_'+str(i),''),loop_item,run_remote = True): return None
                if cmd_line_items.get('local_command',''):
                    if run_command(ssh_connection,cmd_line_items.get('local_command',''),loop_item): return None
                for i in range(command_range):
                    if cmd_line_items.get('local_command_'+str(i),''):
                        if run_command(ssh_connection,cmd_line_items.get('local_command_'+str(i),''),loop_item): return None
                if cmd_line_items.get('exec',''):
                    if exec_command(ssh_connection,cmd_line_items.get('exec',''),loop_item): return None
                for i in range(command_range):
                    if cmd_line_items.get('exec_'+str(i),''):
                        if exec_command(ssh_connection,cmd_line_items.get('exec_'+str(i),''),loop_item): return None
                if cmd_line_items.get('eval',''):
                    if eval_command(ssh_connection,cmd_line_items.get('eval',''),loop_item): return None
                for i in range(command_range):
                    if cmd_line_items.get('eval_'+str(i),''):
                        if eval_command(ssh_connection,cmd_line_items.get('eval_'+str(i),''),loop_item): return None
        return True

    ### RUN_REMOTE_AND_LOCAL_COMMANDS START ====================================
    global remote_connect, glob_vars, DEVICE_PROMPTS
    ssh_connection, output= None, None
    command_range = 10
    try:
        if remote_connect:
            if use_module == 'netmiko':
                ssh_connection = netmiko.ConnectHandler(device_type = router_type, \
                    ip = DEVICE_HOST, port = int(DEVICE_PORT), \
                    username = USERNAME, password = PASSWORD)
            elif use_module == 'paramiko':
                client = paramiko.SSHClient()
                #client.load_system_host_keys()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(DEVICE_HOST, port=int(DEVICE_PORT), \
                              username=USERNAME, password=PASSWORD,look_for_keys=False)
                ssh_connection = client.invoke_shell()
                ssh_connection.settimeout(TIMEOUT)
                dummy, forget_it = ssh_send_command_and_read_output(ssh_connection,DEVICE_PROMPTS,TERM_LEN_0)
                dummy, forget_it = ssh_send_command_and_read_output(ssh_connection,DEVICE_PROMPTS,"")
                time.sleep(0.5)

        ### WORK REMOTE or LOCAL ===============================================
        if not logfilename:
            if 'WIN32' in sys.platform.upper(): logfilename = 'nul'
            else: logfilename = '/dev/null'
        with open(logfilename,"w") as fp:
            #if output and not printcmdtologfile: fp.write(output)
            for cmd_line_items in CMD:
                if debug: print('----> ',cmd_line_items)
                pre_condition_result = True
                if isinstance(cmd_line_items, dict) and cmd_line_items.get('pre_loop_if',''):
                    pre_condition_result = if_function(ssh_connection, \
                        cmd_line_items.get('pre_loop_if',''))
                if pre_condition_result:
                    if isinstance(cmd_line_items, (dict)):
                        if cmd_line_items.get('pre_loop_remote_command','') and remote_connect:
                            if run_command(ssh_connection,cmd_line_items.get('pre_loop_remote_command',''),run_remote = True): return None
                        for ii in range(command_range):
                            if cmd_line_items.get('pre_loop_remote_command_'+str(ii),'') and remote_connect:
                                if run_command(ssh_connection,cmd_line_items.get('pre_loop_remote_command_'+str(ii),''),run_remote = True): return None
                        if cmd_line_items.get('pre_loop_local_command',''):
                            if run_command(ssh_connection,cmd_line_items.get('pre_loop_local_command',''),loop_item): return None
                        if cmd_line_items.get('pre_loop_exec',''):
                            if exec_command(ssh_connection,cmd_line_items.get('pre_loop_exec',''),loop_item): return None
                        if cmd_line_items.get('pre_loop_eval',''):
                            if eval_command(ssh_connection,cmd_line_items.get('pre_if_eval',''),loop_item): return None
                    if isinstance(cmd_line_items, dict) and cmd_line_items.get('loop_glob_var',''):
                        for loop_item in glob_vars.get(cmd_line_items.get('loop_glob_var',''),''):
                            main_do_step(cmd_line_items,loop_item)
                    elif isinstance(cmd_line_items, dict) and cmd_line_items.get('loop',''):
                        for loop_item in eval(cmd_line_items.get('loop','')):
                            main_do_step(cmd_line_items,loop_item)
                    else: main_do_step(cmd_line_items)
                ### DIRECT REMOTE CALL WITHOUT PRE_IF --------------------------
                elif isinstance(cmd_line_items, (list,tuple,six.string_types)):
                    main_do_step(cmd_line_items)
    except () as e:
        print(bcolors.FAIL + " ... EXCEPTION: (%s)" % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        if remote_connect and ssh_connection:
            if use_module == 'netmiko': ssh_connection.disconnect()
            elif use_module == 'paramiko': client.close()
    return None


def get_version_from_file_last_modification_date(path_to_file = str(os.path.abspath(__file__))):
    file_time = None
    if 'WIN32' in sys.platform.upper():
        file_time = os.path.getmtime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        file_time = stat.st_mtime
    struct_time = time.gmtime(file_time)
    return str(struct_time.tm_year)[2:] + '.' + str(struct_time.tm_mon) + '.' + str(struct_time.tm_mday)

def append_variable_to_bashrc(variable_name=None,variable_value=None):
    forget_it = subprocess.check_output('echo export %s=%s >> ~/.bashrc'%(variable_name,variable_value), shell=True)

def send_me_email(subject='testmail', file_name='/dev/null'):
    if not 'WIN32' in sys.platform.upper():
        my_account = subprocess.check_output('whoami', shell=True)
        my_finger_line = subprocess.check_output('finger | grep "%s"'%(my_account.strip()), shell=True)
        try:
            my_name = my_finger_line.splitlines()[0].split()[1]
            my_surname = my_finger_line.splitlines()[0].split()[2]
            if EMAIL_ADDRESS: my_email_address = EMAIL_ADDRESS
            else: my_email_address = '%s.%s@orange.com' % (my_name, my_surname)
            mail_command = 'echo | mutt -s "%s" -a %s -- %s' % (subject,file_name,my_email_address)
            #mail_command = 'uuencode %s %s | mail -s "%s" %s' % (file_name,file_name,subject,my_email_address)
            forget_it = subprocess.check_output(mail_command, shell=True)
            print(' ==> Email "%s" sent to %s.'%(subject,my_email_address))
        except: pass


def generate_file_name(prefix = None, suffix = None , directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(WORKDIR,'logs')
    if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
    if os.path.exists(LOGDIR):
        if not prefix: filename_prefix = os.path.join(LOGDIR,'device')
        else: filename_prefix = prefix
        if not suffix: filename_suffix = 'log'
        else: filename_suffix = suffix
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,script_name.replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/')\
            .split('/')[-1],USERNAME,filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath


def sql_interface_data():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled
    def sql_read_all_table_columns(table_name):
        cursor = sql_connection.cursor()
        try: cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s'"%(table_name))
        except Exception as e: print(e)
        records = cursor.fetchall()
        cursor.close()
        columns = [item[3] for item in records]
        return columns

    def sql_read_data(sql_command):
        cursor = sql_connection.cursor()
        try: cursor.execute(sql_command)
        except Exception as e: print(e)
        records = cursor.fetchall()
        cursor.close()
        return records

    def sql_write_data(sql_command):
        #sql_connection.autocommit = False
        cursor = sql_connection.cursor(prepared=True)
        try: cursor.execute(sql_command)
        except Exception as e: print(e)
        if not sql_connection.autocommit: sql_connection.commit()
        cursor.close()
        return None

    try:
        sql_connection = mysql.connector.connect(host='localhost', user='cfgbuilder', \
            password='cfgbuildergetdata', database='rtr_configuration')

        if sql_connection.is_connected():
            #print(sql_read_all_table_columns('ipxt_data_collector'))
            #print(sql_read_data("SELECT * FROM ipxt_data_collector"))

            sql_table_columns = sql_read_all_table_columns('ipxt_data_collector')
            columns_string, values_string = str(), str()
            for key in bgp_data:
                if key in sql_table_columns:
                    if len(columns_string) > 0: columns_string += ','
                    if len(values_string) > 0: values_string += ','
                columns_string += '`' + key + '`'
                ### be aware of data type
                if isinstance(bgp_data.get(key,""), (list,tuple)):
                    item_string = str()
                    for item in bgp_data.get(key,""):
                        if isinstance(item, (six.string_types)):
                            if len(item_string) > 0: item_string += ','
                            item_string += item
                        elif isinstance(item, (dict,collections.OrderedDict)):
                            for i in item:
                                if len(item_string) > 0: item_string += ','
                                item_string += item.get(i,"")
                    values_string += "'" + item_string + "'"
                elif isinstance(bgp_data.get(key,""), (six.string_types)):
                    values_string += "'" + str(bgp_data.get(key,"")) + "'"

            sql_string = """INSERT INTO `ipxt_data_collector` (%s) VALUES (%s)""" \
                % (columns_string,values_string)
            print(sql_string)
            if columns_string:
                sql_write_data("""INSERT INTO `ipxt_data_collector`
                    (%s) VALUES (%s)""" %(columns_string,values_string))

            # SQL READ CHECK ---------------------------------------------------
            if bgp_data.get('vrf_name',""):
                check_data = sql_read_data("SELECT * FROM ipxt_data_collector WHERE vrf_name = '%s'" \
                    %(bgp_data.get('vrf_name',"")))
                print('DB_READ_CHECK:',check_data)
    except Exception as e: print(e)
    finally:
        if sql_connection.is_connected():
            sql_connection.close()
            print("SQL connection is closed.")


##############################################################################        

config_template_string = '''!<% rule_num = 10 %>
ipv4 access-list IPXT.${customer_name}-IN
% for rule in customer_prefixes_v4:
 ${rule_num} permit ipv4 ${rule['customer_prefix_v4']} ${rule['customer_subnetmask_v4']} any<% rule_num += 10 %>
% endfor
 ${rule_num} deny ipv4 any any
!
'''

input_jinja2_template = '''
<html>
   <body>
      <form action = "{{server_address}}:{{server_port}}/result" method = "POST">
        {% for key, value in parameters.items() %}
           <p>{{key}}<input type = "{{value}}" name = "{{key}}" /></p>
        {% endfor %}
        <p><input type = "submit" value = "submit" /></p>
      </form>
   </body>
</html>
'''

### FUNCTIONS ############################################ 
# def load_json(path, file_name):
#     """Open json file return dictionary."""
#     try:
#         json_data = json.load(open(path + file_name),object_pairs_hook=collections.OrderedDict)
#     except IOError as err:
#         raise Exception('Could not open file: {}'.format(err))
#     except json.decoder.JSONDecodeError as err:
#         raise Exception('JSON format error in: {} {}'.format(file_name, err))

#     return json_data

def print_config():
    mytemplate = Template(config_template_string)
    config_string = mytemplate.render(**bgp_data)
    return config_string

def print_json():
    try: json_data = json.dumps(bgp_data, indent=2)
    except: json_data = ''
    return json_data

def read_cgibin_get_post_form():
    # import collections, cgi
    # import cgitb; cgitb.enable()
    data, submit_form, username, password = collections.OrderedDict(), '', '', ''
    form = cgi.FieldStorage()
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable and value and not variable in ["submit","username","password"]: data[variable] = value
        if variable == "submit": submit_form = value
        if variable == "username": username = value
        if variable == "password": password = value
    return data, submit_form, username, password

def print_html_data(data):
    #print("Content-type:text/html\n\n")
    print("<html>")
    print("<head>")
    print("<title>DATA</title>")
    print("</head>")
    print("<body>")
    for key, value in data.items(): print("<h2>%s : %s</h2>" % (str(key), str(value)))
    print("</body>")
    print("</html>")


def find_last_logfile():
    most_recent_logfile = None
    log_file_name=os.path.join(LOGDIR,huawei_device_name.replace(':','_').replace('.','_')) + '*' + USERNAME + '*vrp-' + vpn_name + "*" + step1_string.replace(' ','_') + "*"
    log_filenames = glob.glob(log_file_name)
    if len(log_filenames) == 0:
        print(bcolors.MAGENTA + " ... Can't find any proper (%s) log file."%(log_file_name) + bcolors.ENDC)
        sys.exit()
    most_recent_logfile = log_filenames[0]
    for item in log_filenames:
        filecreation = os.path.getctime(item)
        if filecreation > (os.path.getctime(most_recent_logfile)):
            most_recent_logfile = item
    return most_recent_logfile
    
    

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### INIT PART #####################################################
glob_vars = {}
global_env = globals()
load_logfile = None

### CGI-BIN READ FORM ############################################
form_data, submit_form, cgi_username, cgi_password = read_cgibin_get_post_form()

if cgi_username and cgi_password: USERNAME, PASSWORD = cgi_username, cgi_password

if submit_form: 
    print("Content-type:text/html\n\n")
    print("<html><head><title>%s</title></head><body>"%(submit_form))
    for key, value in form_data.items(): print("CGI_DATA[%s:%s] <br/>\n" % (str(key), str(value)))

print('LOGDIR[%s] <br/>\n'%(LOGDIR))

script_action = submit_form.replace(' ','_') if submit_form else 'unknown_action' 
device_name = form_data.get('device','')
huawei_device_name = form_data.get('huawei-router-name','')

vpn_name = form_data.get('vpn','')
if vpn_name: glob_vars["VPN_NAME"] = vpn_name

###################################################################
VERSION = get_version_from_file_last_modification_date()

######## Parse program arguments ##################################
parser = argparse.ArgumentParser(
                    description = "Script v.%s" % (VERSION),
                    epilog = "e.g: \n" )
parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device',
                    default = str(),
                    help = "target router to check")
parser.add_argument("--user",
                    action = "store", dest = 'username', default = str(),
                    help = "specify router user login")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = None,
                    help = "print mode with no colors.")
parser.add_argument("--nolog",
                    action = 'store_true', dest = "nolog", default = None,
                    help = "no logging to file.")
parser.add_argument("--readlog",
                    action = "store", dest = 'readlog', default = None,
                    help = "name of the logfile to read json.")
parser.add_argument("--emailaddr",
                    action = "store", dest = 'emailaddr', default = '',
                    help = "insert your email address once if is different than name.surname@orange.com,\
                    it will do NEWR_EMAIL variable record in your bashrc file and \
                    you do not need to insert it any more.")
parser.add_argument("--vpn",
                    action = "store", dest = 'vpn', default = None,
                    help = "vpn name")
parser.add_argument("--latest",
                    action = 'store_true', dest = "latest", default = False,
                    help = "look for really latest shut file (also owned by somebody else),\
                    otherwise your own last shut file will be used by default")
parser.add_argument("--printall",action = "store_true", default = False,
                    help = "print all lines, changes will be coloured")
parser.add_argument("--sim",
                    action = 'store_true', dest = "sim",
                    #default = True,
                    default = None,
                    help = "simulate critical command runs")
args = parser.parse_args()

if args.nocolors or 'WIN32' in sys.platform.upper() or submit_form: bcolors = nocolors

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

### PARSE CMDLINE ARGUMENTS IF NOT CGI-BIN ARGUMENTS #################    
if device_name and not vpn_name and not submit_form:
    device_name = args.device
    
    if args.emailaddr:
        append_variable_to_bashrc(variable_name='NEWR_EMAIL',variable_value=args.emailaddr)
        EMAIL_ADDRESS = args.emailaddr

    if args.sim: glob_vars["SIM_CMD"] = 'ON'
    else: glob_vars["SIM_CMD"] = 'OFF'

    if args.vpn: glob_vars["VPN_NAME"] = args.vpn; vpn_name = args.vpn
    else:
        print(bcolors.MAGENTA + " ... VPN NAME must be specified!" + bcolors.ENDC )
        sys.exit(0)


    if args.device == str():
        remote_connect = None
        local_hostname = str(subprocess.check_output('hostname',shell=True).decode('utf8')).strip().replace('\\','').replace('/','')
        device_name = local_hostname


    if args.readlog:
        bgp_data = read_bgp_data_json_from_logfile(args.readlog)
        if not bgp_data:
            print(bcolors.MAGENTA + " ... Please insert shut session log! (Inserted log seems to be noshut log.)" + bcolors.ENDC )
            sys.exit(0)

    if remote_connect:
        ####### Set USERNAME if needed
        if args.username: USERNAME = args.username
        if not USERNAME:
            print(bcolors.MAGENTA + " ... Please insert your username by cmdline switch \
                --user username !" + bcolors.ENDC )
            sys.exit(0)

        # SSH (default)
        if not PASSWORD:
            PASSWORD = getpass.getpass("TACACS password: ")

logfilename, router_type = None, None

load_logfile = find_last_logfile()
bgp_data = copy.deepcopy(read_bgp_data_json_from_logfile(load_logfile))
print(bgp_data)
print(form_data) 




# if device_name:
    # router_prompt = None
    # try: DEVICE_HOST = device_name.split(':')[0]
    # except: DEVICE_HOST = str()
    # try: DEVICE_PORT = device_name.split(':')[1]
    # except: DEVICE_PORT = '22'
    # print('DEVICE %s (host=%s, port=%s) START.........................'\
        # %(device_name,DEVICE_HOST, DEVICE_PORT))
    # if remote_connect:
        # ####### Figure out type of router OS
            # router_type, router_prompt = detect_router_by_ssh(device_name)
            # if not router_type in KNOWN_OS_TYPES:
                # print('%sUNSUPPORTED DEVICE TYPE: %s , BREAK!%s' % \
                    # (bcolors.MAGENTA,router_type, bcolors.ENDC))
            # else: print('DETECTED DEVICE_TYPE: %s' % (router_type))

    # ######## Create logs directory if not existing  #########
    # if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
    # on_off_name = ''
    # logfilename = generate_file_name(prefix = device_name, suffix = 'vrp-' + vpn_name + '-' + script_action + '-log')
    # if args.nolog: logfilename = None

    # ######## Find command list file (optional)
    # list_cmd = []

    # if len(list_cmd)>0: CMD = list_cmd
    # else:
        # if router_type == 'cisco_ios':
            # CMD = CMD_IOS_XE
            # DEVICE_PROMPTS = [ \
                # '%s%s#'%(device_name.upper(),''), \
                # '%s%s#'%(device_name.upper(),'(config)'), \
                # '%s%s#'%(device_name.upper(),'(config-if)'), \
                # '%s%s#'%(device_name.upper(),'(config-line)'), \
                # '%s%s#'%(device_name.upper(),'(config-router)')  ]
            # TERM_LEN_0 = "terminal length 0"
            # EXIT = "exit"
        # elif router_type == 'cisco_xr':
            # CMD = CMD_IOS_XR
            # DEVICE_PROMPTS = [ \
                # '%s%s#'%(device_name.upper(),''), \
                # '%s%s#'%(device_name.upper(),'(config)'), \
                # '%s%s#'%(device_name.upper(),'(config-if)'), \
                # '%s%s#'%(device_name.upper(),'(config-line)'), \
                # '%s%s#'%(device_name.upper(),'(config-router)')  ]
            # TERM_LEN_0 = "terminal length 0"
            # EXIT = "exit"
        # elif router_type == 'juniper':
            # CMD = CMD_JUNOS
            # DEVICE_PROMPTS = [ \
                 # USERNAME + '@' + device_name.upper() + '> ', # !! Need the space after >
                 # USERNAME + '@' + device_name.upper() + '# ' ]
            # TERM_LEN_0 = "set cli screen-length 0"
            # EXIT = "exit"
        # elif router_type == 'huawei' :
            # CMD = CMD_VRP
            # DEVICE_PROMPTS = [ \
                # '<' + device_name.upper() + '>',
                # '[' + device_name.upper() + ']',
                # '[~' + device_name.upper() + ']',
                # '[*' + device_name.upper() + ']' ]
            # TERM_LEN_0 = "screen-length 0 temporary"     #"screen-length disable"
            # EXIT = "quit"
        # elif router_type == 'linux':
            # CMD = CMD_LINUX
            # DEVICE_PROMPTS = [ ]
            # TERM_LEN_0 = ''     #"screen-length disable"
            # EXIT = "exit"
        # else: CMD = CMD_LOCAL

    # # ADD PROMPT TO PROMPTS LIST
    # if router_prompt: DEVICE_PROMPTS.append(router_prompt)

    # # if submit_form and submit_form == step1_string or router_type == 'huawei':
        # # run_remote_and_local_commands(CMD, logfilename, printall = args.printall, printcmdtologfile = True)
        

    # if logfilename and os.path.exists(logfilename):
        # print('%s file created.' % (logfilename))
        # ### MAKE READABLE for THE OTHERS
        # try:
            # dummy = subprocess.check_output('chmod +r %s' % (logfilename),shell=True)
        # except: pass
        # if not submit_form:
            # try: send_me_email(subject = logfilename.replace('\\','/').\
                     # split('/')[-1], file_name = logfilename)
            # except: pass
    # print('\nDEVICE %s DONE.'%(device_name))

    # if submit_form and submit_form == step1_string or router_type == 'huawei':    
        # if router_type == 'huawei': sql_interface_data()
            
print('\nEND [script runtime = %d sec].'%(time.time() - START_EPOCH))
if submit_form: print("</body></html>")



