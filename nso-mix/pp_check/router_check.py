#!/usr/bin/python

###############################################################################
# File name: router_check                                                     #
# Author: Philippe Marcais (philippe.marcais@orange.com)                      #
#         Peter Nemec      (peter.nemec@orange.com)                           #
# Created: 06/01/2015                                                         #
# Updated: 23/Mar/2019 - custom filediff                                      #
#          25/Mar/2019 - added vrf huawei router type                         #
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
USERNAME        = os.environ['USER']

note_string = "DIFF('-' missing, '+' added, '!' different, '=' equal with problem)\n"
default_problem_list = [' DOWN', ' down','Down','Fail', 'FAIL', 'fail']
default_ignore_list  = [r' MET$', r' UTC$']

###############################################################################
#
# Generic list of commands for pre/post check ans slicers
#
###############################################################################

# IOS-XE is only for IPsec GW 
CMD_IOS_XE = [
            "show version",
            "show running-config",
            "show isis neighbors",
            "show mpls ldp neighbor",
            "show ip interface brief",
            "show ip route summary",
            "show crypto isakmp sa",
            "show crypto ipsec sa count",
            "show crypto eli"
            ]
CMD_IOS_XR = [
            "show version",
            "show running-config",
            "admin show run",
            "show interface brief",
            "show isis interface brief",
            "show isis neighbors",
            "show mpls ldp neighbor brief",
            "show mpls ldp interface brief",
            "show bgp sessions",
            "show route summary",
            "show rsvp  neighbors",
            "show pim neighbor",
            "show l2vpn xconnect group group1",
            "admin show platform",
            "show redundancy summary",
            "show processes cpu | utility head count 3",
            "show inventory",
            "show system verify report"
            ]
CMD_JUNOS = [
            "show system software",
            "show configuration",
            "show interfaces terse",
            "show isis adjacency",
            "show ldp session brief",
            "show ldp neighbor",
            "show bgp summary",
            "show rsvp neighbor",
            "show pim neighbors",
            "show l2vpn connections summary",
            "show chassis routing-engine",
            "show chassis fpc",
            "show chassis fpc pic-status",
            "show chassis power",
            "show system alarms"
        ]
