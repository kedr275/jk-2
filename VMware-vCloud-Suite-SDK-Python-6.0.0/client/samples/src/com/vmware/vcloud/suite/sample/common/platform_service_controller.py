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


from com.vmware.vcloud.suite.sample.common import sso
from vmware.vapi.security.sso import create_saml_bearer_security_context
from com.vmware.vcloud.suite.sample.common.lookup_service_helper import LookupServiceHelper
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.common.platform_service_controller')


class PlatformServiceController(object):
    """
    Manages services on the infrastructure node (e.g. lookup service, SSO etc.)
    """
    def __init__(self, lswsdlurl, lssoapurl, ssousername, ssopassword):
        self.lswsdlurl = lswsdlurl
        self.lssoapurl = lssoapurl
        self.ssousername = ssousername
        self.ssopassword = ssopassword
        self.lookupservicehelper = None
        self.stsurl = None
        self.bearer_token = None  # SAML bearer token
        self.sec_ctx = None  # Security context

    def login(self):
        """
        Finds the SSO URL from the lookup service and retrieves the SAML token from STS URL
        """
        logger.info('Connecting to lookup service url: {0}'.format(self.lssoapurl))
        self.lookupservicehelper = LookupServiceHelper(wsdl_url=self.lswsdlurl, soap_url=self.lssoapurl)
        self.lookupservicehelper.connect()

        self.stsurl = self.lookupservicehelper.find_sso_url()
        assert self.stsurl is not None

        logger.info('Retrieving a SAML bearer token from STS url : {0}'.format(self.stsurl))
        au = sso.SsoAuthenticator(self.stsurl)
        self.bearer_token = au.get_bearer_saml_assertion(
            self.ssousername, self.ssopassword, delegatable=True)
        self.sec_ctx = create_saml_bearer_security_context(self.bearer_token)