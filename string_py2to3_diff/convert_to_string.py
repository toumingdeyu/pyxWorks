#!/usr/bin/python

import sys, os, io, six, collections, json, yaml
import optparse


def convert_to_string(text = None):
    result_str = str()
    try:
        if isinstance(text, (bytes, bytearray)): result_str = text.decode("utf-8")
    except: pass
    try:
        if isinstance(text, (unicode)): result_str = text.encode("ascii")
    except: pass
    try:
        if isinstance(result_str, (unicode)): result_str = result_str.encode("ascii")
    except: pass

    print("TYPE[%20s] = '%25s' TO TYPE[%20s] = '%25s'" % (type(x),x,type(result_str),result_str) )
    return result_str


################################################################################
data = collections.OrderedDict()

################################################################################

if __name__ != "__main__": sys.exit(0)
print('python[%s]' % (sys.version.split()[0]))

print('\nsix.string_types = %s\n' % (str(six.string_types)))

x = bytearray('bytearray(str,"utf-8")', 'utf-8')
convert_to_string(x)

x = b'b'
convert_to_string(x)

x = b'b.decode("utf-8")'.decode('utf-8')
convert_to_string(x)

x = r'r'
convert_to_string(x)

x = u'u'
convert_to_string(x)

x = six.b('six.b(str)')
convert_to_string(x)

x = six.u('six.u(str)')
convert_to_string(x)

x = six.unichr(99)
convert_to_string(x)

print('\n')

try:
    x = str()
    x = bytearray('bytearray(str,"utf-8").ascii()', 'utf-8').ascii()
    convert_to_string(x)
except Exception as e: print("PROBLEM[%45s] = '%s'" % (str(e), "bytearray(str,'utf-8').ascii()"))

try:
    x = str()
    x = u'u.ascii()'.ascii()
    convert_to_string(x)
except Exception as e: print("PROBLEM[%45s] = '%s'" % (str(e),str(x)))

try:
    x = str()
    x = u'u.decode("utf-8")'.decode("utf-8")
    convert_to_string(x)
except Exception as e: print("PROBLEM[%45s] = '%s'" % (str(e),str(x)))

try:
    x = str()
    x = bytearray('bytearray(str,"utf-8").decode("utf-8")', 'utf-8').decode("utf-8")
    convert_to_string(x)
except Exception as e: print("PROBLEM[%45s] = '%s'" % (str(e),str(x)))

print('\n')

### TypeError: Object of type bytes is not JSON serializable
data['bytearray(str,"utf-8")'] = bytearray('bytearray(str,"utf-8")', 'utf-8')
try: print(json.dumps(data, indent=4))
except Exception as e: print(str(data['bytearray(str,"utf-8")']) + '\tPROBLEM[' + str(e) + ']')