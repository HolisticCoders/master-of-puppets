import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import ObjectField
import icarus.dag

class Rivet(RigModule):

    surface = ObjectField()

    def initialize(self, *args, **kwargs):
        self._add_deform_joint()

    def build(self):
        joint = self.driving_joints[0]
        ctl, parent_group = self.add_control(joint)
        icarus.dag.snap_first_to_last(parent_group, joint)
        cmds.parent(ctl, self.controls_group.get())
        icarus.dag.matrix_constraint(ctl, joint)

        if cmds.nodeType(self.surface.get()) == 'transform':
            self.surface.set(cmds.listRelatives(self.surface.get(), shapes=True)[0]) 
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
        if cmds.nodeType(self.surface.get()) == 'mesh':
            cmds.connectAttr(
                self.surface.get() + '.outMesh',
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
                self.surface.get() + '.outMesh',
                closest_point_node + '.inMesh'
            )
            u = cmds.getAttr(closest_point_node + '.result.parameterU')
            v = cmds.getAttr(closest_point_node + '.result.parameterV')
        cmds.connectAttr(
            self.surface.get() + '.worldMatrix[0]',
            follicle + '.inputWorldMatrix'
        )
        cmds.setAttr(follicle + '.parameterU', u)
        cmds.setAttr(follicle + '.parameterV', v)
        icarus.dag.matrix_constraint(
            follicle_transform,
            parent_group,
            maintain_offset=True
        )


exported_rig_modules = [Rivet]
