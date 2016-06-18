/*
 * Copyright 2012-2014 VMware, Inc.  All rights reserved.
 */
package com.vmware.vapi.idl.transformer

import com.vmware.vapi.idl.model.*
import com.vmware.vapi.idl.model.metadata.*
import com.vmware.vapi.idl.model.doc.*
import com.vmware.vapi.idl.util.IndentWriter
import com.vmware.vapi.idl.generator.python.SphinxCommentWriter
import org.apache.commons.lang3.text.WordUtils

/**
 * Defines the Python language helper.
 */
class PythonLanguageHelper extends LanguageHelper {

    static final String NAME = "python"
    static def seenTypes = []
    private static final int SPACES_IN_TAB = 4
    private static final int CHARS_PER_LINE = 79
    private Deque<AbstractNamedNode> contextStack

    //fyi: required factory method to construct an instance
    static PythonLanguageHelper getInstance(LanguageProperties properties, TemplateNamingContext naming) {
        return new PythonLanguageHelper(properties, naming)
    }

    enum FileType {
        CLIENT, PROVIDER, STRUCTURE
    }

    private StringWriter commentBuffer = new StringWriter()
    private IndentWriter comment = new IndentWriter(commentBuffer)

    private static def IDL_TYPE_TO_BINDINGS_TYPE_REPRESENTATION = [
        'binary': 'type.BlobType',
        'boolean': 'type.BooleanType',
        'date_time': 'type.DateTimeType',
        'double': 'type.DoubleType',
        'ID': 'type.IdType',
        'long': 'type.IntegerType',
        'opaque': 'type.OpaqueType',
        'secret': 'type.SecretType',
        'string': 'type.StringType',
        'URI': 'type.URIType',
        'void': 'type.VoidType',
        'structure': 'type.DynamicStructType',
        'dynamic_structure': 'type.DynamicStructType',
        'exception': 'type.AnyErrorType',
    ]

    PythonLanguageHelper(LanguageProperties properties, TemplateNamingContext naming) {
        super(NAME, properties, naming)
        suffixes = [ "py" ]
        this.contextStack = new ArrayDeque<AbstractNamedNode>()
    }

    void pushContext(AbstractNamedNode node) {
        contextStack.push(node)
    }

    void popContext() {
        contextStack.pop()
    }

    FileType getClientType() {
        return FileType.CLIENT
    }

    FileType getProviderType() {
        return FileType.PROVIDER
    }

    FileType getStructType() {
        return FileType.STRUCTURE
    }

    void createPackageMarkers() {
        File dir = this.outputDir

        // recurse down to the root, dropping markers along the way, then stop
        while (dir && dir != outputRootDir) {
            createPackageMarker(dir)
            dir = dir.parentFile
        }
    }

    void createPackageMarker(File dir) {
        File marker = new File(dir, "__init__.py")

        if (!marker.exists()) {
            marker.withWriter { out ->
                out << "# Required to distribute different parts of this\n"
                out << "# package as multiple distributables\n"
                out << "try:\n"
                out << "    import pkg_resources\n"
                out << "    pkg_resources.declare_namespace(__name__)\n"
                out << "except ImportError:\n"
                out << "    from pkgutil import extend_path\n"
                out << "    __path__ = extend_path(__path__, __name__)\n"
            }
        }
    }

    /*
     * Functions to generate variable names used in the bindings
     */

    String getServiceName(IdlService service) {
        return service.name.asCapitalizedWords
    }

    String getStructName(IdlStructure s) {
        return s.name.asCapitalizedWords
    }

    String getStructDefinition(IdlStructure s) {
        return "${getStructName(s)}Type"
    }

    String getEnumName(IdlEnumeration e) {
        return e.name.asCapitalizedWords
    }

    String getStubName(IdlService service) {
        return "_${service.name.asCapitalizedWords}Stub"
    }

    String getEnumDefinition(IdlEnumeration e) {
        return "${getEnumName(e)}Type"
    }

    String getStubName(IdlOperation o) {
        return "_${o.name.asCapitalizedWords}Method"
    }

    String getSkeletonName(IdlService service) {
        return "${service.name.asCapitalizedWords}Skeleton"
    }

    String getSkeletonName(IdlOperation o) {
        return "_${o.name.asCapitalizedWords}Method"
    }

    /*
     * Functions to generate type names (also resolving in case of structure references)
     */

    String getBindingClassName(AbstractNamedNode node) {
        String name = ""
        if (node instanceof IdlService) {
            name = getServiceName((IdlService) node)
        } else if (node instanceof IdlStructure) {
            name = getStructName((IdlStructure) node)
        } else if (node instanceof IdlEnumeration) {
            name = getEnumName((IdlEnumeration) node)
        }
        else {
            name = node.name
        }
        return name
    }

