from icarus.vendor.Qt import QtCore


def get_settings():
    """Return Icarus application settings."""
    return QtCore.QSettings(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        'Holistic Coders',
        'Icarus',
    )
