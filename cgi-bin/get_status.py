#!/usr/bin/python

import sys, os, io
import cgi
import cgitb; cgitb.enable()

if __name__ != "__main__": sys.exit(0)

#print("Status: %s %s\r\n" % ('222',"afafff"))
print("Content-type:text/html; charset=utf-8")
print("Status: %s %s\r\n" % ('222',"afafff"))
#print("Retry-After: 300")
print("\r\n\r\n")
print("<html><head><title>%s</title></head><body>" % ('TITLE'))
print("text body...")
print("</body></html>")


