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
        brand_raw = str()

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        output.sw_version = RCMD.sw_version

        ### def LOOK FOR PATCH ####################################################
        if RCMD.router_type == "cisco_xr":
            xe_device_patch_list = [ ]
            xr_device_patch_list = [ 'show install active summary' ]
            huawei_device_patch_list = []
            juniper_device_patch_list = []

            patch_device_cmds = {
                'cisco_ios': xe_device_patch_list,
                'cisco_xr': xr_device_patch_list,
                'juniper': juniper_device_patch_list,
                'huawei': huawei_device_patch_list
            }

            patch_device_cmds_result = RCMD.run_commands(patch_device_cmds)

            sw_version = str(RCMD.sw_version)
            sw_patches = []

            if RCMD.router_type == "cisco_ios":
                pass
            elif RCMD.router_type == "cisco_xr":
                packages_lines = False
                for line in patch_device_cmds_result.splitlines()[:-1]:
                    try:
                         if '    Active Packages: ' in line: packages_lines = True
                         elif packages_lines and len(line) > 0:
                             if sw_version in line or sw_version.replace('.','') in line: pass
                             else: sw_patches.append(str(line.strip()))
                    except: pass

            elif RCMD.router_type == "huawei":
                pass
            elif RCMD.router_type == "juniper":
                pass
            output.sw_patches = sw_patches


        ### def GET PATHS ON DEVICE ###########################################
        brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
            get_local_subdirectories(brand_raw = brand_raw, type_raw = RCMD.hw_type)

        ### BY DEFAULT = '/' ##################################################
        dev_dir = os.path.abspath(os.path.join(os.sep, type_subdir_on_device))

        xe_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
        xr_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
        huawei_device_dir_list = [ 'dir %s%s' % (RCMD.drive_string, dev_dir) ]
        juniper_device_dir_list = [ 'file list %s%s detail' % (RCMD.drive_string,dev_dir) ]

        dir_device_cmds = {
            'cisco_ios':xe_device_dir_list,
            'cisco_xr':xr_device_dir_list,
            'juniper':juniper_device_dir_list,
            'huawei':huawei_device_dir_list
        }

        dir_device_cmds_result = RCMD.run_commands(dir_device_cmds)
        versions = []

        if RCMD.router_type == "cisco_ios" or RCMD.router_type == "cisco_xr":
            i = 0
            for line in dir_device_cmds_result.splitlines():
                try:
                     sub_directory = line.split()[-1]
                     if str(line.split()[1])[0] == 'd' and int(sub_directory):
                         versions.append(sub_directory)
                         output.target_sw_versions.create().name = str(sub_directory)
                         output.target_sw_versions[i].path = str('%s%s/%s' % (RCMD.drive_string, dev_dir, sub_directory))
                         ### del mylist['key1']
                         i += 1
                except: pass

        elif RCMD.router_type == "huawei":
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

        elif RCMD.router_type == "juniper":
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
            xe_device_file_list = [ 'dir %s%s/%s' % (RCMD.drive_string, dev_dir, output.target_sw_versions[i].name) ]
            xr_device_file_list = [ 'dir %s%s/%s' % (RCMD.drive_string, dev_dir, output.target_sw_versions[i].name) ]

            juniper_device_file_list = [ 'file list %s%s/%s detail' % (RCMD.drive_string, dev_dir, output.target_sw_versions[i].name) ]

            file_device_cmds = {
                'cisco_ios':xe_device_file_list,
                'cisco_xr':xr_device_file_list,
                'juniper':juniper_device_file_list,
                'huawei':[]
            }

            file_device_cmds_result = RCMD.run_commands(file_device_cmds)

            if RCMD.router_type == "cisco_ios" or RCMD.router_type == "cisco_xr":
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
                                    files.append('%s%s/%s/%s' % (RCMD.drive_string, dev_dir,output.target_sw_versions[i].name, tar_file))
                    except: pass
                if len(files)>0:
                    output.target_sw_versions[i].files = files

            elif RCMD.router_type == "huawei":
                pass
            elif RCMD.router_type == "juniper":
                pass

            ### GET SMU FILES ON DEVICE VERSION DIRECTORY #########################
            if RCMD.router_type == "cisco_xr":
                xr_device_patch_file_list = [ 'dir %s%s/%s/SMU' % (RCMD.drive_string, dev_dir, output.target_sw_versions[i].name) ]

                patch_file_device_cmds = {
                    'cisco_ios':[],
                    'cisco_xr':xr_device_patch_file_list,
                    'juniper':[],
                    'huawei':[]
                }

                patch_file_device_cmds_result = RCMD.run_commands(patch_file_device_cmds)

                if RCMD.router_type == "cisco_ios":
                    pass
                elif RCMD.router_type == "cisco_xr":
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
                                    patch_files.append('%s%s/%s/%s/%s' % (RCMD.drive_string, dev_dir,output.target_sw_versions[i].name,'SMU' , tar_file))
                                    patch_path = '%s%s/%s/%s' % (RCMD.drive_string, dev_dir,output.target_sw_versions[i].name,'SMU')
                        except: pass
                    if len(patch_files)>0:
                        output.target_sw_versions[i].patch_files = patch_files
                        output.target_sw_versions[i].patch_path = patch_path

                elif RCMD.router_type == "huawei":
                    pass
                elif RCMD.router_type == "juniper":
                    pass

        self.log.info('\nRCMD: ', nso_object_to_string(self, RCMD))
        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        #self.log.info('\nOUTPUT_dump: ', object_dump(self, output))

        #self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))

        del RCMD


