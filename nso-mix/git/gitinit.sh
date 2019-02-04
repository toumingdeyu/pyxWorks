#!/bin/bash
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ] ;
then
  echo PRECONDITION: You need to be inside of clear subdirectory dedicated for git project.
  echo PARAMETERS:
  echo   1st parameter is \"Name Surname\"
  echo   2nd parameter is \"email\"
  echo   3rd parameter is git inventory: \"https://username:password@gitlabname/groupname/projectname.git\" 
  echo                                                       or 
  echo                                   \"git@gitlabname:groupname/projectname.git\"
  echo FOR EXAMPLE: 
  echo $0 \"Name Surname\" \"email\" \"https://adahra.tb.rns.equant.com/oti_backbone/oti_bgp_meshing.git\"
  exit 0
else
  # --- Start of git initialization ---
  git init
  sleep 2
  git config http.sslverify false
  git config credential.helper cache
  git config user.name $1
  git config user.email $2
  git remote add origin $3
  git pull origin master --force
  git push --set-upstream origin master
fi


