#!/usr/bin/python

import sys, os, io, time, subprocess

output = str()
if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
    ### https://gist.github.com/lopes/168c9d74b988391e702aac5f4aa69e41 ###
    output = subprocess.check_output('python -m pip install PyCryptodome', stderr= subprocess.STDOUT)

elif sys.version_info.major == 2:
    if os.name == 'nt':
        output = subprocess.check_output('easy_install http://www.voidspace.org.uk/downloads/pycrypto26/pycrypto-2.6.win-amd64-py2.7.exe', stderr= subprocess.STDOUT)
    else:
        output = subprocess.check_output('pip install pycrypto', stderr= subprocess.STDOUT)

print(output)

