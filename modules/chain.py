import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField


class Chain(RigModule):

    chain_length = IntField(
        'chain_length',
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    def initialize(self,*args, **kwargs):
        joints = []
        parentJoint = None
        for index in range(self.chain_length.get()):
            parentJoint = cmds.createNode(
                'joint',
                name='_'.join([
                    self.name,
                    self.side,
                    'joint',
                    str(index).zfill(2),
                    'deform'
                ]),
                parent=parentJoint
            )
            joints.append(parentJoint)
        self.deform_joints.set(joints)

    def update(self):
        self._update_chain_length()

    def build(self):
        pass

    def publish(self):
        pass

    def _update_chain_length(self):
        diff = self.chain_length.get() - len(self.deform_joints.get())
        if diff > 0:
            print "adding {} joints".format(diff)
            joints = self.deform_joints.get()
            last_joint = self.deform_joints.get()[-1]
            for index in range(diff):
                new_joint = cmds.createNode(
                    'joint',
                    name='_'.join([
                        self.name,
                        self.side,
                        'joint',
                        str(index).zfill(2),
                        'deform'
                    ]),
                    parent=last_joint
                )
                cmds.setAttr(new_joint + '.translateX', 5)
                joints.append(new_joint)
                last_joint = new_joint
            self.deform_joints.set(joints)
        elif diff < 0:
            print "removing {} joints".format(diff)
            joints = self.deform_joints.get()
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]

            cmds.delete(joints_to_delete)
            self.deform_joints.set(joints_to_keep)

exported_rig_modules = [Chain]
