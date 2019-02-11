#!/bin/bash
### paths what should be set
#export NCS_DIR=/opt/ncs/current
 
#export PYTHONPATH=/opt/ncs/current/src/ncs/pyapi

#export MANPATH=/opt/ncs/current/man:/usr/share/man
 
#export PATH=/opt/ncs/current/bin:$PATH


### netsim basic setup
ssh-keygen
sudo mkdir /netsim
sudo chmod 777 /netsim
export NETSIM_DIR=/netsim
sudo export NETSIM_DIR=/netsim
sudo ssh-keygen -t rsa -f /opt/ncs/current/netsim/confd/etc/confd/ssh/ssh_host_rsa_key
sudo chmod +r /opt/ncs/current/netsim/confd/etc/confd/ssh/ssh_host_rsa_key
ncs-netsim delete-network
ncs-netsim create-network cisco-ios 3 ios
 
#ncs-netsim create-device cisco-ios ios1

cd $NETSIM_DIR
ncs-netsim start

ncs-netsim is-alive
