#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, logging, base64, string
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
    class CGI_handle - Simple static class for handling CGI parameters and
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

    class ploglevel:
            ### PRINT & LOG ALL, BITWISE AND LOGIC IS USED ###

            ### PRINT
            PRINT_ALL          = 0b1111111100000000
            PRINT_JSON_RESULTS = 0b1000000000000000
            PRINT_TEXT_RESULTS = 0b0100000000000000
            PRINT_NORMAL       = 0b1110000000000000
            PRINT_DEBUG        = 0b1111111100000000

            ### LOG
            LOG_ALL            = 0b0000000011111111
            LOG_JSON_RESULTS   = 0b0000000010000000
            LOG_TEXT_RESULTS   = 0b0000000001000000
            LOG_NORMAL         = 0b0000000011100000
            LOG_DEBUG          = 0b0000000011111111

            ### & MASKS ###
            MASK_NO_PRINT      = 0b1100000011111111
            MASK_NO_LOG        = 0b1111111100000000
            MASK_NOTHING       = 0b0000000000000000
            MASK_DEFAULT       = 0b1100000011111111

            ALL                = 0b1111111111111111
            DEFAULT            = 0b1100000111111111


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
        parser.add_argument("--hash",
                            action = 'store', dest = "hash", default = str(),
                            help = "coded hash from iptac1 web")
        parser.add_argument("--device",
                            action = "store", dest = 'device',
                            default = str(),
                            help = "target router to access. For now supports only 1.")
        parser.add_argument("--post", action = "store_true",
                            help = "run Postcheck")
        parser.add_argument("--send_email",
                            action = "store_true", dest = 'send_email', default = None,
                            help = "send email with test result logs")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
        parser.add_argument("--timestamps",
                            action = "store_true", dest = 'timestamp', default = None,
                            help = "show timestamps")
        parser.add_argument("--json",
                            action = "store_true",
                            default = False,
                            dest = 'json_mode',
                            help = "json data output only, no other printouts")
        parser.add_argument("--json_headers",
                            action = "store_true",
                            default = False,
                            dest = 'json_headers',
                            help = "print json headers before data output")
        parser.add_argument("--target_sw_file",
                            action = "store", dest = 'target_sw_file',
                            default = str(),
                            help = "target sw file for os upgrade")
        parser.add_argument("--target_patch_path",
                            action = "store", dest = 'target_patch_path',
                            default = str(),
                            help = "target patch SMU's path for os upgrade")
        parser.add_argument("--read_only",
                            action = "store_true",
                            default = False,
                            dest = 'read_only',
                            help = "no fpd auto-upgrade, no inactive remove packages, no config changes")
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():
        logfile_name = copy.deepcopy(CGI_CLI.logfilename)

        ### PRINT RESULTS #############################################################
        CGI_CLI.print_results()

        ### SEND EMAIL WITH LOGFILE ###################################################
        if logfile_name and CGI_CLI.data.get("send_email"):
            #USERNAME = 'pnemec'
            CGI_CLI.send_me_email( \
                subject = str(logfile_name).replace('\\','/').split('/')[-1] if logfile_name else None, \
                file_name = str(logfile_name), username = USERNAME)

        ### def SEND EMAIL WITH ERROR/TRACEBACK LOGFILE TO SUPPORT ####################
        if traceback_found:
            CGI_CLI.send_me_email( \
                subject = 'TRACEBACK-' + logfile_name.replace('\\','/').\
                split('/')[-1] if logfile_name else str(),
                email_body = str(traceback_found),\
                file_name = logfile_name, username = 'pnemec')

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def hash_decrypt(text = None, key = None, iv = None):
        from Crypto.Cipher import AES
        if not text: return str()
        if not key:
            key = base64.b64decode(b'cGFpaVVORE9wYWlpVU5ET3BhaWlVTkRPcGFpaVVORE8=')
        try:
            key = str.encode(key)
        except: pass
        if not iv: iv = key[:16]
        assert len(key) == 32
        assert len(iv) == 16
        ciphertext = base64.b64decode(text)
        aes = AES.new(key, AES.MODE_CBC, iv)
        plain_text = aes.decrypt(ciphertext).decode('utf-8').strip()
        readable_text = str()
        for c in plain_text:
            if c in string.printable: readable_text += c
        return readable_text

    @staticmethod
    def get_credentials(text = None):
        username, password = str(), str()
        if text:
            strtext = text[19:]
            try:
                username, password = strtext.split('#####')
            except: pass
        return username, password

    @staticmethod
    def init_cgi(chunked = None, css_style = None, newline = None, \
        timestamp = None, disable_page_reload_link = None, no_title = None, \
        json_mode = None, json_headers = None, read_only = None, fake_success = None):
        """
        """
        try: CGI_CLI.sys_stdout_encoding = sys.stdout.encoding
        except: CGI_CLI.sys_stdout_encoding = None
        if not CGI_CLI.sys_stdout_encoding: CGI_CLI.sys_stdout_encoding = 'UTF-8'
        CGI_CLI.MENU_DISPLAYED = False
        CGI_CLI.FAKE_SUCCESS = fake_success
        CGI_CLI.READ_ONLY = read_only
        CGI_CLI.JSON_MODE = json_mode
        CGI_CLI.JSON_HEADERS = json_headers
        CGI_CLI.PRINT_JSON_RESULTS = False
        CGI_CLI.print_results_printed = None
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
            if value and variable == "submit": CGI_CLI.submit_form = value
            if value and variable == "username": CGI_CLI.USERNAME = value
            if value and variable == "password": CGI_CLI.PASSWORD = value
            if value and variable == "json_mode": CGI_CLI.JSON_MODE = value
            if value and variable == "print_json_results": CGI_CLI.PRINT_JSON_RESULTS = value
            if value and variable == "json_headers": CGI_CLI.JSON_HEADERS = value
            if value and variable == "read_only": CGI_CLI.READ_ONLY = value
            if value and variable == "hash":
                CGI_CLI.USERNAME, CGI_CLI.PASSWORD = CGI_CLI.get_credentials(CGI_CLI.hash_decrypt(value))

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

        ### CLI PARSER ########################################################
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active:
            cli_data = vars(CGI_CLI.args)
            for key in cli_data.keys():
                variable = str(key)
                try: value = cli_data.get(variable)
                except: value = None
                if variable and value and \
                    not variable in ["username", "password"]:
                    CGI_CLI.data[variable] = value
                if value and variable == "username": CGI_CLI.USERNAME = value
                if value and variable == "password": CGI_CLI.PASSWORD = value
                if value and variable == "json_mode": CGI_CLI.JSON_MODE = value
                if value and variable == "print_json_results": CGI_CLI.PRINT_JSON_RESULTS = value
                if value and variable == "json_headers": CGI_CLI.JSON_HEADERS = value
                if value and variable == "read_only": CGI_CLI.READ_ONLY = value
                if value and variable == "hash":
                    CGI_CLI.USERNAME, CGI_CLI.PASSWORD = CGI_CLI.get_credentials(CGI_CLI.hash_decrypt(value))

        ### CGI_CLI.data PARSER ###############################################
        for key in CGI_CLI.data.keys():
            variable = str(key)
            value = CGI_CLI.data.get(variable)

            if variable == "printall" and (str(value).upper() == 'NO' or not value):
                CGI_CLI.printall = False
            elif variable == "printall":
                CGI_CLI.printall = True
            if value and variable == "timestamp" and value: CGI_CLI.timestamp = True
            if value and variable == "cusername": CGI_CLI.USERNAME = value.decode('base64','strict')
            if value and variable == "cpassword": CGI_CLI.PASSWORD = value.decode('base64','strict')
            if value and variable == "json_mode": CGI_CLI.JSON_MODE = value
            if value and variable == "print_json_results": CGI_CLI.PRINT_JSON_RESULTS = value
            if value and variable == "json_headers": CGI_CLI.JSON_HEADERS = value
            if value and variable == "read_only": CGI_CLI.READ_ONLY = value
            if value and variable == "hash":
                CGI_CLI.USERNAME, CGI_CLI.PASSWORD = CGI_CLI.get_credentials(CGI_CLI.hash_decrypt(value))

        ### DECIDE - CLI OR CGI MODE ##########################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent and not CGI_CLI.JSON_MODE:
            CGI_CLI.cgi_active = True

        ### HTML HEADERS ######################################################
        if CGI_CLI.cgi_active:
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
        elif CGI_CLI.JSON_MODE and CGI_CLI.JSON_HEADERS:
            ### JSON HEADERS ##################################################
            CGI_CLI.content_type_line = 'Content-type:application/vnd.api+json%s' % (CGI_CLI.newline)
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
        if not CGI_CLI.PASSWORD and not CGI_CLI.cgi_active and not CGI_CLI.JSON_MODE:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
            getpass_done = True
        ### FORCE GAIN/OVERWRITE USERNAME AND PASSWORD FROM CLI GETPASS #######
        if CGI_CLI.data.get('getpass') and not getpass_done and not CGI_CLI.cgi_active and not CGI_CLI.JSON_MODE:
            CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
        ### WINDOWS DOES NOT SUPPORT LINUX COLORS - SO DISABLE IT #############
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): CGI_CLI.bcolors = CGI_CLI.nocolors
        CGI_CLI.cgi_save_files()
        CGI_CLI.JSON_RESULTS['inputs'] = str(CGI_CLI.print_args(ommit_print = True))
        CGI_CLI.JSON_RESULTS['logfile'] = str()
        CGI_CLI.JSON_RESULTS['errors'] = str()
        CGI_CLI.JSON_RESULTS['warnings'] = str()
        CGI_CLI.JSON_RESULTS['result'] = str()
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
                            except Exception as e:
                                CGI_CLI.add_result('PROBLEM[' + str(e) + ']', 'fatal')

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
                replace('<br/>','\n').replace('<br>','\n').\
                replace('&lt;','<').replace('&gt;','>').\
                replace('&nbsp;',' ').\
                replace('&quot;','"').replace('&apos;',"'"))
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
            if printall and not CGI_CLI.JSON_MODE:
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
    def add_result(text = None, type = None, print_now = None):
        if text: CGI_CLI.result_list.append([text, type])
        color = None
        if type == 'fatal': color = 'magenta'
        elif type == 'error': color = 'red'
        elif type == 'warning': color = 'orange'
        if print_now:
            CGI_CLI.uprint(text , tag = 'h3', color = color)
        else:
            CGI_CLI.uprint(text , tag = 'h3', color = color, \
                no_printall = not CGI_CLI.printall)

    @staticmethod
    def print_results(raw_log = None, sort_keys = None):

        print_text = None

        for text, type in CGI_CLI.result_list:
            if type == 'error' or type == 'fatal':
                CGI_CLI.JSON_RESULTS['errors'] += '[%s] ' % (text)
            elif type == 'warning':
                CGI_CLI.JSON_RESULTS['warnings'] += '[%s] ' % (text)

        if len(CGI_CLI.JSON_RESULTS.get('errors',str())) == 0:
            if len(CGI_CLI.JSON_RESULTS.get('warnings',str())) == 0:
                CGI_CLI.JSON_RESULTS['result'] = 'success'
            else:
                #CGI_CLI.JSON_RESULTS['result'] = 'warnings'
                CGI_CLI.JSON_RESULTS['result'] = 'success'
        else: CGI_CLI.JSON_RESULTS['result'] = 'failure'

        if CGI_CLI.JSON_RESULTS.get('precheck_logfile',str()):
             CGI_CLI.JSON_RESULTS['precheck_link'] = CGI_CLI.make_loglink(CGI_CLI.JSON_RESULTS.get('precheck_logfile',str()))

        ### DEBUG FAKE_SUCCESS ###
        if CGI_CLI.FAKE_SUCCESS: CGI_CLI.JSON_RESULTS['result'] = 'success'

        if CGI_CLI.logfilename:
            CGI_CLI.JSON_RESULTS['logfile_link'] = CGI_CLI.make_loglink(CGI_CLI.logfilename)

        if not CGI_CLI.print_results_printed:
            ### ALL MODES - CGI, JSON, CLI ####################################
            if isinstance(CGI_CLI.JSON_RESULTS, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = str(json.dumps(CGI_CLI.JSON_RESULTS, indent = 2, sort_keys = sort_keys))
                except Exception as e:
                    CGI_CLI.print_chunk('{"errors": "JSON_PROBLEM[' + str(e) + str(CGI_CLI.JSON_RESULTS) + ']"}', printall = True)

            if print_text:
                ### PRINT DIFFERENTLY ###
                if CGI_CLI.cgi_active and CGI_CLI.PRINT_JSON_RESULTS:
                    CGI_CLI.uprint('<br/>\n<pre>\nCGI_CLI.JSON_RESULTS = ' + print_text + \
                        '\n</pre>\n', raw = True, ommit_logging = True)
                elif CGI_CLI.JSON_MODE: print(print_text)
                elif CGI_CLI.PRINT_JSON_RESULTS: print(print_text)

                ### LOG JSON IN EACH CASE ###
                if CGI_CLI.cgi_active: CGI_CLI.logtofile('<br/>\n<pre>\n', raw_log = True, ommit_timestamp = True)
                CGI_CLI.logtofile(msg = 'CGI_CLI.JSON_RESULTS = ' + \
                    print_text, raw_log = True, ommit_timestamp = True)
                if CGI_CLI.cgi_active: CGI_CLI.logtofile('\n</pre>\n', raw_log = True, ommit_timestamp = True)

            ### CLI & CGI MODES ###############################################
            if not CGI_CLI.JSON_MODE:
                if len(CGI_CLI.result_list) > 0:
                    CGI_CLI.uprint('\n\nRESULT SUMMARY:', tag = 'h1')

                ### text, type ###
                for text, type in CGI_CLI.result_list:
                    color = None
                    if type == 'fatal': color = 'magenta'
                    elif type == 'error': color = 'red'
                    elif type == 'warning': color = 'orange'
                    CGI_CLI.uprint(text , tag = 'h3', color = color)
                CGI_CLI.uprint('\n')

                res_color = None
                if CGI_CLI.JSON_RESULTS.get('result',str()) == 'success': res_color = 'green'
                if CGI_CLI.JSON_RESULTS.get('result',str()) == 'warnings': res_color = 'orange'
                if CGI_CLI.JSON_RESULTS.get('result',str()) == 'failure': res_color = 'red'

                if not CGI_CLI.MENU_DISPLAYED:
                    CGI_CLI.uprint("RESULT: " + CGI_CLI.JSON_RESULTS.get('result', str()),\
                        tag = 'h1', color = res_color)

            ### LOGFILE LINK ##############################################
            logfile_name = copy.deepcopy(CGI_CLI.logfilename)
            logfilename_link = CGI_CLI.make_loglink(CGI_CLI.logfilename)
            if CGI_CLI.cgi_active:
                if CGI_CLI.logfilename:
                    CGI_CLI.uprint('<p style="color:blue;"> ==> File <a href="%s" target="_blank" style="text-decoration: none">%s</a> created.</p>' \
                        % (logfilename_link, logfile_name), raw = True, color = 'blue', printall = True)
                    CGI_CLI.uprint('<br/>', raw = True)
                if CGI_CLI.timestamp:
                    CGI_CLI.uprint('END.\n', no_printall = not CGI_CLI.printall, tag = 'debug')
                if not CGI_CLI.disable_page_reload_link: CGI_CLI.html_selflink()
            elif CGI_CLI.JSON_MODE:
                pass
            else:
                if CGI_CLI.logfilename:
                    CGI_CLI.uprint(' ==> File %s created.\n\n' % (logfilename_link),printall = True)
            CGI_CLI.set_logfile(logfilename = None)

        CGI_CLI.print_results_printed = True


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
                        if str(tag) == 'fatal':
                            CGI_CLI.print_chunk('<%s style="color:magenta;">'%(tag),\
                                raw_log = True, printall = printall_yes)
                        if str(tag) == 'error':
                            CGI_CLI.print_chunk('<%s style="color:red;">'%(tag),\
                                raw_log = True, printall = printall_yes)
                        if str(tag) == 'warning':
                            CGI_CLI.print_chunk('<%s style="color:orange;">'%(tag),\
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

                if tag == 'fatal': text_color = 'FATAL: ' + CGI_CLI.bcolors.YELLOW
                if tag == 'error': text_color = 'ERROR: ' + CGI_CLI.bcolors.YELLOW
                if tag == 'warning': text_color = 'WARNING: ' + CGI_CLI.bcolors.YELLOW
                if tag == 'debug': text_color = 'DEBUG: ' + CGI_CLI.bcolors.CYAN

                CGI_CLI.print_chunk("%s%s%s%s%s" % \
                    (text_color, timestamp_string, print_name, print_text, \
                    CGI_CLI.bcolors.ENDC if text_color else str()), \
                    raw_log = True, printall = printall_yes, no_newlines = no_newlines, \
                    ommit_logging = ommit_logging)

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
            if CGI_CLI.cgi_active:
                CGI_CLI.print_chunk('<p id="scriptend"></p>', raw_log = True, printall = True)
                CGI_CLI.print_chunk('<br/><a href = "./%s">PAGE RELOAD</a>' % (pyfile), ommit_logging = True, printall = True)

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
        print_string += 'CGI_CLI.cgi_active[%s], CGI_CLI.JSON_MODE[%s], CGI_CLI.submit_form[%s], CGI_CLI.chunked[%s]\n' % \
            (str(CGI_CLI.cgi_active), str(CGI_CLI.JSON_MODE), str(CGI_CLI.submit_form), str(CGI_CLI.chunked))
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
    def make_loglink(file = None):
        logviewer = copy.deepcopy(file)
        if file:
            iptac_server = str(subprocess.check_output('hostname').decode('utf-8')).strip()
            if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
            else: urllink = 'https://%s/cgi-bin/' % (iptac_server)
            if urllink: logviewer = '%slogviewer.py?logfile=%s' % (urllink, copy.deepcopy(file))
            else: logviewer = './logviewer.py?logfile=%s' % (copy.deepcopy(file))
        return logviewer





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
                    if not RCMD.router_type:
                        text = 'DEVICE_TYPE NOT DETECTED!'
                        CGI_CLI.add_result(text, 'fatal')
                    elif RCMD.router_type in RCMD.KNOWN_OS_TYPES and not RCMD.silent_mode:
                        CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type), \
                            color = 'gray', no_printall = not CGI_CLI.printall)
            except Exception as e:
                text = str(device) + ' CONNECTION_PROBLEM[' + str(e) + ']'
                CGI_CLI.add_result(text, 'fatal')
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
                text = str(device) + ' CONNECTION_PROBLEM[' + str(e) + ']'
                CGI_CLI.add_result(text, 'fatal')
            finally:
                if disconnect: RCMD.disconnect()
        else:
            text = 'DEVICE NOT INSERTED!'
            CGI_CLI.add_result(text, 'fatal')
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
                        text = '\nCONFIGURATION PROBLEM FOUND: %s' % (rcmd_output)
                        CGI_CLI.add_result(text, 'warning')
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
                    if CGI_CLI.cgi_active:
                        CGI_CLI.logtofile('%s' % (buff_read), raw_log = True, ommit_timestamp = True)
                    else: CGI_CLI.logtofile('%s' % (buff_read), ommit_timestamp = True)

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
                            CGI_CLI.uprint("AUTOCONFIRMED.", tag = 'debug', no_printall = not CGI_CLI.printall)
                            break
                        else:
                            ### INTERACTIVE QUESTION --> GO AWAY ##############
                            exit_loop = True
                            CGI_CLI.uprint("AUTOCONFIRMATION QUESTION.", tag = 'debug', no_printall = not CGI_CLI.printall)
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
                    CGI_CLI.uprint("COMMAND TIMEOUT (%s sec) !!" % (RCMD.CMD_TIMEOUT*10), tag = 'warning', no_printall = not CGI_CLI.printall)
                    exit_loop = True
                    break

            elif long_lasting_mode:
                ### KEEPALIVE CONNECTION, DEFAULT 300sec TIMEOUT ##############
                if not command_counter_100msec % 100:
                    if CGI_CLI.cgi_active:
                        CGI_CLI.uprint("<script>console.log('10s...');</script>", \
                            raw = True, ommit_logging = True)
                        #CGI_CLI.logtofile('[+10sec_MARK]\n')

                    ### printall or RCMD.printall
                    if not CGI_CLI.printall and not RCMD.silent_mode:
                        CGI_CLI.uprint(' _ ', no_newlines = True, \
                            timestamp = 'no', ommit_logging = True, printall = True)

            ### EXIT SOONER THAN CONNECTION TIMEOUT IF LONG LASTING OR NOT ####
            if command_counter_100msec + 100 > RCMD.CONNECTION_TIMEOUT*10:
                CGI_CLI.uprint("LONG LASTING COMMAND (%d sec) TIMEOUT!!" % (RCMD.CONNECTION_TIMEOUT*10), tag = 'warning', no_printall = not CGI_CLI.printall)
                exit_loop = True
                break

            ### IGNORE NEW PROMPT AND GO AWAY #################################
            if ignore_prompt:
                time.sleep(1)
                CGI_CLI.uprint("PROMPT IGNORED, EXIT !!", tag = 'debug', no_printall = not CGI_CLI.printall)
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
            local_command = 'curl -u ${CURL_AUTH_STRING} -m 5 %s' % (url)
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
            snmp_req = "snmpget -v1 -c " + SNMP_COMMUNITY + " -t 1 " + host + " sysDescr.0"
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







