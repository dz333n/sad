# SAD - Structure-as-Directory

SAD compiles a tree of directories/files into one structured file. Split your giant JSON into a managaeable storage and get your JSON back as a build artifact.

```
python -m sad <root> <transformer> <output>
```

`<transformer>` - the file format. `json` is the only one supported.

## Compile chain and compiler flags (JSON)

- A directory compiles to an object by default. Each file in it becomes a key named after the file, without its extension. Each subdirectory becomes a key named after the directory.
- `index.json` in a directory is optional. Keys start with `$` are compiler flags. Other keys are merged into the object of directory.
- `"$kind": "array"` turns directory into an array. Each file and each subdirectory is one element.
- (for arrays) `"$name_map": "<property>"` - map the file name into a property of array member
- (for array's element) `"$index": <integer>` - set position in array. Leave blank for alphabetial sort.
- All compiler flags are removed from the output. What starts with `.` is skipped.

## Example

```
db/
    guest_additions/
        index.json              {"mount_point": "\\Storage"}
        palettes/
            index.json          {"$kind": "array", "$name_map": "id"}
            gray.json           {"$index": 0, "bpp": 2}
            black_and_white.json {"bpp": 1}
```

↓

```json
{
  "guest_additions": {
    "mount_point": "\\Storage",
    "palettes": [
      {"id": "gray", "bpp": 2},
      {"id": "black_and_white", "bpp": 1}
    ]
  }
}
```

## Tests

```
python -m unittest discover -s tests
```

## [MIT](LICENSE)