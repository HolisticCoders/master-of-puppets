import json
import logging

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from mop.core.fields import EnumField, ObjectField, StringField, ObjectListField
from mop.core.mopNode import MopNode
from mop.modules import all_rig_modules
from mop.utils.dg import find_mirror_node
import mop.attributes
import mop.dag
import mop.utils.dg as _dgutils
import mop.metadata
import mop.config

from shapeshifter import shapeshifter


logger = logging.getLogger(__name__)


class RigModule(MopNode):

    # The base name of the module
    # for example: the name of the module "root_M_mod" is "root"
    name = StringField(
        displayable=True,
        editable=True,
        gui_order=-2,  # make sure it's always on top
        unique=True,
        tooltip="Base name of the module",
    )

    # The side of this module.
    side = EnumField(
        choices=['M', 'L', 'R'],
        displayable=True,
        editable=True,
        gui_order=-2,  # make sure it's always on top
        tooltip="Side of the module:\n" "M: Middle\n" "L: Left\n" "R: Right",
    )

    # The mirror type of this module.
    # The two modes mimic maya's mirror modes.
    mirror_type = EnumField(
        choices=['Behavior', 'Orientation'],
        displayable=True,
        editable=True,
        gui_order=-1,  # make sure it's always on top
        tooltip="How to mirror the module.",
    )

    parent_joint = ObjectField(displayable=True, editable=True, gui_order=-1)

    # The mirror module of this module.
    _module_mirror = ObjectField()

    # Side of this module when it's created.
    default_side = 'M'

    # all the nodes created by this modules `self.add_node`.
    owned_nodes = ObjectListField()

    # The type of this module. Used to re-instantiate the object from the maya node.
    module_type = StringField()

    # group holding all this module's guide nodes.
    guide_group = ObjectField()

    # group holding all this module's controls.
    controls_group = ObjectField()

    # group holding all this module's extra stuff.
    extras_group = ObjectField()

    # list of all of this module's deform joints.
    deform_joints = ObjectListField()

    # list of all of this module's guide_nodes.
    guide_nodes = ObjectListField()

    # All the controllers of this module.
    controllers = ObjectListField()

    guide_to_def_constraints = ObjectListField()

    def __init__(self, name, side='M', parent_joint=None, rig=None):
        if cmds.objExists(name):
            self.node_name = name
        else:
            metadata = {'base_name': name, 'side': side, 'role': 'mod'}
            self.node_name = mop.metadata.name_from_metadata(metadata)
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

            self.initialize()
            self.place_guide_nodes()
            self.update()
            self.is_initialized.set(True)

    @property
    def parent_module(self):
        parent_joint = self.parent_joint.get()
        if parent_joint:
            parent_module = cmds.listConnections(parent_joint + '.module', source=True)[
                0
            ]
            module_type = cmds.getAttr(parent_module + '.module_type')
            parent_module = all_rig_modules[module_type](parent_module, rig=self.rig)
            return parent_module

    @property
    def module_mirror(self):
        """Return the actual instance of the module mirror."""
        mirror_node = self._module_mirror.get()
        if mirror_node:
            mirror_module = all_rig_modules[self.module_type.get()](
                mirror_node, rig=self.rig
            )
            return mirror_module

    @module_mirror.setter
    def module_mirror(self, value):
        self._module_mirror.set(value)

    @property
    def is_mirrored(self):
        return bool(self.module_mirror)

    def initialize(self):
        """Creation of all the needed placement nodes.

        This must at least include all the module's Guide nodes and Deform joints.

        Will be called automatically when creating the module.
        You need to overwrite this method in your subclasses.
        """
        self.guide_group.set(
            self.add_node(
                'transform', 'grp', description='guide', parent=self.node_name
            )
        )
        cmds.setAttr(self.guide_group.get() + '.inheritsTransform', False)
        self.controls_group.set(
            self.add_node(
                'transform', role='grp', description='controls', parent=self.node_name
            )
        )

        self.extras_group.set(
            self.add_node(
                'transform', role='grp', description='extras', parent=self.node_name
            )
        )
        cmds.setAttr(self.extras_group.get() + '.visibility', False)
        self.create_guide_nodes()
        self.create_deform_joints()

    def create_guide_nodes(self):
        """Create all the guide nodes for this module."""
        raise NotImplementedError

    def create_deform_joints(self):
        """Create all the deform joints for this module."""
        raise NotImplementedError

    def place_guide_nodes(self):
        """Place the deform joints and guide nodes based on the config."""
        matrices = mop.config.default_guides_placement.get(self.__class__.__name__, {})
        for i, node in enumerate(self.guide_nodes):
            try:
                matrix = matrices[i]
            except Exception:
                logger.debug("No default matrix found of {}".format(node))
            else:
                cmds.xform(node, matrix=matrix, worldSpace=True)

    def update(self):
        """Update the maya scene based on the module's fields

        This should ONLY be called in placement mode.
        """
        if self.is_built.get():
            return

        self.update_parent_joint()

        scene_metadata = mop.metadata.metadata_from_name(self.node_name)
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
                self.node_name, category='persistent_attribute_backup'
            )
            if persistent_attrs:
                for attr in persistent_attrs:
                    old_node, attr_name = attr.split('__')

                    metadata = mop.metadata.metadata_from_name(old_node)
                    metadata['base_name'] = self.name.get()
                    metadata['side'] = self.side.get()
                    new_node = mop.metadata.name_from_metadata(metadata)
                    logger.debug(
                        "Renaming persistent attribute from {} to {}".format(
                            self.node_name + '.' + attr,
                            self.node_name + '.' + new_node + '__' + attr_name,
                        )
                    )
                    cmds.renameAttr(
                        self.node_name + '.' + attr, new_node + '__' + attr_name
                    )
        if side_changed:
            new_color = mop.config.side_color[self.side.get()]
            for guide in self.guide_nodes:
                shapeshifter.change_controller_color(guide, new_color)
        self.create_guide_nodes()
        self.create_deform_joints()
        self._constraint_deforms_to_guides()

    def update_parent_joint(self):
        """Snap and constraint the module's node to the parent_joint.

        This lets the module's owned DAG nodes be in the same space as its deform_joints.
        """
        # delete the old constraint
        # old_constraint_nodes = []

        # first_level_nodes = cmds.listConnections(
        #     self.node_name + '.translate',
        #     source=True
        # ) or []
        # old_constraint_nodes.extend(first_level_nodes)

        # for node in first_level_nodes:
        #     second_level_nodes = cmds.listConnections(
        #         node + '.inputMatrix',
        #         source=True
        #     ) or []
        #     old_constraint_nodes.extend(second_level_nodes)

        # if old_constraint_nodes:
        #     cmds.delete(old_constraint_nodes)

        # parent = self.parent_joint.get()
        # if parent:
        #     mop.dag.matrix_constraint(parent, self.node_name)

    def _update_node_name(self, node):
        metadata = mop.metadata.metadata_from_name(node)
        metadata['base_name'] = self.name.get()
        metadata['side'] = self.side.get()
        new_name = mop.metadata.name_from_metadata(metadata)
        cmds.rename(node, new_name)
        return new_name

    def _build(self):
        """Setup some stuff before actually building the module.

        Call this method instead of `build()` to make sure
        everything is setup properly
        """
        cmds.delete(self.guide_to_def_constraints.get())
        self.build()
        self.is_built.set(True)

    def build(self):
        """Actual rigging of the module.

        The end result should _always_ drive your module's deform joints
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
        self, node_type, role=None, object_id=None, description=None, *args, **kwargs
    ):
        """Add a node to this `MopNode`.

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
            'id': object_id,
        }
        name = mop.metadata.name_from_metadata(metadata)
        if cmds.objExists(name):
            raise ValueError("A node with the name `{}` already exists".format(name))
        if node_type == 'locator':
            node = cmds.spaceLocator(name=name)[0]
        else:
            node = cmds.createNode(node_type, name=name, *args, **kwargs)
        cmds.addAttr(node, longName='module', attributeType='message')
        cmds.connectAttr(self.node_name + '.message', node + '.module')
        self.owned_nodes.append(node)
        return node

    def add_deform_joint(self, parent=None, object_id=None, description=None):
        """Creates a new deform joint for this module.

        Args:
            parent (str): node under which the new joint will be parented
        """
        if object_id is None:
            object_id = len(self.deform_joints)

        new_joint = self.add_node(
            'joint', role='deform', object_id=object_id, description=description
        )

        if not parent and self.parent_joint:
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

    def add_guide_node(
        self, parent=None, object_id=None, description=None, shape_type='circle'
    ):
        """Creates a new guide node for this module."""
        if object_id is None:
            object_id = len(self.guide_nodes)

        module_matadata = mop.metadata.metadata_from_name(self.node_name)
        metadata = {}
        metadata['base_name'] = module_matadata['base_name']
        metadata['side'] = module_matadata['side']
        metadata['id'] = object_id
        if description is not None:
            metadata['description'] = description
        metadata['role'] = 'guide'
        guide_name = mop.metadata.name_from_metadata(metadata)

        guide = shapeshifter.create_controller_from_name(shape_type)
        color = mop.config.side_color[self.side.get()]
        shapeshifter.change_controller_color(guide, color)
        guide = cmds.rename(guide, guide_name)

        if not parent:
            parent = self.guide_group.get()
        cmds.parent(guide, parent)

        for transform in ['translate', 'rotate', 'scale']:
            if transform == 'scale':
                value = 1
            else:
                value = 0
            for axis in 'XYZ':
                attr = transform + axis
                cmds.setAttr(guide + '.' + attr, value)

        self.guide_nodes.append(guide)
        return guide

    def add_control(
        self, dag_node, object_id=None, description=None, shape_type='circle'
    ):
        metadata = mop.metadata.metadata_from_name(dag_node)
        if object_id is not None:
            metadata['id'] = object_id
        if description is not None:
            metadata['description'] = description
        metadata['role'] = 'ctl'
        ctl_name = mop.metadata.name_from_metadata(metadata)

        ctl = shapeshifter.create_controller_from_name(shape_type)
        ctl = cmds.rename(ctl, ctl_name)
        color = mop.config.side_color[self.side.get()]
        shapeshifter.change_controller_color(ctl, color)

        # get the existing shape data if it exists
        mop.attributes.create_persistent_attribute(
            ctl, self.node_name, longName='shape_data', dataType='string'
        )
        ctl_data = cmds.getAttr(ctl + '.shape_data')
        if ctl_data:
            ctl_data = json.loads(ctl_data)
            shapeshifter.change_controller_shape(ctl, ctl_data)

        mop.attributes.create_persistent_attribute(
            ctl, self.node_name, longName='attributes_state', dataType='string'
        )

        mop.attributes.create_persistent_attribute(
            ctl, self.node_name, longName='parent_space_data', dataType='string'
        )

        # We cannot set a default value on strings, so set the persistent
        # attribute after its creation.
        # It is mandatory to set a default value here, without a value
        # the attribute returns `None` when rebuilt and this crashes
        # the `setAttr` command.
        if not cmds.getAttr(ctl + '.parent_space_data'):
            cmds.setAttr(ctl + '.parent_space_data', '{}', type='string')

        mop.dag.snap_first_to_last(ctl, dag_node)
        parent_group = mop.dag.add_parent_group(ctl, 'buffer')
        self.controllers.append(ctl)
        return ctl, parent_group

    def _constraint_deforms_to_guides(self):
        """Catch all the nodes created by `self.constraint_deforms_to_guides` to delete them later on."""
        cmds.delete(self.guide_to_def_constraints.get())
        with _dgutils.CatchCreatedNodes() as constraint_nodes:
            self.constraint_deforms_to_guides()
        self.guide_to_def_constraints.set(constraint_nodes)

    def constraint_deforms_to_guides(self):
        """Constraint the deform joints to the guide nodes

        You need to overwrite this in subclasses.
        """
        raise NotImplementedError

    def find_non_mirrored_parents(self, non_mirrored_parents=None):
        """Recursively find the parent module that are not mirrored."""

        if non_mirrored_parents is None:
            non_mirrored_parents = []

        parent = self.parent_module

        if not parent.module_mirror and parent.side.get() != 'M':
            non_mirrored_parents.append(parent)
            RigModule.find_non_mirrored_parents(parent, non_mirrored_parents)

        return non_mirrored_parents

    def update_mirror(self):

        # update all the fields to match the mirror module
        for field in self.module_mirror.fields:
            if field.name in ['name', 'side']:
                continue
            if field.editable:
                value = None
                if isinstance(field, ObjectField):
                    orig_value = getattr(self.module_mirror, field.name).get()
                    value = find_mirror_node(orig_value)
                elif isinstance(field, ObjectListField):
                    orig_value = getattr(self.module_mirror, field.name).get()
                    value = [find_mirror_node(v) for v in orig_value]
                else:
                    value = getattr(self.module_mirror, field.name).get()

                if value:
                    getattr(self, field.name).set(value)

        self.update()

        # mirror the nodes based on the mirror type
        mirror_type = self.mirror_type.get()
        for orig_node, new_node in zip(
            self.module_mirror.guide_nodes, self.guide_nodes
        ):
            if mirror_type.lower() == 'behavior':
                # disable black formatting to keep the matrices 4x4
                # fmt: off
                world_reflexion_mat = om2.MMatrix(
                    [
                        -1.0, -0.0, -0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0,
                    ]
                )
                local_reflexion_mat = om2.MMatrix(
                    [
                        -1.0, 0.0, 0.0, 0.0,
                        0.0, -1.0, 0.0, 0.0,
                        0.0, 0.0, -1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0,
                    ]
                )
                # fmt: on
                orig_node_mat = om2.MMatrix(cmds.getAttr(orig_node + '.worldMatrix'))
                new_mat = local_reflexion_mat * orig_node_mat * world_reflexion_mat
                cmds.xform(new_node, matrix=new_mat, worldSpace=True)
                cmds.setAttr(new_node + '.scale', 1, 1, 1)
            if mirror_type.lower() == 'orientation':
                # disable black formatting to keep the matrices 4x4
                # fmt: off
                world_reflexion_mat = om2.MMatrix(
                    [
                        -1.0, -0.0, -0.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0,
                    ]
                )
                # fmt: on
                orig_node_mat = om2.MMatrix(cmds.getAttr(orig_node + '.worldMatrix'))
                new_mat = orig_node_mat * world_reflexion_mat
                cmds.xform(new_node, matrix=new_mat, worldSpace=True)
                cmds.setAttr(new_node + '.scale', 1, 1, 1)
                orig_orient = cmds.xform(orig_node, q=True, rotation=True, ws=True)
                cmds.xform(new_node, rotation=orig_orient, ws=True)

