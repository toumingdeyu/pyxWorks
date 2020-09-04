#!/bin/bash

if [ -z $1 ]
then
	echo Please insert Python package name as 1st parameter...
	exit 1
fi

PACKAGE_NAME="$1"
NCS_PACKAGES_PATH=/var/opt/ncs/packages
MYPATH=$PATH

#COMMAND_LINE="ncs-make-package --service-skeleton python $PACKAGE_NAME --dest /var/opt/ncs/packages/$PACKAGE_NAME"
COMMAND_LINE="ncs-make-package --service-skeleton python --component-class action.Action $PACKAGE_NAME --dest /var/opt/ncs/packages/$PACKAGE_NAME"

#echo $MYPATH
#echo $COMMAND_LINE
#echo .

if [ `whoami` = root ]
then
     $COMMAND_LINE
else
     sudo -E -H -u root PATH=/opt/ncs/current/bin:$MYPATH -s $COMMAND_LINE
fi

ls -l $NCS_PACKAGES_PATH
ls -R $NCS_PACKAGES_PATH/$PACKAGE_NAME






