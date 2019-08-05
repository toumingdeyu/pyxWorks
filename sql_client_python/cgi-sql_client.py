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


class CGI_CLI_handle():
    """
    CGI_handle - Simple class for handling CGI parameters and 
                 clean (debug) printing to HTML/CLI    
       Notes:  - In case of cgi_parameters_error - http[500] is raised, 
                 but at least no appache timeout occurs...
    """ 
    # import collections, cgi, six
    # import cgitb; cgitb.enable()
    def __init__(self):
        self.debug = True
        self.START_EPOCH = time.time()
        self.cgi_parameters_error = None
        self.gci_active = None
        self.data, self.submit_form, self.username, self.password = \
            self.read_cgibin_get_post_form()
        if self.submit_form or len(self.data)>0: self.gci_active = True
        if self.gci_active:
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (self.submit_form if self.submit_form else 'No submit'))
        # if self.cgi_parameters_error:
            # import cgitb; cgitb.enable()   
            # print("Content-type:text/html\n\n")
            # print("<html><head><title>%s</title></head><body>" % 
                # (self.submit_form if self.submit_form else 'No submit'))         
            # self.uprint('\nNO INSERTED CGI PARAMETERS!\n')
        
    def __del__(self):
        self.uprint('\nEND[script runtime = %d sec]. '%(time.time() - self.START_EPOCH))
        if self.gci_active: print("</body></html>")
        
    def read_cgibin_get_post_form(self):
        data, submit_form, username, password = collections.OrderedDict(), '', '', ''
        try: form = cgi.FieldStorage()
        except: 
            form = collections.OrderedDict()
            self.cgi_parameters_error = True
        for key in form.keys():
            variable = str(key)
            try: value = str(form.getvalue(variable))
            except: value = str(','.join(form.getlist(name)))
            if variable and value and not variable in ["submit","username","password"]: 
                data[variable] = value
            if variable == "submit": submit_form = value
            if variable == "username": username = value
            if variable == "password": password = value
        return data, submit_form, username, password

    def uprint(self, text, tag = None):
        if self.debug: 
            if self.gci_active:
                if tag and 'h' in tag: print('<%s>'%(tag))
                if tag and 'p' in tag: print('<p>')
                if isinstance(text, six.string_types): 
                    text = str(text.replace('\n','<br/>'))
                else: text = str(text)   
            print(text)
            if self.gci_active: 
                print('<br/>');
                if tag and 'p' in tag: print('</p>')
                if tag and 'h' in tag: print('</%s>'%(tag))

    def __repr__(self):
        if self.gci_active:
            try: print_string = 'CGI_args=' + json.dumps(self.data) + ' <br/>'
            except: print_string = 'CGI_args=' + ' <br/>'                
        else: print_string = 'CLI_args=%s \n' % (str(sys.argv[1:]))  
        return print_string        


class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled
    
    def __init__(self):
        self.sql_connection = None
        try:    
            self.sql_connection = mysql.connector.connect(host='localhost', user='cfgbuilder', \
                password='cfgbuildergetdata', database='rtr_configuration')
            gci_ins.uprint("SQL connection is open.")    
        except Exception as e: print(e)           
    
    def __del__(self):

        if self.sql_connection and self.sql_connection.is_connected():
            self.sql_connection.close()            
            gci_ins.uprint("SQL connection is closed.")
        
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
               gci_ins.uprint("\n"+sql_string+"\n")        
       return None                
   
    def sql_read_table_to_dict(self, table_name, where_column_name, where_column_equals):
        '''sql_read_table_from_dict('ipxt_data_collector','vrf_name','name_of_vrf')'''
        check_data = None
        if self.sql_connection and self.sql_connection.is_connected():
            if where_column_name and where_column_equals:
                sql_string = "SELECT * FROM %s WHERE %s = '%s';" \
                    %(table_name,where_column_name,where_column_equals)
            else:
                sql_string = "SELECT * FROM %s;" \
                    %(table_name)
            check_data = self.sql_read_sql_command(sql_string)        
            gci_ins.uprint(sql_string)
            gci_ins.uprint(check_data)                    
        return check_data

                
            
##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

### CGI-BIN READ FORM ############################################
gci_ins = CGI_CLI_handle()
print(repr(gci_ins))
#print(str(gci_instance))

CGI_CLI_handle.uprint(gci_ins,'aaa')
gci_ins.uprint('aaa')          
gci_ins.uprint(['aaa2','aaa3'])
gci_ins.uprint({'aaa4':'aaa5'}, tag = 'h1')
#cgi.print_environ()


sql_ins = sql_interface()
gci_ins.uprint(sql_ins.sql_read_all_table_columns('ipxt_data_collector'))
sql_ins.sql_read_table_to_dict('ipxt_data_collector','vrf_name','SIGTRAN.Meditel')





### DESTRUCTORS SEQUENCE
del sql_ins
del gci_ins









