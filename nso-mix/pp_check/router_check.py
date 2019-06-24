#!/usr/bin/python

###############################################################################
# File name: router_check                                                     #
# Author: Philippe Marcais (philippe.marcais@orange.com)                      #
#         Peter Nemec      (peter.nemec@orange.com)                           #
# Created: 06/01/2015                                                         #
# Updated: 23/Mar/2019 -added new custom filediff                             #
#          25/Mar/2019 -added vrp huawei router type, old/new filediff method #
#          05/Apr/2019 -autod. all, new commands, new filtering, new colours  #
# TODO: huawei vrp autodetect                                                 #
# Description: Script to collect and compare output from a router before      #
# and after a configuration change or maintenance to outline router change    #
# status                                                                      #
###############################################################################

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
import six

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

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

TODAY                   = datetime.datetime.now()
PLATFORM_DESCR_XR       = 'Cisco IOS XR Software'
PLATFORM_DESCR_IOS      = 'Cisco IOS Software'
PLATFORM_DESCR_JUNOS    = 'Juniper Networks'
PLATFORM_DESCR_VRP      = 'Huawei Versatile Routing Platform Software'
PLATFORM_DESCR_CRS      = 'Cisco IOS XR Software (Cisco CRS'
PLATFORM_DESCR_NCS      = 'Cisco IOS XR Software (Cisco NCS'
PLATFORM_DESCR_ASR9K    = 'Cisco IOS XR Software (Cisco ASR9K'
PLATFORM_DESCR_MX2020   = 'Juniper Networks, Inc. mx2020'
TIMEOUT         = 60

WORKDIR_IF_EXISTS       = os.path.join(os.path.abspath(os.sep),'var','PrePost')

WORKDIR                 = str()
try:    PASSWORD        = os.environ['NEWR_PASS'].replace('\\','')
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()
try:    EMAIL_ADDRESS   = os.environ['NEWR_EMAIL']
except: EMAIL_ADDRESS   = str()

note_ndiff_string  = "ndiff( %s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (bcolors.RED,bcolors.GREEN,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_ndiff0_string = "ndiff0(%s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFDEL,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )
note_pdiff0_string = "pdiff0(%s'-' missed, %s'+' added, %s'!' difference,    %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )

default_problemline_list   = []
default_ignoreline_list    = [r' MET$', r' UTC$']
default_linefilter_list    = []
default_compare_columns    = []
default_printalllines_list = []

###############################################################################
#
# Generic list of commands for pre/post check ans slicers
#
###############################################################################

# CLI LIST:
# 0-cli
# 1-diff_method
# 2-ignore_list - filters out all lines which contains words
# 3-problemline_list
# 4-printalllines_list
# 5-linefilter_list
# 6-compare_columns
# 7-printall

# IOS-XE is only for IPsec GW 
CMD_IOS_XE = [
            ("show version",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show running-config",
                   'ndiff0'),
            ("show isis neighbors",
                   'ndiff0', [], ['DOWN'],
                   [], [], [0,1,2,3,4], False),
            ("show mpls ldp neighbor",
                   'ndiff0', ['Up time:'], [],
                   [], [], [0,1,2,3,5], False ),
            ("show ip interface brief",
                   'ndiff0', [], [],
                   [], [], [], False ),
            ("show ip route summary",
                   'ndiff0', [], [],
                   [], [], [0,1,2], False),
            ("show crypto isakmp sa",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show crypto ipsec sa count",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show crypto eli",
                   'ndiff0', [], [],
                   [], [], [], False),
            ('sh int | i (line protocol|input rate|output rate)',
                   'ndiff0', [], [],
                   ['line protocol'], [], [], False),
            ('sh ip bgp neighbors | i (BGP neighbor is|Prefixes )',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False),
            ('sh ip bgp vpnv4 all neighbors | i (BGP neighbor is|Prefixes )',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False),

#             ('show interfaces | include (^[A-Z].*|minute|second|Last input)',
#                    'ndiff0', [], [' 0 bits/sec'],
#                    [], [], [], False)
             ]
