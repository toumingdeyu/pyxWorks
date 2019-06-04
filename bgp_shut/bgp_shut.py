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

print('LOGDIR: ' + LOGDIR)

###############################################################################
#
# Generic list of commands
#
###############################################################################


# IOS-XE is only for IPsec GW
CMD_IOS_XE = []

CMD_IOS_XR = [
    {'remote_command':['sh run | in "router bgp"',{'output_variable':'router_bgp_text'}]
    },
    {'eval':['True if "router bgp 5511" in glob_vars.get("router_bgp_text","") else None',{'output_variable':'OTI_5511'}]
    },
    {'eval':'glob_vars.get("OTI_5511","")',},
#     {'eval':['True if "router bgp 2300" in glob_vars.get("router_bgp_text","") else None',{'output_variable':'IMN_2300'}]
#     },
#     {'eval':'glob_vars.get("IMN_2300","")',},
#     {'if':'glob_vars.get("IMN_2300","")', 'remote_command':['show bgp vrf all summary | exclude 2300',{'output_variable':'IMN_EXT_IP_TEXT'}]},
#     {'if':'glob_vars.get("IMN_2300","")', 'remote_command':['show bgp vrf all summary | include 2300',{'output_variable':'IMN_INT_IP_TEXT'}]},
    {'if':'glob_vars.get("OTI_5511","")',
        'remote_command':['show bgp summary'],
        'exec':['try: \
            \n  temp_ipv4 = glob_vars.get("last_output","").split("St/PfxRcd")[1].strip().splitlines() \
            \n  previous_line, ext_list, int_list = None , [], [] \
            \n  for line in temp_ipv4: \
            \n    if len(line.split())==1: previous_line = line; continue \
            \n    if previous_line: line = previous_line + line; previous_line = None \
            \n    try: \
            \n      if "5511" in line.split()[2] and "." in line.split()[0]: int_list.append(line.split()[0]) \
            \n      elif "." in line.split()[0]: ext_list.append(line.split()[0]) \
            \n    except: pass \
            \n  glob_vars["OTI_INT_IPS_V4"] = int_list; glob_vars["OTI_EXT_IPS_V4"] = ext_list \
            \nexcept: pass' \
               ],
    },
    {'if':'glob_vars.get("OTI_5511","")',
        'remote_command':['show bgp ipv6 unicast summary'],
        'exec':['try: \
            \n  temp_ipv6 = glob_vars.get("last_output","").split("St/PfxRcd")[1].strip().splitlines() \
            \n  previous_line, ext_list, int_list = None , [], [] \
            \n  for line in temp_ipv6: \
            \n    if len(line.split())==1: previous_line = line; continue \
            \n    if previous_line: line = previous_line + line; previous_line = None \
            \n    try: \
            \n      if "5511" in line.split()[2] and ":" in line.split()[0]: int_list.append(line.split()[0]) \
            \n      elif ":" in line.split()[0]: ext_list.append(line.split()[0]) \
            \n    except: pass \
            \n  glob_vars["OTI_INT_IPS_V6"] = int_list; glob_vars["OTI_EXT_IPS_V6"] = ext_list \
            \nexcept: pass' \
               ],
    },
    {'eval':'glob_vars.get("OTI_EXT_IPS_V4","")'},
    {'eval':'glob_vars.get("OTI_INT_IPS_V4","")'},
    {'eval':'glob_vars.get("OTI_INT_IPS_V6","")'},
    {'eval':'glob_vars.get("OTI_EXT_IPS_V6","")'},
#     {'if':'glob_vars.get("OTI_5511","")',
#         'remote_command':['show bgp ipv6 unicast summary | include 5511',{'output_variable':'OTI_IPV6_TEXT'}],
#         'exec':['glob_vars["OTI_INT_IPS_V6"] = [ipline.split()[0] for ipline in glob_vars.get("last_output","").split("St/PfxRcd")[1].strip().splitlines()]'],
#     },
#     {'eval':'glob_vars.get("OTI_EXT_IPS_V6","")'},
#     {'eval':'glob_vars.get("OTI_INT_IPS_V6","")'},




#     'show bgp summary | include "local AS number"',
#     'show bgp vrf all summary | include "local AS number"',
#     {'local_function':'ciscoxr_get_bgp_vpn_peer_data_to_json', \
#        'input_variable':'last_output', 'output_variable':'bgp_vpn_peers'},
#     {'loop_zipped_list':'bgp_vpn_peers',\
#        'remote_command':('show bgp vrf ',{'zipped_item':'1'},' neighbors ',\
#            {'zipped_item':'3'}),
#        'local_function':'ciscoxr_parse_bgp_neighbors', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     'sh ipv4 vrf all int brief | exclude "unassigned|Protocol|default"',
#     {'local_function':"ciscoxr_get_vpnv4_all_interfaces",'input_variable':\
#        'last_output','output_variable':'bgp_vpn_peers_with_interfaces'},
#     {'loop_zipped_list':'bgp_vpn_peers_with_interfaces',
#        'remote_command':('show interface ',{'zipped_item':'1'}),
#        'local_function':'ciscoxr_parse_interface', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'}]
#     },
#     {'loop_zipped_list':'bgp_vpn_peers',
#         'remote_command':('show bgp vrf ',{'zipped_item':'1'},' neighbors ',\
#             {'zipped_item':'3'},' routes'),
#         'local_function':'ciscoxr_parse_bgp_neighbor_routes', "input_parameters":\
#             [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     {'loop_zipped_list':'bgp_vpn_peers','remote_command':('ping vrf ',\
#        {'zipped_item':'1'},' ',{'zipped_item':'3'},' size 1470 count 2'),
#        'local_function':'ciscoxr_parse_ping', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     {"eval":"return_bgp_data_json()"},
]

CMD_JUNOS = []

