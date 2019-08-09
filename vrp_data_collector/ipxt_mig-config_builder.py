#!/usr/bin/python36

import sys, os, io, paramiko, json , copy
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
import ipaddress

from mako.template import Template
from mako.lookup import TemplateLookup
import cgi
import cgitb; cgitb.enable()
import requests
#import interactive
#python 2.7 problem - hack 'pip install esptool'
import netmiko
if int(sys.version_info[0]) == 3: import pymysql
else: import mysql.connector

import cgitb; cgitb.enable()


step1_string = 'Submit step 1'
step2_string = 'Submit step 2'

try:    WORKDIR         = os.environ['HOME']
except: WORKDIR         = str(os.path.dirname(os.path.abspath(__file__)))
if WORKDIR: LOGDIR      = os.path.join(WORKDIR,'logs')

try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()
try:    EMAIL_ADDRESS   = os.environ['NEWR_EMAIL']
except: EMAIL_ADDRESS   = str()




###############################################################################
#
# Function and Class
#
###############################################################################

def read_data_json_from_logfile(filename = None, printall = None):
    data_loaded, text = collections.OrderedDict(), None
    if filename:
        with open(filename,"r") as fp:
            text = fp.read()
        if text:
            try: data_json_text = text.split('EVAL_COMMAND: return_bgp_data_json()')[1]
            except: data_json_text = str()
            if data_json_text:
                try:
                    data_loaded = json.loads(data_json_text, \
                        object_pairs_hook = collections.OrderedDict)
                except: pass
                #print("LOADED_data: ",data_loaded)
                if printall: print("\nLOADED JSON data: ")
                if printall: print(json.dumps(data_loaded, indent=2))
    return data_loaded


def generate_file_name(prefix = None, suffix = None , directory = None):
    filenamewithpath = None
    if not directory:
        try:    DIR         = os.environ['HOME']
        except: DIR         = str(os.path.dirname(os.path.abspath(__file__)))
    else: DIR = str(directory)
    if DIR: LOGDIR      = os.path.join(WORKDIR,'logs')
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


def dict_to_json_string(dict_data = None):
    try: json_data = json.dumps(dict_data, indent=2)
    except: json_data = ''
    return json_data


def find_last_logfile():
    most_recent_logfile = None
    log_file_name=os.path.join(LOGDIR,huawei_device_name.replace(':','_'). \
        replace('.','_').upper()) + '*' + USERNAME + '*vrp-' + vpn_name + \
        "*" + step1_string.replace(' ','_') + "*"
    log_filenames = glob.glob(log_file_name)
    if len(log_filenames) == 0:
        print(" ... Can't find any proper (%s) log file.\n"%(log_file_name))
    else:    
        most_recent_logfile = log_filenames[0]
        for item in log_filenames:
            filecreation = os.path.getctime(item)
            if filecreation > (os.path.getctime(most_recent_logfile)):
                most_recent_logfile = item
    return most_recent_logfile


def find_duplicate_keys_in_dictionaries(data1, data2):
    duplicate_keys_list = None
    if data1 and data2:
        list1 = list(data1.keys())
        list2 = list(data2.keys())
        for item in list2:
            if item in list1:
                if not duplicate_keys_list: duplicate_keys_list = []
                duplicate_keys_list.append(list1)
    return duplicate_keys_list


##################################################################################

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
    data, submit_form, username, password = collections.OrderedDict(), None, None, None
    
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
        if CGI_CLI.submit_form or len(CGI_CLI.data)>0: CGI_CLI.cgi_active = True
        if CGI_CLI.cgi_active:
            import cgitb; cgitb.enable()        
            print("Content-type:text/html\n\n")
            print("<html><head><title>%s</title></head><body>" % 
                (CGI_CLI.submit_form if CGI_CLI.submit_form else 'No submit'))
        import atexit; atexit.register(CGI_CLI.__cleanup__)
        return None

    @staticmethod 
    def uprint(text, tag = None):
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
    def print_args():
        if CGI_CLI.cgi_active:
            try: print_string = 'CGI_args=' + json.dumps(CGI_CLI.data) + ' <br/>'
            except: print_string = 'CGI_args=' + ' <br/>'                
        else: print_string = 'CLI_args=%s \n' % (str(sys.argv[1:]))
        CGI_CLI.uprint(print_string)
        return print_string          