CMD_IOS_XR = [
            ("show install active summary",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show install summary",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show install inactive summary",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show running-config",
                   'ndiff0', [], [],
                   [], [], [], False ),
            ("admin show run",
                    'ndiff0', [], [],
                    [], [], [], False ),
            ("show interface brief",
                   'ndiff0', [], [],
                   [], [], [], False ),
            ("show isis interface brief",
                   'ndiff0',[], [],
                   [], [], [], False),
            ("show isis neighbors",
                   "ndiff0", [], ['Down'],
                   [], [], [0,1,2,3], False),
            ("show mpls ldp neighbor brief",
                   'ndiff0', [], [],
                   [], [], [0,1,2,4,5,6,7,9], False),
            ("show mpls ldp interface brief",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show bgp ipv4 uni summary",
                   'ndiff0', ['Speaker'], [],
                   ['Neighbor        Spk'], [], [0,1,2], False),
            ("show bgp ipv4 multi summary",
                   'ndiff0', ['Speaker'], [],
                   ['Neighbor        Spk'], [], [0,1,2], False),
            ("show bgp ipv6 uni summary",
                   'ndiff0', ['Speaker','                  0 '], [],
                   [], [], [0,1,2], False),
            ("show bgp vpnv4 unicast sum",
                   'ndiff0', ['Speaker'], [],
                   [], [], [0,1,2,5,6,7], False),
            ("show bgp vrf all sum | exc \"BGP|ID|stop|Process|Speaker\"",
                   'ndiff0', ['Speaker'], [],
                   [], [], [0,1,2,3,4,5], False),
            ("show route summary",
                   'ndiff0', ['Total'], [],
                   [], [], [], False),
            ("show rsvp neighbors",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show pim neighbor",
                   'ndiff0', [], [],
                   [], [], [0,1,4,5,6], False),
            ("show l2vpn xconnect groups",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("admin show platform",
                    'ndiff0', [], [],
                    [], [], [], False),
            ("show redundancy summary",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show processes cpu | utility head count 3",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show inventory",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show mpls interface",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show license",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show l2vpn xconnect",
                   'ndiff0', [], [],
                   [], [], [], False),
            ('sh int | i "line protocol|input rate|output rate"',
                   'ndiff0', [], [],
                   [', line protocol is'], [], [], False),
            ('sh bgp neighbor',
                   'ndiff0', [], [],
                   [', line protocol is'], [], [], False),
            ('sh ip bgp neighbors | i "BGP neighbor is|prefixes|Prefix"',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False),
            ('sh bgp vpnv4 unicast neighbors | i "BGP neighbor is|prefixes|Prefix"',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False),
#             ("show interfaces | in \"^[A-Z].*|minute|second|Last input|errors|total\"",
#                    'ndiff0', ['is administratively down,'], [],
#                    [', line protocol is'], [], [], False)
             ]
             
### JUNOS ACCEPTS ONLY 60 CHARs LONG LINE, WITH NO CONTRACTIONS !!!             
CMD_JUNOS = [
            ("show system software",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show configuration",
                   "ndiff0"),
            ("show interfaces terse",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show isis adjacency",
                   "ndiff0", [], ['DOWN'],
                   [], [], [0,1,2,3], False),
            ("show ldp session brief",
                   'ndiff0', [], [],
                   [], [], [0,1,2], False),
            ("show ldp neighbor",
                   'ndiff0', [], [],
                   [], [], [0,1,2], False),
            ("show bgp summary",
                   'ndiff0', [], [],
                   [], [], [0,1], False),
            ("show rsvp neighbor",
                   'ndiff0', [], [],
                   [], [], [0], False),
            ("show pim neighbors",
                   'ndiff0', [], [],
                   [], [], [0,1,2,3,6], False),
            ("show l2vpn connections summary",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis routing-engine",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis fpc",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis fpc pic-status",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis power",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show system alarms",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show l2circuit connections brief",
                   'ndiff0', [], [],
                   [], [], [], False),
            ('show interfaces | match "Physical interface:| rate "',
                   'ndiff0', [], [],
                   ['Physical interface:'], [], [], False),
            ('show bgp neighbor | match "^Peer:|prefixes:|damping:"',
                   'ndiff0', [], [],
                   ['Peer:'], [], [], False),
#             ('show interfaces detail | match "Physical interface|Last flapped| bps"',
#                    'ndiff0',['Administratively down'], [],
#                    ['Physical interface:'], [], [0,1,2,3,4], False)
            ]
CMD_VRP = [
            ("display version",
                      'ndiff0', ['uptime','Uptime'], [],
                      [], [], [], False),
            ("display inventory",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display current-configuration",
                      'ndiff0'),
            ("display isis interface",
                      'ndiff0',[], [],
                      [], [], [], False),
            ("display isis peer",
                      'ndiff0', [], ['Down'],
                      [], [], [0,1,2,3], False),
            ("display saved-configuration",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display startup",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display acl all",
                      'ndiff0', [], [' 0 times matched'],
                      [], [], [0,1,2,3,4,5], False),
            ("display alarm all",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display ip interface brief",
                      'ndiff0', [], [],
                      [], [], [], False),
#             ("display ip routing-table",
#                       'ndiff0', [], [],
#                       [], [], [0,1,2,4,5,6], False),
            ("display ip routing-table statistics",
                      'ndiff0', [], [],
                      [], [], [0,1,2], False),
            ("display bgp routing-table statistics",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display bgp peer",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display bgp multicast peer",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display bgp ipv6 peer",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display bgp vpnv4 all peer",
                      'ndiff0', [], [],
                      [], [], [0,1,2,7], False),
            ("display mpls l2vc brief",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("display interface brief",
                      'ndiff0', [], [],
                      [], [], [], False),
            ("disp bgp peer verbose | i (BGP Peer is|routes)",
                      'ndiff0', [], [],
                      ['Peer'], [], [], False),
            ("disp bgp vpnv4 all peer verbose | i (BGP Peer is|routes)",
                      'ndiff0', [], [],
                      ['Peer'], [], [], False),
#             ('display interface | include (Description|current state|minutes|Last physical|bandwidth utilization)',
#                       'ndiff0', [], [],
#                       ['Description:','current state'], [], [0,1,2,3,4], False)
            ]

IOS_XR_SLICE = {
            'show isis neighbors' : 51,
            'show pim neighbor'   : 45,
        }

###############################################################################
#
# Function and Class
#
###############################################################################

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
    #client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try: PARAMIKO_HOST = device.split(':')[0]
    except: PARAMIKO_HOST = str()
    try: PARAMIKO_PORT = device.split(':')[1]
    except: PARAMIKO_PORT = '22'

    try:
        #connect(self, hostname, port=22, username=None, password=None, pkey=None, key_filename=None, timeout=None, allow_agent=True, look_for_keys=True, compress=False)
        client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), username=USERNAME, password=PASSWORD,look_for_keys=False)
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
    output, output2, new_prompt = str(), str(), str()
    exit_loop, exit_loop2 = False, False
    timeout_counter, timeout_counter2 = 0, 0
    # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
    if chan.recv_ready(): flush_buffer = chan.recv(9999)
    chan.send(send_data + '\n')
    time.sleep(0.1)
    if printall: print("%sCOMMAND: %s%s%s" % (bcolors.GREEN,bcolors.YELLOW,send_data,bcolors.ENDC))
    while not exit_loop:
        if chan.recv_ready():
            # workarround for discontious outputs from routers
            timeout_counter = 0
            buff = chan.recv(9999)
            buff_read = buff.decode("utf-8").replace('\x0d','').replace('\x07','').\
                replace('\x08','').replace(' \x1b[1D','')
            output += buff_read
            if printall: print("%s%s%s" % (bcolors.GREY,buff_read,bcolors.ENDC))
        else: time.sleep(0.1); timeout_counter += 1
        # FIND LAST LINE, THIS COULD BE PROMPT
        try: last_line, last_line_orig = output.splitlines()[-1].strip(), output.splitlines()[-1].strip()
        except: last_line, last_line_orig = str(), str()
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
            # 30 SECONDS COMMAND TIMEOUT
            if (timeout_counter) > 30*10: exit_loop=True; break
            # 15 SECONDS --> This could be a new PROMPT
            elif (timeout_counter) > 15*10 and not exit_loop2:
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
                        print('%sNEW_PROMPT: %s%s' % (bcolors.CYAN,last_line_orig,bcolors.ENDC))
                        new_prompt = last_line_orig; exit_loop=True;exit_loop2=True; break
                    # WAIT UP TO 5 SECONDS
                    if (timeout_counter2) > 5*10: exit_loop2 = True; break
    return output, new_prompt


