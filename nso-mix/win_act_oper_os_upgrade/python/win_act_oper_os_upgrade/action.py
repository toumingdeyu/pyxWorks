# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.dp import Action
from .nso_actions import *
from ncs.application import Service


# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')


    # The pre_modification() and post_modification() callbacks are optional,
    # and are invoked outside FASTMAP. pre_modification() is invoked before
    # create, update, or delete of the service, as indicated by the enum
    # ncs_service_operation op parameter. Conversely
    # post_modification() is invoked after create, update, or delete
    # of the service. These functions can be useful e.g. for
    # allocations that should be stored and existing also when the
    # service instance is removed.

    # @Service.pre_lock_create
    # def cb_pre_lock_create(self, tctx, root, service, proplist):
    #     self.log.info('Service plcreate(service=', service._path, ')')

    # @Service.pre_modification
    # def cb_pre_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')

    # @Service.post_modification
    # def cb_post_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Action(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Action RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('win_act_oper_os_upgrade-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).


        self.register_action('get_sw_version', NsoActionsClass_get_sw_version)
        self.register_action('os_upgrade_precheck', NsoActionsClass_os_upgrade_precheck)
        self.register_action('os_upgrade_install_add', NsoActionsClass_os_upgrade_install_add)
        self.register_action('os_upgrade_install_add_progress_check', NsoActionsClass_os_upgrade_install_add_progress_check)
        self.register_action('os_upgrade_install_prepare', NsoActionsClass_os_upgrade_install_prepare)
        self.register_action('os_upgrade_install_prepare_progress_check', NsoActionsClass_os_upgrade_install_prepare_progress_check)
        self.register_action('os_upgrade_install_activate', NsoActionsClass_os_upgrade_install_activate)
        self.register_action('os_upgrade_install_activate_progress_check', NsoActionsClass_os_upgrade_install_activate_progress_check)
        self.register_action('os_upgrade_postcheck', NsoActionsClass_os_upgrade_postcheck)


        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Action FINISHED')