    String getBindingFileName(AbstractNamespacedNode namespacedNode, FileType fileType) {
        def fileName = naming.getPackageName(namespacedNode)

        switch (fileType) {
            case FileType.CLIENT:
                fileName = fileName + "_client"
                break
            case FileType.PROVIDER:
                fileName = fileName + "_provider"
                break
        }
        return fileName
    }

    String getBindingPackage(AbstractNamedNode node, FileType fileType) {
        String result = ''

        if (node instanceof AbstractNamespacedNode) {
             AbstractNamespacedNode namespacedNode = (AbstractNamespacedNode) node
            if (namespacedNode.namespace) {
                result = getBindingFileName(namespacedNode, fileType)
            }
        }
        return result
    }

    String getPackageName(AbstractNamedNode typeDeclarationNode, FileType fileType) {
        AbstractNamedNode node = typeDeclarationNode.declaringNode
        AbstractNamedNode lastNode = typeDeclarationNode
        while (node) {
            lastNode = node
            node = node.declaringNode
        }
        return getBindingPackage(lastNode, fileType)
    }

    String getTypeReferenceName(AbstractNamedNode typeDeclarationNode, FileType fileType) {
        List<String> tokens = new ArrayList<String>()
        AbstractNamedNode node = typeDeclarationNode
        AbstractNamedNode lastNode = null
        while (node) {
            tokens.add(getBindingClassName(node))
            lastNode = node
            node = node.declaringNode
        }
        return tokens.reverse().join('.')
    }

    String getReferencePackage(AbstractNamedNode typeDeclarationNode, FileType fileType, AbstractNamedNode srcNode) {
        AbstractNamedNode node = typeDeclarationNode
        AbstractNamedNode lastNode = null
        while (node) {
            lastNode = node
            node = node.declaringNode
        }
        AbstractNamespacedNode typeDeclarationNsNode = (AbstractNamespacedNode) lastNode

        node = srcNode
        lastNode = null
        while (node) {
            lastNode = node
            node = node.declaringNode
        }
        AbstractNamespacedNode srcNsNode = (AbstractNamespacedNode) lastNode

        if (typeDeclarationNsNode.namespace.toString() != srcNsNode.namespace.toString()) {
            return getBindingPackage(typeDeclarationNsNode, fileType)
        }
        return null
    }

    String toReferenceDefinition(IdlType type, FileType fileType, AbstractNamedNode srcNode, IdlService svc=null) {
        def targetPackage = getReferencePackage(type.declaration, fileType, srcNode)
        def typeName = getTypeReferenceName(type.declaration, fileType)
        if (targetPackage == null) {
            return "type.ReferenceType(sys.modules[__name__], '${typeName}')"
        } else {
            "type.ReferenceType(${targetPackage}, '${typeName}')"
        }
    }

    String toReferenceDefinition(IdlStructure structure, FileType fileType, AbstractNamedNode srcNode, IdlService svc=null) {
        // XXX: Eliminate duplication of this code with above method
        def targetPackage = getReferencePackage(structure, fileType, srcNode)
        def typeName = getTypeReferenceName(structure, fileType)
        if (targetPackage == null) {
            return "type.ReferenceType(sys.modules[__name__], '${typeName}')"
        } else {
            "type.ReferenceType(${targetPackage}, '${typeName}')"
        }
    }

    String handleIdType(AbstractNamedNode tnb, IdlType type) {
        String typeRepr = IDL_TYPE_TO_BINDINGS_TYPE_REPRESENTATION[type.asIdentifier.asCanonical]
        if (tnb.hasResourceTypeHolder()) {
            // Polymorphic resource type
            StringBuilder resources = new StringBuilder()
            resources.append('[')
            resources.append(tnb.getResourceTypes().collect { '"' + it + '"' }.join(', '))
            resources.append(']')
            def resourceTypeHolder = 'None'
            if (tnb.getResourceTypeHolderNode() != null) {
                resourceTypeHolder = '"' + tnb.getResourceTypeHolderNode().name.asCanonical + '"'
            }
            return "${typeRepr}(resource_types=" + resources.toString() + ", resource_type_field_name=" + resourceTypeHolder + ")"
        } else {
            // Static resource type
            return "${typeRepr}(resource_types='${tnb.getResourceTypes()[0]}')"
        }
    }

    String toDefinition(AbstractTypedNode tnb, FileType fileType, AbstractNamedNode srcNode, IdlService svc=null) {
        IdlType type = tnb.impliedType ?: tnb.type
        List<IdlType> hasFieldsOfTypes = null
        if (tnb instanceof IdlAttribute || tnb instanceof IdlParameter || tnb instanceof IdlResult) {
            hasFieldsOfTypes = tnb.hasFieldsOf() ? tnb.getFieldsOf() : null
        }
        if (type == IdlPrimitiveType.ID) {
            return handleIdType(tnb, type)
        } else {
            return toDefinition(type, fileType, srcNode, svc, hasFieldsOfTypes)
        }
    }

