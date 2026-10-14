from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

import postfiat_rpc.pftl_transfer as cli
from postfiat_rpc.wallet import FaucetPftResult, SendPftResult, TransparentWallet


class PftlTransferCliTests(unittest.TestCase):
    def test_transfer_report_preserves_large_atom_amount_as_decimal_string(self) -> None:
        import json

        for atoms, expected in [
            (1, "0.000001"),
            (1_250_000, "1.250000"),
            (2**64 - 1, "18446744073709.551615"),
        ]:
            with self.subTest(atoms=atoms):
                report = json.loads(json.dumps(cli.transfer_report("send", atoms, {"tx_id": "tx"})))
                self.assertEqual(report["amount_atoms"], atoms)
                self.assertEqual(report["amount_pft"], expected)
                self.assertEqual(cli.pft_to_atoms(report["amount_pft"]), atoms)

    def test_pft_to_atoms_is_exact_at_six_decimals(self) -> None:
        self.assertEqual(cli.pft_to_atoms("20"), 20_000_000)
        self.assertEqual(cli.pft_to_atoms("0.000001"), 1)
        with self.assertRaises(ValueError):
            cli.pft_to_atoms("0")
        with self.assertRaises(ValueError):
            cli.pft_to_atoms("1.0000001")

    def test_pft_to_atoms_accepts_finite_positive_amounts(self) -> None:
        self.assertEqual(cli.pft_to_atoms("1"), 1_000_000)
        self.assertEqual(cli.pft_to_atoms("0.000001"), 1)
        self.assertEqual(cli.pft_to_atoms("12.5"), 12_500_000)
        self.assertEqual(cli.pft_to_atoms(" 3 "), 3_000_000)

    def test_send_cli_reports_nan_amount_as_value_error(self) -> None:
        stdout = io.StringIO()
        with (
            mock.patch.object(cli, "PostFiatRpcClient") as client_ctor,
            mock.patch.object(cli, "load_wallet") as load,
            mock.patch.object(cli, "send_pft") as send,
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = cli.main(
                [
                    "send",
                    "--to",
                    "pfrecipient",
                    "--amount",
                    "NaN",
                    "--endpoint",
                    "rpc.invalid:27650",
                    "--wallet-dir",
                    "/nonexistent",
                ]
            )

        self.assertEqual(exit_code, 1)
        report = json.loads(stdout.getvalue())
        self.assertFalse(report["ok"])
        self.assertTrue(report["error"].startswith("ValueError: amount"), report["error"])
        client_ctor.assert_not_called()
        load.assert_not_called()
        send.assert_not_called()

    def test_faucet_requires_explicit_apply_acknowledgement(self) -> None:
        args = cli.build_parser().parse_args(["faucet", "--to", "pfrecipient"])
        with mock.patch.object(cli, "request_faucet_pft") as request:
            with self.assertRaisesRegex(ValueError, "--allow-faucet-apply"):
                cli.run_faucet(args)
        request.assert_not_called()

    def test_faucet_action_delegates_to_wallet_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = cli.build_parser().parse_args(
                [
                    "faucet",
                    "--allow-faucet-apply",
                    "--to",
                    "pfrecipient",
                    "--amount",
                    "20",
                    "--work-dir",
                    str(root / "work"),
                ]
            )
            result = FaucetPftResult(
                tx_id="tx1",
                batch_file=root / "faucet.batch.json",
                batch={"ok": True},
                receipts_by_validator=(),
            )
            with (
                mock.patch.object(cli, "default_data_dir", return_value=root / "node0"),
                mock.patch.object(cli, "default_validator_data_dirs", return_value=[root / "node0"]),
                mock.patch.object(cli, "request_faucet_pft", return_value=result) as request,
            ):
                report = cli.run_faucet(args)

        self.assertTrue(report["ok"])
        self.assertEqual(report["amount_atoms"], 20_000_000)
        self.assertEqual(report["tx_id"], "tx1")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["to_address"], "pfrecipient")
        self.assertEqual(kwargs["amount"], 20_000_000)

    def test_send_action_loads_wallet_and_delegates_to_send_pft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wallet = TransparentWallet(
                chain_id="postfiat-local",
                account_index=0,
                address="pfsender",
                public_key_hex="00",
                key_file=root / "transparent-0.key.json",
                backup_file=root / "transparent-0.backup.json",
                key_report={},
            )
            result = SendPftResult(
                tx_id="tx2",
                quote_response={"ok": True},
                signed_transfer={"ok": True},
                submit_result={"ok": True},
                finalized_batch_file=None,
                receipts_by_validator=(),
            )
            args = cli.build_parser().parse_args(
                [
                    "send",
                    "--to",
                    "pfrecipient",
                    "--amount",
                    "1.25",
                    "--endpoint",
                    "127.0.0.1:27650",
                    "--wallet-dir",
                    str(root),
                ]
            )
            client = object()
            with (
                mock.patch.object(cli, "PostFiatRpcClient", return_value=client) as client_ctor,
                mock.patch.object(cli, "load_wallet", return_value=wallet) as load,
                mock.patch.object(cli, "send_pft", return_value=result) as send,
            ):
                report = cli.run_send(args)

        self.assertTrue(report["ok"])
        self.assertEqual(report["amount_atoms"], 1_250_000)
        self.assertEqual(report["tx_id"], "tx2")
        client_ctor.assert_called_once_with("127.0.0.1:27650", timeout_seconds=8.0)
        self.assertEqual(load.call_args.kwargs["wallet_dir"], str(root))
        kwargs = send.call_args.kwargs
        self.assertIs(kwargs["wallet"], wallet)
        self.assertEqual(kwargs["to_address"], "pfrecipient")
        self.assertEqual(kwargs["amount"], 1_250_000)


