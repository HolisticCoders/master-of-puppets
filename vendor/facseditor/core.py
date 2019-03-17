from collections import OrderedDict
import json
import logging
import maya.cmds as cmds
import re


logger = logging.getLogger(__name__)


def camelcase_to_nicename(name):
    return re.sub("([a-z])([A-Z0-9])","\g<1> \g<2>", name).title()


def nicename_to_camelcase(name):
    res = re.sub(r'(?!^) ([a-zA-Z0-9])', lambda m: m.group(1).upper(), name)
    res = res[0].lower() + res[1:]
    return res


def ensure_facs_node_exists():
    """Makes sure the `FACS_CONTROL` node exists."""
    node = 'FACS_CONTROL'
    if not cmds.objExists('FACS_CONTROL'):
        cmds.createNode('transform', name=node)
        cmds.addAttr(node, ln='actionUnits', dataType='string')
        cmds.addAttr(node, ln='actionUnitEditing', dataType='string')
        for attr in 'trs':
            for axis in 'xyz':
                attr_name = attr + axis
                cmds.setAttr(node + '.' + attr_name, lock=True, keyable=False, channelBox=False)
        cmds.setAttr(node + '.visibility', lock=True, keyable=False, channelBox=False)
    return node


def get_editing_action_unit():
    facs_node = ensure_facs_node_exists()
    return cmds.getAttr(facs_node + '.actionUnitEditing')


def is_editing():
    return bool(get_editing_action_unit())


def get_action_units_dict():
    """Get the dictionary listing all the action units and controls."""
    facs_node = ensure_facs_node_exists()
    value = cmds.getAttr(facs_node + '.actionUnits')
    action_units = json.loads(
        value,
        object_pairs_hook=OrderedDict
    ) if value else {}
    return action_units


def get_action_units():
    """Get the a list of all the action units."""
    return get_action_units_dict().keys()


def get_controllers(action_unit):
    """Get all the controls related to one action unit.

    :param action_unit: The action unit to get the controls from.
    :rtype action_unit: str.
    """
    action_units_dict = get_action_units_dict()
    return action_units_dict.get(action_unit, [])

def add_parent_group(node, name):
    parent_group = cmds.createNode('transform', name=name)
    mat = cmds.xform(node, query=True, matrix=True, worldSpace=True)
    cmds.xform(parent_group, matrix=mat, worldSpace=True)
    node_parent = cmds.listRelatives(node, parent=True)
    if node_parent is not None:
        cmds.parent(parent_group, node_parent[0])
    cmds.parent(node, parent_group)
    return parent_group


def reset_node(node):
    for attribute in ['translate', 'rotate', 'scale']:
        for axis in 'XYZ':
            attr = node + '.' + attribute + axis
            if attribute == 'scale':
                value = 1
            else:
                value = 0
            try:
                cmds.setAttr(attr, value)
            except:
                pass


def reorder_attributes(node, new_order):
    attr_data = {}
    for attribute in new_order:
        data = {}
        attr = node + '.' + attribute
        data['value'] = cmds.getAttr(attr)
        data['locked'] = cmds.getAttr(attr, lock=True)
        source = cmds.listConnections(attr, source=True, destination=False, plugs=True)
        data['source'] = source[0] if source else None
        data['destinations'] = cmds.listConnections(attr, destination=True, source=False, plugs=True)
        data['hasMinValue'] = cmds.addAttr(attr, query=True, hasMinValue=True)
        data['minValue'] = cmds.addAttr(attr, query=True, minValue=True)
        data['hasMaxValue'] = cmds.addAttr(attr, query=True, hasMaxValue=True)
        data['maxValue'] = cmds.addAttr(attr, query=True, maxValue=True)
        data['niceName'] = cmds.addAttr(attr, query=True, niceName=True)
        attr_data[attribute] = data
        cmds.deleteAttr(attr)

    for attribute in new_order:
        data = attr_data[attribute]
        attr = node + '.' + attribute 
        cmds.addAttr(
            node,
            longName=attribute,
            niceName=data['niceName'],
            hasMinValue=data['hasMinValue'],
            minValue=data['minValue'],
            hasMaxValue=data['hasMaxValue'],
            maxValue=data['maxValue'],
            keyable=True
        )
        cmds.setAttr(attr, data['value'])
        if data['source']:
            cmds.connectAttr(data['source'], attr)
        if data['destinations']:
            for dest in data['destinations']:
                cmds.connectAttr(attr, dest)
        if data['locked']:
            cmds.setAttr(attr, lock=True)


