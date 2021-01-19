#!/bin/bash

function do_as_root {
### first parameter is command_line ###
    if [ `whoami` = root ]
    then
         $1
    else
         sudo -E -H -u root PATH=$MYPATH -s $1
    fi
}

if [ -z $1 ]
then
	echo Please insert filename to copy without path as 1st parameter...
	exit 1
fi

FILE_NAME="$1"
COPY_TO_PATH=/usr/local/iptac/bin
MYPATH=$PATH
#COMMAND_LINE="cp ./$FILE_NAME $COPY_TO_PATH/$COPY_TO_PATH"
COMMAND_LINE="echo `whoami`"

do_as_root $COMMAND_LINE



#ls -l $COPY_TO_PATH
#ls -R $COPY_TO_PATH/$FILE_NAME






