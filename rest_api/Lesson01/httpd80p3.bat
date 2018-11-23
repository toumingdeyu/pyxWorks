@echo on
REM to run httpserver on background add on end "&"
call py37.bat
call python -m http.server 80
