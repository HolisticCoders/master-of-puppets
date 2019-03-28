"""Commands used throughout the GUI."""
import sys
import logging


logger = logging.getLogger(__name__)


def reload_mop():
    """Remove all mop modules from the Python session.

    Use this command to reload the `mop` package after
    a change was made.
    """
    import mop.ui
    is_running = mop.ui.is_running()
    mop.ui.close()

    search = [
        'mop',
        'shapeshifter',
        'facseditor',
    ]

    mop_modules = []
    for module in sys.modules:
        for term in search:
            if term in module:
                mop_modules.append(module)
                break

    for module in mop_modules:
        del(sys.modules[module])

    if is_running:
        mop.ui.show()
    logger.info('Reloaded mop modules.')


def open_mop():
    """Open the `mop` GUI."""
    import mop.ui
    mop.ui.close()
    mop.ui.show()


def open_facs_editor():
    """Open the `mop` GUI."""
    import facseditor
    facseditor.close()
    facseditor.show()


def open_parent_spaces():
    """Open the `mop` GUI."""
    import mop.ui.parents
    win = mop.ui.parents.mopParentSpaces()
    win.show()


def build_rig():
    """Build the current scene rig."""
    from mop.core.rig import Rig
    import mop
    mop.incremental_save()
    rig = Rig()
    rig.build()


def unbuild_rig():
    """Unbuild the current scene rig."""
    from mop.core.rig import Rig
    import mop
    mop.incremental_save()
    rig = Rig()
    rig.unbuild()


def publish_rig():
    """Publish the current scene rig."""
    from mop.core.rig import Rig
    import mop
    mop.incremental_save()
    rig = Rig()
    rig.publish()
    mop.save_publish()

