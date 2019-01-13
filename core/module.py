import logging

import maya.cmds as cmds
from icarus.core.icarusNode import IcarusNode
from icarus.core.fields import ObjectField, StringField, ObjectListField
from icarus.modules import all_rig_modules
import icarus.metadata
import icarus.dag
import icarus.attributes

logger = logging.getLogger(__name__)


class RigModule(IcarusNode):

    name = StringField(
        displayable=True,
        editable=True,
        gui_order=-2  # make sure it's always on top
    )
    side = StringField(
        displayable=True,
        editable=True,
        gui_order=-2  # make sure it's always on top
    )

    # Joint of the rig skeleton under which the deform joints will be parented.
    parent_joint = ObjectField(
            displayable=True,
            editable=True,
            gui_order=-1  # always on top but under the name and side
    )

    module_type = StringField()

    # group holding all this module's controls
    controls_group = ObjectField()

    # group holding all this module's driving joints
    driving_group = ObjectField()

    # group holding all this module's driving joints
    extras_group = ObjectField()

    # list of all of this module's deform joints
    deform_joints = ObjectListField()

    def __init__(self, name, side='M', parent_joint=None, rig=None):
        if cmds.objExists(name):
            self.node_name = name
        else:
            self.node_name = icarus.metadata.name_from_metadata(name, side, 'mod')
        super(RigModule, self).__init__(self.node_name)

        self.rig = rig
        if not self.is_initialized.get():
            self.name.set(name)
            self.side.set(side)
            self.module_type.set(self.__class__.__name__)

            parent = cmds.listRelatives(self.node_name, parent=True)
            if not parent or parent[0] != rig.modules_group.get():
                cmds.parent(self.node_name, rig.modules_group.get())

            if parent_joint:
                self.parent_joint.set(parent_joint)
                icarus.dag.matrix_constraint(parent_joint, self.node_name)

            self.initialize()
            self.is_initialized.set(True)

    @property
    def driving_joints(self):
        joints = cmds.listRelatives(self.driving_group.get(), type='joint', allDescendents=True)
        if joints is None:
            return []
        else:
            # listRelative returns a reversed list (children first)
            return list(reversed(joints))

    @property
    def parent_module(self):
        parent_joint = self.parent_joint.get()
        if parent_joint:
            parent_module = '_'.join([
                parent_joint.split('_')[0],
                parent_joint.split('_')[1],
                'mod'
            ])
            module_type = cmds.getAttr(parent_module + '.module_type')
            parent_module = all_rig_modules[module_type](parent_module, rig=self.rig)
            return parent_module

    def initialize(self):
        """Creation of all the needed placement nodes.

        This must at least include all the module's driving joints.

        Will be called automatically when creating the module.
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def update(self):
        """Update the maya scene based on the module's fields

        This should ONLY be called in placement mode.
        """
        if self.is_built.get():
            return

        scene_metadata = icarus.metadata.metadata_from_name(self.node_name)
        name_changed = self.name.get() != scene_metadata['base_name']
        side_changed = self.side.get() != scene_metadata['side']

        if name_changed or side_changed:
            # rename the module node
            new_name = self._update_node_name(self.node_name)
            self.node_name = new_name

            # rename the deform joints
            for node in self.deform_joints.get():
                self._update_node_name(node)

            # rename the persistent attributes
            persistent_attrs = cmds.listAttr(
                self.node_name,
                category='persistent_attribute_backup'
            )
            if persistent_attrs:
                for attr in persistent_attrs:
                    old_node, attr_name = attr.split('__')

                    metadata = icarus.metadata.metadata_from_name(old_node)
                    metadata['base_name'] = self.name.get()
                    metadata['side'] = self.side.get()
                    new_node = icarus.metadata.name_from_metadata(
                        metadata['base_name'],
                        metadata['side'],
                        metadata['type'],
                        object_id = metadata.get('id', None),
                        object_description = metadata.get('description', None),
                    )
                    logger.debug("Renaming persistent attribute from {} to {}".format(
                        self.node_name + '.' + attr,
                        self.node_name + '.' + new_node + '__' + attr_name
                    ))
                    cmds.renameAttr(
                        self.node_name + '.' + attr,
                        new_node + '__' + attr_name
                    )

    def _update_node_name(self, node):
        metadata = icarus.metadata.metadata_from_name(node)
        metadata['base_name'] = self.name.get()
        metadata['side'] = self.side.get()
        new_name = icarus.metadata.name_from_metadata(
            metadata['base_name'],
            metadata['side'],
            metadata['type'],
            object_id = metadata.get('id', None),
            object_description = metadata.get('description', None),
        )
        cmds.rename(node, new_name)

        # propagate the new name in all the object and object list fields
        for module in self.rig.rig_modules:
            for field in module.fields:
                if field.__class__.__name__ == 'ObjectField':
                    if field.__get__(module).get() == node:
                        field.__get__(module).set(new_name)
                if field.__class__.__name__ == 'ObjectListField':
                    objects = field.__get__(module).get()
                    for i, item in enumerate(objects):
                        if item == node:
                            objects[i] = new_name
                    field.__get__(module).set(objects)
        return new_name

    def _build(self):
        """Setup some stuff before actually building the module.

        Call this method instead of `build()` to make sure
        everything is setup properly
        """
        if self.is_built.get():
            raise RuntimeError(
                "Module {} is already built!".format(self.node_name)
            )

        controls_group_name = icarus.metadata.name_from_metadata(
            self.name.get(),
            self.side.get(),
            'grp',
            object_description='controls'
        )
        self.controls_group.set(cmds.createNode(
            'transform',
            name=controls_group_name,
            parent=self.node_name
        ))

        driving_group_name = icarus.metadata.name_from_metadata(
            self.name.get(),
            self.side.get(),
            'grp',
            object_description='driving'
        )
        self.driving_group.set(cmds.createNode(
            'transform',
            name=driving_group_name,
            parent=self.node_name
        ))
        cmds.setAttr(self.driving_group.get() + '.visibility', False)

        extras_group_name = icarus.metadata.name_from_metadata(
            self.name.get(),
            self.side.get(),
            'grp',
            object_description='extras'
        )
        self.extras_group.set(cmds.createNode(
            'transform',
            name=extras_group_name,
            parent=self.node_name
        ))
        cmds.setAttr(self.extras_group.get() + '.visibility', False)

        self.create_driving_joints()
        self.build()
        self.is_built.set(True)

    def build(self):
        """Actual rigging of the module.

        The end result should _always_ drive your module's driving joints
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def publish(self):
        """Clean the rig for the animation.

        Nothing in there should change how the rig works.
        It's meant to hide some stuff that the rigger would need after the build
        maybe lock some attributes, set some default values, etc.
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def _add_deform_joint(self, name=None, parent=None):
        """Creates a new deform joint for this module.

        Args:
            name (str): name of the joint, in case you don't want the default one.
            parent (str): node under which the new joint will be parented
        """
        deform_joints = self.deform_joints.get()

        if deform_joints is None:
            deform_joints = []

        object_id=len(deform_joints)
        if name is not None:
            new_joint = name
        else:
            new_joint = icarus.metadata.name_from_metadata(
                self.name.get(),
                self.side.get(),
                'deform',
                object_id=object_id
            )
        cmds.createNode('joint', name=new_joint)

        if not parent:
            parent = self.parent_joint.get()
        if not parent:
            parent = self.rig.skeleton_group.get()

        cmds.parent(new_joint, parent)
        
        for transform in ['translate', 'rotate', 'scale', 'jointOrient']:
            if transform == 'scale':
                value = 1
            else:
                value = 0
            for axis in 'XYZ':
                attr = transform + axis
                cmds.setAttr(new_joint + '.' + attr, value)

        deform_joints.append(new_joint)
        self.deform_joints.set(
            deform_joints
        )
        return new_joint

    def create_driving_joints(self):
        deform_joints = self.deform_joints.get()
        duplicate = cmds.duplicate(
            deform_joints,
            parentOnly=True,
            renameChildren=True
        )
        driving_joints = []
        for j in duplicate:
            driving_joints.append(cmds.rename(
                j,
                j.replace('deform1', 'driving')
            ))

        for deform, driving in zip(deform_joints, driving_joints):
            # Find out who the father is.
            deform_parent = cmds.listRelatives(deform, parent=True)
            if deform_parent:
                deform_parent = deform_parent[0]
            if (
                deform_parent == self.parent_joint.get() or
                deform_parent == self.rig.skeleton_group.get()
            ):
                parent = self.driving_group.get()
            else:
                # deform_parent should be one of the module's deform joints.
                parent = deform_parent.replace('deform', 'driving')
            # Reunite the family.
            if parent != cmds.listRelatives(driving, parent=True)[0]:
                cmds.parent(driving, parent)

            icarus.dag.matrix_constraint(driving, deform)

