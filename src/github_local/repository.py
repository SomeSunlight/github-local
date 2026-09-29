from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = ".github-local"
CONFIG_FILE = "config.json"


class RepositoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Repository:
    root: Path
    owner: str
    name: str

    @property
    def issues_dir(self) -> Path:
        return self.root / "issues"

    @property
    def config_dir(self) -> Path:
        return self.root / CONFIG_DIR

    @classmethod
    def initialize(cls, root: Path, *, owner: str, name: str) -> "Repository":
        root = root.resolve()
        if not (root / ".git").exists():
            raise RepositoryError(f"not a Git repository: {root}")
        cfg_dir = root / CONFIG_DIR
        cfg_dir.mkdir(exist_ok=True)
        (cfg_dir / "locks").mkdir(exist_ok=True)
        (root / "issues").mkdir(exist_ok=True)
        config_path = cfg_dir / CONFIG_FILE
        payload = {"schema": 1, "owner": owner, "repository": name}
        if config_path.exists():
            existing = json.loads(config_path.read_text(encoding="utf-8"))
            if existing != payload:
                raise RepositoryError(
                    f"already initialized with different configuration: {config_path}"
                )
        else:
            config_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        return cls(root=root, owner=owner, name=name)

    @classmethod
    def discover(cls, start: Path | None = None) -> "Repository":
        current = (start or Path.cwd()).resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            config_path = candidate / CONFIG_DIR / CONFIG_FILE
            if config_path.exists():
                try:
                    payload = json.loads(config_path.read_text(encoding="utf-8"))
                    if payload.get("schema") != 1:
                        raise RepositoryError(f"unsupported config schema: {config_path}")
                    owner = str(payload["owner"])
                    name = str(payload["repository"])
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise RepositoryError(f"invalid repository config: {config_path}") from exc
                return cls(candidate, owner, name)
        raise RepositoryError(
            "github.local is not initialized here; run `github-local init` at the Git root"
        )
