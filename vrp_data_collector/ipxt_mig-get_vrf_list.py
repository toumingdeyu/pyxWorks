#!/usr/bin/python

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
from mako.template import Template
from mako.lookup import TemplateLookup
import cgi
import cgitb; cgitb.enable()
import requests
#import interactive
#python 2.7 problem - hack 'pip install esptool'
import netmiko

step1_string = 'Submit step 1'


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
CMD_IOS_XE = [
]

CMD_IOS_XR = [
]

CMD_JUNOS = []

CMD_VRP = [
    {'exec':'bgp_data["username"] = USERNAME'},
    {'exec':'bgp_data["session_id"] = logfilename'},
    {'exec':'bgp_data["pe_router"] = CGI_CLI.data.get("device","")'},
    {
     'remote_command':'display bgp vpnv4 all peer | in (VPN-Instance)',
     'exec':'bgp_data["vrf_list"] = "" \
           \ntry: \
           \n  for vpnline in glob_vars.get("last_output","").split("VPN-Instance ")[1:]: \
           \n    bgp_data["vrf_list"] += vpnline.split()[0].replace(",","").strip() + ","\
           \n  bgp_data["vrf_list"] = bgp_data["vrf_list"].rstrip(",")\
           \nexcept: pass\
           \nCGI_CLI.uprint("VPN_LIST: " + bgp_data.get("vrf_list","---"))',
    },
]

CMD_LINUX = []

CMD_LOCAL = []


###############################################################################
bgp_data = collections.OrderedDict()


###############################################################################
#
# Function and Class
#
###############################################################################

def read_gw_vrf_parsed_lines(text):
    ip_address, as_number = None, None
    for line in text:
        try: ip_addr = line.split()[0]; as_nr = int(line.split()[2]) 
        except: ip_addr = None; as_nr = None
        if as_nr and ip_addr and as_nr != 2300 and '.' in ip_addr: ip_address = ip_addr; as_number = as_nr       
    return ip_address, str(as_number)

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


def ssh_raw_detect_router_type(device, debug = None):
    # detect device prompt
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
                if debug: print('BUFFER:' + buff)
                try: last_line = output.splitlines()[-1].strip().replace('\x20','')
                except: last_line = 'dummyline1'
                try: 
                    last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
                    if len(last_but_one_line) == 0:
                        ### vJunos '\x20' --> '\n\nprompt' workarround
                        last_but_one_line = output.splitlines()[-3].strip().replace('\x20','')
                except: last_but_one_line = 'dummyline2'
        prompt = output.splitlines()[-1].strip()
        if debug: print('DETECTED PROMPT: \'' + prompt + '\'')
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
    router_os = str()
    client = paramiko.SSHClient()
    #client.load_system_host_keys()
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
        with open(logfilename,"a+") as fp:
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

