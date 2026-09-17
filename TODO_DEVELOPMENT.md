# TODO: Development Process

Checklist usprawnien procesu wytwarzania i wdrazania aplikacji.

## Stan obecny

- [x] Backend i frontend sa rozdzielone na osobne moduly.
- [x] Zaleznosci Pythona sa blokowane przez `uv.lock`.
- [x] Zaleznosci frontendu sa blokowane przez `package-lock.json`.
- [x] Zmiany backendu maja testy regresyjne.
- [x] Istnieje dokumentacja projektu, API, wdrozenia i operacji.
- [x] Istnieje procedura backupu i odtworzenia SQLite.
- [x] Obrazy produkcyjne sa budowane z przypietymi wersjami i digestami.
- [x] Mamy automatyczne CI po pushu.
- [x] Mamy automatyczna walidacje Docker Compose przed wdrozeniem.
- [x] Przygotowac reczny workflow deployu produkcyjnego z kontrola sukcesu CI.
- [ ] Brakuje testow przegladarkowych end-to-end.
- [ ] Brakuje stagingu identycznego z produkcja.
- [ ] Wdrozenie na VPS jest wykonywane recznie.
- [ ] Brakuje automatycznych kontroli formatowania, lintowania i `git diff --check`.
- [ ] Brakuje drugiego przegladu zmian przez pull request.

## Priorytet 1: CI

- [x] Dodac GitHub Actions uruchamiane przy pull requestach i pushu.
- [x] Uruchamiac `uv run pytest -q`.
- [x] Uruchamiac build frontendu przez `npm ci` i `npm run build`.
- [x] Uruchamiac `docker compose -f docker/compose.prod.yaml config -q` bez ujawniania sekretow.
- [x] Sprawdzac skladnie skryptow Bash przez `bash -n`.
- [ ] Sprawdzac `git diff --check` albo odpowiednik bez falszywych alarmow CRLF.
- [ ] Dodac automatyczny build i publikacje wersjonowanych obrazow Dockerowych.
- [ ] Dodac kontrolowany deploy na staging po przejsciu CI.
- [x] Dodac kontrolowany deploy produkcyjny po akceptacji.

## Priorytet 2: testy E2E

- [ ] Dodac Playwright albo rownowazne narzedzie E2E.
- [ ] Przetestowac rejestracje i aktywacje konta.
- [ ] Przetestowac logowanie i wylogowanie.
- [ ] Przetestowac utworzenie oraz filtrowanie ogloszenia.
- [ ] Przetestowac wyslanie i potwierdzenie wymiany.
- [ ] Przetestowac odrzucenie i anulowanie wymiany.
- [ ] Przetestowac reset hasla.
- [ ] Przetestowac wersje mobilna.
- [ ] Wykonywac E2E na danych testowych, nigdy na produkcyjnej bazie.

## Priorytet 2: bezpieczenstwo aplikacji

- [ ] Przygotowac krotki threat model: aktywa, role, granice zaufania i scenariusze ataku.
- [ ] Dodac testy bezpieczenstwa dla auth, CSRF, enumeracji kont i kontroli wlasciciela.
- [ ] Dodac skanowanie zaleznosci Pythona i npm w CI.
- [ ] Dodac skanowanie obrazow Dockerowych pod katem znanych podatnosci.
- [ ] Udokumentowac kompromisy: SQLite, rate limiting in-memory i pojedynczy VPS.

## Priorytet 3: staging i wdrozenia

- [ ] Przygotowac staging z taka sama struktura Compose jak produkcja.
- [ ] Uzywac osobnej domeny, bazy, wolumenu i kluczy Brevo.
- [ ] Wykonywac build obrazow i smoke test na stagingu przed produkcja.
- [ ] Ustalic procedure rollbacku do poprzedniego commita lub obrazu.
- [ ] Dokumentowac kazde wdrozenie numerem commita i wynikiem healthcheckow.
- [ ] Automatyzowac wdrozenie dopiero po przejsciu CI i stagingu.

## Priorytet 4: jakosc zmian

- [ ] Dodac pre-commit dla formatowania, lintowania i kontroli bialych znakow.
- [ ] Ustalic konwencje commitow i stosowac male, logiczne commity.
- [ ] Uzywac pull requestow dla zmian przed beta publiczna.
- [ ] Wykonywac review zmian infrastrukturalnych przed wdrozeniem.
- [ ] Sprawdzac zgodnosc dokumentacji z aktualnym kontraktem API.
- [ ] Nie wdrazac zmian hardeningu bez testu pelnego startu kontenerow.

## Priorytet 5: dokumentacja architektury

- [ ] Dodac diagram architektury: przegladarka, Nginx, FastAPI, SQLite, Brevo i backupy.
- [ ] Dodac diagram przeplywu wymiany miedzy dwoma uzytkownikami.
- [ ] Opisywac wazne decyzje techniczne w formacie ADR.
- [ ] Dodac instrukcje rollbacku i odtwarzania backupu do dokumentacji operacyjnej.
- [ ] Przygotowac opis projektu do portfolio i CV z konkretnymi decyzjami oraz metrykami.

## Priorytet 6: produkt

- [ ] Dopracowac szablony maili transakcyjnych: branding, HTML, mobile i CTA.
- [ ] Dopracowac docelowe logo i branding Spindel.
- [ ] Dodac usuwanie konta i danych uzytkownika.
- [ ] Dodac moderacje oraz zglaszanie tresci.

## Proby odlozone i ograniczenia narzedzi

- [x] Wymusic przejscie jobow CI i Pull Request przed merge'em przez GitHub Ruleset.
	Powod: prywatne repozytorium na obecnym planie GitHub nie egzekwuje rulesetow; CI dziala, ale merge nie jest automatycznie blokowany.
	Obejscie: recznie sprawdzac zielone joby przed merge'em albo przeniesc repo do organizacji z planem GitHub Team.

## Kryterium dojrzalosci procesu

Proces mozna uznac za dojrzaly dla publicznej bety, gdy:

- kazdy push przechodzi automatyczne testy backendu i frontendu,
- Compose jest walidowany automatycznie,
- podstawowy przeplyw uzytkownika przechodzi test E2E,
- wdrozenie jest najpierw testowane na stagingu,
- istnieje rollback i niezalezna weryfikacja healthcheckow,
- dokumentacja oraz backlog sa aktualizowane razem ze zmiana.
