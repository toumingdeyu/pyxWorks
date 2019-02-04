@echo off
IF %1.==. GOTO LABEL
IF %2.==. GOTO LABEL
IF %3.==. GOTO LABEL
@echo on
REM --- Start of git initialization ---
call git init
call git config user.name %1
call git config user.email %2
call git remote add origin %3
call git pull origin master --force
call git push --set-upstream origin master
@echo off
GOTO FILEEND
:LABEL
  @echo off
  ECHO PRECONDITION: You need to be inside of clear subdirectory dedicated for git project.
  ECHO PARAMETERS:
  ECHO   1st parameter is "Name Surname"
  ECHO   2nd parameter is "email"
  ECHO   3rd parameter is git inventory: "https://gitlabname/groupname/projectname.git" 
  ECHO                                                       or 
  ECHO                                   "git@gitlabname:groupname/projectname.git"
  ECHO FOR EXAMPLE: 
  ECHO %0 "Name Surname" "email" "https://adahra.tb.rns.equant.com/oti-iptac/oti_bgp_meshing.git"
:FILEEND
