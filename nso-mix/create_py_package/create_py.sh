#!/bin/bash
  
if [ -z $1 ]
then
        echo Please insert Python package name as 1st parameter...
        exit 1
fi

PACKAGE_NAME=$1
NCS_PACKAGES_PATH=/var/opt/ncs/packages
MYPATH=$PATH

PY_FILE_TO_EDIT=$NCS_PACKAGES_PATH/$PACKAGE_NAME/python/$PACKAGE_NAME/action.py
MAKE_FILE_TO_EDIT=$NCS_PACKAGES_PATH/$PACKAGE_NAME/src/Makefile

#COMMAND_LINE="ncs-make-package --service-skeleton python $PACKAGE_NAME --dest /var/opt/ncs/packages/$PACKAGE_NAME"
COMMAND_LINE="ncs-make-package --service-skeleton python --component-class action.Action $PACKAGE_NAME --dest $NCS_PACKAGES_PATH/$PACKAGE_NAME"

if [ `whoami` = root ]
then
     $COMMAND_LINE
     sleep 3
     #sed --in-place  's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
else
     sudo -E -H -u root PATH=/opt/ncs/current/bin:$MYPATH -s $COMMAND_LINE
     sleep 3
     sudo -E -H -u root sed --in-place 's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place 's/YANGERPATH = \$(YANGPATH:%=--path %)/YANGERPATH = \$(YANGPATH:%=--path %)\nYANGPATH += ..\/..\/oti_common\/src\/yang \\\nYANGPATH += ..\/..\/com_orange_common\/src\/yang \\/' "${MAKE_FILE_TO_EDIT}"
fi

#ls -l $NCS_PACKAGES_PATH
ls -R $NCS_PACKAGES_PATH/$PACKAGE_NAME

head "$PY_FILE_TO_EDIT"
cat "$MAKE_FILE_TO_EDIT"