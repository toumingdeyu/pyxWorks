echo %1 1st parameter is device name ios0..2 ,(needed file ios0..2.xml), %2 2nd parameter is password
rem Create the Device
call curl -H "Content-Type:application/vnd.yang.data+xml" -X PUT -u localnso:%2 -d @%1.xml  http://192.168.56.101:8080/api/running/devices/device/%1

rem Fetch SSH Keys
call curl -H "Content-Type:application/vnd.yang.data+xml" -X POST -u localnso:%2 http://192.168.56.101:8080/api/running/devices/device/%1/ssh/_operations/fetch-host-keys

rem Sync From
call curl -H "Content-Type:application/vnd.yang.data+xml" -X POST -u localnso:%2 http://192.168.56.101:8080/api/running/devices/device/%1/_operations/sync-from