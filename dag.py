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


def matrix_constraint(driver, driven, translate=True, rotate=True, scale=True):
    if not cmds.objExists(driver):
        raise ValueError("{} driver does not exist".format(driver))
    if not cmds.objExists(driven):
        raise ValueError("{} driven does not exist".format(driven))

    mult_mat = cmds.createNode('multMatrix')
    decompose_mat = cmds.createNode('decomposeMatrix')

    cmds.connectAttr(driver + ".worldMatrix[0]", mult_mat + ".matrixIn[0]")
    cmds.connectAttr(
        driven + ".parentInverseMatrix[0]",
        mult_mat + ".matrixIn[1]"
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
                decompose_mat + '.outputQuat',
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
            cmds.connectAttr(decompose_mat + ".outputRotate", driven + ".rotate")
    if scale:
        cmds.connectAttr(decompose_mat + ".outputScale", driven + ".scale")


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