# Find a section of text betwwen "cli" variable from upper block and "prompt
def find_section(text, prompts,cli_index, cli , file_name = str(),debug = False):
    look_end = 0
    b_index, e_index, c_index = None, None, -1
    for index,item in enumerate(text):
        for prompt in prompts:
            if prompt.rstrip() in text[index].rstrip():
                c_index = c_index+1
                # beginning section found ... or (c_index == cli_index):
                # + workarround for long commands shortened in router echoed line
                try: cmd_text_short = text[index].rstrip()[0:73].split(prompt)[1]
                except: cmd_text_short = str()
                if debug: print('@@@@@@@@@@',cli_index,c_index,cmd_text_short,cli)
                if (prompt+cli.rstrip()) in text[index].rstrip() or \
                    (c_index == cli_index and cmd_text_short and cmd_text_short in cli.rstrip()):
                    b_index = index
                    look_end = 1                       # look for end of section now
                    break #continue
                if look_end == 1:
                    if prompt.rstrip() in text[index]:
                        e_index = index
                        look_end = 0
    if not(b_index and e_index):
        print("%sSection '%s' could not be found %s!%s" % \
              (bcolors.MAGENTA,cli.rstrip(),file_name,bcolors.ENDC))
        return str()
    return text[b_index:e_index]


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


