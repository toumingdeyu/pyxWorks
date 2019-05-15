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
import collections

#python 2.7 problem - hack 'pip install esptool'
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
script_name      = sys.argv[0]
TIMEOUT          = 60

KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']

try:    WORKDIR         = os.environ['HOME']
except: WORKDIR         = str(os.path.dirname(os.path.abspath(__file__)))
if WORKDIR: LOGDIR      = os.path.join(WORKDIR,'logs')

try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()

print('LOGDIR: ' + LOGDIR)

###############################################################################
#
# Generic list of commands
#
###############################################################################


# IOS-XE is only for IPsec GW
CMD_IOS_XE = [

              ]
CMD_IOS_XR = [
               {"remote_command":['show bgp vrf all summary | in "VRF: " | ex "monitor-vpn"', {'output_variable':'bgp_vpn_all_summary'}]},
               {'loop_zipped_list':'bgp_vpn_all_summary',"exec":['update_bgpdata_structure(bgp_data["vrf_list"][',{'zipped_item':'0'},'],"vrf_name","',{'zipped_item':'1'},'", ',{'zipped_item':'0'},',void_neighbor_list_item)']}

#              'show bgp vrf all summary',
#              {'local_function':'get_ciscoxr_bgp_vpn_peer_data', 'input_variable':'last_output',\
#                  'output_variable':'bgp_vpn_peers', 'if_output_is_void':'exit'},
#              {'loop_zipped_list':'bgp_vpn_peers','remote_command':('show bgp vrf ',{'zipped_item':'0'},\
#                  ' neighbors ',{'zipped_item':'1'}) },
#
#              {'loop_zipped_list':'bgp_vpn_peers','remote_command':('show bgp vrf ',{'zipped_item':'0'},\
#                  ' neighbors ',{'zipped_item':'1'},' routes') },
#
#              'sh ipv4 vrf all int brief | exclude "unassigned|Protocol|default"',
#              {'local_function':'get_ciscoxr_vpnv4_all_interfaces', 'input_variable':'last_output',\
#                  'output_variable':'interface_list', 'if_output_is_void':'exit'},
#              {'loop_zipped_list':'interface_list','remote_command':('show interface ',{'zipped_item':'2'})},
#
#              {'loop_zipped_list':'bgp_vpn_peers','remote_command':('ping vrf ',{'zipped_item':'0'},\
#                  ' ',{'zipped_item':'1'},' size 1470 count 2')},
             ]
CMD_JUNOS = [

             ]
CMD_VRP = [
             'display bgp vpnv4 all peer',
             {'local_function':'get_huawei_bgp_vpn_peer_data', 'input_variable':'last_output',\
                 'output_variable':'bgp_vpn_peers', 'if_output_is_void':'exit'},
             {'loop_zipped_list':'bgp_vpn_peers','remote_command':('dis bgp vpnv4 vpn-instance ',\
                 {'zipped_item':'0'},' peer ',{'zipped_item':'1'},' verbose') },


             {'loop_zipped_list':'bgp_vpn_peers','remote_command':('dis bgp vpnv4 vpn-instance ',\
                 {'zipped_item':'0'},' routing-table peer ',{'zipped_item':'1'},' accepted-routes') },

             'dis curr int | in (interface|ip binding vpn-instance)',
             {'local_function':'get_huawei_vpn_interface', 'input_variable':'last_output',\
                 'output_variable':'interface_list', 'if_output_is_void':'exit'},
#              {'loop_zipped_list':'interface_list','remote_command':('dis interface ',{'zipped_item':'2'})},
#
#              {'loop_zipped_list':'bgp_vpn_peers','remote_command':('ping -s 1470 -c 2 -t 2000 -vpn-instance ',\
#                  {'zipped_item':'0'},' ',{'zipped_item':'1'})},
          ]