def send_me_email(subject = str(), email_body = str(), file_name = None, attachments = None, \
        email_address = None, cc = None, bcc = None, username = None):
    def send_unix_email_body(mail_command):
        email_success = None
        try: 
            forget_it = subprocess.check_output(mail_command, shell=True)
            CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by COMMAND=[%s] with RESULT=[%s]...'\
                %(subject,sugested_email_address,mail_command,forget_it), color = 'blue')
            email_success = True    
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by COMMAND=[%s], PROBLEM=[%s]\n"\
                % (mail_command,str(e)) ,color = 'red')
        return email_success        
    ### FUCTION send_me_email START ----------------------------------------                    
    email_sent, sugested_email_address = None, str()
    if username: my_account = username        
    else: my_account = subprocess.check_output('whoami', shell=True).strip()    
    if email_address: sugested_email_address = email_address    
    if not 'WIN32' in sys.platform.upper():        
        try: 
            ldapsearch_output = subprocess.check_output('ldapsearch -LLL -x uid=%s mail' % (my_account), shell=True)
            ldap_email_address = ldapsearch_output.decode("utf-8").split('mail:')[1].splitlines()[0].strip()
        except: ldap_email_address = None        
        if ldap_email_address: sugested_email_address = ldap_email_address
        else:
            try: 
                my_getent_line = ' '.join((subprocess.check_output('getent passwd "%s"'% \
                    (my_account.strip()), shell=True)).split(':')[4].split()[:2])
                my_name = my_getent_line.splitlines()[0].split()[0]
                my_surname = my_getent_line.splitlines()[0].split()[1]
                sugested_email_address = '%s.%s@orange.com' % (my_name, my_surname)    
            except: pass        

        ### UNIX - MAILX ----------------------------------------------------
        mail_command = 'echo \'%s\' | mailx -s "%s" ' % (email_body,subject)
        if cc:
            if isinstance(cc, six.string_types): mail_command += '-c %s' % (cc)
            if cc and isinstance(cc, (list,tuple)): mail_command += ''.join([ '-c %s ' % (bcc_email) for bcc_email in bcc ])
        if bcc:
            if isinstance(bcc, six.string_types): mail_command += '-b %s' % (bcc)
            if bcc and isinstance(bcc, (list,tuple)): mail_command += ''.join([ '-b %s ' % (bcc_email) for bcc_email in bcc ])    
        if file_name and isinstance(file_name, six.string_types) and os.path.exists(file_name): 
            mail_command += '-a %s ' % (file_name)
        if attachments:
            if isinstance(attachments, (list,tuple)): 
                mail_command += ''.join([ '-a %s ' % (attach_file) for attach_file in attachments if os.path.exists(attach_file) ])      
            if isinstance(attachments, six.string_types) and os.path.exists(attachments):
                mail_command += '-a %s ' % (attachments)
        mail_command += '%s' % (sugested_email_address)            
        email_sent = send_unix_email_body(mail_command)

    if 'WIN32' in sys.platform.upper():
        ### NEEDED 'pip install pywin32'
        #if not 'win32com.client' in sys.modules: import win32com.client
        import win32com.client
        olMailItem, email_application = 0, 'Outlook.Application'
        try:
            ol = win32com.client.Dispatch(email_application)
            msg = ol.CreateItem(olMailItem)
            if email_address:
                msg.Subject, msg.Body = subject, email_body
                if email_address:
                    if isinstance(email_address, six.string_types): msg.To = email_address
                    if email_address and isinstance(email_address, (list,tuple)): 
                        msg.To = ';'.join([ eadress for eadress in email_address if eadress != "" ])                
                if cc:
                    if isinstance(cc, six.string_types): msg.CC = cc
                    if cc and isinstance(cc, (list,tuple)): 
                        msg.CC = ';'.join([ eadress for eadress in cc if eadress != "" ])
                if bcc:
                    if isinstance(bcc, six.string_types): msg.BCC = bcc
                    if bcc and isinstance(bcc, (list,tuple)): 
                        msg.BCC = ';'.join([ eadress for eadress in bcc if eadress != "" ])             
                if file_name and isinstance(file_name, six.string_types) and os.path.exists(file_name): 
                    msg.Attachments.Add(file_name)
                if attachments:
                    if isinstance(attachments, (list,tuple)): 
                        for attach_file in attachments:
                            if os.path.exists(attach_file): msg.Attachments.Add(attach_file)      
                    if isinstance(attachments, six.string_types) and os.path.exists(attachments):
                        msg.Attachments.Add(attachments)
               
            msg.Send()
            ol.Quit()
            CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by APPLICATION=[%s].'\
                %(subject,sugested_email_address,email_application), color = 'blue')
            email_sent = True    
        except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by APPLICATION=[%s], PROBLEM=[%s]\n"\
                % (email_application,str(e)) ,color = 'red')            
    return email_sent




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
    

def find_dict_duplicate_keys(data1, data2):
    duplicate_keys_list = None
    if data1 and data2:
        list1 = list(data1.keys())
        list2 = list(data2.keys())
        for item in list2:
            if item in list1:
                if not duplicate_keys_list: duplicate_keys_list = []
                duplicate_keys_list.append(list1)
    return duplicate_keys_list


