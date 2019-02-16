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
