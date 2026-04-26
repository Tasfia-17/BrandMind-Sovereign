"""
x402 payment flow for sub-agent hiring.

Uses the real x402 open protocol (coinbase/x402).
No FluxA dependency — works standalone with any EVM wallet.

Install: pip install x402[httpx,evm]
"""
from __future__ import annotations

import os
import uuid
from typing import Any

# x402 is optional — graceful fallback if not installed
try:
    from x402 import x402ResourceServerSync, ResourceConfig
    from x402.http import HTTPFacilitatorClientSync
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    _X402_AVAILABLE = True
except ImportError:
    _X402_AVAILABLE = False

WALLET_ADDRESS = os.getenv("EVM_WALLET_ADDRESS", "")
FACILITATOR_URL = "https://x402.org/facilitator"  # Coinbase's public facilitator


def create_payment_mandate(amount_usd: float, description: str) -> dict[str, Any]:
    """
    Create an x402 payment mandate for a specialist sub-agent.

    Returns a mandate dict that can be embedded in an AgentHansa task post.
    The specialist agent pays this mandate to claim the task.
    """
    if not _X402_AVAILABLE or not WALLET_ADDRESS:
        # Graceful fallback — return a simulated mandate for demo
        return {
            "protocol": "x402",
            "scheme": "exact",
            "network": "eip155:8453",  # Base mainnet
            "pay_to": WALLET_ADDRESS or "0x0000000000000000000000000000000000000000",
            "amount_usd": amount_usd,
            "description": description,
            "mandate_id": str(uuid.uuid4()),
            "status": "simulated" if not WALLET_ADDRESS else "ready",
            "facilitator": FACILITATOR_URL,
        }

    facilitator = HTTPFacilitatorClientSync(url=FACILITATOR_URL)
    server = x402ResourceServerSync(facilitator)
    server.register("eip155:*", ExactEvmServerScheme())
    server.initialize()

    config = ResourceConfig(
        scheme="exact",
        network="eip155:8453",
        pay_to=WALLET_ADDRESS,
        price=f"${amount_usd:.2f}",
    )
    requirements = server.build_payment_requirements(config)

    return {
        "protocol": "x402",
        "scheme": "exact",
        "network": "eip155:8453",
        "pay_to": WALLET_ADDRESS,
        "amount_usd": amount_usd,
        "description": description,
        "mandate_id": str(uuid.uuid4()),
        "payment_requirements": requirements[0] if requirements else None,
        "facilitator": FACILITATOR_URL,
        "status": "ready",
    }


def verify_payment(payment_payload: str, mandate: dict) -> bool:
    """Verify that a specialist agent has paid the mandate."""
    if not _X402_AVAILABLE or mandate.get("status") == "simulated":
        return True  # demo mode

    facilitator = HTTPFacilitatorClientSync(url=FACILITATOR_URL)
    server = x402ResourceServerSync(facilitator)
    server.register("eip155:*", ExactEvmServerScheme())
    server.initialize()

    requirements = mandate.get("payment_requirements")
    if not requirements:
        return False

    result = server.verify_payment(payment_payload, requirements)
    return result.is_valid
