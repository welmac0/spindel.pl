# Wymiana Grup PW

Backend aplikacji do wymiany grup zajeciowych dla studentow PW.

## Dokumentacja

- [Indeks dokumentacji](docs/WIKI.md)
- [Architektura i lokalne uruchomienie](docs/architecture.md)
- [Model danych i API](docs/api.md)
- [Bezpieczenstwo](docs/security.md)
- [Testowanie](docs/testing.md)
- [Operacje, backupy i wdrazanie](docs/operations.md)
- [Kontekst dla agenta kodujacego](docs/LLM_CONTEXT.md)

## Status prac

- [x] Backend MVP, auth, wymiany i maile
- [x] Backup SQLite, checksum i health-check
- [x] Docker backenda z trwalym storage dla SQLite
- [x] Frontend developerski React/Vite
- [x] Frontend w Compose z Nginxem
- [x] HTTPS i deployment produkcyjny na Hetzner VPS

Pelna lista zadan znajduje sie w [TODO.md](TODO.md).

## Szybki start

Wymagany jest Python 3.13+ oraz uv.

```powershell
python -m uv sync
python -m uv run pytest -q
python -m uv run uvicorn wymiana_zajec.main:app --reload
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

Compose developerski uruchamia backend na porcie 8000, frontend przez Nginx na porcie 5175 i zapisuje SQLite w external volume `docker_wymiana_data`. Produkcja działa na Hetzner VPS przez `docker/compose.prod.yaml`, wystawia frontend na HTTPS przez Nginx, nie publikuje portu backendu, używa Certbota i ma backupy SQLite.

Instrukcje smoke testu i przeplywow manualnych sa w [Testowaniu](docs/testing.md).

Sekrety i lokalna konfiguracja sa przechowywane poza repozytorium. Nie dodawaj pliku `.env` do commita.
