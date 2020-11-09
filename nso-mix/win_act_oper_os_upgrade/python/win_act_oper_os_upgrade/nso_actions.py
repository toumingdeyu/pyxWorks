# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.dp import Action
from ncs.application import Service
from .device_access import *
import collections
import os, copy, time, json
from datetime import date
import json

### IMPORT: from .nso_actions import *    ###


# --------------------------
#   GET SW VERSION ACTION
# --------------------------
class NsoActionsClass_get_sw_version(Action):
    """Get sw version action definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
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
                         output.target_sw_versions[i].path = str('%s%s/%s' % (drive_string, dev_dir, sub_directory))
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
                    patch_path = str()
                    for line in patch_file_device_cmds_result.splitlines()[:-1]:
                        try:
                            tar_file = line.split()[-1]
                            for file_type in file_types:
                                try: patch_file = file_type.split('/')[1].replace('*','')
                                except: patch_file = str()
                                if len(patch_file) > 0 and patch_file.upper() in tar_file.upper():
                                    #patch_files.append(tar_file)
                                    patch_files.append('%s%s/%s/%s/%s' % (drive_string, dev_dir,output.target_sw_versions[i].name,'SMU' , tar_file))
                                    patch_path = '%s%s/%s/%s' % (drive_string, dev_dir,output.target_sw_versions[i].name,'SMU')
                        except: pass
                    if len(patch_files)>0:
                        output.target_sw_versions[i].patch_files = patch_files
                        output.target_sw_versions[i].patch_path = patch_path

                elif output.os_type == "huawei-vrp":
                    pass
                elif output.os_type == "junos":
                    pass

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        #self.log.info('\nOUTPUT_dump: ', object_dump(self, output))

        #self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))

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
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        inactive_packages = []
        active_packages = []
        asr_admin_string = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":
            ii = 0
            output.precheck_data.command.create().name = str( '%sshow install inactive sum' % (asr_admin_string) )

            device_cmds = {
                'ios-xr':[ output.precheck_data.command[ii].name ],
            }

            device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)
            output.precheck_data.command[ii].cmd_output = str('\n'.join(device_cmds_result.splitlines()[:-1]))

            inactive_packages = []
            if 'No inactive package(s) in software repository' in device_cmds_result:
                pass
            else:
                if 'inactive package(s) found:' in device_cmds_result:
                    for package_line in device_cmds_result.split('inactive package(s) found:')[1].splitlines()[:-1]:
                        if package_line.strip():
                            inactive_packages.append(str(package_line.strip()))

                ii += 1
                output.precheck_data.command.create().name = str( '%sinstall remove inactive all' % (asr_admin_string) )

                device_cmds2 = {
                    'ios-xr':[ output.precheck_data.command[ii].name ],
                }

                device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds2)
                output.precheck_data.command[ii].cmd_output = str('\n'.join(device_cmds_result.splitlines()[:-1]))

                time.sleep(5)

                ### REPEAT INACTIVE CHECK ###
                ii += 1
                output.precheck_data.command.create().name = str( '%sshow install inactive summary' % (asr_admin_string) )
                device_cmds = {
                    'ios-xr':[ output.precheck_data.command[ii].name ],
                }

                device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)
                output.precheck_data.command[ii].cmd_output = str('\n'.join(device_cmds_result.splitlines()[:-1]))

                inactive_packages = []
                if 'No inactive package(s) in software repository' in device_cmds_result:
                    pass
                else:
                    if 'inactive package(s) found:' in device_cmds_result:
                        for package_line in device_cmds_result.split('inactive package(s) found:')[1].splitlines()[:-1]:
                            if package_line.strip():
                                inactive_packages.append(str(package_line.strip()))
            output.inactive_packages = inactive_packages

            ### show install active summary ###
            ii += 1
            output.precheck_data.command.create().name = str( '%sshow install active summary' % (asr_admin_string) )
            act_device_cmds = {
                'ios-xr':[ output.precheck_data.command[ii].name ],
            }

            device_cmds_result, forget_it = device_command(self, uinfo, input, act_device_cmds)
            output.precheck_data.command[ii].cmd_output = str('\n'.join(device_cmds_result.splitlines()[:-1]))

            if 'Active Packages:' in device_cmds_result:
                number_of_active_packages = int(device_cmds_result.split('Active Packages:')[1].split()[0])
                for i in range(number_of_active_packages):
                     active_packages.append(device_cmds_result.split('Active Packages:')[1].splitlines()[i + 1].split()[0].strip())
                output.active_packages = active_packages

            ### XR CHECK LIST ###
            xr_check_cmd_list = [
                    '%sshow install log | utility tail count 10' % (asr_admin_string),
                    'install verify packages',
                    'show platform',
                    'show run fpd auto-upgrade',
                    'admin show run fpd auto-upgrade',
                    'show configuration failed startup',
                    'clear configuration inconsistency',
                    'show health gsp',
                    'show install request',
                    'show install repository',
                    'show hw-module fpd'
            ]

            for check_cmd in xr_check_cmd_list:
                ii += 1
                output.precheck_data.command.create().name = str( check_cmd )

                device_cmds = {
                    'ios-xr':[ output.precheck_data.command[ii].name ],
                }

                device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)
                output.precheck_data.command[ii].cmd_output = str('\n'.join(device_cmds_result.splitlines()[:-1]))

            ### copy configs ###
            today = date.today()
            date_string = today.strftime("%Y-%m%d-%H:%M")

            cp_device_cmds = {
                'ios-xr':['copy running-config harddisk:%s-config.txt| prompts ENTER' % (str(date_string))],
            }

            cp_device_cmds_result, forget_it = device_command(self, uinfo, input, cp_device_cmds)

            cp2_device_cmds = {
                'ios-xr':['admin copy running-config harddisk:admin-%s-config.txt| prompts ENTER' % (str(date_string))],
            }

            cp2_device_cmds_result, forget_it = device_command(self, uinfo, input, cp2_device_cmds)

            for command in output.precheck_data.command:
                if command.name == 'show run fpd auto-upgrade' \
                and not 'fpd auto-upgrade enable' in command.cmd_output:

                    xr_cmds = {'ios-xr': [
                            'config',
                            '!',
                            'fpd auto-upgrade enable',
                            '!',
                            'commit',
                            '!',
                            'exit',
                            '!'
                    ] }

                    device_cmds_result, forget_it = device_command(self, uinfo, input, xr_cmds)

            for command in output.precheck_data.command:
                if command.name == 'admin show run fpd auto-upgrade' \
                and not 'fpd auto-upgrade enable' in command.cmd_output:

                    xr_cmds = {'ios-xr': [
                            'config',
                            '!',
                            'admin',
                            '!',
                            'fpd auto-upgrade enable',
                            '!',
                            'commit',
                            '!',
                            'exit',
                            '!',
                            'exit',
                            '!'
                    ] }

                    device_cmds_result, forget_it = device_command(self, uinfo, input, xr_cmds)

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))


# --------------------------
#   OS UPGRADE INSTALL ADD
# --------------------------
class NsoActionsClass_os_upgrade_install_add(Action):
    """Does os upgrade install add definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        asr_admin_string = str()

        sw_version_selected_file = str()
        patch_version_selected_files = str()
        file_string_without_path = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        sw_version_selected_file = str()
        try:
            if input.sw_version_selected_file:
                sw_version_selected_file = str(input.sw_version_selected_file)
        except: pass

        patch_version_selected_files = str()
        try:
            if input.patch_version_selected_files:
                patch_version_selected_files = str(input.patch_version_selected_files)
        except: pass

        patch_version_selected_path = str()
        try:
            if input.patch_version_selected_path:
                patch_version_selected_path = str(input.patch_version_selected_path)
        except: pass

        i_device_cmds = {}
        if output.os_type == "ios-xr":
            if sw_version_selected_file:
                i_device_cmds = {
                    'ios-xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                    '/'.join(str(sw_version_selected_file).replace('[','').replace(']','').split()[0].strip().split('/')[:-1]),
                    str(sw_version_selected_file).replace('[','').replace(']','').split()[0].strip().split('/')[-1] )
                    ],
                }
            elif patch_version_selected_files:
                file_list = patch_version_selected_files.replace('[','').replace(']','').split()
                for file in file_list:
                    file_string_without_path += file.strip().split('/')[-1] + ' '
                file_string_without_path = file_string_without_path.strip()

                i_device_cmds = {
                    'ios-xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                    '/'.join(str(patch_version_selected_files).replace('[','').replace(']','').split()[0].strip().split('/')[:-1]),
                    file_string_without_path )
                    ]
                }
            elif patch_version_selected_path:

                ### def GET PATHS ON DEVICE ###########################################
                brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
                get_local_subdirectories(brand_raw = 'CISCO', type_raw = hw_info.get('hw_type',str()) )

                self.log.info('FILE_TYPES=', file_types)

                patch_file_device_cmds = {
                    'ios-xe':[],
                    'ios-xr':['dir %s' % (patch_version_selected_path)],
                    'junos':[],
                    'huawei-vrp':[]
                }
                patch_file_device_cmds_result, forget_it = device_command(self, uinfo, input, patch_file_device_cmds)

                patch_files = []
                patch_path = str()
                for line in patch_file_device_cmds_result.splitlines()[:-1]:
                    try:
                        tar_file = line.split()[-1]
                        for file_type in file_types:
                            try: patch_file = file_type.split('/')[1].replace('*','')
                            except: patch_file = str()
                            if len(patch_file) > 0 and patch_file.upper() in tar_file.upper():
                                patch_files.append('%s' % (tar_file))
                    except: pass
                if len(patch_files)>0:
                    i_device_cmds = {
                        'ios-xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                        patch_version_selected_path,
                        ' '.join(patch_files) )
                        ]
                }

            i_device_cmds_result, output.os_type = device_command(self, uinfo, input, i_device_cmds)

            try: output.operation_id = i_device_cmds_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
            except: output.operation_id = str()

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))

