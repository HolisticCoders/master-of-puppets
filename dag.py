import maya.cmds as cmds


def hierarchy_to_dict(parent, tree, nodes=[]):
    """Build a python `dict` based on a `transform` hierarchy.

    Args:
        parent (str): name of the hierarchy's root node.
        tree (dict): dictionary to store the data in.
        nodes (list): only these nodes should be included in the dict.
    """
    children = cmds.listRelatives(
        parent,
        children=True,
        type='transform'
    )
    if children:
        if nodes:
            children = [c for c in children if c in nodes]
        tree[parent] = {}
        for child in children:
            hierarchy_to_dict(child, tree[parent], nodes=nodes)
    else:
        tree[parent] = None


def dict_to_hierarchy(tree):
    """Parent DAG nodes based on a dictionnary.

    Args:
        tree (dict): Dictionary representing the hierarchy.
    """
    if tree:
        for parent, child_tree in tree.iteritems():
            if child_tree:
                for child in child_tree:
                    cmds.parent(child, parent)
                dict_to_hierarchy(child_tree)


def matrix_constraint(driver, driven, translate=True, rotate=True, scale=True, maintain_offset=False):
    if not cmds.objExists(driver):
        raise ValueError("{} driver does not exist".format(driver))
    if not cmds.objExists(driven):
        raise ValueError("{} driven does not exist".format(driven))

    driven_parent = cmds.listRelatives(driven, parent=True)[0]
    mult_mat = cmds.createNode('multMatrix')
    decompose_mat = cmds.createNode('decomposeMatrix')

    if maintain_offset:
        mult_mat_offset = cmds.createNode('multMatrix')
        cmds.connectAttr(
            driver + ".worldInverseMatrix[0]",
            mult_mat_offset + ".matrixIn[0]",
        )
        cmds.connectAttr(
            driven + ".worldMatrix[0]",
            mult_mat_offset + ".matrixIn[1]",
        )
        offset_mat = cmds.getAttr(mult_mat_offset + '.matrixSum') 
        cmds.setAttr(
            mult_mat + ".matrixIn[0]",
            offset_mat,
            type='matrix'
        )
        cmds.delete(mult_mat_offset)
    else:
        identity_mat = [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]
        cmds.setAttr(
            mult_mat + ".matrixIn[0]",
            identity_mat,
            type='matrix'
        )

    cmds.connectAttr(
        driver + ".worldMatrix[0]",
        mult_mat + ".matrixIn[1]",
    )
    cmds.connectAttr(
        driven_parent + ".worldInverseMatrix[0]",
        mult_mat + ".matrixIn[2]",
    )

    cmds.connectAttr(mult_mat + ".matrixSum", decompose_mat + ".inputMatrix")
    if translate:
        cmds.connectAttr(
            decompose_mat + ".outputTranslate",
            driven + ".translate"
        )

    if rotate:
        if cmds.nodeType(driven) == 'joint':
            # substract the driven's joint orient from the rotation
            euler_to_quat = cmds.createNode('eulerToQuat')
            quat_invert = cmds.createNode('quatInvert')
            quat_prod = cmds.createNode('quatProd')
            quat_to_euler = cmds.createNode('quatToEuler')

            cmds.connectAttr(
                driven + '.jointOrient',
                euler_to_quat + '.inputRotate',
            )
            cmds.connectAttr(
                euler_to_quat + '.outputQuat',
                quat_invert + '.inputQuat',
            )
            cmds.connectAttr(
                decompose_mat + ".outputQuat",
                quat_prod + '.input1Quat',
            )
            cmds.connectAttr(
                quat_invert + '.outputQuat',
                quat_prod + '.input2Quat',
            )
            cmds.connectAttr(
                quat_prod + '.outputQuat',
                quat_to_euler + '.inputQuat',
            )
            cmds.connectAttr(
                quat_to_euler + '.outputRotate',
                driven + '.rotate',
            )
        else:
            cmds.connectAttr(
                decompose_mat + ".outputRotate",
                driven + ".rotate"
            )
    if scale:
        cmds.connectAttr(
            decompose_mat + ".outputScale",
            driven + ".scale"
        )