def add_action_unit():
    """Add an action unit.

    On top of adding an action unit to the action_units_dict it:
        - Creates the control attribute on the `FACS_CONTROL` node.
        - Creates the unit to time conversion node.
    """
    facs_node = ensure_facs_node_exists()
    value = cmds.getAttr(facs_node + '.actionUnits')
    action_units = json.loads(
        value,
        object_pairs_hook=OrderedDict
    ) if value else {}

    name = 'New Action Unit ' + str(len(action_units)).zfill(3)
    action_units[name] = []
    cmds.setAttr(
        facs_node + '.actionUnits',
        json.dumps(action_units),
        type='string'
    )
    attr_name = nicename_to_camelcase(name)
    cmds.addAttr(
        facs_node,
        longName=attr_name,
        niceName=name,
        hasMinValue=True,
        minValue=0,
        hasMaxValue=True,
        maxValue=10,
        keyable=True,
        attributeType='double'
    )
    unit_to_time = cmds.createNode('unitToTimeConversion', name=attr_name + '_unitToTime')
    cmds.connectAttr(
        facs_node + '.' + attr_name,
        unit_to_time + '.input'
    )


def remove_action_units(action_units_to_del):
    facs_node = ensure_facs_node_exists()
    value = cmds.getAttr(facs_node + '.actionUnits')

    action_units = json.loads(
        value,
        object_pairs_hook=OrderedDict
    ) if value else {}

    for action_unit in action_units_to_del:
        if action_unit in action_units.keys():
            del action_units[action_unit]
            cmds.deleteAttr(facs_node, attribute=nicename_to_camelcase(action_unit))
            cmds.delete(nicename_to_camelcase(action_unit) + '_unitToTime')

    cmds.setAttr(
        facs_node + '.actionUnits',
        json.dumps(action_units),
        type='string'
    )


def rename_action_unit(index, new_name):
    action_units_dict = get_action_units_dict()
    new_dict = OrderedDict()
    if new_name in action_units_dict.keys():
        if action_units_dict.keys().index(new_name) != index:
            # log only if the name is not the one we're currently editing
            logger.warning('An action unit named "{}" already exists'.format(
                new_name
            ))
        new_dict = action_units_dict
    else:
        key_to_change = action_units_dict.keys()[index]
        for key, value in action_units_dict.iteritems():
            if key == key_to_change:
                new_dict[new_name] = value
            else:
                new_dict[key] = value

        facs_node = ensure_facs_node_exists()
        if not nicename_to_camelcase(new_name) == nicename_to_camelcase(key_to_change):
            cmds.renameAttr(
                facs_node + '.' + nicename_to_camelcase(key_to_change),
                nicename_to_camelcase(new_name)
            )
        cmds.addAttr(
            facs_node + '.' + nicename_to_camelcase(new_name),
            edit=True,
            niceName=new_name
        )
        cmds.rename(
            nicename_to_camelcase(key_to_change) + '_unitToTime',
            nicename_to_camelcase(new_name) + '_unitToTime',
        )

    return new_dict


def move_action_unit(new_key, new_index):
    action_units_dict = get_action_units_dict()
    action_units_dict[new_key] = action_units_dict.pop(new_key)
    i = 0
    for key, value in action_units_dict.items():
        if key != new_key and i >= new_index:
            action_units_dict[key] = action_units_dict.pop(key)
        i += 1
    facs_node = ensure_facs_node_exists()
    new_order = map(nicename_to_camelcase, action_units_dict.keys())
    reorder_attributes(facs_node, new_order)
    return action_units_dict


def add_controllers_to_action_unit(action_unit):
    maya_sel = cmds.ls(sl=True)
    action_units_dict = get_action_units_dict()
    new_controls = set(action_units_dict.get(action_unit, [])) | set(maya_sel)
    action_units_dict[action_unit] = list(sorted(new_controls))
    facs_node = ensure_facs_node_exists()
    cmds.setAttr(
        facs_node + '.actionUnits',
        json.dumps(action_units_dict),
        type='string'
    )
    for control in new_controls:
        parent_group_name = control + '_' + nicename_to_camelcase(action_unit)
        if not cmds.objExists(parent_group_name):
            add_parent_group(control, name=parent_group_name)


