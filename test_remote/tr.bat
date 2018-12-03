@echo off
set user="root"
set passwrd="xxxxxxx"
set passwrd2="xxxxxx"
set batscriptversion=0.191
SET restofparameters=
SET batchyes="-batch"
SET deleteFile="NO"
SET sudosuYESorNO="NO"
REM SET deleteFile="YES"
echo *************************************************
echo TestRun  v%batscriptversion%
echo (timestamp %TIME% ,%DATE%)  


IF "%~1"=="" GOTO gethelp
IF "%~2"=="" GOTO gethelp

set arg1=%1
set arg2=%2
echo file     %arg2%
echo OS       %arg1%

SHIFT
SHIFT

:Loop
IF "%1"=="" GOTO Continue
  SET restofparameters=%restofparameters% %1 
SHIFT
GOTO Loop
:Continue

echo restofparameters=%restofparameters%

REM Volkers machines
IF "%arg1%"=="all" GOTO startOS1
IF "%arg1%"=="1" GOTO startOS1
IF "%arg1%"=="2" GOTO startOS2
IF "%arg1%"=="3" GOTO startOS3
IF "%arg1%"=="4" GOTO startOS4
REM Pontiac machines
IF "%arg1%"=="5" GOTO startOS5
IF "%arg1%"=="6" GOTO startOS6
IF "%arg1%"=="7" GOTO startOS7
IF "%arg1%"=="8" GOTO startOS8
IF "%arg1%"=="9" GOTO startOS9
IF "%arg1%"=="10" GOTO startOS10
IF "%arg1%"=="11" GOTO startOS11
IF "%arg1%"=="12" GOTO startOS12
REM AIX from JH
IF "%arg1%"=="13" GOTO startOS13
REM dean america
IF "%arg1%"=="14" GOTO startOS14
IF "%arg1%"=="15" GOTO startOS15
IF "%arg1%"=="16" GOTO startOS16
IF "%arg1%"=="17" GOTO startOS17
IF "%arg1%"=="18" GOTO startOS18
IF "%arg1%"=="19" GOTO startOS19

echo.


:startOS1
SET srvnumber=1
SET ossername="Linux16"
SET osserver="bxlvclient16.eu.tslabs.hpecorp.net"
REM CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS2
SET srvnumber=2
SET ossername="Linux17"
SET osserver="bxlvclient17.eu.tslabs.hpecorp.net"
REM CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS3
SET srvnumber=3
SET ossername="SunOS"
SET osserver="bxlvclient18.eu.tslabs.hpecorp.net"
REM CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS4
SET srvnumber=4
SET ossername="HP-UX"
SET osserver="bxlvclient27.eu.tslabs.hpecorp.net"
REM CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile


:startOS5
SET srvnumber=5
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS01 130.175.178.120 HP-UX 11.31"
SET osserver="130.175.178.120"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS6
SET srvnumber=6
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS02 130.175.178.121 Solaris 10u11"
SET osserver="130.175.178.121"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS7
SET srvnumber=7
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS03 130.175.178.122 Solaris 11u1"
SET osserver="130.175.178.122"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS8
SET srvnumber=8
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS04 130.175.178.123 RHEL 5.10"
SET osserver="130.175.178.123"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS9
SET srvnumber=9
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS05 130.175.178.124 RHEL 6.3"
SET osserver="130.175.178.124"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS10
SET srvnumber=10
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS06 130.175.178.125 SUSE 10 SP4"
SET osserver="130.175.178.125"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS11
SET srvnumber=11
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS07 130.175.178.126 SUSE 11 SP3"
SET osserver="130.175.178.126"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS12
SET srvnumber=12
set passwrd=%passwrd2%
SET ossername="PNLVAMSMS08 130.175.178.233 RHEL 7.1"
SET osserver="130.175.178.233"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS13
SET srvnumber=13
set user="jz26tp"
set passwrd=xxxxxxxx
SET ossername="AIX from JH"
SET osserver="148.92.26.6"
rem CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS14
SET srvnumber=14
set user="root"
set passwrd=xxxxxxx
SET ossername="SunOS_130.175.59.122"
SET osserver="130.175.59.122"
rem CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS15
SET srvnumber=15
set user="root"
set passwrd=xxxxxxxx
SET ossername="SunOS_192.85.89.122"
SET osserver="192.85.89.122"
rem CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS16
SET srvnumber=16
set user="root"
set passwrd=xxxxxx
SET ossername="AIX_130.175.109.19"
SET osserver="130.175.109.19"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS17
SET srvnumber=17
set user="root"
set passwrd=xxxxxxxx
SET ossername="REDHAT_pnlvamsma09.getc.ssn.hpe.com"
SET osserver="130.175.178.16"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS18
SET srvnumber=18
set user="root"
set passwrd=xxxxxxx
SET ossername="oracle_130.175.85.98"
SET osserver="130.175.85.98"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