CMD_LINUX = [
#             'hostname',
#             ('echo ', {'input_variable':'last_output'},{"output_variable":"hostname"}),
#             {"remote_command":("who ", "| grep 2019",{"output_variable":"linux_users"})},
#             {"local_command":("echo ", {"input_variable":"linux_users"} , {"output_variable":"linux_users_2"})},
#             {"local_command":("echo ", {"input_variable":"linux_users"} , {"output_variable":"linux_users_2"})},
#             ('echo ', 'aaaa+', {"input_variable":"hostname"}),
#             {'local_function':"return_parameters", "input_variable":"linux_users"},
#             {'local_function':"return_parameters", "input_parameters":[{"input_variable":"linux_users"}]},
#             {'local_function':"return_splitlines_parameters", "input_parameters":[{"input_variable":"linux_users"}] , "output_variable":"splitlines_linux_users"},
#             {'loop_zipped_list':'splitlines_linux_users', 'remote_command':['echo ', {'zipped_item':'0'}] },
#             {'loop_zipped_list':'splitlines_linux_users', 'local_command':['echo ', {'zipped_item':'0'}] },
            #('echo ', {'input_variable':'notexistent'},{'if_output_is_void':'exit'}),
            'free -m',
            {"exec":['update_bgpdata_structure(bgp_data["vrf_list"][',0,'],"vrf_name","','aaaaaa','", ',0,',void_neighbor_list_item)']}

            ]


################################################################################
bgp_data = collections.OrderedDict()

### Start of BASIC STRUCTURES OF JSON
neighbor_list_item_txt_template = '''
{
    "ip_address": null,
    "bgp_current_state": null,
    "received_total_routes": null,
    "advertised_total_routes": null,
    "maximum_allowed_route_limit": null,
    "import_route_policy_is": null,
    "ping_response_success": null,
    "accepted-routes_list": []
}
'''

vrf_list_item_txt_template = '''
{
    "vrf_name": null,
    "neighbor_list": [%s],
    "interface_name": null,
    "interface_mtu" : null,
    "interface_intput_packets_per_seconds": null,
    "interface_output_packets_per_seconds": null
}
''' % (neighbor_list_item_txt_template)

bgp_json_txt_template='''
{
    "vrf_list": [%s]
}
''' % (vrf_list_item_txt_template)
### End of BASIC STRUCTURES OF JSON

bgp_data = json.loads(bgp_json_txt_template, \
    object_pairs_hook = collections.OrderedDict)

void_vrf_list_item = json.loads(vrf_list_item_txt_template, \
    object_pairs_hook = collections.OrderedDict)

void_neighbor_list_item = json.loads(neighbor_list_item_txt_template, \
    object_pairs_hook = collections.OrderedDict)

###############################################################################
#
# Function and Class
#
###############################################################################

def return_parameters(text):
    return text

def return_splitlines_parameters(text):
    return text.splitlines()


def update_bgpdata_structure(data_address, key_name = None, value = None, \
    order_in_list = None, list_append_value = None, add_new_key = None, \
    debug = None):
    """
    FUNCTION: update_bgpdata_structure
    PARAMETERS:
       data_address - address of json ending on parrent (key_name or list_number if exists)
       key_name - name of key in dict
       value - value of key in dict
       order_in_list - if actuaal list is shorter than needed, append new template section
       list_append_value - add new template section to list
       add_new_key = True - add new keys/values to dictionary not existent in templates
       debug - True/None
    RETURNS:
       change_applied - True = change applied , None - no change
    """
    global bgp_data
    change_applied = None
    if debug: print("DATA_TYPE: ", type(data_address),'ID: ',id(data_address), \
         "DATA: ", data_address)
    ### REWRITE VALUE IN DICT ON KEY_NAME POSITION
    if isinstance(data_address, (dict,collections.OrderedDict)) \
        and isinstance(key_name, (six.string_types)):
        data_address_values = data_address.keys()
        for address_key_value in data_address_values:
            if key_name and key_name == address_key_value:
                data_address[key_name] = value
                if debug: print('DICT[%s]=%s.'%(key_name,value))
                change_applied = True
        else:
            if add_new_key:
                data_address[key_name] = value
                if debug: print('ADDED_TO_DICT[%s]=%s.'%(key_name,value))
                change_applied = True
    ### ADD LIST POSITION if NEEDED, REWRITE VALUE IN DICT ON KEY_NAME POSITION
    elif isinstance(data_address, (list,tuple)):
        ### SIMPLY ADD VALUE TO LIST WHEN ORDER NOT INSERTED
        if not order_in_list and not key_name:
            if debug: print('LIST_APPENDED.')
            data_address.append(value)
            change_applied = True
        else:
            ### ORDER_IN_LIST=[0..], LEN()=[0..]
            if order_in_list == len(data_address):
                data_address.append(list_append_value)
                if debug: print('LIST_APPENDED_BY_ONE_SECTION.')
            ### AFTER OPTIONAL ADDITION OF END OF LIST BY ONE
            if order_in_list <= len(data_address)-1 \
                and isinstance(data_address[order_in_list], \
                (dict,collections.OrderedDict)):
                data_address_values = data_address[order_in_list].keys()
                for key_list_item in data_address_values:
                   if key_name and key_name == key_list_item:
                       data_address[order_in_list][key_name] = value
                       if debug: print('DICT_LIST[%s][%s]=%s.'% \
                           (order_in_list,key_name,value))
                       change_applied = True
                else:
                    if add_new_key:
                        data_address[order_in_list][key_name] = value
                        if debug: print('ADDED_TO_DICT_LIST[%s][%s]=%s.'% \
                            (order_in_list,key_name,value))
                        change_applied = True
    if debug: print("CHANGE_APPLIED: ",change_applied)
    return change_applied


