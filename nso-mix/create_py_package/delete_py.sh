#!/bin/bash

NCS_PACKAGES_PATH=/var/opt/ncs/packages

if [ -z $1 ]
then
	ls $NCS_PACKAGES_PATH
	echo ...Please insert Python package name as 1st parameter...
	exit 1
fi

PACKAGE_NAME=$1

if [ `whoami` = root ]
then
     rm -rfd $NCS_PACKAGES_PATH/$PACKAGE_NAME

else
     sudo -E -H -u root rm -rfd $NCS_PACKAGES_PATH/$PACKAGE_NAME 

fi

ls $NCS_PACKAGES_PATH

