import yaml, pathlib

def load_policy(path: str|pathlib.Path) -> dict:
    p = pathlib.Path(path)
    return yaml.safe_load(p.read_text())


