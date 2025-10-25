import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import jsonschema

from tools import generate_vex


SCHEMA = json.loads(Path("schema/cyclonedx-vex-1.5.schema.json").read_text())


class GenerateVexTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.base_path = Path(self._tmpdir.name)

    def _write_config(self, payload: list[dict[str, object]]) -> Path:
        config_path = self.base_path / "statements.json"
        config_path.write_text(json.dumps(payload))
        return config_path

    def test_emits_schema_compliant_vex_document(self) -> None:
        config_path = self._write_config(
            [
                {
                    "id": "CVE-2025-1000",
                    "status": "not_affected",
                    "justification": "component_not_present",
                    "details": "Security team reviewed the component footprint.",
                    "impact": "Library only shipped in build images.",
                    "timestamp": "2024-10-01T00:00:00Z",
                    "source": {
                        "name": "Red Team Assessment",
                        "url": "https://security.example.test/cve/CVE-2025-1000",
                    },
                },
                {
                    "id": "CVE-2025-2000",
                    "status": "fixed",
                },
            ]
        )
        output_path = self.base_path / "vex.json"
        subject = "ghcr.io/example/app@sha256:deadbeef"

        with mock.patch.object(generate_vex, "_now_iso8601", return_value="2025-01-01T00:00:00+00:00"), mock.patch(
            "tools.generate_vex.uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-9abc-123456789abc")
        ):
            generate_vex.generate_vex(
                config_path=config_path,
                output_path=output_path,
                subject=subject,
                manufacturer="ci-intel",
                product="ci-intel-app",
            )

        payload = json.loads(output_path.read_text())

        jsonschema.validate(payload, SCHEMA)

        self.assertEqual(payload["serialNumber"], "urn:uuid:12345678-1234-5678-9abc-123456789abc")
        self.assertEqual(payload["metadata"]["timestamp"], "2025-01-01T00:00:00+00:00")
        self.assertEqual(payload["metadata"]["component"]["manufacturer"], "ci-intel")
        self.assertEqual(payload["metadata"]["properties"][0]["value"], subject)
        self.assertEqual(payload["metadata"]["properties"][1]["value"], "sha256:deadbeef")

        vuln_one, vuln_two = payload["vulnerabilities"]
        self.assertEqual(vuln_one["id"], "CVE-2025-1000")
        self.assertEqual(vuln_one["analysis"]["state"], "not_affected")
        self.assertEqual(vuln_one["analysis"]["justification"], "component_not_present")
        self.assertEqual(vuln_one["analysis"]["detail"], "Security team reviewed the component footprint.")
        self.assertEqual(vuln_one["detail"], "Library only shipped in build images.")
        self.assertEqual(vuln_one["timestamp"], "2024-10-01T00:00:00Z")
        self.assertEqual(vuln_one["source"]["name"], "Red Team Assessment")
        self.assertEqual(vuln_one["source"]["url"], "https://security.example.test/cve/CVE-2025-1000")

        self.assertEqual(vuln_two["id"], "CVE-2025-2000")
        self.assertEqual(vuln_two["analysis"]["state"], "fixed")
        self.assertEqual(vuln_two["ratings"], [])
        self.assertNotIn("detail", vuln_two)
        self.assertNotIn("source", vuln_two)


if __name__ == "__main__":
    unittest.main()
