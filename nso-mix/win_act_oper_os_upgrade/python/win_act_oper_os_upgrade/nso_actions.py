# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.dp import Action
from ncs.application import Service
from .device_access import *
import collections
import os, copy, time
from datetime import date
import os

### IMPORT: from .nso_actions import *    ###


# --------------------------
#   GET SW VERSION ACTION
# --------------------------
class NsoActionsClass_get_sw_version(Action):
    """Get sw version action definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.sw_version = 'UNKNOWN'
        brand_raw = str()
        type_raw = str()


        ### GET SW VERSION ####################################################
        cmd = {
                  "ios-xe":['show version'],
                  "ios-xr":['show version'],
                  "huawei-vrp":['display version'],
                  "junos":['show version']
              }

        result, output.os_type = device_command(self, uinfo, input, cmd)

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

        ### def LOOK FOR PATCH ####################################################
        if output.os_type == "ios-xr":
            xe_device_patch_list = [ ]
            xr_device_patch_list = [ 'show install active summary' ]
            huawei_device_patch_list = []
            juniper_device_patch_list = []

            patch_device_cmds = {
                'ios-xe':xe_device_patch_list,
                'ios-xr':xr_device_patch_list,
                'junos':juniper_device_patch_list,
                'huawei-vrp':huawei_device_patch_list
            }

            patch_device_cmds_result, forget_it = device_command(self, uinfo, input, patch_device_cmds)

            sw_version = copy.deepcopy(output.sw_version)
            sw_patches = []

            if output.os_type == "ios-xe":
                pass
            elif output.os_type == "ios-xr":
                packages_lines = False
                for line in patch_device_cmds_result.splitlines()[:-1]:
                    try:
                         if '    Active Packages: ' in line: packages_lines = True
                         elif packages_lines and len(line) > 0:
                             if sw_version in line or sw_version.replace('.','') in line: pass
                             else: sw_patches.append(str(line.strip()))
                    except: pass

            elif output.os_type == "huawei-vrp":
                pass
            elif output.os_type == "junos":
                pass
            output.sw_patches = sw_patches


        ### def GET PATHS ON DEVICE ###########################################
        brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
            get_local_subdirectories(brand_raw = brand_raw, type_raw = type_raw)

        ### BY DEFAULT = '/' ##################################################
        dev_dir = os.path.abspath(os.path.join(os.sep, type_subdir_on_device))

        xe_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) ]
        xr_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) ]
        huawei_device_dir_list = [ 'dir %s%s' % (drive_string, dev_dir) ]
        juniper_device_dir_list = [ 'file list %s%s detail' % (drive_string,dev_dir) ]

        dir_device_cmds = {
            'ios-xe':xe_device_dir_list,
            'ios-xr':xr_device_dir_list,
            'junos':juniper_device_dir_list,
            'huawei-vrp':huawei_device_dir_list
        }

        dir_device_cmds_result, forget_it = device_command(self, uinfo, input, dir_device_cmds)
        versions = []

        if output.os_type == "ios-xe" or output.os_type == "ios-xr":
            i = 0
            for line in dir_device_cmds_result.splitlines():
                try:
                     sub_directory = line.split()[-1]
                     if str(line.split()[1])[0] == 'd' and int(sub_directory):
                         versions.append(sub_directory)
                         output.target_sw_versions.create().name = str(sub_directory)
                         output.target_sw_versions[i].path = str(dev_dir + '/' + sub_directory)
                         ### del mylist['key1']
                         i += 1
                except: pass

        elif output.os_type == "huawei-vrp":
            ### FILES ARE IN CFCARD ROOT !!! ##################################
            i = 0
            for line in dir_device_cmds_result.splitlines()[:-1]:
                try:
                    tar_file = line.split()[-1]
                    for file_type in file_types:
                        if '/' in file_type.upper():
                            file_type_parts = file_type.split('/')[-1].split('*')
                        else:
                            file_type_parts = file_type.split('*')
                        found_in_tar_file = True
                        for file_type_part in file_type_parts:
                            if file_type_part.upper() in tar_file.upper(): pass
                            else: found_in_tar_file = False
                        if len(file_type_parts) > 0 and found_in_tar_file:
                            output.target_sw_versions.create().name = str(tar_file)
                            output.target_sw_versions[i].path = str(dev_dir)
                            output.target_sw_versions[i].files = [tar_file]
                            i += 1
                except: pass

        elif output.os_type == "junos":
            ### FILES ARE IN re0:/var/tmp #####################################
            i = 0
            for line in dir_device_cmds_result.splitlines()[:-1]:
                try:
                    tar_file = line.split()[-1]
                    for file_type in file_types:
                        if '/' in file_type.upper():
                            file_type_parts = file_type.split('/')[-1].split('*')
                        else:
                            file_type_parts = file_type.split('*')
                        found_in_tar_file = True
                        for file_type_part in file_type_parts:
                            if file_type_part.upper() in tar_file.upper(): pass
                            else: found_in_tar_file = False
                        if len(file_type_parts) > 0 and found_in_tar_file:
                            output.target_sw_versions.create().name = str(tar_file)
                            output.target_sw_versions[i].path = str(dev_dir)
                            output.target_sw_versions[i].files = [tar_file]
                            i += 1
                except: pass

        for i in range(len(output.target_sw_versions)):
            ### def GET FILES ON DEVICE VERSION DIRECTORY #########################
            xe_device_file_list = [ 'dir %s%s/%s' % (drive_string, dev_dir, output.target_sw_versions[i].name) ]
            xr_device_file_list = [ 'dir %s%s/%s' % (drive_string, dev_dir, output.target_sw_versions[i].name) ]

            juniper_device_file_list = [ 'file list %s%s/%s detail' % (drive_string, dev_dir, output.target_sw_versions[i].name) ]

            file_device_cmds = {
                'ios-xe':xe_device_file_list,
                'ios-xr':xr_device_file_list,
                'junos':juniper_device_file_list,
                'huawei-vrp':[]
            }

            file_device_cmds_result, forget_it = device_command(self, uinfo, input, file_device_cmds)

            if output.os_type == "ios-xe" or output.os_type == "ios-xr":
                files = []
                for line in file_device_cmds_result.splitlines()[:-1]:
                    try:
                        tar_file = line.split()[-1]
                        for file_type in file_types:
                            if '/' in file_type.upper(): pass
                            else:
                                file_type_parts = file_type.split('*')
                                found_in_tar_file = True
                                for file_type_part in file_type_parts:
                                    if file_type_part.upper() in tar_file.upper(): pass
                                    else: found_in_tar_file = False
                                if len(file_type_parts) > 0 and found_in_tar_file:
                                    files.append('%s%s/%s/%s' % (drive_string, dev_dir,output.target_sw_versions[i].name, tar_file))
                    except: pass
                if len(files)>0:
                    output.target_sw_versions[i].files = files

            elif output.os_type == "huawei-vrp":
                pass
            elif output.os_type == "junos":
                pass

            ### GET SMU FILES ON DEVICE VERSION DIRECTORY #########################
            if output.os_type == "ios-xr":
                xr_device_patch_file_list = [ 'dir %s%s/%s/SMU' % (drive_string, dev_dir, output.target_sw_versions[i].name) ]

                patch_file_device_cmds = {
                    'ios-xe':[],
                    'ios-xr':xr_device_patch_file_list,
                    'junos':[],
                    'huawei-vrp':[]
                }

                patch_file_device_cmds_result, forget_it = device_command(self, uinfo, input, patch_file_device_cmds)

                if output.os_type == "ios-xe":
                    pass
                elif output.os_type == "ios-xr":
                    patch_files = []
                    for line in patch_file_device_cmds_result.splitlines()[:-1]:
                        try:
                            tar_file = line.split()[-1]
                            for file_type in file_types:
                                try: patch_file = file_type.split('/')[1].replace('*','')
                                except: patch_file = str()
                                if len(patch_file) > 0 and patch_file.upper() in tar_file.upper():
                                    patch_files.append(tar_file)
                        except: pass
                    if len(patch_files)>0:
                        output.target_sw_versions[i].patch_files = patch_files

                elif output.os_type == "huawei-vrp":
                    pass
                elif output.os_type == "junos":
                    pass

#    for i in range(len(output.target_sw_versions)):
#        if len(output.target_sw_versions[i].files) == 0 and len(output.target_sw_versions[key].patch_files) == 0:
#            del output.target_sw_versions[i]




# --------------------------
#   OS UPGRADE PRECHECK
# --------------------------
class NsoActionsClass_os_upgrade_precheck(Action):
    """Does os upgrade precheck definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        inactive_packages = []
        active_packages = []
        asr_admin_string = str()

        device_cmds = {
            'ios-xr':['%sshow install inactive sum' % (asr_admin_string)],
        }

        device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)

        if output.os_type == "ios-xr":
            if 'No inactive package(s) in software repository' in device_cmds_result:
                pass
            else:
                if 'Inactive Packages:' in device_cmds_result:
                    for package_line in device_cmds_result.split('Inactive Packages:')[1].splitlines():
                        if package_line and package_line[0] == ' ':
                            inactive_packages.append(package_line.split()[0].strip())

                for inactive_package in inactive_packages:
                    device_cmds2 = {
                        'ios-xr':['%sinstall remove inactive %s' % (asr_admin_string,inactive_package)],
                    }

                    device_cmds_result2, output.os_type = device_command(self, uinfo, input, device_cmds2)

                time.sleep(1)

                device_cmds = {
                    'ios-xr':['%sshow install inactive sum' % (asr_admin_string)],
                }

                device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)

                if output.os_type == "ios-xr":
                    if 'No inactive package(s) in software repository' in device_cmds_result:
                        pass
                    else:
                        inactive_packages = []
                        if 'Inactive Packages:' in device_cmds_result:
                            for package_line in device_cmds_result.split('Inactive Packages:')[1].splitlines():
                                if package_line and package_line[0] == ' ':
                                    inactive_packages.append(package_line.strip())
            output.inactive_packages = inactive_packages

            ### show install active summary ###
            act_device_cmds = {
                'ios-xr':['%sshow install active summary' % (asr_admin_string)],
            }

            act_device_cmds_result, output.os_type = device_command(self, uinfo, input, act_device_cmds)

            if 'Active Packages:' in act_device_cmds_result:
                number_of_active_packages = int(act_device_cmds_result.split('Active Packages:')[1].split()[0])
                for i in range(number_of_active_packages):
                     active_packages.append(act_device_cmds_result.split('Active Packages:')[1].splitlines()[i + 1].split()[0].strip())
                output.active_packages = active_packages

            inst_device_cmds = {
                'ios-xr':['%s show install log' % (asr_admin_string)],
            }

            ### show install log ###
            inst_device_cmds_result, output.os_type = device_command(self, uinfo, input, inst_device_cmds)
            output.install_log = inst_device_cmds_result

            ### copy configs ###
            today = date.today()
            date_string = today.strftime("%Y-%m%d-%H:%M")

            cp_device_cmds = {
                'ios-xr':['copy running-config harddisk:%s-config.txt| prompts ENTER' % (str(date_string))],
            }

            cp_device_cmds_result, output.os_type = device_command(self, uinfo, input, cp_device_cmds)

            cp2_device_cmds = {
                'ios-xr':['admin copy running-config harddisk:admin-%s-config.txt| prompts ENTER' % (str(date_string))],
            }

            cp2_device_cmds_result, output.os_type = device_command(self, uinfo, input, cp2_device_cmds)