CMD_VRP = [
    'display bgp vpnv4 all peer | in \'Local AS number\'',
#     {'local_function':'huawei_get_bgp_vpn_peer_data_to_json', 'input_variable':'last_output',\
#       'output_variable':'bgp_vpn_peers', 'if_output_is_void':'exit'
#     },
#     {'loop_zipped_list':'bgp_vpn_peers',
#      'remote_command':('dis bgp vpnv4 vpn-instance ',{'zipped_item':'1'},\
#          ' peer ',{'zipped_item':'3'},' verbose'),
#      'local_function':'huawei_parse_bgp_neighbors', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     {'loop_zipped_list':'bgp_vpn_peers',
#      'remote_command':('dis bgp vpnv4 vpn-instance ',{'zipped_item':'1'},\
#          ' routing-table peer ',{'zipped_item':'3'},' accepted-routes'),
#      'local_function':'huawei_parse_bgp_neighbor_routes', "input_parameters":\
#           [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     'dis curr int | in (interface|ip binding vpn-instance)',
#     {'local_function':'huawei_parse_vpn_interfaces', 'input_variable':'last_output',\
#       'output_variable':'interface_list', 'if_output_is_void':'exit'
#     },
#     {'loop_zipped_list':'interface_list',
#       'remote_command':('dis interface ',{'zipped_item':'1'}),
#       'local_function':'huawei_parse_interface', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'}]
#     },
#     {'loop_zipped_list':'bgp_vpn_peers',
#         'remote_command':('ping -s 1470 -c 2 -t 2000 -vpn-instance ',\
#             {'zipped_item':'1'},' ',{'zipped_item':'3'}),
#         'local_function':'huawei_parse_bgp_neighbor_routes', "input_parameters":\
#            [{"input_variable":"last_output"},{'zipped_item':'0'},{'zipped_item':'2'}]
#     },
#     {"eval":"return_bgp_data_json()"},
]

CMD_LINUX = [
             {"local_command":("echo ", {"input_variable":"linux_users"} , {"output_variable":"linux_users_2"})},


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
            {"eval":['update_bgpdata_structure(bgp_data["vrf_list"][',0,'],"vrf_name","','aaaaaa','", ',0,',void_neighbor_list_item)']},
            {"eval":"return_bgp_data_json()"}
]

CMD_LOCAL = [
    {"local_command":['hostname', {"output_variable":"hostname"}]
    },
    #{'eval': 'sys.exit(0)'},
    {"local_command":'hostname'},
    {"loop":"[0,1,2,3]","local_command":['whoami ',{'eval':'loop_item'}]
    },
    {'eval':'glob_vars.get("last_output","")'
    },
    {'if':'glob_vars.get("last_output","")==""','eval':'glob_vars.get("last_output","")'
    },
    {'if':'glob_vars.get("last_output","")', "local_command":'whoami'
    },
    {'exec':'glob_vars["aaa"] = [ ipline for ipline in [0,1,2,3,4,5] ]'
    },
    {'eval':'glob_vars.get("aaa","")'
    },
    {'eval':['[ ipline[0] for ipline in [[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[6,6],[7,7]] ]' ,{'output_variable':'bbb'} ]
    },
    {'eval':'glob_vars.get("bbb","")'
    },
]

#
# ################################################################################
# bgp_data = collections.OrderedDict()
#
# ### Start of BASIC STRUCTURES OF JSON
# neighbor_list_item_txt_template = '''
# {
#     "ip_address": null,
#     "bgp_current_state": null,
#     "received_total_routes": null,
#     "advertised_total_routes": null,
#     "maximum_allowed_route_limit": null,
#     "import_route_policy_is": null,
#     "ping_response_success": null,
#     "accepted_routes_list": []
# }
# '''
#
# vrf_list_item_txt_template = '''
# {
#     "vrf_name": null,
#     "neighbor_list": [%s],
#     "interface_name": null,
#     "interface_ip" : null,
#     "interface_mtu" : null,
#     "interface_input_packets_per_seconds": null,
#     "interface_output_packets_per_seconds": null
# }
# ''' % (neighbor_list_item_txt_template)
#
# bgp_json_txt_template='''
# {
#     "vrf_list": [%s]
# }
# ''' % (vrf_list_item_txt_template)
# ### End of BASIC STRUCTURES OF JSON
#
# ### BASIC BGP_DATA OBJECT with 1 neihbor and 1 vfr
# bgp_data = json.loads(bgp_json_txt_template, \
#     object_pairs_hook = collections.OrderedDict)
#
# ### OBJECTS FOR APPENDING LISTS, DO COPY.DEEPCOPY of them by APPENDING STRUCTURE
# void_vrf_list_item = json.loads(vrf_list_item_txt_template, \
#     object_pairs_hook = collections.OrderedDict)
#
# void_neighbor_list_item = json.loads(neighbor_list_item_txt_template, \
#     object_pairs_hook = collections.OrderedDict)

###############################################################################
#
# Function and Class
#
###############################################################################

# def return_parameters(text):
#     return text
#
# def return_splitlines_parameters(text):
#     return text.splitlines()


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

# def return_bgp_data_json():
#     return json.dumps(bgp_data, indent=2)
#
#
# def read_bgp_data_json_from_logfile(filename = None, printall = None):
#     bgp_data_loaded, text = None, None
#     with open(filename,"r") as fp:
#         text = fp.read()
#     if text:
#         try: bgp_data_json_text = text.split('EVAL_COMMAND: return_bgp_data_json()')[1]
#         except: bgp_data_json_text = str()
#         if bgp_data_json_text:
#             bgp_data_loaded = json.loads(bgp_data_json_text, object_pairs_hook = collections.OrderedDict)
#             #print("LOADED_BGP_DATA: ",bgp_data_loaded)
#             if printall: print("\nLOADED JSON BGP_DATA: ")
#             if printall: print(json.dumps(bgp_data_loaded, indent=2))
#     return bgp_data_loaded
#
# def return_string_from_bgp_vpn_section(vrf_data = None, vrf_name = None):
#     result = None
#     if vrf_data and vrf_name:
#         for vrf_index, vrf_item in return_indexed_list(vrf_data["vrf_list"]):
#             if vrf_item.get("vrf_name").replace('.','').replace('@','') == \
#                 vrf_name.replace('.','').replace('@',''):
#                 result = json.dumps(vrf_item, indent=2)
#                 break
#     return result

