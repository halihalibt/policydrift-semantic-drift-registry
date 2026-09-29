"""Deterministic and adversarial tests with a minimal GenLayer host boundary."""

import importlib.util
import json
import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).parents[1] / "contracts" / "semantic_drift_registry.py"


class Address(str):
    def __format__(self, spec):
        if spec == "x":
            return str(self)
        return super().__format__(spec)


class FakeTreeMap(dict):
    @classmethod
    def __class_getitem__(cls, _args):
        return cls

    def get_or_insert_default(self, key):
        if key not in self:
            self[key] = []
        return self[key]


class FakeDynArray(list):
    @classmethod
    def __class_getitem__(cls, _args):
        return cls


class FakeContract:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for key, value in cls.__annotations__.items():
            if value is FakeTreeMap:
                setattr(instance, key, FakeTreeMap())
        return instance


class Return:
    def __init__(self, calldata):
        self.calldata = calldata


class FakeVM:
    Result = Return
    Return = Return

    def run_nondet_unsafe(self, leader_fn, validator_fn):
        result = leader_fn()
        if not validator_fn(Return(result)):
            raise RuntimeError("validator rejected")
        return result


class FakeNondet:
    def __init__(self):
        self.body = b""
        self.status = 200
        self.web_calls = 0
        self.llm_calls = 0
        self.current_state = None
        self.delta = None
        self.invalid_target = False
        self.web_raises = False
        self.leader_payload_override = None
        self.extract_calls = 0
        self.semantic_equivalence = dict.fromkeys(("conditions", "scope", "exceptions", "quantitative_terms"), True)

    class Web:
        def __init__(self, outer):
            self.outer = outer

        def get(self, _url):
            self.outer.web_calls += 1
            if self.outer.web_raises:
                raise RuntimeError("simulated transport failure")
            return types.SimpleNamespace(status=self.outer.status, body=self.outer.body)

    @property
    def web(self):
        return self.Web(self)

    def exec_prompt(self, prompt, response_format):
        assert response_format == "json"
        self.llm_calls += 1
        if "<untrusted_leader>" in prompt:
            return dict(self.semantic_equivalence)
        if "<untrusted_source>" not in prompt:
            return {"target_status": "INVALID" if self.invalid_target else "VALID"}
        drift = "<accepted_baseline>" in prompt
        present = self.current_state is not None
        state = self.current_state if present else {
            "presence": "NOT_STATED", "disposition": "NONE", "conditions": "NONE",
            "scope": "NONE", "exceptions": "NONE", "quantitative_terms": "NONE",
        }
        payload = {
            "schema_version": 1, "source_status": "OK", "current_state": dict(state),
            "evidence_excerpt": self.body.decode().split("\n")[0] if present else "",
        }
        if drift:
            payload["delta"] = self.delta or {key: "NOT_APPLICABLE" for key in ("conditions", "scope", "exceptions", "quantitative_terms")}
        else:
            payload["target_status"] = "VALID"
        self.extract_calls += 1
        if self.extract_calls % 2 == 1 and self.leader_payload_override:
            payload.update(self.leader_payload_override)
        return payload


