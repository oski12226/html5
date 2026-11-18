# Sejm bez powagi

Statyczna strona (GitHub Pages) ze śmiesznymi i ciekawymi sytuacjami z Sejmu. Workflow co 30 minut uruchamia `scripts/update.py`, który zapisuje `data.json`.

## Uruchomienie
1. Utwórz repozytorium na GitHubie i wgraj wszystkie pliki (łącznie z folderem `.github`).
2. Settings → Pages → Deploy from a branch → `main` / `(root)`.
3. Actions → „Aktualizacja” → Run workflow (pierwsze odświeżenie).

## Źródła
- Google News RSS, Mastodon (hashtagi #sejm), Reddit r/Polska: działają bez kluczy.
- X: opcjonalnie dodaj sekret `X_BEARER_TOKEN` (Settings → Secrets → Actions). API X jest płatne.
- Facebook i Instagram: brak darmowego publicznego API. Dodawaj wybrane posty ręcznie w `manual.json`.
