import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, JSONField, ObjectField
import icarus.dag
import icarus.metadata


class Arm(RigModule):

    chain_length = IntField(
        defaultValue=3,
        hasMinValue=True,
        hasMaxValue=True,
        minValue=3,
        maxValue=3,
    )

    # list containing the FK joints in the same order as the hierarchy
    fk_chain = JSONField()

    # list containing the IK joints in the same order as the hierarchy
    ik_chain = JSONField()

    # list containing the FK controls in the same order as the hierarchy.
    fk_controls = JSONField()

    # list containing the IK controls.
    ik_controls = JSONField()

    # group containing all the FK controls
    fk_controls_group = ObjectField()

    # group containing all the IK controls
    ik_controls_group = ObjectField()

    # settings control of the arm.
    settings_ctl = ObjectField()

    ik_handle = ObjectField()
    effector = ObjectField()

    def initialize(self, *args, **kwargs):
        for i in range(self.chain_length.get()):
            self._add_deform_joint()

    def _add_deform_joint(self):
        """Add a new deform joint, child of the last one."""
        parent = None
        deform_joints = self.deform_joints_list.get()
        if deform_joints:
            parent = deform_joints[-1]
        return super(Arm, self)._add_deform_joint(parent=parent)

    def build(self):
        self._create_ik_fk_chains()
        self._create_settings_control()
        self._setup_fk()
        self._setup_ik()
        self._setup_ik_fk_switch()

    def _create_ik_fk_chains(self):
        driving_chain = self.driving_joints

        # create the fk chain
        fk_chain = cmds.duplicate(
            driving_chain[0],
            renameChildren=True,
        )
        for i, fk in enumerate(fk_chain):
            fk_chain[i] = cmds.rename(
                fk,
                fk.replace('driving1', 'fk')
            )
        cmds.parent(fk_chain[0], self.extras_group.get())
        self.fk_chain.set(fk_chain)

        # create the fk chain
        ik_chain = cmds.duplicate(
            driving_chain[0],
            renameChildren=True,
        )
        for i, ik in enumerate(ik_chain):
            ik_chain[i] = cmds.rename(
                ik,
                ik.replace('driving1', 'ik')
            )
        cmds.parent(ik_chain[0], self.extras_group.get())
        self.ik_chain.set(ik_chain)

    def _create_settings_control(self):
        ctl = cmds.circle()[0]
        ctl = cmds.rename(ctl, icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='ctl',
            object_description='settings'
        ))
        icarus.dag.snap_first_to_last(
            ctl,
            self.driving_joints[-1]
        )
        self.settings_ctl.set(ctl)
        buffer_grp = icarus.dag.add_parent_group(ctl, 'buffer')
        cmds.parent(buffer_grp, self.controls_group.get())
        icarus.dag.matrix_constraint(self.driving_joints[-1], buffer_grp)

        for attr in ['translate', 'rotate', 'scale']:
            for axis in 'XYZ':
                attrName = ctl + '.' + attr + axis
                cmds.setAttr(
                    attrName,
                    lock=True,
                    keyable=False,
                    channelBox=False
                )
        cmds.setAttr(
            ctl + '.visibility',
            lock=True,
            keyable=False,
            channelBox=False
        )

        cmds.addAttr(
            ctl,
            longName="IK_FK_Switch",
            niceName="IK/FK",
            attributeType="enum",
            enumName="IK:FK:"
        )
        cmds.setAttr(ctl + ".IK_FK_Switch", keyable=True)

    def _setup_ik_fk_switch(self):
        """Create the necessary nodes to switch between the ik and fk chains """
        driving_chain = self.driving_joints
        fk_chain = self.fk_chain.get()
        ik_chain = self.ik_chain.get()
        settings_ctl = self.settings_ctl.get()

        # Show the IK or FK controls based on the settings
        cmds.connectAttr(
            settings_ctl + '.IK_FK_Switch',
            self.fk_controls_group.get() + '.visibility'
        )
        reverse_switch = cmds.createNode('reverse')
        cmds.connectAttr(
            settings_ctl + ".IK_FK_Switch",
            reverse_switch + ".inputX"
        )
        cmds.connectAttr(
            reverse_switch + '.outputX',
            self.ik_controls_group.get() + '.visibility'
        )

        for i in xrange(len(driving_chain)):
            driving = driving_chain[i]
            fk = fk_chain[i]
            ik = ik_chain[i]
            wt_add_mat = cmds.createNode('wtAddMatrix')
            mult_mat = cmds.createNode('multMatrix')
            decompose_mat = cmds.createNode('decomposeMatrix')
            cmds.connectAttr(
                fk + ".worldMatrix[0]",
                wt_add_mat + ".wtMatrix[0].matrixIn"
            )
            cmds.connectAttr(
                ik + ".worldMatrix[0]",
                wt_add_mat + ".wtMatrix[1].matrixIn"
            )
            cmds.connectAttr(
                settings_ctl + ".IK_FK_Switch",
                wt_add_mat + ".wtMatrix[0].weightIn"
            )
            cmds.connectAttr(
                reverse_switch + ".outputX",
                wt_add_mat + ".wtMatrix[1].weightIn"
            )
            cmds.connectAttr(
                wt_add_mat + ".matrixSum",
                mult_mat + '.matrixIn[0]',
            )
            cmds.connectAttr(
                driving + '.parentInverseMatrix[0]',
                mult_mat + '.matrixIn[1]',
            )
            cmds.connectAttr(
                mult_mat + ".matrixSum",
                decompose_mat + ".inputMatrix"
            )

            # substract the driven's joint orient from the rotation
            euler_to_quat = cmds.createNode('eulerToQuat')
            quat_invert = cmds.createNode('quatInvert')
            quat_prod = cmds.createNode('quatProd')
            quat_to_euler = cmds.createNode('quatToEuler')

            cmds.connectAttr(
                driving + '.jointOrient',
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

            # connect the graph to the driving joint's transform attributes
            cmds.connectAttr(
                decompose_mat + '.outputTranslate',
                driving + '.translate'
            )
            cmds.connectAttr(
                quat_to_euler + '.outputRotate',
                driving + '.rotate',
            )
            cmds.connectAttr(
                decompose_mat + '.outputScale',
                driving + '.scale'
            )

    def _setup_fk(self):
        fk_controls = self.fk_controls.get()
        fk_controls_group_name = icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='grp',
            object_description='FK_controls',
        )
        self.fk_controls_group.set(
             cmds.createNode('transform', name=fk_controls_group_name)
        )
        cmds.parent(self.fk_controls_group.get(), self.controls_group.get())
        if fk_controls is None:
            fk_controls = []
        parent = self.fk_controls_group.get()
        for i, fk in enumerate(self.fk_chain.get()):
            ctl = cmds.circle()[0]
            ctl = cmds.rename(ctl, icarus.metadata.name_from_metadata(
                object_base_name=self.name.get(),
                object_side=self.side.get(),
                object_type='ctl',
                object_description='FK',
                object_id=i,
            ))
            icarus.dag.snap_first_to_last(ctl, fk)
            parent_group = icarus.dag.add_parent_group(ctl, 'buffer')
            cmds.parent(parent_group, parent)
            icarus.dag.matrix_constraint(ctl, fk)
            parent = ctl

    def _setup_ik(self):
        ik_chain = self.ik_chain.get()
        ik_controls_group_name = icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='grp',
            object_description='IK_controls',
        )
        self.ik_controls_group.set(
             cmds.createNode('transform', name=ik_controls_group_name)
        )
        cmds.parent(self.ik_controls_group.get(), self.controls_group.get())

        wrist_ctl = cmds.circle()[0]
        wrist_ctl = cmds.rename(wrist_ctl, icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='ctl',
            object_description='IK_wrist'
        ))
        icarus.dag.snap_first_to_last(wrist_ctl, ik_chain[-1])
        cmds.setAttr(wrist_ctl + '.rotate', 0, 0, 0)
        parent_group = icarus.dag.add_parent_group(wrist_ctl, 'buffer')
        cmds.parent(parent_group, self.ik_controls_group.get())

        shoulder_ctl = cmds.circle()[0]
        shoulder_ctl = cmds.rename(shoulder_ctl, icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='ctl',
            object_description='IK_shoulder'
        ))
        icarus.dag.snap_first_to_last(shoulder_ctl, ik_chain[0])
        cmds.setAttr(shoulder_ctl + '.rotate', 0, 0, 0)
        parent_group = icarus.dag.add_parent_group(shoulder_ctl, 'buffer')
        cmds.parent(parent_group, self.ik_controls_group.get())

        pole_vector_ctl = cmds.circle()[0]
        pole_vector_ctl = cmds.rename(pole_vector_ctl, icarus.metadata.name_from_metadata(
            object_base_name=self.name.get(),
            object_side=self.side.get(),
            object_type='ctl',
            object_description='IK_pole_vector'
        ))
        icarus.dag.snap_first_to_last(pole_vector_ctl, ik_chain[1])
        cmds.setAttr(pole_vector_ctl + '.rotate', 0, 0, 0)
        cmds.setAttr(pole_vector_ctl + '.translateZ', -5)
        parent_group = icarus.dag.add_parent_group(pole_vector_ctl, 'buffer')
        cmds.parent(parent_group, self.ik_controls_group.get())

        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],
            endEffector=ik_chain[-1]
        )
        cmds.poleVectorConstraint(pole_vector_ctl, ik_handle)
        cmds.parent(ik_handle, wrist_ctl)


exported_rig_modules = [Arm]

