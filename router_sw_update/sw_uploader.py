#!/usr/bin/python

###!/usr/bin/python36


import sys, os, io, paramiko, json, copy, html, logging
import traceback
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
import signal

import cgi
#import cgitb; cgitb.enable()
import requests
from mako.template import Template
from mako.lookup import TemplateLookup

###############################################################################



class CGI_CLI(object):
    """
    class CGI_handle - Simple statis class for handling CGI parameters and
                       clean (debug) printing to HTML/CLI
    INTERFACE FUNCTIONS:
    CGI_CLI.init_cgi() - init CGI_CLI class
    CGI_CLI.print_args(), CGI_CLI.print_env() - debug printing
    CGI_CLI.uprint() - printing CLI/HTML text
    CGI_CLI.formprint() - printing of HTML forms
    """
    # import collections, cgi, six
    # import cgitb; cgitb.enable()

    ### TO BE PLACED - IN BODY ###
    JS_RELOAD_BUTTON = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""

    STOP_APPLICATION_BUTTON = '<form action = "/cgi-bin/%s" target="_blank"><p hidden><input type="checkbox" name="pidtokill" value="%s" checked="checked"></p><input type="submit" name="submit" value="STOP"></form>' \
        % (sys.argv[0].replace('\\','/').split('/')[-1].strip() if '/' or '\\' in sys.argv[0] else sys.argv[0],str(os.getpid()))

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
                            help = "forced to insert router password interactively getpass.getpass()")
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "Target router to access. (Optionable device list separated ba comma, i.e. --device DEVICE1,DEVICE2)")
        parser.add_argument("--sw_release",
                            action = "store", dest = 'sw_release',
                            default = str(),
                            help = "sw release number with or without dots, i.e. 653 or 6.5.3, or alternatively sw release filename")
        parser.add_argument("--file_types",
                            action = "store", dest = 'sw_files',
                            default = str(),
                            help = "--file_types OTI.tar,SMU,pkg,bin , one file type or list of file types separated by ',' without any space. NOTE: This is intended as file-name filter in sw_release directory.")
        parser.add_argument("--files",
                            action = "store", dest = 'additional_files_to_copy',
                            default = str(),
                            help = "--files absolute_path_to_file_with_filename(s), one file or list of files separated by ',' without any space. NOTE: Independent on sw_release.")
        parser.add_argument("--check_only",
                            action = 'store_true', dest = "check_device_sw_files_only",
                            default = None,
                            help = "check existing device sw release files only, do not copy new tar files")
        parser.add_argument("--backup_configs",
                            action = 'store_true', dest = "backup_configs_to_device_disk",
                            default = None,
                            help = "backup configs to device hdd")
        parser.add_argument("--force",
                           action = 'store_true', dest = "force_rewrite_sw_files_on_device",
                           default = None,
                           help = "force rewrite sw release files on device disk")
        parser.add_argument("--delete",
                            action = 'store_true', dest = "delete_device_sw_files_on_end",
                            default = None,
                            help = "delete device sw release files on end after sw upgrade")
        parser.add_argument("--no_backup_re",
                            action = 'store_true', dest = "ignore_missing_backup_re_on_junos",
                            default = None,
                            help = "ignore missing backup re on junos")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
        parser.add_argument("--timestamps",
                            action = "store_true", dest = 'timestamps',
                            default = None,
                            help = "print all lines with timestamps")
        parser.add_argument("--enable_scp",
                            action = "store_true", dest = 'enable_device_scp_before_copying',
                            default = None,
                            help = "enable device scp before copy")
        parser.add_argument("--disable_scp",
                            action = "store_true", dest = 'disable_device_scp_after_copying',
                            default = None,
                            help = "disable device scp after copy")
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():
        if CGI_CLI.timestamp:
            CGI_CLI.uprint('END.\n', no_printall = not CGI_CLI.printall, tag = 'debug')
        CGI_CLI.html_selflink()
        if CGI_CLI.cgi_active:
            CGI_CLI.print_chunk("</body></html>",
                ommit_logging = True, printall = True)

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(chunked = None, css_style = None, newline = None, \
        timestamp = None):
        """
        """
        try: CGI_CLI.sys_stdout_encoding = sys.stdout.encoding
        except: CGI_CLI.sys_stdout_encoding = None
        if not CGI_CLI.sys_stdout_encoding: CGI_CLI.sys_stdout_encoding = 'UTF-8'
        CGI_CLI.result_tag = 'h3'
        CGI_CLI.result_list = []
        CGI_CLI.self_buttons = ['OK','STOP']
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.http_status = 200
        CGI_CLI.http_status_text = 'OK'
        CGI_CLI.chunked = chunked
        CGI_CLI.timestamp = timestamp
        CGI_CLI.CSS_STYLE = css_style if css_style else str()
        CGI_CLI.cgi_active = None
        CGI_CLI.printall = None
        CGI_CLI.initialized = True
        getpass_done = None
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), str(), str(), str()
        form, CGI_CLI.data = collections.OrderedDict(), collections.OrderedDict()
        CGI_CLI.logfilename = None
        try: form = cgi.FieldStorage()
        except: pass
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["username","password"]:
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
            if variable == "printall": CGI_CLI.printall = True

            ### SET CHUNKED MODE BY CGI #######################################
            if variable == "chunked_mode":
                if not value: CGI_CLI.chunked = False
                elif value: CGI_CLI.chunked = True
                try:
                    if value.upper() in ['DISABLE','DISABLED','NO','FALSE','NONE']:
                        CGI_CLI.chunked_mode = False
                    elif value.upper() in ['ENABLE','ENABLED','YES','TRUE','ON']:
                        CGI_CLI.chunked_mode = True
                except: pass

        ### TO BE PLACED - BEFORE HEADER ######################################
        CGI_CLI.newline = '\r\n' if not newline else newline
        CGI_CLI.chunked_transfer_encoding_line = \
            "Transfer-Encoding: chunked%s" % (CGI_CLI.newline) if CGI_CLI.chunked else str()
        ### HTTP/1.1 ???
        CGI_CLI.status_line = \
            "Status: %s %s%s" % (CGI_CLI.http_status, CGI_CLI.http_status_text, CGI_CLI.newline)
        CGI_CLI.content_type_line = 'Content-type:text/html; charset=%s%s' % (str(CGI_CLI.sys_stdout_encoding), CGI_CLI.newline)

        ### DECIDE - CLI OR CGI MODE ##########################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent:
            CGI_CLI.cgi_active = True
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active: CGI_CLI.data = vars(CGI_CLI.args)
        if CGI_CLI.cgi_active:
            sys.stdout.write("%s%s%s" %
                (CGI_CLI.chunked_transfer_encoding_line,
                CGI_CLI.content_type_line,
                CGI_CLI.status_line))
            sys.stdout.flush()
            ### CHROME NEEDS 2NEWLINES TO BE ALREADY CHUNKED !!! ##############
            CGI_CLI.print_chunk("%s%s<!DOCTYPE html><html><head><title>%s</title>%s</head><body>" %
                (CGI_CLI.newline, CGI_CLI.newline,
                #CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit', \
                str(__file__).split('/')[-1] + '  PID' + str(os.getpid()) if '/' in str(__file__) else str(), \
                '<style>%s</style>' % (CGI_CLI.CSS_STYLE) if CGI_CLI.CSS_STYLE else str()),\
                ommit_logging = True, printall = True)
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM ENVIRONMENT BY DEFAULT ###
        try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
        except: CGI_CLI.PASSWORD        = str()
        try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
        except: CGI_CLI.USERNAME        = str()
        ### GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI ###
        if CGI_CLI.args.password: CGI_CLI.password = CGI_CLI.args.password
        if CGI_CLI.args.username:
            CGI_CLI.USERNAME = CGI_CLI.args.username
            if not CGI_CLI.args.password:
                CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
                getpass_done = True
        ### FORCE GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI GETPASS ###
        if CGI_CLI.args.getpass and not getpass_done:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
        ### GAIN/OVERWRITE USERNAME AND PASSWORD FROM CGI ###
        if CGI_CLI.username: CGI_CLI.USERNAME = CGI_CLI.username
        if CGI_CLI.password: CGI_CLI.PASSWORD = CGI_CLI.password
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): CGI_CLI.bcolors = CGI_CLI.nocolors
        CGI_CLI.cgi_save_files()
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

    @staticmethod
    def cgi_save_files():
        for key in CGI_CLI.data:
            if 'file[' in key:
                filename = key.replace('file[','').replace(']','')
                if filename:
                    use_filename = filename.replace('/','\\') if 'WIN32' in sys.platform.upper() else filename
                    dir_path = os.path.dirname(use_filename)
                    if os.path.exists(dir_path):
                        file_content = CGI_CLI.data.get('file[%s]'%(filename),None)
                        if file_content:
                            try:
                                with open(use_filename, 'wb') as file:
                                    file.write(CGI_CLI.data.get('file[%s]'%(filename)))
                                    CGI_CLI.uprint('The file "' + use_filename + '" was uploaded.', printall = True)
                            except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']', color = 'magenta', printall = True)

    @staticmethod
    def set_logfile(logfilename = None):
        """
        set_logfile(logfilename) - uses inserted logfilename
        NOTE: Add html footer to logfile if exists, Add html header to logfile
        """
        CGI_CLI.logtofile(end_log = True)
        CGI_CLI.logfilename = logfilename
        time.sleep(0.1)
        CGI_CLI.logtofile(start_log = True)

    @staticmethod
    def logtofile(msg = None, raw_log = None, start_log = None, end_log = None):
        msg_to_file = str()
        if CGI_CLI.logfilename:
            ### HTML LOGGING ##################################################
            if CGI_CLI.cgi_active:
                ### ADD HTML HEADER ###########################################
                if start_log:
                    msg_to_file += '<!DOCTYPE html><html><head><title>%s</title></head><body>'\
                        % (CGI_CLI.logfilename)
                ### CONVERT TEXT TO HTML FORMAT ###############################
                if not raw_log and msg:
                    msg_to_file += str(msg.replace('&','&amp;').\
                        replace('<','&lt;').\
                        replace('>','&gt;').replace(' ','&nbsp;').\
                        replace('"','&quot;').replace("'",'&apos;').\
                        replace('\n','<br/>'))
                elif msg: msg_to_file += msg
                ### ADD HTML FOOTER ###########################################
                if end_log: msg_to_file += '</body></html>'
            ### CLI LOGGING ###################################################
            elif msg: msg_to_file = msg + '\n'
            ### LOG CLI OR HTML MODE ##########################################
            if msg_to_file:
                with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                    CGI_CLI.fp.write(msg_to_file)
                    del msg_to_file
            ### ON END: LOGFILE SET TO VOID, AVOID OF MULTIPLE FOOTERS ########
            if end_log: CGI_CLI.logfilename = None

    @staticmethod
    def html_escape(text = None, pre_tag = None):
        escaped_text = str()
        if text and not pre_tag:
            escaped_text = str(text.replace('&','&amp;').\
                replace('<','&lt;').replace('>','&gt;').\
                replace(' ','&nbsp;').\
                replace('"','&quot;').replace("'",'&apos;').\
                replace('\n','<br/>'))
        elif text and pre_tag:
            ### OMMIT SPACES,QUOTES AND NEWLINES ##############################
            escaped_text = str(text.replace('&','&amp;').\
                replace('<','&lt;').replace('>','&gt;'))
        return escaped_text

    @staticmethod
    def get_timestamp():
        return '@%s[%.2fs] ' % \
            (datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'), \
            time.time() - CGI_CLI.START_EPOCH)

    @staticmethod
    def get_date_and_time():
        return '%s' % (datetime.datetime.now().strftime('%H:%M %d-%m-%Y'))

    @staticmethod
    def print_chunk(msg = None, no_newlines = None, raw_log = None, \
        ommit_logging = None, printall = None):
        """
        raw_log = raw logging
        """
        if msg:
            if printall:
                ### sys.stdout.write is printing without \n, print adds \n == +1BYTE ##
                if CGI_CLI.chunked and CGI_CLI.cgi_active:
                    if len(msg)>0:
                        sys.stdout.write("\r\n%X\r\n%s" % (len(msg), msg))
                        sys.stdout.flush()
                ### CLI MODE ##################################################
                else:
                    if no_newlines:
                        sys.stdout.write(msg)
                        sys.stdout.flush()
                    else:
                        print(msg)
            if not ommit_logging: CGI_CLI.logtofile(msg = msg, raw_log = raw_log)

    @staticmethod
    def uprint(text = None, tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        ommit_logging = None, no_newlines = None, start_tag = None, end_tag = None, raw = None, \
        timestamp = None, printall = None, no_printall = None, stop_button = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
           timestamp = True - locally allow (CGI_CLI.timestamp = True has priority)
           timestamp = 'no' - locally disable even if CGI_CLI.timestamp == True
           Use 'no_printall = not printall' instead of printall = False
        """
        if not text and not name: return None

        print_text = str()

        ### PRINTALL LOGIC ####################################################
        if not printall and not no_printall: printall_yes = True
        elif no_printall: printall_yes = False
        else: printall_yes = True

        if jsonprint:
            if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = str(json.dumps(text, indent = 4))
                except Exception as e:
                    CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']', printall = printall_yes)
        else: print_text = str(copy.deepcopy(text))

        print_name = str()
        if name == True:
            if not 'inspect.currentframe' in sys.modules: import inspect
            callers_local_vars = inspect.currentframe().f_back.f_locals.items()
            var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
            if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
        elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '

        ### GENERATE TIMESTAMP STRING, 'NO' = NO EVEN IF GLOBALLY IS ALLOWED ###
        timestamp_string = str()
        if timestamp or CGI_CLI.timestamp:
            timestamp_yes = True
            try:
                if str(timestamp).upper() == 'NO': timestamp_yes = False
            except: pass
            if timestamp_yes:
                timestamp_string = CGI_CLI.get_timestamp()

        ### CGI MODE ##########################################################
        if CGI_CLI.cgi_active:
            if raw:
                CGI_CLI.print_chunk(print_text, raw_log = True, \
                    ommit_logging = ommit_logging, printall = printall_yes)
            else:
                ### WORKARROUND FOR COLORING OF SIMPLE TEXT ###################
                if color and not (tag or start_tag): tag = 'void';
                if tag:
                    if str(tag) == 'warning':
                        CGI_CLI.print_chunk('<%s style="color:red; background-color:yellow;">'%(tag),\
                            raw_log = True, printall = printall_yes)
                    elif str(tag) == 'debug':
                        CGI_CLI.print_chunk('<%s style="color:dimgray; background-color:lightgray;">'%(tag),\
                            raw_log = True, printall = printall_yes)
                    else:
                        CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),\
                            ' style="color:%s;"' % (color) if color else str()), \
                            raw_log = True, printall = printall_yes)
                elif start_tag:
                    CGI_CLI.print_chunk('<%s%s%s>'%(start_tag,' id="%s"'%(tag_id) \
                        if tag_id else str(),' style="color:%s;"' % (color) if color else str()),\
                        raw_log = True, printall = printall_yes)
                if isinstance(print_text, six.string_types):
                    print_text = str(print_text.replace('&','&amp;').\
                        replace('<','&lt;').\
                        replace('>','&gt;').replace(' ','&nbsp;').\
                        replace('"','&quot;').replace("'",'&apos;').\
                        replace('\n','<br/>'))
                CGI_CLI.print_chunk(timestamp_string + print_name + print_text, \
                    raw_log = True, ommit_logging = ommit_logging, printall = printall_yes)
        else:
            ### CLI MODE ######################################################
            text_color = str()
            if color:
                if 'RED' in color.upper():       text_color = CGI_CLI.bcolors.RED
                elif 'MAGENTA' in color.upper(): text_color = CGI_CLI.bcolors.MAGENTA
                elif 'GREEN' in color.upper():   text_color = CGI_CLI.bcolors.GREEN
                elif 'BLUE' in color.upper():    text_color = CGI_CLI.bcolors.BLUE
                elif 'CYAN' in color.upper():    text_color = CGI_CLI.bcolors.CYAN
                elif 'GREY' in color.upper():    text_color = CGI_CLI.bcolors.GREY
                elif 'GRAY' in color.upper():    text_color = CGI_CLI.bcolors.GREY
                elif 'YELLOW' in color.upper():  text_color = CGI_CLI.bcolors.YELLOW

            CGI_CLI.print_chunk("%s%s%s%s%s" % \
                (text_color, timestamp_string, print_name, print_text, \
                CGI_CLI.bcolors.ENDC if text_color else str()), \
                raw_log = True, printall = printall_yes, no_newlines = no_newlines)

        ### PRINT END OF TAGS #################################################
        if CGI_CLI.cgi_active and not raw:
            if stop_button:
                CGI_CLI.print_chunk(CGI_CLI.stop_pid_button(pid = str(stop_button)),\
                    ommit_logging = True, printall = True)
            if tag:
                CGI_CLI.print_chunk('</%s>' % (tag), raw_log = True, printall = printall_yes)
                ### USER DEFINED TAGS DOES NOT PROVIDE NEWLINES!!! ############
                if tag in ['debug','warning','error','void']:
                    CGI_CLI.print_chunk('<br/>', raw_log = True, printall = printall_yes)
            elif end_tag:
                CGI_CLI.print_chunk('</%s>' % (end_tag), raw_log = True, printall = printall_yes)
            elif not no_newlines:
                CGI_CLI.print_chunk('<br/>', raw_log = True, printall = printall_yes)

            ### PRINT PER TAG #################################################
            #CGI_CLI.print_chunk(print_per_tag, printall = printall_yes)

        ### COPY CLEANUP ######################################################
        del print_text
        return None

    @staticmethod
    def tableprint(table_line_list = None, column_percents = None, \
        header = None, end_table = None, color = None, chars_per_line = None, \
        tag = None):
        """
        table_line_list - table line is list of table columns
        column_percents - optional column space in % of line
        column_percents is needed only for CLI mode, HTML has table autospacing
        """
        if table_line_list and len(table_line_list) > 0:
            tag_string = str(tag) if tag else 'void'
            color_string = ' style="color:%s;"' % (color) if color else str()
            if CGI_CLI.cgi_active:
                if header:
                    CGI_CLI.print_chunk('<br/><table style="width:70%"><tr>', \
                        raw_log = True, printall = True)
                    for column in table_line_list:
                        CGI_CLI.print_chunk('<th align="left"><%s%s>%s</%s></th>' % \
                            (tag_string, color_string, column, tag_string), \
                            raw_log = True, printall = True)
                else:
                    for column in table_line_list:
                        CGI_CLI.print_chunk('<td><%s%s>%s</%s></td>' % \
                            (tag_string, color_string, column, tag_string),\
                            raw_log = True, printall = True)
                if table_line_list and len (table_line_list) > 0:
                    CGI_CLI.print_chunk('</tr>', raw_log = True, printall = True)
            else:
                if not chars_per_line: line_lenght = 80
                else: line_lenght = int(chars_per_line)
                chars_per_column = 0
                format_string, print_string = str(), str()
                if column_percents and len(column_percents) == len(table_line_list):
                    for percent in column_percents:
                        ### %-Xs ==> left aligned string ###
                        format_string = '%%-%ds ' % int(percent * line_lenght/100)
                        print_string += format_string % (column)
                else:
                    chars_per_column = int(line_lenght / len(table_line_list))
                    if chars_per_column:
                        for column in table_line_list:
                            ### %-Xs ==> left aligned string ###
                            format_string = '%%-%ds ' % (chars_per_column)
                            print_string += format_string % (column)
                if format_string:
                        CGI_CLI.uprint(print_string, color = color, printall = True)
        if CGI_CLI.cgi_active and end_table:
            CGI_CLI.print_chunk('</table><br/>', raw_log = True, printall = True)

    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, \
        color = None, list_separator = None, printall = None, name = None, on_submit = None):
        """ formprint() - print simple HTML form
            form_data - string, just html raw OR list or dict values = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
                      - value in dictionary means cgi variable name / printed componenet value
            name - name of form, could be used for javascript actions
            on_submit - ob submit action (javascript function)
        """
        def subformprint(data_item):
            if isinstance(data_item, six.string_types):  CGI_CLI.print_chunk(data_item, raw_log = True, printall = True)
            elif isinstance(data_item, (dict,collections.OrderedDict)):
                if data_item.get('raw',None): CGI_CLI.print_chunk(data_item.get('raw'), raw_log = True, printall = True)
                elif data_item.get('textcontent',None):
                    CGI_CLI.print_chunk('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4">%s</textarea>'%\
                        (data_item.get('textcontent'), data_item.get('text','')), raw_log = True, printall = True)
                elif data_item.get('text'):
                    CGI_CLI.print_chunk('%s: <input type = "text" name = "%s"><br />'%\
                        (data_item.get('text','').replace('_',' '),data_item.get('text')), raw_log = True, printall = True)
                elif data_item.get('password'):
                    CGI_CLI.print_chunk('%s: <input type = "password" name = "%s"><br />'%\
                        (data_item.get('password','').replace('_',' '),data_item.get('password')), raw_log = True, printall = True)
                elif data_item.get('radio'):
                    ### 'RADIO':'NAME__VALUE' ###
                    if isinstance(data_item.get('radio'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            try:
                                value = radiobutton.split('__')[1]
                                name = radiobutton.split('__')[0]
                            except: value, name = radiobutton, 'radio'
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s %s'%\
                                (name,value,value.replace('_',' '), \
                                list_separator if list_separator else str()), raw_log = True, printall = True)
                    else:
                        try:
                            value = data_item.get('radio').split('__')[1]
                            name = data_item.get('radio').split('__')[0]
                        except: value, name = data_item.get('radio'), 'radio'
                        CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s' %\
                            (name,value,value.replace('_',' ')), raw_log = True, printall = True)
                elif data_item.get('checkbox'):
                    CGI_CLI.print_chunk('<input type = "checkbox" name = "%s" value = "on" /> %s' \
                        % (data_item.get('checkbox'),data_item.get('checkbox','').replace('_',' ')), \
                        raw_log = True, printall = True)
                elif data_item.get('dropdown'):
                    if len(data_item.get('dropdown').split(','))>0:
                        CGI_CLI.print_chunk('<select name = "dropdown[%s]">' \
                            %(data_item.get('dropdown')), raw_log = True, printall = True)
                        for option in data_item.get('dropdown').split(','):
                            CGI_CLI.print_chunk('<option value = "%s">%s</option>' \
                                %(option,option), raw_log = True, printall = True)
                        CGI_CLI.print_chunk('</select>', raw_log = True, printall = True)
                elif data_item.get('file'):
                   CGI_CLI.print_chunk('Upload file: <input type = "file" name = "file[%s]" />' \
                       % (data_item.get('file').replace('\\','/')), raw_log = True, printall = True)
                elif data_item.get('submit'):
                    CGI_CLI.print_chunk('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%\
                        (data_item.get('submit'),data_item.get('submit')), raw_log = True, printall = True)

        ### START OF FORMPRINT ###
        formtypes = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
        i_submit_button = None if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            CGI_CLI.print_chunk('<br/>', raw_log = True, printall = True)
            if tag and 'h' in tag: CGI_CLI.print_chunk('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()), raw_log = True, printall = True)
            if color or tag and 'p' in tag: tag = 'p'; CGI_CLI.print_chunk('<p%s>'%(' style="color:%s;"'%(color) if color else str()), raw_log = True, printall = True)
            CGI_CLI.print_chunk('<form %saction = "/cgi-bin/%s" enctype = "multipart/form-data" action = "save_file.py" %smethod = "post">'%\
                ('name="%s" ' % (str(name)) if name else str(), i_pyfile, 'onsubmit="%s" ' % (str(on_submit)) if on_submit else str()), \
                raw_log = True, printall = True)
            ### RAW HTML ###
            if isinstance(form_data, six.string_types):
                CGI_CLI.print_chunk(form_data, raw_log = True, printall = True)
            ### STRUCT FORM DATA = LIST ###
            elif isinstance(form_data, (list,tuple)):
                for data_item in form_data: subformprint(data_item)
            ### JUST ONE DICT ###
            elif isinstance(form_data, (dict,collections.OrderedDict)): subformprint(form_data)
            if i_submit_button: subformprint({'submit':i_submit_button})
            CGI_CLI.print_chunk('</form>', raw_log = True, printall = True)
            if tag and 'p' in tag: CGI_CLI.print_chunk('</p>', raw_log = True, printall = True)
            if tag and 'h' in tag: CGI_CLI.print_chunk('</%s>'%(tag), raw_log = True, printall = True)


    @staticmethod
    def html_selflink():
        if not CGI_CLI.submit_form or CGI_CLI.submit_form in CGI_CLI.self_buttons:
            i_pyfile = sys.argv[0]
            try: pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
            except: pyfile = i_pyfile.strip()
            CGI_CLI.print_result_summary()
            if CGI_CLI.cgi_active:
                CGI_CLI.print_chunk('<p id="scriptend"></p>', raw_log = True, printall = True)
                CGI_CLI.print_chunk('<br/><a href = "./%s">PAGE RELOAD</a>' % (pyfile), raw_log = True, printall = True)


    @staticmethod
    def VERSION(path_to_file = str(os.path.abspath(__file__))):
        if 'WIN32' in sys.platform.upper():
            file_time = os.path.getmtime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            file_time = stat.st_mtime
        return time.strftime("%y.%m.%d_%H:%M",time.gmtime(file_time))

    @staticmethod
    def print_args(ommit_print = None):
        from platform import python_version
        print_string = 'python[%s]\n' % (str(python_version()))
        print_string += 'version[%s], ' % (CGI_CLI.VERSION())
        print_string += 'file[%s]\n' % (sys.argv[0])
        print_string += 'CGI_CLI.USERNAME[%s], CGI_CLI.PASSWORD[%s]\n' % \
            (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No')
        print_string += 'remote_addr[%s], ' % dict(os.environ).get('REMOTE_ADDR','')
        print_string += 'browser[%s]\n' % dict(os.environ).get('HTTP_USER_AGENT','')
        print_string += 'CGI_CLI.cgi_active[%s], CGI_CLI.submit_form[%s], CGI_CLI.chunked[%s]\n' % \
            (str(CGI_CLI.cgi_active), str(CGI_CLI.submit_form), str(CGI_CLI.chunked))
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_CLI.data[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4)))
            except: pass
        else: print_string += 'CLI_args = %s\nCGI_CLI.data = %s' % (str(sys.argv[1:]), str(json.dumps(CGI_CLI.data,indent = 4)))
        if not ommit_print: CGI_CLI.uprint(print_string, tag = 'debug', no_printall = not CGI_CLI.printall, timestamp = 'no')
        return print_string

    @staticmethod
    def print_env():
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', tag = 'debug', jsonprint = True, no_printall = not CGI_CLI.printall, timestamp = 'no')

    @staticmethod
    def parse_input_data(key = None, key_in = None, \
        append_to_list = None, replace_what = None, replace_by = None, \
        ignore_list = None):
        """
        key - read value of inserted key
        key_in - read part of key which contains key_in
        append_to_list - address of list to append
        replace_what, replace_by - values which will be changed
        return result - string variable
        """
        result = str()
        for data_key in CGI_CLI.data.keys():
            try: data_value = copy.deepcopy(data_key)
            except: data_value = str()

            ### READ KEY VALUE OR KEY VALUES LIST #############################
            if key and key == data_value:
                value_found = copy.deepcopy(CGI_CLI.data.get(key,str()))
                if value_found:
                    if ',' in value_found:
                        ### IF IGNORE_LIST USE ONLY FIRST DATA ################
                        result = value_found.split(',')[0].strip().replace("'",'').replace(']','').replace('[','')
                        if ignore_list:
                            if isinstance(append_to_list, (list)): append_to_list.append(result)
                            break
                        else:
                            for list_item in value_found.split(','):
                                item = copy.deepcopy(list_item).strip().replace("'",'').replace(']','').replace('[','')
                                if replace_what and replace_by:
                                    item = item.replace(str(replace_what),str(replace_by))
                                if isinstance(append_to_list, (list)): append_to_list.append(item)
                    else:
                        if replace_what and replace_by:
                            value_found = value_found.replace(str(replace_what),str(replace_by)).strip().replace(",",'').replace(']','').replace('[','')
                        result = value_found
                        if isinstance(append_to_list, (list)): append_to_list.append(result)

            ### READ PART OF KEY WHICH CONTAINES KEY_IN #######################
            elif key_in and key_in in data_value:
                data_value = data_value.replace(key_in,str()).strip().replace("'",'').replace(']','').replace('[','')
                if replace_what and replace_by:
                    data_value = data_value.replace(str(replace_what),str(replace_by))
                if isinstance(append_to_list, (list)): append_to_list.append(data_value)

        ### RETURN STRING VARIABLE, IGNORE LISTS ##############################
        return result

    @staticmethod
    def stop_pid_button(pid = None):
        if pid:
            return '<form action = "/cgi-bin/%s" target="_blank"><p hidden><input type="checkbox" name="pidtokill" value="%s" checked="checked"></p><input type="submit" name="submit" value="STOP"></form>' \
                % (sys.argv[0].replace('\\','/').split('/')[-1].strip() if '/' or '\\' in sys.argv[0] else sys.argv[0],str(pid))
        return str()

    @staticmethod
    def send_me_email(subject = str(), email_body = str(), file_name = None, attachments = None, \
        email_address = None, cc = None, bcc = None, username = None):
        """
        FUCTION: send_me_email, RETURNS: True/None, Successfully send email or not
        INPUT PARAMETERS:
        email_address - string, email address if is known, otherwise use username parameter
        username    - string, system username from which could be generated email
        subject     - string, email subject
        email_body  - string, email body
        cc, bcc     - list or string, in case of list possibility to insert more email addresses
        attachments - list or string , possibility to attach more files
        file_name   - string, simple file attachment option
        """
        def send_unix_email_body(mail_command):
            email_success = None
            try:
                forget_it = subprocess.check_output(mail_command, shell=True)
                CGI_CLI.uprint(' ==> Email sent. Subject:"%s" SentTo:%s by COMMAND=[%s] with RESULT=[%s]...'\
                    %(subject,sugested_email_address,mail_command,forget_it), color = 'green')
                email_success = True
            except Exception as e:
                CGI_CLI.uprint(" ==> Problem to send email by COMMAND=[%s], PROBLEM=[%s]\n"\
                    % (mail_command,str(e)) ,color = 'magenta', no_printall = not CGI_CLI.printall)
            return email_success

        ### FUCTION send_me_email START ###########################################
        email_sent, sugested_email_address = None, str()
        if username: my_account = username
        else: my_account = subprocess.check_output('whoami', shell=True).strip()
        if email_address: sugested_email_address = email_address
        if not 'WIN32' in sys.platform.upper():
            try:
                ldapsearch_output = subprocess.check_output('ldapsearch -LLL -x uid=%s mail' % (my_account), shell=True)
                ldap_email_address = ldapsearch_output.decode(CGI_CLI.sys_stdout_encoding).split('mail:')[1].splitlines()[0].strip()
            except: ldap_email_address = None
            if ldap_email_address: sugested_email_address = ldap_email_address
            else:
                try: sugested_email_address = os.environ['NEWR_EMAIL']
                except: pass
                if not sugested_email_address:
                    try:
                        my_getent_line = ' '.join((subprocess.check_output('getent passwd "%s"'% \
                            (my_account.strip()), shell=True)).split(':')[4].split()[:2])
                        my_name = my_getent_line.splitlines()[0].split()[0]
                        my_surname = my_getent_line.splitlines()[0].split()[1]
                        if my_name and my_surname:
                            sugested_email_address = '%s.%s@orange.com' % (my_name, my_surname)
                    except: pass

            ### UNIX - MAILX ######################################################
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

            ### IF EMAIL ADDRESS FOUND , SEND EMAIL ###############################
            if not sugested_email_address:
                CGI_CLI.uprint('Email Address not found!', color = 'magenta', no_printall = not CGI_CLI.printall)
            else:
                mail_command += '%s' % (sugested_email_address)
                email_sent = send_unix_email_body(mail_command)

                ### UNIX - MUTT ###################################################
                if not email_sent and file_name:
                    mail_command = 'echo | mutt -s "%s" -a %s -- %s' % \
                        (subject, file_name, sugested_email_address)
                    email_sent = send_unix_email_body(mail_command)


        ### WINDOWS OS PART #######################################################
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
                    %(subject,sugested_email_address,email_application), color = 'green')
                email_sent = True
            except Exception as e: CGI_CLI.uprint(" ==> Problem to send email by APPLICATION=[%s], PROBLEM=[%s]\n"\
                    % (email_application,str(e)) ,color = 'magenta')
        return email_sent

    @staticmethod
    def print_result_summary():
        if len(CGI_CLI.result_list) > 0: CGI_CLI.uprint('\n\nRESULT SUMMARY:', tag = 'h1')
        for result, color in CGI_CLI.result_list:
            CGI_CLI.uprint(result , tag = 'h3', color = color)
        if CGI_CLI.logfilename:
            logfilename = CGI_CLI.logfilename
            iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None, ommit_logging = True).strip()
            if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
            else: urllink = 'https://%s/cgi-bin/' % (iptac_server)
            if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, logfilename)
            else: logviewer = './logviewer.py?logfile=%s' % (logfilename)
            if CGI_CLI.cgi_active:
                CGI_CLI.uprint('<p style="color:blue;"> ==> File <a href="%s" target="_blank" style="text-decoration: none">%s</a> created.</p>' \
                    % (logviewer, logfilename), raw = True, color = 'blue')
                CGI_CLI.uprint('<br/>', raw = True)
            else:
                CGI_CLI.uprint(' ==> File %s created.\n\n' % (logfilename))
            CGI_CLI.set_logfile(logfilename = None)
            ### SEND EMAIL WITH LOGFILE ###########################################
            CGI_CLI.send_me_email( \
                subject = logfilename.replace('\\','/').split('/')[-1] if logfilename else None, \
                file_name = logfilename, username = USERNAME)



##############################################################################


class RCMD(object):

    @staticmethod
    def connect(device = None, cmd_data = None, username = None, password = None, \
        use_module = 'paramiko', \
        connection_timeout = 600, cmd_timeout = 60, \
        conf = None, sim_config = None, disconnect = None, printall = None, \
        do_not_final_print = None, commit_text = None, silent_mode = None, \
        disconnect_timeout = 2, no_alive_test = None):
        """ FUNCTION: RCMD.connect(), RETURNS: list of command_outputs
        PARAMETERS:
        device     - string , device_name/ip_address/device_name:PORT_NUMBER/ip_address:PORT_NUMBER
        cmd_data  - dict, {'cisco_ios':[..], 'cisco_xr':[..], 'juniper':[..], 'huawei':[], 'linux':[..]}
        username   - string, remote username
        password   - string, remote password
        use_module - string, paramiko/netmiko
        disconnect - True/False, immediate disconnect after RCMD.connect and processing of cmd_data
        conf        - True/False, go to config mode
        NOTES:
        1. cmd_data is DEVICE TYPE INDEPENDENT and will be processed after device detection
        2. only 1 instance of static class RCMD could exists
        """
        import atexit; atexit.register(RCMD.__cleanup__)
        command_outputs = str()
        RCMD.ssh_connection = None
        RCMD.CMD = []
        if device:
            RCMD.silent_mode = silent_mode
            RCMD.DISCONNECT_TIMEOUT = disconnect_timeout
            RCMD.CMD = []
            RCMD.output, RCMD.fp = None, None
            RCMD.device = device
            RCMD.ssh_connection = None
            RCMD.CONNECTION_TIMEOUT = int(connection_timeout)
            RCMD.CMD_TIMEOUT = int(cmd_timeout)
            RCMD.use_module = use_module
            RCMD.USERNAME = username
            RCMD.PASSWORD = password
            RCMD.vision_api_json_string = str()
            RCMD.ip_address = None
            RCMD.router_prompt = None
            RCMD.printall = printall
            RCMD.router_type = None
            RCMD.router_version = None
            RCMD.conf = conf
            RCMD.sim_config = sim_config
            RCMD.huawei_version = 0
            RCMD.config_problem = None
            RCMD.commit_text = commit_text
            RCMD.do_not_final_print = do_not_final_print
            RCMD.drive_string = str()
            RCMD.KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']
            try: RCMD.DEVICE_HOST = device.split(':')[0]
            except: RCMD.DEVICE_HOST = str()
            try: RCMD.DEVICE_PORT = device.split(':')[1]
            except: RCMD.DEVICE_PORT = '22'

            if CGI_CLI.timestamp:
                CGI_CLI.uprint('RCMD.connect - start.\n', \
                    no_printall = not printall, tag = 'debug')

            ### IS ALIVE TEST #################################################
            RCMD.ip_address = RCMD.get_IP_from_vision(device)

            if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - after get_IP_from_vision.\n', \
                        no_printall = not printall, tag = 'debug')

            device_id = RCMD.ip_address if RCMD.ip_address else device
            if not no_alive_test:
                for i_repeat in range(3):
                    if RCMD.is_alive(device_id): break
                else:
                    CGI_CLI.uprint('DEVICE %s (ip=%s) is not ALIVE.' % \
                        (device, RCMD.ip_address), color = 'magenta')
                    return command_outputs

            if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - after pingtest.\n', \
                        no_printall = not printall, tag = 'debug')

            ### START SSH CONNECTION ##########################################
            CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.', color = 'gray', no_printall = not printall)
            try:
                ### ONE_CONNECT DETECTION #####################################
                RCMD.client = paramiko.SSHClient()

                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - before RCMD.client.set_missing_host_key_policy.\n', \
                        no_printall = not printall, tag = 'debug')

                RCMD.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - before RCMD.client.connect.\n', \
                        no_printall = not printall, tag = 'debug')

                #RCMD.client.connect(RCMD.DEVICE_HOST, port=int(RCMD.DEVICE_PORT), \
                RCMD.client.connect(device_id, port=int(RCMD.DEVICE_PORT), \
                    username=RCMD.USERNAME, password=RCMD.PASSWORD, \
                    banner_timeout = 15, \
                    ### AUTH_TIMEOUT MAKES PROBLEMS ON IPTAC1 ###
                    #auth_timeout = 10, \
                    timeout = RCMD.CONNECTION_TIMEOUT, \
                    look_for_keys = False)

                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - after RCMD.client.connect.\n', \
                        no_printall = not printall, tag = 'debug')

                RCMD.ssh_connection = RCMD.client.invoke_shell()

                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - after RCMD.client.invoke_shell.\n', \
                        no_printall = not printall, tag = 'debug')

                if RCMD.ssh_connection:
                    RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
                    if not RCMD.router_type: CGI_CLI.uprint('DEVICE_TYPE NOT DETECTED!', color = 'red')
                    elif RCMD.router_type in RCMD.KNOWN_OS_TYPES:
                        CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type), \
                            color = 'gray', no_printall = not printall)
            except Exception as e:
                if not RCMD.silent_mode:
                    CGI_CLI.uprint(str(device) + ' CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
            finally:
                if disconnect: RCMD.disconnect()
            ### EXIT IF NO CONNECTION ##########################################
            if not RCMD.ssh_connection: return command_outputs
            ####################################################################
            if RCMD.router_type == 'cisco_ios':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('cisco_ios',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '%s%s#'%(RCMD.device.upper(),''), \
                    '%s%s#'%(RCMD.device.upper(),'(config)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-if)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-line)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-router)')  ]
                RCMD.TERM_LEN_0 = "terminal length 0"
                RCMD.EXIT = "exit"
                RCMD.drive_string = 'bootflash:'
            elif RCMD.router_type == 'cisco_xr':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('cisco_xr',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '%s%s#'%(RCMD.device.upper(),''), \
                    '%s%s#'%(RCMD.device.upper(),'(config)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-if)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-line)'), \
                    '%s%s#'%(RCMD.device.upper(),'(config-router)'), \
                    'sysadmin#' ]
                RCMD.TERM_LEN_0 = "terminal length 0"
                RCMD.EXIT = "exit"
                RCMD.drive_string = 'harddisk:'
            elif RCMD.router_type == 'juniper':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('juniper',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                     USERNAME + '@' + RCMD.device.upper() + '> ', # !! Need the space after >
                     USERNAME + '@' + RCMD.device.upper() + '# ' ]
                RCMD.TERM_LEN_0 = "set cli screen-length 0"
                RCMD.EXIT = "exit"
                ### MOST PROBABLE IS THAT RE0 IS ALONE OR MASTER ##############
                RCMD.drive_string = 're0:'
            elif RCMD.router_type == 'huawei':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('huawei',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ \
                    '<' + RCMD.device.upper() + '>',
                    '[' + RCMD.device.upper() + ']',
                    '[~' + RCMD.device.upper() + ']',
                    '[*' + RCMD.device.upper() + ']' ]
                RCMD.TERM_LEN_0 = "screen-length 0 temporary"     #"screen-length disable"
                RCMD.EXIT = "quit"
                RCMD.drive_string = 'cfcard:'
            elif RCMD.router_type == 'linux':
                if cmd_data:
                    try: RCMD.CMD = cmd_data.get('linux',[])
                    except:
                        if isinstance(cmd_data,(list,tuple)): RCMD.CMD = cmd_data
                RCMD.DEVICE_PROMPTS = [ ]
                RCMD.TERM_LEN_0 = ''     #"screen-length disable"
                RCMD.EXIT = "exit"
            else: RCMD.CMD = []
            # ADD PROMPT TO PROMPTS LIST
            if RCMD.router_prompt: RCMD.DEVICE_PROMPTS.append(RCMD.router_prompt)
            ### START SSH CONNECTION AGAIN ####################################
            try:
                if RCMD.router_type and RCMD.use_module == 'netmiko':
                    ### PARAMIKO IS ALREADY CONNECTED, SO DISCONNECT FIRST ####
                    RCMD.disconnect()
                    RCMD.ssh_connection = netmiko.ConnectHandler(device_type = RCMD.router_type, \
                        ip = RCMD.DEVICE_HOST, port = int(RCMD.DEVICE_PORT), \
                        username = RCMD.USERNAME, password = RCMD.PASSWORD)
                elif RCMD.router_type and RCMD.use_module == 'paramiko':
                    ### PARAMIKO IS ALREADY CONNECTED #########################
                    RCMD.output, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,RCMD.TERM_LEN_0)
                    RCMD.output2, RCMD.forget_it = RCMD.ssh_send_command_and_read_output(RCMD.ssh_connection,RCMD.DEVICE_PROMPTS,"")
                    RCMD.output += RCMD.output2
                ### WORK REMOTE  ==============================================
                command_outputs = RCMD.run_commands(RCMD.CMD)
                ### ===========================================================
            except Exception as e:
                if not RCMD.silent_mode:
                    CGI_CLI.uprint('CONNECTION_PROBLEM[' + str(e) + ']', color = 'magenta')
            finally:
                if disconnect: RCMD.disconnect()
        else: CGI_CLI.uprint('DEVICE NOT INSERTED!', color = 'magenta')
        return command_outputs

    @staticmethod
    def is_alive(device = None):
        if device:
            try:    device_without_port = device.split(':')[0]
            except: device_without_port = device
            if 'WIN32' in sys.platform.upper():
                command = 'ping %s -n 1' % (device_without_port)
            else: command = 'ping %s -c 1' % (device_without_port)
            try: os_output = subprocess.check_output(str(command), \
                stderr=subprocess.STDOUT, shell=True).decode(CGI_CLI.sys_stdout_encoding)
            except: os_output = str()
            if 'Packets: Sent = 1, Received = 1' in os_output \
                or '1 packets transmitted, 1 received,' in os_output:
                return True
        return False

    @staticmethod
    def run_command(cmd_line = None, printall = None, conf = None, \
        long_lasting_mode = None, autoconfirm_mode = None, \
        sim_config = None, sim_all = None, ignore_prompt = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        sim_all  - simulate execution of all commands, not only config commands
                   used for ommit save/write in normal mode
        sim_config - simulate config commands
        long_lasting_mode - max connection timeout, no cmd timeout, no prompt discovery
        autoconfirm_mode - in case of interactivity send 'Y\n' on huawei ,'\n' on cisco
        """
        last_output, sim_mark = str(), str()
        if RCMD.ssh_connection and cmd_line:
            if ((sim_config or RCMD.sim_config) and (conf or RCMD.conf)) or sim_all: sim_mark = '(SIM)'
            if printall or RCMD.printall:
                CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line, color = 'blue', ommit_logging = True)
            if not sim_mark:
                if RCMD.use_module == 'netmiko':
                    last_output = RCMD.ssh_connection.send_command(cmd_line)
                elif RCMD.use_module == 'paramiko':
                    last_output, new_prompt = RCMD.ssh_send_command_and_read_output( \
                        RCMD.ssh_connection, RCMD.DEVICE_PROMPTS, cmd_line, \
                        long_lasting_mode = long_lasting_mode, \
                        autoconfirm_mode = autoconfirm_mode, \
                        ignore_prompt = ignore_prompt, \
                        printall = printall)
                    if new_prompt: RCMD.DEVICE_PROMPTS.append(new_prompt)
            if printall or RCMD.printall:
                if not long_lasting_mode:
                    CGI_CLI.uprint(last_output, tag = 'pre', timestamp = 'no', ommit_logging = True)
            elif not RCMD.silent_mode:
                if not long_lasting_mode:
                    CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
            ### LOG ALL ONLY ONCE, THAT IS BECAUSE PREVIOUS LINE ommit_logging = True ###
            if CGI_CLI.cgi_active:
                CGI_CLI.logtofile('<p style="color:blue;">REMOTE_COMMAND' + \
                    sim_mark + ': ' + cmd_line + '</p>\n<pre>' + \
                    CGI_CLI.html_escape(last_output, pre_tag = True) + \
                    '\n</pre>\n', raw_log = True)
            else: CGI_CLI.logtofile('REMOTE_COMMAND' + sim_mark + ': ' + \
                      cmd_line + '\n' + last_output + '\n')

        return last_output

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None, \
        do_not_final_print = None , commit_text = None, submit_result = None , \
        long_lasting_mode = None, autoconfirm_mode = None, ignore_prompt = None):
        """
        FUNCTION: run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        conf     - True/False, go to config mode
        sim_config - simulate config commands
        long_lasting_mode - max connection timeout, no cmd timeout, no prompt discovery
        autoconfirm_mode - in case of interactivity send 'Y\n' on huawei ,'\n' on cisco
        """
        command_outputs, cmd_list = str(), []
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if RCMD.router_type=='cisco_ios': cmd_list = cmd_data.get('cisco_ios',[])
            elif RCMD.router_type=='cisco_xr': cmd_list = cmd_data.get('cisco_xr',[])
            elif RCMD.router_type=='juniper': cmd_list = cmd_data.get('juniper',[])
            elif RCMD.router_type=='huawei': cmd_list = cmd_data.get('huawei',[])
            elif RCMD.router_type=='linux': cmd_list = cmd_data.get('linux',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]

        if RCMD.ssh_connection and len(cmd_list)>0:
            ### WORK REMOTE ================================================
            ### CGI_CLI.logtofile(RCMD.output + '\n')
            command_outputs, sim_mark = [], str()
            ### CONFIG MODE FOR NETMIKO ####################################
            if (conf or RCMD.conf) and RCMD.use_module == 'netmiko':
                if (sim_config or RCMD.sim_config): sim_mark, last_output = '(SIM)', str()
                else:
                    ### PROCESS COMMANDS - PER COMMAND LIST! ###############
                    last_output = RCMD.ssh_connection.send_config_set(cmd_list)
                    if printall or RCMD.printall:
                        CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + str(cmd_list), color = 'blue')
                        CGI_CLI.uprint(str(last_output), color = 'gray', timestamp = 'no')
                    CGI_CLI.logtofile('REMOTE_COMMANDS' + sim_mark + ': ' \
                        + str(cmd_list) + '\n' + str(last_output) + '\n')
                    command_outputs = [last_output]
            elif RCMD.use_module == 'paramiko':
                ### CONFIG MODE FOR PARAMIKO ###############################
                conf_output = ''
                if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':
                    if RCMD.router_type=='cisco_ios': conf_output = RCMD.run_command('config t', \
                        conf = conf, sim_config = sim_config, printall = printall)
                    elif RCMD.router_type=='cisco_xr': conf_output = RCMD.run_command('config t', \
                        conf = conf, sim_config = sim_config, printall = printall)
                    elif RCMD.router_type=='juniper': conf_output = RCMD.run_command('configure exclusive', \
                        conf = conf, sim_config = sim_config , printall = printall)
                    elif RCMD.router_type=='huawei':
                        version_output = RCMD.run_command('display version | include software', \
                            conf = False, sim_config = sim_config, printall = printall)
                        try: RCMD.huawei_version = float(version_output.split('VRP (R) software, Version')[1].split()[0].strip())
                        except: RCMD.huawei_version = 0
                        conf_output = RCMD.run_command('system-view', \
                            conf = conf, sim_config = sim_config, printall = printall)
                if conf_output: command_outputs.append(conf_output)
                ### PROCESS COMMANDS - PER COMMAND #########################
                for cmd_line in cmd_list:
                    command_outputs.append(RCMD.run_command(cmd_line, \
                        conf = conf, sim_config = sim_config, printall = printall,
                        long_lasting_mode = long_lasting_mode, \
                        ignore_prompt = ignore_prompt, \
                        autoconfirm_mode = autoconfirm_mode))
                ### EXIT FROM CONFIG MODE FOR PARAMIKO #####################
                if (conf or RCMD.conf) and RCMD.use_module == 'paramiko':
                    ### GO TO CONFIG TOP LEVEL SECTION ---------------------
                    ### CISCO_IOS/XE has end command exiting from config ###
                    if RCMD.router_type=='cisco_xr':
                        for repeat_times in range(10):
                            if '(config-' in ''.join(command_outputs[-1]):
                                command_outputs.append(RCMD.run_command('exit', \
                                    conf = conf, sim_config = sim_config, printall = printall))
                            else: break
                    ### JUNOS - HAS (HOPEFULLY) NO CONFIG LEVELS ###
                    elif RCMD.router_type=='huawei':
                        for repeat_times in range(10):
                            ### NEW HUAWEI has [~ or [* in config mode ###
                            if re.search(r'\[[0-9a-zA-Z\~\*]+\-[0-9a-zA-Z\-\.\@\_]+\]', ''.join(command_outputs[-1:])):
                                command_outputs.append(RCMD.run_command('quit', \
                                    conf = conf, sim_config = sim_config, printall = printall))
                            else: break
                    ### COMMIT SECTION -------------------------------------
                    commit_output = ""
                    if RCMD.router_type=='cisco_ios': pass
                    elif RCMD.router_type=='cisco_xr':
                        command_outputs.append(RCMD.run_command('commit', \
                            conf = conf, sim_config = sim_config, printall = printall))
                        if 'Failed to commit' in ''.join(command_outputs[-1:]):
                            ### ALTERNATIVE COMMANDS: show commit changes diff, commit show-error
                            command_outputs.append(RCMD.run_command('show configuration failed', \
                                conf = conf, sim_config = sim_config, printall = printall))
                    elif RCMD.router_type=='juniper': command_outputs.append(RCMD.run_command('commit and-quit', \
                        conf = conf, sim_config = sim_config, printall = printall))
                    elif RCMD.router_type=='huawei' and RCMD.huawei_version >= 7:
                        commit_output = command_outputs.append(RCMD.run_command('commit', \
                            conf = conf, sim_config = sim_config, printall = printall))
                    ### EXIT CONFIG SECTION --------------------------------
                    if RCMD.router_type=='cisco_ios': command_outputs.append(RCMD.run_command('end', \
                        conf = conf, sim_config = sim_config, printall = printall))
                    elif RCMD.router_type=='cisco_xr': command_outputs.append(RCMD.run_command('exit', \
                        conf = conf, sim_config = sim_config, printall = printall))
                    ### JUNOS IS ALREADY OUT OF CONFIG ###
                    elif RCMD.router_type=='huawei':
                        command_outputs.append(RCMD.run_command('quit', conf = conf, \
                            sim_config = sim_config, printall = printall))
                    ### NVRAM WRITE/SAVE SECTION - NO CONFIG MODE! ---------
                    if RCMD.router_type=='cisco_ios':
                        command_outputs.append(RCMD.run_command('write', conf = False, \
                            sim_all = sim_config, printall = printall))
                    elif RCMD.router_type=='huawei':
                        ### ALL HUAWEI ROUTERS NEED SAVE ###
                        command_outputs.append(RCMD.run_command('save', conf = False, \
                            sim_all = sim_config, printall = printall))
                        command_outputs.append(RCMD.run_command('yes', conf = False, \
                            sim_all = sim_config, printall = printall))
            ### CHECK CONF OUTPUTS #########################################
            if (conf or RCMD.conf):
                RCMD.config_problem = None
                CGI_CLI.uprint('\nCHECKING COMMIT ERRORS...', tag = CGI_CLI.result_tag, color = 'blue')
                for rcmd_output in command_outputs:
                    CGI_CLI.uprint(' . ', no_newlines = True, ommit_logging = True, timestamp = 'no')
                    if 'INVALID INPUT' in rcmd_output.upper() \
                        or 'INCOMPLETE COMMAND' in rcmd_output.upper() \
                        or 'FAILED TO COMMIT' in rcmd_output.upper() \
                        or 'UNRECOGNIZED COMMAND' in rcmd_output.upper() \
                        or 'ERROR:' in rcmd_output.upper() \
                        or 'SYNTAX ERROR' in rcmd_output.upper():
                        RCMD.config_problem = True
                        CGI_CLI.uprint('\nCONFIGURATION PROBLEM FOUND:', color = 'red', timestamp = 'no')
                        CGI_CLI.uprint('%s' % (rcmd_output), color = 'darkorchid', timestamp = 'no')
                ### COMMIT TEXT ###
                if not (do_not_final_print or RCMD.do_not_final_print):
                    text_to_commit = str()
                    if not commit_text and not RCMD.commit_text: text_to_commit = 'COMMIT'
                    elif commit_text: text_to_commit = commit_text
                    elif RCMD.commit_text: text_to_commit = RCMD.commit_text
                    if submit_result:
                        if RCMD.config_problem:
                            CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = CGI_CLI.result_tag, tag_id = 'submit-result', color = 'red')
                        else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = CGI_CLI.result_tag, tag_id = 'submit-result', color = 'green')
                    else:
                        if RCMD.config_problem:
                            CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = CGI_CLI.result_tag, color = 'red')
                        else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = CGI_CLI.result_tag, color = 'green')
        return command_outputs

    @staticmethod
    def __cleanup__():
        RCMD.output, RCMD.fp = None, None
        try:
            if RCMD.ssh_connection:
                if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
                elif RCMD.use_module == 'paramiko': RCMD.client.close()
                if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DONE.' % \
                    (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT), color = 'gray')
                RCMD.ssh_connection = None
        except: pass

    @staticmethod
    def disconnect():
        RCMD.output, RCMD.fp = None, None
        try:
            if RCMD.ssh_connection:
                if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
                elif RCMD.use_module == 'paramiko': RCMD.client.close()
                if RCMD.printall: CGI_CLI.uprint('DEVICE %s:%s DISCONNECTED.' % \
                    (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT), color = 'gray')
                RCMD.ssh_connection = None
                time.sleep(RCMD.DISCONNECT_TIMEOUT)
        except: pass

    @staticmethod
    def ssh_send_command_and_read_output(chan, prompts, \
        send_data = str(), long_lasting_mode = None, \
        autoconfirm_mode = None, ignore_prompt = None, \
        printall = True):
        '''
        autoconfirm_mode = True ==> CISCO - '\n', HUAWEI - 'Y\n'
        '''
        output, output2, new_prompt = str(), str(), str()
        exit_loop = False
        no_rx_data_counter_100msec, command_counter_100msec = 0, 0
        after_enter_counter_100msec, possible_prompts = 0, []
        last_line_original = str()

        ### FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERED ###
        if chan.recv_ready():
            flush_buffer = chan.recv(9999)
            time.sleep(0.3)
        chan.send(send_data + '\n')
        time.sleep(0.1)

        ### MAIN WHILE LOOP ###################################################
        while not exit_loop:
            if not chan.recv_ready():
                ### NOT RECEIVED ANY DATA #####################################
                buff_read = str()
                time.sleep(0.1)
                no_rx_data_counter_100msec += 1
                command_counter_100msec    += 1
                if after_enter_counter_100msec:
                    after_enter_counter_100msec += 1
            else:
                ### RECEIVED DATA IMMEDIATE ACTIONS ###########################
                no_rx_data_counter_100msec = 0
                buff = chan.recv(9999)
                try:
                    buff_read = str(buff.decode(encoding='utf-8').\
                        replace('\x0d','').replace('\x07','').\
                        replace('\x08','').replace(' \x1b[1D','').replace(u'\u2013',''))
                    output += buff_read
                except:
                    try:
                        buff_read = str(buff.decode(encoding='cp1252').\
                            replace('\x0d','').replace('\x07','').\
                            replace('\x08','').replace(' \x1b[1D','').replace(u'\u2013',''))
                        output += buff_read
                    except:
                        CGI_CLI.uprint('BUFF_ERR[%s][%s]'%(buff,type(buff)), color = 'red')
                        CGI_CLI.uprint(traceback.format_exc(), color = 'magenta')

                ### FIND LAST LINE (STRIPPED), THIS COULD BE PROMPT ###
                last_line_edited = str()
                try: last_line_original = output.splitlines()[-1].strip()
                except: last_line_original = str()

                # FILTER-OUT '(...)' FROM PROMPT IOS-XR/IOS-XE ###
                if RCMD.router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
                    try:
                        last_line_part1 = last_line_original.split('(')[0]
                        last_line_part2 = last_line_original.split(')')[1]
                        last_line_edited = last_line_part1 + last_line_part2
                    except:
                        if 'sysadmin' in last_line_original and '#' in last_line_original:
                            last_line_edited = 'sysadmin#'
                        else: last_line_edited = last_line_original

                ### PRINT LONG LASTING OUTPUTS PER PARTS ######################
                if printall and long_lasting_mode and buff_read and not RCMD.silent_mode:
                    CGI_CLI.uprint('%s' % (buff_read), color = 'gray', no_newlines = True)

                ### PROMPT IN LAST LINE = PROPER END OF COMMAND ###############
                for actual_prompt in prompts:
                    if output.strip().endswith(actual_prompt) or \
                        (last_line_edited and last_line_edited.endswith(actual_prompt)) or \
                        (last_line_original and last_line_original.endswith(actual_prompt)):
                            exit_loop = True
                            break
                if exit_loop: break

                ### IS ACTUAL LAST LINE PROMPT ? IF YES, CONFIRM ##############
                dialog_list = ['?', '[Y/N]:', '[confirm]', '? [no]:']
                for dialog_line in dialog_list:
                    if last_line_original.strip().endswith(dialog_line) or \
                        last_line_edited.strip().endswith(dialog_line):
                        if autoconfirm_mode:
                            ### AUTO-CONFIRM MODE #############################
                            if RCMD.router_type in ["ios-xr","ios-xe",'cisco_ios','cisco_xr']:
                                chan.send('\n')
                            elif RCMD.router_type in ["vrp",'huawei']:
                                chan.send('Y\n')
                            time.sleep(0.2)
                            break
                        else:
                            ### INTERACTIVE QUESTION --> GO AWAY ##############
                            exit_loop = True
                            break
                if exit_loop: break

            ### RECEIVED OR NOT RECEIVED DATA COMMON ACTIONS ##################
            if not long_lasting_mode:
                ### COMMAND TIMEOUT EXIT ######################################
                if command_counter_100msec > RCMD.CMD_TIMEOUT*10:
                    exit_loop = True
                    break

            if long_lasting_mode:
                ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ##############
                if not command_counter_100msec%100 and CGI_CLI.cgi_active:
                    CGI_CLI.uprint("<script>console.log('10s...');</script>", \
                        raw = True)

            ### EXIT SOONER THAN CONNECTION TIMEOUT IF LONG LASTING OR NOT ####
            if command_counter_100msec + 100 > RCMD.CONNECTION_TIMEOUT*10:
                CGI_CLI.uprint("LONG LASTING COMMAND TIMEOUT!!", color = 'red')
                exit_loop = True
                break

            ### IGNORE NEW PROMPT AND GO AWAY #################################
            if ignore_prompt:
                time.sleep(1)
                exit_loop = True
                break

            ### PROMPT FOUND OR NOT ###########################################
            if after_enter_counter_100msec > 0:
                if last_line_original and last_line_original in possible_prompts:
                    new_prompt = last_line_original
                    exit_loop = True
                    break
                if after_enter_counter_100msec > 50:
                    exit_loop = True
                    break

            ### LONG TIME NO RESPONSE - THIS COULD BE A NEW PROMPT ############
            if not long_lasting_mode and no_rx_data_counter_100msec > 100 \
                and after_enter_counter_100msec == 0 and last_line_original:
                ### TRICK IS IF NEW PROMPT OCCURS, HIT ENTER ... ###
                ### ... AND IF OCCURS THE SAME LINE --> IT IS NEW PROMPT!!! ###
                try: last_line_actual = copy.deepcopy(output.strip().splitlines[-1])
                except: last_line_actual = str()
                if last_line_original:
                    possible_prompts.append(copy.deepcopy(last_line_original))
                if last_line_edited:
                    possible_prompts.append(copy.deepcopy(last_line_edited))
                if last_line_actual: possible_prompts.append(last_line_actual)
                chan.send('\n')
                time.sleep(0.1)
                after_enter_counter_100msec = 1
        return output, new_prompt

    @staticmethod
    def ssh_raw_detect_router_type(debug = None):
        ### DETECT DEVICE PROMPT FIRST
        def ssh_raw_detect_prompt(chan, debug = debug):
            output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
            flush_buffer = chan.recv(9999)
            del flush_buffer
            chan.send('\t \n\n')
            time.sleep(0.3)
            while not (last_line and last_but_one_line and last_line == last_but_one_line):
                buff = chan.recv(9999)
                if len(buff)>0:
                    if debug: CGI_CLI.uprint('LOOKING_FOR_PROMPT:',last_but_one_line,last_line, color = 'grey')
                    try:
                        output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                            replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                    except:
                        try:
                            output += str(buff.decode("cp1252").replace('\r','').replace('\x07','').replace('\x08','').\
                            replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                        except: pass
                    if '--More--' or '---(more' in buff.strip():
                        chan.send('\x20')
                        if debug: CGI_CLI.uprint('SPACE_SENT.', color = 'blue')
                        time.sleep(0.3)
                    try: last_line = output.splitlines()[-1].strip().replace('\x20','')
                    except: last_line = 'dummyline1'
                    try:
                        last_but_one_line = output.splitlines()[-2].strip().replace('\x20','')
                        if len(last_but_one_line) == 0:
                            ### vJunos '\x20' --> '\n\nprompt' workarround
                            last_but_one_line = output.splitlines()[-3].strip().replace('\x20','')
                    except: last_but_one_line = 'dummyline2'
            prompt = output.splitlines()[-1].strip()
            if debug: CGI_CLI.uprint('DETECTED PROMPT: \'' + prompt + '\'', color = 'yellow')
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
                if debug: CGI_CLI.uprint('LAST_LINE:',prompts,last_line)
                buff = chan.recv(9999)
                try:
                    output += str(buff.decode("utf-8").replace('\r','').replace('\x07','').replace('\x08','').\
                        replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                except:
                    try:
                        output += str(buff.decode("cp1252").replace('\r','').replace('\x07','').replace('\x08','').\
                            replace('\x1b[K','').replace('\n{master}\n','').replace(u'\u2013',''))
                    except: pass
                if '--More--' or '---(more' in buff.strip():
                    chan.send('\x20')
                    time.sleep(0.3)
                if debug: CGI_CLI.uprint('BUFFER:' + buff, color = 'grey')
                try: last_line = output.splitlines()[-1].strip()
                except: last_line = str()
                for actual_prompt in prompts:
                    if output.endswith(actual_prompt) \
                        or (last_line and last_line.endswith(actual_prompt)) \
                        or actual_prompt in last_line: exit_loop = True
            return output
        # Detect function start
        #asr1k_detection_string = 'CSR1000'
        #asr9k_detection_string = 'ASR9K|IOS-XRv 9000'
        router_os, prompt = str(), str()

        ### 1-CONNECTION ONLY, connection opened in RCMD.connect ###
        # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
        # \n\n get prompt as last line

        if CGI_CLI.timestamp:
            CGI_CLI.uprint('RCMD.connect - before ssh_raw_detect_prompt.\n', \
                no_printall = not printall, tag = 'debug')

        prompt = ssh_raw_detect_prompt(RCMD.ssh_connection, debug=debug)

        if CGI_CLI.timestamp:
            CGI_CLI.uprint('RCMD.connect - after ssh_raw_detect_prompt.\n', \
                no_printall = not printall, tag = 'debug')

        ### test if this is HUAWEI VRP
        if prompt and not router_os:
            command = 'display version | include (Huawei)\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'Huawei Versatile Routing Platform Software' in output: router_os = 'vrp'
        ### JUNOS
        if prompt and not router_os:
            command = 'show version | match Software\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'JUNOS' in output: router_os = 'junos'

        ### test if this is CISCO IOS-XR, IOS-XE or JUNOS
        if prompt and not router_os:
            command = 'show version | include Software\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'iosxr-' in output or 'Cisco IOS XR Software' in output:
                router_os = 'ios-xr'
                if 'ASR9K' in output or 'IOS-XRv 9000' in output: RCMD.router_version = 'ASR9K'
            elif 'Cisco IOS-XE software' in output or 'Cisco IOS XE Software' in output:
                router_os = 'ios-xe'
                if 'CSR1000' in output: RCMD.router_version = 'ASR1K'

        if prompt and not router_os:
            command = 'uname -a\n'
            output = ssh_raw_read_until_prompt(RCMD.ssh_connection, command, [prompt], debug=debug)
            if 'LINUX' in output.upper(): router_os = 'linux'
        if not router_os:
            CGI_CLI.uprint("\nCannot find recognizable OS in %s" % (output), color = 'magenta')
        netmiko_os = str()
        if router_os == 'ios-xe': netmiko_os = 'cisco_ios'
        if router_os == 'ios-xr': netmiko_os = 'cisco_xr'
        if router_os == 'junos': netmiko_os = 'juniper'
        if router_os == 'linux': netmiko_os = 'linux'
        if router_os == 'vrp': netmiko_os = 'huawei'
        return netmiko_os, prompt

    @staticmethod
    def get_json_from_vision(URL = None):
        if RCMD.USERNAME and RCMD.PASSWORD:
            os.environ['CURL_AUTH_STRING'] = '%s:%s' % \
                (RCMD.USERNAME,RCMD.PASSWORD)
            if URL: url = URL
            else: url = 'https://vision.opentransit.net/onv/api/nodes/'
            local_command = 'curl -u ${CURL_AUTH_STRING} -m 5 %s' % (url)
            try:
                result_list = LCMD.run_commands(\
                    {'unix':[local_command]}, printall = None, ommit_logging = True)
                RCMD.vision_api_json_string = copy.deepcopy(result_list[0])
            except: pass
            os.environ['CURL_AUTH_STRING'] = '-'

    @staticmethod
    def get_IP_from_vision(DEVICE_NAME = None):
        device_ip_address = str()
        if not RCMD.vision_api_json_string: RCMD.get_json_from_vision()
        if RCMD.vision_api_json_string and DEVICE_NAME:
            try: vision_json = json.loads(RCMD.vision_api_json_string)
            except: vision_json = {}
            for router_json in vision_json.get('results',[]):
                if router_json.get('name',str()).upper() == DEVICE_NAME.upper():
                    device_ip_address = router_json.get('ip',str())
        CGI_CLI.uprint('VISION_IP: %s' % (device_ip_address), tag = "debug")
        return device_ip_address



class LCMD(object):

    @staticmethod
    def init(printall = None):
        LCMD.initialized = True
        LCMD.printall = printall

    @staticmethod
    def run_command(cmd_line = None, printall = None,
        chunked = None, timeout_sec = 5000, ommit_logging = None):
        os_output, cmd_list, timer_counter_100ms = str(), None, 0

        if sys.version_info.major <= 2:
            ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE ###
            try:
                if LCMD.initialized: pass
            except: LCMD.init(printall = printall)
            if cmd_line:
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue', ommit_logging = True)
                if not ommit_logging:
                    if CGI_CLI.cgi_active:
                        CGI_CLI.logtofile('<p style="color:blue;">' + 'LOCAL_COMMAND: ' + cmd_line + '</p>', raw_log = True)
                    else:
                        CGI_CLI.logtofile('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
                try:
                    if chunked:
                        os_output, timer_counter_100ms = str(), 0
                        CommandObject = subprocess.Popen(cmd_line,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT, shell=True)
                        while CommandObject.poll() is None:
                            stdoutput = str(CommandObject.stdout.readline())
                            while stdoutput:
                                if stdoutput:
                                    os_output += copy.deepcopy(stdoutput) + '\n'
                                    if printall:
                                        CGI_CLI.uprint(stdoutput.strip(), timestamp = 'no' , color = 'gray')
                                stdoutput = str(CommandObject.stdout.readline())
                            time.sleep(0.1)
                            timer_counter_100ms += 1
                            if timer_counter_100ms > timeout_sec * 10:
                                CommandObject.terminate()
                                break
                    else:
                        os_output = subprocess.check_output(str(cmd_line), \
                            stderr=subprocess.STDOUT, shell=True).decode(CGI_CLI.sys_stdout_encoding)

                except (subprocess.CalledProcessError) as e:
                    os_output = str(e.output)
                    if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                    CGI_CLI.logtofile('EXITCODE: %s\n' % (str(e.returncode)))
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    CGI_CLI.logtofile(exc_text + '\n')
        elif cmd_line:
            ### PYTHON 3 ###
            if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue', ommit_logging = True)
            if not ommit_logging:
                if CGI_CLI.cgi_active:
                    CGI_CLI.logtofile('<p style="color:blue;">' + 'LOCAL_COMMAND: ' + cmd_line + '</p>', raw_log = True)
                else:
                    CGI_CLI.logtofile('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
            try:
                os_output = subprocess.run([cmd_line], check=True, \
                    stdout=subprocess.PIPE, \
                    stderr=subprocess.STDOUT, text=True)
            except (subprocess.CalledProcessError) as e:
                os_output = str(e.output)
                if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                CGI_CLI.logtofile('EXITCODE: %s\n' % (str(e.returncode)))
            except:
                exc_text = traceback.format_exc()
                CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                CGI_CLI.logtofile(exc_text + '\n')

        ### OUTPUT PRINTING AND LOGGING ####
        if not chunked and os_output and printall:
            CGI_CLI.uprint(os_output, tag = 'pre', timestamp = 'no', ommit_logging = True)
        if not ommit_logging:
            if CGI_CLI.cgi_active:
                CGI_CLI.logtofile('\n<pre>' + \
                    CGI_CLI.html_escape(os_output, pre_tag = True) + \
                    '\n</pre>\n', raw_log = True)
            else: CGI_CLI.logtofile(os_output + '\n')
        return os_output

    @staticmethod
    def run_paralel_commands(cmd_data = None, printall = None, \
        timeout_sec = 5000, custom_text = None, check_exitcode = None):
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(printall = printall)
        commands_ok = None
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            commands_ok = True
            ### START LOOP ###
            CommandObjectList = []
            for cmd_line in cmd_list:
                os_output = str()
                try:
                    actual_CommandObject = subprocess.Popen(cmd_line, \
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    CommandObjectList.append(actual_CommandObject)
                    if printall: CGI_CLI.uprint("LOCAL_COMMAND_(START)[%s]: %s" % (str(actual_CommandObject), str(cmd_line)), color = 'blue')
                    CGI_CLI.logtofile('LOCAL_COMMAND_(START)[%s]: %s' % (str(actual_CommandObject), str(cmd_line)) + '\n')
                except (subprocess.CalledProcessError) as e:
                    os_output = str(e.output)
                    if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                    CGI_CLI.logtofile('EXITCODE: %s\n' % (str(e.returncode)))
                    commands_ok = False
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    CGI_CLI.logtofile(exc_text + '\n')
                    commands_ok = False
            if not printall:
                CGI_CLI.uprint("%s: %d   " % (str(custom_text) if custom_text else "RUNNING LOCAL_COMMANDS", len(CommandObjectList)), no_newlines = True)
            ### LOOP WAITING END ###
            timer_counter_100ms = 0
            while len(CommandObjectList)>0:
                for actual_CommandObject in CommandObjectList:
                    timer_counter_100ms += 1
                    time.sleep(0.1)
                    outputs = str()
                    actual_poll = actual_CommandObject.poll()
                    if actual_poll is None: pass
                    else:
                        StdOutText, StdErrText = actual_CommandObject.communicate()
                        outputs = '\n'.join([StdOutText.decode(), StdErrText.decode()])
                        ExitCode = actual_CommandObject.returncode
                        if check_exitcode and ExitCode != 0: commands_ok = False
                        if printall: CGI_CLI.uprint("LOCAL_COMMAND_(END)[%s]: %s\n%s" % (str(actual_CommandObject), str(cmd_line), outputs), color = 'gray')
                        CGI_CLI.logtofile('LOCAL_COMMAND_(END)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                        CommandObjectList.remove(actual_CommandObject)
                        continue
                    if timer_counter_100ms % 10 == 0:
                        if printall: CGI_CLI.uprint("%d LOCAL_COMMAND%s RUNNING." % (len(CommandObjectList), 'S are' if len(CommandObjectList) > 1 else ' is'))
                        else: CGI_CLI.uprint(" %d   " % (len(CommandObjectList)), no_newlines = True)
                    if timer_counter_100ms % 300 == 0: CGI_CLI.uprint('\n', timestamp = 'no')
                    if timer_counter_100ms > timeout_sec * 10:
                        if printall: CGI_CLI.uprint("LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s" % (str(actual_CommandObject), str(cmd_line), outputs), color = 'red')
                        CGI_CLI.logtofile('LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                        actual_CommandObject.terminate()
                        CommandObjectList.remove(actual_CommandObject)
                        commands_ok = False
            if not printall: CGI_CLI.uprint("\n", timestamp = 'no')
        return commands_ok

    @staticmethod
    def run_commands(cmd_data = None, printall = None, ommit_logging = None):
        """
        FUNCTION: LCMD.run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        """
        os_outputs =  None
                ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(printall = printall)
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            os_outputs = []
            for cmd_line in cmd_list:
                os_output = str()
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue', ommit_logging = True)
                if not ommit_logging:
                    if CGI_CLI.cgi_active:
                        CGI_CLI.logtofile('<p style="color:blue;">' + 'LOCAL_COMMAND: ' + cmd_line + '</p>', raw_log = True)
                    else:
                        CGI_CLI.logtofile('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
                try: os_output = subprocess.check_output(str(cmd_line), stderr=subprocess.STDOUT, shell=True).decode(CGI_CLI.sys_stdout_encoding)
                except (subprocess.CalledProcessError) as e:
                    os_output = str(e.output)
                    if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                    CGI_CLI.logtofile('EXITCODE: %s\n' % (str(e.returncode)))
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    CGI_CLI.logtofile(exc_text + '\n')
                if os_output and printall: CGI_CLI.uprint(os_output, tag = 'pre', timestamp = 'no')
                if not ommit_logging:
                    if CGI_CLI.cgi_active:
                        CGI_CLI.logtofile('\n<pre>' + \
                            CGI_CLI.html_escape(os_output, pre_tag = True) + \
                            '\n</pre>\n', raw_log = True)
                    else: CGI_CLI.logtofile(os_output + '\n')
                os_outputs.append(os_output)
        return os_outputs

    @staticmethod
    def eval_command(cmd_data = None, printall = None):
        """
        NOTE: by default - '\\n' = insert newline to text, '\n' = interpreted line
        """
        local_output = None
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(printall = printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            if printall: CGI_CLI.uprint("EVAL: %s" % (cmd_data))
            try:
                local_output = eval(cmd_data)
                if printall: CGI_CLI.uprint(str(local_output), color= 'gray', timestamp = 'no')
                CGI_CLI.logtofile('EVAL: ' + cmd_data + '\n' + str(local_output) + '\n')
            except Exception as e:
                if printall:CGI_CLI.uprint('EVAL_PROBLEM[' + str(e) + ']')
                CGI_CLI.logtofile('EVAL_PROBLEM[' + str(e) + ']\n', color = 'magenta')
        return local_output

    @staticmethod
    def exec_command(cmd_data = None, printall = None, escape_newline = None):
        """
        NOTE:
              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(printall = printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            if printall: CGI_CLI.uprint("EXEC: %s" % (cmd_data))
            CGI_CLI.logtofile('EXEC: ' + cmd_data + '\n')
            ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
            try:
                if escape_newline:
                    edict = {}; eval(compile(cmd_data.replace('\n', '\\n'),\
                        '<string>', 'exec'), globals(), edict)
                else: edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
            except Exception as e:
                if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', color = 'magenta')
                CGI_CLI.logtofile('EXEC_PROBLEM[' + str(e) + ']\n')
        return None


    @staticmethod
    def exec_command_try_except(cmd_data = None, \
        printall = None, escape_newline = None):
        """
        NOTE: This method can access global variable, expects '=' in expression,
              in case of except assign value None

              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(printall = printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            try:
                if '=' in cmd_data:
                    if escape_newline:
                        cmd_ex_data = 'global %s\ntry: %s = %s \nexcept: %s = None' % \
                            (cmd_data.replace('\n', '\\n').split('=')[0].\
                            strip().split('[')[0],cmd_data.split('=')[0].strip(), \
                            cmd_data.replace('\n', '\\n').split('=')[1].strip(), \
                            cmd_data.split('=')[0].strip())
                    else:
                        cmd_ex_data = 'global %s\ntry: %s = %s \nexcept: %s = None' % \
                            (cmd_data.split('=')[0].strip().split('[')[0], \
                            cmd_data.split('=')[0].strip(), \
                            cmd_data.split('=')[1].strip(), \
                            cmd_data.split('=')[0].strip())
                else: cmd_ex_data = cmd_data
                if printall: CGI_CLI.uprint("EXEC: \n%s" % (cmd_ex_data))
                CGI_CLI.logtofile('EXEC: \n' + cmd_ex_data + '\n')
                ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                edict = {}; eval(compile(cmd_ex_data, '<string>', 'exec'), globals(), edict)
                #CGI_CLI.uprint("%s" % (eval(cmd_data.split('=')[0].strip())))
            except Exception as e:
                if printall: CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', \
                                 color = 'magenta')
                CGI_CLI.logtofile('EXEC_PROBLEM[' + str(e) + ']\n')
        return None

###############################################################################

class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled

    def __init__(self, host = None, user = None, password = None, database = None):
        if int(sys.version_info[0]) == 3 and not 'pymysql.connect' in sys.modules: import pymysql
        elif int(sys.version_info[0]) == 2 and not 'mysql.connector' in sys.modules: import mysql.connector
        default_ipxt_data_collector_delete_columns = ['id','last_updated']
        self.sql_connection = None
        try:
            if not CGI_CLI.initialized:
                CGI_CLI.init_cgi(chunked = True)
                if printall: CGI_CLI.print_args()
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
        except Exception as e: CGI_CLI.uprint(' ==> SQL problem [%s]' % (str(e)), color = 'magenta')

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
        columns = []
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try:
                cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s';"%(table_name))
                records = cursor.fetchall()
                ### 4TH COLUMN IS COLUMN NAME
                ### OUTPUTDATA STRUCTURE IS: '[(SQL_RESULT)]' --> records[0] = UNPACK []
                for item in records:
                    try: new_item = item[3].decode(CGI_CLI.sys_stdout_encoding)
                    except: new_item = item[3]
                    columns.append(new_item)
            except Exception as e: CGI_CLI.uprint(' ==> SQL problem [%s]' % (str(e)), color = 'magenta')
            try: cursor.close()
            except: pass
            if len(columns) == 0:
                CGI_CLI.uprint('SQL PROBLEM[%s table has no existing columns]' % \
                    (table_name), tag = 'h3',color = 'magenta')
        return columns

    def sql_read_all_table_columns_to_void_dict(self, table_name, \
        ommit_columns = None):
        '''
        ommit_columns - list of columns which will be ignored
        '''
        data = collections.OrderedDict()
        columns = self.sql_read_all_table_columns(table_name)
        for column in columns:
            if ommit_columns:
                if column in ommit_columns or column.upper() in ommit_columns: continue
            data[column] = str()
        return data

    def sql_read_sql_command(self, sql_command):
        '''NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE'''
        lines = []
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try:
                cursor.execute(sql_command)
                records = cursor.fetchall()
                ### OUTPUTDATA STRUCTURE IS: '[(SQL_LINE1),...]' --> records[0] = UNPACK []
                ### WORKARROUND FOR BYTEARRAYS WHICH ARE NOT JSONIZABLE
                for line in records:
                    columns = []
                    for item in line:
                        try: new_item = item.decode(CGI_CLI.sys_stdout_encoding)
                        except:
                           try: new_item = str(item)
                           except: new_item = item
                        columns.append(new_item)
                    lines.append(columns)
            except Exception as e: CGI_CLI.uprint(' ==> SQL problem [%s]' % (str(e)), color = 'magenta')
            try: cursor.close()
            except: pass
            ### FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
        return lines

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
            except Exception as e: CGI_CLI.uprint(' ==> SQL problem [%s]' % (str(e)), color = 'magenta')
            try: cursor.close()
            except: pass
            CGI_CLI.uprint('SQL_CMD[%s]' % (sql_command))
        return None

    def sql_write_table_from_dict(self, table_name, dict_data, \
        where_string = None, update = None):

        columns_string, values_string = str(), str()
        name_equals_value_string = str()

        ### EXIT IF NOT CONNECTED #############################################
        if not self.sql_is_connected(): return None

        ### EXIT IF TABLE COLUMNS DOES NOT EXISTS #############################
        existing_sql_table_columns = self.sql_read_all_table_columns(table_name)
        if len(existing_sql_table_columns) == 0: return None

        ### ASSUMPTION: LIST OF COLUMNS HAS CORRECT ORDER!!! ##################
        for key in existing_sql_table_columns:
            if key in list(dict_data.keys()):
                if len(columns_string) > 0: columns_string += ','
                if len(values_string) > 0: values_string += ','
                if len(name_equals_value_string) > 0:
                    name_equals_value_string += ','
                ### WRITE KEY/COLUMNS_STRING ##################################
                columns_string += '`' + key + '`'
                name_equals_value_string += key + '='
                ### BE AWARE OF (LIST/STRING) DATA TYPE #######################
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
                    name_equals_value_string += "'" + item_string + "'"
                ### STRING TYPE ###############################################
                elif isinstance(dict_data.get(key,""), (six.string_types)):
                    values_string += "'" + str(dict_data.get(key,"")) + "'"
                    name_equals_value_string += "'" + str(dict_data.get(key,"")) + "'"
                else:
                    values_string += "'" + str(dict_data.get(key,"")) + "'"
                    name_equals_value_string += "'" + str(dict_data.get(key,"")) + "'"

        ### FINALIZE SQL_STRING - INSERT ######################################
        if not update:
            if table_name and columns_string:
               sql_string = """INSERT INTO `%s` (%s) VALUES (%s);""" \
                   % (table_name, columns_string, values_string)
               self.sql_write_sql_command(sql_string)
               return True
        else:
            ### SQL UPDATE ####################################################
            # UPDATE Customers
            # SET ContactName = 'Alfred Schmidt', City= 'Frankfurt'
            # WHERE CustomerID = 1;
            if table_name and name_equals_value_string and where_string:
                sql_string = """UPDATE %s SET %s WHERE %s;""" % \
                    (table_name, name_equals_value_string, where_string)
                self.sql_write_sql_command(sql_string)
                return True
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

    def sql_read_last_record_to_dict(self, table_name = None, from_string = None, \
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
        columns_list = self.sql_read_all_table_columns(table_name_or_from_string)
        data_list = self.sql_read_table_last_record( \
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

    def sql_read_table_records(self, select_string = None, from_string = None, \
        where_string = None, order_by = None):
        """NOTES: - FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
                  - order_by - needed to append ASC|DESC on end of string"""
        check_data = None
        if not select_string: select_string = '*'
        #SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id) FROM ipxt_data_collector \
        #WHERE username='mkrupa' AND device_name='AUVPE3');
        if self.sql_is_connected():
            if from_string:
                sql_string = "SELECT %s FROM %s%s%s;" % (select_string, from_string, \
                    ' WHERE %s' % (where_string) if where_string else str(), \
                    ' ORDER BY %s' % (order_by) if order_by else str() \
                    )
                check_data = self.sql_read_sql_command(sql_string)
        return check_data

    def sql_read_records_to_dict_list(self, table_name = None, from_string = None, \
        select_string = None, where_string = None, order_by = None, \
        delete_columns = None):
        """sql_read_last_record_to_dict - MAKE DICTIONARY FROM LAST TABLE RECORD
           NOTES: -'table_name' is alternative name to 'from_string'
                  - it always read last record dependent on 'where_string'
                    which contains(=filters by) username,device_name,vpn_name
                  - order_by - needed to append ASC|DESC on end of string
        """
        dict_data, dict_list = collections.OrderedDict(), []
        table_name_or_from_string = None
        if not select_string: select_string = '*'
        if table_name:  table_name_or_from_string = table_name
        if from_string: table_name_or_from_string = from_string
        columns_list = self.sql_read_all_table_columns(table_name_or_from_string)
        data_list = self.sql_read_table_records( \
            from_string = table_name_or_from_string, \
            select_string = select_string, where_string = where_string,
            order_by = order_by)
        ### COLUMNS ARE IN SELECT STRING IF SELECT STRING EXISTS ##############
        if select_string != '*':
            columns_list = [ column.strip() for column in select_string.split(',') ]
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





###############################################################################

def generate_logfilename(prefix = None, USERNAME = None, suffix = None, \
    directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(DIR,'logs')
    if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
    if os.path.exists(LOGDIR):
        html_extention = 'htm' if CGI_CLI.cgi_active else str()
        if not prefix: filename_prefix = os.path.join(LOGDIR,'device')
        else: filename_prefix = prefix
        if not suffix: filename_suffix = '%slog' % (html_extention)
        else: filename_suffix = suffix
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,sys.argv[0].replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/')\
            .split('/')[-1],USERNAME,filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath

##############################################################################

def do_scp_one_file_to_more_devices(true_sw_release_file_on_server = None, \
    device_list = None, USERNAME = None, PASSWORD = None , device_drive_string = None, \
    printall = None, router_type = None):
    """
    COPY ALL FILES FROM SERVER TO DEVICE
    """
    if true_sw_release_file_on_server and len(device_list)>0:
        os.environ['SSHPASS'] = PASSWORD
        time.sleep(2)
        directory,dev_dir,file,md5,fsize = true_sw_release_file_on_server
        cp_cmd_list, local_command = [], str()
        ### ONLY 1 SCP CONNECTION PER ROUTER ###
        for device in device_list:
            if router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s 1>/dev/null 2>/dev/null &' \
                    % (os.path.join(directory, file), USERNAME, device, \
                    '%s%s' % (device_drive_string, os.path.join(dev_dir, file)))
            ### HUAWEI MUST NOT HAVE /cfcard: , cfcard only!!! ###
            elif router_type == 'huawei':
                local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:%s 1>/dev/null 2>/dev/null &' \
                    % (os.path.join(directory, file), USERNAME, device, \
                    '%s%s' % (device_drive_string, os.path.join(dev_dir, file)))
            elif router_type == 'juniper':
                local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:%s 1>/dev/null 2>/dev/null &' \
                    % (os.path.join(directory, file), USERNAME, device, \
                    '%s' % (os.path.join(dev_dir, file)))
            CGI_CLI.uprint(local_command, tag = 'debug', no_printall = not printall)
            os.system(local_command)
            CGI_CLI.uprint('scp start file %s, (file size %.2fMB) to device %s' % \
                (file, float(fsize)/1048576, device))
            time.sleep(2)
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
        time.sleep(2)
    return None

##############################################################################

def do_scp_one_file_to_more_devices_per_needed_to_copy_list(\
    true_sw_release_file_on_server = None, missing_files_per_device_list = None,\
    device_list = None, USERNAME = None, PASSWORD = None , device_drive_string = None, \
    printall = None, router_type = None):
    """
    COPY MISSING FILES FROM SERVER TO DEVICE
    """
    if true_sw_release_file_on_server and len(device_list)>0:
        os.environ['SSHPASS'] = PASSWORD
        time.sleep(2)
        directory,dev_dir,file,md5,fsize = true_sw_release_file_on_server
        cp_cmd_list, local_command = [], str()
        ### ONLY 1 SCP CONNECTION PER ROUTER ###
        for device in device_list:
            for device2, missing_or_bad_files_per_device in missing_files_per_device_list:
                directory2, dev_dir2, file2, md52, fsize2 = missing_or_bad_files_per_device
                if '%s%s' % (device_drive_string, os.path.join(dev_dir, file)) == '%s%s' % (device_drive_string, os.path.join(dev_dir2, file2)) \
                    and device == device2:
                    if router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                        local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:/%s 1>/dev/null 2>/dev/null &' \
                            % (os.path.join(directory, file), USERNAME, device, \
                            '%s%s' % (device_drive_string, os.path.join(dev_dir, file)))
                    elif router_type == 'huawei':
                        local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:%s 1>/dev/null 2>/dev/null &' \
                            % (os.path.join(directory, file), USERNAME, device, \
                            '%s%s' % (device_drive_string, os.path.join(dev_dir, file)))
                    elif router_type == 'juniper':
                        local_command = 'sshpass -e scp -v -o StrictHostKeyChecking=no %s %s@%s:%s 1>/dev/null 2>/dev/null &' \
                            % (os.path.join(directory, file), USERNAME, device, \
                            '%s' % (os.path.join(dev_dir, file)))
                    CGI_CLI.uprint(local_command, tag = 'debug', no_printall = not printall)
                    os.system(local_command)
                    CGI_CLI.uprint('scp start file %s, (file size %.2fMB) to device %s' % \
                        (file, float(fsize)/1048576, device))
                    time.sleep(3)
        ### SECURITY REASONS ###
        os.environ['SSHPASS'] = '-'
        time.sleep(2)
    return None

##############################################################################

def get_existing_sw_release_list(brand_subdir = None, type_subdir = None):
    sw_release_list, sw_release_list_raw, default_sw_release = [], [], str()

    if brand_subdir and type_subdir:
        ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
        LOCAL_SW_SUBTYPE_DIR = os.path.abspath(os.path.join(os.sep,'home',\
            'tftpboot',brand_subdir, type_subdir))
        try:
            sw_release_list_raw = [ str(subdir) for subdir in os.listdir(LOCAL_SW_SUBTYPE_DIR) ]
        except: pass
        for release in sw_release_list_raw:
            try:
                ### TRICK:DIRECTORY (with or without dots) MUST BE A NUMBER ###
                if os.path.isdir(os.path.join(LOCAL_SW_SUBTYPE_DIR,release)):
                    forget_it = int(release.replace('.',''))
                    sw_release_list.append(release)
                ### MAYBE DIRECTORIES ARE NOT DONE, SO CHECK FILES ###
                elif os.path.isfile(os.path.join(LOCAL_SW_SUBTYPE_DIR,release)):
                    for actual_file_type_with_subdir in sw_file_types_list:
                        actual_file_type_subdir, actual_file_name = os.path.split(actual_file_type_with_subdir)
                        ### PROBLEM ARE '*' IN FILE NAME ###
                        for part_of_name in actual_file_name.split('*'):
                            if part_of_name.upper() in release.upper():
                                sw_release_list.append(release)
            except: pass

        ### SORT AND CLEAN SW RELEASE LIST ####################################
        if len(sw_release_list) > 0:
            sw_release_set = set(sw_release_list)
            del sw_release_list
            sw_release_list = list(sw_release_set)
            del sw_release_set
            sw_release_list.sort(reverse = True)

            ### DELETE NOT-PROPER FILES #######################################
            for sw_item in sw_release_list:
                if '.pptx' in sw_item: sw_release_list.remove(sw_item)
                if '.xls' in sw_item: sw_release_list.remove(sw_item)
                if '.doc' in sw_item: sw_release_list.remove(sw_item)

            ### DEFAULT SW RELEASE ############################################
            default_sw_release = sw_release_list[0]
    return sw_release_list, default_sw_release

###############################################################################

def does_local_directory_or_file_exist_by_ls_l(directory_or_file, printall = None):
    this_is_directory, file_found = None, None
    ### BUG: os.path.exists RETURNS ALLWAYS FALSE, SO I USE OS ls -l ######
    ls_all_result = LCMD.run_commands({'unix':['ls -l %s' % (directory_or_file)]}, printall = printall)
    if 'NO SUCH FILE OR DIRECTORY' in ls_all_result[0].upper(): pass
    else:
        if ls_all_result[0].strip().split()[0] == 'total':
            this_is_directory = True
        try:
            if directory_or_file.split('/')[-1] and directory_or_file.split('/')[-1] in ls_all_result[0].strip():
                file_found = True
        except: pass
    return this_is_directory, file_found

### def GET LOCAL SUB-DIRS ####################################################

def get_local_subdirectories(brand_raw = None, type_raw = None):
    """
    type_subdir_on_device - For the x2800..c4500 and the Huawei the files just
        go in the top level directory and for Juniper it goes in /var/tmp/
    """
    brand_subdir, type_subdir_on_server, file_types = str(), str(), []
    type_subdir_on_device = str()
    if type_raw:
        brand_raw_assumed = 'CISCO'
        if 'ASR9K' in type_raw.upper() \
            or 'ASR-9' in type_raw.upper() \
            or '9000' in type_raw.upper():
            type_subdir_on_server = 'ASR9K'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
        elif 'NCS' in type_raw.upper():
            type_subdir_on_server = 'NCS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'ASR1001' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1001X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1001x*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'ASR1002-X' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1002x*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'ASR1002-HX' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002HX/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr100*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'CRS' in type_raw.upper():
            type_subdir_on_server = 'CRS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'C29' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            type_subdir_on_device = ''
            file_types = ['c2900*.bin']
        elif '2901' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            type_subdir_on_device = ''
            file_types = ['c2900*.bin']
        elif 'C35' in type_raw.upper():
            type_subdir_on_server = 'C3500'
            type_subdir_on_device = ''
            file_types = ['c35*.bin']
        elif 'C36' in type_raw.upper():
            type_subdir_on_server = 'C3600'
            type_subdir_on_device = ''
            file_types = ['c36*.bin']
        elif 'C37' in type_raw.upper():
            type_subdir_on_server = 'C3700'
            type_subdir_on_device = ''
            file_types = ['c37*.bin']
            brand_raw_assumed = 'CISCO'
        elif 'C38' in type_raw.upper():
            type_subdir_on_server = 'C3800'
            type_subdir_on_device = ''
            file_types = ['c38*.bin']
        elif 'ISR43' in type_raw.upper():
            type_subdir_on_server = 'C4321'
            type_subdir_on_device = ''
            file_types = ['isr43*.bin']
        elif 'C45' in type_raw.upper():
            type_subdir_on_server = 'C4500'
            type_subdir_on_device = ''
            file_types = ['cat45*.bin']
            brand_raw_assumed = 'CISCO'
        elif 'MX20' in type_raw.upper():
            type_subdir_on_server = 'MX'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'MX480' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'VMX' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'NE40' in type_raw.upper():
            type_subdir_on_server = 'V8R10'
            type_subdir_on_device = ''
            file_types = ['Patch/*.PAT','*.cc']
            brand_raw_assumed = 'HUAWEI'

        ### BRAND ASSUMPTION IF NOT INSERTED ###
        if not brand_raw: brand_subdir = brand_raw_assumed.upper()
        else: brand_subdir = brand_raw.upper()
    return brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types

##############################################################################

def does_run_scp_processes(printall = None):
    scp_list, scp_ps_list = [], []
    split_string = 'scp -v -o StrictHostKeyChecking=no'
    my_ps_result = LCMD.run_commands({'unix':["ps -ef | grep -v grep | grep scp"]},
        printall = printall)
    if my_ps_result:
        for line in str(my_ps_result[0]).splitlines():
            try: scp_ps_list.append(line.split()[1])
            except: pass
            if split_string in line:
                if not 'sshpass' in line:
                    try:
                        files_string = line.split(split_string)[1].strip()
                        server_file = files_string.split()[0]
                        device_user = files_string.split()[1].split('@')[0]
                        device = files_string.split()[1].split('@')[1].split(':')[0]

                        ### TRICK - GET DEVICE TYPE FROM SCP COMMAND LINE #####
                        if 'JUNIPER' in line.upper():
                            device_file = files_string.split()[1].split(device+':')[1]
                        ### HUAWEI SCP WITHOUT '/', CISCO IOS delete '/' ###
                        else:
                            try: device_file = files_string.split()[1].split(device+':/')[1]
                            except: device_file = files_string.split()[1].split(device+':')[1]

                        pid = line.split()[1]
                        ppid = line.split()[2]
                        scp_list.append([server_file, device_file, device, device_user, pid, ppid])
                    except: pass
    return scp_list, scp_ps_list

##############################################################################

def does_run_script_processes(my_pid_only = None, printall = None):
    running_pid_list = []
    try:
        split_string = sys.argv[0].split('/')[-1]
    except: split_string = None
    my_pid = str(os.getpid())
    my_ps_result = LCMD.run_commands({'unix':["ps -ef | grep -v grep | grep %s" % (split_string)]},
        printall = printall)
    if my_ps_result:
        for line in str(my_ps_result[0]).splitlines():
            if split_string and split_string in line:
                try:
                    if my_pid != line.split()[1]:
                        running_pid_list.append(line.split()[1])
                        CGI_CLI.uprint('WARNING: Running %s process PID = %s !' % \
                            (split_string, line.split()[1]), tag = 'warning', stop_button = line.split()[1])
                except: pass
    return running_pid_list

##############################################################################

def kill_stalled_scp_processes(device = None, device_file = None, printall = None):
    ### CHECK PS ###
    def do_check_ps(device_file = None, printall = None):
        pid_list = []
        split_string = 'scp -v '
        my_ps_result = LCMD.run_commands({'unix':["ps -ef | grep -v grep | grep scp"]},
            printall = printall)
        if my_ps_result:
            for line in str(my_ps_result[0]).splitlines():
                try: scp_ps_list.append(line.split()[1])
                except: pass
                if split_string in line:
                    if str(device_file) in line and \
                        str(device).upper() in line.upper():
                        try: pid_list.append(line.split()[1])
                        except: pass
        return pid_list

    ### KILL PS ###
    def do_kill_ps(pid_list = None, printall = None, minus_nine = None):
        minus_nine_string = str()
        if len(pid_list) > 0:
            if minus_nine: minus_nine_string = '-9 '
            kill_cmds = {'unix':[]}
            for pid in pid_list:
                kill_cmds['unix'].append("kill %s%s" % (minus_nine_string,str(pid)))
            my_ps_result = LCMD.run_commands(kill_cmds, printall = printall)

    pid_list = do_check_ps(device_file = device_file, printall = printall)
    if len(pid_list) > 0:
        do_kill_ps(pid_list = pid_list, printall = printall)
        time.sleep(5)

        pid_list = do_check_ps(device_file = device_file, printall = printall)
        if len(pid_list) > 0:
            do_kill_ps(pid_list = pid_list, printall = printall, minus_nine = True)
            time.sleep(5)
        pid_list = do_check_ps(device_file = device_file, printall = printall)
        try_it = 0
        while (len(pid_list) > 0 and try_it < 4):
            try_it += 1
            time.sleep(5)
            pid_list = do_check_ps(device_file = device_file, printall = printall)
        if len(pid_list) > 0:
            result = 'PROBLEM TO KILL PROCESSES [%s] !' % (','.join(pid_list))
            CGI_CLI.uprint(result , color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
            sys.exit(0)


###############################################################################

def check_percentage_of_copied_files(scp_list = [], USERNAME = None, \
    PASSWORD = None, printall = None):
    device_file_percentage_list = []
    for server_file, device_file, device, device_user, pid, ppid in scp_list:
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, silent_mode = True)
            if RCMD.ssh_connection:
                dir_device_cmd = {
                    'cisco_ios':['dir %s' % (device_file)],
                    'cisco_xr':['dir %s' % (device_file)],
                    'juniper':['file list %s detail' % (device_file)],
                    'huawei':['dir %s' % (device_file)]
                }
                dir_one_output = RCMD.run_commands(dir_device_cmd, printall = printall)
                device_filesize_in_bytes = 0
                if RCMD.router_type == 'cisco_xr':
                    ### dir file gets output without 'harddisk:/'!!! ###
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split('/')[-1] in line:
                                try: device_filesize_in_bytes = float(line.split()[3])
                                except:
                                    ### SOME XR GETS FILE SIZE IN 2ND COLUMN ###
                                    try: device_filesize_in_bytes = float(line.split()[2])
                                    except: pass
                        except: pass
                if RCMD.router_type == 'cisco_ios':
                    ### dir file gets output without any path ###
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split('/')[-1] in line:
                                try: device_filesize_in_bytes = float(line.split()[2])
                                except: pass
                        except: pass
                if RCMD.router_type == 'huawei':
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split('/')[-1] in line:
                                try: device_filesize_in_bytes = float(line.split()[2].replace(',',''))
                                except: pass
                        except: pass
                if RCMD.router_type == 'juniper':
                    for line in dir_one_output[0].splitlines():
                        try:
                            if device_file.split('/')[-1] in line:
                                try: device_filesize_in_bytes = float(line.split()[4])
                                except: pass
                        except: pass
                server_filesize_in_bytes = float(os.stat(server_file).st_size)
                percentage = float(100*device_filesize_in_bytes/server_filesize_in_bytes)
                CGI_CLI.uprint('Device %s file %s    %.2f%% copied.' % (device, device_file, \
                    percentage), color = 'blue')
                device_file_percentage_list.append([device, device_file, percentage])
                RCMD.disconnect()
            else:
                CGI_CLI.uprint('Device %s file %s    still copying...' % \
                    (device, device_file) , color = 'blue')
                device_file_percentage_list.append([device, device_file, -1])
            RCMD.disconnect()
            time.sleep(1)
    return device_file_percentage_list

##############################################################################

def get_device_drive_string(device_list = None, \
    USERNAME = None, PASSWORD = None, printall = None, \
    silent_mode = None):
    device_drive_string, router_type = str(), str()
    for device in device_list:
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, silent_mode = silent_mode)
            if not RCMD.ssh_connection:
                if not silent_mode:
                    CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                continue
            device_drive_string = RCMD.drive_string
            router_type = RCMD.router_type

            check_ssh_flow_rate(printall = printall)

            RCMD.disconnect()
            break
    return device_drive_string, router_type

##############################################################################

def check_files_on_devices(device_list = None, true_sw_release_files_on_server = None, \
    USERNAME = None, PASSWORD = None, printall = None, \
    check_mode = None, disk_low_space_devices = None):
    """
    check_mode = True,  check device files and print failed checks
    check_mode = False, just get files needed to copy to device
    """
    nr_of_connected_devices = 0
    all_files_on_all_devices_ok = None
    missing_files_per_device_list, slave_missing_files_per_device_list = [], []
    compatibility_problem_list = []
    device_drive_string, router_type = str(), str()
    for device in device_list:
        md5check_list, filecheck_list, slave_md5check_list, slave_filecheck_list = [], [], [], []
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall)
            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                continue
            nr_of_connected_devices += 1
            device_drive_string = RCMD.drive_string
            router_type = RCMD.router_type

            check_ssh_flow_rate(printall = printall)

            ### MAKE UNIQUE DIRECTORY LIST ####################################
            redundant_dev_dir_list = [ dev_dir for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server ]
            dev_dir_set = set(redundant_dev_dir_list)
            unique_device_directory_list = list(dev_dir_set)

            ### SHOW DEVICE DIRECTORY #########################################
            CGI_CLI.uprint('checking existing device file(s) and md5(s) on %s' \
                % (device), no_newlines = None if printall else True)
            xe_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) for dev_dir in unique_device_directory_list ]
            xr_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) for dev_dir in unique_device_directory_list ]
            huawei_device_dir_list = [ 'dir %s%s/' % (RCMD.drive_string, dev_dir if dev_dir != '/' else str()) for dev_dir in unique_device_directory_list ]
            juniper_device_dir_list = [ 'file list re0:%s detail' % (dev_dir) for dev_dir in unique_device_directory_list ]
            dir_device_cmds = {
                'cisco_ios':xe_device_dir_list,
                'cisco_xr':xr_device_dir_list,
                'juniper':juniper_device_dir_list,
                'huawei':huawei_device_dir_list
            }
            rcmd_dir_outputs = RCMD.run_commands(dir_device_cmds, printall = printall)
            for unique_dir,unique_dir_outputs in zip(unique_device_directory_list,rcmd_dir_outputs):
                for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                    if unique_dir == dev_dir:
                        file_found_on_device = False
                        file_size_ok_on_device = False
                        device_fsize = 0
                        possible_file_name = str()
                        for line in unique_dir_outputs.splitlines():
                            if file in line:
                                try:
                                    possible_file_name = line.split()[-1].strip()
                                    if RCMD.router_type == 'huawei':
                                        device_fsize = float(line.split()[2].replace(',',''))
                                    elif RCMD.router_type == 'cisco_xr':
                                        try: device_fsize = float(line.split()[3].replace(',',''))
                                        except:
                                            try: device_fsize = float(line.split()[2].replace(',',''))
                                            except: pass
                                    elif RCMD.router_type == 'cisco_ios':
                                        device_fsize = float(line.split()[2].replace(',',''))
                                    elif RCMD.router_type == 'juniper':
                                        device_fsize = float(line.split()[4])
                                except: pass
                        if file == possible_file_name: file_found_on_device = True
                        if device_fsize == fsize: file_size_ok_on_device = True
                        filecheck_list.append([file,file_found_on_device,file_size_ok_on_device])

            ### MAKE BAD FILE LIST, BECAUSE HUAWEI MD5 SUM CHECK IS SLOW ######
            bad_files = [ file for file, file_found_on_device, file_size_ok_on_device in \
                filecheck_list if not file_found_on_device and not file_size_ok_on_device]

            # CGI_CLI.uprint(bad_files, \
                # name = 'bad_files', jsonprint = True, \
                # no_printall = not printall, tag = 'debug')

            ### CHECK FILE(S) AND MD5(S) FIRST PER ALL DEVICE TYPES FIRST #####
            xr_md5_cmds, xe_md5_cmds, huawei_md5_cmds, juniper_md5_cmds = [], [], [], []
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                if file in bad_files:
                    ### VOID COMMANDS for BAD FILES ###########################
                    xr_md5_cmds.append('\n')
                    xe_md5_cmds.append('\n')
                    huawei_md5_cmds.append('\n')
                    huawei_md5_cmds.append('\n')
                    juniper_md5_cmds.append('\n')
                else:
                    xr_md5_cmds.append('show md5 file /%s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                    xe_md5_cmds.append('verify /md5 %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                    juniper_md5_cmds.append('file checksum md5 re0:%s' % (os.path.join(dev_dir, file)))
                    if '.CC' in file.upper():
                        huawei_md5_cmds.append('check system-software %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                        #huawei_md5_cmds.append('Y')
                    if '.PAT' in file.upper():
                        huawei_md5_cmds.append('check patch %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                        #huawei_md5_cmds.append('Y')
            rcmd_md5_outputs = RCMD.run_commands( \
                {'cisco_ios':xe_md5_cmds,'cisco_xr':xr_md5_cmds, \
                'huawei':huawei_md5_cmds, 'juniper':juniper_md5_cmds}, \
                printall = printall, autoconfirm_mode = True,
                long_lasting_mode = True)

            ### CHECK MD5 RESULTS IN LOOP #####################################
            if RCMD.router_type == 'huawei':
                for files_list in true_sw_release_files_on_server:
                    md5_ok = False
                    directory, dev_dir, file, md5, fsize = files_list
                    for rcmd_md5_output in rcmd_md5_outputs:
                        if 'Info: Prepare to check' in rcmd_md5_output and file in rcmd_md5_output:
                            if 'Info: System software CRC check OK!' in rcmd_md5_output \
                                or 'Info: The patch is complete.' in rcmd_md5_output:
                                    md5_ok = True
                    md5check_list.append([file,md5_ok])
            if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                for files_list,rcmd_md5_output in zip(true_sw_release_files_on_server,rcmd_md5_outputs):
                    md5_ok = False
                    directory, dev_dir, file, md5, fsize = files_list
                    find_list = re.findall(r'[0-9a-fA-F]{32}', rcmd_md5_output.strip())
                    if len(find_list) == 1:
                        md5_on_device = find_list[0]
                        if md5_on_device == md5:
                            md5_ok = True
                    md5check_list.append([file,md5_ok])
            if RCMD.router_type == 'juniper':
                for files_list,rcmd_md5_output in zip(true_sw_release_files_on_server,rcmd_md5_outputs):
                    md5_ok = False
                    directory, dev_dir, file, md5, fsize = files_list
                    find_list = re.findall(r'[0-9a-fA-F]{32}', rcmd_md5_output.strip())
                    if len(find_list) == 1:
                        md5_on_device = find_list[0]
                        if md5_on_device == md5:
                            md5_ok = True
                    md5check_list.append([file,md5_ok])

            ### DEBUG PRINTOUTS ###############################################
            # CGI_CLI.uprint(filecheck_list, \
                # name = 'filecheck_list', jsonprint = True, \
                # no_printall = not printall, tag = 'debug')

            # CGI_CLI.uprint(md5check_list, \
                # name = 'md5check_list', jsonprint = True, \
                # no_printall = not printall, tag = 'debug')

            ### ===============================================================
            ### CHECK IF DEVICE FILES ARE OK (file on device,filesize,md5) ####
            ### ===============================================================
            CGI_CLI.uprint('\n', timestamp = 'no')
            for md5list in md5check_list:
                 file1, md5_ok = md5list
                 for filelist in filecheck_list:
                     file2, file_found_on_device, file_size_ok_on_device = filelist
                     if file1==file2:
                        if file_found_on_device and md5_ok and file_size_ok_on_device: pass
                        else:
                            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                                if file == file1:
                                    missing_files_per_device_list.append( \
                                        [device,[directory, dev_dir, file, md5, fsize]])
                        if RCMD.router_type == 'juniper':
                            CGI_CLI.uprint('Device=%s, re0_File=%s, found=%s, md5_ok=%s, filesize_ok=%s' % \
                                (device,file1,file_found_on_device,md5_ok,file_size_ok_on_device), \
                                tag = 'debug', no_printall = not printall, timestamp = 'no')
                        else:
                            CGI_CLI.uprint('Device=%s, File=%s, found=%s, md5_ok=%s, filesize_ok=%s' % \
                                (device,file1,file_found_on_device,md5_ok,file_size_ok_on_device), \
                                tag = 'debug', no_printall = not printall, timestamp = 'no')


            ### ===============================================================
            ### JUNIPER RE1 CHECK #############################################
            ### ===============================================================
            if RCMD.router_type == 'juniper':
                re1_filecheck_list = []
                CGI_CLI.uprint('checking existing device re1 file(s) on %s' \
                    % (device), no_newlines = None if printall else True)
                juniper_device_dir_list = [ 'file list re1:%s detail' % (dev_dir) for dev_dir in unique_device_directory_list ]
                re1_dir_device_cmds = {'juniper':juniper_device_dir_list}
                re1_rcmd_dir_outputs = RCMD.run_commands(re1_dir_device_cmds, printall = printall)
                for unique_dir,unique_dir_outputs in zip(unique_device_directory_list, re1_rcmd_dir_outputs):
                    for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                        if unique_dir == dev_dir:
                            file_found_on_device = False
                            file_size_ok_on_device = False
                            device_fsize = 0
                            possible_file_name = str()
                            for line in unique_dir_outputs.splitlines():
                                if file in line:
                                    try:
                                        possible_file_name = line.split()[-1].strip()
                                        if RCMD.router_type == 'juniper':
                                            device_fsize = float(line.split()[4])
                                    except: pass
                            if file == possible_file_name: file_found_on_device = True
                            if device_fsize == fsize: file_size_ok_on_device = True
                            re1_filecheck_list.append([file,file_found_on_device,file_size_ok_on_device])
                ### CHECK MD5 ON RE1 ###
                re1_juniper_md5_cmds, re1_md5check_list = [], []
                for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                    if file in bad_files:
                        ### VOID COMMANDS for BAD FILES ###########################
                        re1_juniper_md5_cmds.append('\n')
                    else:
                        re1_juniper_md5_cmds.append('file checksum md5 re1:%s' % (os.path.join(dev_dir, file)))
                re1_rcmd_md5_outputs = RCMD.run_commands( \
                    {'juniper':re1_juniper_md5_cmds}, \
                    printall = printall, autoconfirm_mode = True,
                    long_lasting_mode = True)
                ### CHECK MD5 RESULTS IN LOOP #####################################
                if RCMD.router_type == 'juniper':
                    for files_list,rcmd_md5_output in zip(true_sw_release_files_on_server,re1_rcmd_md5_outputs):
                        md5_ok = False
                        directory, dev_dir, file, md5, fsize = files_list
                        find_list = re.findall(r'[0-9a-fA-F]{32}', rcmd_md5_output.strip())
                        if len(find_list) == 1:
                            md5_on_device = find_list[0]
                            if md5_on_device == md5:
                                md5_ok = True
                        re1_md5check_list.append([file,md5_ok])
                ### CHECK IF DEVICE FILES ARE OK (file on device,filesize,md5) ####
                CGI_CLI.uprint('\n', timestamp = 'no')
                for md5list,filelist in zip(re1_md5check_list,re1_filecheck_list):
                     file1, md5_ok = md5list
                     file2, file_found_on_device, file_size_ok_on_device = filelist
                     if file1==file2:
                        if file_found_on_device and md5_ok and file_size_ok_on_device: pass
                        else:
                            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                                if file == file1:
                                    ### SLAVE HAS ANALOGIC MEANING OF RE1 #####
                                    slave_missing_files_per_device_list.append( \
                                        [device,[directory, dev_dir, file, md5, fsize]])
                        CGI_CLI.uprint('Device=%s, re1_File=%s, found=%s, md5_ok=%s, filesize_ok=%s' % \
                            (device, file1, file_found_on_device, md5_ok, file_size_ok_on_device), \
                            tag = 'debug', no_printall = not printall, timestamp = 'no')

            ### HUAWEI SLAVE#CFCARD FILES CHECK ###############################
            if RCMD.router_type == 'huawei':
                CGI_CLI.uprint('checking existing device slave#cfcard file(s) on %s.' \
                    % (device), no_newlines = None if printall else True)
                huawei_slave_device_dir_list = [ 'dir slave#%s%s/' % (RCMD.drive_string, dev_dir if dev_dir != '/' else str()) for dev_dir in unique_device_directory_list ]
                slave_dir_device_cmds = {
                    'huawei':huawei_slave_device_dir_list
                }
                rcmd_dir_outputs = RCMD.run_commands(slave_dir_device_cmds, printall = printall)
                for unique_dir,unique_dir_outputs in zip(unique_device_directory_list,rcmd_dir_outputs):
                    for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                        if unique_dir == dev_dir:
                            file_found_on_device = False
                            file_size_ok_on_device = False
                            device_fsize = 0
                            possible_file_name = str()
                            for line in unique_dir_outputs.splitlines():
                                if file in line:
                                    try:
                                        possible_file_name = line.split()[-1].strip()
                                        if RCMD.router_type == 'huawei':
                                            device_fsize = float(line.split()[2].replace(',',''))
                                        elif RCMD.router_type == 'cisco_xr':
                                            try: device_fsize = float(line.split()[3].replace(',',''))
                                            except:
                                               try: device_fsize = float(line.split()[2].replace(',',''))
                                               except: pass
                                        elif RCMD.router_type == 'cisco_ios':
                                            device_fsize = float(line.split()[2].replace(',',''))
                                    except: pass
                            if file == possible_file_name: file_found_on_device = True
                            if device_fsize == fsize: file_size_ok_on_device = True
                            slave_filecheck_list.append([file,file_found_on_device,file_size_ok_on_device])

                ### MAKE BAD FILE LIST, BECAUSE HUAWEI MD5 SUM CHECK IS SLOW ######
                slave_bad_files = [ file for file, file_found_on_device, file_size_ok_on_device in \
                    slave_filecheck_list if not file_found_on_device and not file_size_ok_on_device]

                ### CHECK FILE(S) AND MD5(S) FIRST ################################
                slave_huawei_md5_cmds = []
                for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                    if file in slave_bad_files:
                        ### VOID COMMANDS for BAD FILES ###########################
                        slave_huawei_md5_cmds.append('\n')
                        slave_huawei_md5_cmds.append('\n')
                    else:
                        if '.CC' in file.upper():
                            slave_huawei_md5_cmds.append('check system-software slave#%s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                            #slave_huawei_md5_cmds.append('Y')
                        if '.PAT' in file.upper():
                            slave_huawei_md5_cmds.append('check patch slave#%s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                            #slave_huawei_md5_cmds.append('Y')
                slave_rcmd_md5_outputs = RCMD.run_commands({'huawei':slave_huawei_md5_cmds}, \
                    printall = printall, autoconfirm_mode = True, long_lasting_mode = True)
                ### CHECK MD5 RESULTS IN LOOP #################################
                for files_list in true_sw_release_files_on_server:
                    md5_ok = False
                    directory, dev_dir, file, md5, fsize = files_list
                    for rcmd_md5_output in slave_rcmd_md5_outputs:
                        if 'Info: Prepare to check' in rcmd_md5_output and file in rcmd_md5_output:
                            if 'Info: System software CRC check OK!' in rcmd_md5_output \
                                or 'Info: The patch is complete.' in rcmd_md5_output:
                                    md5_ok = True
                    slave_md5check_list.append([file,md5_ok])

                ### CHECK IF SLAVE DEVICE FILES ARE OK (slavefile,fsize,md5) ##
                for md5list,filelist in zip(slave_md5check_list,slave_filecheck_list):
                     file1, md5_ok = md5list
                     file2, file_found_on_device, file_size_ok_on_device = filelist
                     if file1==file2:
                        if file_found_on_device and md5_ok and file_size_ok_on_device: pass
                        else:
                            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                                if file == file1:
                                    slave_missing_files_per_device_list.append( \
                                        [device,[directory, dev_dir, file, md5, fsize]])
                        CGI_CLI.uprint('Device=%s, SlaveFile=%s, found=%s, md5_ok=%s, filesize_ok=%s' % \
                            (device, file1,file_found_on_device,md5_ok,file_size_ok_on_device), \
                            tag = 'debug', no_printall = not printall, timestamp = 'no')


            ### HUAWEI COMPATIBILITY CHECK ####################################
            if RCMD.router_type == 'huawei':
                CGI_CLI.uprint('\nchecking existing %s device file(s) for hw compatibility.' \
                    % (device), no_newlines = None if printall else True)
                huawei_compatibility_cmds = []
                for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                    if not file in bad_files and '.CC' in file.upper():
                        huawei_compatibility_cmds.append('check hardware-compatibility %s%s' % \
                            (RCMD.drive_string, os.path.join(dev_dir, file)))
                        ### CHECK FILES ON 'slave#' ALSO FOR HW COMPATIBILITY ###
                        #huawei_compatibility_cmds.append('check hardware-compatibility slave#%s%s' % \
                        #    (RCMD.drive_string, os.path.join(dev_dir, file)))
                    else: huawei_compatibility_cmds.append('\n')
                rcmd_compatibility_outputs = RCMD.run_commands( \
                    {'huawei':huawei_compatibility_cmds}, printall = printall, \
                    long_lasting_mode = True)
                for compatibility_output, true_sw_file in zip(rcmd_compatibility_outputs, true_sw_release_files_on_server):
                    directory, dev_dir, file, md5, fsize = true_sw_file
                    if 'check hardware-compatibility failed!' in compatibility_output:
                        compatibility_problem_list.append([device,os.path.join(dev_dir, file)])
            ###################################################################
            CGI_CLI.uprint('\n', timestamp = 'no')
            RCMD.disconnect()

    ### PRINT HEADERS RED OR BLUE #############################################
    files_color = None
    if len(missing_files_per_device_list) > 0 or len(slave_missing_files_per_device_list)>0:

        if CGI_CLI.data.get('check_device_sw_files_only') or check_mode:
            ### DO NOT PRINT HEADER IF IGNORE BACKUP RE #######################
            if RCMD.router_type == 'juniper' \
                and CGI_CLI.data.get('ignore_missing_backup_re_on_junos') \
                and len(missing_files_per_device_list) == 0 \
                and len(slave_missing_files_per_device_list)>0: pass
            else:
                CGI_CLI.tableprint(['Device','Bad_or_missing_file(s):'], \
                    column_percents = [10,90], header = True, color = 'red')
                files_color = 'red'
        else:
            CGI_CLI.tableprint(['Device','Bad_or_missing_file(s):'], \
                column_percents = [10,90], header = True, color = 'blue')
            files_color = 'blue'

        ### PRINT RED OR BLUE FILES TO COPY OR MISSING/BAD ####################
        for device,missing_or_bad_files_per_device in missing_files_per_device_list:
            directory, dev_dir, file, md5, fsize = missing_or_bad_files_per_device
            CGI_CLI.tableprint([device, device_drive_string + os.path.join(dev_dir, file)],\
                    color = files_color)
        ### PRINT SLAVE/BACKUP RE FILES #######################################
        for device,missing_or_bad_files_per_device in slave_missing_files_per_device_list:
            directory, dev_dir, file, md5, fsize = missing_or_bad_files_per_device
            if RCMD.router_type == 'juniper':
                if CGI_CLI.data.get('ignore_missing_backup_re_on_junos'): pass
                else:
                    CGI_CLI.tableprint([device, 're1:%s' % (os.path.join(dev_dir, file))],\
                        column_percents = [10,90], color = files_color)
            elif RCMD.router_type == 'huawei':
                CGI_CLI.tableprint([device, 'slave#%s' % ( \
                    device_drive_string + os.path.join(dev_dir, file))],\
                    column_percents = [10,90], color = files_color)
        CGI_CLI.tableprint(end_table = True)

    ### SET FLAG FILES OK #####################################################
    if len(missing_files_per_device_list) == 0 \
        and len(slave_missing_files_per_device_list) == 0 \
        and len(compatibility_problem_list) == 0 \
        and nr_of_connected_devices > 0 \
        and nr_of_connected_devices == len(device_list):
            all_files_on_all_devices_ok = True

    if len(missing_files_per_device_list) == 0 \
        and len(slave_missing_files_per_device_list) > 0 and CGI_CLI.data.get('ignore_missing_backup_re_on_junos') and RCMD.router_type == 'juniper'\
        and len(compatibility_problem_list) == 0 \
        and nr_of_connected_devices > 0 \
        and nr_of_connected_devices == len(device_list):
            all_files_on_all_devices_ok = True

    if nr_of_connected_devices != len(device_list):
        CGI_CLI.uprint('\nConnection problems to device(s)!', tag = 'h3', color = 'red')

    ### PRINT INCOMPATIBLE FILES WARNING EVEN NOT IN CHECK MODE ###############
    if CGI_CLI.data.get('check_device_sw_files_only') or check_mode \
        or len(missing_files_per_device_list) == 0:
        if len(compatibility_problem_list) > 0:
            CGI_CLI.tableprint(['Device','Incompatible_file(s)'], column_percents = [10,90], header = True, color = 'red')
            for device,devfile in compatibility_problem_list:
                CGI_CLI.tableprint([device,devfile], column_percents = [10,90], color = 'red')
            CGI_CLI.tableprint(end_table = True)
            result = '\nIncompatible file(s) on device(s)!'
            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])

    ### PRINT CHECK RESULTS ###################################################
    if all_files_on_all_devices_ok and len(disk_low_space_devices) == 0:
        result = 'Sw release %s file(s) on device(s) %s - CHECK OK.' % (sw_release, ', '.join(device_list))
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color='green')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
    elif all_files_on_all_devices_ok and len(disk_low_space_devices) > 0:
        result = 'Sw release %s file(s) on device(s) %s - CHECK OK.' % \
            (sw_release, ', '.join(device_list))
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color='green')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
        result = 'Disk space problems & sw release file(s) on device(s) %s - CHECK FAILED!' % \
            (', '.join(disk_low_space_devices))
        CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
    elif CGI_CLI.data.get('check_device_sw_files_only') or check_mode:
        if len(missing_files_per_device_list) == 0 and len(compatibility_problem_list) == 0: pass
        else:
            result = 'Sw release file(s) on device(s) - CHECK FAILED!'
            CGI_CLI.uprint(result , tag = CGI_CLI.result_tag, color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])

    ### END IN CHECK_DEVICE_FILES_ONLY MODE, BECAUSE OF X TIMES SCP TRIES #####
    if CGI_CLI.data.get('check_device_sw_files_only') \
        or len(compatibility_problem_list) > 0:
        if CGI_CLI.data.get('backup_configs_to_device_disk') \
            or CGI_CLI.data.get('delete_device_sw_files_on_end') \
            or CGI_CLI.data.get('enable_device_scp_before_copying') \
            or CGI_CLI.data.get('disable_device_scp_after_copying') \
            or CGI_CLI.data.get('force_rewrite_sw_files_on_device'): pass
        else: sys.exit(0)

    return all_files_on_all_devices_ok, missing_files_per_device_list, device_drive_string, router_type, compatibility_problem_list

###############################################################################

def check_free_disk_space_on_devices(device_list = None, \
    missing_files_per_device_list = None, \
    USERNAME = None, PASSWORD = None, printall = None, \
    max_file_size_even_if_already_exists_on_device = None):

    ### SPACE = -1 MEANS UNTOUCHED/UNKNOWN/NOT EXISTENT SPACE #################
    device_free_space_in_bytes, slave_device_free_space_in_bytes = -1, -1

    disk_low_space_devices, disk_free_list = [], []
    for device in device_list:
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                continue

            ### DO ENABLING OF SCP ON ROUTER ##################################
            if CGI_CLI.data.get('enable_device_scp_before_copying'):
                do_scp_enable(printall = printall)

            check_disk_space_cmds = {
                ### some ios = enable, ask password, 'show bootflash:' , exit
                'cisco_ios':[' ','show bootflash:',' ','show version | in (%s)' % (asr1k_detection_string)],
                'cisco_xr':['show filesystem',
                    'show version | in "%s"' % (asr9k_detection_string),
                    ],
                'juniper':['show system storage detail invoke-on all-routing-engines'],
                'huawei':['dir','dir slave#cfcard:']
            }
            CGI_CLI.uprint('checking disk space on %s' % (device), \
                no_newlines = None if printall else True)
            rcmd_check_disk_space_outputs = RCMD.run_commands(check_disk_space_cmds)

            if RCMD.router_type == 'cisco_ios':
                try: device_free_space_in_bytes = float(rcmd_check_disk_space_outputs[1].\
                         split('bytes available')[0].splitlines()[-1].strip())
                except: pass
            elif RCMD.router_type == 'cisco_xr':
                try: device_free_space_in_bytes = float(rcmd_check_disk_space_outputs[0].\
                         split('harddisk:')[0].splitlines()[-1].split()[1].strip())
                except: pass
            elif RCMD.router_type == 'huawei':
                try:
                     device_free_space_in_bytes = float(rcmd_check_disk_space_outputs[0].\
                         split(' KB free)')[0].splitlines()[-1].split()[-1].\
                         replace('(','').replace(',','').strip())*1024
                     slave_device_free_space_in_bytes = float(rcmd_check_disk_space_outputs[1].\
                         split(' KB free)')[0].splitlines()[-1].split()[-1].\
                         replace('(','').replace(',','').strip())*1024
                except: pass
            elif RCMD.router_type == 'juniper':

                ### RE0 #######################################################
                for line in rcmd_check_disk_space_outputs[0].splitlines():
                    ### AMSCR8 WORKARROUND MOUNT MAPPING BUGFIX ###
                    try:
                        last_column  = str(line).split()[-1]
                        third_column = str(line).split()[3]
                    except: last_column, third_column = str(), str()

                    if last_column == '/.mount/var/tmp':
                        device_free_space_in_bytes = float(third_column)*1024
                        CGI_CLI.uprint("Free1[%s], Line[%s]" % (device_free_space_in_bytes, line), \
                            tag = 'debug', no_printall = not printall)
                        break

                if device_free_space_in_bytes == -1:
                    for line in rcmd_check_disk_space_outputs[0].splitlines():
                        try:
                            last_column  = str(line).split()[-1]
                            third_column = str(line).split()[3]
                        except: last_column, third_column = str(), str()

                        if last_column == '/.mount/var':
                            device_free_space_in_bytes = float(third_column)*1024
                            CGI_CLI.uprint("Free2[%s], Line[%s]" % (device_free_space_in_bytes, line), \
                                tag = 'debug', no_printall = not printall)
                            break

                if device_free_space_in_bytes == -1:
                    for line in rcmd_check_disk_space_outputs[0].splitlines():
                        try:
                            last_column  = str(line).split()[-1]
                            third_column = str(line).split()[3]
                        except: last_column, third_column = str(), str()

                        if last_column == '/.mount':
                            device_free_space_in_bytes = float(third_column)*1024
                            CGI_CLI.uprint("Free3[%s], Line[%s]" % (device_free_space_in_bytes, line), \
                                tag = 'debug', no_printall = not printall)
                            break

                ### RE1 #######################################################
                try: re1_output_part = rcmd_check_disk_space_outputs[0].split('re1:')[1]
                except: re1_output_part = str()
                for line in re1_output_part.splitlines():
                    ### AMSCR8 WORKARROUND MOUNT MAPPING BUGFIX ###
                    try:
                        last_column  = str(line).split()[-1]
                        third_column = str(line).split()[3]
                    except: last_column, third_column = str(), str()

                    if last_column == '/.mount/var/tmp':
                        slave_device_free_space_in_bytes = float(third_column)*1024
                        CGI_CLI.uprint("Free11[%s], Line[%s]" % (slave_device_free_space_in_bytes, line), \
                            tag = 'debug', no_printall = not printall)
                        break

                if slave_device_free_space_in_bytes == -1:
                    for line in re1_output_part.splitlines():
                        try:
                            last_column  = str(line).split()[-1]
                            third_column = str(line).split()[3]
                        except: last_column, third_column = str(), str()

                        if last_column == '/.mount/var':
                            slave_device_free_space_in_bytes = float(third_column)*1024
                            CGI_CLI.uprint("Free12[%s], Line[%s]" % (slave_device_free_space_in_bytes, line), \
                                tag = 'debug', no_printall = not printall)
                            break

                if slave_device_free_space_in_bytes == -1:
                    for line in re1_output_part.splitlines():
                        try:
                            last_column  = str(line).split()[-1]
                            third_column = str(line).split()[3]
                        except: last_column, third_column = str(), str()

                        if last_column == '/.mount':
                            slave_device_free_space_in_bytes = float(third_column)*1024
                            CGI_CLI.uprint("Free13[%s], Line[%s]" % (slave_device_free_space_in_bytes, line), \
                                tag = 'debug', no_printall = not printall)
                            break

            ### MAKE UNIQUE DIRECTORY LIST ####################################
            xr_device_mkdir_list, huawei_device_mkdir_list = [], []
            for dev_dir in unique_device_directory_list:
                up_path = str()
                for dev_sub_dir in dev_dir.split('/'):
                    if dev_sub_dir:
                        xr_device_mkdir_list.append('mkdir %s%s' % \
                            (RCMD.drive_string, os.path.join(up_path,dev_sub_dir)))
                        xr_device_mkdir_list.append('\r\n')
                        huawei_device_mkdir_list.append('mkdir %s/%s' % \
                            (RCMD.drive_string, os.path.join(up_path,dev_sub_dir)))
                        huawei_device_mkdir_list.append('mkdir slave#%s/%s' % \
                            (RCMD.drive_string, os.path.join(up_path,dev_sub_dir)))
                        up_path = os.path.join(up_path, dev_sub_dir)

            mkdir_device_cmds = {
                'cisco_ios':xr_device_mkdir_list,
                'cisco_xr':xr_device_mkdir_list,
                'juniper':['\n'],
                'huawei':huawei_device_mkdir_list
            }
            forget_it = RCMD.run_commands(mkdir_device_cmds)
            CGI_CLI.uprint('\n', timestamp = 'no')

            ### CALCULATE NEEDED SPACE ON DEVICE FORM MISSING FILES ###########
            needed_device_free_space_in_bytes, maximal_filesize = 0, 0
            for device2,missing_or_bad_files_per_device in missing_files_per_device_list:
                directory, dev_dir, file, md5, fsize = missing_or_bad_files_per_device
                if device == device2:
                    needed_device_free_space_in_bytes += fsize
                    ### FIND ACTUAL NEEDED MAX FILE SIZE PER DEVICE ###########
                    if fsize > maximal_filesize:
                        maximal_filesize = copy.deepcopy(fsize)

            ### THIS SITUATION DOES NOT COVER IF FILE IS ALREADY OK ON RE0 ####
            ### BUT THERE IS NO SPACE TO COPY FILE TO RE1 #####################
            ### FOR SURE FORCE OVERWRITE FREE EXPECTED DISK SPACE BY MAXIMUM ##
            ### LATER WE CEN DECIDE ###########################################
            if max_file_size_even_if_already_exists_on_device:
                maximal_filesize = max_file_size_even_if_already_exists_on_device

            disk_free_list.append([device, device_free_space_in_bytes, \
                slave_device_free_space_in_bytes, needed_device_free_space_in_bytes, \
                maximal_filesize])
            RCMD.disconnect()

    ### CHECK FREE SPACE ######################################################
    error_string, first_only = str(), 0
    for device, disk_free, slave_disk_free, disk_reguired, maximal_filesize in disk_free_list:

        if first_only == 0:
            first_only += 1
            ### JUST PRINT TABLE HEADER ###
            if RCMD.router_type == 'juniper':
                if slave_disk_free != -1:
                    CGI_CLI.tableprint(['Device', 'Disk_needed', 're0 disk free', 're1 disk free'], header = True, color = 'blue')
                else:
                    CGI_CLI.tableprint(['Device', 'Disk_needed', 're0 disk free'], header = True, color = 'blue')
            elif RCMD.router_type == 'huawei':
                CGI_CLI.tableprint(['Device','Disk_needed','cfcard free','Slave cfcard free'], header = True, color = 'blue')
            else: CGI_CLI.tableprint(['Device','Disk_needed','Disk_free'], header = True, color = 'blue')

        ### ZERO SPACE OR JUNOS COULD HAVE NEGATIVE FREE SPACE ################
        if disk_free < -1 or slave_disk_free < -1 \
            or disk_free == 0 or slave_disk_free == 0:

            error_string += 'No disk space on %s!\n' % (device)
            disk_low_space_devices.append(device)

            if slave_disk_free == -1:
                CGI_CLI.tableprint([device,  '%.2f MB' % (float(disk_reguired)/1048576),\
                '%.2f MB' % (float(disk_free)/1048576)], \
                    color = 'red')
            else:
                CGI_CLI.tableprint([device, ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576), \
                    ' %.2f MB' % (float(slave_disk_free)/1048576)], \
                    color = 'red', )

        ### FREE SPACE BELOW MINIMUM ##########################################
        elif disk_free < (device_expected_MB_free * 1048576) or \
            slave_disk_free != -1 and slave_disk_free < (device_expected_MB_free * 1048576):

            error_string += 'Disk space below %.2fMB on %s!\n' % (device_expected_MB_free, device)
            disk_low_space_devices.append(device)

            if slave_disk_free == -1:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576)], \
                    color = 'red')
            else:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576), \
                    ' %.2f MB' % (float(slave_disk_free)/1048576)], \
                    color = 'red')

        ### SOME GB FREE EXPECTED (1MB=1048576, 1GB=1073741824) ###############
        elif (disk_free <= disk_reguired) \
            or (slave_disk_free != -1 and (slave_disk_free <= disk_reguired)):

            error_string += 'Not enough space to copy files on %s! Not possible to copy files.\n' % (device)
            disk_low_space_devices.append(device)

            if slave_disk_free == -1:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576)], \
                    color = 'red')
            else:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576), \
                    ' %.2f MB' % (float(slave_disk_free)/1048576)], \
                    color = 'red')

        ### SOME GB FREE EXPECTED (1MB=1048576, 1GB=1073741824) ###############
        elif (disk_free <= disk_reguired + (device_expected_MB_free * 1048576)) \
            or (slave_disk_free != -1 and (slave_disk_free < disk_reguired + (device_expected_MB_free * 1048576))):

            error_string += 'Not enough space to copy files on %s! Space after copy will be less than %sMB!\n' % (device,str(device_expected_MB_free))
            disk_low_space_devices.append(device)

            if slave_disk_free == -1:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576)], \
                    color = 'red')
            else:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576), \
                    ' %.2f MB' % (float(slave_disk_free)/1048576)], \
                    color = 'red')
        else:
            if slave_disk_free == -1:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576)], \
                    color = 'blue')
            else:
                CGI_CLI.tableprint([device, \
                    ' %.2f MB' % (float(disk_reguired)/1048576), \
                    ' %.2f MB' % (float(disk_free)/1048576), \
                    ' %.2f MB' % (float(slave_disk_free)/1048576)], \
                    color = 'blue')

    CGI_CLI.tableprint(end_table = True)

    ### PRINT SPACE CHECK RESULTS ############################################
    if len(disk_low_space_devices) > 0:
        if error_string: CGI_CLI.uprint(error_string, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(error_string), 'red'])
        result = 'Disk space - CHECK FAIL!'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
    else:
        result = 'Disk space - CHECK OK'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
    return disk_low_space_devices

