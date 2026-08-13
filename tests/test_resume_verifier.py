"""
ResumeVerifier Smart Contract — Comprehensive Unit Tests
=========================================================
Uses algorand-python-testing v1.1.0 (algopy_testing) for AVM simulation.

API rules (from txn_context.py source):
  - create_group(active_txn_overrides=...) — for single-txn calls (no group needed)
  - create_group(gtxns=[...])              — for multi-txn groups (payment + appcall)
  - These two are mutually exclusive (ValueError if both supplied)
"""
from __future__ import annotations

import typing

import algosdk
import pytest

import algopy
from algopy_testing import AlgopyTestContext, algopy_testing_context

from smart_contracts.resume_verifier.contract import ResumeVerifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_resume_hash(seed: int = 0) -> algopy.arc4.StaticArray[algopy.arc4.Byte, typing.Literal[32]]:
    """Create a deterministic 32-byte test resume hash."""
    return algopy.arc4.StaticArray(
        *[algopy.arc4.Byte((seed + i) % 256) for i in range(32)]
    )


def get_contract_address(contract: ResumeVerifier) -> algopy.Account:
    """Return the on-chain address of the contract account, derived from its app ID."""
    app_id = contract.__app_id__
    address = algosdk.logic.get_application_address(app_id)
    return algopy.Account(address)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ctx() -> typing.Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as context:
        yield context


@pytest.fixture()
def deployer(ctx: AlgopyTestContext) -> algopy.Account:
    return ctx.any.account(balance=algopy.UInt64(10_000_000))


@pytest.fixture()
def applicant(ctx: AlgopyTestContext) -> algopy.Account:
    return ctx.any.account(balance=algopy.UInt64(5_000_000))


@pytest.fixture()
def other_user(ctx: AlgopyTestContext) -> algopy.Account:
    return ctx.any.account(balance=algopy.UInt64(5_000_000))


@pytest.fixture()
def contract(ctx: AlgopyTestContext, deployer: algopy.Account) -> ResumeVerifier:
    """Return a bootstrapped ResumeVerifier with min_fee=500_000 µALGO."""
    c = ResumeVerifier()
    # Single-call (create): use active_txn_overrides only (no gtxns)
    with ctx.txn.create_group(active_txn_overrides={"sender": deployer}):
        c.bootstrap(algopy.UInt64(500_000))
    return c


# ---------------------------------------------------------------------------
# Helper: grouped register_attestation (payment + appcall)
# ---------------------------------------------------------------------------

def _register(
    ctx: AlgopyTestContext,
    contract: ResumeVerifier,
    sender: algopy.Account,
    resume_hash: algopy.arc4.StaticArray[algopy.arc4.Byte, typing.Literal[32]],
    role_id: str,
    match_score: int,
    payment_amount: int = 500_000,
    payment_receiver: algopy.Account | None = None,
) -> algopy.arc4.String:
    """
    Simulate [PaymentTxn, AppCallTxn] atomic group for register_attestation.
    Uses gtxns= only (no active_txn_overrides — mutually exclusive).
    """
    receiver = payment_receiver if payment_receiver is not None else get_contract_address(contract)
    payment = ctx.any.txn.payment(
        sender=sender,
        receiver=receiver,
        amount=algopy.UInt64(payment_amount),
    )
    # Pass the contract's actual Application object so the group's active txn
    # has the same app_id as the contract being executed.
    app_call = ctx.any.txn.application_call(
        sender=sender,
        app_id=ctx.ledger.get_app(contract),
    )

    # gtxns=[payment, app_call] → active_txn_index defaults to last (app_call)
    with ctx.txn.create_group(gtxns=[payment, app_call]):
        return contract.register_attestation(
            resume_hash=resume_hash,
            role_id=algopy.arc4.String(role_id),
            match_score=algopy.arc4.UInt64(match_score),
            payment=payment,
        )


def _read(ctx: AlgopyTestContext, sender: algopy.Account):
    """Context manager for read-only / single-call operations."""
    return ctx.txn.create_group(active_txn_overrides={"sender": sender})


# ===========================================================================
# Tests
# ===========================================================================


class TestBootstrap:
    def test_sets_admin(
        self, deployer: algopy.Account, contract: ResumeVerifier
    ) -> None:
        """bootstrap() must record the deployer as admin."""
        assert contract.admin.value == deployer

    def test_sets_min_fee(self, contract: ResumeVerifier) -> None:
        """bootstrap() must set min_fee to 500_000 µALGO."""
        assert contract.min_fee.value == algopy.UInt64(500_000)


