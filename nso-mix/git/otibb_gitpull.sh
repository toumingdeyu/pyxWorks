#!/bin/bash

## declare an array variable
declare -a arr=(
"oti_bgp_meshing"
"oti_inventory"
"oti-routeurs-security-configuration"
"oti_isis"
"oti_role"
"orange-oti-lde-workflows"
"orange-oti-lde-project"
"ncs-run-orange-lde"
"orange-oti-bgp-customer"
"oti_subinterface-availability"
"oti_common"
"win_lde"
)

#============================ MAIN =================================

## now loop through the above array
for i in "${arr[@]}"
do
  if [ -d ${PWD}/${i} ] ; then
    cd ${i}
    git pull
    cd ..
  fi  
done


