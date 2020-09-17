#!/bin/bash

if [ -z $1 ]
then
	echo Please insert Python package name as 1st parameter...
	exit 1
else
        PACKAGE_NAME=win_act_oper_$1
fi

if [ -z $2 ]
then
	echo Please insert Python action_name as 2nd parameter...
	exit 1
else
        ACTION_NAME=$2
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
     sed --in-place 's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
     sed --in-place "s/        # When this setup method/\n        self\.register_action\(\'$2\', action_class_$2\)\n\n        # When this setup method/" "${PY_FILE_TO_EDIT}"
     sed --in-place 's/YANGERPATH = \$(YANGPATH:%=--path %)/YANGERPATH = \$(YANGPATH:%=--path %)\nYANGPATH += ..\/..\/win_common\/src\/yang \\\nYANGPATH += ..\/..\/com_orange_common\/src\/yang \\/' "${MAKE_FILE_TO_EDIT}"
     sed --in-place 's/^  description/  import win_common \{\n    prefix win;\n  \}\n  import com_orange_common \{\n    prefix orange;\n  \}\n\n  description/' "${YANG_FILE_TO_EDIT}"
     sed --in-place "s/^  list /  augment \/orange:orange\/orange:win \{\n    container $1 \{\n      tailf:info \"orange win $1\";\n      description \"$1 package\";\n      container actions \{\n      \}\n    \}\n  \}\n\n  augment \/orange:orange\/orange:win\/$PACKAGE_NAME:$1\/$PACKAGE_NAME:actions \{\n    tailf:action $2 \{\n      tailf:actionpoint $2;\n      input \{\n        leaf device \{\n          type leafref \{\n            path \"\/ncs:devices\/ncs:device\/ncs:name\";\n          \}\n        \}\n      \}\n      output \{\n      \}\n    \}\n  \}\n\n  list /" "${YANG_FILE_TO_EDIT}"
     make -C $NCS_PACKAGES_PATH/$PACKAGE_NAME/src
else
     sudo -E -H -u root PATH=/opt/ncs/current/bin:$MYPATH -s $COMMAND_LINE
     sudo -E -H -u root sed --in-place 's/import ncs/import ncs \nfrom ncs.dp import Action/' "${PY_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place "s/        # When this setup method/\n        self\.register_action\(\'$2\', action_class_$2\)\n\n        # When this setup method/" "${PY_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place 's/YANGERPATH = \$(YANGPATH:%=--path %)/YANGERPATH = \$(YANGPATH:%=--path %)\nYANGPATH += ..\/..\/win_common\/src\/yang \\\nYANGPATH += ..\/..\/com_orange_common\/src\/yang \\/' "${MAKE_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place 's/^  description/  import win_common \{\n    prefix win;\n  \}\n  import com_orange_common \{\n    prefix orange;\n  \}\n\n  description/' "${YANG_FILE_TO_EDIT}"
     sudo -E -H -u root sed --in-place "s/^  list /  augment \/orange:orange\/orange:win \{\n    container $1 \{\n      tailf:info \"orange win $1\";\n      description \"$1 package\";\n      container actions \{\n      \}\n    \}\n  \}\n\n  augment \/orange:orange\/orange:win\/$PACKAGE_NAME:$1\/$PACKAGE_NAME:actions \{\n    tailf:action $2 \{\n      tailf:actionpoint $2;\n      input \{\n        leaf device \{\n          type leafref \{\n            path \"\/ncs:devices\/ncs:device\/ncs:name\";\n          \}\n        \}\n      \}\n      output \{\n      \}\n    \}\n  \}\n\n  list /" "${YANG_FILE_TO_EDIT}"
     sudo -E -H -u root make -C $NCS_PACKAGES_PATH/$PACKAGE_NAME/src
fi


ls -R $NCS_PACKAGES_PATH/$PACKAGE_NAME

cat "$PY_FILE_TO_EDIT"
cat "$MAKE_FILE_TO_EDIT"
cat "$YANG_FILE_TO_EDIT"

