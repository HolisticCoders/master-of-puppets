import maya.cmds as cmds

possible_data_types = [
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
    'pointArray' ,
    'reflectanceRGB',
    'spectrumRGB',
    'stringArray',
    'vectorArray',
]
possible_attribute_types = [
    'float',
    'bool',
    'byte',
    'char',
    'compound',
    'double',
    'double2',
    'double3',
    'doubleAngle',
    'doubleLinear',
    'enum',
    'float2',
    'float3',
    'fltMatrix',
    'long',
    'message',
    'reflectance',
    'short',
    'spectrum',
    'time',
]

def get_add_attribute_kwargs(attr_name):
    """Get all the keword arguments used to create ``attr_name``.
    
    :param attr_name: name of the attribute (node + attribute)
    :type attr_name: str
    """
    kwargs = {}

    attribute_type = cmds.addAttr(attr_name, query=True, attributeType=True)
    if attribute_type in possible_attribute_types:
        kwargs['attributeType'] = attribute_type
    if attribute_type == 'enum':
        kwargs['enumName'] = cmds.addAttr(attr_name, query=True, enumName=True)

    data_type = cmds.addAttr(attr_name, query=True, dataType=True)
    if data_type and data_type[0] in possible_data_types:
        kwargs['dataType'] = data_type[0]

    kwargs['category'] = cmds.addAttr(attr_name, query=True, category=True)

    # kwargs['hasMaxValue'] = cmds.addAttr(attr_name, query=True, hasMaxValue=True)
    # if kwargs['hasMaxValue']:
    #     kwargs['maxValue'] = cmds.addAttr(attr_name, query=True, maxValue=True)

    # kwargs['hasMinValue'] = cmds.addAttr(attr_name, query=True, hasMinValue=True)
    # if kwargs['hasMinValue']:
    #     kwargs['minValue'] = cmds.addAttr(attr_name, query=True, minValue=True)

    # kwargs['hasSoftMaxValue'] = cmds.addAttr(attr_name, query=True, hasSoftMaxValue=True)
    # if kwargs['hasSoftMaxValue']:
    #     kwargs['softMaxValue'] = cmds.addAttr(attr_name, query=True, softMaxValue=True)

    # kwargs['hasSoftMinValue'] = cmds.addAttr(attr_name, query=True, hasSoftMinValue=True)
    # if kwargs['hasSoftMinValue']:
    #     kwargs['softMinValue'] = cmds.addAttr(attr_name, query=True, softMinValue=True)

    # kwargs['hidden'] = cmds.addAttr(attr_name, query=True, hidden=True)
    # kwargs['internalSet'] = cmds.addAttr(attr_name, query=True, internalSet=True)
    # kwargs['keyable'] = cmds.addAttr(attr_name, query=True, keyable=True)
    # kwargs['longName'] = cmds.addAttr(attr_name, query=True, longName=True)

    # kwargs['multi'] = cmds.addAttr(attr_name, query=True, multi=True)
    # if kwargs['multi']:
    #     kwargs['indexMatters'] = cmds.addAttr(attr_name, query=True, indexMatters=True)

    # kwargs['niceName'] = cmds.addAttr(attr_name, query=True, niceName=True)

    # number_of_children = cmds.addAttr(attr_name, query=True, numberOfChildren=True)
    # if number_of_children:
    #     kwargs['numberOfChildren'] = number_of_children

    # kwargs['parent'] = cmds.addAttr(attr_name, query=True, parent=True)
    # kwargs['proxy'] = cmds.addAttr(attr_name, query=True, proxy=True)
    # kwargs['readable'] = cmds.addAttr(attr_name, query=True, readable=True)
    # kwargs['shortName'] = cmds.addAttr(attr_name, query=True, shortName=True)
    # kwargs['storable'] = cmds.addAttr(attr_name, query=True, storable=True)
    # kwargs['usedAsColor'] = cmds.addAttr(attr_name, query=True, usedAsColor=True)
    # kwargs['usedAsFilename'] = cmds.addAttr(attr_name, query=True, usedAsFilename=True)
    # kwargs['usedAsProxy'] = cmds.addAttr(attr_name, query=True, usedAsProxy=True)
    # kwargs['writable'] = cmds.addAttr(attr_name, query=True, writable=True)
    # kwargs['binaryTag'] = cmds.addAttr(attr_name, query=True, binaryTag=True)
    # kwargs['cachedInternally'] = cmds.addAttr(attr_name, query=True, cachedInternally=True)
    # kwargs['defaultValue'] = cmds.addAttr(attr_name, query=True, defaultValue=True)
    # kwargs['disconnectBehaviour'] = cmds.addAttr(attr_name, query=True, disconnectBehaviour=True)
    # kwargs['exists'] = cmds.addAttr(attr_name, query=True, exists=True)
    # kwargs['fromPlugin'] = cmds.addAttr(attr_name, query=True, fromPlugin=True)

    return kwargs