# --------------------------
#   OS UPGRADE INSTALL ADD
# --------------------------
class NsoActionsClass_os_upgrade_install_add(Action):
    """Does os upgrade install add definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        asr_admin_string = str()

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        if not RCMD.x64: asr_admin_string = 'admin '

        sw_version_selected_file = str()
        patch_version_selected_files = str()
        file_string_without_path = str()

        output.os_type, output.hw_type = RCMD.os_type, RCMD.hw_type

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
        if RCMD.router_type == "cisco_xr":
            if sw_version_selected_file:
                i_device_cmds = {
                    'cisco_xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                    '/'.join(str(sw_version_selected_file).replace('[','').replace(']','').split()[0].strip().split('/')[:-1]),
                    str(sw_version_selected_file).replace('[','').replace(']','').split()[0].strip().split('/')[-1] )
                    ],
                }
            elif patch_version_selected_files:
                device_cmds = { 'cisco_xr': [ '%sshow install active summary' % (asr_admin_string) ] }
                patch_device_cmds_result = RCMD.run_commands(device_cmds)

                ### PATCH FILE LIST ###########################################
                file_without_path = str()
                file_list = patch_version_selected_files.replace('[','').replace(']','').split()
                for file in file_list:
                    try: file_without_path = file.strip().split('/')[-1]
                    except: file_without_path = str()
                    try: check_CSC_NR = file_without_path.split('.CSC')[1].split('.tar')[0]
                    except: check_CSC_NR = str()
                    ### OMMIT INSTALLATION OF INSTALLED PATCH FILES ###
                    if check_CSC_NR and check_CSC_NR in patch_device_cmds_result: pass
                    elif file_without_path: file_string_without_path += str(file_without_path) + ' '
                file_string_without_path = file_string_without_path.strip()

                if file_string_without_path:
                    i_device_cmds = {
                        'cisco_xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                        '/'.join(str(patch_version_selected_files).replace('[','').replace(']','').split()[0].strip().split('/')[:-1]),
                        file_string_without_path )
                        ]
                    }
            elif patch_version_selected_path:
                device_cmds = { 'cisco_xr': [ '%sshow install active summary' % (asr_admin_string)] }
                patch_device_cmds_result = RCMD.run_commands(device_cmds)

                ### def GET PATHS ON DEVICE ###########################################
                brand_subdir, type_subdir_on_server, type_subdir_on_device, file_types = \
                get_local_subdirectories(brand_raw = 'CISCO', type_raw = RCMD.hw_type )

                self.log.info('FILE_TYPES=', file_types)

                patch_file_device_cmds = {
                    'cisco_ios':[],
                    'cisco_xr':['dir %s' % (patch_version_selected_path)],
                    'juniper':[],
                    'huawei':[]
                }
                patch_file_device_cmds_result = RCMD.run_commands(patch_file_device_cmds)

                patch_files = []
                patch_path = str()
                for line in patch_file_device_cmds_result.splitlines()[:-1]:
                    try:
                        tar_file = line.split()[-1]
                        for file_type in file_types:
                            try: patch_file = file_type.split('/')[1].replace('*','')
                            except: patch_file = str()

                            try: file_without_path = tar_file
                            except: file_without_path = str()
                            try: check_CSC_NR = file_without_path.split('.CSC')[1].split('.tar')[0]
                            except: check_CSC_NR = str()

                            if len(patch_file) > 0 and patch_file.upper() in tar_file.upper():
                                ### OMMIT INSTALLATION OF INSTALLED PATCH FILES ###
                                if check_CSC_NR and check_CSC_NR in patch_device_cmds_result: pass
                                elif file_without_path: patch_files.append('%s' % (tar_file))
                    except: pass
                if len(patch_files) > 0:
                    i_device_cmds = {
                        'cisco_xr':['%sinstall add source %s/ %s' % (asr_admin_string, \
                        patch_version_selected_path,
                        ' '.join(patch_files) )
                        ]
                }

            i_device_cmds_result = RCMD.run_commands(i_device_cmds)

            try:
                output.operation_id = i_device_cmds_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
                output.result = 'success'
            except:
                output.operation_id = str()
                output.completed = 'yes'
                output.result = 'failure'


        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        del RCMD


# -----------------------------------------
#   OS UPGRADE INSTALL ADD PROGRESS CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_progress_check(Action):
    """Does os upgrade install add progress check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.completed = 'no'
        output.result = str()
        asr_admin_string = str()

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        operation_id = str()
        if input.operation_id:
            try: operation_id = str(input.operation_id).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass
        elif input.operation_id_smu:
            try: operation_id = str(input.operation_id_smu).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass

        if not RCMD.x64: asr_admin_string = 'admin '

        if operation_id:
            if RCMD.router_type == "cisco_xr":
                asi_device_cmds = {
                    'cisco_xr':['%sshow install log %s' % (asr_admin_string, operation_id)],
                }

                asi_device_cmds_result = RCMD.run_commands(asi_device_cmds)
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
                    'cisco_xr':['%sshow install log' % (asr_admin_string)],
                }

                device_cmds_result = RCMD.run_commands(device_cmds)

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
        del RCMD


