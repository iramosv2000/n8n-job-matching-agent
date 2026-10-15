#!/usr/bin/env bash
# Create .env from .env.example, replacing every "change-me" with a random secret.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env && "${1:-}" != "--force" ]]; then
  echo ".env already exists; refusing to overwrite (use --force to regenerate secrets)." >&2
  exit 1
fi

tmp="$(mktemp)"
while IFS= read -r line; do
  if [[ "$line" == *"=change-me" ]]; then
    echo "${line%change-me}$(openssl rand -hex 32)"
  else
    echo "$line"
  fi
done < .env.example > "$tmp"
mv "$tmp" .env
chmod 600 .env

echo "Created .env with random secrets."
echo "Back up N8N_ENCRYPTION_KEY outside Git now (see infra/README.md)."
