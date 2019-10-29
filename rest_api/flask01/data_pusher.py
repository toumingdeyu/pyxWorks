#!/usr/bin/python36
# -*- coding: UTF-8 -*-

import sys
import ipaddress
import json
from mako.template import Template
from mako.lookup import TemplateLookup
from flask import Flask, request, render_template_string
import requests
import collections
import json
import six
import os, subprocess

try:    server_address = 'http://' + str(subprocess.check_output('hostname', shell=True).decode('utf-8')).strip()
except: server_address = 'http://localhost'

server_port = 8880

print("--- %s:%s ---"%(server_address,server_port))

parameters = collections.OrderedDict()
parameters.update({'parameter1':'text'})
parameters.update({'parameter2':'text'})
parameters.update({'parameter3':'text'})
parameters.update({'parameter4':'text'})


config_template_string = '''!<% rule_num = 10 %>
ipv4 access-list IPXT.${customer_name}-IN
% for rule in customer_prefixes_v4:
 ${rule_num} permit ipv4 ${rule['customer_prefix_v4']} ${rule['customer_subnetmask_v4']} any<% rule_num += 10 %>
% endfor
 ${rule_num} deny ipv4 any any
!
'''

input_jinja2_template = '''
<html>
   <body>
      <form action = "{{server_address}}:{{server_port}}/result" method = "POST">
        {% for key, value in parameters.items() %}
           <p>{{key}}<input type = "{{value}}" name = "{{key}}" /></p>
        {% endfor %}
        <p><input type = "submit" value = "submit" /></p>
      </form>
   </body>
</html>
'''

### FUNCTIONS ############################################ 
def load_json(path, file_name):
    """Open json file return dictionary."""
    try:
        json_data = json.load(open(path + file_name),object_pairs_hook=collections.OrderedDict)
    except IOError as err:
        raise Exception('Could not open file: {}'.format(err))
    except json.decoder.JSONDecodeError as err:
        raise Exception('JSON format error in: {} {}'.format(file_name, err))

    return json_data

def print_config():
    mytemplate = Template(config_template_string)
    config_string = mytemplate.render(**data)
    return config_string

def print_json():
    try: json_data = json.dumps(data, indent=2)
    except: json_data = ''
    return json_data

### CODE START ############################################
### First load dummy config
data = collections.OrderedDict()
data = load_json('./', 'ipx_cfg.json')
### Then read data and wait to POST REQUEST to '/send'
app = Flask(__name__)

@app.route('/')
def root_path():
   return render_template_string(input_jinja2_template, parameters = parameters, server_port = server_port, server_address = server_address)

@app.route('/result',methods = ['POST', 'GET'])
def result():
    global data   
    if request.method == 'POST':
        result = request.form        
        for key,value in result.items(): data[key] = value    
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 

@app.route('/config',methods=['GET'])
def return_config_data():
    return print_config()

@app.route('/json',methods=['GET'])
def return_json_data():
    return print_json()    

@app.route('/update', methods=['POST'])
def receive_data_addons():
    global data   
    try:    received_json = request.get_json()
    except: received_json = request.form.to_dict(flat=False)
    data.update(received_json)
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 

@app.route('/update/<string:key_plus_value>', methods=['POST','PUT'])
def receive_data_add_one(key_plus_value):
    global data   
    try: data[key_plus_value.split(':')[0]] = key_plus_value.split(':')[1]
    except: pass
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 

@app.route('/send', methods=['GET','POST','PUT'])
def send_data():
    return print_config() 

@app.route('/sendandexit', methods=['GET','POST','PUT'])
def send_data_and_exit():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return str(print_config())+'\n\n==> Data sent + Exit...' 

@app.route('/exit', methods=['GET','POST','PUT'])
def send_exit():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "==> Shutting down..."

### MAIN START ############################################
if __name__ == '__main__':
    app.run(debug=True, port=server_port, use_reloader=False)


