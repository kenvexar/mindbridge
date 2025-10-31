# shellcheck shell=bash

if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

log__base() {
  local tag=$1
  shift || true
  if (($#)); then
    printf "%b " "$tag"
    printf "%s" "$1"
    shift || true
    while (($#)); do
      printf " %s" "$1"
      shift
    done
    printf "\n"
  else
    printf "%b\n" "$tag"
  fi
}
log()         { log__base "${GREEN}[INFO]${NC}" "$@"; }
warn()        { log__base "${YELLOW}[WARN]${NC}" "$@"; }
log_step()    { log__base "${CYAN}[STEP]${NC}" "$@"; }
log_success() { log__base "${GREEN}[SUCCESS]${NC}" "$@"; }
log_error()   { log__base "${RED}[ERROR]${NC}" "$@" >&2; }
die()         { log_error "$@"; exit 1; }

require_cmd() {
  local missing=()
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || missing+=("$c")
  done
  if (( ${#missing[@]} )); then
    die "必要なコマンドが見つかりません: ${missing[*]}"
  fi
}

ensure_repo_root() {
  local root_dir
  root_dir=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
  cd "$root_dir" || die "リポジトリルートへ移動できません"
}

ensure_gcloud_auth() {
  require_cmd gcloud
  gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1 >/dev/null 2>&1 || \
    die "gcloud 未認証。'gcloud auth login' を実行してください"
}

ensure_project_id() {
  if [[ -z "${PROJECT_ID:-}" ]]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
  fi
  [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID が未設定です。引数または 'gcloud config set project' で指定してください"
}

confirm() {
  local msg=${1:-"続行しますか?"}
  read -r -p "$msg [y/N] " yn
  [[ "$yn" =~ ^[Yy]$ ]]
}
