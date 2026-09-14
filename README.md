# Wymiana Grup PW

Backend aplikacji do wymiany grup zajeciowych dla studentow PW.

## Dokumentacja

- [Wiki projektu](docs/WIKI.md) - architektura, API, przeplywy i decyzje.
- [Kontekst dla LLM](docs/LLM_CONTEXT.md) - zwarty kontekst do dalszej pracy z agentem.

## Status prac

- [x] Backend MVP, auth, wymiany i maile
- [x] Backup SQLite, checksum i health-check
- [x] Docker backenda z trwalym storage dla SQLite
- [x] Frontend developerski React/Vite
- [ ] Nginx i HTTPS

Pelna lista zadan znajduje sie w [TODO.md](TODO.md).

## Szybki start

Wymagany jest Python 3.13+ oraz uv.

```powershell
python -m uv sync
python -m uv run pytest -q
python -m uv run uvicorn main:app --reload
```

Dokumentacja Swaggera jest dostepna pod `http://127.0.0.1:8000/docs`.

Frontend developerski uruchom w drugim terminalu:

```powershell
cd frontend
npm install
npm run dev
```

Aplikacja bedzie dostepna pod `http://localhost:5173`.

Backend mozna uruchomic przez Docker:

```powershell
docker compose -f docker/compose.yaml up --build
```

Compose uruchamia backend na porcie 8000 i zapisuje SQLite w wolumenie `wymiana_data`. Frontend nie jest jeszcze zawarty w Compose; `docker/Dockerfile.frontend` pozostaje do uzupelnienia razem z Nginx.

Testy manualne wszystkich mechanik sa opisane w [scenariuszu end-to-end](docs/WIKI.md#9-test-manualny-end-to-end).

Sekrety i lokalna konfiguracja sa przechowywane poza repozytorium. Nie dodawaj pliku `.env` do commita.
