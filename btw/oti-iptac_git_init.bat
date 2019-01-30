@echo off
IF %1.==. GOTO LABEL
IF %2.==. GOTO LABEL
@echo off
call mkdir oti_bgp_meshing
call cd oti_bgp_meshing
call cp ../gitinit.bat gitinit.bat
call gitinit.bat $1 $2 https://adahra.tb.rns.equant.com/oti-iptac/oti_bgp_meshing.git
call cd ..
call mkdir oti_inventory
call cd oti_inventory
call cp ../gitinit.bat gitinit.bat
call gitinit.bat $1 $2 https://adahra.tb.rns.equant.com/oti-iptac/oti_inventory.git
call cd ..
call mkdir oti-routeurs-security-configuration
cd oti-routeurs-security-configuration
call cp ../gitinit.bat gitinit.bat
call gitinit.bat $1 $2 https://adahra.tb.rns.equant.com/oti-iptac/oti-routeurs-security-configuration.git
call cd ..
call mkdir oti_isis
cd oti_isis
call cp ../gitinit.bat gitinit.bat
call gitinit.bat $1 $2 https://adahra.tb.rns.equant.com/pmarcais/oti_isis.git
call cd ..
call mkdir oti_role
call cd oti_role
call cp ../gitinit.bat gitinit.bat
call gitinit.bat $1 $2 https://adahra.tb.rns.equant.com/pmarcais/oti_role.git
call cd ..
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


