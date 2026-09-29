# Testowanie

## Testy automatyczne

Backend:

```powershell
python -m uv run pytest -q
```

Testy korzystaja z osobnej bazy SQLite in-memory i mockuja wysylke Brevo; nie powinny dotykac produkcyjnej bazy ani wysylac prawdziwych e-maili.

Frontend:

```powershell
cd frontend
npm ci
npm run build
```

CI uruchamia backend tests, frontend build, walidacje produkcyjnego Compose i skladnie skryptow Bash. Testy przegladarkowe Playwright nie sa obecnie skonfigurowane.

## Reczny smoke test

Uruchom backend i frontend lokalnie (zob. [Architektura: lokalne uruchomienie](architecture.md#uruchomienie-lokalne)), nastepnie sprawdz:

1. Rejestracje, link aktywacyjny i blokade logowania przed aktywacja.
2. Logowanie, odswiezenie strony, wylogowanie, flage cookie `HttpOnly` oraz odrzucenie nieprawidlowego CSRF.
3. Reset hasla, jednorazowosc tokenu i uniewaznienie starej sesji.
4. Utworzenie, filtrowanie i anulowanie ogloszenia.
5. Zgloszenie z drugiego konta, ukrycie kontaktow przed potwierdzeniem oraz potwierdzenie/odrzucenie.
6. Mail aktywacyjny, resetu i powiadomienia o wymianie — produkcyjnie tylko na kontrolowanych kontach.
7. Wersje mobilna, jezyki PL/EN i maintenance mode.
8. Healthcheck oraz przetrwanie restartu kontenera przez wolumen SQLite.

Szczegolowy kontrakt zachowania endpointow jest w [Modelu danych i API](api.md); tryb maintenance w [instrukcji maintenance](notes-how2/maintenance_mode.md).

## Smoke test po wdrozeniu

- Potwierdz, ze backend i frontend Compose maja `healthy`.
- Sprawdz `https://spindel.pl/api/health` oraz `https://spindel.pl/nginx-health`.
- Sprawdz logi backendu i frontendu, bez kopiowania danych osobowych/sekretow do zgloszen.
- Wykonaj krotki test logowania oraz kluczowego przeplywu, nie prowadzac destrukcyjnych operacji na danych uzytkownikow.

Zglaszaj bledy bez hasel, tokenow, zawartosci `.env` i pelnych logow z danymi uzytkownikow.
