import os
import json

import maya.cmds as cmds


def get_shape_data(ctl):
    """Extract the shape data from a given controller
    
    :param ctl: name of the controller.
    :type ctl: str
    """
    data = []
    shapes = cmds.listRelatives(ctl, shapes=True)
    for shape in shapes:
        shape_data = {}

        # get the degree
        shape_data['degree'] = cmds.getAttr(shape + '.degree')
        if shape_data['degree'] != 1:
            raise ValueError('Shapeshifter only supports degree 1 curves for now')

        # get the color
        shape_data['enable_overrides'] = cmds.getAttr(shape + '.overrideEnabled')
        shape_data['use_rgb'] = cmds.getAttr(shape + '.overrideRGBColors')
        shape_data['color_index'] = cmds.getAttr(shape + '.overrideColor')
        rgb_colors = []
        for color_channel in 'RGB':
            rgb_colors.append(cmds.getAttr(shape + '.overrideColor' + color_channel))
        shape_data['color_rgb'] = rgb_colors

        if not shape_data['enable_overrides']:
            # get all of that from the transform instead
            shape_data['enable_overrides'] = cmds.getAttr(ctl + '.overrideEnabled')
            shape_data['use_rgb'] = cmds.getAttr(ctl + '.overrideRGBColors')
            shape_data['color_index'] = cmds.getAttr(ctl + '.overrideColor')
            rgb_colors = []
            for color_channel in 'RGB':
                rgb_colors.append(cmds.getAttr(ctl + '.overrideColor' + color_channel))
            shape_data['color_rgb'] = rgb_colors

        # get the cvs local position
        cvs = cmds.ls(shape + '.cv[*]', flatten=True)
        cvs_pos = []
        for cv in cvs:
            cvs_pos.append(cmds.xform(cv, q=True, t=True))
        shape_data['cvs'] = cvs_pos
        data.append(shape_data)

    return data


def export_shape(data, name):
    """Write the shape data in a json file.
    
    :param data: data of the shape to be written.
    :type data: list returned by ``get_shape_data``
    :param name: name of the json file.
    :type name: str
    """
    directory = os.path.dirname(__file__)
    shapes_dir = os.path.join(directory, 'shapes')

    if not os.path.exists(shapes_dir):
        os.makedirs(shapes_dir)

    shape_path = os.path.join(shapes_dir, name + '.json')
    with open(shape_path, 'w') as f:
        f.write(json.dumps(data, indent=2))


def import_shape(name):
    """Get the shape data written in the corresponding json file.

    :param name: name of the json file.
    :type name: str
    """
    directory = os.path.dirname(__file__)
    shapes_dir = os.path.join(directory, 'shapes')

    if not os.path.exists(shapes_dir):
        os.makedirs(shapes_dir)

    shape_path = os.path.join(shapes_dir, name + '.json')

    with open(shape_path, 'r') as f:
        return json.loads(f.read()) 


def create_controller_from_data(data):
    """Create a curve based on the given data.

    :param data: data of the shape to be created.
    :type data: list returned by ``get_shape_data`` or ``import_shape``
    """
    transform = cmds.createNode('transform')
    for shape_data in data:
        crv = cmds.curve(
            degree=shape_data['degree'],
            point=shape_data['cvs'],
        )
        shape = cmds.listRelatives(crv, shapes=True)[0]
        cmds.parent(shape, transform, relative=True, shape=True)
        cmds.delete(crv)
        if shape_data['enable_overrides']:
            cmds.setAttr(shape + '.overrideEnabled', True)
            if shape_data['use_rgb']:
                cmds.setAttr(shape + '.overrideRGBColors', 1)
                for color_channel, value in zip('RGB', shape_data['color_rgb']):
                    cmds.setAttr(shape + '.overrideColor' + color_channel, value)
            else:
                cmds.setAttr(shape + '.overrideColor', shape_data['color_index'])

    return transform


def create_controller_from_name(name):
    shape_data = import_shape(name)
    ctl = create_controller_from_data(shape_data)
    return ctl


def change_controller_shape(ctl, data):
    temp = create_controller_from_data(data)
    new_shapes = cmds.listRelatives(temp, shapes=True)
    cmds.delete(cmds.listRelatives(ctl, shapes=True))
    for shape in new_shapes:
        cmds.parent(shape, ctl, relative=True, shape=True)
        cmds.rename(shape, ctl + 'Shape')
    cmds.delete(temp)


def copy_shape(source, targets):
    """Copy the shape from one controller to the targets.

    :param source: controller to copy the shape from.
    :type source: str
    :param targets: controller(s) to copy the shape to.
    :type source: str or list(str)
    """
    if not isinstance(targets, list):
        targets = [targets]
    data = get_shape_data(source)
    for target in targets:
        temp = create_controller_from_data(data)
        new_shapes = cmds.listRelatives(temp, shapes=True)
        cmds.delete(cmds.listRelatives(target, shapes=True))
        for shape in new_shapes:
            cmds.parent(shape, target, relative=True, shape=True)
            cmds.rename(shape, target + 'Shape')
        cmds.delete(temp)
