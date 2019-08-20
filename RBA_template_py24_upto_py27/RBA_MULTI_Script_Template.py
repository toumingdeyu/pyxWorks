#!/opt/opsware/agent/bin/python
##DEVMESH windows ...py.bat 1st line is @setlocal..., devmesh unix ...py.ksh let it be as it is
##@setlocal enabledelayedexpansion && "C:\Program Files\Opsware\agent\lcpython15\python" -x "%~f0" %* & exit /b
#
##########
# NAME: <Script Name>
# UCID: <XXXX>
#
# PURPOSE: <Purpose Description>
#
# TARGET OS(s): (Example: Solaris(5.8 - 5.11), HP-UX(10.20 - 11.31), AIX(4.3 - 7.X), Suse(10.20 - 11.X), Redhat(4.X - 7.X), Oracle, Windows(2003 - 2012) )
#
# INPUT: (Expected Input)
#
# OUTPUT: Standard RBA output
#
# Original Author(s): <Author(s) Name>
# Additional Author(s): <Author(s) Name>
##########
#
#######################################################################################
#                                                                                     #
# (c) Copyright 2017 DXC Technology                                                   #
#                                                                                     #
# Information contained in this document is proprietary and confidential to           #
# DXC Technology and may not be disclosed to any third  party without prior           #
# written consent from DXC Technology                                                 #
#                                                                                     #
#######################################################################################

#
##### MODIFICATION HISTORY:
# MONTH(3 characters only, Mar, Apr, etc.) DAY(XX) YEAR(XXXX) VERSION(X.X.X Major.Minor.Bug notation) Author Name
#   - Modification Information
#
##### End History #####
#
##### Initial python version check. DO NOT MODIFY!!!
import sys
import string

def Python_Version_Error():
  print("RBA script stdout\n")
  print("WFAN=\"")
  print("Python version must be 2.4.4 or greater, but less than 3.x")
  try:
    print("Actually used version is: %s.%s.%s" % (sys.version_info[0],sys.version_info[1] ,sys.version_info[2]))
  except:
    #python<2.0 does not know sys.version_info , so we print older sys.version
    print("Actually used version is: %s" % str(sys.version))
  print("\"")
  print("RBA categorized")
  sys.exit(0)

try:
  PythonVersion=sys.version_info
  
except:
  Python_Version_Error()

if PythonVersion < (2, 4, 4) or PythonVersion > (3, 0):
  Python_Version_Error()

##### Global defined modules
# Only import one module per line. DO NOT MODIFY!!!
import os
import optparse
import fileinput
import glob
import datetime
import time
import socket
import platform
import stat
import subprocess
import re
import pdb
import errno
import signal

def Windows_Not_Supported():
  print("RBA script stdout\n")
  print("WFAN=\"")
  print("OS Windows is not supported!")
  print("\"")
  print("RBA categorized")
  sys.exit(0)

### Easy to make Unix only python script by modules pwd, grp which does not exists under windows
# try:
#  import pwd
# except:
#  Windows_Not_Supported()
#
# try:
#  import grp
# except:
#  Windows_Not_Supported()

# Use this area for additional module imports. Only import one module per line

##### Define global variables
ScriptVersion="0.0.0"
TemplateVersion="2.3.0"
ScriptName=sys.argv[0]
Hostname=socket.gethostname()
SystemPlatform=platform.system()
SystemVersion=platform.release()
PY3 = sys.version_info[0] == 3

if PY3:
    StringType = str
else:
    StringType = basestring

#global timeout for script , script will end if runs longer than TIMEOUT
###SCRIPT SPECIAL VARIABLES
gTimeoutMinutes=15


##### Define primary description, for use by option/argument handling
OptionDescription="This script is not designed to be run from the command line. RBA USE ONLY!!!"

##### Change script priority - Sets the script priority to a higher number, as this will try to mitgate any impact the script has on the performance of the server.
# Work in Progress

##### Global defined functions - All functions that interact with multiple tests or functions should go here
Divider0="+++++"
Divider1="~~~~~"
Divider2=" "
Divider3="-->"
Divider4="<--"

def Permissions_Calculator(Input):
### Return permissions in a 4 digit octal format, including sticky bit
  InputObjectPermissionValue=str(oct(stat.S_IMODE(os.stat(Input).st_mode)))
  return InputObjectPermissionValue[-4:]

def Port_Connectivity_Check(TargetHostIP, TargetHostPortNumber):
### Tests whether a port is open on the target system. Uses normal routing table for network adapter used
  SocketTest=socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  try:
    SocketTest.connect((TargetHostIP, int(TargetHostPortNumber)))
    SocketTest.shutdown(2)
    return True

  except:
    return False

### FUNCTION Is_Os_Windows - returns True if OS is Windows ###
def Is_Os_Windows():
  #python 2.4 has a bug - platform.release()='Windows' instead of platform.system()='Windows'
  if SystemPlatform in ['Windows','Microsoft']:
    return True

  else:
    return False

### FUNCTION Environment_Setup - PATH environment extention , use it for not standard installations###
### i.e. Windows  PathExtentionStringPathExtentionString="%ovinstalldir%\\bin\\win64\\opcagt.bat;%ovistalldir%\\bin\\opcagt.bat"
### i.e. UNIX     PathExtentionString="/opt/OV/bin/OpC;/opt/OV/bin;/opt/Ov/bin;/usr/lpp/OV/bin;/opt/sfw/bin"
def Environment_Setup(PathExtentionString,wfanprint=False):
  sep = ":"
  if Is_Os_Windows():
    sep = ";"
  if not PathExtentionString in os.environ['PATH']:
    printString='Adding %s to PATH.' % (PathExtentionString)
    os.environ['PATH']="%s%s%s" % (os.environ['PATH'], sep, PathExtentionString)
  else:
    printString='%s is already in PATH.' % (PathExtentionString)
  if wfanprint:
    try:
      WFAN.setValues(result=printString)
    except:
      pass
  print(printString)

