import json
import os

default_modules_path = os.path.join(os.path.dirname(__file__), 'default-modules.json')

with open(default_modules_path, 'r') as f:
    default_modules = json.loads(f.read())
