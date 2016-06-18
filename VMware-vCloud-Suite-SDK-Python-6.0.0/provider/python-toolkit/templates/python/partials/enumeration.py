class ${python.getEnumName(e)}(Enum):
    """
    ${python.formatDoc(e,1,fileType)}\
    """
<% e.constants.each { c -> %>\
    ${c.name.asDeclared} = None
    """
${python.formatDoc(c, 1, fileType)}
    """
<% } %>\

    def __init__(self, string):
        """
        :type  string: :class:`str`
        :param string: String value for the :class:`${python.getEnumName(e)}` instance.
        """
        Enum.__init__(string)

<% e.constants.each { c -> %>\
${python.getEnumName(e)}.${c.name.asDeclared} = ${python.getEnumName(e)}('${c.name.asDeclared}')
<% } %>\
${python.getEnumName(e)}._set_binding_type(type.EnumType(
    '${e.getQualifiedName("asCanonical")}',
    ${python.getEnumName(e)}))