def point_constraint(driver, driven, maintain_offset=False):
    if not cmds.objExists(driver):
        raise ValueError("{} driver does not exist".format(driver))
    if not cmds.objExists(driven):
        raise ValueError("{} driven does not exist".format(driven))

    driven_parent = cmds.listRelatives(driven, parent=True)[0]
    mult_mat = cmds.createNode('multMatrix')
    decompose_mat = cmds.createNode('decomposeMatrix')

    cmds.connectAttr(
        driver + ".worldMatrix[0]",
        mult_mat + ".matrixIn[0]",
    )

    if maintain_offset:
        mult_mat_offset = cmds.createNode('multMatrix')
        cmds.connectAttr(
            driver + ".worldInverseMatrix[0]",
            mult_mat_offset + ".matrixIn[0]",
        )
        cmds.connectAttr(
            driven + ".worldMatrix[0]",
            mult_mat_offset + ".matrixIn[1]",
        )
        offset_mat = cmds.getAttr(mult_mat_offset + '.matrixSum') 
        cmds.setAttr(
            mult_mat + ".matrixIn[1]",
            offset_mat,
            type='matrix'
        )
        cmds.delete(mult_mat_offset)
    else:
        identity_mat = [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]
        cmds.setAttr(
            mult_mat + ".matrixIn[1]",
            identity_mat,
            type='matrix'
        )

    cmds.connectAttr(
        driven_parent + ".worldInverseMatrix[0]",
        mult_mat + ".matrixIn[2]",
    )
    cmds.connectAttr(mult_mat + ".matrixSum", decompose_mat + ".inputMatrix")

    cmds.connectAttr(
        decompose_mat + ".outputTranslate",
        driven + ".translate"
    )


def add_parent_group(dag_node, suffix='grp'):
    dag_node_mat = cmds.xform(
        dag_node,
        query=True,
        matrix=True,
        worldSpace=True
    )
    grp = cmds.createNode('transform', name=dag_node + '_' + suffix)
    cmds.xform(grp, matrix=dag_node_mat, worldSpace=True)

    dag_node_parent = cmds.listRelatives(dag_node, parent=True)
    if dag_node_parent:
        cmds.parent(grp, dag_node_parent[0])

    cmds.parent(dag_node, grp)
    return grp


def snap_first_to_last(source, target):
    targ_mat = cmds.xform(
        target,
        query=True,
        matrix=True,
        worldSpace=True
    )
    cmds.xform(
        source,
        matrix=targ_mat,
        worldSpace=True
    )


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
    attrs_to_reset = cmds.listAttr(node, category='should_reset')
    if attrs_to_reset:
        for attribute in attrs_to_reset:
            defaultValue = cmds.addAttr(
                node + '.' + attribute,
                query=True,
                defaultValue=True
            )
            try:
                cmds.setAttr(node + '.' + attribute, defaultValue)
            except:
                pass


