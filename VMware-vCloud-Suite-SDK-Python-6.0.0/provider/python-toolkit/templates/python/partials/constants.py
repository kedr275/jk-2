<% /*
* Render constants
*/%>\
<% node.constants.each { c -> %>\
${c.name.asUpperCaseWithUnderscores} = ${python.getConstantValue(c)}
"""
${python.formatDoc(c, 0, fileType)}
"""
<% } %>\