##############################################################################

def copy_files_to_devices(true_sw_release_files_on_server = None, \
    missing_files_per_device_list = None, \
    device_list = None, USERNAME = None, PASSWORD = None, \
    device_drive_string = None, router_type = None, force_rewrite = None):
    old_files_status = []
    files_status = []
    ### SCP_LIST FROM FOREIGN/ANOTHER PROCCESSES ##############################
    scp_list, forget_it = does_run_scp_processes(printall = printall)

    if force_rewrite:
        CGI_CLI.uprint('Copy all file(s) to all device(s).', tag = 'h3', color = 'blue')

    for true_sw_release_file_on_server in true_sw_release_files_on_server:
        directory,dev_dir,file,md5,fsize = true_sw_release_file_on_server
        ### IF SCP_LIST IS VOID COPY ALL ###
        if len(scp_list) == 0:
            if force_rewrite:
                do_scp_one_file_to_more_devices(true_sw_release_file_on_server, device_list, \
                    USERNAME, PASSWORD, device_drive_string = device_drive_string, \
                    printall = printall, router_type = router_type)
            else:
                do_scp_one_file_to_more_devices_per_needed_to_copy_list( \
                    true_sw_release_file_on_server, \
                    missing_files_per_device_list, \
                    device_list, USERNAME, PASSWORD, \
                    device_drive_string = device_drive_string, \
                    printall = printall, router_type = router_type)

        ### IF SCP_LIST IS NOT VOID CHECK AND COPY ONLY NOT RUNNING ###
        for server_file, device_file, scp_device, device_user, pid, ppid in scp_list:
            #CGI_CLI.uprint('%s=%s, %s=%s' %(scp_device, device_list, device_file, os.path.join(dev_dir, file)))
            if scp_device in device_list and device_file == os.path.join(dev_dir, file):
                CGI_CLI.uprint('FILE %s is already copying to device %s, ommiting new scp copying!' % \
                    (device_file, scp_device))
            else:
                CGI_CLI.uprint('force_rewrite = %s' % (str(force_rewrite)), no_printall = not printall, tag = 'debug')
                CGI_CLI.uprint(true_sw_release_file_on_server, \
                    name = 'true_sw_release_file_on_server', \
                    jsonprint = True, no_printall = not printall, tag = 'debug')
                CGI_CLI.uprint('device_list = [%s]' % (','.join(device_list) if device_list else str()), \
                    no_printall = not printall, tag = 'debug')
                CGI_CLI.uprint(missing_files_per_device_list, \
                    name = 'missing_files_per_device_list', jsonprint = True, \
                    no_printall = not printall, tag = 'debug')

                if force_rewrite:
                    do_scp_one_file_to_more_devices(true_sw_release_file_on_server, device_list, \
                        USERNAME, PASSWORD, device_drive_string = device_drive_string, \
                        printall = printall, router_type = router_type)
                else:
                    do_scp_one_file_to_more_devices_per_needed_to_copy_list( \
                        true_sw_release_file_on_server, \
                        missing_files_per_device_list, \
                        device_list, USERNAME, PASSWORD, \
                        device_drive_string = device_drive_string, \
                        printall = printall, router_type = router_type)

        ### DO SCP LIST AGAIN AND WAIT TILL END OF YOUR SCP SESSIONS ###
        actual_scp_devices_in_scp_list = True
        scp_fails = 0
        while (actual_scp_devices_in_scp_list and scp_fails <= MAX_SCP_FAILS):
            actual_scp_devices_in_scp_list = False

            my_own_scp_list = []
            scp_list, forget_it = does_run_scp_processes(printall = printall)
            for server_file, device_file, scp_device, device_user, pid, ppid in scp_list:
                if scp_device in device_list:
                    actual_scp_devices_in_scp_list = True
                    my_own_scp_list.append([server_file, device_file, scp_device, device_user, pid, ppid])

            if len(my_own_scp_list) > 0:
                old_files_status = files_status
                time.sleep(1)
                files_status = check_percentage_of_copied_files(my_own_scp_list, USERNAME, PASSWORD, printall)
                ### CHECKED STALLED COPYING ###################################
                for old_file_status in old_files_status:
                    if old_file_status in files_status:
                        device, device_file, percentage = old_file_status
                        ### COPYING IN PROGRESS ###############################
                        if percentage > 0 and percentage < 100:
                            scp_fails += 1
                            CGI_CLI.uprint('WARNING: Device=%s, File=%s, Percent copied=%.2f HAS STALLED, KILLING SCP PROCESSES!' % \
                                (device, device_file, percentage), tag = 'warning')
                            kill_stalled_scp_processes(device = device, \
                                device_file = device_file, printall = printall)

                            ### RESTART KILLED SCP ############################
                            do_scp_one_file_to_more_devices_per_needed_to_copy_list( \
                                true_sw_release_file_on_server, \
                                missing_files_per_device_list, \
                                [device], USERNAME, PASSWORD, \
                                device_drive_string = device_drive_string, \
                                printall = printall, router_type = router_type)

                        ### JUNOS MADTR6 WORKARROUND - SCP 100%/ERROR HANGING #
                        elif percentage == 100 and router_type == 'juniper':
                            time.sleep(5)
                            CGI_CLI.uprint('JUNIPER KILL HANGING SCP WORKARROUND.', \
                                no_printall = not printall)
                            kill_stalled_scp_processes(device = device, \
                                device_file = device_file, printall = printall)

                            ### SOME DELAY ####################################
                            time.sleep(1)
            else: break
        if scp_fails >= MAX_SCP_FAILS:
            result = 'ERROR - MULTIPLE (%d) SCP STALLS & RESTARTS of %s file on device %s !!!' \
                % (MAX_SCP_FAILS, device_file, device)
            CGI_CLI.uprint(result , tag = CGI_CLI.result_tag, color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
            sys.exit(0)

##############################################################################

def huawei_copy_device_files_to_slave_cfcard(true_sw_release_files_on_server = None,
    unique_device_directory_list = None):

    if RCMD.router_type == 'huawei':
        for device in device_list:
            if device:
                RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                    printall = printall)

                if not RCMD.ssh_connection:
                    CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                    RCMD.disconnect()
                    continue

                copy_files_cmds = {'huawei':[]}

                for unique_dir in unique_device_directory_list:
                    for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                        if unique_dir == dev_dir:
                            copy_files_cmds['huawei'].append('copy %s%s slave#%s%s' % \
                                (RCMD.drive_string, os.path.join(dev_dir, file),
                                RCMD.drive_string, os.path.join(dev_dir, file)))

                CGI_CLI.uprint('copying sw release files on %s to slave cfcard' % (device), \
                    no_newlines = None if printall else True)
                forget_it = RCMD.run_commands(copy_files_cmds, \
                    autoconfirm_mode = True, long_lasting_mode = True,
                    printall = printall)

                ### CHECK FILES COPY ######################################
                check_dir_files_cmds = {'huawei':[]}
                for unique_dir in unique_device_directory_list:
                    for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                        if unique_dir == dev_dir:
                            check_dir_files_cmds['huawei'].append( \
                                'dir slave#%s%s/' % (RCMD.drive_string, dev_dir if dev_dir != '/' else str()))
                time.sleep(2)
                dir_outputs_after_copy = RCMD.run_commands(check_dir_files_cmds, \
                    printall = printall)
                CGI_CLI.uprint('\n', timestamp = 'no')

                file_not_found_list = []
                for unique_dir, dir_output_after_copy in zip(unique_device_directory_list, dir_outputs_after_copy):
                    for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                        if unique_dir == dev_dir:
                            if file in dir_output_after_copy: pass
                            else: file_not_found_list.append(dev_dir + file)
                if len(file_not_found_list) > 0:
                    result = 'Copy problem from cfcard to slave#cfcard [%s] on %s!' % (','.join(file_not_found_list), device)
                    CGI_CLI.uprint(result , tag = CGI_CLI.result_tag, color = 'red')
                    CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
                ### DISCONNECT ################################################
                RCMD.disconnect()
                time.sleep(3)


