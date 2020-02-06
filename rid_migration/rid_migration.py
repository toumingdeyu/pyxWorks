#!/usr/bin/python

###!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html, traceback
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
                            help = "target router to access")
        parser.add_argument("--rollback",
                            action = "store_true", dest = 'rollback',
                            default = None,
                            help = "do rollback")
        parser.add_argument("--cfg",
                            action = "store_true", dest = 'show_config_only',
                            default = None,
                            help = "show config only, do not push data to device")
        parser.add_argument("--printall",
                            action = "store_true", dest = 'printall',
                            default = None,
                            help = "print all lines, changes will be coloured")
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():
        ### CGI_CLI.uprint('\nEND[script runtime = %d sec]. '%(time.time() - CGI_CLI.START_EPOCH))
        CGI_CLI.html_selflink('OK')
        if CGI_CLI.cgi_active: CGI_CLI.print_chunk("</body></html>")

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(chunked = None, css_style = None, newline = None, \
        timestamp = None, log = None):
        """
        log - start to log all after logfilename is inserted
        """
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.http_status = 200
        CGI_CLI.http_status_text = 'OK'
        CGI_CLI.chunked = chunked
        CGI_CLI.timestamp = timestamp
        CGI_CLI.log = log
        CGI_CLI.CSS_STYLE = css_style if css_style else str()
        ### TO BE PLACED - BEFORE HEADER ###
        CGI_CLI.newline = '\r\n' if not newline else newline
        CGI_CLI.chunked_transfer_encoding_line = \
            "Transfer-Encoding: chunked%s" % (CGI_CLI.newline) if CGI_CLI.chunked else str()
        ### HTTP/1.1 ???
        CGI_CLI.status_line = \
            "Status: %s %s%s" % (CGI_CLI.http_status, CGI_CLI.http_status_text, CGI_CLI.newline)
        CGI_CLI.content_type_line = 'Content-type:text/html; charset=utf-8%s' % (CGI_CLI.newline)
        CGI_CLI.cgi_active = None
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
            if variable and value and not variable in ["submit","username","password"]:
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
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
                '<style>%s</style>' % (CGI_CLI.CSS_STYLE) if CGI_CLI.CSS_STYLE else str()))
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
                                    CGI_CLI.uprint('The file "' + use_filename + '" was uploaded.')
                            except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']', color = 'magenta')

    @staticmethod
    def set_logfile(logfilename = None):
        """
        set_logfile()            - uses LCMD.logfilename or RCMD.logfilename,
        set_logfile(logfilename) - uses inserted logfilename
        """
        actual_logfilename, CGI_CLI.logfilename = None, None
        ### CHECK AND GET ALREADY USED LOGFILES ###############################
        try:
            if not (LCMD.logfilenam == 'nul' or LCMD.logfilename == '/dev/null'):
                actual_logfilename = copy.deepcopy(LCMD.logfilename)
        except: pass
        try:
            if not (RCMD.logfilenam == 'nul' or RCMD.logfilename == '/dev/null'):
               actual_logfilename = copy.deepcopy(RCMD.logfilename)
        except: pass
        ### SET ACTUAL_LOGFILENAME FROM INSERTED IF INSETRED ##################
        if logfilename: actual_logfilename = logfilename
        ### REWRITE CGI_CLI.LOGFILENAME #######################################
        if actual_logfilename == 'nul' or actual_logfilename == '/dev/null' \
            or not actual_logfilename: pass
        else:
            CGI_CLI.logfilename = actual_logfilename
            ### IF LOGFILE SET, SET ALSO OTHER CLASSES LOG FILES ##############
            try:
                if CGI_CLI.logfilename:
                    LCMD.logfilename = copy.deepcopy(CGI_CLI.logfilename)
            except: pass
            try:
                if CGI_CLI.logfilename:
                    RCMD.logfilename = copy.deepcopy(CGI_CLI.logfilename)
            except: pass

    @staticmethod
    def print_chunk(msg=""):
        ### sys.stdout.write is printing without \n , print adds \n == +1BYTE ###
        if CGI_CLI.chunked and CGI_CLI.cgi_active:
            if len(msg)>0:
                sys.stdout.write("\r\n%X\r\n%s" % (len(msg), msg))
                sys.stdout.flush()
        ### CLI MODE ###
        else: print(msg)

    @staticmethod
    def uprint(text = str(), tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        log = None, no_newlines = None, start_tag = None, end_tag = None, raw = None, timestamp = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
           timestamp = True - locally allow (CGI_CLI.timestamp = True has priority)
           timestamp = 'no' - locally disable even if CGI_CLI.timestamp == True
           log = 'no' - locally disable logging even if CGI_CLI.log == True
        """
        print_text, print_name, print_per_tag = copy.deepcopy(text), str(), str()
        if jsonprint:
            if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = json.dumps(text, indent = 4)
                except Exception as e: CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']')
        if name == True:
            if not 'inspect.currentframe' in sys.modules: import inspect
            callers_local_vars = inspect.currentframe().f_back.f_locals.items()
            var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
            if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
        elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '

        print_text = str(print_text)
        log_text   = str(copy.deepcopy((print_text)))

        ### GENERATE TIMESTAMP STRING, 'NO' = NO EVEN IF GLOBALLY IS ALLOWED ###
        timestamp_string = str()
        if timestamp or CGI_CLI.timestamp:
            timestamp_yes = True
            try:
                if str(timestamp).upper() == 'NO': timestamp_yes = False
            except: pass
            if timestamp_yes:
                timestamp_string = '@%s[%.2fs] ' % \
                    (datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'), time.time() - CGI_CLI.START_EPOCH)

        if CGI_CLI.cgi_active and not raw:
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT #######################
            if color and not (tag or start_tag): tag = 'p';
            if tag: CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            elif start_tag: CGI_CLI.print_chunk('<%s%s%s>'%(start_tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').\
                    replace('<','&lt;').\
                    replace('>','&gt;').replace(' ','&nbsp;').\
                    replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
            CGI_CLI.print_chunk(timestamp_string + print_name + print_text)
        elif CGI_CLI.cgi_active and raw: CGI_CLI.print_chunk(print_text)
        else:
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
            ### CLI_MODE ######################################################
            if no_newlines:
                sys.stdout.write(text_color + print_name + print_text \
                    + CGI_CLI.bcolors.ENDC)
                sys.stdout.flush()
            else:
                print(text_color + timestamp_string + print_name + print_text \
                    + CGI_CLI.bcolors.ENDC)
        ### PRINT END OF TAGS #################################################
        if CGI_CLI.cgi_active and not raw:
            if tag:
                CGI_CLI.print_chunk('</%s>' % (tag))
                ### USER DEFINED TAGS DOES NOT PROVIDE NEWLINES!!! ############
                if tag in ['debug','warning']: CGI_CLI.print_chunk('<br/>')
            elif end_tag: CGI_CLI.print_chunk('</%s>' % (end_tag))
            elif not no_newlines: CGI_CLI.print_chunk('<br/>')
            ### PRINT PER TAG #################################################
            CGI_CLI.print_chunk(print_per_tag)
        ### LOG ALL, if CGI_CLI.log is True, EXCEPT log == 'no' ###############
        if CGI_CLI.logfilename and (log or CGI_CLI.log):
            log_yes = True
            try:
                if str(log).upper() == 'NO': log_yes = False
            except: pass
            if log_yes:
                with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                    CGI_CLI.fp.write(timestamp_string + print_name + \
                        log_text + '\n')
        ### COPY CLEANUP ######################################################
        del log_text
        del print_text


    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, \
        color = None, list_separator = None):
        """ formprint() - print simple HTML form
            form_data - string, just html raw OR list or dict values = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
                      - value in dictionary means cgi variable name / printed componenet value
        """
        def subformprint(data_item):
            if isinstance(data_item, six.string_types):  CGI_CLI.print_chunk(data_item)
            elif isinstance(data_item, (dict,collections.OrderedDict)):
                if data_item.get('raw',None): CGI_CLI.print_chunk(data_item.get('raw'))
                elif data_item.get('textcontent',None):
                    CGI_CLI.print_chunk('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4">%s</textarea>'%\
                        (data_item.get('textcontent'), data_item.get('text','')))
                elif data_item.get('text'):
                    CGI_CLI.print_chunk('%s: <input type = "text" name = "%s"><br />'%\
                        (data_item.get('text','').replace('_',' '),data_item.get('text')))
                elif data_item.get('password'):
                    CGI_CLI.print_chunk('%s: <input type = "password" name = "%s"><br />'%\
                        (data_item.get('password','').replace('_',' '),data_item.get('password')))
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
                                list_separator if list_separator else str()))
                    else:
                        try:
                            value = data_item.get('radio').split('__')[1]
                            name = data_item.get('radio').split('__')[0]
                        except: value, name = data_item.get('radio'), 'radio'
                        CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                            (name,value,value.replace('_',' ')))
                elif data_item.get('checkbox'):
                    CGI_CLI.print_chunk('<input type = "checkbox" name = "%s" value = "on" /> %s'%\
                        (data_item.get('checkbox'),data_item.get('checkbox','').replace('_',' ')))
                elif data_item.get('dropdown'):
                    if len(data_item.get('dropdown').split(','))>0:
                        CGI_CLI.print_chunk('<select name = "dropdown[%s]">'%(data_item.get('dropdown')))
                        for option in data_item.get('dropdown').split(','):
                            CGI_CLI.print_chunk('<option value = "%s">%s</option>'%(option,option))
                        CGI_CLI.print_chunk('</select>')
                elif data_item.get('file'):
                   CGI_CLI.print_chunk('Upload file: <input type = "file" name = "file[%s]" />'%(data_item.get('file').replace('\\','/')))
                elif data_item.get('submit'):
                    CGI_CLI.print_chunk('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%\
                        (data_item.get('submit'),data_item.get('submit')))

        ### START OF FORMPRINT ###
        formtypes = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
        i_submit_button = None if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            CGI_CLI.print_chunk('<br/>')
            if tag and 'h' in tag: CGI_CLI.print_chunk('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
            if color or tag and 'p' in tag: tag = 'p'; CGI_CLI.print_chunk('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
            CGI_CLI.print_chunk('<form action = "/cgi-bin/%s" enctype = "multipart/form-data" action = "save_file.py" method = "post">'%\
                (i_pyfile))
            ### RAW HTML ###
            if isinstance(form_data, six.string_types): CGI_CLI.print_chunk(form_data)
            ### STRUCT FORM DATA = LIST ###
            elif isinstance(form_data, (list,tuple)):
                for data_item in form_data: subformprint(data_item)
            ### JUST ONE DICT ###
            elif isinstance(form_data, (dict,collections.OrderedDict)): subformprint(form_data)
            if i_submit_button: subformprint({'submit':i_submit_button})
            CGI_CLI.print_chunk('</form>')
            if tag and 'p' in tag: CGI_CLI.print_chunk('</p>')
            if tag and 'h' in tag: CGI_CLI.print_chunk('</%s>'%(tag))


    @staticmethod
    def html_selflink(submit_button = None):
        if (submit_button and str(submit_button) == str(CGI_CLI.submit_form)) or not CGI_CLI.submit_form:
            i_pyfile = sys.argv[0]
            try: pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
            except: pyfile = i_pyfile.strip()
            if CGI_CLI.cgi_active:
                CGI_CLI.print_chunk('<p id="scriptend"></p>')
                CGI_CLI.print_chunk('<br/><a href = "./%s">PAGE RELOAD</a>' % (pyfile))


    @staticmethod
    def VERSION(path_to_file = str(os.path.abspath(__file__))):
        if 'WIN32' in sys.platform.upper():
            file_time = os.path.getmtime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            file_time = stat.st_mtime
        return time.strftime("%y.%m.%d_%H:%M",time.gmtime(file_time))

    @staticmethod
    def print_args():
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
        CGI_CLI.uprint(print_string, tag = 'debug')
        return print_string

    @staticmethod
    def print_env():
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', tag = 'debug', jsonprint = True)


##############################################################################


class RCMD(object):

    @staticmethod
    def connect(device = None, cmd_data = None, username = None, password = None, \
        use_module = 'paramiko', logfilename = None, \
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
        logfilename - strng, name of logging file
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
            RCMD.logfilename = logfilename
            RCMD.USERNAME = username
            RCMD.PASSWORD = password
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

            ### IS ALIVE TEST #################################################
            if not no_alive_test:
                for i_repeat in range(3):
                    if RCMD.is_alive(device): break
                else:
                    CGI_CLI.uprint('DEVICE %s is not ALIVE.' % (device), color = 'magenta')
                    return command_outputs
            ### START SSH CONNECTION ##########################################
            if printall: CGI_CLI.uprint('DEVICE %s (host=%s, port=%s) START'\
                %(device, RCMD.DEVICE_HOST, RCMD.DEVICE_PORT)+24 * '.', color = 'gray')
            try:
                ### ONE_CONNECT DETECTION #####################################
                RCMD.client = paramiko.SSHClient()
                RCMD.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                RCMD.client.connect(RCMD.DEVICE_HOST, port=int(RCMD.DEVICE_PORT), \
                    username=RCMD.USERNAME, password=RCMD.PASSWORD, \
                    banner_timeout = 10, \
                    ### AUTH_TIMEOUT MAKES PROBLEMS ON IPTAC1 ###
                    #auth_timeout = 10, \
                    timeout = RCMD.CONNECTION_TIMEOUT, \
                    look_for_keys = False)
                RCMD.ssh_connection = RCMD.client.invoke_shell()
                if RCMD.ssh_connection:
                    RCMD.router_type, RCMD.router_prompt = RCMD.ssh_raw_detect_router_type(debug = None)
                    if not RCMD.router_type: CGI_CLI.uprint('DEVICE_TYPE NOT DETECTED!', color = 'red')
                    elif RCMD.router_type in RCMD.KNOWN_OS_TYPES and printall:
                        CGI_CLI.uprint('DETECTED DEVICE_TYPE: %s' % (RCMD.router_type), \
                            color = 'gray')
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
                stderr=subprocess.STDOUT, shell=True).decode("utf-8")
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
                CGI_CLI.uprint('REMOTE_COMMAND' + sim_mark + ': ' + cmd_line, color = 'blue')
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
                    CGI_CLI.uprint(last_output, color = 'gray', timestamp = 'no', log = 'no')
            elif not RCMD.silent_mode:
                if not long_lasting_mode:
                    CGI_CLI.uprint(' . ', no_newlines = True, log = 'no')
            ### LOG ALL ONLY ONCE, THAT IS BECAUSE PREVIOUS LINE log = 'no' ###
            if RCMD.fp: RCMD.fp.write('REMOTE_COMMAND' + sim_mark + ': ' + \
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
            if not RCMD.logfilename:
                if 'WIN32' in sys.platform.upper(): RCMD.logfilename = 'nul'
                else: RCMD.logfilename = '/dev/null'
            with open(RCMD.logfilename,"a+") as RCMD.fp:
                if RCMD.output: RCMD.fp.write(RCMD.output + '\n')
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
                        if RCMD.fp: RCMD.fp.write('REMOTE_COMMANDS' + sim_mark + ': ' \
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
                    CGI_CLI.uprint('\nCHECKING COMMIT ERRORS...', tag = 'h1', color = 'blue')
                    for rcmd_output in command_outputs:
                        CGI_CLI.uprint(' . ', no_newlines = True)
                        if 'INVALID INPUT' in rcmd_output.upper() \
                            or 'INCOMPLETE COMMAND' in rcmd_output.upper() \
                            or 'FAILED TO COMMIT' in rcmd_output.upper() \
                            or 'UNRECOGNIZED COMMAND' in rcmd_output.upper() \
                            or 'ERROR:' in rcmd_output.upper() \
                            or 'SYNTAX ERROR' in rcmd_output.upper():
                            RCMD.config_problem = True
                            CGI_CLI.uprint('\nCONFIGURATION PROBLEM FOUND:', color = 'red')
                            CGI_CLI.uprint('%s' % (rcmd_output), color = 'darkorchid')
                    ### COMMIT TEXT ###
                    if not (do_not_final_print or RCMD.do_not_final_print):
                        text_to_commit = str()
                        if not commit_text and not RCMD.commit_text: text_to_commit = 'COMMIT'
                        elif commit_text: text_to_commit = commit_text
                        elif RCMD.commit_text: text_to_commit = RCMD.commit_text
                        if submit_result:
                            if RCMD.config_problem:
                                CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = 'h1', tag_id = 'submit-result', color = 'red')
                            else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = 'h1', tag_id = 'submit-result', color = 'green')
                        else:
                            if RCMD.config_problem:
                                CGI_CLI.uprint('%s FAILED!' % (text_to_commit), tag = 'h1', color = 'red')
                            else: CGI_CLI.uprint('%s SUCCESSFULL.' % (text_to_commit), tag = 'h1', color = 'green')
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

        ### FLUSH BUFFERS FROM PREVIOUS COMMANDS IF THEY ARE ALREADY BUFFERED ###
        if chan.recv_ready(): flush_buffer = chan.recv(9999)
        time.sleep(0.1)
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
        prompt = ssh_raw_detect_prompt(RCMD.ssh_connection, debug=debug)
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



class LCMD(object):

    @staticmethod
    def init(logfilename = None, printall = None):
        LCMD.initialized = True
        if logfilename: LCMD.logfilename = logfilename
        else:
            if 'WIN32' in sys.platform.upper(): LCMD.logfilename = 'nul'
            else: LCMD.logfilename = '/dev/null'
        LCMD.printall = printall

    @staticmethod
    def init_log_and_print(logfilename = None, printall = None):
        ### RUN INIT DURING FIRST RUN IF NO INIT BEFORE
        try:
            if LCMD.initialized: pass
        except: LCMD.init(logfilename = logfilename, printall = printall)
        ### LOCAL PRINTALL AND LOGFILENAME OVERWRITES GLOBAL
        if not printall: printall = LCMD.printall
        if not logfilename: logfilename = LCMD.logfilename
        return logfilename, printall

    @staticmethod
    def run_command(cmd_line = None, logfilename = None, printall = None,
        chunked = None, timeout_sec = 5000):
        os_output, cmd_list, timer_counter_100ms = str(), None, 0
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_line:
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue')
                LCMD.fp.write('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
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
                                        CGI_CLI.uprint(stdoutput.strip(), color = 'gray')
                                stdoutput = str(CommandObject.stdout.readline())
                            time.sleep(0.1)
                            timer_counter_100ms += 1
                            if timer_counter_100ms > timeout_sec * 10:
                                CommandObject.terminate()
                                break
                    else:
                        os_output = subprocess.check_output(str(cmd_line), \
                            stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                except (subprocess.CalledProcessError) as e:
                    os_output = str(e.output.decode("utf-8"))
                    if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                    LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                except:
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                    LCMD.fp.write(exc_text + '\n')
                if not chunked and os_output and printall: CGI_CLI.uprint(os_output, color = 'gray', timestamp = 'no')
                LCMD.fp.write(os_output + '\n')
        return os_output

    @staticmethod
    def run_paralel_commands(cmd_data = None, logfilename = None, printall = None, \
        timeout_sec = 5000, custom_text = None, check_exitcode = None):
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        commands_ok = None
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            commands_ok = True
            with open(logfilename,"a+") as LCMD.fp:
                ### START LOOP ###
                CommandObjectList = []
                for cmd_line in cmd_list:
                    os_output = str()
                    try:
                        actual_CommandObject = subprocess.Popen(cmd_line, \
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        CommandObjectList.append(actual_CommandObject)
                        if printall: CGI_CLI.uprint("LOCAL_COMMAND_(START)[%s]: %s" % (str(actual_CommandObject), str(cmd_line)), color = 'blue')
                        LCMD.fp.write('LOCAL_COMMAND_(START)[%s]: %s' % (str(actual_CommandObject), str(cmd_line)) + '\n')
                    except (subprocess.CalledProcessError) as e:
                        os_output = str(e.output.decode("utf-8"))
                        if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                        LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                        commands_ok = False
                    except:
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                        LCMD.fp.write(exc_text + '\n')
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
                            LCMD.fp.write('LOCAL_COMMAND_(END)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                            CommandObjectList.remove(actual_CommandObject)
                            continue
                        if timer_counter_100ms % 10 == 0:
                            if printall: CGI_CLI.uprint("%d LOCAL_COMMAND%s RUNNING." % (len(CommandObjectList), 'S are' if len(CommandObjectList) > 1 else ' is'))
                            else: CGI_CLI.uprint(" %d   " % (len(CommandObjectList)), no_newlines = True)
                        if timer_counter_100ms % 300 == 0: CGI_CLI.uprint('\n')
                        if timer_counter_100ms > timeout_sec * 10:
                            if printall: CGI_CLI.uprint("LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s" % (str(actual_CommandObject), str(cmd_line), outputs), color = 'red')
                            LCMD.fp.write('LOCAL_COMMAND_(TIMEOUT)[%s]: %s\n%s\n' % (str(actual_CommandObject), str(cmd_line), outputs))
                            actual_CommandObject.terminate()
                            CommandObjectList.remove(actual_CommandObject)
                            commands_ok = False
            if not printall: CGI_CLI.uprint("\n")
        return commands_ok

    @staticmethod
    def run_commands(cmd_data = None, logfilename = None, printall = None):
        """
        FUNCTION: LCMD.run_commands(), RETURN: list of command_outputs
        PARAMETERS:
        cmd_data - dict, OS TYPE INDEPENDENT,
                 - list of strings or string, OS TYPE DEPENDENT
        """
        os_outputs =  None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (dict,collections.OrderedDict)):
            if 'WIN32' in sys.platform.upper(): cmd_list = cmd_data.get('windows',[])
            else: cmd_list = cmd_data.get('unix',[])
        elif cmd_data and isinstance(cmd_data, (list,tuple)): cmd_list = cmd_data
        elif cmd_data and isinstance(cmd_data, (six.string_types)): cmd_list = [cmd_data]
        else: cmd_list = []
        if len(cmd_list)>0:
            os_outputs = []
            with open(logfilename,"a+") as LCMD.fp:
                for cmd_line in cmd_list:
                    os_output = str()
                    if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line), color = 'blue')
                    LCMD.fp.write('LOCAL_COMMAND: ' + str(cmd_line) + '\n')
                    try: os_output = subprocess.check_output(str(cmd_line), stderr=subprocess.STDOUT, shell=True).decode("utf-8")
                    except (subprocess.CalledProcessError) as e:
                        os_output = str(e.output.decode("utf-8"))
                        if printall: CGI_CLI.uprint('EXITCODE: %s' % (str(e.returncode)))
                        LCMD.fp.write('EXITCODE: %s\n' % (str(e.returncode)))
                    except:
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint('PROBLEM[%s]' % str(exc_text), color = 'magenta')
                        LCMD.fp.write(exc_text + '\n')
                    if os_output and printall: CGI_CLI.uprint(os_output, color = 'gray', timestamp = 'no')
                    LCMD.fp.write(os_output + '\n')
                    os_outputs.append(os_output)
        return os_outputs

    @staticmethod
    def eval_command(cmd_data = None, logfilename = None, printall = None):
        """
        NOTE: by default - '\\n' = insert newline to text, '\n' = interpreted line
        """
        local_output = None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EVAL: %s" % (cmd_data))
                try:
                    local_output = eval(cmd_data)
                    if printall: CGI_CLI.uprint(str(local_output), color= 'gray', timestamp = 'no')
                    LCMD.fp.write('EVAL: ' + cmd_data + '\n' + str(local_output) + '\n')
                except Exception as e:
                    if printall:CGI_CLI.uprint('EVAL_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EVAL_PROBLEM[' + str(e) + ']\n', color = 'magenta')
        return local_output

    @staticmethod
    def exec_command(cmd_data = None, logfilename = None, printall = None, escape_newline = None):
        """
        NOTE:
              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EXEC: %s" % (cmd_data))
                LCMD.fp.write('EXEC: ' + cmd_data + '\n')
                ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                try:
                    if escape_newline:
                        edict = {}; eval(compile(cmd_data.replace('\n', '\\n'),\
                            '<string>', 'exec'), globals(), edict)
                    else: edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
                except Exception as e:
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None


    @staticmethod
    def exec_command_try_except(cmd_data = None, logfilename = None, \
        printall = None, escape_newline = None):
        """
        NOTE: This method can access global variable, expects '=' in expression,
              in case of except assign value None

              escape_newline = None, ==> '\\n' = insert newline to text, '\n' = interpreted line
              escape_newline = True, ==> '\n' = insert newline to text
        """
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
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
                    LCMD.fp.write('EXEC: \n' + cmd_ex_data + '\n')
                    ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                    edict = {}; eval(compile(cmd_ex_data, '<string>', 'exec'), globals(), edict)
                    #CGI_CLI.uprint("%s" % (eval(cmd_data.split('=')[0].strip())))
                except Exception as e:
                    if printall: CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']', \
                                     color = 'magenta')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')
        return None



