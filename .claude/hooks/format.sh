#!/bin/bash
# Claude'un yazdığı dosyayı biçimlendirir.
FILE=$(jq -r '.tool_input.file_path // empty')
case "$FILE" in
  *.py) cd "$CLAUDE_PROJECT_DIR/services/ai" && uv run ruff format -q "$FILE" ;;
  *.ts|*.tsx) cd "$CLAUDE_PROJECT_DIR/apps/web" && npx prettier --write --log-level warn "$FILE" ;;
esac
exit 0
