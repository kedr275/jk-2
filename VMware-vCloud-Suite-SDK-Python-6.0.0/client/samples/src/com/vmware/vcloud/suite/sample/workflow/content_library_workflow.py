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

import os
import time
import tempfile
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2
from com.vmware.content_client import (
    Library, LibraryModel, LocalLibrary)
from com.vmware.content.library_client import (
    Item, ItemModel, PublishInfo, StorageBacking)
from com.vmware.content.library.item_client import (
    UpdateSession, UpdateSessionModel, DownloadSession, DownloadSessionModel)
from com.vmware.content.library.item.updatesession_client import File as UpdateSessionFile
from com.vmware.content.library.item.downloadsession_client import File as DownloadSessionFile
from com.vmware.vcenter.ovf_client import LibraryItem
from com.vmware.vcloud.suite.sample.vim.helpers.vim_utils import (
    get_obj, get_obj_by_moId, poweron_vm, poweroff_vm, delete_object)
from pyVmomi import vim
from com.vmware.vcloud.suite.sample.common.id_generator import generate_random_uuid
from com.vmware.vcloud.suite.sample.vim.helpers.get_datastore_by_name import get_datastore_id
from com.vmware.vcloud.suite.sample.common.sample_base import SampleBase
from com.vmware.vcloud.suite.sample.common.logging_context import LoggingContext

logger = LoggingContext.get_logger('com.vmware.vcloud.suite.sample.workflow.content_library_workflow')