# -----------------------------------------
#   OS UPGRADE INSTALL ADD PROGRESS CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_progress_check(Action):
    """Does os upgrade install add progress check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.completed = 'no'
        output.result = str()
        asr_admin_string = str()

        operation_id = str()
        if input.operation_id:
            try: operation_id = str(input.operation_id).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass
        elif input.operation_id_smu:
            try: operation_id = str(input.operation_id_smu).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass

        if operation_id:
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

                ### FOUND LAST STARTED OPERATION ###
                output.operation_id = str()
                device_cmds = {
                    'ios-xr':['%sshow install log' % (asr_admin_string)],
                }

                device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)
                #output.install_log = device_cmds_result

                for part in device_cmds_result.split('Install operation '):
                    try: part_split_1 = part.split()[1]
                    except: part_split_1 = str()
                    if part_split_1 == 'started':
                        try: part_operation_id = part.split()[0]
                        except: part_operation_id = str()
                        try: part_last_command = part.split('started')[1].split(':')[1].splitlines()[1].strip()
                        except: part_last_command = str()
                        try:
                            if part_operation_id and int(part_operation_id) >= int(operation_id):
                                if not output.operation_id:
                                    output.last_command = part_last_command
                                    output.operation_id = part_operation_id
                                ### FIND MAX OPERATION ID IN LOG, NOT ONLY HIGHER AS INPUT ###
                                elif output.operation_id and int(part_operation_id) >= int(output.operation_id):
                                    output.last_command = part_last_command
                                    output.operation_id = part_operation_id
                        except: pass

                if not output.operation_id:
                    try:
                        output.operation_id = device_cmds_result.split('Invalid')[-1].split('operation id:')[1].split()[0].strip()
                        output.completed = 'yes'
                        output.result = 'failure'
                    except: pass

            self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        else:
            output.completed = 'yes'
            output.result = 'failure'        
            self.log.info('Operation id not inserted!')


# -----------------------------------------
#   OS UPGRADE DEVICE PING CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_device_ping_check(Action):
    """Does os upgrade install device ping check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.result = 'UNKNOWN'

        device = str()
        try:
            if input.device: device = str(input.device)
        except: pass

        ip = str()
        try:
            if input.ip: ip = str(input.ip)
        except: pass

        if device:
            ping_response = os.system("ping -c 1 " + device)
            if int(ping_response) == 0: output.result = 'success'
            else: output.result = 'failure'

        if output.result == 'failure' and ip:
            ping_response = os.system("ping -c 1 " + ip)
            if int(ping_response) == 0: output.result = 'success'
            else: output.result = 'failure'
        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))



