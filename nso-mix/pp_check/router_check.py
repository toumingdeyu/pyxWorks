#!/usr/bin/python

###############################################################################
# File name: router_check                                                     #
# Author: Philippe Marcais (philippe.marcais@orange.com)                      #
#         Peter Nemec      (peter.nemec@orange.com)                           #
# Created: 06/01/2015                                                         #
# Updated: 23/Mar/2019 -added new custom filediff                             #
#          25/Mar/2019 -added vrp huawei router type, old/new filediff method #
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
HELP             = "\nTry 'router_check.py --help' for more information\n"
SNMP_COMMUNITY          = 'otauB9v1kYRO'
PLATFORM_DESCR_XR       = 'Cisco IOS XR Software'
PLATFORM_DESCR_IOS      = 'Cisco IOS Software'
PLATFORM_DESCR_JUNOS    = 'Juniper Networks'
PLATFORM_DESCR_CRS      = 'Cisco IOS XR Software (Cisco CRS'
PLATFORM_DESCR_NCS      = 'Cisco IOS XR Software (Cisco NCS'
PLATFORM_DESCR_ASR9K    = 'Cisco IOS XR Software (Cisco ASR9K'
PLATFORM_DESCR_MX2020   = 'Juniper Networks, Inc. mx2020'
UNKNOW_HOST     = 'Name or service not known'
TIMEOUT         = 60
try:    PASSWORD        = os.environ['PASS']
except: PASSWORD        = None
try:    USERNAME        = os.environ['USER']
except: USERNAME        = None

