#!/usr/bin/python
import sys, os, io, subprocess

### DO FORCE INSTALL OF REQUIRED PACKAGES, IGNORE ERRORS ######################
packages_string = """
flask
django
mako
jinja2
json
collections
six
cgi
cgitb
argparse
optparse
difflib
socket
reguests
html
copy
getpass
re
paramiko
esptool
netmiko
getopt
platform
yaml
optparse
xmltodict
xml.etree
xml.dom.minidom
bs4
ncclient
psutils
lxml
napalm
pysnmp.hlapi
telnetlib
subprocess
getopt
reguests3
urllib3
mysql.connector
pymysql
pandas
numpy
matplotlib.pyplot
cerberus
dynamic
pexpect
matplotlib
mpld3
"""

### MAIN ######################################################################
if __name__ != "__main__": sys.exit(0)

command = "python -m pip install --upgrade pip"
print("\nCOMMAND: " + command)
results = subprocess.check_output(command, shell=True).decode('UTF-8')
print(results)

for package in packages_string.splitlines():
    command = "pip install --no-cache-dir --no-color %s" % (package)
    print("\nCOMMAND: " + command)
    if package.strip():
        try:
            results = subprocess.check_output(command, shell=True).decode('UTF-8')
            print(results)
        except: pass

command = "pip list"
print("\nCOMMAND: " + command)
results = subprocess.check_output(command, shell=True).decode('UTF-8')
print(results)

command = "python --version"
print("\nCOMMAND: " + command)
results = subprocess.check_output(command, shell=True).decode('UTF-8')
print(results)