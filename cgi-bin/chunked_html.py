#!/usr/bin/python
import time
import sys

def print_chunk(msg=""):
    sys.stdout.write("\r\n%X\r\n%s" % (len(msg), msg))
    sys.stdout.flush()


sys.stdout.write("Transfer-Encoding: chunked\r\n")
sys.stdout.write("Content-Type: text/html\r\n")
print_chunk("\r\n\r\n<html><head><title>%s</title></head><body>" % ('No submit'))

for i in range(0,100):
    time.sleep(0.1)
    print_chunk("<h1>%s<br/></h1>" % (i))
    print_chunk("%s" % (70*"="))

print_chunk("</body></html>")