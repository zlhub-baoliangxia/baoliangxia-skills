import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "baoliangxia-skills" / "scripts"))

from create_batch_generations import build_parser as build_batch_parser, prepare_jobs
from create_model_generation import parse_args, prepare_generation
from _batch import initial_tasks
from _models import MODELS


class GatewayOptionTests(unittest.TestCase):
    def test_repeated_reference_audio_and_boolean_options(self):
        args = parse_args([
            "展示", "--model", "wan3.0-video",
            "--reference-audio-id", "upl_a", "--reference-audio-id", "upl_b",
            "--option", "audio=false", "--watermark", "true", "--dry-run",
        ])
        _spec, payload = prepare_generation(args)
        self.assertEqual(payload["referenceAudios"], [{"uploadId": "upl_a"}, {"uploadId": "upl_b"}])
        self.assertEqual(payload["options"], {"audio": False, "watermark": True})

    def test_rejects_duplicate_unknown_and_colliding_options(self):
        cases = [
            ["--option", "audio=true", "--option", "audio=false"],
            ["--option", "notASetting=true"],
            ["--option", "watermark=false", "--watermark", "true"],
        ]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError):
                prepare_generation(parse_args(["p", "--model", "wan3.0-video", *options]))

    def test_audio_limit_and_legacy_flag_exclusion(self):
        args = parse_args([
            "p", "--model", "doubao-seedance-2.0",
            "--reference-audio-id", "a", "--reference-audio-id", "b",
        ])
        with self.assertRaises(ValueError):
            prepare_generation(args)

        args = parse_args(["p", "--model", "MiniMax-H3", "--duration", "5",
                           "--reference-audio-id", "a", "--reference-audio-id", "b",
                           "--reference-audio-id", "c"])
        _spec, payload = prepare_generation(args)
        self.assertEqual(len(payload["referenceAudios"]), 3)
        args.reference_audio_id.append("d")
        with self.assertRaises(ValueError):
            prepare_generation(args)

    def test_rejects_invalid_option_values_and_only_exposes_declared_models(self):
        invalid = [
            ("wan3.0-video", ["--option", "audio=1"]),
            ("kling-v3-omni", ["--option", "mode=turbo"]),
            ("doubao-seedream-5.0-lite", ["--option", "audio=true"]),
            ("zl-ooe-3.1-flash-image-t", ["--watermark", "true"]),
        ]
        for model, flags in invalid:
            with self.subTest(model=model, flags=flags), self.assertRaises(ValueError):
                prepare_generation(parse_args(["p", "--model", model, *flags]))
        args = parse_args(["p", "--model", "wan3.0-video", "--audio-upload-id", "old", "--reference-audio-id", "new"])
        with self.assertRaises(ValueError):
            prepare_generation(args)

    def test_batch_jobs_file_keeps_new_payload_fields_in_retries(self):
        row = [{
            "prompt": "p", "model": "wan3.0-video", "reference_audio_id": ["a", "b"],
            "options": {"audio": False, "watermark": True}, "count": 2,
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            path.write_text(json.dumps(row), encoding="utf-8")
            parser = build_batch_parser()
            parser.add_argument('--count', type=int, default=1)
            parser.add_argument('--jobs-file')
            parser.add_argument('--output-dir')
            parser.add_argument('--concurrency', type=int, default=5)
            parser.add_argument('--interval', type=float, default=20)
            parser.add_argument('--timeout', type=float, default=21600)
            args = parser.parse_args(["--jobs-file", str(path)])
            jobs = prepare_jobs(args)
            mixed = parser.parse_args(["--jobs-file", str(path), "--option", "audio=false"])
            with self.assertRaises(ValueError):
                prepare_jobs(mixed)
        self.assertEqual(jobs[0]["payload"]["referenceAudios"], [{"uploadId": "a"}, {"uploadId": "b"}])
        self.assertEqual(jobs[0]["payload"]["options"], {"audio": False, "watermark": True})
        tasks = initial_tasks(jobs)
        self.assertEqual(tasks[0]["payload"]["options"], jobs[0]["payload"]["options"])
        self.assertEqual(tasks[1]["payload"]["referenceAudios"], jobs[0]["payload"]["referenceAudios"])

    def test_gateway_catalog_model_ids_and_option_defaults(self):
        for model in ("zl-pep-image-2.5-flare-async", "zl-pep-image-2.5-sunburst-async"):
            _spec, payload = prepare_generation(parse_args(["p", "--model", model]))
            self.assertEqual(payload["options"]["quality"], "auto")
            self.assertEqual(payload["options"]["background"], "auto")
        _spec, nano = prepare_generation(parse_args(["p", "--model", "zl-ooe-3.1-flash-image-t"]))
        self.assertEqual(nano["options"]["imageSize"], "2K")
        self.assertFalse(MODELS["zl-pep-image-2.5-flare-async"].max_outputs)

    def test_output_duration_is_at_most_15_seconds(self):
        models = (
            "doubao-seedance-2.0", "doubao-seedance-2.0-fast", "doubao-seedance-2.0-mini",
            "happyhorse-1.1", "jielan-video", "jielan-video-lite", "jielan-video-mini",
        )
        for model in models:
            with self.subTest(model=model):
                self.assertEqual(MODELS[model].duration_max, 15)
                _spec, payload = prepare_generation(parse_args(["p", "--model", model, "--duration", "15"]))
                self.assertEqual(payload["duration"], 15)
                with self.assertRaisesRegex(ValueError, "at most 15"):
                    prepare_generation(parse_args(["p", "--model", model, "--duration", "16"]))

    def test_model_specific_options_and_defaults(self):
        cases = [
            ("doubao-seedream-4.5", ["--watermark", "true"], {"watermark": True}),
            ("zl-pep-image-2-async", ["--option", "quality=high", "--option", "background=opaque"],
             {"quality": "high", "background": "opaque"}),
            ("doubao-seedance-2.0", ["--option", "generate_audio=false"], {"generate_audio": False, "watermark": False}),
            ("doubao-seedance-2.5", ["--reference-video-id", "v", "--option", "omni_reference_task_type=edit"],
             {"generate_audio": True, "omni_reference_task_type": "edit", "watermark": False}),
            ("kling-v3-omni", ["--option", "mode=4k", "--option", "sound=on"],
             {"mode": "4k", "sound": "on", "watermark": False}),
        ]
        for model, flags, expected in cases:
            with self.subTest(model=model):
                _spec, payload = prepare_generation(parse_args(["p", "--model", model, *flags]))
                self.assertEqual(payload["options"], expected)


if __name__ == "__main__":
    unittest.main()