#
# ### CISCO-XR FUNCTIONS ###
# def ciscoxr_get_bgp_vpn_peer_data_to_json(text = None):
#     output = []
#     if text:
#         try:    vrf_sections = text.split('VRF: ')[1:]
#         except: vrf_sections = []
#         vrf_index = 0
#         for vrf_section in vrf_sections:
#            vrf_instance = vrf_section.splitlines()[0].strip()
#            try: vrf_peer_lines = vrf_section.strip().split('Neighbor')[1].splitlines()[1:]
#            except: vrf_peer_lines = []
#            if len(vrf_peer_lines)>0:
#                update_bgpdata_structure(bgp_data["vrf_list"],"vrf_name",str(vrf_instance),vrf_index, void_vrf_list_item)
#                neighbor_index = 0
#                for vrf_peer_line in vrf_peer_lines:
#                    output.append((vrf_index,vrf_instance,neighbor_index,vrf_peer_line.split()[0]))
#                    update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"],"ip_address",vrf_peer_line.split()[0],neighbor_index,void_neighbor_list_item)
#                    neighbor_index += 1
#                vrf_index += 1
#     return output
#
#
# def ciscoxr_parse_bgp_neighbors(text = None,vrf_index = None,neighbor_index = None):
#     output = []
#     if text:
#         bgp_current_state = get_first_row_after(text,'BGP state = ',',')
#         import_route_policy_is = get_first_row_after(text,'Policy for incoming advertisements is ')
#         received_total_routes = get_first_row_before(text,'accepted prefixes, ')
#         advertised_total_routes = get_first_row_after(text,'Prefix advertised ',',')
#         maximum_allowed_route_limit = get_first_row_after(text,'Maximum prefixes allowed ')
#         if vrf_index != None and neighbor_index != None:
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"bgp_current_state",bgp_current_state)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"import_route_policy_is",import_route_policy_is)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"received_total_routes",received_total_routes)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"advertised_total_routes",advertised_total_routes)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"maximum_allowed_route_limit",maximum_allowed_route_limit)
#     return output
#
#
# def ciscoxr_get_vpnv4_all_interfaces(text = None):
#     output, vpn_list = [], []
#     if text:
#         try: text = text.strip().split('MET')[1]
#         except: text = text.strip()
#         for row in text.splitlines():
#            ### LIST=VPN,INTERFACE_NAME,INTERFACE_IP
#            columns = row.strip().split()
#            try: vpn_list.append((columns[4],columns[0],columns[1]))
#            except: pass
#         for vpn_to_if in vpn_list:
#             for vrf_index, vrf_item in return_indexed_list(bgp_data["vrf_list"]):
#                 if vrf_item.get("vrf_name") == vpn_to_if[0]:
#                     update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_name",vpn_to_if[1])
#                     update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_ip",vpn_to_if[2])
#                     output.append(vpn_to_if)
#     return output
#
#
# def ciscoxr_parse_interface(text = None,vrf_name = None):
#     output = []
#     if text:
#         interface_mtu = get_first_row_after(text,'MTU ')
#         interface_input_packets_per_seconds = get_first_row_before(text,'packets/sec')
#         interface_output_packets_per_seconds = get_first_row_before(text,'packets/sec',split_text_index=1)
#         output = [interface_mtu, interface_input_packets_per_seconds,interface_output_packets_per_seconds]
#         for vrf_index, vrf_item in return_indexed_list(bgp_data["vrf_list"]):
#             if vrf_item.get("vrf_name") == vrf_name: break
#         else:
#             return []
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_mtu",interface_mtu)
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_input_packets_per_seconds",interface_input_packets_per_seconds)
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_output_packets_per_seconds",interface_output_packets_per_seconds)
#     return output
#
#
# def ciscoxr_parse_ping(text = None,vrf_index = None,neighbor_index = None):
#     ping_response_success = get_first_row_after(text,'Success rate is ')
#     if ping_response_success == str(): ping_response_success = '0'
#     if vrf_index != None and neighbor_index != None:
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#             [neighbor_index],"ping_response_success",ping_response_success)
#     return [ping_response_success]
#
#
# def ciscoxr_parse_bgp_neighbor_routes(text = None,vrf_index = None,neighbor_index = None):
#     output = []
#     try:
#         accepted_routes_text = text.split('Route Distinguisher: ')[2].splitlines()[1:]
#         for line in accepted_routes_text:
#             if line.strip() == str(): break
#             try: output.append(line.split()[1])
#             except: pass
#     except: pass
#     if vrf_index != None and neighbor_index != None:
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#             [neighbor_index],"accepted_routes_list",output)
#     return output

