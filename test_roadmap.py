"""Offline, stdlib-only checks for the roadmap's active guidance and agent."""
import copy
import importlib.util
import io
import json
import logging
from pathlib import Path
import re
import socket
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack
from unittest import mock
from urllib.error import URLError


ROOT = Path(__file__).resolve().parent
AUTHORITY = (
    "https://github.com/kody-w/rapp-1/blob/"
    "eb50008011447f5e69372ac22a1755f0978d15ed/SPEC.md"
)
RETIRED = re.compile(r"\brapp-(?:frame|egg)/[0-9]+(?:\.[0-9]+)*")
FRAME = re.compile(r"\brapp/1(?![-\w./])")
COLLISION_RECORD = (
    "\u2705 DONE 2026-06-28 \u2014 Fixed the rapp-frame schema-id collision: "
    "bumped to rapp-frame/2.0, unifying the kernel's Dream-Catcher memory-frame "
    "+ the swarm wire as one kind-discriminated family (memory.*/swarm.*); "
    "sig made optional."
)


def read_roadmap():
    return json.loads((ROOT / "roadmap.json").read_text(encoding="utf-8"))


def active_data(document):
    active = {
        key: value for key, value in document.items()
        if not (
            key in ("architecture", "grounding")
            and isinstance(value, dict)
            and value.get("status") == "historical"
        )
    }
    if document.get("spec") == "rapp-backlog/1.0":
        active["wrenches"] = [
            {key: value for key, value in item.items() if key != "scenario"}
            if item.get("scenario_status") == "historical" else item
            for item in document["wrenches"]
        ]
    return active


