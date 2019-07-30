#!/usr/bin/python

import sys
import collections
import cgi
import cgitb; cgitb.enable()


def read_cgibin_get_post_form():
    # import collections, cgi
    # import cgitb; cgitb.enable()
    data, submit_form = collections.OrderedDict(), None
    form = cgi.FieldStorage()
    for key in form.keys():
        variable = str(key)
        try: value = str(form.getvalue(variable))
        except: value = str(','.join(form.getlist(name)))
        if variable and value and variable != "submit": data[variable] = value
        if variable == "submit": submit_form = value
    return data, submit_form


def print_html_data(data):
    print("Content-type:text/html\r\n\r\n")
    print "<html>"
    print "<head>"
    print "<title>DATA</title>"
    print "</head>"
    print "<body>"
    for key, value in data.items(): print "<h2>%s : %s</h2>" % (str(key), str(value))
    print "</body>"
    print "</html>"



if __name__ != "__main__": sys.exit(0)


data, submit_form = read_cgibin_get_post_form()
print_html_data(data)

### http://127.0.0.1/cgi-bin/cgi-bin_example.py?name=Joe+Blow&addr=At+Home
### https://iptac1.apps.ocn.infra.ftgroup/cgi-bin/cgi-bin_example?name=Joe+Blow&addr=At+Home
