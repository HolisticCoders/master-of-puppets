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
        for attr in 'trs':
            for axis in 'xyz':
                attr_name = attr + axis
                cmds.setAttr(node + '.' + attr_name, lock=True, keyable=False, channelBox=False)
        cmds.setAttr(node + '.visibility', lock=True, keyable=False, channelBox=False)
    return node


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


def remove_action_units(action_units):
    facs_node = ensure_facs_node_exists()
    value = cmds.getAttr(facs_node + '.actionUnits')

    action_units = json.loads(
        value,
        object_pairs_hook=OrderedDict
    ) if value else {}

    for action_unit in action_units:
        if action_unit in action_units.keys():
            del action_units[action_unit]

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
        cmds.renameAttr(
            facs_node + '.' + nicename_to_camelcase(key_to_change),
            nicename_to_camelcase(new_name)
        )
        cmds.addAttr(
            facs_node + '.' + nicename_to_camelcase(new_name),
            edit=True,
            niceName=new_name
        )

    return new_dict