def remove_controllers_from_action_unit(action_unit, controllers):
    action_units_dict = get_action_units_dict()
    action_unit_controllers = action_units_dict[action_unit]
    for controller in controllers:
        action_unit_controllers.remove(controller)
        action_unit_group = controller + '_' + nicename_to_camelcase(action_unit)
        parent = cmds.listRelatives(action_unit_group, parent=True)
        children = cmds.listRelatives(action_unit_group)
        for child in children:
            if parent:
                cmds.parent(child, parent[0])
            else:
                cmds.parent(child, world=True)
        cmds.delete(action_unit_group)
    action_units_dict[action_unit] = action_unit_controllers
    facs_node = ensure_facs_node_exists()
    cmds.setAttr(
        facs_node + '.actionUnits',
        json.dumps(action_units_dict),
        type='string'
    )


def edit_action_unit(action_unit):
    facs_node = ensure_facs_node_exists()
    for au in get_action_units():
        cmds.setAttr(facs_node + '.' + nicename_to_camelcase(au), 0)
    controllers = get_controllers(action_unit)
    cmds.setAttr(facs_node + '.actionUnitEditing', action_unit, type='string')
    for controller in controllers:
        action_unit_group = controller + '_' + nicename_to_camelcase(action_unit)
        for attr in ['translate', 'rotate', 'scale']:
            for axis in 'XYZ':
                attr_name = attr + axis
                anim_curves = cmds.listConnections(
                    action_unit_group + '.' +  attr_name,
                    source=True,
                    destination=False,
                    type='animCurve'
                )
                if anim_curves:
                    for anim_curve in anim_curves:
                        cmds.disconnectAttr(
                            anim_curve + '.' + 'output',
                            action_unit_group + '.' + attr_name
                        )
                        cmds.connectAttr(
                            anim_curve + '.' + 'output',
                            controller + '.' + attr_name
                        )
        reset_node(action_unit_group)
        cmds.setKeyframe(
            facs_node,
            attribute=nicename_to_camelcase(action_unit),
            value=0,
            time=0,
            outTangentType='linear',
            inTangentType='linear'
        )
        cmds.setKeyframe(
            facs_node,
            attribute=nicename_to_camelcase(action_unit),
            value=10,
            time=10,
            outTangentType='linear',
            inTangentType='linear'
        )

def finish_edit():
    facs_node = ensure_facs_node_exists()
    action_unit = cmds.getAttr(facs_node + '.actionUnitEditing')
    controllers = get_controllers(action_unit)
    for controller in controllers:
        action_unit_group = controller + '_' + nicename_to_camelcase(action_unit)
        for attr in ['translate', 'rotate', 'scale']:
            for axis in 'XYZ':
                attr_name = attr + axis
                anim_curves = cmds.listConnections(
                    controller + '.' +  attr_name,
                    source=True,
                    destination=False,
                    type='animCurve'
                )
                if anim_curves:
                    for anim_curve in anim_curves:
                        keyframe_values = cmds.keyframe(anim_curve, query=True, valueChange=True)
                        if len(set(keyframe_values)) <= 1:  # if all the values are the same
                            cmds.delete(anim_curve)
                        else:
                            cmds.disconnectAttr(
                                anim_curve + '.' + 'output',
                                controller + '.' + attr_name
                            )
                            cmds.connectAttr(
                                anim_curve + '.' + 'output',
                                action_unit_group + '.' + attr_name
                            )
                            unit_to_time = nicename_to_camelcase(action_unit) + '_unitToTime'
                            cmds.connectAttr(
                                unit_to_time + '.output',
                                anim_curve + '.input',
                                force=True
                            )
        reset_node(controller)
        cmds.delete(
            cmds.listConnections(
                facs_node + '.' + nicename_to_camelcase(action_unit),
                source=True,
                destination=False,
                type='animCurve'
            )
        )
        cmds.setAttr(facs_node + '.' + nicename_to_camelcase(action_unit), 0)

    cmds.setAttr(facs_node + '.actionUnitEditing', '', type='string')
