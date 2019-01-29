import maya.cmds as cmds

import icarus.dag
import icarus.metadata


def build_foot(module):
    """Build a foot.

    :param module: module to add the foot on.
    :type module: icarus.core.module.RigModule
    """
    create_foot_pivots(module)
    create_ik_handles(module)
    create_attributes(module)

    # heel setup
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'clamp',
        'description': '0_to_neg_90'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    clamp = cmds.createNode('clamp', name=name)
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.footRoll',
        clamp + '.inputR'
    )
    cmds.setAttr(clamp + '.minR', -90)
    cmds.connectAttr(
        clamp + '.outputR',
        module.heel_pivot.get() + '.rotateX'
    )

    # tip setup
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'percent',
        'description': 'bend_to_straight'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    bend_to_straight_percent = cmds.createNode('setRange', name=name)
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.bendLimitAngle',
        bend_to_straight_percent + '.oldMinX'
    )
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.toeStraightAngle',
        bend_to_straight_percent + '.oldMaxX'
    )
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.footRoll',
        bend_to_straight_percent + '.valueX'
    )
    cmds.setAttr(bend_to_straight_percent + '.maxX', 1)

    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'mult',
        'description': 'tip_roll'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    tip_roll_mult = cmds.createNode('multDoubleLinear', name=name)
    cmds.connectAttr(
        bend_to_straight_percent + '.outValueX',
        tip_roll_mult + '.input1'
    )
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.footRoll',
        tip_roll_mult + '.input2'
    )
    cmds.connectAttr(
        tip_roll_mult + '.output',
        module.tip_pivot.get() + '.rotateX'
    )

    # ball setup
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'percent',
        'description': 'zero_to_bend'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    zero_to_bend_percent = cmds.createNode('setRange', name=name)
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.bendLimitAngle',
        zero_to_bend_percent + '.oldMaxX'
    )
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.footRoll',
        zero_to_bend_percent + '.valueX'
    )
    cmds.setAttr(zero_to_bend_percent + '.maxX', 1)
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'reverse',
        'description': 'bend_to_straight'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    bend_to_straight_reverse = cmds.createNode('reverse', name=name)
    cmds.connectAttr(
        bend_to_straight_percent + '.outValueX',
        bend_to_straight_reverse + '.inputX'
    )
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'mult',
        'description': 'ball_percent'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    ball_percent_mult = cmds.createNode('multDoubleLinear', name=name)
    cmds.connectAttr(
        bend_to_straight_reverse + '.outputX',
        ball_percent_mult + '.input1'
    )
    cmds.connectAttr(
        zero_to_bend_percent + '.outValueX',
        ball_percent_mult + '.input2'
    )
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'mult',
        'description': 'ball_roll'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    ball_roll_mult = cmds.createNode('multDoubleLinear', name=name)
    cmds.connectAttr(
        ball_percent_mult + '.output',
        ball_roll_mult + '.input1'
    )
    cmds.connectAttr(
        module.ik_end_ctl.get() + '.footRoll',
        ball_roll_mult + '.input2'
    )
    cmds.connectAttr(
        ball_roll_mult + '.output',
        module.ball_pivot.get() + '.rotateX'
    )


def create_foot_pivots(module):
    """Create the pivots for the foot roll

    :param module: module to add the foot on.
    :type module: icarus.core.module.RigModule
    """
    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'grp',
        'description': 'foot_roll_pivots'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    pivots_grp = cmds.createNode('transform', name=name)
    icarus.dag.snap_first_to_last(pivots_grp, module.extras_group.get())
    cmds.parent(pivots_grp, module.extras_group.get())
    icarus.dag.matrix_constraint(module.ik_end_ctl.get(), pivots_grp, maintain_offset=True)

    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'pivot',
        'description': 'heel'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    module.heel_pivot.set(cmds.spaceLocator(name=name)[0])
    icarus.dag.snap_first_to_last(
        module.heel_pivot.get(),
        module.heel_placement.get()
    )

    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'pivot',
        'description': 'ball'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    module.ball_pivot.set(cmds.spaceLocator(name=name)[0])
    icarus.dag.snap_first_to_last(
        module.ball_pivot.get(),
        module.ball_placement.get()
    )

    metadata = {
        'base_name': module.name.get(),
        'side': module.side.get(),
        'role': 'pivot',
        'description': 'tip'
    }
    name = icarus.metadata.name_from_metadata(metadata)
    module.tip_pivot.set(cmds.spaceLocator(name=name)[0])
    icarus.dag.snap_first_to_last(
        module.tip_pivot.get(),
        module.tip_placement.get()
    )
    cmds.parent(
        module.ball_pivot.get(),
        module.tip_pivot.get(),
    )
    cmds.parent(
        module.tip_pivot.get(),
        module.heel_pivot.get()
    )
    cmds.parent(
        module.heel_pivot.get(),
        pivots_grp
    )


def create_ik_handles(module):
    """Create the ik handles for the foot roll

    :param module: module to add the foot on.
    :type module: icarus.core.module.RigModule
    """
    ball_ikHandle, ball_effector = cmds.ikHandle(
        startJoint=module.driving_chain[-1],  # ankle joint
        endEffector=module.foot_driving_joints[0],  # ball joint 
        sol='ikSCsolver'
    )
    cmds.parent(ball_ikHandle, module.ball_pivot.get())

    tip_ikHandle, tip_effector = cmds.ikHandle(
        startJoint=module.foot_driving_joints[0],  # ball joint
        endEffector=module.foot_driving_joints[1],  # tip joint
        sol='ikSCsolver'
    )
    cmds.parent(tip_ikHandle, module.tip_pivot.get())

    cmds.parent(module.ik_handle.get(), module.ball_pivot.get())

def create_attributes(module):
    print module.ik_end_ctl.get()
    cmds.addAttr(
        module.ik_end_ctl.get(),
        longName='footRoll',
        attributeType='double',
        keyable=True
    )
    cmds.addAttr(
        module.ik_end_ctl.get(),
        longName='bendLimitAngle',
        attributeType='double',
        defaultValue=45,
        keyable=True
    )
    cmds.addAttr(
        module.ik_end_ctl.get(),
        longName='toeStraightAngle',
        attributeType='double',
        defaultValue=70,
        keyable=True
    )