###############################################################################

def juniper_copy_device_files_to_other_routing_engine(true_sw_release_files_on_server = None,
    unique_device_directory_list = None):

    missing_backup_re_list = []
    for device in device_list:
        if device:
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall)

            if not RCMD.ssh_connection:
                CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
                RCMD.disconnect()
                continue

            if RCMD.router_type == 'juniper':

                master_re, backup_re = 're0', None

                re_files_cmds = {'juniper':['show chassis routing-engine']}
                CGI_CLI.uprint('actual routing engine check', \
                    no_newlines = None if printall else True)
                re_output = RCMD.run_commands(re_files_cmds, \
                    printall = printall)
                try:
                    if re_output[0].split('Slot 0:')[1].split('Current state')[1].split()[0] == 'Master':
                        master_re = 're0'
                    if re_output[0].split('Slot 0:')[1].split('Current state')[1].split()[0] == 'Backup':
                        backup_re = 're0'
                    if re_output[0].split('Slot 1:')[1].split('Current state')[1].split()[0] == 'Master':
                        master_re = 're1'
                    if re_output[0].split('Slot 1:')[1].split('Current state')[1].split()[0] == 'Backup':
                        backup_re = 're1'
                except: pass

                CGI_CLI.uprint('\n', timestamp = 'no')
                result = '\nDevice %s routing engines: MASTER=%s, BACKUP=%s.' % \
                    (device, master_re, str(backup_re))
                CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, printall = True)
                CGI_CLI.result_list.append([copy.deepcopy(result), 'default'])

                if not backup_re: missing_backup_re_list.append(device)
                else:
                    copy_files_cmds = {'juniper':[]}

                    for unique_dir in unique_device_directory_list:
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                # copy_files_cmds['juniper'].append('file copy %s:%s %s:%s' % \
                                    # (master_re, os.path.join(dev_dir, file), \
                                    # backup_re, os.path.join(dev_dir, file)))
                                ### PRATIMA'S JUNOS HINT TO PREVENT TWICE SPACE NEEDED ON MASTER ###
                                copy_files_cmds['juniper'].append('file copy %s %s:%s' % \
                                    (os.path.join(dev_dir, file), backup_re, dev_dir))

                    CGI_CLI.uprint('copying sw release files on %s to backup routing engine' % (device), \
                        no_newlines = None if printall else True)
                    forget_it = RCMD.run_commands(copy_files_cmds, \
                        autoconfirm_mode = True, long_lasting_mode = True, \
                        printall = printall)

                    ### CHECK FILES COPY ######################################
                    check_dir_files_cmds = {'juniper':[]}
                    for unique_dir in unique_device_directory_list:
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                check_dir_files_cmds['juniper'].append( \
                                    'file list %s:%s' % (backup_re, dev_dir if dev_dir != '/' else str()))
                    time.sleep(2)
                    dir_outputs_after_copy = RCMD.run_commands(check_dir_files_cmds, \
                        printall = printall)
                    CGI_CLI.uprint('\n', timestamp = 'no')

                    file_not_found_list = []
                    for unique_dir, dir_output_after_copy in zip(unique_device_directory_list, dir_outputs_after_copy):
                        for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                            if unique_dir == dev_dir:
                                if file in dir_output_after_copy: pass
                                else: file_not_found_list.append(dev_dir + file)
                    if len(file_not_found_list) > 0:
                        result = 'Copy problem from master re to backup re [%s] on %s!' % (','.join(file_not_found_list), device)
                        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
            ### DISCONNECT ################################################
            RCMD.disconnect()
            time.sleep(3)

    if len(missing_backup_re_list) > 0:
        result = 'BACKUP routing engine is NOT PRESENT on device(s) %s!' % (','.join(missing_backup_re_list))
        CGI_CLI.uprint(result, \
            tag = 'warning')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'orange'])
    return missing_backup_re_list


