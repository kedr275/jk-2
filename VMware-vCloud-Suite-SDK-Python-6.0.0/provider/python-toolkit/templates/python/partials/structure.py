class ${python.getStructName(structure)}(VapiStruct):
    """
${python.formatDoc(structure,1,fileType)}\
    """
${python.render('constants.py', [node:structure, fileType:fileType], 1)}
<% def union_tags = structure.getUnionTags() %>\
<% if (union_tags.size() > 0) { %>\
    _validator_list = [
<% union_tags.each { union_tag -> %>\
        UnionValidator(
            '${union_tag.name.asCanonical}',
            {
<% def cases_map = structure.getUnionCasesMap(union_tag)
   cases_map.each { constant, attrs ->
     def attrs_csv = (attrs) ? attrs.collect { "('${it.name.asCanonical}', " + (((it.type.isGeneric() && it.type.isOptional()) || (structure.markedCrud() && !it.isRequiredForAll()) || (structure.isOptionalByDefault())) ? "False)" : "True)")}.join(', ') : ''
%>\
                '${constant.name.asDeclared}' : [${attrs_csv}],
<% } %>\
            }
        ),
<% } %>\
    ]
<% } %>

    def __init__(self,
<% structure.impliedAttributes.each { a -> %>\
                 ${a.name.asLowerCaseWithUnderscores}=None,
<% } %>\
                ):
        """
${python.formatInitDoc(structure,2,fileType)}\
        """
<%  structure.impliedAttributes.each { a -> %>\
        self.${a.name.asLowerCaseWithUnderscores} = ${a.name.asLowerCaseWithUnderscores}
<% } %>\
<% if (python.getNames(structure)) { %>\
        VapiStruct.__init__(self, {
<% python.getNames(structure).each { n -> %>\
                            '${n.name.asCanonical}': '${n.name.asLowerCaseWithUnderscores}',
<% } %>\
                            })
<% } else { %>\
        VapiStruct.__init__(self)
<% } %>\

<% structure.enumerations.each { e -> %>\
${python.render('enumeration.py', [e:e,fileType:fileType], 1)}
<% } %>\
${python.getStructName(structure)}._set_binding_type(type.StructType(
    '${structure.getQualifiedName("asCanonical")}', {
<%  structure.impliedAttributes.each { a -> %>\
        '${a.name.asCanonical}': ${python.toDefinition(a, fileType, structure)},
<% } %>\
    },
    ${python.getStructName(structure)},
    ${python.isModelKeyAsString(structure)},
    ${python.modelKeysAsString(structure)}))
