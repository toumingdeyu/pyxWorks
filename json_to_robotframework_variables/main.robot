*** Settings ***
Resource    import1.robot
Variables    variables1.yaml
Variables    variables2.py
Variables    py_get_variables.py

*** Variables ***

${CLUSTER_ID}=    130

${BGP_ASN}=    {"oti_bgp_meshing:oti_bgp_meshing": [{"as_number": 5511}]}

${FULL_MESH}=    {"devices": [{"device": "${RTR_FM}", "full_mesh": true}]}
${RR}=    {"devices": [{"device": "${RTR_RR}", "full_mesh": true, "route_reflector": true, "cluster_id": ${CLUSTER_ID}}]}
${RR2}=    {"devices": [{"device": "${RTR_RR2}", "full_mesh": true, "route_reflector": true, "cluster_id": ${CLUSTER_ID}}]}
${RR_CL}=    {"devices": [{"device": "${RTR_CL}", "full_mesh": false, "cluster_id": ${CLUSTER_ID}}]}
${RR_CL2}=    {"devices": [{"device": "${RTR_CL2}", "full_mesh": false, "cluster_id": ${CLUSTER_ID}}]}
${UPG_2_RR}=    {"devices": [{"device": "${RTR_FM}", "route_reflector": true, "cluster_id": ${CLUSTER_ID}}]}
${LOCAL_MESH}=   { "oti_bgp_meshing:oti_bgp_meshing": { "as_number": 5511, "devices": [ { "device": "AUVPE1", "full_mesh": false, "cluster_id": 130, "local_mesh": true, "local_mesh_region": "AUV_SIN" }, {"device": "SINPE2","local_mesh": true, "local_mesh_region": "AUV_SIN"} ] }}

*** Keywords ***

*** Test Cases ***
GET SERVICES
  Log Variables

