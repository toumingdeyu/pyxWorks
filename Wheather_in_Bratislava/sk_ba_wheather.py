import requests
import sys

url='https://www.yr.no/place/Slovakia/Bratislava/Bratislava/hour_by_hour.html'
response=requests.get(url)
for table in response.text.split('<table')[1:]:
  for tr in table.split('<tr>'):
    line=[]
    for i,td in enumerate(tr.split('<td')):
      column=td.splitlines()[0].split('For the period')[0].split(',')[0].replace('::',':')
      for j in ['<','>','/','strong','td','"','class','scope','title','=','row','precipitation','Precipitation:','Temperature:','Wind:','temperature','txt-left','plus']:
        column=column.replace(j,'')
      line.append(column.strip()) if column.strip() else None
    print("{:<10} {:<7} {:<18} {:<10} {:<30} {:<15}".format(line[0].split()[0],line[0].split()[1], line[1].replace('.',''), line[3].replace('m.','m'), line[2].replace('.',''), line[4])) if len(line)>3 else None
