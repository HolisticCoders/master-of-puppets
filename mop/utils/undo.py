import contextlib
from functools import wraps

import maya.cmds as cmds


@contextlib.contextmanager
def undoChunk():
    """Code block will execute in one undo chunk."""
    cmds.undoInfo(openChunk=True)
    yield
    cmds.undoInfo(closeChunk=True)


def undoable(func):
    """Decorated function will execute in one undo chunk."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)

    return wrapped