def make_host():
    nondet = FakeNondet()
    vm = FakeVM()
    gl = types.SimpleNamespace(
        Contract=FakeContract,
        vm=vm,
        nondet=nondet,
        public=types.SimpleNamespace(write=lambda fn: fn, view=lambda fn: fn),
        message=types.SimpleNamespace(sender_address=Address("0xowner")),
    )
    genlayer = types.ModuleType("genlayer")
    genlayer.gl = gl
    genlayer.Address = Address
    genlayer.u8 = int
    genlayer.u32 = int
    genlayer.u256 = int
    genlayer.TreeMap = FakeTreeMap
    genlayer.DynArray = FakeDynArray
    genlayer.allow_storage = lambda obj: obj
    genlayer.__all__ = ["gl", "Address", "u8", "u32", "u256", "TreeMap", "DynArray", "allow_storage"]
    with patch.dict(sys.modules, {"genlayer": genlayer}):
        spec = importlib.util.spec_from_file_location("policy_drift_under_test", SOURCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return module, gl, nondet


def state(condition="Attribution is required.", disposition="ALLOWED"):
    return {
        "presence": "PRESENT", "disposition": disposition, "conditions": condition,
        "scope": "Third-party commercial API applications.",
        "exceptions": "NONE", "quantitative_terms": "NONE",
    }


def drift_payload(current=None, delta=None, quote="Policy quote."):
    return {
        "schema_version": 1, "source_status": "OK",
        "current_state": current or state(),
        "delta": delta or dict.fromkeys(("conditions", "scope", "exceptions", "quantitative_terms"), "SAME"),
        "evidence_excerpt": quote,
    }


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.m, self.gl, self.nondet = make_host()
        self.contract = self.m.SemanticDriftRegistry()
        self.nondet.current_state = state()
        self.nondet.body = b"Attribution is required.\nCommercial apps may use API data."
        self.clock = patch.object(self.m.time, "time", return_value=1000)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def register(self):
        return self.contract.register_watch("https://example.com/policy", "Can developers use API data commercially?")

    def test_register_and_independent_validation(self):
        watch_id = self.register()
        self.assertEqual(watch_id, 1)
        self.assertEqual(self.contract.get_protocol_version(), "PolicyDrift-V1.1-Studio")
        self.assertEqual(self.nondet.web_calls, 2)
        self.assertEqual(self.contract.get_watch_baseline_ids(watch_id), [1])
        self.assertEqual(self.contract.get_watch_count(), 1)
        self.assertEqual(self.contract.get_active_baseline(watch_id)["presence"], self.m.PRESENT)
        self.assertEqual(self.contract.get_active_baseline(watch_id)["origin_observation_id"], 0)
        self.assertEqual(self.contract.get_watch(watch_id)["owner"], "0xowner")

    def test_changed_condition_then_deduplicate_and_adopt(self):
        self.register()
        self.nondet.body = b"Prior written permission is required.\nCommercial apps may use API data."
        self.nondet.current_state = state("Prior written permission is required.")
        self.nondet.delta = dict(conditions="CHANGED", scope="SAME", exceptions="NOT_APPLICABLE", quantitative_terms="NOT_APPLICABLE")
        with patch.object(self.m.time, "time", return_value=2000):
            observation_id = self.contract.check_drift(1)
            self.assertEqual(self.contract.check_drift(1), observation_id)
            observation = self.contract.get_observation(observation_id)
            self.assertEqual(observation["verdict"], self.m.MATERIAL_DRIFT)
            self.assertEqual(observation["change_flags"], self.m.CONDITION_CHANGED)
            self.assertEqual(observation["checked_by"], "0xowner")
            self.assertEqual(self.contract.get_watch(1)["check_count"], 2)
            self.assertEqual(self.contract.get_watch_observation_ids(1), [1])
            baseline_id = self.contract.adopt_observation(1, observation_id)
        self.assertEqual(baseline_id, 2)
        self.assertEqual(self.contract.get_watch_baseline_ids(1), [1, 2])
        self.assertEqual(self.contract.get_baseline(1)["conditions"], "Attribution is required.")
        self.assertEqual(self.contract.get_baseline(2)["origin_observation_id"], observation_id)
        self.assertEqual(self.contract.get_active_baseline(1)["conditions"], "Prior written permission is required.")
        with self.assertRaisesRegex(ValueError, "PD009"):
            self.contract.adopt_observation(1, observation_id)

    def test_no_material_drift_and_disposition_flags(self):
        self.register()
        self.nondet.delta = dict(conditions="SAME", scope="SAME", exceptions="NOT_APPLICABLE", quantitative_terms="NOT_APPLICABLE")
        observation_id = self.contract.check_drift(1)
        self.assertEqual(self.contract.get_observation(observation_id)["verdict"], self.m.NO_MATERIAL_DRIFT)
        with self.assertRaisesRegex(ValueError, "PD008"):
            self.contract.adopt_observation(1, observation_id)
        self.nondet.current_state = state(disposition="PROHIBITED")
        next_id = self.contract.check_drift(1)
        self.assertEqual(self.contract.get_observation(next_id)["change_flags"], self.m.DISPOSITION_CHANGED)

    def test_rule_appeared_and_disappeared(self):
        self.nondet.current_state = None
        self.register()
        self.assertEqual(self.contract.get_baseline(1)["presence"], self.m.NOT_STATED)
        self.nondet.current_state = state()
        appeared = self.contract.check_drift(1)
        self.assertEqual(self.contract.get_observation(appeared)["change_flags"], self.m.RULE_APPEARED)
        self.contract.adopt_observation(1, appeared)
        self.nondet.current_state = None
        disappeared = self.contract.check_drift(1)
        self.assertEqual(self.contract.get_observation(disappeared)["change_flags"], self.m.RULE_DISAPPEARED)

    def test_rule_appeared_normalizes_independent_known_relations(self):
        self.nondet.current_state = None
        self.register()
        self.nondet.body = b"API data may not be used for AI model training."
        self.nondet.current_state = state("NONE", "PROHIBITED")
        self.nondet.current_state["scope"] = "Use of API data for AI model training"
        self.nondet.delta = dict(conditions="SAME", scope="SAME", exceptions="ADDED", quantitative_terms="CHANGED")
        # All leader labels are globally known; some are disallowed for these particular fields.
        self.nondet.leader_payload_override = {"delta": dict(
            conditions="REDUCED", scope="ADDED", exceptions="EXPANDED", quantitative_terms="REMOVED")}
        observation = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual((observation["verdict"], observation["change_flags"]),
                         (self.m.MATERIAL_DRIFT, self.m.RULE_APPEARED))
        self.assertEqual([observation[field] for field in (
            "condition_relation", "scope_relation", "exception_relation", "quantitative_relation")],
            [self.m.NOT_APPLICABLE] * 4)
        self.assertEqual(observation["current_scope"], "Use of API data for AI model training")
        self.assertEqual(self.nondet.web_calls, 4)  # Both leader and validator fetched independently.

    def test_rule_disappeared_normalizes_independent_known_relations(self):
        self.register()
        self.nondet.current_state = None
        self.nondet.delta = dict(conditions="SAME", scope="SAME", exceptions="SAME", quantitative_terms="SAME")
        self.nondet.leader_payload_override = {"delta": dict(
            conditions="EXPANDED", scope="REMOVED", exceptions="REDUCED", quantitative_terms="ADDED")}
        observation = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual((observation["verdict"], observation["change_flags"]),
                         (self.m.MATERIAL_DRIFT, self.m.RULE_DISAPPEARED))
        self.assertEqual([observation[field] for field in (
            "condition_relation", "scope_relation", "exception_relation", "quantitative_relation")],
            [self.m.NOT_APPLICABLE] * 4)
        self.assertEqual(observation["evidence_excerpt"], "")

    def test_presence_transition_ambiguous_relation_is_preserved(self):
        self.nondet.current_state = None
        self.register()
        self.nondet.current_state = state()
        self.nondet.delta = dict(conditions="SAME", scope="AMBIGUOUS", exceptions="SAME", quantitative_terms="SAME")
        self.nondet.leader_payload_override = {"delta": dict(
            conditions="REDUCED", scope="AMBIGUOUS", exceptions="EXPANDED", quantitative_terms="ADDED")}
        observation = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual((observation["verdict"], observation["change_flags"], observation["scope_relation"]),
                         (self.m.VERDICT_AMBIGUOUS, 0, self.m.RELATION_AMBIGUOUS))
        self.assertEqual(observation["condition_relation"], self.m.NOT_APPLICABLE)

        # A real ambiguity cannot be erased to agree with a definite relation.
        self.nondet.leader_payload_override = {"delta": dict(
            conditions="REDUCED", scope="SAME", exceptions="EXPANDED", quantitative_terms="ADDED")}
        with self.assertRaisesRegex(RuntimeError, "validator rejected"):
            self.contract.check_drift(1)
        self.assertEqual((self.contract.get_watch(1)["check_count"], self.contract.get_watch(1)["observation_count"]), (1, 1))

        # The reverse transition must also keep a genuine ambiguous relation.
        self.nondet.leader_payload_override = None
        self.nondet.current_state = state()
        reverse_watch = self.register()
        self.nondet.current_state = None
        self.nondet.delta = dict(conditions="SAME", scope="AMBIGUOUS", exceptions="SAME", quantitative_terms="SAME")
        self.nondet.leader_payload_override = {"delta": dict(
            conditions="REDUCED", scope="AMBIGUOUS", exceptions="EXPANDED", quantitative_terms="ADDED")}
        reverse = self.contract.get_observation(self.contract.check_drift(reverse_watch))
        self.assertEqual((reverse["verdict"], reverse["change_flags"], reverse["scope_relation"]),
                         (self.m.VERDICT_AMBIGUOUS, 0, self.m.RELATION_AMBIGUOUS))

    def test_404_is_unverifiable_not_disappearance(self):
        self.register()
        self.nondet.status = 404
        observation_id = self.contract.check_drift(1)
        observed = self.contract.get_observation(observation_id)
        self.assertEqual((observed["source_status"], observed["verdict"], observed["change_flags"]),
                         (self.m.SOURCE_UNAVAILABLE, self.m.UNVERIFIABLE, 0))
        self.assertEqual(observed["current_conditions"], "")
        with self.assertRaisesRegex(ValueError, "PD008"):
            self.contract.adopt_observation(1, observation_id)

    def test_transport_failure_is_independently_unverifiable(self):
        self.register()
        self.nondet.web_raises = True
        observation_id = self.contract.check_drift(1)
        observed = self.contract.get_observation(observation_id)
        self.assertEqual((observed["source_status"], observed["verdict"], observed["change_flags"]),
                         (self.m.SOURCE_UNAVAILABLE, self.m.UNVERIFIABLE, 0))
        self.assertEqual(self.nondet.web_calls, 4)

    def test_too_large_page_never_truncates_or_calls_llm(self):
        self.register()
        self.nondet.body = b"A" * 30001
        before = self.nondet.llm_calls
        observed = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual(observed["source_status"], self.m.SOURCE_TOO_LARGE)
        self.assertEqual(observed["verdict"], self.m.UNVERIFIABLE)
        self.assertEqual(self.nondet.llm_calls, before)

    def test_public_cooldown_and_owner_bypass(self):
        self.register()
        self.gl.message.sender_address = Address("0xpublic")
        self.contract.check_drift(1)
        with patch.object(self.m.time, "time", return_value=1050):
            with self.assertRaisesRegex(ValueError, "PD015"):
                self.contract.check_drift(1)
            self.gl.message.sender_address = Address("0xowner")
            self.contract.check_drift(1)
        with patch.object(self.m.time, "time", return_value=1951):
            self.gl.message.sender_address = Address("0xpublic")
            self.contract.check_drift(1)

    def test_owner_latest_and_cross_watch_guards(self):
        first = self.register()
        second = self.register()
        self.nondet.current_state = state("Prior written permission is required.")
        self.nondet.body = b"Prior written permission is required."
        self.nondet.delta = dict(conditions="CHANGED", scope="SAME", exceptions="NOT_APPLICABLE", quantitative_terms="NOT_APPLICABLE")
        observation = self.contract.check_drift(first)
        self.gl.message.sender_address = Address("0xpublic")
        with self.assertRaisesRegex(ValueError, "PD006"):
            self.contract.adopt_observation(first, observation)
        self.gl.message.sender_address = Address("0xowner")
        with self.assertRaisesRegex(ValueError, "PD007"):
            self.contract.adopt_observation(second, observation)
        self.nondet.current_state = None
        latest = self.contract.check_drift(first)
        self.assertNotEqual(latest, observation)
        with self.assertRaisesRegex(ValueError, "PD016"):
            self.contract.adopt_observation(first, observation)

    def test_strict_ccv_evidence_and_payload(self):
        base = state()
        leader = {"schema_version": 1, "target_status": "VALID", "source_status": "OK",
                  "current_state": base, "evidence_excerpt": "Attribution is required."}
        candidate = json.loads(json.dumps(leader))
        self.assertTrue(self.m._validate_independent(leader, candidate, "Attribution is required.", False))
        candidate["current_state"]["disposition"] = "REQUIRED"
        self.assertFalse(self.m._validate_independent(leader, candidate, "Attribution is required.", False))
        self.assertFalse(self.m._validate_independent(leader, leader, "No real quote here", False))
        bad = dict(leader, change_flags=8192)
        with self.assertRaisesRegex(ValueError, "PD011"):
            self.m._parse_extraction(bad, False)
        paraphrase = json.loads(json.dumps(leader))
        paraphrase["current_state"]["conditions"] = "Provide attribution."
        self.assertTrue(self.m._validate_independent(leader, paraphrase, "Attribution is required.", False))

    def test_transition_unknown_enum_bad_schema_and_types_fail_closed(self):
        present = state("NONE", "PROHIBITED")
        valid = drift_payload(present)
        cases = {}
        unknown = json.loads(json.dumps(valid))
        unknown["delta"]["scope"] = "MYSTERY"
        cases["unknown relation"] = unknown
        wrong_relation_type = json.loads(json.dumps(valid))
        wrong_relation_type["delta"]["scope"] = ["SAME"]
        cases["relation type"] = wrong_relation_type
        wrong_schema = json.loads(json.dumps(valid))
        wrong_schema["schema_version"] = 2
        cases["schema version"] = wrong_schema
        extra_key = json.loads(json.dumps(valid))
        extra_key["change_flags"] = 1
        cases["extra key"] = extra_key
        missing_key = json.loads(json.dumps(valid))
        del missing_key["delta"]["scope"]
        cases["missing delta key"] = missing_key
        wrong_status_type = json.loads(json.dumps(valid))
        wrong_status_type["source_status"] = ["OK"]
        cases["source status type"] = wrong_status_type
        wrong_presence_type = json.loads(json.dumps(valid))
        wrong_presence_type["current_state"]["presence"] = ["PRESENT"]
        cases["presence type"] = wrong_presence_type
        wrong_disposition = json.loads(json.dumps(valid))
        wrong_disposition["current_state"]["disposition"] = "NONE"
        cases["invalid present disposition"] = wrong_disposition
        wrong_field_type = json.loads(json.dumps(valid))
        wrong_field_type["current_state"]["scope"] = 123
        cases["semantic field type"] = wrong_field_type
        wrong_quote_type = json.loads(json.dumps(valid))
        wrong_quote_type["evidence_excerpt"] = None
        cases["evidence type"] = wrong_quote_type
        cases["non-object JSON result"] = "not a JSON object"
        for name, payload in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "PD011"):
                self.m._parse_extraction(payload, True, self.m.NOT_STATED)
        with self.assertRaisesRegex(ValueError, "PD011"):
            self.m._parse_extraction(valid, True)  # Never silently omit baseline context.

        # Malformed leader output cannot advance a registered Watch.
        self.nondet.current_state = None
        self.register()
        self.nondet.current_state = present
        self.nondet.leader_payload_override = {"delta": unknown["delta"]}
        with self.assertRaisesRegex(ValueError, "PD011"):
            self.contract.check_drift(1)
        self.assertEqual((self.contract.get_watch(1)["check_count"], self.contract.get_watch(1)["observation_count"]), (0, 0))

    def test_present_to_present_verdicts_and_exact_ccv_remain_strict(self):
        self.register()
        self.nondet.delta = dict.fromkeys(("conditions", "scope", "exceptions", "quantitative_terms"), "SAME")
        self.nondet.delta["conditions"] = "CHANGED"
        self.nondet.current_state = state("Prior written permission is required.")
        self.nondet.body = b"Prior written permission is required."
        changed = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual((changed["verdict"], changed["change_flags"], changed["condition_relation"]),
                         (self.m.MATERIAL_DRIFT, self.m.CONDITION_CHANGED, self.m.CHANGED))
        self.nondet.current_state = state()
        self.nondet.body = b"Attribution is required."
        self.nondet.delta["conditions"] = "SAME"
        same = self.contract.get_observation(self.contract.check_drift(1))
        self.assertEqual((same["verdict"], same["change_flags"]), (self.m.NO_MATERIAL_DRIFT, 0))

        leader = drift_payload(quote="Attribution is required.")
        candidate = json.loads(json.dumps(leader))
        candidate["delta"]["conditions"] = "CHANGED"
        self.assertFalse(self.m._validate_independent(leader, candidate, "Attribution is required.", True, self.m.PRESENT))
        invalid = json.loads(json.dumps(leader))
        invalid["delta"]["scope"] = "ADDED"  # Globally known, but invalid for scope outside a transition.
        with self.assertRaisesRegex(ValueError, "PD011"):
            self.m._parse_extraction(invalid, True, self.m.PRESENT)
        same_absence = json.loads(json.dumps(leader))
        same_absence["current_state"] = dict(presence="NOT_STATED", disposition="NONE", conditions="NONE",
                                             scope="NONE", exceptions="NONE", quantitative_terms="NONE")
        same_absence["evidence_excerpt"] = ""
        same_absence["delta"]["scope"] = "ADDED"
        with self.assertRaisesRegex(ValueError, "PD011"):
            self.m._parse_extraction(same_absence, True, self.m.NOT_STATED)

    def test_state_equivalence_core_ccv_and_evidence_guards_stay_strict(self):
        text = "Attribution is required."
        leader = drift_payload(quote=text)
        for baseline in (self.m.PRESENT, self.m.NOT_STATED):
            with self.subTest(baseline=baseline):
                self.assertTrue(self.m._validate_independent(leader, leader, text, True, baseline))
                absent = json.loads(json.dumps(leader))
                absent["current_state"] = dict(presence="NOT_STATED", disposition="NONE", conditions="NONE",
                                               scope="NONE", exceptions="NONE", quantitative_terms="NONE")
                absent["evidence_excerpt"] = ""
                self.assertFalse(self.m._validate_independent(leader, absent, text, True, baseline))
                other_disposition = json.loads(json.dumps(leader))
                other_disposition["current_state"]["disposition"] = "PROHIBITED"
                self.assertFalse(self.m._validate_independent(leader, other_disposition, text, True, baseline))
                self.assertFalse(self.m._validate_independent(leader, leader, "Not the claimed quote", True, baseline))
                for field in ("conditions", "scope", "exceptions", "quantitative_terms"):
                    candidate = json.loads(json.dumps(leader))
                    candidate["current_state"][field] = "Materially different rule"
                    self.nondet.semantic_equivalence[field] = False
                    try:
                        self.assertFalse(self.m._validate_independent(leader, candidate, text, True, baseline), field)
                    finally:
                        self.nondet.semantic_equivalence[field] = True

    def test_invalid_targets_urls_and_untrusted_payloads(self):
        for url in ("http://example.com/p", "https://127.0.0.1/", "https://[::1]/",
                    "https://user:pass@example.com/", "https://example.com/a#b", "https://localhost/p", "https://0x7f.1/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.contract.register_watch(url, "Can developers use API data commercially?")
        self.assertEqual(self.contract.get_watch_count(), 0)
        self.nondet.invalid_target = True
        with self.assertRaisesRegex(ValueError, "PD014"):
            self.register()
        self.nondet.invalid_target = False
        self.nondet.current_state = state()
        self.nondet.body = b"This page does not contain the claimed leader quote."
        self.nondet.leader_payload_override = {"evidence_excerpt": "Invented source quote"}
        with self.assertRaises(RuntimeError):
            self.register()
        self.assertEqual(self.contract.get_watch_count(), 0)

    def test_source_html_extraction_and_digest_normalization(self):
        html = b"<html><head><script>bad()</script></head><body><p>Commercial&nbsp;use</p><p>is permitted.</p></body></html>"
        self.assertEqual(self.m._source_text(html), "Commercial use is permitted.")
        normalized = state("ＡＢ  C")
        equivalent = state("AB C")
        self.assertEqual(self.m._semantic_digest(self.m._parse_state(normalized, self.m.SOURCE_OK)),
                         self.m._semantic_digest(self.m._parse_state(equivalent, self.m.SOURCE_OK)))
        self.assertNotEqual(self.m._semantic_digest(self.m._parse_state(state("Rule A"), self.m.SOURCE_OK)),
                            self.m._semantic_digest(self.m._parse_state(state("Rule B"), self.m.SOURCE_OK)))


if __name__ == "__main__":
    unittest.main()
