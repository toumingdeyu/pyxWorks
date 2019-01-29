def get_variables():
  import json
  variables={}
  with open('json_var.json') as json_file:
    variables = json.load(json_file)
  return variables


