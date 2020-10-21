# -*- mode: python; python-indent: 4 -*-
import ncs
#from ncs.application import Service
import collections

def device_command(self, uinfo, input, cmd):
    """
    Run device_command and return result as string.
    IMPORT: from .device_access import *
    """

    if not hasattr(__builtins__, "basestring"): basestring = (str, bytes)

    result = str()
    platform = str()

    m = ncs.maapi.Maapi()
    with m.start_read_trans(usid=uinfo.usid) as t:
        root = ncs.maagic.get_root(t)
        dev = root.ncs__devices.device[input.device]

        self.log.info('DEV: ', object_to_string(self, dev))

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

        try:
            if dev.platform.name: platform = str(dev.platform.name)

            ### Cisco XE platform #############################################
            if dev.platform.name == "ios-xe" and cmd_data.get("ios-xe"):
                command = dev.live_status.ios_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xe"), (list,tuple)):
                    command.args = cmd_data.get("ios-xe")
                else: command.args = [ cmd_data.get("ios-xe",str()) ]

                command_output = dev.live_status.ios_stats__exec.any(command)
                result = command_output.result

            ### Cisco XR platform #############################################
            elif dev.platform.name == "ios-xr" and cmd_data.get("ios-xr"):
                command = dev.live_status.cisco_ios_xr_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xr"), (list,tuple)):
                    command.args = cmd_data.get("ios-xr")
                else: command.args = [ cmd_data.get("ios-xr",str()) ]

                command_output = dev.live_status.cisco_ios_xr_stats__exec.any(command)  # nopep8
                result = command_output.result

            ### Huawei platform ###############################################
            elif dev.platform.name == "huawei-vrp" and cmd_data.get("huawei-vrp"):
                command = dev.live_status.vrp_stats__exec.display.get_input()

                if isinstance(cmd_data.get("huawei-vrp"), (list,tuple)):
                    command.args = cmd_data.get("huawei-vrp")
                else: command.args = [ cmd_data.get("huawei-vrp",str()) ]

                command_output = dev.live_status.vrp_stats__exec.any(command)
                result = command_output.result

            ### Juniper platform ##############################################
            elif dev.platform.name == "junos" and cmd_data.get("junos"):
                command_input = dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.get_input()

                if isinstance(cmd_data.get("junos"), (list,tuple)):
                    for item in cmd_data.get("junos"):
                        command_input.command = 'cli ' + item.replace('|','\|')
                        command_output = dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                        result = result + '\n' + command_output.output
                else:
                    command_input.command = [ 'cli ' + cmd_data.get("junos",str()).replace('|','\|') ]
                    command_output = dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                    result = command_output.output

            self.log.info('\nREMOTE_COMMAND({}): {}\n{}\n'.format(dev.platform.name,str(cmd),result))
        except Exception as E:
            self.log.info("\nEXCEPTION in device_command(): ", str(E))

    m.close()   
    return result, platform

###############################################################################

def object_to_string(self, object):
    """ Printable representation of object variables."""
    return_string = str(eval("str(object)")) + ':\n'
    for item in dir(object):
        if '_' in str(item[0]) and '_' in str(item[-1]): pass
        else:
            try: return_string += "\\___" + str(item) + '=' + str(eval("object.%s" % str(item))) + '\n'
            except: return_string += '\\____...\n'
    return return_string
    
###############################################################################    