class TestRegisterAttestation:
    def test_success_returns_attested(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        result = _register(ctx, contract, applicant, make_resume_hash(1), "backend-engineer", 75)
        assert result == algopy.arc4.String("ATTESTED")

    def test_box_written_with_correct_fields(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        resume_hash = make_resume_hash(42)
        ctx.ledger.patch_global_fields(round=algopy.UInt64(999))
        _register(ctx, contract, applicant, resume_hash, "data-scientist", 88, 500_000)

        with _read(ctx, applicant):
            record = contract.get_attestation(applicant, resume_hash)

        assert record.role_id == algopy.arc4.String("data-scientist")
        assert record.match_score == algopy.arc4.UInt64(88)
        assert record.attestation_round == algopy.arc4.UInt64(999)
        assert record.fee_paid == algopy.arc4.UInt64(500_000)

    def test_reattestion_overwrites(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        resume_hash = make_resume_hash(7)
        _register(ctx, contract, applicant, resume_hash, "devops", 60)
        _register(ctx, contract, applicant, resume_hash, "ml-engineer", 80)

        with _read(ctx, applicant):
            record = contract.get_attestation(applicant, resume_hash)

        assert record.role_id == algopy.arc4.String("ml-engineer")
        assert record.match_score == algopy.arc4.UInt64(80)

    def test_different_hashes_are_independent(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        hash_a, hash_b = make_resume_hash(10), make_resume_hash(20)
        _register(ctx, contract, applicant, hash_a, "backend-engineer", 70)
        _register(ctx, contract, applicant, hash_b, "product-manager", 55)

        with _read(ctx, applicant):
            rec_a = contract.get_attestation(applicant, hash_a)
            rec_b = contract.get_attestation(applicant, hash_b)

        assert rec_a.role_id == algopy.arc4.String("backend-engineer")
        assert rec_b.role_id == algopy.arc4.String("product-manager")

    def test_payment_wrong_receiver_rejected(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier,
        applicant: algopy.Account, other_user: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="receiver"):
            _register(ctx, contract, applicant, make_resume_hash(3), "backend-engineer", 70,
                      payment_receiver=other_user)

    def test_payment_below_min_fee_rejected(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="minimum attestation fee"):
            _register(ctx, contract, applicant, make_resume_hash(4), "backend-engineer", 70,
                      payment_amount=100_000)

    def test_score_above_100_rejected(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="0 and 100"):
            _register(ctx, contract, applicant, make_resume_hash(5), "backend-engineer", 101)

    def test_score_100_accepted(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        """Score == 100 (upper boundary) must be accepted."""
        result = _register(ctx, contract, applicant, make_resume_hash(6), "backend-engineer", 100)
        assert result == algopy.arc4.String("ATTESTED")

    def test_score_0_accepted(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        """Score == 0 (lower boundary) must be accepted."""
        result = _register(ctx, contract, applicant, make_resume_hash(9), "backend-engineer", 0)
        assert result == algopy.arc4.String("ATTESTED")

    def test_payment_exactly_min_fee_accepted(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        result = _register(ctx, contract, applicant, make_resume_hash(11), "backend-engineer", 75,
                           payment_amount=500_000)
        assert result == algopy.arc4.String("ATTESTED")

    def test_overpayment_stores_real_amount(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        """fee_paid stores the REAL payment amount, not just the minimum."""
        resume_hash = make_resume_hash(12)
        _register(ctx, contract, applicant, resume_hash, "devops-engineer", 90,
                  payment_amount=1_000_000)

        with _read(ctx, applicant):
            record = contract.get_attestation(applicant, resume_hash)

        assert record.fee_paid == algopy.arc4.UInt64(1_000_000)


class TestGetAttestation:
    def test_returns_correct_record(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        resume_hash = make_resume_hash(50)
        ctx.ledger.patch_global_fields(round=algopy.UInt64(42))
        _register(ctx, contract, applicant, resume_hash, "ml-engineer", 93)

        with _read(ctx, applicant):
            record = contract.get_attestation(applicant, resume_hash)

        assert record.role_id == algopy.arc4.String("ml-engineer")
        assert record.match_score == algopy.arc4.UInt64(93)
        assert record.attestation_round == algopy.arc4.UInt64(42)

    def test_missing_attestation_reverts(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="No attestation found"):
            with _read(ctx, applicant):
                contract.get_attestation(applicant, make_resume_hash(99))


class TestVerifyResumeHash:
    def test_returns_true_when_exists(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        resume_hash = make_resume_hash(60)
        _register(ctx, contract, applicant, resume_hash, "devops-engineer", 65)
        with _read(ctx, applicant):
            result = contract.verify_resume_hash(applicant, resume_hash)
        assert result == algopy.arc4.Bool(True)

    def test_returns_false_when_not_exists(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        with _read(ctx, applicant):
            result = contract.verify_resume_hash(applicant, make_resume_hash(61))
        assert result == algopy.arc4.Bool(False)

    def test_different_applicants_independent(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier,
        applicant: algopy.Account, other_user: algopy.Account
    ) -> None:
        """Attestation for applicant A must not affect verify result for applicant B."""
        resume_hash = make_resume_hash(62)
        _register(ctx, contract, applicant, resume_hash, "backend-engineer", 70)

        with _read(ctx, other_user):
            result = contract.verify_resume_hash(other_user, resume_hash)
        assert result == algopy.arc4.Bool(False)


class TestWithdrawFees:
    def test_admin_can_withdraw(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, deployer: algopy.Account
    ) -> None:
        with _read(ctx, deployer):
            contract.withdraw_fees(algopy.UInt64(100_000))  # must not raise

    def test_non_admin_cannot_withdraw(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, other_user: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="admin"):
            with _read(ctx, other_user):
                contract.withdraw_fees(algopy.UInt64(100_000))

    def test_applicant_cannot_withdraw(
        self, ctx: AlgopyTestContext, contract: ResumeVerifier, applicant: algopy.Account
    ) -> None:
        with pytest.raises(Exception, match="admin"):
            with _read(ctx, applicant):
                contract.withdraw_fees(algopy.UInt64(50_000))
