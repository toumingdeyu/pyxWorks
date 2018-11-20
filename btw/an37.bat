@echo off
REM Quick and easy way how to set desired python version/distribution 
REM only for the current cmd session without influencing of other python versions
REM WARNING/SideEffect: Do not set any prefered python paths into system variables permanently, because first-one found is used.
REM That is reason because our path is first. Setting is temporary forcurrent session.
REM Please locate such BAT files for more versions into Folter which is in permanent PATH.
set PYTHONPATH=c:\Anaconda3\;c:\Anaconda3\Scripts
REM ECHO %PATH% | FIND /I "%PYTHONPATH%" >Nul && ( Echo Path is already set. ) || ( set PATH=%PYTHONPATH%;%PATH% )
set PATH=%PYTHONPATH%;%PATH%
@echo on
echo %PATH%
python --version
@echo off