#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Checking DNS resolution for github.com"
if getent hosts github.com >/dev/null 2>&1; then
  echo "PASS: getent resolved github.com"
  getent hosts github.com | head -n 3
else
  echo "FAIL: getent could not resolve github.com"
fi

echo "[2/5] Showing resolver config"
if [ -f /etc/resolv.conf ]; then
  cat /etc/resolv.conf
else
  echo "WARN: /etc/resolv.conf not found"
fi

echo "[3/5] Trying nslookup (if available)"
if command -v nslookup >/dev/null 2>&1; then
  nslookup github.com || true
else
  echo "WARN: nslookup not installed"
fi

echo "[4/5] Trying curl to github.com (if available)"
if command -v curl >/dev/null 2>&1; then
  curl -I --max-time 10 https://github.com || true
else
  echo "WARN: curl not installed"
fi

echo "[5/5] Trying git ls-remote"
git ls-remote https://github.com/Kariembassam/3DGaussian-test.git || true

echo "Done. If DNS resolution failed, this is an infra/network issue in the pod, not a repo code issue."
