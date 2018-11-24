import requests
import json
import sys

url='http://127.0.0.1/lang'

if len(sys.argv)>1: value=sys.argv[1]
else:               value='some_language'
print(url)
response = requests.post(url, json={"name" : value})
print(response.status_code)





