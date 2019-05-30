import maya.cmds as cmds

from mop.core.module import RigModule
from mop.core.fields import ObjectField
import mop.dag


class Rivet(RigModule):

    geometry = ObjectField(
        displayable=True,
        editable=True,
        tooltip="The geometry on which the rivet will be attached to.\n"
        "This can be either a mesh or a nurbsSurface."
    )

    def initialize(self, *args, **kwargs):
        super(Rivet, self).initialize()
        self._add_deform_joint()

    def build(self):
        joint = self.deform_joints[0]
        ctl, parent_group = self.add_control(joint)
        mop.dag.snap_first_to_last(parent_group, joint)
        cmds.parent(parent_group, self.controls_group.get())
        mop.dag.matrix_constraint(ctl, joint)
        follicle, follicle_transform = self.add_follicle(ctl)
        mop.dag.matrix_constraint(
            follicle_transform,
            parent_group,
            maintain_offset=True
        )

    def add_follicle(self, ctl):
        if cmds.nodeType(self.geometry.get()) == 'transform':
            self.geometry.set(cmds.listRelatives(self.geometry.get(), shapes=True)[0]) 
        follicle = self.add_node('follicle')
        follicle_transform = cmds.listRelatives(follicle, parent=True)[0]
        cmds.parent(follicle_transform, self.extras_group.get())
        cmds.connectAttr(
            follicle + '.outTranslate',
            follicle_transform + '.translate'
        )
        cmds.connectAttr(
            follicle + '.outRotate',
            follicle_transform + '.rotate'
        )
        if cmds.nodeType(self.geometry.get()) == 'mesh':
            cmds.connectAttr(
                self.geometry.get() + '.outMesh',
                follicle + '.inputMesh'
            )
            closest_point_node = cmds.createNode('closestPointOnMesh')
            ctl_pos = cmds.xform(
                ctl,
                query=True,
                translation=True,
                worldSpace=True
            )
            cmds.setAttr(
                closest_point_node + '.inPosition',
                *ctl_pos
            )
            cmds.connectAttr(
                self.geometry.get() + '.outMesh',
                closest_point_node + '.inMesh'
            )
            u_value = cmds.getAttr(closest_point_node + '.result.parameterU')
            v_value = cmds.getAttr(closest_point_node + '.result.parameterV')
            cmds.delete(closest_point_node)
        elif cmds.nodeType(self.geometry.get()) == 'nurbsSurface':
            cmds.connectAttr(
                self.geometry.get() + '.local',
                follicle + '.inputSurface'
            )
            closest_point_node = cmds.createNode('closestPointOnSurface')
            ctl_pos = cmds.xform(
                ctl,
                query=True,
                translation=True,
                worldSpace=True
            )
            cmds.setAttr(
                closest_point_node + '.inPosition',
                *ctl_pos
            )
            cmds.connectAttr(
                self.geometry.get() + '.local',
                closest_point_node + '.inputSurface'
            )
            u_value = cmds.getAttr(closest_point_node + '.result.parameterU')
            v_value = cmds.getAttr(closest_point_node + '.result.parameterV')
            cmds.delete(closest_point_node)

        cmds.connectAttr(
            self.geometry.get() + '.worldMatrix[0]',
            follicle + '.inputWorldMatrix'
        )
        cmds.setAttr(follicle + '.parameterU', u_value)
        cmds.setAttr(follicle + '.parameterV', v_value)
        return [follicle, follicle_transform]

    def update_parent_joint(self):
        """Reparent the joint to the proper parent_joint if needed."""
        super(Rivet, self).update_parent_joint()
        expected_parent = self.parent_joint.get()
        joint = self.deform_joints[0]
        actual_parent = cmds.listRelatives(joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(joint, expected_parent)


exported_rig_modules = [Rivet]
