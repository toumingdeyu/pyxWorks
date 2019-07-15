#!/usr/bin/python36
# -*- coding: UTF-8 -*-

import ipaddress
import json

from mako.template import Template
from mako.lookup import TemplateLookup

template_string = '''!<% rule_num = 10 %>
ipv4 access-list IPXT.${customer_name}-IN
% for rule in customer_prefixes_v4:
 ${rule_num} permit ipv4 ${rule['customer_prefix_v4']} ${rule['customer_subnetmask_v4']} any<% rule_num += 10 %>
% endfor
 ${rule_num} deny ipv4 any any
!
'''


def load_json(path, file_name):
    """Open json file return dictionary."""
    try:
        json_data = json.load(open(path + file_name))
    except IOError as err:
        raise Exception('Could not open file: {}'.format(err))
    except json.decoder.JSONDecodeError as err:
        raise Exception('JSON format error in: {} {}'.format(file_name, err))

    return json_data

############################################
# Define paths to data.
############################################

#mylookup = TemplateLookup(directories=['./'])

data = load_json('./', 'ipx_cfg.json')

#mytemplate = mylookup.get_template('ipv4_acl_xr.tmpl')

mytemplate = Template(template_string)

print(mytemplate.render(**data))