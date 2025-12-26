"""
Credit Service

Handles credit operations including balance management, transactions,
and subscription-related credit refreshes.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from supabase import Client

from .client import get_supabase_admin_client


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits."""
    pass


class CreditService:
    """
    Service class for credit operations.

    All credit modifications are logged in the credit_transactions table
    for audit purposes.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_supabase_admin_client()
        return self._client

    # =========================================================================
    # Credit Balance
    # =========================================================================

    async def get_balance(self, user_id: UUID | str) -> int:
        """Get user's current credit balance."""
        result = (
            self.client.table("users")
            .select("credits")
            .eq("id", str(user_id))
            .execute()
        )

        if not result.data:
            raise ValueError(f"User {user_id} not found")

        return result.data[0]["credits"]

    async def has_credits(self, user_id: UUID | str, amount: int = 1) -> bool:
        """Check if user has sufficient credits."""
        balance = await self.get_balance(user_id)
        return balance >= amount

    # =========================================================================
    # Credit Deductions (using database function)
    # =========================================================================

    async def deduct(
        self,
        user_id: UUID | str,
        amount: int,
        transaction_type: str,
        reference_id: Optional[UUID | str] = None,
        description: Optional[str] = None,
    ) -> int:
        """
        Deduct credits from user's balance.

        Uses the deduct_credits database function for atomicity.

        Args:
            user_id: User ID
            amount: Credits to deduct
            transaction_type: Type of deduction
                - 'story_generation': New story
                - 'retell_generation': Story revision
            reference_id: Related entity ID (e.g., story ID)
            description: Human-readable description

        Returns:
            New credit balance

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        # Call the database function
        result = self.client.rpc(
            "deduct_credits",
            {
                "p_user_id": str(user_id),
                "p_amount": amount,
                "p_transaction_type": transaction_type,
                "p_reference_id": str(reference_id) if reference_id else None,
                "p_description": description,
            }
        ).execute()

        # The function returns boolean - true if successful
        if not result.data:
            raise InsufficientCreditsError(
                f"User {user_id} has insufficient credits. "
                f"Required: {amount}"
            )

        # Get new balance
        return await self.get_balance(user_id)

    async def deduct_for_story(
        self,
        user_id: UUID | str,
        story_id: UUID | str,
        is_retell: bool = False,
    ) -> int:
        """
        Deduct credits for story generation.

        Args:
            user_id: User ID
            story_id: Generated story ID
            is_retell: Whether this is a retell

        Returns:
            New credit balance
        """
        transaction_type = "retell_generation" if is_retell else "story_generation"
        description = f"{'Retell' if is_retell else 'New story'} generation"

        return await self.deduct(
            user_id=user_id,
            amount=1,
            transaction_type=transaction_type,
            reference_id=story_id,
            description=description,
        )

    # =========================================================================
    # Credit Additions (using database function)
    # =========================================================================

    async def add(
        self,
        user_id: UUID | str,
        amount: int,
        transaction_type: str,
        reference_id: Optional[UUID | str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add credits to user's balance.

        Uses the add_credits database function for atomicity.

        Args:
            user_id: User ID
            amount: Credits to add
            transaction_type: Type of addition
                - 'subscription_refresh': Monthly subscription refresh
                - 'credit_pack_purchase': One-time purchase
                - 'hallucination_reward': Reward for finding hallucination
                - 'manual_adjustment': Admin adjustment
                - 'rollover': Credits rolled over from previous period
            reference_id: Related entity ID
            description: Human-readable description
            metadata: Additional metadata (e.g., Stripe payment details)

        Returns:
            New credit balance
        """
        result = self.client.rpc(
            "add_credits",
            {
                "p_user_id": str(user_id),
                "p_amount": amount,
                "p_transaction_type": transaction_type,
                "p_reference_id": str(reference_id) if reference_id else None,
                "p_description": description,
                "p_metadata": metadata,
            }
        ).execute()

        return result.data  # Returns new balance

    async def add_subscription_credits(
        self,
        user_id: UUID | str,
        tier: str,
        stripe_invoice_id: Optional[str] = None,
    ) -> int:
        """
        Add monthly subscription credits.

        Also handles rollover from previous month.

        Args:
            user_id: User ID
            tier: 'monthly' or 'annual'
            stripe_invoice_id: Stripe invoice ID for reference

        Returns:
            New credit balance
        """
        # Monthly credits for both tiers
        credits_to_add = 15

        return await self.add(
            user_id=user_id,
            amount=credits_to_add,
            transaction_type="subscription_refresh",
            description=f"Monthly credit refresh ({tier} subscription)",
            metadata={
                "tier": tier,
                "stripe_invoice_id": stripe_invoice_id,
            } if stripe_invoice_id else None,
        )

    async def add_credit_pack(
        self,
        user_id: UUID | str,
        pack_size: int,
        stripe_payment_id: str,
        amount_paid_cents: int,
    ) -> int:
        """
        Add credits from credit pack purchase.

        Args:
            user_id: User ID
            pack_size: Number of credits purchased (5, 10, or 20)
            stripe_payment_id: Stripe payment intent ID
            amount_paid_cents: Amount paid in cents

        Returns:
            New credit balance
        """
        return await self.add(
            user_id=user_id,
            amount=pack_size,
            transaction_type="credit_pack_purchase",
            description=f"Credit pack purchase ({pack_size} credits)",
            metadata={
                "pack_size": pack_size,
                "stripe_payment_id": stripe_payment_id,
                "amount_paid_cents": amount_paid_cents,
            },
        )

    async def add_hallucination_reward(
        self,
        user_id: UUID | str,
        hallucination_id: UUID | str,
        amount: int = 1,
    ) -> int:
        """
        Award credits for finding a hallucination.

        Args:
            user_id: User ID
            hallucination_id: Hallucination record ID
            amount: Credits to award (default 1)

        Returns:
            New credit balance
        """
        return await self.add(
            user_id=user_id,
            amount=amount,
            transaction_type="hallucination_reward",
            reference_id=hallucination_id,
            description="Reward for finding a story hallucination",
        )

    # =========================================================================
    # Transaction History
    # =========================================================================

    async def get_transactions(
        self,
        user_id: UUID | str,
        *,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get user's credit transaction history.

        Args:
            user_id: User ID
            limit: Max transactions to return
            offset: Pagination offset
            transaction_type: Filter by type

        Returns:
            List of transactions, newest first
        """
        query = (
            self.client.table("credit_transactions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        if transaction_type:
            query = query.eq("transaction_type", transaction_type)

        result = query.execute()
        return result.data

    async def get_usage_summary(
        self,
        user_id: UUID | str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get credit usage summary for a period.

        Args:
            user_id: User ID
            days: Number of days to summarize

        Returns:
            Usage summary including totals by type
        """
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = (
            self.client.table("credit_transactions")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("created_at", since.isoformat())
            .execute()
        )

        transactions = result.data

        # Calculate summaries
        credits_used = sum(
            abs(t["amount"]) for t in transactions if t["amount"] < 0
        )
        credits_added = sum(
            t["amount"] for t in transactions if t["amount"] > 0
        )

        by_type = {}
        for t in transactions:
            tx_type = t["transaction_type"]
            if tx_type not in by_type:
                by_type[tx_type] = {"count": 0, "amount": 0}
            by_type[tx_type]["count"] += 1
            by_type[tx_type]["amount"] += t["amount"]

        return {
            "period_days": days,
            "credits_used": credits_used,
            "credits_added": credits_added,
            "net_change": credits_added - credits_used,
            "transaction_count": len(transactions),
            "by_type": by_type,
        }

    # =========================================================================
    # Credit Pack Definitions
    # =========================================================================

    @staticmethod
    def get_credit_packs() -> List[Dict[str, Any]]:
        """Get available credit pack options."""
        return [
            {
                "size": 5,
                "price_cents": 449,
                "price_display": "$4.49",
                "per_credit": "$0.90",
                "savings": "10% off",
            },
            {
                "size": 10,
                "price_cents": 799,
                "price_display": "$7.99",
                "per_credit": "$0.80",
                "savings": "20% off",
            },
            {
                "size": 20,
                "price_cents": 1499,
                "price_display": "$14.99",
                "per_credit": "$0.75",
                "savings": "25% off",
            },
        ]