def print_cmd_list(CMD):
    if str(args.cmdlist) == 'list':
        print("\nCOMMAND LIST:")
        for cli_index, cli_items in enumerate(CMD):
            print("  %2d.    %s" % (cli_index,cli_items[0]))
        print('\n')
        sys.exit(0)


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

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

VERSION = get_version_from_file_last_modification_date()


######## Parse program arguments #########
if len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
    print(('DIFF_FORMATS:\n  %s  %s  %s') % \
          (note_ndiff_string,note_ndiff0_string, note_pdiff0_string))

parser = argparse.ArgumentParser(
    description = "Script to perform Pre and Post router check v.%s" % (VERSION),
    epilog = "e.g: %s --device ASHTR2 --post\n" % (sys.argv[0]))

parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device', default = None,
                    help = "target router to check")
parser.add_argument("--os",
                    action = "store", dest="router_type",
                    choices = ["ios-xr", "ios-xe", "junos", "vrp", "linux"],
                    help = "router operating system type")
parser.add_argument("--post", action = "store_true",
                    help = "run Postcheck")
parser.add_argument("--prefile",
                    action = 'store', dest = "precheck_file", default = str(),
                    help = "run postcheck against a specific precheck file")
parser.add_argument("--postfile",
                    action = 'store', dest = "postcheck_file", default = str(),
                    help = "specify your postcheck file")
parser.add_argument("--cmdfile", action = 'store', dest = "cmd_file", default = str(),
                    help = "specify a file with a list of commands to execute")
parser.add_argument("--user", default = str(),
                    action = "store", dest = 'username',
                    help = "specify router user login")
parser.add_argument("--noslice",
                    action = "store_true",
                    default = False,
                    help = "postcheck with no end of line cut")
