# Dispatcharr Homepage Widget (Dynamic List)

Homepage widget for Dispatcharr with an auto-refreshing status proxy.

This setup uses a small proxy to fetch Dispatcharr status and auto-refresh the
JWT token. Homepage then reads the proxy endpoint and renders all active
streams as a dynamic list.

## Files

- `dispatcharr-proxy.py`: Minimal HTTP proxy with token refresh.
- `docker-compose.yml`: Example container for the proxy.
- `services.yaml`: Homepage widget snippet.

## Usage

1) Set your Dispatcharr URL and credentials in the compose file.
2) Run the proxy container.
3) Add the `services.yaml` widget block to your Homepage config.

## Environment Variables

- `DISPATCHARR_BASE_URL` (required)
- `DISPATCHARR_USERNAME` (required)
- `DISPATCHARR_PASSWORD` (required)
- `DISPATCHARR_STATUS_PATH` (optional)
- `DISPATCHARR_TOKEN_PATH` (optional)
- `DISPATCHARR_REFRESH_PATH` (optional)
- `DISPATCHARR_PROXY_HOST` (optional)
- `DISPATCHARR_PROXY_PORT` (optional)

## Notes

- The proxy listens on `/status` and returns the upstream JSON as-is.
- Homepage should be on the same Docker network to reach `dispatcharr-proxy`.
- Use secrets or an `.env` file for credentials; do not hardcode them in git.