##############################################################################

def do_scp_enable(printall = None):
    scp_status_cmds = {
        'cisco_xr':[],
        'cisco_ios':[],
        'huawei':['display ssh server status'],
        'juniper':[]
        }

    scp_status_outputs = RCMD.run_commands(scp_status_cmds, printall = printall)

    if len(scp_status_outputs) > 0:
        scp_enable_cmds = {
            'cisco_xr':[],
            'cisco_ios':[],
            'huawei':['scp %sserver enable' % ('ipv4 ' if 'SCP IPv4 server' in scp_status_outputs[0] else str())],
            'juniper':[]
            }

        RCMD.run_commands(scp_enable_cmds, conf = True, autoconfirm_mode = True, \
            printall = printall)


##############################################################################

def do_scp_disable(printall = None):
    scp_status_cmds = {
        'cisco_xr':[],
        'cisco_ios':[],
        'huawei':['display ssh server status'],
        'juniper':[]
        }

    scp_status_outputs = RCMD.run_commands(scp_status_cmds, printall = printall)

    if len(scp_status_outputs) > 0:
        scp_disable_cmds = {
            'cisco_xr':[],
            'cisco_ios':[],
            'huawei':['scp %sserver disable' % ('ipv4 ' if 'SCP IPv4 server' in scp_status_outputs[0] else str())],
            'juniper':[]
            }

        RCMD.run_commands(scp_disable_cmds, conf = True, autoconfirm_mode = True, \
            printall = printall)


