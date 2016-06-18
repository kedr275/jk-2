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
import traceback
import os
from com.vmware.vcloud.suite.sample.common.platform_service_controller import PlatformServiceController
from com.vmware.vcloud.suite.sample.common.service_manager_factory import ServiceManagerFactory
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext
from com.vmware.vcloud.suite.sample.common.sample_config import SampleConfig

logger = LoggingContext.get_logger(__name__)


class SampleBase(object):
    def __init__(self, description, platformservicecontroller=None, multiplemgmtnode=False):
        if description is None:
            raise Exception('Sample description cannot be empty')
        self.description = description
        # setup the argument parser
        self.argparser = argparse.ArgumentParser(description=description)
        self.argparser.add_argument('-lswsdlurl', '--lswsdlurl', help='Lookup service WSDL URL')
        self.argparser.add_argument('-lssoapurl', '--lssoapurl', help='Lookup service SOAP URL')
        self.argparser.add_argument('-ssousername', '--ssousername', help='SSO user name')
        self.argparser.add_argument('-ssopassword', '--ssopassword', help='SSO user password')
        self.argparser.add_argument('-mgmtinstancename', '--mgmtinstancename',
                                    help='Instance name of the vCenter Server management node. ' + \
                                    'When only one node is registered, it is selected by default; ' + \
                                    'otherwise, omit the parameter to get a list of available nodes.')
        self.argparser.add_argument('-cleardata', '--cleardata', help='Clears the sample data on server after running')
        self.args = None
        self.lswsdlurl = None
        self.lssoapurl = None
        self.ssousername = None
        self.ssopassword = None
        self.multiplemgmtnode = multiplemgmtnode
        # the following two configurations are used when the sample uses a single management node.
        # which is the case for most of our samples. When a sample uses multiple management nodes, the
        # sample has to deal with the management nodes service managers at the sample level.
        self.mgmtinstancename = None
        self.mgmtnodeid = None

        self.cleardata = False
        self.platformservicecontroller = platformservicecontroller

    def parse_args(self):
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and name == '_options':
                attr()  # calling the method
        self.args = self.argparser.parse_args()  # parse all the sample arguments when they are all set

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

        if self.args.cleardata is not None:
            if self.args.cleardata.lower() == 'true':
                self.cleardata = True

    def before(self):
        if self.platformservicecontroller is None:
            self.platformservicecontroller = PlatformServiceController(lswsdlurl=self.lswsdlurl,
                                                                       lssoapurl=self.lssoapurl,
                                                                       ssousername=self.ssousername,
                                                                       ssopassword=self.ssopassword)
            self.platformservicecontroller.login()

        if not self.multiplemgmtnode:
            # the sample is using only a single management node
            # let's use the default management node if there's nothing specified by the user.
            # Note: this will only work when there's a single management node
            if self.mgmtinstancename is None:
                instance_name, node_id = self.platformservicecontroller.lookupservicehelper.get_default_mgmt_node()
                assert node_id is not None
                self.mgmtinstancename = instance_name
                self.mgmtnodeid = node_id
            elif self.mgmtnodeid is None:
                # management instance name is passed by the user
                node_id = self.platformservicecontroller.lookupservicehelper.get_mgmt_node_id(self.mgmtinstancename)
                if node_id is None:
                    # user must have passed an invalid value
                    mgmt_nodes = self.platformservicecontroller.lookupservicehelper.find_mgmt_nodes()
                    message = '{0} is not a valid management node instance name'.format(self.mgmtinstancename) + os.linesep + 'Available management nodes:'
                    for k, v in mgmt_nodes.items():
                        message = message + os.linesep + 'Node name: {0} uuid: {1}'.format(k, v)
                    raise ValueError(message)
                self.mgmtnodeid = node_id
            assert self.mgmtnodeid is not None

        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and name == '_setup':
                attr()  # calling the method

    def run(self):
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and name == '_execute':
                try:
                    attr()  # calling the method
                except Exception as e:
                    # print the exception and move on to the cleanup stage if cleardata is set to True.
                    logger.exception(e)
                    traceback.print_exc()
                    if bool(self.cleardata) is not True:
                        # re-throw the exception
                        raise Exception(e)

    def after(self):
        if bool(self.cleardata) is True:
            for name in dir(self):
                attr = getattr(self, name)
                if callable(attr) and name == '_cleanup':
                    attr()  # calling the method

    def main(self):
        self.parse_args()
        self.before()
        self.run()
        self.after()

    def get_service_manager(self, node_id=None):
        if node_id is None and not self.multiplemgmtnode:
            node_id = self.mgmtnodeid
        assert node_id is not None
        return ServiceManagerFactory.get_service_manager(self.platformservicecontroller, node_id)