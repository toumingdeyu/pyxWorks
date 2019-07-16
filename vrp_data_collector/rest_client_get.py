﻿import requests
import json
import sys

if len(sys.argv)>1: url='http://127.0.0.1:8080/'+sys.argv[1]
else:               url='http://127.0.0.1:8080/'
print(url)
response = requests.get(url)
if response.status_code != 200: raise ApiError('GET /tasks/ {}'.format(response.status_code))
print('-'*80)
try: print(json.dumps(response.json(), indent=2))
except: print("JSON format not detected, so printing text:\n%s\n"%(str(response.text)))
print('-'*80)





