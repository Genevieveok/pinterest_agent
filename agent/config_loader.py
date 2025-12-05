import os
import yaml

def replace_env(value):
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        return os.getenv(value[2:-1], '')
    return value

def walk_replace(obj):
    if isinstance(obj, dict):
        return {k: walk_replace(v) for k,v in obj.items()}
    if isinstance(obj, list):
        return [walk_replace(v) for v in obj]
    return replace_env(obj)

def load_yaml_with_env(path):
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    return walk_replace(raw)
