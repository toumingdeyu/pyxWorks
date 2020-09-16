#!/bin/bash

if [ -z $1 ]
then
	echo Please insert Python package name as 1st parameter...
	exit 1
else
        PACKAGE_NAME=win_act_oper_$1
fi

NCS_PACKAGES_PATH=/var/opt/ncs/packages
MYPATH=$PATH

PY_FILE_TO_EDIT=$NCS_PACKAGES_PATH/$PACKAGE_NAME/python/$PACKAGE_NAME/action.py
MAKE_FILE_TO_EDIT=$NCS_PACKAGES_PATH/$PACKAGE_NAME/src/Makefile
YANG_FILE_TO_EDIT=$NCS_PACKAGES_PATH/$PACKAGE_NAME/src/yang/$PACKAGE_NAME.yang

COMMAND_LINE="ncs-make-package --service-skeleton python --component-class action.Action $PACKAGE_NAME --dest $NCS_PACKAGES_PATH/$PACKAGE_NAME"



if [ `whoami` = root ]
then
     $COMMAND_LINE
     sleep 1
     sed --in-place  's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
     sed --in-place 's/YANGERPATH = \$(YANGPATH:%=--path %)/YANGERPATH = \$(YANGPATH:%=--path %)\nYANGPATH += ..\/..\/win_common\/src\/yang \\\nYANGPATH += ..\/..\/com_orange_common\/src\/yang \\/' "${MAKE_FILE_TO_EDIT}"
     sed --in-place 's/^  description/  import win_common \{\n    prefix win;\n  \}\n  import com_orange_common \{\n    prefix orange;\n  \}\n\n  description/' "${YANG_FILE_TO_EDIT}"
     sed --in-place "s/^  list /  augment \/orange:orange\/orange:win \{\n    container common_actions \{\n      tailf:info \"orange win $PACKAGE_NAME\";\n      description \"$PACKAGE_NAME package\";\n      container actions \{\n      \}\n    \}\n  \}\n\n  augment \/orange:orange\/orange:win\/$PACKAGE_NAME:common_actions\/$PACKAGE_NAME:actions \{\n    tailf:action action_name \{\n      tailf:actionpoint action_name;\n      input \{\n        leaf device \{\n          type leafref \{\n            path \"\/ncs:devices\/ncs:device\/ncs:name\";\n          }\n        \}\n      \}\n      output \{\n      \}\n    \}\n  \}\n\n  list /" "${YANG_FILE_TO_EDIT}"

else
     sudo -E -H -u root PATH=/opt/ncs/current/bin:$MYPATH -s $COMMAND_LINE
     sleep 1
     sudo -E -H -u root sed --in-place 's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place 's/YANGERPATH = \$(YANGPATH:%=--path %)/YANGERPATH = \$(YANGPATH:%=--path %)\nYANGPATH += ..\/..\/win_common\/src\/yang \\\nYANGPATH += ..\/..\/com_orange_common\/src\/yang \\/' "${MAKE_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place 's/^  description/  import win_common \{\n    prefix win;\n  \}\n  import com_orange_common \{\n    prefix orange;\n  \}\n\n  description/' "${YANG_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place "s/^  list /  augment \/orange:orange\/orange:win \{\n    container common_actions \{\n      tailf:info \"orange win $PACKAGE_NAME\";\n      description \"$PACKAGE_NAME package\";\n      container actions \{\n      \}\n    \}\n  \}\n\n  augment \/orange:orange\/orange:win\/$PACKAGE_NAME:common_actions\/$PACKAGE_NAME:actions \{\n    tailf:action action_name \{\n      tailf:actionpoint action_name;\n      input \{\n        leaf device \{\n          type leafref \{\n            path \"\/ncs:devices\/ncs:device\/ncs:name\";\n          }\n        \}\n      \}\n      output \{\n      \}\n    \}\n  \}\n\n  list /" "${YANG_FILE_TO_EDIT}"

fi

#   /com_orange_common:orange/com_orange_common:win





ls -R $NCS_PACKAGES_PATH/$PACKAGE_NAME

head "$PY_FILE_TO_EDIT"
cat "$MAKE_FILE_TO_EDIT"
cat "$YANG_FILE_TO_EDIT"
