import requests
import sys

url='https://www.yr.no/place/Slovakia/Bratislava/Bratislava/hour_by_hour.html'
response=requests.get(url)
#print(response.text)
for table in response.text.split('<table')[1:]:
  for tr in table.split('<tr>'):
    line=[]
    for i,td in enumerate(tr.split('<td')):
      column=td.splitlines()[0].split('For the period')[0].split(',')[0].replace('::',':')
      for j in ['<','>','/','strong','td','"','class','scope','title','=','row','.','precipitation','temperature','txt-left','plus']:
        column=column.replace(j,'')
      line.append(column.strip()) if column.strip() else None
    print("{:<10} {:<6} {:<15} {:<40} {:<23} {:<15}".format(line[0].split()[0],line[0].split()[1], line[1], line[2], line[3], line[4])) if len(line)>3 else None
