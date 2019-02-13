import weakref

import maya.cmds as cmds

from icarus.core.fields import FieldContainerMeta, BoolField
import icarus.metadata


class IcarusNode(object):

    __metaclass__ = FieldContainerMeta

    is_initialized = BoolField(defaultValue=False)
    is_built = BoolField(defaultValue=False)
    is_published = BoolField(defaultValue=False)

    def __new__(cls, *args, **kwargs):
        if 'instances' not in cls.__dict__:
            cls.instances = weakref.WeakSet()
        if args:
            node_name = args[0]

            for inst in cls.instances:
                if inst.node_name == node_name:
                    return inst

        instance = object.__new__(cls, *args, **kwargs)
        cls.instances.add(instance)
        return instance

    def __init__(self, name):
        """Create the node if it doesn't already exist."""
        self.node_name = name
        if not cmds.objExists(name):
            cmds.createNode('transform', name=name)

        for field in self.fields:
            field.ensure_maya_attr(self)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.node_name)

    def __str__(self):
        return self.node_name

    def add_node(self, node_type, role, object_id=None, description=None, *args, **kwargs):
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
        return node

