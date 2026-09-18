from pathlib import Path
import yaml

def load_config(path: str | Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(path)
    cfg["_project_root"] = str(path.parent.parent)
    return cfg

def project_path(cfg: dict, relative_path: str) -> Path:
    return Path(cfg["_project_root"]) / relative_path
