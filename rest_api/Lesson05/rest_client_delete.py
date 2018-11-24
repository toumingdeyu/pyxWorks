import requests
import json
import sys

url='http://127.0.0.1/lang/python'

if len(sys.argv)>1: value=sys.argv[1]
else:               value='some_language'
print(url)
response = requests.delete(url)
print(response.status_code)





