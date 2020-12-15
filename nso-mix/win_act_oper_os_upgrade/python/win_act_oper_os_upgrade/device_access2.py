# -*- mode: python; python-indent: 4 -*-
import ncs
#from ncs.application import Service
import collections


class RCMD(object):

    @staticmethod
    def connect(device = None, **kwargs):
        input_device = str()
        if device: input_device = device

        input = kwargs.get('input')
        uinfo = kwargs.get('uinfo')

        if input:
            if input.device: input_device = input.device
            elif input.ip: input_device = input.ip
            elif input.device_iap.device: input_device = input.device_iap.device

        if input_device and uinfo:
            RCMD.m = ncs.maapi.Maapi()
            RCMD.t = RCMD.m.start_read_trans(usid = uinfo.usid)
            RCMD.root = ncs.maagic.get_root(t)
            RCMD.dev = root.ncs__devices.device[input_device]

            if RCMD.dev.platform.name:
                RCMD.hw_info['os_type'] = str(dev.platform.name)
                if RCMD.dev.platform.name == "ios-xe": RCMD.router_type = 'cisco_ios'
                elif RCMD.dev.platform.name == "ios-xr": RCMD.router_type = 'cisco_xr'
                elif RCMD.dev.platform.name == "junos": RCMD.router_type = 'juniper'
                elif RCMD.dev.platform.name == "huawei-vrp": RCMD.router_type = 'huawei'

                cmd = {
                          "ios-xe":['show version'],
                          "ios-xr":['show version'],
                          "huawei-vrp":['display version'],
                          "junos":['show version']
                      }

                RCMD.hw_info = {}
                RCMD.hw_info['device'] = copy.deepcopy(input_device)

                result = RCMD.run_commands(cmd)

                if RCMD.hw_info.get('os_type') == "ios-xe":
                    RCMD.hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
                    RCMD.hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
                    RCMD.hw_info['hw_brand'] = 'CISCO'
                    RCMD.hw_info['drive_string'] = 'bootflash:'

                elif RCMD.hw_info.get('os_type') == "ios-xr":
                    RCMD.hw_info['sw_version'] = result.split('Software, Version')[1].split()[0].strip()
                    RCMD.hw_info['hw_type'] = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()
                    RCMD.hw_info['hw_brand'] = 'CISCO'
                    RCMD.hw_info['drive_string'] = 'harddisk:'

                elif RCMD.hw_info.get('os_type') == "huawei-vrp":
                    RCMD.hw_info['sw_version'] = result.split('software, Version')[1].split()[0].strip()
                    RCMD.hw_info['hw_type'] = result.split(' version information:')[0].splitlines()[-1].strip()
                    RCMD.hw_info['hw_brand'] = 'HUAWEI'
                    RCMD.hw_info['drive_string'] = 'cfcard:'

                elif RCMD.hw_info.get('os_type') == "junos":
                    RCMD.hw_info['sw_version'] = result.split('Junos: ')[1].split()[0].strip()
                    RCMD.hw_info['hw_type'] = result.split('Model: ')[1].split()[0].strip()
                    RCMD.hw_info['hw_brand'] = 'JUNIPER'
                    RCMD.hw_info['drive_string'] = 're0:'


    @staticmethod
    def disconnect():
        try: RCMD.m.close()
        except: pass

    @staticmethod
    def run_commands(cmd, **kwargs):
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
            ### accept paramiko's device type strings ###
            if cmd_data.get('cisco_ios'): cmd_data["ios-xe"] = cmd_data.get('cisco_ios')
            if cmd_data.get('cisco_xr'): cmd_data["ios-xr"] = cmd_data.get('cisco_xr')
            if cmd_data.get('juniper'): cmd_data["junos"] = cmd_data.get('juniper')
            if cmd_data.get('huawei'): cmd_data["huawei-vrp"] = cmd_data.get('huawei')
            cmd_data = cmd

        try:
            ### Cisco XE platform #############################################
            if RCMD.dev.platform.name == "ios-xe" and cmd_data.get("ios-xe"):
                command = RCMD.dev.live_status.ios_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xe"), (list,tuple)):
                    command.args = cmd_data.get("ios-xe")
                else: command.args = [ cmd_data.get("ios-xe",str()) ]

                command_output = RCMD.dev.live_status.ios_stats__exec.any(command)
                result = command_output.result

            ### Cisco XR platform #############################################
            elif RCMD.dev.platform.name == "ios-xr" and cmd_data.get("ios-xr"):
                command = RCMD.dev.live_status.cisco_ios_xr_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xr"), (list,tuple)):
                    command.args = cmd_data.get("ios-xr")
                else: command.args = [ cmd_data.get("ios-xr",str()) ]

                command_output = RCMD.dev.live_status.cisco_ios_xr_stats__exec.any(command)  # nopep8
                result = command_output.result

            ### Huawei platform ###############################################
            elif RCMD.dev.platform.name == "huawei-vrp" and cmd_data.get("huawei-vrp"):
                command = RCMD.dev.live_status.vrp_stats__exec.display.get_input()

                if isinstance(cmd_data.get("huawei-vrp"), (list,tuple)):
                    command.args = cmd_data.get("huawei-vrp")
                else: command.args = [ cmd_data.get("huawei-vrp",str()) ]

                command_output = RCMD.dev.live_status.vrp_stats__exec.any(command)
                result = command_output.result

            ### Juniper platform ##############################################
            elif RCMD.dev.platform.name == "junos" and cmd_data.get("junos"):
                command_input = RCMD.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.get_input()

                if isinstance(cmd_data.get("junos"), (list,tuple)):
                    for item in cmd_data.get("junos"):
                        command_input.command = 'cli ' + item.replace('|','\|')
                        command_output = RCMD.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                        result = result + '\n' + command_output.output
                else:
                    command_input.command = [ 'cli ' + cmd_data.get("junos",str()).replace('|','\|') ]
                    command_output = RCMD.dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                    result = command_output.output

            self.log.info('\nREMOTE_COMMAND({}): {}\n{}\n'.format(RCMD.dev.platform.name,str(cmd),result))
        except Exception as E:
            self.log.info("\nEXCEPTION in REMOTE_COMMAND({}):{}\n{}".format(RCMD.dev.platform.name, str(cmd), str(E)))
        return result





###############################################################################

# def object_to_string(self, object):
    # """ Printable representation of object variables."""
    # return_string = str(eval("str(object)")) + ':\n'
    # for item in dir(object):
        # if '_' in str(item[0]) and '_' in str(item[-1]): pass
        # else:
            # try: return_string += "\\___" + str(item) + '=' + str(eval("object.%s" % str(item))) + '\n'
            # except: return_string += '\\____...\n'
    # return return_string

###############################################################################