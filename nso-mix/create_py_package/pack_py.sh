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

if [ `whoami` = root ]
then

     sh -c "cd $NCS_PACKAGES_PATH && tar -cvf /home/$MY_USER/$PACKAGE_NAME.$ACTUAL_DATE.tar.gz $PACKAGE_NAME ; cd $ACTUAL_DIR"

else

     #sudo -E -H -u root tar -cvf /home/$MY_USER/$PACKAGE_NAME.$ACTUAL_DATE.tar.gz $NCS_PACKAGES_PATH/$PACKAGE_NAME
     sudo -E -H -u root sh -c "cd $NCS_PACKAGES_PATH && tar -cvf /home/$MY_USER/$PACKAGE_NAME.$ACTUAL_DATE.tar.gz $PACKAGE_NAME ; cd $ACTUAL_DIR" 

fi


