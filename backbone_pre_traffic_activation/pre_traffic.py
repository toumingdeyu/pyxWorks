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

import cgi
#import cgitb; cgitb.enable()
import requests
from mako.template import Template
from mako.lookup import TemplateLookup
import ipaddress




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
                            help = "target router to access. For now supports only 1.")
        parser.add_argument("--interface",
                            action = "store", dest = 'interface',
                            default = str(),
                            help = "interface id for testing. Interface list separated by , without whitespace.")
        parser.add_argument("--precheck",
                            action = "store_true", dest = 'precheck', default = None,
                            help = "do monitoring/precheck")
        parser.add_argument("--postcheck",
                            action = "store_true", dest = 'postcheck', default = None,
                            help = "do traffic/postcheck")
        parser.add_argument("--swan_id",
                            action = "store", dest = 'swan_id',
                            default = str(),
                            help = "swan_id name stored in DB")
        parser.add_argument("--reinit_swan_id",
                            action = "store_true", dest = 'reinit_swan_id', default = None,
                            help = "re-init/rewrite initial swan_id record in DB")
        parser.add_argument("--send_email",
                            action = "store_true", dest = 'send_email', default = None,
                            help = "send email with test result logs")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
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
            if variable and value and \
                not variable in ["username", "password", "cusername", "cpassword"]:
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
            if variable == "cusername": CGI_CLI.username = value.decode('base64','strict')
            if variable == "cpassword": CGI_CLI.password = value.decode('base64','strict')
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
        CGI_CLI.logtofile(end_log = True, ommit_timestamp = True)
        CGI_CLI.logfilename = logfilename
        time.sleep(0.1)
        CGI_CLI.logtofile(start_log = True, ommit_timestamp = True)

    @staticmethod
    def logtofile(msg = None, raw_log = None, start_log = None, end_log = None, \
        ommit_timestamp = None):
        msg_to_file = str()
        if CGI_CLI.logfilename:
            ### HTML LOGGING ##################################################
            if CGI_CLI.cgi_active:
                ### ADD HTML HEADER ###########################################
                if start_log:
                    msg_to_file += '<!DOCTYPE html><html><head><title>%s</title></head><body>'\
                        % (CGI_CLI.logfilename)
                    msg_to_file += '\n<br/>%sLOG_START:<br/>' % ( CGI_CLI.get_timestamp())

                ### CONVERT TEXT TO HTML FORMAT ###############################
                if msg:
                    msg_to_file += '\n<br/>' + CGI_CLI.get_timestamp() if not ommit_timestamp else str()
                    if not raw_log:
                        msg_to_file += str(msg.replace('&','&amp;').\
                            replace('<','&lt;').\
                            replace('>','&gt;').replace(' ','&nbsp;').\
                            replace('"','&quot;').replace("'",'&apos;').\
                            replace('\n','<br/>'))
                    else: msg_to_file += msg

                ### ADD HTML FOOTER ###########################################
                if end_log:
                    msg_to_file += '\n<br/>%sLOG_END.<br/>' % ( CGI_CLI.get_timestamp())
                    msg_to_file += '</body></html>'

            ### CLI LOGGING ###################################################
            else:
                if start_log:
                    msg_to_file += '\n%sLOG_START:\n' % ( CGI_CLI.get_timestamp())

                if msg:
                    msg_to_file += '\n' + CGI_CLI.get_timestamp() if not ommit_timestamp else str()
                    msg_to_file = msg + '\n'

                if end_log:
                    msg_to_file += '\n%sLOG_END.\n' % ( CGI_CLI.get_timestamp())

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
            if not ommit_logging: CGI_CLI.logtofile(msg = msg, raw_log = raw_log, \
                                      ommit_timestamp = True)

    @staticmethod
    def uprint(text = None, tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        ommit_logging = None, no_newlines = None, start_tag = None, end_tag = None, raw = None, \
        timestamp = None, printall = None, no_printall = None, stop_button = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
           timestamp = True - locally allow (CGI_CLI.timestamp = True has priority)
           timestamp = 'no' - locally disable even if CGI_CLI.timestamp == True
           Use 'no_printall = not CGI_CLI.printall' instead of printall = False
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

            if tag == 'warning': text_color = CGI_CLI.bcolors.YELLOW
            if tag == 'debug': text_color = CGI_CLI.bcolors.CYAN

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
    def get_scriptname():
        i_pyfile = sys.argv[0]
        try: pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: pyfile = i_pyfile.strip()
        return pyfile

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
            RCMD.vision_api_json_string = None
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
            RCMD.router_os_by_snmp = None
            RCMD.KNOWN_OS_TYPES = ['cisco_xr', 'cisco_ios', 'juniper', 'juniper_junos', 'huawei' ,'linux']
            try: RCMD.DEVICE_HOST = device.split(':')[0]
            except: RCMD.DEVICE_HOST = str(device)
            try: RCMD.DEVICE_PORT = device.split(':')[1]
            except: RCMD.DEVICE_PORT = '22'


            ### PING 1 = IS ALIVE TEST , IF NOT FIND IP ADDRESS ###############
            if RCMD.is_alive(device):
                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - ping DEVICE by name - OK.\n', \
                        no_printall = not printall, tag = 'debug')
                device_id = RCMD.DEVICE_HOST
            else:
                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - start.\n', \
                        no_printall = not printall, tag = 'debug')

                RCMD.ip_address = RCMD.get_IP_from_vision(device)

                if CGI_CLI.timestamp:
                        CGI_CLI.uprint('RCMD.connect - after get_IP_from_vision.\n', \
                            no_printall = not printall, tag = 'debug')

                device_id = RCMD.ip_address

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

            ### SNMP DETECTION ################################################
            RCMD.router_os_by_snmp = RCMD.snmp_find_router_type(device_id)

            if CGI_CLI.timestamp:
                    CGI_CLI.uprint('RCMD.connect - after SNMP detection(%s).\n' % (str(RCMD.router_os_by_snmp)), \
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
        sim_config = None, sim_all = None, ignore_prompt = None, ignore_syntax_error = None):
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
                if not RCMD.silent_mode:
                    CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line, color = 'blue', ommit_logging = True)

            if long_lasting_mode:
                if CGI_CLI.cgi_active:
                    CGI_CLI.logtofile('<p style="color:blue;">REMOTE_COMMAND' + \
                        sim_mark + ': ' + cmd_line + '</p>\n<pre>\n', raw_log = True)
                    if not RCMD.silent_mode and printall or RCMD.printall:
                        CGI_CLI.uprint('<pre>\n', timestamp = 'no', raw = True, ommit_logging = True)
                elif not RCMD.silent_mode:
                    CGI_CLI.logtofile('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line + '\n' )

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

            if not long_lasting_mode:
                if printall or RCMD.printall:
                        CGI_CLI.uprint(last_output, tag = 'pre', timestamp = 'no', ommit_logging = True)
                elif not RCMD.silent_mode:
                        CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
                ### LOG ALL ONLY ONCE, THAT IS BECAUSE PREVIOUS LINE ommit_logging = True ###
                if CGI_CLI.cgi_active:
                    CGI_CLI.logtofile('<p style="color:blue;">REMOTE_COMMAND' + \
                        sim_mark + ': ' + cmd_line + '</p>\n<pre>' + \
                        CGI_CLI.html_escape(last_output, pre_tag = True) + \
                        '\n</pre>\n', raw_log = True)
                else: CGI_CLI.logtofile('REMOTE_COMMAND' + sim_mark + ': ' + \
                          cmd_line + '\n' + last_output + '\n')
            else:
                if CGI_CLI.cgi_active:
                    CGI_CLI.logtofile('\n</pre>\n', raw_log = True)
                    if not RCMD.silent_mode:
                        if printall or RCMD.printall:
                            CGI_CLI.uprint('\n</pre>\n', timestamp = 'no', raw = True, ommit_logging = True)
                        else:
                            CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
                else:
                    if not RCMD.silent_mode:
                        if printall or RCMD.printall:
                            CGI_CLI.uprint('\n', timestamp = 'no', ommit_logging = True)
                        else:
                            CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
            if not ignore_syntax_error:
                for line in last_output.splitlines():
                    if line.strip() == '^':
                        CGI_CLI.uprint("\nSYNTAX ERROR in CMD: '%s' !\n" % (str(cmd_line)), timestamp = 'no', color = 'orange')
        return str(last_output)

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None, \
        do_not_final_print = None , commit_text = None, submit_result = None , \
        long_lasting_mode = None, autoconfirm_mode = None, ignore_prompt = None, \
        ignore_syntax_error = None):
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
                        autoconfirm_mode = autoconfirm_mode, \
                        ignore_syntax_error = ignore_syntax_error))
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
                if long_lasting_mode:
                    if printall and buff_read and not RCMD.silent_mode:
                        CGI_CLI.uprint('%s' % (buff_read), no_newlines = True, \
                            ommit_logging = True)

                    CGI_CLI.logtofile('%s' % (buff_read), ommit_timestamp = True)

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
                    CGI_CLI.uprint("COMMAND TIMEOUT!!", tag = 'warning')
                    exit_loop = True
                    break

            if long_lasting_mode:
                ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ##############
                if not command_counter_100msec%100 and CGI_CLI.cgi_active:
                    CGI_CLI.uprint("<script>console.log('10s...');</script>", \
                        raw = True)
                    CGI_CLI.logtofile('[+10sec_MARK]\n')

                    if printall and buff_read and not RCMD.silent_mode:
                        CGI_CLI.uprint('_', no_newlines = True, \
                            timestamp = 'no', ommit_logging = True)

            ### EXIT SOONER THAN CONNECTION TIMEOUT IF LONG LASTING OR NOT ####
            if command_counter_100msec + 100 > RCMD.CONNECTION_TIMEOUT*10:
                CGI_CLI.uprint("LONG LASTING COMMAND TIMEOUT!!", tag = 'warning')
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
                CGI_CLI.uprint("ENTER INSERTED AFTER DEVICE INACTIVITY!!", \
                    tag = 'debug', no_printall = not CGI_CLI.printall)
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
        router_os, prompt, netmiko_os = str(), str(), str()

        ### AVOID SSH DETECTION COMMANDS TO SAVE TIME IF ROUTER TYPE WAS DETECTED ###
        if RCMD.router_os_by_snmp:
            router_os = copy.deepcopy(RCMD.router_os_by_snmp)
            netmiko_os = copy.deepcopy(RCMD.router_os_by_snmp)

        ### 1-CONNECTION ONLY, connection opened in RCMD.connect ###
        # prevent --More-- in log banner (space=page, enter=1line,tab=esc)
        # \n\n get prompt as last line

        if CGI_CLI.timestamp:
            CGI_CLI.uprint('RCMD.connect - before ssh_raw_detect_prompt.\n', \
                no_printall = not printall, tag = 'debug')

        prompt = ssh_raw_detect_prompt(RCMD.ssh_connection, debug=debug)

        if CGI_CLI.timestamp:
            CGI_CLI.uprint('RCMD.connect - after ssh_raw_detect_prompt(%s).\n' % (str(prompt)), \
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

        if CGI_CLI.timestamp:
            CGI_CLI.uprint('RCMD.connect - after router type detection commands.\n', \
                no_printall = not printall, tag = 'debug')

        if not router_os:
            CGI_CLI.uprint("\nCannot find recognizable OS in %s" % (output), color = 'magenta')

        if router_os == 'ios-xe': netmiko_os = 'cisco_ios'
        if router_os == 'ios-xr': netmiko_os = 'cisco_xr'
        if router_os == 'junos': netmiko_os = 'juniper'
        if router_os == 'linux': netmiko_os = 'linux'
        if router_os == 'vrp': netmiko_os = 'huawei'
        return netmiko_os, prompt

    @staticmethod
    def get_json_from_vision(URL = None):
        global vision_api_json_string
        if RCMD.USERNAME and RCMD.PASSWORD:
            os.environ['CURL_AUTH_STRING'] = '%s:%s' % \
                (RCMD.USERNAME,RCMD.PASSWORD)
            if URL: url = URL
            else: url = 'https://vision.opentransit.net/onv/api/nodes/'
            local_command = 'curl -u ${CURL_AUTH_STRING} -m 1 %s' % (url)
            RCMD.vision_api_json_string = LCMD.run_commands(\
                {'unix':[local_command]}, printall = None, ommit_logging = True)
            os.environ['CURL_AUTH_STRING'] = '-'

    @staticmethod
    def get_IP_from_vision(DEVICE_NAME = None):
        device_ip_address = str()
        if not RCMD.vision_api_json_string: RCMD.get_json_from_vision()
        if RCMD.vision_api_json_string and DEVICE_NAME:
            try:
                device_ip_address = str(RCMD.vision_api_json_string[0].split(DEVICE_NAME.upper())[1].\
                    splitlines()[1].\
                    split('"ip":')[1].replace('"','').replace(',','')).strip()
            except: pass
        return device_ip_address

    @staticmethod
    def snmp_find_router_type(host = None):
        router_os = None
        if host:
            SNMP_COMMUNITY = 'qLqVHPZUNnGB'
            snmp_req = "snmpget -v1 -c " + SNMP_COMMUNITY + " -t 5 " + host + " sysDescr.0"
            #return_stream = os.popen(snmp_req)
            #retvalue = return_stream.readline()

            os_output = None
            if 'WIN32' in sys.platform.upper(): pass
            else:
                try: os_output = subprocess.check_output(str(snmp_req), \
                         stderr = subprocess.STDOUT, shell = True).decode(CGI_CLI.sys_stdout_encoding)
                except: pass

            if os_output:
                if 'Cisco IOS XR Software' in os_output:
                    router_os = 'cisco_xr'
                elif 'Cisco IOS Software' in os_output:
                    router_os = 'cisco_ios'
                elif 'Juniper Networks' in os_output:
                    router_os = 'juniper'
                elif 'Huawei' in os_output:
                    router_os = 'huawei'
        return router_os






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
                    '\n</pre>\n', raw_log = True, ommit_timestamp = True)
            else: CGI_CLI.logtofile(str(os_output) + '\n', ommit_timestamp = True)
        return str(os_output)

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
                            '\n</pre>\n', raw_log = True, ommit_timestamp = True)
                    else: CGI_CLI.logtofile(os_output + '\n', ommit_timestamp = True)
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

    def __init__(self, host = None, user = None, password = None, database = None, printall = None):
        if int(sys.version_info[0]) == 3 and not 'pymysql.connect' in sys.modules: import pymysql
        elif int(sys.version_info[0]) == 2 and not 'mysql.connector' in sys.modules: import mysql.connector
        default_ipxt_data_collector_delete_columns = ['id','last_updated']
        self.sql_connection = None
        self.printall = printall
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
            CGI_CLI.uprint('SQL_CMD[%s]' % (sql_command), no_printall = not self.printall)
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
        if not prefix: filename_prefix = os.path.join(LOGDIR,'device')
        else: filename_prefix = prefix
        if not suffix: filename_suffix = 'log'
        else: filename_suffix = suffix
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s.%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,sys.argv[0].replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/')\
            .split('/')[-1],USERNAME,filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath

###############################################################################

def get_interface_list_per_device(device = None, action_type = None):
    interface_list = []
    get_interface_rcmds = {
        'cisco_ios':['sh interfaces description'],
        'cisco_xr':['sh interfaces description'],
        'juniper':['show interfaces description'],
        'huawei':['display interface description '],
    }

    if device:
        RCMD.connect(device, username = USERNAME, password = PASSWORD, \
            printall = printall, silent_mode = True, \
            disconnect_timeout = 0.1)

        if RCMD.ssh_connection:
            get_interface_rcmd_outputs = RCMD.run_commands(get_interface_rcmds, \
                autoconfirm_mode = True, \
                printall = printall)

            if_lines = []
            try:
                if_lines = get_interface_rcmd_outputs[0].strip().split('Description')[1].splitlines()[1:]
                if '-----' in if_lines[0]: del if_lines[0]
                if if_lines[-1] in RCMD.DEVICE_PROMPTS: del if_lines[-1]
            except: pass

            for in_line_orig in if_lines:
                if_line = in_line_orig.replace('                                               ','').strip()
                if if_line.strip() == '{master}': continue

                if 'bb' in action_type:
                    if '- CUSTOM' in if_line.strip().upper() \
                        or '-CUSTOM' in if_line.strip().upper(): continue
                    if '- PRIVPEER' in if_line.strip().upper() \
                        or '-PRIVPEER' in if_line.strip().upper(): continue
                    if '- PUBPEER' in if_line.strip().upper() \
                        or '-PUBPEER' in if_line.strip().upper(): continue
                    if 'LOOPBACK' in if_line.strip().upper(): continue
                elif 'custom' in action_type:
                    if '- BACKBONE' in if_line.strip().upper() \
                        or '-BACKBONE' in if_line.strip().upper(): continue
                    if 'LOOPBACK' in if_line.strip().upper(): continue


                try: if_name = if_line.split()[0]
                except: if_name = str()

                if not '100GE' in if_name: if_name = if_name.replace('GE','Gi')

                try: if_name = if_name.split('(')[0]
                except: pass

                try: if_line_mod = if_name + ' - ' + ' '.join(if_line.split()[3:])
                except: if_line_mod = str()
                if if_name and if_line_mod: interface_list.append([if_line_mod, if_name])

        RCMD.disconnect()
    return interface_list

###############################################################################

### GET_XPATH_FROM_XMLSTRING ===================================================
def get_void_json_elements(json_data, ignore_void_strings = None, \
    ignore_void_lists = None, no_equal_sign = None, no_root_backslash = None):
    """
    FUNCTION: get_void_json_elements()
    parameters: json_data   - data structure
    returns:    xpath_list  - lists of all void xpaths found in json_data
    """
    ### SUBFUNCTION --------------------------------------------------------------
    def get_dictionary_subreferences(tuple_data):
        json_deeper_references = []
        parrent_xpath = tuple_data[0]
        json_data = tuple_data[1]
        if isinstance(json_data, (dict,collections.OrderedDict)):
            for key in json_data.keys():
                key_content=json_data.get(key)
                if isinstance(key_content, (dict,collections.OrderedDict)): json_deeper_references.append((parrent_xpath+'/'+key,key_content))
                elif isinstance(key_content, (list,tuple)):
                    if len(key_content)==0:
                        json_deeper_references.append((parrent_xpath+'/'+key+'=[]',key_content))
                    for ii,sub_xml in enumerate(key_content,start=0):
                        if type(sub_xml) in [dict,collections.OrderedDict]: json_deeper_references.append((parrent_xpath+'/'+key+'['+str(ii)+']',sub_xml))
                elif isinstance(key_content, (six.string_types,six.integer_types,float,bool,bytearray)):
                      if '#text' in key: json_deeper_references.append((parrent_xpath+'="'+key_content+'"',key_content))
                      elif str(key)[0]=='@': json_deeper_references.append((parrent_xpath+'['+key+'="'+key_content+'"]',key_content))
                      else: json_deeper_references.append((parrent_xpath+'/'+key+'="'+str(key_content)+'"',key_content))
                elif key_content == None:
                    json_deeper_references.append((parrent_xpath+'/'+key+'='+str(key_content),key_content))
        return json_deeper_references
    ### FUNCTION -----------------------------------------------------------------
    references,xpath_list = [], []
    references.append(('',json_data))
    while len(references)>0:
        add_references=get_dictionary_subreferences(references[0])
        if '=None' in references[0][0]\
            or not ignore_void_strings and '=""' in references[0][0]\
            or not ignore_void_lists and '=[]' in references[0][0]:
            if no_equal_sign and no_root_backslash: xpath_list.append(str(references[0][0].split('=')[0][1:]))
            elif no_equal_sign and not no_root_backslash: xpath_list.append(references[0][0].split('=')[0])
            else: xpath_list.append(references[0][0])
        references.remove(references[0])
        references=add_references+references
    del references
    return xpath_list
### ----------------------------------------------------------------------------

###############################################################################

def get_fiblist(input_text = None):
    fib_list = []
    if input_text:
        fib_list = re.findall(r'LD[0-9]{5,6}|FIB[0-9]{5,6}|LDA[0-9]{5,6}', str(input_text))
        fib_dash_list = re.findall(r'LD[0-9]{5,6}\-LDA[0-9]{5,6}', str(input_text))

        fib_set = set(fib_list)
        fib_list = list(fib_set)
        fib_list.sort()

        fib_dash_set = set(fib_dash_list)
        fib_dash_list = list(fib_dash_set)
        fib_dash_list.sort()

        for dash_line in fib_dash_list:
            for line in fib_list:
                if line in dash_line:
                    fib_list.remove(line)
    return fib_list

###############################################################################

check_interface_result_ok, check_warning_interface_result_ok = True, True
def check_interface_data_content(where = None, what_yes_in = None, what_not_in = None, \
    exact_value_yes = None, lower_than = None, higher_than = None, equals_to = None,
    warning = None, ignore_data_existence = None):
    """
    multiple tests in once are possible
    what_yes_in - string = if occurs in where then OK.
    what_not_in - list = if all items from list occurs, then FAIL. Otherwise OK.
    what_not_in - string = if string occurs in text, then FAIL.
    """
    global check_interface_result_ok
    global check_warning_interface_result_ok
    local_check_interface_result_ok, Alarm_text = 0, []
    key_exists = False
    where_value = str()

    if warning:
        try:
            where_value = eval('interface_warning_data%s' % (str(where)))
            key_exists = True
        except:
            try:
                where_value = interface_warning_data.get(where, str())
                if str(where) in interface_warning_data.keys(): key_exists = True
            except: pass

    else:
        try:
            where_value = eval('interface_data%s' % (str(where)))
            key_exists = True
        except:
            try:
                where_value = interface_data.get(where, str())
                if str(where) in interface_data.keys(): key_exists = True
            except: pass

    #CGI_CLI.uprint('CHECK[%s, key_exists=%s ,where_value=%s, what_yes_in=%s, what_not_in=%s, exact_value_yes=%s, lower_than=%s, higher_than=%s, warning=%s, key_exists=%s, ignore_data_existence=%s]' \
    #    % (where, key_exists, where_value, what_yes_in, what_not_in, exact_value_yes, lower_than, higher_than, warning, str(key_exists), str(ignore_data_existence)),\
    #    tag = 'debug', no_printall = not CGI_CLI.printall, timestamp = 'no')

    if key_exists: pass
    else:
        if ignore_data_existence: pass
        else: CGI_CLI.logtofile("DATA '%s' DOES NOT EXISTS.\n" % (where), ommit_timestamp = True)
        return None

    ### FLOAT ZERO WORKARROUND ###
    if str(lower_than) and str(lower_than) != 'None':
        try:
            if float(where_value) < float(lower_than):
                CGI_CLI.logtofile("CHECK['%s'(%s) < '%.2f'] = OK\n" % (where, str(where_value), float(lower_than)), ommit_timestamp = True)
            else:
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) < '%.2f'] = WARNING" % (where, str(where_value), float(lower_than)), color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) < '%.2f'] = NOT OK" % (where, str(where_value), float(lower_than)), color = 'red', timestamp = 'no')
        except: CGI_CLI.logtofile("CHECK['%s'(%s) < '%s'] = NaN\n" % (where, str(where_value), str(lower_than)), ommit_timestamp = True)

    ### FLOAT ZERO WORKARROUND ###
    if str(higher_than) and str(higher_than) != 'None':
        try:
            if float(where_value) > float(higher_than):
                CGI_CLI.logtofile("CHECK['%s'(%s) > '%.2f'] = OK\n" % (where, str(where_value), float(higher_than)), ommit_timestamp = True)
            else:
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) > '%.2f'] = WARNING" % (where, str(where_value), float(higher_than)), color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) > '%.2f'] = NOT OK" % (where, str(where_value), float(higher_than)), color = 'red', timestamp = 'no')
        except: CGI_CLI.logtofile("CHECK['%s'(%s) > '%s'] = NaN\n" % (where, str(where_value), str(higher_than)), ommit_timestamp = True)

    ### FLOAT ZERO WORKARROUND ###
    if str(equals_to) and str(equals_to) != 'None':
        try:
            if float(where_value) > float(equals_to):
                CGI_CLI.logtofile("CHECK['%s'(%s) == '%.2f'] = OK\n" % (where, str(where_value), float(equals_to)), ommit_timestamp = True)
            else:
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) == '%.2f'] = WARNING" % (where, str(where_value), float(equals_to)), color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s'(%s) == '%.2f'] = NOT OK" % (where, str(where_value), float(equals_to)), color = 'red', timestamp = 'no')
        except: CGI_CLI.logtofile("CHECK['%s'(%s) == '%s'] = NaN\n" % (where, str(where_value), str(equals_to)), ommit_timestamp = True)

    if exact_value_yes:
        if str(exact_value_yes).upper() == str(where_value).upper():
            CGI_CLI.logtofile("CHECK['%s' == '%s'(%s)] = OK\n" % (exact_value_yes, where, str(where_value)), ommit_timestamp = True)
        else:
            if warning:
                check_warning_interface_result_ok = False
                CGI_CLI.uprint("CHECK['%s' == '%s'(%s)] = WARNING" % (exact_value_yes, where, str(where_value)),
                    color = 'orange', timestamp = 'no')
            else:
                check_interface_result_ok = False
                CGI_CLI.uprint("CHECK['%s' == '%s'(%s)] = NOT OK" % (exact_value_yes, where, str(where_value)),
                    color = 'red', timestamp = 'no')

    if what_yes_in:
        if isinstance(where, (list,tuple)):
            if what_yes_in in where_value:
                CGI_CLI.logtofile("CHECK['%s' in '%s'(%s)] = OK\n" % (what_yes_in, where, str(where_value)), ommit_timestamp = True)
            else:
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' in '%s'(%s)] = WARNING" % (what_yes_in, where, str(where_value)),
                        color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' in '%s'(%s)] = NOT OK" % (what_yes_in, where, str(where_value)),
                        color = 'red', timestamp = 'no')
        else:
            if str(what_yes_in).upper() in str(where_value).upper():
                CGI_CLI.logtofile("CHECK['%s' in '%s'(%s)] = OK\n" % (what_yes_in, where, str(where_value)), ommit_timestamp = True)
            else:
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' in '%s'(%s)] = WARNING" % (what_yes_in, where, str(where_value)),
                        color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' in '%s'(%s)] = NOT OK" % (what_yes_in, where, str(where_value)),
                        color = 'red', timestamp = 'no')

    if what_not_in:
        if isinstance(what_not_in, (list,tuple)):
            for item in what_not_in:
                if item.upper() in where_value.upper():
                    local_check_interface_result_ok += 1
                    Alarm_text.append("'%s' not in '%s'(%s)" % (item, where, str(where_value)))
            ### ALL FAIL LOGIC ###
            if local_check_interface_result_ok == len(what_not_in):
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK[" + ' AND '.join(Alarm_text) + '] = WARNING', color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK[" + ' AND '.join(Alarm_text) + '] = NOT OK', color = 'red', timestamp = 'no')
            else: CGI_CLI.logtofile("CHECK[ ['%s'] not in '%s'] = OK\n" % (','.join(what_not_in), where), ommit_timestamp = True)
        else:
            if str(what_not_in).upper() in str(where_value).upper():
                if warning:
                    check_warning_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' not in '%s'(%s)] = WARNING" % (str(what_not_in), where, str(where_value)),
                        color = 'orange', timestamp = 'no')
                else:
                    check_interface_result_ok = False
                    CGI_CLI.uprint("CHECK['%s' not in '%s'(%s)] = NOT OK" % (str(what_not_in), where, str(where_value)),
                        color = 'red', timestamp = 'no')
            else: CGI_CLI.logtofile("CHECK['%s' not in '%s'(%s)] = OK\n" % (str(what_not_in), where, str(where_value)), ommit_timestamp = True)

###############################################################################

def do_ping(address = None, mtu = None, count = None, ipv6 = None, source = None):
    """
    ipv6 is flag True/False
    count is number of pings
    mtu is mtu size
    source is ip source address
    returns 0..100% ping success
    """
    percent_success = 0
    ping_counts = str(count) if count else '4'
    mtu_size = mtu if mtu else 100
    if address:
        # ping4_config_rcmds = {
            # 'cisco_ios':[
                # 'ping %s%s size %s %scount %s' % \
                    # ('ipv6 ' if ipv6 else str(), address, str(mtu), \
                    # 'df-bit ' if not ipv6 else str(), ping_counts)
            # ],
            # 'cisco_xr':[
                # 'ping %s%s size %s %scount %s' % \
                    # ('ipv6 ' if ipv6 else str(), address, str(mtu), \
                    # 'df-bit ' if not ipv6 else str(), ping_counts)
            # ],
            # 'juniper': [
                # 'ping %s%s rapid count %s size %s' % \
                    # ('inet6 ' if ipv6 else str(), address, ping_counts, str(mtu))
            # ],
            # 'huawei': [
                # 'ping %s-s %s -c %s %s' % \
                    # ('ipv6 ' if ipv6 else str(),str(mtu), ping_counts, address)
            # ]
        # }

        ping4_config_rcmds = {
            'cisco_ios':[
                'ping %s%s size %s %scount %s%s' % \
                    ('ipv6 ' if ipv6 else str(), address, str(mtu_size), \
                    'df-bit ' if not ipv6 else str(), ping_counts,
                    ' source %s' % (str(source)) if source else str())
            ],
            'cisco_xr':[
                'ping %s%s size %s %scount %s%s' % \
                    ('ipv6 ' if ipv6 else str(), address, str(mtu_size), \
                    'df-bit ' if not ipv6 else str(), ping_counts,
                    ' source %s' % (str(source)) if source else str())
            ],
            'juniper': [
                'ping %s%s rapid count %s size %s%s' % \
                    ('inet6 ' if ipv6 else str(), address, ping_counts, str(mtu_size),
                    ' source %s' % (str(source)) if source else str())
            ],
            'huawei': [
                'ping %s%s-s %s -c %s %s' % \
                    ('ipv6 ' if ipv6 else str(), \
                    '-a %s ' % (str(source)) if source else str(), \
                    str(mtu_size), ping_counts, address)
            ]
        }

        ping4_config_rcmds_outputs = RCMD.run_commands(ping4_config_rcmds, \
            autoconfirm_mode = True, \
            long_lasting_mode = True, \
            printall = CGI_CLI.printall, ignore_syntax_error = True)

        if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
            try: percent_success = float(ping4_config_rcmds_outputs[0].\
                     split('Success rate is ')[1].splitlines()[0].split('percent')[0].strip())
            except: pass

        elif RCMD.router_type == 'juniper':
            try: percent_success = 100 - float(ping4_config_rcmds_outputs[0].\
                     split('received,')[1].splitlines()[0].split('%')[0].strip())
            except: pass

        elif RCMD.router_type == 'huawei':
            try: percent_success = 100 - float(ping4_config_rcmds_outputs[0].\
                     split('% packet loss')[0].splitlines()[-1].strip())
            except: pass
    return percent_success

###############################################################################

def find_max_pingsize(address = None, ipv6 = None, max_mtu = None, source = None):
    """
    ipv6 is flag True/False
    count is number of pings
    """
    max_mtu_size = 65536
    try:
        if max_mtu: max_mtu_size = int(max_mtu)
    except: pass
    mtu, diff_mtu = max_mtu_size, max_mtu_size
    looping, max_success_mtu = 0, 0

    while looping < 18:
        looping += 1
        diff_mtu = int(diff_mtu/2)
        if diff_mtu == 0: diff_mtu = 1

        CGI_CLI.uprint('ipv6 = %s, diff_pingsize = %s, pingsize = %s' % \
            (str(ipv6),str(diff_mtu),  str(mtu)), \
            no_printall = not printall, tag = 'debug')

        if do_ping(address = address, mtu = mtu, count = 3, ipv6 = ipv6, source = source) > 0:
            if max_success_mtu and mtu > max_success_mtu or max_success_mtu == 0:
                max_success_mtu = mtu
            elif max_success_mtu and mtu <= max_success_mtu:
                looping = False
                break
            mtu = int(mtu + diff_mtu)
        else: mtu = int(mtu - diff_mtu)
        if mtu <= 0:
            looping = False
            break
    return max_success_mtu

