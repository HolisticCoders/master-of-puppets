import re

import maya.cmds as cmds


def increment_version(path):
    """Increment the version of `path` and return it.

    The base implementation looks for the following pattern:

    `v001`

    If you use a different versionning convention, you can
    specify another function to use instead by overriding
    the `icarus.increment_version` attribute.

    Example::

        >>> def my_increment_version(path):
        ...     return path + '1'
        >>> import icarus
        >>> icarus.increment_version = my_increment_version

    The ``path`` argument is automatically given to you
    by `icarus` when a new path version is needed, and
    corresponds to the current version path.

    If the path is invalid (e.g does not contain a version
    number), you can raise a :class:`ValueError` to notify
    `icarus` something went wrong.

    .. note::

        This function will not save the scene, but is used to
        create a new file name for the incremental save feature
        of `icarus`.

    :param path: Path to increment.
    :type path: str
    :rtype: str
    :raise ValueError: When the path does not contain a version number.
    """
    pattern = r'v(?P<version>\d{3})'
    regex = re.compile(pattern)
    match = regex.search(path)
    if not match:
        raise ValueError('%s does not contain a version number' % path)
    version = match.group('version')
    version = 'v' + str(int(version) + 1).zfill(3)
    return regex.sub(version, path)


def incremental_save():
    """Increment the current scene version.

    The base implementation uses :func:`icarus.increment_version` to
    generate the new file path.

    If you want to further customize the way scenes are saved, you
    can override the `icarus.incremental_save` attribute.

    :raise ValueError: When the path does not contain a version number.
                       This exception is inherited from
                       :func:`icarus.increment_version`.
    """
    import icarus
    path = cmds.file(query=True, location=True)
    new_path = icarus.increment_version(path)
    cmds.file(rename=new_path)
    cmds.file(save=True, force=True)
