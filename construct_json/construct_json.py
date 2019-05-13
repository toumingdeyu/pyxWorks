#!/usr/bin/python
import sys
import os
import io
import optparse
import json
import yaml
import collections
import six

# def update_bgpdata_structure(data_structure = None, data_key = None, data_to_update = None):
#     print('START:',type(data_structure),data_structure)
#     if not data_structure: return None
#     if not data_to_update: return data_structure
#     if not data_key:       return data_structure
#
#
#
#
#     ### CHECK DATA TYPE
#     if isinstance(data_structure, dict):
#         ### IF KEY EXISTS
#         if data_structure.get(data_key,'') or data_key in data_structure.keys():
#             data_structure.update(data_to_update)
#         else: data_structure[data_key] = data_to_update
#     elif isinstance(data_structure, (list,tuple)):
#         if data_to_update in data_structure:
#             data_structure[data_to_update]
#         else:
#             data_structure.append(data_to_update)
#     else: data_structure = data_to_update
#     print('END:',type(data_structure),data_structure)
#     return data_structure


################################################################################
bgp_data = collections.OrderedDict()

def update_bgpdata_structure(data_address, key_name = None, value = None, \
    order_in_list = None, list_append_value = None, add_new_key = None, \
    debug = True):
    """
    FUNCTION: update_bgpdata_structure
    PARAMETERS:
       data_address - address of json ending on parrent (key_name or list_number)
       key_name - name of key in dict
       value - value of key in dict
       order_in_list - if actuaal list is shorter than needed, append new template section
       list_append_value - add new template section to list
       add_new_key = True - add new keys/values to dictionary not existent in templates
       debug - True/None
    RETURNS:
       change_applied - True = change applied , None - no change
    """
    global bgp_data
    change_applied = None
    ### REWRITE VALUE IN DICT ON KEY_NAME POSITION
    if isinstance(data_address, (dict,collections.OrderedDict)) \
        and isinstance(key_name, (six.string_types)):
        data_address_values = data_address.keys()
        # k,v = data_address.items()  , py3 data_address.iteritems()
        for address_key_value in data_address_values:
            if key_name and key_name == address_key_value:
                data_address[key_name] = value
                change_applied = True
        else:
            if add_new_key:
                data_address[key_name] = value
                change_applied = True
    ### ADD LIST POSITION if NEEDED, REWRITE VALUE IN DICT ON KEY_NAME POSITION
    elif isinstance(data_address, (list,tuple)):
        ### ORDER_IN_LIST=[0..], LEN()=[0..]
        if order_in_list == len(data_address):
            data_address.append(list_append_value)
        ### AFTER OPTIONAL ADDITION OF END OF LIST BY ONE
        if order_in_list <= len(data_address)-1 \
            and isinstance(data_address[order_in_list], (dict,collections.OrderedDict)):
            data_address_values = data_address[order_in_list].keys()
            for key_list_item in data_address_values:
               if key_name and key_name == key_list_item:
                   data_address[order_in_list][key_name] = value
                   change_applied = True
            else:
                if add_new_key:
                    data_address[order_in_list][key_name] = value
                    change_applied = True
    if debug: print(json.dumps(bgp_data, indent=2))
    return change_applied
################################################################################

if __name__ != "__main__": sys.exit(0)

### Start of BASIC STRUCTURES OF JSON
neighbor_list_item_txt_template = '''
{
    "ip_address": null,
    "bgp_current_state": null,
    "received_total_routes": null,
    "advertised_total_routes": null,
    "maximum_allowed_route_limit": null,
    "import_route_policy_is": null,
    "ping_response_success": null,
    "accepted-routes_list": []
}
'''

vrf_list_item_txt_template = '''
{
    "vrf_name": null,
    "neighbor_list": [%s],
    "interface_name": null,
    "interface_mtu" : null,
    "interface_intput_packets_per_seconds": null,
    "interface_output_packets_per_seconds": null
}
''' % (neighbor_list_item_txt_template)

bgp_json_txt_template='''
{
    "vrf_list": [%s]
}
''' % (vrf_list_item_txt_template)
### End of BASIC STRUCTURES OF JSON

print(bgp_json_txt_template)

bgp_data = json.loads(bgp_json_txt_template, \
    object_pairs_hook = collections.OrderedDict)

void_vrf_list_item = json.loads(vrf_list_item_txt_template, \
    object_pairs_hook = collections.OrderedDict)

#json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode('{"foo":1, "bar": 2}')

print(json.dumps(bgp_data, indent=2))
print(75*'-'+'\n')
# bgp_data["vrf_list"][0]["vrf_name"]='aasaas'
#
# aa = bgp_data["vrf_list"]
# print(type(aa))
#
#
# #print(bgp_dict_data.get(bgp_dict_data["vrf_list"][1],''))
#
# bgp_data["vrf_list"].append(void_vrf_list_item)
#
# bgp_data["vrf_list"][1]["vrf_name"]='qqqsaas'

update_bgpdata_structure(bgp_data["vrf_list"][0],"vrf_name",'asasasa')
update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"][0],"ip_address",'1.1.1.1')
update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"][0],"bgp_current_state",'ENABLED')

update_bgpdata_structure(bgp_data["vrf_list"],"vrf_name",'dddddd',1,void_vrf_list_item)
#print(json.dumps(bgp_data, indent=2))
