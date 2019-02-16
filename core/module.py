import json
import logging

import maya.cmds as cmds

from icarus.core.fields import (
    EnumField,
    ObjectField,
    StringField,
    ObjectListField,
)
from icarus.core.icarusNode import IcarusNode
from icarus.modules import all_rig_modules
import icarus.attributes
import icarus.dag
import icarus.metadata

from shapeshifter import shapeshifter


logger = logging.getLogger(__name__)


class RigModule(IcarusNode):

    name = StringField(
        displayable=True,
        editable=True,
        gui_order=-2,  # make sure it's always on top
        unique=True,
    )
    side = EnumField(
        choices=['M', 'L', 'R'],
        displayable=True,
        editable=True,
        gui_order=-2  # make sure it's always on top
    )

    owned_nodes = ObjectListField()

    # Joint of the rig skeleton under which the deform joints will be parented.
    parent_joint = ObjectField()

    module_type = StringField()

    # group holding all this module's placement nodes
    placement_group = ObjectField()

    # group holding all this module's controls
    controls_group = ObjectField()

    # group holding all this module's driving joints
    driving_group = ObjectField()

    # group holding all this module's driving joints
    extras_group = ObjectField()

    # list of all of this module's deform joints
    deform_joints = ObjectListField()

    # list of all of this module's placement_locators
    placement_locators = ObjectListField()

    controllers = ObjectListField()

    def __init__(self, name, side='M', parent_joint=None, rig=None):
        if cmds.objExists(name):
            self.node_name = name
        else:
            metadata = {
                'base_name': name,
                'side': side,
                'role': 'mod',
            }
            self.node_name = icarus.metadata.name_from_metadata(metadata)
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
            self.update()
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
            parent_module = cmds.listConnections(parent_joint + '.module', source=True)[0]
            module_type = cmds.getAttr(parent_module + '.module_type')
            parent_module = all_rig_modules[module_type](parent_module, rig=self.rig)
            return parent_module

    def initialize(self):
        """Creation of all the needed placement nodes.

        This must at least include all the module's driving joints.

        Will be called automatically when creating the module.
        You need to overwrite this method in your subclasses.
        """
        self.placement_group.set(
            self.add_node(
                'transform',
                'grp',
                description='placement',
                parent=self.node_name
            )
        )
        self.controls_group.set(
            self.add_node(
                'transform',
                role='grp',
                description='controls',
                parent = self.node_name
            )
        )

        self.driving_group.set(
            self.add_node(
                'transform',
                role='grp',
                description='driving',
                parent = self.node_name
            )
        )
        cmds.setAttr(self.driving_group.get() + '.visibility', False)

        self.extras_group.set(
            self.add_node(
                'transform',
                role='grp',
                description='extras',
                parent = self.node_name
            )
        )
        cmds.setAttr(self.extras_group.get() + '.visibility', False)

    def update(self):
        """Update the maya scene based on the module's fields

        This should ONLY be called in placement mode.
        """
        if self.is_built.get():
            return

        self.update_parent_joint()

        scene_metadata = icarus.metadata.metadata_from_name(self.node_name)
        name_changed = self.name.get() != scene_metadata['base_name']
        side_changed = self.side.get() != scene_metadata['side']

        if name_changed or side_changed:
            # rename the module node
            new_name = self._update_node_name(self.node_name)
            self.node_name = new_name

            # rename the owned nodes
            for node in self.owned_nodes.get():
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
                    new_node = icarus.metadata.name_from_metadata(metadata)
                    logger.debug("Renaming persistent attribute from {} to {}".format(
                        self.node_name + '.' + attr,
                        self.node_name + '.' + new_node + '__' + attr_name
                    ))
                    cmds.renameAttr(
                        self.node_name + '.' + attr,
                        new_node + '__' + attr_name
                    )

    def update_parent_joint(self):
        # delete the old constraint
        old_constraint_nodes = []
        first_node = cmds.listConnections(
            self.node_name + '.translate',
            source=True
        )[0]
        second_node = cmds.listConnections(
            first_node + '.inputMatrix',
            source=True
        )[0]
        old_constraint_nodes.append(first_node)
        old_constraint_nodes.append(second_node)
        cmds.delete(old_constraint_nodes)
        icarus.dag.matrix_constraint(self.parent_joint.get(), self.node_name)

    def _update_node_name(self, node):
        metadata = icarus.metadata.metadata_from_name(node)
        metadata['base_name'] = self.name.get()
        metadata['side'] = self.side.get()
        new_name = icarus.metadata.name_from_metadata(metadata)
        cmds.rename(node, new_name)
        return new_name

    def _build(self):
        """Setup some stuff before actually building the module.

        Call this method instead of `build()` to make sure
        everything is setup properly
        """
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
        """
        cmds.setAttr(self.extras_group.get() + '.visibility', False)

    def add_node(
        self,
        node_type,
        role=None,
        object_id=None,
        description=None,
        *args,
        **kwargs
    ):
        """Add a node to this `IcarusNode`.

        args and kwargs will directly be passed to ``cmds.createNode()``

        :param node_type: type of the node to create, will be passed to ``cmds.createNode()``.
        :type node_type: str
        :param role: role of the node (this will be the last part of its name).
        :type role: str
        :param object_id: optional index for the node.
        :type object_id: int
        :param description: optional description for the node
        :type object_id: str
        """
        if not role:
            role = node_type
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': role,
            'description': description,
            'id': object_id
        }
        name = icarus.metadata.name_from_metadata(metadata)
        if cmds.objExists(name):
            raise ValueError("A node with the name `{}` already exists".format(name))
        node = cmds.createNode(node_type, name=name, *args, **kwargs)
        cmds.addAttr(
            node,
            longName='module',
            attributeType = 'message'
        )
        cmds.connectAttr(
            self.node_name + '.message',
            node + '.module'
        )
        self.owned_nodes.append(node)
        return node

    def _add_deform_joint(
        self,
        parent=None,
        object_id=None,
        description=None,
    ):
        """Creates a new deform joint for this module.

        Args:
            parent (str): node under which the new joint will be parented
        """
        if object_id is None:
            object_id = len(self.deform_joints)

        new_joint = self.add_node(
            'joint',
            role='deform',
            object_id=object_id,
            description=description
        )

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

        self.deform_joints.append(new_joint)
        return new_joint

    def _add_placement_locator(self, name=None, parent=None):
        """Creates a new placement locator for this module.

        A placement locator is a way to get placement data without polluting
        the deform skeleton.
        """
        object_id = len(self.placement_locators)
        if name is None:
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'placement',
                'id': object_id
            }
            name = icarus.metadata.name_from_metadata(metadata)
        locator = cmds.spaceLocator(name=name)[0]
        if not parent:
            parent = self.placement_group.get()
        cmds.parent(locator, parent)

        for transform in ['translate', 'rotate', 'scale']:
            if transform == 'scale':
                value = 1
            else:
                value = 0
            for axis in 'XYZ':
                attr = transform + axis
                cmds.setAttr(locator + '.' + attr, value)

        self.placement_locators.append(locator)
        return locator

    def create_driving_joints(self):
        deform_joints = self.deform_joints.get()
        duplicate = cmds.duplicate(
            deform_joints,
            parentOnly=True,
            renameChildren=True
        )
        driving_joints = []
        for joint in duplicate:
            metadata = icarus.metadata.metadata_from_name(joint)
            metadata['role'] = 'driving'
            new_name = icarus.metadata.name_from_metadata(metadata)
            joint = cmds.rename(joint, new_name)
            driving_joints.append(joint)

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

    def add_control(self, dag_node, ctl_name=None, shape_type='circle'):
        if not ctl_name:
            metadata = icarus.metadata.metadata_from_name(dag_node)
            metadata['role'] = 'ctl'
            ctl_name = icarus.metadata.name_from_metadata(metadata)
        ctl = shapeshifter.create_controller_from_name(shape_type)
        ctl = cmds.rename(ctl, ctl_name)

        # get the existing shape data if it exists
        icarus.attributes.create_persistent_attribute(
            ctl,
            self.node_name,
            longName='shape_data',
            dataType='string'
        )
        ctl_data = cmds.getAttr(ctl + '.shape_data')
        if ctl_data:
            ctl_data = json.loads(ctl_data)
            shapeshifter.change_controller_shape(ctl, ctl_data)

        icarus.attributes.create_persistent_attribute(
            ctl,
            self.node_name,
            longName='attributes_state',
            dataType='string'
        )

        icarus.attributes.create_persistent_attribute(
            ctl,
            self.node_name,
            longName='parent_space_data',
            dataType='string',
        )

        # We cannot set a default value on strings, so set the persistent
        # attribute after its creation.
        # It is mandatory to set a default value here, without a value
        # the attribute returns `None` when rebuilt and this crashes
        # the `setAttr` command.
        if not cmds.getAttr(ctl + '.parent_space_data'):
            cmds.setAttr(ctl + '.parent_space_data', '{}', type='string')

        icarus.dag.snap_first_to_last(ctl, dag_node)
        parent_group = icarus.dag.add_parent_group(ctl, 'buffer')
        self.controllers.append(ctl)
        return ctl, parent_group