    String toDefinition(IdlType type, FileType fileType, AbstractNamedNode srcNode, IdlService svc=null, List<IdlStructure> hasFieldsOfTypes=null) {
        String instance = "type.VoidType()"
        if (type.isPrimitive()) {
            String typeRepr = IDL_TYPE_TO_BINDINGS_TYPE_REPRESENTATION[type.asIdentifier.asCanonical]
            // Handle Structure type field
            if (typeRepr == "type.DynamicStructType") {
                if (hasFieldsOfTypes) {
                    instance = "${typeRepr}('vmware.vapi.dynamic_struct', {}, VapiStruct, ["
                    for (IdlStructure t : hasFieldsOfTypes) {
                        String ref = toReferenceDefinition(t, fileType, srcNode, svc)
                        instance = instance + "${ref}"
                    }
                    instance += "])"
                } else {
                    instance = "${typeRepr}('vmware.vapi.dynamic_struct', {}, VapiStruct)"
                }
            } else {
                instance = "${typeRepr}()"
            }
        } else if (type.isReference()) {
            instance = toReferenceDefinition(type, fileType, srcNode, svc)
        } else if (type.isGeneric()) {
            String arg = toDefinition(type.arguments[0], fileType, srcNode, svc, hasFieldsOfTypes)
            if (type.isOptional()) {
                instance = "type.OptionalType(${arg})"
            } else if (type.isList()) {
                instance = "type.ListType(${arg})"
            } else if (type.isSet()) {
                instance = "type.SetType(${arg})"
            } else if (type.isMap()) {
                String arg2 = toDefinition(type.arguments[1], fileType, srcNode, svc, hasFieldsOfTypes)
                instance = "type.MapType(${arg}, ${arg2})"
            }
        }

        return instance
    }

    String toStubDefinition(IdlService svc, AbstractNamedNode srcNode, AbstractTypedNode tnb) {
        return toDefinition(tnb, FileType.CLIENT, srcNode, svc)
    }

    String toStubDefinition(AbstractNamedNode srcNode, AbstractTypedNode tnb) {
        return toDefinition(tnb, FileType.CLIENT, srcNode)
    }

    String toSkeletonDefinition(IdlService svc, AbstractNamedNode srcNode, AbstractTypedNode tnb) {
        return toDefinition(tnb, FileType.PROVIDER, srcNode, svc)
    }

    String toSkeletonDefinition(AbstractNamedNode srcNode, AbstractTypedNode tnb) {
        return toDefinition(tnb, FileType.PROVIDER, srcNode)
    }

    /*
     * Functions to generate Sphinx reST documentation
     */

    /**
     * Generate the fully qualified type name in PEP8 for Sphinx docs.
     *
     * @param node Node for which the fully qualified name has to be generated.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return fully qualified type name in PEP8.
     */
    private String formatReferenceTypeName(AbstractNamedNode node, FileType fileType) {
        def typeName = getTypeReferenceName(node, fileType)
        def packageName = getPackageName(node, fileType)
        return "${packageName}.${typeName}"
    }

    /**
     * Generate the type name for Sphinx docs.
     *
     * @param type Type for which the name has to be generated
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @param nested true if formatTypeName is invoked within formatTypeName method scope, false otherwise.
     * @return type name.
     */
    private String formatTypeName(IdlType type, FileType fileType, boolean nested=false) {
        String result = "``None``"
        if (type.isPrimitive()) {
            result = ":class:`" + toCanonicalForm(type) + "`"
        } else if (type.isReference()) {
            result = ":class:`" + formatTypeLinkName(type.declaration, fileType) + "`"
        } else if (type.isOptional()) {
            result = formatTypeName(type.arguments[0], fileType, true) + " or ``None``"
            if (nested) {
                result = "(${result})"
            }
        } else if (type.isList()) {
            result = ":class:`list` of " + formatTypeName(type.arguments[0], fileType, true)
        } else if (type.isSet()) {
            result = ":class:`set` of " + formatTypeName(type.arguments[0], fileType, true)
        } else if (type.isMap()) {
            def keyResult = formatTypeName(type.arguments[0], fileType, true)
            def valueResult = formatTypeName(type.arguments[1], fileType, true)
            result = ":class:`dict` of ${keyResult} and ${valueResult}"
            if (nested) {
                result = "(${result})"
            }
        }
        return result
    }

    /**
     * Format the IDL package name to be used Sphinx docs.
     *
     * @param node IdlPackage node
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     */
    private String formatPackageName(IdlPackage node, FileType fileType) {
        if (fileType == FileType.CLIENT) {
            return node.name.asCanonical + '_client'
        } else {
            return node.name.asCanonical + '_provider'
        }
    }