# -----------------------------------------
#   OS UPGRADE DEVICE GET IP
# -----------------------------------------
class NsoActionsClass_os_upgrade_device_get_ip(Action):
    """Does os upgrade install device ping check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))

        try: device = str(input.device)
        except: device = str()

        if device:
            hw_info = detect_hw(self, uinfo, input)
            #output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

            cmd = {
                      "ios-xr":['show running-config interface loopback 0'],
                  }

            cmd_result, forget_it = device_command(self, uinfo, input, cmd)

            if hw_info.get('os_type') == "ios-xr":
                try: output.ip_address = cmd_result.split('ipv4 address')[1].split()[0].strip()
                except: output.ip_address = str()

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))



# --------------------------
#   OS UPGRADE INSTALL PREPARE
# --------------------------
class NsoActionsClass_os_upgrade_install_prepare(Action):
    """Does os upgrade install prepare definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'

        output.completed = str()
        output.result = str()
        asr_admin_string = str()

        operation_id = str()
        if input.operation_id:
            try: operation_id = str(input.operation_id).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass
        elif input.operation_id_smu:
            try: operation_id = str(input.operation_id_smu).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass

        if operation_id:
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

            self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        else:
            self.log.info('Operation id not inserted!')


# --------------------------
#   OS UPGRADE INSTALL ACTIVATE
# --------------------------
class NsoActionsClass_os_upgrade_install_activate(Action):
    """Does os upgrade install activate definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.operation_id = str()
        output.last_command = str()
        output.completed = str()
        output.result = str()
        asr_admin_string = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        cmd = {
                  #"ios-xe":['show version'],
                  "ios-xr":['%sinstall activate noprompt' % (asr_admin_string)],
                  #"huawei-vrp":['display version'],
                  #"junos":['show version']
              }

        cmd_result, forget_it = device_command(self, uinfo, input, cmd)
        output.install_log = cmd_result

        if hw_info.get('os_type') == "ios-xr":
            for i in range(20):
                time.sleep(3)
                device_cmds = {
                    'ios-xr':['%sshow install log' % (asr_admin_string)],
                }

                device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)

                find_success = False
                part_operation_id, part_operation_id_int, last_operation_id_int = str(), 0, 0
                for part in device_cmds_result.split('Install operation '):
                    try: part_split_1 = part.split()[1]
                    except: part_split_1 = str()
                    try: part_operation_id_int = int(part.split()[0])
                    except: part_operation_id_int = 0
                    if part_operation_id_int > 0: last_operation_id_int = part_operation_id_int
                    if part_split_1 == 'started':
                        try: part_operation_id = part.split()[0]
                        except: part_operation_id = str()
                        try: part_last_command = part.split('started')[1].split(':')[1].splitlines()[1].strip()
                        except: part_last_command = str()
                        try:
                            if part_operation_id:
                                if not output.operation_id:
                                    if part_last_command == '%sinstall activate noprompt' % (asr_admin_string):
                                        output.operation_id = part_operation_id
                                        output.last_command = part_last_command
                                elif output.operation_id and int(part_operation_id) >= int(output.operation_id):
                                    if part_last_command == '%sinstall activate noprompt' % (asr_admin_string):
                                        output.operation_id = part_operation_id
                                        output.last_command = part_last_command
                        except: pass
                ### CHECK IF LAST OPERATION ID IS 'install activate noprompt' ###
                if part_operation_id and last_operation_id_int > 0 and last_operation_id_int == int(part_operation_id):
                    find_success = True
                if output.last_command and output.operation_id and find_success: break
            if not output.last_command and not output.operation_id and not find_success:
                output.install_log = "Problem to find started 'install activate noprompt' in install log!"

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))


# --------------------------
#   OS UPGRADE REMOVE INACTIVE
# --------------------------
class NsoActionsClass_os_upgrade_remove_inactive(Action):
    """Does os upgrade remove inactive definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        asr_admin_string = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        device_cmds = {
            'ios-xr':['%sinstall remove inactive all' % (asr_admin_string)],
        }

        device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)
        output.log = device_cmds_result

        if hw_info.get('os_type') == "ios-xr":

            for part in device_cmds_result.split('Install operation '):
                try: part_split_1 = part.split()[1]
                except: part_split_1 = str()
                if part_split_1 == 'started':
                    try: part_operation_id = part.split()[0]
                    except: part_operation_id = str()
                    try: part_last_command = part.split('started')[1].split(':')[1].splitlines()[1].strip()
                    except: part_last_command = str()
                    try:
                        if part_operation_id:
                            if not output.operation_id:
                                output.last_command = part_last_command
                                output.operation_id = part_operation_id
                            ### FIND MAX OPERATION ID IN LOG, NOT ONLY HIGHER AS INPUT ###
                            elif output.operation_id and int(part_operation_id) >= int(output.operation_id):
                                output.last_command = part_last_command
                                output.operation_id = part_operation_id
                    except: pass
        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))


