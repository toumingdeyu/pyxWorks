#!/usr/bin/python

import sys, os, io, paramiko, json, copy, html
import cgi
import cgitb; cgitb.enable()
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
import requests


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


class CGI_CLI(object):
    """
    CGI_handle - Simple statis class for handling CGI parameters and 
                 clean (debug) printing to HTML/CLI    
       Notes:  - In case of cgi_parameters_error - http[500] is raised, 
                 but at least no appache timeout occurs...
    """ 
    # import collections, cgi, six
    # import cgitb; cgitb.enable()
     
    debug = True
    initialized = None
    START_EPOCH = time.time()
    cgi_parameters_error = None
    cgi_active = None

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
                            help = "insert router password interactively getpass.getpass()")                                                        
        parser.add_argument("--pe_device",
                            action = "store", dest = 'pe_device',
                            default = str(),
                            help = "target pe router to check")
        parser.add_argument("--gw_device",
                            action = "store", dest = 'gw_device',
                            default = str(),
                            help = "target gw router to check")                    
        args = parser.parse_args()
        return args
    
    @staticmethod        
    def __cleanup__():
        CGI_CLI.uprint('\nEND[script runtime = %d sec]. '%(time.time() - CGI_CLI.START_EPOCH))
        if CGI_CLI.cgi_active: print("</body></html>")

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor 
        --> Register __cleanup__ in system
        """
        if not 'atexit' in sys.modules: import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(interaction = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.initialized = True 
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), '', '', ''   
        try: form = cgi.FieldStorage()
        except: 
            form = collections.OrderedDict()
            CGI_CLI.cgi_parameters_error = True
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["submit","username","password"]: 
                CGI_CLI.data[variable] = value
            if variable == "submit": CGI_CLI.submit_form = value
            if variable == "username": CGI_CLI.username = value
            if variable == "password": CGI_CLI.password = value
        if CGI_CLI.submit_form or len(CGI_CLI.data)>0: CGI_CLI.cgi_active = True
        if CGI_CLI.cgi_active:
            if not 'cgitb' in sys.modules: import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        if not 'atexit' in sys.modules: import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM CGI/CLI
        CGI_CLI.args = CGI_CLI.cli_parser()               
        try:    CGI_CLI.PASSWORD        = os.environ['NEWR_PASS']
        except: CGI_CLI.PASSWORD        = str()
        try:    CGI_CLI.USERNAME        = os.environ['NEWR_USER']
        except: CGI_CLI.USERNAME        = str()
        if CGI_CLI.args.username:        
            CGI_CLI.USERNAME = CGI_CLI.args.username
            CGI_CLI.PASSWORD = str()
            if interaction or CGI_CLI.args.getpass: CGI_CLI.PASSWORD = getpass.getpass("TACACS password: ")
            elif CGI_CLI.args.password: CGI_CLI.password = CGI_CLI.args.password                
        if CGI_CLI.username: CGI_CLI.USERNAME = CGI_CLI.username
        if CGI_CLI.password: CGI_CLI.PASSWORD = CGI_CLI.password
        if CGI_CLI.cgi_active or 'WIN32' in sys.platform.upper(): bcolors = nocolors
        CGI_CLI.uprint('USERNAME[%s], PASSWORD[%s]' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No'))        
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

    @staticmethod 
    def oprint(text, tag = None):
        if CGI_CLI.debug: 
            if CGI_CLI.cgi_active:
                if tag and 'h' in tag: print('<%s>'%(tag))
                if tag and 'p' in tag: print('<p>')
                if isinstance(text, six.string_types): 
                    text = str(text.replace('\n','<br/>').replace(' ','&nbsp;'))
                else: text = str(text)   
            print(text)
            if CGI_CLI.cgi_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod 
    def uprint(text, tag = None, color = None, name = None, jsonprint = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name = copy.deepcopy(text), str()
        if CGI_CLI.debug:
            if jsonprint:
                if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                    try: print_text = json.dumps(text, indent = 4)
                    except: pass   
            if name==True:
                if not 'inspect.currentframe' in sys.modules: import inspect
                callers_local_vars = inspect.currentframe().f_back.f_locals.items()
                var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
                if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
            elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '
            
            print_text = str(print_text)
            if CGI_CLI.cgi_active:
                if tag and 'h' in tag: print('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
                if color or tag and 'p' in tag: tag = 'p'; print('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
                if isinstance(print_text, six.string_types): 
                    print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                        replace('>','&gt;').replace('\n','<br/>').replace(' ','&nbsp;')) 
            print(print_name + print_text)
            del print_text
            if CGI_CLI.cgi_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod 
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, color = None):
        """ print simple HTML form """
        i_submit_button = 'Submit' if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            print('<br/>');
            if tag and 'h' in tag: print('<%s%s>'%(tag,' style="color:%s;"'%(color) if color else str()))
            if color or tag and 'p' in tag: tag = 'p'; print('<p%s>'%(' style="color:%s;"'%(color) if color else str()))
            print('<form action = "/cgi-bin/%s" method = "post">' % (i_pyfile))


            #print('First Name: <input type = "text" name = "first_name"><br />')
            print('<textarea type = "textcontent" name = "commandtoexecute" cols = "60" rows = "3"></textarea>')



            print('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%(i_submit_button,i_submit_button))
            print('</form>')
            if tag and 'p' in tag: print('</p>')
            if tag and 'h' in tag: print('</%s>'%(tag))

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
        print_string = 'python[%s], ' % (str(python_version()))
        print_string += 'file[%s], ' % (sys.argv[0])
        print_string += 'version[%s], ' % (CGI_CLI.VERSION())
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_args[%s] = %s' % (str(CGI_CLI.submit_form),json.dumps(CGI_CLI.data)) 
            except: pass                 
        else: print_string += 'CLI_args = %s' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string

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
    def run_command(cmd_line = None, logfilename = None, printall = None):
        os_output, cmd_list = str(), None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_line:      
            with open(logfilename,"a+") as LCMD.fp:      
                if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line))
                LCMD.fp.write('LOCAL_COMMAND: ' + cmd_line + '\n')
                try: os_output = subprocess.check_output(str(cmd_line), shell=True).decode("utf-8") 
                except (subprocess.CalledProcessError) as e: 
                    if printall: CGI_CLI.uprint(str(e))
                    LCMD.fp.write(str(e) + '\n')
                except: 
                    exc_text = traceback.format_exc()
                    CGI_CLI.uprint(exc_text)
                    LCMD.fp.write(exc_text + '\n')                
                if os_output and printall: CGI_CLI.uprint(os_output)
                LCMD.fp.write(os_output + '\n')
        return os_output

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
                    if printall: CGI_CLI.uprint("LOCAL_COMMAND: " + str(cmd_line))
                    LCMD.fp.write('LOCAL_COMMAND: ' + cmd_line + '\n')
                    try: os_output = subprocess.check_output(str(cmd_line), shell=True).decode("utf-8") 
                    except (subprocess.CalledProcessError) as e: 
                        if printall: CGI_CLI.uprint(str(e))
                        LCMD.fp.write(str(e) + '\n')
                    except: 
                        exc_text = traceback.format_exc()
                        CGI_CLI.uprint(exc_text)
                        LCMD.fp.write(exc_text + '\n')                
                    if os_output and printall: CGI_CLI.uprint(os_output)
                    LCMD.fp.write(os_output + '\n')
                    os_outputs.append(os_output)
        return os_outputs

    @staticmethod
    def eval_command(cmd_data = None, logfilename = None, printall = None):
        local_output = None
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)):
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EVAL: %s" % (cmd_data))
                try: 
                    local_output = eval(cmd_data)
                    if printall: CGI_CLI.uprint(str(local_output))
                    LCMD.fp.write('EVAL: ' + cmd_data + '\n' + str(local_output) + '\n')
                except Exception as e: 
                    if printall:CGI_CLI.uprint('EVAL_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EVAL_PROBLEM[' + str(e) + ']\n')
        return local_output
        
    @staticmethod
    def exec_command(cmd_data = None, logfilename = None, printall = None):
        logfilename, printall = LCMD.init_log_and_print(logfilename, printall)
        if cmd_data and isinstance(cmd_data, (six.string_types)): 
            with open(logfilename,"a+") as LCMD.fp:
                if printall: CGI_CLI.uprint("EXEC: %s" % (cmd_data))
                LCMD.fp.write('EXEC: ' + cmd_data + '\n')
                ### EXEC CODE WORKAROUND for OLD PYTHON v2.7.5
                try:
                    edict = {}; eval(compile(cmd_data, '<string>', 'exec'), globals(), edict)
                except Exception as e: 
                    if printall:CGI_CLI.uprint('EXEC_PROBLEM[' + str(e) + ']')
                    LCMD.fp.write('EXEC_PROBLEM[' + str(e) + ']\n')                    
        return None

            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
#CGI_CLI()
CGI_CLI.init_cgi()
CGI_CLI.print_args()


if CGI_CLI.cgi_active:
    CGI_CLI.formprint()
    LCMD.init(printall = True)
    LCMD.run_command(CGI_CLI.data.get('commandtoexecute',''))

