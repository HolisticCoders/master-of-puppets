import maya.cmds as cmds

from icarus.core.fields import BoolField


class IcarusNode(object):

    is_initialized = BoolField('is_initialized', defaultValue=False)
    is_built = BoolField('is_built', defaultValue=False)
    is_published = BoolField('is_published', defaultValue=False)

    def __init__(self, name, node_type=None):
        """Create the node if it doesn't already exist."""
        self.node_name = name
        if not cmds.objExists(name):
            if node_type is None:
                node_type = 'transform'
            elif node_type not in cmds.allNodeTypes():
                raise Exception("Specified `{}` node_type is not a valid maya node.".format(node_type))
                return
            cmds.createNode(node_type, name=name)

