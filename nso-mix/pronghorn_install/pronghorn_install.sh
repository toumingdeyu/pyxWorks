#!/bin/bash

### Prerequisities:
#NCS_DIR=/home/nso/ncs-4.7
export NCS_RUN=$HOME/ncs-run

### Dependencies:
sudo apt install nodejs
sudo apt install redis
sudo apt install mongodb
sudo apt install npm

### Install:
echo y | sudo ./pronghorn-20180202_101453-linux.x86_64.bin -i

service pronghorn start
sleep 2
systemctl -l --type service --all | egrep "pronghorn|redis|mongo"


#do for sure: 
sudo systemctl enable pronghorn

#check if autostart is enabled
sudo systemctl is-enabled pronghorn

cd $NCS_RUN
ncs 
pgrep ncs

sleep 2
#web access
firefox http://127.0.0.1:3000