### FUNCTIONs run OS commands with possible printouts
def CheckRunOSOutputs(winargs,unixargs,success,exitcode,outputs,grepText=False,exitOnBadExitcode=True,exitOnNoOutput=True):
  returnSuccess=True
  if Is_Os_Windows():
    command=winargs
  else:
    command=unixargs
  if not success or exitcode!=0:
    returnSuccess=False
    if exitOnBadExitcode:
      try:
        WFAN.setValues(step="NZEerr",reason=True,result="Nonzero exitcode in OS CMD(%s),OUTPUT(%s)\n"%(str(command),' '.join(outputs).strip()[:100]),rbaexitstatus=2,scriptexit=True)
      except:
        pass
  if len(outputs[0].strip())==0:
    returnSuccess=False
    if exitOnNoOutput:
      try:
        WFAN.setValues(step="NOerr",reason=True,result="No output from OS CMD(%s)\n"%(str(command)),rbaexitstatus=2,scriptexit=True)
      except:
        pass
  else:
    if grepText and grepText in str(''.join(outputs)):
      returnSuccess=True
  return returnSuccess

################################################################################
def RunOsCommandWithoutShell(winargs, unixargs,printouts=False,wfanprint=10,timeoutinsec=False):
  out=str()
  CommandUsed=''
  if Is_Os_Windows():
    if winargs:
      if isinstance(winargs, str) or isinstance(winargs, StringType):
        print("Please insert command as a list!")
        return False, None , ('', '')
      else:
        CommandUsed=' '.join(winargs)
  else:
    if unixargs:
      if isinstance(unixargs, str) or isinstance(unixargs, StringType):
        print("Please insert command as a list!")
        return False, None , ('', '')
      else:
        CommandUsed=' '.join(unixargs)
  if bool(printouts):
    print("COMMAND: %s" % CommandUsed)
  if bool(wfanprint):
    try:
      WFAN.addToWFAN("\nCOMMAND: %s" % CommandUsed)
    except:
      pass
  try:
    if Is_Os_Windows():
      CommandObject=subprocess.Popen(winargs, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE , shell=True)
    else:
      CommandObject=subprocess.Popen(unixargs, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE , shell=False)

    ### timeout default 30sec/cmd. terminate() occurs in python2.6
    if PythonVersion > (2, 5, 9):
      timercounter100Ms=0
      if timeoutinsec:
        while CommandObject.poll() is None:
          time.sleep(0.1)
          timercounter100Ms=timercounter100Ms+1
          if timercounter100Ms>timeoutinsec*10:
            CommandObject.terminate()
            WFAN.addToWFAN("\nTimeout %dsec occured in cmd[%s], terminating cmd..." % (timeoutinsec,CommandUsed))
            break

    ### comunicate
    StdOutText, StdErrText=CommandObject.communicate()
    ExitCode=CommandObject.returncode
    if StdOutText:
      out = StdOutText.strip()
    if StdErrText:
      if StdOutText:
        out = out + str("\n") + StdErrText.strip()
      else:
        out = StdErrText.strip()
    out2 = out
    if not ExitCode is None:
      out = out + "\nEXITCODE: " + str(ExitCode)
    if bool(printouts):
      print("%s" % out)
    if bool(wfanprint):
      try:
        WFAN.addToWFAN(out2+'\n',printlimit=wfanprint)
      except:
        pass
    return True, ExitCode , (StdOutText, StdErrText)
  except OSError:         
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    try:
      ExitCode=CommandObject.returncode
    except:
      ExitCode=None
    if bool(printouts):
      print("\nEXITCODE: " + str(ExitCode) + "\nEXCEPTION: " + ErrorOutput)
    return False, ExitCode, ('', ErrorOutput)
#     http://stackoverflow.com/questions/730764/try-except-in-python-how-do-you-properly-ignore-exceptions
#     ???how to gain e??? , if python3 takes "except OSError, e:" as syntax error and python244 does not accept "except OSError as e"
#     except OSError, e:
#     if e.errno == 2:
#         # suppress "No such file or directory" error
#         pass
#     else:
#         # reraise the exception, as it's an unexpected error
#         raise
  except ValueError:
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    try:
      ExitCode=CommandObject.returncode
    except:
      ExitCode=None
    if bool(printouts):
      print("\nEXITCODE: " + str(ExitCode) + "\nEXCEPTION: " + ErrorOutput)
    return False, ExitCode, ('', ErrorOutput)
  except:
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    if bool(printouts):
      print("\nEXCEPTION: " + ErrorOutput)
    return False, None, ('', ErrorOutput)