###############################################################################

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
            if printall:
                CGI_CLI.uprint(" ==> Problem to send email by COMMAND=[%s], PROBLEM=[%s]\n"\
                    % (mail_command,str(e)) ,color = 'magenta')
        return email_success

    ### FUCTION send_me_email START ###########################################
    email_sent, sugested_email_address = None, str()
    if username: my_account = username
    else: my_account = subprocess.check_output('whoami', shell=True).strip()
    if email_address: sugested_email_address = email_address
    if not 'WIN32' in sys.platform.upper():
        try:
            ldapsearch_output = subprocess.check_output('ldapsearch -LLL -x uid=%s mail' % (my_account), shell=True)
            ldap_email_address = ldapsearch_output.decode("utf-8").split('mail:')[1].splitlines()[0].strip()
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
            if printall: CGI_CLI.uprint('Email Address not found!', color = 'magenta')
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
        filename = "%s-%.2i%.2i%i-%.2i%.2i%.2i-%s-%s-%s" % \
            (filename_prefix,now.year,now.month,now.day,now.hour,now.minute,\
            now.second,sys.argv[0].replace('.py','').replace('./','').\
            replace(':','_').replace('.','_').replace('\\','/')\
            .split('/')[-1],USERNAME,filename_suffix)
        filenamewithpath = str(os.path.join(LOGDIR,filename))
    return filenamewithpath