parser.add_argument("--olddiff",action = "store_true", default = False,
                    help = "force old diff method")
parser.add_argument("--printall",action = "store_true", default = False,
                    help = "print all lines, changes will be coloured")
parser.add_argument("--recheck",action = "store_true", default = False,
                    help = "recheck last or specified diff pre/post files per inserted device")
parser.add_argument("--cmdlist",
                    action = "store", dest = 'cmdlist', default = '',
                    help = "<list> - print command list / <nr of command> - choose one command from command list for post comparison")
parser.add_argument("--logfile",
                    action = 'store_true', dest = "log_file", default = False,
                    help = "do file-diff logfile (name will be generated and printed)")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = False,
                    help = "print mode with no colors.")
parser.add_argument("--fgetpass",
                    action = 'store_true', dest = "fgetpass", default = False,
                    help = "force getpass.getpass() call even if NEWR_PASS is set.")
parser.add_argument("--latest",
                    action = 'store_true', dest = "latest", default = False,
                    help = "look for really latest pre/postcheck files (also from somebody else),\
                    otherwise your own last pre/postcheck files will be used by default")
parser.add_argument("--emailaddr",
                    action = "store", dest = 'emailaddr', default = '',
                    help = "insert your email address once if is different than name.surname@orange.com,\
                    it will do NEWR_EMAIL variable record in your bashrc file and you do not need to insert it any more.")
args = parser.parse_args()

if args.emailaddr:
    append_variable_to_bashrc(variable_name='NEWR_EMAIL',variable_value=args.emailaddr)
    EMAIL_ADDRESS = args.emailaddr

if args.nocolors: bcolors = nocolors

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

if args.post: pre_post = 'post'
elif args.recheck: pre_post = 'post'
else: pre_post = 'pre'

if not args.device:
    print(bcolors.MAGENTA + " ... Please insert device name !" + bcolors.ENDC)
    sys.exit(0)

# SET WORKING DIRECTORY
try:    WORKDIR         = os.path.join(os.environ['HOME'],'logs')
except: WORKDIR         = os.path.join(str(os.path.dirname(os.path.abspath(__file__))),'logs')
if os.path.isdir(WORKDIR_IF_EXISTS) and os.path.exists(WORKDIR_IF_EXISTS):
    WORKDIR = WORKDIR_IF_EXISTS

####### Set USERNAME if needed
if args.username: USERNAME = args.username
if not USERNAME:
    print(bcolors.MAGENTA + " ... Please insert your username by cmdline switch --user username !" + bcolors.ENDC )
    sys.exit(0)

# SSH (default)
if not PASSWORD or args.fgetpass: PASSWORD = getpass.getpass("TACACS password: ")

router_prompt = None
try: PARAMIKO_HOST = args.device.split(':')[0]
except: PARAMIKO_HOST = str()
try: PARAMIKO_PORT = args.device.split(':')[1]
except: PARAMIKO_PORT = '22'

####### Figure out type of router OS
if not args.router_type:
    #router_type = find_router_type(args.device)
    router_type, router_prompt = detect_router_by_ssh(args.device,debug = False)
    print('DETECTED ROUTER_TYPE: ' + router_type)
else:
    router_type = args.router_type
    print('FORCED ROUTER_TYPE: ' + router_type)

######## Create logs directory if not existing  ######### 
if not os.path.exists(WORKDIR): os.makedirs(WORKDIR)

####### Find necessary pre and post check files if needed 
if args.precheck_file:
    if not os.path.isfile(args.precheck_file):
        if os.path.isfile(os.path.join(WORKDIR,args.precheck_file)):
            precheck_file = os.path.join(WORKDIR,args.precheck_file)
        else:
            print(bcolors.MAGENTA + " ... Can't find precheck file: %s" % \
                (args.precheck_file) + bcolors.ENDC)
            sys.exit()
    else:
        precheck_file = args.precheck_file
        pre_post = 'post'
