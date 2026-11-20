from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .errors import SadError


def _unique_keys(path: Path, pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise SadError(f"{path}: key '{key}' appears twice")
        out[key] = value
    return out


class JsonTransformer:
    extension = ".json"

    def load(self, path: Path) -> Any:
        try:
            with path.open(encoding="utf-8") as stream:
                return json.load(stream, object_pairs_hook=lambda pairs: _unique_keys(path, pairs))
        except ValueError as exc:
            raise SadError(f"{path}: {exc}") from exc

    def dump(self, value: Any) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


TRANSFORMERS = {"json": JsonTransformer}