### FUNCTION OS command run with possible printouts
def RunOsCommandWithShell(winargs, unixargs,printouts=False,wfanprint=10,timeoutinsec=False):
  out=str()
  CommandUsed=''
  if Is_Os_Windows():
    if winargs:
      if isinstance(winargs, str) or isinstance(winargs, StringType):
        CommandUsed=winargs
      else:
        CommandUsed=' '.join(winargs)
  else:
    if unixargs:
      if isinstance(unixargs, str) or isinstance(unixargs, StringType):
        CommandUsed=unixargs
      else:
        CommandUsed=' '.join(unixargs)
  if bool(printouts):
    print("COMMAND: %s" % CommandUsed)
  if bool(wfanprint):
    try:
      WFAN.addToWFAN("\nCOMMAND: %s" % CommandUsed)
    except:
      pass
  try:
    if Is_Os_Windows():
      #cmd /C  /E:ON   Enable command extensions ,  /V:ON   Enable delayed environment variable expansion using ! as the
      #  delimiter. For example, /V:ON would allow !var! to expand the
      #  variable var at execution time.  The var syntax expands variables
      #  at input time, which is quite a different thing when inside of a F
      #  loop.
      #  PURPOSE: To have defined environment , indepentent on windows registry settings
      CommandObject=subprocess.Popen('cmd E:ON V:ON /C "'+CommandUsed+'"', stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE , shell=True)
    else:
      CommandObject=subprocess.Popen(CommandUsed, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE , shell=True)

    ### timeout default 30sec/cmd. terminate() occurs in python2.6
    if PythonVersion > (2, 5, 9):
      timercounter100Ms=0
      if timeoutinsec:
        while CommandObject.poll() is None:
          time.sleep(0.1)
          timercounter100Ms=timercounter100Ms+1
          if timercounter100Ms>timeoutinsec*10:
            CommandObject.terminate()
            WFAN.addToWFAN("\nTimeout %dsec occured in cmd[%s], terminating cmd..." % (timeoutinsec,CommandUsed))
            break

    ### comunicate
    StdOutText, StdErrText=CommandObject.communicate()
    ExitCode=CommandObject.returncode
    if StdOutText:
      out = StdOutText.strip()
    if StdErrText:
      if StdOutText:
        out = out + str("\n") + StdErrText.strip()
      else:
        out = StdErrText.strip()
    out2 = out
    if ExitCode:
      out = out + str("\nEXITCODE: ") + str(ExitCode)
    if bool(printouts):
      print("%s" % out)
    if bool(wfanprint):
      try:
        WFAN.addToWFAN(out2+'\n',printlimit=wfanprint)
      except:
        pass
    return True, ExitCode , (StdOutText, StdErrText)
  except OSError:
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    try:
      ExitCode=CommandObject.returncode
    except:
      ExitCode=None
    if bool(printouts):
      print("\nEXITCODE: " + str(ExitCode) + "\nEXCEPTION: " + ErrorOutput)
    return False, ExitCode, ('', ErrorOutput)
  except ValueError:
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    try:
      ExitCode=CommandObject.returncode
    except:
      ExitCode=None
    if bool(printouts):
      print("\nEXITCODE: " + str(ExitCode) + "\nEXCEPTION: " + ErrorOutput)
    return False, ExitCode, ('', ErrorOutput)
  except:
    WFAN.saveExceptions()
    ErrorOutput = str(sys.exc_info()[0])
    if bool(printouts):
      print("\nEXCEPTION: " + ErrorOutput)
    return False, None, ('', ErrorOutput)

################################################################################
def DoesExistsFileOrLink(WindowsFile,UnixFile,wfanprint=False):
  result=''
  if Is_Os_Windows():
    filetocheck=WindowsFile
  else:
    filetocheck=UnixFile
  if (os.path.isfile(filetocheck) or os.path.islink(filetocheck)) and os.access(filetocheck, os.R_OK):
    result=filetocheck
    if wfanprint:
      try:
        WFAN.addToWFAN('-->File %s FOUND.' % (filetocheck.replace('\\','/')))
      except:
        pass
  else:
    if wfanprint:
      try:
        WFAN.addToWFAN('-->File %s NOT FOUND.' % (filetocheck.replace('\\','/')))
      except:
        pass
  return result

##### DefineBinary function ####################################################
def DefineBinary(inputprogram,AdditionalPathList=[],nonbinary=False,printouts=False,wfanprint=False):
  """Function DefineBinary returns found and executable binary with path included"""
  def wfanPrintoutsFoundOrNot(outfilename):
    if wfanprint:
      try:
        if nonbinary:
          if outfilename:
            WFAN.addToWFAN('-->File %s FOUND in %s.' % (inputprogram.replace('\\','/'),outfilename.replace('\\','/')))
          else:
            WFAN.addToWFAN('-->File %s NOT FOUND.' % (inputprogram.replace('\\','/')))
        else:
          if outfilename:
            WFAN.addToWFAN('-->Binary %s FOUND in %s.' % (inputprogram.replace('\\','/'),outfilename.replace('\\','/')))
          else:
            WFAN.addToWFAN('-->Binary %s NOT FOUND.' % (inputprogram.replace('\\','/')))
      except:
        pass
  ### subfuction doesBinaryExists
  def doesBinaryExists(binaryToCheck):
    if nonbinary:
      return (os.path.isfile(binaryToCheck) or os.path.islink(binaryToCheck)) and os.access(binaryToCheck, os.R_OK)
    else:
      return (os.path.isfile(binaryToCheck) or os.path.islink(binaryToCheck)) and os.access(binaryToCheck, os.X_OK)
  ### subfunction returnPrintable
  def returnPrintable(binary):
    if Is_Os_Windows():
      printBinary='"%s"' % (binary)
    else:
      printBinary=binary
    if printouts:
      print("FOUND: %s" % printBinary)
    return printBinary
  ### subfunction testBinaryAlsoExeAndBat
  def testBinaryAlsoExeAndBat(inputfile):
    WindowsExtentionsList=['.COM','.EXE','.BAT','.JOB','.CMD','.MSI','.VBS','.VBE','.JS','.JSE','.WSF','.WSH','.MSC','.PS1','.PS']
    filename,extention=os.path.splitext(inputfile)
    if Is_Os_Windows():
      if extention.upper() in WindowsExtentionsList:
        if doesBinaryExists(inputfile):
          return returnPrintable(inputfile)
      elif not extention.upper():
        for ext in WindowsExtentionsList:
          if doesBinaryExists(inputfile+ext):
            return returnPrintable(inputfile+ext)
    else:
      if doesBinaryExists(inputfile):
        return returnPrintable(inputfile)
    return ''
  ### DefineBinary function start itself ---------------------------------------
  if not inputprogram:
    if printouts:
      print("BINARY NAME NOT INSERTED.")
    wfanPrintoutsFoundOrNot('')
    return ''
  fpath, fname = os.path.split(inputprogram)
  if fpath:
    ### 1st try - original inputprogram string with path
    resultFile=testBinaryAlsoExeAndBat(inputprogram)
    if resultFile:
      wfanPrintoutsFoundOrNot(resultFile)
      return resultFile
  if fname:
    ### 2nd try - look in additional paths
    for path in AdditionalPathList:
      path=path.strip('"')
      if path:
        inputProgramWithPath=os.path.join(path, fname)
        resultFile=testBinaryAlsoExeAndBat(inputProgramWithPath)
        if resultFile:
          wfanPrintoutsFoundOrNot(resultFile)
          return resultFile
    ### 3rd try - look in OS PATH
    for path in os.environ["PATH"].split(os.pathsep):
      path=path.strip('"')
      if path:
        inputProgramWithPath=os.path.join(path, fname)
        resultFile=testBinaryAlsoExeAndBat(inputProgramWithPath)
        if resultFile:
          wfanPrintoutsFoundOrNot(resultFile)
          return resultFile
    ### 4rd try - look also with win:where/unix:which
    success,exitcode,outputs=RunOsCommandWithShell("where " + fname, "which " + fname,printouts=False,wfanprint=False)
    if success and exitcode==0:
      inputBinFile=outputs[0].strip()
      resultFile=testBinaryAlsoExeAndBat(inputBinFile)
      if resultFile:
        wfanPrintoutsFoundOrNot(resultFile)
        return resultFile
  if printouts:
    if nonbinary:
      print("FILE %s NOT FOUND." % inputprogram)
    else:
      print("EXECUTABLE %s NOT FOUND." % inputprogram)
  wfanPrintoutsFoundOrNot('')
  return ''

