import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).parent
PREFIX = "APP_"
ALIASES = {"num_workers": "workers"}
INT_KEYS = {"port", "workers"}

DEFAULTS: Dict[str, Any] = {
    "port": 8000, "workers": 1, "debug": False,
    "log_level": "info", "api_key": "default-secret-000",
}

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def norm_key(k: str, strip_prefix: bool = True) -> str:
    k = k.strip()
    if strip_prefix and k.upper().startswith(PREFIX):
        k = k[len(PREFIX):]
    k = k.lower()
    return ALIASES.get(k, k)


def load_yaml(env: str) -> Dict[str, Any]:
    p = BASE / f"config.{env}.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text()) or {}
    return {norm_key(str(k), False): v for k, v in data.items()}


def load_dotenv(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        out[norm_key(k)] = v
    return out


def load_os_env() -> Dict[str, Any]:
    return {norm_key(k): v for k, v in os.environ.items() if k.upper().startswith(PREFIX)}


def to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "on"}


def coerce(key: str, v: Any) -> Any:
    if key in INT_KEYS:
        try:
            return int(str(v).strip())
        except ValueError:
            raise HTTPException(422, f"{key} must be an integer")
    if key == "debug":
        return to_bool(v)
    return v if isinstance(v, str) else str(v)


def parse_overrides(items: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise HTTPException(422, f"bad override: {item}")
        k, v = item.split("=", 1)
        out[norm_key(k, False)] = v
    return out


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    env = os.environ.get("APP_ENV", "development")
    merged: Dict[str, Any] = dict(DEFAULTS)
    for layer in (load_yaml(env), load_dotenv(BASE / ".env"), load_os_env(), parse_overrides(set)):
        merged.update(layer)
    result = {k: coerce(k, v) for k, v in merged.items()}
    result["api_key"] = "****"
    return result
