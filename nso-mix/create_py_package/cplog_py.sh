#!/bin/bash

NCS_PACKAGES_PATH=/var/opt/ncs/packages
NCS_LOG_PATH=/var/log/ncs/

if [ -z $1 ]
then
	ls $NCS_LOG_PATH/*.log
	echo ...Please insert Python package name as 1st parameter...
	exit 1
fi

PACKAGE_NAME=$1

if [ `whoami` = root ]
then
     cp $NCS_LOG_PATH/$PACKAGE_NAME ./

else
     sudo -E -H -u root cp $NCS_LOG_PATH/$PACKAGE_NAME ./

fi

ls ./*.log

