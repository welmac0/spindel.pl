# Dokumentacja Spindel

To jest indeks dokumentacji projektu. Zmiany w dokumentacji powinny trafiać do repozytorium razem z odpowiadającą im zmianą kodu.

## Dla kogo?

- **Chcesz uruchomic projekt?** Zacznij od [README](../README.md), potem [Architektura](architecture.md).
- **Szukasz endpointu albo reguly biznesowej?** Przejdz do [Modelu danych i API](api.md).
- **Zmiana dotyczy logowania, danych lub sekretow?** Przeczytaj [Bezpieczenstwo](security.md).
- **Chcesz uruchomic testy?** Zobacz [Testowanie](testing.md).
- **Obslugujesz produkcje/VPS?** Zobacz [Operacje i wdrazanie](operations.md) oraz szczegolowe [instrukcje operacyjne](notes-how2/).
- **Kontynuujesz prace z agentem?** Zapoznaj sie z [kontekstem dla agenta](LLM_CONTEXT.md).

## Zrodla prawdy

- Biezace zadania i priorytety sa w GitHub Issues/Project; pliki TODO pozostaja backlogiem pomocniczym do czasu pelnego przeniesienia.
- Aktualne zachowanie API powinno byc zgodne z kodem i OpenAPI (`/docs`, `/openapi.json`); strona [API](api.md) opisuje stabilny kontrakt i reguly domenowe.
- Procedury wdrozenia/backupu sa w [Operacjach](operations.md) i dokumentach `notes-how2`.
- Zalozenia projektu i wskazniki plikow opisuje [Architektura](architecture.md).

## Zasada aktualizacji

Jesli zmiana modyfikuje kontrakt API, bezpieczenstwo, testowanie, wdrozenie albo backup, zaktualizuj odpowiednia strone dokumentacji w tym samym commicie. Nie kopiuj calej dokumentacji do `LLM_CONTEXT.md`; ten plik ma zawierac tylko reguly potrzebne agentowi do bezpiecznej pracy.
