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
        parser.add_argument("--cpassword", default = str(),
                            action = "store", dest = 'cpassword',
                            help = "specify router user cpassword")
        parser.add_argument("--getpass",
                            action = "store_true", dest = 'getpass', default = None,
                            help = "forced to insert router password interactively getpass.getpass()")
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "target router to access. For now supports only 1.")
        parser.add_argument("--precheck",
                            action = "store_true", dest = 'precheck', default = None,
                            help = "do monitoring/precheck")
        parser.add_argument("--postcheck",
                            action = "store_true", dest = 'postcheck', default = None,
                            help = "do traffic/postcheck")
        parser.add_argument("--recheck",
                            action = "store_true", dest = 'postcheck', default = None,
                            help = "recheck last or specified diff pre/post files per inserted device")
        parser.add_argument("--prefile",
                            action = 'store', dest = "precheck_file", default = str(),
                            help = "run postcheck against a specific precheck file")
        parser.add_argument("--postfile",
                            action = 'store', dest = "postcheck_file", default = str(),
                            help = "specify your postcheck file")
        parser.add_argument("--send_email",
                            action = "store_true", dest = 'send_email', default = None,
                            help = "send email with test result logs")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
        parser.add_argument("--append_logfile",
                            action = "store", dest = 'append_logfile',
                            default = None,
                            help = "append logfile with specified name")
        parser.add_argument("--latest",
                    action = 'store_true', dest = "latest", default = False,
                    help = "look for really latest pre/postcheck files (also from somebody else),\
                    otherwise your own last pre/postcheck files will be used by default")
        parser.add_argument("--timestamps",
                            action = "store_true", dest = 'timestamp', default = None,
                            help = "show timestamps")
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():    
        if CGI_CLI.json_api: 
            CGI_CLI.uprint_json_results(CGI_CLI.JSON_RESULTS)
        else:
            if CGI_CLI.timestamp:
                CGI_CLI.uprint('END.\n', no_printall = not CGI_CLI.printall, tag = 'debug')
            if not CGI_CLI.disable_page_reload_link: CGI_CLI.html_selflink()
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
        timestamp = None, disable_page_reload_link = None, no_title = None, \
        json_api = None):
        """
        """
        try: CGI_CLI.sys_stdout_encoding = sys.stdout.encoding
        except: CGI_CLI.sys_stdout_encoding = None
        if not CGI_CLI.sys_stdout_encoding: CGI_CLI.sys_stdout_encoding = 'UTF-8'
        CGI_CLI.json_api = json_api
        CGI_CLI.JSON_RESULTS = collections.OrderedDict()
        CGI_CLI.USERNAME, CGI_CLI.PASSWORD = None, None
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
        CGI_CLI.disable_page_reload_link = disable_page_reload_link
        ### CGI PARSING #######################################################
        try: form = cgi.FieldStorage()
        except: pass
        for key in form.keys():
            variable = str(key)
            try: value = form.getvalue(variable)
            except: value = ','.join(form.getlist(name))
            if variable and value and \
                not variable in ["username", "password"]:
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.USERNAME = value
            if variable == "password": CGI_CLI.PASSWORD = value

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
        if CGI_CLI.json_api:
            CGI_CLI.content_type_line = 'Content-type:application/vnd.api+json%s' % (CGI_CLI.newline)
        
        ### DECIDE - CLI OR CGI MODE ##########################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent:
            CGI_CLI.cgi_active = True

        ### CLI PARSER ########################################################
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active:
            cli_data = vars(CGI_CLI.args)
            for key in cli_data.keys():
                variable = str(key)
                try: value = cli_data.get(variable)
                except: value = None
                if variable and \
                    not variable in ["username", "password"]:
                    CGI_CLI.data[variable] = value
                if variable == "username": CGI_CLI.USERNAME = value
                if variable == "password": CGI_CLI.PASSWORD = value

        ### CGI_CLI.data PARSER ###############################################
        for key in CGI_CLI.data.keys():
            variable = str(key)
            value = CGI_CLI.data.get(variable)

            if variable == "printall" and (str(value).upper() == 'NO' or not value):
                CGI_CLI.printall = False
            elif variable == "printall":
                CGI_CLI.printall = True
            if variable == "timestamp" and value: CGI_CLI.timestamp = True
            if variable == "cusername": CGI_CLI.USERNAME = value.decode('base64','strict')
            if variable == "cpassword": CGI_CLI.PASSWORD = value.decode('base64','strict')

        ### HTML PRINTING START ###############################################
        if CGI_CLI.cgi_active and not CGI_CLI.json_api:
            sys.stdout.write("%s%s%s" %
                (CGI_CLI.chunked_transfer_encoding_line,
                CGI_CLI.content_type_line,
                CGI_CLI.status_line))
            sys.stdout.flush()
            if no_title: title_string = str()
            else: title_string = '<title>' + str(__file__).split('/')[-1] + '  PID' + str(os.getpid()) + '</title>' if '/' in str(__file__) else str()
            ### CHROME NEEDS 2NEWLINES TO BE ALREADY CHUNKED !!! ##############
            CGI_CLI.print_chunk("%s%s<!DOCTYPE html><html><head>%s%s</head><body>" %
                (CGI_CLI.newline, CGI_CLI.newline,
                #CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit', \
                title_string, \
                '<style>%s</style>' % (CGI_CLI.CSS_STYLE) if CGI_CLI.CSS_STYLE else str()),\
                ommit_logging = True, printall = True)
        ### JSON API PRINTING START ###########################################                
        elif CGI_CLI.json_api:
            sys.stdout.write("%s%s%s%s%s" %
                (CGI_CLI.chunked_transfer_encoding_line,
                CGI_CLI.content_type_line,
                CGI_CLI.status_line, CGI_CLI.newline, CGI_CLI.newline))
            sys.stdout.flush()
        
        ### REGISTER CLEANUP FUNCTION #########################################
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM ENVIRONMENT BY DEFAULT ############
        if not CGI_CLI.PASSWORD:
            try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
            except: CGI_CLI.PASSWORD        = str()
        if not CGI_CLI.USERNAME:
            try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
            except: CGI_CLI.USERNAME        = str()
        ### GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI ###
        getpass_done = None
        if not CGI_CLI.PASSWORD and not CGI_CLI.cgi_active:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
            getpass_done = True
        ### FORCE GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI GETPASS #######
        if CGI_CLI.data.get('getpass') and not getpass_done and not CGI_CLI.cgi_active:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
        ### WINDOWS DOES NOT SUPPORT LINUX COLORS - SO DISABLE IT #############
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
    def html_deescape(text = None, pre_tag = None):
        escaped_text = str()
        if text and not pre_tag:
            escaped_text = str(text.replace('&amp;','&').\
                replace('&lt;','<').replace('&gt;','>').\
                replace('&nbsp;',' ').\
                replace('&quot;','"').replace('&apos;',"'").\
                replace('<br/>','\n'))
        elif text and pre_tag:
            ### OMMIT SPACES,QUOTES AND NEWLINES ##############################
            escaped_text = str(text.replace('&amp;','&').\
                replace('&lt;','<').replace('&gt;','>'))
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
            if printall and not CGI_CLI.json_api:
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
    def uprint_json_results(msg = None, raw_log = None, sort_keys = None,\
        ommit_logging = None, printall = None):

        print_text = None
        if msg: 
            if isinstance(msg, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = str(json.dumps(msg, indent = 2, sort_keys = sort_keys))
                except Exception as e:
                    CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']', printall = printall_yes)
        
            if print_text:        
                print(print_text)
                if not ommit_logging: CGI_CLI.logtofile(msg = print_text, raw_log = raw_log, \
                                          ommit_timestamp = True)
            else:                              
                print(msg)
                if not ommit_logging: CGI_CLI.logtofile(msg = msg, raw_log = raw_log, \
                                          ommit_timestamp = True)

        

    @staticmethod
    def uprint(text = None, tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        ommit_logging = None, no_newlines = None, start_tag = None, end_tag = None, raw = None, \
        timestamp = None, printall = None, no_printall = None, stop_button = None, sort_keys = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
           timestamp = True - locally allow (CGI_CLI.timestamp = True has priority)
           timestamp = 'no' - locally disable even if CGI_CLI.timestamp == True
           Use 'no_printall = not CGI_CLI.printall' instead of printall = False
        """
        try:
            if not text and not name: return None

            print_text = str()

            ### PRINTALL LOGIC ####################################################
            if not printall and not no_printall: printall_yes = True
            elif no_printall: printall_yes = False
            else: printall_yes = True

            if jsonprint:
                if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                    try: print_text = str(json.dumps(text, indent = 4, sort_keys = sort_keys))
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
                    elif 'ORANGE' in color.upper():  text_color = CGI_CLI.bcolors.YELLOW

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
        except: print(text)

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
            try: print_string += 'CGI_CLI.data[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4, sort_keys = True)))
            except: pass
        else: print_string += 'CLI_args = %s\nCGI_CLI.data = %s' % (str(sys.argv[1:]), str(json.dumps(CGI_CLI.data,indent = 4, sort_keys = True)))
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
                CGI_CLI.uprint("NON STANDARD CHARACTERS (>128) found [%s] in TEXT!" % (err_chars), color = 'orange', no_printall = not CGI_CLI.printall)
        return buff_read

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
        disconnect_timeout = 2, no_alive_test = None, rx_buffer = None):
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
            RCMD.printall = None
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
            RCMD.rx_buffer_size = 100000
            if rx_buffer:
                try: RCMD.rx_buffer_size = int(rx_buffer)
                except: pass

            RCMD.printall = CGI_CLI.printall if not printall else printall

            ### PING 1 = IS ALIVE TEST , IF NOT FIND IP ADDRESS ###############
            if RCMD.is_alive(device):
                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - ping DEVICE by name - OK.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')
                device_id = RCMD.DEVICE_HOST
            else:
                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - start.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

                RCMD.ip_address = RCMD.get_IP_from_vision(device)

                if CGI_CLI.timestamp and not RCMD.silent_mode:
                        CGI_CLI.uprint('RCMD.connect - after get_IP_from_vision.\n', \
                            no_printall = not CGI_CLI.printall, tag = 'debug')

                device_id = RCMD.ip_address

                if not no_alive_test:
                    for i_repeat in range(3):
                        if RCMD.is_alive(device_id): break
                    else:
                        CGI_CLI.uprint('DEVICE %s (ip=%s) is not ALIVE.' % \
                            (device, RCMD.ip_address), color = 'magenta')
                        return command_outputs

            if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - after pingtest.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

            ### SNMP DETECTION ################################################
            RCMD.router_os_by_snmp = RCMD.snmp_find_router_type(device_id)

            if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - after SNMP detection(%s).\n' % (str(RCMD.router_os_by_snmp)), \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

            ### START SSH CONNECTION ##########################################
            if not RCMD.silent_mode:
                CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                    %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.', \
                    color = 'gray', no_printall = not CGI_CLI.printall)
            try:
                ### ONE_CONNECT DETECTION #####################################
                RCMD.client = paramiko.SSHClient()

                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - before RCMD.client.set_missing_host_key_policy.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

                RCMD.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - before RCMD.client.connect.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

                #RCMD.client.connect(RCMD.DEVICE_HOST, port=int(RCMD.DEVICE_PORT), \
                RCMD.client.connect(device_id, port=int(RCMD.DEVICE_PORT), \
                    username=RCMD.USERNAME, password=RCMD.PASSWORD, \
                    banner_timeout = 15, \
                    ### AUTH_TIMEOUT MAKES PROBLEMS ON IPTAC1 ###
                    #auth_timeout = 10, \
                    timeout = RCMD.CONNECTION_TIMEOUT, \
                    look_for_keys = False)

                ### FIX - https://github.com/paramiko/paramiko/issues/175 ###
                RCMD.client.get_transport().window_size = 2147483647

                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - after RCMD.client.connect.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

                RCMD.ssh_connection = RCMD.client.invoke_shell()

                if CGI_CLI.timestamp and not RCMD.silent_mode:
                    CGI_CLI.uprint('RCMD.connect - after RCMD.client.invoke_shell.\n', \
                        no_printall = not CGI_CLI.printall, tag = 'debug')

                if RCMD.ssh_connection:
                    RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
                    if not RCMD.router_type: CGI_CLI.uprint('DEVICE_TYPE NOT DETECTED!', color = 'red')
                    elif RCMD.router_type in RCMD.KNOWN_OS_TYPES and not RCMD.silent_mode:
                        CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type), \
                            color = 'gray', no_printall = not CGI_CLI.printall)
            except Exception as e:
                #if not RCMD.silent_mode:
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
                #if not RCMD.silent_mode:
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
        sim_config = None, sim_all = None, ignore_prompt = None, \
        ignore_syntax_error = None, multiline_mode = None):
        """
        cmd_line - string, DETECTED DEVICE TYPE DEPENDENT
        sim_all  - simulate execution of all commands, not only config commands
                   used for ommit save/write in normal mode
        sim_config - simulate config commands
        long_lasting_mode - max connection timeout, no cmd timeout, no prompt discovery
        autoconfirm_mode - in case of interactivity send 'Y\n' on huawei ,'\n' on cisco
        multiline_mode - more commands in one block like: (cisco) cmd1CRLF!CRLFcmd2CRLF!
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
                        multiline_mode = multiline_mode, \
                        printall = printall)
                    if new_prompt: RCMD.DEVICE_PROMPTS.append(new_prompt)

            if not long_lasting_mode:
                if (printall or RCMD.printall) and not RCMD.silent_mode:
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
                        if (printall or RCMD.printall) and not RCMD.silent_mode:
                            CGI_CLI.uprint('\n</pre>\n', timestamp = 'no', raw = True, ommit_logging = True)
                        elif not RCMD.silent_mode:
                            CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
                else:
                    if not RCMD.silent_mode:
                        if (printall or RCMD.printall) and not RCMD.silent_mode:
                            CGI_CLI.uprint('\n', timestamp = 'no', ommit_logging = True)
                        elif not RCMD.silent_mode:
                            CGI_CLI.uprint(' . ', no_newlines = True, timestamp = 'no', ommit_logging = True)
            if not ignore_syntax_error:
                for line in last_output.splitlines():
                    if line.strip() == '^' and not RCMD.silent_mode:
                        CGI_CLI.uprint("\nSYNTAX ERROR in CMD: '%s' !\n" % (str(cmd_line)), timestamp = 'no', color = 'orange')
        return str(last_output)

    @staticmethod
    def run_commands(cmd_data = None, printall = None, conf = None, sim_config = None, \
        do_not_final_print = None , commit_text = None, submit_result = None , \
        long_lasting_mode = None, autoconfirm_mode = None, ignore_prompt = None, \
        ignore_syntax_error = None, multiline_mode = None):
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
                    if (printall or RCMD.printall) and not RCMD.silent_mode:
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
                        ignore_syntax_error = ignore_syntax_error,
                        multiline_mode = multiline_mode))
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
                        if RCMD.config_problem and not RCMD.silent_mode:
                            CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = CGI_CLI.result_tag, tag_id = 'submit-result', color = 'red')
                        elif not RCMD.silent_mode: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = CGI_CLI.result_tag, tag_id = 'submit-result', color = 'green')
                    else:
                        if RCMD.config_problem and not RCMD.silent_mode:
                            CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = CGI_CLI.result_tag, color = 'red')
                        elif not RCMD.silent_mode: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = CGI_CLI.result_tag, color = 'green')
        return command_outputs

    @staticmethod
    def __cleanup__():
        RCMD.output, RCMD.fp = None, None
        try:
            if RCMD.ssh_connection:
                if RCMD.use_module == 'netmiko': RCMD.ssh_connection.disconnect()
                elif RCMD.use_module == 'paramiko': RCMD.client.close()
                if RCMD.printall and not RCMD.silent_mode: CGI_CLI.uprint('DEVICE %s:%s DONE.' % \
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
                if RCMD.printall and not RCMD.silent_mode: CGI_CLI.uprint('DEVICE %s:%s DISCONNECTED.' % \
                    (RCMD.DEVICE_HOST, RCMD.DEVICE_PORT), color = 'gray')
                RCMD.ssh_connection = None
                time.sleep(RCMD.DISCONNECT_TIMEOUT)
        except: pass

    @staticmethod
    def ssh_send_command_and_read_output(chan, prompts, \
        send_data = str(), long_lasting_mode = None, \
        autoconfirm_mode = None, ignore_prompt = None, \
        multiline_mode = None, printall = True):
        '''
        autoconfirm_mode = True ==> CISCO - '\n', HUAWEI - 'Y\n'
        '''
        output, output2, new_prompt = str(), str(), str()
        exit_loop = False
        no_rx_data_counter_100msec, command_counter_100msec = 0, 0
        after_enter_counter_100msec, possible_prompts = 0, []
        no_multiline_traffic_counter_100msec = 0
        last_line_original, last_line_edited = str(), str()

        ### FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERED ###
        if chan.recv_ready():
            flush_buffer = chan.recv(RCMD.rx_buffer_size)
            time.sleep(0.3)
        chan.send(send_data + '\n')
        time.sleep(0.1)

        ### MAIN WHILE LOOP ###################################################
        while not exit_loop:
            if chan.recv_ready() or chan.recv_stderr_ready():
                ### RECEIVED DATA IMMEDIATE ACTIONS ###########################
                ### https://stackoverflow.com/questions/57615182/paramiko-why-is-reading-so-slow ###
                if multiline_mode: no_multiline_traffic_counter_100msec = 0
                no_rx_data_counter_100msec = 0
                buff = chan.recv(RCMD.rx_buffer_size)

                buff_read = CGI_CLI.decode_bytearray(buff)
                output += buff_read

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
                            CGI_CLI.uprint("AUTOCONFIRMATION INSERTED , EXIT !!", tag = 'warning')
                            break
                        else:
                            ### INTERACTIVE QUESTION --> GO AWAY ##############
                            exit_loop = True
                            CGI_CLI.uprint("AUTOCONFIRMATION QUESTION, EXIT !!", tag = 'warning')
                            break

                if exit_loop: break
            else:
                ### NOT RECEIVED ANY DATA #####################################
                buff_read = str()
                time.sleep(0.1)
                no_rx_data_counter_100msec += 1
                command_counter_100msec    += 1
                if after_enter_counter_100msec:
                    after_enter_counter_100msec += 1
                if multiline_mode: no_multiline_traffic_counter_100msec += 1
            ###################################################################


            ### PROMPT IN LAST LINE = PROPER END OF COMMAND ###############
            if not multiline_mode or multiline_mode and no_multiline_traffic_counter_100msec > 30:
                for actual_prompt in prompts:
                    if output.strip().endswith(actual_prompt) or \
                        (last_line_edited and last_line_edited.endswith(actual_prompt)) or \
                        (last_line_original and last_line_original.endswith(actual_prompt)):
                            exit_loop = True
                            break
                if exit_loop: break

            ### RECEIVED OR NOT RECEIVED DATA COMMON ACTIONS ##################
            if not long_lasting_mode:
                ### COMMAND TIMEOUT EXIT ######################################
                if command_counter_100msec > RCMD.CMD_TIMEOUT*10:
                    CGI_CLI.uprint("COMMAND TIMEOUT (%s sec) !!" % (RCMD.CMD_TIMEOUT*10), tag = 'warning')
                    exit_loop = True
                    break

            elif long_lasting_mode:
                ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ##############
                if not command_counter_100msec % 100:
                    if CGI_CLI.cgi_active:
                        CGI_CLI.uprint("<script>console.log('10s...');</script>", \
                            raw = True)
                        CGI_CLI.logtofile('[+10sec_MARK]\n')

                    ### printall or RCMD.printall
                    if not CGI_CLI.printall and not RCMD.silent_mode:
                        CGI_CLI.uprint(' _ ', no_newlines = True, \
                            timestamp = 'no', ommit_logging = True, printall = True)

            ### EXIT SOONER THAN CONNECTION TIMEOUT IF LONG LASTING OR NOT ####
            if command_counter_100msec + 100 > RCMD.CONNECTION_TIMEOUT*10:
                CGI_CLI.uprint("LONG LASTING COMMAND (%d sec) TIMEOUT!!" % (RCMD.CONNECTION_TIMEOUT*10), tag = 'warning')
                exit_loop = True
                break

            ### IGNORE NEW PROMPT AND GO AWAY #################################
            if ignore_prompt:
                time.sleep(1)
                CGI_CLI.uprint("PROMPT IGNORED, EXIT !!", tag = 'warning')
                exit_loop = True
                break

            ### PROMPT FOUND OR NOT - AFTER '\n' ##############################
            if after_enter_counter_100msec > 0:
                if last_line_original and last_line_original in possible_prompts:
                    new_prompt = last_line_original
                    exit_loop = True
                    break
                if after_enter_counter_100msec > 50:
                    CGI_CLI.uprint("(5 sec) after '\n' EXIT!!", \
                        tag = 'debug', no_printall = not CGI_CLI.printall)
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
                CGI_CLI.uprint("INSERTED '\n' after (10 sec no rx) DEVICE INACTIVITY!!", \
                    tag = 'debug', no_printall = not CGI_CLI.printall)
                time.sleep(0.1)
                after_enter_counter_100msec = 1
        return output, new_prompt

    @staticmethod
    def ssh_raw_detect_router_type(debug = None):
        ### DETECT DEVICE PROMPT FIRST
        def ssh_raw_detect_prompt(chan, debug = debug):
            output, buff, last_line, last_but_one_line = str(), str(), 'dummyline1', 'dummyline2'
            flush_buffer = chan.recv(RCMD.rx_buffer_size)
            del flush_buffer
            chan.send('\t \n\n')
            time.sleep(0.3)
            while not (last_line and last_but_one_line and last_line == last_but_one_line):
                buff = chan.recv(RCMD.rx_buffer_size)
                if len(buff)>0:
                    if debug: CGI_CLI.uprint('LOOKING_FOR_PROMPT:',last_but_one_line,last_line, color = 'grey')

                    output += CGI_CLI.decode_bytearray(buff).replace('\n{master}\n','')

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
            flush_buffer = chan.recv(RCMD.rx_buffer_size)
            del flush_buffer
            chan.send(command)
            time.sleep(0.3)
            output, exit_loop = '', False
            while not exit_loop:
                if debug: CGI_CLI.uprint('LAST_LINE:',prompts,last_line)
                buff = chan.recv(RCMD.rx_buffer_size)

                output += CGI_CLI.decode_bytearray(buff).replace('\n{master}\n','')

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

        if CGI_CLI.timestamp and not RCMD.silent_mode:
            CGI_CLI.uprint('RCMD.connect - before ssh_raw_detect_prompt.\n', \
                no_printall = not CGI_CLI.printall, tag = 'debug')

        prompt = ssh_raw_detect_prompt(RCMD.ssh_connection, debug=debug)

        if CGI_CLI.timestamp and not RCMD.silent_mode:
            CGI_CLI.uprint('RCMD.connect - after ssh_raw_detect_prompt(%s).\n' % (str(prompt)), \
                no_printall = not CGI_CLI.printall, tag = 'debug')

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
                no_printall = not CGI_CLI.printall, tag = 'debug')

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
        LCMD.printall = CGI_CLI.printall if not printall else printall

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



##############################################################################
#
# BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)
##############################################################################

# rcmd_data = {
    # 'cisco_ios':[],
    # 'cisco_xr':[],
    # 'juniper':[],
    # 'huawei':[],
    # 'linux':[],
# }
# lcmd_data = {
    # 'windows':['whoami'],
    # 'unix':['whoami'],
# }
##############################################################################

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

USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = None, css_style = None, json_api = True)

CGI_CLI.JSON_RESULTS['inputs'] = str(CGI_CLI.print_args(ommit_print = True))
CGI_CLI.JSON_RESULTS['success'] = 'OK'
CGI_CLI.JSON_RESULTS['logfile'] = 'No logfile.'
CGI_CLI.JSON_RESULTS['errors'] = str()