# --------------------------
#   OS UPGRADE INSTALL ADD
# --------------------------
class NsoActionsClass_os_upgrade_install_add(Action):
    """Does os upgrade install add definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        asr_admin_string = str()

        device_cmds = {
            'ios-xr':['show version'],
        }

        device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)

        if output.os_type == "ios-xr":
            i_device_cmds = {
                'ios-xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                '/'.join(str(input.sw_version_selected_file).replace('[','').replace(']','').split(',')[0].strip().split('/')[:-1]),
                str(input.sw_version_selected_file).replace('[','').replace(']','').split(',')[0].strip().split('/')[-1])
                ],
            }

            i_device_cmds_result, output.os_type = device_command(self, uinfo, input, input.device, i_device_cmds)

            try: output.operation_id = i_device_cmds_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
            except: output.operation_id = str()


# -----------------------------------------
#   OS UPGRADE INSTALL ADD PROGRESS CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_install_add_progress_check(Action):
    """Does os upgrade install add progress check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.completed = 'no'
        output.result = str()
        asr_admin_string = str()
        operation_id = str()

        try: operation_id = str(input.operation_id).replace('[','').replace(']','').split(',')[0].strip()
        except: pass

        device_cmds = {
            'ios-xr':['show version'],
        }

        device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)

        if output.os_type == "ios-xr":
            asi_device_cmds = {
                'ios-xr':['%sshow install log %s' % (asr_admin_string, operation_id)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            if 'Ending operation %s' % (operation_id) in asi_device_cmds_result:
                output.completed = 'yes'

            if 'Install operation %s aborted' % (operation_id) in asi_device_cmds_result:
                output.result = 'failure'

            if 'Install operation %s completed successfully' % (operation_id) in asi_device_cmds_result \
            or 'Install operation %s finished successfully' % (operation_id) in asi_device_cmds_result:
                output.result = 'success'
                output.completed = 'yes'


# --------------------------
#   OS UPGRADE INSTALL PREPARE
# --------------------------
class NsoActionsClass_os_upgrade_install_prepare(Action):
    """Does os upgrade install prepare definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'

        output.completed = str()
        output.result = str()
        asr_admin_string = str()
        operation_id = str()

        try: operation_id = str(input.operation_id).replace('[','').replace(']','').split(',')[0].strip()
        except: pass

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        cmd = {
                  #"ios-xe":['show version'],
                  "ios-xr":['install prepare id %s' % (operation_id)],
                  #"huawei-vrp":['display version'],
                  #"junos":['show version']
              }

        cmd_result, forget_it = device_command(self, uinfo, input, cmd)
        output.install_log = cmd_result

        if hw_info.get('os_type') == "ios-xr":
            try: output.operation_id = cmd_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
            except: output.operation_id = str()

# -----------------------------------------
#   OS UPGRADE INSTALL PREPARE PROGRESS CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_install_prepare_progress_check(Action):
    """Does os upgrade install prepare progress check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.completed = 'no'
        output.result = str()

        asr_admin_string = str()
        operation_id = str()

        try: operation_id = str(input.operation_id).replace('[','').replace(']','').split(',')[0].strip()
        except: pass

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":
            asi_device_cmds = {
                'ios-xr':['%sshow install log %s' % (asr_admin_string, operation_id)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            if 'Ending operation %s' % (operation_id) in asi_device_cmds_result:
                output.completed = 'yes'

            if 'Install operation %s aborted' % (operation_id) in asi_device_cmds_result:
                output.result = 'failure'

            if 'Install operation %s completed successfully' % (operation_id) in asi_device_cmds_result \
            or 'Install operation %s finished successfully' % (operation_id) in asi_device_cmds_result:
                output.result = 'success'
                output.completed = 'yes'




# --------------------------
#   OS UPGRADE INSTALL ACTIVATE
# --------------------------
class NsoActionsClass_os_upgrade_install_activate(Action):
    """Does os upgrade install activate definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'

        output.completed = str()
        output.result = str()
        asr_admin_string = str()
        operation_id = str()

        try: operation_id = str(input.operation_id).replace('[','').replace(']','').split(',')[0].strip()
        except: pass

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        cmd = {
                  #"ios-xe":['show version'],
                  "ios-xr":['install activate id %s' % (operation_id)],
                  #"huawei-vrp":['display version'],
                  #"junos":['show version']
              }

        cmd_result, forget_it = device_command(self, uinfo, input, cmd)
        output.install_log = cmd_result

        if hw_info.get('os_type') == "ios-xr":
            try: output.operation_id = cmd_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
            except: output.operation_id = str()

# -----------------------------------------
#   OS UPGRADE INSTALL ADD PROGRESS CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_install_activate_progress_check(Action):
    """Does os upgrade install activate progress check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.completed = 'no'
        output.result = str()

        asr_admin_string = str()
        operation_id = str()

        try: operation_id = str(input.operation_id).replace('[','').replace(']','').split(',')[0].strip()
        except: pass

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":
            asi_device_cmds = {
                'ios-xr':['%sshow install log %s' % (asr_admin_string, operation_id)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            if 'Ending operation %s' % (operation_id) in asi_device_cmds_result:
                output.completed = 'yes'

            if 'Install operation %s aborted' % (operation_id) in asi_device_cmds_result:
                output.result = 'failure'

            if 'Install operation %s completed successfully' % (operation_id) in asi_device_cmds_result \
            or 'Install operation %s finished successfully' % (operation_id) in asi_device_cmds_result:
                output.result = 'success'
                output.completed = 'yes'

        ping_response = os.system("ping -c 1 " + hw_info.get('device',str()))
        if ping_response == 0: pass
        else: output.completed = 'no'


# --------------------------
#   OS UPGRADE POSTCHECK
# --------------------------
class NsoActionsClass_os_upgrade_postcheck(Action):
    """Does os upgrade postcheck definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.result = str()

        asr_admin_string = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":
            asi_device_cmds = {
                'ios-xr':['%sshow configuration failed startup' % (asr_admin_string)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            asi_device_cmds = {
                'ios-xr':['%ssh install active summary' % (asr_admin_string)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            asi_device_cmds = {
                'ios-xr':['%sinstall commit' % (asr_admin_string)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result

            asi_device_cmds = {
                'ios-xr':['%ssh hw-module fpd location all' % (asr_admin_string)],
            }

            asi_device_cmds_result, output.os_type = device_command(self, uinfo, input, asi_device_cmds)
            output.install_log = asi_device_cmds_result






###############################################################################

def detect_hw(self, uinfo, input):
    hw_info = {}

    cmd = {
              "ios-xe":['show version'],
              "ios-xr":['show version'],
              "huawei-vrp":['display version'],
              "junos":['show version']
          }

    hw_info['device'] = copy.deepcopy(str(input.device))

    result, hw_info['os_type'] = device_command(self, uinfo, input, cmd)

    if hw_info.get('os_type') == "ios-xe":
        hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
        hw_info['hw_brand'] = 'CISCO'
        hw_info['drive_string'] = 'bootflash:'

    elif hw_info.get('os_type') == "ios-xr":
        hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
        hw_info['hw_brand'] = 'CISCO'
        hw_info['drive_string'] = 'harddisk:'

    elif hw_info.get('os_type') == "huawei-vrp":
        hw_info['sw_version'] = result.split('software, Version')[1].split()[0].strip()
        hw_info['hw_type'] = result.split(' version information:')[0].splitlines()[-1].strip()
        hw_info['hw_brand'] = 'HUAWEI'
        hw_info['drive_string'] = 'cfcard:'

    elif hw_info.get('os_type') == "junos":
        hw_info['sw_version'] = result.split('Junos: ')[1].split()[0].strip()
        hw_info['hw_type'] = result.split('Model: ')[1].split()[0].strip()
        hw_info['hw_brand'] = 'JUNIPER'
        hw_info['drive_string'] = 're0:'

    return hw_info

###############################################################################

def get_local_subdirectories(brand_raw = None, type_raw = None):
    """
    type_subdir_on_device - For the x2800..c4500 and the Huawei the files just
        go in the top level directory and for Juniper it goes in /var/tmp/
    """
    brand_subdir, type_subdir_on_server, file_types = str(), str(), []
    type_subdir_on_device = str()
    if type_raw:
        brand_raw_assumed = 'CISCO'
        if 'ASR9K' in type_raw.upper() \
            or 'ASR-9' in type_raw.upper() \
            or '9000' in type_raw.upper():
            type_subdir_on_server = 'ASR9K'
            type_subdir_on_device = 'IOS-XR'
            ### file_types = ['asr9k*OTI.tar', 'SMU/*.tar']
            file_types = ['9k', 'SMU/*.tar']
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
            brand_raw_assumed = 'CISCO'
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
            brand_raw_assumed = 'CISCO'
        elif 'MX20' in type_raw.upper():
            type_subdir_on_server = 'MX'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'MX480' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'VMX' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['junos*.img.gz', 'junos*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'NE40' in type_raw.upper():
            type_subdir_on_server = 'V8R10'
            type_subdir_on_device = ''
            file_types = ['Patch/*.PAT','*.cc']
            brand_raw_assumed = 'HUAWEI'

        ### BRAND ASSUMPTION IF NOT INSERTED ###
        if not brand_raw: brand_subdir = brand_raw_assumed.upper()
        else: brand_subdir = brand_raw.upper()
    return brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types











