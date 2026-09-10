# Wymiana Grup PW

Backend aplikacji do wymiany grup zajeciowych dla studentow PW.

## Dokumentacja

- [Wiki projektu](docs/WIKI.md) - architektura, API, przeplywy i decyzje.
- [Kontekst dla LLM](docs/LLM_CONTEXT.md) - zwarty kontekst do dalszej pracy z agentem.

## Status prac

- [x] Backend MVP, auth, wymiany i maile
- [x] Backup SQLite, checksum i health-check
- [ ] Docker z trwalym storage dla SQLite
- [ ] Frontend
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

Sekrety i lokalna konfiguracja sa przechowywane poza repozytorium. Nie dodawaj pliku `.env` do commita.
