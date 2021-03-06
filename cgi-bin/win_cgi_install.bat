rem https://docs.microsoft.com/en-us/iis/configuration/system.webserver/cgi
@echo on
echo %cd%

REM - ENABLE IIS_CGI
call dism /online /enable-feature /featurename:IIS-CGI

REM - CGI DEFAULT SETTINGS
rem c:\Windows\System32\inetsrv\appcmd.exe
call c:\Windows\System32\inetsrv\appcmd.exe set CONFIG "Default Web Site" -section:system.webServer/cgi /createCGIWithNewConsole:"True" /commit:apphost
call c:\Windows\System32\inetsrv\appcmd.exe set CONFIG "Default Web Site" -section:system.webServer/cgi /createProcessAsUser:"False" /commit:apphost
call c:\Windows\System32\inetsrv\appcmd.exe set CONFIG "Default Web Site" -section:system.webServer/cgi /timeout:"00:20:00" /commit:apphost

REM - ADD CGI HANDLER - SPACE IS NEEDED %u0020
call c:\Windows\System32\inetsrv\appcmd.exe set config /section:system.webServer/handlers /+[name='cgi-py',path='*.py',verb='*',modules='CgiModule',scriptProcessor='C:\python38\python.exe%u0020%s%u0020%s',resourceType='File',requireAccess='Script']

REM - INSTALL IIS6 COMPATIBILITY
rem IIS 6 Management Compatibility:IIS6 scripting Tools, IIS 6 Management Compatibility:IIS6 WMI compatibility
call cscript C:\inetpub\AdminScripts\adsutil.vbs set /W3SVC/AspEnableChunkedEncoding "TRUE"

REM - DISABLE HTTP2
rem HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\HTTP\Parameters
rem EnableHttp2Tls REG_DWORD 0
rem EnableHttp2Cleartext REG_DWORD 0
call REG ADD HKLM\System\CurrentControlSet\Services\HTTP\Parameters /v EnableHttp2Tls /t REG_DWORD /d 0
call REG ADD HKLM\System\CurrentControlSet\Services\HTTP\Parameters /v EnableHttp2Cleartext /t REG_DWORD /d 0

@echo on
cd C:\inetpub\AdminScripts
call cscript adsutil.vbs set /W3SVC/AspEnableChunkedEncoding "TRUE"





rem call c:\windows\system32\inetsrv\iis.msc
rem echo How-to:
rem echo https://docs.microsoft.com/en-us/iis/configuration/system.webserver/fastcgi/index
rem echo open Handler Mappings, add Script Map,
rem echo Reguest path: *.py, Executable: C:\python38\python.exe %s %s, Name: some_name

rem <add name="cc" path="*.py" verb="*" modules="CgiModule" scriptProcessor="C:\python38\python.exe %s %s" resourceType="File" requireAccess="Script" />
rem call c:\Windows\System32\inetsrv\appcmd.exe list config /section:system.webServer/handlers
rem call c:\Windows\System32\inetsrv\appcmd.exe set config /section:system.webServer/handlers /+[name=cgi-py',path='*.py',verb='*',modules="CgiModule",scriptProcessor="C:\python38\python.exe %s %s",resourceType="File" requireAccess="Script"]
rem call c:\Windows\System32\inetsrv\appcmd.exe set config /section:system.webServer/handlers /+[@end,name='cgi-py',path='*.py',verb='*',modules='CgiModule',scriptProcessor='C:\python38\python.exe %s %s',resourceType='File',requireAccess='Script']

rem c:\Windows\System32\inetsrv\appcmd.exe set config /section:system.webServer/handlers /+[name='cgi-py',path='*.py',verb='*',modules='CgiModule',scriptProcessor='C:\python38\python.exe',resourceType='File',requireAccess='Script']



REM FAST-CGI
rem call c:\Windows\System32\inetsrv\appcmd.exe set config -section:system.webServer/fastCgi /+"[fullPath='c:\php\php-cgi.exe']" /commit:apphost
rem call c:\Windows\System32\inetsrv\appcmd.exe set config "Contoso" -section:system.webServer/handlers /+"[name='PHP-FastCGI',path='*.php',verb='GET,HEAD,POST',modules='FastCgiModule',scriptProcessor='c:\php\php-cgi.exe',resourceType='Either']"