################################################################################
class WFAN(object):
  """The class WFAN is responsible for RBA script printouts."""
  import traceback
  ###from sys import exit as sysExitImported     ###python 1.5 syntax issue
  from sys import exit
  RBAExitStatusDefinitions=["success", "failure", "diagnose", "categorized"]
  StepMarker='++++++\n'
  CommandMarker='COMMAND: '
  NextCommandMarker='~~~~~~\nCOMMAND: '
  ResultMarker='-->'
  ResumeMarker='### '
  OS_release = ""
  OS_version = ""
  OS_name = ""
  OS_type = ""
  Interpreter = ""

  def __init__(self):
    """WFAN constructor prints RBA script output header"""
    self.WfanPrinted=False
    self.SrbaYesOrNo=True
    self.__steps = ""
    self.__reason = ""
    self.__summary = ""
    self.__exception = ""
    self.RBAExitStatus=3
    self.printHeader()
    self.printInputParameters()
    self.StandardOutput=[]
    self.AdditionalOutput=[]

  def __del__(self):
    """WFAN denstructor prints WFAN , if WFAN was not printed before in case of traceback from unhandled exception."""
    if not self.WfanPrinted:
      if self.__reason=="":
        self.RBAExitStatus=3
        self.setStep("Exc")
        self.setValues(reason="Script ended abnormally! Possible unhandled Exception! Check Reason in tailStdOut.")
      self.GenerateFinalReportOutput()

  def addToWFAN(self, stdout="", printlimit=10):
    """The method addToWFAN("something") adds line into script WFAN output."""
    if stdout is None:
      pass
    elif isinstance(stdout, StringType):
      if bool(printlimit):
        if int(printlimit)>0:
          self.StandardOutput.extend(stdout.split('\n')[0:int(printlimit)-1])
          if len(stdout.split('\n'))>int(printlimit):
            self.StandardOutput.append('         ...OUTPUT TRUNCATED...')
        else:
          if len(stdout.split('\n'))>int(printlimit):
            self.StandardOutput.append('         ...TAIL OF OUTPUT...')
          self.StandardOutput.extend(stdout.split('\n')[printlimit:-1])
      else:
        self.StandardOutput.append(stdout)
    else:
      if bool(printlimit):
        if int(printlimit)>0:
          self.StandardOutput.extend(stdout[0:int(printlimit)-1])
          if len(stdout)>int(printlimit):
            self.StandardOutput.append('         ...OUTPUT TRUNCATED...')
        else:
          if len(stdout)>int(printlimit):
            self.StandardOutput.append('         ...TAIL OF OUTPUT...')
          self.StandardOutput.extend(stdout[printlimit:-1])
      else:
        self.StandardOutput.extend(stdout)

  def addToAdditionalInfornation(self, stdout=""):
    """The method addToAdditionalInfornation("something") adds line into Additional Information field in WFAN output."""
    if isinstance(stdout, StringType):
      self.AdditionalOutput.append(stdout)
    else:
      self.AdditionalOutput.extend(stdout)

  def copyToSummary(self):
    self.__summary = self.__reason

  def getInputParameters(self):
    return str(' '.join(sys.argv[1:])) + '\n'

  def getRBAExitStatus(self):
    return self.RBAExitStatus

  def getSRBA(self):
    return self.SrbaYesOrNo

  def getSummary(self):
    collectedSummary=""
    if len(self.__summary)==0:
      collectedSummary=self.__reason
    else:
      collectedSummary=self.__summary
    if len(self.__exception)>0:
      collectedSummary=collectedSummary+'\nFound Exceptions: '+self.__exception
    return collectedSummary

