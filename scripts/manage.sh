#!/usr/bin/env bash
set -Eeuo pipefail

# MindBridge 統合 CLI（サブコマンドで操作を集約）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/manage"

# shellcheck source=scripts/manage/_common.sh
source "${MODULE_DIR}/_common.sh"
# shellcheck source=scripts/manage/maintenance.sh
source "${MODULE_DIR}/maintenance.sh"
# shellcheck source=scripts/manage/local.sh
source "${MODULE_DIR}/local.sh"

ensure_repo_root

usage() {
  cat <<USAGE
MindBridge CLI

サブコマンド (実行順の目安):
  help                             このヘルプ

  init                             ローカル初期設定（.env 生成）
  clean [--with-uv-cache]          Pythonキャッシュ削除
  run                              ローカル起動（uv 使用）


例:
  ./scripts/manage.sh init
  ./scripts/manage.sh run
  ./scripts/manage.sh clean --with-uv-cache
USAGE
}

cmd=${1:-help}
shift || true

case "$cmd" in
  help|-h|--help)
    usage
    ;;
  clean)
    cmd_clean "$@"
    ;;
  init)
    cmd_init "$@"
    ;;
  run)
    cmd_run "$@"
    ;;
  *)
    warn "未知のコマンド: $cmd"
    usage
    exit 2
    ;;
esac