    /**
     * Format the type name that is used in {@link xxx} javadocs. The generated link name
     * should be a local name if the node that {@link xxx} is referencing is in the same
     * IdlPackage and it should be a fully qualified name if the node is in a different
     * IdlPackage. This is handled by name of the IdlPackage present in contextStack.
     * The template pushes and pops the current IdlPackage into the stack.
     *
     * @param node Node for which the link has to be generated.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @param type name.
     */
    private String formatTypeLinkName(AbstractNamedNode node, FileType fileType) {
        String currentScope = formatPackageName(contextStack.getFirst(), fileType)
        return formatReferenceTypeName(node, fileType).replace(currentScope + '.', '')
    }

    /**
     * Reset the comment buffer
     */
    private void resetCommentBuffer() {
        commentBuffer.buffer.setLength(0)
    }

    /**
     * Print a line in the comment buffer.
     *
     * @param line String to be printed.
     * @param level Indentation level.
     * @param firstLine If true, then this line is the first line of the text paragraph.
     * @param indentFirst If true, indent the first line, otherwise do not indent. The subsequent
     *                    lines are always indented.
     */
    private void printLine(String line, int level, boolean firstLine=true, boolean indentFirst=false) {
        String extraIndent
        // For lists and nested lists, we need to extra indent if the line is too long and is
        // wrapped. Need to trim before checking for "* " or "#. " as nested lists will already
        // be indented by SphinxCommentWriter.
        def trimmedLine = line.trim()
        if (trimmedLine.startsWith('* ')) {
            extraIndent = '  '
        } else if (trimmedLine.startsWith('#. ')) {
            extraIndent = '   '
        }

        // Word wrap the current line based on maximum characters allowed per
        // line and the current indent level
        List<String> wrappedLines = WordUtils.wrap(
            line, CHARS_PER_LINE - level * SPACES_IN_TAB).split('\n')
        wrappedLines.eachWithIndex { it, i ->
            if (firstLine && !indentFirst) {
                comment.println(it)
            } else {
                comment.indent(level)
                // If extra indent is set, indent the line by 2 more spaces.
                // Otherwise lists are not rendered correctly in Sphinx.
                if (i > 0 && extraIndent) {
                    comment.print(extraIndent)
                }
                comment.println(it)
            }
            firstLine = false
        }
        extraIndent = false
    }

    /**
     * Print the given IDL doc model.
     *
     * @param docModel IDL doc model.
     * @param level Indentation level.
     * @param indentFirst If true, indent the first line, otherwise do not indent. The subsequent
     *                    lines are always indented.
     */
    private void printDocModel(DocModel docModel, int level, boolean indentFirst=false) {
        List<String> textLines = commentWriter.makeLines(docModel)
        textLines.eachWithIndex { line, i ->
            if (i == 0) {
                printLine(line, level, /* first line */ true, indentFirst)
            } else {
                printLine(line, level, /* first line */ false)
            }
        }
    }

    /**
     * Print the IDL doc model present in the given node
     *
     * @param node Node for which the doc model has to be printed
     * @param level Indentation level.
     * @param indentFirst If true, indent the first line, otherwise do not indent. The subsequent
     *                    lines are always indented.
     */
    private void printDocModel(AbstractNamedNode node, int level, boolean indentFirst=false) {
        if (node && node.doc) {
            printDocModel(node.doc.descriptionModel, level, indentFirst)
        } else {
            comment.println()
        }
    }

    /**
     * Print the optional reason for an operation parameter of structure field
     *
     * @param node Node for which the optional reason has to be printed
     * @param level Indentation level.
     */
    private void printOptionalReason(AbstractNamedNode node, int level) {
        if (node.isOptional()) {
            def reason = node.doc.getOptionalReasonModel()
            if (reason) {
                printDocModel(reason, level, true)
            }
        }
    }

    /**
     * Print the documentation for the annotations present on the operation parameter, operation result or structure field
     *
     * @param node typed node
     * @param level Indentation level
     */
    private void printAnnotationDoc(AbstractNamedNode node, int level) {
        def docModel = node.doc.getMetadataModel()
        if (docModel) {
            printDocModel(docModel, level, true)
        }
    }

    /**
     * Print the documentation about a structure field
     *
     * @param node Structure field node
     * @param level Indentation level
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     */
    private void printField(AbstractTypedNode node, int level, FileType fileType) {
        String c = formatTypeName(node.type, fileType)
        comment.indent(level).print(":type  ${node.name.asLowerCaseWithUnderscores}: ").println("${c}")
        comment.indent(level).print(":param ${node.name.asLowerCaseWithUnderscores}: ")
        // Extra indent subsequent lines in the docs
        printDocModel(node, level + 1)
        printAnnotationDoc(node, level + 1)
        printOptionalReason(node, level + 1)
    }

