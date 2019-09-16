#!/usr/bin/python
import sys
import os
import io
import optparse
import json
import yaml
import collections
import six



def tprint(x):
    print('%s\t TYPE:%s'%(x,type(x)))
################################################################################
data = collections.OrderedDict()

################################################################################

if __name__ != "__main__": sys.exit(0)
print(sys.version)
print(six.string_types)
print('\n')

x = bytearray('bytearray(str,"utf-8")', 'utf-8')
tprint(x)

x = b'b'
tprint(x)

x = b'b.decode("utf-8")'.decode('utf-8')
tprint(x)

x = r'r'
tprint(x)

x = u'u'
tprint(x)

x = six.b('six.b(str)')
tprint(x)

x = six.u('six.u(str)')
tprint(x)

x = six.unichr(99)
tprint(x)

print('\n')

### TypeError: Object of type bytes is not JSON serializable
data['bytearray(str,"utf-8")'] = bytearray('bytearray(str,"utf-8")', 'utf-8')
try: print(json.dumps(data, indent=4))
except Exception as e: print('PROBLEM[' + str(e) + ']')