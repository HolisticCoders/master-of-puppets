from mop.vendor.Qt import QtCore


def get_settings():
    """Return mop application settings."""
    return QtCore.QSettings(
        QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, "Holistic Coders", "mop"
    )
