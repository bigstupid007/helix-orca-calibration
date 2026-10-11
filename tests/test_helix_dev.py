import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("helix_dev", ROOT / "scripts" / "helix_dev.py")
helix_dev = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(helix_dev)


class HelixDevContractTests(unittest.TestCase):
    def test_runtime_and_source_are_pinned(self):
        self.assertEqual(helix_dev.HELIX_TAG, "v1.1.0-beta.4")
        self.assertEqual(len(helix_dev.HELIX_SOURCE_COMMIT), 40)
        self.assertEqual(len(helix_dev.HELIX_ARTIFACT_BINARY_SHA256), 64)
        self.assertEqual(len(helix_dev.HELIX_RELEASE_SHA256), 64)
        self.assertIsInstance(helix_dev.HELIX_ARTIFACT_ID, int)
        self.assertEqual(helix_dev.HELIX_SUBMODULE_COUNT, 14)
        self.assertTrue(helix_dev.BUILDER_DOCKERFILE.is_file())

    def test_matrix_is_the_verified_eleven_target_union(self):
        observed = {
            (width, height, layout, dpi)
            for _label, width, height, layout, dpi in helix_dev.VIEWPORTS
        }
        expected = {
            (480, 272, "standard", 160),
            (272, 480, "portrait", 160),
            (480, 320, "standard", 160),
            (480, 400, "standard", 160),
            (800, 480, "standard", 160),
            (480, 800, "portrait", 160),
            (1024, 600, "standard", 160),
            (1280, 720, "standard", 160),
            (1080, 2400, "portrait", 405),
            (1920, 480, "ultrawide", 160),
            (320, 1480, "portrait", 160),
        }
        self.assertEqual(observed, expected)
        self.assertEqual(len(helix_dev.VIEWPORTS), 11)

    def test_review_listener_matches_canonical_registry(self):
        self.assertEqual(helix_dev.REVIEW_BIND, "0.0.0.0")
        self.assertEqual(helix_dev.REVIEW_HOST, "192.168.1.114")
        self.assertEqual(helix_dev.REVIEW_PORT, 8540)
        self.assertEqual(helix_dev.CONTAINER, "helix-orca-dev")

    def test_durable_cache_and_state_do_not_depend_on_tmp(self):
        with mock.patch.dict(
            helix_dev.os.environ,
            {"XDG_CACHE_HOME": "/cache", "XDG_STATE_HOME": "/state"},
            clear=False,
        ):
            self.assertEqual(
                helix_dev.cache_root(),
                Path("/cache/helix-orca-calibration/helixscreen/v1.1.0-beta.4"),
            )
            self.assertEqual(
                helix_dev.state_root(), Path("/state/helix-orca-calibration/helix-dev")
            )

    def test_container_is_mock_only_network_isolated_and_read_only(self):
        args = helix_dev._container_args(
            "contract-test", Path("/state/contract"), 800, 480, "standard", 160
        )
        joined = " ".join(args)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", args)
        self.assertIn("--test", args)
        self.assertNotIn("--real-moonraker", args)
        self.assertIn("HELIX_PLUGIN_DIR=/plugin", args)
        self.assertIn("HELIX_HOT_RELOAD=1", args)
        self.assertIn(f"{helix_dev.PLUGIN_ROOT}:/plugin:ro", args)

    def test_seed_enables_only_orcacal_and_places_accepted_tile(self):
        template = {
            "dark_mode": False,
            "plugins": {"enabled": []},
            "printers": {"default": {}},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template_path = root / "settings.json.template"
            template_path.write_text(json.dumps(template), encoding="utf-8")
            with mock.patch.object(helix_dev, "_template_path", return_value=template_path):
                output = helix_dev.seed_settings(root / "config")
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            result["plugins"]["enabled"],
            {"orcacal": {"permissions": [], "version": "0.2.0"}},
        )
        home = result["printers"]["default"]["panel_widgets"]["home"]
        self.assertEqual(home["main_page_index"], 1)
        self.assertEqual(home["pages"][1]["widgets"][0]["id"], "orcacal__tile")
        self.assertTrue(result["dark_mode"])
        self.assertEqual(result["tour"], {"completed": True, "last_seen_version": 1})

    def test_seed_refuses_to_replace_malformed_retained_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            (config / "settings-test.json").write_text("{", encoding="utf-8")
            with self.assertRaises(helix_dev.HarnessError):
                helix_dev.seed_settings(config)

    def test_tar_extraction_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unsafe.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                item = tarfile.TarInfo("../escape")
                item.size = 1
                bundle.addfile(item, io.BytesIO(b"x"))
            with self.assertRaises(helix_dev.HarnessError):
                helix_dev._safe_extract_tar(archive, root / "output")

    def test_docker_build_context_is_bounded_to_scripts(self):
        with mock.patch.object(helix_dev, "run") as run_mock, mock.patch.object(
            helix_dev, "image_metadata", return_value={"id": "image"}
        ):
            helix_dev.build_image()
        argv = run_mock.call_args.args[0]
        self.assertEqual(argv[-1], helix_dev.DOCKERFILE.parent)
        self.assertNotIn(helix_dev.PROJECT_ROOT, argv)
        self.assertIn("org.helixscreen.runtime.recipe.sha256=", " ".join(map(str, argv)))

    def test_source_build_cache_requires_matching_retained_builder(self):
        metadata = {
            "binary_origin": {
                "kind": "source-build",
                "builder_image_id": "sha256:expected",
            }
        }
        with mock.patch.object(
            helix_dev, "_builder_image_metadata", return_value={"id": "sha256:expected"}
        ):
            helix_dev.verify_source_builder(metadata)
        with mock.patch.object(
            helix_dev, "_builder_image_metadata", return_value={"id": "sha256:different"}
        ):
            with self.assertRaises(helix_dev.HarnessError):
                helix_dev.verify_source_builder(metadata)

    def test_capture_structure_requires_exact_matrix_and_candidate_hashes(self):
        results = []
        screenshots = {}
        for expected in helix_dev._expected_rows():
            row = dict(expected)
            row["assertions"] = list(helix_dev.EXPECTED_ASSERTIONS)
            results.append(row)
            for filename in helix_dev.CAPTURE_FRAME_NAMES:
                screenshots[f"{row['label']}/{filename}"] = "a" * 64
        report = {
            "candidate_files": helix_dev._candidate_hashes(),
            "container_network": "none",
            "image": helix_dev.IMAGE,
            "plugin_files_before_and_after": helix_dev._plugin_hashes(),
            "results": results,
            "runtime": {
                "binary_origin": {"kind": "source-build"},
                "release_archive_sha256": helix_dev.HELIX_RELEASE_SHA256,
                "source_commit": helix_dev.HELIX_SOURCE_COMMIT,
                "tag": helix_dev.HELIX_TAG,
                "tag_object": helix_dev.HELIX_TAG_OBJECT,
            },
            "screenshots": screenshots,
        }
        helix_dev._validate_report_structure(report, helix_dev._matrix_text(results))
        report["results"][0]["label"] = "wrong"
        with self.assertRaises(helix_dev.HarnessError):
            helix_dev._validate_report_structure(report, helix_dev._matrix_text(results))

    def test_geometry_assertion_rejects_horizontal_overflow(self):
        fitting = {
            "widgets": [
                {"name": "ok", "x": 0, "y": 0, "w": 480, "h": 30, "scroll": {}}
            ]
        }
        helix_dev._assert_horizontal_fit(fitting, 480)
        overflowing = {
            "widgets": [
                {"name": "bad", "x": 20, "y": 0, "w": 480, "h": 30, "scroll": {}}
            ]
        }
        with self.assertRaises(helix_dev.HarnessError):
            helix_dev._assert_horizontal_fit(overflowing, 480)

    def test_overlay_assertion_requires_exact_native_stack(self):
        helix_dev._assert_overlay(
            {"overlays": ["orcacal__wizard", "orcacal__temperature"]},
            ["orcacal__wizard", "orcacal__temperature"],
        )
        with self.assertRaises(helix_dev.HarnessError):
            helix_dev._assert_overlay(
                {"overlays": ["orcacal__temperature"]},
                ["orcacal__wizard", "orcacal__temperature"],
            )

    def test_viewer_labels_native_pixels_and_uses_native_input_endpoints(self):
        page = helix_dev.VIEWER_HTML
        self.assertIn("Real HelixScreen beta.4 mock", page)
        self.assertIn("/frame.png", page)
        self.assertIn("/api/tap", page)
        self.assertIn('data-action="back"', page)
        self.assertIn("'/api/'+button.dataset.action", page)
        self.assertNotIn("Moonraker", page)

    def test_cli_exposes_bounded_issue_two_commands(self):
        commands = helix_dev.parser()._subparsers._group_actions[0].choices
        self.assertTrue(
            {
                "bootstrap",
                "up",
                "status",
                "down",
                "reload",
                "capture",
                "promote",
                "verify-evidence",
                "doctor",
            }.issubset(commands)
        )


if __name__ == "__main__":
    unittest.main()