class ContentLibraryWorkflow(SampleBase):
    """
    Demonstrates content library workflow
    Step 1: Retrieve datastores vAPI UUID by using its name.
    Step 2: Create a published content library backed by vc ds using vAPIs.
    Step 3: Create a content library item.
    Step 4: Upload a VM template to the published CL.
    Step 5: Download the template files from the CL to make sure the upload went OK.
    Step 6: Deploy a VM using the uploaded template on a given cluster using OVF importer.
    Step 7: Power on the VM and wait for the power on operation to complete.
    Additional steps when clearData flag is set to TRUE:
    Step 8: Power off the VM and wait for the power off operation to complete.
    Step 9: Delete the VM.
    Step 10: Delete the CL item.
    Step 11: Delete the CL.
    Note: the workflow needs an existing VC DS with available storage and a cluster with resources for creating the VM
    """

    def __init__(self, platformservicecontroller):
        SampleBase.__init__(self, self.__doc__, platformservicecontroller)
        self.servicemanager = None
        self.datastore_name = None
        self.datastore_id = None
        self.cl_name = None
        self.cluster_name = None
        self.vm_name = None
        self.lib_description = 'published content library'

        self.library_service = None
        self.local_library_service = None
        self.library_item_service = None
        self.upload_service = None
        self.upload_file_service = None
        self.download_service = None
        self.download_file_service = None
        self.ovf_lib_item_service = None

        self.published_library = None
        self.library_item_id = None
        self.vm_id = None
        self.vm_obj = None

    def _options(self):
        self.argparser.add_argument('-contentlibraryname', '--contentlibraryname', help='The name of the content library to be created.')
        self.argparser.add_argument('-datastorename', '--datastorename', help='The name of the data store.')
        self.argparser.add_argument('-clustername', '--clustername', help='The name of the cluster where the vm gets created from the uploaded template.')
        self.argparser.add_argument('-vmname', '--vmname', help='The name of the vm to be created in the cluster.')

    def _setup(self):
        if self.cl_name is None:
            self.cl_name = self.args.contentlibraryname
        assert self.cl_name is not None

        if self.datastore_name is None:
            self.datastore_name = self.args.datastorename
        assert self.datastore_name is not None

        if self.cluster_name is None:
            self.cluster_name = self.args.clustername
        assert self.cluster_name is not None

        if self.vm_name is None:
            self.vm_name = self.args.vmname
        assert self.vm_name is not None

        if self.servicemanager is None:
            self.servicemanager = self.get_service_manager()

        self.library_service = Library(self.servicemanager.stub_config)
        self.local_library_service = LocalLibrary(self.servicemanager.stub_config)
        self.library_item_service = Item(self.servicemanager.stub_config)
        self.upload_service = UpdateSession(self.servicemanager.stub_config)
        self.upload_file_service = UpdateSessionFile(self.servicemanager.stub_config)
        self.download_service = DownloadSession(self.servicemanager.stub_config)
        self.download_file_service = DownloadSessionFile(self.servicemanager.stub_config)
        self.ovf_lib_item_service = LibraryItem(self.servicemanager.stub_config)

    def _execute(self):
        # Find the data store by the given data store name using property collector
        self.datastore_id = get_datastore_id(service_manager=self.servicemanager, datastore_name=self.datastore_name)
        assert self.datastore_id is not None
        logger.info('DataStore: {0} ID: {1}'.format(self.datastore_name, self.datastore_id))
        visible_cls = self.library_service.list()
        if len(visible_cls) > 0:
            for visible_cl in visible_cls:
                get_visible_cl = self.library_service.get(visible_cl)
                logger.info('Visible content library: {0} with id: {1}'.format(get_visible_cl.name, visible_cl))
        local_cls = self.local_library_service.list()
        if len(local_cls) > 0:
            for local_cl in local_cls:
                get_local_cl = self.local_library_service.get(local_cl)
                logger.info('Local content library: {0} with id: {1}'.format(get_local_cl.name, local_cl))
        logger.info('Creating Published Content Library')
        # Create a public (no auth) publish info
        publish_info = self.get_publish_info(published=True,
                                             publish_url=None,
                                             authentication=PublishInfo.AuthenticationMethod.NONE,
                                             publish_user_name=None,
                                             publish_password=None)

        # Create a published content library
        self.published_library = self.create_published_library(client_token=generate_random_uuid(),
                                                               cl_name=self.cl_name,
                                                               publish_info=publish_info,
                                                               ds_id=self.datastore_id)
        assert self.published_library is not None
        logger.info('Published Content Library created with name: {0} and id: {1}'.format
                    (self.published_library.name, self.published_library.id))
        publish_info = self.published_library.publish_info
        publish_url = publish_info.publish_url
        logger.info('Publish url: {0}'.format(publish_url))

        # create a new library item in the content library for uploading the files
        self.library_item_id = self.create_library_item(library_id=self.published_library.id,
                                                        item_name='simpleVmTemplate',
                                                        item_description='Sample simple VM template',
                                                        item_type='ovf')
        assert self.library_item_id is not None
        assert self.library_item_service.get(self.library_item_id) is not None
        logger.info('Library item created id: {0}'.format(self.library_item_id))

        # Upload a VM template to the published CL
        ovf_files_map = self.get_ovf_files_map()
        self.upload_files(library_item_id=self.library_item_id, ovf_files_map=ovf_files_map)
        logger.info('Uploaded ovf and vmdk files to library item {0}'.format(self.library_item_id))

        # download the library item from the CL
        temp_dir = tempfile.mkdtemp(prefix='simpleVmTemplate-')
        logger.info('Downloading library item {0} to directory {1}'.format(self.library_item_id, temp_dir))
        downloaded_files_map = self.download(library_item_id=self.library_item_id, directory=temp_dir)
        assert len(downloaded_files_map) == len(ovf_files_map)

        # deploy vm into the cluster's resource pool from the uploaded template
        self.vm_id = self.deploy_vm_from_cl()
        assert self.vm_id is not None
        logger.info('Vm created: {}'.format(self.vm_id))

        # power on the vm and wait for the power on operation to be completed
        self.vm_obj = get_obj_by_moId(self.servicemanager.content, [vim.VirtualMachine], self.vm_id)
        assert self.vm_obj is not None
        poweron_vm(self.servicemanager.content, self.vm_obj)

    def _cleanup(self):
        if self.vm_obj is not None:
            # power off the vm
            poweroff_vm(self.servicemanager.content, self.vm_obj)
            # delete the vm
            delete_object(self.servicemanager.content, self.vm_obj)

        if self.library_item_id is not None:
            self.library_item_service.delete(library_item_id=self.library_item_id)
            logger.info('Deleted Library Item: {0}'.format(self.library_item_id))

        if self.published_library is not None:
            self.local_library_service.delete(library_id=self.published_library.id)
            logger.info('Deleted Library Id: {0}'.format(self.published_library.id))

    def get_ovf_files_map(self):
        """Get vm template files"""
        ovf_files_map = {}
        ovf_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../../../../../../resources/simpleVmTemplate'))
        for file_name in os.listdir(ovf_dir):
            if file_name.endswith('.ovf') or file_name.endswith('.vmdk'):
                ovf_files_map[file_name] = os.path.join(ovf_dir, file_name)
        return ovf_files_map

    def get_publish_info(self, published, publish_url, authentication, publish_user_name, publish_password):
        """Generate PublishInfo"""
        publish_info = PublishInfo()
        publish_info.published = published
        publish_info.authentication_method = authentication
        publish_info.publish_url = publish_url
        publish_info.user_name = publish_user_name
        publish_info.password = publish_password
        return publish_info

    def create_published_library(self, client_token, cl_name, publish_info, ds_id):
        """Creates publish library back up by vCenter data store (as is)"""
        library_model = LibraryModel()
        library_model.id = client_token
        library_model.name = cl_name
        library_model.description = self.lib_description
        library_model.type = library_model.LibraryType.LOCAL
        library_model.publish_info = publish_info
        storage_backings = []
        storage_backing = StorageBacking(type=StorageBacking.Type.DATASTORE, datastore_id=ds_id)
        storage_backings.append(storage_backing)
        library_model.storage_backings = storage_backings
        library_id = self.local_library_service.create(create_spec=library_model, client_token=client_token)
        library = self.local_library_service.get(library_id)
        return library

    def create_library_item(self, library_id, item_name, item_description, item_type):
        """Create a library item in the specified library"""
        lib_item_spec = self.get_libraryitem_spec(client_token=generate_random_uuid(),
                                                  name=item_name,
                                                  description=item_description,
                                                  library_id=library_id,
                                                  library_item_type=item_type)
        # Create a library item
        return self.library_item_service.create(create_spec=lib_item_spec, client_token=generate_random_uuid())

    def upload_files(self, library_item_id, ovf_files_map):
        """Upload a VM template to the published CL"""
        # create a new upload session for uploading the files
        session_id = self.upload_service.create(create_spec=UpdateSessionModel(library_item_id=library_item_id),
                                                client_token=generate_random_uuid())
        for f_name, f_path in ovf_files_map.items():
            file_spec = self.upload_file_service.AddSpec(name=f_name,
                                                         source_type=UpdateSessionFile.SourceType.PUSH,
                                                         size=os.path.getsize(f_path))
            file_info = self.upload_file_service.add(session_id, file_spec)
            # Upload the file content to the file upload URL
            with open(f_path, 'rb') as local_file:
                request = urllib2.Request(file_info.upload_endpoint.uri, local_file)
                request.add_header('Cache-Control', 'no-cache')
                request.add_header('Content-Length', '{0}'.format(os.path.getsize(f_path)))
                request.add_header('Content-Type', 'text/ovf')
                urllib2.urlopen(request)
        self.upload_service.complete(session_id)
        self.upload_service.delete(session_id)

    def get_libraryitem_spec(self, client_token, name, description, library_id, library_item_type):
        """Create library item spec"""
        lib_item_spec = ItemModel()
        lib_item_spec.id = client_token
        lib_item_spec.name = name
        lib_item_spec.description = description
        lib_item_spec.library_id = library_id
        lib_item_spec.type = library_item_type
        return lib_item_spec

    def download(self, library_item_id, directory):
        """Download vappTemplate files"""
        downloaded_files_map = {}
        # create a new download session for downloading the session files
        session_id = self.download_service.create(create_spec=DownloadSessionModel(library_item_id=library_item_id),
                                                  client_token=generate_random_uuid())
        file_infos = self.download_file_service.list(session_id)
        for file_info in file_infos:
            self.download_file_service.prepare(session_id, file_info.name)
            download_info = self.wait_for_prepare(session_id, file_info.name)
            response = urllib2.urlopen(download_info.download_endpoint.uri)
            file_path = os.path.join(directory, file_info.name)
            with open(file_path, 'wb') as local_file:
                local_file.write(response.read())
            downloaded_files_map[file_info.name] = file_path
        self.download_service.delete(session_id)
        return downloaded_files_map

    def wait_for_prepare(self, session_id, file_name, status_list=[DownloadSessionFile.PrepareStatus.PREPARED],
                         timeout=30, sleep_interval=1):
        """
        waits for a file part of a download session to reach a status in the status list (by default prepared)
        this method will either timeout or return the result of downloadSessionFile.get(session_id, file_name)
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            file_info = self.download_file_service.get(session_id, file_name)
            if file_info.status in status_list:
                return file_info
            else:
                time.sleep(sleep_interval)
        raise Exception('timed out after waiting {0} seconds for file {1} to reach a terminal state'.format(
            timeout, file_name))

    def deploy_vm_from_cl(self):
        """
        deploys vm into the cluster's resource pool from the uploaded template in the content library.
        Returns the deployed vm's moid
        """
        # Find the cluster's resource pool moid
        cluster_obj = get_obj(self.servicemanager.content, [vim.ClusterComputeResource], self.cluster_name)
        if cluster_obj is None:
            raise ValueError('Cannot find the cluster: {}'.format(self.cluster_name))

        deployment_target = LibraryItem.DeploymentTarget(resource_pool_id=cluster_obj.resourcePool._GetMoId())

        # Suppose the caller does not know much about the OVF descriptor, and would like to obtain
        # more information regarding network mapping, storage mapping, or the additional parameters
        # policies available for the target resource pool. To do so, caller may use filter()
        # and specifying the target resource pool as input. The result from filter() will give
        # the list of storage group sections and network sections defined in the OVF descriptor that
        # are also applicable for the target resource pool.
        ovf_summary = self.ovf_lib_item_service.filter(ovf_library_item_id=self.library_item_id, target=deployment_target)
        logger.info('OVF Name: {}'.format(ovf_summary.name))
        logger.info('OVF Annotation: {}'.format(ovf_summary.annotation))
        if ovf_summary.networks is not None:
            for network in ovf_summary.networks:
                logger.info('OVF Network section: {}'.format(network))
        if ovf_summary.storage_groups is not None:
            for storage_group in ovf_summary.storage_groups:
                logger.info('OVF Storage group section: {}'.format(storage_group))
        if ovf_summary.additional_params:
            for param in ovf_summary.additional_params:
                logger.info('OVF Additional possible parameter Type: {}'.format(param))

        deployment_spec = LibraryItem.ResourcePoolDeploymentSpec(
                     name=self.vm_name,
                     annotation=ovf_summary.annotation,
                     accept_all_eula=True,
                     network_mappings=None,
                     storage_mappings=None,
                     storage_provisioning=None,
                     storage_profile_id=None,
                     locale=None,
                     flags=None,
                     additional_parameters=None,
                     default_datastore_id=None)

        result = self.ovf_lib_item_service.deploy(self.library_item_id,
                                                  deployment_target,
                                                  deployment_spec,
                                                  client_token=generate_random_uuid())

        # The type and ID of the target deployment is available in the instantiate result.
        if result.succeeded is True:
            logger.info('Instantiate successful! Result resource {}, ID {}'.format(result.resource_id.type,
                                                                                   result.resource_id.id))
            error = result.error
            if error is not None:
                for warning in error.warnings:
                    logger.warn('OVF warning: {}'.format(warning.message))
                for info in error.information:
                    for message in info.messages:
                        logger.info('OVF information message: {}'.format(message))
        else:
            logger.error('Instantiate failed!')
            for error in result.error.errors:
                logger.error('OVF error: {}'.format(error.message))
            raise Exception('OVF Instantiate failed!')

        return result.resource_id.id


def main():
    content_library_workflow = ContentLibraryWorkflow(platformservicecontroller=None)
    content_library_workflow.main()

# Start program
if __name__ == '__main__':
    main()
