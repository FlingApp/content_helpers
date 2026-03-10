@echo off
setlocal
set "HAS_CHANGES="
for /f "delims=" %%i in ('git status --porcelain 2^>nul') do set "HAS_CHANGES=1"
if defined HAS_CHANGES (
  echo 🛑 Есть локальные изменения. >&2
  echo 🛑 Выполните: git reset --hard (сбросить) или git stash (сохранить временно) >&2
  exit /b 1
)
echo 🔄 Синхронизация...
git fetch
git pull
echo ✅ Синхронизация завершена
exit /b 0
