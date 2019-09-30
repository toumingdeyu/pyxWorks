#!/usr/bin/python

import json, collections, six, sys, os
#from cerberus import Validator


json_str = """
{
    "username": "xxxxx", 
    "session_id": "/var/www/cgi-bin/logs/PASPE8-20190925-085451-ipxt_mig-data_collector-pnemec-vrp-IPXT.Tyntec-Submit_step_1-log", 
    "customer_name": "Tyntec", 
    "device_name": "PASPE8", 
    "interface_number": "2/0/18", 
    "peer_id": "", 
    "vrf_name": "IPXT.Tyntec", 
    "rd": "0.0.0.128:1502", 
    "rt_import": "2300:9005,2300:9001", 
    "rt_export": "2300:9006,2300:9001", 
    "vlan_id": "81", 
    "circuit_id": "LD012394", 
    "ip_address": "178.23.30.71", 
    "mask": "255.255.255.254", 
    "ip_address_customer": "172.25.10.23", 
    "peer_as": "43566", 
    "peer_address": "178.23.30.70", 
    "pref_limit": "1000", 
    "bgp_community_1": "43566:11000", 
    "bgp_community_2": "43566:20200", 
    "contract_band_width": "10", 
    "customer_prefixes_v4": "172.25.10.23,0,172.25.10.40,0,78.110.224.70,0,178.23.31.16,0,178.23.31.128,0.0.0.127,78.110.239.128,0.0.0.127", 
    "gw_subinterface": "Gi0/0/2.81", 
    "gw_peer_address_ibgp": "172.25.10.22", 
    "old_pe_interface": "GigabitEthernet2/0/18.81", 
    "last_updated": null, 
    "id": 259,
    "structured_customer_prefixes_v4": [
    {
      "customer_prefix_v4": [], 
      "customer_subnetmask_v4": "0"
    }, 
    {
      "customer_prefix_v4": "78.110.224.70", 
      "customer_subnetmask_v4": "0"
    }, 
    {
      "customer_prefix_v4": "178.23.31.16", 
      "customer_subnetmask_v4": "0"
    }, 
    {
      "customer_prefix_v4": "178.23.31.128", 
      "customer_subnetmask_v4": null
    }, 
    {
      "customer_prefix_v4": "78.110.239.128", 
      "customer_subnetmask_v4": "0.0.0.127"
    }
    ]    
}
"""

def load_json(path, file_name, dict = None):
    """Open json file return dictionary."""
    try:
        if dict:
            json_data = json.load(open(path + file_name))
        else:    
            json_data = json.load(open(path + file_name),object_pairs_hook=collections.OrderedDict)
    except Exception as e: print('PROBLEM[' + str(e) + ']')
    return json_data


### GET_XPATH_FROM_XMLSTRING ===================================================
def get_void_json_elements(json_data, ignore_void_strings = None, ignore_void_lists = None):
    """
    FUNCTION: get_void_json_elements()
    parameters: json_data   - data structure
    returns:    xpath_list  - lists of all void xpaths found in json_data
    """
    ### SUBFUNCTION --------------------------------------------------------------
    def get_dictionary_subreferences(tuple_data):
        json_deeper_references = []
        parrent_xpath = tuple_data[0]
        json_data = tuple_data[1]
        if isinstance(json_data, (dict,collections.OrderedDict)):
            for key in json_data.keys():
                key_content=json_data.get(key)
                if isinstance(key_content, (dict,collections.OrderedDict)): json_deeper_references.append((parrent_xpath+'/'+key,key_content))
                elif isinstance(key_content, (list,tuple)):
                    if len(key_content)==0:
                        json_deeper_references.append((parrent_xpath+'/'+key+'=[]',key_content))
                    for ii,sub_xml in enumerate(key_content,start=0):
                        if type(sub_xml) in [dict,collections.OrderedDict]: json_deeper_references.append((parrent_xpath+'/'+key+'['+str(ii)+']',sub_xml))
                elif isinstance(key_content, (six.string_types,six.integer_types,float,bool,bytearray)):
                      if '#text' in key: json_deeper_references.append((parrent_xpath+'="'+key_content+'"',key_content))
                      elif str(key)[0]=='@': json_deeper_references.append((parrent_xpath+'['+key+'="'+key_content+'"]',key_content))
                      else: json_deeper_references.append((parrent_xpath+'/'+key+'="'+str(key_content)+'"',key_content))               
                elif key_content == None: 
                    json_deeper_references.append((parrent_xpath+'/'+key+'="'+str(key_content)+'"',key_content))    
        return json_deeper_references
    ### FUNCTION -----------------------------------------------------------------
    references,xpath_list = [], []
    references.append(('',json_data))
    while len(references)>0:
        add_references=get_dictionary_subreferences(references[0])
        if '="None"' in references[0][0]\
            or not ignore_void_strings and '=""' in references[0][0]\
            or not ignore_void_lists and '=[]' in references[0][0]:
            xpath_list.append(references[0][0])
        references.remove(references[0])
        references=add_references+references
    del references
    return xpath_list
### ----------------------------------------------------------------------------



### MAIN =======================================================================
def main():
    #data = load_json('', 'ipx_cfg.json', dict = True)
    data = json.loads(json_str)
    print(json.dumps(data, indent = 2))
    
    if data: 
       None_elements = get_void_json_elements(data)
       print(None_elements)
    
    
if __name__ == "__main__": main()


#isinstance(json_data, (dict,collections.OrderedDict)):
