#!/usr/bin/python
import time
import sys

def chunk(msg=""):
    return "\r\n%X\r\n%s" % ( len( msg ) , msg )

sys.stdout.write("Transfer-Encoding: chunked\r\n")
sys.stdout.write("Content-Type: text/html\r\n")
sys.stdout.write(chunk("\r\n\r\n<html><head><title>%s</title></head><body>" % ('No submit')))

for i in range(0,10):
    time.sleep(1)
    sys.stdout.write( chunk( "%s<br/>" % ( i ) ) )
    sys.stdout.flush()

sys.stdout.write(chunk("</body></html>" % ('No submit')))