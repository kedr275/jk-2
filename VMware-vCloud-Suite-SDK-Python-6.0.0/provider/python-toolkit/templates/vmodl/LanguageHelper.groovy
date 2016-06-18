/*
 * Copyright 2012 VMware, Inc.    All rights reserved.
 */
package com.vmware.vapi.idl.transformer

import com.vmware.vapi.idl.model.*


/**
 * Defines the VMODL language helper.
 */
class VmodlLanguageHelper extends LanguageHelper {

    static final String NAME = "vmodl"

    //fyi: required factory method to construct an instance
    static VmodlLanguageHelper getInstance(LanguageProperties properties, TemplateNamingContext naming) {
        return new VmodlLanguageHelper(properties, naming)
    }


    VmodlLanguageHelper(LanguageProperties properties, TemplateNamingContext naming) {
        super(NAME, properties, naming)

        suffixes = ['vmodl', 'java']
    }

    String headerComment(AbstractNamedNode thing) {
        String result = """\
/*
 * Auto generated VMODL2 file for illustration purpose
 * DO NOT MODIFY!
 */
"""
        return result
    }

    String javadoc(AbstractNamedNode thing, int level=0) {
        final List<String> lines = []
        final String indent = "    " * level
        final String instar = "${indent} *"
        def tag = { tag, name, doc ->
            if (doc.description) {
                doc.descriptions.each { desc ->
                    lines << "${instar} ${tag} ${name} ${desc[0]}"
                    if (desc.size() > 1) {
                        def fill = " " * tag.length()

                        desc[1..-1].each { line ->
                            lines << "${instar} ${fill} ${line}"
                        }
                    }
                }
            } else if (tag != '@return' || name != 'void') {
                lines << "${instar} ${tag} ${name} TODO: add doc here!"
            }
        }

        //lines << "${indent}/**"
        if (thing.doc) {
            lines << "/**" // fyi - the indent will be implicit by where the "macro" is located in the template
            thing.doc.description.each { text ->
                lines << "${instar} ${text}"
            }
            // fyi - generally the one type of node that composes javadoc from contained elements
            if (thing instanceof IdlOperation) {
                lines << "${instar}"
                thing.parameters.each { p ->
                    tag('@param', p.name, p.doc)
                }
                tag('@return', mapType(thing.result.type), thing.result.doc)
                thing.errors.each { e ->
                    tag('@throws', e.name, e.doc)
                }
            }
            thing.doc.links.each { link ->
                lines << "${instar} @see ${link}"
            }
            lines << "${instar}/"
        } else {
            lines << "/* TODO: add doc here! */"
        }
        return lines.join('\n')
    }

    String mapType(IdlType type) {
        String result

        if (type.isGeneric()) {
            String arg = mapType(type.arguments[0])

            if (type.isList()) {
                result = "List<${arg}>"
            } else if (type.isSet()) {
                result = "Set<${arg}>"
            } else if (type.isOptional()) {
                result = "Optional<${arg}>"
            }
        } else if (type.isReference()) {
            result = type.asIdentifier.asCapitalizedWords
        } else if (type.isPrimitive()) {
            switch (type.name) {
            case "string":
                result = type.name.capitalize()
                break
            default:
                result = type.name
            }
        } else if (type.isAnonymous()) {
            result = "Anonymous"
        } else if (type.isVoid()) {
            result = type.name
        }
        return result
    }

    String atResource(def element) {
        if (element.isResource()) {
            return "@Resource(\"${element.getResourceId()}\") "
        }
        return ""
    }

    String atHasFieldsOf(def element) {
        if (element.hasFieldsOf()) {
            return "@HasFieldsOf(${element.getFieldsOf()[0].name}.class) "
        }
        return ""
    }

    String atIncludable(def element) {
        if (element.isIncludable()) {
            return "@Includable"
        }
        return ""
    }

    String atInclude(def element) {
        if (element.hasIncludedStructures()) {
            def values = element.getIncludedStructures().collect { "" + it.name + ".class" }
            return "@Include(" + values.join(", ")  + ") "
        }
        return ""
    }
}

