import maya.cmds as cmds


def add_follicle(shape, transform):
    if cmds.nodeType(shape) == 'transform':
        shape = cmds.listRelatives(shape, shapes=True)[0] 
    follicle = cmds.createNode('follicle')
    follicle_transform = cmds.listRelatives(follicle, parent=True)[0]
    cmds.connectAttr(
        follicle + '.outTranslate',
        follicle_transform + '.translate'
    )
    cmds.connectAttr(
        follicle + '.outRotate',
        follicle_transform + '.rotate'
    )
    if cmds.nodeType(shape) == 'mesh':
        cmds.connectAttr(
            shape + '.outMesh',
            follicle + '.inputMesh'
        )
        closest_point_node = cmds.createNode('closestPointOnMesh')
        ctl_pos = cmds.xform(
            transform,
            query=True,
            translation=True,
            worldSpace=True
        )
        cmds.setAttr(
            closest_point_node + '.inPosition',
            *ctl_pos
        )
        cmds.connectAttr(
            shape + '.outMesh',
            closest_point_node + '.inMesh'
        )
        u_value = cmds.getAttr(closest_point_node + '.result.parameterU')
        v_value = cmds.getAttr(closest_point_node + '.result.parameterV')
        cmds.delete(closest_point_node)

    if cmds.nodeType(shape) == 'nurbsSurface':
        cmds.connectAttr(
            shape + '.local',
            follicle + '.inputSurface'
        )
        closest_point_node = cmds.createNode('closestPointOnSurface')
        ctl_pos = cmds.xform(
            transform,
            query=True,
            translation=True,
            worldSpace=True
        )
        cmds.setAttr(
            closest_point_node + '.inPosition',
            *ctl_pos
        )
        cmds.connectAttr(
            shape + '.local',
            closest_point_node + '.inputSurface'
        )
        u_value = cmds.getAttr(closest_point_node + '.result.parameterU')
        v_value = cmds.getAttr(closest_point_node + '.result.parameterV')
        cmds.delete(closest_point_node)

    cmds.setAttr(follicle + '.parameterU', u_value)
    cmds.setAttr(follicle + '.parameterV', v_value)
    return follicle