# -----------------------------------------
#   OS UPGRADE DEVICE PING CHECK
# -----------------------------------------
class NsoActionsClass_os_upgrade_device_ping_check(Action):
    """Does os upgrade install device ping check definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.result = 'UNKNOWN'

        ### alternative is nso cmd: 'devices device NYKTR0 ping'

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

        if ip and output.result != 'success':
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

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)

        try: device = str(input.device)
        except: device = str()

        if device:

            cmd = {
                      "cisco_xr":['show running-config interface loopback 0'],
                  }

            cmd_result = RCMD.run_commands(cmd)

            if RCMD.router_type == "cisco_xr":
                try: output.ip_address = cmd_result.split('ipv4 address')[1].split()[0].strip()
                except: output.ip_address = str()

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        del RCMD



# --------------------------
#   OS UPGRADE INSTALL PREPARE
# --------------------------
class NsoActionsClass_os_upgrade_install_prepare(Action):
    """Does os upgrade install prepare definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

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

        if RCMD.x64:
            if operation_id:
                output.os_type, output.hw_type = RCMD.os_type, RCMD.hw_type

                cmd = {
                          #"cisco_ios":['show version'],
                          "cisco_xr":['install prepare id %s' % (operation_id)],
                          #"huawei":['display version'],
                          #"juniper":['show version']
                      }

                cmd_result = RCMD.run_commands(cmd)
                output.install_log = cmd_result

                if RCMD.router_type == "cisco_xr":
                    try: output.operation_id = cmd_result.split(' started')[0].split('Install operation ')[1].split()[0].strip()
                    except: output.operation_id = str()

                self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
            else:
                output.completed = 'yes'
                output.result = 'failure'
                self.log.info('Operation id not inserted!')
        else:
            ### FAKE IAP WORKFLOW in 32BIT ASR9K ###
            output.completed = 'yes'
            output.result = 'success'
            output.operation_id = operation_id
        del RCMD


