<% python.pushContext(idlPackage) %>\
<% def lines = [
    "vAPI skeleton file for package ${idlPackage.name.asCanonical}.",
] %>\
${python.render('header.comment', [model:model, extra:lines])}
__author__ = 'VMware, Inc.'
__docformat__ = 'restructuredtext en'

import sys

from vmware.vapi.bindings import type
from vmware.vapi.bindings.converter import TypeConverter
from vmware.vapi.bindings.enum import Enum
from vmware.vapi.bindings.error import VapiError
from vmware.vapi.bindings.skeleton import VapiInterface, ApiInterfaceSkeleton
from vmware.vapi.bindings.common import raise_core_exception
from vmware.vapi.bindings.struct import VapiStruct
from vmware.vapi.data.validator import UnionValidator, HasFieldsOfValidator
<% python.getPackagesToImport(idlPackage, python.providerType).each { pkg -> %>\
import ${pkg}
<% } %>\

<% idlPackage.enumerations.each { e -> %>\
${python.render('enumeration.py', [e:e, fileType:python.providerType])}

<% } %>\
<% idlPackage.structures.findAll { !it.isErrorType() }.each { structure -> %>\
${python.render('structure.py', [structure:structure, fileType:python.providerType])}


<% } %>\
<% idlPackage.structures.findAll { it.isErrorType() }.sort(false) { a, b -> python.compareErrorTypes(b, a) }.each { error -> %>\
${python.render('error.py', [error:error, fileType:python.providerType])}

<% } %>\

<% idlPackage.services.each { service -> %>
class ${service.name.asCapitalizedWords}(VapiInterface):
    """
    ${python.formatDoc(service, python.providerType)}\
    """
${python.render('constants.py', [node:service, fileType:python.providerType], 1)}

    def __init__(self, error_types=None):
        VapiInterface.__init__(self, ${python.getSkeletonName(service)},
                               error_types=error_types)

<% service.enumerations.each { e -> %>\
${python.render('enumeration.py', [e:e, fileType:python.providerType], 1)}

<% } %>\
<% service.structures.findAll { !it.isErrorType() }.each { structure -> %>\
${python.render('structure.py', [structure:structure, fileType:python.providerType], 1)}

<% } %>\
<% service.structures.findAll { it.isErrorType() }.sort(false) { a, b -> python.compareErrorTypes(b, a) }.each { error -> %>\
${python.render('error.py', [error:error, fileType:python.providerType], 1)}

<% } %>\
<% service.operations.each { o -> %>
<% if (o.parameters) { %>\
    def ${o.name.asLowerCaseWithUnderscores}(self,
<% python.getRequiredParameters(o).each { p -> %>\
         ${python.getOperationNameIndent(o)}${p.name.asLowerCaseWithUnderscores},
<% } %>\
<% python.getOptionalParameters(o).each { p -> %>\
         ${python.getOperationNameIndent(o)}${p.name.asLowerCaseWithUnderscores}=None,
<% } %>\
         ${python.getOperationNameIndent(o)}):
<% } else { %>\
    def ${o.name.asLowerCaseWithUnderscores}(self):
<% } %>\
        """
        ${python.formatDoc(o,2,python.providerType)}\
        """
        raise NotImplementedError('Method %s in class %s is not implemented' %
                                  ('${o.name.asLowerCaseWithUnderscores}', '${service.name.asCapitalizedWords}'))
<% } %>

<% } %>\

<% idlPackage.services.each { service -> %>
class ${python.getSkeletonName(service)}(ApiInterfaceSkeleton):
    def __init__(self, impl, error_types):
<% service.operations.each { o -> %>
        # properties for ${o.name.asCanonical} operation
<% if (o.parameters) { %>\
        ${o.name.asCanonical}_input_type = type.StructType('operation-input', {
<%  o.parameters.each { p -> %>\
            '${p.name.asCanonical}': ${python.toSkeletonDefinition(service, o, p)},
<% } %>\
        })
<% } else { %>\
        ${o.name.asCanonical}_input_type = type.StructType('operation-input', {})
<%  } %>\
<%  if (o.errors) { %>\
        ${o.name.asCanonical}_error_list = [
<%   o.errors.each { e -> %>\
            ${python.toSkeletonDefinition(service, o, e)},
<% } %>\
        ]
<%  } else { %>\
        ${o.name.asCanonical}_error_list = []
<%  } %>\
        ${o.name.asCanonical}_input_validator_list = [
<% def union_tags = o.getUnionTags() %>\
<% union_tags.each { union_tag -> %>\
            UnionValidator(
                '${union_tag.name.asCanonical}',
                {
<% def cases_map = o.getUnionCasesMap(union_tag)
   cases_map.each { constant, params ->
     def params_csv = (params) ? params.collect { "('${it.name.asCanonical}', " + ((it.type.isGeneric() && it.type.isOptional()) ? "False)" : "True)")}.join(', ') : ''
%>\
                '${constant.name.asDeclared}' : [${params_csv}],
<% } %>\
                }
            ),
<% } %>\
<%  if (python.hasHasFieldsOfAnnotation(o)) { %>\
            HasFieldsOfValidator()
<% } %>\
        ]
        ${o.name.asCanonical}_output_validator_list = [
<%  if (python.hasHasFieldsOfAnnotation(o.result)) { %>\
            HasFieldsOfValidator()
<% } %>\
        ]
<% } %>
        operations = {
<% service.operations.each { o -> %>\
            '${o.name.asCanonical}': {
                'input_type':${o.name.asCanonical}_input_type,
                'output_type': ${python.toSkeletonDefinition(service, o, o.result)},
                'errors': ${o.name.asCanonical}_error_list,
                'input_validator_list': ${o.name.asCanonical}_input_validator_list,
                'output_validator_list': ${o.name.asCanonical}_output_validator_list,
            },
<% } %>\
        }
        ApiInterfaceSkeleton.__init__(self,
                                      iface_name='${service.getQualifiedName("asCanonical")}',
                                      impl=impl,
                                      operations=operations,
                                      error_types=error_types)

<% } %>\

<% python.popContext() %>\
<% python.createPackageMarkers() %>\
