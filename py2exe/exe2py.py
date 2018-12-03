#!/usr/bin/python
import optparse
def bin2data(binaryfile,pythonfile,dataname):
  try:
    infile = open(binaryfile, 'rb')
    outfile = open(pythonfile, 'w')
  except:
    print ('Exception!')
    exit(0)
  line = ''
  firstline = True
  outfile.write('#!/usr/bin/python\nimport optparse\n')
  while True:
    inbyte = infile.read(1)
    if not inbyte:
      if len(line) > 0:
        outfile.write("%s)\n" % line)
      break
    if len(line) == 0:
      if firstline:
        line = line + '%s=(' % dataname
        firstline=False
      else:
        line = line + '  '
    elif len(line) > 0:
      line = line + ','
    line = line + "%d" % ord(inbyte)
    if len(line) > 75:
      outfile.write("%s,\n" % line)
      line = ''

  outfile.write("\ndef data2bin(binaryfile,dataname):\n")
  outfile.write("  outfile = open(binaryfile, 'wb')\n")
  outfile.write("  for item in dataname: \n")
  outfile.write("    outfile.write(chr(item))\n")
  outfile.write("  outfile.close()\n")
  outfile.write('parser = optparse.OptionParser(usage="python py2exe.py file.exe", version="%prog 0.1")\n')
  outfile.write('(options, args) = parser.parse_args()\n')
  outfile.write('if len(args) == 1:\n')
  outfile.write('  binaryfile=args[0]\n')
  outfile.write("  data2bin(binaryfile,%s)\n" % dataname)

  infile.close()
  outfile.close()

def data2bin(binaryfile,dataname):
  outfile = open(binaryfile, 'wb')
  for item in dataname:
    outfile.write(chr(item))
  outfile.close()

parser = optparse.OptionParser(usage="usage: python exe2py.py file.exe", version="%prog 0.1")
(options, args) = parser.parse_args()
if len(args) == 1:
  binaryfile=args[0]
  bin2data(binaryfile,"py2exe.py","Data")
else:
  parser.print_help()