def _poll_wallet(root: Path) -> TransparentWallet:
    return TransparentWallet(
        chain_id="postfiat-local",
        account_index=0,
        address="pfsender",
        public_key_hex="00",
        key_file=root / "transparent-0.key.json",
        backup_file=root / "transparent-0.backup.json",
        key_report={},
    )


def _send_result(
    *,
    tx_id: str | None = "tx3",
    pending: bool,
    finalized: bool,
    finality_timeout: bool,
    submit_mode: str = "submit_and_poll",
) -> SendPftResult:
    return SendPftResult(
        tx_id=tx_id,
        quote_response={"ok": True},
        signed_transfer={"ok": True},
        submit_result={"accepted": True},
        finalized_batch_file=None,
        receipts_by_validator=(),
        submit_mode=submit_mode,
        pending=pending,
        finalized=finalized,
        finality_receipt={"tx_id": tx_id, "accepted": True} if finalized else None,
        finality_timeout=finality_timeout,
    )


def _run_send_cli(extra: list[str], *, helper: str, result: object) -> tuple[int, dict, mock.MagicMock]:
    stdout = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        argv = [
            "send",
            "--to",
            "pfrecipient",
            "--amount-atoms",
            "5",
            "--endpoint",
            "127.0.0.1:27650",
            "--wallet-dir",
            str(root),
            *extra,
        ]
        with (
            mock.patch.object(cli, "PostFiatRpcClient", return_value=object()),
            mock.patch.object(cli, "load_wallet", return_value=_poll_wallet(root)),
            mock.patch.object(cli, "send_pft") as send,
            mock.patch.object(cli, "send_pft_and_poll_finality") as poll,
            contextlib.redirect_stdout(stdout),
        ):
            target = {"send_pft": send, "send_pft_and_poll_finality": poll}[helper]
            other = poll if helper == "send_pft" else send
            target.return_value = result
            exit_code = cli.main(argv)
        other.assert_not_called()
        target.assert_called_once()
    return exit_code, json.loads(stdout.getvalue()), target


POLL_ARGS = ["--poll-finality", "--poll-timeout-seconds", "0.01", "--poll-interval-seconds", "0.001"]


def test_send_poll_finality_timeout_fails_and_keeps_tx_id_and_result() -> None:
    exit_code, report, poll = _run_send_cli(
        POLL_ARGS,
        helper="send_pft_and_poll_finality",
        result=_send_result(pending=True, finalized=False, finality_timeout=True),
    )

    assert exit_code == 1
    assert report["ok"] is False
    assert report["error"] == cli.FINALITY_TIMEOUT_ERROR
    assert report["error"].startswith("finality_timeout")
    assert report["action"] == "send"
    assert report["tx_id"] == "tx3"
    assert report["amount_atoms"] == 5
    assert report["result"]["tx_id"] == "tx3"
    assert report["result"]["finality_timeout"] is True
    assert report["result"]["pending"] is True
    assert report["result"]["finalized"] is False
    assert poll.call_args.kwargs["poll_timeout_seconds"] == 0.01
    assert poll.call_args.kwargs["poll_interval_seconds"] == 0.001