#   def getLastUnhandledException2(self):
#     return str(self.traceback.format_exc())
#
#   def getLastUnhandledException(self):
#     output=""
#     try:
#       output='('+str(sys.last_type)+' '+str(sys.last_value)+' '+str(sys.last_traceback)+')'
#     except:
#       pass
#     return output

  def getLastException(self):
    return str(self.traceback.format_exc())

  def saveExceptions(self):
    """The method saveExceptions() save data about handled exceptions.This will be printed on end of firstline statement of WFAN as a notice."""
    self.setStep("Exc")
    self.__exception=self.__exception+'\n'+self.getLastException()

  def setRBAExitStatus(self, status=""):
    """The method setRBAExitStatus(0..3) sets RBA exit status in number.
       :param int[0..3]
    """
    if status != "":
      self.RBAExitStatus=int(status)

  def setReason(self, reason=""):
    """The method setReason("something") adds Diagnosed reason field in WFAN output."""
    self.__reason=reason

  def setSRBA(self, status=""):
    """The method setSRBA(True/False) sets Run SRBA field in WFAN output."""
    if status != "":
      self.SrbaYesOrNo=bool(status)

  def setStep(self, step=""):
    """The method setStep("S1") adds step into Performed Steps field in WFAN output."""
    if step != "":
      self.__steps = self.__steps + " " + step

  def setSummary(self, msg=""):
    """The method setSummary("some summary") sets first line final result in WFAN output."""
    self.__summary = msg

  ### Universal SWISSKNIFE FUNCTION ############################################
  def setValues(self, step="", reason=None, stepname="", standardoutput="", command="", nextcommand="" , result="", summary="",endtext='' , rbaexitstatus="",start="",before="",after="",end="",wfanprint=10,scriptexit=False):
    """The method setValues(step="", reason="", stepname="", standardoutput="", command="", nextcommand="" , result="", summary="", endtext='',rbaexitstatus="",start="",before="",after="",end="",wfanprint=10) sets all fields in WFAN output."""
    """Parameters: """
    """   - start,before,after,end - could be "\n",3,or "3" , where number means how much free lines to insert. """
    """   - nextcommand - print ~~~~~~\n before COMMAND:... (like command parameter)"""
    """   - rbaexitstatus=0 : RBA success , rbaexitstatus=1 : RBA failure , rbaexitstatus=2 : RBA diagnose , rbaexitstatus=3 : RBA categorized """
    if '\n' in [str(start),str(before)]:
      self.addToWFAN(" ")
    if str.isdigit(str(start)):
      for i in range(int(start)):
        self.addToWFAN(" ")
    if str.isdigit(str(before)):
      for i in range(int(before)):
        self.addToWFAN(" ")

    if isinstance(reason, StringType):
      self.__reason = self.__reason + str(reason)
    elif isinstance(reason, list) or isinstance(reason, tuple):
      self.__reason = self.__reason + ''.join(reason)
    elif isinstance(reason, bool):
      if reason==True:
        self.__reason = self.__reason + str(result)

    if len(step) > 20:
      self.__reason = step
    else:
      if step != "":
        self.__steps = self.__steps + " " + step

    if step == "FS":
      if self.RBAExitStatus == 0:
        self.__reason = ""

    if summary != "":
      self.__summary = ''.join(summary)

    if stepname != "":
      if step != "":
        self.addToWFAN("%s%s. %s" % (self.StepMarker,step,stepname))
      else:
        self.addToWFAN("%s%s" % (self.StepMarker,stepname))

    if command != "":
      if isinstance(command, StringType):
        self.addToWFAN("%s%s" % (self.CommandMarker,command))
      else:
        self.addToWFAN("%s%s" % (self.CommandMarker,' '.join(command)))

    if nextcommand != "":
      if isinstance(nextcommand, StringType):
        self.addToWFAN("%s%s" % (self.NextCommandMarker,nextcommand))
      else:
        self.addToWFAN("%s%s" % (self.NextCommandMarker,' '.join(nextcommand)))

    if standardoutput != "":
        self.addToWFAN(standardoutput,printlimit=wfanprint)

    if result != "":
      self.addToWFAN("%s%s" % (self.ResultMarker,result))

    if endtext:
      self.addToWFAN('### '+endtext,printlimit=wfanprint)

    if rbaexitstatus != "":
      self.RBAExitStatus=int(rbaexitstatus)

    if '\n' in [str(after),str(end)]:
      self.addToWFAN(" ")
    if str.isdigit(str(after)):
      for i in range(int(after)):
        self.addToWFAN(" ")
    if str.isdigit(str(end)):
      for i in range(int(end)):
        self.addToWFAN(" ")
    if scriptexit==True:
      self.scriptExit()
    ###REM WFAN.SetValues END

  def printSrbaYN(self):
    if self.SrbaYesOrNo:
      print('Run SRBA: YES')
    else:
      print('Run SRBA: NO')

  def printHeader(self):
    # Header
    print("RBA script stdout")
    print("Script Version: %s" % (ScriptVersion))
    print("Template Version: %s" % (TemplateVersion))
    self.printEnvironmentInfo()
    print("")
  #-----------------------------------------------------------------------------
  def readFile(self,file=""):
    f = None
    returnValue=""
    if os.path.isfile(file):
      try:
        f = open(file, 'r')
        returnValue=f.read()
        f.close()
      except:
        pass
    return returnValue
  #-----------------------------------------------------------------------------
  def getWmi(self,wmiclass='', property=''):
    returnValue=''
    success,exitcode,outputs = RunOsCommandWithShell('echo | wmic ' + wmiclass + ' Get ' + property, None, printouts=False,wfanprint=False)
    stdoutput, erroutput = outputs
    if success is True and exitcode==0:
      returnValue=str(stdoutput.split('\n')[1].strip())
    return returnValue
  #-----------------------------------------------------------------------------
  def printEnvironmentInfo(self):
    Environment = "Environment: "
    self.OS_version = str(platform.uname()[3])

    if '64' in str(platform.machine()):
      self.OS_type = '64-bit'
    elif '32' in str(platform.machine()):
      self.OS_type = '32-bit'
    elif '86' in str(platform.machine()):
      self.OS_type = '32-bit'

    if not self.OS_type:
      success,exitcode,outputs = RunOsCommandWithShell(r'wmic /namespace:\\root\cimv2 path Win32_ComputerSystem get SystemType /format:list','uname -a', printouts=False,wfanprint=False)
      if success and exitcode==0:
        if 'X64' in outputs[0].upper() or 'X86_64' in outputs[0].upper():
          self.OS_type = '64-bit'
        else:
          self.OS_type = '32-bit'

    self.Interpreter = "Python " + str(sys.version.split()[0])
    if 'bit' in sys.version:
      self.Interpreter = self.Interpreter + " " + str(sys.version.split('bit')[0].split()[-1]) + "-bit"

    if platform.uname()[0] in ['Windows','Microsoft']:
      self.OS_class = str("Windows")
      self.OS_name = self.getWmi(wmiclass='OS',property='Caption')
      if self.OS_type=='':
        self.OS_type = self.getWmi(wmiclass='OS',property='OSArchitecture')
      #win2k3 workarround , OSArchitecture does not exists
      if self.OS_type=='' and 'x64' in self.OS_name:
        self.OS_type = '64-bit'

      if self.OS_release=='':
        majorNumber = self.getWmi(wmiclass='OS',property='ServicePackMajorVersion')
        minorNumber = self.getWmi(wmiclass='OS',property='ServicePackMinorVersion')
        if int(majorNumber)>0 or int(minorNumber):
          self.OS_release='SP' + majorNumber + '.' + minorNumber
        else:
          self.OS_release='No Service Pack'

    else:
      self.OS_class = str(platform.uname()[0])
      self.OS_release = str(platform.uname()[2])

      if self.OS_class=="HP-UX":
        self.OS_name=self.OS_class
        self.OS_version = str(platform.uname()[2].split('B.')[1].split('.')[0].split('\n')[0])
        self.OS_release = str(platform.uname()[2].split('B.')[1].split('.')[1].split()[0])
      elif self.OS_class=="AIX":
        self.OS_name=self.OS_class
        self.OS_version = str(platform.uname()[3])
        self.OS_release = str(platform.uname()[2])
      elif self.OS_class=="SunOS":
        self.OS_name=self.OS_class
        self.OS_version = str(platform.uname()[2].split('.')[0])
        self.OS_release = str(platform.uname()[2].split('.')[1])
      elif self.OS_class=='Linux':
        if os.path.isfile('/etc/oracle-release'):
          self.OS_name='ORACLE'
        elif os.path.isfile('/etc/SuSE-release'):
          self.OS_name='SUSE'
          self.OS_version=self.readFile('/etc/SuSE-release').split('VERSION')[1].split('=')[1].split('\n')[0].strip()
          self.OS_release=self.readFile('/etc/SuSE-release').split('PATCHLEVEL')[1].split('=')[1].split('\n')[0].strip()
        elif os.path.isfile('/etc/redhat-release'):
          self.OS_name='REDHAT'
          self.OS_version=self.readFile('/etc/redhat-release').split('release')[1].split()[0].split('.')[0].strip()
          self.OS_release=self.readFile('/etc/redhat-release').split('release')[1].split()[0].split('.')[1].strip()
        else:
          self.OS_release = str(platform.uname()[2])

    #print Environment part
    if self.OS_class:
      Environment = Environment + "OS_class=" + str(self.OS_class) + ","
    if self.OS_name:
      Environment = Environment + "OS_name=" + str(self.OS_name) + ","
    if self.OS_version:
      Environment = Environment + "OS_version=" + str(self.OS_version) + ","
    if self.OS_release:
      Environment = Environment + "OS_release=" + str(self.OS_release) + ","
    if self.OS_type:
      Environment = Environment + "OS_type=" + str(self.OS_type) + ","
    if self.Interpreter:
      Environment = Environment + "Interpreter=" + str(self.Interpreter)
    print(str(Environment))

  def printInputParameters(self):
    print('Input parameters: ' + str(' '.join(sys.argv[1:])) + '\n')

  def printSummary(self):
    print(self.StepMarker + 'Script ended with ' + self.RBAExitStatusDefinitions[self.RBAExitStatus] + '. ' + self.getSummary().strip() )
    print("")

  def printSteps(self):
    self.__steps = self.__steps.strip()
    if self.__steps != "":
      print("Steps Performed: %s" % self.__steps)

  def printReason(self):
    self.__reason = self.__reason.strip()
    if self.__reason != "":
      print("Diagnosed Reason: %s" % self.__reason)

  def GenerateFinalReportOutput(self):
    """The method GenerateFinalReportOutput() prints all WFAN output on the end of the script."""
    ### Generates the final report - DO NOT MODIFY!!!
    #Header printed in WFAN constructor, reason is do diagnostic printouts by simple print
    self.printSteps()
    self.printReason()
    self.printSrbaYN()

    SumOfBytes = len(self.StepMarker + 'Script ended with ' + self.RBAExitStatusDefinitions[self.RBAExitStatus] + '. ' + self.getSummary())
    for CurrentLine in self.StandardOutput:
      SumOfBytes = SumOfBytes + len(CurrentLine)
      SumOfBytes = SumOfBytes + len("\"")

      if self.AdditionalOutput:
        SumOfBytes = SumOfBytes + len("##### Additional information #####")

        for CurrentLine in self.AdditionalOutput:
          SumOfBytes = SumOfBytes + len(CurrentLine)

    print("W-F-A-N lenght=" + str(SumOfBytes) + " Bytes")
    print("WFAN=\"")

    # Send all report information to STDIO(screen normally)
    self.printSummary()

    for CurrentLine in self.StandardOutput:
      print(CurrentLine)

    # Additional script messages - This will be used to pass along any messages or status's that should be captured, but that does not fall within
    # the standard report output display. Examples: Any error messages, including binary(s) not found, insuffient disk space, etc
    if self.AdditionalOutput:
      print("")
      print("##### Additional information #####")
      print("")

      for CurrentLine in self.AdditionalOutput:
        print(CurrentLine)

      print("")

    # Footer
    print("")
    print("\"")
    ##### Report RBA exit status
    print("RBA %s" % self.RBAExitStatusDefinitions[self.RBAExitStatus])
    """variable self.WfanPrinted=True means WFAN was printed correctly."""
    self.WfanPrinted=True

  def setFinalSteps(self):
    if self.getRBAExitStatus()==0:
      self.setValues("FS")
    elif self.getRBAExitStatus()==1:
      self.setValues("FF")
    elif self.getRBAExitStatus()==2:
      self.setValues("FD")
    else:
      self.setValues("FC")

  def scriptExit(self):
    self.setFinalSteps()
    self.GenerateFinalReportOutput()
    try:
      sys.exit(0)
    except:
      self.exit(0)
  ### =========== end of WFAN class ============================================