note_ndiff_string  = "ndiff( %s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (bcolors.RED,bcolors.GREEN,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_ndiff1_string = "ndiff1(%s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (bcolors.RED,bcolors.YELLOW,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_ndiff2_string = "ndiff2(%s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s'=' equal%s)\n" % \
    (bcolors.RED,bcolors.YELLOW,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_new1_string   = "new1(  %s'-' missed, %s'+' added, %s'!' difference,    %s' ' equal%s)\n" % \
    (bcolors.RED,bcolors.YELLOW,bcolors.YELLOW,bcolors.GREY,bcolors.ENDC )
note_new2_string   = "new2(  %s'-' missed, %s'+' added, %s'!' difference,    %s'=' equal%s)\n" % \
    (bcolors.RED,bcolors.YELLOW,bcolors.YELLOW,bcolors.GREY,bcolors.ENDC )

default_problemline_list = []
default_ignoreline_list  = [r' MET$', r' UTC$']
default_linefilter_list  = []
default_compare_columns  = []



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
# 4-linefilter_list
# 5-compare_columns
# 6-printall

# IOS-XE is only for IPsec GW 
CMD_IOS_XE = [
            ("show version",           'ndiff1', ['uptime','Uptime'], [], [], [], False),
            ("show running-config",    'ndiff1'),
            ("show isis neighbors",    'new1', [], ['DOWN'], [], [0,1,2,3,4], False),
            ("show mpls ldp neighbor", 'new1', ['Up time:'], [], [], [0,1,2,3,5], False ),
            ("show ip interface brief",'new1', [], [], [], [], False ),
#             "show ip route summary",
#             "show crypto isakmp sa",
#             "show crypto ipsec sa count",
#             "show crypto eli",
#             'show interfaces | in (^[A-Z].*|minute|second|Last input)'
             ]
CMD_IOS_XR = [
            ("show version",'ndiff1', ['uptime','Uptime'], [], [], [], False),
            ("show running-config",'ndiff1'),
            ("admin show run",'ndiff1'),
            ("show interface brief",'new1', [], [], [], [], False ),
            ("show isis interface brief",'ndiff1',[], [], [], [], False),
            ("show isis neighbors", "new1", [], ['Down'], [], [0,1,2,3], False),
#             "show mpls ldp neighbor brief",
#             "show mpls ldp interface brief",
#             "show bgp sessions",
#             "show route summary",
#             "show rsvp  neighbors",
#             "show pim neighbor",
#             "show l2vpn xconnect group group1",
#             "admin show platform",
#             "show redundancy summary",
#             "show processes cpu | utility head count 3",
#             "show inventory",
#             "show system verify report",
#             "show interfaces | in \"^[A-Z].*|minute|second|Last input\""
            ]
CMD_JUNOS = [
            ("show system software",'ndiff1', ['uptime','Uptime'], [], [], [], False),
            ("show configuration","ndiff1"),
            #"show interfaces terse",
            ("show isis adjacency","new1", [], ['DOWN'], [], [0,1,2,3], False),
#             "show ldp session brief",
#             "show ldp neighbor",
#             "show bgp summary",
#             "show rsvp neighbor",
#             "show pim neighbors",
#             "show l2vpn connections summary",
#             "show chassis routing-engine",
#             "show chassis fpc",
#             "show chassis fpc pic-status",
#             "show chassis power",
#             "show system alarms",
#             'show interfaces detail | match "Physical interface|Last flapped| bps"'
            ]
CMD_VRP = [
            ("display version",'ndiff1', ['uptime','Uptime'], [], [], [], False),
            #"display inventory",
            ("display current-configuration",'ndiff1'),
            ("display isis interface",'new1',[], [], [], [], False),
            ("display isis peer",'new1', [], ['Down'], [], [0,1,2,3], False),
#             "display saved-configuration",
#             "display startup",
#             "display acl all",
#             "display alarm all",
#             "display interface brief",
#             "display ip interface brief",
#             "display ip routing-table",
#             "display bgp routing-table",
#             'display interface | include (Description|current state|minutes|bandwidth utilization|Last physical)'
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


# detect device prompt
def ssh_detect_prompt(chan, debug = False):
    output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
    chan.send('\t \n\n')
    while not (last_line and last_but_one_line and last_line == last_but_one_line):
        if debug: print('FIND_PROMPT:',last_but_one_line,last_line)
        buff = chan.recv(9999)
        output += buff.replace('\r','').replace('\x07','').replace('\x08','').replace('\x1b[K','').replace('\n{master}\n','')
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
        output += buff.replace('\r','').replace('\x07','').replace('\x08','').replace('\x1b[K','').replace('\n{master}\n','')
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
            if 'iosxr-' in output: router_os = 'ios-xr'
            elif 'Cisco IOS-XE software' in output: router_os = 'ios-xe'
            elif 'JUNOS OS' in output: router_os = 'junos'

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.FAIL + " ... Connection closed: %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()
    return router_os


# Find OS running on a router with a snmp request
def find_router_type(host):
    snmp_req = "snmpget -v1 -c " + SNMP_COMMUNITY + " -t 5 " + host + " sysDescr.0"
    return_stream = os.popen(snmp_req)
    retvalue = return_stream.readline()
    if len(retvalue) == 0:
        print("\nCannot connect to %s (unknow host)" % (host))
        sys.exit()
    else:
        if PLATFORM_DESCR_XR in retvalue:
            router_os = 'ios-xr'
        elif PLATFORM_DESCR_IOS in retvalue:
            router_os = 'ios-xe'
        elif PLATFORM_DESCR_JUNOS in retvalue:
            router_os = 'junos'
        else:
            print("\nCannot find recognizable OS in %s" % (retvalue))
            sys.exit()
    return router_os

# Find router platform type with a snmp request
def find_platform_type(host):
    snmp_req = "snmpget -v1 -c " + SNMP_COMMUNITY + " -t 5 " + host + " sysDescr.0"
    return_stream = os.popen(snmp_req)
    retvalue = return_stream.readline()
    if len(retvalue) == 0:
        print("\nCannot connect to %s (unknow host)" % (host))
        sys.exit()
    else:
        if PLATFORM_DESCR_CRS in retvalue:
            platform_type = 'cisco-crs'
        elif PLATFORM_DESCR_NCS in retvalue:
            platform_type = 'cisco-ncs'
        elif PLATFORM_DESCR_AR9K in retvalue:
            platform_type = 'cisco-asr9k'
        elif PLATFORM_DESCR_MX2020 in retvalue:
            platform_type = 'juniper-mx2020'
        else:
            print("\nCannot find recognizable OS in %s" % (retvalue))
            sys.exit()
    return platform_type


def ssh_read_until(channel,prompt):
    output = ''
    while not output.endswith(prompt):
        buff = chan.recv(9999)
        output += buff
    return output

# Find a section of text betwwen "cli" variable from upper block and "prompt
def find_section(text, prompt,cli_index, cli):
    look_end = 0
    b_index, e_index, c_index = None, None, -1
    for index,item in enumerate(text):
        if prompt.rstrip() in text[index].rstrip():
            c_index = c_index+1
            # beginning section found
            # + workarround for long commands shortened in router echoed line
            if (prompt+cli.rstrip()) in text[index].rstrip() or c_index == cli_index:
                b_index = index
                look_end = 1                       # look for end of section now
                continue
            if look_end == 1:
                if prompt.rstrip() in text[index]:
                    e_index = index
                    look_end = 0
    if not(b_index and e_index):
        print("%sSection '%s' could not be found and compared!%s" % \
              (bcolors.MAGENTA,prompt+cli.rstrip(),bcolors.ENDC))
        return str()
    return text[b_index:e_index]


def get_difference_string_from_string_or_list(
    old_string_or_list, \
    new_string_or_list, \
    diff_method = 'new1', \
    ignore_list = default_ignoreline_list, \
    problem_list = default_problemline_list, \
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
      - diff_method - ndiff, ndiff1, ndiff2, new1, new2
      - ignore_list - list of regular expressions or strings when line is ignored for file (string) comparison
      - problem_list - list of regular expressions or strings which detects problems, even if files are equal
      - linefilter_list - list of regular expressions which filters each line (regexp results per line comparison)
      - compare_columns - list of columns which are intended to be different , other columns in line are ignored
      - print_equallines - True/False prints all equal new file lines with '=' prefix , by default is False
      - debug - True/False, prints debug info to stdout, by default is False
      - note - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies

    NEW/NEW2 FORMAT: The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    '=' for the same line, but with problem. (valid for new2 format)
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''
    print_string = str()
    if note:
       print_string = "DIFF_METHOD: "
       if diff_method   == 'new1':   print_string += note_new1_string
       elif diff_method == 'new2':   print_string += note_new2_string
       elif diff_method == 'ndiff1': print_string += note_ndiff1_string
       elif diff_method == 'ndiff2': print_string += note_ndiff2_string
       elif diff_method == 'ndiff':  print_string += note_ndiff_string

    # make list from string if is not list already
    old_lines_unfiltered = old_string_or_list if type(old_string_or_list) == list else old_string_or_list.splitlines()
    new_lines_unfiltered = new_string_or_list if type(new_string_or_list) == list else new_string_or_list.splitlines()

    # make filtered-out list of lines from both files
    old_lines, new_lines = [], []
    old_linefiltered_lines, new_linefiltered_lines = [], []
    old_split_lines, new_split_lines = [], []

    for line in old_lines_unfiltered:
        ignore, linefiltered_line, split_line = False, line, str()
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        for linefilter_item in linefilter_list:
            if (re.search(linefilter_item,line)) != None:
                linefiltered_line = re.findall(linefilter_item,line)[0]
        for split_column in compare_columns:
           try: temp_column = line.split()[split_column]
           except: temp_column = str()
           split_line += ' ' + temp_column
        if not ignore:
            old_lines.append(line)
            old_linefiltered_lines.append(linefiltered_line)
            old_split_lines.append(split_line)

    for line in new_lines_unfiltered:
        ignore, linefiltered_line, split_line = False, line, str()
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        for linefilter_item in linefilter_list:
            if (re.search(linefilter_item,line)) != None:
                linefiltered_line = re.findall(linefilter_item,line)[0]
        for split_column in compare_columns:
           try: temp_column = line.split()[split_column]
           except: temp_column = str()
           split_line += ' ' + temp_column
        if not ignore:
            new_lines.append(line);
            new_linefiltered_lines.append(linefiltered_line)
            new_split_lines.append(split_line)

    del old_lines_unfiltered
    del new_lines_unfiltered

    # NDIFF COMPARISON METHOD
    if diff_method == 'ndiff':
        diff = difflib.ndiff(old_lines, new_lines)
        for line in list(diff):
            try:    first_chars = line.strip()[0]+line.strip()[1]
            except: first_chars = str()
            if '+ ' == first_chars: print_string += bcolors.GREEN + line + bcolors.ENDC + '\n'
            elif '- ' == first_chars: print_string += bcolors.RED + line + bcolors.ENDC + '\n'
            elif '! ' == first_chars: print_string += bcolors.YELLOW + line + bcolors.ENDC + '\n'
            elif '? ' == first_chars or first_chars == str(): pass
            elif print_equallines: print_string += bcolors.GREY + line + bcolors.ENDC + '\n'
        return print_string

    # NEW COMPARISON METHOD CONTINUE
    enum_old_lines = enumerate(old_lines)
    enum_new_lines = enumerate(new_lines)

    if old_lines and new_lines:
        new_first_words = [line.split(' ')[0] for line in new_lines]
        old_first_words = [line.split(' ')[0] for line in old_lines]
        if debug: print('11111 :',old_first_words,new_first_words)

        lost_lines = [item for item in old_first_words if item not in new_first_words]
        added_lines = [item for item in new_first_words if item not in old_first_words]
        if debug: print('----- :',lost_lines)
        if debug: print('+++++ :',added_lines)

        try:    j, old_line = next(enum_old_lines)
        except: j, old_line = -1, str()

        try:    i, line = next(enum_new_lines)
        except: i, line = -1, str()

        print_old_line=None
        while i >= 0 and j>=0:
            go, diff_sign, color, print_line = 'void', ' ', bcolors.GREY, str()

            # void new lines
            if not line.strip():
                while len(line.strip()) == 0 and i >= 0:
                    try:    i, line = next(enum_new_lines)
                    except: i, line = -1, str()

            # void old lines
            if not old_line.strip():
                while len(old_line.strip()) == 0 and j >= 0:
                    try:    j, old_line = next(enum_old_lines)
                    except: j, old_line = -1, str()

            # auxiliary first words
            try: first_line_word = line.strip().split()[0]
            except: first_line_word = str()
            try: first_old_line_word = old_line.strip().split()[0]
            except: first_old_line_word = str()

            # if again - lines are the same
            if line.strip() == old_line.strip():
                diff_sign = '=' if diff_method == 'new2' or diff_method == 'ndiff2' else ' '
                if print_equallines: go, color, print_line= 'line_equals', bcolors.GREY, line
                else:            go, color, print_line= 'line_equals', bcolors.GREY, str()

                # In case of DOWN/FAIL write also equal values !!!
                for item in problem_list:
                    if (re.search(item,line)) != None: color, print_line = bcolors.RED, line

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # changed line
            elif first_line_word == first_old_line_word and not new_first_words[i] in added_lines:
                if debug: print('SPLIT:' + new_split_lines[i] + ', LINEFILTER:' + new_linefiltered_lines[i])
                # filter-out not-important changes by SPLIT or LINEFILTER
                if old_linefiltered_lines[j] and new_linefiltered_lines[i] and \
                    new_linefiltered_lines[i] == old_linefiltered_lines[j]:
                    if print_equallines: go, color, print_line= 'line_equals', bcolors.GREY, line
                    else:            go, color, print_line= 'line_equals', bcolors.GREY, str()
                elif old_split_lines[j] and new_split_lines[i] and old_split_lines[j] == new_split_lines[i]:
                    if print_equallines: go, color, print_line= 'line_equals', bcolors.GREY, line
                    else:            go, color, print_line= 'line_equals', bcolors.GREY, str()
                else:
                    go, diff_sign, color, print_line = 'changed_line', '!', bcolors.YELLOW, line
                    print_old_line = old_line

                    for item in problem_list:
                        if (re.search(item,line)) != None: color = bcolors.RED

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # added line
            elif first_line_word in added_lines:
                go, diff_sign, color, print_line = 'added_line','+',  bcolors.YELLOW, line

                for item in problem_list:
                    if (re.search(item,line)) != None: color = bcolors.RED

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # lost line
            elif not first_line_word in lost_lines and old_line.strip():
                go, diff_sign, color, print_line = 'lost_line', '-',  bcolors.RED, old_line

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()
            else:
                # added line on the end
                if first_line_word and not first_old_line_word:
                    go, diff_sign, color, print_line = 'added_line_on_end','+',  bcolors.YELLOW, line

                    for item in problem_list:
                        if (re.search(item,line)) != None: color = bcolors.RED

                    try:    i, line = next(enum_new_lines)
                    except: i, line = -1, str()
                # lost line on the end
                elif not first_line_word and first_old_line_word:
                    go, diff_sign, color, print_line = 'lost_line_on_end', '-',  bcolors.RED, old_line

                    try:    j, old_line = next(enum_old_lines)
                    except: j, old_line = -1, str()
                else: print('!!! PARSING PROBLEM: ',j,old_line,' -- vs -- ',i,line,' !!!')

            if debug: print('####### %s  %s  %s  %s\n'%(go,color,diff_sign,print_line))
            if print_line:
                if not print_old_line:
                    print_string=print_string+'%s  %s  %s%s\n'%(color,diff_sign,print_line.rstrip(),bcolors.ENDC)
                else:
                    if diff_method == 'ndiff1' or diff_method == 'ndiff2':
                        print_string=print_string+'%s  %s  %s%s\n'%(bcolors.RED,'-',print_old_line.rstrip(),bcolors.ENDC)
                        print_string=print_string+'%s  %s  %s%s\n'%(bcolors.GREEN,'+',print_line.rstrip(),bcolors.ENDC)
                    else:
                        print_string=print_string+'%s  %s  %s%s\n'%(color,diff_sign,print_line.rstrip(),bcolors.ENDC)
                    print_old_line=None
    return print_string


def print_cmd_list(CMD):
    if str(args.cmdlist) == 'list':
        print("\nCOMMAND LIST:")
        for cli_index, cli_items in enumerate(CMD):
            print("  %2d.    %s" % (cli_index,cli_items[0]))
        print('\n')
        sys.exit(0)

##############################################################################
#
# BEGIN MAIN
#
##############################################################################

######## Parse program arguments #########
if len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
    print(('DIFF_FORMATS:\n  %s  %s  %s  %s  %s') % (note_ndiff_string, \
        note_ndiff1_string,note_ndiff2_string,note_new1_string,note_new2_string))

parser = argparse.ArgumentParser(
                description = "Script to perform Pre and Post router check",
                epilog = "e.g: ./router_check.py --device ASHTR2 --post\n")

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
parser.add_argument("--post", action = "store_true",
                    help = "run Postcheck")
parser.add_argument("--file",
                    action = 'store', dest = "precheck_file",
                    help = "run postcheck against a specific precheck file")
parser.add_argument("--cmd", action = 'store', dest = "cmd_file",
                    help = "specify a file with a list of commands to execute")
parser.add_argument("--user",
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
                    help = "recheck last diff pre/post files per inserted device")
parser.add_argument("--cmdlist",
                    action = "store", dest = 'cmdlist', default = '',
                    help = "<list> - print command list / <nr of command> - choose one command from command list for post comparison")
# parser.add_argument("--diff", action = "store", dest = "diff", \
#                     choices = ['old','ndiff','ndiff1','ndiff2','new1','new2'], \
#                     default = 'new1', \
#                     help = "more available diff formats" )
args = parser.parse_args()
if args.post: pre_post = 'post'
else: pre_post = 'pre'

####### Set USERNAME if needed
if args.username != None: USERNAME = args.username

####### Figure out type of router OS
if not args.router_type:
    #router_type = find_router_type(args.device)
    router_type = detect_router_by_ssh(debug = False)
    print('DETECTED ROUTER_TYPE: ' + router_type)
else:
    router_type = args.router_type
    print('FORCED ROUTER_TYPE: ' + router_type)

######## Create logs directory if not existing  ######### 
if not os.path.exists('./logs'):
    os.makedirs('./logs')

####### Find necessary pre and post check files if needed 
if args.precheck_file != None:
    if not os.path.isfile(args.precheck_file):
        print(bcolors.MAGENTA + " ... Can't find precheck file: %s" + bcolors.ENDC) \
           % args.precheck_file
        sys.exit()
else:
    if pre_post == 'post':
        list_precheck_files = glob.glob("./logs/" + args.device + '*' + 'pre')
        if len(list_precheck_files) == 0:
            print(bcolors.MAGENTA + " ... Can't find any precheck file. %s " + bcolors.ENDC)
            sys.exit()
        most_recent_precheck = list_precheck_files[0]
        for item in list_precheck_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_precheck)):
                most_recent_precheck = item
        args.precheck_file = most_recent_precheck
        precheck_file = most_recent_precheck

# find last existing postcheck file
if args.recheck:
    list_postcheck_files = glob.glob("./logs/" + args.device + '*' + 'post')
    if len(list_postcheck_files) == 0:
        print(bcolors.MAGENTA + " ... Can't find any postcheck file. %s " + bcolors.ENDC)
        sys.exit()
    most_recent_postcheck = list_postcheck_files[0]
    for item in list_postcheck_files:
        filecreation = os.path.getctime(item)
        if filecreation > (os.path.getctime(most_recent_postcheck)):
            most_recent_postcheck = item
    postcheck_file = most_recent_postcheck

else:
    ######## Find command list file (optional)
    if args.cmd_file != None:
        if not os.path.isfile(args.cmd_file):
            print(bcolors.MAGENTA + " ... Can't find command file: %s " + bcolors.ENDC) \
                    % args.cmd_file
            sys.exit()
        else:
            list_cmd = ['']
            num_lines = sum(1 for line in open(args.cmd_file))
            fp_cmd = open(args.cmd_file,"r")
            for index in range(0, num_lines):
                list_cmd.append(fp_cmd.readline())
            fp_cmd.close

            # clean up the list of commands - Remove empty line in file
            if '' in list_cmd:
                list_cmd.remove('')
            if '\n' in list_cmd:
                list_cmd.remove('\n')
            # clean up the list of commands - Remove trailling \n
            for index, line in enumerate(list_cmd):
                list_cmd[index] = list_cmd[index].rstrip('\n')

            if router_type == 'ios-xe':
                CMD_IOS_XE = list_cmd
            elif router_type == 'ios-xr':
                CMD_IOS_XR = list_cmd

    if str(args.cmdlist) != 'list':
        ############# Starting pre or post check
        if not PASSWORD: PASSWORD = getpass.getpass("TACACS password: ")

        if pre_post == "post":
            print " ==> STARTING POSTCHECK ..."
        elif pre_post == "pre":
            print " ==> STARTING PRECHECK ..."

        print " ... Openning %s check file to collect output" %( pre_post )

        filename_prefix = "./logs/" + args.device
        filename_suffix = pre_post
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,now.second,filename_suffix)

        if pre_post == "post":
            postcheck_file = filename
            precheck_file = args.precheck_file

        fp = open(filename,"w")

# Collect pre/post check information
if router_type == "ios-xe":
    CMD = CMD_IOS_XE
    DEVICE_PROMPT = args.device.upper() + '#'
    TERM_LEN_0 = "terminal length 0\n"
    EXIT = "exit\n"

elif router_type == "ios-xr":
    CMD = CMD_IOS_XR
    DEVICE_PROMPT = args.device.upper() + '#'
    TERM_LEN_0 = "terminal length 0\n"
    EXIT = "exit\n"

elif router_type == "junos":
    CMD = CMD_JUNOS
    DEVICE_PROMPT = USERNAME + '@' + args.device.upper() + '> ' # !! Need the space after >
    TERM_LEN_0 = "set cli screen-length 0\n"
    EXIT = "exit\n"

elif router_type == "vrp":
    CMD = CMD_VRP
    DEVICE_PROMPT = '<' + args.device.upper() + '>'
    TERM_LEN_0 = "screen-length 0 temporary\n"     #"screen-length disable\n"
    EXIT = "quit\n"

print_cmd_list(CMD)

if not args.recheck:
    # SSH (default)
    print " ... Connecting (SSH) to %s" % args.device
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(args.device, username=USERNAME, password=PASSWORD)
        chan = client.invoke_shell()
        chan.settimeout(TIMEOUT)
        while not chan.recv_ready():
            time.sleep(1)
        output = ssh_read_until(chan,DEVICE_PROMPT)
        chan.send(TERM_LEN_0 + '\n')
        output = ssh_read_until(chan,DEVICE_PROMPT)
        # router prompt needed as file header
        chan.send('\n')
        output = ssh_read_until(chan,DEVICE_PROMPT)
        fp.write(output)

        for cli_items in CMD:
            item = cli_items[0]
            output = ''
            chan.send(item + '\n')
            print " ... %s" % item
            # chan.send('\n')
            output = ssh_read_until(chan,DEVICE_PROMPT)
            fp.write(output)

    except (socket.timeout, paramiko.AuthenticationException) as e:
        print(bcolors.FAIL + " ... Connection closed. %s " % (e) + bcolors.ENDC )
        sys.exit()
    finally:
        client.close()

    print " ... Collection is completed\n"
    fp.flush()
    fp.close()

# Post Check treatment 
if pre_post == "post":
    print " ==> COMPARING PRECHECK & POSTCHECK ...\n"

    # Opening pre and post check files and loading content for processing
    print "\nPrecheck file:"
    subprocess.call(['ls','-l',precheck_file])
    print "\nPostcheck file:"
    subprocess.call(['ls','-l',postcheck_file])
    fp1 = open(precheck_file,"r")
    fp2 = open(postcheck_file,"r")

    # routers sometimes returns windows lines ('\r\n')
    # readlines() splits by default '\n' only and '\r'stays in lines ('\r'+text+'\r\n' )
    text1_lines = fp1.read().replace('\r','').splitlines()
    text2_lines = fp2.read().replace('\r','').splitlines()

    # close file descriptors for sure
    fp1.close()
    fp2.close()

    # run only chosen command from list by its number
    if args.cmdlist != 'listall':
        try: cmd_index = int(args.cmdlist)
        except: cmd_index = -1
        for cli_index, cli_items in enumerate(CMD):
            if cli_index == cmd_index:
                CMD = [cli_items]
                break

    # run commands tgrough CMD list
    for cli_index, cli_items in enumerate(CMD):
        cli = cli_items[0]

        # old comparison method
        if args.olddiff:
            # set up correct slicing to remove irrelevant end of line info
            if (cli in IOS_XR_SLICE) and (not args.noslice):
                slicer = IOS_XR_SLICE[cli]
            else:
                slicer = 100
            # Looking for relevant section in precheck file
            precheck_section = find_section(text1_lines, DEVICE_PROMPT, cli_index, cli)
            for index, item in enumerate(precheck_section):
                precheck_section[index] =  precheck_section[index][:slicer]

            #Looking for relevant section in postcheck file
            postcheck_section = find_section(text2_lines, DEVICE_PROMPT, cli_index, cli)
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
                print(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                for index, line in enumerate(diff_print_pre):
                    print bcolors.GREEN + '\t' +  diff_print_pre[index] + bcolors.ENDC
                for index, line in enumerate(diff_print_post):
                    print bcolors.RED + '\t' +  diff_print_post[index] + bcolors.ENDC
        else:
            # unpack cli list
            try: cli_diff_method = cli_items[1]
            except: cli_diff_method = 'ndiff1'

            try: cli_ignore_list = cli_items[2]
            except: cli_ignore_list = []

            try: cli_problemline_list = cli_items[3]
            except: cli_problemline_list = []

            try: cli_linefilter_list = cli_items[4]
            except: cli_linefilter_list = []

            try: cli_compare_columns = cli_items[5]
            except: cli_compare_columns = []

            if args.printall:
                cli_printall = args.printall
            else:
                try: cli_printall = cli_items[6]
                except: cli_printall = False

            # Looking for relevant section in precheck file
            precheck_section = find_section(text1_lines, DEVICE_PROMPT,cli_index, cli)

            #Looking for relevant section in postcheck file
            postcheck_section = find_section(text2_lines, DEVICE_PROMPT,cli_index, cli)

            if precheck_section and postcheck_section:
                print(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
                diff_result = get_difference_string_from_string_or_list( \
                    precheck_section,postcheck_section, \
                    diff_method = cli_diff_method, \
                    ignore_list = default_ignoreline_list + cli_ignore_list, \
                    problem_list = cli_problemline_list, \
                    linefilter_list = cli_linefilter_list, \
                    compare_columns = cli_compare_columns, \
                    print_equallines = cli_printall, \
                    note=False)
                if len(diff_result) == 0: print(bcolors.GREY + 'OK' + bcolors.ENDC)
                else: print(diff_result)
    print '\n ==> POSTCHECK COMPLETE !'

elif pre_post == "pre" and not args.recheck:
    subprocess.call(['ls','-l',filename])
    print '\n ==> PRECHECK COMPLETE !'

############################################## END ################################################