def find_last_shut_logfile(prefix = None, USERNAME = None, suffix = None, directory = None, \
    latest = None , printall = None):
    shut_file = str()
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
        CGI_CLI.uprint( " ... Can't find any shut session log file!", color = 'magenta')
    else:
        most_recent_shut = list_shut_files[0]
        for item in list_shut_files:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_shut)):
                most_recent_shut = item
        shut_file = most_recent_shut
    if printall and shut_file: CGI_CLI.uprint('FOUND LAST SHUT LOGFILE: %s' % (str(shut_file)), color = 'blue')
    return shut_file


def cisco_xr_parse_bgp_summary(text, LOCAL_AS_NUMBER):
    previous_line, ext_v4_list, ext_v6_list = str(), [], []
    try:
        temp_splited = (copy.deepcopy(text)).split("St/PfxRcd")[1].strip().splitlines()
        for line in temp_splited:
            if line.strip() == str(): continue
            if len(line.split()) == 1 and ('.' in line or ':' in line):
                previous_line = line; continue
            if previous_line: line, previous_line = previous_line + line, str()
            ### COLUMN10 IS DE FACTO SECOND WORD OF COLUMN9
            try: column10 = line.split()[10]
            except: column10 = str()
            try:
                if not LOCAL_AS_NUMBER in line.split()[2] and "." in line.split()[0]:
                    ext_v4_list.append([line.split()[0],line.split()[9] + column10])
                if not LOCAL_AS_NUMBER in line.split()[2] and ":" in line.split()[0]:
                    ext_v6_list.append([line.split()[0],line.split()[9] + column10])
            except: pass
        del temp_splited
    except: pass
    ### RETURNS LIST IN LISTS [PEER,STATUS] ###
    return ext_v4_list, ext_v6_list


