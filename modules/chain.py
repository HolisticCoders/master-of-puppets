import math

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectListField
import icarus.dag
import icarus.utils.shape as _shapeutils


class Chain(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        displayable=True,
        editable=True,
    )

    twist_joint_count = IntField(
        defaultValue=0,
        hasMinValue=True,
        minValue=0,
        displayable=True,
        editable=True,
    )

    deform_chain = ObjectListField()

    driving_chain = ObjectListField()

    deform_twists = ObjectListField()

    driving_twists = ObjectListField()

    def initialize(self):
        super(Chain, self).initialize()
        for i in range(self.joint_count.get()):
            new_joint = self._add_chain_deform_joint()
            if i > 0:
                cmds.setAttr(new_joint + '.translateX', 5)

    def update(self):
        super(Chain, self).update()
        self._update_chain_joint_count()
        self._update_twist_joint_count()

    def create_driving_joints(self):
        super(Chain, self).create_driving_joints()
        driving_twists = [j for j in self.driving_joints if 'twist' in j]
        self.driving_twists.set(driving_twists)
        driving_chain = [j for j in self.driving_joints if 'twist' not in j]
        self.driving_chain.set(driving_chain)

    def build(self):
        self._setup_twist()
        parent = self.controls_group.get()
        for joint in self.driving_chain.get():
            ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, parent)
            icarus.dag.matrix_constraint(ctl, joint)
            parent = ctl

    def _setup_twist(self):
        if not self.twist_joint_count.get():
            return

        for joint, next_joint in zip(self.driving_chain[:-1], self.driving_chain[1:]):
            twists = [j for j in cmds.listRelatives(joint) if 'twist' in j]
            mult_mat = cmds.createNode('multMatrix')
            decomp_mat = cmds.createNode('decomposeMatrix')
            quat_to_euler = cmds.createNode('quatToEuler')
            cmds.connectAttr(
                next_joint + '.worldMatrix[0]',
                mult_mat + '.matrixIn[0]'
            )
            cmds.connectAttr(
                joint + '.worldInverseMatrix[0]',
                mult_mat + '.matrixIn[1]'
            )
            cmds.connectAttr(
                mult_mat + '.matrixSum',
                decomp_mat + '.inputMatrix',
            )

            mat = om2.MMatrix(cmds.getAttr(mult_mat + '.matrixSum'))
            inverseMat = mat.inverse()
            cmds.setAttr(mult_mat + '.matrixIn[2]', inverseMat, type='matrix')

            cmds.connectAttr(
                decomp_mat + '.outputQuatX',
                quat_to_euler + '.inputQuatX',
            )
            cmds.connectAttr(
                decomp_mat + '.outputQuatW',
                quat_to_euler + '.inputQuatW',
            )

            factor = 1.0 / self.twist_joint_count.get()
            for i, twist in enumerate(twists):
                current_factor = (i + 1) * factor
                current_factor_reverse = 1 - current_factor
                anim_blend = cmds.createNode('animBlendNodeAdditiveRotation')
                cmds.setAttr(
                    anim_blend + '.weightA',
                    current_factor
                )
                cmds.setAttr(
                    anim_blend + '.weightB',
                    current_factor_reverse
                )
                cmds.connectAttr(
                    quat_to_euler + '.outputRotate',
                    anim_blend + '.inputA',
                )
                cmds.connectAttr(
                    anim_blend + '.output',
                    twist + '.rotate'
                )

    def _add_chain_deform_joint(self):
        deform_chain = self.deform_chain.get()
        if deform_chain:
            parent = deform_chain[-1]
        else:
            parent = self.parent_joint.get()
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'deform',
            'id': len(self.deform_chain)
        }
        joint_name = icarus.metadata.name_from_metadata(metadata)
        joint = self._add_deform_joint(name=joint_name, parent=parent)
        self.deform_chain.append(joint)
        return joint

    def _add_twist_deform_joints(self, parent, index):
        metadata = icarus.metadata.metadata_from_name(parent)
        description_data = []
        if metadata['description']:
            description_data.append(metadata['description'])
        if metadata['id'] is not None:
            description_data.append(str(metadata['id']).zfill(3))
        description_data.append('twist')
        metadata['description'] = '_'.join(description_data)
        metadata['id'] = index
        name = icarus.metadata.name_from_metadata(metadata)
        twist_joint = self._add_deform_joint(name=name, parent=parent)
        self.deform_twists.append(twist_joint)

    def _update_chain_joint_count(self):
        diff = self.joint_count.get() - len(self.deform_chain)
        if diff > 0:
            for index in range(diff):
                new_joint = self._add_chain_deform_joint()
                cmds.setAttr(new_joint + '.translateX', 5)
        elif diff < 0:
            joints = self.deform_chain.get()
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]

            for module in self.rig.rig_modules:
                if module.parent_joint.get() in joints_to_delete:
                    if joints_to_keep:
                        new_parent_joint = joints_to_keep[-1]
                    else:
                        new_parent_joint = self.parent_joint.get()
                    module.parent_joint.set(new_parent_joint)
                    module.update()

            cmds.delete(joints_to_delete)

    def _update_twist_joint_count(self):
        exptected_twist_count = self.twist_joint_count.get()
        for chain_joint in self.deform_chain[:-1]:
            twists = [t for t in cmds.listRelatives(chain_joint) if 'twist' in t]
            current_twist_count = len(twists)
            diff = exptected_twist_count - current_twist_count
            if diff > 0:
                for i in xrange(diff):
                    self._add_twist_deform_joints(
                        parent=chain_joint,
                        index=current_twist_count + i
                    )
            elif diff < 0:
                twists_to_del = twists[diff:]
                cmds.delete(twists_to_del)

    def update_parent_joint(self):
        """Reparent the first joint to the proper parent_joint if needed."""
        super(Chain, self).update_parent_joint()
        expected_parent = self.parent_joint.get()
        first_joint = self.deform_joints[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)


exported_rig_modules = [Chain]
