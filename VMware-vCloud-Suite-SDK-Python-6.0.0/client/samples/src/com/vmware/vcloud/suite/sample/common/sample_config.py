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

from os import path
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


class SampleConfig(object):
    config = configparser.RawConfigParser()
    config.read(path.join(path.dirname(path.realpath(__file__)), '../../../../../../sample.cfg'))

    @classmethod
    def get_sample_config(cls):
        return cls.config

    @classmethod
    def get_ls_wsdl_url(cls):
        config = SampleConfig.get_sample_config()
        return config.get('connection', 'lswsdlurl')

    @classmethod
    def get_ls_soap_url(cls):
        config = SampleConfig.get_sample_config()
        return config.get('connection', 'lssoapurl')

    @classmethod
    def get_sso_username(cls):
        config = SampleConfig.get_sample_config()
        return config.get('connection', 'ssousername')

    @classmethod
    def get_sso_password(cls):
        config = SampleConfig.get_sample_config()
        return config.get('connection', 'ssopassword')


def main():
    print('lswsdlurl: {0}'.format(SampleConfig.get_ls_wsdl_url()))
    print('lssoapurl: {0}'.format(SampleConfig.get_ls_soap_url()))
    print('ssousername: {0}'.format(SampleConfig.get_sso_username()))
    print('ssopassword: {0}'.format(SampleConfig.get_sso_password()))

# Start program
# just for testing
if __name__ == "__main__":
    main()
