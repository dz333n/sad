from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import SadError
from .transformers import TRANSFORMERS

FLAG_PREFIX = "$"
KIND = "$kind"
NAME_MAP = "$name_map"
INDEX = "$index"
KIND_OBJECT = "object"
KIND_ARRAY = "array"
INDEX_FILE_STEM = "index"
DIRECTORY_FLAGS = {KIND, NAME_MAP, INDEX}
ELEMENT_FLAGS = {INDEX}


def _split_flags(value: Dict[str, Any], allowed: set, path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    flags = {k: v for k, v in value.items() if k.startswith(FLAG_PREFIX)}
    unknown = sorted(set(flags) - allowed)
    if unknown:
        raise SadError(f"{path}: unknown compiler flags {unknown}")
    data = {k: v for k, v in value.items() if not k.startswith(FLAG_PREFIX)}
    return data, flags


def _element_index(flags: Dict[str, Any], in_array: bool, path: Path) -> Optional[int]:
    if INDEX not in flags:
        return None
    index = flags[INDEX]
    if not in_array:
        raise SadError(f"{path}: {INDEX} is valid only for an element of an array")
    if not isinstance(index, int) or isinstance(index, bool):
        raise SadError(f"{path}: {INDEX} must be an integer")
    return index


class Compiler:
    def __init__(self, transformer_id: str):
        if transformer_id not in TRANSFORMERS:
            raise SadError(f"unknown transformer '{transformer_id}', known: {sorted(TRANSFORMERS)}")
        self._transformer = TRANSFORMERS[transformer_id]()
        self._index_name = INDEX_FILE_STEM + self._transformer.extension

    def compile(self, root: Path) -> Any:
        root = Path(root)
        if not root.is_dir():
            raise SadError(f"{root}: the root must be a directory")
        return self._directory(root, in_array=False)[0]

    def dump(self, value: Any) -> str:
        return self._transformer.dump(value)

    def _node(self, path: Path, in_array: bool) -> Tuple[Any, Optional[int]]:
        if path.is_dir():
            return self._directory(path, in_array)
        value = self._transformer.load(path)
        if not isinstance(value, dict):
            return value, None
        data, flags = _split_flags(value, ELEMENT_FLAGS, path)
        return data, _element_index(flags, in_array, path)

    def _directory(self, path: Path, in_array: bool) -> Tuple[Any, Optional[int]]:
        index_path = path / self._index_name
        settings = self._transformer.load(index_path) if index_path.is_file() else {}
        if not isinstance(settings, dict):
            raise SadError(f"{index_path}: an index must hold an object")
        data, flags = _split_flags(settings, DIRECTORY_FLAGS, index_path)
        index = _element_index(flags, in_array, index_path)
        kind = flags.get(KIND, KIND_OBJECT)
        name_map = flags.get(NAME_MAP)
        children = self._children(path)
        if kind == KIND_ARRAY:
            if data:
                raise SadError(f"{index_path}: the index of an array holds no data keys")
            return self._array(children, name_map, index_path), index
        if kind != KIND_OBJECT:
            raise SadError(f"{index_path}: {KIND} must be '{KIND_OBJECT}' or '{KIND_ARRAY}'")
        if name_map is not None:
            raise SadError(f"{index_path}: {NAME_MAP} needs {KIND} '{KIND_ARRAY}'")
        return self._object(data, children), index

    def _children(self, path: Path) -> List[Tuple[str, Path]]:
        named: Dict[str, Path] = {}
        for child in path.iterdir():
            if child.name.startswith(".") or child.name == self._index_name:
                continue
            if child.is_dir():
                name = child.name
            elif child.suffix == self._transformer.extension:
                name = child.stem
            else:
                raise SadError(f"{child}: not a '{self._transformer.extension}' file")
            if name in named:
                raise SadError(f"{child}: '{name}' is also {named[name]}")
            named[name] = child
        return sorted(named.items())

    def _array(self, children: List[Tuple[str, Path]], name_map: Any, index_path: Path) -> List[Any]:
        if name_map is not None and (not isinstance(name_map, str) or not name_map):
            raise SadError(f"{index_path}: {NAME_MAP} must be a property name")
        elements = []
        for name, child in children:
            value, index = self._node(child, in_array=True)
            if name_map is not None:
                if not isinstance(value, dict):
                    raise SadError(f"{child}: {NAME_MAP} needs an object")
                if name_map in value:
                    raise SadError(f"{child}: '{name_map}' comes from the name, remove it")
                value = {name_map: name, **value}
            elements.append(((index is None, index or 0, name), value))
        elements.sort(key=lambda element: element[0])
        return [value for _key, value in elements]

    def _object(self, data: Dict[str, Any], children: List[Tuple[str, Path]]) -> Dict[str, Any]:
        out = dict(data)
        for name, child in children:
            if name in out:
                raise SadError(f"{child}: key '{name}' is already defined in the index")
            out[name] = self._node(child, in_array=False)[0]
        return out


def compile_tree(root: Path, transformer_id: str) -> Any:
    return Compiler(transformer_id).compile(root)


def compile_file(root: Path, transformer_id: str, output: Path) -> bool:
    compiler = Compiler(transformer_id)
    text = compiler.dump(compiler.compile(root))
    output = Path(output)
    if output.is_file() and output.read_text(encoding="utf-8") == text:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(text.encode("utf-8"))
    return True
