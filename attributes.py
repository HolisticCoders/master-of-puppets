import maya.cmds as cmds


valid_data_types = [
    'matrix',
    'string',
    'double2',
    'double3',
    'doubleArray',
    'float2',
    'float3',
    'floatArray',
    'lattice',
    'mesh',
    'nurbsCurve',
    'nurbsSurface',
    'pointArray',
    'reflectanceRGB',
    'spectrumRGB',
    'stringArray',
    'vectorArray',
]


def create_persistent_attribute(node, module_node, *args, **kwargs):
    """Create an attribute that keeps its value when rebuilding."""
    category = kwargs.pop('category', kwargs.pop('ct', []))
    source_category = list(category)
    source_category.append('persistent_attribute_source')
    long_name = kwargs.pop('longName', kwargs.pop('ln', None))

    cmds.addAttr(
        node,
        longName=long_name,
        category=source_category,
        *args,
        **kwargs
    )

    module_attr_name = node + '__' + long_name
    if cmds.attributeQuery(module_attr_name, node=module_node, exists=True):
        value = cmds.getAttr(module_node + '.' + module_attr_name)
        data_type = cmds.addAttr(
            module_node + '.' + module_attr_name,
            query=True,
            dataType=True
        )
        kwargs = {}
        if data_type and data_type[0] in valid_data_types:
            kwargs['type'] = data_type[0]
        cmds.setAttr(node + '.' + long_name, value, **kwargs)
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
