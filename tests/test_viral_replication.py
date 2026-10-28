import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "baoliangxia-viral-replication" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _viral import validate_request, validate_key
from query_viral_replication import collect_outputs


class ViralReplicationTests(unittest.TestCase):
    def test_image_and_video_use_distinct_payloads(self):
        image = {
            "type": "image", "sourceImage": {"uploadId": "upl_source"},
            "requirement": "替换产品", "count": 2, "ratio": "1:1",
            "imageModel": "doubao-seedream-4.5",
        }
        video = {
            "type": "video", "sourceVideo": {"uploadId": "upl_video"},
            "productDescription": "产品广告", "count": 20,
            "videoModel": "doubao-seedance-2.0", "replicationMode": "full",
        }
        self.assertIs(validate_request(image), image)
        self.assertIs(validate_request(video), video)
        with self.assertRaisesRegex(ValueError, "unsupported field"):
            validate_request({**image, "sourceVideo": {"uploadId": "upl_video"}})
        with self.assertRaisesRegex(ValueError, "1 to 20"):
            validate_request({**video, "count": 21})
        with self.assertRaisesRegex(ValueError, "sourceVideo"):
            validate_request({**video, "sourceVideo": "https://example.com/video.mp4"})
        with self.assertRaisesRegex(ValueError, "type must"):
            validate_request({**image, "type": ["image"]})
        with self.assertRaisesRegex(ValueError, "sourceVideoMetadata"):
            validate_request({**video, "sourceVideoMetadata": {"durationSeconds": float("nan")}})

    def test_dry_run_needs_no_key_and_does_not_send(self):
        body = {
            "type": "image", "sourceImage": {"uploadId": "upl_source"},
            "requirement": "替换产品", "count": 1, "ratio": "1:1",
            "imageModel": "doubao-seedream-4.5",
        }
        with tempfile.TemporaryDirectory() as directory:
            request_file = Path(directory) / "request.json"
            request_file.write_text(json.dumps(body), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPTS / "create_viral_replication.py"),
                 "--request-file", str(request_file), "--idempotency-key", "12345678", "--dry-run"],
                capture_output=True, text=True, check=True,
                env={**os.environ, "BAOLIANGXIA_AGENT_GATEWAY_BASE_URL": "https://example.test",
                     "BAOLIANGXIA_AGENT_GATEWAY_API_KEY": "", "PYTHONUTF8": "1"},
            )
        result = json.loads(process.stdout)
        self.assertEqual(result["url"], "https://example.test/api/v1/viral-replications")
        self.assertEqual(result["body"], body)
        self.assertTrue(result["dryRun"])
        with self.assertRaises(ValueError):
            validate_key("short")

    def test_query_collects_stable_cursor_pages(self):
        first = {"outputs": [{"url": "https://example.test/one"}], "nextCursor": "page-2"}
        with patch("query_viral_replication.fetch_page", return_value={"outputs": [{"url": "https://example.test/two"}], "nextCursor": None}) as fetch:
            outputs = collect_outputs("https://example.test/api/v1/viral-replications/batch", first)
        self.assertEqual(len(outputs), 2)
        fetch.assert_called_once_with("https://example.test/api/v1/viral-replications/batch", "page-2")


if __name__ == "__main__":
    unittest.main()
