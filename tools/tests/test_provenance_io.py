import json
from pathlib import Path
import tempfile
import unittest

from tools import provenance_io


class TestProvenanceIO(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)

    def test_load_records_from_array(self):
        data = [{"payloadType": "in-toto", "payload": "aaa"}]
        path = self.tmpdir / "prov.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        records = provenance_io.load_records(path)
        self.assertEqual(records, data)

    def test_load_records_from_single_object(self):
        data = {"payloadType": "in-toto", "payload": "bbb"}
        path = self.tmpdir / "single.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        records = provenance_io.load_records(path)
        self.assertEqual(records, [data])

    def test_load_records_from_jsonl(self):
        entries = [
            {"payloadType": "in-toto", "payload": "aaa"},
            {"payloadType": "in-toto", "payload": "bbb"},
        ]
        path = self.tmpdir / "multi.jsonl"
        path.write_text(
            "\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8"
        )
        records = provenance_io.load_records(path)
        self.assertEqual(records, entries)

    def test_dump_records_creates_pretty_json(self):
        path = self.tmpdir / "out.json"
        provenance_io.dump_records(
            [{"payloadType": "in-toto", "payload": "ccc"}], path, indent=4
        )
        content = path.read_text(encoding="utf-8")
        self.assertIn("\n", content)
        parsed = json.loads(content)
        self.assertEqual(len(parsed), 1)
