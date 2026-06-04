"""Scheduled background jobs for GPMS integration.

- hums_poll: GET /user/assets/{id} per active mapping (default every 600s)
- fdm_poll: incremental exportstates ingest per active mapping (default every 600s)
- token_renewal: proactive GPMS JWT refresh (default every 7 days)

See README.md for poll behavior and mapping scope.
"""
