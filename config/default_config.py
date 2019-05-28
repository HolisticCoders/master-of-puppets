########## General ##########
# modules that are automatically created by MOP at startup
# the dict is set up like so: {ModuleClassName:{arg1: value1, arg2: value2}}
default_modules = {"Root": {"name": "root", "side": "M"}}

controllers_data = {
    "M": {"enable_overrides": True, "use_rgb": True, "color_rgb": [1.0, 0.6, 0.0]},
    "L": {"enable_overrides": True, "use_rgb": True, "color_rgb": [0.0, 0.5, 1.0]},
    "R": {"enable_overrides": True, "use_rgb": True, "color_rgb": [1.0, 0.05, 0.05]},
}  # data for the controllers matching the data structure of shapeshifter.


########## Custom Scripts ##########
general_scripts_dir = None  # {"relative": bool, "path": str}
project_scripts_dir = None  # {"relative": bool, "path": str}
asset_scripts_dir = {"relative": True, "path": "scripts"}


########## Assets ##########
asset_types = []  # List of asset types (str)


def get_asset_type():
    """Get the asset type of the asset currently open in maya.

    :rtype: str
    """
    return


# This should contain everything that you want accessible through mop.config
# but nothing more
__all__ = [
    "default_modules",
    "controllers_data",
    "general_scripts_dir",
    "project_scripts_dir",
    "asset_scripts_dir",
    "asset_types",
    "get_asset_type",
]
