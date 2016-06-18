class ${python.getStructName(error)}(${python.getBaseStructureReferenceName(error,fileType)}):
    """
${python.formatDoc(error,1,fileType)}\
    """
${python.render('constants.py', [node:error, fileType:fileType], 1)}
    _qualname = '${python.getStructName(error)}'

    def __init__(self,
<% if (error.extendsType) { %>\
<% python.getAllAttributes(error.extendsType.declaration).each { a -> %>\
                 ${a.name.asLowerCaseWithUnderscores}=None,
<% } %>\
<% } %>\
<% error.impliedAttributes.each { a -> %>\
                 ${a.name.asLowerCaseWithUnderscores}=None,
<% } %>\
                ):
        """
${python.formatInitDoc(error,2,fileType)}\
        """
<% error.impliedAttributes.each { a -> %>
        self.${a.name.asLowerCaseWithUnderscores} = ${a.name.asLowerCaseWithUnderscores}<% } %>
<% if (error.extendsType) { %>\
        ${python.getBaseStructureReferenceName(error,fileType)}.__init__(
            self,
<% if (python.getAllNames(error)) { %>\
            {
<% python.getAllNames(error).each { n -> %>\
                '${n.name.asCanonical}' : '${n.name.asLowerCaseWithUnderscores}',
<% } %>\
            },
<% } else { %>\
<% } %>\
<%  python.getAllAttributes(error.extendsType.declaration).each { a -> %>\
            ${a.name.asLowerCaseWithUnderscores}=${a.name.asLowerCaseWithUnderscores },
<% } %>\
        )
<% } else { %>\
<% if (python.getNames(error)) { %>\
        VapiError.__init__(self, {
<% python.getNames(error).each { n -> %>\
                            '${n.name.asCanonical}' : '${n.name.asLowerCaseWithUnderscores}',
<% } %>\
                           })
<% } else { %>\
        VapiError.__init__(self)
<% } %>\
<% } %>
<% error.enumerations.each { e -> %>\
${python.render('enumeration.py', [e:e,fileType:fileType], 1)}
<% } %>\
${python.getStructName(error)}._set_binding_type(type.ErrorType(
    '${error.getQualifiedName("asCanonical")}', {
<% python.getAllAttributes(error).each { a -> %>\
        '${a.name.asCanonical}': ${python.toDefinition(a, fileType, error)},
<% } %>\
    },
    ${python.getStructName(error)}))