class RoadmapDataTests(unittest.TestCase):
    def test_all_machine_readable_files_have_no_active_retired_formats(self):
        files = sorted(ROOT.rglob("*.json"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsNone(
                    RETIRED.search(json.dumps(active_data(document))),
                    "retired format in active guidance: " + path.name,
                )

    def test_current_guidance_uses_the_accepted_frame_and_egg_forms(self):
        roadmap = read_roadmap()
        self.assertEqual(roadmap.get("format_authority"), AUTHORITY)
        for text in (
            roadmap["the_medium"],
            roadmap["phases"][0]["theme"],
            " ".join(roadmap["phases"][0]["items"]),
            " ".join(roadmap["phases"][3]["items"]),
        ):
            with self.subTest(text=text[:80]):
                self.assertRegex(text, FRAME)
                self.assertIn("rapp/1-egg", text)
                self.assertIn("variant", text)
                self.assertNotIn("scale field", text)
                self.assertNotIn("`scale`", text)

    def test_historical_evidence_is_labeled_and_preserved(self):
        roadmap = read_roadmap()
        for key in ("architecture", "grounding"):
            self.assertEqual(roadmap[key].get("status"), "historical")
            self.assertIn("not current", roadmap[key]["note"])
        self.assertEqual(
            roadmap["grounding"]["phase_0_frame_collision"], COLLISION_RECORD
        )
        self.assertEqual(
            roadmap["architecture"]["pillars"][2]["spec"], "rapp-frame/1.0"
        )
        self.assertIn("rapp-egg/2.0", json.dumps(roadmap["grounding"]))
        self.assertNotIn(COLLISION_RECORD, roadmap["phases"][0]["items"])
        backlog = json.loads((ROOT / "backlog.json").read_text(encoding="utf-8"))
        historical = [
            item for item in backlog["wrenches"]
            if item.get("scenario_status") == "historical"
        ]
        self.assertEqual(len(historical), 2)
        for item in historical:
            self.assertIn("not current", item["scenario_note"])
            self.assertIn("rapp-frame/1.0", item["scenario"])

    def test_active_documentation_agrees_with_machine_guidance(self):
        for name in ("README.md", "ROADMAP.md"):
            with self.subTest(name=name):
                active_lines = []
                historical = False
                for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
                    if line.startswith("## "):
                        historical = line.startswith("## Historical ")
                    if not historical:
                        active_lines.append(line)
                active = "\n".join(active_lines)
                self.assertIsNone(
                    RETIRED.search(active), "retired format in active " + name
                )
                self.assertRegex(active, FRAME)
                self.assertIn("rapp/1-egg", active)
                self.assertIn(AUTHORITY, active)

    def test_static_page_reads_the_canonical_json_without_a_format_copy(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('getJSON("roadmap.json")', page)
        self.assertIn('getJSON("board.json")', page)
        self.assertIn("ROADMAP.phases", page)
        self.assertIn("esc(p.theme", page)
        self.assertRegex(read_roadmap()["phases"][0]["theme"], FRAME)
        self.assertIn("rapp/1-egg", read_roadmap()["phases"][0]["theme"])
        self.assertNotRegex(page, RETIRED)


class RoadmapAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class BasicAgentStub:
            def __init__(self, name, metadata):
                self.name = name
                self.metadata = metadata

        package = types.ModuleType("agents")
        basic_agent = types.ModuleType("agents.basic_agent")
        basic_agent.BasicAgent = BasicAgentStub
        spec = importlib.util.spec_from_file_location(
            "roadmap_under_test", ROOT / "rapp_roadmap_agent.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                socket.socket, "connect", side_effect=AssertionError("network forbidden")
            ))
            stack.enter_context(mock.patch(
                "urllib.request.urlopen", side_effect=AssertionError("network forbidden")
            ))
            stack.enter_context(mock.patch.dict(
                sys.modules, {"agents": package, "agents.basic_agent": basic_agent}
            ))
            spec.loader.exec_module(cls.module)

    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        directory = stack.enter_context(
            tempfile.TemporaryDirectory(prefix=".roadmap-test-", dir=ROOT)
        )
        self.cache = Path(directory) / "cache.json"
        stack.enter_context(mock.patch.object(self.module, "CACHE", str(self.cache)))
        stack.enter_context(mock.patch.object(
            self.module, "HEADS", ["https://first.invalid", "https://second.invalid"]
        ))
        self.urlopen = stack.enter_context(mock.patch.object(
            self.module.urllib.request, "urlopen", side_effect=URLError("offline test")
        ))
        stack.enter_context(mock.patch.object(
            socket.socket, "connect", side_effect=AssertionError("network forbidden")
        ))
        self.warning = stack.enter_context(mock.patch.object(
            logging.getLogger(self.module.__name__), "warning"
        ))
        self.roadmap = read_roadmap()
        self.agent = self.module.RappRoadmapAgent()

    def cache_roadmap(self, roadmap):
        self.cache.write_text(
            json.dumps({"at": 0, "head": "test", "roadmap": roadmap}),
            encoding="utf-8",
        )

    def serve(self, roadmap):
        self.urlopen.side_effect = lambda *args, **kwargs: io.BytesIO(
            json.dumps(roadmap).encode("utf-8")
        )

    def response(self, **kwargs):
        response = json.loads(self.agent.perform(**kwargs))
        self.assertIsNone(
            RETIRED.search(json.dumps(response)), "retired format in agent response"
        )
        return response

    def test_live_fetch_caches_current_guidance(self):
        self.serve(self.roadmap)
        response = self.response(action="the_medium")
        self.assertEqual(response["the_medium"], self.roadmap["the_medium"])
        self.assertRegex(response["the_medium"], FRAME)
        self.assertIn("rapp/1-egg", response["the_medium"])
        self.assertEqual(response["via"], self.module.HEADS[0])
        cached = json.loads(self.cache.read_text(encoding="utf-8"))
        self.assertEqual(cached["roadmap"], self.roadmap)
        self.assertEqual(cached["head"], self.module.HEADS[0])

    def test_offline_cache_preserves_all_action_responses(self):
        self.cache_roadmap(self.roadmap)
        for action, key in (
            ("north_star", "north_star"),
            ("the_medium", "the_medium"),
            ("hero_use_cases", "hero_use_cases"),
        ):
            with self.subTest(action=action):
                response = self.response(action=action)
                self.assertEqual(response[key], self.roadmap[key])
                self.assertEqual(response["via"], "cache (offline)")
        phase = self.response(action="phase")
        self.assertEqual(phase["phase"], self.roadmap["phases"][0])
        refreshed = self.response(action="refresh")
        self.assertTrue(refreshed["ok"])
        self.assertEqual(refreshed["refreshed_from"], "cache (offline)")
        self.assertEqual(refreshed["north_star"], self.roadmap["north_star"])

    def test_phase_selection_and_guidance_use_canonical_title_and_items(self):
        self.cache_roadmap(self.roadmap)
        expected = self.roadmap["phases"][3]
        phase = self.response(action="phase", name="MESH")
        self.assertEqual(phase["phase"], expected)
        guidance = self.response(
            action="guidance", situation="neighborhood estate variant"
        )
        self.assertEqual(guidance["fits_phase"], expected["title"])
        self.assertEqual(guidance["items"], expected["items"])
        self.assertIn("rapp/1-egg", json.dumps(guidance))

    def test_system_context_reads_only_the_local_current_cache(self):
        self.cache_roadmap(self.roadmap)
        context = self.agent.system_context()
        self.assertEqual(
            context, "North star (RAPP roadmap): " + self.roadmap["north_star"]
        )
        self.assertNotRegex(context, RETIRED)
        self.urlopen.assert_not_called()

    def test_stale_heads_cannot_overwrite_a_current_cache(self):
        self.cache_roadmap(self.roadmap)
        before = self.cache.read_bytes()
        stale = copy.deepcopy(self.roadmap)
        stale["the_medium"] = "Use rapp-frame/2.0 and rapp-egg/2.0 scale field."
        self.serve(stale)
        response = self.response(action="the_medium")
        self.assertEqual(response["the_medium"], self.roadmap["the_medium"])
        self.assertEqual(response["via"], "cache (offline)")
        self.assertEqual(self.cache.read_bytes(), before)
        self.assertTrue(self.warning.called)

    def test_stale_head_is_skipped_for_a_current_head(self):
        stale = copy.deepcopy(self.roadmap)
        stale["phases"][3]["items"].append("Publish rapp-egg/2.0 eggs.")
        self.urlopen.side_effect = [
            io.BytesIO(json.dumps(stale).encode("utf-8")),
            io.BytesIO(json.dumps(self.roadmap).encode("utf-8")),
        ]
        response = self.response(action="the_medium")
        self.assertEqual(response["via"], self.module.HEADS[1])
        self.assertEqual(
            json.loads(self.cache.read_text(encoding="utf-8"))["roadmap"],
            self.roadmap,
        )
        self.assertTrue(self.warning.called)

    def test_stale_cache_is_not_served_or_used_as_system_context(self):
        for token in ("rapp-frame/1.0", "rapp-frame/2.0", "rapp-frame/2.1", "rapp-egg/2.0"):
            with self.subTest(token=token):
                stale = copy.deepcopy(self.roadmap)
                stale["productization_checklist"].append("Use " + token)
                self.cache_roadmap(stale)
                before = self.cache.read_bytes()
                response = self.response(action="the_medium")
                self.assertFalse(response["ok"])
                self.assertIn("current", response["error"])
                self.assertEqual(self.agent.system_context(), "")
                self.assertEqual(self.cache.read_bytes(), before)
                self.assertTrue(self.warning.called)

    def test_unlabeled_history_is_not_exempt_from_validation(self):
        for key in ("architecture", "grounding"):
            with self.subTest(key=key):
                unlabeled = copy.deepcopy(self.roadmap)
                unlabeled[key].pop("status", None)
                self.serve(unlabeled)
                self.assertFalse(self.response(action="the_medium")["ok"])
                self.assertFalse(self.cache.exists())

    def test_historical_label_cannot_hide_retired_active_phase_guidance(self):
        stale = copy.deepcopy(self.roadmap)
        stale["phases"][0]["status"] = "historical"
        stale["phases"][0]["items"].append("Use rapp-frame/2.0.")
        self.serve(stale)
        self.assertFalse(self.response(action="phase")["ok"])
        self.assertFalse(self.cache.exists())

    def test_both_current_format_tokens_are_required(self):
        for medium in ("Use rapp/1-egg with variant.", "Use rapp/1 frames.", None):
            with self.subTest(medium=medium):
                incomplete = copy.deepcopy(self.roadmap)
                incomplete["the_medium"] = medium
                self.serve(incomplete)
                self.assertFalse(self.response(action="the_medium")["ok"])
                self.assertFalse(self.cache.exists())

    def test_missing_or_malformed_cache_fails_explicitly(self):
        self.assertFalse(self.response(action="north_star")["ok"])
        for content in ("{", "[]", '{"roadmap": null}', '{"roadmap": {}}'):
            with self.subTest(content=content):
                self.cache.write_text(content, encoding="utf-8")
                self.assertFalse(self.response(action="north_star")["ok"])
                self.assertEqual(self.agent.system_context(), "")
                self.assertTrue(self.warning.called)

    def test_malformed_heads_fall_back_to_current_cache(self):
        self.cache_roadmap(self.roadmap)
        self.urlopen.side_effect = [
            io.BytesIO(b"{"),
            io.BytesIO(b"[]"),
        ]
        response = self.response(action="the_medium")
        self.assertEqual(response["via"], "cache (offline)")
        self.assertEqual(response["the_medium"], self.roadmap["the_medium"])

    def test_cache_write_failure_does_not_hide_current_network_guidance(self):
        self.serve(self.roadmap)
        with mock.patch.object(self.module, "CACHE", str(self.cache.parent)):
            response = self.response(action="the_medium")
        self.assertEqual(response["the_medium"], self.roadmap["the_medium"])
        self.assertEqual(response["via"], self.module.HEADS[0])
        self.assertTrue(self.warning.called)


if __name__ == "__main__":
    unittest.main()
