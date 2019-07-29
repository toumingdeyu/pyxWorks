#!/usr/bin/env python
import sys
import collections
import cgi
import cgitb; cgitb.enable()

sys.stderr = sys.stdout
print("Content-type:text/html\r\n\r\n")
#print("Content-Type: text/plain")



def read_cgibin_post_form(debug = None):
    # import collections
    # import cgi
    # import cgitb; cgitb.enable()
    data = collections.OrderedDict()
    form = cgi.FieldStorage()
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable and value: data[variable] = value
        if debug: print('%s:%s'%(variable,value))
    return data


if __name__ != "__main__": sys.exit(0)

print "<html>"
print "<head>"
print "<title>READ_FORM:</title>"
print "</head>"
print "<body>"
data = read_cgibin_post_form()
for key, value in data.items(): print "<h2>%s : %s</h2>" % (key, value)
print "</body>"
print "</html>"

### http://127.0.0.1/cgi-bin/cgi-bin_example.py?name=Joe+Blow&addr=At+Home
### https://iptac1.apps.ocn.infra.ftgroup/cgi-bin/cgi-bin_example?name=Joe+Blow&addr=At+Home