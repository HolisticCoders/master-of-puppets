import os
import importlib


all_rig_modules = {}
current_dir = os.path.dirname(__file__)
for mod in os.listdir(current_dir):
    if os.path.isdir(os.path.join(current_dir, mod)):
        continue
    if mod.endswith('.pyc'):
        continue
    if mod == os.path.basename(__file__):
        continue
    mod_name = 'icarus.modules.' + mod.split('.')[0]
    current_mod = importlib.import_module(mod_name)
    for rig_module in current_mod.exported_rig_modules:
        all_rig_modules[rig_module.__name__] = rig_module
