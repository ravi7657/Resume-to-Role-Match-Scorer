"""
Resume Role Matcher — ResumeVerifier Smart Contract
====================================================
Provides tamper-evident, on-chain attestation of AI-computed resume
match results using Algorand Box Storage.

WHAT IS STORED ON-CHAIN (per attestation box):
  - SHA-256 hash of the resume file           (32 bytes, the box key suffix)
  - Job role identifier                        (≤ 64 chars, in box value)
  - Deterministic match score (0–100)         (uint64, in box value)
  - Algorand round at time of attestation     (uint64, tamper-proof timestamp)
  - Actual µALGO fee paid                     (uint64, from real PaymentTxn)

WHAT IS NOT STORED ON-CHAIN:
  - Resume text, PDF, or any resume content
  - Applicant name, email, or any PII
  - AI reasoning or skill extraction output
  - Any sensitive personal information

PAYMENT REQUIREMENT:
  register_attestation() MUST be called in an atomic group where the first
  transaction is a PaymentTransaction sending ≥ min_fee µALGO to this
  contract's address.  The contract enforces this on-chain — there is no
  way to register an attestation without a valid, sufficient payment.
"""
import typing

from algopy import (
    ARC4Contract,
    Account,
    Bytes,
    Global,
    GlobalState,
    BoxMap,
    Txn,
    UInt64,
    gtxn,
    itxn,
)
from algopy.arc4 import (
    abimethod,
    String,
    UInt64 as arc4UInt64,
    Bool,
    Byte,
    StaticArray,
    Struct,
)


# ---------------------------------------------------------------------------
# ARC4 Data Types
# ---------------------------------------------------------------------------

class AttestationRecord(Struct):
    """
    ARC4 struct stored in Box Storage for each resume attestation.

    Stored as the value in a BoxMap keyed by
    (applicant_address_bytes || resume_sha256_hash_bytes).
    """
    role_id: String          # Short job role identifier (e.g. "backend-engineer")
    match_score: arc4UInt64  # Deterministic score 0–100 (computed off-chain by scoring engine)
    attestation_round: arc4UInt64  # Algorand round — serves as a trust-anchored timestamp
    fee_paid: arc4UInt64     # Real µALGO amount from the grouped PaymentTransaction


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

