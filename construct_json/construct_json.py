#!/usr/bin/python
import sys
import os
import io
import optparse
import json
import yaml
import collections
import six

################################################################################
bgp_data = collections.OrderedDict()

def update_bgpdata_structure(data_address, key_name = None, value = None, \
    order_in_list = None, list_append_value = None, add_new_key = None, \
    debug = None):
    """
    FUNCTION: update_bgpdata_structure
    PARAMETERS:
       data_address - address of json ending on parrent (key_name or list_number if exists)
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
    if debug: print("DATA_TYPE: ", type(data_address),'ID: ',id(data_address), \
         "DATA: ", data_address)
    ### REWRITE VALUE IN DICT ON KEY_NAME POSITION
    if isinstance(data_address, (dict,collections.OrderedDict)) \
        and isinstance(key_name, (six.string_types)):
        data_address_values = data_address.keys()
        for address_key_value in data_address_values:
            if key_name and key_name == address_key_value:
                data_address[key_name] = value
                if debug: print('DICT[%s]=%s.'%(key_name,value))
                change_applied = True
        else:
            if add_new_key:
                data_address[key_name] = value
                if debug: print('ADDED_TO_DICT[%s]=%s.'%(key_name,value))
                change_applied = True
    ### ADD LIST POSITION if NEEDED, REWRITE VALUE IN DICT ON KEY_NAME POSITION
    elif isinstance(data_address, (list,tuple)):
        ### SIMPLY ADD VALUE TO LIST WHEN ORDER NOT INSERTED
        if not order_in_list and not key_name:
            if debug: print('LIST_APPENDED.')
            data_address.append(value)
            change_applied = True
        else:
            ### ORDER_IN_LIST=[0..], LEN()=[0..]
            if order_in_list == len(data_address):
                data_address.append(list_append_value)
                if debug: print('LIST_APPENDED_BY_ONE_SECTION.')
            ### AFTER OPTIONAL ADDITION OF END OF LIST BY ONE
            if order_in_list <= len(data_address)-1 \
                and isinstance(data_address[order_in_list], \
                (dict,collections.OrderedDict)):
                data_address_values = data_address[order_in_list].keys()
                for key_list_item in data_address_values:
                   if key_name and key_name == key_list_item:
                       data_address[order_in_list][key_name] = value
                       if debug: print('DICT_LIST[%s][%s]=%s.'% \
                           (order_in_list,key_name,value))
                       change_applied = True
                else:
                    if add_new_key:
                        data_address[order_in_list][key_name] = value
                        if debug: print('ADDED_TO_DICT_LIST[%s][%s]=%s.'% \
                            (order_in_list,key_name,value))
                        change_applied = True
#     else:
#         data_address = value
#         change_applied = True
    #if debug: print(json.dumps(bgp_data, indent=2))
    if debug: print("CHANGE_APPLIED: ",change_applied)
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

bgp_data = json.loads(bgp_json_txt_template, \
    object_pairs_hook = collections.OrderedDict)

void_vrf_list_item = json.loads(vrf_list_item_txt_template, \
    object_pairs_hook = collections.OrderedDict)

void_neighbor_list_item = json.loads(neighbor_list_item_txt_template, \
    object_pairs_hook = collections.OrderedDict)

#json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode('{"foo":1, "bar": 2}')

# print(json.dumps(bgp_data, indent=2))
# print(75*'-'+'\n')

try:
    update_bgpdata_structure(bgp_data["vrf_list"][0],"vrf_name",'asasasa')
    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"],"ip_address",'1.1.1.1',0,void_neighbor_list_item)
    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"],"bgp_current_state",'ENABLED',0,void_neighbor_list_item)

    update_bgpdata_structure(bgp_data["vrf_list"],"vrf_name",'dddddd',1,void_vrf_list_item)
    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"],"bgp_current_state",'ENABLED',1,void_neighbor_list_item)
    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"],"ip_address",'2.2.2.2',1,void_neighbor_list_item)

    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"][1]["accepted-routes_list"],None,'3.3.3.3')
    update_bgpdata_structure(bgp_data["vrf_list"][0]["neighbor_list"][1]["accepted-routes_list"],None,'4.4.4.4')


#    update_bgpdata_structure(bgp_data["vrf_list"][0]["interface_name"],None,"AAAAAA",debug = True)
    #bgp_data["vrf_list"][0]["interface_name"] = 'BBBBB'
    #update_bgpdata_structure(bgp_data["vrf_list"][0],"interface_name","CCCCC",debug = True)

    aaa='bgp_data["vrf_list"][0]["interface_name"]'
    exec('%s="%s"'%(aaa,'EEE'))


#     print(id(bgp_data["vrf_list"][0]["vrf_name"]))
#     update_bgpdata_structure(bgp_data["vrf_list"][0]["vrf_name"],None,'asasasa',debug = True)
#
#     #bgp_data["vrf_list"][0]["vrf_name"] = 'aaaaaa'
#     #update_bgpdata_structure(bgp_data["vrf_list"][0]["received_total_routes"],None,2222)



except ValueError: print("Error Value.")
except IndexError: print("Error Index.")
except KeyError:   print("Error Key.")

print(json.dumps(bgp_data, indent=2))
