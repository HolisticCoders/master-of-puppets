import json
import logging
import time
from collections import OrderedDict
import re

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from mop.core.mopNode import MopNode
from mop.modules import all_rig_modules
from mop.config import default_modules
from mop.core.fields import ObjectField, ObjectListField
from mop.utils.undo import undoable
from mop.utils.dg import find_mirror_node
import mop.dag
from shapeshifter import shapeshifter

logger = logging.getLogger(__name__)


class Rig(MopNode):

    modules_group = ObjectField()
    extras_group = ObjectField()
    skeleton_group = ObjectField()

    def __init__(self):
        super(Rig, self).__init__("RIG")

        if not self.is_initialized.get():
            self._create_basic_hierarchy()
            self._add_default_modules()
            self.is_initialized.set(True)

    @property
    def rig_modules(self):
        modules = []
        for node in cmds.listRelatives(self.modules_group.get()) or []:
            module_type = cmds.getAttr(node + ".module_type")
            module = all_rig_modules[module_type](node, rig=self)
            modules.append(module)

        sorted_modules = []
        while modules:
            module = modules.pop()
            self.sort_parent_module(module, modules, sorted_modules)

        return sorted_modules

    def sort_parent_module(self, module, modules, sorted_modules):
        parent_module = module.parent_module
        if parent_module in modules:
            modules.remove(parent_module)
            self.sort_parent_module(parent_module, modules, sorted_modules)

        sorted_modules.append(module)

    @property
    def skeleton(self):
        return [
            n
            for n in reversed(
                cmds.listRelatives(self.skeleton_group.get(), allDescendents=True)
            )
            if cmds.nodeType(n) == "joint"
        ]

    @property
    def build_nodes(self):
        all_nodes = cmds.ls("*")
        build_nodes = []
        for node in all_nodes:
            if cmds.attributeQuery("is_build_node", node=node, exists=True):
                build_nodes.append(node)
        return build_nodes

    def _create_basic_hierarchy(self):
        if not cmds.objExists("MODULES"):
            self.modules_group.set(cmds.createNode("transform", name="MODULES"))
            cmds.parent(self.modules_group.get(), "RIG")
        if not cmds.objExists("EXTRAS"):
            self.extras_group.set(cmds.createNode("transform", name="EXTRAS"))
            cmds.parent(self.extras_group.get(), "RIG")
        if not cmds.objExists("SKELETON"):
            self.skeleton_group.set(cmds.createNode("transform", name="SKELETON"))
            cmds.parent(self.skeleton_group.get(), "RIG")
            
            # make the deform_joints unselectable
            cmds.setAttr(self.skeleton_group.get() + ".overrideEnabled", True)
            cmds.setAttr(self.skeleton_group.get() + ".overrideDisplayType", 2)

    def _add_default_modules(self):
        for module_type, data in default_modules.iteritems():
            self.add_module(module_type, **data)

    @undoable
    def add_module(self, module_type, *args, **kwargs):
        if self.is_built.get():
            raise RuntimeError("Cannot add module when the rig is built.")

        if module_type not in all_rig_modules:
            raise ValueError("Module Type {} is not valid".format(module_type))

        name = kwargs.get("name", module_type.lower())
        side = kwargs.get("side", all_rig_modules[module_type].default_side)

        # extract the name without the index of the module
        pattern = "^(?P<raw_name>[a-zA-Z]*)[0-9]*"
        regex = re.compile(pattern)
        match = re.match(regex, name)
        raw_name = match.group("raw_name")

        # get the highest index from the modules with the same name and side
        highest_index = None
        for mod in self.rig_modules:
            pattern = "^{}(?P<id>[0-9]*)_{}_mod".format(raw_name, side)
            regex = re.compile(pattern)
            match = re.match(regex, mod.node_name)
            if match:
                index = match.group("id")
                index = int(index) if index else 0
                if index > highest_index:
                    highest_index = index

        if highest_index is not None:
            name = raw_name + str(highest_index + 1).zfill(2)

        # update the kwargs in case the values changed
        kwargs["rig"] = self
        kwargs["name"] = name
        kwargs["side"] = side
        new_module = all_rig_modules[module_type](*args, **kwargs)

        return new_module

    def get_module(self, module_node_name):
        """Get a module instance from a node name.

        :param module_node_name: name of the module's node
        :type module_node_name: str
        """
        for module in self.rig_modules:
            if module.node_name == module_node_name:
                return module
        logger.warning("Found no module named {}.".format(module_node_name))

    @undoable
    def delete_module(self, module_node_name):
        """Delete a module.

        :param module_node_name: name of the module's node
        :type module_node_name: str
        """
        if self.is_built.get():
            logger.error("Cannot delete a module if the rig is built.")
            return

        module_to_del = self.get_module(module_node_name)
        deform_joints = module_to_del.deform_joints.get()
        for module in self.rig_modules:
            if module.parent_joint.get() in deform_joints:
                new_parent_joint = module_to_del.parent_joint.get()
                module.parent_joint.set(new_parent_joint)
                module.update()
        cmds.delete(module_to_del.node_name)
        cmds.delete(deform_joints)

    @undoable
    def build(self):
        self.deactivate_move_joints_mode()
        nodes_before_build = set(cmds.ls("*"))
        for module in self.rig_modules:
            logger.info("Building: " + module.node_name)
            module._build()

            # set the attributes state back to what it was before unbuilding
            for ctl in module.controllers.get():
                attributes_state = cmds.getAttr(ctl + ".attributes_state")
                if attributes_state:
                    attributes_state = json.loads(attributes_state)
                    mop.attributes.set_attributes_state(ctl, attributes_state)
            cmds.setAttr(module.guide_group.get() + ".visibility", False)

        nodes_after_build = set(cmds.ls("*"))
        build_nodes = list(nodes_after_build - nodes_before_build)

        for module in self.rig_modules:
            for ctl in module.controllers.get():
                parent_spaces = cmds.getAttr(ctl + ".parent_space_data")
                if not parent_spaces:
                    continue

                # Restore parent spaces.
                # We use an OrderedDict to load saved data
                # in order to preserve the parents ordering.
                spaces = json.loads(parent_spaces, object_pairs_hook=OrderedDict)
                if not hasattr(spaces, "get"):
                    # In case serialized data is bad or serialization
                    # changes along the way.
                    continue

                # TODO: Allow multiple types of spaces at the same type
                parents = spaces.get("parent", [])
                orients = spaces.get("orient", [])
                points = spaces.get("point", [])
                if parents:
                    mop.dag.create_space_switching(ctl, parents, "parent")
                elif orients:
                    mop.dag.create_space_switching(ctl, orients, "orient")
                elif points:
                    mop.dag.create_space_switching(ctl, points, "point")


        self._tag_nodes_for_unbuild(build_nodes)

        # make the deform joints selectable
        cmds.setAttr(self.skeleton_group.get() + ".overrideEnabled", False)
        cmds.setAttr(self.skeleton_group.get() + ".overrideDisplayType", 0)

        self.is_built.set(True)

    @undoable
    def unbuild(self):
        self.reset_pose()

        for module in self.rig_modules:
            for ctl in module.controllers.get():
                try:
                    shape_data = shapeshifter.get_shape_data(ctl)
                    cmds.setAttr(
                        ctl + ".shape_data", json.dumps(shape_data), type="string"
                    )
                except:
                    pass
                attributes_state = mop.attributes.get_attributes_state(ctl)
                cmds.setAttr(
                    ctl + ".attributes_state",
                    json.dumps(attributes_state),
                    type="string",
                )
            cmds.setAttr(module.guide_group.get() + ".visibility", True)

        for node in self.skeleton:
            for attribute in [".translate", ".rotate", ".scale"]:
                attr = node + attribute
                input_attr = cmds.connectionInfo(attr, sourceFromDestination=True)
                if input_attr:
                    cmds.disconnectAttr(input_attr, attr)
        cmds.delete(self.build_nodes)
        for module in self.rig_modules:
            module._constraint_deforms_to_guides()
            module.is_built.set(False)

        # make the deform joints unselectable
        cmds.setAttr(self.skeleton_group.get() + ".overrideEnabled", True)
        cmds.setAttr(self.skeleton_group.get() + ".overrideDisplayType", 2)
        self.activate_move_joints_mode()
        self.is_built.set(False)

    def publish(self):
        cmds.setAttr(self.skeleton_group.get() + ".visibility", False)
        for module in self.rig_modules:
            logger.info("Publishing: " + module.node_name)
            module.publish()

    @staticmethod
    @undoable
    def reset_pose():
        for control in cmds.ls("*_ctl"):
            mop.dag.reset_node(control)

    def _tag_nodes_for_unbuild(self, nodes):
        """Tag the nodes created during the build.

        this will allow to delete them easily later on.
        """
        for node in nodes:
            cmds.addAttr(
                node, longName="is_build_node", attributeType="bool", defaultValue=True
            )

    def mirror_module(self, module):
        """Mirrors the specified rig module."""

        # don't mirror an already mirrored module
        if module.is_mirrored:
            return

        # make sure we're not mirroring a middle module
        orig_side = module.side.get()
        if orig_side == "M":
            return

        # recursively mirror all parent modules that aren't already mirrored
        non_mirrored_parents = module.find_non_mirrored_parents()
        if non_mirrored_parents:
            for parent in non_mirrored_parents:
                self.mirror_module(parent)

        new_side = "R" if orig_side == "L" else "L"
        orig_name = module.name.get()
        orig_type = module.module_type.get()

        orig_parent_module = module.parent_module
        metadata = mop.metadata.metadata_from_name(orig_parent_module.node_name)
        metadata["side"] = new_side
        new_parent_module = mop.metadata.name_from_metadata(metadata)
        if not cmds.objExists(new_parent_module):
            new_parent_module = orig_parent_module

        new_module = self.add_module(
            orig_type, name=orig_name, side=new_side, parent_module=new_parent_module
        )

        module.module_mirror = self.node_name
        new_module.module_mirror = module.node_name

        new_module.update_mirror()

        return new_module

    @undoable
    def duplicate_module(self, module):
        """Duplicate the specified rig module"""
        module_type = module.module_type.get()
        name = module.name.get()
        side = module.side.get()
        new_module = module.rig.add_module(
            module_type, name=name, side=side, parent_module=module.parent_module
        )
        for field in module.fields:
            if field.name in ["name", "side"]:
                continue
            if field.editable:
                value = getattr(module, field.name).get()
                getattr(new_module, field.name).set(value)
        new_module.update()

        # orig_nodes = module.deform_joints.get() + module.guide_nodes.get()
        # new_nodes = new_module.deform_joints.get() + new_module.guide_nodes.get()
        for orig_node, new_node in zip(module.guide_nodes, new_module.guide_nodes):
            for attr in ["translate", "rotate", "scale", "jointOrient"]:
                for axis in "XYZ":
                    attr_name = attr + axis
                    if not cmds.attributeQuery(attr_name, node=orig_node, exists=True):
                        continue
                    value = cmds.getAttr(orig_node + "." + attr_name)
                    cmds.setAttr(new_node + "." + attr_name, value)
        return new_module

    def activate_move_joints_mode(self):
        for module in self.rig_modules:
            for joint in module.deform_joints:
                plugs = cmds.listConnections(joint + '.worldMatrix[0]', type='skinCluster', plugs=True)
                if not plugs:
                    continue
                for plug in plugs:
                    regex = re.match("(.*).matrix\[([0-9])\]", plug)
                    node, index = regex.groups()
                    cmds.connectAttr(joint + ".worldInverseMatrix[0]", node + '.bindPreMatrix[{}]'.format(index))

    def deactivate_move_joints_mode(self):
        for module in self.rig_modules:
            for joint in module.deform_joints:
                plugs = cmds.listConnections(joint + '.worldInverseMatrix[0]', type='skinCluster', plugs=True)
                if not plugs:
                    continue
                for plug in plugs:
                    regex = re.match("(.*).bindPreMatrix\[([0-9])\]", plug)
                    node, index = regex.groups()
                    cmds.disconnectAttr(joint + ".worldInverseMatrix[0]", node + ".bindPreMatrix[{}]".format(index))
                    mat = cmds.getAttr(joint + ".worldInverseMatrix[0]")
                    cmds.setAttr(node + ".bindPreMatrix[{}]".format(index), mat, type="matrix")

                bind_poses = cmds.dagPose(joint, bindPose=True, q=True)
                for bind_pose in bind_poses:
                    cmds.dagPose(joint, reset=True, n=bind_pose)
