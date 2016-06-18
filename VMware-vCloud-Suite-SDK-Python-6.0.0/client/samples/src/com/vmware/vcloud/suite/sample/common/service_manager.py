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


from pyVim.connect import SmartConnect, Disconnect
from vmware.vapi.lib import connect
from com.vmware.cis_client import Session
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from vmware.vapi.security.session import create_session_security_context
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.common.service_manager')


class ServiceManager(object):
    """
    Manages all the services on a management node.
    """
    def __init__(self, node_id, platform_service_controller):
        self.platform_service_controller = platform_service_controller
        self.node_id = node_id
        self.instance_name = None

        self.vapi_url = None
        self.vim_url = None
        self.session = None
        self.session_id = None
        self.stub_config = None
        self.si = None
        self.content = None
        self.vim_uuid = None

    def connect(self):
        assert self.node_id is not None
        assert self.platform_service_controller is not None

        self.instance_name = self.platform_service_controller.lookupservicehelper.get_mgmt_node_instance_name(self.node_id)

        # discover the service endpoints from the lookup service on infrastructure node
        self.vapi_url = self.platform_service_controller.lookupservicehelper.find_vapi_url(self.node_id)
        assert self.vapi_url is not None
        self.vim_url = self.platform_service_controller.lookupservicehelper.find_vim_url(self.node_id)
        assert self.vim_url is not None

        # login to vAPI endpoint
        logger.info('Connecting to vapi url: {0}'.format(self.vapi_url))
        connector = connect.get_connector('https', 'json', url=self.vapi_url)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)
        connector.set_security_context(self.platform_service_controller.sec_ctx)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)
        self.session = Session(self.stub_config)
        self.session_id = self.session.create()
        # update the connection with session id
        session_sec_ctx = create_session_security_context(self.session_id)
        connector.set_security_context(session_sec_ctx)

        # pyvmomi
        # extract the host from the vim url
        vim_host = get_url_host(self.vim_url)
        assert vim_host is not None

        self.si = SmartConnect(host=vim_host,
                               user=self.platform_service_controller.ssousername,
                               pwd=self.platform_service_controller.ssopassword)
        assert self.si is not None

        # retrieve the service content
        self.content = self.si.RetrieveContent()
        assert self.content is not None
        self.vim_uuid = self.content.about.instanceUuid

    def disconnect(self):
        logger.info('disconnecting the session: {0}'.format(self.session_id))
        self.session.delete()
        Disconnect(self.si)


def get_url_host(url):
    try:
        from urlparse import urlparse
    except ImportError:
        from urllib.parse import urlparse
    import re
    # parse the URL
    _scheme, netloc, _path, _params, _query, _fragment = urlparse(url)
    if netloc is not None:
        p = '(?P<host>[^:/ ]+).?(?P<port>[0-9]*)'
        m = re.search(p, netloc)
        host = m.group('host')
        return host
    return None