def get_first_value_after(text = None, split_text = None, delete_text = None):
    output = str()
    if text:
        try:
            output = text.strip().split(split_text)[1].split()[0].strip()
            if delete_text: output = output.replace(delete_text,'')
        except: pass
    return output


def get_huawei_vpn_interface(text = None):
    output = []
    if text:
        try: text = text.strip().split('MET')[1]
        except: text = text.strip()
        for interface in text.split('interface'):
            try:
                ### LIST=VPN,INTERFACE_NAME
                interface_name = interface.split()[0].strip()
                vpn_name = interface.split('ip binding vpn-instance')[1].strip()
                output.append((vpn_name,interface_name))
            except: pass
    return output


def get_ciscoxr_vpnv4_all_interfaces(text = None):
    output = []
    if text:
        try: text = text.strip().split('MET')[1]
        except: text = text.strip()
        for row in text.splitlines():
           ### LIST=VPN,INTERFACE_NAME
           columns = row.strip().split()
           try: output.append((columns[4],columns[0]))
           except: pass
    return output


def get_ciscoxr_bgp_vpn_peer_data(text = None):
    output = []
    if text:
        try:
            vpn_sections = text.split('VRF: ')[1:]
            for vpn_section in vpn_sections:
               vpn_instance   = vpn_section.splitlines()[0].strip()
               try: vpn_peer_lines = vpn_section.strip().split('Neighbor')[1].splitlines()[1:]
               except: vpn_peer_lines = []
#                vpn_peers = [vpn_peer_line.split()[0] for vpn_peer_line in vpn_peer_lines]
#                output.append((vpn_instance,vpn_peers))
               for vpn_peer_line in vpn_peer_lines:
                   output.append((vpn_instance,vpn_peer_line.split()[0]))
        except: pass
    return output


def get_huawei_bgp_vpn_peer_data(text = None):
    output = []
    if text:
        try:
            vpn_sections = text.split('VPN-Instance')[1:]
            for vpn_section in vpn_sections:
               vpn_instance   = vpn_section.split(',')[0].strip()
               try: vpn_peer_lines = vpn_section.strip().splitlines()[1:]
               except: vpn_peer_lines = []
#                vpn_peers = [vpn_peer_line.split()[0] for vpn_peer_line in vpn_peer_lines]
#                output.append((vpn_instance,vpn_peers))
               for vpn_peer_line in vpn_peer_lines:
                   output.append((vpn_instance,vpn_peer_line.split()[0]))
        except: pass
    return output


