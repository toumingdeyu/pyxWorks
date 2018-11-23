import requests

def dictionaryRecursivePrint(d,depth=0):
  if isinstance(d,dict):
    for k,v in d.items():
      if isinstance(v, dict):
        print(' '*4*depth + ("%s:" % k))
        dictionaryRecursivePrint(v,depth+1)
      else:
        print(' '*4*depth + "%s: %s" % (k, v) )


response = requests.get('http://127.0.0.1/')
print(response.status_code)
print('-'*80)
print(response.headers)
if response.status_code != 200:
  raise ApiError('GET /tasks/ {}'.format(response.status_code))
print('-'*80)
print(response.text)
print('-'*80)
print(response.json())
print('-'*80)
dictionaryRecursivePrint(response.json())






