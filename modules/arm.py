import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.modules.fkikrpchain import FkIkRPChain
from icarus.core.fields import IntField, ObjectListField, ObjectField
import icarus.dag
import icarus.metadata


class Arm(FkIkRPChain):

    upper_twist_joint_count = IntField(
        defaultValue=0,
        hasMinValue=True,
        minValue=0,
    )

    lower_twist_joint_count = IntField(
        defaultValue=0,
        hasMinValue=True,
        minValue=0,
    )

    # bunch of properties that filter the driving and
    # deform joints to get either the twist or arm joints
    @property
    def arm_driving_joints(self):
        driving_joints = self.driving_joints
        return [j for j in driving_joints if 'twist' not in j]

    @property
    def arm_deform_joints(self):
        deform_joints = self.deform_joints.get()
        return [j for j in deform_joints if 'twist' not in j]

    @property
    def upper_twist_driving_joints(self):
        driving_joints = self.driving_joints
        return [j for j in driving_joints if 'twist_upper' in j]

    @property
    def upper_twist_deform_joints(self):
        deform_joints = self.deform_joints.get()
        return [j for j in deform_joints if 'twist_upper' in j]

    @property
    def lower_twist_driving_joints(self):
        driving_joints = self.driving_joints
        return [j for j in driving_joints if 'twist_lower' in j]

    @property
    def lower_twist_deform_joints(self):
        deform_joints = self.deform_joints.get()
        return [j for j in deform_joints if 'twist_lower' in j]

    def initialize(self):
        super(Arm, self).initialize()
        self.ik_start_description.set('IK_wrist')
        self.ik_end_description.set('IK_shoulder')

        name_list = ['shoulder', 'elbow', 'wrist']

        for deform, name in zip(self.deform_joints.get(), name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name
            }
            deform_name = icarus.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)

        for i in xrange(self.upper_twist_joint_count.get()):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': 'twist_upper',
                'id': i
            }
            name = icarus.metadata.name_from_metadata(metadata)
            self._add_twist_joint(
                name=name,
                parent=self.deform_joints.get()[0]
            )

        for i in xrange(self.lower_twist_joint_count.get()):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': 'twist_lower',
                'id': i
            }
            name = icarus.metadata.name_from_metadata(metadata)
            self._add_twist_joint(
                name=name,
                parent=self.deform_joints.get()[1]
            )

    def _add_twist_joint(self, name, parent):
        return super(Arm, self)._add_deform_joint(name=name, parent=parent)

    def update(self):
        super(Arm, self).update()
        self._update_upper_twists()
        self._update_lower_twists()

    def _update_upper_twists(self):
        current_upper_twists = len(self.upper_twist_deform_joints)
        target_upper_twists = self.upper_twist_joint_count.get()
        joint_diff = target_upper_twists - current_upper_twists
        if joint_diff > 0:
            # add twist joints
            for i in xrange(current_upper_twists, target_upper_twists):

                metadata = {
                    'base_name': self.name.get(),
                    'side': self.side.get(),
                    'role': 'deform',
                    'description': 'twist_upper',
                    'id': i
                }
                name = icarus.metadata.name_from_metadata(metadata)
                self._add_twist_joint(
                    name=name,
                    parent=self.deform_joints.get()[0]
                )
        elif joint_diff < 0:
            joints_to_remove = self.upper_twist_deform_joints[joint_diff:]
            cmds.delete(joints_to_remove)

    def _update_lower_twists(self):
        current_lower_twists = len(self.lower_twist_deform_joints)
        target_lower_twists = self.lower_twist_joint_count.get()
        joint_diff = target_lower_twists - current_lower_twists
        if joint_diff > 0:
            # add twist joints
            for i in xrange(current_lower_twists, target_lower_twists):
                metadata = {
                    'base_name': self.name.get(),
                    'side': self.side.get(),
                    'role': 'deform',
                    'description': 'twist_lower',
                    'id': i
                }
                name = icarus.metadata.name_from_metadata(metadata)
                self._add_twist_joint(
                    name=name,
                    parent=self.deform_joints.get()[1]
                )
        elif joint_diff < 0:
            joints_to_remove = self.lower_twist_deform_joints[joint_diff:]
            cmds.delete(joints_to_remove)

    def build(self):
        super(Arm, self).build()
        self._setup_lower_twist()

    def _setup_lower_twist(self):
        wrist_driving = self.arm_driving_joints[-1]
        twists = self.lower_twist_driving_joints
        twists_count = len(twists)
        multiplier = 1.0 / (twists_count + 1)
        for i, twist in enumerate(twists):
            current_mult = 1 - (i + 1) * multiplier
            mult_double_linear = cmds.createNode('multDoubleLinear')
            cmds.connectAttr(
                wrist_driving + '.rotateX',
                mult_double_linear + '.input1'
            )
            cmds.setAttr(mult_double_linear + '.input2', current_mult)
            cmds.connectAttr(
                mult_double_linear + '.output',
                twist + '.rotateX'
            )


exported_rig_modules = [Arm]
