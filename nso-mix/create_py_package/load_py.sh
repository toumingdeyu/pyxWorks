#!/bin/bash
#!/bin/bash

NCS_PACKAGES_PATH=/var/opt/ncs/packages

if [ -z $1 ]
then
  ls $NCS_PACKAGES_PATH
  echo ...Please insert Python package name as 1st parameter...
  exit 1
else
  PACKAGE_NAME=$1
fi

./delete_py.sh $PACKAGE_NAME
./unpack_py.sh /home/pnemec/$PACKAGE_NAME.tar.gz
./make_py.sh $PACKAGE_NAME
echo packages reload force | ncs_cli -C
./tailf_py.sh $PACKAGE_NAME

