import imp
import logging
import os

import config
import maya.cmds as cmds

logger = logging.getLogger(__name__)


def run_scripts(step):
    general_dir = get_scripts_dir(level="general")
    if general_dir:
        logger.info("Running general {} scripts".format(step))
        general_step_dir = os.path.join(general_dir, step)
        run_scripts_from_path(general_step_dir)

    project_dir = get_scripts_dir(level="project")
    if project_dir:
        logger.info("Running project {} scripts".format(step))
        project_step_dir = os.path.join(project_dir, step)
        run_scripts_from_path(project_step_dir)

    asset_dir = get_scripts_dir(level="asset")
    if asset_dir:
        logger.info("Running asset {} scripts".format(step))
        asset_step_dir = os.path.join(asset_dir, step)
        run_scripts_from_path(asset_step_dir)


def run_scripts_from_path(scripts_path):
    if os.path.isdir(scripts_path):
        for script_name in os.listdir(scripts_path):
            module_name = os.path.splitext(script_name)[0]
            script_path = os.path.join(scripts_path, script_name)
            mod = imp.load_source(module_name, script_path)
            logger.info("Running script: {}".format(module_name))
            mod.run()


def get_scripts_dir(level="asset"):
    dir_data = getattr(config, level + "_scripts_dir")
    if dir_data is None:
        return
    if dir_data["relative"]:
        scene_path = os.path.dirname(cmds.file(query=True, sceneName=True))
        return os.path.join(scene_path, dir_data["path"])
    else:
        return dir_data["path"]
