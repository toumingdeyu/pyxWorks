#!/usr/bin/python

###############################################################################
# File name: router_check                                                     #
# Author: Philippe Marcais (philippe.marcais@orange.com)                      #
#         Peter Nemec      (peter.nemec@orange.com)                           #
# Created: 06/01/2015                                                         #
# Updated: 10/Nov/2020 - --username alternative switch for unification        #
#          27/Oct/2020 - json mode                                            #
#          24/Aug/2020 - Custom opposite logic, new cli switch --pluscustom   #
#                      - cli switch change --custom = --customonly            #
#                      - deleted cli switch --nocustom                        #
#          29/Jun/2020 - bgp prefix check, ascii filter of chars, custom log  #
#          26/May/2020 - send emails by mailx (by apache user)                #
#          25/May/2020 - --custom (BGP) check                                 #
#          14/May/2020 -huawei L2VPN commands added                           #
#          ...                                                                #
#          21/Nov/2019 -junos name in prompt bugfix                           #
#          09/Nov/2019 -device name used allways UPPERCASE                    #
#          03/Oct/2019 -added acl commands for all router types.Linefilter ok.#
#          25/Jun/2019 -line numbers %tolerance.                              #
#          23/Mar/2019 -added new custom filediff                             #
#          25/Mar/2019 -added vrp huawei router type, old/new filediff method #
#          05/Apr/2019 -autod. all, new commands, new filtering, new colours  #
#          03/Oct/2019 -acl filter all types, ignore twice tolerance          #
# TODO:                                                                       #
# Description: Script to collect and compare output from a router before      #
# and after a configuration change or maintenance to outline router change    #
# status                                                                      #
###############################################################################

import sys, os, paramiko, copy, traceback, json, collections
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

JSON_MODE = False

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


###############################################################################
### CUSTOM CHECK POSITION LIST (PICKUP LIMITED SET of CMDs FROM ALL CMDs) #####
###############################################################################
CUSTOM_LIST_IOS_XE = []
CUSTOM_LIST_IOS_XR = [3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 27, 28, 29, 30]
CUSTOM_LIST_JUNOS = [1, 2, 3, 6, 9, 15, 16, 17, 18]
CUSTOM_LIST_VRP = [2, 3, 4, 7, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19]
###############################################################################
### OMMIT CUSTOM BGP CHECK , BUT NOT SHOW CONFIG ##############################
###############################################################################
OMMIT_CUSTOM_LIST_IOS_XE = []
OMMIT_CUSTOM_LIST_IOS_XR = [5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 27, 28, 29, 30]
OMMIT_CUSTOM_LIST_JUNOS = [2, 3, 6, 9, 15, 16, 17, 18]
OMMIT_CUSTOM_LIST_VRP = [3, 4, 7, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19]
###############################################################################


###############################################################################
# CLI LIST:
###############################################################################
# 0-cli
# 1-diff_method
# 2-ignore_list - filters out all lines which contains words
# 3-problemline_list
# 4-printalllines_list
# 5-linefilter_list
# 6-compare_columns
# 7-printall
# 8-tolerance_percentage (number)
###############################################################################


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
                   ['line protocol'], [], [], False, 10),
            ('sh ip bgp neighbors | i (BGP neighbor is|Prefixes )',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False, 3),
            ('sh ip bgp vpnv4 all neighbors | i (BGP neighbor is|Prefixes )',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False, 3),
            ('show access-lists',
                   'ndiff0', ['remark'], [],
                   ['access'], [r'^\s+\d+', r'\(\d+', r'matches\)', r'match\)'], [1,2,3,4,5,6], False),
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
                   [], [], [0,1,2,9,10], False,3),
            ("show bgp vpnv4 unicast sum",
                   'ndiff0', ['Speaker'], [],
                   [], [], [0,1,2,5,6,7,9,10], False,3),
            ("show bgp summary",
                   'ndiff0', [], [],
                   [], [], [0,1,9,10], False,3),
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
                   [', line protocol is'], [], [], False, 10),
            ('sh bgp neighbor | i "neighbor is|prefixes|Prefix"',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False, 3),
            ('sh bgp vpnv4 unicast neighbors | i "neighbor is|refix"',
                   'ndiff0', [], [],
                   ['neighbor'], [], [], False, 3),
            ('show access-lists',
                   'ndiff0', ['remark'], [],
                   ['access-list'], [r'^\s+\d+', r'\(\d+', r'matches\)', r'match\)'], [1,2,3,4,5,6], False),
#             ("show interfaces | in \"^[A-Z].*|minute|second|Last input|errors|total\"",
#                    'ndiff0', ['is administratively down,'], [],
#                    [', line protocol is'], [], [], False)
             ]

