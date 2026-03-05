#!/bin/bash
if [ -n "$(git status --porcelain)" ]; then
  echo "🛑 Есть локальные изменения." >&2
  echo "🛑 Выполните: git reset --hard (сбросить) или git stash (сохранить временно)" >&2
  exit 1
fi
echo "🔄 Синхронизация..."
git status; git fetch; git pull; 
echo "✅ Синхронизация завершена"