def get_variable_name(var):
    import inspect
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    var_list = [var_name for var_name, var_val in callers_local_vars if var_val is var]
    return str(','.join(var_list))


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
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "target router to check")
        parser.add_argument("--printall",action = "store_true", default = None,
                            help = "print all lines, changes will be coloured")                            
        # parser.add_argument("--pe_device",
                            # action = "store", dest = 'pe_device',
                            # default = str(),
                            # help = "target pe router to check")
        # parser.add_argument("--gw_device",
                            # action = "store", dest = 'gw_device',
                            # default = str(),
                            # help = "target gw router to check")                    
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
    def init_cgi(interaction = None):
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
            if not 'cgitb' in sys.modules: import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
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
        CGI_CLI.uprint('USERNAME[%s], PASSWORD[%s]' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No'))        
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

    @staticmethod 
    def oprint(text, tag = None):
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
    def uprint(text, tag = None, color = None, name = None, jsonprint = None):
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
                if tag and 'h' in tag: print('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
                if color or tag and 'p' in tag: tag = 'p'; print('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
                if isinstance(print_text, six.string_types): 
                    print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                        replace('>','&gt;').replace('\n','<br/>').replace(' ','&nbsp;')) 
            print(print_name + print_text)
            del print_text
            if CGI_CLI.cgi_active: 
                print('<br/>');
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
        print_string = 'python[%s], ' % (str(python_version()))
        print_string += 'file[%s], ' % (sys.argv[0])
        print_string += 'version[%s], ' % (CGI_CLI.VERSION())
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_args = %s' % (json.dumps(CGI_CLI.data)) 
            except: pass                 
        else: print_string += 'CLI_args = %s' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string


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
        columns = None
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s';"%(table_name))
                records = cursor.fetchall()
                columns = [item[3] for item in records]
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return columns 

    def sql_read_sql_command(self, sql_command):
        '''NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE'''
        records = None
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute(sql_command)
                records = cursor.fetchall()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
            ### FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
        return records 

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
CGI_CLI()
USERNAME, PASSWORD = CGI_CLI.init_cgi()
CGI_CLI.print_args()

device_name = CGI_CLI.data.get('device','')
glob_vars["CGI_ACTIVE"] = CGI_CLI.cgi_active

###################################################################

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

### PARSE CMDLINE ARGUMENTS IF NOT CGI-BIN ARGUMENTS #################    
glob_vars["SIM_CMD"] = 'OFF'

if not CGI_CLI.cgi_active:
    if CGI_CLI.args.device:
        device_name = CGI_CLI.args.device              
    if CGI_CLI.args.device == str():
        remote_connect = None
        local_hostname = str(subprocess.check_output('hostname',shell=True).decode('utf8')).strip().replace('\\','').replace('/','')
        device_name = local_hostname

logfilename, router_type, first_router_type = None, None, None

if device_name:
    router_prompt = None
    try: DEVICE_HOST = device_name.split(':')[0]
    except: DEVICE_HOST = str()
    try: DEVICE_PORT = device_name.split(':')[1]
    except: DEVICE_PORT = '22'
    CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START.........................'\
        %(device_name,DEVICE_HOST, DEVICE_PORT))
    if remote_connect:
        ####### Figure out type of router OS
            router_type, router_prompt = ssh_raw_detect_router_type(device_name)
            if not router_type in KNOWN_OS_TYPES:
                CGI_CLI.uprint('%sUNSUPPORTED DEVICE TYPE: %s , BREAK! %s' % \
                    (bcolors.MAGENTA,router_type, bcolors.ENDC))
            else: CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s ' % (router_type))

    ######## Create logs directory if not existing  #########
    if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)

    ######## Find command list file (optional)
    list_cmd = []

    if len(list_cmd)>0: CMD = list_cmd
    else:
        if router_type == 'cisco_ios':
            CMD = CMD_IOS_XE
            DEVICE_PROMPTS = [ \
                '%s%s#'%(device_name.upper(),''), \
                '%s%s#'%(device_name.upper(),'(config)'), \
                '%s%s#'%(device_name.upper(),'(config-if)'), \
                '%s%s#'%(device_name.upper(),'(config-line)'), \
                '%s%s#'%(device_name.upper(),'(config-router)')  ]
            TERM_LEN_0 = "terminal length 0"
            EXIT = "exit"
        elif router_type == 'cisco_xr':
            CMD = CMD_IOS_XR
            DEVICE_PROMPTS = [ \
                '%s%s#'%(device_name.upper(),''), \
                '%s%s#'%(device_name.upper(),'(config)'), \
                '%s%s#'%(device_name.upper(),'(config-if)'), \
                '%s%s#'%(device_name.upper(),'(config-line)'), \
                '%s%s#'%(device_name.upper(),'(config-router)')  ]
            TERM_LEN_0 = "terminal length 0"
            EXIT = "exit"
        elif router_type == 'juniper':
            CMD = CMD_JUNOS
            DEVICE_PROMPTS = [ \
                 USERNAME + '@' + device_name.upper() + '> ', # !! Need the space after >
                 USERNAME + '@' + device_name.upper() + '# ' ]
            TERM_LEN_0 = "set cli screen-length 0"
            EXIT = "exit"
        elif router_type == 'huawei' :
            CMD = CMD_VRP
            DEVICE_PROMPTS = [ \
                '<' + device_name.upper() + '>',
                '[' + device_name.upper() + ']',
                '[~' + device_name.upper() + ']',
                '[*' + device_name.upper() + ']' ]
            TERM_LEN_0 = "screen-length 0 temporary"     #"screen-length disable"
            EXIT = "quit"
        elif router_type == 'linux':
            CMD = CMD_LINUX
            DEVICE_PROMPTS = [ ]
            TERM_LEN_0 = ''     #"screen-length disable"
            EXIT = "exit"
        else: CMD = CMD_LOCAL

    # ADD PROMPT TO PROMPTS LIST
    if router_prompt: DEVICE_PROMPTS.append(router_prompt)
    first_router_type = router_type
    
    if CGI_CLI.cgi_active and CGI_CLI.submit_form == step1_string or router_type == 'huawei':
        run_remote_and_local_commands(CMD, logfilename, printall = CGI_CLI.args.printall, printcmdtologfile = True)
    else: pass        
    CGI_CLI.uprint('\nDEVICE %s DONE. '%(device_name))
    
    if CGI_CLI.cgi_active and CGI_CLI.submit_form == step1_string or first_router_type == 'huawei':    
        if first_router_type == 'huawei': 
            sql_inst = sql_interface(host='localhost', user='cfgbuilder', \
                password='cfgbuildergetdata', database='rtr_configuration')
            CGI_CLI.uprint(bgp_data, tag = 'p', color = 'blue', name = True, jsonprint = True)    
            CGI_CLI.uprint('BEFORE_SQL_WRITE:',tag = 'h1')    
            CGI_CLI.uprint(sql_inst.sql_read_last_record_to_dict(from_string = 'ipxt_vrf_list'), jsonprint = True)    
            sql_inst.sql_write_table_from_dict('ipxt_vrf_list', bgp_data)  
            CGI_CLI.uprint('AFTER_SQL_WRITE:',tag = 'h1')
            CGI_CLI.uprint(sql_inst.sql_read_last_record_to_dict(from_string = 'ipxt_vrf_list'), jsonprint = True)



# MariaDB [rtr_configuration]> describe ipxt_vrf_list;                                 
# +-----------+---------------+------+-----+---------+----------------+
# | Field     | Type          | Null | Key | Default | Extra          |
# +-----------+---------------+------+-----+---------+----------------+
# | id        | int(11)       | NO   | PRI | NULL    | auto_increment |
# | pe_router | varchar(6)    | NO   |     | NULL    |                |
# | vrf_list  | varchar(1000) | YES  |     | NULL    |                |
# +-----------+---------------+------+-----+---------+----------------+ 

# AUVPE3
# PASPE8
# HKGPE3
# SINPE3
# MIAPE4
# NYKPE3