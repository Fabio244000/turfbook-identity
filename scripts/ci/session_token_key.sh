#!/usr/bin/env bash
# A throwaway RSA key pair for this CI run only: Settings requires a signing key for the
# session token, and no real key ever reaches CI.
set -euo pipefail

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$RUNNER_TEMP/jwt.pem"
{
  echo 'JWT_PRIVATE_KEY<<EOF'
  cat "$RUNNER_TEMP/jwt.pem"
  echo 'EOF'
} >> "$GITHUB_ENV"