##### SIGNAL Handlers functions
def SignalHandlerInt(signal, frame):
  WFAN.setValues("Script INTERRUPTED by signal SIGINT !")
  WFAN.scriptExit()

def SignalHandlerTerm(signal, frame):
  WFAN.setValues("Script TERMINATED by signal SIGTERM !")
  WFAN.scriptExit()

def SignalHandlerAlarm(signal, frame):
  WFAN.setValues("Script TIMEOUT %s min EXPIRED !" % str(gTimeoutMinutes))
  WFAN.scriptExit()



##### OS defined test functions - All tests should be defined here. Tests are not order specific, and can be added in any order

def RBA_Automation_Test():
  ### Initialize global variables, local variables, and lists

  ### Function specific common commands - Sub functions that are called by all OS's, should be put here
  #WFAN.setSRBA(False)
  WFAN.setSRBA(True)


  ############################ START OF EXAMPLE AREA ###########################


  #example of run commnads with shell=on  
  unixargs='sleep 10'
  winargs=r'timeout /T 10 /NOBREAK'
  success,exitcode,outputs = RunOsCommandWithShell(winargs,unixargs,wfanprint=-30)

  unixargs='sleep 20'
  winargs=r'timeout /T 20 /NOBREAK'
  success,exitcode,outputs = RunOsCommandWithShell(winargs,unixargs,wfanprint=-30,timeoutinsec=5)

  ############################# END OF EXAMPLE AREA ############################

