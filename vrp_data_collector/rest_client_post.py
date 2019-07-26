#!/usr/bin/env python
#!/usr/bin/python

import requests
import json
import sys, os

url='http://127.0.0.1:8880/'

if len(sys.argv)>1: url = url + str(sys.argv[1])

print(url)

response = requests.post(url, json={"XXX" : "YYY", "AAA" : "BBB"})
print(response.status_code)
print('-'*80)
try: print(json.dumps(response.json(), indent=2))
except: print("JSON format not detected, so printing text:\n%s\n"%(str(response.text)))
print('-'*80)





