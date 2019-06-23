import maya.cmds as cmds
import mop.metadata


class CatchCreatedNodes(object):
    def __init__(self):
        self.nodes = []
        self.before_nodes = set()
        self.after_nodes = set()

    def __enter__(self):
        self.before_nodes = set(cmds.ls("*"))
        return self.nodes

    def __exit__(self, *args):
        self.after_nodes = set(cmds.ls("*"))
        self.nodes.extend(list(self.after_nodes - self.before_nodes))


def find_mirror_node(node):
    """Find the mirror of the specified node."""
    if not node:
        return None

    metadata = mop.metadata.metadata_from_name(node)
    mirror_metadata = metadata
    orig_side = metadata["side"]
    if orig_side == "M":
        mirror_node = node
    else:
        mirror_metadata["side"] = "R" if orig_side == "L" else "L"
        mirror_node = mop.metadata.name_from_metadata(mirror_metadata)

    if cmds.objExists(mirror_node):
        return mirror_node

    return None
