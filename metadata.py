import maya.cmds as cmds


def name_from_metadata(metadata):
    """Generate a node name from the given metadata.

    This function should be used EVERYTIME a node is named.
    """
    name_components = [
        metadata['base_name'],
        metadata['side'],
        metadata['role'],
    ]
    if metadata.get('description', None) is not None:
        name_components.insert(2, metadata['description'])
    if metadata.get('id', None) is not None:
        object_id = str(metadata['id']).zfill(3)
        name_components.insert(-1, object_id)
    name = '_'.join(name_components)
    return name


def metadata_from_name(name):
    data = {}
    split_name = name.split('_')

    # every name should at least contain these 3 components.
    data['base_name'] = split_name.pop(0)
    data['side'] = split_name.pop(0)
    data['role'] = split_name.pop(-1)
    data['id'] = None
    data['description'] = None

    # try to get the optional components.
    if split_name:
        try:
            # only works if the last component is the object id.
            data['id'] = int(split_name[-1])
            split_name.pop(-1)
        except ValueError:
            # if it was not the id, it can only be the description.
            data['description'] = '_'.join(split_name)
        else:
            if split_name:
                # since we removed the id,
                # the description is the last component.
                data['description'] = '_'.join(split_name)
    return data