def netmiko_autodetect(device, debug = None):
    router_os = str()
    try: DEVICE_HOST = device.split(':')[0]
    except: DEVICE_HOST = str()
    try: DEVICE_PORT = device.split(':')[1]
    except: DEVICE_PORT = '22'
    guesser = netmiko.ssh_autodetect.SSHDetect(device_type='autodetect', \
        ip=DEVICE_HOST, port=int(DEVICE_PORT), username=USERNAME, password=PASSWORD)
    best_match = guesser.autodetect()
    if debug:
        print('BEST_MATCH: %s\nPOTENTIAL_MATCHES:' %(best_match))
        print(guesser.potential_matches)
    router_os = best_match
    return router_os


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
    return netmiko_os
    #return router_os, prompt


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
    try: set_text = text.split('set')[1].split('\n')[0]
    except: set_text = str()
    if set_text: set_ipv6line = 'set' + set_text + ' primary\n'
    else: set_ipv6line = str()
    return set_ipv6line

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


def run_remote_and_local_commands(CMD, logfilename = None, printall = None, printcmdtologfile = None):
    ### RUN_COMMAND - REMOTE or LOCAL ------------------------------------------
    def run_command(ssh_connection,cmd_line_items,loop_item = None,run_remote = None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global dictionary_of_variables
        cli_line, name_of_output_variable = str(), None
        ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE/LOCAL DEVICE COMMANDS
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if isinstance(cmd_line_items, six.string_types): cli_line = cmd_line_items
            elif isinstance(cmd_line_items, (list,tuple)):
                for cli_item in cmd_line_items:
                    if isinstance(cli_item, dict):
                        if cli_item.get('zipped_item',''):
                            try: cli_line += str(loop_item[int(cli_item.get('zipped_item',''))])
                            except: pass
                        elif cli_item.get('input_variable',''):
                            name_of_input_variable = cli_item.get('input_variable','')
                            cli_line += dictionary_of_variables.get(name_of_input_variable,'')
                        elif cli_item.get('output_variable',''):
                            name_of_output_variable = cli_item.get('output_variable','')
                    else: cli_line += str(cli_item)
            if run_remote:
                print(bcolors.GREEN + "REMOTE_COMMAND: %s" % (cli_line) + bcolors.ENDC )
                ### NETMIKO
                last_output = ssh_connection.send_command(cli_line)

                ### PARAMIKO
                #last_output, new_prompt = ssh_send_command_and_read_output(ssh_connection,DEVICE_PROMPTS,cli_line)
                #if new_prompt: DEVICE_PROMPTS.append(new_prompt)
            else:
                print(bcolors.CYAN + "LOCAL_COMMAND: %s" % (cli_line) + bcolors.ENDC )
                ### LOCAL COMMAND - SUBPROCESS CALL
                last_output = subprocess.check_output(str(cli_line),shell=True)

            ### FILTER LAST_OUTPUT
            if isinstance(last_output, six.string_types):
                last_output = last_output.decode("utf-8").replace('\x07','').\
                    replace('\x08','').replace('\x0d','').replace('\x1b','').replace('\x1d','')

                ### NETMIKO-BUG (https://github.com/ktbyers/netmiko/issues/1200)
                if len(str(cli_line))>80 and run_remote:
                    first_bugged_line = last_output.splitlines()[0]
                    #print('NOISE:',first_bugged_line)
                    last_output = last_output.replace(first_bugged_line+'\n','')
                    if(last_output.strip() == first_bugged_line): last_output = str()

            if printall: print(bcolors.GREY + "%s" % (last_output) + bcolors.ENDC )
            if printcmdtologfile:
                if run_remote: fp.write('REMOTE_COMMAND: ' + cli_line + '\n'+last_output+'\n')
                else: fp.write('LOCAL_COMMAND: ' + cli_line + '\n'+last_output+'\n')
            else: fp.write(last_output)
            ### Result will be allways string, so rstrip() could be done
            dictionary_of_variables['last_output'] = last_output.rstrip()
            if name_of_output_variable:
                dictionary_of_variables[name_of_output_variable] = last_output.rstrip()
            for cli_item in cmd_line_items:
                if isinstance(cli_item, dict) \
                    and last_output.strip() == str() \
                    and cli_item.get('if_output_is_void','') in ['exit','quit','stop']:
                    if printall: print("%sSTOP [VOID OUTPUT].%s" % \
                        (bcolors.RED,bcolors.ENDC))
                    return True
        return None
    ### RUN_LOCAL_FUNCTION -----------------------------------------------------
    def run_local_function(cmd_line_items,loop_item = None,logfilename = logfilename,\
        printall = printall, printcmdtologfile = printcmdtologfile):
        global dictionary_of_variables
        local_function_name = cmd_line_items.get('local_function','')
        if cmd_line_items.get('input_parameters',''):
            local_input = []
            for input_list_item in cmd_line_items.get('input_parameters',''):
                if isinstance(input_list_item, dict):
                    if input_list_item.get('zipped_item',''):
                        try: local_input.append(loop_item[int(input_list_item.get('zipped_item',''))])
                        except: pass
                    elif input_list_item.get('input_variable',''):
                        name_of_local_variable = input_list_item.get('input_variable','')
                        local_input.append(dictionary_of_variables.get(name_of_local_variable,''))
                else: local_input.append(input_list_item)
        elif cmd_line_items.get('input_variable',''):
            name_of_local_variable = cmd_line_items.get('input_variable','')
            local_input = dictionary_of_variables.get(name_of_local_variable,'')
        name_of_output_variable = cmd_line_items.get('output_variable','')
        ### GLOBAL SYMBOLS
        if isinstance(local_input, (list,tuple)):
            local_output = globals()[local_function_name](*local_input)
        else: local_output = globals()[local_function_name](local_input)
        if isinstance(local_output, six.string_types):
            local_output = local_output.replace('\x0d','')
        if name_of_output_variable:
            dictionary_of_variables[name_of_output_variable] = local_output
        if printall: print("%sLOCAL_FUNCTION: %s(%s)\n%s%s\n%s" % \
            (bcolors.CYAN,local_function_name,\
            local_input if len(local_input)<100 else name_of_local_variable,\
            bcolors.GREY,local_output,bcolors.ENDC))
        fp.write("LOCAL_FUNCTION: %s(%s)\n%s\n" % (local_function_name,\
            local_input if len(local_input)<100 else name_of_local_variable,\
            local_output))
        dictionary_of_variables['last_output'] = local_output
        if (not local_output or str(local_output).strip() == str() )\
            and cmd_line_items.get('if_output_is_void') in ['exit','quit','stop']:
            if printall: print("%sSTOP [VOID OUTPUT].%s" % \
                (bcolors.RED,bcolors.ENDC))
            return True
        return None
    ### EXEC_COMMAND -----------------------------------------------------------
    def exec_command(ssh_connection,cmd_line_items,loop_item = None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global dictionary_of_variables
        cli_line, name_of_output_variable = str(), None
        ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE/LOCAL DEVICE COMMANDS
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if isinstance(cmd_line_items, six.string_types): cli_line = cmd_line_items
            elif isinstance(cmd_line_items, (list,tuple)):
                for cli_item in cmd_line_items:
                    if isinstance(cli_item, dict):
                        if cli_item.get('zipped_item',''):
                            try: cli_line += str(loop_item[int(cli_item.get('zipped_item',''))])
                            except: pass
                        elif cli_item.get('input_variable',''):
                            name_of_input_variable = cli_item.get('input_variable','')
                            cli_line += dictionary_of_variables.get(name_of_input_variable,'')
                        elif cli_item.get('output_variable',''):
                            name_of_output_variable = cli_item.get('output_variable','')
                    else: cli_line += str(cli_item)
            print(bcolors.CYAN + "EXEC_COMMAND: %s" % (cli_line) + bcolors.ENDC )
            ### EXEC COMMAND
            exec(cli_line, {'update_bgpdata_structure':update_bgpdata_structure,\
                'bgp_data':bgp_data,'void_neighbor_list_item':void_neighbor_list_item,\
                'void_vrf_list_item':void_vrf_list_item })
            if printcmdtologfile: fp.write('EXEC_COMMAND: ' + cli_line + '\n')
        return None
    ### RUN_REMOTE_AND_LOCAL_COMMANDS START ====================================
    ssh_connection, output= None, None
    try:
        ssh_connection = netmiko.ConnectHandler(device_type = router_type, \
            ip = DEVICE_HOST, port = int(DEVICE_PORT), \
            username = USERNAME, password = PASSWORD)

#           global DEVICE_PROMPTS
#           client = paramiko.SSHClient()
#           client.load_system_host_keys()
#           client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#           client.connect(DEVICE_HOST, port=int(DEVICE_PORT), \
#                          username=USERNAME, password=PASSWORD)
#           ssh_connection = client.invoke_shell()
#           ssh_connection.settimeout(TIMEOUT)
#           output, forget_it = ssh_send_command_and_read_output(ssh_connection,DEVICE_PROMPTS,TERM_LEN_0)
#           output2, forget_it = ssh_send_command_and_read_output(ssh_connection,DEVICE_PROMPTS,"")
#           output += output2

        if not logfilename:
            if 'WIN32' in sys.platform.upper(): logfilename = 'nul'
            else: logfilename = '/dev/null'
        with open(logfilename,"w") as fp:
            if output and not printcmdtologfile: fp.write(output)
            for cmd_line_items in CMD:
                cli_line = str()
                ### LIST,TUPPLE,STRINS ARE REMOTE REMOTE DEVICE COMMANDS
                if isinstance(cmd_line_items, (six.string_types,list,tuple)):
                    if run_command(ssh_connection,cmd_line_items,run_remote = True): return None
                ### HACK: USE DICT FOR RUN LOCAL PYTHON CODE FUNCTIONS OR LOCAL OS COMMANDS or LOOPS
                elif isinstance(cmd_line_items, dict):
                    if cmd_line_items.get('loop_zipped_list',''):
                        list_name = cmd_line_items.get('loop_zipped_list','')
                        for loop_item in dictionary_of_variables.get(list_name,''):
                            ### HACK lower functions expect list or tupple so convert it
                            if isinstance(loop_item, (int,float,six.string_types)):
                                loop_item = [loop_item]
                            if isinstance(loop_item, (list,tuple)):    #six.string_types
                                if cmd_line_items.get('remote_command',''):
                                    remote_cmd = cmd_line_items.get('remote_command','')
                                    if run_command(ssh_connection,remote_cmd,\
                                        loop_item,run_remote = True): return None
                                if cmd_line_items.get('local_function',''):
                                    if run_local_function(cmd_line_items,loop_item): return None
                                elif cmd_line_items.get('local_command',''):
                                    if run_command(ssh_connection,cmd_line_items.get('local_command',''),loop_item): return None
                                elif cmd_line_items.get('exec',''):
                                    if exec_command(ssh_connection,cmd_line_items.get('exec',''),loop_item): return None
                    elif cmd_line_items.get('local_function',''):
                        if run_local_function(cmd_line_items): return None
                    elif cmd_line_items.get('local_command',''):
                        if run_command(ssh_connection,cmd_line_items.get('local_command','')): return None
                    elif cmd_line_items.get('remote_command',''):
                        if run_command(ssh_connection,cmd_line_items.get('remote_command',''),run_remote = True): return None
                    elif cmd_line_items.get('exec',''):
                        if exec_command(ssh_connection,cmd_line_items.get('exec','')): return None
                elif printall: print('%sUNSUPPORTED_TYPE %s of %s!%s' % \
                            (bcolors.MAGENTA,type(item),str(cmd_line_items),bcolors.ENDC))
    except () as e:
        print(bcolors.FAIL + " ... EXCEPTION: (%s)" % (e) + bcolors.ENDC )
        sys.exit()
    finally:

        if ssh_connection: ssh_connection.disconnect()

#        client.close()

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

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

VERSION = get_version_from_file_last_modification_date()
dictionary_of_variables = {}

######## Parse program arguments #########
parser = argparse.ArgumentParser(
                description = "Script v.%s" % (VERSION),
                epilog = "e.g: \n" )

parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device',
                    default = str(),
                    help = "target router to check")
parser.add_argument("--os",
                    action = "store", dest="router_type",
                    choices = KNOWN_OS_TYPES,
                    help = "router operating system type")
parser.add_argument("--cmdfile", action = 'store', dest = "cmd_file", default = None,
                    help = "specify a file with a list of commands to execute")
parser.add_argument("--user",
                    action = "store", dest = 'username', default = str(),
                    help = "specify router user login")
parser.add_argument("--pass",
                    action = "store", dest = 'password', default = str(),
                    help = "specify router user password")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = None,
                    help = "print mode with no colors.")
