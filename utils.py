import maya.cmds as cmds


def hierarchy_to_dict(parent, tree, nodes=[]):
    """Build a python `dict` based on a `transform` hierarchy.

    Args:
        parent (str): name of the hierarchy's root node.
        tree (dict): dictionary to store the data in.
        nodes (list): only these nodes should be included in the dict.
    """
    children = cmds.listRelatives(
        parent,
        children=True,
        type='transform'
    )
    if children:
        if nodes:
            children = [c for c in children if c in nodes]
        tree[parent] = {}
        for child in children:
            hierarchy_to_dict(child, tree[parent], nodes=nodes)
    else:
        tree[parent] = None


def dict_to_hierarchy(tree):
    """Parent DAG nodes based on a dictionnary.

    Args:
        tree (dict): Dictionary representing the hierarchy.
    """
    if tree:
        for parent, child_tree in tree.iteritems():
            if child_tree:
                for child in child_tree:
                    cmds.parent(child, parent)
                reparent(child_tree)


def name_from_metadata(
    owner_base_name,
    object_side,
    object_type,
    object_id=None,
    object_description=None
):
    """Generate a node name from the given metadata.

    This function should be used EVERYTIME a node is named.
    """
    name_components = [
        owner_base_name,
        object_side,
        object_type,
    ]
    if object_description is not None:
        name_components.insert(2, object_description)
    if object_id is not None:
        object_id = str(object_id).zfill(3)
        name_components.insert(-1, object_id)
    name = '_'.join(name_components)
    return name


def metadata_from_name(name):
    data = {}
    split_name = name.split('_')

    # every name should at least contain these 3 components.
    data['owner'] = split_name.pop(0)
    data['side'] = split_name.pop(0)
    data['type'] = split_name.pop(-1)

    # try to get the optional components.
    if split_name:
        try:
            # only works if the last component is the object id.
            data['id'] = int(split_name.pop(-1))
        except ValueError:
            # if it was not the id, it can only be the description.
            data['description'] = '_'.join(split_name)
        else:
            if split_name:
                # since we removed the id, the description is the last component.
                data['description'] = '_'.join(split_name)
    return data
