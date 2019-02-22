#!/bin/bash

### go to https://github.com/NSO-developer/ntool
### copy zip from web and unzip it to packages directory /var/opt/ncs.packages
### rename directory ntool-master to tailf-ntool

sudo -s
cd /var/opt/ncs/packages
wget https://github.com/NSO-developer/ntool/archive/master.zip
unzip master.zip
rm -rfd master.zip
mv ntool-master tailf-ntool
source /etc/profile.d/ncs.sh
cd /var/opt/ncs
make -C packages/tailf-ntool/src clean all