parser.add_argument("--nolog",
                    action = 'store_true', dest = "nolog", default = None,
                    help = "no logging to file.")
parser.add_argument("--rcmd",
                    action = "store", dest = 'rcommand', default = str(),
                    help = "'command' or ['list of commands',...] to run on remote device")
# parser.add_argument("--alloti",
#                     action = 'store_true', dest = "alloti", default = None,
#                     help = "do action on all oti routers")
args = parser.parse_args()

if args.nocolors: bcolors = nocolors

# if args.alloti: device_list = parse_json_file_and_get_oti_routers_list()
# else: device_list = [args.device]

device_list = [args.device]

####### Set USERNAME if needed
if args.username: USERNAME = args.username
if not USERNAME:
    print(bcolors.MAGENTA + " ... Please insert your username by cmdline switch \
        --user username !" + bcolors.ENDC )
    sys.exit(0)

# SSH (default)
if not PASSWORD:
    if args.password: PASSWORD = args.password
    else:             PASSWORD = getpass.getpass("TACACS password: ")

for device in device_list:
    if device:
        router_prompt = None
        try: DEVICE_HOST = device.split(':')[0]
        except: DEVICE_HOST = str()
        try: DEVICE_PORT = device.split(':')[1]
        except: DEVICE_PORT = '22'
        print('DEVICE %s (host=%s, port=%s) START.........................'\
            %(device,DEVICE_HOST, DEVICE_PORT))

        ####### Figure out type of router OS
        if not args.router_type:
            #router_type = netmiko_autodetect(device)
            router_type = detect_router_by_ssh(device)
            if not router_type in KNOWN_OS_TYPES:
                print('%sUNSUPPORTED DEVICE TYPE: %s , BREAK!%s' % \
                    (bcolors. MAGENTA,router_type, bcolors.ENDC))
            else: print('DETECTED DEVICE_TYPE: %s' % (router_type))
        else:
            router_type = args.router_type
            print('FORCED DEVICE_TYPE: ' + router_type)

        ######## Create logs directory if not existing  #########
        if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
        filename_prefix = os.path.join(LOGDIR,device)
        filename_suffix = 'log'
        now = datetime.datetime.now()
        logfilename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,script_name.replace('.py','').replace('./',''),USERNAME,\
            filename_suffix)
        if args.nolog: logfilename = None

        ######## Find command list file (optional)
        list_cmd = []
        if args.cmd_file:
            if not os.path.isfile(args.cmd_file):
                print("%s ... Can't find command file: %s%s") % \
                    (bcolors.MAGENTA, args.cmd_file, bcolors.ENDC)
                sys.exit()
            else:
                with open(args.cmd_file) as cmdf:
                    list_cmd = cmdf.read().replace('\x0d','').splitlines()

        if args.rcommand: list_cmd = args.rcommand.replace('\'','').\
            replace('"','').replace('[','').replace(']','').split(',')

        if len(list_cmd)>0: CMD = list_cmd
        else:
            if router_type == 'cisco_ios':  CMD = CMD_IOS_XE
            elif router_type == 'cisco_xr': CMD = CMD_IOS_XR
            elif router_type == 'juniper':  CMD = CMD_JUNOS
            elif router_type == 'huawei' :  CMD = CMD_VRP
            elif router_type == 'linux':    CMD = CMD_LINUX
            else: CMD = list_cmd

        run_remote_and_local_commands(CMD, logfilename, printall = True , \
            printcmdtologfile = True)

        if logfilename and os.path.exists(logfilename):
            print('%s file created.' % (logfilename))
        print('\nDEVICE %s DONE.'%(device))
print('\nEND.')

print(json.dumps(bgp_data, indent=2))

