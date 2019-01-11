import maya.cmds as cmds


def name_from_metadata(
    object_base_name,
    object_side,
    object_type,
    object_id=None,
    object_description=None
):
    """Generate a node name from the given metadata.

    This function should be used EVERYTIME a node is named.
    """
    name_components = [
        object_base_name,
        object_side,
        object_type,
    ]
    if object_description is not None:
        name_components.insert(2, object_description)
    if object_id is not None:
        object_id = str(object_id).zfill(3)
        name_components.insert(-1, object_id)
    name = '_'.join(name_components)
    return name


def metadata_from_name(name):
    data = {}
    split_name = name.split('_')

    # every name should at least contain these 3 components.
    data['base_name'] = split_name.pop(0)
    data['side'] = split_name.pop(0)
    data['type'] = split_name.pop(-1)

    # try to get the optional components.
    if split_name:
        try:
            # only works if the last component is the object id.
            data['id'] = int(split_name.pop(-1))
        except ValueError:
            # if it was not the id, it can only be the description.
            data['description'] = '_'.join(split_name)
        else:
            if split_name:
                # since we removed the id,
                # the description is the last component.
                data['description'] = '_'.join(split_name)
    return data


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
        cmds.setAttr(node + '.' + long_name, value)
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