def huawei_parse_bgp_summary(text, LOCAL_AS_NUMBER):
    previous_line, ext_v4_list, ext_v6_list = str(), [], []
    try:
        temp_splited = (copy.deepcopy(text)).split("PrefRcv")[1].strip().splitlines()
        for line in temp_splited:
            if line.strip() == str(): continue
            if len(line.split()) == 1 and ('.' in line or ':' in line):
                previous_line = line; continue
            if previous_line: line, previous_line = previous_line + line, str()
            try:
                if not LOCAL_AS_NUMBER in line.split()[2] and "." in line.split()[0]:
                    ext_v4_list.append([line.split()[0], line.split()[7]])
                if not LOCAL_AS_NUMBER in line.split()[2] and ":" in line.split()[0]:
                    ext_v6_list.append([line.split()[0], line.split()[7]])
            except: pass
        del temp_splited
    except: pass
    ### RETURNS LIST IN LISTS [PEER,STATUS] ###
    return ext_v4_list, ext_v6_list


def huawei_parse_bgp_summary_parts(text, LOCAL_AS_NUMBER):
    previous_line, ext_v4_list, ext_v6_list = str(), [], []
    try:
        temp_splited = (copy.deepcopy(text)).strip().splitlines()
        for line in temp_splited:
            if line.strip() == str(): continue
            if len(line.split()) == 1 and ('.' in line or ':' in line):
                previous_line = line; continue
            if previous_line: line, previous_line = previous_line + line, str()
            try:
                if not LOCAL_AS_NUMBER in line.split()[2] and "." in line.split()[0]:
                    ext_v4_list.append([line.split()[0], line.split()[7]])
                if not LOCAL_AS_NUMBER in line.split()[2] and ":" in line.split()[0]:
                    ext_v6_list.append([line.split()[0], line.split()[7]])
            except: pass
        del temp_splited
    except: pass
    ### RETURNS LIST IN LISTS [PEER,STATUS] ###
    return ext_v4_list, ext_v6_list


