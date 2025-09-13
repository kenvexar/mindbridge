#!/usr/bin/env bash

# Artifact Registry の古い Docker イメージをクリーンアップ
# 使い方:
#   ./scripts/cleanup-artifact-registry.sh <PROJECT_ID> [REGION] [REPO] [IMAGE] [KEEP] [OLDER_DAYS] [--no-dry-run]
# 例:
#   ./scripts/cleanup-artifact-registry.sh my-proj us-central1 mindbridge mindbridge 10 30 --no-dry-run

set -euo pipefail

PROJECT_ID=${1:-}
REGION=${2:-us-central1}
REPO=${3:-mindbridge}
IMAGE=${4:-mindbridge}
KEEP=${5:-10}
OLDER_DAYS=${6:-30}
DRY_RUN=true

if [[ "$*" == *"--no-dry-run"* ]]; then
  DRY_RUN=false
fi

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <PROJECT_ID> [REGION] [REPO] [IMAGE] [KEEP] [OLDER_DAYS] [--no-dry-run]" >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI が見つかりません。インストールしてください。" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq が見つかりません。インストールしてください。" >&2
  exit 1
fi

AR_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}"

echo "[INFO] 対象: ${AR_PATH} / KEEP=${KEEP} / OLDER_THAN=${OLDER_DAYS}d / DRY_RUN=${DRY_RUN}"

# 画像一覧取得（JSON）
IMAGES_JSON=$(gcloud artifacts docker images list "${AR_PATH}" \
  --include-tags \
  --format=json || echo '[]')

COUNT=$(echo "$IMAGES_JSON" | jq 'length')
echo "[INFO] 総イメージ数: ${COUNT}"

if [[ "$COUNT" -eq 0 ]]; then
  echo "[INFO] 対象イメージがありません。"
  exit 0
fi

# 削除対象の digest を算出
DELETABLE_DIGESTS=$(echo "$IMAGES_JSON" | jq -r --argjson keep "$KEEP" --argjson older "$OLDER_DAYS" '
  map({digest, created: (.createTime | fromdateiso8601), tags: (.tags // [])}) as $imgs
  | ($imgs | sort_by(.created) | reverse | .[:$keep] | map(.digest)) as $keep_digests
  | $imgs
  | map(select(.created < (now - ($older*86400))))
  | map(select(.digest as $d | ($keep_digests | index($d)) | not))
  | .[] | .digest
')

if [[ -z "$DELETABLE_DIGESTS" ]]; then
  echo "[INFO] 削除対象はありません（保持数/日数条件によりゼロ）。"
  exit 0
fi

echo "[PLAN] 削除予定:")
while read -r DIGEST; do
  [[ -z "$DIGEST" ]] && continue
  echo "  - ${AR_PATH}@${DIGEST}"
done <<< "$DELETABLE_DIGESTS"

if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY-RUN] 実際の削除は行いません。--no-dry-run を付けると削除します。"
  exit 0
fi

echo "[EXEC] 削除を実行します..."
FAILED=0
while read -r DIGEST; do
  [[ -z "$DIGEST" ]] && continue
  IMG_REF="${AR_PATH}@${DIGEST}"
  if gcloud artifacts docker images delete "$IMG_REF" --quiet; then
    echo "[OK] $IMG_REF"
  else
    echo "[WARN] 削除失敗: $IMG_REF" >&2
    FAILED=$((FAILED+1))
  fi
done <<< "$DELETABLE_DIGESTS"

if [[ "$FAILED" -gt 0 ]]; then
  echo "[DONE] 完了（失敗: $FAILED）"
  exit 1
fi

echo "[DONE] クリーンアップ完了"