    /**
     * Print the documentation about an operation parameter.
     *
     * @param node operation parameter node.
     * @param level Indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     */
    private void printParam(AbstractTypedNode node, int level, FileType fileType) {
        String c = formatTypeName(node.type, fileType)
        comment.indent(level).print(":type  ${node.name.asLowerCaseWithUnderscores}: ").println("${c}")
        comment.indent(level).print(":param ${node.name.asLowerCaseWithUnderscores}: ")
        // Extra indent subsequent lines in the docs
        printDocModel(node, level + 1)
        printAnnotationDoc(node, level + 1)
        printOptionalReason(node, level + 1)
    }

    /**
     * Print the documentation about an operation result
     *
     * @param node operation result node
     * @param level Indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     */
    private void printResult(AbstractTypedNode node, int level, FileType fileType) {
        comment.indent(level).print(":rtype: ").println(formatTypeName(node.type, fileType))
        comment.indent(level).print(":return: ")
        // Extra indent subsequent lines in the docs
        printDocModel(node, level + 1)
        printAnnotationDoc(node, level + 1)
        printOptionalReason(node, level + 1)
    }

    /**
     * Print the documentation about a constant.
     *
     * @param node Structure field node.
     * @param level Indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     */
    private void printConstant(IdlConstant node, int level, FileType fileType) {
        printDocModel(node, level, true)
        printAnnotationDoc(node, level)
    }