def create_parent_space(driven, drivers, translate=True, rotate=True):
    if translate and rotate:
        short_name = 'Space'
    elif not translate and rotate:
        short_name = 'Orient_Space'
    elif not translate and not rotate:
        return

    if isinstance(drivers, dict):
        names = drivers.keys()
        drivers = drivers.values()
    else:
        names = drivers

    cmds.addAttr(
        driven,
        longName='space',
        shortName=short_name,
        attributeType="enum",
        enumName=':'.join(names) + ':',
        keyable=True
    )

    driven_parent = add_parent_group(driven, suffix='PS')
    mult_mat = cmds.createNode('multMatrix')
    decompose_mat = cmds.createNode('decomposeMatrix')
    offset_choice = cmds.createNode('choice')
    driver_choice = cmds.createNode('choice')
    cmds.connectAttr(
        driven + '.space',
        offset_choice + '.selector'
    )
    cmds.connectAttr(
        driven + '.space',
        driver_choice + '.selector'
    )

    todel = []
    for i, driver in enumerate(drivers):
        cmds.addAttr(
            driven,
            longName = driver + '_offset',
            attributeType='matrix'
        )
        # get the offset between the driven and driver
        mult_mat_offset = cmds.createNode('multMatrix')
        todel.append(mult_mat_offset)
        cmds.connectAttr(
            driver + ".worldInverseMatrix[0]",
            mult_mat_offset + ".matrixIn[0]",
        )
        cmds.connectAttr(
            driven + ".worldMatrix[0]",
            mult_mat_offset + ".matrixIn[1]",
        )
        offset_mat= cmds.getAttr(mult_mat_offset + '.matrixSum')

        cmds.setAttr(
            driven + '.' + driver + '_offset',
            offset_mat,
            type='matrix'
        )
        cmds.connectAttr(
            driven + '.' + driver + '_offset',
            offset_choice + ".input[{}]".format(i),
        )

        cmds.connectAttr(
            driver + '.worldMatrix[0]',
            driver_choice + ".input[{}]".format(i),
        )

    cmds.connectAttr(
        offset_choice + ".output",
        mult_mat + ".matrixIn[0]",
    )
    cmds.connectAttr(
        driver_choice + ".output",
        mult_mat + ".matrixIn[1]",
    )
    parent = cmds.listRelatives(driven_parent, parent=True)[0]
    cmds.connectAttr(
        parent + ".worldInverseMatrix[0]",
        mult_mat + ".matrixIn[2]",
    )
    cmds.connectAttr(mult_mat + ".matrixSum", decompose_mat + ".inputMatrix")

    if translate:
        cmds.connectAttr(
            decompose_mat + ".outputTranslate",
            driven_parent + ".translate"
        )
    if rotate:
        cmds.connectAttr(
            decompose_mat + ".outputRotate",
            driven_parent + ".rotate"
        )
    cmds.delete(todel)

def create_point_space(driven, drivers):
    cmds.addAttr(
        driven,
        longName='space',
        shortName='Point_Space',
        attributeType="enum",
        enumName=':'.join(drivers) + ':',
        keyable=True
    )

    driven_parent = cmds.listRelatives(driven, parent=True)[0]
    mult_mat = cmds.createNode('multMatrix')
    decompose_mat = cmds.createNode('decomposeMatrix')
    offset_choice = cmds.createNode('choice')
    driver_choice = cmds.createNode('choice')
    cmds.connectAttr(
        driven + '.space',
        offset_choice + '.selector'
    )
    cmds.connectAttr(
        driven + '.space',
        driver_choice + '.selector'
    )

    todel = []
    for i, driver in enumerate(drivers):
        cmds.addAttr(
            driven_parent,
            longName = driver + '_offset',
            attributeType='matrix'
        )
        # get the offset between the driven and driver
        mult_mat_offset = cmds.createNode('multMatrix')
        todel.append(mult_mat_offset)
        cmds.connectAttr(
            driver + ".worldInverseMatrix[0]",
            mult_mat_offset + ".matrixIn[0]",
        )
        cmds.connectAttr(
            driven + ".worldMatrix[0]",
            mult_mat_offset + ".matrixIn[1]",
        )
        offset_mat= cmds.getAttr(mult_mat_offset + '.matrixSum')

        cmds.setAttr(
            driven_parent + '.' + driver + '_offset',
            offset_mat,
            type='matrix'
        )
        cmds.connectAttr(
            driven_parent + '.' + driver + '_offset',
            offset_choice + ".input[{}]".format(i),
        )

        cmds.connectAttr(
            driver + '.worldMatrix[0]',
            driver_choice + ".input[{}]".format(i),
        )

    cmds.connectAttr(
        offset_choice + ".output",
        mult_mat + ".matrixIn[1]",
    )
    cmds.connectAttr(
        driver_choice + ".output",
        mult_mat + ".matrixIn[0]",
    )
    cmds.connectAttr(
        driven_parent + ".worldInverseMatrix[0]",
        mult_mat + ".matrixIn[2]",
    )
    cmds.connectAttr(mult_mat + ".matrixSum", decompose_mat + ".inputMatrix")

    cmds.connectAttr(
        decompose_mat + ".outputTranslate",
        driven + ".translate"
    )
    cmds.delete(todel)

def create_orient_space(driven, drivers):
    create_parent_space(driven, drivers, translate=False, rotate=True)
