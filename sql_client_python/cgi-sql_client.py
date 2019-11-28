#!/usr/bin/python36

import sys, os, io, paramiko, json, copy, html

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
import cgitb; cgitb.enable()
import requests
if int(sys.version_info[0]) == 3: import pymysql
else: import mysql.connector



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
    js_reload_button = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""

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
        parser.add_argument("--sw_release",
                            action = "store", dest = 'sw_release',
                            default = str(),
                            help = "sw release number without dots, i.e 653")
        parser.add_argument("--OTI_tar",
                            action = 'store_true', dest = "OTI.tar_file",
                            default = None,
                            help = "copy/check OTI.tar file")
        parser.add_argument("--SMU_tar",
                            action = 'store_true', dest = "SMU.tar_files",
                            default = None,
                            help = "copy/check SMU.tar files")
        parser.add_argument("--delete_files",
                            action = 'store_true', dest = "delete_device_tar_files_on_end",
                            default = None,
                            help = "delete device tar files on end")
        parser.add_argument("--check_files_only",
                            action = 'store_true', dest = "check_device_tar_files_only",
                            default = None,
                            help = "check existing device tar files only, do not copy new tar files")
        parser.add_argument("--backup_configs",
                            action = 'store_true', dest = "backup_configs_to_device_disk",
                            default = None,
                            help = "backup configs to device hdd")
        parser.add_argument("--force_rewrite",
                            action = 'store_true', dest = "force_rewrite_tar_files_on_device",
                            default = None,
                            help = "force rewrite tar files on device hdd")
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
    def init_cgi(chunked = None):
        CGI_CLI.START_EPOCH = time.time()
        CGI_CLI.chunked = None
        ### TO BE PLACED - BEFORE HEADER ###
        CGI_CLI.chunked_transfer_encoding_string = "Transfer-Encoding: chunked\r\n"
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
            sys.stdout.write("%sContent-type:text/html\r\n" %
                (CGI_CLI.chunked_transfer_encoding_string if CGI_CLI.chunked else str()))
            sys.stdout.flush()
            CGI_CLI.print_chunk("\r\n\r\n<html><head><title>%s</title></head><body>" %
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
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
    def uprint(text, tag = None, tag_id = None, color = None, name = None, jsonprint = None, \
        log = None, no_newlines = None):
        """NOTE: name parameter could be True or string."""
        print_text, print_name, print_per_tag = copy.deepcopy(text), str(), str()
        if jsonprint:
            if isinstance(text, (dict,collections.OrderedDict,list,tuple)):
                try: print_text = json.dumps(text, indent = 4)
                except Exception as e: CGI_CLI.print_chunk('JSON_PROBLEM[' + str(e) + ']')
        if name==True:
            if not 'inspect.currentframe' in sys.modules: import inspect
            callers_local_vars = inspect.currentframe().f_back.f_locals.items()
            var_list = [var_name for var_name, var_val in callers_local_vars if var_val is text]
            if str(','.join(var_list)).strip(): print_name = str(','.join(var_list)) + ' = '
        elif isinstance(name, (six.string_types)): print_name = str(name) + ' = '

        print_text = str(print_text)
        log_text   = str(copy.deepcopy((print_text)))
        if CGI_CLI.cgi_active:
            ### WORKARROUND FOR COLORING OF SIMPLE TEXT
            if color and not tag: tag = 'p';
            if tag: CGI_CLI.print_chunk('<%s%s%s>'%(tag,' id="%s"'%(tag_id) if tag_id else str(),' style="color:%s;"'%(color) if color else 'black'))
            if isinstance(print_text, six.string_types):
                print_text = str(print_text.replace('&','&amp;').replace('<','&lt;'). \
                    replace('>','&gt;').replace(' ','&nbsp;').replace('"','&quot;').replace("'",'&apos;').\
                    replace('\n','<br/>'))
            CGI_CLI.print_chunk(print_name + print_text)
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
        if CGI_CLI.cgi_active:
            if tag: CGI_CLI.print_chunk('</%s>'%(tag))
            elif not no_newlines: CGI_CLI.print_chunk('<br/>');
            ### PRINT PER TAG ###
            CGI_CLI.print_chunk(print_per_tag)
        ### LOGGING ###
        if CGI_CLI.logfilename and log:
            with open(CGI_CLI.logfilename,"a+") as CGI_CLI.fp:
                CGI_CLI.fp.write(print_name + log_text + '\n')
                del log_text


    @staticmethod
    def formprint(form_data = None, submit_button = None, pyfile = None, tag = None, color = None):
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
                    if isinstance(data_item.get('radio'), (list,tuple)):
                        for radiobutton in data_item.get('radio'):
                            CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                                ('script_action',radiobutton,radiobutton.replace('_',' ')))
                    else:
                        CGI_CLI.print_chunk('<input type = "radio" name = "%s" value = "%s" /> %s'%\
                            (data_item.get('radio'),data_item.get('radio'),data_item.get('radio','').replace('_',' ')))
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