# --------------------------
#   OS UPGRADE COMMIT
# --------------------------
class NsoActionsClass_os_upgrade_commit(Action):
    """Does os upgrade commit definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'

        asr_admin_string = str()

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":

            device_cmds = {
                'ios-xr':['%sinstall commit' % (asr_admin_string)],
            }

            device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)
            output.log = device_cmds_result

            for part in device_cmds_result.split('Install operation '):
                try: part_split_1 = part.split()[1]
                except: part_split_1 = str()
                if part_split_1 == 'started':
                    try: part_operation_id = part.split()[0]
                    except: part_operation_id = str()
                    try: part_last_command = part.split('started')[1].split(':')[1].splitlines()[1].strip()
                    except: part_last_command = str()
                    try:
                        if part_operation_id:
                            if not output.operation_id:
                                output.last_command = part_last_command
                                output.operation_id = part_operation_id
                            ### FIND MAX OPERATION ID IN LOG, NOT ONLY HIGHER AS INPUT ###
                            elif output.operation_id and int(part_operation_id) >= int(output.operation_id):
                                output.last_command = part_last_command
                                output.operation_id = part_operation_id
                    except: pass
        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))


# --------------------------
#   OS UPGRADE POSTCHECK
# --------------------------
class NsoActionsClass_os_upgrade_postcheck(Action):
    """Does os upgrade postcheck definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.result = str()

        asr_admin_string = str()

        self.log.info('\nINPUT.PRECHECK_COMMANDS: ', input.precheck_commands)

        list_lenght = len(input.precheck_commands)
        self.log.info('\nINPUT.PRECHECK_COMMANDS[len=%s] ' % (list_lenght))

        precheck_list = input.precheck_commands
        for i in input.precheck_commands:
            self.log.info('\nINPUT.PRECHECK_COMMAND = %s ' % (i))

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        return None

        hw_info = detect_hw(self, uinfo, input)
        output.os_type, output.hw_type = hw_info.get('os_type',str()), hw_info.get('hw_type',str())

        if hw_info.get('os_type') == "ios-xr":
            postcheck_list = []

            check_cmd = str( '%sshow install inactive sum' % (asr_admin_string) )
            device_cmds = {
                'ios-xr':[ check_cmd ],
            }

            device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)
            postcheck_list.append([str(check_cmd), str('\n'.join(device_cmds_result.splitlines()[:-1]))])

            inactive_packages = []
            if 'No inactive package(s) in software repository' in device_cmds_result:
                pass
            else:
                if 'inactive package(s) found:' in device_cmds_result:
                    for package_line in device_cmds_result.split('inactive package(s) found:')[1].splitlines()[:-1]:
                        if package_line.strip():
                            inactive_packages.append(str(package_line.strip()))

                check_cmd = str( '%sinstall remove inactive all' % (asr_admin_string) )
                device_cmds2 = {
                    'ios-xr':[ check_cmd ],
                }

                device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds2)
                postcheck_list.append([str(check_cmd), str('\n'.join(device_cmds_result.splitlines()[:-1]))])

                time.sleep(5)

                ### REPEAT INACTIVE CHECK ###
                check_cmd = str( '%sshow install inactive sum' % (asr_admin_string) )
                device_cmds = {
                    'ios-xr':[ check_cmd ],
                }

                device_cmds_result, output.os_type = device_command(self, uinfo, input, device_cmds)
                postcheck_list.append([str(check_cmd), str('\n'.join(device_cmds_result.splitlines()[:-1]))])

                inactive_packages = []
                if 'No inactive package(s) in software repository' in device_cmds_result:
                    pass
                else:
                    if 'inactive package(s) found:' in device_cmds_result:
                        for package_line in device_cmds_result.split('inactive package(s) found:')[1].splitlines()[:-1]:
                            if package_line.strip():
                                inactive_packages.append(str(package_line.strip()))

            ### XR CHECK LIST ###
            xr_postcheck_cmd_list = [
                    '%sshow install active summary' % (asr_admin_string),
                    '%sshow install log | utility tail count 10' % (asr_admin_string),
                    'install verify packages',
                    'show platform',
                    'show run fpd auto-upgrade',
                    'admin show run fpd auto-upgrade',
                    'show configuration failed startup',
                    'clear configuration inconsistency',
                    'show health gsp',
                    'show install request',
                    'show install repository',
                    'show hw-module fpd',
                    'show running-config',
                    'admin show running-config'
            ]

            for check_cmd in xr_postcheck_cmd_list:
                device_cmds = {
                    'ios-xr':[ check_cmd ],
                }

                device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)
                postcheck_list.append([check_cmd, str('\n'.join(device_cmds_result.splitlines()[:-1]))])

            ### PARSE 'show hw-module fpd' !!! ###
            fpd_problems = []
            postcheck_config , postcheck_admin_config = str(), str()
            for post_check in postcheck_list:
                try:
                    if post_check[0] == 'show hw-module fpd':
                        for fpd_line in post_check[1].split('Running Programd')[1].splitlines():
                            if fpd_line.strip() and not '-----' in fpd_line:
                                if fpd_line.strip().split()[3] != 'CURRENT':
                                    fpd_problems.append(fpd_line.strip())
                    elif post_check[0] == 'show running-config':
                        postcheck_config = str(post_check[1])
                    elif post_check[0] == 'admin show running-config':
                        postcheck_admin_config = str(post_check[1])
                except: pass

            ### TODO: FIND LAST PRECHECK CONFIG FILE !!! ###
            admin_config_files, config_files = [], []
            device_cmds = {
                'ios-xr':['dir harddisk: | include config.txt'],
            }

            device_cmds_result, forget_it = device_command(self, uinfo, input, device_cmds)

            for file_line in device_cmds_result.splitlines()[:-1]:
                if file_line.strip() and '-config.txt' in file_line and ':' in file_line.split()[-1]:
                    try:
                        if 'admin' in file_line.split()[-1]:
                            admin_config_files.append(file_line.split()[-1])
                        else: config_files.append(file_line.split()[-1])
                    except: pass
            if len(config_files) > 1: config_files.sort()
            if len(admin_config_files) > 1: admin_config_files.sort()

            last_config_file, last_admin_config_file = str(), str()
            try:
                last_config_file = config_files[-1]
                last_admin_config_file = admin_config_files[-1]
            except: pass

            self.log.info('\nCONFIG FILE: ', last_config_file, '\nCHOSEN FROM: ', config_files)
            self.log.info('\nADMIN CONFIG FILE: ', last_admin_config_file, '\nCHOSEN FROM: ', admin_config_files)

            ### copy configs ###
            # today = date.today()
            # date_string = today.strftime("%Y-%m%d-%H:%M")

            # cp_device_cmds = {
                # 'ios-xr':['copy running-config harddisk:%s-postconfig.txt| prompts ENTER' % (str(date_string))],
            # }

            # cp_device_cmds_result, forget_it = device_command(self, uinfo, input, cp_device_cmds)

            # cp2_device_cmds = {
                # 'ios-xr':['admin copy running-config harddisk:admin-%s-postconfig.txt| prompts ENTER' % (str(date_string))],
            # }

            # cp2_device_cmds_result, forget_it = device_command(self, uinfo, input, cp2_device_cmds)

            ### TODO: DIFF CONFIGS !!! ###
            ### run diff YYYY-MMDD-config-before-upgrade.txt YYYY-MMDD-config-afer-upgrade.txt
            ### utility head count 1000000 file harddisk:/2020-1001-00:00-config.txt

            if last_config_file:
                cp_device_cmds = {
                    'ios-xr':['utility head count 1000000 file harddisk:/%s' % (last_config_file)],
                }

                cp_device_cmds_result, forget_it = device_command(self, uinfo, input, cp_device_cmds)

            if last_admin_config_file:
                cp2_device_cmds = {
                    'ios-xr':['admin utility head count 1000000 file harddisk:/%s' % (last_admin_config_file)],
                }

                cp2_device_cmds_result, forget_it = device_command(self, uinfo, input, cp2_device_cmds)

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))


