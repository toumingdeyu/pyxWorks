#!/bin/bash

./delete_py.sh win_act_oper_os_upgrade
./unpack_py.sh /home/pnemec/win_act_oper_os_upgrade.tar.gz
./make_py.sh win_act_oper_os_upgrade
echo packages reload force | ncs_cli -C
./tailf_py.sh win_act_oper_os_upgrade

