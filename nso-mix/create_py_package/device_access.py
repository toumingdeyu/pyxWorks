# -*- mode: python; python-indent: 4 -*-
import ncs
#from ncs.application import Service

def device_command(self, uinfo, input, device, cmd_data):
    """
    Run device_command and return result as string.
    """
    result = str()
    m = ncs.maapi.Maapi()
    with m.start_read_trans(usid=uinfo.usid) as t:
        root = ncs.maagic.get_root(t)
        dev = root.ncs__devices.device[input.device]
        try:
            ### Cisco XE platform #############################################
            if dev.platform.name == "ios-xe" and cmd_data.get("ios-xe"):
                command = dev.live_status.ios_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xe"), (list,tuple)):
                    command.args = cmd_data.get("ios-xe")
                else: command.args = [ cmd_data.get("ios-xe") ]

                command_output = dev.live_status.ios_stats__exec.any(command)
                self.log.info('OUTPUT: {}'.format(command_output.result))
                result = command_output.result

            ### Cisco XR platform #############################################
            elif dev.platform.name == "ios-xr" and cmd_data.get("ios-xr"):
                command = dev.live_status.cisco_ios_xr_stats__exec.show.get_input()

                if isinstance(cmd_data.get("ios-xr"), (list,tuple)):
                    command.args = cmd_data.get("ios-xr")
                else: command.args = [ cmd_data.get("ios-xr") ]

                command_output = dev.live_status.cisco_ios_xr_stats__exec.any(command)  # nopep8
                self.log.info('OUTPUT: {}'.format(command_output.result))
                result = command_output.result

            ### Huawei platform ###############################################
            elif dev.platform.name == "huawei-vrp" and cmd_data.get("huawei-vrp"):
                command = dev.live_status.vrp_stats__exec.get_input()

                if isinstance(cmd_data.get("huawei-vrp"), (list,tuple)):
                    command.args = cmd_data.get("huawei-vrp")
                else: command.args = [ cmd_data.get("huawei-vrp") ]

                command_output = dev.live_status.vrp_stats__exec.any(command)
                self.log.info('OUTPUT: {}'.format(command_output.result))
                result = command_output.result

            ### Juniper platform ##############################################
            elif dev.platform.name == "junos" and cmd_data.get("junos"):
                command_input = dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.get_input()

                #command_input.command = 'cli show version \| match Junos'
                if isinstance(cmd_data.get("junos"), (list,tuple)):
                    command.args = []
                    for item in cmd_data.get("junos"):
                        command.args.append('cli ' + item.replace('|','\|'))
                else: command.args = [ 'cli ' + cmd_data.get("junos").replace('|','\|') ]

                self.log.info(command_input.command)
                command_output = dev.rpc.jrpc__rpc_request_shell_execute.request_shell_execute.request(command_input)
                self.log.info(command_output.output)
                result = command_output.output

        except Exception as E:
            self.log.info("Exception device_command(): ", str(E))

    m.close()
    return result

