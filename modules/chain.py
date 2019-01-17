import math

import maya.cmds as cmds

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

        i = 0
        for joint, next_joint in zip(self.driving_chain[:-1], self.driving_chain[1:]):
            joint_metadata = icarus.metadata.metadata_from_name(joint)
            joint_metadata['role'] = 'ribbonDeform'
            joint_metadata['description'] = 'start'
            joint_metadata['id'] = i
            surface_skin_jnt1 = icarus.metadata.name_from_metadata(joint_metadata)
            dupli = cmds.duplicate(joint, parentOnly=True)[0]
            cmds.rename(dupli, surface_skin_jnt1)
            cmds.parent(surface_skin_jnt1, self.extras_group.get())
            buffer_grp = icarus.dag.add_parent_group(surface_skin_jnt1, 'buffer')
            icarus.dag.matrix_constraint(joint, buffer_grp)
            cmds.aimConstraint(
                next_joint,
                surface_skin_jnt1,
                worldUpType='objectrotation',
                worldUpObject=joint
            )

            next_joint_metadata = icarus.metadata.metadata_from_name(next_joint)
            next_joint_metadata['role'] = 'ribbonDeform'
            next_joint_metadata['description'] = 'end'
            next_joint_metadata['id'] = joint_metadata['id']
            next_joint_metadata['id'] = i
            surface_skin_jnt2 = icarus.metadata.name_from_metadata(next_joint_metadata)
            dupli = cmds.duplicate(next_joint, parentOnly=True)[0]
            cmds.rename(dupli, surface_skin_jnt2)
            cmds.parent(surface_skin_jnt2, self.extras_group.get())
            buffer_grp = icarus.dag.add_parent_group(surface_skin_jnt2, 'buffer')
            icarus.dag.matrix_constraint(next_joint, buffer_grp)
            cmds.aimConstraint(
                joint,
                surface_skin_jnt2,
                worldUpType='objectrotation',
                worldUpObject=next_joint
            )

            i += 1

            surface = self._create_surface(surface_skin_jnt1, surface_skin_jnt2)
            twists = [j for j in cmds.listRelatives(joint) if 'twist' in j]
            for twist in twists:
                metadata = icarus.metadata.metadata_from_name(twist)
                metadata['role'] = 'follicle'
                follicle_name = icarus.metadata.name_from_metadata(metadata)
                follicle = _shapeutils.add_follicle(surface, twist)
                follicle = cmds.rename(
                    cmds.listRelatives(follicle, parent=True)[0],
                    follicle_name
                )
                cmds.parent(follicle, self.extras_group.get())
                icarus.dag.matrix_constraint(follicle, twist, maintain_offset=True)

    def _create_surface(self, joint1, joint2):
        joint_pos = cmds.xform(
            joint1,
            query=True,
            translation=True,
            ws=True
        )
        next_joint_pos = cmds.xform(
            joint2,
            query=True,
            translation=True,
            ws=True
        )

        dist = math.sqrt(
            (joint_pos[0] - next_joint_pos[0]) ** 2 +
            (joint_pos[1] - next_joint_pos[1]) ** 2 +
            (joint_pos[2] - next_joint_pos[2]) ** 2
        )

        mid_point = []
        mid_point.append((joint_pos[0] + next_joint_pos[0]) / 2)
        mid_point.append((joint_pos[1] + next_joint_pos[1]) / 2)
        mid_point.append((joint_pos[2] + next_joint_pos[2]) / 2)

        metadata = icarus.metadata.metadata_from_name(joint1)
        metadata['role'] = 'ribbon'
        surface_name = icarus.metadata.name_from_metadata(metadata)
        surface, make_nurb_surface = cmds.nurbsPlane(name=surface_name)
        cmds.setAttr(surface + '.rotateZ', 90)
        cmds.makeIdentity(surface, apply=True)
        cmds.setAttr(make_nurb_surface + '.lengthRatio', dist)
        cmds.setAttr(surface + '.translate', *mid_point)
        aim = cmds.aimConstraint(
            joint2,
            surface,
            aimVector=[1, 0, 0],
            worldUpType='objectrotation',
            worldUpObject=joint2
        )
        cmds.delete(aim)
        cmds.delete(surface, constructionHistory=True)
        cmds.parent(surface, self.extras_group.get())
        cmds.makeIdentity(surface, apply=True)

        skin = cmds.skinCluster(
            [joint1, joint2],
            surface,
            toSelectedBones=True,
        )[0]
        cmds.setAttr(skin + '.skinningMethod', 1)
        cmds.skinPercent(
            skin,
            surface + '.cv[0:3][3]',
            transformValue=[(joint1, 1), (joint2, 0)]
        )
        cmds.skinPercent(
            skin,
            surface + '.cv[0:3][2]',
            transformValue=[(joint1, 0.75), (joint2, 0.25)]
        )
        cmds.skinPercent(
            skin,
            surface + '.cv[0:3][1]',
            transformValue=[(joint1, 0.25), (joint2, 0.75)]
        )
        cmds.skinPercent(
            skin,
            surface + '.cv[0:3][0]',
            transformValue=[(joint1, 0), (joint2, 1)]
        )
        return surface

    def publish(self):
        pass

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
