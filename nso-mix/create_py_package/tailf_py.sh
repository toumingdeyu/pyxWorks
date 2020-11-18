#!/bin/bash

NCS_PACKAGES_PATH=/var/opt/ncs/packages

if [ -z $1 ]
then
	ls $NCS_PACKAGES_PATH
	echo ...Please insert Python package name as 1st parameter...
	exit 1
fi

PACKAGE_NAME=$1
MYPATH=$PATH
MY_USER=`whoami`
ACTUAL_DATE=`date +%Y%m%d_%H%M`
ACTUAL_DIR=`pwd`

echo FILE: /var/log/ncs/ncs-python-vm-$PACKAGE_NAME.log
echo -----------------------------------------------------------------
tail -f /var/log/ncs/ncs-python-vm-$PACKAGE_NAME.log


