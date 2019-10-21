#!/usr/bin/python
import time
import sys

def chunk(msg=""):
    return "\r\n%X\r\n%s" % ( len( msg ) , msg )

sys.stdout.write("Transfer-Encoding: chunked\r\n")
sys.stdout.write("Content-Type: text/html\r\n")

for i in range(0,1000):
    time.sleep(1)
    sys.stdout.write( chunk( "%s\n" % ( i ) ) )
    sys.stdout.flush()

sys.stdout.write(chunk() + '\r\n')