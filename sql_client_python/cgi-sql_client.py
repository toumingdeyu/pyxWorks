#!/usr/bin/python

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
import mysql.connector
import cgi
###import cgitb; cgitb.enable()
import requests


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
    gci_active = None
    
    @staticmethod        
    def __cleanup__():
        CGI_CLI.uprint('\nEND[script runtime = %d sec]. '%(time.time() - CGI_CLI.START_EPOCH))
        if CGI_CLI.gci_active: print("</body></html>")

    @staticmethod
    def register_cleanup_at_exit():
        """
        In static class is no constructor or destructor 
        --> Register __cleanup__ in system
        """
        import atexit; atexit.register(CGI_CLI.__cleanup__)

    @staticmethod
    def init_cgi():
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
        if CGI_CLI.submit_form or len(CGI_CLI.data)>0: CGI_CLI.gci_active = True
        if CGI_CLI.gci_active:
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        return None

    @staticmethod 
    def uprint(text, tag = None):
        if CGI_CLI.debug: 
            if CGI_CLI.gci_active:
                if tag and 'h' in tag: print('<%s>'%(tag))
                if tag and 'p' in tag: print('<p>')
                if isinstance(text, six.string_types): 
                    text = str(text.replace('\n','<br/>'))
                else: text = str(text)   
            print(text)
            if CGI_CLI.gci_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    @staticmethod
    def print_args():
        if CGI_CLI.gci_active:
            try: print_string = 'CGI_args=' + json.dumps(CGI_CLI.data) + ' <br/>'
            except: print_string = 'CGI_args=' + ' <br/>'                
        else: print_string = 'CLI_args=%s \n' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string          


class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled
    
    def __init__(self):
        self.sql_connection = None
        try: 
            if CGI_CLI.initialized: pass
            else: CGI_CLI.init_cgi(); CGI_CLI.print_args()
        except: pass
        try:    
            self.sql_connection = mysql.connector.connect(host='localhost', user='cfgbuilder', \
                password='cfgbuildergetdata', database='rtr_configuration')
            CGI_CLI.uprint("SQL connection is open.")    
        except Exception as e: print(e)           
    
    def __del__(self):

        if self.sql_connection and self.sql_connection.is_connected():
            self.sql_connection.close()            
            CGI_CLI.uprint("SQL connection is closed.")
        
    def sql_read_all_table_columns(self, table_name):
        columns = None
        if self.sql_connection and self.sql_connection.is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute("select * from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='%s';"%(table_name))
                records = cursor.fetchall()
                columns = [item[3] for item in records]
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return columns 

    def sql_read_sql_command(self, sql_command):
        records = None
        if self.sql_connection and self.sql_connection.is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute(sql_command)
                records = cursor.fetchall()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return records 

    def sql_write_sql_command(self, sql_command):
        if self.sql_connection and self.sql_connection.is_connected():
            cursor = self.sql_connection.cursor(prepared=True)
            try: 
                cursor.execute(sql_command)
                ### DO NOT COMMIT IF AUTOCOMMIT IS SET 
                if not sql_connection.autocommit: sql_connection.commit()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
        return None

    def sql_write_table_from_dict(self, table_name, dict_data):  ###'ipxt_data_collector'
       if self.sql_connection and self.sql_connection.is_connected():
           existing_sql_table_columns = sql_read_all_table_columns(table_name) 
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
               ### FINALIZE SQL_STRING
               sql_string = """INSERT INTO `ipxt_data_collector` (%s) VALUES (%s);""" \
                   % (columns_string,values_string)   
               if columns_string:
                   self.sql_write_sql_command("""INSERT INTO `ipxt_data_collector`
                       (%s) VALUES (%s);""" %(columns_string,values_string))
               CGI_CLI.uprint("\n"+sql_string+"\n")        
       return None                
   
    def sql_read_table_record_to_dict(self, table_name = None, where_string = None):
        '''sql_read_table_from_dict('ipxt_data_collector',"vrf_name = 'name_of_vrf'" ) '''
        check_data = None
        
        #SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id)FROM ipxt_data_collector) AND username='mkrupa' AND device_name='AUVPE3'; 
        if self.sql_connection and self.sql_connection.is_connected():
            if where_string:
                sql_string = "SELECT * FROM %s WHERE id=(SELECT max(id) FROM %s) AND %s;" \
                    %(table_name, table_name, where_string)
            else:
                sql_string = "SELECT * FROM %s WHERE id=(SELECT max(id) FROM %s);" \
                    %(table_name, table_name)
            check_data = self.sql_read_sql_command(sql_string)        
            CGI_CLI.uprint(sql_string)
            CGI_CLI.uprint(check_data)                    
        return check_data

                
            
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

CGI_CLI.uprint('aaa')       

CGI_CLI.uprint(['aaa2','aaa3'])
CGI_CLI.uprint({'aaa4':'aaa5'}, tag = 'h1')

sql_inst = sql_interface()
CGI_CLI.uprint(sql_inst.sql_read_all_table_columns('ipxt_data_collector'))
sql_inst.sql_read_table_record_to_dict('ipxt_data_collector')
#,"username='mkrupa' AND device_name='AUVPE3'")

#SELECT vlan_id FROM ipxt_data_collector WHERE id=(SELECT max(id)FROM ipxt_data_collector) AND username='mkrupa' AND device_name='AUVPE3';



### DESTRUCTORS SEQUENCE
del sql_inst








