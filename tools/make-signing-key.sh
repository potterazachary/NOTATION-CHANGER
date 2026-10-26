#!/usr/bin/env bash
# Creates the permanent key that signs every Klavar build, so new versions
# install over old ones. Run once, in your Codespace:  bash tools/make-signing-key.sh
set -e
OUT=signing-key-base64.txt
if [ -f klavar-debug.keystore ]; then echo "A key already exists (klavar-debug.keystore). Not replacing it."; else
  keytool -genkeypair -v -keystore klavar-debug.keystore -storepass android -alias androiddebugkey \
    -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi
base64 -w0 klavar-debug.keystore > "$OUT"
if command -v gh >/dev/null && gh secret set ANDROID_DEBUG_KEYSTORE < "$OUT" 2>/dev/null; then
  echo "Saved as the ANDROID_DEBUG_KEYSTORE secret automatically."
else
  echo
  echo "Now add it as a secret by hand:"
  echo "  1. Open $OUT in the editor, select all, copy."
  echo "  2. On GitHub: repo Settings > Secrets and variables > Actions > New repository secret."
  echo "  3. Name: ANDROID_DEBUG_KEYSTORE   Secret: paste."
fi
echo
echo "Keep klavar-debug.keystore somewhere safe (download it). Losing it means reinstalling the app once."
