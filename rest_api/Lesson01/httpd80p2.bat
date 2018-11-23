@echo on
REM to run httpserver on background add on end "&"
call py27.bat
call python -m SimpleHTTPServer 80
