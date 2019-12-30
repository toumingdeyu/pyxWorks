### https://serverfault.com/questions/594298/iis-wont-let-python-script-set-headers
### https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
import sys, os

RELOAD_BUTTON = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""
PAGE_TITLE = 'PID' + str(os.getpid())

print('HTTP/1.1 Status: 200 OK\nContent-type: text/html; charset=utf-8\n\n')
print('<!DOCTYPE html><HTML><HEAD><TITLE>%s</TITLE></HEAD>' % (PAGE_TITLE))
print('<BODY>')

print('<H1>H1</H1>')
print('<p>') 
print('text')
print('<br>')

print(RELOAD_BUTTON)

print('</BODY></HTML>')
