# ============================================================================
# FixionMail Process Configuration
# ============================================================================
#
# All services use the same entrypoint script (entrypoint.sh).
# Set SERVICE_TYPE environment variable in each Railway service to control
# which process runs:
#
#   SERVICE_TYPE=web       -> Web server (gunicorn/FastAPI)
#   SERVICE_TYPE=worker    -> RQ worker for story generation
#   SERVICE_TYPE=scheduler -> Daily story scheduler
#   SERVICE_TYPE=delivery  -> Email delivery scheduler
#
# ============================================================================

web: bash entrypoint.sh
