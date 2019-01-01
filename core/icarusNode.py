import weakref

import maya.cmds as cmds

from icarus.core.fields import FieldContainerMeta, BoolField


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
        """Create the node if it doesn't already exist."""
        self.node_name = name
        if not cmds.objExists(name):
            if node_type is None:
                node_type = 'transform'
            elif node_type not in cmds.allNodeTypes():
                raise Exception("Specified `{}` node_type is not a valid maya node.".format(node_type))
                return
            cmds.createNode(node_type, name=name)
