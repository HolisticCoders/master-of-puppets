import maya.cmds as cmds

def create_persistent_attribute(node, module_node, *args, **kwargs):
    """Create an attribute that keeps its value when rebuilding."""
    category = kwargs.pop('category', kwargs.pop('ct', []))
    source_category = list(category)
    source_category.append('persistent_attribute_source')
    long_name = kwargs.pop('longName', kwargs.pop('ln', None))

    cmds.addAttr(node, longName=long_name, category=source_category, *args, **kwargs)

    module_attr_name = node + '__' + long_name
    if cmds.attributeQuery(module_attr_name, node=module_node, exists=True):
        value = cmds.getAttr(module_node + '.' + module_attr_name)
        data_type = cmds.addAttr(
            module_node + '.' + module_attr_name,
            query=True,
            dataType=True
        )
        if data_type:
            data_type = data_type[0]
        else:
            data_type = None
        cmds.setAttr(node + '.' + long_name, value, type=data_type)
    else:
        backup_category = list(category)
        backup_category.append('persistent_attribute_backup')
        kwargs.pop('keyable', None)
        kwargs.pop('k', None)
        cmds.addAttr(
            module_node,
            longName=module_attr_name,
            category=backup_category,
            *args,
            **kwargs
        )
    cmds.connectAttr(
        node + '.' + long_name,
        module_node + '.' + module_attr_name
    )
