import json
import tempfile
import unittest
from pathlib import Path

from tools import build_vuln_input


class BuildVulnInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.base_path = Path(self._tmpdir.name)

    def _write_json(self, filename: str, payload: dict) -> Path:
        target = self.base_path / filename
        target.write_text(json.dumps(payload))
        return target

    def test_aggregates_cvss_and_epss_across_matches(self) -> None:
        report = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-0001",
                        "cvss": [
                            {"metrics": {"baseScore": 5.1}},
                            {"metrics": {"baseScore": 7.5}},
                        ],
                        "severity": "high",
                    },
                    "relatedVulnerabilities": [
                        {
                            "cvss": [{"metrics": {"baseScore": 9.3}}],
                            "metadata": {"epss": {"percentile": 90}},
                        }
                    ],
                    "metadata": {"epss": {"percentile": 0.7}},
                },
                {
                    "vulnerability": {
                        "id": "CVE-0002",
                        "severity": "medium",
                    },
                    "relatedVulnerabilities": [],
                },
                {
                    "vulnerability": {
                        "id": "CVE-0002",
                        "severity": "low",
                    },
                    "epss": {"percentile": 65},
                },
            ]
        }
        report_path = self._write_json("grype.json", report)
        output_path = self.base_path / "result.json"

        build_vuln_input.build_input(
            grype_report=report_path,
            output_path=output_path,
            cvss_threshold=8.5,
            epss_threshold=0.6,
            vex_json=None,
        )

        payload = json.loads(output_path.read_text())
        self.assertEqual(payload["policy"]["cvss_threshold"], 8.5)
        self.assertEqual(payload["policy"]["epss_threshold"], 0.6)
        vulnerabilities = payload["vulnerabilities"]
        self.assertEqual([item["id"] for item in vulnerabilities], ["CVE-0001", "CVE-0002"])
        self.assertAlmostEqual(vulnerabilities[0]["cvss"], 9.3)
        self.assertAlmostEqual(vulnerabilities[0]["epss_percentile"], 0.9)
        self.assertAlmostEqual(vulnerabilities[1]["cvss"], 5.0)
        self.assertAlmostEqual(vulnerabilities[1]["epss_percentile"], 0.65)
        self.assertEqual(payload["vex"], [])

    def test_normalizes_vex_documents_with_varied_shapes(self) -> None:
        report_path = self._write_json("grype.json", {"matches": []})
        vex_document = {
            "statements": [
                {"id": "CVE-0001", "status": "NOT_AFFECTED"},
                {
                    "vulnerability": {"id": "CVE-0002"},
                    "analysis": {"state": "Fixed"},
                },
                {
                    "vulnerability": {"id": "CVE-0003"},
                    "analysis": {"state": " Under Investigation "},
                },
                {"id": "CVE-0004", "status": "notaffected"},
                {"status": "ignored"},
            ]
        }
        vex_path = self._write_json("evidence.vex.json", vex_document)
        output_path = self.base_path / "vex_result.json"

        build_vuln_input.build_input(
            grype_report=report_path,
            output_path=output_path,
            cvss_threshold=7.0,
            epss_threshold=0.7,
            vex_json=vex_path,
        )

        payload = json.loads(output_path.read_text())
        self.assertEqual(
            payload["vex"],
            [
                {"id": "CVE-0001", "status": "not_affected"},
                {"id": "CVE-0002", "status": "fixed"},
                {"id": "CVE-0003", "status": "under_investigation"},
                {"id": "CVE-0004", "status": "not_affected"},
            ],
        )

    def test_epss_percentile_filters_out_of_range_values(self) -> None:
        report = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-0100",
                        "severity": "critical",
                        "cvss": [{"metrics": {"baseScore": "n/a"}}],
                    },
                    "metadata": {"epss": {"percentile": 150}},
                    "epss": {"percentile": 0.81},
                    "relatedVulnerabilities": [
                        {
                            "cvss": [{"metrics": {"baseScore": "?"}}],
                            "metadata": {"epss": {"percentile": 82}},
                        },
                        {
                            "metadata": {"epss": {"percentile": -5}},
                        },
                    ],
                }
            ]
        }
        report_path = self._write_json("epss.json", report)
        output_path = self.base_path / "epss_result.json"

        build_vuln_input.build_input(
            grype_report=report_path,
            output_path=output_path,
            cvss_threshold=9.0,
            epss_threshold=0.5,
            vex_json=None,
        )

        payload = json.loads(output_path.read_text())
        vuln = payload["vulnerabilities"][0]
        self.assertEqual(vuln["id"], "CVE-0100")
        self.assertAlmostEqual(vuln["cvss"], 10.0)  # severity fallback
        self.assertAlmostEqual(vuln["epss_percentile"], 0.82)

    def test_vex_vulnerabilities_section_is_normalized(self) -> None:
        report_path = self._write_json("grype.json", {"matches": []})
        vex_document = {
            "vulnerabilities": [
                {"id": "CVE-010", "status": "In-Progress"},
                {"id": "CVE-011", "analysis": {"state": "Fixed"}},
                {"id": "CVE-012", "analysis": {"state": "NOT affected"}},
                {"status": "Ignored"},
            ]
        }
        vex_path = self._write_json("vuln-section.vex.json", vex_document)
        output_path = self.base_path / "vuln_section.json"

        build_vuln_input.build_input(
            grype_report=report_path,
            output_path=output_path,
            cvss_threshold=7.0,
            epss_threshold=0.7,
            vex_json=vex_path,
        )

        payload = json.loads(output_path.read_text())
        self.assertEqual(
            payload["vex"],
            [
                {"id": "CVE-010", "status": "in_progress"},
                {"id": "CVE-011", "status": "fixed"},
                {"id": "CVE-012", "status": "not_affected"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
