#!/usr/bin/env bash
set -Eeuo pipefail

# MindBridge 統合 CLI（サブコマンドで操作を集約）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/manage"

# shellcheck source=scripts/manage/_common.sh
source "${MODULE_DIR}/_common.sh"
# shellcheck source=scripts/manage/env.sh
source "${MODULE_DIR}/env.sh"
# shellcheck source=scripts/manage/secrets.sh
source "${MODULE_DIR}/secrets.sh"
# shellcheck source=scripts/manage/optional.sh
source "${MODULE_DIR}/optional.sh"
# shellcheck source=scripts/manage/deploy.sh
source "${MODULE_DIR}/deploy.sh"
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

  env <PROJECT_ID>                 Google Cloud 環境セットアップ
  secrets <PROJECT_ID> [FLAGS]     必須/オプションシークレット設定（env 後に実行）
  optional <PROJECT_ID>            カレンダー/ウェブフックなど追加設定（secrets 後）
  deploy <PROJECT_ID> [REGION]     Cloud Run デプロイ（secrets/optional 完了後）
  deploy-precheck <PROJECT_ID> [FLAGS]
                                   デプロイ前チェック（テスト/Secret/GCP 権限）
  deploy-auto <PROJECT_ID> [REGION] [FLAGS]
                                   precheck → deploy を一括実行
  full-deploy <PROJECT_ID> [FLAGS] env→secrets→optional→deploy を一括実行
  ar-clean <PROJECT_ID> [...]      Artifact Registry の古いイメージ削除（運用メンテ）

例:
  ./scripts/manage.sh init
  ./scripts/manage.sh run
  ./scripts/manage.sh env my-proj
  ./scripts/manage.sh secrets my-proj --with-optional --skip-existing
  ./scripts/manage.sh deploy my-proj us-central1
USAGE
}

cmd=${1:-help}
shift || true

case "$cmd" in
  help|-h|--help)
    usage
    ;;
  env)
    cmd_env "$@"
    ;;
  secrets)
    cmd_secrets "$@"
    ;;
  optional)
    cmd_optional "$@"
    ;;
  deploy)
    cmd_deploy "$@"
    ;;
  deploy-precheck)
    cmd_deploy_precheck "$@"
    ;;
  deploy-auto)
    cmd_deploy_auto "$@"
    ;;
  full-deploy)
    cmd_full_deploy "$@"
    ;;
  ar-clean)
    cmd_ar_clean "$@"
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
