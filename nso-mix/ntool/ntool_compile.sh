#!/bin/bash

### https://github.com/NSO-developer/ntool

sudo -s
source /etc/profile.d/ncs.sh
cd /var/opt/ncs
make -C packages/tailf-ntool/src clean all
