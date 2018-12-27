import imp
import os
import maya.cmds as cmds


def run_post_scripts(step):
    scene_path = os.path.dirname(cmds.file(query=True, sceneName=True))
    scripts_path = os.path.join(scene_path, 'SCRIPTS', step)
    for script_name in os.listdir(scripts_path):
        script_path = os.path.join(scripts_path, script_name)
        mod = imp.load_source(script_name, script_path)
        mod.run()


