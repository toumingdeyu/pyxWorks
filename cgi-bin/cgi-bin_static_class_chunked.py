#!/usr/bin/python

import sys, os, io, paramiko, json, copy, html, traceback
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
                            help = "Target router to access. (Optionable device list separated ba comma, i.e. --device DEVICE1,DEVICE2)")
        parser.add_argument("--sw_release",
                            action = "store", dest = 'sw_release',
                            default = str(),
                            help = "sw release number with or without dots, i.e. 653 or 6.5.3, or alternatively sw release filename")
        parser.add_argument("--files",
                            action = "store", dest = 'sw_files',
                            default = str(),
                            help = "--files OTI.tar,SMU,pkg,bin")
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
        parser.add_argument("--slave",
                           action = 'store_true', dest = "copy_device_sw_files_to_huawei_slave_cfcard",
                           default = None,
                           help = "copy device sw files to huawei slave cfcard")
        parser.add_argument("--delete",
                            action = 'store_true', dest = "delete_device_sw_files_on_end",
                            default = None,
                            help = "delete device sw release files on end after sw upgrade")
        # parser.add_argument("--sim",
                            # action = "store_true", dest = 'sim',
                            # default = None,
                            # help = "config simulation mode")
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
    def init_cgi(chunked = None, css_style = None, newline = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.chunked = None
        CGI_CLI.CSS_STYLE = css_style if css_style else str()
        ### TO BE PLACED - BEFORE HEADER ###
        CGI_CLI.newline = '\n' if not newline else newline
        CGI_CLI.chunked_transfer_encoding_string = \
            "Transfer-Encoding: chunked%s" % (CGI_CLI.newline)
        CGI_CLI.status_line = \
            "HTTP/1.1 Status: 200 OK%s" % (CGI_CLI.newline)
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
        ### DECIDE - CLI OR CGI MODE #######################################
        CGI_CLI.remote_addr =  dict(os.environ).get('REMOTE_ADDR','')
        CGI_CLI.http_user_agent = dict(os.environ).get('HTTP_USER_AGENT','')
        if CGI_CLI.remote_addr and CGI_CLI.http_user_agent:
            CGI_CLI.cgi_active = True
        CGI_CLI.args = CGI_CLI.cli_parser()
        if not CGI_CLI.cgi_active: CGI_CLI.data = vars(CGI_CLI.args)
        if CGI_CLI.cgi_active:
            CGI_CLI.chunked = chunked
            sys.stdout.write("%s%sContent-type:text/html; charset=utf-8%s%s" %
                (CGI_CLI.status_line,
                CGI_CLI.chunked_transfer_encoding_string if CGI_CLI.chunked else str(),
                CGI_CLI.newline, CGI_CLI.newline))
            sys.stdout.flush()
            CGI_CLI.print_chunk("<!DOCTYPE html><html><head><title>%s</title>%s</head><body>" %
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit', \
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
        try:
            if not (LCMD.logfilenam == 'nul' or LCMD.logfilename == '/dev/null'):
                actual_logfilename = LCMD.logfilename
        except: pass
        try:
            if not (RCMD.logfilenam == 'nul' or RCMD.logfilename == '/dev/null'):
               actual_logfilename = RCMD.logfilename
        except: pass
        if logfilename: actual_logfilename = logfilename
        if actual_logfilename == 'nul' or actual_logfilename == '/dev/null' \
            or not actual_logfilename: pass
        else: CGI_CLI.logfilename = actual_logfilename

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
        log = None, no_newlines = None, start_tag = None, end_tag = None, raw = None):
        """NOTE: name parameter could be True or string.
           start_tag - starts tag and needs to be ended next time by end_tag
           raw = True , print text as it is, not convert to html. Intended i.e. for javascript
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
        if CGI_CLI.cgi_active and not raw:
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT
            if color and not (tag or start_tag): tag = 'p';
            if tag: CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            elif start_tag: CGI_CLI.print_chunk('<%s%s%s>'%(start_tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"' % (color) if color else str()))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                    replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
            CGI_CLI.print_chunk(print_name + print_text)
        elif CGI_CLI.cgi_active and raw:
            CGI_CLI.print_chunk(print_text)
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
            ### CLI_MODE ###
            if no_newlines:
                sys.stdout.write(text_color + print_name + print_text + CGI_CLI.bcolors.ENDC)
                sys.stdout.flush()
            else:
                print(text_color + print_name + print_text + CGI_CLI.bcolors.ENDC)
        del print_text
        if CGI_CLI.cgi_active and not raw:
            if tag: CGI_CLI.print_chunk('</%s>' % (tag))
            elif end_tag: CGI_CLI.print_chunk('</%s>' % (end_tag))
            elif not no_newlines: CGI_CLI.print_chunk('<br/>');
            ### PRINT PER TAG ###
            CGI_CLI.print_chunk(print_per_tag)
        ### LOGGING ###
        if CGI_CLI.logfilename and log:
            with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                CGI_CLI.fp.write(print_name + log_text + '\n')
                del log_text


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
            CGI_CLI.print_chunk('<br/>');
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
            if CGI_CLI.cgi_active: CGI_CLI.print_chunk('<br/><a href = "./%s">RELOAD</a>' % (pyfile))

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
        print_string += 'CGI_CLI.USERNAME[%s], CGI_CLI.PASSWORD[%s]\n' % (CGI_CLI.USERNAME, 'Yes' if CGI_CLI.PASSWORD else 'No')
        print_string += 'remote_addr[%s], ' % dict(os.environ).get('REMOTE_ADDR','')
        print_string += 'browser[%s]\n' % dict(os.environ).get('HTTP_USER_AGENT','')
        print_string += 'CGI_CLI.cgi_active[%s]\n' % (str(CGI_CLI.cgi_active))
        if CGI_CLI.cgi_active:
            try: print_string += 'CGI_CLI.data[%s] = %s\n' % (str(CGI_CLI.submit_form),str(json.dumps(CGI_CLI.data, indent = 4)))
            except: pass
        else: print_string += 'CLI_args = %s\nCGI_CLI.data = %s' % (str(sys.argv[1:]), str(json.dumps(CGI_CLI.data,indent = 4)))
        CGI_CLI.uprint(print_string)
        return print_string

    @staticmethod
    def print_env():
        CGI_CLI.uprint(dict(os.environ), name = 'os.environ', jsonprint = True)





##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
CSS_STYLE = """
body {
  background-color: lightblue;
}

h1 {
  color: green;
  text-align: center;
}

p {
  font-family: verdana;
  font-size: 20px;
}
"""


CGI_CLI.init_cgi(chunked = False, css_style = CSS_STYLE)

CGI_CLI.print_args()
CGI_CLI.print_env()
#print(repr(CGI_CLI))
#print(str(CGI_CLI))

# CGI_CLI.uprint('aaa')
# CGI_CLI.uprint('aaa')
# CGI_CLI.uprint(['aaa2','aaa3'])
# CGI_CLI.uprint({'aaa4':'aaa5'}, tag = 'h1' , name = True)
# CGI_CLI.uprint(CGI_CLI.data, name = True, jsonprint = True , tag = 'h1' , color = 'yellow')

# aaa = {'aaa8':'aaa9'}
# CGI_CLI.uprint(aaa, name = True)
# bbb = ['aaa8','aaa9']
# CGI_CLI.uprint(bbb, name = True)
# #cgi.print_environ()

# CGI_CLI.uprint(123423, color = 'red')
# CGI_CLI.uprint('&<">&')



# form = """
# <br/>
# <form action = "/cgi-bin/hello_get.py" method = "post">
# First Name: <input type = "text" name = "first_name"><br />
# Last Name: <input type = "text" name = "last_name" />
# <input type = "submit" value = "Submit" />
# </form>
# """

# print(form)

### https://www.tutorialspoint.com/python/python_cgi_programming.htm




CGI_CLI.formprint([{'text':'email_address'},'<br/>',{'textcontent':'email_body'},'<br/>',{'file':'/var/www/cgi-bin/file_1'},'<br/>',{'checkbox':'aa_ss'},{'radio':'iii_ddd'},{'submit':'YES'},{'submit':'NO'}], submit_button = 'Send_Email', pyfile = None, tag = None, color = None)

CGI_CLI.formprint([{'password':'password'},'<br/>',{'textcontent':'email_body'},'<br/>',{'file':'/var/www/cgi-bin/file_1'},'<br/>',{'checkbox':'aa_ss'},{'radio':'iii_ddd'},{'dropdown':'aa,bb,cc'},{'submit':'YES'},{'submit':'NO'}], submit_button = 'Send_Email', pyfile = None, tag = None, color = None)

### DROPDOWN MENU DOES HTTP500 :(
###CGI_CLI.formprint([{'dropdown':'aa,bb,cc_cc'}])

#CGI_CLI.formprint([{'file':'/var/www/cgi-bin/file_1'},{'dropdown':'aa,bb,cc_cc'},{'checkbox':'aa_ss'},{'radio':'iii_ddd'},'<br/>', {'radio':'q q'},'<br/>',{'submit':'YES'},{'submit':'NO'}],submit_button = None, pyfile = None, tag = None, color = None)



CGI_CLI.formprint([{'raw':'<select name = "dropdown"><option value = "Maths" selected>Maths</option><option value = "Physics">Physics</option></select>'}])

CGI_CLI.uprint('Tag - H1\n', tag = 'h1')
CGI_CLI.uprint('Tag - H2\n', tag = 'h2')
CGI_CLI.uprint('Tag - H3\n', tag = 'h3')

CGI_CLI.uprint('DEFAULT LINE.')
CGI_CLI.uprint('RED LINE.', color='red')

CGI_CLI.uprint("""<?php
echo "My first PHP script!";
?>""", raw = True)

CGI_CLI.uprint("""
        <p id="demo2">Move mouse here...</p>
        <script>
            var still_mouseover = false
            document.getElementById("demo2").onmouseover = function() {myFunction2()};

            function myFunction2() {
                still_mouseover = true
                document.getElementById("demo2").innerHTML = "Mouse is here...";
                setTimeout(function (){
                    if(still_mouseover) {
                        document.getElementById("demo2").innerHTML = "Mouse stays her over 2 seconds...";
                    }
                }, 2000);
            }
            document.getElementById("demo2").onmouseout = function() {myFunction3()};
            function myFunction3() {
                still_mouseover = false
                document.getElementById("demo2").innerHTML = "Mouse was here...";
                setTimeout(function (){
                    document.getElementById("demo2").innerHTML = "Move mouse here...";
                }, 500);
            }
        </script>""", raw = True)
