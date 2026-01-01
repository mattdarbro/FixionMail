"""
Email module for FixionMail.
Handles email delivery via Resend at scheduled times.

The DeliveryWorker sends emails from the scheduled_deliveries queue.
Story generation is decoupled from email delivery.
"""

from backend.email.delivery_worker import (
    DeliveryWorker,
    start_delivery_worker,
    stop_delivery_worker,
    get_delivery_worker
)

__all__ = [
    "DeliveryWorker",
    "start_delivery_worker",
    "stop_delivery_worker",
    "get_delivery_worker",
]