    /**
     * Format the documentation for a package to match Sphinx reST format.
     *
     * @param pkg IdlPackage node.
     * @return formatted string.
     */
    String formatDoc(IdlPackage pkg) {
        resetCommentBuffer()
        printDocModel(pkg, 0)
        printAnnotationDoc(pkg, 0)
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for a service to match Sphinx reST format.
     *
     * @param service IdlService node.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatDoc(IdlService service, FileType fileType) {
        resetCommentBuffer()
        printDocModel(service, 1)
        printAnnotationDoc(service, 1)
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for a structure to match Sphinx reST format.
     *
     * @param structure IdlStructure node.
     * @param level indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatDoc(IdlStructure structure, int level, FileType fileType) {
        resetCommentBuffer()
        printDocModel(structure, level, true)
        printAnnotationDoc(structure, level)
        comment.println()
        comment.indent(level).println(".. tip::")
        def output = "The arguments are used to initialize data attributes with the same names."
        printLine(output, level + 1, false, true)
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for a structure to match Sphinx reST format.
     *
     * @param structure IdlStructure node.
     * @param level indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatInitDoc(IdlStructure structure, int level, FileType fileType) {
        resetCommentBuffer()
        if (structure.isErrorType()) {
            getAllAttributes(structure).each { a ->
                printField(a, level, fileType)
            }
        } else {
            structure.impliedAttributes.each { a ->
                printField(a, level, fileType)
            }
        }
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for an enumeration to match Sphinx reST format.
     *
     * @param enumeration IdlEnumeration node.
     * @param level indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatDoc(IdlEnumeration enumeration, int level, FileType fileType) {
        resetCommentBuffer()
        printDocModel(enumeration, level)
        comment.println()
        comment.indent(level).println(".. note::")
        def output = "This class represents an enumerated type in the interface language definition. The class contains class attributes which represent the values in the current version of the enumerated type. Newer versions of the enumerated type may contain new values. To use new values of the enumerated type in communication with a server that supports the newer version of the API, you instantiate this class. See :ref:`enumerated type description page <enumeration_description>`."
        printLine(output, level + 1, false, true)
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for a constant to match Sphinx reST format.
     *
     * @param constant IdlConstant node.
     * @param level indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatDoc(IdlConstant constant, int level, FileType fileType) {
        resetCommentBuffer()
        printConstant(constant, level, fileType)
        return commentBuffer.toString()
    }

    /**
     * Format the documentation for an operation to match Sphinx reST format.
     *
     * @param operation IdlOperation node.
     * @param level indentation level.
     * @param fileType Specifies the current file type of the template. i.e. Provider (or) Client.
     * @return formatted string.
     */
    String formatDoc(IdlOperation operation, int level=2, FileType fileType) {
        resetCommentBuffer()
        printDocModel(operation, level)
        printAnnotationDoc(operation, level)
        if (operation.parameters || !operation.result.type.isVoid() || operation.errors) {
            comment.println()
        }

        operation.parameters.each { p ->
            printParam(p, level, fileType)
        }
        if (!operation.parameters) {
            comment.println()
        }
        if (!operation.result.type.isVoid()) {
            printResult(operation.result, level, fileType)
        }
        operation.errors.each { error ->
            // Extra indent subsequent lines in the docs
            error.doc.getDescriptionModels().each { errorDoc ->
                comment.indent(level).println(":raise: " + formatTypeName(error.type, fileType) + " ")
                printDocModel(errorDoc, level + 1, true)
            }
        }
        if (operation.doc.privilegeModel) {
            comment.indent(level).println(":raise: :class:`com.vmware.vapi.std.errors_client.Unauthorized`")
            printDocModel(operation.doc.privilegeModel, level + 1, true)
        }

        return commentBuffer.toString()
    }

    /**
     * Get the current template type that is being processed.
     *
     * @return Current template type that is being processed.
     */
    private FileType getCurrentTemplate() {
        return isClientTemplate() ? FileType.CLIENT : FileType.PROVIDER
    }

    /**
     * Creates comment writer for writing Sphinx reST docs in the generated
     * code.
     *
     * @return initialized comment writer.
     */
    @Override
    CommentWriter createCommentWriter() {
        return new SphinxCommentWriter(
                createLinkConverter(),
                createNameConverter()).injectTermMapping(termMapping)
    }

    LinkConverter createLinkConverter() {
        return new LinkConverter() {
            @Override
            String toLink(ResolvedLinkToPackage link) {
                StringBuilder result = new StringBuilder()

                result << ":mod:`" << toName(link) << "`"
                return result.toString()
            }

            @Override
            String toName(ResolvedLinkToPackage link) {
                return formatPackageName(link.pkg, getCurrentTemplate())
            }

            @Override
            String toLink(ResolvedLinkToType link) {
                StringBuilder result = new StringBuilder()

                result << ":class:`" << toName(link) << "`"
                return result.toString()
            }

            @Override
            String toName(ResolvedLinkToType link) {
                return formatTypeLinkName(link.type, getCurrentTemplate())
            }

            @Override
            String toLink(ResolvedLinkToMember link) {
                StringBuilder result = new StringBuilder()

                switch (link.member) {
                    case IdlConstant:
                    case IdlAttribute:
                        result << ':attr:`' << toName(link) << '`'
                        break
                    case IdlOperation:
                        result << ':func:`' << toName(link) << '`'
                        break
                }
                return result.toString()
            }

            @Override
            String toName(ResolvedLinkToMember link) {
                StringBuilder result = new StringBuilder()
                String typeName = formatTypeLinkName(link.type, FileType.CLIENT)

                switch (link.member) {
                    case IdlConstant:
                        result << typeName << '.' << link.member.name.asDeclared
                        break
                    case IdlOperation:
                    case IdlAttribute:
                        result << typeName << '.' << link.member.name.asLowerCaseWithUnderscores
                        break
                }
                return result.toString()
            }
        }
    }

    private NameConverter createNameConverter() {
        return new NameConverter() {
            @Override
            String toName(ResolvedLinkToPackage link) {
                return formatPackageName(link.pkg, getCurrentTemplate())
            }

            @Override
            String toBasename(ResolvedLinkToPackage link) {
                return toName(link)
            }

            @Override
            String toFullname(ResolvedLinkToPackage link) {
                return toName(link)
            }

            @Override
            String toName(ResolvedLinkToType link) {
                //TODO: use current context to decide:
                // if element is in scope, then use basename
                // else use fullname
                return formatTypeLinkName(link.type, getCurrentTemplate())
            }

            @Override
            String toBasename(ResolvedLinkToType link) {
                return toName(link)
                //return link.type.name.asCapitalizedWords
            }

            @Override
            String toFullname(ResolvedLinkToType link) {
                return toName(link)
                //return link.type.getQualifiedName('asCapitalizedWords')
            }

            @Override
            String toName(ResolvedLinkToMember link) {
                //TODO: use current context to decide:
                // if element is in scope, then use basename
                // else use fullname
                return toBasename(link)
            }

            @Override
            String toBasename(ResolvedLinkToMember link) {
                return link.member.name
            }

            @Override
            String toFullname(ResolvedLinkToMember link) {
                return toName(link)
            }
        }
    }

    /*
     * Function to get the list of field names whose canonical names do not match PEP8 names
     */

    List getNames(IdlStructure structure) {
        def namesToStore = []
        structure.impliedAttributes.each { a ->
            if (a.name.asCanonical != a.name.asLowerCaseWithUnderscores) {
                namesToStore.add(a)
            }
        }
        return namesToStore
    }

    /*
     * Function to get the list of field names (include base class fields) whose canonical names do not match PEP8 names
     */

    List getAllNames(IdlStructure error) {
        def namesToStore = []
        getAllAttributes(error).each { a ->
            if (a.name.asCanonical != a.name.asLowerCaseWithUnderscores) {
                namesToStore.add(a)
            }
        }
        return namesToStore
    }

    /*
     * Functions to determine what set of packages to import to resolve types from different packages. This section
     * of functions parse the field names of all structures, parameters and result types of all operations in the
     * package. If there are any references to structures outside of this package, they add it to the list of
     * packages to import
     */

    String getImportPackage(AbstractNamedNode typeDeclarationNode, FileType fileType, AbstractNamedNode srcNode) {
        String result = null
        AbstractNamedNode node = typeDeclarationNode
        AbstractNamedNode lastNode = null

        while (node) {
            lastNode = node
            node = node.declaringNode
        }
        AbstractNamespacedNode namespacedNode = (AbstractNamespacedNode) lastNode
        if (namespacedNode.namespace && namespacedNode.namespace.toString() != srcNode.name.toString()) {
            result = getBindingFileName(namespacedNode, fileType)
        }
        return result
    }

    String getImportPackage(IdlType type, FileType fileType, IdlPackage pkg) {
        if (type.isReference()) {
            return getImportPackage(type.declaration, fileType, pkg)
        } else if (type.isGeneric()) {
            return getImportPackage(type.arguments[0], fileType, pkg)
        }
        return null
    }

    String getImportPackage(AbstractTypedNode node, FileType fileType, IdlPackage pkg) {
        if (!(node instanceof IdlError) && node.hasFieldsOf()) {
            List<IdlType> hasFieldsOfTypes = node.getFieldsOf()
            return getImportPackage(hasFieldsOfTypes[0], fileType, pkg)
        } else {
            return getImportPackage(node.type, fileType, pkg)
        }
    }

    Set getPackagesToImport(IdlStructure structure, FileType fileType, IdlPackage pkg) {
        def packagesToImport = [] as Set
        if (structure.extendsType) {
            def ns = getImportPackage(structure.extendsType, fileType, pkg)
            if (ns) {
                packagesToImport.add(ns)
            }
        }
        structure.impliedAttributes.each { a ->
            def ns = getImportPackage(a, fileType, pkg)
            if (ns) {
                packagesToImport.add(ns)
            }
        }
        return packagesToImport
    }

    Set getPackagesToImport(List structures, FileType fileType, IdlPackage pkg) {
        def packagesToImport = [] as Set
        structures.each { structure ->
            packagesToImport.addAll(getPackagesToImport(structure, fileType, pkg))
        }
        return packagesToImport
    }

    Set getPackagesToImport(IdlService service, FileType fileType, IdlPackage pkg) {
        def packagesToImport = [] as Set
        service.structures.each { structure ->
            packagesToImport.addAll(getPackagesToImport(structure, fileType, pkg))
        }
        service.operations.each { operation ->
            operation.parameters.each { p ->
                def ns = getImportPackage(p, fileType, pkg)
                if (ns) {
                    packagesToImport.add(ns)
                }
            }
            getAugmentedErrors(operation).each { e ->
                def ns = getImportPackage(e, fileType, pkg)
                if (ns) {
                    packagesToImport.add(ns)
                }
            }
            def ns = getImportPackage(operation.result, fileType, pkg)
            if (ns) {
                packagesToImport.add(ns)
            }
        }
        return packagesToImport
    }

    Set getPackagesToImport(IdlPackage pkg, FileType fileType) {
        def packagesToImport = [] as Set
        pkg.services.each { service ->
            packagesToImport.addAll(getPackagesToImport(service, fileType, pkg))
        }
        pkg.structures.each { structure ->
            packagesToImport.addAll(getPackagesToImport(structure, fileType, pkg))
        }
        return packagesToImport
    }

    /**
     * Returns 0 if error1==error2 (i.e. if error1 and error2 represent the
     * same type), or if they are unrelated (i.e. neither type is an ancestor
     * of the other).
     * Returns a negative integer if error1<error2 (i.e. error2 is an ancestor
     * of error1).
     * Returns a positive integer if error1>error2 (i.e. error1 is an ancestor
     * of error2).
     */
    int compareErrorTypes(IdlStructure error1, IdlStructure error2) {
        if (error1 == error2 ||
            error1.getQualifiedName().equals(error2.getQualifiedName()))
        {
            return 0
        }
        // Check if error2 is an ancestor of error1
        IdlReferenceType eRef = error1.extendsType
        while (eRef != null) {
            IdlStructure e = eRef.declaration
            if (e == error2 ||
                e.getQualifiedName().equals(error2.getQualifiedName())) {
                return -1
            }
            eRef = e.extendsType
        }

        // Check if error1 is an ancestor of error2
        eRef = error2.extendsType
        while (eRef != null) {
            IdlStructure e = eRef.declaration
            if (e == error2 ||
                e.getQualifiedName().equals(error1.getQualifiedName())) {
                return 1
            }
            eRef = e.extendsType
        }

        /*
         * Neither type is an ancestor of the other, use an arbitrary (but
         * stable) ordering.
         */
        return error1.getQualifiedName().compareTo(error2.getQualifiedName())
    }

    /**
     * Return the appropriate name to reference the Python class representing
     * 'target' when the reference is from 'referencingScope'.
     */
    String getTypeReferenceName(AbstractNamespacedNode target,
                                AbstractNamedNode referencingScope,
                                FileType fileType) {
       if (target.namespace == referencingScope.namespace) {
           /*
            * The target type is defined in the same scope (package or
            * interface) as the referencing scope
            */
           return getStructName(target)
       }
       if (referencingScope.declaringNode != null) {
           // The referencingScope is nested in an interface
           if (referencingScope.declaringNode.namespace == target.namespace) {
               // and the target type is in the same package as the interface
               return getStructName(target)
           }
       }
       // The target type is defined in a different package from the referencing
       // scope
       return formatReferenceTypeName(target,fileType)
    }

    /**
     * Return the name of the appropriate Python base class for a VMODL2
     * structure or error type.
     */
    String getBaseStructureReferenceName(IdlStructure structure,
                                         FileType fileType) {
       if (structure.extendsType == null) {
           return structure.isErrorType() ? "VapiError" : "VapiStruct"
       }

       IdlStructure base = structure.extendsType.declaration
       return getTypeReferenceName(base, structure, fileType)
    }

    boolean hasHasFieldsOfAnnotation(IdlType type) {
        if (type.isReference() && type.isStructure()) {
            if (type.declaration in seenTypes) {
                return false
            }
            seenTypes.push(type.declaration)
            for (IdlAttribute attr : type.declaration.attributes) {
                if (attr.hasFieldsOf()) {
                    seenTypes.pop()
                    return true
                }
                if (hasHasFieldsOfAnnotation(attr.type)) {
                    seenTypes.pop()
                    return true
                }
            }
            seenTypes.pop()
            return false
        }
        if (type.isGeneric()) {
            for (IdlType element : type.arguments) {
                if (hasHasFieldsOfAnnotation(element)) {
                    return true
                }
            }
            return false
        }
        return false
    }

    boolean hasHasFieldsOfAnnotation(IdlOperation o) {
        for (IdlParameter p : o.parameters) {
            if (p.hasFieldsOf()) {
                return true
            }
            seenTypes = []
            if (hasHasFieldsOfAnnotation(p.type)) {
                return true
            }
        }
        return false
    }

    boolean hasHasFieldsOfAnnotation(IdlResult r) {
        if (r.hasFieldsOf()) {
            return true
        }
        seenTypes = []
        if (hasHasFieldsOfAnnotation(r.type)) {
            return true
        }
    }

    String getPrimitiveConstantValue(IdlConstantRef constantRef) {
        IdlConstant constant = constantRef.declaration
        if (constant.type == IdlPrimitiveType.STRING) {
            return '"' + constant.value + '"'
        } else if (constant.type == IdlPrimitiveType.BOOLEAN) {
            return constant.value.toString().capitalize()
        } else {
            return constant.value
        }
    }

    String getPrimitiveConstantValue(IdlConstant constant) {
        if (constant.type == IdlPrimitiveType.STRING) {
            return '"' + constant.value + '"'
        } else if (constant.type == IdlPrimitiveType.BOOLEAN) {
            return constant.value.toString().capitalize()
        } else {
            return constant.value
        }
    }

    String getPrimitiveConstantValue(String value) {
        return "\"${value}\""
    }

    String getPrimitiveConstantValue(Long value) {
        return value
    }

    String getPrimitiveConstantValue(Double value) {
        return value
    }

    String getPrimitiveConstantValue(Boolean value) {
        return value.toString().capitalize()
    }

    String getConstantValue(IdlConstant constant) {
        if (constant.type.isPrimitive()) {
            return getPrimitiveConstantValue(constant)
        } else if (constant.type.isList()) {
            def values = []
            constant.value.each { value ->
                values.add(getPrimitiveConstantValue(value))
            }
            return "[" + values.join(", ") + "]"
        }
    }

    String isModelKeyAsString(IdlStructure structure) {
        if (structure.isModel()) {
            return "True"
        } else {
            return "False"
        }
    }

    String modelKeysAsString(IdlStructure structure) {
        List<IdlAttribute> keys = structure.getModelKeys()

        if (!keys) {
            return "None"
        }

        StringBuilder result = new StringBuilder()
        result.append("[")
        result.append(keys.collect { '"' + it.name.asCanonical + '"' }.join(", "))
        result.append("]")
        return result.toString()
    }

    List<IdlParameter> getRequiredParameters(IdlOperation operation) {
        def result = []
        operation.parameters.each { parameter ->
            IdlType type = parameter.impliedType ?: parameter.type
            if (!(type.isGeneric() && type.isOptional())) {
                result.add(parameter)
            }
        }
        return result
    }

    List<IdlParameter> getOptionalParameters(IdlOperation operation) {
        def result = []
        operation.parameters.each { parameter ->
            IdlType type = parameter.impliedType ?: parameter.type
            if ((type.isGeneric() && type.isOptional())) {
                result.add(parameter)
            }
        }
        return result
    }

    String getOperationNameIndent(IdlOperation operation) {
        return ' ' * operation.name.asLowerCaseWithUnderscores.length()
    }

    private boolean isClientTemplate() {
        char sep = File.separatorChar
        return naming.templateFile.file.path.endsWith("BASENAME_client.py")
    }

    private boolean isProviderTemplate() {
        char sep = File.separatorChar
        return naming.templateFile.file.path.endsWith("BASENAME_provider.py")
    }
}