class sql_interface():
    ### import mysql.connector
    ### MARIADB - By default AUTOCOMMIT is disabled
    
    def __init__(self, host = None, user = None, password = None, database = None):
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
        columns = None
        if self.sql_is_connected():
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
        '''NOTE: FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE'''
        records = None
        if self.sql_is_connected():
            cursor = self.sql_connection.cursor()
            try: 
                cursor.execute(sql_command)
                records = cursor.fetchall()
            except Exception as e: print(e)
            try: cursor.close()
            except: pass
            ### FORMAT OF RETURNED DATA IS [(LINE1),(LINE2)], SO USE DATA[0] TO READ LINE
        return records 

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

    def sql_write_table_from_dict(self, table_name, dict_data):  ###'ipxt_data_collector'
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
               ### FINALIZE SQL_STRING
               sql_string = """INSERT INTO `ipxt_data_collector` (%s) VALUES (%s);""" \
                   % (columns_string,values_string)   
               if columns_string:
                   self.sql_write_sql_command("""INSERT INTO `ipxt_data_collector`
                       (%s) VALUES (%s);""" %(columns_string,values_string))       
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
        select_string = None, where_string = None):
        """sql_read_last_record_to_dict - MAKE DICTIONARY FROM LAST TABLE RECORD 
           NOTES: -'table_name' is alternative name to 'from_string'
                  - it always read last record dependent on 'where_string'
                    which contains(=filters by) username,device_name,vpn_name                  
        """
        dict_data = collections.OrderedDict()
        table_name_or_from_string = None
        if table_name:  table_name_or_from_string = table_name
        if from_string: table_name_or_from_string = from_string     
        columns_list = sql_inst.sql_read_all_table_columns(table_name_or_from_string)
        data_list = sql_inst.sql_read_table_last_record( \
            from_string = table_name_or_from_string, \
            select_string = select_string, where_string = where_string)
        if columns_list and data_list: 
            dict_data = collections.OrderedDict(zip(columns_list, data_list[0]))
        try:
            ### DELETE NOT VALID (AUXILIARY) TABLE COLUMNS
            del dict_data['id']
            del dict_data['last_updated']
        except: pass    
        return dict_data      



###############################################################################

GW_interface_change_templ = '''
interface Tunnel${cgi_data.get('vlan-id','UNKNOWN')}
 no ip address
 ip address ${cgi_data.get('vlan-id','UNKNOWN')} ${cgi_data.get('mask','UNKNOWN')} 
 exit
'''

################################################################################

PE_vrf_config_templ = """!
vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
 description ${cgi_data.get('vpn','UNKNOWN')}.${cgi_data.get('customer_name','UNKNOWN')}.IPXT
 address-family ipv4 unicast
 import route-target
% for item in bgp_data.get('rt_import',[]):
  ${item}
% endfor  
 exit
 export route-target
% for item in bgp_data.get('rt_export',[]): 
  ${item}
% endfor  
  exit
 exit
!
"""

PE_acl_config_templ = '''!<% rule_num = 10 %>
ipv4 access-list IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
% for rule in bgp_data.get('customer_prefixes_v4',{}):
 ${rule_num} permit ipv4 ${rule.get('customer_prefix_v4','UNKNOWN')} ${rule.get('customer_subnetmask_v4','UNKNOWN')} any<% rule_num += 10 %>
% endfor
 1000 deny ipv4 any any
!
'''

PE_prefix_config_templ = """! <% list_count = 0; list_len = len(bgp_data.get('customer_prefixes_v4',{})) %>\
prefix-set IPXT.${cgi_data.get('customer_name','UNKNOWN')}-IN
% for item in bgp_data.get('customer_prefixes_v4',{}):
<% import ipaddress; net = ipaddress.ip_network(item.get('customer_prefix_v4','1.1.1.1')+'/'+item.get('customer_subnetmask_v4','32')); list_count += 1 %>
% if list_count == list_len:
  ${net} le 32
% else:
  ${net} le 32,
% endif 
% endfor
end-set
!
"""

PE_policy_map_templ = """!
policy-map ${cgi_data.get('vpn','UNKNOWN')}-IN
 class class-default
  service-policy ${cgi_data.get('vpn','UNKNOWN')}-COS-IN
  police rate ${cgi_data.get('vpn','UNKNOWN')} mbps 
end-policy-map
! 
policy-map ${cgi_data.get('vpn','UNKNOWN')}-OUT
 class class-default
  service-policy IPXT.Tyntec-COS-OUT
  shape average ${cgi_data.get('gold-bw','UNKNOWN')} mbps
  bandwidth ${cgi_data.get('vpn','UNKNOWN')} mbps 
 ! 
end-policy-map
! 
policy-map ${cgi_data.get('vpn','UNKNOWN')}-COS-IN
 class GOLD
  police rate ${cgi_data.get('gold-bw','UNKNOWN')} mbps 
  ! 
  set mpls experimental imposition 5
 ! 
 class SILVER
  set mpls experimental imposition 3
 ! 
 class class-default
  set mpls experimental imposition 0
 ! 
 end-policy-map
! 
policy-map ${cgi_data.get('vpn','UNKNOWN')}-COS-OUT
 class GOLD
  police rate ${cgi_data.get('gold-bw','UNKNOWN')} mbps 
  ! 
  priority level 1 
 ! 
 class SILVER
  bandwidth remaining percent 50 
 ! 
 class class-default
 ! 
 end-policy-map
!
!
"""