################################################################################
##### Main script function - DO NOT MODIFY #####################################
################################################################################
if __name__ == "__main__":
  WFAN = WFAN()
  # Capture break signals
  signal.signal(signal.SIGINT, SignalHandlerInt)
  signal.signal(signal.SIGTERM, SignalHandlerTerm)

  if not Is_Os_Windows() and not "TERM" in os.environ:
    os.environ["TERM"] = "xterm"

  ##### Initial option/argument handling
  parser=optparse.OptionParser(version="%prog - Version: " + ScriptVersion, description=OptionDescription)
  parser.add_option("", "--gTimeoutMinutes" , action="store", type="string", metavar="gTimeoutMinutes", dest="gTimeoutMinutes", help="Script timeout in minutes.")
  #DESCRIPTION: parser.add_option("-i", "--instance", action="store", type="string", metavar="TargetInstanceDisplayedInHelp", dest="TargetInstance", help="What parameter means or does.")
  ###EDIT_HERE - EXAMPLE of adding switches for external input, one switch/option per line
  #...

  try:
    (options, args) = parser.parse_args()
    ###SCRIPT SPECIAL OPTIONS
    tempTimeoutMinutes=options.gTimeoutMinutes
    try:
      gTimeoutMinutes=float(tempTimeoutMinutes)
    except:
      try:
        if str(tempTimeoutMinutes).upper()=='OFF':
          gTimeoutMinutes=None
      except:
        pass
    ###EDIT_HERE - EXAMPLE of assigment of parsed input parametes into global variable
    #...

  except:
     #WFAN.saveExceptions()
     WFAN.setValues(reason="Input parameters parsing problem! , Input parameters: " + WFAN.getInputParameters())
     WFAN.setRBAExitStatus(3)  

  if not Is_Os_Windows():
    if gTimeoutMinutes:
      WFAN.setValues(result="Timeout %.1fmin active."%(gTimeoutMinutes))
      signal.signal(signal.SIGALRM, SignalHandlerAlarm)
      signal.alarm(int(60*gTimeoutMinutes))

  # Run automation test
  RBA_Automation_Test()

  # Set Final Steps
  WFAN.setFinalSteps()

  # Wfan Output
  WFAN.GenerateFinalReportOutput()

##### Script exit status - This should always be set to '0'
sys.exit(0)

