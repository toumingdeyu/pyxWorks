# -*- mode: python; python-indent: 4 -*-
import ncs
#from ncs.application import Service
import collections
import time, copy


class RCMD_class():

    def __del__(self):
        try: self.m.close()
        except: pass
        time.sleep(0.3)

    def __init__(self, device = None, **kwargs):
        self.input_device, self.router_type = str(), str()
        self.device, self.os_type = str(), str()
        self.hw_brand, self.drive_string = str(), str()
        self.sw_version = str()
        self.ip = str()
        self.port = str()

        if device: self.input_device = device

        self.input = kwargs.get('input')
        self.uinfo = kwargs.get('uinfo')
        self.log_info = kwargs.get('log_info')

        if self.input:
            if self.input.device: self.input_device = self.input.device
            elif self.input.ip: self.input_device = self.input.ip
            elif self.input.device_iap.device: self.input_device = self.input.device_iap.device

        if self.input_device and self.uinfo:
            self.m = ncs.maapi.Maapi()
            self.t = self.m.start_read_trans(usid = self.uinfo.usid)
            self.root = ncs.maagic.get_root(self.t)
            self.dev = self.root.ncs__devices.device[self.input_device]

            if self.dev.platform.name:

                try: self.ip  = self.root.ncs__devices.device[self.input_device].address
                except: pass

                try: self.port  = self.root.ncs__devices.device[self.input_device].port
                except: pass

                ### NSO OS TYPE ###
                self.os_type = str(self.dev.platform.name)
                ### PARAMIKO/NETMIKO OS TYPE ###
                if self.dev.platform.name == "ios-xe": self.router_type = 'cisco_ios'
                elif self.dev.platform.name == "ios-xr": self.router_type = 'cisco_xr'
                elif self.dev.platform.name == "junos": self.router_type = 'juniper'
                elif self.dev.platform.name == "huawei-vrp": self.router_type = 'huawei'

                cmd = {
                          "ios-xe":['show version'],
                          "ios-xr":['show version'],
                          "huawei-vrp":['display version'],
                          "junos":['show version']
                      }

                self.device = str(self.input_device)

                result = self.run_commands(cmd)

                if self.os_type == "ios-xe":
                    try: self.sw_version = str(result.split('Software, Version')[1].split()[0].strip())
                    except:
                        try: self.sw_version = str(result.split('Version      :')[1].split()[0].strip())
                        except: pass
                    try: self.hw_type = str(result.split(') processor')[0].splitlines()[-1].split('(')[0].strip())
                    except: pass
                    self.hw_brand = 'CISCO'
                    self.drive_string = 'bootflash:'

                elif self.os_type == "ios-xr":
                    try: self.sw_version = str(result.split('Software, Version')[1].split()[0].strip())
                    except:
                        try: self.sw_version = str(result.split('Version      :')[1].split()[0].strip())
                        except: pass
                    try: self.hw_type = str(result.split(') processor')[0].splitlines()[-1].split('(')[0].strip())
                    except: pass
                    self.hw_brand = 'CISCO'
                    self.drive_string = 'harddisk:'
                    cmd = {
                          "ios-xe":[],
                          "ios-xr":['show instal active summary'],
                          "huawei-vrp":[],
                          "junos":[]
                    }
                    result = self.run_commands(cmd)
                    if '-x64-' in result: self.x64 = True
                    else: self.x64 = False
                    if 'IOS-XRv' in self.hw_type or 'NCS' in self.hw_type: self.x64 = True


                elif self.os_type == "huawei-vrp":
                    try: self.sw_version = str(result.split('software, Version')[1].split()[0].strip())
                    except: pass
                    try: self.hw_type = str(result.split(' version information:')[0].splitlines()[-1].strip())
                    except: pass
                    self.hw_brand = 'HUAWEI'
                    self.drive_string= 'cfcard:'

                elif self.os_type == "junos":
                    try: self.sw_version = str(result.split('Junos: ')[1].split()[0].strip())
                    except: pass
                    try: self.hw_type = str(result.split('Model: ')[1].split()[0].strip())
                    except: pass
                    self.hw_brand = 'JUNIPER'
                    self.drive_string = 're0:'
                time.sleep(0.1)
        #if self.log_info: self.log_info('\n__VARS(self):[{}]\n'.format(vars(self)))


    def run_commands(self, cmd, **kwargs):
        """
        Run device_command and return result as string.
        IMPORT: from .device_access import *
        """

        if not hasattr(__builtins__, "basestring"): basestring = (str, bytes)

        result = str()

        if isinstance(cmd, (basestring)):
            cmd_data = {}
            cmd_data["ios-xe"] = [ cmd ]
            cmd_data["ios-xr"] = [ cmd ]
            cmd_data["huawei-vrp"] = [ cmd ]
            cmd_data["junos"] = [ cmd ]
        elif isinstance(cmd, (list,tuple)):
            cmd_data = {}
            cmd_data["ios-xe"] = cmd
            cmd_data["ios-xr"] = cmd
            cmd_data["huawei-vrp"] = cmd
            cmd_data["junos"] = cmd
        elif isinstance(cmd, (dict,collections.OrderedDict)):
            cmd_data = cmd
            ### accept paramiko's device type strings ###
            if cmd_data.get('cisco_ios'): cmd_data["ios-xe"] = cmd_data.get('cisco_ios')
            if cmd_data.get('cisco_xr'): cmd_data["ios-xr"] = cmd_data.get('cisco_xr')
            if cmd_data.get('juniper'): cmd_data["junos"] = cmd_data.get('juniper')
            if cmd_data.get('huawei'): cmd_data["huawei-vrp"] = cmd_data.get('huawei')

        try:
            ### Cisco XE platform #############################################
            if self.dev.platform.name == "ios-xe" and cmd_data.get("ios-xe"):
                command = self.dev.live_status.ios_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xe"), (list,tuple)):
                    command.args = cmd_data.get("ios-xe")
                else: command.args = [ cmd_data.get("ios-xe",str()) ]

                command_output = self.dev.live_status.ios_stats__exec.any(command)
                result = command_output.result

            ### Cisco XR platform #############################################
            elif self.dev.platform.name == "ios-xr" and cmd_data.get("ios-xr"):
                command = self.dev.live_status.cisco_ios_xr_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xr"), (list,tuple)):
                    command.args = cmd_data.get("ios-xr")
                else: command.args = [ cmd_data.get("ios-xr",str()) ]

                command_output = self.dev.live_status.cisco_ios_xr_stats__exec.any(command)  # nopep8
                result = command_output.result

            ### Huawei platform ###############################################
            elif self.dev.platform.name == "huawei-vrp" and cmd_data.get("huawei-vrp"):
                command = self.dev.live_status.vrp_stats__exec.display.get_input()

                if isinstance(cmd_data.get("huawei-vrp"), (list,tuple)):
                    command.args = cmd_data.get("huawei-vrp")
                else: command.args = [ cmd_data.get("huawei-vrp",str()) ]

                command_output = self.dev.live_status.vrp_stats__exec.any(command)
                result = command_output.result

            ### Juniper platform ##############################################
            elif self.dev.platform.name == "junos" and cmd_data.get("junos"):
                command_input = self.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.get_input()

                if isinstance(cmd_data.get("junos"), (list,tuple)):
                    for item in cmd_data.get("junos"):
                        command_input.command = 'cli ' + item.replace('|','\|')
                        command_output = self.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                        result = result + '\n' + command_output.output
                else:
                    command_input.command = [ 'cli ' + cmd_data.get("junos",str()).replace('|','\|') ]
                    command_output = self.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                    result = command_output.output

            if self.log_info: self.log_info('\nREMOTE_COMMAND({}): {}\n{}\n'.format(self.dev.platform.name,str(cmd),result))
        except Exception as E:
            if self.log_info: self.log_info("\nEXCEPTION in REMOTE_COMMAND({}):{}\n{}".format(self.dev.platform.name, str(cmd), str(E)))
        return copy.deepcopy(result)

