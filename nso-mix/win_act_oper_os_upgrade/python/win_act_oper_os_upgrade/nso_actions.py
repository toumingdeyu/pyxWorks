# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.dp import Action
from ncs.application import Service
from .device_access import *
import collections
import os

### IMPORT: from .nso_actions import *    ###


# --------------------------
#   GET SW VERSION ACTION
# --------------------------
class Nso_Actions_Class_get_sw_version(Action):
    """Get sw version action definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.sw_version = 'UNKNOWN'
        output.target_sw_version = 'UNKNOWN'
        output.path_to_target_sw = 'UNKNOWN'
        brand_raw = str()
        type_raw = str()

        cmd = {
                  "ios-xe":['show version'],
                  "ios-xr":['show version'],
                  "huawei-vrp":['display version'],
                  "junos":['show version']
              }

        result, output.os_type = device_command(self, uinfo, input, input.device, cmd)

        if output.os_type == "ios-xe":
            output.sw_version = result.split('Software, Version')[1].split()[0].strip()
            output.hw_type = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
            brand_raw = 'CISCO'
            type_raw = output.hw_type
            drive_string = 'bootflash:'

        elif output.os_type == "ios-xr":
            output.sw_version = result.split('Software, Version')[1].split()[0].strip()
            output.hw_type = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
            brand_raw = 'CISCO'
            type_raw = output.hw_type
            drive_string = 'harddisk:'

        elif output.os_type == "huawei-vrp":
            output.sw_version = result.split('software, Version')[1].split()[0].strip()
            output.hw_type = result.split(' version information:')[0].splitlines()[-1].strip()
            brand_raw = 'HUAWEI'
            type_raw = output.hw_type
            drive_string = 'cfcard:'

        elif output.os_type == "junos":
            output.sw_version = result.split('Junos: ')[1].split()[0].strip()
            output.hw_type = result.split('Model: ')[1].split()[0].strip()
            brand_raw = 'JUNIPER'
            type_raw = output.hw_type
            drive_string = 're0:'

        ### GET PATH AND FILE TYPES ON DEVICE ###
        brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
            get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)

        dev_dir = os.path.abspath(os.path.join(os.sep, type_subdir_on_device))

        output.path_to_target_sw = dev_dir

        xe_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) ]
        xr_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) ]
        huawei_device_dir_list = [ 'dir %s%s/' % (drive_string, dev_dir) ]
        juniper_device_dir_list = [ 'file list %s%s detail' % (drive_string,dev_dir) ]

        dir_device_cmds = {
            'ios-xe':xe_device_dir_list,
            'ios-xr':xr_device_dir_list,
            'junos':juniper_device_dir_list,
            'huawei-vrp':huawei_device_dir_list
        }

        dir_device_cmds_result, forget_it = device_command(self, uinfo, input, input.device, dir_device_cmds)

        output.target_sw_version = dir_device_cmds_result

        if output.os_type == "ios-xe":
            pass        
        elif output.os_type == "ios-xr":             
            for line in dir_device_cmds_result.splitlines():
                try: 
                     if str(line.split()[1])[0] == 'd' and int(line.split()[-1]):
                         output.target_sw_version = line.split()[-1]                     
                except: pass            
            
        elif output.os_type == "huawei-vrp":
            pass
        elif output.os_type == "junos":
            pass




###############################################################################

def get_local_subdirectories(brand_raw = None, type_raw = None):
    """
    type_subdir_on_device - For the x2800..c4500 and the Huawei the files just
        go in the top level directory and for Juniper it goes in /var/tmp/
    """
    brand_subdir, type_subdir_on_server, file_types = str(), str(), []
    type_subdir_on_device = str()
    if brand_raw and type_raw:
        brand_subdir = brand_raw.upper()
        if 'ASR9K' in type_raw.upper() \
            or 'ASR-9' in type_raw.upper() \
            or '9000' in type_raw.upper():
            type_subdir_on_server = 'ASR9K'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
        elif 'NCS' in type_raw.upper():
            type_subdir_on_server = 'NCS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'ASR1001' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1001X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1001x*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'ASR1002-X' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002X/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr1002x*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'ASR1002-HX' in type_raw.upper():
            type_subdir_on_server = 'ASR1K/ASR1002HX/IOS_XE'
            type_subdir_on_device = 'IOS-XE'
            file_types = ['asr100*.bin','asr100*.pkg','/home/tftpboot/CISCO/ASR1K/ASR1002X/ROMMON/*.pkg']
        elif 'CRS' in type_raw.upper():
            type_subdir_on_server = 'CRS'
            type_subdir_on_device = 'IOS-XR'
            file_types = ['*OTI.tar', 'SMU/*.tar']
        elif 'C29' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            type_subdir_on_device = ''
            file_types = ['c2900*.bin']
        elif '2901' in type_raw.upper():
            type_subdir_on_server = 'C2900'
            type_subdir_on_device = ''
            file_types = ['c2900*.bin']
        elif 'C35' in type_raw.upper():
            type_subdir_on_server = 'C3500'
            type_subdir_on_device = ''
            file_types = ['c35*.bin']
        elif 'C36' in type_raw.upper():
            type_subdir_on_server = 'C3600'
            type_subdir_on_device = ''
            file_types = ['c36*.bin']
        elif 'C37' in type_raw.upper():
            type_subdir_on_server = 'C3700'
            type_subdir_on_device = ''
            file_types = ['c37*.bin']
        elif 'C38' in type_raw.upper():
            type_subdir_on_server = 'C3800'
            type_subdir_on_device = ''
            file_types = ['c38*.bin']
        elif 'ISR43' in type_raw.upper():
            type_subdir_on_server = 'C4321'
            type_subdir_on_device = ''
            file_types = ['isr43*.bin']
        elif 'C45' in type_raw.upper():
            type_subdir_on_server = 'C4500'
            type_subdir_on_device = ''
            file_types = ['cat45*.bin']
        elif 'MX20' in type_raw.upper():
            type_subdir_on_server = 'MX'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
        elif 'MX480' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
        elif 'NE40' in type_raw.upper():
            type_subdir_on_server = 'V8R10'
            type_subdir_on_device = ''
            file_types = ['Patch/*.PAT','*.cc']
    return brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types

