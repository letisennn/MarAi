#!/usr/bin/env bash
# Kör EN gång efter att du skapat ett tomt privat GitHub-repo.
#   ./deploy.sh https://github.com/<du>/marc-ai.git
# Funkar med en Personal Access Token i URL:en om du inte har SSH-nyckel:
#   ./deploy.sh https://<TOKEN>@github.com/<du>/marc-ai.git
set -euo pipefail

REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  echo "Ge repo-URL:en som argument. Se kommentaren högst upp i filen." >&2
  exit 1
fi

cd "$(dirname "$0")"

git config user.name  >/dev/null 2>&1 || git config user.name  "Jonas"
git config user.email >/dev/null 2>&1 || git config user.email "jonassitell06@gmail.com"

git remote remove origin 2>/dev/null || true
git remote add origin "$REPO"
git branch -M main
git push -u origin main

cat <<'DONE'

Pushat. Nästa steg (i webbläsaren, ~2 min):

  1. https://share.streamlit.io  ->  Sign in  ->  "New app"
  2. Välj repot, branch: main, Main file path: app/Home.py
  3. "Advanced settings" -> Secrets, klistra in:
         MARC_AUTOBUILD = "1"
         MARC_APP_PASSWORD = "valfritt-delat-losenord"
  4. Deploy. Forsta laddningen bygger databasen (~1-2 min), sen ar den snabb.
  5. App-menyn (uppe till hoger pa streamlit.app) -> Settings -> Sharing:
     satt till privat och lagg till Hugos Google-mail.

Skicka Hugo: lanken + losenordet.
DONE
