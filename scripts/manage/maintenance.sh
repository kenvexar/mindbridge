# shellcheck shell=bash

cmd_ar_clean() {
  require_cmd gcloud jq
  local PROJECT_ID=${1:-}
  local REGION=${2:-us-central1}
  local REPO=${3:-mindbridge}
  local IMAGE=${4:-mindbridge}
  local KEEP=${5:-10}
  local OLDER_DAYS=${6:-30}
  local DRY_RUN=true
  [[ " $* " == *" --no-dry-run "* ]] && DRY_RUN=false
  if [[ -z "$PROJECT_ID" ]]; then
    die "Usage: mindbridge ar-clean <PROJECT_ID> [REGION] [REPO] [IMAGE] [KEEP] [OLDER_DAYS] [--no-dry-run]"
  fi
  local AR_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}"
  printf "%s\n" "[INFO] 対象: ${AR_PATH} KEEP=${KEEP} OLDER_THAN=${OLDER_DAYS}d DRY_RUN=${DRY_RUN}"
  local IMAGES_JSON
  IMAGES_JSON=$(gcloud artifacts docker images list "$AR_PATH" --include-tags --format=json || echo '[]')
  local COUNT
  COUNT=$(echo "$IMAGES_JSON" | jq 'length')
  (( COUNT == 0 )) && { printf "%s\n" "[INFO] 対象なし"; return 0; }
  local DELETABLE_DIGESTS
  DELETABLE_DIGESTS=$(echo "$IMAGES_JSON" | jq -r --argjson keep "$KEEP" --argjson older "$OLDER_DAYS" '
    map({digest, created: (.createTime | fromdateiso8601)}) as $imgs
    | ($imgs | sort_by(.created) | reverse | .[:$keep] | map(.digest)) as $keep_digests
    | $imgs | map(select(.created < (now - ($older*86400))))
    | map(select(.digest as $d | ($keep_digests | index($d)) | not))
    | .[] | .digest')
  [[ -z "$DELETABLE_DIGESTS" ]] && { printf "%s\n" "[INFO] 条件により削除対象なし"; return 0; }
  printf "%s\n" "[PLAN] 削除予定:"
  while read -r d; do
    [[ -n "$d" ]] && printf "  - %s\n" "${AR_PATH}@${d}"
  done <<< "$DELETABLE_DIGESTS"
  [[ "$DRY_RUN" == true ]] && { printf "%s\n" "[DRY-RUN] --no-dry-run で実行"; return 0; }
  printf "%s\n" "[EXEC] 削除実行..."
  local FAILED=0
  while read -r d; do
    [[ -z "$d" ]] && continue
    gcloud artifacts docker images delete "${AR_PATH}@${d}" --quiet || FAILED=$((FAILED+1))
  done <<< "$DELETABLE_DIGESTS"
  if (( FAILED > 0 )); then
    printf "%s\n" "[DONE] 完了（失敗: $FAILED）"
    return 1
  else
    printf "%s\n" "[DONE] クリーンアップ完了"
  fi
}