:startOS19
SET srvnumber=19
set user="nemec"
set passwrd=xxxxxxx
rem N3m3c123!
SET ossername="ec4t01167.itcs.entsvcs.net"
SET osserver="ec4t01167.itcs.entsvcs.net"
SET sudosu="sudo su - root -c "
SET sudosuYESorNO="YES"
CALL :doplink
IF NOT "%arg1%"=="all" GOTO endofthisfile

GOTO endofthisfile
:doplink
if "%arg2%"=="list" (
    echo -------------------------------------------------
    echo SERVER %srvnumber% : %ossername% = %osserver%
    echo -------------------------------------------------
    ping -n 1 %osserver%
    echo -------------------------------------------------
) else (
  if exist "%arg2%"  (
    echo *************************************************
    echo dir %arg2%
    echo.
    dir %arg2%
    plink %batch% -ssh -l %user% -pw %passwrd% %osserver%  rm -rf /tmp/%arg2%
    echo *************************************************
    pscp  -l %user% -pw %passwrd%   %arg2%  %osserver%:/tmp
    plink %batch% -ssh -l %user% -pw %passwrd% %osserver% chmod +x /tmp/%arg2%
    echo *************************************************
    echo SERVER %srvnumber% : %ossername% = %osserver%
    echo uname -a :
    plink %batch% -ssh -l %user% -pw %passwrd% %osserver%  uname -a
    echo *************************************************
    if %sudosuYESorNO%=="NO" (
      plink %batch% -ssh -l %user% -pw %passwrd% %osserver% /tmp/%arg2%  %restofparameters% ; echo EXITCODE=$?
    ) else (
      plink %batch% -ssh -l %user% -pw %passwrd% %osserver% %sudosu% '/tmp/%arg2%  %restofparameters% ; echo EXITCODE=$? '
    )
    echo *************************************************
    if %deleteFile%=="YES" (
      plink %batch% -ssh -l %user% -pw %passwrd% %osserver%  rm -rf /tmp/%arg2%
    )
    echo *************************************************
    echo.
    echo.
    echo.
  ) else (
    rem run command like OS command ls -l
    echo =================================================
    echo SERVER %srvnumber% : %ossername% = %osserver%
    echo cmd      : %arg2% %restofparameters%
    echo uname -a :
    plink %batch% -ssh -l %user% -pw %passwrd% %osserver%  uname -a
    echo =================================================
    if %sudosuYESorNO%=="NO" (
      plink %batch% -ssh -l %user% -pw %passwrd% %osserver% %arg2%  %restofparameters% ; echo EXITCODE=$?
    ) else (
      plink %batch% -ssh -l %user% -pw %passwrd% %osserver% %sudosu% '%arg2%  %restofparameters% ; echo EXITCODE=$? '
    )

    rem plink %batch% -ssh -l %user% -pw %passwrd% %osserver% %sudosu% '%arg2% %restofparameters% ; echo EXITCODE=$?  '
    echo =================================================
    echo.
  )
)
exit /b
GOTO endofthisfile


:gethelp
echo 1st parameter       is OS/server to select - all,1,2,3,4 
echo 2nd parameter       is ksh script file , keyword 'list' prints only name of server
echo 3rd..X parameters   are linux scripts arguments
echo (btw - install putty and set path variable)



:endofthisfile