else:
    if pre_post == 'post' or args.recheck or args.postcheck_file:
        if args.latest:
            list_precheck_files = glob.glob(os.path.join(WORKDIR,args.device.replace(':','_').replace('.','_')) + '*' + 'pre')
        else:
            list_precheck_files = glob.glob(os.path.join(WORKDIR,args.device.replace(':','_').replace('.','_')) + '*' + USERNAME + '-pre')

        if len(list_precheck_files) == 0:
            print(bcolors.MAGENTA + " ... Can't find any precheck file." + bcolors.ENDC)
            sys.exit()
        most_recent_precheck = list_precheck_files[0]
        for item in list_precheck_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_precheck)):
                most_recent_precheck = item
        args.precheck_file = most_recent_precheck
        precheck_file = most_recent_precheck

# find last existing postcheck file
if args.recheck or args.postcheck_file:
    if args.postcheck_file:
        if not os.path.isfile(args.postcheck_file):
            if os.path.isfile(os.path.join(WORKDIR,args.postcheck_file)):
                postcheck_file = os.path.join(WORKDIR,args.postcheck_file)
            else:
                print(bcolors.MAGENTA + " ... Can't find postcheck file: %s" % \
                    (args.postcheck_file) + bcolors.ENDC)
                sys.exit()
        else:
            postcheck_file = args.postcheck_file
            pre_post = 'post'
    else:
        if args.latest:
            list_postcheck_files = glob.glob(os.path.join(WORKDIR,args.device.replace(':','_').replace('.','_')) + '*' + 'post')
        else:
            list_postcheck_files = glob.glob(os.path.join(WORKDIR,args.device.replace(':','_').replace('.','_')) + '*' + USERNAME + '-post')

        if len(list_postcheck_files) == 0:
            print(bcolors.MAGENTA + " ... Can't find any postcheck file." + bcolors.ENDC)
            sys.exit()
        most_recent_postcheck = list_postcheck_files[0]
        for item in list_postcheck_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_postcheck)):
                most_recent_postcheck = item
        postcheck_file = most_recent_postcheck


######## Find command list file (optional)
list_cmd = []
if args.cmd_file:
    if not os.path.isfile(args.cmd_file):
        print(bcolors.MAGENTA + " ... Can't find command file: %s " + bcolors.ENDC) \
                % args.cmd_file
        sys.exit()
    else:
        num_lines = sum(1 for line in open(args.cmd_file))
        fp_cmd = open(args.cmd_file,"r")
        for index in range(0, num_lines):
            list_cmd.append([fp_cmd.readline().strip()])
        fp_cmd.close

filename_prefix = os.path.join(WORKDIR,args.device.replace(':','_').replace('.','_'))
filename_suffix = pre_post
now = datetime.datetime.now()
filename_generated = "%s-%.2i%.2i%.2i-%.2i%.2i%.2i-%s-%s" % \
    (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,now.second,USERNAME,filename_suffix)
filename = None

logfilename=str()
if args.log_file:
    logfilename = "%s-%.2i%.2i%.2i-%.2i%.2i%.2i-%s-%s" % \
    (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,now.second,USERNAME,'log')

if not args.recheck:
    if str(args.cmdlist) != 'list':
        if pre_post == "post":
            print(" ==> STARTING POSTCHECK ...")
        elif pre_post == "pre":
            print(" ==> STARTING PRECHECK ...")
        print(" ... Openning %s check file to collect output" %( pre_post ))
        filename = filename_generated

### if not inserted --postfile, we will use generated filename and write to this new file
if not args.recheck and not args.postcheck_file: postcheck_file = filename

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

print_cmd_list(CMD)

