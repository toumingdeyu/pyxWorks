@echo on
echo %cd%
dism /online /enable-feature /featurename:IIS-CGI
c:\windows\system32\inetsrv\iis.msc
echo open Handler Mappings, add Script Map, 
echo Reguest path: *.py, Executable: C:\python37\python.exe %s %s, Name: some_name
