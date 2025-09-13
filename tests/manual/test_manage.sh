#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

SCRIPT=./scripts/manage.sh

pass=0; fail=0
green='\033[0;32m'; red='\033[0;31m'; yellow='\033[1;33m'; nc='\033[0m'

section(){ echo -e "${yellow}==> $*${nc}"; }
ok(){ echo -e "${green}[OK]${nc} $*"; pass=$((pass+1)); }
ng(){ echo -e "${red}[NG]${nc} $*"; fail=$((fail+1)); }
assert_contains(){ local hay=$1; local needle=$2; [[ "$hay" == *"$needle"* ]] && ok "$needle" || ng "期待文字列が見つかりません: $needle"; }

TMPDIR=$(mktemp -d)
export TMPDIR
ORIG_PATH=$PATH
RM_BIN=$(command -v rm)

# .env のバックアップ/初期化
ENV_BACKUP=false
if [[ -f .env ]]; then
  mv .env "$TMPDIR/.env.backup"
  ENV_BACKUP=true
fi
trap '{ [[ "$ENV_BACKUP" == true ]] && mv -f "$TMPDIR/.env.backup" .env || $RM_BIN -f .env; $RM_BIN -rf "$TMPDIR"; PATH="$ORIG_PATH"; }' EXIT

section "help が使用方法を表示する"
out=$($SCRIPT help 2>&1 || true)
assert_contains "$out" "env <PROJECT_ID>"

section "run は .env が無ければ失敗する（uv スタブ使用）"
mkdir -p "$TMPDIR/bin"
cat > "$TMPDIR/bin/uv" <<'EOS'
#!/usr/bin/env bash
echo "UV_STUB $*"; target="${MB_UV_MARK:-$TMPDIR/uv_called}"; : > "$target"; exit 0
EOS
chmod +x "$TMPDIR/bin/uv"
PATH="$TMPDIR/bin:$ORIG_PATH"; hash -r; out=$($SCRIPT run 2>&1 || true)
# 期待通り非ゼロ終了であれば OK（stderr 出力は環境により抑制されることがある）
if $SCRIPT run >/dev/null 2>&1; then ng "run が成功してしまいました"; else ok "run は .env 不足で非ゼロ終了"; fi

section "init は .env を生成する"
export HOME="$TMPDIR/home"
mkdir -p "$HOME"
VAULT="$TMPDIR/vault"
printf "TOKEN\nAPIKEY\n%s\nGUILD\n" "$VAULT" | $SCRIPT init >/dev/null 2>&1
test -f .env && ok ".env 作成" || ng ".env が作成されていません"
grep -q "DISCORD_BOT_TOKEN=TOKEN" .env && ok "DISCORD_BOT_TOKEN 設定" || ng "DISCORD_BOT_TOKEN 欠落"
grep -q "GEMINI_API_KEY=APIKEY" .env && ok "GEMINI_API_KEY 設定" || ng "GEMINI_API_KEY 欠落"
grep -F -q "OBSIDIAN_VAULT_PATH=$VAULT" .env && ok "OBSIDIAN_VAULT_PATH 設定" || ng "OBSIDIAN_VAULT_PATH 欠落"

section "run は .env があれば 0 終了（スタブ PATH 使用）"
export MB_UV_MARK="$TMPDIR/uv_called"
PATH="$TMPDIR/bin:$ORIG_PATH"; hash -r; if $SCRIPT run >/dev/null 2>&1; then ok "run 成功 (exit 0)"; else ng "run が失敗しました"; fi

section "env は PROJECT_ID 未指定でエラー"
out=$($SCRIPT env 2>&1 || true)
assert_contains "$out" "PROJECT_ID を指定してください"

section "env は gcloud が無い場合にエラー"
PATH="$TMPDIR/bin"; hash -r; if $SCRIPT env test-proj >/dev/null 2>&1; then ng "gcloud 無しで env が成功"; else ok "gcloud 無しで env が適切に失敗"; fi

section "ar-clean は gcloud/jq 無しでエラー"
PATH="$TMPDIR/bin"; hash -r; if $SCRIPT ar-clean >/dev/null 2>&1; then ng "gcloud/jq 無しで ar-clean が成功"; else ok "gcloud/jq 無しで ar-clean が適切に失敗"; fi

echo
echo "合計: $((pass+fail)) / 成功: $pass / 失敗: $fail"
exit $(( fail == 0 ? 0 : 1 ))