###############################################################################

def check_ssh_flow_rate(printall = None):
    flow_rate_cmds = {
        'cisco_xr':['sh run | include flow ssh known rate'],
        'cisco_ios':['sh run | include flow ssh known rate'],
        'huawei':[],
        'juniper':[]
        }

    flow_rate_outputs = RCMD.run_commands(flow_rate_cmds, printall = printall)

    if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
        try: flow_rate = float(flow_rate_outputs[0].split('flow ssh known rate')[-1].split()[0].strip())
        except: flow_rate = None

        if flow_rate and flow_rate < 500:
            result = "WARNING: flow ssh known rate is below 500! SCP can stall!"
            CGI_CLI.uprint(result, tag = 'warning')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'orange'])

###############################################################################

def delete_files(device = None, unique_device_directory_list = None, \
    true_sw_release_files_on_server = None, printall = None):

    local_connect = None
    if device:
        if not RCMD.ssh_connection:
            local_connect = True
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall)

        if not RCMD.ssh_connection:
            result = 'PROBLEM TO CONNECT TO %s DEVICE.' % (device)
            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
            RCMD.disconnect()
            return

        del_files_cmds = {'cisco_xr':[], 'cisco_ios':[], \
            'huawei':[], 'juniper':[]}

        for unique_dir in unique_device_directory_list:
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                if unique_dir == dev_dir:
                    del_files_cmds['cisco_xr'].append( \
                        'del %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))

                    del_files_cmds['cisco_ios'].append( \
                        'del %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))

                    del_files_cmds['huawei'].append( \
                        'del /unreserved %s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))
                    del_files_cmds['huawei'].append( \
                        'del /unreserved slave#%s%s' % (RCMD.drive_string, os.path.join(dev_dir, file)))

                    del_files_cmds['juniper'].append( \
                        'file delete re0:%s' % (os.path.join(dev_dir, file)))
                    if not CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
                        del_files_cmds['juniper'].append( \
                            'file delete re1:%s' % (os.path.join(dev_dir, file)))

        CGI_CLI.uprint('deleting sw release files on %s' % (device), \
            no_newlines = None if printall else True)
        forget_it = RCMD.run_commands(del_files_cmds, \
            autoconfirm_mode = True, printall = printall)

        ### CHECK FILES DELETION ##################################
        check_dir_files_cmds = {'cisco_xr':[],'cisco_ios':[], \
            'huawei':[], 'juniper':[]}
        for unique_dir in unique_device_directory_list:
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                if unique_dir == dev_dir:
                    check_dir_files_cmds['cisco_xr'].append( \
                        'dir %s%s' % (RCMD.drive_string, dev_dir))
                    check_dir_files_cmds['cisco_ios'].append( \
                        'dir %s%s' % (RCMD.drive_string, dev_dir))
                    check_dir_files_cmds['huawei'].append( \
                        'dir %s%s/' % (RCMD.drive_string, dev_dir if dev_dir != '/' else str()))
                    check_dir_files_cmds['huawei'].append( \
                        'dir slave#%s%s/' % (RCMD.drive_string, dev_dir if dev_dir != '/' else str()))
                    check_dir_files_cmds['juniper'].append( \
                        'file list re0:%s' % (dev_dir))
                    if not CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
                        check_dir_files_cmds['juniper'].append( \
                            'file list re1:%s' % (dev_dir))
        time.sleep(0.5)
        dir_outputs_after_deletion = RCMD.run_commands(check_dir_files_cmds, \
            printall = printall)
        CGI_CLI.uprint('\n', timestamp = 'no')
        file_not_deleted = False
        for unique_dir in unique_device_directory_list:
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                if unique_dir == dev_dir:
                    for dir_output in dir_outputs_after_deletion:
                        if file in dir_output:
                            CGI_CLI.uprint('File %s not deleted from %s on %s!' \
                                % (file,unique_dir, device), color = 'red')
                            file_not_deleted = True
        if file_not_deleted:
            result = '%s delete problem!' % (device)
            CGI_CLI.uprint(result, color = 'red')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
        else:
            result = '%s delete done!' % (device)
            CGI_CLI.uprint(result, color = 'green')
            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])

        ### DISCONNECT ################################################
        if local_connect: RCMD.disconnect()

###############################################################################



###############################################################################

def terminate_process_term(signalNumber, frame):
    result = 'SIGTERM RECEIVED - terminating the process'
    CGI_CLI.uprint(result, color = 'magenta')
    #CGI_CLI.result_list.append([copy.deepcopy(result), 'magenta'])
    RCMD.disconnect()
    sys.exit(0)

###############################################################################


###############################################################################
#
# def BEGIN MAIN
#
###############################################################################

if __name__ != "__main__": sys.exit(0)

signal.signal(signal.SIGTERM, terminate_process_term)

try:

    CSS_STYLE = """
authentication {
  color: #cc0000;
  font-size: x-large;
  font-weight: bold;
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
th {
  text-align: left;
}
"""

    # goto_webpage_end_by_javascript = """
# <script language="javascript" type="text/javascript">
# setInterval(function() {
# if (document.readyState !== "complete") {
# window.scrollTo(0,document.body.scrollHeight); }
# }, 100);
# </script>
# """

    # goto_webpage_end_by_javascript = """<script language="javascript" type="text/javascript">
# var refreshIntervalId = setInterval(function() { window.scrollTo(0,document.body.scrollHeight);}, 100);
# document.addEventListener('readystatechange', (event) => {
    # log.textContent = log.textContent + `readystate: ${document.readyState}\\n`;
    # if (document.readyState === 'complete') {
    # clearInterval(refreshIntervalId);
  # }
# });
# document.onreadystatechange = function () {
  # if (document.readyState === 'complete') {
    # clearInterval(refreshIntervalId);
  # }
# }
# </script>"""



    on_submit_action = """<script>
function validateForm() {
  var x = document.forms["mainForm"]["username"].value;
  var y = document.forms["mainForm"]["password"].value;
  if (x == "") {
    alert("Username must be filled out");
    return false;
  }
  if (y == "") {
    alert("Password must be filled out");
    return false;
  }
}
</script>
"""

    logging.raiseExceptions = False
    goto_webpage_end_by_javascript = str()
    traceback_found = None

    ### def GLOBAL CONSTANTS #################################################
    device_expected_MB_free = 1
    total_number_of_scp_attempts = 3
    MAX_SCP_FAILS = 3


    SCRIPT_ACTIONS_LIST = [
    #'copy_tar_files','do_sw_upgrade',
    ]

    active_menu_list, active_menu = [ None,'select_router_type','select_routers','copy_to_routers'], 0

    asr1k_detection_string = 'CSR1000'
    asr9k_detection_string = 'ASR9K|IOS-XRv 9000'

    ### GLOBAL VARIABLES ######################################################

    logfilename = None
    SCRIPT_ACTION = None
    ACTION_ITEM_FOUND = None
    type_subdir = str()
    remote_sw_release_dir_exists = None
    total_size_of_files_in_bytes = 0
    device_list = []
    device_types = []
    true_sw_release_files_on_server = []
    missing_files_per_device_list = []
    all_files_on_all_devices_ok = None
    disk_low_space_devices, compatibility_problem_list = [], []
    router_type_id_string, router_id_string = "router_type", '__'

    ### GCI_CLI INIT ##########################################################
    USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True, css_style = CSS_STYLE)
    LCMD.init()
    CGI_CLI.timestamp = CGI_CLI.data.get("timestamps")

    printall = True if CGI_CLI.data.get("printall",False) else False

    ### KILLING APLICATION PROCESS ############################################
    if CGI_CLI.data.get('submit',str()) == 'STOP' and CGI_CLI.data.get('pidtokill'):
        LCMD.run_commands({'unix':['kill %s' % (CGI_CLI.data.get('pidtokill',str()))]}, printall = None)
        CGI_CLI.uprint('PID%s stopped.' % (CGI_CLI.data.get('pidtokill',str())))
        sys.exit(0)

    ### GENERATE DEVICE LIST ##################################################
    devices_string = CGI_CLI.data.get("device",str())
    if devices_string:
        if ',' in devices_string:
            device_list = [ dev_mix_case.upper() for dev_mix_case in devices_string.split(',') ]
        else: device_list = [devices_string.upper()]

    ### APPEND DEVICE LIST ####################################################
    for key in CGI_CLI.data.keys():
        ### DEVICE NAME IS IN '__KEY' ###
        try: value = str(key)
        except: value = str()
        if router_id_string in value: device_list.append(value.replace('_',''))

    ### def LOGFILENAME GENERATION, DO LOGGING ONLY WHEN DEVICE LIST EXISTS ###
    if device_list:
        html_extention = 'htm' if CGI_CLI.cgi_active else str()
        logfilename = generate_logfilename(prefix = ('_'.join(device_list)).upper(), \
            USERNAME = USERNAME, suffix = str('scp') + '.%slog' % (html_extention))
        ### NO WINDOWS LOGGING ################################################
        if 'WIN32' in sys.platform.upper(): logfilename = None
        if logfilename: CGI_CLI.set_logfile(logfilename = logfilename)

    ### START PRINTING AND LOGGING ########################################
    changelog = 'https://github.com/peteneme/pyxWorks/commits/master/router_sw_update/sw_uploader.py'
    if CGI_CLI.cgi_active:
        CGI_CLI.uprint('<h1 style="color:blue;">SW UPLOADER <a href="%s" style="text-decoration: none">(v.%s)</a>%s</h1>' % \
            (changelog, CGI_CLI.VERSION(), CGI_CLI.STOP_APPLICATION_BUTTON), raw = True)
    else: CGI_CLI.uprint('SW UPLOADER (v.%s)' % (CGI_CLI.VERSION()), \
              tag = 'h1', color = 'blue')
    CGI_CLI.print_args()

    #CGI_CLI.uprint(sys.modules.keys())
    CGI_CLI.uprint("ENCODING='%s'" % CGI_CLI.sys_stdout_encoding, no_printall = not printall, tag = 'debug')

    ### CHECK RUNNING SCP PROCESSES ON START ##################################
    does_run_script_processes(printall = printall)
    scp_list, foreign_scp_ps_list = does_run_scp_processes(printall = printall)
    if len(scp_list)>0:
        CGI_CLI.uprint('WARNING: Running scp copy...', tag = 'warning')
        for server_file, device_file, device, device_user, pid, ppid in scp_list:
            if device:
                CGI_CLI.uprint('USER=%s, DEVICE=%s, FILE=%s, COPYING_TO=%s, PID=%s, PPID=%s' % \
                    (device_user, device, server_file, device_file, pid, ppid), \
                    tag = 'warning', stop_button = pid)

    ### GET sw_release FROM cli ###############################################
    sw_release = CGI_CLI.data.get('sw_release',str())
    try: device_expected_MB_free = float(CGI_CLI.data.get('remaining_device_disk_free_MB',device_expected_MB_free))
    except: pass
    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()

    if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
    else: urllink = 'https://%s/cgi-bin/' % (iptac_server)

    ### GENERATE selected_sw_file_types_list ##################################
    selected_sw_file_types_list = []
    selected_files_types_string = '_file(s)'
    for key in CGI_CLI.data.keys():
        try: value = str(key)
        except: value = str()
        if selected_files_types_string in value:
            selected_sw_file_types_list.append(value.replace(selected_files_types_string,str()))
            active_menu = 3

    ### GET sw_release FROM CGI ###################################################
    selected_release_string = 'soft_release'
    if not sw_release:
        for key in CGI_CLI.data.keys():
            try: value = CGI_CLI.data.get(key)
            except: value = None
            if selected_release_string == key and value:
                sw_release = value
                active_menu = 3
                break

    ### def SQL INIT ##############################################################
    sql_inst = sql_interface(host='localhost', user='cfgbuilder', \
        password='cfgbuildergetdata', database='rtr_configuration')

    ### SQL READ ALL HARDVARE TYPES ###############################################
    device_types_list_in_list = sql_inst.sql_read_table_records( \
        select_string = 'hardware',\
        from_string = 'oti_all_table',\
        order_by = 'hardware')

    ### SQL READ ALL DEVICES IN NETWORK ###########################################
    data = collections.OrderedDict()
    data['oti_all_table'] = sql_inst.sql_read_records_to_dict_list( \
        select_string = 'vendor, hardware, software, rtr_name, network',\
        from_string = 'oti_all_table',\
        order_by = 'vendor, hardware, rtr_name ASC')


    ### DO SORTED DEVICE TYPE LIST ################################################
    if device_types_list_in_list:
        device_types_set = set([ dev_type[0] for dev_type in device_types_list_in_list ])
        device_types = list(device_types_set)
        device_types.sort()

    ### FIND SELECTED DEVICE TYPE #################################################
    selected_device_type = str()
    for key in CGI_CLI.data.keys():
        ### DEVICE NAME IS IN 'router_type__VALUE' ###
        try: value = CGI_CLI.data.get(key)
        except: value = None
        if router_type_id_string == key and value:
            selected_device_type = value.replace('_','')
            active_menu = 2

    ### GAIN SUBDIRS FROM OTI_ALL_TABLE WHERE HARDWARE = SELECTED_DEVICE_TYPE ###
    brand_raw, type_raw , brand_subdir, type_subdir = str(), str() , str(), str()
    sw_release_list, default_sw_release, sw_file_types_list = [], str(), []
    type_subdir_on_device, sw_release_list_raw = str(), []
    if selected_device_type:
        for router_dict in data['oti_all_table']:
            if selected_device_type == router_dict.get('hardware',str()):
                brand_raw = router_dict.get('vendor',str())
                type_raw  = router_dict.get('hardware',str())
                brand_subdir, type_subdir,type_subdir_on_device, sw_file_types_list = \
                    get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)
                break

        ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
        sw_release_list, default_sw_release = get_existing_sw_release_list(brand_subdir, type_subdir)


    ### ROUTER-TYPE MENU PART #####################################################
    table_rows = 5
    counter = 0
    router_type_menu_list = ['<h2>Select router type:</h2>',
        '<div align="left">', '<table style="width:70%">']
    for router_type in device_types:
        if counter == 0: router_type_menu_list.append('<tr>')
        router_type_menu_list.append('<td>')
        router_type_menu_list.append({'radio':'%s__%s' % (router_type_id_string,router_type)})
        counter += 1
        router_type_menu_list.append('</td>')
        if counter + 1 > table_rows:
            router_type_menu_list.append('</tr>')
            counter = 0
    if counter != 0: router_type_menu_list.append('</tr>')
    router_type_menu_list.append('</table>')
    router_type_menu_list.append('</div>')

    ### ROUTER MENU PART ##########################################################
    table_rows = 5
    counter = 0
    router_menu_list = ['<h2>%s routers:</h2>'% (selected_device_type),
        '<div align="left">', '<table style="width:70%">']
    for router_dict in data['oti_all_table']:
        if selected_device_type and \
            selected_device_type in router_dict.get('hardware',str()):
            if counter == 0: router_menu_list.append('<tr>')
            router_menu_list.append('<td>')
            router_menu_list.append({'checkbox':'%s%s' % \
                (router_id_string,router_dict.get('rtr_name',str()))})
            counter += 1
            router_menu_list.append('</td>')
            if counter + 1 > table_rows:
                router_menu_list.append('</tr>')
                counter = 0
    if counter != 0: router_menu_list.append('</tr>')
    router_menu_list.append('</table>')
    router_menu_list.append('</div>')

    ### GAIN VENDOR + HARDWARE FROM DEVICE LIST "AGAIN" ###########################
    if len(device_list)>0:
        for router_dict in data['oti_all_table']:
            if device_list[0] and device_list[0].upper() == router_dict.get('rtr_name',str()).upper():
                brand_raw = router_dict.get('vendor',str())
                type_raw  = router_dict.get('hardware',str())
                brand_subdir, type_subdir, type_subdir_on_device, sw_file_types_list = \
                    get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)
                CGI_CLI.uprint('READ_FROM_DB: [router=%s, vendor=%s, hardware=%s]' % \
                    (device_list[0], brand_raw, type_raw), tag = 'debug', no_printall = not printall)
                break
        else:
            if CGI_CLI.data.get('force_selected_hw_type'):
                brand_raw = str()
                type_raw = CGI_CLI.data.get("selected_router_type", str())
                brand_subdir, type_subdir, type_subdir_on_device, sw_file_types_list = \
                    get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)
            else:
                CGI_CLI.uprint('Router %s has no record in DB!' % \
                    (device_list[0]), tag = 'warning', printall = True)

        ### CHECK LOCAL SW VERSIONS DIRECTORIES ###################################
        if len(sw_release_list) == 0:
            sw_release_list, default_sw_release = get_existing_sw_release_list(brand_subdir, type_subdir)

    ###############################################################################




    ### SHOW HTML MENU SHOWS ONLY IN CGI/HTML MODE ################################
    if CGI_CLI.cgi_active and (not CGI_CLI.submit_form or active_menu == 2):
        ### DISPLAY ROUTER-TYPE MENU ##############################################
        if active_menu == 0:
            main_menu_list = router_type_menu_list + ['<br/>', {'checkbox':'printall'} ]
        ### def DISPLAY SELECT ROUTER MENU ########################################
        elif active_menu == 2:
            main_menu_list = router_menu_list + \
            ['<p>Additional device(s) (optional) [list separator=,]:</p>',\
            {'text':'device'}, '<br/>', \
            '<h3>SW RELEASE (required) [default=%s]:</h3>' % (default_sw_release)]

            if len(sw_release_list) > 0:
                release_sw_release_list = [ "%s__%s" % (selected_release_string, release) for release in sw_release_list ]
                main_menu_list.append({'radio':release_sw_release_list})
            else:
                main_menu_list.append('<h3 style="color:red">NO SW RELEASE VERSIONS AVAILABLE on server %s!</h3>' % (iptac_server))

            main_menu_list.append('<br/>')
            main_menu_list.append('<h3>FILES TO COPY (required):</h3>')
            for sw_file in sw_file_types_list:
                main_menu_list.append({'checkbox':sw_file + '_file(s)'})
                main_menu_list.append('<br/>')
            if len(sw_file_types_list) == 0:
                main_menu_list.append('<h3 style="color:red">NO FILE TYPES SPECIFIED!</h3>')
            main_menu_list.append('<p>Additional file(s) to copy (optional) [list separator=,]:</p>')
            main_menu_list.append({'text':'additional_files_to_copy'})
            main_menu_list.append('<br/>')

            main_menu_list += ['<h3>REMAINING DEVICE DISK FREE (optional) [default &gt %.2f MB]:</h3>'%(device_expected_MB_free),\
            {'text':'remaining_device_disk_free_MB'}, '<br/>',\
            '<br/><authentication>LDAP authentication (required):<br/><br/>',\
            {'text':'username'}, \
            '<br/>', {'password':'password'},
            '</authentication>','<br/>']

            if len(SCRIPT_ACTIONS_LIST)>0: main_menu_list.append({'radio':[ 'script_action__' + action for action in SCRIPT_ACTIONS_LIST ]})

            main_menu_list += ['<br/>','<h3>Options:</h3>', \
                {'checkbox':'check_device_sw_files_only'},'<br/>',\
                {'checkbox':'display_scp_percentage_only'},'<br/>',\
                {'checkbox':'force_rewrite_sw_files_on_device'},'<br/>',\
                {'checkbox':'ignore_missing_backup_re_on_junos'},'<br/>',\
                {'checkbox':'enable_device_scp_before_copying'},'<br/>',\
                {'checkbox':'disable_device_scp_after_copying'},'<br/>',\
                {'checkbox':'backup_configs_to_device_disk'},'<br/>',\
                {'checkbox':'delete_device_sw_files_on_end'},'<br/>',\
                {'checkbox':'force_selected_hw_type'},'<br/>',\
                '<br/>', {'checkbox':'timestamps'}, \
                '<br/>', {'checkbox':'printall'}, \
                on_submit_action
                ]

            main_menu_list += [
                '<p hidden><input type="checkbox" name="selected_router_type" value="%s" checked="checked"></p>' \
                    % ( CGI_CLI.data.get("router_type", str())) ]

        CGI_CLI.formprint( main_menu_list + ['<br/>','<br/>'], submit_button = 'OK', \
            pyfile = None, tag = None, color = None , list_separator = '&emsp;', \
            name = 'mainForm', on_submit = 'return validateForm()')

        ### SHOW HTML MENU AND EXIT ###########################################
        sys.exit(0)
    else:
        ### READ SCRIPT ACTION ###
        for item in SCRIPT_ACTIONS_LIST:
            if CGI_CLI.data.get(item):
                SCRIPT_ACTION = copy.deepcopy(item)
                break
        else:
            if CGI_CLI.data.get("script_action"):
                SCRIPT_ACTION = CGI_CLI.data.get("script_action")

    ### def DISPLAY PERCENTAGE OF SCP ONLY ####################################
    if CGI_CLI.data.get('display_scp_percentage_only'):
        scp_list, forget_it = does_run_scp_processes(printall = printall)
        if len(scp_list)>0 and USERNAME and PASSWORD:
            check_percentage_of_copied_files(scp_list, USERNAME, PASSWORD, printall)
        else: CGI_CLI.uprint('No currently running scp processes.')
        sys.exit(0)

    ### SET DEFAULT (HIGHEST) SW RELEASE IF NOT SET ###########################
    if not sw_release and default_sw_release: sw_release = default_sw_release

    ### DO SELECTED SW FILE TYPE LIST #########################################
    ### ALSO DIRECT FILES WITH ABS-PATH COULD BE USED HERE DIRECTLY ###########
    if CGI_CLI.data.get('sw_files'):
        ft_string = CGI_CLI.data.get('sw_files')
        ft_list = ft_string.split(',') if ',' in ft_string else [ft_string]

        for ft_item in ft_list:
            selected_sw_file_types_list += \
                [ filetype for filetype in sw_file_types_list if ft_item in filetype ]

    ### APPEND SELECTED SW FILE TYPE LIST By ADDITIONAL FILE LIST #############
    additional_file_list = []
    if CGI_CLI.data.get('additional_files_to_copy'):
        if ',' in CGI_CLI.data.get('additional_files_to_copy'):
            additional_file_list = CGI_CLI.data.get('additional_files_to_copy').split(',')
        else: additional_file_list = [CGI_CLI.data.get('additional_files_to_copy')]
    selected_sw_file_types_list += additional_file_list


    ### def PRINT BASIC INFO ######################################################
    CGI_CLI.uprint('server = %s, user = %s' % (iptac_server, USERNAME))
    if len(device_list) > 0: CGI_CLI.uprint('device(s) = %s' % (', '.join(device_list)))
    if sw_release: CGI_CLI.uprint('sw release = %s' % (sw_release))
    if device_expected_MB_free:
        CGI_CLI.uprint('expected remaining device disk free >= %.2f MB' % (device_expected_MB_free))
    if len(selected_sw_file_types_list)>0:
        CGI_CLI.uprint('sw file types/sw files= %s' % (', '.join(selected_sw_file_types_list) ))
    if logfilename: CGI_CLI.uprint('logfilename=%s' % (logfilename))
    if CGI_CLI.data.get('display_scp_percentage_only'):
        CGI_CLI.uprint('display_scp_percentage_only = Y')
    elif CGI_CLI.data.get('check_device_sw_files_only'):
        CGI_CLI.uprint('check_device_sw_files_only = Y')
    elif CGI_CLI.data.get('force_rewrite_sw_files_on_device'):
        CGI_CLI.uprint('force_rewrite_sw_files_on_device = Y')
    if CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
        CGI_CLI.uprint('ignore_missing_backup_re_on_junos = Y')
    if CGI_CLI.data.get('enable_device_scp_before_copying'):
        CGI_CLI.uprint('enable_device_scp_before_copying = Y')
    if CGI_CLI.data.get('disable_device_scp_after_copying'):
        CGI_CLI.uprint('disable_device_scp_after_copying = Y')
    if CGI_CLI.data.get('backup_configs_to_device_disk'):
        CGI_CLI.uprint('backup_configs_to_device_disk = Y')
    if CGI_CLI.data.get('delete_device_sw_files_on_end'):
        CGI_CLI.uprint('delete_device_sw_files_on_end = Y')




    ### START TO MOVE WEBPAGE ALLWAYS TO END ##################################
    CGI_CLI.uprint(goto_webpage_end_by_javascript, raw=True)

    ### END DUE TO ERRORS #####################################################
    exit_due_to_error = None

    if len(device_list) == 0:
        result = 'DEVICE NAME(S) NOT INSERTED!'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
        exit_due_to_error = True

    if not USERNAME:
        result = 'USERNAME NOT INSERTED!'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
        exit_due_to_error = True

    if not PASSWORD:
        result = 'PASSWORD NOT INSERTED!'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
        exit_due_to_error = True

    if exit_due_to_error: sys.exit(0)

    ###############################################################################

    if type_subdir and brand_subdir \
        and len(selected_sw_file_types_list) > 0:
        CGI_CLI.uprint('Server %s checks:\n' % (iptac_server), tag = CGI_CLI.result_tag, color = 'blue')

        ### def CHECK LOCAL SW DIRECTORIES ########################################
        directory_list = []
        for actual_file_type in selected_sw_file_types_list:
            actual_file_type_subdir, forget_it = os.path.split(actual_file_type)

            ### WARNING: 'sw_release' COULD BE ALSO FILE !!! ######################
            ### BUG: os.path.exists RETURNS ALLWAYS FALSE, SO I USE OS ls -l ######
            IS_DIRECTORY_OR_FILE_FOUND = False
            FILE_FOUND_STRING, DIR_FOUND_STRING = str(), str()

            ### ABSOLUTE PATH 'actual_file_type', ROMMON IS OUTSIDE OF SUBDIR #####
            if str(actual_file_type).startswith(os.sep):
                use_dir_or_file = str(actual_file_type)
                this_is_directory, file_found = \
                    does_local_directory_or_file_exist_by_ls_l(use_dir_or_file, printall = printall)
                CGI_CLI.uprint('Path=%s, is_dir[%s], is_file[%s]' % \
                    (use_dir_or_file, this_is_directory,  file_found), tag = 'debug', no_printall = not printall)
                if this_is_directory:
                    IS_DIRECTORY_OR_FILE_FOUND = True
                    directory_list.append([use_dir_or_file, str()])
                if file_found and not this_is_directory:
                    try:
                        DIR_FOUND_STRING, FILE_FOUND_STRING = os.path.split(use_dir_or_file)
                        #FILE_FOUND_STRING = use_dir_or_file.split('/')[-1]
                        IS_DIRECTORY_OR_FILE_FOUND = True
                    except: pass
                    directory_list.append([DIR_FOUND_STRING, FILE_FOUND_STRING])

            ### LET DOTS IN DIRECTORY NAME ########################################
            if not IS_DIRECTORY_OR_FILE_FOUND:
                if sw_release:
                    use_dir_or_file = os.path.abspath(os.path.join(os.sep,'home',\
                        'tftpboot',brand_subdir, type_subdir, sw_release, actual_file_type_subdir)).strip()
                else:
                    use_dir_or_file = os.path.abspath(os.path.join(os.sep,'home',\
                        'tftpboot',brand_subdir, type_subdir, actual_file_type_subdir)).strip()

                this_is_directory, file_found = \
                    does_local_directory_or_file_exist_by_ls_l(use_dir_or_file, printall = printall)
                CGI_CLI.uprint('Path=%s, is_dir[%s], is_file[%s]' % \
                    (use_dir_or_file, this_is_directory,  file_found), tag = 'debug', no_printall = not printall)
                if this_is_directory:
                    IS_DIRECTORY_OR_FILE_FOUND = True
                    directory_list.append([use_dir_or_file, str()])
                if file_found and not this_is_directory:
                    try:
                        DIR_FOUND_STRING, FILE_FOUND_STRING = os.path.split(use_dir_or_file)
                        #FILE_FOUND_STRING = use_dir_or_file.split('/')[-1]
                        IS_DIRECTORY_OR_FILE_FOUND = True
                    except: pass
                    directory_list.append([DIR_FOUND_STRING, FILE_FOUND_STRING])

            ### DELETE DOTS FROM DIRECTORY NAME ###################################
            if not IS_DIRECTORY_OR_FILE_FOUND:
                if sw_release:
                    use_dir_or_file = os.path.abspath(os.path.join(os.sep,'home',\
                        'tftpboot',brand_subdir, type_subdir, sw_release.replace('.',''), actual_file_type_subdir)).strip()
                else:
                    use_dir_or_file = os.path.abspath(os.path.join(os.sep,'home',\
                        'tftpboot',brand_subdir, type_subdir, actual_file_type_subdir)).strip()

                this_is_directory, file_found = \
                    does_local_directory_or_file_exist_by_ls_l(use_dir_or_file, printall = printall)
                CGI_CLI.uprint('Path=%s, is_dir[%s], is_file[%s]' % \
                    (use_dir_or_file, this_is_directory, file_found), tag = 'debug', no_printall = not printall)
                if this_is_directory:
                    IS_DIRECTORY_OR_FILE_FOUND = True
                    directory_list.append([use_dir_or_file, str()])
                if file_found and not this_is_directory:
                    try:
                        DIR_FOUND_STRING, FILE_FOUND_STRING = os.path.split(use_dir_or_file)
                        #FILE_FOUND_STRING = use_dir_or_file.split('/')[-1]
                        IS_DIRECTORY_OR_FILE_FOUND = True
                    except: pass
                    directory_list.append([DIR_FOUND_STRING, FILE_FOUND_STRING])

            ### NO SW_RELEASE SUBDIRECTORY ########################################
            if not IS_DIRECTORY_OR_FILE_FOUND:
                use_dir_or_file = os.path.abspath(os.path.join(os.sep,'home',\
                    'tftpboot',brand_subdir, type_subdir, actual_file_type_subdir)).strip()
                this_is_directory, file_found = \
                    does_local_directory_or_file_exist_by_ls_l(use_dir_or_file, printall = printall)
                CGI_CLI.uprint('Path=%s, is_dir[%s], is_file[%s]' % \
                    (use_dir_or_file, this_is_directory, file_found), tag = 'debug', no_printall = not printall)
                if this_is_directory:
                    IS_DIRECTORY_OR_FILE_FOUND = True
                    directory_list.append([use_dir_or_file, str()])
                if file_found and not this_is_directory:
                    try:
                        DIR_FOUND_STRING, FILE_FOUND_STRING = os.path.split(use_dir_or_file)
                        #FILE_FOUND_STRING = use_dir_or_file.split('/')[-1]
                        IS_DIRECTORY_OR_FILE_FOUND = True
                    except: pass
                    directory_list.append([DIR_FOUND_STRING, FILE_FOUND_STRING])

            ### PRINT WARNING #####################################################
            if not IS_DIRECTORY_OR_FILE_FOUND:
                CGI_CLI.uprint('Path for %s is NOT FOUND!' % (actual_file_type), tag = 'warning')

        ### EXIT if DIRECTORY LIST IS VOID ########################################
        if len(directory_list) == 0:
           result = 'Server install directories NOT FOUND!'
           CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
           CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
           sys.exit(0)
        else:
           CGI_CLI.uprint(directory_list, name = 'directory_list', tag = 'debug', no_printall = not printall)

        ### CHECK LOCAL SERVER FILES EXISTENCY ####################################
        for directory_sublist,actual_file_type in zip(directory_list,selected_sw_file_types_list):
            forget_it, actual_file_name = os.path.split(actual_file_type)

            ### WORKARROUND FOR ABSOLUTE PATH, LIKE ROMMON ########################
            if actual_file_type.startswith(os.sep): actual_file_type_subdir = str()
            else:
                actual_file_type_subdir, forget_it = os.path.split(actual_file_type)

            directory, true_local_file_in_sw_release = directory_sublist

            if sw_release and sw_release in directory:
                device_directory = os.path.abspath(os.path.join(os.sep, \
                    type_subdir_on_device, sw_release.replace('.',''), actual_file_type_subdir))
            else:
                ### FILES ON DEVICE WILL BE IN DIRECTORY WITHOUT SW_RELEASE IF SW_RELEASE SUDBIR DOES NOT EXISTS ON SERVER, BECAUSE THEN SW_RELEASE IS FILENAME ###
                device_directory = os.path.abspath(os.path.join(os.sep,type_subdir_on_device, actual_file_type_subdir))
            local_results = LCMD.run_commands({'unix':['ls -l %s' % (directory)]}, printall = printall)

            no_such_files_in_directory = True
            if true_local_file_in_sw_release:
                if true_local_file_in_sw_release in local_results[0]:
                    no_such_files_in_directory = False
                    true_file_name = true_local_file_in_sw_release
                    local_oti_checkum_string = LCMD.run_commands({'unix':['md5sum %s' % \
                        (os.path.join(directory,true_file_name))]}, printall = printall)
                    try: md5_sum = local_oti_checkum_string[0].split()[0].strip()
                    except: md5_sum = str()
                    filesize_in_bytes = os.stat(os.path.join(directory,true_file_name)).st_size
                    ### MAKE TRUE AND UNIQUE FILE LIST, SW RELEASE ONLY ###
                    if not [directory,device_directory,true_file_name,md5_sum,filesize_in_bytes] in true_sw_release_files_on_server:
                        true_sw_release_files_on_server.append([directory,device_directory,true_file_name,md5_sum,filesize_in_bytes])
            else:
                for line in local_results[0].splitlines():
                    ### PROBLEM ARE '*' IN FILE NAME ###
                    all_file_name_parts_found = True
                    for part_of_name in actual_file_name.split('*'):
                        if part_of_name.upper() in line.upper(): pass
                        else: all_file_name_parts_found = False
                    if all_file_name_parts_found:
                        no_such_files_in_directory = False
                        true_file_name = line.split()[-1].strip()
                        local_oti_checkum_string = LCMD.run_commands({'unix':['md5sum %s' % \
                            (os.path.join(directory,true_file_name))]}, printall = printall)
                        md5_sum = local_oti_checkum_string[0].split()[0].strip()
                        filesize_in_bytes = os.stat(os.path.join(directory,true_file_name)).st_size
                        ### MAKE TRUE AND UNIQUE FILE LIST ###
                        if not [directory,device_directory,true_file_name,md5_sum,filesize_in_bytes] in true_sw_release_files_on_server:
                            true_sw_release_files_on_server.append([directory,device_directory,true_file_name,md5_sum,filesize_in_bytes])
            if no_such_files_in_directory:
                result = 'Specified %s file(s) NOT FOUND in %s!' % (actual_file_name,directory)
                CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'orange')
                CGI_CLI.result_list.append([copy.deepcopy(result), 'orange'])

        ### PRINT LIST OF FILES OR END SCRIPT #################################
        if len(true_sw_release_files_on_server) > 0:
            CGI_CLI.tableprint(['File(s)','md5 checksum(s)','device folder(s)','filesize:'], \
                header = True, color = 'blue')
            for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server:
                CGI_CLI.tableprint(['%s/%s' % (directory,file), md5, dev_dir, '%.2fMB' % (float(fsize)/1048576)],\
                    color = 'blue')
            CGI_CLI.tableprint(end_table = True)
            CGI_CLI.uprint('\n', timestamp = 'no')
        else: sys.exit(0)

    else:
        result = 'Specified file(s) NOT FOUND!'
        CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
        CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
        sys.exit(0)

    ### MAKE ALL SUB-DIRECTORIES ONE BY ONE ###################################
    redundant_dev_dir_list = [ dev_dir for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server ]
    dev_dir_set = set(redundant_dev_dir_list)
    unique_device_directory_list = list(dev_dir_set)

    ### GET DEVICE DRIVE STRING ###############################################
    if CGI_CLI.data.get('force_rewrite_sw_files_on_device'):
        device_drive_string, router_type = get_device_drive_string(device_list = device_list, \
            USERNAME = USERNAME, PASSWORD = PASSWORD, \
            printall = printall, \
            silent_mode = True)

        for device in device_list:
            ### DELETE FILES ON START - JUNIPER SHOWS BAD SIZE WHEN REWRITES ##
            delete_files(device = device, \
                unique_device_directory_list = unique_device_directory_list, \
                true_sw_release_files_on_server = true_sw_release_files_on_server,\
                printall = printall)

        CGI_CLI.uprint('Device    All_File(s)_to_copy:', tag = 'h3', color = 'blue')
        CGI_CLI.uprint(no_newlines = True, start_tag = 'p', color = 'blue')

        ### DO MISSING_FILES_PER_DEVICE_LIST, BECAUSE IT IS NEEDED FURTHER ####
        for device in device_list:
            for directory, dev_dir, file, md5, fsize in true_sw_release_files_on_server:
                missing_files_per_device_list.append( \
                    [device,[directory, dev_dir, file, md5, fsize]])
                CGI_CLI.uprint('%s    %s' % \
                    (device, device_drive_string + os.path.join(dev_dir, file)))
        CGI_CLI.uprint(end_tag = 'p')

    elif len(selected_sw_file_types_list) > 0 or sw_release:
        if CGI_CLI.data.get('check_device_sw_files_only'):
            ### CHECK EXISTING FILES ON DEVICES ###############################
            all_files_on_all_devices_ok, missing_files_per_device_list, \
                device_drive_string, router_type, compatibility_problem_list = \
                check_files_on_devices(device_list = device_list, \
                true_sw_release_files_on_server = true_sw_release_files_on_server, \
                USERNAME = USERNAME, PASSWORD = PASSWORD, \
                printall = printall, disk_low_space_devices = disk_low_space_devices,\
                check_mode = True)
        else:
            ### CHECK EXISTING FILES ON DEVICES ###############################
            all_files_on_all_devices_ok, missing_files_per_device_list, \
                device_drive_string, router_type, compatibility_problem_list = \
                check_files_on_devices(device_list = device_list, \
                true_sw_release_files_on_server = true_sw_release_files_on_server, \
                USERNAME = USERNAME, PASSWORD = PASSWORD, \
                printall = printall, disk_low_space_devices = disk_low_space_devices,\
                check_mode = False)


    ### FIND MAX FILE SIZE, FOR JUNIPER RE0 LOCAL COPY DISK CHECK #############
    max_file_size_even_if_already_exists_on_device = 0
    ### PRATIMA'S HINT WORKARROUND ############################################
    # for directory,dev_dir,file,md5,fsize in true_sw_release_files_on_server:
        # if fsize > max_file_size_even_if_already_exists_on_device:
            # max_file_size_even_if_already_exists_on_device = fsize


    ### def CHECK DISK SPACE ON DEVICES #######################################
    original_device_list = copy.deepcopy(device_list)
    if not CGI_CLI.data.get('check_device_sw_files_only'):
        if len(selected_sw_file_types_list) > 0 or sw_release:
            if all_files_on_all_devices_ok: pass
            else:
                disk_low_space_devices = check_free_disk_space_on_devices(\
                    device_list = device_list, \
                    missing_files_per_device_list = missing_files_per_device_list, \
                    USERNAME = USERNAME, PASSWORD = PASSWORD, \
                    printall = printall, \
                    max_file_size_even_if_already_exists_on_device = \
                        max_file_size_even_if_already_exists_on_device)

        ### DELETE NOT-OK DISK SPACE DEVICES FROM COPY LIST ###################
        if len(disk_low_space_devices) > 0:
            disk_ok_missing_files_per_device_list, disk_ok_device_list = [], []
            for copy_to_device, missing_or_bad_files_per_device in missing_files_per_device_list:
                directory, dev_dir, file, md5, fsize = missing_or_bad_files_per_device
                if copy_to_device in disk_low_space_devices: pass
                else:
                    disk_ok_missing_files_per_device_list.append([copy_to_device,[directory, dev_dir, file, md5, fsize]])
                    if not copy_to_device in disk_ok_device_list: disk_ok_device_list.append(copy_to_device)
            ### RENEW LISTS ###
            del device_list
            del missing_files_per_device_list
            missing_files_per_device_list = disk_ok_missing_files_per_device_list
            device_list = disk_ok_device_list


    ### def LOOP TILL ALL FILES ARE COPIED OK #################################
    counter_of_scp_attempts = 0
    while not all_files_on_all_devices_ok:
        missing_backup_re_list = []
        counter_of_scp_attempts += 1

        ### DO NOT COPY FILES IN CHECK ONLY MODE ##############################
        if CGI_CLI.data.get('check_device_sw_files_only'): break

        ### DO NOT SCP IF NO SW VERSION #######################################
        if len(selected_sw_file_types_list) > 0 or sw_release: pass
        else: break

        ### END IF FILE COMPATIBILTY PROBLEM OCCURS ON DEVICES AFTER ONE SCP ##
        if len(compatibility_problem_list) > 0 and counter_of_scp_attempts > 1:
            break

        ### TRY SCP X TIMES, THEN END #########################################
        if counter_of_scp_attempts > total_number_of_scp_attempts:
            result = 'Multiple (%d) scp attempts failed!' % \
                (total_number_of_scp_attempts)
            CGI_CLI.uprint(result, color = 'red', tag = CGI_CLI.result_tag)
            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
            break

        ### FORCE REWRITE ONLY ONCE ###########################################
        if CGI_CLI.data.get('force_rewrite_sw_files_on_device') and counter_of_scp_attempts <= 1:
            force_rewrite = True
        else: force_rewrite = False

        ### DO SCP COPYING - FORCE REWRITE HAS A SENSE FIRST TIME ONLY ########
        copy_files_to_devices(true_sw_release_files_on_server = true_sw_release_files_on_server, \
            missing_files_per_device_list = missing_files_per_device_list, \
            device_list = device_list, USERNAME = USERNAME, PASSWORD = PASSWORD, \
            device_drive_string = device_drive_string, router_type = router_type, \
            force_rewrite = force_rewrite)

        ### TIMEOUT ###########################################################
        time.sleep(6)

        ### COPY DEVICE FILES TO HUAWEI SLAVE CFCARD ##########################
        huawei_copy_device_files_to_slave_cfcard(true_sw_release_files_on_server, \
            unique_device_directory_list)

        ### COPY DEVICE FILES TO JUNIPER OTHER ROUTING ENGINE #################
        if CGI_CLI.data.get('ignore_missing_backup_re_on_junos'): pass
        else:
            missing_backup_re_list = juniper_copy_device_files_to_other_routing_engine( \
                true_sw_release_files_on_server, \
                unique_device_directory_list)
            if len(missing_backup_re_list) > 0: sys.exit(0)

        ### CHECK DEVICE FILES AFTER SCP COPYING ##############################
        all_files_on_all_devices_ok, missing_files_per_device_list, \
            device_drive_string, router_type, compatibility_problem_list = \
            check_files_on_devices(device_list = device_list, \
            true_sw_release_files_on_server = true_sw_release_files_on_server, \
            USERNAME = USERNAME, PASSWORD = PASSWORD, \
            printall = printall, check_mode = True, \
            disk_low_space_devices = disk_low_space_devices)

        ### DO LOCAL FILE COPY TO RE1/slave#cfcard AND CHECK BEFORE END #######
        if len(device_list) == 0 or len(missing_files_per_device_list) == 0:
            break
    ### END OF LOOP TILL ALL FILES ARE COPIED OK ##############################


    ### def ADITIONAL DEVICE ACTIONS ##########################################
    if CGI_CLI.data.get('backup_configs_to_device_disk') \
        or CGI_CLI.data.get('delete_device_sw_files_on_end') \
        or CGI_CLI.data.get('enable_device_scp_before_copying') \
        or CGI_CLI.data.get('disable_device_scp_after_copying'):
        for device in original_device_list:

            ### REMOTE DEVICE OPERATIONS ######################################
            if device:
                RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                    printall = printall)

                if not RCMD.ssh_connection:
                    result = 'PROBLEM TO CONNECT TO %s DEVICE.' % (device)
                    CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                    CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
                    RCMD.disconnect()
                    continue

                ### CHECK LOCAL SERVER AND DEVICE HDD FILES #######################
                actual_date_string = str(time.strftime("%Y_%mm%dd_%Hh%M",time.gmtime(time.time())))

                ### def BACKUP NORMAL AND ADMIN CONFIG ########################
                if CGI_CLI.data.get('backup_configs_to_device_disk'):
                    backup_config_rcmds = {
                        'cisco_ios':[
                        'copy running-config %s%s-config.txt' % (RCMD.drive_string, actual_date_string),
                        ],

                        'cisco_xr':[
                        'copy running-config %s%s-config.txt' % (RCMD.drive_string, actual_date_string),
                        'admin',
                        'copy running-config %sadmin-%s-config.txt' % (RCMD.drive_string, actual_date_string),
                        'exit'
                        ],

                        'juniper': [
                        'show configuration | save re0:/var/tmp/%s-config.txt' % (actual_date_string)
                        ],

                        'huawei': [
                        'save %s/%s-config.cfg' % (RCMD.drive_string, actual_date_string),
                        'save slave#%s/%s-config.cfg' % (RCMD.drive_string, actual_date_string)
                        ]
                    }
                    if not CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
                        backup_config_rcmds['juniper'].append('show configuration | save re1:/var/tmp/%s-config.txt' % (actual_date_string))

                    CGI_CLI.uprint('backup configs on %s' % (device), \
                        no_newlines = None if printall else True)
                    forget_it = RCMD.run_commands(backup_config_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    time.sleep(0.5)

                    ### CHECK CONFIG FILE EXISTENCY ###
                    check_dir_cfgfiles_cmds = {'cisco_xr':[],'cisco_ios':[], \
                        'huawei':[], 'juniper':[]}

                    check_dir_cfgfiles_cmds['cisco_ios'].append( \
                        'dir %s%s-config.txt' % (RCMD.drive_string, actual_date_string))

                    check_dir_cfgfiles_cmds['cisco_xr'].append( \
                        'dir %s%s-config.txt' % (RCMD.drive_string, actual_date_string))
                    check_dir_cfgfiles_cmds['cisco_xr'].append('admin')
                    check_dir_cfgfiles_cmds['cisco_xr'].append( \
                        'dir %sadmin-%s-config.txt' % (RCMD.drive_string, actual_date_string))
                    check_dir_cfgfiles_cmds['cisco_xr'].append('exit'),

                    check_dir_cfgfiles_cmds['huawei'].append( \
                        'dir %s/%s-config.cfg' % (RCMD.drive_string, actual_date_string))
                    check_dir_cfgfiles_cmds['huawei'].append( \
                        'dir slave#%s/%s-config.cfg' % (RCMD.drive_string, actual_date_string))

                    check_dir_cfgfiles_cmds['juniper'].append( \
                        'file list re0:/var/tmp/%s-config.txt' % (actual_date_string))

                    if not CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
                        check_dir_cfgfiles_cmds['juniper'].append( \
                            'file list re1:/var/tmp/%s-config.txt' % (actual_date_string))

                    cfgfiles_cmds_outputs = RCMD.run_commands(check_dir_cfgfiles_cmds, \
                        autoconfirm_mode = True, printall = printall)
                    CGI_CLI.uprint('\n', timestamp = 'no')

                    if RCMD.router_type == 'cisco_xr':
                        if '%s-config.txt' % (actual_date_string) in cfgfiles_cmds_outputs[0] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[0]:
                            result = '%s backup config done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else: CGI_CLI.uprint('%s backup config problem!' % (device), tag = CGI_CLI.result_tag, color = 'red')
                        if '%s-config.txt' % (actual_date_string) in cfgfiles_cmds_outputs[2] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[2]:
                            result = '%s backup admin config done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else:
                            result = '%s backup admin config problem!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])

                    elif RCMD.router_type == 'cisco_ios':
                        if '%s-config.txt' % (actual_date_string) in cfgfiles_cmds_outputs[0] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[0]:
                            result = '%s backup config done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else:
                            result = '%s backup config problem!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])

                    elif RCMD.router_type == 'juniper':
                        if '%s-config.txt' % (actual_date_string) in cfgfiles_cmds_outputs[0] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[0]:
                            result = '%s backup config to re0 done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else:
                            result = '%s backup config to re0 problem!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
                        if not CGI_CLI.data.get('ignore_missing_backup_re_on_junos'):
                            if '%s-config.txt' % (actual_date_string) in cfgfiles_cmds_outputs[1] \
                                and not 'No such file or directory' in cfgfiles_cmds_outputs[1]:
                                result = '%s backup config to re1 done!' % (device)
                                CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                                CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                            else:
                                result = '%s backup config to re1 problem!' % (device)
                                CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                                CGI_CLI.result_list.append([copy.deepcopy(result),'red'])

                    elif RCMD.router_type == 'huawei':
                        if '%s-config.cfg' % (actual_date_string) in cfgfiles_cmds_outputs[0] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[0] \
                            and not "Such file or path doesn't exist." in cfgfiles_cmds_outputs[0]:
                            result = '%s backup config to cfcard done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else:
                            result = '%s backup config to cfcard problem!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])
                        if '%s-config.cfg' % (actual_date_string) in cfgfiles_cmds_outputs[1] \
                            and not 'No such file or directory' in cfgfiles_cmds_outputs[1] \
                            and not "Such file or path doesn't exist." in cfgfiles_cmds_outputs[0]:
                            result = '%s backup config to slave#cfcard done!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'green')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'green'])
                        else:
                            result = '%s backup config to slave#cfcard problem!' % (device)
                            CGI_CLI.uprint(result, tag = CGI_CLI.result_tag, color = 'red')
                            CGI_CLI.result_list.append([copy.deepcopy(result), 'red'])


                ### def DELETE FILES ON END ###################################
                if CGI_CLI.data.get('delete_device_sw_files_on_end'):
                    delete_files(device = device, \
                        unique_device_directory_list = unique_device_directory_list, \
                        true_sw_release_files_on_server = true_sw_release_files_on_server,\
                        printall = printall)

                ### def DISABLE SCP ###########################################
                if CGI_CLI.data.get('disable_device_scp_after_copying'):
                    do_scp_disable(printall = printall)

                ### DISCONNECT ################################################
                RCMD.disconnect()

    del sql_inst
except SystemExit: pass
except KeyboardInterrupt:
    result = 'KeyboardInterrupt - terminating the process'
    CGI_CLI.uprint(result, color = 'magenta')
    pass
except:
    traceback_found = traceback.format_exc()
    CGI_CLI.uprint(str(traceback_found), tag = CGI_CLI.result_tag, color = 'magenta')

    ### SEND EMAIL WITH ERROR/TRACEBACK LOGFILE TO SUPPORT ########################
    if traceback_found:
        CGI_CLI.send_me_email( \
            subject = 'TRACEBACK-SW_ULOADER-' + logfilename.replace('\\','/').\
            split('/')[-1] if logfilename else str(), \
            email_body = str(traceback_found),\
            file_name = logfilename, username = 'pnemec')



