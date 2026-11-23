import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sad import SadError, compile_file, compile_tree


class TreeCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def put(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    def compile(self):
        return compile_tree(self.root, "json")


class ObjectTests(TreeCase):
    def test_files_and_directories_become_keys(self):
        self.put("a.json", 1)
        self.put("b/c.json", '"text"')
        self.assertEqual(self.compile(), {"a": 1, "b": {"c": "text"}})

    def test_index_data_merges_into_the_object(self):
        self.put("g/index.json", {"mount": "x", "names": ["a", "b"]})
        self.put("g/list/index.json", {"$kind": "array"})
        self.assertEqual(self.compile(), {"g": {"mount": "x", "names": ["a", "b"], "list": []}})

    def test_key_defined_twice_fails(self):
        self.put("g/index.json", {"a": 1})
        self.put("g/a.json", 2)
        with self.assertRaises(SadError):
            self.compile()

    def test_file_and_directory_with_one_name_fail(self):
        self.put("a.json", 1)
        self.put("a/b.json", 2)
        with self.assertRaises(SadError):
            self.compile()


class ArrayTests(TreeCase):
    def test_name_map_puts_the_name_first(self):
        self.put("p/index.json", {"$kind": "array", "$name_map": "id"})
        self.put("p/gray.json", {"bpp": 2})
        self.assertEqual(self.compile(), {"p": [{"id": "gray", "bpp": 2}]})

    def test_order_is_index_then_name(self):
        self.put("p/index.json", {"$kind": "array", "$name_map": "id"})
        for name in ("d", "c", "b", "a"):
            self.put(f"p/{name}.json", {})
        self.put("p/c.json", {"$index": 1})
        self.put("p/d.json", {"$index": 0})
        self.assertEqual([e["id"] for e in self.compile()["p"]], ["d", "c", "a", "b"])

    def test_directory_element_takes_its_index_from_index_json(self):
        self.put("p/index.json", {"$kind": "array", "$name_map": "id"})
        self.put("p/a.json", {})
        self.put("p/z/index.json", {"$index": 0, "name": "Z"})
        self.put("p/z/specs/index.json", {"$kind": "array"})
        self.put("p/z/specs/one.json", {"part": "x"})
        self.assertEqual(self.compile()["p"],
                         [{"id": "z", "name": "Z", "specs": [{"part": "x"}]}, {"id": "a"}])

    def test_name_map_conflict_fails(self):
        self.put("p/index.json", {"$kind": "array", "$name_map": "id"})
        self.put("p/a.json", {"id": "a"})
        with self.assertRaises(SadError):
            self.compile()

    def test_array_index_with_data_fails(self):
        self.put("p/index.json", {"$kind": "array", "name": "x"})
        with self.assertRaises(SadError):
            self.compile()


class GroupTests(TreeCase):
    def setUp(self):
        super().setUp()
        self.put("p/index.json", {"$kind": "array", "$name_map": "id"})

    def test_group_elements_join_the_parent_array(self):
        self.put("p/screens/index.json", {"$kind": "group", "$group_map": "kind"})
        self.put("p/screens/lcd_a.json", {"bpp": 2})
        self.put("p/speakers/index.json", {"$kind": "group", "$group_map": "kind"})
        self.put("p/speakers/hp.json", {})
        self.assertEqual(self.compile()["p"], [{"id": "hp", "kind": "speakers"},
                                               {"id": "lcd_a", "kind": "screens", "bpp": 2}])

    def test_group_without_map_only_joins(self):
        self.put("p/more/index.json", {"$kind": "group"})
        self.put("p/more/b.json", {})
        self.put("p/a.json", {})
        self.assertEqual([e["id"] for e in self.compile()["p"]], ["a", "b"])

    def test_groups_sort_with_their_siblings(self):
        self.put("p/g/index.json", {"$kind": "group"})
        self.put("p/g/c.json", {"$index": 0})
        self.put("p/g/a.json", {})
        self.put("p/b.json", {})
        self.assertEqual([e["id"] for e in self.compile()["p"]], ["c", "a", "b"])

    def test_nested_groups_join_the_outer_array(self):
        self.put("p/g/index.json", {"$kind": "group", "$group_map": "outer"})
        self.put("p/g/h/index.json", {"$kind": "group", "$group_map": "inner"})
        self.put("p/g/h/a.json", {})
        self.assertEqual(self.compile()["p"], [{"id": "a", "outer": "g", "inner": "h"}])

    def test_group_outside_an_array_fails(self):
        self.put("o/g/index.json", {"$kind": "group"})
        with self.assertRaises(SadError):
            self.compile()

    def test_group_with_data_fails(self):
        self.put("p/g/index.json", {"$kind": "group", "name": "x"})
        with self.assertRaises(SadError):
            self.compile()

    def test_group_with_index_fails(self):
        self.put("p/g/index.json", {"$kind": "group", "$index": 0})
        with self.assertRaises(SadError):
            self.compile()

    def test_group_map_needs_a_group(self):
        self.put("q/index.json", {"$kind": "array", "$group_map": "kind"})
        with self.assertRaises(SadError):
            self.compile()

    def test_same_name_in_two_groups_fails(self):
        self.put("p/g/index.json", {"$kind": "group"})
        self.put("p/g/a.json", {})
        self.put("p/h/index.json", {"$kind": "group"})
        self.put("p/h/a.json", {})
        with self.assertRaises(SadError):
            self.compile()

    def test_group_map_conflict_fails(self):
        self.put("p/g/index.json", {"$kind": "group", "$group_map": "kind"})
        self.put("p/g/a.json", {"kind": "x"})
        with self.assertRaises(SadError):
            self.compile()

    def test_group_map_same_as_name_map_fails(self):
        self.put("p/g/index.json", {"$kind": "group", "$group_map": "id"})
        self.put("p/g/a.json", {})
        with self.assertRaises(SadError):
            self.compile()


class FlagTests(TreeCase):
    def test_unknown_flag_fails(self):
        self.put("p/index.json", {"$kind": "array", "$sort": "id"})
        with self.assertRaises(SadError):
            self.compile()

    def test_index_outside_an_array_fails(self):
        self.put("a.json", {"$index": 0})
        with self.assertRaises(SadError):
            self.compile()

    def test_index_must_be_an_integer(self):
        self.put("p/index.json", {"$kind": "array"})
        self.put("p/a.json", {"$index": "1"})
        with self.assertRaises(SadError):
            self.compile()


class FileTests(TreeCase):
    def test_foreign_file_fails(self):
        self.put("notes.txt", "x")
        with self.assertRaises(SadError):
            self.compile()

    def test_hidden_entries_are_skipped(self):
        self.put(".gitkeep", "")
        self.put("a.json", 1)
        self.assertEqual(self.compile(), {"a": 1})

    def test_duplicate_json_key_fails(self):
        self.put("a.json", '{"x": 1, "x": 2}')
        with self.assertRaises(SadError):
            self.compile()

    def test_output_is_written_only_when_it_changes(self):
        self.put("tree/a.json", 1)
        output = self.root / "out" / "db.json"
        self.assertTrue(compile_file(self.root / "tree", "json", output))
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"a": 1})
        self.assertFalse(compile_file(self.root / "tree", "json", output))


if __name__ == "__main__":
    unittest.main()
