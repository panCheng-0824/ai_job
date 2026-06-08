#!/usr/bin/env bash
# 执行业务数据清空 SQL（默认仅预览连接与表行数，加 --execute 才真正删除）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_FILE="${ROOT}/sql/purge_business_data_mysql8.sql"

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-pc0824tq}"
MYSQL_DATABASE="${MYSQL_DATABASE:-app_db}"

EXECUTE=0
if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE=1
elif [[ -n "${1:-}" ]]; then
  echo "用法: $0 [--execute]" >&2
  echo "  省略参数：仅预览各表当前行数" >&2
  echo "  --execute：执行 purge_business_data_mysql8.sql（不可恢复）" >&2
  exit 1
fi

mysql_base=(mysql -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" --default-character-set=utf8mb4)

echo "目标库: ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}"
echo

preview_sql="
SELECT 'preview' AS phase,
       (SELECT COUNT(*) FROM t_biz_jobs_info)           AS jobs,
       (SELECT COUNT(*) FROM t_biz_company_info)        AS companies,
       (SELECT COUNT(*) FROM student_favorite_job)      AS favorite_jobs,
       (SELECT COUNT(*) FROM student_follow_company)    AS follow_companies,
       (SELECT COUNT(*) FROM student_job_review)        AS job_reviews,
       (SELECT COUNT(*) FROM student_company_review)    AS company_reviews,
       (SELECT COUNT(*) FROM student_resume)            AS resume_copies,
       (SELECT COUNT(*) FROM student_interview_records) AS interview_records,
       (SELECT COUNT(*) FROM interview_sessions)        AS interview_sessions;
"

"${mysql_base[@]}" -e "${preview_sql}"

if [[ "${EXECUTE}" -ne 1 ]]; then
  echo
  echo "未执行删除。确认后运行:"
  echo "  MYSQL_PASSWORD=*** bash ${ROOT}/scripts/run_purge_business_data.sh --execute"
  exit 0
fi

echo
echo ">>> 开始执行清空（不可恢复）..."
"${mysql_base[@]}" < "${SQL_FILE}"
echo ">>> 完成。"