class ResumeVerifier(ARC4Contract):
    """
    ResumeVerifier — Resume Role Matcher on Algorand.

    Contract account accumulates attestation fees (0.5 ALGO per attestation).
    Admin (deployer) can withdraw accumulated fees via withdraw_fees().
    """

    def __init__(self) -> None:
        # Global state: administrator address (the deployer)
        self.admin = GlobalState(Account)

        # Global state: minimum µALGO required for attestation (default: 500_000)
        self.min_fee = GlobalState(UInt64)

        # Box storage: (applicant_bytes 32 + resume_hash_bytes 32) → AttestationRecord
        # key_prefix=b"" means the box name IS the raw 64-byte concatenated key
        self.attestations = BoxMap(Bytes, AttestationRecord, key_prefix=b"")

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    @abimethod(create="require")
    def bootstrap(self, min_fee: UInt64) -> None:
        """
        Initialize the contract on creation.  Must be the first call.
        Called by deploy_config.py immediately after contract creation.

        Args:
            min_fee: Minimum payment required to register an attestation, in µALGO.
                     For the MVP this is set to 500_000 (0.5 ALGO).
        """
        self.admin.value = Txn.sender
        self.min_fee.value = min_fee

    # -----------------------------------------------------------------------
    # Core: Attestation Registration
    # -----------------------------------------------------------------------

    @abimethod()
    def register_attestation(
        self,
        resume_hash: StaticArray[Byte, typing.Literal[32]],
        role_id: String,
        match_score: arc4UInt64,
        payment: gtxn.PaymentTransaction,
    ) -> String:
        """
        Register a resume–role match attestation on-chain.

        This method MUST be called as part of an atomic transaction group:
          Group[0]: PaymentTransaction → this contract address, ≥ min_fee µALGO
          Group[1]: ApplicationCallTransaction → this method

        The AVM enforces atomicity: if any assertion fails, BOTH transactions
        in the group are rejected and the payment is not made.

        Only the resume SHA-256 hash (not the resume content) and attestation
        metadata are stored on-chain.  No PII is stored.

        A second attestation for the same (applicant, resume_hash) pair will
        overwrite the previous record (e.g. re-attesting after a score update).

        Args:
            resume_hash:  SHA-256 hash of the resume file (exactly 32 bytes).
            role_id:      Short identifier for the job role (e.g. "backend-engineer").
            match_score:  Deterministic match score 0–100 computed by the scoring engine.
            payment:      Reference to the grouped PaymentTransaction (group index 0).

        Returns:
            "ATTESTED" on success.

        Reverts if:
            - payment.receiver ≠ this contract's address
            - payment.amount < min_fee
            - match_score > 100
        """
        # --- Payment receiver validation ---
        # The payment MUST go to this specific contract, not any other address.
        assert (
            payment.receiver == Global.current_application_address
        ), "Payment receiver must be this contract's address"

        # --- Payment amount validation ---
        # The payment MUST meet the minimum fee set at bootstrap time.
        # fee_paid stores the real amount from the actual PaymentTxn — not a boolean.
        assert (
            payment.amount >= self.min_fee.value
        ), "Payment amount is below the minimum attestation fee"

        # --- Score range validation ---
        assert match_score.as_uint64() <= UInt64(100), "Match score must be between 0 and 100"

        # --- Construct box key ---
        # Key = applicant wallet address bytes (32) + resume SHA-256 hash bytes (32) = 64 bytes
        # This uniquely identifies each (applicant, resume) attestation.
        box_key = Txn.sender.bytes + resume_hash.bytes

        # --- Write attestation record to Box Storage ---
        # Overwrites any existing record for this key (safe — allows re-attestation).
        self.attestations[box_key] = AttestationRecord(
            role_id=role_id,
            match_score=match_score,
            attestation_round=arc4UInt64(Global.round),
            fee_paid=arc4UInt64(payment.amount),  # Real µALGO from the PaymentTxn — not a flag
        )

        return String("ATTESTED")

    # -----------------------------------------------------------------------
    # Read: Verification Methods (readonly — no fees, anyone can call)
    # -----------------------------------------------------------------------

    @abimethod(readonly=True)
    def get_attestation(
        self,
        applicant: Account,
        resume_hash: StaticArray[Byte, typing.Literal[32]],
    ) -> AttestationRecord:
        """
        Retrieve the full attestation record for a given applicant and resume hash.

        Callable by anyone (employer, auditor, third party).
        Reverts if no attestation exists.

        Args:
            applicant:    Wallet address of the applicant who registered the attestation.
            resume_hash:  SHA-256 hash of the resume file (32 bytes).

        Returns:
            The AttestationRecord: role_id, match_score, attestation_round, fee_paid.
        """
        box_key = applicant.bytes + resume_hash.bytes
        assert (
            box_key in self.attestations
        ), "No attestation found for this applicant and resume hash"
        return self.attestations[box_key].copy()

    @abimethod(readonly=True)
    def verify_resume_hash(
        self,
        applicant: Account,
        resume_hash: StaticArray[Byte, typing.Literal[32]],
    ) -> Bool:
        """
        Quick existence check: does an attestation exist for this (applicant, resume_hash)?

        Does NOT revert — returns False if not found.
        Useful for a simple verified / not-verified badge in the employer UI.

        Args:
            applicant:    Wallet address of the applicant.
            resume_hash:  SHA-256 hash of the resume file (32 bytes).

        Returns:
            True if an attestation exists, False otherwise.
        """
        box_key = applicant.bytes + resume_hash.bytes
        return Bool(box_key in self.attestations)

    # -----------------------------------------------------------------------
    # Admin: Fee Withdrawal
    # -----------------------------------------------------------------------

    @abimethod()
    def withdraw_fees(self, amount: UInt64) -> None:
        """
        Admin-only: transfer accumulated attestation fees from the contract to admin.

        Sends an inner PaymentTransaction from the contract account to the admin address.
        Only the admin (the address set during bootstrap) may call this.

        Args:
            amount: Amount in µALGO to withdraw from the contract account.

        Reverts if:
            - Txn.sender ≠ admin
        """
        assert Txn.sender == self.admin.value, "Only the admin may withdraw fees"

        # Inner transaction: contract account → admin
        itxn.Payment(
            receiver=self.admin.value,
            amount=amount,
            fee=Global.min_txn_fee,
        ).submit()
