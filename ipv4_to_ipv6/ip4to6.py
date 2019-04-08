#!/usr/bin/python
import os, sys

def ipv4_to_ipv6(ipv4address):
    ip4to6, ip6to4 = str(), str()
    try: v4list = ipv4address.split('/')[0].split('.')
    except: v4list = []
    if len(v4list) == 4:
        try:
            if int(v4list[0])<256 and int(v4list[1])<256 and int(v4list[2])<256 \
                and int(v4list[3])<256 and int(v4list[0])>=0 and \
                int(v4list[1])>=0 and int(v4list[2])>=0 and int(v4list[3])>=0:
                ip4to6 = '0:0:0:0:0:FFFF:%02X%02X:%02X%02X' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
                ip6to4 = '2002:%02x%02x:%02x%02x:0:0:0:0:0' % \
                    (int(v4list[0]),int(v4list[1]),int(v4list[2]),int(v4list[3]))
        except: pass
    return ip4to6, ip6to4

ipv4list = ['1.1.1.1','2.2.2.2','1.2.3.4','255.255.255.255','172.25.4.65']

for ipv4 in ipv4list:
    print(ipv4_to_ipv6(ipv4))
exit(0)