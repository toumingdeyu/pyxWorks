#!/usr/bin/python
import paramiko, sys, os, argparse
import forward
# 'pip install forward'

try:    PASSWORD        = os.environ['NEWR_PASS']
except: PASSWORD        = str()
try:    USERNAME        = os.environ['NEWR_USER']
except: USERNAME        = str()



##############################################################################
#
# BEGIN MAIN
#
##############################################################################

if __name__ != "__main__": sys.exit(0)

######## Parse program arguments #########
parser = argparse.ArgumentParser(
                description = "",
                epilog = "e.g: \n")

parser.add_argument("--rhost",
                    action = "store", dest = 'rhost',
                    default = None,
                    help = "remote host:port")
parser.add_argument("--lport",
                    action = "store", dest = 'lport',
                    default = '',
                    help = "local port")
parser.add_argument("--sshhost",
                    action = "store", dest = 'sshhost',
                    default = None,
                    help = "ssh host:port")
parser.add_argument("--user",
                    action = "store", dest = 'username', default = None,
                    help = "specify user login")
parser.add_argument("--pass",
                    action = "store", dest = 'password', default = None,
                    help = "specify user password")
args = parser.parse_args()

####### Set USERNAME if needed
if args.username: USERNAME = args.username
if not USERNAME:
    print(" ... Please insert your username by cmdline switch --user username !" )
    sys.exit(0)

# SSH (default)
if not PASSWORD:
    if args.password: PASSWORD = args.password
    else:             PASSWORD = getpass.getpass("TACACS password: ")


try: remote_host = args.rhost.split(':')[0]
except: remote_host = None
try: remote_port = args.rhost.split(':')[1]
except: remote_port = '22'

try: local_port = args.lport.split(':')[1]
except: local_port = '22'

try: ssh_host = args.sshhost.split(':')[0]
except: ssh_host = None
try: ssh_port = args.sshhost.split(':')[1]
except: ssh_port = '22'

print("RHOST = '%s:%s', SSHHOST = '%s:%s', LPORT = '%s'"%(remote_host,remote_port,ssh_host,ssh_port,local_port))

if remote_host and ssh_host:
    transport = paramiko.Transport((ssh_host, int(ssh_port)))
    transport.connect(hostkey = None, username = USERNAME, password = PASSWORD, pkey = None)

    try:
        forward.forward_tunnel(local_port, remote_host, remote_port, transport)
    except KeyboardInterrupt:
        print 'Port forwarding stopped.'
        sys.exit(0)
else: print("No port forwarding...")