CMD_VRF = [
            "display version",
            "display current-configuration",
            "display saved-configuration",
            "display startup",
            "display acl all",
            "display alarm all",
            "display interface brief",
            "display ip interface brief",
            "display ip routing-table",
            "display bgp routing-table"
            #,"display diagnostic-information"
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
            print('DEBUG:',retvalue)
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

# Find a section of text betwwen "cli" varaible from upper block and "prompt
def find_section(text, prompt):
    look_end = 0
    for index,item in enumerate(text):
        text[index] = item.rstrip()
        if (prompt+cli.rstrip()) in text[index]:    # beginning section found
            b_index = index
            look_end = 1                  # look for end of section now
            continue
        if look_end == 1:
            if prompt.rstrip() in text[index]:
                e_index = index
                look_end = 0

    return text[b_index:e_index]


def get_difference_string_from_string_or_list(old_string_or_list,new_string_or_list,problem_list = default_problem_list,ignore_list = default_ignore_list,print_equals = None,debug = None,note = True ):
    '''
    FUNCTION get_difference_string_from_string_or_list:
    INPUT PARAMETERS:
      - old_string_or_list - content of old file in string or list type
      - new_string_or_list - content of new file in string or list type
      - problem_list - list of regular expressions or strings which detects problems, even if files are equal
      - ignore_list - list of regular expressions or strings when line is ignored for file (string) comparison
      - print_equals - True/False prints all equal new file lines with '=' prefix , by default is False
      - debug - True/False, prints debug info to stdout, by default is False
      - note - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies

    The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    '=' for the same line, but with problem.
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''

    print_string = note_string if note else str()

    # make list from string if is not list already
    old_lines_unfiltered = old_string_or_list if type(old_string_or_list) == list else old_string_or_list.splitlines()
    new_lines_unfiltered = new_string_or_list if type(new_string_or_list) == list else new_string_or_list.splitlines()

    # make filtered-out list of lines from both files
    old_lines, new_lines = [], []
    for line in old_lines_unfiltered:
        ignore=False
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        if not ignore: old_lines.append(line)

    for line in new_lines_unfiltered:
        ignore=False
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        if not ignore: new_lines.append(line)

    del old_lines_unfiltered
    del new_lines_unfiltered

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

        while i >= 0 and j>=0:
            go, diff_sign, color, print_line = 'void', ' ', bcolors.WHITE, str()

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
                if print_equals: go, diff_sign, color, print_line= 'line_equals', '=', bcolors.WHITE, line
                else:            go, diff_sign, color, print_line= 'line_equals', '=', bcolors.WHITE, str()

                # In case of DOWN/FAIL write also equal values !!!
                for item in problem_list:
                    if (re.search(item,line)) != None: color, print_line = bcolors.RED, line

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # changed line
            elif first_line_word == first_old_line_word and not new_first_words[i] in added_lines:
                go, diff_sign, color, print_line = 'changed_line', '!', bcolors.YELLOW, line

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
                go, diff_sign, color, print_line = 'lost_line', '-',  bcolors.YELLOW, old_line

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
                    go, diff_sign, color, print_line = 'lost_line_on_end', '-',  bcolors.YELLOW, old_line

                    try:    j, old_line = next(enum_old_lines)
                    except: j, old_line = -1, str()
                else: print('!!! PARSING PROBLEM: ',j,old_line,' -- vs -- ',i,line,' !!!')

            if debug: print('####### %s  %s  %s  %s\n'%(go,color,diff_sign,print_line))
            if print_line: print_string=print_string+'%s  %s  %s%s\n'%(color,diff_sign,print_line,bcolors.ENDC)

    return print_string


##############################################################################
#
# BEGIN MAIN
#
##############################################################################

######## Parse program arguments #########

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
                    choices = ["ios-xr","ios-xe","junos","vrf"],
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

args = parser.parse_args()
if args.post: pre_post = 'post'
else: pre_post = 'pre'

####### Set USERNAME if needed

if args.username != None:
    USERNAME = args.username

####### Figure out type of router OS

if args.router_type == None:
    router_type = find_router_type(args.device)
else:
    router_type = args.router_type
    print('Forced router_type:',router_type)

######## Create logs directory if not existing  ######### 

if not os.path.exists('./logs'):
    os.makedirs('./logs')

####### Find necessary pre and post check files if needed 

if args.precheck_file != None:
    if not os.path.isfile(args.precheck_file):
        print(bcolors.FAIL + " ... Can't find precheck file: %s" + bcolors.ENDC) \
           % args.precheck_file
        sys.exit()
else:
    if pre_post == 'post':
        list_precheck_files = glob.glob("./logs/" + args.device + '*' + 'pre')
        if len(list_precheck_files) == 0:
            print(bcolors.FAIL + " ... Can't find any precheck file: %s " + bcolors.ENDC)
            sys.exit()
        most_recent_precheck = list_precheck_files[0]
        for item in list_precheck_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_precheck)):
                most_recent_precheck = item
        args.precheck_file = most_recent_precheck

######## Find command list file (optional)

if args.cmd_file != None:
    if not os.path.isfile(args.cmd_file):
        print(bcolors.FAIL + " ... Can't find command file: %s " + bcolors.ENDC) \
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

############# Starting pre or post check

PASSWORD = getpass.getpass("TACACS password: ")

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

elif router_type == "vrf":
    CMD = CMD_VRF
    DEVICE_PROMPT = '<' + args.device.upper() + '>'
    TERM_LEN_0 = "screen-length 0 temporary\n"     #"screen-length disable\n"
    EXIT = "quit\n"

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

    for item in CMD:
        output = ''
        chan.send(item + '\n')
        print " ... %s" % item
        # chan.send('\n')
        output = ssh_read_until(chan,DEVICE_PROMPT)
        fp.write(output)                                            

except (socket.timeout, paramiko.AuthenticationException) as e:
    print(bcolors.FAIL + " ... Connection closed: %s " + bcolors.ENDC % (e))
    sys.exit()
finally:
    client.close()

print " ... Collection is completed\n"
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
    text1_lines = fp1.readlines()
    text2_lines = fp2.readlines()

    print('\nNOTE: ' + note_string)

    for cli in CMD:
        # set up correct slicing to remove irrelevant end of line info
        if (cli in IOS_XR_SLICE) and (not args.noslice):
            slicer = IOS_XR_SLICE[cli]
        else:
            slicer = 100

        # Looking for relevant section in precheck file
        precheck_section = find_section(text1_lines, DEVICE_PROMPT)
        for index, item in enumerate(precheck_section):
            precheck_section[index] =  precheck_section[index][:slicer]

        #Looking for relevant section in postcheck file
        postcheck_section = find_section(text2_lines, DEVICE_PROMPT)
        for index, item in enumerate(postcheck_section):
            postcheck_section[index] = postcheck_section[index][:slicer]

        print(bcolors.BOLD + '\n' + cli + bcolors.ENDC)
        print(get_difference_string_from_string_or_list(precheck_section,postcheck_section,note=False))

    fp1.close()
    fp2.close()
    print '\n ==> POSTCHECK COMPLETE !'

elif pre_post == "pre":
    subprocess.call(['ls','-l',filename])
    print '\n ==> PRECHECK COMPLETE !'

############################################## END ################################################


