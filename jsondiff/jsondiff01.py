import json
import jsondiff

json1 = json.loads(
    '{"isDynamic": false, "name": "", "value": "SID:<sid>", "description": "instance","argsOrder": 1,"isMultiSelect": false}')

json2 = json.loads(
    '{ "name": "", "value": "aSID:<sid>","isDynamic": false, "description": "instance","argsOrder": 1,"isMultiSelect": false}')

res = jsondiff.diff(json1, json2)
if res:
    print("Diff found")
    print(res)
else:
    print("Same")