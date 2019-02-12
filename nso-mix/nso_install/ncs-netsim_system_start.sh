#!/bin/bash
nsc-netsim list
ncs-netsim start
ncs-netsim is-alive

#source /etc/profile.d/ncs.sh

ncs --stop
sleep 2
sudo /etc/init.d/ncs start
sleep 2
pgrep ncs