#
# ### HUAWEI FUNCTIONS ###
# def huawei_get_bgp_vpn_peer_data_to_json(text = None):
#     output = []
#     if text:
#         try: vrf_sections = text.split('VPN-Instance')[1:]
#         except: vrf_sections = []
#         vrf_index = 0
#         for vrf_section in vrf_sections:
#             vrf_instance = vrf_section.split(',')[0].strip()
#             try: vrf_peer_lines = vrf_section.strip().splitlines()[1:]
#             except: vrf_peer_lines = []
#             if len(vrf_peer_lines)>0:
#                 update_bgpdata_structure(bgp_data["vrf_list"],key_name="vrf_name",\
#                     value=str(vrf_instance),order_in_list=vrf_index, \
#                     list_append_value=void_vrf_list_item,debug=True)
#                 neighbor_index = 0
#                 for vrf_peer_line in vrf_peer_lines:
#                    output.append((vrf_index,vrf_instance,neighbor_index,vrf_peer_line.split()[0]))
#                    update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"],\
#                        key_name="ip_address",value=str(vrf_peer_line.split()[0]),\
#                        order_in_list=neighbor_index,list_append_value=\
#                        void_neighbor_list_item,debug=True)
#                    neighbor_index += 1
#                 vrf_index += 1
#     return output
#
#
# def huawei_parse_bgp_neighbors(text = None,vrf_index = None,neighbor_index = None):
#     output = []
#     if text:
#         bgp_current_state = get_first_row_after(text,'BGP current state: ',',')
#         import_route_policy_is = get_first_row_after(text,'Import route policy is: ')
#         received_total_routes = get_first_row_after(text,'Received total routes: ')
#         advertised_total_routes = get_first_row_after(text,'Advertised total routes: ')
#         maximum_allowed_route_limit = get_first_row_after(text,'Maximum allowed route limit: ')
#         if vrf_index != None and neighbor_index != None:
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"bgp_current_state",bgp_current_state)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"import_route_policy_is",import_route_policy_is)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"received_total_routes",received_total_routes)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"advertised_total_routes",advertised_total_routes)
#             update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#                 [neighbor_index],"maximum_allowed_route_limit",maximum_allowed_route_limit)
#     return output
#
#
# def huawei_parse_bgp_neighbor_routes(text = None,vrf_index = None,neighbor_index = None):
#     output = []
#     try:
#         accepted_routes_text = text.split('PrefVal Path/Ogn')[1].splitlines()[1:]
#         for line in accepted_routes_text:
#             if line.strip() == str(): continue
#             try: output.append(line.split()[1])
#             except: pass
#     except: pass
#     if vrf_index != None and neighbor_index != None:
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#             [neighbor_index],"accepted_routes_list",output)
#     return output
#
#
# def huawei_parse_vpn_interfaces(text = None):
#     output, vpn_list = [], []
#     if text:
#         try: text = text.strip().split('MET')[1]
#         except: text = text.strip()
#         for interface in text.split('interface'):
#             ### LIST=VPN,INTERFACE_NAME
#             interface_name = interface.split()[0].strip()
#             try:
#                 vpn_name = interface.split('ip binding vpn-instance')[1].strip()
#                 vpn_list.append((vpn_name,interface_name))
#             except: pass
#         for vpn_to_if in vpn_list:
#             for vrf_index, vrf_item in return_indexed_list(bgp_data["vrf_list"]):
#                 if vrf_item.get("vrf_name") == vpn_to_if[0]:
#                     update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_name",vpn_to_if[1])
#                     output.append(vpn_to_if)
#     return output
#
#
# def huawei_parse_interface(text = None,vrf_name = None):
#     output = []
#     if text:
#         interface_mtu = get_first_row_after(text,'The Maximum Transmit Unit is ')
#         interface_input_packets_per_seconds = get_first_row_before(text,'packets/sec')
#         interface_output_packets_per_seconds = get_first_row_before(text,'packets/sec',split_text_index=1)
#         output = [interface_mtu, interface_input_packets_per_seconds,interface_output_packets_per_seconds]
#         for vrf_index, vrf_item in return_indexed_list(bgp_data["vrf_list"]):
#             if vrf_item.get("vrf_name") == vrf_name: break
#         else:
#             return []
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_mtu",interface_mtu)
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_input_packets_per_seconds",interface_input_packets_per_seconds)
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index],"interface_output_packets_per_seconds",interface_output_packets_per_seconds)
#     return output
#
#
# def huawei_parse_bgp_neighbor_routes(text = None,vrf_index = None,neighbor_index = None):
#     ping_response = get_first_row_before(text,' packet loss',delete_text = '%')
#     try: ping_response_success = str(100 - int(round(float(ping_response))))
#     except: ping_response_success = '0'
#     if ping_response_success == str(): ping_response_success = '0'
#     if vrf_index != None and neighbor_index != None:
#         update_bgpdata_structure(bgp_data["vrf_list"][vrf_index]["neighbor_list"]\
#             [neighbor_index],"ping_response_success",ping_response_success)
#     return [ping_response_success]

#
# ### SSH FUNCTIONS ###
# def netmiko_autodetect(device, debug = None):
#     router_os = str()
#     try: DEVICE_HOST = device.split(':')[0]
#     except: DEVICE_HOST = str()
#     try: DEVICE_PORT = device.split(':')[1]
#     except: DEVICE_PORT = '22'
#     guesser = netmiko.ssh_autodetect.SSHDetect(device_type='autodetect', \
#         ip=DEVICE_HOST, port=int(DEVICE_PORT), username=USERNAME, password=PASSWORD)
#     best_match = guesser.autodetect()
#     if debug:
#         print('BEST_MATCH: %s\nPOTENTIAL_MATCHES:' %(best_match))
#         print(guesser.potential_matches)
#     router_os = best_match
#     return router_os


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


# def ipv4_to_ipv6_obs(ipv4address):
#     ip4to6, ip6to4 = str(), str()
#     try: v4list = ipv4address.split('/')[0].split('.')
#     except: v4list = []
#     if len(v4list) == 4:
#         try:
#             if int(v4list[0])<256 and int(v4list[1])<256 and int(v4list[2])<256 \
#                 and int(v4list[3])<256 and int(v4list[0])>=0 and \
#                 int(v4list[1])>=0 and int(v4list[2])>=0 and int(v4list[3])>=0:
#                 ip4to6 = 'fd00:0:0:5511::%02x%02x:%02x%02x' % \
#                     (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
#                 ip6to4 = '2002:%02x%02x:%02x%02x:0:0:0:0:0' % \
#                     (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
#         except: pass
#     return ip4to6, ip6to4
#
# def parse_ipv4_from_text(text):
#     try: ipv4 = text.split('address')[1].split()[0].replace(';','')
#     except: ipv4 = str()
#     converted_ipv4 = ipv4_to_ipv6_obs(ipv4)[0]
#     return converted_ipv4
#
# def stop_if_ipv6_found(text):
#     try: ipv6 = text.split('address')[1].split()[0].replace(';','')
#     except: ipv6 = str()
#     if ipv6: return str()
#     else: return "NOT_FOUND"
#
# def stop_if_two_ipv6_found(text):
#     try: ipv6 = text.split('address')[1].split()[0].replace(';','')
#     except: ipv6 = str()
#     try: ipv6two = text.split('address')[2].split()[0].replace(';','')
#     except: ipv6two = str()
#     if ipv6 and ipv6two: return str()
#     else: return "NOT_FOUND"
#
# def parse_whole_set_line_from_text(text):
#     try: set_text = text.split('set')[1].split('\n')[0]
#     except: set_text = str()
#     if set_text: set_ipv6line = 'set' + set_text + ' primary\n'
#     else: set_ipv6line = str()
#     return set_ipv6line

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


