#!/usr/bin/python

import sys, io, collections, six, json, requests, subprocess
from flask import Flask, request, render_template_string


parameters = collections.OrderedDict()
parameters.update({'parameter1':'text'})
parameters.update({'parameter2':'text'})
parameters.update({'parameter3':'text'})
parameters.update({'parameter4':'text'})


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

### FUNCTIONS #################################################################
def root_path():
   return render_template_string(input_jinja2_template, parameters = parameters, server_port = server_port, server_address = server_address)

def function_result():
    global data   
    if request.method == 'POST':
        result = request.form        
        for key,value in result.items(): data[key] = value    
    json_dumps = json.dumps(data, indent=2)
    return json_dumps 


### MAIN ######################################################################
if __name__ != '__main__': sys.exit(0)

data = collections.OrderedDict()
data = load_json('./', 'ipx_cfg.json')

try:    server_address = 'http://' + str(subprocess.check_output('hostname', shell=True).decode('utf-8')).strip()
except: server_address = 'http://localhost'

server_port = 9999

### INIT FLASK ###
app = Flask(__name__)
  
#root_path = (app.route('/'))(root_path)
#result = (app.route('/result',methods = ['POST', 'GET']))(function_result)

route = '/'
function_name = 'root_path'
exec("%s = (app.route('%s'))(%s)" % (function_name,route,function_name))


route = '/result'
function_name = 'function_result'
methods_string = "['POST', 'GET']"
exec("%s = (app.route('%s',methods = %s))(%s)" % (function_name,route,methods_string,function_name))

app.run(debug=True, port=server_port, use_reloader=False)