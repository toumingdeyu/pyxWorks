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
    class CGI_handle - Simple statis class for handling CGI parameters and
                       clean (debug) printing to HTML/CLI
    INTERFACE FUNCTIONS:
    CGI_CLI.init_cgi() - init CGI_CLI class
    CGI_CLI.print_args(), CGI_CLI.print_env() - debug printing
    CGI_CLI.uprint() - printing CLI/HTML text
    CGI_CLI.formprint() - printing of HTML forms
    CGI_CLI.set_http_status_code() - sets return http status code to decimal value
    """
    # import collections, cgi, six
    # import cgitb; cgitb.enable()

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
        args = parser.parse_args()
        return args

    @staticmethod
    def __cleanup__():
        if not CGI_CLI.buffer_printed:
            if CGI_CLI.cgi_active and CGI_CLI.return_http_status: print("Status: %s %s\r\n" % (str(CGI_CLI.http_status_code),''))
            print(CGI_CLI.buffer_string)
            print('%sEND[script runtime = %d sec]. '%('<br/>' if CGI_CLI.cgi_active else '\n',time.time() - CGI_CLI.START_EPOCH))
            if CGI_CLI.cgi_active: print("</body></html>")
        CGI_CLI.buffer_printed = True

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi(interaction = None, return_http_status = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.cgi_active = None
        CGI_CLI.initialized = True
        CGI_CLI.data, CGI_CLI.submit_form, CGI_CLI.username, CGI_CLI.password = \
            collections.OrderedDict(), '', '', ''
        CGI_CLI.buffer_string, CGI_CLI.buffer_printed = str(), None
        CGI_CLI.http_status_code = '200'
        CGI_CLI.return_http_status = return_http_status
        form, CGI_CLI.data = collections.OrderedDict(), collections.OrderedDict()
        try:
            form = cgi.FieldStorage()
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
            #if not 'cgitb' in sys.modules: import cgitb; cgitb.enable()
            CGI_CLI.http_status_code = '200'
            print("Content-type:text/html")
            if CGI_CLI.return_http_status: print("Retry-After: 300")
            CGI_CLI.buffprint('\r\n\r\n')
            CGI_CLI.buffprint("<html><head><title>%s</title></head><body>" %
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        ### GAIN USERNAME AND PASSWORD FROM CGI/CLI
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
        CGI_CLI.cgi_save_files()
        return CGI_CLI.USERNAME, CGI_CLI.PASSWORD

    @staticmethod
    def set_http_status_code(http_status_code = None):
        if http_status_code:
            try: CGI_CLI.http_status_code = str(http_status_code)
            except: pass

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
                            except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

    @staticmethod
    def buffprint(text):
        CGI_CLI.buffer_string += str(text) + '\n'

    @staticmethod
    def uprint(text, tag = None, tag_id = None, color = None, name = None, jsonprint = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name = copy.deepcopy(text), str()
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
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT
            if color and not tag: tag = 'p';
            if tag: CGI_CLI.buffprint('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"'%(color) if color else 'black'))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                    replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
        CGI_CLI.buffprint(print_name + print_text)
        del print_text
        if CGI_CLI.cgi_active:
            if tag: CGI_CLI.buffprint('</%s>'%(tag))
            else: CGI_CLI.buffprint('<br/>');

    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, color = None):
        """ formprint() - print simple HTML form
            form_data - string, just html raw OR list or dict values = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
                      - value in dictionary means cgi variable name / printed componenet value
        """
        def subformprint(data_item):
            if isinstance(data_item, six.string_types): CGI_CLI.buffprint(data_item)
            elif isinstance(data_item, (dict,collections.OrderedDict)):
                if data_item.get('raw',None): CGI_CLI.buffprint(data_item.get('raw'))
                elif data_item.get('textcontent',None):
                    CGI_CLI.buffprint('<textarea type = "textcontent" name = "%s" cols = "40" rows = "4">%s</textarea>'%\
                        (data_item.get('textcontent'), data_item.get('text','')))
                elif data_item.get('text'):
                    CGI_CLI.buffprint('%s: <input type = "text" name = "%s"><br />'%\
                        (data_item.get('text','').replace('_',' '),data_item.get('text')))
                elif data_item.get('radio'):
                    CGI_CLI.buffprint('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                        (data_item.get('radio'),data_item.get('radio'),data_item.get('radio','').replace('_',' ')))
                elif data_item.get('checkbox'):
                    CGI_CLI.buffprint('<input type = "checkbox" name = "%s" value = "on" /> %s'%\
                        (data_item.get('checkbox'),data_item.get('checkbox','').replace('_',' ')))
                elif data_item.get('dropdown'):
                    if len(data_item.get('dropdown').split(','))>0:
                        CGI_CLI.buffprint('<select name = "dropdown[%s]">'%(data_item.get('dropdown','')))
                        for option in data_item.get('dropdown').split(','):
                            CGI_CLI.buffprint('<option value = "%s">%s</option>'%(option,option))
                        CGI_CLI.buffprint('</select>')
                elif data_item.get('file'):
                   CGI_CLI.buffprint('Upload file: <input type = "file" name = "file[%s]" />'%(data_item.get('file').replace('\\','/')))
                elif data_item.get('submit'):
                    CGI_CLI.buffprint('<input id = "%s" type = "submit" name = "submit" value = "%s" />'%\
                        (data_item.get('submit'),data_item.get('submit')))


        ### START OF FORMPRINT ###
        formtypes = ['raw','text','checkbox','radio','submit','dropdown','textcontent']
        i_submit_button = None if not submit_button else submit_button
        if not pyfile: i_pyfile = sys.argv[0]
        try: i_pyfile = i_pyfile.replace('\\','/').split('/')[-1].strip()
        except: i_pyfile = i_pyfile.strip()
        if CGI_CLI.cgi_active:
            CGI_CLI.buffprint('<br/>');
            if color and not tag: tag = 'p';
            if tag: CGI_CLI.buffprint('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"'%(color) if color else 'black'))
            CGI_CLI.buffprint('<form action = "/cgi-bin/%s" enctype = "multipart/form-data" action = "save_file.py" method = "post">'%\
                (i_pyfile))
            ### RAW HTML ###
            if isinstance(form_data, six.string_types): CGI_CLI.buffprint(form_data)
            ### STRUCT FORM DATA = LIST ###
            elif isinstance(form_data, (list,tuple)):
                for data_item in form_data: subformprint(data_item)
            ### JUST ONE DICT ###
            elif isinstance(form_data, (dict,collections.OrderedDict)): subformprint(form_data)
            if i_submit_button: subformprint({'submit':i_submit_button})
            CGI_CLI.buffprint('</form>')
            if tag: CGI_CLI.buffprint('</%s>'%(tag))
            else: CGI_CLI.buffprint('<br/>');

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
CGI_CLI.init_cgi(return_http_status = True)
CGI_CLI.print_args()
#CGI_CLI.print_env()


if CGI_CLI.cgi_active:
    CGI_CLI.formprint(\
        ['REGEX:',{'textcontent':'regex_string','text':CGI_CLI.data.get('regex_string','')},\
        'SUB:',{'textcontent':'sub_string','text':CGI_CLI.data.get('sub_string','')},\
        'TEXT:',{'textcontent':'text_string','text':CGI_CLI.data.get('text_string','')}],\
        submit_button = 'Submit')

regex_string = CGI_CLI.data.get('regex_string','')
text_string  = CGI_CLI.data.get('text_string','')
sub_string   = CGI_CLI.data.get('sub_string','')

raw_regex    = CGI_CLI.data.get('regex_string','').encode('unicode_escape')
raw_text     = CGI_CLI.data.get('text_string','').encode('unicode_escape')

CGI_CLI.uprint('REGEX[%s], SUB[%s], TEXT[%s]' % (regex_string,sub_string,text_string))

try:
    result = text_string.replace(regex_string, sub_string)
    CGI_CLI.uprint("TEXT.replace(REGEX, SUB, TEXT)        # Delete/Substitude pattern",tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.sub(regex_string, "", text_string)
    CGI_CLI.uprint("re.sub(REGEX, '', TEXT)        # Delete pattern",tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.sub(regex_string, sub_string, text_string)
    CGI_CLI.uprint('\nre.sub(REGEX, SUB, TEXT)       # Replace pattern by SUB',tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.sub(r'\s+', "", text_string)
    CGI_CLI.uprint("\nre.sub(r'\s+', ' ', TEXT)      # Eliminate duplicate whitespaces",tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.sub('abc(def)ghi', r'\1', text_string)
    CGI_CLI.uprint("\nre.sub('abc(def)ghi', r'\1', TEXT)     # Replace a string with a part of itself",tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.search(regex_string,text_string)
    CGI_CLI.uprint('\nre.search(REGEX, TEXT)',tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.search(regex_string,text_string)
    CGI_CLI.uprint('\nif re.search(REGEX, TEXT):',tag = 'h1', color = 'blue')
    CGI_CLI.uprint((str(True) if result else str(None)) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.findall(regex_string,text_string)
    CGI_CLI.uprint('\nre.findall(REGEX, TEXT)',tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.findall(regex_string, text_string)
    CGI_CLI.uprint('\nre.findall(REGEX, TEXT)[0]',tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result[0]) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

try:
    result = re.findall(regex_string, text_string, re.MULTILINE)
    CGI_CLI.uprint('\nre.findall(REGEX, TEXT, re.MULTILINE)',tag = 'h1', color = 'blue')
    CGI_CLI.uprint(str(result) ,tag = 'h1', color = 'green')
except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')


# try:
    # result = re.match(regex_string, text_string).groups()
    # result2 = (result.groups()) if result else None
    # CGI_CLI.uprint('z = re.match(REGEX,TEXT): ' + str(result) ,tag = 'h1', color = 'blue')
    # CGI_CLI.uprint('z.groups(): ' + str(result2) ,tag = 'h1', color = 'blue')
# except Exception as e: CGI_CLI.uprint('PROBLEM[' + str(e) + ']')

#CGI_CLI.set_http_status_code(200)