class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled

    def __init__(self, host = None, user = None, password = None, database = None):
        if int(sys.version_info[0]) == 3 and not 'pymysql.connect' in sys.modules: import pymysql
        elif int(sys.version_info[0]) == 2 and not 'mysql.connector' in sys.modules: import mysql.connector
        default_ipxt_data_collector_delete_columns = ['id','last_updated']
        self.sql_connection = None
        try:
            if CGI_CLI.initialized: pass
            else: CGI_CLI.init_cgi(); CGI_CLI.print_args()
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
        except Exception as e: print(e)

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
                    try: new_item = item[3].decode('utf-8')
                    except: new_item = item[3]
                    columns.append(new_item)
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return columns

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
                        try: new_item = item.decode('utf-8')
                        except:
                           try: new_item = str(item)
                           except: new_item = item
                        columns.append(new_item)
                    lines.append(columns)
            except Exception as e: print(e)
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
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return None

    def sql_write_table_from_dict(self, table_name, dict_data, update = None):  ###'ipxt_data_collector'
       if self.sql_is_connected():
           existing_sql_table_columns = self.sql_read_all_table_columns(table_name)
           if existing_sql_table_columns:
               columns_string, values_string = str(), str()
               ### ASSUMPTION: LIST OF COLUMNS HAS CORRECT ORDER!!!
               for key in existing_sql_table_columns:
                   if key in list(dict_data.keys()):
                        if len(columns_string) > 0: columns_string += ','
                        if len(values_string) > 0: values_string += ','
                        ### WRITE KEY/COLUMNS_STRING
                        columns_string += '`' + key + '`'
                        ### BE AWARE OF DATA TYPE
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
                        elif isinstance(dict_data.get(key,""), (six.string_types)):
                            values_string += "'" + str(dict_data.get(key,"")) + "'"
                        else:
                            values_string += "'" + str(dict_data.get(key,"")) + "'"
               ### FINALIZE SQL_STRING - INSERT
               if not update:
                   sql_string = """INSERT INTO `%s` (%s) VALUES (%s);""" \
                       % (table_name,columns_string,values_string)
                   if columns_string:
                       self.sql_write_sql_command("""INSERT INTO `%s`
                           (%s) VALUES (%s);""" %(table_name,columns_string,values_string))
               else:
                   sql_string = """UPDATE `%s` (%s) VALUES (%s);""" \
                       % (table_name,columns_string,values_string)
                   if columns_string:
                       self.sql_write_sql_command("""UPDATE `%s`
                           (%s) VALUES (%s);""" %(table_name,columns_string,values_string))
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

    def sql_read_last_record_to_dict(table_name = None, from_string = None, \
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
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_last_record( \
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

    def sql_read_records_to_dict_list(table_name = None, from_string = None, \
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
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_records( \
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

### CGI-BIN READ FORM ############################################
CGI_CLI()
CGI_CLI.init_cgi()
CGI_CLI.print_args()

# CGI_CLI.uprint('aaa')

# CGI_CLI.uprint(['aaa2','aaa3'])
# CGI_CLI.uprint({'aaa4':'aaa5'}, tag = 'h1')

# sql_inst = sql_interface(host='localhost', user='cfgbuilder', password='cfgbuildergetdata', database='rtr_configuration')
# CGI_CLI.uprint(sql_inst.sql_read_all_table_columns('ipxt_data_collector'))
# sql_inst.sql_read_table_last_record(from_string = 'ipxt_data_collector')
# sql_inst.sql_read_table_last_record(from_string = 'ipxt_data_collector', \
    # where_string = "username='mkrupa' AND device_name='AUVPE3'")

# sql_inst.sql_read_table_last_record(from_string = 'ipxt_data_collector', \
    # where_string = "username='%s'" % \
        # ('mkrupa' if not CGI_CLI.username else CGI_CLI.username,))

sql_inst = sql_interface(host='localhost', user='cfgbuilder', password='cfgbuildergetdata', database='rtr_configuration')

# name_list = sql_inst.sql_read_all_table_columns('ipxt_data_collector')
# data_list = sql_inst.sql_read_table_last_record(from_string = 'ipxt_data_collector')

# CGI_CLI.uprint(name_list)
# CGI_CLI.uprint(data_list)

# if name_list and data_list: read_data = collections.OrderedDict(zip(name_list[:-1], data_list[0][:-1]))
# else: read_data = collections.OrderedDict()

# CGI_CLI.uprint('READ_DATA:')
# CGI_CLI.uprint(read_data)

# sql_inst.sql_write_table_from_dict('ipxt_data_collector', read_data)

CGI_CLI.uprint(sql_inst.sql_read_table_last_record(from_string = 'ipxt_data_collector'), jsonprint = True)
CGI_CLI.uprint(sql_inst.sql_read_last_record_to_dict(from_string = 'ipxt_data_collector'), jsonprint = True)

data={}
data['oti_all_table'] = sql_inst.sql_read_records_to_dict_list( \
    #select_string = 'vendor, hardware, software, rtr_name, network',\
    from_string = 'oti_all_table',\
    order_by = 'vendor, hardware, rtr_name ASC')
CGI_CLI.uprint(text = data, name = True, jsonprint = True)

data['oti_all_table'] = sql_inst.sql_read_records_to_dict_list( \
    select_string = 'vendor, hardware, software, rtr_name, network',\
    from_string = 'oti_all_table',\
    order_by = 'vendor, hardware, rtr_name ASC')
CGI_CLI.uprint(text = data, name = True, jsonprint = True)

### DESTRUCTORS SEQUENCE
del sql_inst