def return_bgp_data_json():
    return json.dumps(bgp_data, indent=2)


def read_bgp_data_json_from_logfile(filename = None, printall = None):
    bgp_data_loaded, text = None, None
    with open(filename,"r") as fp:
        text = fp.read()
    if text:
        try: bgp_data_json_text = text.split('EVAL: return_bgp_data_json()')[1]
        except: bgp_data_json_text = str()
        if bgp_data_json_text:
            try:
                bgp_data_loaded = json.loads(bgp_data_json_text, object_pairs_hook = collections.OrderedDict)
            except: pass
            #print("LOADED_BGP_DATA: ",bgp_data_loaded)
            if printall: CGI_CLI.uprint("\nLOADED JSON BGP_DATA: ")
            if printall: CGI_CLI.uprint(json.dumps(bgp_data_loaded, indent=2))
    return bgp_data_loaded




### GET_XPATH_FROM_XMLSTRING ===================================================
def get_void_json_elements(json_data, ignore_void_strings = None, ignore_void_lists = None):
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
                    json_deeper_references.append((parrent_xpath+'/'+key+'="'+str(key_content)+'"',key_content))
        return json_deeper_references
    ### FUNCTION -----------------------------------------------------------------
    references,xpath_list = [], []
    references.append(('',json_data))
    while len(references)>0:
        add_references=get_dictionary_subreferences(references[0])
        if '="None"' in references[0][0]\
            or not ignore_void_strings and '=""' in references[0][0]\
            or not ignore_void_lists and '=[]' in references[0][0]:
            xpath_list.append(references[0][0])
        references.remove(references[0])
        references=add_references+references
    del references
    return xpath_list
### ----------------------------------------------------------------------------

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

###############################################################################

### def XR CONFIG ###

xr_config = """!
interface Loopback10
% for item in loopback_0_config:
${item}
% endfor
!
!
interface Loopback0
 no ipv4 address
 no ipv6 address
% for item in loopback_200_config:
${item}
% endfor
!
!
no interface Loopback200
!
!
no logging source-interface Loopback0
logging source-interface Loopback10
!
domain lookup source-interface Loopback10
!
tacacs source-interface Loopback10 vrf default
!
snmp-server trap-source Loopback10
!
ftp client source-interface Loopback10
!
ntp
 source Loopback10
!
flow exporter-map ICX
 source Loopback10
!
tftp client source-interface Loopback10
!
ssh client source-interface Loopback10
!
!
router isis PAII
!
 !
 interface Loopback10
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
  no interface Loopback200
 !
!
router bgp 5511
% for item in neighbor_groups:
neighbor-group ${item}
 update-source Loopback10
% endfor
!
!
router isis PAII
 address-family ipv4 unicast
  mpls traffic-eng router-id Loopback0
 !
!
!
router bgp 5511
 bgp router-id ${loopback_200_address}
!
"""

### def XR UNDO CONFIG ###

undo_xr_config = """!
interface Loopback0
no ipv6 address
% for item in loopback_0_config:
${item}
% endfor
!
!
!
interface Loopback200
% for item in loopback_200_config:
${item}
% endfor
!
!
no interface Loopback10
!
no logging source-interface Loopback10
logging source-interface Loopback0
!
domain lookup source-interface Loopback0
!
tacacs source-interface Loopback0 vrf default
!
snmp-server trap-source Loopback0
!
ftp client source-interface Loopback0
!
ntp
 source Loopback0
!
flow exporter-map ICX
 source Loopback0
!
tftp client source-interface Loopback0
!
ssh client source-interface Loopback0
!
!
router isis PAII
!
no interface Loopback10
 !
 interface Loopback200
  passive
  address-family ipv4 unicast
  !
  address-family ipv6 unicast
  !
 !
!
router bgp 5511
% for item in neighbor_groups:
neighbor-group ${item}
 update-source Loopback0
% endfor
!
!
router isis PAII
 address-family ipv4 unicast
  mpls traffic-eng router-id Loopback0
!
!
!
router bgp 5511
 bgp router-id ${loopback_200_address}
!
"""

### def HUAWEI CONFIG ###

huawei_config = []

huawei_config_part_1 = """#
undo mpls lsr-id
Y
#
undo interface Loopback200
#"""

huawei_config_part_2 = """#
interface LoopBack0
 undo ipv6 address
% for item in loopback_200_config:
 ${item}
% endfor
#
interface LoopBack10
% for item in loopback_0_config:
${item}
% endfor
#
#
info-center loghost source LoopBack10
ntp-service source-interface LoopBack10
ntp-service ipv6 source-interface LoopBack10
sftp client-source -i LoopBack10
snmp-agent trap source LoopBack10
#
#
bgp ${bgp_as}
% for item in neighbor_groups:
peer ${item} connect-interface LoopBack10
% endfor
#
bgp ${bgp_as}
 router-id ${loopback_200_address}
Y
#
#
#
${router_id_line}
#
mpls lsr-id ${loopback_200_address}
#
#
mpls
mpls te
mpls rsvp-te
mpls te cspf
lsp-trigger ip-prefix TAG-ADVERTISE-FILTER
#
mpls l2vpn
mpls l2vpn default martini
#
mpls ldp
ipv4-family
#
"""

huawei_config.append(huawei_config_part_1)
huawei_config.append(huawei_config_part_2)

### def HUAWEI UNDO CONFIG ###

undo_huawei_config = []

undo_huawei_config_part_1 = """#
undo mpls lsr-id
Y
#
undo interface loopback10
#
"""

undo_huawei_config_part_2 = """#
interface LoopBack0
% for item in loopback_0_config:
${item}
% endfor
#
"""

