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

import argparse
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
from com.vmware.vcloud.suite.sample.common import sso
from vmware.vapi.lib import connect
from com.vmware.cis_client import Session
from vmware.vapi.security.sso import create_saml_bearer_security_context
from vmware.vapi.security.session import create_session_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.workflow.connection_workflow')


class ConnectionWorkflow(object):
    """
    Demonstrates vAPI connection and service initialization callflow
    Step 1: Connect to the SSO URL and retrieve the SAML token.
    Step 2: Connect to the vapi service endpoint.
    Step 3: Use the SAML token to login to vAPI service endpoint.
    Step 4: Create a vAPI session.
    Step 5: Delete the vAPI session.
    Note: Use the lookup service print services sample to retrieve the SSO and vAPI service URLs
    """

    def __init__(self):
        self.vapi_url = None
        self.sts_url = None
        self.sso_username = None
        self.sso_password = None
        self.session = None

    def options(self):
        self.argparser = argparse.ArgumentParser(description=self.__doc__)
        # setup the argument parser
        self.argparser.add_argument('-vapiurl', '--vapiurl', help='vAPI URL')
        self.argparser.add_argument('-stsurl', '--stsurl', help='SSO URL')
        self.argparser.add_argument('-ssousername', '--ssousername', help='SSO username')
        self.argparser.add_argument('-ssopassword', '--ssopassword', help='SSO user password')
        self.args = self.argparser.parse_args()   # parse all the sample arguments when they are all set

    def setup(self):
        self.vapi_url = self.args.vapiurl
        assert self.vapi_url is not None
        self.sts_url = self.args.stsurl
        assert self.sts_url is not None
        self.sso_username = self.args.ssousername
        assert self.sso_username is not None
        self.sso_password = self.args.ssopassword
        assert self.sso_password is not None

    def execute(self):
        logger.info('vapi_url: {0}'.format(self.vapi_url))
        # parse the URL and determine the scheme
        o = urlparse(self.vapi_url)
        assert o.scheme is not None
        if o.scheme.lower() != 'https':
            logger.error('VAPI URL must be a https URL')
            raise Exception('VAPI URL must be a https URL')

        logger.info('sts_url: {0}'.format(self.sts_url))
        logger.info('Initialize SsoAuthenticator and fetching SAML bearer token...')
        authenticator = sso.SsoAuthenticator(self.sts_url)
        bearer_token = authenticator.get_bearer_saml_assertion(self.sso_username, self.sso_password, delegatable=True)

        logger.info('Creating SAML Bearer Security Context...')
        sec_ctx = create_saml_bearer_security_context(bearer_token)

        logger.info('Connecting to VAPI provider and preparing stub configuration...')
        connector = connect.get_connector('https', 'json', url=self.vapi_url)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)

        connector.set_security_context(sec_ctx)
        self.stub_config = StubConfigurationFactory.new_std_configuration(connector)
        self.session = Session(self.stub_config)

        logger.info('Login to VAPI endpoint and get the session_id...')
        self.session_id = self.session.create()

        logger.info('Update the VAPI connection with session_id...')
        session_sec_ctx = create_session_security_context(self.session_id)
        connector.set_security_context(session_sec_ctx)

    def cleanup(self):
        if self.session_id is not None:
            self.disconnect()
            logger.info('VAPI session disconnected successfully...')

    def disconnect(self):
        self.session.delete()


def main():
    connectionWorkflow = ConnectionWorkflow()
    connectionWorkflow.options()
    connectionWorkflow.setup()
    connectionWorkflow.execute()
    connectionWorkflow.cleanup()

# Start program
if __name__ == "__main__":
    main()