###############################################################################

def generate_logfilename(prefix = None, USERNAME = None, pre_suffix = None, \
    suffix = None, directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(DIR,'logs')
    if not os.path.exists(LOGDIR): os.makedirs(LOGDIR)
    if os.path.exists(LOGDIR):
        if not prefix: filename_prefix = os.path.join(LOGDIR,'device')
        else: filename_prefix = str(prefix)
        if not suffix: filename_suffix = 'log'
        else: filename_suffix = str(suffix)
        if pre_suffix: filename_pre_suffix = str(pre_suffix)
        else: filename_pre_suffix = str()
        now = datetime.datetime.now()
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s%s.%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second, sys.argv[0].replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/').split('/')[-1],
            USERNAME,
            filename_pre_suffix,
            filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath

###############################################################################

def find_last_logfile(prefix = None, USERNAME = None, suffix = None, directory = None, \
    latest = None , action_text = None):
    log_file = str()
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(DIR,'logs')
    if not prefix: use_prefix = str()
    else: use_prefix = prefix
    if latest:
        list_shut_files = glob.glob(os.path.join(LOGDIR, use_prefix.replace(':','_').replace('.','_')) \
            + '*' + sys.argv[0].replace('.py','').replace('./','').replace(':','_').replace('.','_').replace('\\','/').split('/')[-1] \
            + '*' + '-' + suffix)
    else:
        list_shut_files = glob.glob(os.path.join(LOGDIR, use_prefix.replace(':','_').replace('.','_')) \
            + '*' + sys.argv[0].replace('.py','').replace('./','').replace(':','_').replace('.','_').replace('\\','/').split('/')[-1] \
            + '*' + USERNAME + '-' + suffix)
    if len(list_shut_files) == 0:
        text = " ... Can't find any %s session log file!" % (action_text if action_text else str())
        CGI_CLI.add_result(text, 'fatal')
    else:
        most_recent_shut = list_shut_files[0]
        for item in list_shut_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_shut)):
                most_recent_shut = item
        log_file = most_recent_shut
    if log_file: CGI_CLI.uprint('FOUND LAST %s LOGFILE: %s' % (action_text.upper() if action_text else str(), str(log_file)), tag = 'debug', no_printall = not CGI_CLI.printall)
    return log_file


