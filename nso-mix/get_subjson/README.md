"# peteneme's nso-mix learning sub-github..."

Sub-json parser utility:

SYNTAX: python get_subjson.py nameOfInputFile.json json_key json_value/- k/v(= get key/value)

NOTE: 
-When v/value parameter is inserted , value is written only to screen and file is not created.

FOR EXAMPLE:

GET config subjson from json:
=============================
python get_subjson.py file.json config
python get_subjson.py file.json config -
python get_subjson.py file.json config - k


GET hostname value from json:
=====================================
python get_subjson.py file.json hostname - v




