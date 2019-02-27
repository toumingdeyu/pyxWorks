"# peteneme's nso-mix learning sub-github..."

Sub-xml parser utility:
========================

SYNTAX:
======= 
python get_subxml.py nameOfInputFile.json json_key xml_value/- k/v(= get key/value)

NOTE:
===== 
-When v/value parameter is inserted , value is written only to screen and file is not created.

FOR EXAMPLE:
============

GET config subjson from json:
=============================
python get_subxml.py file.xml config

python get_subxml.py file.xml config -

python get_subxml.py file.xml config - k


GET hostname value from json:
=============================
python get_subxml.py file.xml hostname - v




