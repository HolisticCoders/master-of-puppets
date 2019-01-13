import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.modules.abstract.chainswitcher import ChainSwitcher
from icarus.core.fields import IntField, ObjectListField, ObjectField
import icarus.dag
import icarus.metadata


class Arm(ChainSwitcher):

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

    # list containing the FK joints in the same order as the hierarchy
    fk_chain = ObjectListField()

    # list containing the IK joints in the same order as the hierarchy
    ik_chain = ObjectListField()

    # list containing the FK controls in the same order as the hierarchy.
    fk_controls = ObjectListField()

    # list containing the IK controls.
    ik_controls = ObjectListField()

    # group containing all the FK controls
    fk_controls_group = ObjectField()

    # group containing all the IK controls
    ik_controls_group = ObjectField()

    ik_handle = ObjectField()
    effector = ObjectField()

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

    def initialize(self, *args, **kwargs):
        self.joint_count.set(3)
        super(Arm, self).initialize()

        self.switch_long_name.set('FK_IK_Switch')
        self.switch_nice_name.set('FK/IK')
        self.switch_enum_name.set('FK:IK:')

        name_list = ['shoulder', 'elbow', 'wrist']

        deform_joints = []
        for deform, name in zip(self.deform_joints.get(), name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name
            }
            deform_name = icarus.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)
            deform_joints.append(deform)
        self.deform_joints.set(deform_joints)

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
            all_deform = self.deform_joints.get()
            joints_to_remove = self.upper_twist_deform_joints[joint_diff:]
            self.deform_joints.set(
                [j for j in all_deform if j not in joints_to_remove]
            )
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
            all_deform = self.deform_joints.get()
            joints_to_remove = self.lower_twist_deform_joints[joint_diff:]
            self.deform_joints.set(
                [j for j in all_deform if j not in joints_to_remove]
            )
            cmds.delete(joints_to_remove)

    def build(self):
        super(Arm, self).build()
        self._setup_fk()
        self._setup_ik()
        self._setup_switch_vis()
        self._setup_lower_twist()

    def _create_chains(self):
        """Rename the FK and IK joints."""
        super(Arm, self)._create_chains()

        return
        fk_chain = self.chain_a.get()
        for i, fk in enumerate(fk_chain):
            metadata = icarus.metadata.metadata_from_name(fk)
            metadata['role'] = 'fk'
            fk_chain[i] = cmds.rename(
                fk,
                icarus.metadata.name_from_metadata(metadata)
            )
        self.chain_a.set(fk_chain)

        ik_chain = self.chain_b.get()
        for i, ik in enumerate(ik_chain):
            metadata = icarus.metadata.metadata_from_name(ik)
            metadata['role'] = 'ik'
            ik_chain[i] = cmds.rename(
                ik,
                icarus.metadata.name_from_metadata(metadata)
            )
        self.chain_b.set(ik_chain)

    def _setup_switch_vis(self):
        settings_ctl = self.settings_ctl.get()
        cmds.connectAttr(
            self.reverse_switch.get() + '.outputX',
            self.fk_controls_group.get() + '.visibility'
        )
        cmds.connectAttr(
            settings_ctl + '.' + self.switch_long_name.get(),
            self.ik_controls_group.get() + '.visibility'
        )

    def _setup_fk(self):
        fk_controls = self.chain_a.get()
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'grp',
            'description': 'FK_controls',
        }
        fk_controls_group_name = icarus.metadata.name_from_metadata(metadata)
        self.fk_controls_group.set(
             cmds.createNode('transform', name=fk_controls_group_name)
        )
        cmds.parent(self.fk_controls_group.get(), self.controls_group.get())
        icarus.dag.reset_node(self.fk_controls_group.get())

        if fk_controls is None:
            fk_controls = []

        parent = self.fk_controls_group.get()
        names = ['shoulder', 'elbow', 'wrist']
        for i, fk in enumerate(self.chain_a.get()):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'ctl',
                'description': 'FK_' + names[i],
            }
            ctl_name = icarus.metadata.name_from_metadata(metadata)
            ctl, parent_group = self.add_control(fk, ctl_name)
            cmds.parent(parent_group, parent)
            icarus.dag.matrix_constraint(ctl, fk)
            parent = ctl

    def _setup_ik(self):
        ik_chain = self.chain_b.get()
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'grp',
            'description': 'IK_controls',
        }
        ik_controls_group_name = icarus.metadata.name_from_metadata(metadata)
        self.ik_controls_group.set(
             cmds.createNode('transform', name=ik_controls_group_name)
        )
        cmds.parent(self.ik_controls_group.get(), self.controls_group.get())
        icarus.dag.reset_node(self.ik_controls_group.get())

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': 'IK_wrist',
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        wrist_ctl, parent_group = self.add_control(ik_chain[-1], ctl_name, 'cube')
        cmds.setAttr(parent_group + '.rotate', 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        icarus.dag.matrix_constraint(
            wrist_ctl,
            ik_chain[-1],
            translate=False,
            rotate=True,
            scale=False,
            maintain_offset=True
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': 'IK_shoulder',
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        shoulder_ctl, parent_group = self.add_control(ik_chain[0], ctl_name, 'cube')
        cmds.setAttr(parent_group + '.rotate', 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        icarus.dag.matrix_constraint(shoulder_ctl, ik_chain[0], maintain_offset=True)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': 'IK_pole_vector',
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        pole_vector_ctl, parent_group = self.add_control(ik_chain[-1], ctl_name, 'sphere')
        self._place_pole_vector(parent_group)
        cmds.xform(parent_group, rotation=[0, 0, 0], worldSpace=True)
        cmds.parent(parent_group, self.ik_controls_group.get())

        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],
            endEffector=ik_chain[2]
        )
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(pole_vector_ctl, ik_handle)
        icarus.dag.matrix_constraint(wrist_ctl, ik_handle, maintain_offset=True)

    def _place_pole_vector(self, ctl):
        ik_chain = self.chain_b.get()
        shoulder_pos = cmds.xform(
            ik_chain[0],
            query=True,
            worldSpace=True,
            translation=True
        )
        elbow_pos = cmds.xform(
            ik_chain[1],
            query=True,
            worldSpace=True,
            translation=True
        )
        wrist_pos = cmds.xform(
            ik_chain[2],
            query=True,
            worldSpace=True,
            translation=True
        )

        shoulder_vec = om2.MVector(*shoulder_pos)
        elbow_vec = om2.MVector(*elbow_pos)
        wrist_vec = om2.MVector(*wrist_pos)

        shoulder_wrist_vec = wrist_vec - shoulder_vec
        shouler_elbow_vec = elbow_vec - shoulder_vec

        dot_product = shouler_elbow_vec * shoulder_wrist_vec
        proj = float(dot_product) / float(shoulder_wrist_vec.length())
        shoulder_wrist_vec_norm = shoulder_wrist_vec.normal()
        projection_vec = shoulder_wrist_vec_norm * proj

        pole_vec = shouler_elbow_vec - projection_vec
        pole_vec *= 10
        pv_control_vec = pole_vec + elbow_vec
        cmds.xform(ctl, worldSpace=1, translation=pv_control_vec)

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

    def update_parent_joint(self):
        """Reparent the first joint to the proper parent_joint if needed."""
        expected_parent = self.parent_joint.get()
        first_joint = self.deform_joints.get()[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)


exported_rig_modules = [Arm]

