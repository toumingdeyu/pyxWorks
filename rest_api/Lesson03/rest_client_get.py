import requests
import json
import sys

if len(sys.argv)>1: url=sys.argv[1]
else:               url='http://127.0.0.1/'
print(url)
response = requests.get(url)
if response.status_code != 200: raise ApiError('GET /tasks/ {}'.format(response.status_code))
print('-'*80)
print(response.text)
print('-'*80)
print(response.json())
print('-'*80)
print(json.dumps(response.json(), indent=8))
print('-'*80)




