import json
import os

default_modules_path = os.path.join(os.path.dirname(__file__), 'default-modules.json')
controller_colors_path = os.path.join(os.path.dirname(__file__), 'controller-colors.json')

with open(default_modules_path, 'r') as f:
    default_modules = json.loads(f.read())

with open(controller_colors_path, 'r') as f:
    controller_colors = json.loads(f.read())
