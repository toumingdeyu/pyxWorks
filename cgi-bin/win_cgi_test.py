### https://serverfault.com/questions/594298/iis-wont-let-python-script-set-headers
### https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
import sys

sys.stdout.write('HTTP/1.1 Status: 200 OK\nContent-type: text/html\n\n')
#sys.stdout.write('HTTP/1.1 Status: 200 OK\nContent-type: text/plain\nTransfer-Encoding: chunked\n\n')
#print('HTTP/1.1 Status: 200 OK')
#print('Content-type: text/html')
#print()

print('<HTML><HEAD><TITLE>Python Sample CGI</TITLE></HEAD>')
print('<BODY>')
print('<H1>This is a header</H1>')

print('<p>') #this is a comment
print('this is just like most other HTML')
print('<br>')
print('</BODY>')