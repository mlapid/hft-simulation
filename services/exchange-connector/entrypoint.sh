#!/bin/bash
set -e

# echo "⏳ Running startup tests..."
# uv run pytest /app/libs/common/tests/settings_test.py

# echo "✅ Tests passed, starting exchange-connector..."
exec uv run --no-sync exchange-connector