'''
* *******************************************************
* Copyright VMware, Inc. 2013.  All Rights Reserved.
* *******************************************************
*
* DISCLAIMER. THIS PROGRAM IS PROVIDED TO YOU "AS IS" WITHOUT
* WARRANTIES OR CONDITIONS # OF ANY KIND, WHETHER ORAL OR WRITTEN,
* EXPRESS OR IMPLIED. THE AUTHOR SPECIFICALLY # DISCLAIMS ANY IMPLIED
* WARRANTIES OR CONDITIONS OF MERCHANTABILITY, SATISFACTORY # QUALITY,
* NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
'''

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2013 VMware, Inc. All rights reserved.'

from com.vmware.vcloud.suite.sample.common.service_manager import ServiceManager
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.common.service_manager_factory')


class ServiceManagerFactory(object):
    """
    factory class for getting service manager for a management node.
    This class keeps the service manager objects on a dictionary against the management node id
    """
    service_manager_dict = {}

    @classmethod
    def get_service_manager(cls, platform_service_controller, node_id):
        logger.info('Getting service manager for node id: {0}'.format(node_id))
        if cls.service_manager_dict.get(node_id) is None:
            service_manager = ServiceManager(node_id=node_id,
                                             platform_service_controller=platform_service_controller)
            service_manager.connect()
            cls.service_manager_dict[node_id] = service_manager
        return cls.service_manager_dict.get(node_id)

    @classmethod
    def disconnect(cls):
        for service_manager in cls.service_manager_dict.values():
            service_manager.disconnect()

import atexit
atexit.register(ServiceManagerFactory.disconnect)


def main():
    from com.vmware.vcloud.suite.sample.common.platform_service_controller import PlatformServiceController
    platform_service_controller = PlatformServiceController(lswsdlurl='file:///Users/smukhopadhyay/Downloads/lookupservice.wsdl',
                                                            lssoapurl='https://10.160.84.156/lookupservice/sdk',
                                                            ssousername='Administrator@vsphere.local',
                                                            ssopassword='AdminPassword')
    platform_service_controller.login()
    management_nodes = platform_service_controller.lookupservicehelper.find_mgmt_nodes()
    for node_id in management_nodes.values():
        service_manager = ServiceManagerFactory.get_service_manager(platform_service_controller, node_id)
        print(service_manager.session_id)

# Start program
if __name__ == "__main__":
    main()