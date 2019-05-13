#!/usr/bin/python
import sys
import os
import io
import optparse
import json
import yaml
import collections

# def update_data_structure(data_structure = None, data_key = None, data_to_update = None):
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

def update_data_structure(data2):
    global bgp_data

    try: data2_type = type(data2)
    except: data2_type = None
    print(data2_type)

    if isinstance(data2, dict):
        #bgp_data.update(data2) #rewrite
        bgp_data = {key: value for (key, value) in (bgp_data.items() + data2.items())}

if __name__ != "__main__": sys.exit(0)

bgp_data = {}

# bgp_data['aa'] = ['aaaaa']
# bgp_data['dd'] = 'ddddd'

# bgp_data['aa'].append('ccccc')
# bgp_data.update(bb='bbbbb' )
#
# json_dumps=json.dumps(bgp_data)
# print(bgp_data,json_dumps)
# print(bgp_data['aa'][0])


# update_data_structure({'vrf_list':[{'vrf_name':'orange1','neighbor_list':[{'ip_address':'11.22.33.44'}]}]})
# print(bgp_data)
# update_data_structure({'vrf_list':[{'vrf_name':'orange2','neighbor_list':[{'ip_address':'55.22.33.11'}]}]})
# print(bgp_data)

bgp_json_txt_template='''
{
    "vrf_list": [
            {
                "vrf_name": null,
                "neighbor_list": [
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
                    ],
                "interface_name": null,
                "interface_mtu" : null,
                "interface_intput_packets_per_seconds": null,
                "interface_output_packets_per_seconds": null
            }
        ]
}
'''

print(bgp_json_txt_template)

bgp_dict_data=json.loads(bgp_json_txt_template, \
    object_pairs_hook = collections.OrderedDict)

#json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode('{"foo":1, "bar": 2}')

print(bgp_dict_data)
print('\n')

bgp_dict_data["vrf_list"][0]["vrf_name"]='aasaas'

print(json.dumps(bgp_dict_data, indent=4))
