#!/usr/bin/env python
import cgi
import cgitb
cgitb.enable()

form = cgi.FieldStorage()
for key in form.keys():
    variable = str(key)
    try: value = str(form.getvalue(variable))
    except: value = str(','.join(form.getlist(name)))
    print('%s:%s'%(variable,value))

#print("Content-Type: text/plain")