###############################################################################

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
            ### file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
            file_types = ['9k', 'SMU/*.tar']
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


###############################################################################


def detect_hw(device = None):
    hw_info = {}

    if not device: return hw_info

    cmd = {
              "cisco_ios":['show version'],
              "cisco_xr":['show version', 'show instal active summary'],
              "huawei":['display version'],
              "juniper":['show version']
          }

    hw_info['device'] = copy.deepcopy(str(device))

    results = RCMD.run_commands(cmd)
    result = results[0]

    if RCMD.router_type == 'cisco_ios':
        hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
        hw_info['hw_brand'] = 'CISCO'
        hw_info['drive_string'] = 'bootflash:'

    elif RCMD.router_type == 'cisco_xr':
        hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
        hw_info['hw_brand'] = 'CISCO'
        hw_info['drive_string'] = 'harddisk:'
        if '-x64-' in results[1]: hw_info['x64'] = True
        else: hw_info['x64'] = False

    elif RCMD.router_type == 'huawei':
        hw_info['sw_version'] = result.split('software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(' version information:')[0].splitlines()[-1].strip()
        hw_info['hw_brand'] = 'HUAWEI'
        hw_info['drive_string'] = 'cfcard:'

    elif RCMD.router_type == 'juniper':
        hw_info['sw_version'] = result.split('Junos: ')[1].split()[0].strip()
        hw_info['hw_type'] = result.split('Model: ')[1].split()[0].strip()
        hw_info['hw_brand'] = 'JUNIPER'
        hw_info['drive_string'] = 're0:'

    return hw_info

##############################################################################

def check_data_content(where = None, what_yes_in = None, what_not_in = None, \
    exact_value_yes = None, lower_than = None, higher_than = None, equals_to = None,
    warning = None, ignore_data_existence = None):
    """
    multiple tests in once are possible
    what_yes_in - string = if occurs in where then OK.
    what_not_in - list = if all items from list occurs, then FAIL. Otherwise OK.
    what_not_in - string = if string occurs in text, then FAIL.
    """
    local_check_interface_result_ok, Alarm_text = 0, []

    key_exists, where_value, text = False, str(), str()
    try:
        where_value = eval('%s' % (str(where)))
        key_exists = True
    except: pass

    if key_exists: pass
    else:
        if ignore_data_existence: pass
        else:
            text = "DATA '%s' DOES NOT EXISTS!" % (where)
            CGI_CLI.add_result(text, 'warning')
            CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)
        return None

    ### FLOAT ZERO WORKARROUND ###
    if str(lower_than) and str(lower_than) != 'None':
        try:
            if float(where_value) < float(lower_than):
                text = "CHECK['%s'(%s) < '%.2f'] = OK" % (where, str(where_value), float(lower_than))
            else:
                if warning:
                    text = "CHECK['%s'(%s) < '%.2f'] = WARNING" % (where, str(where_value), float(lower_than))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s'(%s) < '%.2f'] = NOT OK" % (where, str(where_value), float(lower_than))
                    CGI_CLI.add_result(text, 'error')
        except: text = "CHECK['%s'(%s) < '%s'] = NaN" % (where, str(where_value), str(lower_than))
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)

    ### FLOAT ZERO WORKARROUND ###
    if str(higher_than) and str(higher_than) != 'None':
        try:
            if float(where_value) > float(higher_than):
                text = "CHECK['%s'(%s) > '%.2f'] = OK" % (where, str(where_value), float(higher_than))
            else:
                if warning:
                    text = "CHECK['%s'(%s) > '%.2f'] = WARNING" % (where, str(where_value), float(higher_than))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s'(%s) > '%.2f'] = NOT OK" % (where, str(where_value), float(higher_than))
                    CGI_CLI.add_result(text, 'error')
        except: text = "CHECK['%s'(%s) > '%s'] = NaN\n" % (where, str(where_value), str(higher_than))
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)

    ### FLOAT ZERO WORKARROUND ###
    if str(equals_to) and str(equals_to) != 'None':
        try:
            if float(where_value) > float(equals_to):
                text = "CHECK['%s'(%s) == '%.2f'] = OK" % (where, str(where_value), float(equals_to))
            else:
                if warning:
                    text = "CHECK['%s'(%s) == '%.2f'] = WARNING" % (where, str(where_value), float(equals_to))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s'(%s) == '%.2f'] = NOT OK" % (where, str(where_value), float(equals_to))
                    CGI_CLI.add_result(text, 'error')
        except: text = "CHECK['%s'(%s) == '%s'] = NaN\n" % (where, str(where_value), str(equals_to))
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)

    if exact_value_yes:
        if str(exact_value_yes).upper() == str(where_value).upper():
            text = "CHECK['%s' == '%s'(%s)] = OK" % (exact_value_yes, where, str(where_value))
        else:
            if warning:
                text = "CHECK['%s' == '%s'(%s)] = WARNING" % (exact_value_yes, where, str(where_value))
                CGI_CLI.add_result(text, 'warning')
            else:
                text = "CHECK['%s' == '%s'(%s)] = NOT OK" % (exact_value_yes, where, str(where_value))
                CGI_CLI.add_result(text, 'error')
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)

    if what_yes_in:
        if isinstance(where, (list,tuple)):
            if what_yes_in in where_value:
                text = "CHECK['%s' in '%s'(%s)] = OK" % (what_yes_in, where, str(where_value))
            else:
                if warning:
                    text = "CHECK['%s' in '%s'(%s)] = WARNING" % (what_yes_in, where, str(where_value))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s' in '%s'(%s)] = NOT OK" % (what_yes_in, where, str(where_value))
                    CGI_CLI.add_result(text, 'error')
        else:
            if str(what_yes_in).upper() in str(where_value).upper():
                text = "CHECK['%s' in '%s'(%s)] = OK" % (what_yes_in, where, str(where_value))
            else:
                if warning:
                    text = "CHECK['%s' in '%s'(%s)] = WARNING" % (what_yes_in, where, str(where_value))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s' in '%s'(%s)] = NOT OK" % (what_yes_in, where, str(where_value))
                    CGI_CLI.add_result(text, 'error')
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)

    if what_not_in:
        if isinstance(what_not_in, (list,tuple)):
            for item in what_not_in:
                if item.upper() in where_value.upper():
                    local_check_interface_result_ok += 1
                    Alarm_text.append("'%s' not in '%s'(%s)" % (item, where, str(where_value)))
            ### ALL FAIL LOGIC ###
            if local_check_interface_result_ok == len(what_not_in):
                if warning:
                    text = "CHECK[" + ' AND '.join(Alarm_text) + '] = WARNING'
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK[" + ' AND '.join(Alarm_text) + '] = NOT OK'
                    CGI_CLI.add_result(text, 'error')
            else: text = "CHECK[ ['%s'] not in '%s'] = OK" % (','.join(what_not_in), where)
        else:
            if str(what_not_in).upper() in str(where_value).upper():
                if warning:
                    text = "CHECK['%s' not in '%s'(%s)] = WARNING" % (str(what_not_in), where, str(where_value))
                    CGI_CLI.add_result(text, 'warning')
                else:
                    text = "CHECK['%s' not in '%s'(%s)] = NOT OK" % (str(what_not_in), where, str(where_value))
                    CGI_CLI.add_result(text, 'error')
            else: text = "CHECK['%s' not in '%s'(%s)] = OK" % (str(what_not_in), where, str(where_value))
        CGI_CLI.logtofile(text + '\n', ommit_timestamp = True)


##############################################################################

def read_section_from_logfile(section = None, logfile = None, pre_tag = None):
    """text and html logs are supported, logging of timestamps needed"""
    text, whole_file = str(), str()

    if section and logfile:
        with open(logfile, 'r') as rfile:
            whole_file = rfile.read()

    ### first try - section split by '@20' timestamp ###
    if whole_file and section:
        try: text = whole_file.split(section)[1].split('@20')[0].strip().\
            replace('<p>','').replace('<pre>','').replace('</p>','').\
            replace('</pre>','').replace('<br/>','').replace('<br>','')
        except: pass

        ### delete debug html tags ###
        for i in range(len(text.split('<debug')) - 1):
            if '<debug' in text:
                try: r_text = '<debug' + text.split('<debug')[1].split('</debug>')[0] + '</debug>'
                except: r_text = str()
                if r_text: text = text.replace(r_text,'')

        if '.htmlog' in str(logfile):
            text = CGI_CLI.html_deescape(text = text, pre_tag = pre_tag)

        ### workarround for text mode log, split section by REMOTE COMMAND ###
        elif 'REMOTE_COMMAND:' in text:
            try: text = text.split('REMOTE_COMMAND:')[0].strip()
            except: pass

        ### workarround for CLI color mode ###
        text = text.replace('\r','')
        for splittext in ['FATAL: ', 'ERROR: ', 'WARNING: ', 'DEBUG: ']:
            for i in range(len(text.split(splittext)) - 1):
                r_text = str()
                if splittext in text and '\u001b[0m' in text:
                    try: r_text = splittext + text.split(splittext)[1].split('\u001b[0m')[0]
                    except: pass
                if splittext in text:
                    try: r_text = splittext + text.split(splittext)[1].splitlines()[0]
                    except: pass
                if r_text:
                    text = text.replace(r_text,'').replace('\n\n','\n')
    return text

##############################################################################
# print(read_section_from_logfile('REMOTE_COMMAND: show int description | exclude "admin-down"', \
    # '/var/www/cgi-bin/logs/PARTR0-2020124-090556-sw_upgrade_pre_post_checker-mkrupa-pre.htmlog'))
# sys.exit(0)


##############################################################################
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


default_problemline_list   = []
default_ignoreline_list    = [r' MET$', r' UTC$']
default_linefilter_list    = []
default_compare_columns    = []
default_printalllines_list = []

bcolors = nocolors

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
    note = None,
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





##############################################################################
#
# def BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)
##############################################################################
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


    ### GLOBAL VARIABLES AND SETTINGS #########################################
    logging.raiseExceptions = False
    goto_webpage_end_by_javascript = str()
    traceback_found = None
    logfilename = str()
    test_mode = None
    asr_admin_string = str()
    precheck_file = str()

    SCRIPT_ACTION = str()

    USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = None, css_style = CSS_STYLE, \
        json_mode = False, read_only = True, fake_success = True)

    LCMD.init()

    CGI_CLI.timestamp = CGI_CLI.data.get("timestamps")
    printall = CGI_CLI.data.get("printall")

    target_patch_path = CGI_CLI.data.get('target_patch_path',str()).replace('[','').replace(']','').strip()
    target_sw_file    = CGI_CLI.data.get('target_sw_file',str()).replace('[','').replace(']','').strip()

    ### def KILLING APLICATION PROCESS ########################################
    if CGI_CLI.data.get('submit',str()) == 'STOP' and CGI_CLI.data.get('pidtokill'):
        LCMD.run_commands({'unix':['kill %s' % (CGI_CLI.data.get('pidtokill',str()))]}, printall = None)
        CGI_CLI.uprint('PID%s stopped.' % (CGI_CLI.data.get('pidtokill',str())))
        sys.exit(0)

    if CGI_CLI.data.get("test-version",str()) == 'test-mode' \
        or CGI_CLI.data.get("test-version",str()) == 'test mode':
            test_mode = True

    if '_test' in CGI_CLI.get_scriptname():
        test_mode = True

    device_list = []
    devices_string = CGI_CLI.data.get("device",str())
    if devices_string:
        if ',' in devices_string:
            device_list = [ dev_mix_case.upper() for dev_mix_case in devices_string.split(',') ]
        else: device_list = [devices_string.upper()]

    ### TESTSERVER WORKAROUND #################################################
    iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()

    if iptac_server == 'iptac5': urllink = 'https://10.253.58.126/cgi-bin/'
    else: urllink = 'https://%s/cgi-bin/' % (iptac_server)


    ### START PRINTING AND LOGGING ############################################
    changelog = 'https://github.com/peteneme/pyxWorks/commits/master/router_sw_update/check_ph.py'

    SCRIPT_NAME = 'SW UPDATE PRE/POST CHECK TOOL'

    if CGI_CLI.cgi_active:
        CGI_CLI.uprint('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s)</a>%s</h1>' % \
            (SCRIPT_NAME, changelog, CGI_CLI.VERSION(), CGI_CLI.STOP_APPLICATION_BUTTON), raw = True)

    else: CGI_CLI.uprint('%s (v.%s)' % (SCRIPT_NAME,CGI_CLI.VERSION()), \
              tag = 'h1', color = 'blue')
    CGI_CLI.print_args()


    ### def HTML MENUS DISPLAYED ONLY IN CGI MODE #############################
    MULTIPLE_SELFMENUS = False
    if CGI_CLI.cgi_active and len(device_list) == 0 and \
        (not CGI_CLI.submit_form or \
        MULTIPLE_SELFMENUS and CGI_CLI.submit_form in CGI_CLI.self_buttons):
        CGI_CLI.MENU_DISPLAYED = True
        ### OTHER SUBMIT BUTTONS THAN OK ALLOWS "REMOTE" CGI CONTROL ##########

        interface_menu_list = []
        interface_menu_list.append('<br/>')
        interface_menu_list.append({'text':'device'})
        interface_menu_list.append('<br/>')
        interface_menu_list.append({'text':'target_sw_file'})
        interface_menu_list.append('<br/>')
        interface_menu_list.append({'text':'target_patch_path'})
        interface_menu_list.append('<br/>')
        interface_menu_list.append('<br/>')

        if not (USERNAME and PASSWORD):
            interface_menu_list.append('<authentication>')
            interface_menu_list.append('LDAP authentication (required):')
            interface_menu_list.append('<br/>')
            interface_menu_list.append('<br/>')
            interface_menu_list.append({'text':'username'})
            interface_menu_list.append('<br/>')
            interface_menu_list.append({'password':'password'})
            interface_menu_list.append('<br/>')
            interface_menu_list.append({'text':'hash'})
            interface_menu_list.append('<br/>')
            interface_menu_list.append('</authentication>')

        CGI_CLI.formprint(interface_menu_list + [ \
            {'radio':['precheck','postcheck']},'<br/>',\
            {'checkbox':'json_mode'}, '<br/>',\
            {'checkbox':'json_headers'}, '<br/>',\
            {'checkbox':'read_only'}, '<br/>',\
            {'checkbox':'print_json_results'}, '<br/>',\
            '<br/><b><u>',{'checkbox':'send_email'},'</u></b><br/>',\
            {'checkbox':'chunked_mode'}, '<br/>',\
            {'checkbox':'timestamps'}, '<br/>',\
            {'checkbox':'printall'},'<br/>','<br/>'],\
            submit_button = CGI_CLI.self_buttons[0], \
            pyfile = None, tag = None, color = None)

        ### EXIT AFTER MENU PRINTING ######################################
        sys.exit(0)
    else:
        ### READ SCRIPT ACTION ###
        SCRIPT_ACTION = 'pre'
        if (CGI_CLI.data.get("post") or CGI_CLI.data.get("radio")):
            if CGI_CLI.data.get("radio") == 'precheck': SCRIPT_ACTION = 'pre'
            if CGI_CLI.data.get("radio") == 'postcheck' or CGI_CLI.data.get("post"): SCRIPT_ACTION = 'post'

    CGI_CLI.JSON_RESULTS['SCRIPT_ACTION'] = '%s' % (SCRIPT_ACTION)


    ### def LOGFILENAME GENERATION, DO LOGGING ONLY WHEN DEVICE LIST EXISTS ###
    #try:
    html_extention = 'htm' if CGI_CLI.cgi_active else str()
    logfilename = generate_logfilename(
        prefix = '_'.join(device_list).upper(), \
        USERNAME = USERNAME, pre_suffix = '-' + SCRIPT_ACTION, \
        suffix = '%slog' % (html_extention),
        directory = '/var/www/cgi-bin')
    CGI_CLI.JSON_RESULTS['logfile'] = logfilename
    #except: pass

    ### NO WINDOWS LOGGING ########################################
    #if 'WIN32' in sys.platform.upper(): logfilename = None
    if logfilename:
        CGI_CLI.set_logfile(logfilename = logfilename)

        if CGI_CLI.cgi_active:
            CGI_CLI.logtofile('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s) [action=%s]</a></h1>' % \
                (SCRIPT_NAME, changelog, CGI_CLI.VERSION(), SCRIPT_ACTION), raw_log = True, ommit_timestamp = True)
        else: CGI_CLI.logtofile('%s (v.%s) [action=%s]' % (SCRIPT_NAME, CGI_CLI.VERSION(), SCRIPT_ACTION), ommit_timestamp = True)

        CGI_CLI.logtofile(CGI_CLI.print_args(ommit_print = True) + '\n\n', ommit_timestamp = True)

    ### END DUE TO MISSING INPUT DATA #########################################
    exit_due_to_error = None

    if len(device_list) == 0:
        text = 'Device(s) NOT INSERTED!'
        CGI_CLI.add_result(text, 'error')
        exit_due_to_error = True

    if not USERNAME:
        text = 'Username NOT INSERTED!'
        CGI_CLI.add_result(text, 'error')
        exit_due_to_error = True

    if not PASSWORD:
        text = 'Password NOT INSERTED!'
        CGI_CLI.add_result(text, 'error')
        exit_due_to_error = True

    if SCRIPT_ACTION == 'post':
        html_extention = 'htm' if CGI_CLI.cgi_active else str()
        precheck_file = find_last_logfile(prefix = '_'.join(device_list).upper(), \
            USERNAME = USERNAME, suffix = 'pre.%slog' % (html_extention), directory = None, \
            latest = None , action_text = 'precheck')
        if precheck_file:
            CGI_CLI.JSON_RESULTS['precheck_logfile'] = '%s' % (precheck_file)
        else: exit_due_to_error = True

    if exit_due_to_error: sys.exit(0)

    ### def REMOTE DEVICE OPERATIONS ##########################################
    for device in device_list:
        if device:

            ### DEVICE CONNECT ############################################
            RCMD.connect(device, username = USERNAME, password = PASSWORD, \
                printall = printall, \
                connection_timeout = 10000, cmd_timeout = 2200)

            if not RCMD.ssh_connection:
                text = 'PROBLEM TO CONNECT TO %s DEVICE.' % (device)
                CGI_CLI.uprint(text, \
                    color = 'red')
                CGI_CLI.add_result(text, 'error')
                RCMD.disconnect()
                continue

            ### DO NOT GO FURTHER IF NO CONNECTION ############################
            if not RCMD.ssh_connection: continue

            CGI_CLI.logtofile('\nDETECTED DEVICE_TYPE: %s\n\n' % (RCMD.router_type))


            ###################################################################
            ### def PRE&POST_CHECK START ######################################
            ###################################################################

            HW_INFO = {}
            HW_INFO = detect_hw(device)
            CGI_CLI.uprint(HW_INFO, tag = 'debug', no_printall = not CGI_CLI.printall)

            brand_raw = str()
            type_raw = HW_INFO.get('hw_type',str())
            ### def GET PATHS ON DEVICE ###########################################
            brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
                get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)

            ### BY DEFAULT = '/' ##################################################
            dev_dir = os.path.abspath(os.path.join(os.sep, type_subdir_on_device))

            xe_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
            xr_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
            huawei_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
            juniper_device_dir_list = [ 'file list %s%s detail' % (RCMD.drive_string,dev_dir) ]

            dir_device_cmds = {
                'cisco_ios':xe_device_dir_list,
                'cisco_xr':xr_device_dir_list,
                'juniper':juniper_device_dir_list,
                'huawei':huawei_device_dir_list
            }

            device_cmds_result = RCMD.run_commands(dir_device_cmds, printall = printall)
            versions = []

            JSON_DATA = {}
            JSON_DATA['target_sw_versions'] = {}
            if RCMD.router_type == "cisco_ios" or RCMD.router_type == "cisco_xr":
                for line in device_cmds_result[0].splitlines():
                    try:
                         sub_directory = line.split()[-1]
                         if str(line.split()[1])[0] == 'd' and int(sub_directory):
                             versions.append(sub_directory)
                             JSON_DATA['target_sw_versions'][str(sub_directory)] = {}
                             JSON_DATA['target_sw_versions'][str(sub_directory)]['path'] = str('%s%s/%s' % (RCMD.drive_string, dev_dir, sub_directory))
                    except: pass

            elif RCMD.router_type == "huawei":
                ### FILES ARE IN CFCARD ROOT !!! ##################################
                for line in device_cmds_result[0].splitlines()[:-1]:
                    try:
                        tar_file = line.split()[-1]
                        for file_type in file_types:
                            if '/' in file_type.upper():
                                file_type_parts = file_type.split('/')[-1].split('*')
                            else:
                                file_type_parts = file_type.split('*')
                            found_in_tar_file = True
                            for file_type_part in file_type_parts:
                                if file_type_part.upper() in tar_file.upper(): pass
                                else: found_in_tar_file = False
                            if len(file_type_parts) > 0 and found_in_tar_file:
                                JSON_DATA['target_sw_versions'][str(tar_file)] = {}
                                JSON_DATA['target_sw_versions'][str(tar_file)]['path'] = str(dev_dir)
                                JSON_DATA['target_sw_versions'][str(tar_file)]['files'] = [tar_file]
                    except: pass

            elif RCMD.router_type == "juniper":
                ### FILES ARE IN re0:/var/tmp #####################################
                for line in device_cmds_result[0].splitlines()[:-1]:
                    try:
                        tar_file = line.split()[-1]
                        for file_type in file_types:
                            if '/' in file_type.upper():
                                file_type_parts = file_type.split('/')[-1].split('*')
                            else:
                                file_type_parts = file_type.split('*')
                            found_in_tar_file = True
                            for file_type_part in file_type_parts:
                                if file_type_part.upper() in tar_file.upper(): pass
                                else: found_in_tar_file = False
                            if len(file_type_parts) > 0 and found_in_tar_file:
                                JSON_DATA['target_sw_versions'][str(tar_file)] = {}
                                JSON_DATA['target_sw_versions'][str(tar_file)]['path'] = str(dev_dir)
                                JSON_DATA['target_sw_versions'][str(tar_file)]['files'] = [tar_file]
                    except: pass

            for key in JSON_DATA.get('target_sw_versions').keys():
                ### def get files on device version directory #########################
                xe_device_file_list = [ 'dir %s' % (JSON_DATA['target_sw_versions'][key].get('path',str)) ]
                xr_device_file_list = [ 'dir %s' % (JSON_DATA['target_sw_versions'][key].get('path',str)) ]

                juniper_device_file_list = [ 'file list %s detail' % (JSON_DATA['target_sw_versions'][key].get('path',str)) ]

                file_device_cmds = {
                    'cisco_ios':xe_device_file_list,
                    'cisco_xr':xr_device_file_list,
                    'juniper':juniper_device_file_list,
                    'huawei':[]
                }

                file_device_cmds_result = RCMD.run_commands(file_device_cmds, printall = printall)

                if RCMD.router_type == "cisco_ios" or RCMD.router_type == "cisco_xr":
                    files = []
                    for line in file_device_cmds_result[0].splitlines()[:-1]:
                        try:
                            tar_file = line.split()[-1]
                            for file_type in file_types:
                                if '/' in file_type.upper(): pass
                                else:
                                    file_type_parts = file_type.split('*')
                                    found_in_tar_file = True
                                    for file_type_part in file_type_parts:
                                        if file_type_part.upper() in tar_file.upper(): pass
                                        else: found_in_tar_file = False
                                    if len(file_type_parts) > 0 and found_in_tar_file:
                                        files.append('%s/%s' % (JSON_DATA['target_sw_versions'][key].get('path',str), tar_file))
                        except: pass
                    if len(files)>0:
                        JSON_DATA['target_sw_versions'][key]['files'] = files

                elif RCMD.router_type == "huawei":
                    pass
                elif RCMD.router_type == "juniper":
                    pass

                ### GET SMU FILES ON DEVICE VERSION DIRECTORY #########################
                if RCMD.router_type == "cisco_xr":
                    xr_device_patch_file_list = [ 'dir %s/SMU' % (JSON_DATA['target_sw_versions'][key].get('path',str)) ]

                    patch_file_device_cmds = {
                        'cisco_ios':[],
                        'cisco_xr':xr_device_patch_file_list,
                        'juniper':[],
                        'huawei':[]
                    }

                    patch_file_device_cmds_result = RCMD.run_commands(patch_file_device_cmds, printall = printall)

                    if RCMD.router_type == "cisco_ios":
                        pass
                    elif RCMD.router_type == "cisco_xr":
                        patch_files = []
                        patch_path = str()
                        for line in patch_file_device_cmds_result[0].splitlines()[:-1]:
                            try:
                                tar_file = line.split()[-1]
                                for file_type in file_types:
                                    try: patch_file = file_type.split('/')[1].replace('*','')
                                    except: patch_file = str()
                                    if len(patch_file) > 0 and patch_file.upper() in tar_file.upper():
                                        patch_files.append('%s/%s/%s' % (JSON_DATA['target_sw_versions'][key].get('path',str), 'SMU' , tar_file))
                                        patch_path = '%s/%s' % (JSON_DATA['target_sw_versions'][key].get('path',str), 'SMU')
                            except: pass
                        if len(patch_files) > 0:
                            JSON_DATA['target_sw_versions'][key]['patch_files'] = patch_files
                            JSON_DATA['target_sw_versions'][key]['patch_path'] = patch_path

                    elif RCMD.router_type == "huawei":
                        pass
                    elif RCMD.router_type == "juniper":
                        pass

            ### CISCO_IOS #####################################################
            if RCMD.router_type == 'cisco_ios':
                text = 'NOT IMPLEMENTED YET !'
                CGI_CLI.add_result(text, 'error')


            ### JUNOS ###################################
            elif RCMD.router_type == 'juniper':
                text = 'NOT IMPLEMENTED YET !'
                CGI_CLI.add_result(text, 'error')

            ### HUAWEI ##################################
            elif RCMD.router_type == 'huawei':
                text = 'NOT IMPLEMENTED YET !'
                CGI_CLI.add_result(text, 'error')

            ### CISCO_XR ################################
            elif RCMD.router_type == 'cisco_xr':

                ### def show install inactive sum #########################
                device_cmds = {
                    'cisco_xr':[ 'show install inactive sum' ],
                }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    autoconfirm_mode = True, \
                    printall = printall)

                inactive_packages = []
                if 'No inactive package(s) in software repository' in rcmd_outputs[0]:
                    pass
                else:
                    if 'inactive package(s) found:' in rcmd_outputs[0]:
                        for package_line in rcmd_outputs[0].split('inactive package(s) found:')[1].splitlines()[:-1]:
                            if package_line.strip():
                                inactive_packages.append(str(package_line.strip()))

                    if not CGI_CLI.READ_ONLY:
                        device_cmds2 = {
                            'cisco_xr':[ 'install remove inactive all' ],
                        }

                        rcmd_outputs2 = RCMD.run_commands(device_cmds2, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        try: JSON_DATA['remove_inactive_id_nr'] = copy.deepcopy(rcmd_outputs2[0].split('Install operation ')[1].split(' started').strip())
                        except: pass
                        ### INSTEAD OF WAITING RECHECK IS DONE ON THE END ###

                ### admin show install inactive sum ###
                device_cmds = {
                    'cisco_xr':[ 'admin show install inactive sum' ],
                }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    autoconfirm_mode = True, \
                    printall = printall)

                inactive_packages = []
                if 'Inactive Packages: 0' in rcmd_outputs[0]:
                    pass
                else:
                    if 'Inactive Packages:' in rcmd_outputs[0]:
                        for package_line in rcmd_outputs[0].split('Inactive Packages:')[1].splitlines()[1:-1]:
                            if package_line.strip():
                                inactive_packages.append(str(package_line.strip()))

                    if not CGI_CLI.READ_ONLY:
                        device_cmds2 = {
                            'cisco_xr':[ 'admin install remove inactive all' ],
                        }

                        rcmd_outputs2 = RCMD.run_commands(device_cmds2, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        try: JSON_DATA['admin_remove_inactive_id_nr'] = copy.deepcopy(rcmd_outputs2[0].split('Install operation ')[1].split(' started').strip())
                        except: pass
                        ### INSTEAD OF WAITING RECHECK IS DONE ON THE END ###

                ### def show install active summary #######################
                device_cmds4 = {
                    'cisco_xr':[ 'show install active summary' ],
                }

                rcmd_outputs4 = RCMD.run_commands(device_cmds4, \
                    autoconfirm_mode = True, \
                    printall = printall)

                active_packages = []
                if 'Active Packages:' in rcmd_outputs4[0]:
                    number_of_active_packages = int(rcmd_outputs4[0].split('Active Packages:')[1].split()[0])
                    for i in range(number_of_active_packages):
                         active_packages.append(rcmd_outputs4[0].split('Active Packages:')[1].splitlines()[i + 1].split()[0].strip())
                    JSON_DATA['active_packages'] = active_packages

                ### admin show install active summary ###
                device_cmds4b = {
                    'cisco_xr':[ 'admin show install active summary' ],
                }

                rcmd_outputs4b = RCMD.run_commands(device_cmds4b, \
                    autoconfirm_mode = True, \
                    printall = printall)

                active_packages = []
                if 'Active Packages:' in rcmd_outputs4b[0]:
                    number_of_active_packages = int(rcmd_outputs4b[0].split('Active Packages:')[1].split()[0])
                    for i in range(number_of_active_packages):
                         active_packages.append(rcmd_outputs4b[0].split('Active Packages:')[1].splitlines()[i + 1].split()[0].strip())
                    JSON_DATA['admin_active_packages'] = active_packages


                ### def 'show platform' #########################
                device_cmds_p = { 'cisco_xr': [ 'show platform' ] }

                rcmd_outputs_p = RCMD.run_commands(device_cmds_p, \
                    long_lasting_mode = True, \
                    printall = printall)

                if 'Config state' in rcmd_outputs_p[0]:
                    for line in rcmd_outputs_p[0].split('Config state')[1].splitlines()[2:-1]:
                        try: platform_state = line.split()[2]
                        except: platform_state = str()
                        if 'UP' in platform_state or 'OPERATIONAL' in platform_state \
                            or 'IOS XR RUN' in line: pass
                        else:
                            text = "(CMD:'show platform', PROBLEM:'%s' !)" % (line)
                            CGI_CLI.add_result(text, 'error')


                ### def 'show version' #########################
                device_cmds = { 'cisco_xr': [ 'show version' ] }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    long_lasting_mode = True, \
                    printall = printall)

                try: version = rcmd_outputs[0].split('Version')[1].split()[0].strip()
                except: version = str()
                JSON_DATA['version'] = copy.deepcopy(version)


                ### def 'show isis adjacency' #########################
                device_cmds = { 'cisco_xr': [ 'show isis adjacency' ] }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    long_lasting_mode = True, \
                    printall = printall)

                if 'BFD  BFD' in rcmd_outputs[0]:
                    for line in rcmd_outputs[0].split('BFD  BFD')[1].splitlines()[0:-1]:
                        try: isis_state = line.split()[3]
                        except: isis_state = str()
                        if 'UP' in isis_state.upper(): pass
                        elif line.strip() and not 'Total adjacency count:' in line:
                            text = "(CMD:'show isis adjacency', PROBLEM:'%s' !)" % (line.strip())
                            CGI_CLI.add_result(text, 'error')


                ### def 'show alarms brief system active' #########################
                device_cmds = { 'cisco_xr': [ 'show alarms brief system active' ] }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    long_lasting_mode = True, \
                    printall = printall)

                if 'Description' in rcmd_outputs[0]:
                    for line in rcmd_outputs[0].split('Description')[1].splitlines()[2:-1]:
                        try: alarm_state = line.split()[-1]
                        except: alarm_state = str()
                        if 'ALARM' in isis_state.upper():
                            text = "(CMD:'show alarms brief system active', PROBLEM:'%s' !)" % (line.strip())
                            CGI_CLI.add_result(text, 'error')
                        elif 'WARNING' in isis_state.upper():
                            text = "(CMD:'show alarms brief system active', PROBLEM:'%s' !)" % (line.strip())
                            CGI_CLI.add_result(text, 'warning')


                ### def 'show health gsp' #####################################
                device_cmds = { 'cisco_xr': [ 'show health gsp' ] }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    printall = printall)

                if 'Summary: gsp is healthy.' in rcmd_outputs[0]: pass
                else:
                    text = "(CMD:'show health gsp', PROBLEM:'%s')" % (rcmd_outputs[0].strip())
                    CGI_CLI.add_result(text, 'error')


                ### def 'clear configuration inconsistency' #####################################
                device_cmds = { 'cisco_xr': [ 'clear configuration inconsistency' ] }

                rcmd_outputs = RCMD.run_commands(device_cmds, \
                    long_lasting_mode = True, printall = printall)

                for line in rcmd_outputs[0].splitlines():
                    if '...' in line:
                        if '...OK' in line: pass
                        else:
                            text = "(CMD:'clear configuration inconsistency', PROBLEM:'%s')" % (rcmd_outputs[0].strip())
                            CGI_CLI.add_result(text, 'error')
                            break


                ### def xr check list #########################################
                device_cmds5 = { 'cisco_xr': [
                        'show configuration failed startup',
                        'show install repository',
                ] }

                rcmd_outputs5 = RCMD.run_commands(device_cmds5, \
                    autoconfirm_mode = True, \
                    printall = printall)


                ### def save configs ##########################################
                device_cmds55 = { 'cisco_xr': [
                        'show running-config',
                        'admin show running-config'
                ] }

                rcmd_outputs_configs = RCMD.run_commands(device_cmds55, \
                    ignore_syntax_error = True, \
                    printall = printall)


                ### def copy configs ######################################
                date_string = datetime.datetime.now().strftime("%Y-%m%d-%H:%M")

                device_cmds6 = {
                    'cisco_xr':['copy running-config harddisk:%s-config.txt' % (str(date_string))],
                }

                rcmd_outputs6 = RCMD.run_commands(device_cmds6, \
                    autoconfirm_mode = True, \
                    printall = printall)

                device_cmds7 = {
                    'cisco_xr':['admin copy running-config harddisk:admin-%s-config.txt' % (str(date_string))],
                }

                rcmd_outputs7 = RCMD.run_commands(device_cmds7, \
                    autoconfirm_mode = True, \
                    printall = printall)


                if not 'IOS-XRv 9000' in HW_INFO.get('hw_type',str()):
                    ### def 'show hw-module fpd' ##########################
                    xr_check_cmd_list = { 'cisco_xr': [ 'show hw-module fpd' ] }
                    rcmd_outputs = RCMD.run_commands(xr_check_cmd_list, printall = printall)

                    ### PARSE 'show hw-module fpd' !!! ###
                    fpd_problems = []
                    try:
                        for fpd_line in rcmd_outputs[0].split('Running Programd')[1].splitlines():
                            if fpd_line.strip() and not '-----' in fpd_line:
                                try:
                                    ### NCS has current in 4th column , XRv in 3rd ###
                                    if fpd_line.strip().split()[3] == 'CURRENT' \
                                        or fpd_line.strip().split()[4] == 'CURRENT': pass
                                    else: fpd_problems.append(fpd_line.strip())
                                except: pass
                    except: pass

                    if len(fpd_problems) > 0:
                        text = "(PROBLEM: FPDs which are not 'CURRENT': [%s] !)" % (','.join(fpd_problems))
                        CGI_CLI.add_result(text, 'error')


                ### def PRECHECK - cards check ################################
                if SCRIPT_ACTION == 'pre' and \
                    not 'IOS-XRv 9000' in HW_INFO.get('hw_type',str()):
                    ### 'show run fpd auto-upgrade' ###########################

                    xr_cmds = {'cisco_xr': [ 'show run fpd auto-upgrade' ]}

                    rcmd_outputs = RCMD.run_commands(xr_cmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if not CGI_CLI.READ_ONLY and not 'fpd auto-upgrade enable' in rcmd_outputs[0]:

                        xr_cmds = {'cisco_xr': [
                                '!',
                                'fpd auto-upgrade enable',
                                '!',
                        ] }

                        ### CHECK IF AURO UPGRADE IS ENABLED ###
                        rcmd_outputs = RCMD.run_commands(xr_cmds, conf = True,\
                                autoconfirm_mode = True, \
                                printall = printall)

                        device_cmds5a = { 'cisco_xr': [
                                'show run fpd auto-upgrade',
                        ] }

                        rcmd_outputs5a = RCMD.run_commands(device_cmds5a, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if not 'fpd auto-upgrade enable' in rcmd_outputs5a[0]:
                            text = "(PROBLEM: 'fpd auto-upgrade enable' is not in CMD 'show run fpd auto-upgrade' !)"
                            CGI_CLI.add_result(text, 'error')

                    ### 'admin show run fpd auto-upgrade' #################
                    xr_cmds = {'cisco_xr': ['admin show run fpd auto-upgrade']}

                    rcmd_outputs = RCMD.run_commands(xr_cmds, \
                        autoconfirm_mode = True, \
                        printall = printall)

                    if not CGI_CLI.READ_ONLY and not 'fpd auto-upgrade enable' in rcmd_outputs[0]:
                        xr_cmds = {'cisco_xr': [
                                '!',
                                'admin',
                                '!',
                                'fpd auto-upgrade enable',
                                '!',
                        ] }

                        rcmd_outputs = RCMD.run_commands(xr_cmds, conf = True,\
                            autoconfirm_mode = True, \
                            printall = printall)

                        ### CHECK IF AURO UPGRADE IS ENABLED ###
                        device_cmds5b = { 'cisco_xr': [ 'admin show run fpd auto-upgrade' ] }

                        rcmd_outputs5b = RCMD.run_commands(device_cmds5b, \
                            autoconfirm_mode = True, \
                            printall = printall)

                        if not 'fpd auto-upgrade enable' in rcmd_outputs5b[0]:
                            text = "(PROBLEM: 'fpd auto-upgrade enable' is not in CMD 'admin show run fpd auto-upgrade' !)"
                            CGI_CLI.add_result(text, 'error')


            ###################################################################
            ### def PRECHECK commands #########################################
            ###################################################################
            if SCRIPT_ACTION == 'pre':
                if RCMD.router_type == 'cisco_xr':

                    ### def 'show int description | exclude "admin-down"' #####
                    device_cmds = { 'cisco_xr': [ 'show int description | exclude "admin-down"' ] }

                    rcmd_outputs = RCMD.run_commands(device_cmds, \
                        long_lasting_mode = True, printall = printall)


            ###################################################################
            ### def POSTCHECK commands ########################################
            ###################################################################
            if SCRIPT_ACTION == 'post':
                if RCMD.router_type == 'cisco_xr':

                    ### def 'show int description | exclude "admin-down"' #########
                    device_cmds = { 'cisco_xr': [ 'show int description | exclude "admin-down"' ] }

                    rcmd_outputs_int = RCMD.run_commands(device_cmds, printall = printall)

                    ### def POSTCHECK compare int #############################
                    postcheck_int = rcmd_outputs_int[0].strip()
                    precheck_int = read_section_from_logfile('REMOTE_COMMAND: show int description | exclude "admin-down"', \
                        CGI_CLI.JSON_RESULTS.get('precheck_logfile',str()), pre_tag = True).strip()

                    CGI_CLI.uprint('(PRECHECK INTERFACES:\n' + str(precheck_int) + ')', tag= 'debug', no_printall = not CGI_CLI.printall)

                    if postcheck_int and postcheck_int:
                        diff_result, all_ok = get_difference_string_from_string_or_list( \
                            precheck_int.strip(), postcheck_int.strip())
                        if all_ok: pass
                        else:
                            pass
                            text = "(PROBLEM: pre/post check 'show int' difference:\n'%s')" % (diff_result)
                            CGI_CLI.add_result(text, 'error')



                    ### def POSTCHECK compare configs #########################
                    postcheck_config = rcmd_outputs_configs[0]
                    postcheck_admin_config = rcmd_outputs_configs[1]

                    precheck_config = read_section_from_logfile('REMOTE_COMMAND: show running-config', \
                        CGI_CLI.JSON_RESULTS.get('precheck_logfile',str()), pre_tag = True)
                    precheck_admin_config = read_section_from_logfile('REMOTE_COMMAND: admin show running-config', \
                        CGI_CLI.JSON_RESULTS.get('precheck_logfile',str()), pre_tag = True)

                    if not precheck_config.strip():
                        text = "(PROBLEM: precheck config is VOID !)"
                        CGI_CLI.add_result(text, 'error')

                    if not precheck_admin_config.strip():
                        text = "(PROBLEM: precheck admin config is VOID !)"
                        CGI_CLI.add_result(text, 'error')

                    if not postcheck_config.strip():
                        text = "(PROBLEM: postcheck config is VOID !)"
                        CGI_CLI.add_result(text, 'error')

                    if not postcheck_admin_config.strip():
                        text = "(PROBLEM: postcheck admin config is VOID !)"
                        CGI_CLI.add_result(text, 'error')


                    if precheck_config and postcheck_config:
                        diff_result, all_ok = get_difference_string_from_string_or_list( \
                            precheck_config.strip(), postcheck_config.strip(),
                            ignore_list = default_ignoreline_list + ['set-overload-bit','fpd auto-upgrade enable','Last configuration change','Configuration version ='])
                        if all_ok: pass
                        else:
                            pass
                            text = "(PROBLEM: pre/post check configs difference:\n'%s')" % (diff_result)
                            CGI_CLI.add_result(text, 'error')

                    if precheck_admin_config and postcheck_admin_config:
                        diff_result, all_ok = get_difference_string_from_string_or_list( \
                            precheck_admin_config.strip(), postcheck_admin_config.strip(),
                            ignore_list = default_ignoreline_list + ['set-overload-bit','fpd auto-upgrade enable','Last configuration change'])
                        if all_ok: pass
                        else:
                            pass
                            text = "(PROBLEM: pre/post check admin configs difference:\n'%s')" % (diff_result)
                            CGI_CLI.add_result(text, 'error')

                    # ### FIND LAST PRECHECK???? CONFIG FILE !!! ################
                    # admin_config_files, config_files = [], []
                    # device_cmds = {
                        # 'cisco_xr':['dir harddisk: | include config.txt']
                    # }

                    # device_cmds_result = RCMD.run_commands(device_cmds, \
                        # autoconfirm_mode = True, \
                        # printall = printall)
                    # try:
                        # for file_line in device_cmds_result[0].splitlines()[:-1]:
                            # if file_line.strip() and '-config.txt' in file_line and ':' in file_line.split()[-1]:
                                # try:
                                    # if 'admin' in file_line.split()[-1]:
                                        # admin_config_files.append(file_line.split()[-1])
                                    # else: config_files.append(file_line.split()[-1])
                                # except: pass
                    # except: pass
                    # if len(config_files) > 1: config_files.sort()
                    # if len(admin_config_files) > 1: admin_config_files.sort()

                    # last_config_file, last_admin_config_file = str(), str()
                    # try:
                        # last_config_file = config_files[-1]
                        # last_admin_config_file = admin_config_files[-1]
                    # except: pass

                    # CGI_CLI.uprint('\nCONFIG FILE: ' + last_config_file + '\nCHOSEN FROM: ' + str(config_files), tag= 'debug', no_printall = not CGI_CLI.printall)
                    # CGI_CLI.uprint('\nADMIN CONFIG FILE: ' + last_admin_config_file + '\nCHOSEN FROM: ' + str(admin_config_files), tag= 'debug', no_printall = not CGI_CLI.printall)


                    # ### def POSTCHECK read config files - hack ################
                    # if last_config_file:
                        # cp_device_cmds = {
                            # 'cisco_xr':['utility head count 1000000 file harddisk:/%s' % (last_config_file)],
                        # }

                        # device_cmds_result = RCMD.run_commands(cp_device_cmds, \
                            # autoconfirm_mode = True, ignore_syntax_error = True, printall = printall)

                    # if last_admin_config_file:
                        # cp2_device_cmds = {
                            # 'cisco_xr':['admin utility head count 1000000 file harddisk:/%s' % (last_admin_config_file)],
                        # }

                        # device_cmds_result = RCMD.run_commands(cp2_device_cmds, \
                            # autoconfirm_mode = True, ignore_syntax_error = True, printall = printall)





            ### def PRE&POST - check actions ##################################

            ### def 'show install request' ################################
            device_cmds = { 'cisco_xr': [ 'show install request' ] }

            rcmd_outputs = RCMD.run_commands(device_cmds, \
                printall = printall)

            if 'No install operation in progress' in rcmd_outputs[0]:

                ### def 'install verify packages' #########################
                ### 'install verify packages synchronous' is not working on VM ####
                if 'IOS-XRv 9000' in HW_INFO.get('hw_type',str()):
                    device_cmds_inst = { 'cisco_xr': [ 'install verify packages' ] }

                    rcmd_outputs_inst = RCMD.run_commands(device_cmds_inst, \
                        long_lasting_mode = True, \
                        printall = printall)

                    try: JSON_DATA['verify_id_nr'] = rcmd_outputs_inst[0].split('Install operation ')[1].split(' started')[0].strip()
                    except: pass

                    if JSON_DATA.get('verify_id_nr',str()):
                        ### wait till no install packages in progress ###
                        for times in range(10):
                            device_cmds = { 'cisco_xr': [ 'show install request' ] }

                            rcmd_outputs = RCMD.run_commands(device_cmds, \
                                printall = printall)

                            if 'No install operation in progress' in rcmd_outputs[0]: break
                            time.sleep(2)
                        else:
                            text = "(CMD:'show install request', PROBLEM:'%s') !" % (rcmd_outputs[0].strip())
                            CGI_CLI.add_result(text, 'error')

            elif JSON_DATA.get('remove_inactive_id_nr',str()) or JSON_DATA.get('admin_remove_inactive_id_nr',str()) in rcmd_outputs[0]:
                ### wait till no install packages in progress ###
                for times in range(10):
                    device_cmds = { 'cisco_xr': [ 'show install request' ] }

                    rcmd_outputs = RCMD.run_commands(device_cmds, \
                        printall = printall)

                    if ' %s ' % (JSON_DATA.get('remove_inactive_id_nr',str())) in rcmd_outputs[0] or \
                    ' %s ' % (JSON_DATA.get('admin_remove_inactive_id_nr',str())) in rcmd_outputs[0]: pass

                    if 'No install operation in progress' in rcmd_outputs[0]: break
                    time.sleep(2)
                else:
                    text = "(CMD:'show install request', PROBLEM:'%s') !" % (rcmd_outputs[0].strip())
                    CGI_CLI.add_result(text, 'error')
            else:
                text = "(CMD:'show install request', PROBLEM:'%s')" % (rcmd_outputs[0].strip())
                CGI_CLI.add_result(text, 'error')


            ### def 'install verify packages synchronous' is not working on VM ####
            if not 'IOS-XRv 9000' in HW_INFO.get('hw_type',str()):
                device_cmds_inst = { 'cisco_xr': [ 'install verify packages synchronous' ] }

                rcmd_outputs_inst = RCMD.run_commands(device_cmds_inst, \
                    long_lasting_mode = True, \
                    printall = printall)
                if 'Install operation' in rcmd_outputs_inst[0] and 'finished successfully' in rcmd_outputs_inst[0]: pass
                else:
                    text = "(CMD:'install verify packages', PROBLEM:'%s')" % (rcmd_outputs_inst[0])
                    CGI_CLI.add_result(text, 'error')


            ### def REPEAT 'show install inactive summary' ###
            device_cmds3 = { 'cisco_xr':[ 'show install inactive summary' ] }

            rcmd_outputs3 = RCMD.run_commands(device_cmds3, \
                long_lasting_mode = True, printall = printall)

            inactive_packages = []
            if 'No inactive package(s) in software repository' in rcmd_outputs3[0]:
                pass
            else:
                if 'inactive package(s) found:' in rcmd_outputs3[0]:
                    for package_line in rcmd_outputs3[0].split('inactive package(s) found:')[1].splitlines()[:-1]:
                        if package_line.strip():
                            inactive_packages.append(str(package_line.strip()))
            JSON_DATA['inactive_packages'] = copy.deepcopy(inactive_packages)


            ### def REPEAT 'admin show install inactive summary' ###
            device_cmds3 = { 'cisco_xr':[ 'admin show install inactive summary' ] }

            rcmd_outputs3 = RCMD.run_commands(device_cmds3, \
                long_lasting_mode = True, printall = printall)

            inactive_packages = []
            if 'Inactive Packages: 0' in rcmd_outputs3[0]:
                pass
            else:
                if 'Inactive Packages:' in rcmd_outputs3[0]:
                    for package_line in rcmd_outputs3[0].split('Inactive Packages:')[1].splitlines()[1:-1]:
                        if package_line.strip():
                            inactive_packages.append(str(package_line.strip()))
            JSON_DATA['admin_inactive_packages'] = copy.deepcopy(inactive_packages)


            ### def check if patch smu files are in active packages #######
            if target_patch_path:
                check_files = []
                try:
                    for key in JSON_DATA['target_sw_versions'].keys():
                        if target_patch_path in JSON_DATA['target_sw_versions'][key].get('patch_path',str()) \
                            or key == target_patch_path:
                            check_files = JSON_DATA['target_sw_versions'][key].get('patch_files',[])
                except: pass

                if len(check_files) == 0:
                    text = "(PROBLEM: No SMU files found in patch path %s !)" % (target_patch_path)
                    CGI_CLI.add_result(text, 'error')

                if SCRIPT_ACTION == 'post':
                    for check_file in check_files:
                        try: check_part = check_file.split('.CSC')[1].split('.tar')[0]
                        except: check_part = str()
                        if check_part:
                            if check_part in JSON_DATA['active_packages'] \
                                or check_part in JSON_DATA['admin_active_packages']: pass
                            else:
                                text = "(PROBLEM: SMU file %s is not found in (admin) active packages !)" % (check_file)
                                CGI_CLI.add_result(text, 'error')


            ### def check if tar file is in active packages ###############
            if target_sw_file:
                check_files = []
                try:
                    for key in JSON_DATA['target_sw_versions'].keys():
                        if target_sw_file in JSON_DATA['target_sw_versions'][key].get('files',str()) \
                            or key == target_sw_file:
                            check_files = JSON_DATA['target_sw_versions'][key].get('files',[])
                except: pass

                if len(check_files) == 0:
                    text = "(PROBLEM: Tar file %s not found !)" % (target_sw_file)
                    CGI_CLI.add_result(text, 'error')

                if len(check_files) > 1:
                    text = "(WARNING: Multiple tar files %s found in the same directory !)" % (target_sw_file)
                    CGI_CLI.add_result(text, 'warning')

                if SCRIPT_ACTION == 'post':
                    ### FIND VERSION 3..4 DIGITS NUMBER DOT OR DOTLESS ########
                    try: version = re.findall(r'[0-9]\.[0-9]\.[0-9]\.[0-9]', target_sw_file)[-1]
                    except:
                        try: version = re.findall(r'[0-9]\.[0-9]\.[0-9]', target_sw_file)[-1]
                        except:
                            try: version = re.findall(r'[0-9][0-9][0-9][0-9]', target_sw_file)[-1]
                            except:
                                try: version = re.findall(r'[0-9][0-9][0-9][0-9]', target_sw_file)[-1]
                                except: version = str()

                    if version:
                        JSON_DATA['version_from_filename'] = str(version)
                        force_dotted_version, undotted_version = None, None
                        if '.' in version: undotted_version = version.replace('.','')
                        else: force_dotted_version = '.'.join(list(version))
                        if version in JSON_DATA['active_packages'] \
                            or version in JSON_DATA['admin_active_packages']: pass
                        elif undotted_version and (undotted_version in JSON_DATA['active_packages'] \
                            or undotted_version in JSON_DATA['admin_active_packages']): pass
                        elif force_dotted_version and (force_dotted_version in JSON_DATA['active_packages'] \
                            or force_dotted_version in JSON_DATA['admin_active_packages']): pass
                        else:
                            text = "(PROBLEM: Tar file %s is not found in (admin) active packages !)" % (target_sw_file)
                            CGI_CLI.add_result(text, 'error')

                        ### def installed version check #######################
                        if JSON_DATA['version'] == version \
                            or undotted_version and JSON_DATA['version'] == undotted_version \
                            or force_dotted_version and JSON_DATA['version'] == force_dotted_version: pass
                        else:
                            text = "(PROBLEM: Installed version does not fit with tar file version: '%s' != '%s' !)" % (JSON_DATA['version'], version)
                            CGI_CLI.add_result(text, 'error')




            ### CHECK INSTALL LOG FOR LAST ERRORS #####################
            device_cmds_log = { 'cisco_xr': [ 'show install log | utility tail count 10' ] }

            rcmd_outputs_log = RCMD.run_commands(device_cmds_log, printall = printall)

            if 'ERROR!' in rcmd_outputs_log[0].upper():
                text = "(PROBLEM: Error in end of install log: '%s' !)" % (rcmd_outputs_log[0].split('ERROR!')[1])
                CGI_CLI.add_result(text, 'error')



            ### def FINAL CHECKS ##############################################
            check_data_content("JSON_DATA['inactive_packages']", exact_value_yes = '[]', warning = True)
            check_data_content("JSON_DATA['admin_inactive_packages']", exact_value_yes = '[]',  warning = True)


            ### print JSON_DATA ###############################################
            if isinstance(JSON_DATA, (dict,collections.OrderedDict,list,tuple)):
                try:
                    print_text = str(json.dumps(JSON_DATA, indent = 2))
                    CGI_CLI.uprint('\nJSON_DATA = ' + print_text + '\n', \
                        color = 'blue', no_printall = not CGI_CLI.printall)
                except Exception as e:
                    CGI_CLI.add_result("(PROBLEM: Json.dumps - " + str(e) + ")", 'error')


except SystemExit: pass
except:
    text = traceback.format_exc()
    CGI_CLI.add_result(text, 'fatal')