def run_remote_and_local_commands(CMD, logfilename = None, printall = None, printcmdtologfile = None):
    ### RUN_COMMAND - REMOTE or LOCAL ------------------------------------------
    def run_command(ssh_connection,cmd_line_items,loop_item=None,run_remote = None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars
        cli_line, name_of_output_variable = str(), None
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
                try:
                    last_output = subprocess.check_output(str(cli_line),shell=True)
                except: last_output = str()

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
            glob_vars['last_output'] = last_output.rstrip()
            if name_of_output_variable:
                glob_vars[name_of_output_variable] = last_output.rstrip()
        return None
    ### EVAL_COMMAND -----------------------------------------------------------
    def eval_command(ssh_connection,cmd_line_items,loop_item=None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars
        cli_line, name_of_output_variable = str(), None
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
                    else: cli_line += str(cli_item)
            print(bcolors.CYAN + "EVAL_COMMAND: %s" % (cli_line) + bcolors.ENDC )
            try: local_output = eval(cli_line)
            except: local_output = str()
            print(bcolors.GREY + str(local_output) + bcolors.ENDC )
            if printcmdtologfile: fp.write('EVAL_COMMAND: ' + cli_line + '\n' + str(local_output) + '\n')
            if name_of_output_variable:
                glob_vars[name_of_output_variable] = local_output
            glob_vars['last_output'] = local_output
        return None
    ### EXEC_COMMAND -----------------------------------------------------------
    def exec_command(ssh_connection,cmd_line_items,loop_item=None,\
        logfilename = logfilename,printall = printall, printcmdtologfile = printcmdtologfile):
        global glob_vars, global_env
        cli_line, name_of_output_variable = str(), None
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
                    else: cli_line += str(cli_item)
            print(bcolors.CYAN + "EXEC_COMMAND: %s" % (cli_line) + bcolors.ENDC )
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
            print(bcolors.CYAN + "IF_CONDITION(%s)" % (condition_eval_text) + " --> " +\
                str(success).upper() + bcolors.ENDC )
            if printcmdtologfile: fp.write('IF_CONDITION(%s): ' % (condition_eval_text) +\
                 " --> "+ str(success).upper() + '\n')
        return success
    ### MAIN_DO_STEP -----------------------------------------------------------
    def main_do_step(cmd_line_items,loop_item=None):
        global glob_vars
        condition_result = True
        if isinstance(cmd_line_items, (six.string_types,list,tuple)):
            if run_command(ssh_connection,cmd_line_items,loop_item,run_remote = True): return None
        if isinstance(cmd_line_items, (dict)):
            if cmd_line_items.get('pre_remote_command','') and remote_connect:
                if run_command(ssh_connection,cmd_line_items.get('pre_remote_command',''),loop_item,run_remote = True): return None
            if cmd_line_items.get('pre_local_command',''):
                if run_command(ssh_connection,cmd_line_items.get('pre_local_command',''),loop_item): return None
            if cmd_line_items.get('pre_exec',''):
                if exec_command(ssh_connection,cmd_line_items.get('pre_exec',''),loop_item): return None
            if cmd_line_items.get('pre_eval',''):
                if eval_command(ssh_connection,cmd_line_items.get('pre_eval',''),loop_item): return None
            if cmd_line_items.get('if',''):
                condition_result = if_function(ssh_connection,cmd_line_items.get('if',''),loop_item)
            if condition_result:
                if cmd_line_items.get('remote_command','') and remote_connect:
                    if run_command(ssh_connection,cmd_line_items.get('remote_command',''),loop_item,run_remote = True): return None
                if cmd_line_items.get('local_command',''):
                    if run_command(ssh_connection,cmd_line_items.get('local_command',''),loop_item): return None
                if cmd_line_items.get('exec',''):
                    if exec_command(ssh_connection,cmd_line_items.get('exec',''),loop_item): return None
                if cmd_line_items.get('eval',''):
                    if eval_command(ssh_connection,cmd_line_items.get('eval',''),loop_item): return None
        return True

    ### RUN_REMOTE_AND_LOCAL_COMMANDS START ====================================
    global remote_connect, glob_vars
    ssh_connection, output= None, None

    try:
        if remote_connect:
            ssh_connection = netmiko.ConnectHandler(device_type = router_type, \
                ip = DEVICE_HOST, port = int(DEVICE_PORT), \
                username = USERNAME, password = PASSWORD)
        # ### paramiko
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

        ### WORK REMOTE or LOCAL ===================================================
        if not logfilename:
            if 'WIN32' in sys.platform.upper(): logfilename = 'nul'
            else: logfilename = '/dev/null'
        with open(logfilename,"w") as fp:
            if output and not printcmdtologfile: fp.write(output)
            for cmd_line_items in CMD:
                #print('----> ',cmd_line_items)
                if isinstance(cmd_line_items, dict) and cmd_line_items.get('loop_zipped_list',''):
                    for loop_item in glob_vars.get(cmd_line_items.get('loop_zipped_list',''),''):
                        main_do_step(cmd_line_items,loop_item)
                elif isinstance(cmd_line_items, dict) and cmd_line_items.get('loop',''):
                    for loop_item in eval(cmd_line_items.get('loop','')):
                        main_do_step(cmd_line_items,loop_item)
                else: main_do_step(cmd_line_items)
    except () as e:
        print(bcolors.FAIL + " ... EXCEPTION: (%s)" % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        if remote_connect and ssh_connection: ssh_connection.disconnect()
    # ### paramiko
    #        client.close()

    return None


# def update_bgpdata_structure(data_address, key_name = None, value = None, \
#     order_in_list = None, list_append_value = None, add_new_key = None, \
#     debug = None):
#     """
#     FUNCTION: update_bgpdata_structure
#     PARAMETERS:
#        data_address - address of json ending on parrent (key_name or list_number if exists)
#        key_name - name of key in dict
#        value - value of key in dict
#        order_in_list - if actuaal list is shorter than needed, append new template section
#        list_append_value - add new template section to list
#        add_new_key = True - add new keys/values to dictionary not existent in templates
#        debug - True/None
#     RETURNS:
#        change_applied - True = change applied , None - no change
#     """
#     global bgp_data
#     change_applied = None
#     if debug:
#         print(bcolors.MAGENTA+"KEY="+str(key_name)+" VALUE="+str(value)+" ORDER_IN_LIST="+\
#             str(order_in_list)+" DATA_TYPE="+str(type(data_address))+' ID='+\
#             str(id(data_address))+bcolors.ENDC)
#
#     ### REWRITE VALUE IN DICT ON KEY_NAME POSITION
#     if isinstance(data_address, (dict,collections.OrderedDict)) \
#         and isinstance(key_name, (six.string_types)):
#         data_address_values = data_address.keys()
#         for address_key_value in data_address_values:
#             if key_name and key_name == address_key_value:
#                 data_address[key_name] = value
#                 if debug: print('DICT[%s]=%s'%(key_name,value))
#                 change_applied = True
#         else:
#             if add_new_key:
#                 data_address[key_name] = value
#                 if debug: print('ADDED_TO_DICT[%s]=%s'%(key_name,value))
#                 change_applied = True
#     ### ADD LIST POSITION if NEEDED, REWRITE VALUE IN DICT ON KEY_NAME POSITION
#     elif isinstance(data_address, (list)):
#         ### SIMPLY ADD VALUE TO LIST WHEN ORDER NOT INSERTED ###
#         if not order_in_list and not key_name:
#             if debug: print('LIST_APPENDED.')
#             data_address.append(value)
#             change_applied = True
#         else:
#             ### INCREASE LIST LENGHT if NEEDED ###
#             if int(order_in_list) >= len(data_address):
#                 how_much_to_add = 1 + int(order_in_list) - len(data_address)
#                 for i in range(how_much_to_add):
#                     data_address.append(copy.deepcopy(list_append_value))
#                 if debug: print(bcolors.GREEN+'LIST_APPENDED_BY_SECTIONs +(%s).'\
#                     %(how_much_to_add)+bcolors.ENDC)
#             ### AFTER OPTIONAL ADDITION OF END OF LIST (AT LEAST) BY ONE ###
#             if int(order_in_list) < len(data_address) \
#                 and isinstance(data_address[int(order_in_list)], \
#                 (dict,collections.OrderedDict)) and value != None:
#                 data_address_values = data_address[int(order_in_list)].keys()
#                 for key_list_item in data_address_values:
#                    if key_name and str(key_name) == str(key_list_item):
#                        data_address[int(order_in_list)][str(key_name)] = value
#                        if debug: print('DICT_LIST[%s][%s]=%s'% \
#                            (order_in_list,key_name,value))
#                        change_applied = True
#                 else:
#                     if add_new_key:
#                         data_address[int(order_in_list)][key_name] = value
#                         if debug: print('ADDED_TO_DICT_LIST[%s][%s]=%s'% \
#                             (order_in_list,key_name,value))
#                         change_applied = True
#     if debug: print("CHANGE_APPLIED: ",change_applied)
#     return change_applied


def get_difference_string_from_string_or_list(
    old_string_or_list, \
    new_string_or_list, \
    diff_method = 'ndiff0', \
    ignore_list = default_ignoreline_list, \
    problem_list = default_problemline_list, \
    printalllines_list = default_printalllines_list, \
    linefilter_list = default_linefilter_list, \
    compare_columns = [], \
    print_equallines = None, \
    debug = None, \
    note = True ):
    '''
    FUNCTION get_difference_string_from_string_or_list:
    INPUT PARAMETERS:
      - old_string_or_list - content of old file in string or list type
      - new_string_or_list - content of new file in string or list type
      - diff_method - ndiff, ndiff0, pdiff0
      - ignore_list - list of regular expressions or strings when line is ignored for file (string) comparison
      - problem_list - list of regular expressions or strings which detects problems, even if files are equal
      - printalllines_list - list of regular expressions or strings which will be printed grey, even if files are equal
      - linefilter_list - list of regular expressions which filters each line (regexp results per line comparison)
      - compare_columns - list of columns which are intended to be different , other columns in line are ignored
      - print_equallines - True/False prints all equal new file lines with '=' prefix , by default is False
      - debug - True/False, prints debug info to stdout, by default is False
      - note - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies

    PDIFF0 FORMAT: The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    ' ' for the same line, but with problem.
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''
    print_string = str()
    if note:
       print_string = "DIFF_METHOD: "
       if diff_method   == 'ndiff0': print_string += note_ndiff0_string
       elif diff_method == 'pdiff0': print_string += note_pdiff0_string
       elif diff_method == 'ndiff' : print_string += note_ndiff_string

    # make list from string if is not list already
    old_lines_unfiltered = old_string_or_list if type(old_string_or_list) == list else old_string_or_list.splitlines()
    new_lines_unfiltered = new_string_or_list if type(new_string_or_list) == list else new_string_or_list.splitlines()

    # NDIFF COMPARISON METHOD---------------------------------------------------
    if diff_method == 'ndiff':
        diff = difflib.ndiff(old_lines_unfiltered, new_lines_unfiltered)
        for line in list(diff):
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            ignore = False
            for ignore_item in ignore_list:
                if (re.search(ignore_item,line)) != None: ignore = True
            if ignore: continue
            if len(line.strip())==0: pass
            elif '+ ' == first_chars: print_string += COL_ADDED + line + bcolors.ENDC + '\n'
            elif '- ' == first_chars: print_string += COL_DELETED + line + bcolors.ENDC + '\n'
            elif '? ' == first_chars or first_chars == str(): pass
            elif print_equallines: print_string += COL_EQUAL + line + bcolors.ENDC + '\n'
            else:
                print_line, ignore = False, False
                for item in printalllines_list:
                    if (re.search(item,line)) != None: print_line = True
                if print_line:
                    print_string += COL_EQUAL + line + bcolors.ENDC + '\n'
        return print_string

    # NDIFF0 COMPARISON METHOD--------------------------------------------------
    if diff_method == 'ndiff0' or diff_method == 'pdiff0':
        ignore_previous_line = False
        diff = difflib.ndiff(old_lines_unfiltered, new_lines_unfiltered)
        listdiff_nonfiltered = list(diff)
        listdiff = []
        # filter diff lines out of '? ' and void lines
        for line in listdiff_nonfiltered:
            # This ignore filter is much faster
            ignore = False
            for ignore_item in ignore_list:
                if (re.search(ignore_item,line)) != None: ignore = True
            if ignore: continue
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            if '+ ' in first_chars or '- ' in first_chars or '  ' in first_chars:
                listdiff.append(line)
        del diff, listdiff_nonfiltered
        # main ndiff0/pdiff0 loop
        previous_minus_line_is_change = False
        for line_number,line in enumerate(listdiff):
            print_color, print_line = COL_EQUAL, str()
            try:    first_chars_previousline = listdiff[line_number-1][0]+listdiff[line_number-1][1]
            except: first_chars_previousline = str()
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            try:    first_chars_nextline = listdiff[line_number+1][0]+listdiff[line_number+1][1]
            except: first_chars_nextline = str()
            # CHECK IF ARE LINES EQUAL AFTER FILTERING (compare_columns + linefilter_list)
            split_line,split_next_line,linefiltered_line,linefiltered_next_line = str(),str(),str(),str()
            if '- ' == first_chars and '+ ' == first_chars_nextline:
                for split_column in compare_columns:
                    # +1 means equal of deletion of first column -
                    try: temp_column = line.split()[split_column+1]
                    except: temp_column = str()
                    split_line += ' ' + temp_column
                for split_column in compare_columns:
                    # +1 means equal of deletion of first column +
                    try: temp_column = listdiff[line_number+1].split()[split_column+1]
                    except: temp_column = str()
                    split_next_line += ' ' + temp_column
                for linefilter_item in linefilter_list:
                    try: next_line = listdiff[line_number+1]
                    except: next_line = str()
                    if line and (re.search(linefilter_item,line)) != None:
                        linefiltered_line = re.findall(linefilter_item,line)[0]
                    if next_line and (re.search(linefilter_item,next_line)) != None:
                        linefiltered_next_line = re.findall(linefilter_item,line)[0]
                # LINES ARE EQUAL AFTER FILTERING - filtered linefilter and columns commands
                if (split_line and split_next_line and split_line == split_next_line) or \
                   (linefiltered_line and linefiltered_next_line and linefiltered_line == linefiltered_next_line):
                    ignore_previous_line = True
                    continue
            # CONTINUE CHECK DELETED/ADDED LINES--------------------------------
            if '- ' == first_chars:
                # FIND IF IT IS CHANGEDLINE OR DELETED LINE
                line_list_lenght, the_same_columns = len(line.split()), 0
                percentage_of_equality = 0
                try: nextline_sign_column = listdiff[line_number+1].split()[0]
                except: nextline_sign_column = str()
                if nextline_sign_column == '+':
                    for column_number,column in enumerate(line.split()):
                        try: next_column = listdiff[line_number+1].split()[column_number]
                        except: next_column = str()
                        if column == next_column: the_same_columns += 1
                    if line_list_lenght>0:
                        percentage_of_equality = (100*the_same_columns)/line_list_lenght
                # CHANGED LINE -------------------------------------------------
                if percentage_of_equality > 54:
                    previous_minus_line_is_change = True
                    if diff_method == 'ndiff0':
                        print_color, print_line = COL_DIFFDEL, line
                # LOST/DELETED LINES -------------------------------------------
                else: print_color, print_line = COL_DELETED, line
            # IGNORE EQUAL -/= LINES or PRINT printall and problem lines -------
            elif '+ ' == first_chars and ignore_previous_line:
                line = ' ' + line[1:]
                ignore_previous_line = False
            # ADDED NEW LINE ---------------------------------------------------
            elif '+ ' == first_chars and not ignore_previous_line:
                if previous_minus_line_is_change:
                    previous_minus_line_is_change = False
                    if diff_method == 'pdiff0': line = '!' + line[1:]
                    print_color, print_line = COL_DIFFADD, line
                else: print_color, print_line = COL_ADDED, line
            # PRINTALL ---------------------------------------------------------
            elif print_equallines: print_color, print_line = COL_EQUAL, line
            # check if
            if not print_line:
                # print lines grey, write also equal values !!!
                for item in printalllines_list:
                    if (re.search(item,line)) != None: print_color, print_line = COL_EQUAL, line
            # PROBLEM LIST - In case of DOWN/FAIL write also equal values !!!
            for item in problem_list:
                if (re.search(item,line)) != None: print_color, print_line = COL_PROBLEM, line
            # Final PRINT ------------------------------------------------------
            if print_line: print_string += "%s%s%s\n" % (print_color,print_line,bcolors.ENDC)
    return print_string


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
    pass
#     my_account = subprocess.check_output('whoami', shell=True)
#     my_finger_line = subprocess.check_output('finger | grep "%s"'%(my_account.strip()), shell=True)
#     try:
#         my_name = my_finger_line.splitlines()[0].split()[1]
#         my_surname = my_finger_line.splitlines()[0].split()[2]
#         if EMAIL_ADDRESS: my_email_address = EMAIL_ADDRESS
#         else: my_email_address = '%s.%s@orange.com' % (my_name, my_surname)
#         mail_command = 'echo | mutt -s "%s" -a %s -- %s' % (subject,file_name,my_email_address)
#         #mail_command = 'uuencode %s %s | mail -s "%s" %s' % (file_name,file_name,subject,my_email_address)
#         forget_it = subprocess.check_output(mail_command, shell=True)
#         print(' ==> Email "%s" sent to %s.'%(subject,my_email_address))
#     except: pass


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

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

VERSION = get_version_from_file_last_modification_date()
glob_vars = {}

# global_env = {}
# for item in eval('dir()'): global_env[item] = eval(item)

global_env = globals()

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
parser.add_argument("--readlog",
                    action = "store", dest = 'readlog', default = None,
                    help = "name of the logfile to read json.")
parser.add_argument("--readlognew",
                    action = "store", dest = 'readlognew', default = None,
                    help = "name of the logfile to read json.")
parser.add_argument("--emailaddr",
                    action = "store", dest = 'emailaddr', default = '',
                    help = "insert your email address once if is different than name.surname@orange.com,\
                    it will do NEWR_EMAIL variable record in your bashrc file and \
                    you do not need to insert it any more.")
# parser.add_argument("--vpnlist",
#                     action = "store", dest = 'vpnlist', default = str(),
#                     help = "'vpn' or ['list of vpns',...] to compare")
parser.add_argument("--printall",action = "store_true", default = False,
                    help = "print all lines, changes will be coloured")
# parser.add_argument("--difffile",
#                     action = 'store_true', dest = "diff_file", default = False,
#                     help = "do file-diff logfile (name will be generated and printed)")
parser.add_argument("--alloti",
                    action = 'store_true', dest = "alloti", default = None,
                    help = "do action on all oti routers")

args = parser.parse_args()

if args.nocolors or 'WIN32' in sys.platform.upper(): bcolors = nocolors

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

if args.emailaddr:
    append_variable_to_bashrc(variable_name='NEWR_EMAIL',variable_value=args.emailaddr)
    EMAIL_ADDRESS = args.emailaddr

if args.alloti: device_list = parse_json_file_and_get_oti_routers_list()
else: device_list = [args.device]

device_list = [args.device]

if args.device == str():
    remote_connect = None
    local_hostname = str(subprocess.check_output('hostname',shell=True)).strip().replace('\\','').replace('/','')
    device_list = [local_hostname]

# bgp_data_loaded = None
# if args.readlog:
#     bgp_data_loaded = copy.deepcopy(read_bgp_data_json_from_logfile(args.readlog))
#
# if args.readlognew:
#     bgp_data = copy.deepcopy(read_bgp_data_json_from_logfile(args.readlognew))

# compare_vpn_list = None
# if args.vpnlist:
#     compare_vpn_list = args.vpnlist.replace('[','').replace(']','').replace('(','').\
#         replace(')','').split(',')

if remote_connect:
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

logfilename, router_type = None, None
if not args.readlognew:
    for device in device_list:
        if device:
            router_prompt = None
            try: DEVICE_HOST = device.split(':')[0]
            except: DEVICE_HOST = str()
            try: DEVICE_PORT = device.split(':')[1]
            except: DEVICE_PORT = '22'
            print('DEVICE %s (host=%s, port=%s) START.........................'\
                %(device,DEVICE_HOST, DEVICE_PORT))
            if remote_connect:
                ####### Figure out type of router OS
                if not args.router_type:
                    #router_type = netmiko_autodetect(device)
                    router_type = detect_router_by_ssh(device)
                    if not router_type in KNOWN_OS_TYPES:
                        print('%sUNSUPPORTED DEVICE TYPE: %s , BREAK!%s' % \
                            (bcolors.MAGENTA,router_type, bcolors.ENDC))
                        continue
                    else: print('DETECTED DEVICE_TYPE: %s' % (router_type))
                else:
                    router_type = args.router_type
                    print('FORCED DEVICE_TYPE: ' + router_type)

            ######## Create logs directory if not existing  #########
            if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
            logfilename = generate_file_name(prefix = device, suffix = 'log')
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
                else: CMD = CMD_LOCAL

            run_remote_and_local_commands(CMD, logfilename, printall = True , \
                printcmdtologfile = True)

            if logfilename and os.path.exists(logfilename):
                print('%s file created.' % (logfilename))
                try: send_me_email(subject = logfilename.replace('\\','/').\
                         split('/')[-1], file_name = logfilename)
                except: pass
            print('\nDEVICE %s DONE.'%(device))

# difffilename = str()
# if not logfilename: logfilename = generate_file_name(prefix = device, suffix = 'log')
#
# if bgp_data_loaded and compare_vpn_list:
#     print(bcolors.YELLOW + '\n' + 75*'=' + '\nBGP DIFFERENCIES:\n' + 75*'=' + bcolors.ENDC)
#     for vpn_name in compare_vpn_list:
#         data1 = copy.deepcopy(return_string_from_bgp_vpn_section(bgp_data_loaded, vpn_name))
#         data2 = copy.deepcopy(return_string_from_bgp_vpn_section(bgp_data, vpn_name))
#         if data1 and data2:
#             print(bcolors.BOLD + '\nVPN: ' + vpn_name + bcolors.ENDC)
#             diff_result = get_difference_string_from_string_or_list( \
#                 data1,data2, \
#                 diff_method = 'ndiff0', \
#                 ignore_list = default_ignoreline_list, \
#                 print_equallines = args.printall, \
#                 note=False)
#             if len(diff_result) == 0: print(bcolors.GREY + 'OK' + bcolors.ENDC)
#             else: print(diff_result)
#             if args.diff_file:
#                 difffilename = logfilename + '-diff'
#                 print(difffilename)
#                 with open(difffilename, "a") as myfile:
#                     myfile.write('\n' + bcolors.BOLD + vpn_name + bcolors.ENDC +'\n')
#                     if len(diff_result) == 0: myfile.write(bcolors.GREY + 'OK' + bcolors.ENDC + '\n\n')
#                     else: myfile.write(diff_result + '\n\n')
#     print(bcolors.YELLOW + '\n' + 75*'=' + bcolors.ENDC)
#     if args.diff_file:
#         try: send_me_email(subject = difffilename.replace('\\','/').split('/')[-1],\
#                     file_name = difffilename)
#         except: pass

print('\nEND [script runtime = %d sec].'%(time.time() - START_EPOCH))


