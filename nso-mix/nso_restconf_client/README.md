"# peteneme's nso-mix learning sub-github..."

DEVICE NAME = iosxr


CREATE DEVICE in NSO:
---------------------

SYNTAX: 
python nso_restconf_client.py -a c -f iosxr.json 



PATCH DEVICE in NSO:
--------------------

SYNTAX: 
python nso_restconf_client.py -a p -f iosxr.json
python nso_restconf_client.py -a p -f iosxr.json -p device



PATCH DEVICE CONFIG in NSO:
---------------------------

SYNTAX: 
python nso_restconf_client.py -a p -f iosxr.json
python nso_restconf_client.py -a p -f iosxr.json -p config


READ DEVICE JSON (all) from NSO:
--------------------------------

SYNTAX: 
python nso_restconf_client.py -c all -n iosxr 



READ DEVICE JSON (all) from NSO:
--------------------------------

SYNTAX: 
python nso_restconf_client.py -c all -n iosxr -t xml



READ JSON DEVICE CONFIG from NSO:
---------------------------------

SYNTAX: 
python nso_restconf_client.py -n iosxr
python nso_restconf_client.py -c config -n iosxr


READ XML DEVICE CONFIG from NSO:
--------------------------------

SYNTAX: 
python nso_restconf_client.py -n iosxr -t x
python nso_restconf_client.py -n iosxr -t xml
python nso_restconf_client.py -c config -n iosxr -t xml


DELETE DEVICE in NSO:
---------------------

SYNTAX: 
python nso_restconf_client.py -a d -n iosxr



NOTE:
-----
-HTTP 403 ACCESS DENIED could mean locked element (device) in NSO by NETCONF or 'ncs_load' command. 