# --------------------------
#   OS UPGRADE INSTALL ACTIVATE
# --------------------------
class NsoActionsClass_os_upgrade_install_activate(Action):
    """Does os upgrade install activate definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.operation_id = str()
        output.last_command = str()
        output.completed = str()
        output.result = 'failure'
        asr_admin_string = str()

        operation_id = str()

        if input.operation_id:
            try: operation_id = str(input.operation_id).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass
        elif input.operation_id_smu:
            try: operation_id = str(input.operation_id_smu).replace('[','').replace(']','').replace('"','').split(',')[0].strip()
            except: pass

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        if not RCMD.x64: asr_admin_string = 'admin '

        if RCMD.router_type == "cisco_xr":
            if operation_id and not RCMD.x64:
                cmd = { "cisco_xr": [ '%sinstall activate id %s prompt-level none' % (asr_admin_string, operation_id) ] }
            else:
                cmd = { "cisco_xr": [ '%sinstall activate noprompt' % (asr_admin_string) ] }

            cmd_result = RCMD.run_commands(cmd)
            output.install_log = cmd_result

            for i in range(20):
                time.sleep(2)
                device_cmds = {
                    'cisco_xr':[ '%sshow install log | utility tail count 20' % (asr_admin_string) ]
                }
                device_cmds_result = RCMD.run_commands(device_cmds)

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
                                    if 'install activate' in part_last_command:
                                        output.operation_id = part_operation_id
                                        output.last_command = part_last_command
                                elif output.operation_id and int(part_operation_id) >= int(output.operation_id):
                                    if 'install activate' in part_last_command:
                                        output.operation_id = part_operation_id
                                        output.last_command = part_last_command
                        except: pass
                ### CHECK IF LAST OPERATION ID IS 'install activate noprompt' ###
                if part_operation_id and last_operation_id_int > 0 and last_operation_id_int == int(part_operation_id):
                    find_success = True
                if output.last_command and output.operation_id and find_success:
                    output.result = 'success'
                    break

                ### EXIT LOOP AFTER END OF OPERATION ##########################
                device_cmds2 = { 'cisco_xr': [ '%s show install request' % (asr_admin_string) ] }
                device_cmds_result2 = RCMD.run_commands(device_cmds2)
                if 'No install operation in progress' in device_cmds_result2:
                    break

            if not output.last_command and not output.operation_id and not find_success:
                output.install_log = "Problem to find started 'install activate noprompt' in install log!"
                output.completed = 'yes'
                output.result = 'failure'

        self.log.info('\nOUTPUT: ', nso_object_to_string(self, output))
        del RCMD


# --------------------------
#   OS UPGRADE REMOVE INACTIVE
# --------------------------
class NsoActionsClass_os_upgrade_remove_inactive(Action):
    """Does os upgrade remove inactive definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))
        output.hw_type = 'UNKNOWN'
        asr_admin_string = str()

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        if not RCMD.x64: asr_admin_string = 'admin '

        device_cmds = {
            'cisco_xr':['%sinstall remove inactive all' % (asr_admin_string)],
        }

        device_cmds_result = RCMD.run_commands(device_cmds)
        output.log = device_cmds_result

        if RCMD.router_type == "cisco_xr":

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
        del RCMD


# --------------------------
#   OS UPGRADE COMMIT
# --------------------------
class NsoActionsClass_os_upgrade_commit(Action):
    """Does os upgrade commit definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('\nACTION_NAME: ', name, '\nINPUT: ', nso_object_to_string(self, input))

        RCMD = RCMD_class(uinfo = uinfo, input = input, log_info = self.log.info)
        output.hw_type, output.os_type = RCMD.hw_type, RCMD.os_type

        asr_admin_string = str()

        if not RCMD.x64: asr_admin_string = 'admin '

        if RCMD.router_type == "cisco_xr":

            device_cmds = {
                'cisco_xr':['%sinstall commit' % (asr_admin_string)],
            }

            device_cmds_result = RCMD.run_commands(device_cmds)
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
        del RCMD


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
            file_types = ['juniper*.img.gz', 'juniper*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'MX480' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['juniper*.img.gz', 'juniper*.tgz']
            brand_raw_assumed = 'JUNIPER'
        elif 'VMX' in type_raw.upper():
            type_subdir_on_server = 'MX/MX480'
            type_subdir_on_device = '/var/tmp'
            file_types = ['juniper*.img.gz', 'juniper*.tgz']
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











