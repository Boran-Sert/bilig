#!/bin/bash
# Korunan dosyalarda düzenlemeyi engeller.
command -v jq >/dev/null || { echo "jq kurulu değil (Windows: winget install jqlang.jq)" >&2; exit 2; }
FILE=$(jq -r '.tool_input.file_path // empty')
FILE=${FILE//\\//}
deny() { echo "Korunan dosya: $FILE ($1)" >&2; exit 2; }
case "$FILE" in
  */.env.example) exit 0 ;;
  */.env|*/.env.*) deny "gizli değerler" ;;
  */schema.d.ts|*/components/ui/*) deny "üretilen dosya" ;;
  */uv.lock|*/package-lock.json) deny "kilit dosyası" ;;
esac
if [[ "$FILE" == */db/migration/* && -e "$FILE" ]]; then
  deny "uygulanmış migration; yeni dosya ekle"
fi
exit 0
