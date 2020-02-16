### https://docs.microsoft.com/en-us/iis/configuration/system.webserver/cgi
### https://docs.microsoft.com/en-us/iis/configuration/system.webserver/fastcgi/index
### https://serverfault.com/questions/594298/iis-wont-let-python-script-set-headers
### https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
import sys, os

RELOAD_BUTTON = """<input type="button" value="Reload Page" onClick="document.location.reload(true)">"""
PAGE_TITLE = 'PID' + str(os.getpid())

CSS_STYLE = """
body {
  background-color: gray;
}

h1 {
  color: blue;
  text-align: center;
}

p {
  font-family: verdana;
  font-size: 20px;
}
"""


print('HTTP/1.1 Status: 200 OK\nContent-type: text/html; charset=utf-8\n\n')
print('<!DOCTYPE html><HTML><HEAD><TITLE>%s</TITLE><STYLE>%s</STYLE></HEAD>' % (PAGE_TITLE, CSS_STYLE))
print('<BODY>')

print('<H1>H1</H1>')
print('<p>') 
print('text')
print('<br>')
print('<br>')
print("""
<iframe src="win_cgi_test.py" width="90%" height="70%" scrolling="yes">
aaa
</iframe>
""")
print('<br>')
print(RELOAD_BUTTON)
print('</BODY></HTML>')
