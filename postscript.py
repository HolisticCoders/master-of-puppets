import imp
import logging
import maya.cmds as cmds
import os


logger = logging.getLogger(__name__)


def run_scripts(step):
    logger.info("Running {} scripts".format(step))
    scene_path = os.path.dirname(cmds.file(query=True, sceneName=True))
    scripts_path = os.path.join(scene_path, 'SCRIPTS', step)
    if os.path.isdir(scripts_path):
        for script_name in os.listdir(scripts_path):
            module_name = os.path.splitext(script_name)[0]
            script_path = os.path.join(scripts_path, script_name)
            mod = imp.load_source(module_name, script_path)
            logger.info("Running script: {}".format(module_name))
            mod.run()
