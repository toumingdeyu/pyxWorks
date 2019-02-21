@echo off
IF %1.==. GOTO LABEL
IF %2.==. GOTO LABEL
@echo off
setlocal enabledelayedexpansion
REM ============================================================================
SET URL=https://adahra.tb.rns.equant.com/oti_backbone/
SET GIT=.git
REM ============================================================================
SET PRJ[0]=oti_bgp_meshing
SET PRJ[1]=oti_inventory
SET PRJ[2]=oti-routeurs-security-configuration
SET PRJ[3]=oti_isis
SET PRJ[4]=oti_role
SET PRJ[5]=orange-oti-lde-workflows
SET PRJ[6]=orange-oti-lde-project
SET PRJ[7]=ncs-run-orange-lde
SET PRJ[8]=oti_backbones
SET PRJ[9]=oti_mgmt
SET PRJ[10]=orange-oti-bgp-customer
SET PRJ[11]=oti_subinterface-availability
SET PRJ[12]=oti_common
SET PRJ[13]=win_lde
REM ----------------------------------------------------------------------------
SET "x=0"
:SymLoop
if defined PRJ[%x%] (
   call mkdir %%PRJ[%x%]%%
   call cd %%PRJ[%x%]%%
   call gitinit.bat $1 $2 %URL%%%PRJ[%x%]%%%GIT%
   call cd ..
   set /a "x+=1"
   GOTO :SymLoop
)
REM ----------------------------------------------------------------------------
@echo off
GOTO FILEEND
:LABEL
  @echo off
  ECHO PRECONDITION: You need to be inside of clear subdirectory dedicated for git project.
  ECHO PARAMETERS:
  ECHO   1st parameter is "Name Surname"
  ECHO   2nd parameter is "email"
  ECHO FOR EXAMPLE:
  ECHO %0 "Name Surname" "email" 
:FILEEND


