#!/bin/bash

NCS_PACKAGES_PATH=/var/opt/ncs/packages
MY_USER=`whoami`

if [ -z $1 ]
then
	ls /home/$MY_USER/*.gz
	echo ...Please insert Python tar.gz package name as 1st parameter...
	exit 1
fi

PACKAGE_NAME=$1
MYPATH=$PATH
MY_USER=`whoami`
ACTUAL_DATE=`date +%Y%m%d_%H%M`

if echo $PACKAGE_NAME | grep -q "/"
then

    echo .
else
    PACKAGE_NAME=/home/$MY_USER/$PACKAGE_NAME
    echo ...unpacking $PACKAGE_NAME ...
fi



if [ `whoami` = root ]
then

     tar -xvf /home/$MY_USER/$PACKAGE_NAME -C $NCS_PACKAGES_PATH

else

     sudo -E -H -u root tar -xvf $PACKAGE_NAME -C $NCS_PACKAGES_PATH

fi

ls $NCS_PACKAGES_PATH