PE_interface_description_templ = """interface Bundle-Ether1 
 description TESTING ${cgi_data.get('ipsec-gw-router','UNKNOWN')} from ${cgi_data.get('pe-router','UNKNOWN')} :IPXT ASN43566 @XXX.XXX.XXX.XXX - For IPXT over IPSEC FIBXXXXX - Custom
 no ipv4 address
 carrier-delay up 3 down 0
 load-interval 30
!
"""

PE_customer_interface_templ = """interface Bundle-Ether1.${cgi_data.get('vlan-id','UNKNOWN')}
 encapsulation dot1Q ${cgi_data.get('vlan-id','UNKNOWN')}
 description TESTING Tyntec :IPXT ASN43566 @${cgi_data.get('aaaaa','UNKNOWN')} - IPX LD123456 TunnelIpsec${cgi_data.get('vlan-id','UNKNOWN')} - Custom
 bandwidth ${cgi_data.get('gold-bw','UNKNOWN')}000
 vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')} 
 ipv4 address ${cgi_data.get('interco_ip','UNKNOWN')} ${cgi_data.get('interco_mask','UNKNOWN')}
 ipv4 access-group ${cgi_data.get('vpn','UNKNOWN')}-IN ingress
 service-policy input ${cgi_data.get('vpn','UNKNOWN')}-IN
 service-policy output ${cgi_data.get('vpn','UNKNOWN')}-OUT
!
"""

PE_customer_policy_templ = """!
route-policy IPXT.Tyntec-IN
  if not destination in ${cgi_data.get('vpn','UNKNOWN')}-IN then
   drop
  endif
  if community matches-any (2300:80) then
    set local-preference 80
    set community (43566:11000) <--<< need to collect the communities from Huawei
    set community (43566:20200) additive
  elseif community matches-any (2300:90) then
    set local-preference 90
    set community (43566:11000)
    set community (43566:20200) additive
  else
    set local-preference 100
    set community (43566:11000)
    set community (43566:20200) additive
  endif
end-policy 
!
"""

PE_bgp_config_templ = """!
router bgp 2300
 neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  remote-as 43566
  ebgp-multihop 5
  advertisement-interval 0
  address-family ipv4 unicast
   send-community-ebgp
   route-policy ${cgi_data.get('vpn','UNKNOWN')}-IN in
   maximum-prefix 10 90
   route-policy PASS-ALL out
   soft-reconfiguration inbound
  !
 !
vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')}
  rd ${bgp_data.get('rd','UNKNOWN')}
  address-family ipv4 unicast
   redistribute connected route-policy NO-EXPORT-INTERCO
  !
  neighbor 193.251.244.166
   use neighbor-group ${cgi_data.get('vpn','UNKNOWN')}
  !
!
"""

PE_static_route_config_templ = '''!
router static
 vrf ${cgi_data.get('vpn','UNKNOWN').replace('.','@')} 
  address-family ipv4 unicast
   193.251.244.166/32 Bundle-Ether1.65 193.251.157.67
!
'''


#############################################################################
def generate_IPSEC_GW_router_config(data = None):
    config_string = str()
    
    mytemplate = Template(GW_interface_change_templ,strict_undefined=True)
    config_string += mytemplate.render(**data)     
    
    
    return config_string

    
def generate_PE_router_config(dict_data = None):
    config_string = str()

    mytemplate = Template(PE_vrf_config_templ,strict_undefined=True)
    config_string += mytemplate.render(**data)
    
    mytemplate = Template(PE_acl_config_templ,strict_undefined=True)
    config_string += mytemplate.render(**data)
    
    mytemplate = Template(PE_prefix_config_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_policy_map_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_interface_description_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_customer_interface_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_customer_policy_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_bgp_config_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')

    mytemplate = Template(PE_static_route_config_templ,strict_undefined=True)
    config_string += (mytemplate.render(**data)).replace('\n\n','\n')    
    return config_string 



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

script_action = CGI_CLI.submit_form.replace(' ','_') if CGI_CLI.submit_form else 'unknown_action' 
device_name = CGI_CLI.data.get('device','')
huawei_device_name = CGI_CLI.data.get('huawei-router-name','')
vpn_name = CGI_CLI.data.get('vpn','')

### START OF DATA PROCESSING ###

data = collections.OrderedDict()
bgp_data = copy.deepcopy(read_data_json_from_logfile(find_last_logfile()))
cgi_data = copy.deepcopy(CGI_CLI.data)
data['bgp_data'] = bgp_data
data['cgi_data'] = cgi_data

CGI_CLI.uprint(dict_to_json_string(data)+'\n')
    
if data: 
    config_text_gw = generate_IPSEC_GW_router_config(data)
    CGI_CLI.uprint('IPSEC GW ROUTER (%s) CONFIG:' %(data['cgi_data'].get('ipsec-gw-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(config_text_gw)    
    config_text_pe = generate_PE_router_config(data)
    CGI_CLI.uprint('PE ROUTER (%s) CONFIG:' % (data['cgi_data'].get('pe-router','UNKNOWN').upper()), tag = 'h1')
    CGI_CLI.uprint(config_text_pe)
     








