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

attr_whitelist = [
    'translateX',           'translateY',           'translateZ',
    'rotateX',              'rotateY',              'rotateZ',
    'scaleX',               'scaleY',               'scaleZ',
    'maxTransXLimit',       'maxTransYLimit',       'maxTransZLimit',
    'minTransXLimit',       'maxTransYLimit',       'maxTransZLimit',
    'maxTransXLimitEnable', 'maxTransZLimitEnable', 'maxTransZLimitEnable',
    'minTransXLimitEnable', 'minTransZLimitEnable', 'minTransZLimitEnable',
    'maxRotXLimit',         'maxRotYLimit',         'maxRotZLimit',
    'minRotXLimit',         'maxRotYLimit',         'maxRotZLimit',
    'maxRotXLimitEnable',   'maxRotZLimitEnable',   'maxRotZLimitEnable',
    'minRotXLimitEnable',   'minRotZLimitEnable',   'minRotZLimitEnable',
    'maxScaleXLimit',       'maxScaleYLimit',       'maxScaleZLimit',
    'minScaleXLimit',       'maxScaleYLimit',       'maxScaleZLimit',
    'maxScaleXLimitEnable', 'maxScaleZLimitEnable', 'maxScaleZLimitEnable',
    'minScaleXLimitEnable', 'minScaleZLimitEnable', 'minScaleZLimitEnable',
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


def get_attributes_state(node):
    """Get all the attribute data for the ``node``.

    :param node: node to get the attribute data from
    :param node: str
    """
    attributes_state = {}
    for attr in cmds.listAttr(node):
        if attr not in attr_whitelist:
            continue
        attr_name = node + '.' + attr
        attr_state = {}
        attr_state['lock'] = cmds.getAttr(
            attr_name,
            lock=True
        )
        attr_state['keyable'] = cmds.getAttr(
            attr_name,
            keyable=True
        )
        attr_state['channelBox'] = cmds.getAttr(
            attr_name,
            channelBox=True
        )
        attr_state['value'] = cmds.getAttr(attr_name)
        attributes_state[attr] = attr_state
    return attributes_state


def set_attributes_state(node, attributes_state):
    for attr in cmds.listAttr(node):
        if attr not in attributes_state:
            continue
        attr_name = node + '.' + attr
        attr_state = attributes_state[attr]
        value = attr_state.pop('value')
        cmds.setAttr(attr_name, keyable=attr_state['keyable'])
        cmds.setAttr(attr_name, lock=attr_state['lock'])
        cmds.setAttr(attr_name, channelBox=attr_state['channelBox'])
        try:
            cmds.setAttr(attr_name, value)
        except:
            pass
