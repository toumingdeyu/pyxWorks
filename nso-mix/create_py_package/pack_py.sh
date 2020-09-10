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

if [ `whoami` = root ]
then

     tar -cvf $NCS_PACKAGES_PATH/$PACKAGE_NAME.$ACTUAL_DATE.tar.gz $NCS_PACKAGES_PATH/$PACKAGE_NAME

else

     sudo -E -H -u root tar -cvf /home/$MY_USER/$PACKAGE_NAME.$ACTUAL_DATE.tar.gz $NCS_PACKAGES_PATH/$PACKAGE_NAME

fi


