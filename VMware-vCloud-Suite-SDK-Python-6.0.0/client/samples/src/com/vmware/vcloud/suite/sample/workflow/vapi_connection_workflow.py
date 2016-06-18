'''
* *******************************************************
* Copyright VMware, Inc. 2014.  All Rights Reserved.
* *******************************************************
*
* DISCLAIMER. THIS PROGRAM IS PROVIDED TO YOU "AS IS" WITHOUT
* WARRANTIES OR CONDITIONS # OF ANY KIND, WHETHER ORAL OR WRITTEN,
* EXPRESS OR IMPLIED. THE AUTHOR SPECIFICALLY # DISCLAIMS ANY IMPLIED
* WARRANTIES OR CONDITIONS OF MERCHANTABILITY, SATISFACTORY # QUALITY,
* NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
'''

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2014 VMware, Inc. All rights reserved.'

import argparse
from vmware.vapi.lib import connect
from com.vmware.cis_client import Session
from vmware.vapi.security.user_password import create_user_password_security_context
from vmware.vapi.security.session import create_session_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.cis.tagging_client import Tag
from com.vmware.vcloud.suite.sample.common.lookup_service_helper import LookupServiceHelper
from com.vmware.vcloud.suite.sample.common.sample_config import SampleConfig
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.workflow.vapi_connection_workflow')


class VapiConnectionWorkflow(object):
    """
    Demonstrates vAPI connection and service initialization callflow using the username and password
    Step 1: Retrieve the vAPI service endpoint URL from lookup service.
    Step 2: Connect to the vAPI service endpoint.
    Step 3: Use the username/password to login to the vAPI service endpoint.
    Step 4: Create a vAPI session.
    Step 5: Validate some of the vAPI services.
    Step 6: Delete the vAPI session.
    """

    def __init__(self):
        self.lswsdlurl = None
        self.lssoapurl = None
        self.mgmtinstancename = None  # Optional: used when there are more than one mgmt node
        self.ssousername = None
        self.ssopassword = None

        self.mgmtnodeid = None
        self.vapiurl = None
        self.session = None
        self.session_id = None
        self.stub_config = None

    def options(self):
        self.argparser = argparse.ArgumentParser(description=self.__doc__)
        # setup the argument parser
        self.argparser.add_argument('-lswsdlurl', '--lswsdlurl', help='Lookup service WSDL URL')
        self.argparser.add_argument('-lssoapurl', '--lssoapurl', help='Lookup service SOAP URL')
        self.argparser.add_argument('-mgmtinstancename', '--mgmtinstancename',
                                    help='Instance name of the vCenter Server management node. ' + \
                                    'When only one node is registered, it is selected by default; ' + \
                                    'otherwise, omit the parameter to get a list of available nodes.')
        self.argparser.add_argument('-ssousername', '--ssousername', help='SSO user name')
        self.argparser.add_argument('-ssopassword', '--ssopassword', help='SSO user password')
        self.args = self.argparser.parse_args()   # parse all the sample arguments when they are all set

    def setup(self):
        if self.args.lswsdlurl is None:
            self.lswsdlurl = SampleConfig.get_ls_wsdl_url()  # look for lookup service WSDL in the sample config
        else:
            self.lswsdlurl = self.args.lswsdlurl
        assert self.lswsdlurl is not None
        logger.info('lswsdlurl: {0}'.format(self.lswsdlurl))

        if self.args.lssoapurl is None:
            self.lssoapurl = SampleConfig.get_ls_soap_url()  # look for lookup service SOAP URL in the sample config
        else:
            self.lssoapurl = self.args.lssoapurl
        assert self.lssoapurl is not None
        logger.info('lssoapurl: {0}'.format(self.lssoapurl))

        if self.args.ssousername is None:
            self.ssousername = SampleConfig.get_sso_username()  # look for sso user name in the sample config
        else:
            self.ssousername = self.args.ssousername
        assert self.ssousername is not None

        if self.args.ssopassword is None:
            self.ssopassword = SampleConfig.get_sso_password()  # look for sso password in the sample config
        else:
            self.ssopassword = self.args.ssopassword
        assert self.ssopassword is not None

        if self.mgmtinstancename is None:
            self.mgmtinstancename = self.args.mgmtinstancename

    def execute(self):
        logger.info('Connecting to lookup service url: {0}'.format(self.lssoapurl))
        lookupservicehelper = LookupServiceHelper(wsdl_url=self.lswsdlurl, soap_url=self.lssoapurl)
        lookupservicehelper.connect()

        if self.mgmtinstancename is None:
            self.mgmtinstancename, self.mgmtnodeid = lookupservicehelper.get_default_mgmt_node()
        elif self.mgmtnodeid is None:
            self.mgmtnodeid = lookupservicehelper.get_mgmt_node_id(self.mgmtinstancename)
        assert self.mgmtnodeid is not None

        self.vapiurl = lookupservicehelper.find_vapi_url(self.mgmtnodeid)
        logger.info('vapi_url: {0}'.format(self.vapiurl))

        logger.info('Connecting to VAPI endpoint and preparing stub configuration...')
        connector = connect.get_connector('https', 'json', url=self.vapiurl)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)

        sec_ctx = create_user_password_security_context(self.ssousername, self.ssopassword)
        connector.set_security_context(sec_ctx)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)
        self.session = Session(self.stub_config)

        logger.info('Login to VAPI endpoint and get the session_id...')
        self.session_id = self.session.create()

        logger.info('Update the VAPI connection with session_id...')
        session_sec_ctx = create_session_security_context(self.session_id)
        connector.set_security_context(session_sec_ctx)

        # make sure you can access some of the VAPI services
        tag_svc = Tag(self.stub_config)
        logger.info('List all the existing tags user has access to...')
        tags = tag_svc.list()
        if len(tags) > 0:
            for tag in tags:
                logger.info('Found Tag: {0}'.format(tag))
        else:
            logger.info('No Tag Found...')

    def cleanup(self):
        if self.session_id is not None:
            self.disconnect()
            logger.info('VAPI session disconnected successfully...')

    def disconnect(self):
        self.session.delete()


def main():
    vapiConnectionWorkflow = VapiConnectionWorkflow()
    vapiConnectionWorkflow.options()
    vapiConnectionWorkflow.setup()
    vapiConnectionWorkflow.execute()
    vapiConnectionWorkflow.cleanup()

# Start program
if __name__ == "__main__":
    main()
