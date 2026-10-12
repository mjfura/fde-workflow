#!/bin/sh
# Tests for the hook wrapper. Run: sh plugin/hooks/test_fde_hook.sh
set -u
HOOK="$(cd "$(dirname "$0")" && pwd)/fde-hook"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
failures=0

check() {  # check NAME EXPECTED_OUTPUT PATH_VALUE
  name=$1 want=$2
  got=$(printf '{"cwd": "/tmp"}' | PATH="$3" sh "$HOOK" session-start 2>/dev/null)
  code=$?
  if [ "$code" -ne 0 ] || [ "$got" != "$want" ]; then
    echo "FAIL: $name (exit $code, output: $got)"
    failures=$((failures + 1))
  else
    echo "ok: $name"
  fi
}

check "silent without the CLI" "" "/usr/bin:/bin"

mkdir -p "$WORK/bin"
printf '#!/bin/sh\necho "args=$*"; cat\n' > "$WORK/bin/fde-workflow"
chmod 755 "$WORK/bin/fde-workflow"
check "passes the event and stdin to the CLI" 'args=hook session-start
{"cwd": "/tmp"}' "$WORK/bin:/usr/bin:/bin"

printf '#!/bin/sh\nexit 3\n' > "$WORK/bin/fde-workflow"
check "exits 0 when the CLI fails" "" "$WORK/bin:/usr/bin:/bin"

if [ "$failures" -eq 0 ]; then echo "all hook tests passed"; else echo "$failures failure(s)"; exit 1; fi