undo_huawei_config_part_3 = """
#
interface LoopBack200
% for item in loopback_200_config:
 ${item}
% endfor
#
info-center loghost source LoopBack0
ntp-service source-interface LoopBack0
ntp-service ipv6 source-interface LoopBack0
sftp client-source -i LoopBack0
snmp-agent trap source LoopBack0
#
#
bgp ${bgp_as}
% for item in neighbor_groups:
peer ${item} connect-interface LoopBack0
% endfor
#
bgp ${bgp_as}
 router-id ${loopback_200_address}
Y
#
peer ARBOR connect-interface LoopBack0
peer ARBOR connect-interface LoopBack0
peer RR-SERVER-L0-IPV6 connect-interface LoopBack0
#
${router_id_line}
#
mpls lsr-id ${loopback_200_address}
#
"""

undo_huawei_config.append(undo_huawei_config_part_1)
undo_huawei_config.append(undo_huawei_config_part_2)
undo_huawei_config.append(undo_huawei_config_part_3)


### def JUNIPER CONFIG ###

juniper_config = """
delete interfaces lo0 unit 0 family inet address ${loopback_0_ipv4_address}/32 primary
set interfaces lo0 unit 0 family inet address ${loopback_0_ipv4_address}/32
set interfaces lo0 unit 0 family inet address ${loopback_200_ipv4_address}/32 primary
set routing-options router-id ${loopback_200_ipv4_address}
set protocols ldp transport-address ${loopback_200_ipv4_address}
"""

undo_juniper_config = """
set interfaces lo0 unit 0 family inet address ${loopback_0_ipv4_address}/32 primary
delete interfaces lo0 unit 0 family inet address ${loopback_200_ipv4_address}/32 primary
set routing-options router-id ${loopback_0_ipv4_address}
set protocols ldp transport-address ${loopback_0_ipv4_address}
"""

### def PRE POST CHECK COMMANDS ###
prepost_commands_1 = {
    'cisco_ios':[
        'show run interface LoopBack 0',
        'show run interface LoopBack 10',
        'show run interface LoopBack 200',
        'show run | include Loopback0',
        'show run | include Loopback10',
        'show run | include Loopback200'
        ],
    'cisco_xr':[
        'show run interface LoopBack 0',
        'show run interface LoopBack 10',
        'show run interface LoopBack 200',
        'show run | include Loopback0',
        'show run | include Loopback10',
        'show run | include Loopback200'
        ],
    'huawei':[
        'display current-configuration interface LoopBack 0',
        'display current-configuration interface LoopBack 10',
        'display current-configuration interface LoopBack 200',
        'display current-configuration | include LoopBack0',
        'display current-configuration | include LoopBack10',
        'display current-configuration | include LoopBack200',
        ],
    'juniper':[
        'show configuration interfaces lo0 | display set',
        'show configuration | match transport-address | display set'
        ]
}


###############################################################################

def do_pre_post_check(post = None, printall = None):
    loopback_0_address, loopback_10_address, loopback_200_address = str(), str(), str()
    CGI_CLI.uprint('%s-CHECK START:' % ('POST' if post else 'PRE'), tag = 'h2', color = 'blue')

    check_outputs_1 = RCMD.run_commands(prepost_commands_1, printall = True)

    if RCMD.router_type == 'cisco_xr' or RCMD.router_type == 'cisco_ios':
        try:    loopback_0_address = check_outputs_1[0].split('ipv4 address')[1].split()[0].strip()
        except: pass
        try:    loopback_10_address = check_outputs_1[1].split('ipv4 address')[1].split()[0].strip()
        except: pass
        try:    loopback_200_address = check_outputs_1[2].split('ipv4 address')[1].split()[0].strip()
        except: pass

    if RCMD.router_type == 'huawei':
        try:    loopback_0_address = check_outputs_1[0].split('ip address')[1].split()[0].strip()
        except: pass
        try:    loopback_10_address = check_outputs_1[1].split('ip address')[1].split()[0].strip()
        except: pass
        try:    loopback_200_address = check_outputs_1[2].split('ip address')[1].split()[0].strip()
        except: pass

    prepost_commands_2 = {
        'cisco_ios':[
            '%s' % ('show run | include ' + loopback_0_address if loopback_0_address else str()),
            '%s' % ('show run | include ' + loopback_10_address if loopback_10_address else str()),
            '%s' % ('show run | include ' + loopback_200_address if loopback_200_address else str())
            ],
        'cisco_xr':[
            '%s' % ('show run | include ' + loopback_0_address if loopback_0_address else str()),
            '%s' % ('show run | include ' + loopback_10_address if loopback_10_address else str()),
            '%s' % ('show run | include ' + loopback_200_address if loopback_200_address else str())
            ],
        'huawei':[
            '%s' % ('display current-configuration | include ' + loopback_0_address if loopback_0_address else str()),
            '%s' % ('display current-configuration | include ' + loopback_10_address if loopback_10_address else str()),
            '%s' % ('display current-configuration | include ' + loopback_200_address if loopback_200_address else str())
            ],
        'juniper':[]
    }

    check_outputs_2 = RCMD.run_commands(prepost_commands_2, printall = True)

    if printall: CGI_CLI.uprint('%s-CHECK DONE.' % ('POST' if post else 'PRE'))
    else: CGI_CLI.uprint('\n')

##############################################################################

