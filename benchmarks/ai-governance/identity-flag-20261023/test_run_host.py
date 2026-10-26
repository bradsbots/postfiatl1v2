"""Offline tests of the flag host runner ``run_host.py`` with a stubbed model backend.

No host, server or model is contacted. Run:
``python3 -m pytest benchmarks/ai-governance/identity-flag-20261023 -q``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import threading
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import admissibility  # noqa: E402
import identity_flag_pipeline as pl  # noqa: E402
import run_host  # noqa: E402

ROUND_28 = HERE / "fixtures/round_28_candidates.json"
CORPUS = HERE.parent / "validator-identity-packets-20260901"
SPEC = pl.REPO / "docs/specs/identity-flag-pipeline-spec-20261023.md"
WORKED_ROUND = {"network": "corpus-20260901", "round_number": 0, "input_package_hash": "0" * 64}
RESULT_KEYS = {"slot", "request_sha256", "content", "finish_reason"}


class StubBackend:
    """Answers each request by its row; records the bytes it got and which slots were in flight."""

    def __init__(self, rows, decide, overrides=None):
        self.rows = {row["request_sha256"]: row for row in rows}
        self.decide = decide
        self.overrides = overrides or {}
        self.received: list[str] = []
        self.in_flight: set[int] = set()
        self.batches_in_flight: list[set[int]] = []
        self.lock = threading.Lock()

    def complete(self, body: bytes) -> dict:
        row = self.rows[hashlib.sha256(body).hexdigest()]  # KeyError unless the exact request bytes arrive
        with self.lock:
            self.received.append(row["request_sha256"])
            self.in_flight.add(row["slot"])
            self.batches_in_flight.append({slot // pl.BATCH_SIZE for slot in self.in_flight})
        try:
            if row["validator_id"] in self.overrides:
                content, finish_reason = self.overrides[row["validator_id"]]
            elif row["padding"]:
                content, finish_reason = pl.PAD_CONTENT, "stop"
            else:
                content, finish_reason = json.dumps({
                    "validator_id": row["validator_id"],
                    "packet_sha256": row["packet_sha256"],
                    "classification": self.decide(row["validator_id"]),
                    "cited_fields": ["public_identity"],
                    "reason_codes": (["identity_not_established"]
                                     if self.decide(row["validator_id"]) == "flag" else []),
                }, sort_keys=True), "stop"
            return {"content": content, "finish_reason": finish_reason, "usage": {"completion_tokens": 1}}
        finally:
            with self.lock:
                self.in_flight.discard(row["slot"])

    def host_facts(self) -> dict:
        return {"gpu": "stub", "python": "stub", "server": {}}


def all_flag(_vid: str) -> str:
    return "flag"


def write_round28_requests(tmp_path: Path) -> tuple[Path, list]:
    path = tmp_path / "requests.json"
    assert admissibility.main(["--round", str(ROUND_28), "--requests-out", str(path)]) == 0
    return path, json.loads(path.read_text())


def worked_packets() -> tuple[dict, list]:
    data = json.loads((HERE / "fixtures/worked_example_20260903.json").read_text())
    packets = [{"validator_id": r["validator_id"], "network": r["network"], "packet_sha256": r["packet_sha256"],
                "packet_text": (CORPUS / r["packet_path"]).read_text(encoding="utf-8")}
               for r in data["validators"]]
    return data, packets


def four_runs(requests_path: Path, out_dir: Path, backends: dict) -> dict:
    """Two owners × two runs through ``run_host.main``; returns ``{owner: [paths]}``."""
    paths: dict = {}
    for owner, backend in backends.items():
        for index in (1, 2):
            assert run_host.main(["--requests", str(requests_path), "--owner", owner,
                                  "--provider-host-id", f"host-{owner}", "--run-index", str(index),
                                  "--out-dir", str(out_dir)], backend=backend) == 0
            paths.setdefault(owner, []).append(out_dir / f"{owner}-run{index}.json")
    return paths


# --- run files the comparison accepts ------------------------------------------

def test_runner_writes_run_files_that_admissibility_cli_accepts(tmp_path, capsys):
    requests_path, rows = write_round28_requests(tmp_path)
    paths = four_runs(requests_path, tmp_path / "outputs",
                      {owner: StubBackend(rows, all_flag) for owner in ("ownerA", "ownerB")})
    for owner, owner_paths in paths.items():
        assert [p.name for p in owner_paths] == [f"{owner}-run1.json", f"{owner}-run2.json"]
        for path in owner_paths:
            record = json.loads(path.read_text())
            assert record["host"]["owner"] == owner and record["host"]["provider_host_id"] == f"host-{owner}"
            assert "owner" not in record  # the comparison's owner label comes from --run OWNER=PATH
            assert record["requests_sha256"] == pl.requests_sha256(rows)
            assert record["prompt_sha256"] == run_host.PROMPT_SHA256
            assert record["response_schema_sha256"] == run_host.RESPONSE_SCHEMA_SHA256
            assert record["profile_sha256"] == pl.profile_sha256()
            assert [r["slot"] for r in record["results"]] == list(range(len(rows)))
            assert all(RESULT_KEYS <= set(r) for r in record["results"])
    section = tmp_path / "section.json"
    section.write_text(json.dumps(pl.manifest_section()))
    args = ["--round", str(ROUND_28), "--section", str(section), "--out", str(tmp_path / "out")]
    for owner, owner_paths in paths.items():
        args += [arg for path in owner_paths for arg in ("--run", f"{owner}={path}")]
    capsys.readouterr()
    assert admissibility.main(args) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["flags"] == 0 and printed["replay_unreliable"] is False
    assert printed["packet_coverage"] == {"candidates": 61, "with_packet": 20, "missing_packet": 41}
    assert printed["counts_by_class"]["admissible"] == 20 and printed["counts_by_class"]["missing"] == 41
    adm = json.loads((tmp_path / "out/admissibility.json").read_text())
    assert adm["outage"] is False and all(s["byte_identical"] for s in adm["slots"])


def test_four_runs_over_two_stubbed_owners_give_the_fixture_admissibility(tmp_path):
    data, packets = worked_packets()
    score_zero = {r["validator_id"] for r in data["validators"] if r["legitimacy_score"] == 0}
    rows = pl.build_requests(packets)
    requests_path = tmp_path / "requests.json"
    requests_path.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    decide = lambda vid: "flag" if vid in score_zero else "clear"  # noqa: E731
    target = sorted(score_zero)[0]
    bad_b = StubBackend(rows, decide, overrides={target: ('{"x": 1}', "stop")})
    for out, backends in (("same", {"A": StubBackend(rows, decide), "B": StubBackend(rows, decide)}),
                          ("diverge", {"A": StubBackend(rows, decide), "B": bad_b})):
        paths = four_runs(requests_path, tmp_path / out, backends)
        runs = [{"owner": owner, **json.loads(p.read_text())} for owner, ps in paths.items() for p in ps]
        flags, adm = pl.build_flags(round_info=WORKED_ROUND, packets=packets, runs=runs,
                                    candidates=[{"validator_id": r["validator_id"],
                                                 "domain_verified": r["domain_verified"]}
                                                for r in data["validators"]],
                                    expected_section=pl.manifest_section())
        counts = flags["admissibility_summary"]["counts_by_class"]
        flagged = {op["validator_id"] for op in flags["operators"] if op["identity_flag"] == "flag"}
        if out == "same":
            assert len(flagged) == data["expected_flags"]["legitimacy_score_zero"] == 13
            assert counts["admissible"] == 55 and flags["replay_unreliable"] is False
        else:
            status = {op["validator_id"]: op["admissibility"] for op in flags["operators"]}
            assert status[target] == "divergent" and counts["admissible"] == 54
            assert flags["replay_unreliable"] is True and target not in flagged
    # The execution profile's batching: one batch of 32 at a time, never two batches in flight.
    assert bad_b.batches_in_flight and all(len(b) == 1 for b in bad_b.batches_in_flight)


# --- refusals -------------------------------------------------------------------

def _tamper(tmp_path: Path, source: Path, edit) -> Path:
    copy = tmp_path / source.name
    shutil.copy(source, copy)
    copy.write_text(edit(copy.read_text(encoding="utf-8")), encoding="utf-8")
    return copy


@pytest.mark.parametrize("attribute, edit, message", [
    ("PROMPT_PATH", lambda text: text + " ", "prompt_v1.txt"),
    ("SCHEMA_PATH", lambda text: text.replace('"minItems": 1', '"minItems": 2'), "response_schema_v1.json"),
])
def test_wrong_prompt_or_schema_hash_refuses_to_start(tmp_path, monkeypatch, attribute, edit, message):
    requests_path, rows = write_round28_requests(tmp_path)
    backend = StubBackend(rows, all_flag)
    monkeypatch.setattr(pl, attribute, _tamper(tmp_path, getattr(pl, attribute), edit))
    with pytest.raises(run_host.Refused, match=message):
        run_host.main(["--requests", str(requests_path), "--owner", "A", "--provider-host-id", "1",
                       "--run-index", "1", "--out-dir", str(tmp_path / "outputs")], backend=backend)
    assert backend.received == [] and not (tmp_path / "outputs").exists()


def test_a_pin_that_differs_from_the_package_refuses(tmp_path, monkeypatch):
    requests_path, rows = write_round28_requests(tmp_path)
    for name in ("PROMPT_SHA256", "RESPONSE_SCHEMA_SHA256"):
        with monkeypatch.context() as patch:
            patch.setattr(run_host, name, "0" * 64)
            with pytest.raises(run_host.Refused, match="SHA-256"):
                run_host.run(rows, owner="A", run_index=1, provider_host_id="1",
                             out_dir=tmp_path / "outputs", backend=StubBackend(rows, all_flag))


def test_request_rows_that_are_not_the_flag_requests_refuse(tmp_path):
    _, rows = write_round28_requests(tmp_path)
    legitimacy = json.loads(json.dumps(rows))
    legitimacy[0]["body"]["messages"][0]["content"] = "You score legitimacy."
    legitimacy[0]["request_sha256"] = pl.sha256(pl.canonical(legitimacy[0]["body"]))
    rehashed_temperature = json.loads(json.dumps(rows))
    rehashed_temperature[1]["body"]["temperature"] = 0.7
    rehashed_temperature[1]["request_sha256"] = pl.sha256(pl.canonical(rehashed_temperature[1]["body"]))
    unhashed = json.loads(json.dumps(rows))
    unhashed[2]["body"]["max_tokens"] = 4096
    cases = {
        "system prompt": legitimacy,
        "not the flag pipeline's requests": rehashed_temperature,
        "request hash": unhashed,
        "whole batches": rows[:-1],
    }
    for message, bad in cases.items():
        backend = StubBackend(rows, all_flag)
        with pytest.raises(run_host.Refused, match=message):
            run_host.run(bad, owner="A", run_index=1, provider_host_id="1",
                         out_dir=tmp_path / "outputs", backend=backend)
        assert backend.received == []


def test_bad_owner_run_index_or_existing_run_file_refuses(tmp_path):
    _, rows = write_round28_requests(tmp_path)
    out = tmp_path / "outputs"
    for owner, index, message in (("../A", 1, "owner"), ("A", 3, "run index"), ("A", 0, "run index")):
        with pytest.raises(run_host.Refused, match=message):
            run_host.run(rows, owner=owner, run_index=index, provider_host_id="1", out_dir=out,
                         backend=StubBackend(rows, all_flag))
    run_host.run(rows, owner="A", run_index=1, provider_host_id="1", out_dir=out,
                 backend=StubBackend(rows, all_flag))
    first = (out / "A-run1.json").read_bytes()
    with pytest.raises(run_host.Refused, match="exists"):
        run_host.run(rows, owner="A", run_index=1, provider_host_id="1", out_dir=out,
                     backend=StubBackend(rows, all_flag))
    assert (out / "A-run1.json").read_bytes() == first


# --- what the run file records -------------------------------------------------

def test_truncated_or_invalid_reply_is_written_with_its_real_finish_reason(tmp_path):
    _, rows = write_round28_requests(tmp_path)
    scoring = [r for r in rows if not r["padding"]]
    truncated, invalid, padding = scoring[0], scoring[1], next(r for r in rows if r["padding"])
    overrides = {truncated["validator_id"]: ('{"validator_id": "n9', "length"),
                 invalid["validator_id"]: ("not json", "stop"),
                 padding["validator_id"]: ("", None)}
    path = run_host.run(rows, owner="A", run_index=2, provider_host_id="1", out_dir=tmp_path,
                        backend=StubBackend(rows, all_flag, overrides))
    record = json.loads(path.read_text())
    by_slot = {r["slot"]: r for r in record["results"]}
    assert len(by_slot) == len(rows)
    assert (by_slot[truncated["slot"]]["content"], by_slot[truncated["slot"]]["finish_reason"]) == (
        '{"validator_id": "n9', "length")
    assert (by_slot[invalid["slot"]]["content"], by_slot[invalid["slot"]]["finish_reason"]) == ("not json", "stop")
    assert (by_slot[padding["slot"]]["content"], by_slot[padding["slot"]]["finish_reason"]) == ("", None)
    assert by_slot[truncated["slot"]]["slot_check"] == "truncated"
    assert by_slot[invalid["slot"]]["slot_check"] == "invalid"
    assert record["slot_checks"] == {"admissible": len(rows) - 3, "invalid": 1, "truncated": 2}


def test_request_sha256_echoed_is_the_one_from_the_request_row(tmp_path):
    _, rows = write_round28_requests(tmp_path)
    backend = StubBackend(rows, all_flag)
    path = run_host.run(rows, owner="A", run_index=1, provider_host_id="1", out_dir=tmp_path, backend=backend)
    results = json.loads(path.read_text())["results"]
    assert [r["request_sha256"] for r in results] == [row["request_sha256"] for row in rows]
    # The bytes sent hash to the row's request_sha256 (the stub looks each request up by that hash).
    assert sorted(backend.received) == sorted(row["request_sha256"] for row in rows)
    assert all(r["content_sha256"] == pl.sha256(r["content"]) for r in results)


# --- the real backend ------------------------------------------------------------

def test_real_backend_is_the_2026_09_03_endpoint_and_loads_only_for_a_real_run(monkeypatch):
    assert run_host.LEGACY_MODULE not in sys.modules  # importing the runner loads no backend
    sent = {}

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": None}, "finish_reason": "length"}],
                               "usage": {"completion_tokens": 2048}}).encode()

    def fake_urlopen(request, timeout):
        sent.update(url=request.full_url, data=request.data, method=request.get_method(), timeout=timeout)
        return Reply()

    backend = run_host.SGLangBackend()
    legacy = sys.modules[run_host.LEGACY_MODULE]
    assert backend.url == legacy.URL == "http://127.0.0.1:8000/v1/chat/completions"
    monkeypatch.setattr(run_host.urllib.request, "urlopen", fake_urlopen)
    reply = backend.complete(b'{"model":"m"}')
    assert sent == {"url": legacy.URL, "data": b'{"model":"m"}', "method": "POST", "timeout": 3600}
    assert reply == {"content": "", "finish_reason": "length", "usage": {"completion_tokens": 2048}}


# --- pins ------------------------------------------------------------------------

def test_runner_pins_are_the_package_and_spec_pins():
    assert run_host.PROMPT_SHA256 == pl.file_sha256(pl.PROMPT_PATH)
    assert run_host.RESPONSE_SCHEMA_SHA256 == pl.response_schema_sha256()
    readme, spec = (HERE / "README.md").read_text(), SPEC.read_text()
    for digest in (run_host.PROMPT_SHA256, run_host.RESPONSE_SCHEMA_SHA256):
        assert digest in readme and digest in spec
    # Pin decision of 2026-10-26: spec §6 does not pin the runner, so the manifest section has no runner hash.
    runner_sha = pl.file_sha256(HERE / "run_host.py")
    assert runner_sha not in json.dumps(pl.manifest_section()) and "run_host" not in json.dumps(pl.execution_profile())
    assert "**Decision, 2026-10-26.**" in readme


# --- run-file owners, run indexes and provider hosts (spec §5, §9) -----------------

@pytest.fixture(scope="module")
def worked_round(tmp_path_factory):
    """The worked example as a round file, its request rows, and four clean run files from the runner."""
    data, _ = worked_packets()
    score_zero = {r["validator_id"] for r in data["validators"] if r["legitimacy_score"] == 0}
    tmp = tmp_path_factory.mktemp("worked_round")
    round_path = tmp / "round.json"
    round_path.write_text(json.dumps({"round": WORKED_ROUND, "candidates": [
        {key: r[key] for key in ("validator_id", "domain_verified", "network", "packet_path", "packet_sha256")}
        for r in data["validators"]]}))
    requests_path = tmp / "requests.json"
    assert admissibility.main(["--round", str(round_path), "--requests-out", str(requests_path)]) == 0
    rows = json.loads(requests_path.read_text())
    decide = lambda vid: "flag" if vid in score_zero else "clear"  # noqa: E731
    paths = four_runs(requests_path, tmp / "outputs",
                      {owner: StubBackend(rows, decide) for owner in ("ownerA", "ownerB")})
    section = tmp / "section.json"
    section.write_text(json.dumps(pl.manifest_section()))
    return round_path, section, paths


def run_admissibility(worked_round, tmp_path, capsys, runs) -> tuple[dict, dict]:
    """``admissibility.py`` over ``runs = [(owner_label, path)]``; returns the printed summary and admissibility.json."""
    round_path, section, _ = worked_round
    args = ["--round", str(round_path), "--section", str(section), "--out", str(tmp_path / "out")]
    for owner, path in runs:
        args += ["--run", f"{owner}={path}"]
    capsys.readouterr()
    assert admissibility.main(args) == 0
    return json.loads(capsys.readouterr().out), json.loads((tmp_path / "out/admissibility.json").read_text())


def clean_runs(worked_round) -> list:
    return [(owner, path) for owner, paths in worked_round[2].items() for path in paths]


def assert_outage(printed: dict, adm: dict, problem: str) -> None:
    assert printed["flags"] == 0 and adm["outage"] is True
    assert printed["counts_by_class"]["outage"] == 55 and printed["counts_by_class"]["admissible"] == 0
    assert any(problem in line for line in printed["run_file_problems"]), printed["run_file_problems"]


def test_four_clean_run_files_give_the_fixture_flags(worked_round, tmp_path, capsys):
    printed, adm = run_admissibility(worked_round, tmp_path, capsys, clean_runs(worked_round))
    assert printed["flags"] == 13 and printed["run_file_problems"] == [] and adm["outage"] is False


def test_owner_label_that_differs_from_the_files_host_owner_is_an_outage(worked_round, tmp_path, capsys):
    (a1, a2), (b1, b2) = worked_round[2]["ownerA"], worked_round[2]["ownerB"]
    swapped = [("ownerA", a1), ("ownerB", a2), ("ownerA", b1), ("ownerB", b2)]
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, swapped), "host.owner")


def test_same_provider_host_id_across_owners_is_an_outage(worked_round, tmp_path, capsys):
    runs = []
    for owner, path in clean_runs(worked_round):
        record = json.loads(path.read_text())
        record["host"]["provider_host_id"] = "445596"
        copy = tmp_path / path.name
        copy.write_text(json.dumps(record))
        runs.append((owner, copy))
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, runs), "provider host")


def test_duplicated_or_out_of_range_run_index_is_an_outage(worked_round, tmp_path, capsys):
    (a1, _a2), (b1, b2) = worked_round[2]["ownerA"], worked_round[2]["ownerB"]
    duplicated = [("ownerA", a1), ("ownerA", a1), ("ownerB", b1), ("ownerB", b2)]
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, duplicated), "run index")
    record = json.loads(b2.read_text())
    record["host"]["run_index"] = 3
    out_of_range = tmp_path / "ownerB-run3.json"
    out_of_range.write_text(json.dumps(record))
    runs = [("ownerA", a1), ("ownerA", _a2), ("ownerB", b1), ("ownerB", out_of_range)]
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, runs), "run index")


def test_run_file_without_a_host_record_is_an_outage(worked_round, tmp_path, capsys):
    runs = []
    for owner, path in clean_runs(worked_round):
        copy = tmp_path / path.name
        copy.write_text(json.dumps({"results": json.loads(path.read_text())["results"]}))
        runs.append((owner, copy))
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, runs), "host")


def test_one_owners_two_runs_on_different_provider_hosts_is_an_outage(worked_round, tmp_path, capsys):
    (a1, a2), (b1, b2) = worked_round[2]["ownerA"], worked_round[2]["ownerB"]
    record = json.loads(a2.read_text())
    record["host"]["provider_host_id"] = "host-ownerA-second"
    moved = tmp_path / a2.name
    moved.write_text(json.dumps(record))
    runs = [("ownerA", a1), ("ownerA", moved), ("ownerB", b1), ("ownerB", b2)]
    assert_outage(*run_admissibility(worked_round, tmp_path, capsys, runs), "more than one provider host")
