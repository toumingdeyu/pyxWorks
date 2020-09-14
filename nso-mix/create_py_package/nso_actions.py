# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.dp import Action
from ncs.application import Service
from .device_access import *
import collections

### IMPORT: from .nso_actions import *    ###


# --------------------------
#   GET SW VERSION ACTION
# --------------------------
class Oti_Get_Sw_Version(Action):
    """Get sw version action definition."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        output.os_type = 'UNKNOWN'
        output.hw_type = 'UNKNOWN'
        output.sw_version = 'UNKNOWN'
        output.target_sw_version = 'UNKNOWN'
        output.path_to_target_sw = 'UNKNOWN'

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

        elif output.os_type == "ios-xr":
            output.sw_version = result.split('Software, Version')[1].split()[0].strip()
            output.hw_type = result.split(') processor')[0].splitlines()[-1].split('(')[0].strip()

        elif output.os_type == "huawei-vrp":
            output.sw_version = result.split('software, Version')[1].split()[0].strip()
            output.hw_type = result.split(' version information:')[0].splitlines()[-1].strip()

        elif output.os_type == "junos":
            output.sw_version = result.split('Junos: ')[1].split()[0].strip()
            output.hw_type = result.split('Model: ')[1].split()[0].strip()

