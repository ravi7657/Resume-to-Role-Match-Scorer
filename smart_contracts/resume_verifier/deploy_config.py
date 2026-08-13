import logging

import algokit_utils

logger = logging.getLogger(__name__)

MIN_ATTESTATION_FEE = 500_000  # 0.5 ALGO in µALGO


# define deployment behaviour based on supplied app spec
def deploy() -> None:
    from smart_contracts.artifacts.resume_verifier.resume_verifier_client import (
        BootstrapArgs,
        ResumeVerifierFactory,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer_ = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        ResumeVerifierFactory, default_sender=deployer_.address
    )

    # Deploy (or find existing) contract; bootstrap() is called on creation via create_params.
    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
        create_params=algokit_utils.AppClientMethodCallCreateParams(
            method="bootstrap(uint64)void",
            args=[MIN_ATTESTATION_FEE],
        ),
    )

    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        # Fund the contract account with 1 ALGO to cover box MBR and inner txn fees.
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer_.address,
                receiver=app_client.app_address,
            )
        )
        logger.info(
            f"Deployed ResumeVerifier (app_id={app_client.app_id}) "
            f"at {app_client.app_address} with min_fee={MIN_ATTESTATION_FEE} µALGO"
        )
    else:
        logger.info(
            f"ResumeVerifier already deployed (app_id={app_client.app_id}) "
            f"at {app_client.app_address}"
        )