# if postcheck file inserted DO-NOT new postcheck file
if args.recheck or args.postcheck_file: pass
else:
    # SSH (default)
    print(" ... Connecting (SSH) to %s" % (args.device))
    client = paramiko.SSHClient()
    #client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        output = str()
        client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), username=USERNAME, password=PASSWORD,look_for_keys=False)
        chan = client.invoke_shell()
        chan.settimeout(TIMEOUT)
        output, forget_it = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,TERM_LEN_0,printall=False)
        output, forget_it = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,"",printall=False)
        with open(filename,"w") as fp:
            fp.write(output)
            for cli_items in CMD:
                try:
                    item = cli_items[0] if type(cli_items) == list or type(cli_items) == tuple else cli_items
                    # py2to3 compatible test if type == string
                    if isinstance(item, six.string_types):
                        print(' ... %s'%(item))
                        output, new_prompt = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,item,printall=False)
                        if new_prompt: DEVICE_PROMPTS.append(new_prompt)
                        fp.write(output)
                except: pass

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.FAIL + " ... Connection closed. %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    ### MAKE READABLE for THE OTHERS
    last_output = subprocess.check_output('chmod +r %s' % (filename),shell=True)
    print(" ... Collection is completed\n")

# Post Check treatment 
if pre_post == "post" or args.recheck or args.postcheck_file:
    print(" ==> COMPARING PRECHECK & POSTCHECK ...\n")

    # Opening pre and post check files and loading content for processing
    print("\nPrecheck file:")
    if os.path.isfile(precheck_file) and os.access(precheck_file, os.R_OK):
        print('%s file exists.'%(precheck_file))
    else:
        print('%s file does not exists or access problem occurs.'%(precheck_file))
        sys.exit()

    print("\nPostcheck file:")
    if os.path.isfile(postcheck_file) and os.access(postcheck_file, os.R_OK):
        print('%s file exists.'%(postcheck_file))
    else:
        print('%s file does not exists or access problem occurs.'%(postcheck_file))
        sys.exit()
    fp1 = open(precheck_file,"r")
    fp2 = open(postcheck_file,"r")

    # routers sometimes returns windows lines ('\r\n')
    # readlines() splits by default '\n' only and '\r'stays in lines ('\r'+text+'\r\n' )
    text1_lines = fp1.read().replace('\r','').splitlines()
    text2_lines = fp2.read().replace('\r','').splitlines()

    # close file descriptors for sure
    fp1.close()
    fp2.close()

    # run chosen command only from CMD list if inserted
    try: cmd_index = int(args.cmdlist)
    except: cmd_index = -1

    if logfilename:
        with open(logfilename, "w+") as myfile:
            myfile.write('\nPrecheck file: %s\nPostcheck file: %s\n\n'%(precheck_file,postcheck_file))

    # run commands tgrough CMD list
    for cli_index, cli_items in enumerate(CMD):
        if cmd_index>=0 and cli_index != cmd_index: continue
        cli = cli_items[0]

        # old comparison method
        if args.olddiff:
            # set up correct slicing to remove irrelevant end of line info
            if (cli in IOS_XR_SLICE) and (not args.noslice):
                slicer = IOS_XR_SLICE[cli]
            else:
                slicer = 100
            # Looking for relevant section in precheck file
            precheck_section = find_section(text1_lines, DEVICE_PROMPTS, cli_index, cli)
            for index, item in enumerate(precheck_section):
                precheck_section[index] =  precheck_section[index][:slicer]

            #Looking for relevant section in postcheck file
            postcheck_section = find_section(text2_lines, DEVICE_PROMPTS, cli_index, cli)
            for index, item in enumerate(postcheck_section):
                postcheck_section[index] = postcheck_section[index][:slicer]

            # Building DIFF for this section
            diff = difflib.ndiff(precheck_section, postcheck_section)
            clean_diff = list(diff)
            diff_print_pre = list()
            diff_print_post = list()

            for index, item in enumerate(clean_diff):
                clean_diff[index] = item.rstrip()
            if (re.match(r'^\+',clean_diff[index])) != None \
                and (re.search(r'MET$',clean_diff[index])) == None \
                and (re.search(r'UTC$',clean_diff[index])) == None:
                    diff_print_pre.append(clean_diff[index])

            for index, item in enumerate(clean_diff):
                clean_diff[index] = item.rstrip()
                if (re.match(r'^\-',clean_diff[index])) != None \
                    and (re.search(r'MET$',clean_diff[index])) == None \
                    and (re.search(r'UTC$',clean_diff[index])) == None:
                        diff_print_post.append(clean_diff[index])

            # Display diff
            if len(diff_print_pre) != 0 or len(diff_print_post) != 0:
                if logfilename:
                    with open(logfilename, "a") as myfile:
                        myfile.write(bcolors.BOLD + '\n' + cli + bcolors.ENDC +'\n')
                        for index, line in enumerate(diff_print_pre):
                            myfile.write(bcolors.GREEN + '\t' +  diff_print_pre[index] + bcolors.ENDC + '\n')
                        for index, line in enumerate(diff_print_post):
                            myfile.write(bcolors.RED + '\t' +  diff_print_post[index] + bcolors.ENDC + '\n')

                print(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                for index, line in enumerate(diff_print_pre):
                    print(bcolors.GREEN + '\t' +  diff_print_pre[index] + bcolors.ENDC)
                for index, line in enumerate(diff_print_post):
                    print(bcolors.RED + '\t' +  diff_print_post[index] + bcolors.ENDC)



        else:
            # unpack cli list
            try: cli_diff_method = cli_items[1]
            except: cli_diff_method = 'ndiff0'

            try: cli_ignore_list = cli_items[2]
            except: cli_ignore_list = []

            try: cli_problemline_list = cli_items[3]
            except: cli_problemline_list = []

            try: cli_printalllines_list = cli_items[4]
            except: cli_printalllines_list = []

            try: cli_linefilter_list = cli_items[5]
            except: cli_linefilter_list = []

            try: cli_compare_columns = cli_items[6]
            except: cli_compare_columns = []

            if args.printall:
                cli_printall = args.printall
            else:
                try: cli_printall = cli_items[7]
                except: cli_printall = False

            # Looking for relevant section in precheck file
            precheck_section = find_section(text1_lines, DEVICE_PROMPTS, \
                cli_index, cli, file_name = 'in ' + precheck_file + ' file ')

            #Looking for relevant section in postcheck file
            postcheck_section = find_section(text2_lines, DEVICE_PROMPTS, \
                cli_index, cli, file_name = 'in ' + postcheck_file + ' file ')

            if precheck_section and postcheck_section:
                print(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                diff_result = get_difference_string_from_string_or_list( \
                    precheck_section,postcheck_section, \
                    diff_method = cli_diff_method, \
                    ignore_list = default_ignoreline_list + cli_ignore_list, \
                    problem_list = cli_problemline_list, \
                    printalllines_list = cli_printalllines_list, \
                    linefilter_list = cli_linefilter_list, \
                    compare_columns = cli_compare_columns, \
                    print_equallines = cli_printall, \
                    note=False)
                if len(diff_result) == 0: print(bcolors.GREY + 'OK' + bcolors.ENDC)
                else: print(diff_result)
                if logfilename:
                    with open(logfilename, "a") as myfile:
                        myfile.write('\n' + bcolors.BOLD + cli + bcolors.ENDC +'\n')
                        if len(diff_result) == 0: myfile.write(bcolors.GREY + 'OK' + bcolors.ENDC + '\n\n')
                        else: myfile.write(diff_result + '\n\n')

    print('\n ==> POSTCHECK COMPLETE !')
elif pre_post == "pre" and not args.recheck:
    print('\n ==> PRECHECK COMPLETE !')

if filename and os.path.exists(filename):
    print(' ==> File %s created.'%(filename))
    try: send_me_email(subject = filename.replace('\\','/').split('/')[-1], file_name = filename)
    except: pass

if logfilename:
    print(' ==> LOGFILE GENERATED: %s' % (logfilename))
    try: send_me_email(subject = logfilename.replace('\\','/').split('/')[-1], file_name = logfilename)
    except: pass
############################################## END ################################################