###############################################################################

def nso_object_to_string(self, object_instance):
    """ Printable representation of object variables."""
    try: return_string = '\n' + str(eval("str(object_instance)")) + ':\n'
    except: pass
    for item in dir(object_instance):
        if '_' in str(item[0]) and '_' in str(item[-1]): pass
        else:
            # dir_subobjects = None
            # try: dir_subobjects = dir(object_instance.item)
            # except: pass
            # if dir_subobjects:
                # for subitem in dir(object_instance.item):
                    # if '_' in str(subitem[0]) and '_' in str(subitem[-1]): pass
                    # else:
                        # try: return_string += "\\_____" + str(item) + '.' + str(subitem) + '=' + str(eval("object_instance.%s.%s" % str(item, subitem))) + '\n'
                        # except: return_string += '\\_____...\n'
            # else:
                item_type = str(eval("type(object_instance.%s)" % str(item)))
                try: return_string += "\\____" + str(item) + " [" + str(eval("type(object_instance.%s)" % str(item))) + '] = ' + str(eval("repr(object_instance.%s)" % str(item))) + '\n'
                except: return_string += '\\____'+ str(item) + ' = ...\n'
                ### vars,dir,str,repr ###
                ### '<class 'ncs.maagic.LeafList'>' 'ncs.maagic.Container', 'ncs.maagic.LeafList', 'ncs.maagic.List' ###
                if item_type == "<class 'ncs.maagic.LeafList'>":
                    ### len(leaflist) does not work !!! ###
                    return_string += "\\____" + str(item) + " [" + str(eval("type(object_instance.%s)" % str(item))) + '] = [ '
                    for list_item in getattr(object_instance, item):
                        return_string += "%s" % (repr(list_item)) + " "
                    return_string += ']\n'
                elif item_type == "<class 'ncs.maagic.List'>":
                    list_lenght = int(eval("len(object_instance.%s)" % (item)))
                    return_string += "\\____" + str(item) + " [" + str(eval("type(object_instance.%s)" % str(item))) + '] [len=' + str(list_lenght) + '] = [ '
                    i = 0
                    for list_item in getattr(object_instance, item):   #eval("object_instance.%s" % (item)):
                        #return_string += "\n%s" % (str(ncs.maagic.List(list_item)) + " "
                        return_string += "\nrepr(%s)" % (repr(list_item)) + " "
                        return_string += "\ndir(%s)" % (str(dir(list_item))) + " "
                        return_string += "\nvars(%s)\n" % (str(vars(list_item))) + " "
                        i += 1
                    #list_iterator = iter(getattr(object_instance, item))
                    #for i in range(list_lenght):
                        #list_reference = next(list_iterator)
                        #return_string += "%s" % (list_reference) + ' '

                    return_string += ']\n'

    return return_string

###############################################################################

def object_dump(self, obj):
    if hasattr(obj, '__dict__'):
        return vars(obj)
    else:
        return {attr: getattr(obj, attr, None) for attr in obj.__slots__}

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











