"""Commands used throughout the GUI."""
import sys
import logging


logger = logging.getLogger(__name__)


def reload_icarus():
    """Remove all icarus modules from the Python session.

    Use this command to reload the `icarus` package after
    a change was made.
    """
    import icarus.ui
    is_running = icarus.ui.is_running()
    icarus.ui.close()

    search = [
        'icarus',
        'shapeshifter',
        'facseditor',
    ]

    icarus_modules = []
    for module in sys.modules:
        for term in search:
            if term in module:
                icarus_modules.append(module)
                break

    for module in icarus_modules:
        del(sys.modules[module])

    if is_running:
        icarus.ui.show()
    logger.info('Reloaded Icarus modules.')


def open_icarus():
    """Open the `icarus` GUI."""
    import icarus.ui
    icarus.ui.close()
    icarus.ui.show()


def open_facs_editor():
    """Open the `icarus` GUI."""
    import icarus.vendor.facseditor.window
    win = icarus.vendor.facseditor.window.FACSWindow()
    win.show()


def open_parent_spaces():
    """Open the `icarus` GUI."""
    import icarus.ui.parents
    win = icarus.ui.parents.IcarusParentSpaces()
    win.show()


def build_rig():
    """Build the current scene rig."""
    from icarus.core.rig import Rig
    import icarus
    icarus.incremental_save()
    rig = Rig()
    rig.build()


def unbuild_rig():
    """Unbuild the current scene rig."""
    from icarus.core.rig import Rig
    import icarus
    icarus.incremental_save()
    rig = Rig()
    rig.unbuild()


def publish_rig():
    """Publish the current scene rig."""
    from icarus.core.rig import Rig
    import icarus
    icarus.incremental_save()
    rig = Rig()
    rig.publish()
    icarus.save_publish()