def render_template(config_template = None):
    ### CONFIG COULD HAVE MORE PARTS ###
    if isinstance(config_template, (list,tuple)):
        config_to_apply = []
        for config_item in config_template:
            mytemplate = Template(config_item,strict_undefined=True)
            config_to_apply.append(str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n')
    else:
        config_to_apply = str()
        mytemplate = Template(config_template,strict_undefined=True)
        config_to_apply += str(mytemplate.render(**data)).rstrip().replace('\n\n','\n').replace('  ',' ') + '\n'
    return config_to_apply


##############################################################################
#
# def BEGIN MAIN
#
##############################################################################
if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ########################################################
USERNAME, PASSWORD = CGI_CLI.init_cgi(chunked = True, log = True)
traceback_found = None
logfilename = None
device = None
if CGI_CLI.data.get("device"): device = CGI_CLI.data.get("device")
printall = CGI_CLI.data.get("printall")
iptac_server = LCMD.run_command(cmd_line = 'hostname', printall = None).strip()
if CGI_CLI.cgi_active and not (USERNAME and PASSWORD):
    if iptac_server == 'iptac5': USERNAME, PASSWORD = 'iptac', 'paiiUNDO'

try:
    ### def LOGFILENAME GENERATION, DO LOGGING ONLY WHEN DEVICE LIST EXISTS ###
    if device:
        logfilename = generate_logfilename(prefix = str(device).upper(), \
            USERNAME = USERNAME, suffix = str('rid') + '.log')
        ### NO WINDOWS LOGGING ################################################
        if 'WIN32' in sys.platform.upper(): logfilename = None
        if logfilename: CGI_CLI.set_logfile(logfilename = logfilename)

    ### START PRINTING AND LOGGING ############################################
    changelog = 'https://github.com/peteneme/pyxWorks/commits/master/rid_migration/rid_migration.py'
    SCRIPT_NAME = 'ROUTER ID MIGRATION TOOL'
    if CGI_CLI.cgi_active:
        CGI_CLI.uprint('<h1 style="color:blue;">%s <a href="%s" style="text-decoration: none">(v.%s)</a></h1>' % \
            (SCRIPT_NAME, changelog, CGI_CLI.VERSION()), raw = True)
        CGI_CLI.uprint('WARNING: PLEASE BE CAREFUL WHEN USING THIS TOOL!\nSUBMITING THE FORM WILL CHANGE CONFIGURATION ON LIVE DEVICE!', \
            tag = 'h2', color = 'red')
    else: CGI_CLI.uprint('%s (v.%s)' % (SCRIPT_NAME,CGI_CLI.VERSION()), \
              tag = 'h1', color = 'blue')
    if printall: CGI_CLI.print_args()

    ### def HTML MENU SHOWS ONLY IN CGI MODE ##################################
    if CGI_CLI.cgi_active and not CGI_CLI.submit_form:
        CGI_CLI.formprint([{'text':'device'},'<br/>',\
        {'text':'username'},'<br/>',\
        {'password':'password'},'<br/>',\
        {'checkbox':'rollback'},'<br/>',\
        {'checkbox':'show_config_only'},'<br/>',\
        {'checkbox':'printall'},'<br/>','<br/>'], \
        submit_button = 'OK', pyfile = None, tag = None, color = None)

    config_to_apply = str()

    if not device:
        if CGI_CLI.cgi_active and CGI_CLI.submit_form:
            CGI_CLI.uprint('DEVICE NAME NOT INSERTED!', tag = 'h1', color = 'red')

    for device in [device]:
        if not device: continue
        rcmd_outputs = RCMD.connect(device, username = USERNAME, \
            logfilename = logfilename, password = PASSWORD)

        if not RCMD.ssh_connection:
            CGI_CLI.uprint('PROBLEM TO CONNECT TO %s DEVICE.' % (device), color = 'red')
            RCMD.disconnect()
            continue

        ### def PRECHECK SECTION ##############################################
        do_pre_post_check(post = None, printall = printall)

        ### RID MIGRATION START ###############################################
        if RCMD.router_type == 'cisco_xr':
            if not CGI_CLI.data.get('rollback'):
                collector_cmd = {'cisco_xr':['sh run interface loopback 0','sh run interface loopback 200',
                "show running-config router bgp | utility egrep 'neighbor-group|update-source' | exclude use neighbor-group"]}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                try: loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface Loopback0\n')[1].replace('Loopback0','Loopback10').strip().split('!')[0] + '!').splitlines()
                except: loopback_0_config = []
                try: loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface Loopback200\n')[1].replace('Loopback200','Loopback0').strip().split('!')[0] + '!').splitlines()
                except: loopback_200_config = []
                try:    loopback_200_address = rcmd_outputs[1].split('ipv4 address')[1].split()[0].strip()
                except: loopback_200_address = str()
                try:
                    neighbor_groups = re.findall(r'neighbor-group\s+[0-9a-zA-Z\-\.\@\_]+$\s+update-source Loopback0', rcmd_outputs[2], re.MULTILINE)
                    neighbor_groups = [ item.splitlines()[0].replace('neighbor-group','').strip() for item in neighbor_groups ]
                except: neighbor_groups = []

                data = {}
                data['loopback_0_config']    = loopback_0_config
                data['loopback_200_config']  = loopback_200_config
                data['neighbor_groups']      = neighbor_groups
                data['loopback_200_address'] = loopback_200_address
                data['bgp_as'] = '5511'

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(xr_config)
            else:
                ### UNDO/ROLLBACK CONFIG GENERATION ###
                collector_cmd = {'cisco_xr':['sh run interface loopback 10','sh run interface loopback 0',
                "show running-config router bgp | utility egrep 'neighbor-group|update-source' | exclude use neighbor-group"]}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                try: loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface Loopback10\n')[1].replace('Loopback10','Loopback0').strip().split('!')[0] + '!').splitlines()
                except: loopback_0_config = []
                try:loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface Loopback0\n')[1].replace('Loopback0','Loopback200').strip().split('!')[0] + '!').splitlines()
                except: loopback_200_config = []
                ### output 0 = lo10 ###
                try:    loopback_200_address = rcmd_outputs[0].split('ipv4 address')[1].split()[0].strip()
                except: loopback_200_address = str()
                try:
                    neighbor_groups = re.findall(r'neighbor-group\s+[0-9a-zA-Z\-\.\@\_]+$\s+update-source Loopback10', rcmd_outputs[2], re.MULTILINE)
                    neighbor_groups = [ item.splitlines()[0].replace('neighbor-group','').strip() for item in neighbor_groups ]
                except: neighbor_groups = []

                data = {}
                data['loopback_0_config']    = loopback_0_config
                data['loopback_200_config']  = loopback_200_config
                data['neighbor_groups']      = neighbor_groups
                data['loopback_200_address'] = loopback_200_address
                data['bgp_as'] = '5511'

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(undo_xr_config)

        ### HUAWEI #####################################################################
        if RCMD.router_type == 'huawei':
            if not CGI_CLI.data.get('rollback'):
                collector_cmd = {'huawei':[
                    'disp current-configuration interface LoopBack 0',
                    'disp current-configuration interface LoopBack 200',
                    'display current-configuration configuration bgp | include connect-interface',
                    'disp current-configuration | include router id']}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                try: loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface LoopBack0\n')[1].replace('Loopback0','Loopback10').strip().split('#')[0] + '#').splitlines()
                except: loopback_0_config = []
                try: loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface LoopBack200\n')[1].replace('Loopback200','Loopback0').strip().split('#')[0] + '#').splitlines()
                except: loopback_200_config = []
                try:    loopback_200_address = rcmd_outputs[1].split('ip address')[1].split()[0].strip()
                except: loopback_200_address = str()
                try:
                    neighbor_groups = re.findall(r'peer\s+[0-9a-zA-Z\-\.\@\_]+ connect-interface LoopBack0', rcmd_outputs[2], re.MULTILINE)
                    neighbor_groups = [ item.splitlines()[0].replace('peer','').replace('connect-interface LoopBack0','').strip() for item in neighbor_groups ]
                except: neighbor_groups = []

                if 'router id 193.251.245.' in rcmd_outputs[3] and loopback_200_address:
                    router_id_line = 'router id ' + loopback_200_address
                else: router_id_line = '#'

                data = {}
                data['loopback_0_config']    = loopback_0_config
                data['loopback_200_config']  = loopback_200_config
                data['neighbor_groups']      = neighbor_groups
                data['loopback_200_address'] = loopback_200_address
                data['bgp_as']               = '5511'
                data['router_id_line']       = router_id_line

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(huawei_config)
            else:
                ### UNDO/ROLLBACK CONFIG GENERATION ###
                collector_cmd = {'huawei':[
                    'disp current-configuration interface LoopBack 10',
                    'disp current-configuration interface LoopBack 0',
                    'display current-configuration configuration bgp | include connect-interface',
                    'disp current-configuration | include router id']}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                try: loopback_0_config    = (rcmd_outputs[0].replace('\r','').split('interface LoopBack10\n')[1].replace('Loopback10','Loopback0').strip().split('#')[0] + '#').splitlines()
                except: loopback_0_config = []
                try: loopback_200_config  = (rcmd_outputs[1].replace('\r','').split('interface LoopBack0\n')[1].replace('Loopback0','Loopback200').strip().split('#')[0] + '#').splitlines()
                except: loopback_200_config = []
                try:    loopback_200_address = rcmd_outputs[0].split('ip address')[1].split()[0].strip()
                except: loopback_200_address = str()
                try:    loopback_0_address = rcmd_outputs[0].split('ip address')[1].split()[0].strip()
                except: loopback_0_address = str()
                try:
                    neighbor_groups = re.findall(r'peer\s+[0-9a-zA-Z\-\.\@\_]+ connect-interface LoopBack10', rcmd_outputs[2], re.MULTILINE)
                    neighbor_groups = [ item.splitlines()[0].replace('peer','').replace('connect-interface LoopBack10','').strip() for item in neighbor_groups ]
                except: neighbor_groups = []

                if 'router id 193.251.245.' in rcmd_outputs[3] and loopback_0_address:
                    router_id_line = 'router id ' + loopback_0_address
                else: router_id_line = '#'

                data = {}
                data['loopback_0_config']    = loopback_0_config
                data['loopback_200_config']  = loopback_200_config
                data['neighbor_groups']      = neighbor_groups
                data['loopback_200_address'] = loopback_200_address
                data['bgp_as']               = '5511'
                data['router_id_line']       = router_id_line

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(undo_huawei_config)

        ### JUNIPER #####################################################################
        if RCMD.router_type == 'juniper':
            if not CGI_CLI.data.get('rollback'):
                collector_cmd = {'juniper':[ 'show configuration interfaces lo0 | display set']}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                loopback_0_ipv4_address, loopback_200_ipv4_address, loopback_0_ipv6_address = str(), str(), str()
                look_for = ['inet address 193.251.245.','inet address 172.25.4.','inet6 address 2001:688:0:1:']
                for line in rcmd_outputs[0].splitlines():
                    if look_for[0] in line and 'primary' in line:
                        loopback_0_ipv4_address = look_for[0].replace('inet address ','') + line.split(look_for[0])[1].split()[0].split('/')[0]
                    if look_for[1] in line and not 'primary' in line:
                        loopback_200_ipv4_address = look_for[1].replace('inet address ','') + line.split(look_for[1])[1].split()[0].split('/')[0]
                    # if look_for[2] in line and 'primary' in line:
                        # loopback_0_ipv6_address = look_for[2].replace('inet6 address ','') + line.split(look_for[2])[1].split()[0].split('/')[0]
                # loopback_200_ipv6_address = ipv4_to_ipv6_obs(loopback_0_ipv4_address)[0] if loopback_0_ipv4_address else str()

                data = {}
                data['loopback_0_ipv4_address']    = loopback_0_ipv4_address
                data['loopback_200_ipv4_address']  = loopback_200_ipv4_address
                #data['loopback_0_ipv6_address']    = loopback_0_ipv6_address
                #data['loopback_200_ipv6_address']  = loopback_200_ipv6_address
                data['bgp_as']               = '5511'

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(juniper_config)
            else:
                ### UNDO/ROLLBACK CONFIG GENERATION ###
                collector_cmd = {'juniper':[ 'show configuration interfaces lo0 | display set']}

                rcmd_outputs = RCMD.run_commands(collector_cmd, printall = printall)

                loopback_0_ipv4_address, loopback_200_ipv4_address, loopback_0_ipv6_address = str(), str(), str()
                look_for = ['inet address 193.251.245.','inet address 172.25.4.','inet6 address 2001:688:0:1:']
                for line in rcmd_outputs[0].splitlines():
                    if look_for[0] in line:
                        loopback_0_ipv4_address = look_for[0].replace('inet address ','') + line.split(look_for[0])[1].split()[0].split('/')[0]
                    if look_for[1] in line:
                        loopback_200_ipv4_address = look_for[1].replace('inet address ','') + line.split(look_for[1])[1].split()[0].split('/')[0]
                    # if look_for[2] in line and 'primary' in line:
                        # loopback_0_ipv6_address = look_for[2].replace('inet6 address ','') + line.split(look_for[2])[1].split()[0].split('/')[0]
                # loopback_200_ipv6_address = ipv4_to_ipv6_obs(loopback_0_ipv4_address)[0] if loopback_0_ipv4_address else str()

                data = {}
                data['loopback_0_ipv4_address']    = loopback_0_ipv4_address
                data['loopback_200_ipv4_address']  = loopback_200_ipv4_address
                #data['loopback_0_ipv6_address']    = loopback_0_ipv6_address
                #data['loopback_200_ipv6_address']  = loopback_200_ipv6_address
                data['bgp_as']               = '5511'

                if printall:
                    CGI_CLI.uprint('\n')
                    CGI_CLI.uprint(data, name = True, jsonprint = True)
                    CGI_CLI.uprint('\n\n')

                if data:
                   None_elements = get_void_json_elements(data)

                   CGI_CLI.uprint('VOID ELEMENTS CHECK: %s\n' % (str(None_elements) if len(None_elements)>0 else 'OK'), \
                       color = 'red' if len(None_elements)>0 else 'green')

                   if len(None_elements)>0:
                      CGI_CLI.uprint('\nVOID DATA PROBLEM FOUND!', tag = 'h1', color = 'red')
                      RCMD.disconnect()
                      continue

                config_to_apply = render_template(undo_juniper_config)

        ### def PRINT CONFIG ##################################################
        CGI_CLI.uprint('CONFIG:\n', tag = 'h1', color = 'blue')

        if isinstance(config_to_apply, (list,tuple)):
            for config_item in config_to_apply:
                CGI_CLI.uprint('CONFIG PART:\n\n' + config_item + "\n\n", color = 'blue')
        else: CGI_CLI.uprint(config_to_apply, color = 'blue')


        ### def PUSH CONFIG TO DEVICE #########################################
        if not CGI_CLI.data.get('show_config_only'):
            if isinstance(config_to_apply, (list,tuple)):
                for config_item in config_to_apply:
                    splitted_config = copy.deepcopy(config_item)
                    try: splitted_config = str(splitted_config.decode("utf-8")).splitlines()
                    except: splitted_config = []

                    rcmd_outputs = RCMD.run_commands(cmd_data = splitted_config, \
                        conf = True, printall = printall, \
                        sim_config = CGI_CLI.data.get('sim',None))
            else:
                splitted_config = copy.deepcopy(config_to_apply)
                try: splitted_config = str(splitted_config.decode("utf-8")).splitlines()
                except: splitted_config = []

                rcmd_outputs = RCMD.run_commands(cmd_data = splitted_config, \
                    conf = True, printall = printall, \
                    sim_config = CGI_CLI.data.get('sim',None))


        ### def POSTCHECK SECTION #############################################
        if not CGI_CLI.data.get('show_config_only'):
            do_pre_post_check(post = True, printall = printall)

        RCMD.disconnect()

except SystemExit: pass
except:
    traceback_found = True
    CGI_CLI.uprint(traceback.format_exc(), tag = 'h3',color = 'magenta')

### PRINT LOGFILENAME #########################################################
if logfilename: CGI_CLI.uprint(' ==> File %s created.' % (logfilename))

### SEND EMAIL WITH ERROR/TRACEBACK LOGFILE TO SUPPORT ########################
if traceback_found:
    send_me_email( \
        subject = 'TRACEBACK-RID-' + logfilename.replace('\\','/').\
        split('/')[-1] if logfilename else str(), \
        file_name = logfilename, username = 'pnemec')
    send_me_email( \
        subject = 'TRACEBACK-RID-' + logfilename.replace('\\','/').\
        split('/')[-1] if logfilename else str(), \
        file_name = logfilename, username = 'mkrupa')