### TEMPLATE CHANGELOG:
#   May 03 2017 , 2.0.8 , Peter Nemec
#      - WFAN class enhancements - header printing in class constructor 
#      - added more functions to WFAN class 
#      - moving of input parameters parsing to __main__ section for better parameter extention handling
#      - added printout Run SRBA: YES/NO, Input Parameters , ENVIRONMENT by default
#      - FINAL STEPS extention to FS,FF,FD,FC
#      - added section "W-F-A-N lenght=xxx Bytes" to "RBA script stdout"
#      - Firstline WFAN Summary printouts enhanced also for printing of reason if summary is void
#      - redefining StandardOutput=[] and AdditionalOutput=[] as WFAN object private variables
#      - RBAExitStatus changed to WFAN.setRBAExitStatus(0..3)
#      - WFAN printed even in case of fail or break
#      - more universal printing to WFAN by function WFAN.setValues(step="S1", standardoutput="StepNameExample"),...
#      - added getters/setters to WFAN class
#      - added docstring into WFAN class
#      - repaired minor bug of spaces in Steps Perforwed if step="" in method SetValues()
#      - python3 run compatibility - print()
#      - python version check changed to from version 2.4.4
#      - old way WFAN.StandardOutput.append NOT_SUPPORTED!!! use WFAN.addToWFAN("text") 
#      - added import errno,traceback
#      - old way WFAN.RBAExitStatus=2 NOT_SUPPORTED!!! , use WFAN.setRBAExitStatus(0..3)
#      - RunOsCommand... functions returns tuple (stdout,stderr) similar as function popen.communicate() , use ''.join(outputs)
#
#   May 15 2017 , 2.0.9 , Peter Nemec
#      - added handling of signals SIGINT, SIGTERM
#      - added gTimeoutMinutes variable and script end after timeout , available only on UNIX
#      - add setSRBA on start of RBA_Automation_Test() function
#      - print of RBA exit status moved to function WFAN.GenerateFinalReportOutput()
#      - added example of input parameters
#      - printout ENVIRONMENT:... without -->
#      - trimming of trailing spaces
#
#   May 17 2017 , 2.1.0 , Peter Nemec
#      - use sys.version in case of sys.version_info exception
#      - added WFAN variables - WFAN.OS_release,WFAN.OS_version,WFAN.OS_release,WFAN.OS_name,WFAN.OStype,WFAN.Interpreter
#      - implemented Environment information due to Martin Valach proposal
#      - added new parameter to function - setValues(rbaexitstatus=0..3)
#      - added new parameter to setValues(start='\n',end='\n') - intended insert free lines to WFAN before and after setValues printout
#      - StepMarker , CommandMarker without '\n' on start , if you need it use setValues(start='\n',end='\n')
#      - added new parameter to function setValues(nextCommand="") to display ~~~~~\nCOMMAND:
#
#   May 18 2017 , 2.1.1 , Peter Nemec
#      - WFAN.setvalues(rbaexitstatus) bug repaired
#      - added new parameters to function setValues(before=3,after='\n') , mixed syntax number/string means number of lines or '\n\
#
#   May 19 2017 , 2.1.2 , Peter Nemec
#      - change of condition in "if ExitCode!= None:" RunOsCommandWithShell nad RunOsCommandWithoutShell functions to show exitcode correctly
#      - added WFAN.scriptExit() function to correct immediate script end
#      - added info about interpreter 32/64bit
#
#   May 19 2017 , 2.1.3 , Peter Nemec
#      - 'is' instead of '==' in case of checks for object identity
#      - added "" in cmd /c part of RunOsCommandWithShell function
#      - list update in setValues(command=list or string)
#
#   Jun 06 2017 , 2.1.4 , Peter Nemec
#      - delete twice definition of WFAN.OS_release variable
#      - WFAN.addToWFAN() accept also None
#
#   Jun 19 2017 , 2.1.5 , Peter Nemec
#      - correction of bugs in functions scriptExit , setFinalSteps
#      - moving of function WFAN.setFinalSteps() to __main__ and also to WFAN.scriptExit()
#      - added Rommel's function DefineBinary() to template , it works like in Jonathan's function in ksh template
#
#   Jun 28 2017 , 2.1.6 , Peter Nemec
#      - DXC copyright
#
#   Jun 30 2017 , 2.1.7 , Peter Nemec
#      - automatic first 10 lines printouts to WFAN in functions RunOsCommandWithShell/RunOsCommandWithoutShell, parameter wfanprint is True by default
#
#   Jul 03 2017 , 2.1.8 , Peter Nemec
#      - w2k3 OS 32/64bit detection improoved , thanks to hint of BranislavF
#      - limit of truncation i.e. wfanprint=5, limit WFAN to 5 lines
#
#   Jul 20 2017 , 2.1.9 , Peter Nemec
#      - addToWFAN default limit 10lines , (printlimit>0 head ,<0 tail ,=0 no limitation)
#
#   Sep 20 2017 , 2.2.0 , Peter Nemec
#      - DefineBinary return '' instead of None, because len of None makes exception
#      - both RunOs... functions added \n to output, otherwise limiting of printings do not print last line
#      - $TERM set if not set
#      - added oracle database detection and runsql functions
#
#   Nov 14 2017 , 2.2.1 , Peter Nemec
#      - fixed in functions RunOS... sporadic non printed last line , when wfanprint limitation is set
#      - functions RunOS... default switched-off printouts to tailstdout , default wfanprint 10lines to WFAN
#      - known behaviour/issue in functions RunOS... if wfanprint=True, it prints only truncation info :(...
#      - function DefineBinary() enhanced, aux optional parameter, Folder list where also to look for binary
#      - improved compatibility with python 1.5
#
#   Dec 01 2017 , 2.2.2 , Peter Nemec
#      - small printout bug found by Martin Stanik in function WFAN.setValues
#
#   Dec 11 2017 , 2.2.3 , Peter Nemec
#      - Categorized as default
#
#   Dec 11 2017 , 2.2.4 , Peter Nemec
#      - BUGFIX traceback in printEnvironmentInfo 64/32bit system detection
#
#   Feb 21 2018 , 2.2.5 , Peter Nemec
#      - DefineBinary function update
#      - runoscmd.. functions update , not to return Nonetype
#      - version 2.2.4 to 2.2.5 + ''' to """
#
#   Mar 08 2018 , 2.2.6 , Peter Nemec
#      - WFAN.setValues - added parameter scriptexit=True --> script end
#      - WFAN.setValues - if parameter reason=True , copy result to reason
#
#   Apr 18 2018 , 2.2.7 , Peter Nemec
#      - assume file links in DefineBinary() , added wfanprint in DefineBinary()
#      - added CheckRunOSOutputs()
#      - BUFFIX - RunOsC...() void winargs/unixargs, pass in case of no WFAN instance
#      - BUGFIX - OSName for unix OS ,
#      - BUGFIX - CommandMarker/NextCommandMarker in WFAN.setValues()
#
#   Apr 19 2018 , 2.2.8 , Peter Nemec
#      - BUGFIX - wfanprint in DefineBinary, paramerter CHANGE - debugprintouts to printouts
#      - ADDED - wfanprint in EnvironmentSetup
#
#   Apr 30 2018 , 2.2.9 , Peter Nemec
#      - ADDED - cmdline switch '--gTimeoutMinutes 12.3' or '--gTimeoutMinutes off'
#
#   May 10 2018 , 2.3.0 , Peter Nemec
#      - ADDED - endtext parameter in function WFAN.setValues()
#      - ADDED - function DoesExistsFileOrLink()
#
#   May 17 2018 , 2.3.1 , Peter Nemec
#      - ADDED - parameter timeoutinsec in functions RunOsCommand.. valid for python>2.6