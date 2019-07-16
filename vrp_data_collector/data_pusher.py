#!/usr/bin/python36
# -*- coding: UTF-8 -*-

import sys
import ipaddress
import json
from mako.template import Template
from mako.lookup import TemplateLookup
from flask import Flask, request
import requests

template_string = '''!<% rule_num = 10 %>
ipv4 access-list IPXT.${customer_name}-IN
% for rule in customer_prefixes_v4:
 ${rule_num} permit ipv4 ${rule['customer_prefix_v4']} ${rule['customer_subnetmask_v4']} any<% rule_num += 10 %>
% endfor
 ${rule_num} deny ipv4 any any
!
'''

### FUNCTIONS ############################################ 
def load_json(path, file_name):
    """Open json file return dictionary."""
    try:
        json_data = json.load(open(path + file_name))
    except IOError as err:
        raise Exception('Could not open file: {}'.format(err))
    except json.decoder.JSONDecodeError as err:
        raise Exception('JSON format error in: {} {}'.format(file_name, err))

    return json_data

def print_config():
    mytemplate = Template(template_string)
    config_string = mytemplate.render(**data)
    return config_string

def print_json():
    try: json_data = json.dumps(data, indent=2)
    except: json_data = ''
    return json_data

### CODE START ############################################
### First load dummy config
data = load_json('./', 'ipx_cfg.json')
### Then read data and wait to POST REQUEST to '/send'
app = Flask(__name__)

@app.route('/',methods=['GET'])
def return_data():
    return print_config() + '\n'+ 70 * '-' + '\n' + print_json()

@app.route('/config',methods=['GET'])
def return_config_data():
    return print_config()

@app.route('/json',methods=['GET'])
def return_json_data():
    return print_json()    

@app.route('/update', methods=['POST'])
def receive_data_addons():
    received_json = request.get_json()
    data.update(received_json)
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 

@app.route('/update/<string:key_plus_value>', methods=['POST','PUT'])
def receive_data_add_one(key_plus_value):
    try: data[key_plus_value.split(':')[0]] = key_plus_value.split(':')[1]
    except: pass
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 

@app.route('/send', methods=['POST','PUT'])
def send_data():
    return print_config() 

@app.route('/sendandexit', methods=['POST','PUT'])
def send_data_and_exit():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return str(print_config())+'\n\n==> Data sent + Exit...' 

@app.route('/exit', methods=['POST','PUT'])
def send_exit():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "==> Shutting down..."

### MAIN START ############################################
if __name__ == '__main__':
    app.run(debug=True, port=8080)