###############################################################################

def interface_traffic_errors_check(undotted_interface_id = None, after_ping = None):
    global interface_warning_data
    global interface_data

    after_string = '_After_ping' if after_ping else str()
    err_check_after_pings_data_rcmds = {
        'cisco_ios':[
            'show interfaces %s' % (undotted_interface_id),
        ],

        'cisco_xr':[
            'show interfaces %s' % (undotted_interface_id),
        ],

        'juniper': [
            'show interfaces %s extensive' % (undotted_interface_id),
            'show interfaces %s detail | match MTU' % (undotted_interface_id),
        ],

        'huawei': [
            'display interface %s' % (undotted_interface_id),
        ]
    }

    err_check_after_pings_outputs = RCMD.run_commands( \
        err_check_after_pings_data_rcmds, \
        autoconfirm_mode = True, \
        printall = CGI_CLI.printall)

    if not after_ping:
        try:    interface_data['interface_data']['ASN'] = err_check_after_pings_outputs[0].split('Description:')[1].splitlines()[0].split(' ASN')[1].split()[0].strip()
        except: pass

    if not after_ping:
        interface_data['interface_data']['bundle_members'] = []

    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
        try: interface_data['interface_data']['is'] = err_check_after_pings_outputs[0].split(', line protocol is ')[0].split(' is ')[1].strip()
        except: interface_data['interface_data']['is'] = str()

        try: interface_data['interface_data']['line protocol is'] = err_check_after_pings_outputs[0].split('line protocol is ')[1].split()[0]
        except: interface_data['interface_data']['line protocol is'] = str()

        if not after_ping:
            try:    interface_data['interface_data']['bundle_members_nr'] = int(err_check_after_pings_outputs[0].split('No. of members in this bundle:')[1].splitlines()[0].strip())
            except: pass

            inactive_bundle_members = str()
            for number in range(interface_data['interface_data'].get('bundle_members_nr',0)):
                try:    interface_line = err_check_after_pings_outputs[0].split('No. of members in this bundle:')[1].splitlines()[number + 1].strip()
                except: interface_line = str()
                if interface_line:
                    interface_data['interface_data']['bundle_members'].append(copy.deepcopy(interface_line.split()[0]))
                if 'Active' in interface_line: pass
                else: inactive_bundle_members += interface_line.split()[0] + ' '
            if inactive_bundle_members:
                interface_data['interface_data']['inactive_bundle_members'] = inactive_bundle_members

            try: interface_warning_data['interface_data']['IPV4 MTU set'] = err_check_after_pings_outputs[0].upper().split('MTU ')[1].split()[0]
            except: pass

            try: interface_warning_data['interface_data']['IPV6 MTU set'] = err_check_after_pings_outputs[0].upper().split('MTU ')[1].split()[0]
            except: pass

        try:    interface_warning_data['interface_statistics']['input_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('input errors')[0].splitlines()[-1].split()[0].strip()
        except: interface_warning_data['interface_statistics']['input_errors%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['input_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['input_errors_After_ping']) - int(interface_warning_data['interface_statistics']['input_errors']))
            except: interface_warning_data['interface_statistics']['input_errors_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['input_CRC%s' % (after_string)] = err_check_after_pings_outputs[0].split('input errors,')[1].split('CRC,')[0].strip()
        except: interface_warning_data['interface_statistics']['input_CRC%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['input_CRC_Difference'] = str(int(interface_warning_data['interface_statistics']['input_CRC_After_ping']) - int(interface_warning_data['interface_statistics']['input_CRC']))
            except: interface_warning_data['interface_statistics']['input_CRC_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['output_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('output errors')[0].splitlines()[-1].split()[0].strip()
        except: interface_warning_data['interface_statistics']['output_errors%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['output_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['output_errors_After_ping']) - int(interface_warning_data['interface_statistics']['output_errors']))
            except: interface_warning_data['interface_statistics']['output_errors_Difference'] = str()

        ### TRAFFIC ###
        if not precheck_mode and not after_ping and not PING_ONLY:
            try: interface_warning_data['interface_statistics']['txload'] = err_check_after_pings_outputs[0].split('txload')[1].split()[0].replace(',','').strip()
            except: interface_warning_data['interface_statistics']['txload'] = str()
            try: interface_warning_data['interface_statistics']['rxload'] = err_check_after_pings_outputs[0].split('rxload')[1].split()[0].replace(',','').strip()
            except: interface_warning_data['interface_statistics']['rxload'] = str()
            if interface_warning_data['interface_statistics'].get('txload'):
                try: interface_warning_data['interface_statistics']['txload_percent'] = 100 * float(interface_warning_data['interface_statistics'].get('txload').split('/')[0]) / float(interface_warning_data['interface_statistics'].get('txload').split('/')[1])
                except: pass
            if interface_warning_data['interface_statistics'].get('rxload'):
                try: interface_warning_data['interface_statistics']['rxload_percent'] = 100 * float(interface_warning_data['interface_statistics'].get('rxload').split('/')[0]) / float(interface_warning_data['interface_statistics'].get('rxload').split('/')[1])
                except: pass


    elif RCMD.router_type == 'juniper':
        try: interface_data['interface_data']['Physical interface state'] = err_check_after_pings_outputs[0].split(', Physical link is')[0].split(',')[-1].strip()
        except: interface_data['interface_data']['Physical interface state'] = str()

        try: interface_data['interface_data']['Physical link is'] = err_check_after_pings_outputs[0].split('Physical link is ')[1].split()[0]
        except: interface_data['interface_data']['Physical link is'] = str()

        if not after_ping:
            try:    interface_data['interface_data']['bundle_members_nr'] = int(err_check_after_pings_outputs[0].split('Aggregate member links:')[1].splitlines()[0].strip())
            except: pass

            inactive_bundle_members = str()
            for number in range(interface_data['interface_data'].get('bundle_members_nr',0)):
                try:    interface_line = err_check_after_pings_outputs[0].split('Interfaces:')[1].strip().splitlines()[number].strip()
                except: interface_line = str()
                if interface_line:
                    interface_data['interface_data']['bundle_members'].append(copy.deepcopy(interface_line.split()[0]))
                if 'Up' in interface_line: pass
                else: inactive_bundle_members += interface_line.split()[0] + ' '
            if inactive_bundle_members:
                interface_data['interface_data']['inactive_bundle_members'] = inactive_bundle_members

            try: interface_warning_data['interface_data']['IPV4 MTU set'] = err_check_after_pings_outputs[1].split('Protocol inet, MTU:')[1].split()[0]
            except: pass

            try: interface_warning_data['interface_data']['IPV6 MTU set'] = err_check_after_pings_outputs[1].split('Protocol inet6, MTU:')[1].split()[0]
            except: pass

        try:
            active_alarms = err_check_after_pings_outputs[0].split('Active alarms  : ')[1].split()[0].strip()
            if active_alarms:
                interface_warning_data['interface_statistics']['Active_alarms%s' % (after_string)] = active_alarms
        except: pass

        try:
            active_defects = err_check_after_pings_outputs[0].split('Active defects : ')[1].split()[0].strip()
            if active_defects:
                interface_warning_data['interface_statistics']['Active_defects%s' % (after_string)] = active_defects
        except: pass

        try:    interface_warning_data['interface_statistics']['Bit_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('Bit errors ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Bit_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['Bit_errors_After_ping']) - int(interface_warning_data['interface_statistics']['Bit_errors']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Errored_blocks%s' % (after_string)] = err_check_after_pings_outputs[0].split('Errored blocks ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Errored_blocks_Difference'] = str(int(interface_warning_data['interface_statistics']['Errored_blocks_After_ping']) - int(interface_warning_data['interface_statistics']['Errored_blocks']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Ethernet_FEC_statistics%s' % (after_string)] = err_check_after_pings_outputs[0].split('Ethernet FEC statistics ')[1].split()[0].strip()
        except: pass

        try:    interface_warning_data['interface_statistics']['FEC_Corrected_Errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('FEC Corrected Errors ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['FEC_Corrected_Errors_Difference'] = str(int(interface_warning_data['interface_statistics']['FEC_Corrected_Errors_After_ping']) - int(interface_warning_data['interface_statistics']['FEC_Corrected_Errors']))
            except: pass

        try:    interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('FEC Uncorrected Errors ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_Difference'] = str(int(interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_After_ping']) - int(interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors']))
            except: pass

        try:    interface_warning_data['interface_statistics']['FEC_Corrected_Errors_Rate%s' % (after_string)] = err_check_after_pings_outputs[0].split('FEC Corrected Errors Rate ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['FEC_Corrected_Errors_Rate_Difference'] = str(int(interface_warning_data['interface_statistics']['FEC_Corrected_Errors_Rate_After_ping']) - int(interface_warning_data['interface_statistics']['FEC_Corrected_Errors_Rate']))
            except: pass

        try:    interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_Rate%s' % (after_string)] = err_check_after_pings_outputs[0].split('FEC Uncorrected Errors Rate ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_Rate_Difference'] = str(int(interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_Rate_After_ping']) - int(interface_warning_data['interface_statistics']['FEC_Uncorrected_Errors_Rate']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Input_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('Input errors:')[1].strip().split('Output errors:')[0].strip().split('Errors: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Input_errors%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Input_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['Input_errors_After_ping']) - int(interface_warning_data['interface_statistics']['Input_errors']))
            except: interface_warning_data['interface_statistics']['Input_errors_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Input_errors__Drops%s' % (after_string)] = err_check_after_pings_outputs[0].split('Input errors:')[1].strip().split('Output errors:')[0].strip().split('Drops: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Input_errors__Drops%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Input_errors__Drops_Difference'] = str(int(interface_warning_data['interface_statistics']['Input_errors__Drops_After_ping']) - int(interface_warning_data['interface_statistics']['Input_errors__Drops']))
            except: interface_warning_data['interface_statistics']['Input_errors__Drops_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Input_errors__Framing_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('Input errors:')[1].strip().split('Output errors:')[0].strip().split('Framing errors: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Input_errors__Framing_errors%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Input_errors__Framing_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['Input_errors__Framing_errors_After_ping']) - int(interface_warning_data['interface_statistics']['Input_errors__Framing_errors']))
            except: interface_warning_data['interface_statistics']['Input_errors__Framing_errors_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Input_errors__Runts%s' % (after_string)] = err_check_after_pings_outputs[0].split('Input errors:')[1].strip().split('Output errors:')[0].strip().split('Runts: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Input_errors__Runts%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Input_errors__Runts_Difference'] = str(int(interface_warning_data['interface_statistics']['Input_errors__Runts_After_ping']) - int(interface_warning_data['interface_statistics']['Input_errors__Runts']))
            except: interface_warning_data['interface_statistics']['Input_errors__Runts_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Input_errors__Policed_discards%s' % (after_string)] = err_check_after_pings_outputs[0].split('Input errors:')[1].strip().split('Output errors:')[0].strip().split('Policed discards: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Input_errors__Policed_discards%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Input_errors__Policed_discards_Difference'] = str(int(interface_warning_data['interface_statistics']['Input_errors__Policed_discards_After_ping']) - int(interface_warning_data['interface_statistics']['Input_errors__Policed_discards']))
            except: interface_warning_data['interface_statistics']['Input_errors__Policed_discards_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Output_errors%s' % (after_string)] = err_check_after_pings_outputs[0].split('Output errors:')[1].strip().split('Active alarms')[0].strip().split('Errors: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Output_errors%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Output_errors_Difference'] = str(int(interface_warning_data['interface_statistics']['Output_errors_After_ping']) - int(interface_warning_data['interface_statistics']['Output_errors']))
            except: interface_warning_data['interface_statistics']['Output_errors_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions%s' % (after_string)] = err_check_after_pings_outputs[0].split('Output errors:')[1].strip().split('Active alarms')[0].strip().split('Carrier transitions: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions_Difference'] = str(int(interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions_After_ping']) - int(interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions']))
            except: interface_warning_data['interface_statistics']['Output_errors__Carrier_transitions_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Output_errors__Drops%s' % (after_string)] = err_check_after_pings_outputs[0].split('Output errors:')[1].strip().split('Active alarms')[0].strip().split('Drops: ')[1].split()[0].replace(',','')
        except: interface_warning_data['interface_statistics']['Output_errors__Drops%s' % (after_string)] = str()
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Output_errors__Drops_Difference'] = str(int(interface_warning_data['interface_statistics']['Output_errors__Drops_After_ping']) - int(interface_warning_data['interface_statistics']['Output_errors__Drops']))
            except: interface_warning_data['interface_statistics']['Output_errors__Drops_Difference'] = str()

        try:    interface_warning_data['interface_statistics']['Output_errors__Collisions%s' % (after_string)] = err_check_after_pings_outputs[0].split('Output errors:')[1].strip().split('Active alarms')[0].strip().split('Collisions: ')[1].split()[0].replace(',','')
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Output_errors__Collisions_Difference'] = str(int(interface_warning_data['interface_statistics']['Output_errors__Collisions_After_ping']) - int(interface_warning_data['interface_statistics']['Output_errors__Collisions']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Output_errors__Aged_packets%s' % (after_string)] = err_check_after_pings_outputs[0].split('Output errors:')[1].strip().split('Active alarms')[0].strip().split('Aged packets: ')[1].split()[0].replace(',','')
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Output_errors__Aged_packets_Difference'] = str(int(interface_warning_data['interface_statistics']['Output_errors__Aged_packets_After_ping']) - int(interface_warning_data['interface_statistics']['Output_errors__Aged_packets']))
            except: pass

        ### TRAFFIC ###
        if not precheck_mode and not after_ping and not PING_ONLY:
            try: interface_warning_data['interface_statistics']['txload'] = err_check_after_pings_outputs[0].split('Output rate    :')[1].split()[0].replace(',','').strip()
            except: interface_warning_data['interface_statistics']['txload'] = str()
            try: interface_warning_data['interface_statistics']['rxload'] = err_check_after_pings_outputs[0].split('Input rate     :')[1].split()[0].replace(',','').strip()
            except: interface_warning_data['interface_statistics']['rxload'] = str()

            # """Traffic statistics:
            #Input  bytes  :     5256259942920724           8772959240 bps
            #Output bytes  :     1519104622857050           3748473568 bps"""

            if not interface_warning_data['interface_statistics'].get('txload'):
                try: interface_warning_data['interface_statistics']['txload'] = err_check_after_pings_outputs[0].split('Output bytes  :')[1].split()[1].strip()
                except: pass

            if not interface_warning_data['interface_statistics'].get('rxload'):
                try: interface_warning_data['interface_statistics']['rxload'] = err_check_after_pings_outputs[0].split('Input  bytes  :')[1].split()[1].strip()
                except: pass


            try: interface_warning_data['interface_statistics']['Speed'] = err_check_after_pings_outputs[0].split('Speed:')[1].split()[0].replace(',','').strip()
            except: interface_warning_data['interface_statistics']['Speed'] = str()

            multiplikator = 1
            if interface_warning_data['interface_statistics'].get('Speed') and 'Gbps' in interface_warning_data['interface_statistics'].get('Speed'): multiplikator = 1073741824
            if interface_warning_data['interface_statistics'].get('Speed') and 'Mbps' in interface_warning_data['interface_statistics'].get('Speed'): multiplikator = 1048576
            if interface_warning_data['interface_statistics'].get('txload'):
                try: interface_warning_data['interface_statistics']['txload_percent'] = 100 * float(interface_warning_data['interface_statistics'].get('txload')) / (float(interface_warning_data['interface_statistics'].get('Speed').replace('Gbps','').replace('Mbps','')) * multiplikator)
                except: pass
            if interface_warning_data['interface_statistics'].get('rxload'):
                try: interface_warning_data['interface_statistics']['rxload_percent'] = 100 * float(interface_warning_data['interface_statistics'].get('rxload')) / (float(interface_warning_data['interface_statistics'].get('Speed').replace('Gbps','').replace('Mbps','')) * multiplikator)
                except: pass


    elif RCMD.router_type == 'huawei':
        try: interface_data['interface_data']['current state'] = err_check_after_pings_outputs[0].split('current state : ')[1].splitlines()[0].split('(')[0].strip()
        except: pass

        try: interface_data['interface_data']['Line protocol current state'] = err_check_after_pings_outputs[0].split('Line protocol current state : ')[1].splitlines()[0].strip()
        except: pass

        if not after_ping:
            try:    interface_lines = err_check_after_pings_outputs[0].split('PortName ')[1].splitlines()[2:]
            except: interface_lines = []

            inactive_bundle_members = str()
            bundle_members_nr = 0
            for interface_line in interface_lines:
                if '-----' in interface_line: break
                bundle_members_nr += 1
                if interface_line:
                    interface_data['interface_data']['bundle_members'].append(copy.deepcopy(interface_line.split()[0]))
                if 'UP' in interface_line: pass
                else: inactive_bundle_members += interface_line.split()[0] + ' '
            if inactive_bundle_members:
                interface_data['interface_data']['inactive_bundle_members'] = inactive_bundle_members

            if bundle_members_nr > 0: interface_data['interface_data']['bundle_members_nr'] = bundle_members_nr

            try: interface_warning_data['interface_data']['IPV4 MTU set'] = err_check_after_pings_outputs[0].split('The Maximum Transmit Unit is ')[1].split()[0].replace(',','')
            except: pass

            try: interface_warning_data['interface_data']['IPV6 MTU set'] = err_check_after_pings_outputs[0].split('The Maximum Transmit Unit is ')[1].split()[0].replace(',','')
            except: pass

        try:    interface_warning_data['interface_statistics']['Rx_Power_dBm%s' % (after_string)] = err_check_after_pings_outputs[0].split('Rx Power: ')[1].split()[0].strip().replace(',','').replace('dBm','')
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Rx_Power_dBm_Difference'] = str(float(interface_warning_data['interface_statistics']['Rx_Power_dBm_After_ping']) - float(interface_warning_data['interface_statistics']['Rx_Power_dBm']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Tx_Power_dBm%s' % (after_string)] = err_check_after_pings_outputs[0].split('Tx Power: ')[1].split()[0].strip().replace(',','').replace('dBm','')
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Tx_Power_dBm_Difference'] = str(float(interface_warning_data['interface_statistics']['Tx_Power_dBm_After_ping']) - float(interface_warning_data['interface_statistics']['Tx_Power_dBm']))
            except: pass

        try:    interface_warning_data['interface_statistics']['CRC%s' % (after_string)] = err_check_after_pings_outputs[0].split('CRC: ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['CRC_Difference'] = str(int(interface_warning_data['CRC_After_ping']) - int(interface_warning_data['CRC']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Overrun%s' % (after_string)] = err_check_after_pings_outputs[0].split('Overrun: ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Overrun_Difference'] = str(int(interface_warning_data['interface_statistics']['Overrun_After_ping']) - int(interface_warning_data['interface_statistics']['Overrun']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Lost%s' % (after_string)] = err_check_after_pings_outputs[0].split('Lost: ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Lost_Difference'] = str(int(interface_warning_data['Lost_After_ping']) - int(interface_warning_data['Lost']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Overflow%s' % (after_string)] = err_check_after_pings_outputs[0].split('Overflow: ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Overflow_Difference'] = str(int(interface_warning_data['interface_statistics']['Overflow_After_ping']) - int(interface_warning_data['interface_statistics']['Overflow']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Underrun%s' % (after_string)] = err_check_after_pings_outputs[0].split('Underrun: ')[1].split()[0].strip()
        except: pass
        if after_ping:
            try:    interface_warning_data['interface_statistics']['Underrun_Difference'] = str(int(interface_warning_data['interface_statistics']['Underrun_After_ping']) - int(interface_warning_data['interface_statistics']['Underrun']))
            except: pass

        try:    interface_warning_data['interface_statistics']['Local_fault%s' % (after_string)] = err_check_after_pings_outputs[0].split('Local fault: ')[1].split()[0].strip().replace('.','')
        except: pass

        try:    interface_warning_data['interface_statistics']['Remote_fault%s' % (after_string)] = err_check_after_pings_outputs[0].split('Remote fault: ')[1].split()[0].strip().replace('.','')
        except: pass

        if CUSTOMER_MODE and not after_ping:
            try:    interface_data['interface_data']['Line protocol current state'] = err_check_after_pings_outputs[0].split('Line protocol current state :')[1].split()[0]
            except: pass

            try:    interface_data['interface_data']['Link quality grade'] = err_check_after_pings_outputs[0].split('Link quality grade :')[1].split()[0]
            except: pass

            #try:    interface_data['interface_data']['The Maximum Transmit Unit'] = err_check_after_pings_outputs[0].split('The Maximum Transmit Unit is')[1].split()[0].replace(',','')
            #except: pass

            #try:    interface_data['interface_data']['Internet Address'] = err_check_after_pings_outputs[0].split('Internet Address is')[1].split()[0]
            #except: pass

            try:    interface_data['interface_data']['Port BW'] = err_check_after_pings_outputs[0].split('Port BW:')[1].split()[0].replace(',','')
            except: pass

        ### TRAFFIC ###
        if not precheck_mode and not after_ping and not PING_ONLY:
            try: interface_warning_data['interface_statistics']['txload_percent'] = float(err_check_after_pings_outputs[0].split('output utility rate:')[1].split()[0].replace('%','').strip())
            except: pass
            try: interface_warning_data['interface_statistics']['rxload_percent'] = float(err_check_after_pings_outputs[0].split('input utility rate:')[1].split()[0].replace('%','').strip())
            except: pass

    ### IF NOT BUNDLE DELETE DATA RECORD ######################################
    if not after_ping and len(interface_data['interface_data'].get('bundle_members',[])) == 0:
        try:
            del interface_data['interface_data']['bundle_members']
        except: pass

        optic_data_rcmds = {
            'cisco_ios':[],
            'cisco_xr': [],
            'juniper': [],
            'huawei': []
        }

        optic_data_rcmds['cisco_ios'].append('sh controllers %s' % (str(undotted_interface_id)))
        optic_data_rcmds['cisco_ios'].append('sh controllers %s phy' % (str(undotted_interface_id)))
        optic_data_rcmds['cisco_xr'].append('sh controllers %s' % (str(undotted_interface_id)))
        optic_data_rcmds['cisco_xr'].append('sh controllers %s phy' % (str(undotted_interface_id)))
        optic_data_rcmds['juniper'].append('show interfaces diagnostics optics %s' % (str(undotted_interface_id)))

        optic_data_outputs = RCMD.run_commands( \
            optic_data_rcmds, \
            autoconfirm_mode = True, \
            printall = CGI_CLI.printall)

        if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
            interface_data['interface_statistics']['Tx_Power_Lanes_dBm'] = collections.OrderedDict()
            interface_data['interface_statistics']['Rx_Power_Lanes_dBm'] = collections.OrderedDict()

            ### ZERO LANES INTERFACES #########################################
            i = 0

            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_high'] = optic_data_rcmds[0].split('Transmit Power (dBm):')[1].splitlines()[0].split()[1]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_low'] = optic_data_rcmds[0].split('Transmit Power (dBm):')[1].splitlines()[0].split()[2]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_high'] = optic_data_rcmds[0].split('Transmit Power (dBm):')[1].splitlines()[0].split()[0]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_low'] = optic_data_rcmds[0].split('Transmit Power (dBm):')[1].splitlines()[0].split()[3]
            except: pass


            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_high'] = optic_data_rcmds[0].split('Receive Power (dBm):')[1].splitlines()[0].split()[1]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_low'] = optic_data_rcmds[0].split('Receive Power (dBm):')[1].splitlines()[0].split()[2]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_high'] = optic_data_rcmds[0].split('Receive Power (dBm):')[1].splitlines()[0].split()[0]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_low'] = optic_data_rcmds[0].split('Receive Power (dBm):')[1].splitlines()[0].split()[3]
            except: pass

            try:    interface_data['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(optic_data_rcmds[1].split('Tx Power:')[1].splitlines()[0].split()[2].replace('(',''))
            except: pass
            try:    interface_data['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(optic_data_rcmds[1].split('Rx Power:')[1].splitlines()[0].split()[2].replace('(',''))
            except: pass


            ### MULTILANES INTERFACES #########################################
            i = 0
            try:
                for line in optic_data_rcmds[0].split('Laser Bias')[1].split('Lane ')[1].splitlines()[1:]:
                    if '---' in line: continue
                    if line.strip() == str(): break
                    try:    interface_data['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(line.split()[2])
                    except: pass
                    try:    interface_data['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(line.split()[4])
                    except: pass
                    i += 1
            except: pass

            try:
                for line in optic_data_rcmds[0].split('Thresholds ')[1].splitlines()[1:]:
                    if '---' in line: continue
                    if line.strip() == str(): break
                    if 'Transmit Power (dBm):' in line:
                        try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_high'] = line.split()[4]
                        except: pass
                        try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_low'] = line.split()[5]
                        except: pass
                        try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_high'] = line.split()[3]
                        except: pass
                        try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_low'] = line.split()[6]
                        except: pass

                    elif 'Receive Power (dBm):' in line:
                        try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_high'] = line.split()[4]
                        except: pass
                        try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_low'] = line.split()[5]
                        except: pass
                        try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_high'] = line.split()[3]
                        except: pass
                        try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_low'] = line.split()[6]
                        except: pass
            except: pass

            try:
                if interface_data['interface_statistics']['Tx_Power_Lanes_dBm'].get('Lane %d' % (0)): pass
                else: interface_data['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d' % (0)] = copy.deepcopy(optic_data_rcmds[1].split('Total Tx power:')[1].split()[3])
            except: pass

            try:
                if interface_data['interface_statistics']['Rx_Power_Lanes_dBm'].get('Lane %d' % (0)): pass
                else: interface_data['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d' % (0)] = copy.deepcopy(optic_data_rcmds[1].split('Total Rx power:')[1].split()[3])
            except: pass

        elif RCMD.router_type == 'juniper':
            interface_data['interface_statistics']['Tx_Power_Lanes_dBm'] = collections.OrderedDict()
            interface_data['interface_statistics']['Rx_Power_Lanes_dBm'] = collections.OrderedDict()
            i = 0
            try:
                for part in optic_data_rcmds[0].split('Lane ')[1:]:
                    try:    interface_data['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(part.split('Laser output power')[1].split()[4])
                    except: pass
                    try:    interface_data['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(part.split('Laser receiver power')[1].split()[4])
                    except: pass
                    i += 1
            except: pass

            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_high'] = optic_data_rcmds[0].split('Laser output power high warning threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Warning_low'] = optic_data_rcmds[0].split('Laser output power low warning threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_high'] = optic_data_rcmds[0].split('Laser output power high alarm threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Tx_Power_Lanes_dBm_Alarm_low'] = optic_data_rcmds[0].split('Laser output power low alarm threshold')[1].split()[4]
            except: pass

            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_high'] = optic_data_rcmds[0].split('Laser rx power high alarm threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Warning_low'] = optic_data_rcmds[0].split('Laser rx power low alarm threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_high'] = optic_data_rcmds[0].split('Laser rx power high warning threshold')[1].split()[4]
            except: pass
            try: interface_data['interface_statistics']['Rx_Power_Lanes_dBm_Alarm_low'] = optic_data_rcmds[0].split('Laser rx power low warning threshold')[1].split()[4]
            except: pass


    ### BUNDLE ################################################################
    if not after_ping and len(interface_data['interface_data'].get('bundle_members',[])) > 0:

        interface_data['interface_data']['LAG_interfaces'] = collections.OrderedDict()
        interface_data['interface_statistics']['LAG_interfaces'] = collections.OrderedDict()

        lag_data_rcmds = {
            'cisco_ios':[],
            'cisco_xr': [],
            'juniper': [],
            'huawei': []
        }

        i = 0
        for lag_member in interface_data['interface_data'].get('bundle_members',[]):
            i += 1
            lag_data_rcmds['cisco_ios'].append('show run interface  %s' % (str(lag_member)))
            lag_data_rcmds['cisco_ios'].append('show interface %s' % (str(lag_member)))
            lag_data_rcmds['cisco_ios'].append('sh controllers %s' % (str(lag_member)))
            lag_data_rcmds['cisco_ios'].append('sh controllers %s phy' % (str(lag_member)))
            if i == 1:
                lag_data_rcmds['cisco_ios'].append('show bundle %s' % (str(undotted_interface_id)))

            lag_data_rcmds['cisco_xr'].append('show run interface %s' % (str(lag_member)))
            lag_data_rcmds['cisco_xr'].append('show interface %s' % (str(lag_member)))
            lag_data_rcmds['cisco_xr'].append('sh controllers %s' % (str(lag_member)))
            lag_data_rcmds['cisco_xr'].append('sh controllers %s phy' % (str(lag_member)))
            if i == 1:
                lag_data_rcmds['cisco_xr'].append('show bundle %s' % (str(undotted_interface_id)))

            lag_data_rcmds['juniper'].append('show configuration interfaces %s | display set' % (str(lag_member)))
            lag_data_rcmds['juniper'].append('show interface %s' % (str(lag_member)))
            lag_data_rcmds['juniper'].append('show interfaces diagnostics optics %s' % (str(lag_member)))

            lag_data_rcmds['huawei'].append('display current-configuration interface %s' % (str(lag_member)))
            lag_data_rcmds['huawei'].append('display interface %s' % (str(lag_member)))

            lag_data_outputs = RCMD.run_commands( \
                lag_data_rcmds, \
                autoconfirm_mode = True, \
                printall = CGI_CLI.printall)


            interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))] = collections.OrderedDict()

            if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))] = collections.OrderedDict()
                if i == 1:
                    try:    interface_data['interface_data']['LAG_interfaces']['Local links active'] = copy.deepcopy(lag_data_outputs[3].split('Local links <active/standby/configured>:')[1].split()[0].split('/')[0])
                    except: pass

                    try:    interface_data['interface_data']['LAG_interfaces']['Local links standby'] = copy.deepcopy(lag_data_outputs[3].split('Local links <active/standby/configured>:')[1].split()[0].split('/')[1])
                    except: pass

                    try:    interface_data['interface_data']['LAG_interfaces']['Local links configured'] = copy.deepcopy(lag_data_outputs[3].split('Local links <active/standby/configured>:')[1].split()[0].split('/')[2])
                    except: pass

                    try:    interface_data['interface_data']['LAG_interfaces']['Local bandwidth effective kbps'] = copy.deepcopy(lag_data_outputs[3].split('Local bandwidth <effective/available>:')[1].split()[0])
                    except: pass

                    try:    interface_data['interface_data']['LAG_interfaces']['Local bandwidth available kbps'] = copy.deepcopy(lag_data_outputs[3].split('Local bandwidth <effective/available>:')[1].split()[1].replace('(','').replace(')',''))
                    except: pass

                    try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['B/W kbps'] = copy.deepcopy(lag_data_outputs[3].split('%s' % (str(lag_member)))[1].splitlines()[0].split()[4])
                    except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['bundle id'] = copy.deepcopy(lag_data_outputs[0].split('bundle id')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['mode active'] = True if 'mode active' in lag_data_outputs[0] else str()
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['is'] = copy.deepcopy(lag_data_outputs[1].split(', line protocol is')[0].split()[-1])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['line protocol is'] = copy.deepcopy(lag_data_outputs[1].split('line protocol is')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Internet address is'] = copy.deepcopy(lag_data_outputs[1].split('Internet address is')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['MTU'] = copy.deepcopy(lag_data_outputs[1].split('MTU ')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['BW Kbit'] = copy.deepcopy(lag_data_outputs[1].split(', BW ')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Last link flapped'] = copy.deepcopy(lag_data_outputs[1].split('Last link flapped ')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['input errors'] = copy.deepcopy(lag_data_outputs[1].split('input errors,')[0].split()[-1])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['CRC'] = copy.deepcopy(lag_data_outputs[1].split('CRC,')[0].split()[-1])
                except: pass

                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm'] = collections.OrderedDict()
                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm'] = collections.OrderedDict()

                i = 0
                try:
                    for line in lag_data_outputs[2].split('Laser Bias')[1].split('Lane ')[1].splitlines()[1:]:
                        if '---' in line: continue
                        if line.strip() == str(): break
                        try:    interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(line.split()[2])
                        except: pass
                        try:    interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(line.split()[4])
                        except: pass
                        i += 1
                except: pass

                try:
                    for line in lag_data_outputs[2].split('Thresholds ')[1].splitlines()[1:]:
                        if '---' in line: continue
                        if line.strip() == str(): break
                        if 'Transmit Power (dBm):' in line:
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Warning_high'] = line.split()[4]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Warning_low'] = line.split()[5]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Alarm_high'] = line.split()[3]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Alarm_low'] = line.split()[6]
                            except: pass

                        elif 'Receive Power (dBm):' in line:
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Warning_high'] = line.split()[4]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Warning_low'] = line.split()[5]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Alarm_high'] = line.split()[3]
                            except: pass
                            try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Alarm_low'] = line.split()[6]
                            except: pass
                except: pass

                try:
                    if interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm'].get('Lane %d' % (0)): pass
                    else: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm']['Lane %d' % (0)] = copy.deepcopy(lag_data_outputs[3].split('Total Tx power:')[1].split()[3])
                except: pass

                try:
                    if interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm'].get('Lane %d' % (0)): pass
                    else: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm']['Lane %d' % (0)] = copy.deepcopy(lag_data_outputs[3].split('Total Rx power:')[1].split()[3])
                except: pass

            elif RCMD.router_type == 'juniper':
                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))] = collections.OrderedDict()
                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['gigether-options 802.3ad'] = copy.deepcopy(lag_data_outputs[0].split('gigether-options 802.3ad')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Enabled'] = True if 'Enabled,' in lag_data_outputs[1] else str()
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Physical link is'] = copy.deepcopy(lag_data_outputs[1].split('Physical link is')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['MTU'] = copy.deepcopy(lag_data_outputs[1].split('MTU: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Last flapped'] = copy.deepcopy(lag_data_outputs[1].split('Last flapped   :')[1].splitlines()[0].strip())
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Statistics last cleared'] = copy.deepcopy(lag_data_outputs[1].split('Statistics last cleared:')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Errors'] = copy.deepcopy(lag_data_outputs[1].split('Errors: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Drops'] = copy.deepcopy(lag_data_outputs[1].split('Drops: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Framing errors'] = copy.deepcopy(lag_data_outputs[1].split('Framing errors: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Runts'] = copy.deepcopy(lag_data_outputs[1].split('Runts: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Policed discards'] = copy.deepcopy(lag_data_outputs[1].split('Policed discards: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['L3 incompletes'] = copy.deepcopy(lag_data_outputs[1].split('L3 incompletes: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['L2 channel errors'] = copy.deepcopy(lag_data_outputs[1].split('L2 channel errors: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['L2 mismatch timeouts'] = copy.deepcopy(lag_data_outputs[1].split('L2 mismatch timeouts: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['FIFO errors'] = copy.deepcopy(lag_data_outputs[1].split('FIFO errors: ')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Resource errors'] = copy.deepcopy(lag_data_outputs[1].split('Resource errors: ')[1].split()[0].replace(',',''))
                except: pass

                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm'] = collections.OrderedDict()
                interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm'] = collections.OrderedDict()

                i = 0
                try:
                    for part in lag_data_outputs[2].split('Lane ')[1:]:
                        try:    interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm']['Lane %d' % (i)] = copy.deepcopy(part.split('Laser output power')[1].split()[4])
                        except: pass
                        try:    interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm']['Lane %d' % (i)] =copy.deepcopy(part.split('Laser receiver power')[1].split()[4])
                        except: pass
                        i += 1
                except: pass

                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Warning_high'] = lag_data_outputs[2].split('Laser output power high warning threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Warning_low'] = lag_data_outputs[2].split('Laser output power low warning threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Alarm_high'] = lag_data_outputs[2].split('Laser output power high alarm threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Tx_Power_Lanes_dBm_Alarm_low'] = lag_data_outputs[2].split('Laser output power low alarm threshold')[1].split()[4]
                except: pass

                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Warning_high'] = lag_data_outputs[2].split('Laser rx power high alarm threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Warning_low'] = lag_data_outputs[2].split('Laser rx power low alarm threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Alarm_high'] = lag_data_outputs[2].split('Laser rx power high warning threshold')[1].split()[4]
                except: pass
                try: interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))]['Rx_Power_Lanes_dBm_Alarm_low'] = lag_data_outputs[2].split('Laser rx power low warning threshold')[1].split()[4]
                except: pass


            elif RCMD.router_type == 'huawei':
                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['eth-trunk'] = copy.deepcopy(lag_data_outputs[0].split('eth-trunk')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Line protocol current state'] = copy.deepcopy(lag_data_outputs[1].split('Line protocol current state :')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Link quality grade'] = copy.deepcopy(lag_data_outputs[1].split('Link quality grade :')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Maximum Transmit Unit'] = copy.deepcopy(lag_data_outputs[1].split('Maximum Transmit Unit is ')[1].split()[0])
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Port BW'] = copy.deepcopy(lag_data_outputs[1].split('Port BW:')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['CRC'] = copy.deepcopy(lag_data_outputs[1].split('CRC:')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Lost'] = copy.deepcopy(lag_data_outputs[1].split('Lost:')[1].split()[0].replace(',',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Last 30 seconds input utility rate percentage'] = float(lag_data_outputs[1].split('Last 30 seconds input utility rate:')[1].split()[0].replace('%',''))
                except: pass

                try:    interface_data['interface_data']['LAG_interfaces']['%s' % (str(lag_member))]['Last 30 seconds output utility rate percentage'] = float(lag_data_outputs[1].split('Last 30 seconds output utility rate:')[1].split()[0].replace('%',''))
                except: pass





###############################################################################

def normalized_ipv6(ipv6 = None):
    result_ipv6, doubledot_string = str(), str()
    if ipv6:
        ipv6 = str(ipv6).split('/')[0].replace('0000','0')
        if str(ipv6)[-1] == ':': ipv6 += '0'
        ### ip_number_count minus one because of ::
        ip_number_count = len(str(ipv6).split(':')) - 1
        if len(ipv6.split('::')) == 2:
            before_doubledot, after_doubledot = ipv6.split('::')
            for i in range(8-int(ip_number_count)):
                doubledot_string += ':0'
            result_ipv6 = before_doubledot + doubledot_string + ':' + after_doubledot
        else: result_ipv6 = str(ipv6)
    return result_ipv6

###############################################################################



###############################################################################
#
# def BEGIN MAIN
#
###############################################################################

if __name__ != "__main__": sys.exit(0)
try:
    CSS_STYLE = """
debug {
  background-color: lightgray;
}

warning {
  color: red;
  background-color: yellow;
}

pre {
  color: gray;
}

authentication {
  color: #cc0000;
  font-size: x-large;
  font-weight: bold;
}
"""
    ### GLOBAL VARIABLES AND SETTINGS #########################################
    logging.raiseExceptions = False
    goto_webpage_end_by_javascript = str()
    traceback_found = None
    device_list = []
    logfilename = None
    mtu_size = 0
    LDP_neighbor_IP = str()
    device_interface_list = []
    interface_cgi_string = 'interface__'
    interface_line_list = []
    logfilename_list = []
    global_logfilename = str()
    swan_id = str()
    precheck_mode = True
    global_logfilename = str()
    test_mode = None
    table_test_extension = str()
    ping_counts = '0'
    OTI_LOCAL_AS = '5511'
    IMN_LOCAL_AS = '2300'
    LOCAL_AS_NUMBER = str()
    chunked_mode = None
    IMN_INTERFACE = False
    CUSTOMER_MODE = False
    BB_MODE = False
    USE_IPV6 = False


    ### GCI_CLI INIT ##########################################################
    PING_ONLY = True if 'ping_only' in CGI_CLI.get_scriptname() else False
    action_type = 'ping_only' if 'ping_only' in CGI_CLI.get_scriptname() else 'bbactivation'

    if PING_ONLY:
        ping_counts = '1000'
        chunked_mode = True

    USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = chunked_mode, css_style = CSS_STYLE)
    LCMD.init()

    #CGI_CLI.printall = True
    #CGI_CLI.timestamp = True
    #printall = True

    CGI_CLI.timestamp = CGI_CLI.data.get("timestamps")
    printall = CGI_CLI.data.get("printall")

    ping_counts = CGI_CLI.data.get("ping_counts",str(ping_counts))

    if CGI_CLI.data.get("test-version",str()) == 'test-mode' \
        or CGI_CLI.data.get("test-version",str()) == 'test mode':
            test_mode = True
            table_test_extension = '_test'

    if '_test' in CGI_CLI.get_scriptname():
        test_mode = True
        table_test_extension = '_test'


    ### ACTION TYPE ###########################################################

    action_type_list = ['bbactivation', 'bbmigration', 'custommigration','customactivation','ping_only']

    if not PING_ONLY and CGI_CLI.data.get('customer_interfaces'):
        action_type = 'custommigration'

    if not PING_ONLY and CGI_CLI.data.get("type"):
        if isinstance(CGI_CLI.data.get("type"), (str,basestring,six.string_types)):
            if '[' in CGI_CLI.data.get("type"):
                ### fake_list_is_string ###
                for list_item in action_type_list:
                    if list_item in CGI_CLI.data.get("type"):
                        action_type = list_item

            elif CGI_CLI.data.get("type") in action_type_list:
                action_type = CGI_CLI.data.get("type")

        elif isinstance(CGI_CLI.data.get("type"), (list,tuple)):
            for type_item in CGI_CLI.data.get("type"):
                if type_item in action_type_list:
                    action_type = type_item

    if not PING_ONLY:
        if CGI_CLI.data.get('devicetest'):       action_type = 'bbactivation'
        if CGI_CLI.data.get('devicetestcustom'): action_type = 'customactivation'
        if CGI_CLI.data.get('routertestcustom'): action_type = 'customactivation'

        ### MULTIPLE INPUTS FROM MORE MARTIN'S PAGES ##############################
        swan_id = CGI_CLI.data.get("swan",str())
        if CGI_CLI.data.get("postcheck") \
            or CGI_CLI.data.get("radio",str()) == 'postcheck' \
            or CGI_CLI.data.get('submit-type',str()) == 'submit-with-postcheck' \
            or CGI_CLI.data.get('submit',str()) == 'Run postcheck'\
            or CGI_CLI.data.get('submit',str()) == 'Run+postcheck+on+all+interfaces'\
            or CGI_CLI.data.get('submit',str()) == 'Run postcheck on all interfaces':
                precheck_mode = False
        elif CGI_CLI.data.get("precheck") \
            or CGI_CLI.data.get('submit',str()) == 'Run+precheck+on+all+interfaces' \
            or CGI_CLI.data.get('submit',str()) == 'Run precheck on all interfaces' \
            or CGI_CLI.data.get("radio",str()) == 'precheck' \
            or CGI_CLI.data.get('submit-type',str()) == 'submit-with-precheck' \
            or CGI_CLI.data.get('submit',str()) == 'Run precheck':
                precheck_mode = True


    ### def MAKE DEVICE LIST ##################################################
    CGI_CLI.parse_input_data(key = 'devicetestcustom', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'devicetest', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'device', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'router', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'router2', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'router3', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'routertest', append_to_list = device_list, ignore_list = True)
    CGI_CLI.parse_input_data(key = 'routertestcustom', append_to_list = device_list, ignore_list = True)

    router = CGI_CLI.parse_input_data(key = 'device')
    if not router: router = CGI_CLI.parse_input_data(key = 'routertest')
    if not router: router = CGI_CLI.parse_input_data(key = 'routertestcustom')
    if not router: router = CGI_CLI.parse_input_data(key = 'router')
    router2 = CGI_CLI.parse_input_data(key = 'router2')
    router3 = CGI_CLI.parse_input_data(key = 'router3')

    ### COLLECT INTERFACE LISTS ###############################################
    interface_id_list1, interface_id_list2, interface_id_list3 = [], [], []
    CGI_CLI.parse_input_data(key_in = interface_cgi_string, append_to_list = interface_line_list)

    ### FILTER MY OWN RECEIVED INTERFACE LINE TO INTERFACE_LIST to LIST1 ######
    interface_id_list1 = [ interface_line.split()[0] for interface_line in interface_line_list ]

    #if len(interface_id_list1) == 0:
    CGI_CLI.parse_input_data(key = 'interface', append_to_list = interface_id_list1)

    CGI_CLI.parse_input_data(key = 'interface_id[]', append_to_list = interface_id_list1)
    CGI_CLI.parse_input_data(key = 'interface_id2[]', append_to_list = interface_id_list2)
    CGI_CLI.parse_input_data(key = 'interface_id3[]', append_to_list = interface_id_list3)

    ### def COLLECT DEVICE INTERFACE LIST #####################################
    devices_interfaces_list = []
    if router and len(interface_id_list1) > 0:
        devices_interfaces_list.append([router.upper(), interface_id_list1])
    if router2 and len(interface_id_list2) > 0:
        devices_interfaces_list.append([router2.upper(), interface_id_list2])
    if router3 and len(interface_id_list3) > 0:
        devices_interfaces_list.append([router3.upper(), interface_id_list3])

    ### MARTIN'S SPECIAL FORM OF SENDING DATA #################################
    testint_list = []
    operation_type = str()
    CGI_CLI.parse_input_data(key = 'testint', append_to_list = testint_list)

    ### LIST FORMAT: SWAN--DEVICE--INTERFACE--MODE ############################
    for testint in testint_list:
        try: dash_interface = testint.split('--')[2].strip()
        except: dash_interface = str()

        try:
            swan_id = testint.split('--')[0].strip()
            devices_interfaces_list.append([testint.split('--')[1].strip(),\
                [dash_interface]])
        except: pass

        try: operation_type = testint.split('--')[3].strip()
        except: operation_type = str()

    if not PING_ONLY:
        if operation_type:
            if operation_type in action_type_list:
                action_type = operation_type

        if 'bb' in action_type:
            BB_MODE = True
        elif 'custom' in action_type:
            CUSTOMER_MODE = True

    if CGI_CLI.timestamp:
        CGI_CLI.uprint('After parsing of input data.\n', \
            no_printall = not printall, tag = 'debug')

    ### TESTSERVER WORKAROUND #################################################
    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()

    if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
    else: urllink = 'https://%s/cgi-bin/' % (iptac_server)


    ### START PRINTING AND LOGGING ############################################
    changelog = 'https://github.com/peteneme/pyxWorks/commits/master/backbone_pre_traffic_activation/pre_traffic.py'

    if PING_ONLY:
        SCRIPT_NAME = 'Interface pre traffic ping check'
    else:
        SCRIPT_NAME = 'Interface (Backbone/Custom) pre traffic activation check'

    if CGI_CLI.cgi_active:
        CGI_CLI.uprint('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s)</a></h1>' % \
            (SCRIPT_NAME, changelog, CGI_CLI.VERSION()), raw = True)
    else: CGI_CLI.uprint('%s (v.%s)' % (SCRIPT_NAME,CGI_CLI.VERSION()), \
              tag = 'h1', color = 'blue')
    CGI_CLI.print_args()

    CGI_CLI.uprint('action_type = "%s"' % (action_type))

    CGI_CLI.uprint('BB_MODE = %s, CUSTOMER_MODE = %s, PING_ONLY = %s' % \
        (str(BB_MODE),str(CUSTOMER_MODE),str(PING_ONLY)), \
        no_printall = not printall, tag = 'debug')

    ### def SQL INIT ##########################################################
    sql_inst = sql_interface(host='localhost', user='cfgbuilder', \
        password='cfgbuildergetdata', database='rtr_configuration')


    ### def SQL CREATE RECORDS IF SWAN_ID AND NO PRE/POST CHECK ACTION ########
    if not swan_id and CGI_CLI.data.get('swan_id'):
        swan_id = CGI_CLI.data.get('swan_id')

    if not swan_id and CGI_CLI.data.get('swan-id'):
        swan_id = CGI_CLI.data.get('swan-id')

    ### SIGN BUTTON ###########################################################
    if not PING_ONLY and swan_id and (CGI_CLI.data.get('submit',str()) == 'Sign precheck' \
        or CGI_CLI.data.get('submit',str()) == 'Sign postcheck'):

        for device, interface_list in devices_interfaces_list:
            for interface_id in interface_list:

                ### TEST IF SWAN ALREADY RECORD EXISTS ########################
                sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                    table_name = 'pre_post_result' + table_test_extension, \
                    where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                         % (swan_id, device.upper(), interface_id) )

                CGI_CLI.uprint(sql_read_data, name = True, jsonprint = True, \
                    no_printall = not CGI_CLI.printall)

                ### WARNING MESSAGE ###########################################
                if len(sql_read_data) > 0:
                    if CGI_CLI.data.get('submit',str()) == 'Sign precheck':
                        sql_read_data[0]['precheck_signed'] = '%s %s' % (CGI_CLI.get_date_and_time(), USERNAME)
                        sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, sql_read_data[0],
                            where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                            % (swan_id, device.upper(), interface_id), update = True)
                        sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                            table_name = 'pre_post_result' + table_test_extension, \
                            where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                                 % (swan_id, device.upper(), interface_id) )
                    if CGI_CLI.data.get('submit',str()) == 'Sign postcheck':
                        sql_read_data[0]['postcheck_signed'] = '%s %s' % (CGI_CLI.get_date_and_time(), USERNAME)
                        sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, sql_read_data[0],
                            where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                            % (swan_id, device.upper(), interface_id), update = True)
                        sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                            table_name = 'pre_post_result' + table_test_extension, \
                            where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                                 % (swan_id, device.upper(), interface_id) )
                else: CGI_CLI.uprint("No record found in db!", tag = 'warning')
        sys.exit(0)


    ### MAKE SQL TABLE RECORD ONLY AND EXIT ###################################
    if not PING_ONLY and ( \
        (swan_id and CGI_CLI.data.get('submit',str()) == 'SUBMIT+STEP+2') \
        or (swan_id \
        and not (CGI_CLI.data.get('submit-type',str()) == 'submit-with-precheck' \
        or CGI_CLI.data.get('submit-type',str()) == 'submit-with-precheck' \
        or CGI_CLI.data.get('submit',str()) == 'Run precheck' \
        or CGI_CLI.data.get('submit',str()) == 'Run postcheck'))):

        ### TEST IF SWAN ALREADY RECORD EXISTS ########################
        sql_read_data = sql_inst.sql_read_records_to_dict_list( \
            table_name = 'pre_post_result' + table_test_extension, \
            where_string = "swan_id='%s'" % (swan_id) )

        ### WARNING MESSAGE ###########################################
        if len(sql_read_data) > 0:
            if CGI_CLI.data.get('reinit_swan_id'):
                CGI_CLI.uprint("WARNING: REINIT swan_id='%s' record(s) in pre_post_result%s table in DB." \
                     % (swan_id, table_test_extension), color = 'red')
            else:
                CGI_CLI.uprint("WARNING: swan_id='%s' record(s) already exist(s) in pre_post_result%s table in DB! Aborting..." \
                     % (swan_id, table_test_extension), color = 'red')
                sys.exit(0)

        for device, interface_list in devices_interfaces_list:
            for interface_id in interface_list:
                pre_post_template = sql_inst.sql_read_all_table_columns_to_void_dict(\
                    'pre_post_result' + table_test_extension, ommit_columns = ['id','last_updated'])

                pre_post_template['swan_id'] = swan_id
                pre_post_template['router_name'] = device.upper()
                pre_post_template['int_name'] = interface_id
                pre_post_template['precheck_result'] = '-'
                pre_post_template['postcheck_result'] = '-'
                pre_post_template['precheck_log'] = str()
                pre_post_template['postcheck_log'] = str()

                if 'operation_type' in pre_post_template.keys():
                    pre_post_template['operation_type'] = str(action_type)

                ### TEST IF SWAN ALREADY RECORD EXISTS ########################
                sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                    table_name = 'pre_post_result' + table_test_extension, \
                    where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                         % (swan_id, device.upper(), interface_id) )

                CGI_CLI.uprint(sql_read_data, name = True, jsonprint = True, \
                    no_printall = not CGI_CLI.printall)

                ### WARNING MESSAGE ###########################################
                if len(sql_read_data) > 0:
                    CGI_CLI.uprint("WARNING: DB Record already exists per swan_id='%s' and router_name='%s' and int_name='%s'! Overwriting..." \
                         % (swan_id, device.upper(), interface_id), color = 'red')

                    sql_read_data[0]['precheck_result'] = '-'
                    sql_read_data[0]['postcheck_result'] = '-'
                    sql_read_data[0]['precheck_log'] = str()
                    sql_read_data[0]['postcheck_log'] = str()

                    if 'operation_type' in sql_read_data[0].keys():
                        sql_read_data[0]['operation_type'] = str(action_type)

                    try:
                        del sql_read_data[0]['id']
                        del sql_read_data[0]['last_updated']
                    except: pass
                    sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, sql_read_data[0],
                        where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                            % (swan_id, device.upper(), interface_id), update = True)

                else:
                    sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, pre_post_template)
                    CGI_CLI.uprint ("RECORD swan_id='%s' and router_name='%s' and int_name='%s' DONE." \
                        % (swan_id, device.upper(), interface_id), no_printall = not CGI_CLI.printall)

                ### TEST IF SWAN ALREADY RECORD EXISTS ########################
                sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                    table_name = 'pre_post_result' + table_test_extension, \
                    where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                         % (swan_id, device.upper(), interface_id) )
                CGI_CLI.uprint(sql_read_data, name = 'DB_READ_CHECK', jsonprint = True, \
                    no_printall = not CGI_CLI.printall)

        sys.exit(0)


    ### def CREATE ALL INTERFACES LIST PER DEVICE ##############################
    if len(device_list) > 0 and len(devices_interfaces_list) == 0:
        for device in device_list:
            device_interface_list = get_interface_list_per_device(device, action_type = action_type)
        CGI_CLI.uprint(device_interface_list, name='%s_interface_list' % (device), \
            jsonprint = True, no_printall = not printall, tag = 'debug')


    ### def HTML MENUS DISPLAYED ONLY IN CGI MODE #############################
    if CGI_CLI.cgi_active and \
        (not CGI_CLI.submit_form or CGI_CLI.submit_form in CGI_CLI.self_buttons):
        ### OTHER SUBMIT BUTTONS THAN OK ALLOWS "REMOTE" CGI CONTROL ##########

        ### MAIN MENU #########################################################
        if len(device_list) == 0 and len(interface_line_list) == 0 \
            and len(device_interface_list) == 0:

            interface_menu_list = [{'text':'device'},'<br/>', \
                '<h3>(Optional) select menu available in next step:</h3>',\
                {'text':'interface'},'<br/>']

            if not (USERNAME and PASSWORD):
                interface_menu_list.append('<br/>')
                interface_menu_list.append('<authentication>')
                interface_menu_list.append('LDAP authentication (required):')
                interface_menu_list.append('<br/>')
                interface_menu_list.append('<br/>')
                interface_menu_list.append({'text':'username'})
                interface_menu_list.append('<br/>')
                interface_menu_list.append({'password':'password'})
                interface_menu_list.append('<br/>')
                interface_menu_list.append('</authentication>')

            CGI_CLI.formprint(interface_menu_list + ['<br/><b><u>',\
                {'checkbox':'customer_interfaces'}, '</u></b><br/>',\
                {'checkbox':'timestamps'}, '<br/>',\
                {'checkbox':'printall'},'<br/>','<br/>'],\
                submit_button = CGI_CLI.self_buttons[0], \
                pyfile = None, tag = None, color = None)
            ### EXIT AFTER MENU PRINTING ######################################
            sys.exit(0)

        ### INTERFACE MENU PART ###############################################
        elif len(devices_interfaces_list) == 0 and len(device_interface_list) > 0:
            table_rows = 1
            counter = 0
            interface_menu_list = [
                '<p hidden><input type="checkbox" name="device" value="%s" checked="checked"></p>' \
                    % (','.join(device_list) if len(device_list) > 0 else str()),
                '<p hidden><input type="checkbox" name="cusername" value="%s" checked="checked"></p>' \
                    % (USERNAME.encode('base64','strict')),
                '<p hidden><input type="checkbox" name="cpassword" value="%s" checked="checked"></p>' \
                    % (PASSWORD.encode('base64','strict')),
                '<p hidden><input type="checkbox" name="type" value="%s" checked="checked"></p>' \
                    % (str(action_type)),
                '<h2>Select interface on %s:</h2>' % (device if device else str()),
                '<div align="left">', '<table style="width:90%">']

            for whole_if_line, interface in device_interface_list:
                if counter == 0: interface_menu_list.append('<tr>')
                interface_menu_list.append('<td>')
                interface_menu_list.append({'checkbox':'%s%s' % (interface_cgi_string,whole_if_line)})
                counter += 1
                interface_menu_list.append('</td>')
                if counter + 1 > table_rows:
                    interface_menu_list.append('</tr>')
                    counter = 0
            if counter != 0: router_type_menu_list.append('</tr>')
            interface_menu_list.append('</table>')
            interface_menu_list.append('</div>')
            interface_menu_list.append('<br/><br/>')

            if not (USERNAME and PASSWORD):
                interface_menu_list.append('<h3>LDAP authentication (required):</h3>')
                interface_menu_list.append({'text':'username'})
                interface_menu_list.append('<br/>')
                interface_menu_list.append({'password':'password'})
                interface_menu_list.append('<br/><br/><br/>')

            if not PING_ONLY:
                interface_menu_list.append({'radio':['precheck','postcheck']})
                interface_menu_list.append('<br/><br/>')
                interface_menu_list.append({'text':'swan_id'})
                interface_menu_list.append({'checkbox':'reinit_swan_id'})
                interface_menu_list.append('<br/><br/>')
                interface_menu_list.append('Additional ping_counts = %s' % (ping_counts))
            else:
                interface_menu_list.append('<br/><br/>')
                interface_menu_list.append('Default ping_counts = %s' % (ping_counts))


            interface_menu_list.append('<br/>')
            interface_menu_list.append({'text':'ping_counts'})
            interface_menu_list.append('<br/>')

            if not PING_ONLY:
                interface_menu_list.append('<br/><b>NOTE: chunked mode is longtime running mode without http connection timeout.</b><br/>')
                interface_menu_list.append({'checkbox':'chunked_mode'})
                interface_menu_list.append('<br/><br/>')

            CGI_CLI.formprint( interface_menu_list + \
                [ {'checkbox':'timestamps'}, '<br/><b><u>',\
                {'checkbox':'send_email'},'</u></b><br/>',\
                {'checkbox':'printall'},'<br/>','<br/>' ], \
                submit_button = CGI_CLI.self_buttons[0],
                pyfile = None, tag = None, color = None , list_separator = '&emsp;')
            ### EXIT AFTER MENU PRINTING ######################################
            sys.exit(0)



    ### END DUE TO MISSING INPUT DATA #########################################
    exit_due_to_error = None

    if len(devices_interfaces_list) == 0:
        CGI_CLI.uprint('Interface id NOT INSERTED!', tag = 'h2', color = 'red')
        exit_due_to_error = True

    if not USERNAME:
        CGI_CLI.uprint('Username NOT INSERTED!', tag = 'h2', color = 'red')
        exit_due_to_error = True

    if not PASSWORD:
        CGI_CLI.uprint('Password NOT INSERTED!', tag = 'h2', color = 'red')
        exit_due_to_error = True

    if exit_due_to_error: sys.exit(0)

    ### PRINT SELECTED DEVICE AND INTERFACE ###################################
    CGI_CLI.uprint(devices_interfaces_list, name = 'devices_interfaces_list',\
            jsonprint = True, color = 'blue')


    ### def REMOTE DEVICE OPERATIONS ##########################################
    device_data, interface_results = [], []
    old_device = str()
    for device, interface_list in devices_interfaces_list:
        if device:
            ### DISCONNECT, IF DEVICE IS NOT THE SAME AS BEFORE ###############
            if old_device and old_device != device: RCMD.disconnect()

            ### LOOP THROUGH THE SAME DEVICE WITHOUT RECONNECT OR NEW CONNECT #
            if not old_device or old_device != device:

                ### IF NOT POSSIBLE TO CONNECT AND DEVICE IS THE SAME #########
                old_device = device

                ### DEVICE CONNECT ############################################
                RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                    printall = printall, \
                    connection_timeout = 10000, cmd_timeout = 2200)

                if not RCMD.ssh_connection:
                    CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), \
                        color = 'red')
                    RCMD.disconnect()
                    continue

            ### NORMAL CASE, CONNECTON OK --> SET OLD_DEVICE ##################
            old_device = device

            ### DO NOT GO FURTHER IF NO CONNECTION ############################
            if not RCMD.ssh_connection: continue

            ### LOOP PER INTERFACE ############################################
            for interface_id in interface_list:
                ### VARIABLES PER INTERFACE ###
                USE_IPV6 = False
                IPV4_STATIC_ROUTING = False
                IPV6_STATIC_ROUTING = False
                check_interface_result_ok = True
                check_warning_interface_result_ok = True

                ### def LOGFILENAME GENERATION, DO LOGGING ONLY WHEN DEVICE LIST EXISTS ###
                html_extention = 'htm' if CGI_CLI.cgi_active else str()

                if BB_MODE: PREFIX_PART = str('BB_PRECHECK' if precheck_mode else 'BB_POSTCHECK')
                elif CUSTOMER_MODE: PREFIX_PART = str('CUST_PRECHECK' if precheck_mode else 'CUST_POSTCHECK')
                elif PING_ONLY: PREFIX_PART = 'PINGCHECK'

                logfilename = generate_logfilename(
                    prefix = str(swan_id) + '-' if swan_id else str() + PREFIX_PART + \
                    '_' + device.upper() + '_' + interface_id.replace('/','-'), \
                    USERNAME = USERNAME, suffix = '%slog' % (html_extention))
                ### NO WINDOWS LOGGING ########################################
                if 'WIN32' in sys.platform.upper(): logfilename = None
                if logfilename: CGI_CLI.set_logfile(logfilename = logfilename)
                logfilename_list.append(logfilename)

                if CGI_CLI.cgi_active:
                    CGI_CLI.logtofile('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s)</a></h1>' % \
                        (SCRIPT_NAME, changelog, CGI_CLI.VERSION()), raw_log = True, ommit_timestamp = True)
                else: CGI_CLI.logtofile('%s (v.%s)' % (SCRIPT_NAME,CGI_CLI.VERSION()), ommit_timestamp = True)

                CGI_CLI.logtofile(CGI_CLI.print_args(ommit_print = True) + '\n\n', ommit_timestamp = True)

                if swan_id: CGI_CLI.uprint('SWAN_ID=%s' % (swan_id))

                if BB_MODE:
                    if precheck_mode: CGI_CLI.uprint('Backbone monitoring/precheck mode.')
                    else: CGI_CLI.uprint('Backbone traffic/postcheck mode.')
                elif CUSTOMER_MODE:
                    if precheck_mode: CGI_CLI.uprint('Customer monitoring/precheck mode.')
                    else: CGI_CLI.uprint('Customer traffic/postcheck mode.')
                elif PING_ONLY: CGI_CLI.uprint('Ping only mode.')

                CGI_CLI.logtofile('\nDETECTED DEVICE_TYPE: %s\n\n' % (RCMD.router_type))

                interface_data = collections.OrderedDict()
                interface_data['interface_id'] = interface_id
                interface_warning_data = collections.OrderedDict()
                interface_warning_data['interface_id'] = interface_id
                interface_data['interface_data'] = collections.OrderedDict()
                interface_data['interface_statistics'] = collections.OrderedDict()
                interface_warning_data['interface_data'] = collections.OrderedDict()
                interface_warning_data['interface_statistics'] = collections.OrderedDict()

                try: undotted_interface_id = interface_id.split('.')[0]
                except: undotted_interface_id = interface_id

                ### def LONG INTERFACE NAMES ##################################
                interface_long_name = str()
                interface_long_names = {}
                interface_long_names['BE'] = 'Bundle-Ether'
                interface_long_names['GI'] = 'GigabitEthernet'
                interface_long_names['HU'] = 'HundredGigE'
                interface_long_names['TE'] = 'TenGigE'
                interface_long_names['NU'] = 'Null'

                if interface_long_names.get(interface_id[0:2].upper()):
                    interface_long_name = interface_long_names.get(interface_id[0:2].upper(),str()) + interface_id[2:]
                else: interface_long_name = interface_id[2:]

                CGI_CLI.uprint('Collecting %s data on %s' % (interface_id, device), \
                    no_newlines = None if printall else True)

                ### def START OF DATA COLLECTION ##############################
                interface_traffic_errors_check(undotted_interface_id)

                ### LOCAL AS NUMBER COMMANDS ##################################
                collector_cmds = {
                    'cisco_ios':['show bgp summary',
                                 'show bgp vpnv4 unicast summary',
                                 'show bgp ipv6 unicast summary',
                                 'show running-config router static | include %s' % (str(interface_long_name)),
                                ],

                    'cisco_xr': ['show bgp summary',
                                 'show bgp vpnv4 unicast summary',
                                 'show bgp ipv6 unicast summary',
                                 'show running-config router static | include %s' % (str(interface_long_name)),
                                ],

                    'juniper':  ['show bgp neighbor | match "Group:|Peer:" | except "NLRI|Restart"',
                                 'show bgp summary',
                                ],

                    'huawei':   ['display bgp peer',
                                 'display bgp vpnv4 all peer',
                                 'disp current-configuration configuration route-static | include %s' % (interface_id),
                                ]
                }

                ### RUN START COLLETING OF DATA ###
                rcmd_outputs = RCMD.run_commands(collector_cmds, \
                    autoconfirm_mode = True, \
                    printall = printall)

                ### FIND LOCAL AS NUMBER ###
                if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
                    try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("local AS number")[1].splitlines()[0].strip()
                    except: pass
                    if not LOCAL_AS_NUMBER:
                        try: LOCAL_AS_NUMBER = rcmd_outputs[1].split("local AS number")[1].splitlines()[0].strip()
                        except: pass

                    if interface_data['interface_data'].get('ASN'):
                        interface_data['interface_data']['IPV4_addr_rem_from_ASN'] = []
                        for line in rcmd_outputs[0].splitlines():
                            try:
                                if str(line.split()[1]) == interface_data['interface_data'].get('ASN') or str(line.split()[2]) == interface_data['interface_data'].get('ASN'):
                                    interface_data['interface_data']['IPV4_addr_rem_from_ASN'].append(line.split()[0])
                            except: pass
                        if len(interface_data['interface_data']['IPV4_addr_rem_from_ASN']) == 0:
                            del interface_data['interface_data']['IPV4_addr_rem_from_ASN']

                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'] = []
                        previous_line = str()
                        for line in rcmd_outputs[2].splitlines() or str(line.split()[2]) == interface_data['interface_data'].get('ASN'):
                            try:
                                if str(line.split()[1]) == interface_data['interface_data'].get('ASN'):
                                    if ':' in line.split()[0]:
                                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'].append(copy.deepcopy(line.split()[0]))
                                    elif ':' in previous_line:
                                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'].append(copy.deepcopy(previous_line.split()[0]))
                            except: pass
                            previous_line = line
                        if len(interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']) == 0:
                            del interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']

                    ### def ROUTER STATIC #####################################
                    for line in rcmd_outputs[3].splitlines():
                        try:    possible_bgp_peer = line.split()[0]
                        except: possible_bgp_peer = None
                        try:    possible_interface = line.split()[1]
                        except: possible_interface = None
                        try:    possible_addr_rem = line.split()[2]
                        except: possible_addr_rem = None

                        if possible_bgp_peer and possible_interface and possible_addr_rem:
                            if '.' in possible_bgp_peer and '/' in possible_bgp_peer and possible_interface[0] == interface_id[0] and str(interface_id[2:]) in possible_interface:
                                interface_data['interface_data']['IPV4_bgp_peer_from_ROUTER_STATIC'] = copy.deepcopy(possible_bgp_peer.split('/'))[0]
                                interface_data['interface_data']['IPV4_addr_rem_from_ROUTER_STATIC'] = copy.deepcopy(possible_addr_rem)
                                IPV4_STATIC_ROUTING = True
                                interface_data['interface_data']['IPV4_STATIC_ROUTING'] = True
                            elif ':' in possible_bgp_peer and '/' in possible_bgp_peer:
                                interface_data['interface_data']['IPV6_bgp_peer_from_ROUTER_STATIC'] = copy.deepcopy(possible_bgp_peer.split('/')[0])
                                interface_data['interface_data']['IPV6_addr_rem_from_ROUTER_STATIC'] = copy.deepcopy(possible_addr_rem)
                                IPV6_STATIC_ROUTING = True
                                interface_data['interface_data']['IPV6_STATIC_ROUTING'] = True

                            if IPV4_STATIC_ROUTING:
                                 interface_data['interface_data']['IPV4_bgp_neighbor'] = copy.deepcopy(interface_data['interface_data'].get('IPV4_bgp_peer_from_ROUTER_STATIC'))
                                 interface_data['interface_data']['IPV4_addr_rem'] = copy.deepcopy(interface_data['interface_data'].get('IPV4_addr_rem_from_ROUTER_STATIC'))

                            if IPV6_STATIC_ROUTING:
                                 interface_data['interface_data']['IPV6_bgp_neighbor'] = copy.deepcopy(interface_data['interface_data'].get('IPV6_bgp_peer_from_ROUTER_STATIC'))
                                 interface_warning_data['interface_data']['IPV6_addr_rem'] = copy.deepcopy(interface_data['interface_data'].get('IPV6_addr_rem_from_ROUTER_STATIC'))

                elif RCMD.router_type == 'juniper':
                    try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("Local:")[1].splitlines()[0].split('AS')[1].strip()
                    except: pass

                    if interface_data['interface_data'].get('ASN'):
                        interface_data['interface_data']['IPV4_addr_rem_from_ASN'] = []
                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'] = []
                        for line in rcmd_outputs[1].splitlines():
                            try:
                                if str(line.split()[1]) == interface_data['interface_data'].get('ASN'):
                                    if '.' in line.split()[0]:
                                        interface_data['interface_data']['IPV4_addr_rem_from_ASN'].append(copy.deepcopy(line.split()[0]))
                                    elif ':' in line.split()[0]:
                                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'].append(copy.deepcopy(line.split()[0]))
                            except: pass
                        if len(interface_data['interface_data']['IPV4_addr_rem_from_ASN']) == 0:
                            del interface_data['interface_data']['IPV4_addr_rem_from_ASN']
                        if len(interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']) == 0:
                            del interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']

                elif RCMD.router_type == 'huawei':
                    try: LOCAL_AS_NUMBER = rcmd_outputs[0].split("Local AS number :")[1].splitlines()[0].strip()
                    except: pass
                    if not LOCAL_AS_NUMBER:
                        try: LOCAL_AS_NUMBER = rcmd_outputs[1].split("Local AS number :")[1].splitlines()[0].strip()
                        except: pass

                    if interface_data['interface_data'].get('ASN'):
                        interface_data['interface_data']['IPV4_addr_rem_from_ASN'] = []
                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'] = []
                        for line in rcmd_outputs[0].splitlines():
                            try:
                                if str(line.split()[2]) == interface_data['interface_data'].get('ASN'):
                                    if '.' in line.split()[0]:
                                        interface_data['interface_data']['IPV4_addr_rem_from_ASN'].append(copy.deepcopy(line.split()[0]))
                                    elif ':' in line.split()[0]:
                                        interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN'].append(copy.deepcopy(line.split()[0]))
                            except: pass
                        if len(interface_data['interface_data']['IPV4_addr_rem_from_ASN']) == 0:
                            del interface_data['interface_data']['IPV4_addr_rem_from_ASN']
                        if len(interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']) == 0:
                            del interface_warning_data['interface_data']['IPV6_addr_rem_from_ASN']

                    for line in rcmd_outputs[2].splitlines():
                        try: bgp_peer = line.split('ip route-static ')[1].split()[0]
                        except: bgp_peer = None
                        if bgp_peer and '.' in bgp_peer:
                            interface_data['interface_data']['IPV4_bgp_neighbor'] = copy.deepcopy(bgp_peer)
                            IPV4_STATIC_ROUTING = True
                            interface_data['interface_data']['IPV4_STATIC_ROUTING'] = True
                        elif bgp_peer and ':' in bgp_peer:
                            interface_data['interface_data']['IPV6_bgp_neighbor'] = copy.deepcopy(bgp_peer)
                            IPV6_STATIC_ROUTING = True
                            interface_data['interface_data']['IPV6_STATIC_ROUTING'] = True
                interface_data['LOCAL_AS_NUMBER'] = LOCAL_AS_NUMBER

                ### def CONFIGURATION RUN INTERFACE LIST ######################
                collect_if_data_rcmds = {
                    'cisco_ios':[
                        'show run interface %s' % (interface_id),
                    ],

                    'cisco_xr':[
                        'show run interface %s' % (interface_id),
                    ],

                    'juniper': [
                        'show configuration interfaces %s | display set' % (interface_id),
                        'show configuration groups mtu-default | display set',
                    ],

                    'huawei': [
                        'display current-configuration interface %s' % (interface_id),
                    ]
                }

                collect_if_config_rcmd_outputs = RCMD.run_commands(collect_if_data_rcmds, \
                    autoconfirm_mode = True, \
                    printall = printall)

                if BB_MODE:
                    try: interface_data['interface_data']['name_of_remote_device_from_description'] = copy.deepcopy(collect_if_config_rcmd_outputs[0].upper().split('DESCRIPTION')[1].splitlines()[0].split('FROM')[0].split()[-1].strip().replace('"',''))
                    except: interface_data['interface_data']['name_of_remote_device_from_description'] = str()

                if 'PE' in interface_data['interface_data'].get('name_of_remote_device_from_description',str()).upper() or 'PE' in device.upper():
                    IMN_INTERFACE = True

                interface_data['IMN_INTERFACE'] = IMN_INTERFACE

                try: interface_data['interface_data']['IPV4_addr_rem_from_DESCRIPTION'] = copy.deepcopy(collect_if_config_rcmd_outputs[0].split('description')[1].splitlines()[0].split('@')[1].split()[0])
                except: pass

                try: interface_warning_data['interface_data']['bandwidth'] = copy.deepcopy(collect_if_config_rcmd_outputs[0].\
                         split('bandwidth ')[1].splitlines()[0].strip().replace(';',''))
                except: interface_warning_data['interface_data']['bandwidth'] = str()

                try: interface_data['interface_data']['fib_number(s)'] = ','.join(get_fiblist(collect_if_config_rcmd_outputs[0].split('description')[1].splitlines()[0]))
                except: interface_data['interface_data']['fib_number'] = str()

                ### CISCO XR+XE ping CMDS ##################################
                if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                    try: interface_data['interface_data']['LAG_member'] = 'yes' if 'bundle id ' in collect_if_config_rcmd_outputs[0] else 'no'
                    except: pass

                    try: interface_data['interface_data']['IPV4_addr_loc'] = collect_if_config_rcmd_outputs[0].split('ipv4 address ')[1].split()[0]
                    except: interface_data['interface_data']['IPV4_addr_loc'] = str()

                    try: interface_data['interface_data']['IPV4_mask_loc_dotted'] = collect_if_config_rcmd_outputs[0].split('ipv4 address ')[1].split()[1]
                    except: pass

                    try: interface_data['interface_data']['IPV6_addr_loc'] = collect_if_config_rcmd_outputs[0].split('ipv6 address ')[1].split()[0].split('/')[0]
                    except: pass

                    try: interface_data['interface_data']['IPV6_mask_loc'] = collect_if_config_rcmd_outputs[0].split('ipv6 address ')[1].split()[0].split('/')[1]
                    except: pass

                    try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[0].split('mtu ')[1].splitlines()[0].strip()
                    except:
                        if interface_data['interface_data'].get('bundle_members_nr') and interface_data['interface_data'].get('LAG_member',str()) == 'no': pass
                        else: interface_warning_data['interface_data']['MTU_interface_configured'] = str()

                    if BB_MODE:
                        interface_data['interface_data']['dampening'] = True if 'dampening' in collect_if_config_rcmd_outputs[0] else str()
                        try: interface_data['interface_data']['flow ipv4 monitor'] = collect_if_config_rcmd_outputs[0].split('flow ipv4 monitor ')[1].split()[0]
                        except: interface_data['interface_data']['flow ipv4 monitor'] = str()

                        if interface_data['interface_data'].get('IPV6_addr_loc'):
                            try: interface_data['interface_data']['flow ipv6 monitor'] = collect_if_config_rcmd_outputs[0].split('flow ipv4 monitor ')[1].split()[0]
                            except: interface_data['interface_data']['flow ipv6 monitor'] = str()

                    elif CUSTOMER_MODE:
                        try: interface_data['interface_data']['service-policy_input'] = collect_if_config_rcmd_outputs[0].split('service-policy input ')[1].splitlines()[0].strip()
                        except: interface_data['interface_data']['service-policy_input'] = str()

                        try: interface_data['interface_data']['service-policy_output'] = collect_if_config_rcmd_outputs[0].split('service-policy output ')[1].splitlines()[0].strip()
                        except: interface_data['interface_data']['service-policy_output'] = str()

                        try: interface_data['interface_data']['flow_ipv4_monitor'] = collect_if_config_rcmd_outputs[0].split('flow ipv4 monitor ')[1].splitlines()[0].strip()
                        except: interface_data['interface_data']['flow_ipv4_monitor'] = str()

                        try: interface_data['interface_data']['IPV4_access-group'] = collect_if_config_rcmd_outputs[0].split('ipv4 access-group ')[1].splitlines()[0].strip()
                        except: interface_data['interface_data']['IPV4_access-group'] = str()

                        if interface_data['interface_data'].get('IPV6_addr_loc'):
                            try: interface_data['interface_data']['flow_ipv6_monitor'] = collect_if_config_rcmd_outputs[0].split('flow ipv6 monitor ')[1].splitlines()[0].strip()
                            except: interface_data['interface_data']['flow_ipv6_monitor'] = str()

                            try: interface_data['interface_data']['IPV6_access-group'] = collect_if_config_rcmd_outputs[0].split('ipv6 access-group ')[1].splitlines()[0].strip()
                            except: interface_data['interface_data']['IPV6_access-group'] = str()

                elif RCMD.router_type == 'juniper':
                    try: interface_data['interface_data']['LAG_member'] = 'yes' if 'gigether-options ' in collect_if_config_rcmd_outputs[0] else 'no'
                    except: pass

                    try: interface_data['interface_data']['IPV4_addr_loc'] = collect_if_config_rcmd_outputs[0].split('family inet address ')[1].split()[0].split('/')[0].replace(';','')
                    except: interface_data['interface_data']['IPV4_addr_loc'] = str()

                    try: interface_data['interface_data']['IPV4_mask_loc'] = collect_if_config_rcmd_outputs[0].split('family inet address ')[1].split()[0].split('/')[1].replace(';','')
                    except: pass

                    try: interface_data['interface_data']['IPV6_addr_loc'] = collect_if_config_rcmd_outputs[0].split('family inet6 address ')[1].split()[0].split('/')[0].replace(';','')
                    except: pass

                    try: interface_data['interface_data']['IPV6_mask_loc'] = collect_if_config_rcmd_outputs[0].split('family inet6 address ')[1].split()[0].split('/')[1].replace(';','')
                    except: pass

                    if CUSTOMER_MODE:
                        interface_data['interface_data']['inet filter input(-list)'] = []
                        for line in collect_if_config_rcmd_outputs[0].splitlines():
                            try: interface_data['interface_data']['inet filter input(-list)'].append(line.split('inet filter input-list ')[1].split()[0])
                            except:
                                try: interface_data['interface_data']['inet filter input(-list)'].append(copy.deepcopy(line.split('inet filter input ')[1].split()[0]))
                                except: pass

                        if interface_data['interface_data'].get('IPV6_addr_loc'):
                            interface_data['interface_data']['inet6 filter input(-list)'] = []
                            for line in collect_if_config_rcmd_outputs[0].splitlines():
                                try: interface_data['interface_data']['inet6 filter input(-list)'].append(copy.deepcopy(line.split('inet6 filter input-list ')[1].split()[0]))
                                except:
                                    try: interface_data['interface_data']['inet6 filter input(-list)'].append(copy.deepcopy(line.split('inet6 filter input ')[1].split()[0]))
                                    except: pass

                    try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[1].split('<%s%s' % (interface_id[0],interface_id[1]))[1].split('mtu ')[1].splitlines()[0].strip()
                    except:
                        if interface_data['interface_data'].get('bundle_members_nr') and interface_data['interface_data'].get('LAG_member',str()) == 'no': pass
                        else: interface_warning_data['interface_data']['MTU_interface_configured'] = str()

                elif RCMD.router_type == 'huawei':
                    try: interface_data['interface_data']['LAG_member'] = 'yes' if 'eth-trunk ' in collect_if_config_rcmd_outputs[0] else 'no'
                    except: pass

                    try: interface_data['interface_data']['IPV4_addr_loc'] = collect_if_config_rcmd_outputs[0].split('ip address ')[1].split()[0]
                    except: interface_data['interface_data']['IPV4_addr_loc'] = str()

                    try: interface_data['interface_data']['IPV4_mask_loc_dotted'] = collect_if_config_rcmd_outputs[0].split('ip address ')[1].split()[1]
                    except: pass

                    try: interface_data['interface_data']['IPV6_addr_loc'] = collect_if_config_rcmd_outputs[0].split('ipv6 address ')[1].split()[0].split('/')[0]
                    except: pass

                    try: interface_data['interface_data']['IPV6_mask_loc'] = collect_if_config_rcmd_outputs[0].split('ipv6 address ')[1].split()[0].split('/')[1]
                    except: pass

                    try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[0].split('mtu ')[1].splitlines()[0].strip()
                    except:
                        if interface_data['interface_data'].get('bundle_members_nr') and interface_data['interface_data'].get('LAG_member',str()) == 'no': pass
                        else: interface_warning_data['interface_data']['MTU_interface_configured'] = str()

                    if CUSTOMER_MODE:
                        try: interface_warning_data['interface_data']['traffic-policy'] = collect_if_config_rcmd_outputs[0].split('traffic-policy ')[1].split()[0].strip()
                        except: interface_warning_data['interface_data']['traffic-policy'] = str()

                        try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[0].split('mtu ')[1].splitlines()[0].strip()
                        except: interface_warning_data['interface_data']['MTU_interface_configured'] = str()


                ### def IPV6 CONDITION - YES OR NO ############################
                ### OTI_LOCAL_AS = '5511', IMN_LOCAL_AS = '2300' ##############
                #if (LOCAL_AS_NUMBER != IMN_LOCAL_AS and not IMN_INTERFACE) \
                #    or interface_data['interface_data'].get('IPV6_addr_loc'):

                if interface_data['interface_data'].get('IPV6_addr_loc'): USE_IPV6 = True
                interface_data['USE_IPV6'] = USE_IPV6

                ###############################################################
                ### def CALCULATE REMOTE IP ADDRESES: THE OTHER IP IN NETWORK #
                ###############################################################
                ### https://cpython-test-docs.readthedocs.io/en/latest/howto/ipaddress.html
                list_of_ipv4_network, list_of_ipv6_network = [], []
                if interface_data['interface_data'].get('IPV4_addr_loc'):
                    if interface_data['interface_data'].get('IPV4_mask_loc_dotted',str()) == '255.255.255.254':
                        interface_data['interface_data']['IPV4_mask_loc'] = '31'
                    if interface_data['interface_data'].get('IPV4_mask_loc_dotted',str()) == '255.255.255.252':
                        interface_data['interface_data']['IPV4_mask_loc'] = '30'
                    if interface_data['interface_data'].get('IPV4_mask_loc'):
                        interface = ipaddress.IPv4Interface(u'%s/%s' % \
                            (interface_data['interface_data'].get('IPV4_addr_loc'), \
                            interface_data['interface_data'].get('IPV4_mask_loc')))

                        ipv4_network = interface.network
                        CGI_CLI.uprint('Network: ' + str(ipv4_network), tag = 'debug', no_printall = not CGI_CLI.printall)

                        if interface_data['interface_data'].get('IPV4_mask_loc') == '31':
                            for addr in ipaddress.IPv4Network(ipv4_network):
                                CGI_CLI.uprint("addr4=%s" % (addr), tag = 'debug', no_printall = not CGI_CLI.printall)
                                if str(addr).upper() == str(interface_data['interface_data'].get('IPV4_addr_loc')).upper(): pass
                                else:
                                    interface_warning_data['interface_data']['IPV4_addr_rem_calculated'] = copy.deepcopy(str(addr))
                                    interface_data['interface_data']['IPV4_addr_rem'] = copy.deepcopy(str(addr))
                                    break


                        if interface_data['interface_data'].get('IPV4_mask_loc') == '30':
                            i_counter = 0
                            for addr in ipaddress.IPv4Network(ipv4_network):
                                CGI_CLI.uprint("addr4=%s" % (addr), tag = 'debug', no_printall = not CGI_CLI.printall)
                                if i_counter == 1 or i_counter == 2:
                                    if str(addr).upper() == str(interface_data['interface_data'].get('IPV4_addr_loc')).upper(): pass
                                    else:
                                        interface_warning_data['interface_data']['IPV4_addr_rem_calculated'] =  copy.deepcopy(str(addr))
                                        interface_data['interface_data']['IPV4_addr_rem'] = copy.deepcopy(str(addr))
                                        break
                                i_counter += 1

                if interface_data['interface_data'].get('IPV6_addr_loc') and interface_data['interface_data'].get('IPV6_mask_loc'):
                    interface = ipaddress.IPv6Interface(u'%s/%s' % \
                        (interface_data['interface_data'].get('IPV6_addr_loc'), interface_data['interface_data'].get('IPV6_mask_loc')))

                    ipv6_network = interface.network
                    CGI_CLI.uprint('Network: ' + str(ipv6_network), tag = 'debug', no_printall = not CGI_CLI.printall)

                    if interface_data['interface_data'].get('IPV6_mask_loc') == '127':
                        for addr in ipaddress.IPv6Network(ipv6_network):
                            CGI_CLI.uprint("addr6=%s" % (addr), tag = 'debug', no_printall = not CGI_CLI.printall)
                            if normalized_ipv6(str(addr).upper()) == normalized_ipv6(str(interface_data['interface_data'].get('IPV6_addr_loc')).upper()): pass
                            else:
                                interface_warning_data['interface_data']['IPV6_addr_rem_calculated'] = copy.deepcopy(normalized_ipv6(addr))
                                interface_warning_data['interface_data']['IPV6_addr_rem'] = copy.deepcopy(normalized_ipv6(addr))
                                break

                    if interface_data['interface_data'].get('IPV6_mask_loc') == '126':
                        i_counter = 0
                        for addr in ipaddress.IPv6Network(ipv6_network):
                            CGI_CLI.uprint("addr6=%s" % (addr), tag = 'debug', no_printall = not CGI_CLI.printall)
                            if i_counter == 1 or i_counter == 2:
                                if normalized_ipv6(str(addr).upper()) == normalized_ipv6(str(interface_data['interface_data'].get('IPV6_addr_loc')).upper()): pass
                                else:
                                    interface_warning_data['interface_data']['IPV6_addr_rem_calculated'] = copy.deepcopy(normalized_ipv6(addr))
                                    interface_warning_data['interface_data']['IPV6_addr_rem'] = copy.deepcopy(normalized_ipv6(addr))
                                    break
                            i_counter += 1


                ### def ALL MODES LOCALHOST ADDRESS ###########################
                collect0_if_data_rcmds = {
                    'cisco_ios':[
                        'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                        'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                    ],

                    'cisco_xr':[
                        'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                        'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                    ],

                    'juniper': [
                        'show configuration routing-options static | match %s | display set ' % (interface_data['interface_data'].get('IPV4_addr_rem')) if interface_data['interface_data'].get('IPV4_addr_rem') else str(),
                        'show configuration routing-options static | match %s | display set ' % (interface_warning_data['interface_data'].get('IPV6_addr_rem')) if interface_warning_data['interface_data'].get('IPV6_addr_rem') else str(),
                    ],

                    'huawei': [
                    ]
                }

                collect0_if_config_rcmd_outputs = RCMD.run_commands(collect0_if_data_rcmds, \
                    autoconfirm_mode = True, \
                    printall = printall)

                interface_data['bgp'] = collections.OrderedDict()
                possible_ipv4_bgp_peers = []
                possible_ipv6_bgp_peers = []

                if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                    try: interface_data['bgp']['IPV4 Local host'] = copy.deepcopy(collect0_if_config_rcmd_outputs[0].split('Local host:')[1].split()[0].replace(',',''))
                    except: pass

                    try: interface_data['bgp']['IPV6 Local host'] = copy.deepcopy(collect0_if_config_rcmd_outputs[1].split('Local host:')[1].split()[0].replace(',',''))
                    except: pass

                elif RCMD.router_type == 'juniper':
                    try:
                        for line in collect0_if_config_rcmd_outputs[0].splitlines():
                            try: possible_ipv4_bgp_peers.append(line.split('set routing-options static route ')[1].split()[0].split('/')[0])
                            except: pass
                    except: pass

                    try:
                        for line in collect0_if_config_rcmd_outputs[1].splitlines():
                            try: possible_ipv6_bgp_peers.append(line.split('set routing-options static route ')[1].split()[0].split('/')[0])
                            except: pass
                    except: pass


                CGI_CLI.uprint("possible_ipv4_bgp_peers = " + str(possible_ipv4_bgp_peers), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("possible_ipv6_bgp_peers = " + str(possible_ipv6_bgp_peers), tag = 'debug', no_printall = not CGI_CLI.printall)

                ### def ALL MODES SECOND LOCALHOST ADDRESS ####################
                if len(possible_ipv4_bgp_peers) > 0:
                    collect1_if_data_rcmds = {
                        'cisco_ios':[
                         ],

                        'cisco_xr':[
                         ],

                        'juniper': [
                         ],

                        'huawei': [
                        ]
                    }

                    for peer in possible_ipv4_bgp_peers:
                        collect1_if_data_rcmds['juniper'].append('show bgp neighbor %s' % (str(peer)))

                    for peer in possible_ipv6_bgp_peers:
                        collect1_if_data_rcmds['juniper'].append('show bgp neighbor %s' % (str(peer)))

                    collect1_if_config_rcmd_outputs = RCMD.run_commands(collect1_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'juniper':
                        for cmd_output in collect1_if_config_rcmd_outputs:
                            if 'Peer: ' in cmd_output and 'Local: ' in cmd_output:
                                try:
                                    localhost = cmd_output.split('Local: ')[1].split()[0].split('+')[0]
                                    bgp_peer = cmd_output.split('Peer: ')[1].split()[0].split('+')[0]
                                except: localhost, bgp_peer = str(), str()

                                if localhost and bgp_peer and '.' in localhost and '.' in bgp_peer:
                                    interface_data['bgp']['IPV4 Local host'] = cmd_output.split('Local: ')[1].split()[0].split('+')[0]
                                    interface_data['interface_data']['IPV4_bgp_neighbor'] = cmd_output.split('Peer: ')[1].split()[0].split('+')[0]
                                    IPV4_STATIC_ROUTING = True
                                    interface_data['interface_data']['IPV4_STATIC_ROUTING'] = True

                                elif localhost and bgp_peer and ':' in localhost and ':' in bgp_peer:
                                    interface_data['bgp']['IPV6 Local host'] = cmd_output.split('Local: ')[1].split()[0].split('+')[0]
                                    interface_data['interface_data']['IPV6_bgp_neighbor'] = cmd_output.split('Peer: ')[1].split()[0].split('+')[0]
                                    IPV6_STATIC_ROUTING = True
                                    interface_data['interface_data']['IPV6_STATIC_ROUTING'] = True


                ###############################################################
                ### def FIND REMOTE IP ADDRESES: THE OTHER IP IN NETWORK ######
                ###############################################################
                if not interface_data['interface_data'].get('IPV4_addr_rem') and interface_data['interface_data'].get('IPV4_addr_rem_from_DESCRIPTION'):
                    interface_data['interface_data']['IPV4_addr_rem'] = copy.deepcopy(interface_data['interface_data'].get('IPV4_addr_rem_from_DESCRIPTION'))

                if not interface_data['interface_data'].get('IPV4_bgp_neighbor') and interface_data['interface_data'].get('IPV4_addr_rem'):
                    interface_data['interface_data']['IPV4_bgp_neighbor'] = copy.deepcopy(interface_data['interface_data'].get('IPV4_addr_rem'))

                if not interface_data['interface_data'].get('IPV6_bgp_neighbor') and interface_warning_data['interface_data'].get('IPV6_addr_rem'):
                    interface_data['interface_data']['IPV6_bgp_neighbor'] = copy.deepcopy(interface_warning_data['interface_data'].get('IPV6_addr_rem'))


                ### def ADDRESSES PRINTOUTS ###################################
                CGI_CLI.uprint("interface_data['interface_data']['IPV4_addr_loc'] = " + str(interface_data['interface_data'].get('IPV4_addr_loc')), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("interface_data['interface_data']['IPV6_addr_loc'] = " + str(interface_data['interface_data'].get('IPV6_addr_loc')), tag = 'debug', no_printall = not CGI_CLI.printall)

                CGI_CLI.uprint("interface_data['interface_data']['IPV4_mask_loc'] = " + str(interface_data['interface_data'].get('IPV4_mask_loc')), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("interface_data['interface_data']['IPV6_mask_loc'] = " + str(interface_data['interface_data'].get('IPV6_mask_loc')), tag = 'debug', no_printall = not CGI_CLI.printall)

                CGI_CLI.uprint("interface_warning_data['interface_data']['IPV4_addr_rem_calculated'] = " + str(interface_warning_data['interface_data'].get('IPV4_addr_rem_calculated')), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("interface_warning_data['interface_data']['IPV6_addr_rem_calculated'] = " + str(interface_warning_data['interface_data'].get('IPV6_addr_rem_calculated')), tag = 'debug', no_printall = not CGI_CLI.printall)

                CGI_CLI.uprint("interface_data['interface_data']['IPV4_addr_rem'] = " + str(interface_data['interface_data'].get('IPV4_addr_rem')), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("interface_warning_data['interface_data']['IPV6_addr_rem'] = " + str(interface_warning_data['interface_data'].get('IPV6_addr_rem')), tag = 'debug', no_printall = not CGI_CLI.printall)

                CGI_CLI.uprint("interface_data['interface_data']['IPV4_bgp_neighbor'] = " + str(interface_data['interface_data'].get('IPV4_bgp_neighbor')), tag = 'debug', no_printall = not CGI_CLI.printall)
                CGI_CLI.uprint("interface_data['interface_data']['IPV6_bgp_neighbor'] = " + str(interface_data['interface_data'].get('IPV6_bgp_neighbor')), tag = 'debug', no_printall = not CGI_CLI.printall)


                ###############################################################
                ### def BB_MODE - 1st COLLECT COMMAND LIST ####################
                ###############################################################
                if BB_MODE:
                    collect_if_data_rcmds = {
                        'cisco_ios':[
                            'show run router isis PAII interface %s ' % (interface_id),
                            'show run mpls traffic-eng interface %s' % (interface_id),
                            'show run mpls ldp interface %s' % (interface_id),
                            'show run rsvp interface %s' % (interface_id),

                            'show interface %s' % (interface_id),
                            'show isis neighbors %s' % (interface_id),
                            'show mpls ldp neighbor %s' % (interface_id),
                            'show mpls ldp igp sync interface %s' % (interface_id),
                            'show rsvp interface %s' % (interface_id),

                            'show interfaces %s' % (undotted_interface_id),
                            'show interfaces description'
                        ],

                        'cisco_xr':[
                            'show run router isis PAII interface %s ' % (interface_id),
                            'show run mpls traffic-eng interface %s' % (interface_id),
                            'show run mpls ldp interface %s' % (interface_id),
                            'show run rsvp interface %s' % (interface_id),

                            'show interface %s' % (interface_id),
                            'show isis neighbors %s' % (interface_id),
                            'show mpls ldp neighbor %s' % (interface_id),
                            'show mpls ldp igp sync interface %s' % (interface_id),
                            'show rsvp interface %s' % (interface_id),

                            'show interfaces %s' % (undotted_interface_id),
                            'show interfaces description'
                        ],

                        'juniper': [
                            'show isis interface %s' % (interface_id),
                            'show configuration protocols mpls',
                            'show configuration protocols ldp | match %s' % (interface_id),
                            'show configuration protocols rsvp | match %s' % (interface_id),

                            'show interfaces brief %s' % (undotted_interface_id),
                            'show isis adjacency | match %s' % (interface_id),
                            'show ldp neighbor | match %s' % (interface_id),
                            'show isis interface %s extensive' % (interface_id),
                            'show rsvp interface %s' % (interface_id),

                            'show configuration class-of-service interfaces %s | display set'  % (undotted_interface_id),
                            'show configuration groups mtu-default | display set',
                            'show configuration protocols isis interface %s' % (interface_id),
                            'show interfaces %s extensive' % (undotted_interface_id), ### ???
                            'show interfaces descriptions'
                        ],

                        'huawei': [
                            'display current-configuration interface %s | i isis' % (interface_id),
                            'display current-configuration interface %s | i  mpls te' % (interface_id),
                            'display current-configuration interface %s | i mpls ldp' % (interface_id),
                            'display current-configuration interface %s | i rsvp' % (interface_id),

                            'display interface %s' % (interface_id),
                            'display isis interface %s' % (interface_id),
                            'display mpls ldp adjacency interface %s' % (interface_id),
                            'display isis ldp-sync interface | i %s' % (interface_id.upper().replace('GI','GE')),
                            'display mpls rsvp-te interface %s' % (interface_id),

                            'display interface %s' % (undotted_interface_id),
                            'display interface description'
                        ]
                    }

                    collect_if_config_rcmd_outputs = RCMD.run_commands(collect_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    ### CISCO XR+XE 1st CMDS ##################################
                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        interface_data['interface_data']['mpls ldp sync'] = True if 'mpls ldp sync' in collect_if_config_rcmd_outputs[0] else str()

                        try: interface_data['interface_data']['ipv4_metric'] = collect_if_config_rcmd_outputs[0].split('address-family ipv4 unicast')[1].splitlines()[1].split('metric ')[1].split()[0]
                        except: interface_data['interface_data']['ipv4_metric'] = str()

                        if USE_IPV6:
                            try: interface_data['interface_data']['ipv6_metric'] = collect_if_config_rcmd_outputs[0].split('address-family ipv6 unicast')[1].splitlines()[1].split('metric ')[1].split()[0]
                            except: interface_data['interface_data']['ipv6_metric'] = str()

                        try: interface_data['interface_data']['run mpls traffic-eng interface'] = collect_if_config_rcmd_outputs[1].split('interface')[1].split()[0]
                        except: interface_data['interface_data']['run mpls traffic-eng interface'] = str()

                        try: interface_data['interface_data']['run mpls ldp interface'] = collect_if_config_rcmd_outputs[2].split('interface')[1].split()[0]
                        except: interface_data['interface_data']['run mpls ldp interface'] = str()

                        try: interface_data['interface_data']['run mpls rsvp interface'] = collect_if_config_rcmd_outputs[2].split('interface')[1].split()[0]
                        except: interface_data['interface_data']['run mpls rsvp interface'] = str()

                        try: interface_data['interface_data']['isis neighbors'] = collect_if_config_rcmd_outputs[5].split(interface_data['interface_data'].get('name_of_remote_device_from_description','XXYYZZ').upper())[1].split(interface_id)[1].split()[1].strip()
                        except: interface_data['interface_data']['isis neighbors'] = str()

                        try: interface_data['interface_data']['Up time'] = collect_if_config_rcmd_outputs[6].split('Up time:')[1].split()[0]
                        except: interface_data['interface_data']['Up time'] = str()

                        try: interface_data['interface_data']['Sync status'] = collect_if_config_rcmd_outputs[7].split('Sync status:')[1].split()[0]
                        except: interface_data['interface_data']['Sync status'] = str()

                        if 'Requested item does not exist' in collect_if_config_rcmd_outputs[8]: interface_data['interface_data']['rsvp interface'] = str()
                        else:
                            try: interface_data['interface_data']['rsvp interface'] = collect_if_config_rcmd_outputs[8].split('------')[-1].splitlines()[1].split()[0].strip()
                            except: interface_data['interface_data']['rsvp interface'] = str()

                        if not precheck_mode:
                            ### BACKUP INTERFACES ###
                            try:
                                backup_if_list = []
                                if interface_data['interface_data'].get('name_of_remote_device_from_description'):
                                    for line in collect_if_config_rcmd_outputs[10].splitlines():
                                        if '%s FROM %s' % (interface_data['interface_data'].get('name_of_remote_device_from_description',str()).upper(), device.upper()) in line.upper():
                                            local_backup_interface = str(line.split()[0]).replace('GE','Gi')
                                            if '(' in local_backup_interface: local_backup_interface = local_backup_interface.split('(')[0]
                                            if ' TESTING ' in line or ' OLD ' in line.upper(): pass
                                            else: backup_if_list.append(copy.deepcopy(local_backup_interface))
                                interface_data['interface_data']['parallel_interfaces'] = copy.deepcopy(backup_if_list)
                            except: interface_data['interface_data']['parallel_interfaces'] = []

                    ### JUNIPER 1st CMDS ##########################################
                    elif RCMD.router_type == 'juniper':
                        try: interface_data['interface_data']['scheduler-map'] = collect_if_config_rcmd_outputs[9].split('scheduler-map ')[1].split()[0].split('/')[0].replace(';','')
                        except: interface_data['interface_data']['scheduler-map'] = str()

                        try: interface_prefix = interface_id[0:2]
                        except: interface_prefix = str()

                        if interface_prefix:
                            try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[10].split('<' + interface_prefix).split('mtu ')[1].splitlines()[0].strip()
                            except: interface_warning_data['interface_data']['MTU_interface_configured'] = str()

                        if not interface_warning_data['interface_data'].get('MTU_interface_configured'):
                            try: interface_warning_data['interface_data']['MTU_interface_configured'] = collect_if_config_rcmd_outputs[10].split('mtu ')[1].splitlines()[0].strip()
                            except: interface_warning_data['interface_data']['MTU_interface_configured'] = str()

                        interface_data['interface_data']['ldp-synchronization;'] = True if 'ldp-synchronization;' in collect_if_config_rcmd_outputs[11] else str()

                        try: interface_data['interface_data']['L2 metric'] = collect_if_config_rcmd_outputs[11].split('metric ')[1].split()[0].replace(';','').strip()
                        except: interface_data['interface_data']['L2 metric'] = str()

                        interface_data['interface_data']['traffic-engineering;'] = True if 'traffic-engineering;' in collect_if_config_rcmd_outputs[1] else str()
                        interface_plus_interface_id = 'interface %s'% (interface_id)

                        interface_data['interface_data']['configuration protocols mpls interface %s' % (interface_id)] = True if interface_plus_interface_id in collect_if_config_rcmd_outputs[1] else str()
                        interface_data['interface_data']['configuration protocols ldp interface %s' % (interface_id)] = True if interface_plus_interface_id in collect_if_config_rcmd_outputs[2] else str()
                        interface_data['interface_data']['configuration protocols rsvp interface %s' % (interface_id)] = True if interface_plus_interface_id in collect_if_config_rcmd_outputs[3] else str()

                        try: interface_data['interface_data']['Flags'] = collect_if_config_rcmd_outputs[4].split('Flags:')[1].split()[0]
                        except: interface_data['interface_data']['Flags'] = str()

                        try: interface_data['interface_data']['isis adjacency'] = collect_if_config_rcmd_outputs[5].split(interface_data['interface_data'].get('name_of_remote_device_from_description','XXYYZZ').upper())[1].splitlines()[0].split()[1]
                        except: interface_data['interface_data']['isis adjacency'] = str()

                        find_ip = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3} ', collect_if_config_rcmd_outputs[6].strip())

                        if len(find_ip) == 1: interface_data['interface_data']['ldp_neighbor_ip'] = find_ip[0].strip()
                        else: interface_data['interface_data']['ldp_neighbor_ip'] = str()

                        try: interface_data['interface_data']['LDP sync state'] = collect_if_config_rcmd_outputs[7].split('LDP sync state:')[1].split(',')[0].strip()
                        except: interface_data['interface_data']['LDP sync state'] = str()

                        try: interface_data['interface_data']['rsvp interface'] = collect_if_config_rcmd_outputs[8].split('Interface')[1].splitlines()[1].split()[0]
                        except: interface_data['interface_data']['rsvp interface'] = str()

                        if not precheck_mode:
                            ### BACKUP INTERFACES ###
                            try:
                                backup_if_list = []
                                if interface_data['interface_data'].get('name_of_remote_device_from_description'):
                                    for line in collect_if_config_rcmd_outputs[13].splitlines():
                                        if '%s FROM %s' % (interface_data['interface_data'].get('name_of_remote_device_from_description',str()).upper(), device.upper()) in line.upper():
                                            local_backup_interface = str(line.split()[0]).replace('GE','Gi')
                                            if '(' in local_backup_interface: local_backup_interface = local_backup_interface.split('(')[0]
                                            if ' TESTING ' in line or ' OLD ' in line: pass
                                            else: backup_if_list.append(copy.deepcopy(local_backup_interface))
                                interface_data['interface_data']['parallel_interfaces'] = copy.deepcopy(backup_if_list)
                            except: interface_data['interface_data']['parallel_interfaces'] = []

                    ### HUAWEI 1st CMDS ###########################################
                    elif RCMD.router_type == 'huawei':

                        ### BANDWITH IS OPTIONABLE --> AVOID FROM VOID CHECK ######
                        if not interface_warning_data['interface_data'].get('bandwidth'):
                            del interface_warning_data['interface_data']['bandwidth']

                        interface_data['interface_data']['isis ldp-sync'] = True if 'isis ldp-sync' in collect_if_config_rcmd_outputs[0] else str()

                        try: interface_data['interface_data']['isis cost'] = collect_if_config_rcmd_outputs[0].split('isis cost ')[1].split()[0]
                        except: interface_data['interface_data']['isis cost'] = str()

                        if USE_IPV6:
                            try: interface_data['interface_data']['isis ipv6 cost'] = collect_if_config_rcmd_outputs[0].split('isis ipv6 cost ')[1].split()[0]
                            except: interface_data['interface_data']['isis ipv6 cost'] = str()

                        interface_data['interface_data']['mpls te'] = True if 'mpls te' in collect_if_config_rcmd_outputs[1] else str()
                        interface_data['interface_data']['mpls ldp'] = True if 'mpls ldp' in collect_if_config_rcmd_outputs[2] else str()
                        interface_data['interface_data']['mpls rsvp-te'] = True if 'mpls rsvp-te' in collect_if_config_rcmd_outputs[3] else str()

                        try: interface_data['interface_data']['Line protocol current state'] = collect_if_config_rcmd_outputs[4].split('Line protocol current state :')[1].split()[0]
                        except: interface_data['interface_data']['Line protocol current state'] = str()

                        try: interface_data['interface_data']['isis interface IPV4.State'] = collect_if_config_rcmd_outputs[5].split(' Type')[1].split(' DIS')[1].split()[2]
                        except: interface_data['interface_data']['isis interface IPV4.State'] = str()

                        if USE_IPV6:
                            try: interface_data['interface_data']['isis interface IPV6.State'] = collect_if_config_rcmd_outputs[5].split(' Type')[1].split(' DIS')[1].split()[3]
                            except: interface_data['interface_data']['isis interface IPV6.State'] = str()

                        find_time = re.findall(r'[0-9]{2,4}\:[0-9]{2}\:[0-9]{2}', collect_if_config_rcmd_outputs[6].strip())
                        if len(find_time) == 1: interface_data['Up time'] = find_time[0]
                        else: interface_data['interface_data']['Up time'] = str()

                        try: interface_data['interface_data']['isis ldp-sync'] = collect_if_config_rcmd_outputs[7].split('Sync State')[1].split(interface_id.upper().replace('GI','GE'))[1].split()[3].strip()
                        except: interface_data['interface_data']['isis ldp-sync'] = str()

                        try: interface_data['interface_data']['rsvp interface'] = collect_if_config_rcmd_outputs[8].split('Interface:')[1].split()[0]
                        except: interface_data['interface_data']['rsvp interface'] = str()

                        if not precheck_mode:
                            ### BACKUP INTERFACES ###
                            try:
                                backup_if_list = []
                                if interface_data['interface_data'].get('name_of_remote_device_from_description'):
                                    for line in collect_if_config_rcmd_outputs[10].splitlines():
                                        if '%s FROM %s' % (interface_data['interface_data'].get('name_of_remote_device_from_description',str()).upper(), device.upper()) in line.upper():
                                            local_backup_interface = str(line.split()[0])
                                            if not '100GE' in local_backup_interface: local_backup_interface = local_backup_interface.replace('GE','Gi')
                                            if '(' in local_backup_interface: local_backup_interface = local_backup_interface.split('(')[0]
                                            if ' TESTING ' in line or ' OLD ' in line: pass
                                            else: backup_if_list.append(copy.deepcopy(local_backup_interface))
                                interface_data['interface_data']['parallel_interfaces'] = copy.deepcopy(backup_if_list)
                            except: interface_data['interface_data']['parallel_interfaces'] = []


                    ###########################################################
                    ### def BB_MODE - 2nd COLLECT COMMAND LIST ################
                    ###########################################################
                    if RCMD.router_type == 'juniper':
                        second_collect_if_data_rcmds = {
                            'cisco_ios':[
                            ],

                            'cisco_xr':[
                            ],

                            'juniper': [
                                'show ldp neighbor %s extensive' % (interface_data['interface_data'].get('ldp_neighbor_ip',str()))
                            ],

                            'huawei': [
                            ]
                        }

                        second_collect_if_config_rcmd_outputs = RCMD.run_commands(second_collect_if_data_rcmds, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if RCMD.router_type == 'juniper':
                            try: interface_data['interface_data']['Up for'] = second_collect_if_config_rcmd_outputs[0].split('Up for ')[1].splitlines()[0].strip()
                            except: interface_data['interface_data']['Up for'] = str()


                ###############################################################
                ### def CUSTOMER_MODE - ISIS COLLECT COMMAND LIST #############
                ###############################################################
                elif CUSTOMER_MODE:
                    interface_data['isis'] = collections.OrderedDict()

                    collect_if_data_rcmds = {
                        'cisco_ios':[
                            'show run router isis PAII interface %s ' % (interface_id),
                            'show interface %s' % (interface_id),
                        ],

                        'cisco_xr':[
                            'show run router isis PAII interface %s ' % (interface_id),
                            'show interface %s' % (interface_id),
                        ],

                        'juniper': [
                            'show configuration class-of-service interfaces %s' % (undotted_interface_id),
                            'show configuration protocols isis interface %s' % (interface_id),
                            'show isis interface %s' % (interface_id),
                            'show interfaces brief %s' % (interface_id),
                            'show interfaces %s extensive' % (interface_id),
                        ],

                        'huawei': [
                            'display current-configuration interface %s | i isis' % (interface_id),
                            'display isis interface %s' % (interface_id),

                        ]
                    }

                    collect_if_config_rcmd_outputs = RCMD.run_commands(collect_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        interface_data['isis']['passive'] = True if 'passive' in collect_if_config_rcmd_outputs[0] else None

                        try: interface_data['isis']['IPV4 address-family'] = collect_if_config_rcmd_outputs[0].split('address-family ipv4 ')[1].splitlines()[0].strip()
                        except: interface_data['isis']['IPV4 address-family'] = str()

                        try: interface_data['isis']['IPV6 address-family'] = collect_if_config_rcmd_outputs[0].split('address-family ipv6 ')[1].splitlines()[0].strip()
                        except: interface_data['isis']['IPV6 address-family'] = str()

                        try: interface_warning_data['interface_data']['MTU_default'] = collect_if_config_rcmd_outputs[1].split('MTU ')[1].splitlines()[0].split()[0].strip()
                        except: interface_warning_data['interface_data']['MTU_default'] = str()

                        try: interface_data['interface_data']['Full-duplex_bandwith'] = collect_if_config_rcmd_outputs[1].split('Full-duplex,')[1].splitlines()[0].split()[0].replace(',','').strip()
                        except: interface_data['interface_data']['Full-duplex_bandwith'] = str()

                    elif RCMD.router_type == 'juniper':
                        try: interface_data['interface_data']['scheduler-map'] = collect_if_config_rcmd_outputs[0].split('scheduler-map')[1].split()[0].replace(';','')
                        except: interface_data['interface_data']['scheduler-map'] = str()

                        try: interface_data['isis']['level'] = collect_if_config_rcmd_outputs[1].split('level')[1].split()[0]
                        except: interface_data['isis']['level'] = str()

                        try: interface_data['isis']['metric'] = collect_if_config_rcmd_outputs[1].split('metric')[1].split()[0].replace(';','')
                        except: interface_data['isis']['metric'] = str()

                        try: interface_data['isis']['passive'] = True if 'passive;' in collect_if_config_rcmd_outputs[1] else str()
                        except: interface_data['isis']['passive'] = str()

                        try: interface_data['isis']['Level 2 DR'] = collect_if_config_rcmd_outputs[2].split('L1/L2 Metric')[1].split(interface_id)[1].split()[3].replace(';','')
                        except: interface_data['isis']['Level 2 DR'] = str()

                        try: interface_data['isis']['L1 Metric'] = collect_if_config_rcmd_outputs[2].split('L1/L2 Metric')[1].split(interface_id)[1].split()[4].split('/')[0]
                        except: interface_data['isis']['L1 Metric'] = str()

                        try: interface_data['interface_data']['Flags'] = collect_if_config_rcmd_outputs[3].split('Flags:')[1].split()[0]
                        except: interface_data['interface_data']['Flags'] = str()

                        try: interface_data['interface_data']['inet'] = collect_if_config_rcmd_outputs[3].split('inet ')[1].split()[0]
                        except: interface_data['interface_data']['inet'] = str()

                        try: interface_data['interface_data']['inet6'] = collect_if_config_rcmd_outputs[3].split('inet6 ')[1].split()[0]
                        except: interface_data['interface_data']['inet6'] = str()

                        try: interface_data['interface_data']['multiservice'] = True if 'multiservice' in collect_if_config_rcmd_outputs[3] else str()
                        except: interface_data['interface_data']['multiservice'] = str()

                        try: interface_data['interface_data']['MTU_default'] = collect_if_config_rcmd_outputs[4].split('Protocol inet, MTU:')[1].split()[0]
                        except: interface_data['interface_data']['MTU_default'] = str()

                        try: interface_data['interface_data']['IPV6 MTU_default'] = collect_if_config_rcmd_outputs[4].split('Protocol inet6, MTU:')[1].split()[0]
                        except: pass

                        try: interface_data['interface_data']['IPV4 Destination'] = collect_if_config_rcmd_outputs[4].split('Protocol inet,')[1].split('Destination: ')[1].split()[0].replace(',','')
                        except: interface_data['interface_data']['IPV4 Destination'] = str()

                        try: interface_data['interface_data']['IPV4 Local'] = collect_if_config_rcmd_outputs[4].split('Protocol inet,')[1].split('Local: ')[1].split()[0]
                        except: interface_data['interface_data']['IPV4 Local'] = str()

                        try: interface_data['interface_data']['IPV6 MTU_default'] = collect_if_config_rcmd_outputs[4].split('Protocol inet6')[1].split('MTU: ')[1].split()[0]
                        except: pass

                        try: interface_data['interface_data']['IPV6 Destination'] = collect_if_config_rcmd_outputs[4].split('Protocol inet6')[1].split('Destination: ')[1].split()[0].replace(',','')
                        except: pass

                        try: interface_data['interface_data']['IPV6 Local'] = collect_if_config_rcmd_outputs[4].split('Protocol inet6')[1].split('Local: ')[1].split()[0]
                        except: pass


                    elif RCMD.router_type == 'huawei':
                        interface_data['isis']['isis enable 5511'] = True if 'isis enable 5511' in collect_if_config_rcmd_outputs[0] else str()

                        if USE_IPV6:
                            interface_data['isis']['isis ipv6 enable 5511'] = True if 'isis ipv6 enable 5511' in collect_if_config_rcmd_outputs[0] else str()

                        interface_data['isis']['isis silent advertise-zero-cost'] = True if 'isis silent advertise-zero-cost' in collect_if_config_rcmd_outputs[0] else str()




                    ###########################################################
                    ### def CUSTOMER_MODE - 2nd DATA COLLECTION ###############
                    ###########################################################
                    collect2_if_data_rcmds = {
                        'cisco_ios':[
                            'show running-config router bgp 5511 neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            'show running-config router bgp 5511 neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                        ],

                        'cisco_xr':[
                            'show running-config router bgp 5511 neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            'show running-config router bgp 5511 neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                        ],

                        'juniper': [
                            'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                        ],

                        'huawei': [
                            "display bgp peer %s verbose | i Peer's description" % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            "display bgp peer %s verbose | i Peer's description" % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                        ]
                    }

                    collect2_if_config_rcmd_outputs = RCMD.run_commands(collect2_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        if IPV4_STATIC_ROUTING:
                            try: interface_data['bgp']['IPV4 ebgp-multihop'] = collect2_if_config_rcmd_outputs[0].split('ebgp-multihop ')[1].split()[0]
                            except: pass

                        if IPV6_STATIC_ROUTING:
                            try: interface_data['bgp']['IPV6 ebgp-multihop'] = collect2_if_config_rcmd_outputs[1].split('ebgp-multihop ')[1].split()[0]
                            except: pass

                        if interface_data['interface_data'].get('IPV4_bgp_neighbor'):
                            try: interface_data['bgp']['IPV4 use_neighbor-group'] = collect2_if_config_rcmd_outputs[0].split('use neighbor-group ')[1].splitlines()[0].strip()
                            except: interface_data['bgp']['IPV4 use_neighbor-group'] = str()

                        if interface_data['interface_data'].get('IPV6_bgp_neighbor'):
                            try: interface_data['bgp']['IPV6 use neighbor-group'] = collect2_if_config_rcmd_outputs[1].split('use neighbor-group ')[1].splitlines()[0].strip()
                            except: pass

                    elif RCMD.router_type == 'juniper':
                        if interface_data['interface_data'].get('IPV4_bgp_neighbor'):
                            try: interface_data['bgp']['IPV4 neighbor-group'] = collect2_if_config_rcmd_outputs[0].split('Group: ')[1].split()[0]
                            except: interface_data['bgp']['IPV4 neighbor-group'] = str()

                        if interface_data['interface_data'].get('IPV6_bgp_neighbor'):
                            try: interface_data['bgp']['IPV6 neighbor-group'] = collect2_if_config_rcmd_outputs[1].split('Group: ')[1].split()[0]
                            except: pass

                        try: interface_data['bgp']['IPV4 Active prefixes'] = collect2_if_config_rcmd_outputs[0].split('Active prefixes: ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 Received prefixes'] = collect2_if_config_rcmd_outputs[0].split('Received prefixes: ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 Accepted prefixes'] = collect2_if_config_rcmd_outputs[0].split('Accepted prefixes: ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 Suppressed due to damping'] = collect2_if_config_rcmd_outputs[0].split('Suppressed due to damping: ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 Advertised prefixes'] = collect2_if_config_rcmd_outputs[0].split('Advertised prefixes: ')[1].split()[0]
                        except: pass

                    elif RCMD.router_type == 'huawei':
                        if interface_data['interface_data'].get('IPV4_bgp_neighbor'):
                            try: interface_data['bgp']['IPV4 neighbor-group'] = collect2_if_config_rcmd_outputs[0].split("Peer's description:")[1].splitlines()[0].replace('"','').strip()
                            except: interface_data['bgp']['IPV4 neighbor-group'] = str()

                        if interface_data['interface_data'].get('IPV6_bgp_neighbor'):
                            try: interface_data['bgp']['IPV6 neighbor-group'] = collect2_if_config_rcmd_outputs[1].split("Peer's description:")[1].splitlines()[0].replace('"','').strip()
                            except: pass



                    ###########################################################
                    ### def CUSTOMER_MODE - 3rd DATA COLLECTION ###############
                    ###########################################################
                    collect3_if_data_rcmds = {
                        'cisco_ios':[
                            'show running-config router bgp 5511 neighbor-group %s' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv4 unicast' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv4 multicast' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv6 unicast' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv6 multicast' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                          ],

                        'cisco_xr':[
                            'show running-config router bgp 5511 neighbor-group %s' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv4 unicast' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv4 multicast' % (interface_data['bgp'].get('IPV4 use_neighbor-group',str())) if interface_data['bgp'].get('IPV4 use_neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv6 unicast' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                            'show running-config router bgp 5511 neighbor-group %s address-family ipv6 multicast' % (interface_data['bgp'].get('IPV6 use neighbor-group',str())) if interface_data['bgp'].get('IPV6 use neighbor-group') else str(),
                         ],

                        'juniper': [
                            'show configuration protocols bgp group %s | display set' % (interface_data['bgp'].get('IPV4 neighbor-group',str())) if interface_data['bgp'].get('IPV4 neighbor-group') else str(),
                            'show configuration protocols bgp group %s | display set' % (interface_data['bgp'].get('IPV6 neighbor-group',str())) if interface_data['bgp'].get('IPV6 neighbor-group') else str(),
                        ],

                        'huawei': [
                            'display current-configuration configuration bgp | i %s' % (interface_data['bgp'].get('IPV4 neighbor-group',str())) if interface_data['bgp'].get('IPV4 neighbor-group') else str(),
                            'display current-configuration configuration bgp | i %s' % (interface_data['bgp'].get('IPV6 neighbor-group',str())) if interface_data['bgp'].get('IPV6 neighbor-group') else str(),
                        ]
                    }

                    collect3_if_config_rcmd_outputs = RCMD.run_commands(collect3_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        if interface_data['bgp'].get('IPV4 use_neighbor-group'):
                            if IPV4_STATIC_ROUTING:
                                try: interface_data['bgp']['IPV4 ebgp-multihop'] = collect3_if_config_rcmd_outputs[0].split('ebgp-multihop ')[1].split()[0]
                                except: pass

                            if IPV6_STATIC_ROUTING:
                                try: interface_data['bgp']['IPV6 ebgp-multihop'] = collect3_if_config_rcmd_outputs[3].split('ebgp-multihop ')[1].split()[0]
                                except: pass

                            interface_data['bgp']['IPV4 address-family'] = []
                            try:
                                if 'address-family ipv4 unicast' in collect3_if_config_rcmd_outputs[0]:
                                    interface_data['bgp']['IPV4 address-family'].append('unicast')
                            except: pass

                            try:
                                if 'address-family ipv4 multicast' in collect3_if_config_rcmd_outputs[0]:
                                    interface_data['bgp']['IPV4 address-family'].append('multicast')
                            except: pass

                            try: interface_data['bgp']['IPV4 remote-as'] = collect3_if_config_rcmd_outputs[0].split('remote-as ')[1].splitlines()[0].strip()
                            except: interface_data['bgp']['IPV4 remote-as'] = str()

                            if 'unicast' in interface_data['bgp'].get('IPV4 address-family',str()):
                                try: interface_data['bgp']['IPV4 unicast route-policy in'] = collect3_if_config_rcmd_outputs[1].split('route-policy ')[1].splitlines()[0].split()[0].strip()
                                except: interface_data['bgp']['IPV4 unicast route-policy in'] = str()

                                try: interface_data['bgp']['IPV4 unicast maximum-prefix'] = collect3_if_config_rcmd_outputs[1].split('maximum-prefix ')[1].splitlines()[0].split()[0].strip()
                                except: interface_data['bgp']['IPV4 unicast maximum-prefix'] = str()

                                try: interface_data['bgp']['IPV4 unicast route-policy out'] = collect3_if_config_rcmd_outputs[1].split('route-policy ')[2].splitlines()[0].split()[0].strip()
                                except: interface_data['bgp']['IPV4 unicast route-policy out'] = str()

                            if 'multicast' in interface_data['bgp'].get('IPV4 address-family',str()):
                                try: interface_data['bgp']['IPV4 multicast route-policy in'] = collect3_if_config_rcmd_outputs[2].split('route-policy ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV4 multicast maximum-prefix'] = collect3_if_config_rcmd_outputs[2].split('maximum-prefix ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV4 multicast route-policy out'] = collect3_if_config_rcmd_outputs[2].split('route-policy ')[2].splitlines()[0].split()[0].strip()
                                except: pass

                        if USE_IPV6 and interface_data['bgp'].get('IPV6 use neighbor-group'):
                            interface_warning_data['bgp'] = collections.OrderedDict()
                            interface_warning_data['bgp']['IPV6 address-family'] = []
                            try:
                                if 'address-family ipv6 unicast' in collect3_if_config_rcmd_outputs[3]:
                                    interface_warning_data['bgp']['IPV6 address-family'].append('unicast')
                            except: pass

                            try:
                                if 'address-family ipv6 multicast' in collect3_if_config_rcmd_outputs[3]:
                                    interface_warning_data['bgp']['IPV6 address-family'].append('multicast')
                            except: pass

                            try: interface_data['bgp']['IPV6 remote-as'] = collect3_if_config_rcmd_outputs[3].split('remote-as ')[1].splitlines()[0].strip()
                            except: interface_data['bgp']['IPV6 remote-as'] = str()

                            if 'unicast' in interface_warning_data['bgp'].get('IPV6 address-family',str()):
                                try: interface_data['bgp']['IPV6 unicast route-policy in'] = collect3_if_config_rcmd_outputs[4].split('route-policy ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV6 unicast maximum-prefix'] = collect3_if_config_rcmd_outputs[4].split('maximum-prefix ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV6 unicast route-policy out'] = collect3_if_config_rcmd_outputs[4].split('route-policy ')[2].splitlines()[0].split()[0].strip()
                                except: pass

                            if 'multicast' in interface_warning_data['bgp'].get('IPV6 address-family',str()):
                                try: interface_data['bgp']['IPV6 multicast route-policy in'] = collect3_if_config_rcmd_outputs[5].split('route-policy ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV6 multicast maximum-prefix'] = collect3_if_config_rcmd_outputs[5].split('maximum-prefix ')[1].splitlines()[0].split()[0].strip()
                                except: pass

                                try: interface_data['bgp']['IPV6 multicast route-policy out'] = collect3_if_config_rcmd_outputs[5].split('route-policy ')[2].splitlines()[0].split()[0].strip()
                                except: pass

                    elif RCMD.router_type == 'juniper':
                        interface_data['bgp']['IPV4 unicast_route-policy_in'] = []
                        for line in collect3_if_config_rcmd_outputs[0].splitlines():
                            if 'import ' in line:
                                try: interface_data['bgp']['IPV4 unicast_route-policy_in'].append(line.split('import ')[1].split()[0])
                                except: pass

                        interface_data['bgp']['IPV4 unicast_route-policy_out'] = []
                        for line in collect3_if_config_rcmd_outputs[0].splitlines():
                            if 'export ' in line:
                                try: interface_data['bgp']['IPV4 unicast_route-policy_out'].append(line.split('export ')[1].split()[0])
                                except: pass

                        try: interface_data['bgp']['IPV4 unicast prefix-limit maximum'] = collect3_if_config_rcmd_outputs[0].split('unicast prefix-limit maximum ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 Received/maximum prefixes percent'] = 100 * (float(interface_data['bgp']['IPV4 Received prefixes']) / float(interface_data['bgp']['IPV4 unicast prefix-limit maximum']))
                        except: pass

                        try: interface_data['bgp']['IPV4 unicast prefix-limit teardown'] = collect3_if_config_rcmd_outputs[0].split('unicast prefix-limit teardown ')[1].split()[0]
                        except: pass

                        try: interface_data['bgp']['IPV4 peer-as'] = collect3_if_config_rcmd_outputs[0].split('peer-as ')[1].split()[0]
                        except: pass

                        interface_data['bgp']['IPV4 neighbors'] = []
                        for line in collect3_if_config_rcmd_outputs[0].splitlines():
                            if 'neighbor ' in line:
                                try: interface_data['bgp']['IPV4 neighbors'].append(line.split('neighbor ')[1].split()[0])
                                except: pass

                        # interface_data['IPV4 multipath'] = True if 'multipath' in collect3_if_config_rcmd_outputs[0] else str()

                        if USE_IPV6 and interface_data['bgp'].get('IPV6 neighbor-group'):
                            interface_data['bgp']['IPV6 unicast_route-policy_in'] = []
                            for line in collect3_if_config_rcmd_outputs[1].splitlines():
                                if 'import ' in line:
                                    try: interface_data['bgp']['IPV6 unicast_route-policy_in'].append(line.split('import ')[1].split()[0])
                                    except: pass

                            interface_data['bgp']['IPV6 unicast_route-policy_out'] = []
                            for line in collect3_if_config_rcmd_outputs[1].splitlines():
                                if 'export ' in line:
                                    try: interface_data['bgp']['IPV6 unicast_route-policy_out'].append(line.split('export ')[1].split()[0])
                                    except: pass

                            try: interface_data['bgp']['IPV6 unicast prefix-limit maximum'] = collect3_if_config_rcmd_outputs[1].split('unicast prefix-limit maximum ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 unicast prefix-limit teardown'] = collect3_if_config_rcmd_outputs[1].split('unicast prefix-limit teardown ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 peer-as'] = collect3_if_config_rcmd_outputs[1].split('peer-as ')[1].split()[0]
                            except: pass

                            interface_data['bgp']['IPV6 neighbors'] = []
                            for line in collect3_if_config_rcmd_outputs[1].splitlines():
                                if 'neighbor ' in line:
                                    try: interface_data['bgp']['IPV6 neighbors'].append(normalized_ipv6(line.split('neighbor ')[1].split()[0]))
                                    except: pass

                            # interface_data['IPV6 multipath'] = True if 'multipath' in collect3_if_config_rcmd_outputs[1] else str()

                    elif RCMD.router_type == 'huawei':
                        interface_data['bgp']['IPV4 unicast_route-policy_in'] = []
                        for line in collect3_if_config_rcmd_outputs[0].splitlines():
                            if '%s route-policy' % (interface_data['bgp'].get('IPV4 neighbor-group',str())) in line and 'import' in line:
                                try: interface_data['bgp']['IPV4 unicast_route-policy_in'].append(line.split('route-policy ')[1].split()[0])
                                except: pass

                        interface_data['bgp']['IPV4 unicast_route-policy_out'] = []
                        for line in collect3_if_config_rcmd_outputs[0].splitlines():
                            if '%s route-policy' % (interface_data['bgp'].get('IPV4 neighbor-group',str())) in line and 'export' in line:
                                try: interface_data['bgp']['IPV4 unicast_route-policy_out'].append(line.split('route-policy ')[1].split()[0])
                                except: pass

                        if USE_IPV6 and interface_data['bgp'].get('IPV6 neighbor-group'):
                            interface_data['bgp']['IPV6 unicast_route-policy_in'] = []
                            for line in collect3_if_config_rcmd_outputs[1].splitlines():
                                if '%s route-policy' % (interface_data['bgp'].get('IPV6 neighbor-group',str())) in line and 'import' in line:
                                    try: interface_data['bgp']['IPV6 unicast_route-policy_in'].append(line.split('route-policy ')[1].split()[0])
                                    except: pass

                            interface_data['bgp']['IPV6 unicast_route-policy_out'] = []
                            for line in collect3_if_config_rcmd_outputs[1].splitlines():
                                if '%s route-policy' % (interface_data['bgp'].get('IPV6 neighbor-group',str())) in line and 'export' in line:
                                    try: interface_data['bgp']['IPV6 unicast_route-policy_out'].append(line.split('route-policy ')[1].split()[0])
                                    except: pass

                    ###########################################################
                    ### def CUSTOMER_MODE - 4th DATA COLLECTION ###############
                    ###########################################################
                    collect4_if_data_rcmds = {
                        'cisco_ios':[
                            'show running-config route-policy DENY-ALL',
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 unicast route-policy in',str())) if interface_data['bgp'].get('IPV4 unicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 unicast route-policy out',str())) if interface_data['bgp'].get('IPV4 unicast route-policy out') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 multicast route-policy in',str())) if interface_data['bgp'].get('IPV4 multicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 multicast route-policy out',str())) if interface_data['bgp'].get('IPV4 multicast route-policy out') else str(),

                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 unicast route-policy in',str())) if interface_data['bgp'].get('IPV6 unicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 unicast route-policy out',str())) if interface_data['bgp'].get('IPV6 unicast route-policy out') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 multicast route-policy in',str())) if interface_data['bgp'].get('IPV6 multicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 multicast route-policy out',str())) if interface_data['bgp'].get('IPV6 multicast route-policy out') else str(),
                         ],

                        'cisco_xr':[
                            'show running-config route-policy DENY-ALL',
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 unicast route-policy in',str())) if interface_data['bgp'].get('IPV4 unicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 unicast route-policy out',str())) if interface_data['bgp'].get('IPV4 unicast route-policy out') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 multicast route-policy in',str())) if interface_data['bgp'].get('IPV4 multicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV4 multicast route-policy out',str())) if interface_data['bgp'].get('IPV4 multicast route-policy out') else str(),

                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 unicast route-policy in',str())) if interface_data['bgp'].get('IPV6 unicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 unicast route-policy out',str())) if interface_data['bgp'].get('IPV6 unicast route-policy out') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 multicast route-policy in',str())) if interface_data['bgp'].get('IPV6 multicast route-policy in') else str(),
                            'show running-config route-policy %s' % (interface_data['bgp'].get('IPV6 multicast route-policy out',str())) if interface_data['bgp'].get('IPV6 multicast route-policy out') else str(),                         ],

                        'juniper': [
                            'show configuration policy-options policy-statement DENY-ALL',
                        ],

                        'huawei': [
                            'display route-policy DENY-ALL',
                        ]
                    }

                    for policy in interface_data['bgp'].get('IPV4 unicast_route-policy_in',[]):
                        collect4_if_data_rcmds['juniper'].append('show configuration policy-options policy-statement %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV4 unicast_route-policy_out',[]):
                        collect4_if_data_rcmds['juniper'].append('show configuration policy-options policy-statement %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV6 unicast_route-policy_in',[]):
                        collect4_if_data_rcmds['juniper'].append('show configuration policy-options policy-statement %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV6 unicast_route-policy_out',[]):
                        collect4_if_data_rcmds['juniper'].append('show configuration policy-options policy-statement %s' % (policy))


                    for policy in interface_data['bgp'].get('IPV4 unicast_route-policy_in',[]):
                        collect4_if_data_rcmds['huawei'].append('display route-policy %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV4 unicast_route-policy_out',[]):
                        collect4_if_data_rcmds['huawei'].append('display route-policy %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV6 unicast_route-policy_in',[]):
                        collect4_if_data_rcmds['huawei'].append('display route-policy %s' % (policy))

                    for policy in interface_data['bgp'].get('IPV6 unicast_route-policy_out',[]):
                        collect4_if_data_rcmds['huawei'].append('display route-policy %s' % (policy))

                    collect4_if_config_rcmd_outputs = RCMD.run_commands(collect4_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        for cmd_in,cmd_output in zip(collect4_if_data_rcmds, collect4_if_config_rcmd_outputs):
                            if 'NO SUCH CONFIGURATION ITEM' in cmd_output.upper():
                                interface_data[cmd_in] = str()

                    elif RCMD.router_type == 'juniper':
                        for cmd_in,cmd_output in zip(collect4_if_data_rcmds, collect4_if_config_rcmd_outputs):
                            if not ';' in cmd_output.upper():
                                interface_data[cmd_in] = str()

                    elif RCMD.router_type == 'huawei':
                        for cmd_in,cmd_output in zip(collect4_if_data_rcmds, collect4_if_config_rcmd_outputs):
                            if not ':' in cmd_output.upper():
                                interface_data[cmd_in] = str()


                    ###########################################################
                    ### def CUSTOMER_MODE - 5th DATA COLLECTION ###############
                    ###########################################################
                    collect5_if_data_rcmds = {
                        'cisco_ios':[
                            'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            'show bgp neighbor %s advertised-count' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                         ],

                        'cisco_xr':[
                            'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                            'show bgp neighbor %s advertised-count' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                         ],

                        'juniper': [
                            'show bgp group %s detail' % (interface_data['bgp'].get('IPV4 neighbor-group')) if interface_data['bgp'].get('IPV4 neighbor-group') else str(),
                        ],

                        'huawei': [
                            'display bgp group %s' % (interface_data['bgp'].get('IPV4 neighbor-group')) if interface_data['bgp'].get('IPV4 neighbor-group') else str(),
                            'display bgp peer %s verbose' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')) if interface_data['interface_data'].get('IPV4_bgp_neighbor') else str(),
                        ]
                    }

                    collect5_if_config_rcmd_outputs = RCMD.run_commands(collect5_if_data_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                        try: interface_data['bgp']['IPV4 BGP state'] = collect5_if_config_rcmd_outputs[0].split('BGP state =')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 BGP state'] = str()

                        try: interface_data['bgp']['IPV4 Policy for incoming advertisements'] = collect5_if_config_rcmd_outputs[0].split('Policy for incoming advertisements is ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 Policy for incoming advertisements'] = str()

                        try: interface_data['bgp']['IPV4 Policy for outgoing advertisements'] = collect5_if_config_rcmd_outputs[0].split('Policy for outgoing advertisements is ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 Policy for outgoing advertisements'] = str()

                        try: interface_data['bgp']['IPV4 accepted prefixes'] = collect5_if_config_rcmd_outputs[0].split('accepted prefixes,')[0].splitlines()[-1].split()[0]
                        except: interface_data['bgp']['IPV4 accepted prefixes'] = str()

                        try: interface_data['bgp']['IPV4 accepted/max prefixes percent'] = 100 * (float(interface_data['bgp']['IPV4 accepted prefixes']) / float(interface_data['bgp']['IPV4 unicast maximum-prefix']))
                        except: pass

                        try: interface_data['bgp']['IPV4 bestpaths'] = collect5_if_config_rcmd_outputs[0].split('are bestpaths')[0].splitlines()[-1].split()[-1]
                        except: interface_data['bgp']['IPV4 bestpaths'] = str()

                        try: interface_data['bgp']['IPV4 No of prefixes Advertised'] = collect5_if_config_rcmd_outputs[1].split('No of prefixes Advertised:')[1].split()[0]
                        except: interface_data['bgp']['IPV4 No of prefixes Advertised'] = str()

                    elif RCMD.router_type == 'juniper':
                        ### BUG - MORE GROUPS CAN BE DISPLAYED !!! ###
                        try: interface_data['bgp']['IPV4 bgp group Export'] = collect5_if_config_rcmd_outputs[0].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Export: [ ')[1].splitlines()[0].replace(']','').strip().split()
                        except: interface_data['bgp']['IPV4 bgp group Export'] = str()

                        try: interface_data['bgp']['IPV4 bgp group Total peers'] = collect5_if_config_rcmd_outputs[0].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Total peers: ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 bgp group Total peers'] = str()

                        try: interface_data['bgp']['IPV4 bgp group Established'] = collect5_if_config_rcmd_outputs[0].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Established: ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 bgp group Established'] = str()

                        interface_data['bgp']['IPV4 bgp group Peers'] = []

                        try: lines = collect5_if_config_rcmd_outputs[0].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Established: ')[1].strip().splitlines()
                        except: lines = []

                        for line in lines:
                            if '.' in line:
                                if 'inet' in line or 'Route Queue Timer' in line: break
                                interface_data['bgp']['IPV4 bgp group Peers'].append(str(line).strip())


                    elif RCMD.router_type == 'huawei':
                        try: interface_data['bgp']['IPV4 remote AS'] = collect5_if_config_rcmd_outputs[1].split('remote AS ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 remote AS'] = str()

                        try: interface_data['bgp']['IPV4 Remote router ID'] = collect5_if_config_rcmd_outputs[1].split('Remote router ID ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 Remote router ID'] = str()

                        try: interface_data['bgp']['IPV4 BGP current state'] = collect5_if_config_rcmd_outputs[1].split('BGP current state: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 BGP current state'] = str()

                        try: interface_data['bgp']['IPV4 BGP Up for'] = collect5_if_config_rcmd_outputs[1].split('Up for ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 BGP Up for'] = str()

                        try: interface_data['bgp']['IPV4 Received total routes'] = collect5_if_config_rcmd_outputs[1].split('Received total routes: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Received total routes'] = str()

                        try: interface_data['bgp']['IPV4 Advertised total routes'] = collect5_if_config_rcmd_outputs[1].split('Advertised total routes: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Advertised total routes'] = str()

                        try: interface_data['bgp']['IPV4 Authentication type configured'] = collect5_if_config_rcmd_outputs[1].split('Authentication type configured: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Authentication type configured'] = str()

                        try: interface_data['bgp']['IPV4 Maximum allowed route limit'] = collect5_if_config_rcmd_outputs[1].split('Maximum allowed route limit: ')[1].split()[0]
                        except: interface_data['bgp']['IPV4 Maximum allowed route limit'] = str()

                        try: interface_data['bgp']['IPV4 Received/maximum total routes percent'] = 100 * (float(interface_data['bgp']['IPV4 Received total routes']) / float(interface_data['bgp']['IPV4 Maximum allowed route limit']))
                        except: pass

                        try: interface_data['bgp']['IPV4 Threshold'] = collect5_if_config_rcmd_outputs[1].split('Threshold: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Threshold'] = str()

                        try: interface_data['bgp']['IPV4 Parameter'] = collect5_if_config_rcmd_outputs[1].split(', Parameter: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Parameter'] = str()

                        try: interface_data['bgp']['IPV4 Import prefix list is'] = collect5_if_config_rcmd_outputs[1].split('Import prefix list is: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Import prefix list is'] = str()

                        try: interface_data['bgp']['IPV4 Export prefix list is:'] = collect5_if_config_rcmd_outputs[1].split('Export prefix list is: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Export prefix list is'] = str()

                        try: interface_data['bgp']['IPV4 Export prefix list is:'] = collect5_if_config_rcmd_outputs[1].split('Export prefix list is: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Export prefix list is'] = str()

                        try: interface_data['bgp']['IPV4 Import route policy is'] = collect5_if_config_rcmd_outputs[1].split('Import route policy is: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Import route policy is'] = str()

                        try: interface_data['bgp']['IPV4 Export route policy is'] = collect5_if_config_rcmd_outputs[1].split('Export route policy is: ')[1].split()[0].replace(',','')
                        except: interface_data['bgp']['IPV4 Export route policy is'] = str()


                    ###########################################################
                    ### def CUSTOMER_MODE - 6th DATA COLLECTION ###############
                    ###########################################################
                    if interface_warning_data.get('IPV6_addr_rem'):
                        collect6_if_data_rcmds = {
                            'cisco_ios':[
                                'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                                'show bgp neighbor %s advertised-count' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                             ],

                            'cisco_xr':[
                                'show bgp neighbor %s' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                                'show bgp neighbor %s advertised-count' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                             ],

                            'juniper': [
                                'show bgp group %s' % (interface_data['bgp'].get('IPV6 neighbor-group')) if interface_data['bgp'].get('IPV6 neighbor-group') else str(),
                                'show bgp group %s detail' % (interface_data['bgp'].get('IPV6 neighbor-group')) if interface_data['bgp'].get('IPV6 neighbor-group') else str(),
                            ],

                            'huawei': [
                                'display bgp group %s' % (interface_data['bgp'].get('IPV6 neighbor-group')) if interface_data['bgp'].get('IPV6 neighbor-group') else str(),
                                'display bgp peer %s verbose' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')) if interface_data['interface_data'].get('IPV6_bgp_neighbor') else str(),
                            ]
                        }

                        collect6_if_config_rcmd_outputs = RCMD.run_commands(collect6_if_data_rcmds, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                            try: interface_data['bgp']['IPV6 BGP state'] = collect6_if_config_rcmd_outputs[0].split('BGP state =')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 BGP state'] = str()

                            try: interface_data['bgp']['IPV6 Policy for incoming advertisements'] = collect6_if_config_rcmd_outputs[0].split('Policy for incoming advertisements is ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 Policy for incoming advertisements'] = str()

                            try: interface_data['bgp']['IPV6 Policy for outgoing advertisements'] = collect6_if_config_rcmd_outputs[0].split('Policy for outgoing advertisements is ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 Policy for outgoing advertisements'] = str()

                            try: interface_data['bgp']['IPV6 accepted prefixes'] = collect6_if_config_rcmd_outputs[0].split('accepted prefixes,')[0].splitlines()[-1].split()[0]
                            except: interface_data['bgp']['IPV6 accepted prefixes'] = str()

                            try: interface_data['bgp']['IPV6 bestpaths'] = collect6_if_config_rcmd_outputs[0].split('are bestpaths')[0].splitlines()[-1].split()[-1]
                            except: interface_data['bgp']['IPV6 bestpaths'] = str()

                            try: interface_data['bgp']['IPV6 No of prefixes Advertised'] = collect6_if_config_rcmd_outputs[1].split('No of prefixes Advertised:')[1].split()[0]
                            except: interface_data['bgp']['IPV6 No of prefixes Advertised'] = str()

                        elif RCMD.router_type == 'juniper':
                            try: interface_data['bgp']['IPV6 bgp group Name'] = collect6_if_config_rcmd_outputs[0].split('Name: ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 bgp group Name'] = str()

                            try: interface_data['bgp']['IPV6 bgp group Export'] = collect6_if_config_rcmd_outputs[0].split('Export: [ ')[1].splitlines()[0].replace(']','').strip().split()
                            except: interface_data['bgp']['IPV6 bgp group Export'] = str()

                            try: interface_data['bgp']['IPV6 bgp group Total peers'] = collect6_if_config_rcmd_outputs[0].split('Total peers: ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 bgp group Total peers'] = str()

                            try: interface_data['bgp']['IPV6 bgp group Established'] = collect6_if_config_rcmd_outputs[0].split('Established: ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 bgp group Established'] = str()

                            try: interface_data['bgp']['IPV6 bgp group Export'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Export: [ ')[1].splitlines()[0].replace(']','').strip().split()
                            except: pass

                            try: interface_data['bgp']['IPV6 bgp group Total peers'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Total peers: ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 bgp group Established'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV4 neighbor-group']))[1].split('Established: ')[1].split()[0]
                            except: pass

                            interface_data['bgp']['IPV6 bgp group Peers'] = []

                            try: lines = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Established: ')[1].strip().splitlines()
                            except: lines = []

                            for line in lines:
                                if ':' in line:
                                    if 'inet6' in line or 'Route Queue Timer' in line: break
                                    interface_data['bgp']['IPV6 bgp group Peers'].append(str(line).strip())

                            if interface_data['bgp']['IPV6 bgp group Peers'] == []:
                                del interface_data['bgp']['IPV6 bgp group Peers']

                            try: interface_data['bgp']['IPV6 Active prefixes'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Active prefixes: ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 Received prefixes'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Received prefixes: ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 Accepted prefixes'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Accepted prefixes: ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 Suppressed due to damping'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Suppressed due to damping: ')[1].split()[0]
                            except: pass

                            try: interface_data['bgp']['IPV6 Advertised prefixes'] = collect6_if_config_rcmd_outputs[1].split('Name: %s ' % (interface_data['bgp']['IPV6 neighbor-group']))[1].split('Advertised prefixes: ')[1].split()[0]
                            except: pass


                        elif RCMD.router_type == 'huawei':
                            try: interface_data['bgp']['IPV6 remote AS'] = collect6_if_config_rcmd_outputs[1].split('remote AS ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 remote AS'] = str()

                            try: interface_data['bgp']['IPV6 Remote router ID'] = collect6_if_config_rcmd_outputs[1].split('Remote router ID ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 Remote router ID'] = str()

                            try: interface_data['bgp']['IPV6 BGP current state'] = collect6_if_config_rcmd_outputs[1].split('BGP current state: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 BGP current state'] = str()

                            try: interface_data['bgp']['IPV6 BGP Up for'] = collect6_if_config_rcmd_outputs[1].split('Up for ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 BGP Up for'] = str()

                            try: interface_data['bgp']['IPV6 Received total routes'] = collect6_if_config_rcmd_outputs[1].split('Received total routes: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Received total routes'] = str()

                            try: interface_data['bgp']['IPV6 Advertised total routes'] = collect6_if_config_rcmd_outputs[1].split('Advertised total routes: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Advertised total routes'] = str()

                            try: interface_data['bgp']['IPV6 Authentication type configured'] = collect6_if_config_rcmd_outputs[1].split('Authentication type configured: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Authentication type configured'] = str()

                            try: interface_data['bgp']['IPV6 Maximum allowed route limit'] = collect6_if_config_rcmd_outputs[1].split('Maximum allowed route limit: ')[1].split()[0]
                            except: interface_data['bgp']['IPV6 Maximum allowed route limit'] = str()

                            try: interface_data['bgp']['IPV6 Threshold'] = collect6_if_config_rcmd_outputs[1].split('Threshold: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Threshold'] = str()

                            try: interface_data['bgp']['IPV6 Parameter'] = collect6_if_config_rcmd_outputs[1].split(', Parameter: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Parameter'] = str()

                            try: interface_data['bgp']['IPV6 Import prefix list is'] = collect6_if_config_rcmd_outputs[1].split('Import prefix list is: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Import prefix list is'] = str()

                            try: interface_data['bgp']['IPV6 Export prefix list is:'] = collect6_if_config_rcmd_outputs[1].split('Export prefix list is: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Export prefix list is'] = str()

                            try: interface_data['bgp']['IPV6 Export prefix list is:'] = collect6_if_config_rcmd_outputs[1].split('Export prefix list is: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Export prefix list is'] = str()

                            try: interface_data['bgp']['IPV6 Import route policy is'] = collect6_if_config_rcmd_outputs[1].split('Import route policy is: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Import route policy is'] = str()

                            try: interface_data['bgp']['IPV6 Export route policy is'] = collect6_if_config_rcmd_outputs[1].split('Export route policy is: ')[1].split()[0].replace(',','')
                            except: interface_data['bgp']['IPV6 Export route policy is'] = str()


                    ###########################################################
                    ### def CUSTOMER_MODE - 7th DATA COLLECTION ###############
                    ###########################################################
                    ### show run router static | i <bgp-neighbor>/32 <!interface-id!> <!ipv4-addr-rem!> tag 2
                    ### show run router static | i IPV4_addr_rem_from_ASN/32 interface_id IPV4_addr_rem_from_DESCRIPTION tag 2
                    if IPV4_STATIC_ROUTING and interface_data['interface_data'].get('IPV4_bgp_neighbor') and interface_data['interface_data'].get('IPV4_addr_rem'):
                        collect7_if_data_rcmds = {
                            'cisco_ios':[
                             ],

                            'cisco_xr':[
                             ],

                            'juniper': [
                             ],

                            'huawei': [
                            ]
                        }

                        collect7_if_data_rcmds['cisco_ios'].append('show run router static | i %s/32' % (interface_data['interface_data'].get('IPV4_bgp_neighbor')))
                        collect7_if_data_rcmds['cisco_xr'].append('show run router static | i %s/32'  % (interface_data['interface_data'].get('IPV4_bgp_neighbor')))

                        collect7_if_config_rcmd_outputs = RCMD.run_commands(collect7_if_data_rcmds, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                            route_exists = True

                            if str(interface_data['interface_data'].get('IPV4_bgp_neighbor')) in str(collect7_if_config_rcmd_outputs[0]): pass
                            else: route_exists = str()

                            if str("%s tag 2" % (interface_data['interface_data'].get('IPV4_addr_rem'))) in str(collect7_if_config_rcmd_outputs[0]): pass
                            else: route_exists = str()

                            interface_data['interface_data'][collect7_if_data_rcmds.get('cisco_xr')[0]] = route_exists


                    ###########################################################
                    ### def CUSTOMER_MODE - 8th DATA COLLECTION ###############
                    ###########################################################
                    if IPV6_STATIC_ROUTING and interface_data['interface_data'].get('IPV6_bgp_neighbor') and interface_warning_data['interface_data'].get('IPV6_addr_rem'):
                        collect8_if_data_rcmds = {
                            'cisco_ios':[
                             ],

                            'cisco_xr':[
                             ],

                            'juniper': [
                             ],

                            'huawei': [
                            ]
                        }

                        collect8_if_data_rcmds['cisco_ios'].append('show run router static | i %s/128' % (interface_data['interface_data'].get('IPV6_bgp_neighbor')))
                        collect8_if_data_rcmds['cisco_xr'].append('show run router static | i %s/128'  % (interface_data['interface_data'].get('IPV6_bgp_neighbor')))

                        collect8_if_config_rcmd_outputs = RCMD.run_commands(collect8_if_data_rcmds, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                            route_exists = True
                            if str(interface_data['interface_data'].get('IPV6_bgp_neighbor')) in str(collect8_if_config_rcmd_outputs[0]): pass
                            else: route_exists = str()

                            if str("%s tag 2" % (interface_warning_data['interface_data'].get('IPV6_addr_rem'))) in str(collect8_if_config_rcmd_outputs[0]): pass
                            else: route_exists = str()

                            interface_data['interface_data'][collect8_if_data_rcmds.get('cisco_xr')[0]] = route_exists

                ### def INTENDED MTU CALCULATIONS #############################
                ping_size, ping_size_v6 = 0, 0

                ### L2 PING HEADER ############################################
                if RCMD.router_type == 'juniper' or RCMD.router_type == 'cisco_xr':
                    L2_ping_header, L2_ping_header_v6 = 14, 14
                else: L2_ping_header, L2_ping_header_v6 = 0, 0

                ### L3 PING HEADER ############################################
                if RCMD.router_type == 'huawei' or RCMD.router_type == 'juniper':
                    ### PING6(4490=40+8+4442 bytes) ###
                    L3_ping_header, L3_ping_header_v6 = 28, 48
                else: L3_ping_header, L3_ping_header_v6 = 0, 0

                interface_warning_data['interface_data']['IPV4 L2 ping header size'] = L2_ping_header
                interface_warning_data['interface_data']['IPV6 L2 ping header size'] = L2_ping_header_v6
                interface_warning_data['interface_data']['IPV4 L3 ping header size'] = L3_ping_header
                interface_warning_data['interface_data']['IPV6 L3 ping header size'] = L3_ping_header_v6

                if interface_warning_data['interface_data'].get('IPV4 MTU set'):
                    if RCMD.router_type == 'cisco_xr':
                        ping_size = (int(interface_warning_data['interface_data'].get('IPV4 MTU set')) - L3_ping_header - L2_ping_header) if (int(interface_warning_data['interface_data'].get('IPV4 MTU set')) - L3_ping_header - L2_ping_header) > 0 else 1
                    else:
                        ping_size = (int(interface_warning_data['interface_data'].get('IPV4 MTU set')) - L3_ping_header) if (int(interface_warning_data['interface_data'].get('IPV4 MTU set')) - L3_ping_header) > 0 else 1

                    if interface_warning_data['interface_data'].get('IPV6 MTU set'):
                        if RCMD.router_type == 'cisco_xr':
                            ping_size_v6 = (int(interface_warning_data['interface_data'].get('IPV6 MTU set')) - L3_ping_header_v6 - L2_ping_header) if (int(interface_warning_data['interface_data'].get('IPV6 MTU set')) - L3_ping_header_v6 - L2_ping_header) > 0 else 1
                        else:
                            ping_size_v6 = (int(interface_warning_data['interface_data'].get('IPV6 MTU set')) - L3_ping_header_v6) if (int(interface_warning_data['interface_data'].get('IPV6 MTU set')) - L3_ping_header_v6) > 0 else 1

                elif interface_warning_data['interface_data'].get('MTU_interface_configured'):
                    ping_size = (int(interface_warning_data['interface_data'].get('MTU_interface_configured')) - L3_ping_header - L2_ping_header) if (int(interface_warning_data['interface_data'].get('MTU_interface_configured')) - L3_ping_header - L2_ping_header) > 0 else 1
                    ping_size_v6 = (int(interface_warning_data['interface_data'].get('MTU_interface_configured')) - L3_ping_header_v6 - L2_ping_header_v6) if (int(interface_warning_data['interface_data'].get('MTU_interface_configured')) - L3_ping_header_v6 - L2_ping_header_v6) > 0 else 1

                if CUSTOMER_MODE:
                    #ping_size, ping_size_v6 = 1500, 1500
                    ping_size, ping_size_v6 = 1500 - L3_ping_header , 1500 - L3_ping_header_v6

                if not PING_ONLY:
                    if ping_size <= 1:
                        CGI_CLI.uprint('\nIPV4 PING SIZE CALCULATION WARNING!', color = 'orange', timestamp = 'no')
                    if ping_size_v6 <= 1 and USE_IPV6:
                        CGI_CLI.uprint('\nIPV6 PING SIZE CALCULATION WARNING!', color = 'orange', timestamp = 'no')

                if BB_MODE:
                    if ping_size <= 1:
                        ping_size = 4484 - L3_ping_header - L2_ping_header
                    if ping_size_v6 <= 1 and USE_IPV6:
                        ping_size_v6 = 4484 - L3_ping_header_v6 - L2_ping_header_v6

                interface_warning_data['interface_data']['IPV4 intended ping size'] = copy.deepcopy(ping_size)
                interface_warning_data['interface_data']['IPV6 intended ping size'] = copy.deepcopy(ping_size_v6)

                if ping_size <= 1:
                    CGI_CLI.uprint('\nIPV4 PING SIZE CALCULATION WARNING!', color = 'orange', timestamp = 'no')
                if ping_size_v6 <= 1 and USE_IPV6:
                    CGI_CLI.uprint('\nIPV6 PING SIZE CALCULATION WARNING!', color = 'orange', timestamp = 'no')


                if IPV4_STATIC_ROUTING:
                    ### def NEXT HOP FIRST PINGv4 COMMAND LIST ############
                    try: ping_source = interface_data['bgp']['IPV4 Local host']
                    except: ping_source = None

                    if ping_source and interface_data['interface_data'].get('IPV4_bgp_neighbor'):
                        interface_data['interface_statistics']['IPV4 next hop ping percent success from localhost'] = str(do_ping( \
                            address = interface_data['interface_data'].get('IPV4_bgp_neighbor',str()), \
                            mtu = 100, count = 5, ipv6 = None, \
                            source = ping_source))

                        interface_warning_data['interface_statistics']['IPV4 next hop ping percent success on intended ping size from localhost'] = str(do_ping( \
                            address = interface_data['interface_data'].get('IPV4_bgp_neighbor',str()), \
                            mtu = interface_warning_data['interface_data']['IPV4 intended ping size'], count = 5, ipv6 = None, \
                            source = ping_source))

                if IPV6_STATIC_ROUTING:
                    ### def NEXT HOP FIRST PINGv6 COMMAND LIST ############
                    try: ping_source_v6 = interface_data['bgp']['IPV6 Local host']
                    except: ping_source_v6 = None

                    if ping_source_v6 and interface_data['interface_data'].get('IPV6_bgp_neighbor'):
                        interface_warning_data['interface_statistics']['IPV6 next hop ping percent success from localhost'] = str(do_ping( \
                            address = interface_data['interface_data'].get('IPV6_bgp_neighbor',str()), \
                            mtu = 100, count = 5, ipv6 = True, \
                            source = ping_source_v6))

                        interface_warning_data['interface_statistics']['IPV6 next hop ping percent success on intended ping size from localhost'] = str(do_ping( \
                            address = interface_data['interface_data'].get('IPV6_bgp_neighbor',str()), \
                            mtu = interface_warning_data['interface_data']['IPV6 intended ping size'], count = 5, ipv6 = True, \
                            source = ping_source_v6))


                ### def FIRST PINGv4 COMMAND LIST #############################
                if interface_data['interface_data'].get('IPV4_addr_rem',str()):
                    interface_data['interface_statistics']['IPV4 ping percent success'] = str(do_ping( \
                        address = interface_data['interface_data'].get('IPV4_addr_rem',str()), \
                        mtu = 100, count = 5, ipv6 = None, \
                        source = interface_data['interface_data'].get('IPV4_addr_loc',str())))

                    interface_warning_data['interface_statistics']['IPV4 ping percent success on intended ping size'] = str(do_ping( \
                        address = interface_data['interface_data'].get('IPV4_addr_rem',str()), \
                        mtu = interface_warning_data['interface_data']['IPV4 intended ping size'], count = 5, ipv6 = None, \
                        source = interface_data['interface_data'].get('IPV4_addr_loc',str())))


                ### def FIRST PINGv6 COMMAND LIST ###################################
                if USE_IPV6:
                    if interface_warning_data['interface_data'].get('IPV6_addr_rem',str()):
                        interface_warning_data['interface_statistics']['IPV6 ping percent success'] = str(do_ping( \
                            address = interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), \
                            mtu = 100, count = 5, ipv6 = True, \
                            source = interface_data['interface_data'].get('IPV6_addr_loc',str())))

                        interface_warning_data['interface_statistics']['IPV6 ping percent success on intended ping size'] = str(do_ping( \
                            address = interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), \
                            mtu = interface_warning_data['interface_data']['IPV6 intended ping size'], count = 5, ipv6 = True, \
                            source = interface_data['interface_data'].get('IPV6_addr_loc',str())))

                ### def FIND MAX MTU ##########################################
                if PING_ONLY:
                    max_pingsize_ipv4, max_pingsize_ipv6 = 0, 0
                    if float(interface_data['interface_statistics'].get('IPV4 ping percent success','0')) > 0:
                        if interface_data['interface_data'].get('IPV4_addr_rem',str()):
                            max_pingsize_ipv4 = find_max_pingsize(interface_data['interface_data'].get('IPV4_addr_rem',str()), max_mtu = 9300, \
                                source = interface_data['interface_data'].get('IPV4_addr_loc',str()))
                            interface_data['interface_statistics']['IPV4 max working ping size'] = str(max_pingsize_ipv4)

                    if float(interface_warning_data['interface_statistics'].get('IPV6 ping percent success','0')) > 0:
                        if interface_warning_data['interface_data'].get('IPV6_addr_rem',str()):
                            max_pingsize_ipv6 = find_max_pingsize(interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), ipv6 = True, \
                                source = interface_data['interface_data'].get('IPV6_addr_loc',str()))
                            interface_data['interface_statistics']['IPV6 max working ping size'] = str(max_pingsize_ipv6)

                    if IPV4_STATIC_ROUTING:
                        try: ping_source = interface_data['bgp']['IPV4 Local host']
                        except: ping_source = None

                        if ping_source:
                            ### DO "THOUSANDS" NEXT HOP PING ON MAX WORKING PING SIZE #
                            if float(interface_data['interface_statistics'].get('IPV4 max working ping size', 0)) > 0:
                                interface_data['interface_statistics']['IPV4 next hop %spings percent success on max working ping size from localhost' % (ping_counts)] = str(\
                                    do_ping(address = interface_data['interface_data'].get('IPV4_bgp_neighbor',str()), \
                                        mtu = interface_data['interface_data'].get('IPV4 max working ping size'), \
                                        count = ping_counts, ipv6 = None,
                                        source = ping_source))

                    if IPV6_STATIC_ROUTING:
                        try: ping_source_v6 = interface_data['bgp']['IPV6 Local host']
                        except: ping_source_v6 = None

                        if ping_source_v6:
                            if float(interface_data['interface_statistics'].get('IPV6 max working ping size', 0)) > 0:
                                interface_warning_data['interface_statistics']['IPV6 next hop %spings percent success on max working ping size from localhost' % (ping_counts)] = str(\
                                    do_ping(address = interface_data['interface_data'].get('IPV6_bgp_neighbor',str()), \
                                        mtu = interface_data['interface_data'].get('IPV6 max working ping size'), \
                                        count = ping_counts, ipv6 = True,
                                        source = ping_source))

                    ### def DO "THOUSANDS" PING ON MAX WORKING PING SIZE ######
                    if float(interface_data['interface_statistics'].get('IPV4 max working ping size', 0)) > 0:
                        interface_data['interface_statistics']['IPV4 %spings percent success on max working ping size' % (ping_counts)] = str(\
                            do_ping(address = interface_data['interface_data'].get('IPV4_addr_rem',str()), \
                                mtu = interface_data['interface_data'].get('IPV4 max working ping size'), \
                                count = ping_counts, ipv6 = None,
                                source = interface_data['interface_data'].get('IPV4_addr_loc',str())))

                    if float(interface_data['interface_statistics'].get('IPV6 max working ping size', 0)) > 0:
                        interface_warning_data['interface_statistics']['IPV6 %spings percent success on max working ping size' % (ping_counts)] = str(\
                            do_ping(address = interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), \
                                mtu = interface_data['interface_data'].get('IPV6 max working ping size'), \
                                count = ping_counts, ipv6 = True,
                                source = interface_data['interface_data'].get('IPV6_addr_loc',str())))


                if IPV4_STATIC_ROUTING:
                    try: ping_source = interface_data['bgp']['IPV4 Local host']
                    except: ping_source = None

                    if ping_source:
                        ### "THOUSANDS" NEXT HOP PINGs TEST ####################################
                        if not interface_data['interface_statistics'].get('IPV4 next hop %spings percent success on max working ping size from localhost' % (ping_counts)) \
                            and ping_counts and int(ping_counts) > 0:
                            if '100' in interface_warning_data['interface_statistics'].get('IPV4 next hop ping percent success on intended ping size',str()):
                                ### def NEXT HOP "THOUSANDS" PINGv4 MTU COMMAND LIST ###################
                                if interface_data['interface_data'].get('IPV4_bgp_neighbor',str()):

                                    interface_warning_data['interface_statistics']['IPV4 next hop %spings percent success on intended ping size from localhost' % (ping_counts)] = \
                                        str(do_ping(address = interface_data['interface_data'].get('IPV4_bgp_neighbor',str()), \
                                            mtu = interface_warning_data['interface_data']['IPV4 intended ping size'], count = ping_counts, ipv6 = None, \
                                            source = ping_source))

                            elif '100' in interface_data['interface_statistics'].get('IPV4 next hop ping percent success',str()):
                                ### def NEXT HOP "THOUSANDS" PINGv4 COMMAND LIST ###################
                                if interface_data['interface_data'].get('IPV4_bgp_neighbor',str()):

                                    interface_data['interface_statistics']['IPV4 next hop %spings percent success from localhost' % (ping_counts)] = \
                                        str(do_ping(address = interface_data['interface_data'].get('IPV4_bgp_neighbor',str()), \
                                            mtu = 100, count = ping_counts, ipv6 = None, \
                                            source = ping_source))

                if IPV6_STATIC_ROUTING:
                    try: ping_source_v6 = interface_data['bgp']['IPV6 Local host']
                    except: ping_source_v6 = None

                    if ping_source_v6:
                        if USE_IPV6 \
                            and not interface_warning_data['interface_statistics'].get('IPV6 next hop %spings percent success on max working ping size from localhost' % (ping_counts)):
                            if '100' in interface_warning_data['interface_statistics'].get('IPV6 ping percent success on intended ping size from localhost',str()):
                                ### def NEXT HOP "THOUSANDS" PINGv6 COMMAND LIST ###################
                                if interface_data['interface_data'].get('IPV6_bgp_neighbor',str()):

                                    interface_warning_data['interface_statistics']['IPV6 next hop %spings percent success on intended ping size from localhost' % (ping_counts)] = \
                                        str(do_ping(address = interface_data['interface_data'].get('IPV6_bgp_neighbor',str()), \
                                            mtu = interface_warning_data['interface_data']['IPV6 intended ping size'], count = ping_counts, ipv6 = True,
                                            source = ping_source_v6))

                            elif '100' in interface_warning_data['interface_statistics'].get('IPV6 next hopping percent success from localhost',str()):
                                ### def NEXT HOP "THOUSANDS" PINGv6 COMMAND LIST ###################
                                if interface_data['interface_data'].get('IPV6_bgp_neighbor',str()):

                                    interface_warning_data['interface_statistics']['IPV6 next hop %spings percent success from localhost' % (ping_counts)] = \
                                        str(do_ping(address = interface_data['interface_data'].get('IPV6_bgp_neighbor',str()), \
                                            mtu = 100, count = ping_counts, ipv6 = True, \
                                            source = ping_source_v6))


                ### "THOUSANDS" PINGs TEST ####################################
                if not interface_data['interface_statistics'].get('IPV4 %spings percent success on max working ping size' % (ping_counts)) \
                    and ping_counts and int(ping_counts) > 0:
                    if '100' in interface_warning_data['interface_statistics'].get('IPV4 ping percent success on intended ping size',str()):
                        ### def "THOUSANDS" PINGv4 MTU COMMAND LIST ###################
                        if interface_data['interface_data'].get('IPV4_addr_rem',str()):

                            interface_warning_data['interface_statistics']['IPV4 %spings percent success on intended ping size' % (ping_counts)] = \
                                str(do_ping(address = interface_data['interface_data'].get('IPV4_addr_rem',str()), \
                                    mtu = interface_warning_data['interface_data']['IPV4 intended ping size'], count = ping_counts, ipv6 = None, \
                                    source = interface_data['interface_data'].get('IPV4_addr_loc',str())))

                    elif '100' in interface_data['interface_statistics'].get('IPV4 ping percent success',str()):
                        ### def "THOUSANDS" PINGv4 COMMAND LIST ###################
                        if interface_data['interface_data'].get('IPV4_addr_rem',str()):

                            interface_data['interface_statistics']['IPV4 %spings percent success' % (ping_counts)] = \
                                str(do_ping(address = interface_data['interface_data'].get('IPV4_addr_rem',str()), \
                                    mtu = 100, count = ping_counts, ipv6 = None, \
                                    source = interface_data['interface_data'].get('IPV4_addr_loc',str())))

                    if USE_IPV6 \
                        and not interface_warning_data['interface_statistics'].get('IPV6 %spings percent success on max working ping size' % (ping_counts)):
                        if '100' in interface_warning_data['interface_statistics'].get('IPV6 ping percent success on intended ping size',str()):
                            ### def "THOUSANDS" PINGv6 COMMAND LIST ###################
                            if interface_warning_data['interface_data'].get('IPV6_addr_rem',str()):

                                interface_warning_data['interface_statistics']['IPV6 %spings percent success on intended ping size' % (ping_counts)] = \
                                    str(do_ping(address = interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), \
                                        mtu = interface_warning_data['interface_data']['IPV6 intended ping size'], count = ping_counts, ipv6 = True,
                                        source = interface_data['interface_data'].get('IPV6_addr_loc',str())))

                        elif '100' in interface_warning_data['interface_statistics'].get('IPV6 ping percent success',str()):
                            ### def "THOUSANDS" PINGv6 COMMAND LIST ###################
                            if interface_warning_data['interface_data'].get('IPV6_addr_rem',str()):

                                interface_warning_data['interface_statistics']['IPV6 %spings percent success' % (ping_counts)] = \
                                    str(do_ping(address = interface_warning_data['interface_data'].get('IPV6_addr_rem',str()), \
                                        mtu = 100, count = ping_counts, ipv6 = True, \
                                        source = interface_data['interface_data'].get('IPV6_addr_loc',str())))

                if not precheck_mode:
                    ### def PARALLEL INTERFACES COMMAND LIST ##################
                    parrallel_interfaces_rcmds = collections.OrderedDict()
                    parrallel_interfaces_rcmds['cisco_ios'] = []
                    parrallel_interfaces_rcmds['cisco_xr'] = []
                    parrallel_interfaces_rcmds['juniper'] = []
                    parrallel_interfaces_rcmds['huawei'] = []
                    for parallel_interface in interface_data.get('parallel_interfaces',[]):
                        parrallel_interfaces_rcmds['cisco_ios'].append('sh isis interface %s' % (parallel_interface))
                        parrallel_interfaces_rcmds['cisco_xr'].append('sh isis interface %s' % (parallel_interface))
                        parrallel_interfaces_rcmds['juniper'].append('show isis interface %s' % (parallel_interface))
                        parrallel_interfaces_rcmds['huawei'].append('display isis interface %s verbose' % (parallel_interface))

                    parrallel_interfaces_outputs = RCMD.run_commands(parrallel_interfaces_rcmds, \
                        autoconfirm_mode = True, \
                        printall = printall)


                ###############################################################
                ### def INCREMENTAL ERROR CHECK AFTER PINGS ###################
                ###############################################################
                if ping_counts and int(ping_counts) > 0:
                    interface_traffic_errors_check(\
                        undotted_interface_id = undotted_interface_id, after_ping = True)

                ###############################################################
                ### PRINT \n AFTER COLLECTING OF DATA #########################
                ###############################################################
                CGI_CLI.uprint('\n', timestamp = 'no')

                if LOCAL_AS_NUMBER: pass
                else:
                    CGI_CLI.uprint("PROBLEM TO PARSE LOCAL AS NUMBER on device %s!\n" \
                        % (device), color = 'red', timestamp = 'no')

                ### def PRINT RESULTS PER INTERFACE ###########################
                CGI_CLI.uprint(interface_data, name = 'Collected data on Device %s' % (device), \
                    jsonprint = True, color = 'blue', timestamp = 'no', no_printall = not printall)
                CGI_CLI.uprint('\n', timestamp = 'no', no_printall = not printall)
                CGI_CLI.uprint(interface_warning_data, name = 'Collected WARNING data on Device %s' % (device), \
                    jsonprint = True, color = 'blue', timestamp = 'no', no_printall = not printall)
                CGI_CLI.uprint('\n', timestamp = 'no', no_printall = not printall)

                ### PRINT MAX WORKING PINGSIZE ################################
                if PING_ONLY:
                    if interface_data['interface_statistics'].get('IPV4 max working ping size'):
                        CGI_CLI.uprint('MAX. WORKING IPV4 PING SIZE = %s' % (str(interface_data['interface_statistics'].get('IPV4 max working ping size'))), \
                            timestamp = 'no', no_printall = not printall, color = 'blue', tag = 'h2')

                    if interface_data['interface_statistics'].get('IPV6 max working ping size'):
                        CGI_CLI.uprint('MAX. WORKING IPV6 PING SIZE = %s' % (str(interface_data['interface_statistics'].get('IPV6 max working ping size'))), \
                            timestamp = 'no', no_printall = not printall, color = 'blue', tag = 'h2')

                    CGI_CLI.uprint('\n', timestamp = 'no', no_printall = not printall)


                ### START OF CHECKS PER INTERFACE #############################
                check_interface_result_ok, check_warning_interface_result_ok = True, True
                CGI_CLI.uprint('RESULTS:', timestamp = 'no', tag = 'h1')

                if not interface_data['interface_data'].get('bundle_members_nr') \
                    and interface_data['interface_data'].get('LAG_member',str()) == 'yes':
                        CGI_CLI.uprint('This test is not intended for LAG member interface!', \
                            timestamp = 'no', color = 'red', tag = 'h2')

                ### def ALL - VOID ELEMENTS CHECK #############################
                None_elements = get_void_json_elements(interface_data, \
                    no_equal_sign = True, no_root_backslash = True)

                None_warning_elements = get_void_json_elements(interface_warning_data, \
                    no_equal_sign = True, no_root_backslash = True)

                if len(None_elements) > 0:
                    check_interface_result_ok = False
                    CGI_CLI.uprint('\nUNSET CONFIG ELEMENTS ON INTERFACE %s:' % \
                        (interface_data.get('interface_id')), tag = 'h3', color = 'red', timestamp = 'no')
                    CGI_CLI.uprint('\n'.join(None_elements), color = 'red', timestamp = 'no')
                    CGI_CLI.uprint('\n\n', timestamp = 'no')

                if CUSTOMER_MODE:
                    if len(None_warning_elements) > 0:
                        check_warning_interface_result_ok = False
                        CGI_CLI.uprint('\nUNSET WARNING CONFIG ELEMENTS ON INTERFACE %s:' % \
                            (interface_data.get('interface_id')), tag = 'h3', color = 'orange', timestamp = 'no')
                        CGI_CLI.uprint('\n'.join(None_warning_elements), color = 'orange', timestamp = 'no')
                        CGI_CLI.uprint('\n\n', timestamp = 'no')


                if BB_MODE and not precheck_mode:
                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr' and not interface_data['interface_data'].get('ipv4_metric') \
                        or RCMD.router_type == 'juniper' and not interface_data['interface_data'].get('L2 metric') \
                        or RCMD.router_type == 'huawei' and not interface_data['interface_data'].get('isis cost'):
                            check_interface_result_ok = False
                            CGI_CLI.uprint('Ipv4 L2 metric missing on Interface %s = NOT OK' % (interface_id), color = 'red')
                    elif RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr' and not interface_data['interface_data'].get('ipv6_metric') \
                        or RCMD.router_type == 'huawei' and not interface_data['interface_data'].get('isis ipv6 cost'):
                            if USE_IPV6 and BB_MODE:
                                check_interface_result_ok = False
                                CGI_CLI.uprint('Ipv6 L2 metric missing on Interface %s = NOT OK' % (interface_id), color = 'red')
                    else:
                        ### def BB - L2 METRIC POST-CHECK #####################
                        for parralel_cmd_output, parallel_interface in zip(parrallel_interfaces_outputs, interface_data['interface_data'].get('parallel_interfaces',[])):
                            L2_metric, ipv6_L2_metric = None, None
                            if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                                try: L2_metric = parralel_cmd_output.split(' Unicast Topology:')[1].split('Metric (L1/L2):')[1].split()[0].split('/')[1]
                                except: pass
                                try: ipv6_L2_metric = parralel_cmd_output.split('IPv6 Unicast Topology:')[1].split('Metric (L1/L2):')[1].split()[0].split('/')[1]
                                except: pass

                                if interface_data['interface_data'].get('ipv4_metric'):
                                    if L2_metric == '99999':
                                        CGI_CLI.logtofile("Ipv4 L2 Metric (99999) check on Interface %s = IGNORE\n" % (parallel_interface), ommit_timestamp = True)
                                    elif interface_data['interface_data'].get('ipv4_metric') != L2_metric:
                                        check_interface_result_ok = False
                                        CGI_CLI.uprint('Ipv4 L2 Metric (%s) on Interface %s is different from metric (%s) on Interface %s = NOT OK' \
                                            % (L2_metric, parallel_interface, interface_data['interface_data'].get('ipv4_metric'), interface_id), color = 'red')
                                    else: CGI_CLI.logtofile("Ipv4 L2 Metric (%s) check on Interface %s = OK\n" % (L2_metric, parallel_interface), ommit_timestamp = True)

                                if USE_IPV6 and BB_MODE:
                                    if interface_data['interface_data'].get('ipv6_metric'):
                                        if ipv6_L2_metric == '99999':
                                            CGI_CLI.logtofile("Ipv6 L2 Metric (99999) check on Interface %s = IGNORE\n" % (parallel_interface), ommit_timestamp = True)
                                        elif interface_data['interface_data'].get('ipv6_metric') != L2_metric:
                                            check_interface_result_ok = False
                                            CGI_CLI.uprint('Ipv6 L2 Metric (%s) on Interface %s is different from metric (%s) on Interface %s = NOT OK' \
                                                % (ipv6_L2_metric, parallel_interface, interface_data['interface_data'].get('ipv6_metric'), interface_id), color = 'red')
                                        else: CGI_CLI.logtofile("Ipv6 L2 Metric (%s) check on Interface %s = OK\n" % (ipv6_L2_metric, parallel_interface), ommit_timestamp = True)

                            elif RCMD.router_type == 'juniper':
                                try: L2_metric = parralel_cmd_output.upper().split('L2 METRIC')[1].split(parallel_interface.upper())[1].splitlines()[0].split()[-1].split('/')[1]
                                except: pass

                                if interface_data['interface_data'].get('L2 metric'):
                                    if L2_metric == '99999':
                                        CGI_CLI.logtofile("Ipv4 L2 Metric (99999) check on Interface %s = IGNORE\n" % (parallel_interface), ommit_timestamp = True)
                                    elif interface_data['interface_data'].get('L2 metric') != L2_metric:
                                        check_interface_result_ok = False
                                        CGI_CLI.uprint('Ipv4 L2 Metric (%s) on Interface %s is different from metric (%s) on Interface %s = NOT OK' \
                                            % (L2_metric, parallel_interface, interface_data['interface_data'].get('L2 metric'), interface_id), color = 'red')
                                    else: CGI_CLI.logtofile("Ipv4 L2 Metric (%s) check on Interface %s = OK\n" % (L2_metric, parallel_interface), ommit_timestamp = True)

                            elif RCMD.router_type == 'huawei':
                                try: L2_metric = parralel_cmd_output.split('Cost                        :')[1].splitlines()[0].split()[-1]
                                except: pass
                                try: ipv6_L2_metric = parralel_cmd_output.split('Ipv6 Cost                   :')[1].splitlines()[0].split()[-1]
                                except: pass

                                if interface_data['interface_data'].get('isis cost'):
                                    if L2_metric == '99999':
                                        CGI_CLI.logtofile("Ipv4 L2 Metric (99999) check on Interface %s = IGNORE\n" % (parallel_interface), ommit_timestamp = True)
                                    elif interface_data['interface_data'].get('isis cost') != L2_metric:
                                        check_interface_result_ok = False
                                        CGI_CLI.uprint('Ipv4 L2 Metric (%s) on Interface %s is different from metric (%s) on Interface %s = NOT OK' \
                                            % (L2_metric, parallel_interface, interface_data['interface_data'].get('isis cost'), interface_id), color = 'red')
                                    else: CGI_CLI.logtofile("Ipv4 L2 Metric (%s) check on Interface %s = OK\n" % (L2_metric, parallel_interface), ommit_timestamp = True)

                                if USE_IPV6 and BB_MODE:
                                    if interface_data['interface_data'].get('isis ipv6 cost'):
                                        if ipv6_L2_metric == '99999':
                                            CGI_CLI.logtofile("Ipv4 L2 Metric (99999) check on Interface %s = IGNORE\n" % (parallel_interface), ommit_timestamp = True)
                                        elif interface_data['interface_data'].get('isis ipv6 cost') != L2_metric:
                                            check_interface_result_ok = False
                                            CGI_CLI.uprint('Ipv6 L2 Metric (%s) on Interface %s is different from metric (%s) on Interface %s = NOT OK' \
                                                % (ipv6_L2_metric, parallel_interface, interface_data['interface_data'].get('isis ipv6 cost'), interface_id), color = 'red')
                                        else: CGI_CLI.logtofile("Ipv6 L2 Metric (%s) check on Interface %s = OK\n" % (ipv6_L2_metric, parallel_interface), ommit_timestamp = True)


                if not precheck_mode and (BB_MODE or CUSTOMER_MODE):
                    ### def BB - TRAFFIC POST-CHECK ###########################
                    low_percent = 3
                    high_percent = 90
                    if isinstance(interface_warning_data['interface_statistics'].get('txload_percent'), (str,basestring,six.string_types)):
                        CGI_CLI.uprint('Tx Traffic on Interface %s not found !' % (interface_id), color = 'red')
                        check_interface_result_ok = False
                    elif interface_warning_data['interface_statistics'].get('txload_percent') >= 0:
                        if interface_warning_data['interface_statistics'].get('txload_percent') < low_percent:
                            check_warning_interface_result_ok = False
                            CGI_CLI.uprint('Tx Traffic (%.2f%%) on Interface %s is below %d%%. = WARNING' % (interface_warning_data['interface_statistics'].get('txload_percent'), interface_id, low_percent), color = 'orange')
                        elif interface_warning_data['interface_statistics'].get('txload_percent') > high_percent:
                            CGI_CLI.uprint('Tx Traffic (%.2f%%) on Interface %s is over %d%%. = WARNING' % (interface_warning_data['interface_statistics'].get('txload_percent'), interface_id, high_percent), color = 'orange')
                            check_warning_interface_result_ok = False
                        else: CGI_CLI.logtofile('Tx Traffic on Interface %s is %.2f%% = OK\n' % (interface_id, interface_warning_data['interface_statistics'].get('txload_percent')), ommit_timestamp = True)

                    if isinstance(interface_warning_data['interface_statistics'].get('rxload_percent'), (str,basestring,six.string_types)):
                        CGI_CLI.uprint('Rx Traffic on Interface %s not found !' % (interface_id), color = 'red')
                        check_interface_result_ok = False
                    elif interface_warning_data['interface_statistics'].get('rxload_percent') >= 0:
                        if interface_warning_data['interface_statistics'].get('rxload_percent') < low_percent:
                            CGI_CLI.uprint('Rx Traffic (%.2f%%) on Interface %s is below %d%%. = WARNING' % (interface_warning_data['interface_statistics'].get('rxload_percent'), interface_id, low_percent), color = 'orange')
                            check_warning_interface_result_ok = False
                        elif interface_warning_data['interface_statistics'].get('rxload_percent') > high_percent:
                            CGI_CLI.uprint('Rx Traffic (%.2f%%) on Interface %s is over %d%%. = WARNING' % (interface_warning_data['interface_statistics'].get('rxload_percent'), interface_id, high_percent), color = 'orange')
                            check_warning_interface_result_ok = False
                        else: CGI_CLI.logtofile('Rx Traffic on Interface %s is %.2f%% = OK\n' % (interface_id, interface_warning_data['interface_statistics'].get('rxload_percent')), ommit_timestamp = True)

                ### def BB - REMOTE DEVICE CHECK #############################
                if BB_MODE:
                    check_interface_data_content("['interface_data']['name_of_remote_device_from_description']", what_not_in = device)

                ### def ALL - CONTENT ELEMENT CHECK ##########################
                if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                    check_interface_data_content("['interface_data']['is']", 'UP')
                    check_interface_data_content("['interface_data']['line protocol is']", 'UP')
                if RCMD.router_type == 'juniper':
                    check_interface_data_content("['interface_data']['Physical interface state']", 'Enabled')
                    check_interface_data_content("['interface_data']['Physical link is']", 'UP')
                if RCMD.router_type == 'huawei':
                    check_interface_data_content("['interface_data']['current state']", 'UP')
                    check_interface_data_content("['interface_data']['Line protocol current state']", 'UP')

                if interface_data['interface_data'].get('inactive_bundle_members'):
                    check_interface_result_ok = False
                    CGI_CLI.uprint('Inactive bundle interfaces found: %s' % (interface_data['interface_data'].get('inactive_bundle_members')), color = 'red')

                if interface_data['interface_data'].get('bundle_members_nr') and not interface_data['interface_data'].get('inactive_bundle_members'):
                    CGI_CLI.logtofile('CHECK of bundle interfaces is OK.\n', ommit_timestamp = True)


                ### def PING CHECKS ###########################################
                if RCMD.router_type == 'juniper':
                    CGI_CLI.uprint('NOTE: Juniper control plane protection could drop some of longer ping packets, so ping success could be less than 100%.', color = 'blue')

                if IPV4_STATIC_ROUTING:
                    check_interface_data_content("['bgp']['IPV4 ebgp-multihop']", higher_than = 2)
                    check_interface_data_content("['interface_statistics']['IPV4 next hop ping percent success from localhost']", '100')

                if IPV6_STATIC_ROUTING:
                    check_interface_data_content("['bgp']['IPV6 ebgp-multihop']", higher_than = 2, ignore_data_existence = True)
                    check_interface_data_content("['interface_statistics']['IPV6 next hop ping percent success from localhost']", '100', warning = True, ignore_data_existence = True)

                check_interface_data_content("['interface_statistics']['IPV4 ping percent success']", '100')

                if USE_IPV6:
                    check_interface_data_content("['interface_statistics']['IPV6 ping percent success']", '100', warning = True, ignore_data_existence = True)


                if BB_MODE or CUSTOMER_MODE:
                    if IPV4_STATIC_ROUTING:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV4 next hop ping percent success on intended ping size from localhost']", higher_than = 0, warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV4 next hop ping percent success on intended ping size from localhost']", '100', warning = True, ignore_data_existence = True)

                    if IPV6_STATIC_ROUTING:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV6 next hop ping percent success on intended ping size from localhost']", higher_than = 0, warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 next hop ping percent success on intended ping size from localhost']", '100', warning = True, ignore_data_existence = True)

                    if RCMD.router_type == 'juniper':
                        check_interface_data_content("['interface_statistics']['IPV4 ping percent success on intended ping size']", higher_than = 0, warning = True, ignore_data_existence = True)
                    else:
                        check_interface_data_content("['interface_statistics']['IPV4 ping percent success on intended ping size']", '100', warning = True, ignore_data_existence = True)

                    if USE_IPV6:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV6 ping percent success on intended ping size']", higher_than = 0, warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 ping percent success on intended ping size']", '100', warning = True, ignore_data_existence = True)


                if PING_ONLY:
                    if IPV4_STATIC_ROUTING:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV4 next hop %spings percent success on max working ping size from localhost']" % (ping_counts), higher_than = 0)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV4 next hop %spings percent success on max working ping size from localhost']" % (ping_counts), '100')

                    if IPV6_STATIC_ROUTING:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV6 next hop %spings percent success on max working ping size from localhost']" % (ping_counts), higher_than = 0, warning = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 next hop %spings percent success on max working ping size from localhost']" % (ping_counts), '100', warning = True)

                    if RCMD.router_type == 'juniper':
                        check_interface_data_content("['interface_statistics']['IPV4 %spings percent success on max working ping size']" % (ping_counts), higher_than = 0)
                    else:
                        check_interface_data_content("['interface_statistics']['IPV4 %spings percent success on max working ping size']" % (ping_counts), '100')

                    if USE_IPV6:
                        if RCMD.router_type == 'juniper':
                            check_interface_data_content("['interface_statistics']['IPV6 %spings percent success on max working ping size']" % (ping_counts), higher_than = 0, warning = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 %spings percent success on max working ping size']" % (ping_counts), '100', warning = True)


                if ping_counts and int(ping_counts) > 0:
                    if IPV4_STATIC_ROUTING:
                        if '100' in interface_warning_data['interface_statistics'].get('IPV4 next hop ping percent success on intended ping size from localhost',str()):
                            check_interface_data_content("['interface_statistics']['IPV4 next hop %spings percent success on intended ping size from localhost']" % (ping_counts), '100', warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV4 next hop %spings percent success from localhost']" % (ping_counts), '100', ignore_data_existence = True)

                    if IPV6_STATIC_ROUTING:
                        if '100' in interface_warning_data['interface_statistics'].get('IPV6 next hop ping percent success on intended ping size from localhost',str()):
                            check_interface_data_content("['interface_statistics']['IPV6 next hop %spings percent success on intended ping size from localhost']" % (ping_counts), '100', warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 next hop %spings percent success from localhost']" % (ping_counts), '100', warning = True, ignore_data_existence = True)

                    if '100' in interface_warning_data['interface_statistics'].get('IPV4 ping percent success on intended ping size',str()):
                        check_interface_data_content("['interface_statistics']['IPV4 %spings percent success on intended ping size']" % (ping_counts), '100', warning = True, ignore_data_existence = True)
                    else:
                        check_interface_data_content("['interface_statistics']['IPV4 %spings percent success']" % (ping_counts), '100', ignore_data_existence = True)

                    if USE_IPV6:
                        if '100' in interface_warning_data['interface_statistics'].get('IPV6 ping percent success on intended ping size',str()):
                            check_interface_data_content("['interface_statistics']['IPV6 %spings percent success on intended ping size']" % (ping_counts), '100', warning = True, ignore_data_existence = True)
                        else:
                            check_interface_data_content("['interface_statistics']['IPV6 %spings percent success']" % (ping_counts), '100', warning = True, ignore_data_existence = True)

                check_interface_data_content("['interface_statistics']['IPV4 max working ping size']", \
                    higher_than = (1500 - 1 - int(interface_warning_data['interface_data']['IPV4 L3 ping header size'])), \
                    warning = True, ignore_data_existence = True)

                check_interface_data_content("['interface_statistics']['IPV6 max working ping size']", \
                    higher_than = (1500 - 1 - int(interface_warning_data['interface_data']['IPV6 L3 ping header size'])), \
                    warning = True, ignore_data_existence = True)


                if interface_warning_data['interface_data'].get('IPV4_addr_rem_calculated'):
                    check_interface_data_content("['interface_data']['IPV4_addr_rem_calculated']", interface_data['interface_data'].get('IPV4_addr_rem'), ignore_data_existence = True, warning = True)

                if interface_warning_data['interface_data'].get('IPV6_addr_rem_calculated'):
                     check_interface_data_content("['interface_data']['IPV6_addr_rem_calculated']", normalized_ipv6(interface_warning_data['interface_data'].get('IPV6_addr_rem')), ignore_data_existence = True, warning = True)


                if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':
                    if BB_MODE:
                        check_interface_data_content("['interface_data']['line protocol is']", 'UP')
                        if precheck_mode:
                            check_interface_data_content("['interface_data']['ipv4_metric']", '99999')

                            if USE_IPV6:
                                check_interface_data_content("['interface_data']['ipv6_metric']", '99999')
                        else:
                            check_interface_data_content("['interface_data']['ipv4_metric']", None, '99999')

                            if USE_IPV6:
                                check_interface_data_content("['interface_data']['ipv6_metric']", None, '99999')

                    if ping_counts and int(ping_counts) > 0:
                        check_interface_data_content("['interface_statistics']['input_errors_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['input_CRC_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['output_errors_Difference']", exact_value_yes = '0', warning = True)
                    else:
                        check_interface_data_content("['interface_statistics']['input_errors']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['input_CRC']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['output_errors']", exact_value_yes = '0', warning = True)


                elif RCMD.router_type == 'juniper':
                    if BB_MODE:
                        check_interface_data_content("['interface_data']['Flags']", 'UP')
                        check_interface_data_content("['interface_data']['Physical link is']", 'UP')
                        check_interface_data_content("['interface_data']['LDP sync state']", 'in sync')

                        if precheck_mode:
                            check_interface_data_content("['interface_data']['L2 metric']", '99999')
                        else:
                            check_interface_data_content("['interface_data']['L2 metric']", None,  '99999')

                        check_interface_data_content("['interface_statistics']['Active_alarms']", 'None', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['Active_defects']", 'None', warning = True, ignore_data_existence = True)

                    if ping_counts and int(ping_counts) > 0:
                        check_interface_data_content("['interface_statistics']'Active_alarms_After_ping']", 'None', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']'Active_defects_After_ping']", 'None', warning = True, ignore_data_existence = True)

                        check_interface_data_content("['interface_statistics']['Input_errors_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Input_errors__Drops_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Input_errors__Framing_errors_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Input_errors__Runts_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Input_errors__Policed_discards_Difference']", exact_value_yes = '0', warning = True)

                        check_interface_data_content("['interface_statistics']['Output_errors_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Output_errors__Carrier_transitions_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Output_errors__Drops_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Output_errors__Collisions_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['Output_errors__Aged_packets_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)

                        check_interface_data_content("['interface_statistics']['Bit_errors_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['Errored_blocks_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['FEC_Corrected_Errors_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['FEC_Uncorrected_Errors_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['FEC_Corrected_Errors_Rate_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)
                        check_interface_data_content("['interface_statistics']['FEC_Uncorrected_Errors_Rate_Difference']", exact_value_yes = '0', warning = True, ignore_data_existence = True)


                elif RCMD.router_type == 'huawei':
                    if BB_MODE:
                        check_interface_data_content("['interface_data']['isis ldp-sync']", 'Achieved')
                        check_interface_data_content("['interface_data'][Line protocol current state']", 'UP')
                        check_interface_data_content("['interface_data']['isis interface IPV4.State']", 'UP')

                        if USE_IPV6:
                            check_interface_data_content("['interface_data']['isis interface IPV6.State']", 'UP')

                        if precheck_mode:
                            check_interface_data_content("['interface_data']['isis cost']", '99999')

                            if USE_IPV6:
                                check_interface_data_content("['interface_data']['isis ipv6 cost']", '99999')
                        else:
                            check_interface_data_content("['interface_data']['isis cost']", None, '99999')

                            if USE_IPV6 and BB_MODE:
                                check_interface_data_content("['interface_data']['isis ipv6 cost']", None, '99999')

                        if interface_warning_data['interface_statistics'].get('Local_fault'):
                            check_interface_data_content("['interface_statistics']['Local_fault']", 'NORMAL', warning = True)

                        if interface_warning_data['interface_statistics'].get('Remote_fault'):
                            check_interface_data_content("['interface_statistics']['Remote_fault']", 'NORMAL', warning = True)

                    if ping_counts and int(ping_counts) > 0:
                        check_interface_data_content("['interface_statistics']['Local_fault_After_ping']", 'NORMAL', warning = True)
                        check_interface_data_content("['interface_statistics']['Remote_fault_After_ping']", 'NORMAL', warning = True)

                    check_interface_data_content("['interface_statistics']['Rx_Power_dBm']", higher_than = interface_warning_data.get('Rx_Power_Warning_range_dBm_1'), warning = True)
                    check_interface_data_content("['interface_statistics']['Rx_Power_dBm']", lower_than = interface_warning_data.get('Rx_Power_Warning_range_dBm_2'), warning = True)

                    check_interface_data_content("['interface_statistics']['Tx_Power_dBm']", higher_than = interface_warning_data.get('Tx_Power_Warning_range_dBm_1'), warning = True)
                    check_interface_data_content("['interface_statistics']['Tx_Power_dBm']", lower_than = interface_warning_data.get('Tx_Power_Warning_range_dBm_2'), warning = True)

                    if ping_counts and int(ping_counts) > 0:
                        check_interface_data_content("['interface_statistics']['Rx_Power_dBm_After_ping']", higher_than = interface_warning_data.get('Rx_Power_Warning_range_dBm_1'), warning = True)
                        check_interface_data_content("['interface_statistics']['Rx_Power_dBm_After_ping']", lower_than = interface_warning_data.get('Rx_Power_Warning_range_dBm_2'), warning = True)

                        check_interface_data_content("['interface_statistics']['Tx_Power_dBm_After_ping']", higher_than = interface_warning_data.get('Tx_Power_Warning_range_dBm_1'), warning = True)
                        check_interface_data_content("['interface_statistics']['Tx_Power_dBm_After_ping']", lower_than = interface_warning_data.get('Tx_Power_Warning_range_dBm_2'), warning = True)

                        check_interface_data_content("['interface_statistics']['CRC_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Overrun_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Lost_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Overflow_Difference']", exact_value_yes = '0', warning = True)
                        check_interface_data_content("['interface_statistics']['Underrun_Difference']", exact_value_yes = '0', warning = True)


                if CUSTOMER_MODE:
                    ### def CUST - CHECKS #####################################
                    if RCMD.router_type == 'cisco_ios' or RCMD.router_type == 'cisco_xr':

                        check_interface_data_content("['bgp']['IPV4 address-family']", what_yes_in = 'unicast')

                        check_interface_data_content("['interface_data']['IPV4_addr_rem_from_DESCRIPTION']", what_yes_in = interface_data['interface_data'].get('IPV4_addr_rem'))

                        #if USE_IPV6:
                        #    check_interface_data_content("['interface_data']['IPV6_addr_rem_from_ASN']", what_yes_in = interface_warning_data.get('IPV6_addr_rem'), warning = True)

                        if precheck_mode:
                            check_interface_data_content("['bgp']['IPV4 unicast route-policy in']", exact_value_yes = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast route-policy out']", exact_value_yes = 'DENY-ALL')

                            check_interface_data_content("['bgp']['IPV4 accepted prefixes']", exact_value_yes = '0')
                            #check_interface_data_content("['bgp']['IPV4 bestpaths']", exact_value_yes = '0')
                            check_interface_data_content("['bgp']['IPV4 No of prefixes Advertised']", exact_value_yes = '0')

                        else:
                            check_interface_data_content("['bgp']['IPV4 unicast route-policy in']", what_not_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast route-policy out']", what_not_in = 'DENY-ALL')

                            check_interface_data_content("['bgp']['IPV4 accepted prefixes']", higher_than = 0)
                            #check_interface_data_content("['bgp']['IPV4 bestpaths']", higher_than = 0)
                            check_interface_data_content("['bgp']['IPV4 No of prefixes Advertised']", higher_than = 0)

                            check_interface_data_content("['bgp']['IPV4 accepted/max prefixes percent']", lower_than = 90)

                            for lag_member in interface_data['interface_data'].get('bundle_members',[]):
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['is']" % (str(lag_member)), what_yes_in = 'UP')
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['line protocol is']" % (str(lag_member)), what_yes_in = 'UP')


                    elif RCMD.router_type == 'juniper':
                        check_interface_data_content("['bgp']['IPV4 bgp group Established']", higher_than = 0)
                        check_interface_data_content("['bgp']['IPV6 bgp group Established']", higher_than = 0, ignore_data_existence = True)

                        check_interface_data_content("['interface_data']['Flags']", exact_value_yes = 'Up')

                        for neighbor in interface_data['bgp'].get('IPV4 bgp group Peers',[]):
                            try:
                                neighbor_filtered = neighbor.split('+')[0]
                                check_interface_data_content("['bgp']['IPV4 neighbors']", what_yes_in = neighbor_filtered)
                            except: pass

                        for neighbor in interface_data['bgp'].get('IPV6 bgp group Peers',[]):
                            try:
                                neighbor_filtered = normalized_ipv6(neighbor.split('+')[0])
                                check_interface_data_content("['bgp']['IPV6 neighbors']", what_yes_in = neighbor_filtered)
                            except: pass

                        if precheck_mode:
                            check_interface_data_content("['bgp']['IPV4 bgp group Established']", exact_value_yes = '0')
                            check_interface_data_content("['bgp']['IPV6 bgp group Established']", exact_value_yes = '0', ignore_data_existence = True)

                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_in']", what_yes_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_out']", what_yes_in = 'DENY-ALL')
                            if USE_IPV6:
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_in']", what_yes_in = 'DENY-ALL')
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_out']", what_yes_in = 'DENY-ALL')
                        else:
                            check_interface_data_content("['bgp']['IPV4 bgp group Established']", higher_than = 0)
                            check_interface_data_content("['bgp']['IPV6 bgp group Established']", higher_than = 0, ignore_data_existence = True)

                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_in']", what_not_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_out']", what_not_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 Received/maximum prefixes percent']", lower_than = 90)

                            if USE_IPV6:
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_in']", what_not_in = 'DENY-ALL')
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_out']", what_not_in = 'DENY-ALL')

                            for lag_member in interface_data['interface_data'].get('bundle_members',[]):
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['Enabled']" % (str(lag_member)), what_yes_in = True)
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['Physical link is']" % (str(lag_member)), what_yes_in = 'UP')


                    elif RCMD.router_type == 'huawei':
                        check_interface_data_content("['bgp']['IPV4 BGP current state']", what_yes_in = 'Established')
                        check_interface_data_content("['bgp']['IPV6 BGP current state']", what_yes_in = 'Established', ignore_data_existence = True)

                        if precheck_mode:
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_in']", what_yes_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_out']", what_yes_in = 'DENY-ALL')
                            if USE_IPV6:
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_in']", what_yes_in = 'DENY-ALL')
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_out']", what_yes_in = 'DENY-ALL')
                        else:
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_in']", what_not_in = 'DENY-ALL')
                            check_interface_data_content("['bgp']['IPV4 unicast_route-policy_out']", what_not_in = 'DENY-ALL')
                            if USE_IPV6:
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_in']", what_not_in = 'DENY-ALL')
                                check_interface_data_content("['bgp']['IPV6 unicast_route-policy_out']", what_not_in = 'DENY-ALL')
                                check_interface_data_content("['bgp']['IPV4 Received/maximum total routes percent']", lower_than = 90)

                            for lag_member in interface_data['interface_data'].get('bundle_members',[]):
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['Line protocol current state']" % (str(lag_member)), what_yes_in = 'UP')
                                check_interface_data_content("['interface_data']['LAG_interfaces']['%s']['Link quality grade']" % (str(lag_member)), what_yes_in = 'GOOD')

                        check_interface_data_content("['interface_data']['Line protocol current state']", what_yes_in = 'UP')
                        check_interface_data_content("['interface_data']['Link quality grade']", what_yes_in = 'GOOD')


                ### def OPTICS CHECK ##########################################
                if (CUSTOMER_MODE or BB_MODE) and RCMD.router_type != 'huawei':
                    if len(interface_data['interface_data'].get('bundle_members',[])) == 0:
                        for i in range(4):
                            check_interface_data_content("['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d']" % i, higher_than = interface_data['interface_statistics'].get('Tx_Power_Lanes_dBm_Warning_low'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d']" % i, higher_than = interface_data['interface_statistics'].get('Tx_Power_Lanes_dBm_Alarm_low'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d']" % i, lower_than = interface_data['interface_statistics'].get('Tx_Power_Lanes_dBm_Warning_high'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Tx_Power_Lanes_dBm']['Lane %d']" % i, lower_than = interface_data['interface_statistics'].get('Tx_Power_Lanes_dBm_Alarm_high'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d']" % i, higher_than = interface_data['interface_statistics'].get('Rx_Power_Lanes_dBm_Warning_low'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d']" % i, higher_than = interface_data['interface_statistics'].get('Rx_Power_Lanes_dBm_Alarm_low'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d']" % i, lower_than = interface_data['interface_statistics'].get('Rx_Power_Lanes_dBm_Warning_high'), ignore_data_existence = True)
                            check_interface_data_content("['interface_statistics']['Rx_Power_Lanes_dBm']['Lane %d']" % i, lower_than = interface_data['interface_statistics'].get('Rx_Power_Lanes_dBm_Alarm_high'), ignore_data_existence = True)

                    elif len(interface_data['interface_data'].get('bundle_members',[])) > 0:
                        for lag_member in interface_data['interface_data'].get('bundle_members',[]):
                            for i in range(4):
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Tx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), higher_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Tx_Power_Lanes_dBm_Warning_low'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Tx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), higher_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Tx_Power_Lanes_dBm_Alarm_low'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Tx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), lower_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Tx_Power_Lanes_dBm_Warning_high'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Tx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), lower_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Tx_Power_Lanes_dBm_Alarm_high'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Rx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), higher_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Rx_Power_Lanes_dBm_Warning_low'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Rx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), higher_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Rx_Power_Lanes_dBm_Alarm_low'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Rx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), lower_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Rx_Power_Lanes_dBm_Warning_high'), ignore_data_existence = True)
                                check_interface_data_content("['interface_statistics']['LAG_interfaces']['%s']['Rx_Power_Lanes_dBm']['Lane %d']" % (str(lag_member),i), lower_than = interface_data['interface_statistics']['LAG_interfaces']['%s' % (str(lag_member))].get('Rx_Power_Lanes_dBm_Alarm_high'), ignore_data_existence = True)


                ###############################################################
                ### def INTERFACE RESULTS #####################################
                ###############################################################
                interface_result = 'WARNING'
                html_color = 'orange'

                if check_interface_result_ok and check_warning_interface_result_ok:
                    interface_result = 'OK'
                    html_color = 'green'
                elif not check_interface_result_ok:
                    interface_result = 'NOT OK'
                    html_color = 'red'

                #CGI_CLI.uprint('check_interface_result_ok = %s, check_warning_interface_result_ok = %s' % (str(check_interface_result_ok), str(check_warning_interface_result_ok)))

                interface_results.append([copy.deepcopy(device), copy.deepcopy(interface_id), copy.deepcopy(interface_result)])


                ### PRINT LOGFILENAME #########################################
                if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, logfilename)
                else: logviewer = './logviewer.py?logfile=%s' % (logfilename)
                if CGI_CLI.cgi_active:
                    if interface_result == 'NOT_OK':
                        CGI_CLI.uprint('<p style="color:red;">The selected backbone interface %s on device %s does not comply to the required parameters for traffic activation.</p>' % (interface_id, device), raw = True)

                    CGI_CLI.uprint('Device=%s, Interface=%s  -  RESULT = %s' \
                        % (device, interface_id, interface_result), color = html_color, tag = 'h2')
                    CGI_CLI.uprint('<p style="color:blue;"> ==> File <a href="%s" target="_blank" style="text-decoration: none">%s</a> created.</p>' \
                        % (logviewer, logfilename), raw = True)
                else:
                    CGI_CLI.uprint('Device=%s, Interface=%s  -  RESULT = %s' % \
                        (device, interface_id, interface_result), color = html_color)
                    CGI_CLI.uprint(' ==> File %s created.' % (logfilename), color = 'blue')
                CGI_CLI.uprint(' ')

                ### END OF LOGGING TO FILE PER DEVICE #########################
                CGI_CLI.logtofile(end_log = True)


                ### def SQL UPDATE IF SWAN_ID DEFINED #########################
                if not swan_id: continue

                #MariaDB [rtr_configuration]> select * from pre_post_result;
                #+----+---------+-------------+-----------+-----------------+------------------+--------------+---------------+--------------+
                #| id | swan_id | router_name | int_name  | precheck_result | postcheck_result | precheck_log | postcheck_log | last_updated |

                ### AVOID OF REWRITING SQL PRE/POST DB FIELDS #################
                if precheck_mode:
                    pre_post_template = sql_inst.sql_read_all_table_columns_to_void_dict(\
                        'pre_post_result' + table_test_extension, ommit_columns = ['id','postcheck_result','postcheck_log'])
                else:
                     pre_post_template = sql_inst.sql_read_all_table_columns_to_void_dict(\
                        'pre_post_result' + table_test_extension, ommit_columns = ['id','precheck_result','precheck_log'])

                pre_post_template['swan_id'] = swan_id
                pre_post_template['router_name'] = device.upper()
                pre_post_template['int_name'] = interface_id

                if 'operation_type' in pre_post_template.keys():
                    pre_post_template['operation_type'] = str(action_type)

                if precheck_mode:
                    pre_post_template['precheck_result'] = interface_result
                    pre_post_template['precheck_log'] = copy.deepcopy(logfilename)
                    pre_post_template['last_updated_precheck'] = CGI_CLI.get_date_and_time()
                else:
                    pre_post_template['postcheck_result'] = interface_result
                    pre_post_template['postcheck_log'] = copy.deepcopy(logfilename)
                    pre_post_template['last_updated_postcheck'] = CGI_CLI.get_date_and_time()

                CGI_CLI.uprint(pre_post_template, name = True, jsonprint = True, \
                    no_printall = not CGI_CLI.printall)

                ### TEST IF SWAN ALREADY RECORD EXISTS ########################
                sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                    table_name = 'pre_post_result' + table_test_extension, \
                    where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                         % (swan_id, device.upper(), interface_id) )

                CGI_CLI.uprint(sql_read_data, name = True, jsonprint = True, \
                    no_printall = not CGI_CLI.printall)

                ### WARNING MESSAGE ###########################################
                if len(sql_read_data) > 1:
                    CGI_CLI.uprint("WARNING: More records per swan_id='%s' and router_name='%s' and int_name='%s'! 1st will be edited." \
                         % (swan_id, device.upper(), interface_id), color = 'red')

                ### UPDATE OR INSERT ##########################################
                if len(sql_read_data) > 0:

                    if 'operation_type' in sql_read_data[0].keys():
                        sql_read_data[0]['operation_type'] = str(action_type)

                    if precheck_mode:
                        sql_read_data[0]['precheck_log'] = copy.deepcopy(logfilename)
                        sql_read_data[0]['precheck_result'] = interface_result
                        sql_read_data[0]['last_updated_precheck'] = CGI_CLI.get_date_and_time()
                    else:
                        sql_read_data[0]['postcheck_log'] = copy.deepcopy(logfilename)
                        sql_read_data[0]['postcheck_result'] = interface_result
                        sql_read_data[0]['last_updated_postcheck'] = CGI_CLI.get_date_and_time()
                    try:
                        del sql_read_data[0]['id']
                    except: pass
                    sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, sql_read_data[0],
                        where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                            % (swan_id, device.upper(), interface_id), update = True)
                else:
                    sql_inst.sql_write_table_from_dict('pre_post_result' + table_test_extension, pre_post_template)

                ### TEST IF SWAN ALREADY RECORD EXISTS ########################
                sql_read_data = sql_inst.sql_read_records_to_dict_list( \
                    table_name = 'pre_post_result' + table_test_extension, \
                    where_string = "swan_id='%s' and router_name='%s' and int_name='%s'" \
                         % (swan_id, device.upper(), interface_id) )
                CGI_CLI.uprint(sql_read_data, name = 'DB_READ_CHECK', jsonprint = True,
                    no_printall = not CGI_CLI.printall)

    ### LOOP PER INTERFACE - END ######################################
    RCMD.disconnect()

    ### def GLOBAL_LOGFILENAME, DO LOG ONLY WHEN DEVICE LIST EXISTS ###########
    if len(devices_interfaces_list) > 0:
        html_extention = 'htm' if CGI_CLI.cgi_active else str()
        if BB_MODE:
            global_logfilename = copy.deepcopy(generate_logfilename( \
                prefix = '%s' % ('BB_PRECHECK' if precheck_mode else 'BB_POSTCHECK'), \
                USERNAME = USERNAME, suffix = str('%slog' % (html_extention))))
        elif CUSTOMER_MODE:
            global_logfilename = copy.deepcopy(generate_logfilename( \
                prefix = '%s' % ('CUST_PRECHECK' if precheck_mode else 'CUST_POSTCHECK'), \
                USERNAME = USERNAME, suffix = str('%slog' % (html_extention))))
        elif PING_ONLY:
            global_logfilename = copy.deepcopy(generate_logfilename( \
                prefix = '%s' % ('PINGCHECK'), \
                USERNAME = USERNAME, suffix = str('%slog' % (html_extention))))

        ### NO WINDOWS LOGGING ################################################
        if 'WIN32' in sys.platform.upper(): global_logfilename = None
        if global_logfilename: CGI_CLI.set_logfile(logfilename = global_logfilename)

        if CGI_CLI.cgi_active:
            CGI_CLI.logtofile('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s)</a></h1>' % \
                (SCRIPT_NAME, changelog, CGI_CLI.VERSION()), raw_log = True, ommit_timestamp = True)
            if swan_id: CGI_CLI.logtofile('<p>SWAN_ID=%s</p>' %(swan_id), raw_log = True, ommit_timestamp = True)

            if BB_MODE:
                if precheck_mode: CGI_CLI.logtofile('<p>Backbone monitoring/precheck mode.</p>', raw_log = True, ommit_timestamp = True)
                else: CGI_CLI.logtofile('<p>Backbone traffic/postcheck mode.</p>', raw_log = True)
            elif CUSTOMER_MODE:
                if precheck_mode: CGI_CLI.logtofile('<p>Customer monitoring/precheck mode.</p>', raw_log = True, ommit_timestamp = True)
                else: CGI_CLI.logtofile('<p>Customer traffic/postcheck mode.</p>', raw_log = True)
            elif PING_ONLY: CGI_CLI.logtofile('<p>Ping only mode.</p>', ommit_timestamp = True)

            CGI_CLI.logtofile('<p>LOGFILES:</p>' , raw_log = True, ommit_timestamp = True)
        else:
            CGI_CLI.logtofile('%s (v.%s)' % (SCRIPT_NAME,CGI_CLI.VERSION()), ommit_timestamp = True)
            if swan_id: CGI_CLI.logtofile('SWAN_ID=%s\n' %(swan_id))

            if BB_MODE:
                if precheck_mode: CGI_CLI.logtofile('Backbone monitoring/precheck mode.\n')
                else: CGI_CLI.logtofile('Backbone traffic/postcheck mode.\n', ommit_timestamp = True)
            elif CUSTOMER_MODE:
                if precheck_mode: CGI_CLI.logtofile('Customer monitoring/precheck mode.\n')
                else: CGI_CLI.logtofile('Customer traffic/postcheck mode.\n', ommit_timestamp = True)
            elif PING_ONLY: CGI_CLI.logtofile('Ping only mode.\n', ommit_timestamp = True)

            CGI_CLI.logtofile('\nLOGFILES:\n', ommit_timestamp = True)

        for logfilename, interface_result in zip(logfilename_list, interface_results):
            device, interface_id, interface_result = interface_result
            ### PRINT LOGFILENAME #############################################
            if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, logfilename)
            else: logviewer = './logviewer.py?logfile=%s' % (logfilename)
            if CGI_CLI.cgi_active:
                if interface_result == 'NOT OK':
                    CGI_CLI.logtofile('<p style="color:red;">The selected backbone interface %s on device %s does not comply to the required parameters for traffic activation.</p>' % (interface_id, device), raw_log = True, ommit_timestamp = True)
                    CGI_CLI.logtofile('<p style="color:red;">Device=%s, Interface=%s  -  RESULT = %s</p>' \
                        % (device, interface_id, interface_result), raw_log = True, ommit_timestamp = True)
                elif interface_result == 'WARNING':
                    CGI_CLI.logtofile('<p style="color:orange;">Device=%s, Interface=%s  -  RESULT = %s</p>' \
                        % (device, interface_id, interface_result), raw_log = True, ommit_timestamp = True)
                else: CGI_CLI.logtofile('<p style="color:green;">Device=%s, Interface=%s  -  RESULT = %s</p>' \
                          % (device, interface_id, interface_result), raw_log = True, ommit_timestamp = True)
                CGI_CLI.logtofile('<p style="color:blue;"> ==> File <a href="%s" target="_blank" style="text-decoration: none">%s</a> created.</p>' \
                    % (logviewer, logfilename), raw_log = True, ommit_timestamp = True)
                CGI_CLI.logtofile('<br/>', raw_log = True, ommit_timestamp = True)
            else:
                CGI_CLI.logtofile('Device=%s, Interface=%s  -  RESULT = %s\n' % (device, interface_id, interface_result), ommit_timestamp = True)
                CGI_CLI.logtofile(' ==> File %s created.\n\n' % (logfilename), ommit_timestamp = True)

        ### CLOSE GLOBAL LOGFILE ##############################################
        CGI_CLI.logtofile(end_log = True, ommit_timestamp = True)

except SystemExit: pass
except:
    traceback_found = traceback.format_exc()
    CGI_CLI.uprint(str(traceback_found), tag = 'h3', color = 'magenta')

if global_logfilename and CGI_CLI.data.get("send_email"):
    ### SEND EMAIL WITH LOGFILE ###############################################
    CGI_CLI.send_me_email( \
        subject = str(global_logfilename).replace('\\','/').split('/')[-1] if global_logfilename else None, \
        file_name = str(global_logfilename), username = USERNAME)

# if global_logfilename:
    ## SEND EMAIL WITH LOGFILE ###############################################
    # send_me_email( \
        # subject = str(global_logfilename).replace('\\','/').split('/')[-1] if global_logfilename else None, \
        # file_name = str(global_logfilename), username = 'pnemec')

### def SEND EMAIL WITH ERROR/TRACEBACK LOGFILE TO SUPPORT ####################
if traceback_found:
    CGI_CLI.send_me_email( \
        subject = 'TRACEBACK-PRE_TRAFFIC-' + global_logfilename.replace('\\','/').\
        split('/')[-1] if global_logfilename else str(),
        email_body = str(traceback_found),\
        file_name = global_logfilename, username = 'pnemec')