def test_send_poll_finality_reached_is_ok() -> None:
    exit_code, report, _ = _run_send_cli(
        POLL_ARGS,
        helper="send_pft_and_poll_finality",
        result=_send_result(pending=False, finalized=True, finality_timeout=False),
    )

    assert exit_code == 0
    assert report["ok"] is True
    assert "error" not in report
    assert report["tx_id"] == "tx3"
    assert report["result"]["finalized"] is True


def test_send_poll_finality_without_tx_id_fails() -> None:
    # send_pft_and_poll_finality returns the bare send_pft result when the
    # submit produced no tx_id, so nothing was polled.
    exit_code, report, _ = _run_send_cli(
        POLL_ARGS,
        helper="send_pft_and_poll_finality",
        result=_send_result(
            tx_id=None, pending=True, finalized=False, finality_timeout=False, submit_mode="submit_only"
        ),
    )

    assert exit_code == 1
    assert report["ok"] is False
    assert report["error"] == cli.FINALITY_NOT_POLLED_ERROR
    assert report["tx_id"] is None
    assert report["result"]["tx_id"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"tx_id": "tx3", "pending": True},
        {"tx_id": "tx3", "finalized": None},
        {"tx_id": "tx3", "finalized": 1},
        {"tx_id": "tx3", "finalized": "true"},
        {"tx_id": "tx3", "finalized": [True]},
        {"tx_id": "tx3", "finalized": {"value": True}},
        {"tx_id": "tx3", "finalized": True, "finality_timeout": True},
    ],
)
def test_send_poll_finality_requires_bool_true_finalized(body: dict) -> None:
    exit_code, report, _ = _run_send_cli(POLL_ARGS, helper="send_pft_and_poll_finality", result=body)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["error"] == cli.FINALITY_TIMEOUT_ERROR
    assert report["tx_id"] == "tx3"
    assert report["result"] == body


@pytest.mark.parametrize(
    "body",
    [
        {"tx_id": "", "finalized": True},
        {"tx_id": 7, "finalized": True},
        {"finalized": True},
    ],
)
def test_send_poll_finality_requires_tx_id(body: dict) -> None:
    exit_code, report, _ = _run_send_cli(POLL_ARGS, helper="send_pft_and_poll_finality", result=body)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["error"] == cli.FINALITY_NOT_POLLED_ERROR


def test_send_poll_finality_non_dict_result_fails() -> None:
    exit_code, report, _ = _run_send_cli(POLL_ARGS, helper="send_pft_and_poll_finality", result=None)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["error"] == cli.FINALITY_NOT_POLLED_ERROR


def test_plain_send_pending_result_is_still_ok() -> None:
    exit_code, report, _ = _run_send_cli(
        [],
        helper="send_pft",
        result=_send_result(pending=True, finalized=False, finality_timeout=False, submit_mode="submit_only"),
    )

    assert exit_code == 0
    assert report["ok"] is True
    assert "error" not in report
    assert report["tx_id"] == "tx3"


def test_finalize_data_dir_takes_precedence_and_is_unchanged() -> None:
    # --finalize-data-dir is checked before --poll-finality in run_send, so
    # the local-harness path keeps its existing report even with both flags.
    exit_code, report, send = _run_send_cli(
        ["--finalize-data-dir", "/nonexistent-node0", "--validator-data-dirs", "/nonexistent-node0", *POLL_ARGS],
        helper="send_pft",
        result=_send_result(pending=False, finalized=False, finality_timeout=False, submit_mode="local_apply"),
    )

    assert exit_code == 0
    assert report["ok"] is True
    assert "error" not in report
    assert str(send.call_args.kwargs["finalize_data_dir"]) == "/nonexistent-node0"


@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "sNaN",
        "-NaN",
        "Infinity",
        "-Infinity",
        "inf",
        "1e400000000",
        "",
        "abc",
        "0",
        "-1",
        "0.0000001",
    ],
)
def test_pft_to_atoms_refuses_non_finite_and_invalid_amounts(value: str) -> None:
    with pytest.raises(ValueError, match="amount"):
        cli.pft_to_atoms(value)


if __name__ == "__main__":
    unittest.main()