### JUNOS ACCEPTS ONLY 60 CHARs LONG LINE, WITH NO CONTRACTIONS !!!
CMD_JUNOS = [
            ("show system software",
                   'ndiff0', ['uptime','Uptime'], [],
                   [], [], [], False),
            ("show configuration | display set",
                   "ndiff"),
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
                   [], [], [0,1,8,9], False,3),
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
                   [], [], [], False,5),
            ("show chassis fpc",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis fpc pic-status",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show chassis power",
                   'ndiff0', [], [],
                   [], [], [], False,5),
            ("show system alarms",
                   'ndiff0', [], [],
                   [], [], [], False),
            ("show l2circuit connections brief",
                   'ndiff0', [], [],
                   [], [], [], False),
            ('show interfaces | match "Physical interface:| rate "',
                   'ndiff0', [], [],
                   ['Physical interface:'], [], [], False, 10),
            ('show bgp neighbor | match "^Peer:|prefixes:|damping:"',
                   'ndiff0', [], [],
                   ['Peer:'], [], [], False, 3),
            ('show configuration firewall | display set',
                   'ndiff0', [], [],
                   ['filter', 'term', 'from', 'then', 'source', 'destination', '{', '}'], [], [], False),
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
                      'ndiff0', [], [],
                      [], [r'^\s+\w+\s+\d+', r'\(\d+', r'matched\)'], [0,2,3,4,5,6], False),
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
                      [], [], [], False, 10),
            ("disp bgp peer verbose | i (BGP Peer is|routes)",
                      'ndiff0', [], [],
                      ['Peer'], [], [], False, 3),
            ("disp bgp vpnv4 all peer verbose | i (BGP Peer is|routes)",
                      'ndiff0', [], [],
                      ['Peer'], [], [], False, 3),
            ("display l2vpn ccc-interface vc-type all",
                      'ndiff0', [], [],
                      [], [], [], False),
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
        flush_buffer = chan.recv(9999)
        del flush_buffer
        chan.send('\t \n\n')
        time.sleep(0.2)
        while not (last_line and last_but_one_line and last_line == last_but_one_line):
            if debug: ifprint('FIND_PROMPT:',last_but_one_line,last_line)
            buff = chan.recv(9999)
            try:
                output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                    replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
            except: pass
            if '--More--' or '---(more' in buff.strip():
                chan.send('\x20')
                time.sleep(0.2)
            if debug: ifprint('BUFFER:' + buff)
            try: last_line = output.splitlines()[-1].strip().replace('\x20','')
            except: last_line = 'dummyline1'
            try: last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
            except: last_but_one_line = 'dummyline2'
        prompt = output.splitlines()[-1].strip()
        if debug: ifprint('DETECTED PROMPT: \'' + prompt + '\'')
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
            if debug: ifprint('LAST_LINE:',prompts,last_line)
            buff = chan.recv(9999)
            try:
                output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                    replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
            except: pass
            if '--More--' or '---(more' in buff.strip():
                chan.send('\x20')
                time.sleep(0.2)
            if debug: ifprint('BUFFER:' + buff)
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
        client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), username=USERNAME, password=PASSWORD,\
            banner_timeout = 10, \
            look_for_keys = False)

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
            ifprint(bcolors.MAGENTA + "\nCannot find recognizable OS in %s" % (output) + bcolors.ENDC)

    except (socket.timeout, paramiko.AuthenticationException) as e:
        ifprint(bcolors.MAGENTA + " ... Connection closed: %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    return router_os, prompt


def decode_bytearray(buff = None, ascii_only = None):
    buff_read = str()
    exception_text = None

    replace_sequence = lambda buffer : str(buffer.\
        replace('\x0d','').replace('\x07','').\
        replace('\x08','').replace(' \x1b[1D','').replace(u'\u2013',''))

    ### https://docs.python.org/3/library/codecs.html#standard-encodings ###
    ### http://lwp.interglacial.com/appf_01.htm ###
    if buff and not ascii_only:
        ###for coding in [CGI_CLI.sys_stdout_encoding, 'utf-8','utf-16', 'cp1252', 'cp1140','cp1250', 'latin_1', 'ascii']:
        for coding in ['utf-8', 'ascii']:
            exception_text = None
            try:
                buff_read = replace_sequence(buff.encode(encoding = coding))
                break
            except: exception_text = traceback.format_exc()

    ### available in PYTHON3 ###
    # if buff and ascii_only or not buff_read:
        # try:
            # exception_text = str()
            # buff_read = replace_sequence(ascii(buff))
        # except: exception_text = traceback.format_exc()

    if exception_text:
        err_chars = str()
        for character in replace_sequence(buff):
            if ord(character) > 128:
                err_chars += '\\x%x,' % (ord(character))
            else: buff_read += character

        if len(err_chars) > 0:
            ifprint("%sNON ASCII CHARACTERS found [%s]!%s" % (bcolors.MAGENTA,err_chars,bcolors.ENDC))
    return buff_read


def ssh_send_command_and_read_output(chan,prompts,send_data=str(),printall=True):
    output, output2, new_prompt = str(), str(), str()
    exit_loop, exit_loop2 = False, False
    timeout_counter, timeout_counter2 = 0, 0
    # FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERD
    if chan.recv_ready(): flush_buffer = chan.recv(9999)
    time.sleep(0.1)
    chan.send(send_data + '\n')
    time.sleep(0.1)
    if printall: ifprint("%sCOMMAND: %s%s%s" % (bcolors.GREEN,bcolors.YELLOW,send_data,bcolors.ENDC))
    while not exit_loop:
        if chan.recv_ready():
            # workarround for discontious outputs from routers
            timeout_counter = 0
            buff = chan.recv(9999)

            buff_read = decode_bytearray(buff)
            output += buff_read

            if printall: ifprint("%s%s%s" % (bcolors.GREY,buff_read,bcolors.ENDC))
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

                        buff_read = decode_bytearray(buff)
                        output2 += buff_read

                    else: time.sleep(0.1); timeout_counter2 += 1
                    try: new_last_line = output2.splitlines()[-1].strip()
                    except: new_last_line = str()
                    if last_line_orig and new_last_line and last_line_orig == new_last_line:
                        ifprint('%sNEW_PROMPT: %s%s' % (bcolors.CYAN,last_line_orig,bcolors.ENDC))
                        new_prompt = last_line_orig; exit_loop=True;exit_loop2=True; break
                    # WAIT UP TO 5 SECONDS
                    if (timeout_counter2) > 5*10: exit_loop2 = True; break
    return output, new_prompt


# Find a section of text betwwen "cli" variable from upper block and "prompt
def find_section(text, prompts, cli_index, cli, file_name = str(),debug = False):
    look_end = 0
    b_index, e_index, c_index = None, None, -1
    for index,item in enumerate(text):
        for prompt in prompts:
            ### JUNOS HAS USERNAME IN PROMPT!!! ###
            use_prompt = str(prompt.replace(USERNAME,'').rstrip().decode())
            use_text   = str(text[index].replace(USERNAME,'').rstrip().decode())
            use_cli    = str(cli.rstrip().decode())
            if use_prompt in use_text:
                c_index = c_index+1
                # beginning section found ... or (c_index == cli_index):
                # + workarround for long commands shortened in router echoed line
                try: cmd_text_short = str((use_text[0:73].split(use_prompt)[1]).decode())
                except: cmd_text_short = str()
                if debug: ifprint('@@@@@@@@@@',use_prompt,use_cli,use_text,cli_index,c_index,cmd_text_short)
                if (use_prompt in use_text and use_cli in use_text) or \
                    (c_index == cli_index and cmd_text_short and cmd_text_short in use_cli):
                    b_index = index
                    look_end = 1                       # look for end of section now
                    if debug: ifprint('==========',use_text,use_cli)
                    break #continue
                if look_end == 1:
                    if use_prompt in use_text:
                        e_index = index
                        look_end = 0
    if not(b_index and e_index):
        ifprint("%sSection '%s' could not be found %s!%s" % \
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
    tolerance_percentage = None, \
    debug = None, \
    note = True,
    use_twice_tolerance_for_small_values = None ):
    '''
    FUNCTION get_difference_string_from_string_or_list:
    INPUT PARAMETERS:
      - OLD_STRING_OR_LIST - content of old file in string or list type
      - NEW_STRING_OR_LIST - content of new file in string or list type
      - DIFF_METHOD - ndiff, ndiff0, pdiff0
      - IGNORE_LIST - list of regular expressions or strings when line is ignored for file (string) comparison
      - PROBLEM_LIST - list of regular expressions or strings which detects problems, even if files are equal
      - PRINTALLLINES_LIST - list of regular expressions or strings which will be printed grey, even if files are equal
      - LINEFILTER_LIST - list of REGEXs! which are filtered-out items for comparison (deleted each item in line)
      - COMPARE_COLUMNS - list of columns which are intended to be different , other columns in line are ignored
      - PRINT_EQUALLINES - True/False prints all equal new file lines with '=' prefix , by default is False
      - TOLERANCE_PERCENTAGE - All numbers/selected columns in line with % tolerance. String columns must be equal.
      - USE_TWICE_TOLERANCE_FOR_SMALL_VALUES - By default it is off , it slows down check performance
      - DEBUG - True/False, prints debug info to stdout, by default is False
      - NOTE - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies , all_ok [True/False]

    PDIFF0 FORMAT: The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    ' ' for the same line, but with problem.
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''
    print_string, all_ok = str(), True
    if note:
       print_string = "DIFF_METHOD: "
       if diff_method   == 'ndiff0': print_string += note_ndiff0_string
       elif diff_method == 'pdiff0': print_string += note_pdiff0_string
       elif diff_method == 'ndiff' : print_string += note_ndiff_string

    # MAKE LIST FROM STRING IF IS NOT LIST ALREADY -----------------------------
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
        if print_string: all_ok = False
        return print_string, all_ok

    # NDIFF0 COMPARISON METHOD--------------------------------------------------
    if diff_method == 'ndiff0' or diff_method == 'pdiff0':
        ignore_previous_line = False
        diff = difflib.ndiff(old_lines_unfiltered, new_lines_unfiltered)
        listdiff_nonfiltered = list(diff)
        listdiff = []
        # FILTER OUT - DIFF LINES OUT OF '? ' AND VOID LINES -------------------
        for line in listdiff_nonfiltered:
            # IGNORE_LIST FILTER - THISONE IS MUCH FASTER ----------------------
            ignore = False
            for ignore_item in ignore_list:
                if (re.search(ignore_item,line)) != None: ignore = True
            if ignore: continue
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            if '+ ' in first_chars or '- ' in first_chars or '  ' in first_chars:
                listdiff.append(line)
        del diff, listdiff_nonfiltered
        # MAIN NDIFF0/PDIFF0 LOOP PER LISTDIFF LIST ----------------------------
        previous_minus_line_is_change = False
        for line_number,line in enumerate(listdiff):
            print_color, print_line = COL_EQUAL, str()
            try:    first_chars_previousline = listdiff[line_number-1][0]+listdiff[line_number-1][1].replace('\t',' ')
            except: first_chars_previousline = str()
            try:    first_chars = line[0]+line[1].replace('\t',' ')
            except: first_chars = str()
            try:    first_chars_nextline = listdiff[line_number+1][0]+listdiff[line_number+1][1].replace('\t',' ')
            except: first_chars_nextline = str()
            # CHECK IF ARE LINES EQUAL AFTER FILTERING -------------------------
            split_line,split_next_line,linefiltered_line,linefiltered_next_line = str(),str(),str(),str()
            ### CLEAR AUXILIARY VARIABLES WHEN NO -/+ FIRST CHARACTERS ---------
            if first_chars.strip() == str():
                ignore_previous_line = False
                previous_minus_line_is_change = False
            ### POSSIBLE CHANGE in LINE ----------------------------------------
            if '-' in first_chars and '+' in first_chars_nextline:
                ### SELECT COMPARE_COLUMNS -------------------------------------
                for split_column in compare_columns:
                    # +1 MEANS EQUAL OF DELETION OF FIRST COLUMN -
                    try: temp_column = line.split()[split_column+1]
                    except: temp_column = str()
                    split_line += ' ' + temp_column.replace('/',' ')
                for split_column in compare_columns:
                    # +1 MEANS EQUAL OF DELETION OF FIRST COLUMN +
                    try: temp_column = listdiff[line_number+1].split()[split_column+1]
                    except: temp_column = str()
                    split_next_line += ' ' + temp_column.replace('/',' ')
                ### LINEFILTER_LIST --------------------------------------------
                try: next_line = listdiff[line_number+1]
                except: next_line = str()
                try:
                    linefiltered_next_line = re.sub(r'^[+-] ', '', next_line)
                    linefiltered_line = re.sub(r'^[+-] ', '', line)
                except:
                    linefiltered_next_line, linefiltered_line = str(), str()
                for linefilter_item in linefilter_list:
                    if linefiltered_line:
                        try: linefiltered_line = re.sub(linefilter_item, '', linefiltered_line)
                        except: pass
                    if linefiltered_next_line:
                        try: linefiltered_next_line = re.sub(linefilter_item, '', linefiltered_next_line)
                        except: pass
                ### IF SPLIT_LINE DOES not EXIST FROM COMPARE_COLUMNS DO IT ----
                if not split_line: split_line = line.replace('/',' ')
                if not split_next_line: split_next_line = listdiff[line_number+1].replace('/',' ')
                ### TOLERANCE_PERCENTAGE = COMPARING NUMBER COLUMNS with TOLERANCE
                columns_are_equal = 0
                for split_column,split_next_column in zip(split_line.split()[1:],split_next_line.split()[1:]):
                    try: next_column_is_number = float(split_next_column.replace(',','').replace('%','').replace('(',''))
                    except: next_column_is_number = None
                    try: column_is_number = float(split_column.replace(',','').replace('%','').replace('(',''))
                    except: column_is_number = None
                    if column_is_number and next_column_is_number and tolerance_percentage:
                        if not use_twice_tolerance_for_small_values or column_is_number>100:
                            if column_is_number <= next_column_is_number * ((100 + float(tolerance_percentage))/100)\
                                and column_is_number >= next_column_is_number * ((100 - float(tolerance_percentage))/100):
                                    columns_are_equal += 1
                        ### FOR SMALL VALUES UP to 100 , use TWICE TOLERANCE_PERCENTAGE - SLOW!!!
                        else:
                            if column_is_number <= next_column_is_number * ((100 + float(2 * tolerance_percentage))/100)\
                                and column_is_number >= next_column_is_number * ((100 - float(2 * tolerance_percentage))/100):
                                    columns_are_equal += 1
                    elif split_column and split_next_column and split_column == split_next_column:
                        columns_are_equal += 1
                ### IF LINES ARE EQUAL WITH +/- TOLERANCE ----------------------
                if columns_are_equal > 0 and columns_are_equal + 1 == len(split_line.split()) \
                    and columns_are_equal + 1 == len(split_next_line.split()):
                        ignore_previous_line = True
                        continue
                ### LINES ARE EQUAL AFTER FILTERING - filtered linefilter and columns commands
                if (split_line and split_next_line and split_line == split_next_line) or \
                   (linefiltered_line and linefiltered_next_line and linefiltered_line == linefiltered_next_line):
                    ignore_previous_line = True
                    continue
            # CONTINUE CHECK DELETED/ADDED LINES--------------------------------
            if '-' in first_chars:
                ignore_previous_line = False
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
            elif '+' in first_chars and ignore_previous_line:
                line = ' ' + line[1:]
                ignore_previous_line = False
            # ADDED NEW LINE ---------------------------------------------------
            elif '+' in first_chars and not ignore_previous_line:
                if previous_minus_line_is_change:
                    previous_minus_line_is_change = False
                    if diff_method == 'pdiff0': line = '!' + line[1:]
                    print_color, print_line = COL_DIFFADD, line
                else: print_color, print_line = COL_ADDED, line
            # PRINTALL ---------------------------------------------------------
            elif print_equallines: print_color, print_line = COL_EQUAL, line
            # PRINTALL LINES GREY IF not ALREADY PRINTED BY ANOTHER COLOR ------
            if not print_line:
                for item in printalllines_list:
                    if (re.search(item,line)) != None: print_color, print_line = COL_EQUAL, line
            # PROBLEM LIST - IN CASE OF DOWN/FAIL WRITE ALSO EQUAL VALUES !!! --
            for item in problem_list:
                if (re.search(item,line)) != None: print_color, print_line = COL_PROBLEM, line
            # TEST if ALL_OK ---------------------------------------------------
            if len(print_line)>0:
                if print_color == COL_PROBLEM or print_line[0] in ['+','-','!']: all_ok = False
            # Final PRINT ------------------------------------------------------
            if print_line: print_string += "%s%s%s\n" % (print_color,print_line,bcolors.ENDC)
    return print_string, all_ok


def print_cmd_list(CMD):
    if str(args.cmdlist) == 'list':
        ifprint("\nCOMMAND LIST:")
        for cli_index, cli_items in enumerate(CMD):
            ifprint("  %2d.    %s" % (cli_index,cli_items[0]))
        ifprint('\n')
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


# def send_me_email(subject='testmail', file_name='/dev/null'):
    # my_account = subprocess.check_output('whoami', shell=True)
    # my_finger_line = subprocess.check_output('finger | grep "%s"'%(my_account.strip()), shell=True)
    # try:
        # my_name = my_finger_line.splitlines()[0].split()[1]
        # my_surname = my_finger_line.splitlines()[0].split()[2]
        # if EMAIL_ADDRESS: my_email_address = EMAIL_ADDRESS
        # else: my_email_address = '%s.%s@orange.com' % (my_name, my_surname)
        # mail_command = 'echo | mutt -s "%s" -a %s -- %s' % (subject,file_name,my_email_address)
        # #mail_command = 'uuencode %s %s | mail -s "%s" %s' % (file_name,file_name,subject,my_email_address)
        # forget_it = subprocess.check_output(mail_command, shell=True)
        # ifprint(' ==> Email "%s" sent to %s.'%(subject,my_email_address))
    # except: pass



def send_me_email(subject = str(), email_body = str(), \
    file_name = None, cc = None, bcc = None, attachments = None):

    def send_unix_email_body(mail_command):
        email_success = None
        try:
            forget_it = subprocess.check_output(mail_command, shell=True)
            ifprint(' ==> Email sent. Subject:"%s" SentTo:%s by COMMAND=[%s] with RESULT=[%s]...'\
                %(subject, sugested_email_address, mail_command, forget_it))
            email_success = True
        except Exception as e:
            ifprint(" ==> Problem to send email by COMMAND=[%s], PROBLEM=[%s]\n"\
                % (mail_command, str(e)))
        return email_success

    try:
        ldapsearch_output = subprocess.check_output('ldapsearch -LLL -x uid=%s mail' % (USERNAME), shell=True)
        sugested_email_address = ldapsearch_output.decode().split('mail:')[1].splitlines()[0].strip()
    except: sugested_email_address = None

    ### UNIX - MAILX ######################################################
    mail_command = 'echo \'%s\' | mailx -s "%s" ' % (email_body, subject)
    if cc:
        if isinstance(cc, six.string_types): mail_command += '-c %s' % (cc)
        if cc and isinstance(cc, (list,tuple)): mail_command += ''.join([ '-c %s ' % (cc_email) for cc_email in cc ])
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

    ### IF EMAIL ADDRESS FOUND , SEND EMAIL ###############################
    if not sugested_email_address:
        ifprint(' ==> Email Address not found!')
    else:
        mail_command += '%s' % (sugested_email_address)
        email_sent = send_unix_email_body(mail_command)

        ### UNIX - MUTT ###################################################
        if not email_sent and file_name:
            mail_command = 'echo | mutt -s "%s" -a %s -- %s' % \
                (subject, file_name, sugested_email_address)
            email_sent = send_unix_email_body(mail_command)



def run_isis_check(append_ppfile = None, append_logfile = None, json_mode = None):

    time.sleep(3)

    command_string = '/usr/local/bin/isis_check.py'
    if args.device: command_string += ' --device %s' % (args.device.upper())
    if json_mode: command_string += ' --json'
    if append_ppfile: command_string += ' --append_ppfile %s' % (append_ppfile)
    if append_logfile: command_string += ' --append_logfile %s' % (append_logfile)
    if args.printall: command_string += ' --printall'
    command_string += ' --username %s' % (USERNAME)
    command_string += ' --password %s' % (PASSWORD)

    if append_ppfile:
        with open(append_ppfile, "a+") as myfile:
            myfile.write('\n\n')
            myfile.flush()

    if append_logfile:
        with open(append_logfile, "a+") as myfile:
            myfile.write('\n\n')
            myfile.flush()

    os.system(command_string)


def run_bgp_prefixes_checker(append_ppfile = None, append_logfile = None, json_mode = None):

    time.sleep(3)

    path_to_file = '/usr/local/bin/bgp_prefixes_checker.py'

    #path_to_file = './bgp_prefixes_checker.py'

    if not args.recheck:
        command_string = str()
        command_string += path_to_file
        if args.device: command_string += ' --device %s' % (args.device.upper())
        if json_mode: command_string += ' --json'
        if append_ppfile: command_string += ' --append_ppfile %s' % (append_ppfile)
        if append_logfile: command_string += ' --append_logfile %s' % (append_logfile)
        if args.printall: command_string += ' --printall'
        command_string += ' --username %s' % (USERNAME)
        if pre_post == 'pre': command_string += ' --precheck'
        else: command_string += ' --postcheck'
        #if precheck_file: command_string += ' --prefile %s' % (precheck_file)
        #if postcheck_file: command_string += ' --postfile %s' % (postcheck_file)
        if args.latest: command_string += ' --latest'
        command_string += ' --cpassword %s' % (CPASSWORD)

    else:
        command_string = str()
        command_string += path_to_file
        if args.device: command_string += ' --device %s' % (args.device.upper())
        if json_mode: command_string += ' --json'
        if args.printall: command_string += ' --printall'
        command_string += ' --username %s' % (USERNAME)
        command_string += ' --recheck'
        if precheck_file: command_string += ' --prefile %s' % (precheck_file)
        if postcheck_file: command_string += ' --postfile %s' % (postcheck_file)
        if args.latest: command_string += ' --latest'
        command_string += ' --cpassword %s' % (CPASSWORD)


    if append_ppfile:
        with open(append_ppfile, "a+") as myfile:
            myfile.write('\n\n')
            myfile.flush()

    if append_logfile:
        with open(append_logfile, "a+") as myfile:
            myfile.write('\n\n')
            myfile.flush()

    ###print(command_string)
    os.system(command_string)


def GET_VERSION(path_to_file = str(os.path.abspath(__file__))):
    if 'WIN32' in sys.platform.upper():
        file_time = os.path.getmtime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        file_time = stat.st_mtime
    return time.strftime("%y.%m.%d_%H:%M",time.gmtime(file_time))


def ifprint(text):
    if not JSON_MODE:
        print(text)


def json_print(prefile = None, postfile = None, logfilename = None, error = None):
    def make_link(file):
        logviewer = file
        iptac_server = str(subprocess.check_output('hostname')).strip()
        if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
        else: urllink = 'https://%s/cgi-bin/' % (iptac_server)
        if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, file)
        else: logviewer = './logviewer.py?logfile=%s' % (file)
        return logviewer

    if JSON_MODE:
        #json_header = "Content-type:application/vnd.api+json\r\nStatus: 200 OK\r\n\r\n\r\n"
        json_data = collections.OrderedDict()
        if error: json_data['error'] = str(error)
        if prefile: json_data['pre_log'] = str(make_link(prefile))
        if postfile: json_data['post_log'] = str(make_link(postfile))
        if logfilename: json_data['diff_log'] = str(make_link(logfilename))

        #print_text = str(json.dumps(json_data, indent = 2))
        print_text = str(json.dumps(json_data))
        print(print_text)
        #print(json_header + print_text)

        #print_text = str(json.dumps(json_data))
        #print(print_text)

##############################################################################
#
# def BEGIN MAIN
#
##############################################################################

precheck_file, postcheck_file = None, None

VERSION = GET_VERSION() #get_version_from_file_last_modification_date()

parser = argparse.ArgumentParser(
    description = "Script to perform Pre and Post router check v.%s" % (VERSION),
    epilog = "e.g: %s --device ASHTR2 --post\n" % (sys.argv[0]))

parser.add_argument("--version",
                    action = 'version', version = VERSION)
parser.add_argument("--device",
                    action = "store", dest = 'device', default = None,
                    help = "target router to check")
parser.add_argument("--post", action = "store_true",
                    help = "run Postcheck")
parser.add_argument("--emailaddr",
                    action = "store", dest = 'emailaddr', default = '',
                    help = "insert your email address once if is different than name.surname@orange.com,\
                    it will do NEWR_EMAIL variable record in your bashrc file and you do not need to insert it any more.")
parser.add_argument("--printall",action = "store_true", default = False,
                    help = "print all lines, changes will be coloured")
parser.add_argument("--prefile",
                    action = 'store', dest = "precheck_file", default = str(),
                    help = "run postcheck against a specific precheck file")
parser.add_argument("--postfile",
                    action = 'store', dest = "postcheck_file", default = str(),
                    help = "specify your postcheck file")
parser.add_argument("--user",
                    action = "store", dest = 'user', default = str(),
                    help = "specify router user login")
parser.add_argument("--username",
                    action = "store", dest = 'username', default = str(),
                    help = "specify router user login")
parser.add_argument("--password", default = str(),
                    action = "store", dest = 'password',
                    help = "specify router user password")
parser.add_argument("--cpassword", default = str(),
                    action = "store", dest = 'cpassword',
                    help = "specify router user cpassword")
parser.add_argument("--fgetpass",
                    action = 'store_true', dest = "fgetpass", default = False,
                    help = "force getpass.getpass() call even if NEWR_PASS is set.")
parser.add_argument("--recheck",action = "store_true", default = False,
                    help = "recheck last or specified diff pre/post files per inserted device")
parser.add_argument("--cmdlist",
                    action = "store", dest = 'cmdlist', default = '',
                    help = "<list> - print command list / <nr of command> - choose one command from command list for post comparison")
parser.add_argument("--logfile",
                    action = 'store_true', dest = "log_file", default = False,
                    help = "do file-diff logfile (name will be generated and printed)")
parser.add_argument("--latest",
                    action = 'store_true', dest = "latest", default = False,
                    help = "look for really latest pre/postcheck files (also from somebody else),\
                    otherwise your own last pre/postcheck files will be used by default")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = False,
                    help = "print mode with no colors.")
parser.add_argument("--os",
                    action = "store", dest="router_type",
                    choices = ["ios-xr", "ios-xe", "junos", "vrp", "linux"],
                    help = "router operating system type")
parser.add_argument("--cmdfile", action = 'store', dest = "cmd_file", default = str(),
                    help = "specify a file with a list of custom commands to execute, instead of built-in commands")
parser.add_argument("--olddiff",action = "store_true", default = False,
                    help = "force old diff method")
parser.add_argument("--noslice",
                    action = "store_true",
                    default = False,
                    help = "postcheck with no end of line cut used with --olddiff")
parser.add_argument("--isis",
                    action = "store_true",
                    default = False,
                    dest = 'isis_check_only',
                    help = "do isis check only")
parser.add_argument("--bgp",
                    action = "store_true",
                    default = False,
                    dest = 'bgp_prefix_check_only',
                    help = "do bgp prefixes check only")
parser.add_argument("--nobgpcheck",
                    action = "store_true",
                    default = False,
                    dest = 'nobgpcheck',
                    help = "ommit bgp prefixes check")
parser.add_argument("--customonly",
                    action = "store_true",
                    default = False,
                    dest = 'custom_check_only',
                    help = "do custom (bgp commands) check only")
parser.add_argument("--pluscustom",
                    action = "store_true",
                    default = False,
                    dest = 'plus_custom',
                    help = "do all commands with custom (bgp commands)")
parser.add_argument("--json",
                    action = "store_true",
                    default = False,
                    dest = 'json_output',
                    help = "json data output only, no other printouts")
args = parser.parse_args()

if args.json_output:
    JSON_MODE = True
    json_header = "Content-type:application/vnd.api+json\r\nStatus: 200 OK\r\n\r\n\r\n"
    #print(json_header)

if args.emailaddr:
    append_variable_to_bashrc(variable_name='NEWR_EMAIL',variable_value=args.emailaddr)
    EMAIL_ADDRESS = args.emailaddr

if args.nocolors or 'WIN32' in sys.platform.upper(): bcolors = nocolors

ifprint('router_check (v.%s)' % (VERSION))

if args.printall:
    ifprint('CLI_args = %s, [%s]\n' % (str(sys.argv[1:]), str(args)))

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

note_ndiff_string  = "ndiff( %s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (bcolors.RED,bcolors.GREEN,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_ndiff0_string = "ndiff0(%s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFDEL,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )
note_pdiff0_string = "pdiff0(%s'-' missed, %s'+' added, %s'!' difference,    %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )

######## Parse program arguments #########
if len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
    ifprint(('DIFF_FORMATS:\n  %s  %s  %s') % \
          (note_ndiff_string,note_ndiff0_string, note_pdiff0_string))


if args.post: pre_post = 'post'
elif args.recheck: pre_post = 'post'
else: pre_post = 'pre'

if not args.device:
    err_text = " ... Please insert device name !"
    ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
    json_print(error = err_text)
    sys.exit(0)

custom_check_only = True if args.custom_check_only else False
plus_custom_check = True if args.plus_custom else False

# SET WORKING DIRECTORY
try:    WORKDIR         = os.path.join(os.environ['HOME'],'logs')
except: WORKDIR         = os.path.join(str(os.path.dirname(os.path.abspath(__file__))),'logs')
if os.path.isdir(WORKDIR_IF_EXISTS) and os.path.exists(WORKDIR_IF_EXISTS):
    WORKDIR = WORKDIR_IF_EXISTS

####### Set USERNAME if needed
if args.username: USERNAME = args.username
if args.user: USERNAME = args.user
if not USERNAME:
    err_text = " ... Please insert your username by cmdline switch --user/--username username !"
    ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
    json_print(error = err_text)
    sys.exit(0)

if args.password:
    PASSWORD = str(args.password)
if args.cpassword:
    PASSWORD = str(args.cpassword).decode('base64','strict')
elif not PASSWORD or args.fgetpass:
    PASSWORD = getpass.getpass("TACACS password: ")

router_prompt = None
try: PARAMIKO_HOST = args.device.upper().split(':')[0]
except: PARAMIKO_HOST = str()
try: PARAMIKO_PORT = args.device.upper().split(':')[1]
except: PARAMIKO_PORT = '22'

CPASSWORD = '-'
if PASSWORD:
    CPASSWORD = str(PASSWORD).encode('base64','strict')


####### def Figure out type of router OS
if not args.router_type:
    #router_type = find_router_type(args.device.upper())
    router_type, router_prompt = detect_router_by_ssh(args.device.upper(),debug = False)
    ifprint('DETECTED ROUTER_TYPE: ' + router_type)
else:
    router_type = args.router_type
    ifprint('FORCED ROUTER_TYPE: ' + router_type)

######## Create logs directory if not existing  #########
if not os.path.exists(WORKDIR): os.makedirs(WORKDIR)

####### Find necessary pre and post check files if needed
if args.precheck_file:
    if not os.path.isfile(args.precheck_file):
        if os.path.isfile(os.path.join(WORKDIR,args.precheck_file)):
            precheck_file = os.path.join(WORKDIR,args.precheck_file)
        else:
            err_text = " ... Can't find precheck file: %s" % (args.precheck_file)
            ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
            json_print(error = err_text)
            sys.exit()
    else:
        precheck_file = args.precheck_file
        pre_post = 'post'
else:
    if pre_post == 'post' or args.recheck or args.postcheck_file:
        if args.latest:
            list_precheck_files = glob.glob(os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_')) + '*' + 'pre')
        else:
            list_precheck_files = glob.glob(os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_')) + '*' + USERNAME + '-pre')

        if len(list_precheck_files) == 0:
            err_text = " ... Can't find any precheck file."
            ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
            json_print(error = err_text)
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
                err_text = " ... Can't find postcheck file: %s" % (args.postcheck_file)
                ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
                json_print(error = err_text)
                sys.exit()
        else:
            postcheck_file = args.postcheck_file
            pre_post = 'post'
    else:
        if args.latest:
            list_postcheck_files = glob.glob(os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_')) + '*' + 'post')
        else:
            list_postcheck_files = glob.glob(os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_')) + '*' + USERNAME + '-post')

        if len(list_postcheck_files) == 0:
            err_text = " ... Can't find any postcheck file."
            ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
            json_print(error = err_text)
            sys.exit()
        most_recent_postcheck = list_postcheck_files[0]
        for item in list_postcheck_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_postcheck)):
                most_recent_postcheck = item
        postcheck_file = most_recent_postcheck


######## def Find command list file (optional)
list_cmd = []
if args.cmd_file:
    if not os.path.isfile(args.cmd_file):
        err_text = " ... Can't find command file: %s " % args.cmd_file
        ifprint(bcolors.MAGENTA + err_text + bcolors.ENDC)
        json_print(error = err_text)
        sys.exit()
    else:
        num_lines = sum(1 for line in open(args.cmd_file))
        fp_cmd = open(args.cmd_file,"r")
        for index in range(0, num_lines):
            list_cmd.append([fp_cmd.readline().strip()])
        fp_cmd.close

### def CUSTOM CHECK LIST CREATION ###
if custom_check_only:
    if router_type == "ios-xe":
        cmd_position = 0
        for router_cmd in CMD_IOS_XE:
            if cmd_position in CUSTOM_LIST_IOS_XE: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "ios-xr":
        cmd_position = 0
        for router_cmd in CMD_IOS_XR:
            if cmd_position in CUSTOM_LIST_IOS_XR: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "junos":
        cmd_position = 0
        for router_cmd in CMD_JUNOS:
            if cmd_position in CUSTOM_LIST_JUNOS: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "vrp":
        cmd_position = 0
        for router_cmd in CMD_VRP:
            if cmd_position in CUSTOM_LIST_VRP: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1

elif not plus_custom_check:
    if router_type == "ios-xe":
        cmd_position = 0
        for router_cmd in CMD_IOS_XE:
            if not cmd_position in OMMIT_CUSTOM_LIST_IOS_XE: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "ios-xr":
        cmd_position = 0
        for router_cmd in CMD_IOS_XR:
            if not cmd_position in OMMIT_CUSTOM_LIST_IOS_XR: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "junos":
        cmd_position = 0
        for router_cmd in CMD_JUNOS:
            if not cmd_position in OMMIT_CUSTOM_LIST_JUNOS: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1
    elif router_type == "vrp":
        cmd_position = 0
        for router_cmd in CMD_VRP:
            if not cmd_position in OMMIT_CUSTOM_LIST_VRP: list_cmd.append(copy.deepcopy(router_cmd))
            cmd_position += 1


if custom_check_only:
    filename_prefix = os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_') + '-customonly')
elif plus_custom_check:
    filename_prefix = os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_') + '-pluscustom')
else:
    filename_prefix = os.path.join(WORKDIR,args.device.upper().replace(':','_').replace('.','_'))

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
        filename = filename_generated

### ACTUAL POSTCHECK: if not inserted --postfile, we will use generated filename and write to this new file
if not pre_post == "pre" and not args.recheck and not args.postcheck_file: postcheck_file = filename



### def ISIS AND BGP_PREFIX CHECK ###
if args.isis_check_only:
    run_isis_check(filename)
    sys.exit(0)

if args.bgp_prefix_check_only:
    if args.recheck or  pre_post == "post":
        if args.recheck: run_isis_check()
        else: run_bgp_prefixes_checker(filename)
    elif pre_post == "pre" and not args.recheck:
        run_bgp_prefixes_checker(filename)
    sys.exit(0)


### def CHECK START ###
if not args.recheck:
    if str(args.cmdlist) != 'list':
        if pre_post == "post":
            ifprint(" ==> STARTING POSTCHECK ...")
        elif pre_post == "pre":
            ifprint(" ==> STARTING PRECHECK ...")
        ifprint(" ... Openning %s check file to collect output" %( pre_post ))

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
    ifprint(" ... Connecting (SSH) to %s" % (args.device.upper()))
    client = paramiko.SSHClient()
    #client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        output = str()
        client.connect(PARAMIKO_HOST, port=int(PARAMIKO_PORT), username=USERNAME, password=PASSWORD,\
            banner_timeout = 10, \
            look_for_keys = False)

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
                        ifprint(' ... %s'%(item))
                        output, new_prompt = ssh_send_command_and_read_output(chan,DEVICE_PROMPTS,item,printall=False)
                        if new_prompt: DEVICE_PROMPTS.append(new_prompt)
                        fp.write(output)
                except: pass

    except (socket.timeout, paramiko.AuthenticationException) as e:
        ifprint(bcolors.FAIL + " ... Connection closed. %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
        time.sleep(0.5)
    ### MAKE READABLE for THE OTHERS
    last_output = subprocess.check_output('chmod +r %s' % (filename), shell=True)
    ifprint(" ... Collection is completed\n")

# Post Check treatment
if pre_post == "post" or args.recheck or args.postcheck_file:
    ifprint(" ==> COMPARING PRECHECK & POSTCHECK ...\n")

    # Opening pre and post check files and loading content for processing
    ifprint("\nPrecheck file:")
    if os.path.isfile(precheck_file) and os.access(precheck_file, os.R_OK):
        ifprint('%s file exists.'%(precheck_file))
    else:
        ifprint('%s file does not exists or access problem occurs.'%(precheck_file))
        sys.exit()

    ifprint("\nPostcheck file:")
    if os.path.isfile(postcheck_file) and os.access(postcheck_file, os.R_OK):
        ifprint('%s file exists.'%(postcheck_file))
    else:
        ifprint('%s file does not exists or access problem occurs.'%(postcheck_file))
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
        ### MAKE READABLE for THE OTHERS
        forget_it = subprocess.check_output('chmod +r %s' % (logfilename), shell=True)

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

                ifprint(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                for index, line in enumerate(diff_print_pre):
                    ifprint(bcolors.GREEN + '\t' +  diff_print_pre[index] + bcolors.ENDC)
                for index, line in enumerate(diff_print_post):
                    ifprint(bcolors.RED + '\t' +  diff_print_post[index] + bcolors.ENDC)



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

            try: cli_tolerance_percentage = cli_items[8]
            except: cli_tolerance_percentage = None

            # Looking for relevant section in precheck file
            precheck_section = find_section(text1_lines, DEVICE_PROMPTS, \
                cli_index, cli, file_name = 'in ' + precheck_file + ' file ')

            #Looking for relevant section in postcheck file
            postcheck_section = find_section(text2_lines, DEVICE_PROMPTS, \
                cli_index, cli, file_name = 'in ' + postcheck_file + ' file ')

            if precheck_section and postcheck_section:
                ifprint(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                diff_result, all_ok = get_difference_string_from_string_or_list( \
                    precheck_section,postcheck_section, \
                    diff_method = cli_diff_method, \
                    ignore_list = default_ignoreline_list + cli_ignore_list, \
                    problem_list = cli_problemline_list, \
                    printalllines_list = cli_printalllines_list, \
                    linefilter_list = cli_linefilter_list, \
                    compare_columns = cli_compare_columns, \
                    print_equallines = cli_printall, \
                    tolerance_percentage = cli_tolerance_percentage, \
                    note = False)
                if all_ok: ifprint(bcolors.GREY + 'OK' + bcolors.ENDC)
                elif len(diff_result) > 0: ifprint(diff_result)

                if logfilename:
                    with open(logfilename, "a") as myfile:
                        myfile.write('\n' + bcolors.BOLD + cli + bcolors.ENDC +'\n')
                        if len(diff_result) == 0: myfile.write(bcolors.GREY + 'OK' + bcolors.ENDC + '\n\n')
                        else: myfile.write(diff_result + '\n\n')
                        myfile.flush()

    ### def ISIS CHECK DO NOT LOG IF RECHECK ##################################
    ifprint('\n')
    if args.recheck: run_isis_check()
    else:
        if JSON_MODE: run_isis_check(filename, logfilename, True)
        else: run_isis_check(filename, logfilename)

    ### def BGP PREFIX CHECK DO NOT LOG IF RECHECK ############################
    ifprint('\n')
    if args.recheck: run_bgp_prefixes_checker()
    elif not args.nobgpcheck:
        if JSON_MODE: run_bgp_prefixes_checker(filename, logfilename, True)
        else: run_bgp_prefixes_checker(filename, logfilename)

    ifprint('\n ==> POSTCHECK COMPLETE !')

elif pre_post == "pre" and not args.recheck:

    ### BGP PREFIX CHECK DO NOT LOG IF RECHECK ################################
    ifprint('\n')
    if not args.nobgpcheck:
        if JSON_MODE and logfilename: run_bgp_prefixes_checker(filename, logfilename, True)
        elif JSON_MODE: run_bgp_prefixes_checker(filename, None, True)
        else: run_bgp_prefixes_checker(filename, logfilename)

    ifprint('\n ==> PRECHECK COMPLETE !')

if filename and os.path.exists(filename):
    ifprint(' ==> File %s created.'%(filename))
    try: send_me_email(subject = filename.replace('\\','/').split('/')[-1], file_name = filename)
    except: pass

if logfilename:
    ifprint(' ==> LOGFILE GENERATED: %s' % (logfilename))
    try: send_me_email(subject = logfilename.replace('\\','/').split('/')[-1], file_name = logfilename)
    except: pass

### JSON MODE PRINT DATA ######################################################
if pre_post == "post":
    json_print(prefile = precheck_file, postfile = postcheck_file, logfilename = logfilename)

if pre_post == "pre":
    json_print(prefile = filename, logfilename = logfilename)
############################################## END ################################################


