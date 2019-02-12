call echo '%1' is password

rem call curl -i -X OPTIONS http://192.168.56.101:8080/api -u localnso:%1
rem call curl -i -X GET http://192.168.56.101:8080/api -u localnso:%1 -H "Accept: application/vnd.yang.api+json"

rem call curl -i -X GET http://192.168.56.101:8080/restconf/data/services  -u localnso:%1 -H "Accept: application/yang-data+json"

call curl -i -X GET http://192.168.56.101:8080/api/running/devices -u localnso:%1 -H "Accept: application/vnd.yang.data+json"

