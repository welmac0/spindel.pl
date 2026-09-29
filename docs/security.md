# Bezpieczenstwo

## Zabezpieczenia

- Hasla sa hashowane przez `hashlib.scrypt` z losowa sola.
- Tokeny sesji, weryfikacji e-mail i resetu hasla sa generowane kryptograficznie; surowe tokeny nie sa zapisywane w bazie, przechowywane sa ich hashe.
- Sesja przegladarki jest w cookie `spindel_session`: `HttpOnly`, `SameSite=Lax`, 7 dni; produkcja ustawia `Secure` przez `SESSION_COOKIE_SECURE=true`.
- Metody `POST`, `PUT`, `PATCH`, `DELETE` wymagaja double-submit CSRF (`spindel_csrf` + `X-CSRF-Token`); backend waliduje rowniez `Origin`, jesli naglowek zostal wyslany.
- Po zmianie hasla i wylogowaniu sesja jest uniewazniana w bazie.
- Rejestracja, resend i reset hasla maja neutralne odpowiedzi, aby ograniczyc enumeracje kont.
- Endpointy mutujace sprawdzaja wlasciciela i prawidlowy stan biznesowy.
- Tokeny verify/reset sa usuwane z paska adresu przez frontend po odczytaniu.
- Logi nie powinny zawierac hasel, sekretow ani surowych tokenow.

## Produkcyjny hardening

Produkcyjny Compose uruchamia backend i frontend z ograniczonymi uprawnieniami (`read_only`, `cap_drop`, `no-new-privileges`), limitami zasobow i wymaganymi wolumenami. Backend nie publikuje portu na zewnatrz. Nginx obsluguje HTTPS, przekierowanie HTTP -> HTTPS, HSTS, CSP, ochrone przed framingiem, `X-Content-Type-Options` i `Referrer-Policy`.

Sekrety przechowuj poza repozytorium w lokalnym `.env` na VPS; nigdy go nie odczytuj w celu diagnostyki, nie commituj ani nie wklejaj do Issue/logow. Sprawdzaj nazwy zmiennych albo stan uslugi bez ujawniania wartosci.

## Znane ograniczenia / ryzyka

- Rate limiting `slowapi` jest przechowywany w pamieci procesu; nie jest wspoldzielony miedzy wieloma workerami.
- Jedna instancja VPS oznacza pojedynczy punkt awarii.
- SQLite nie jest docelowym magazynem dla wiekszej skali.
- Brak migracji schematu; `create_all()` nie aktualizuje istniejacych tabel.

Nie dodawaj Redisa, migracji ani architektury wieloinstancyjnej bez decyzji projektowej. Procedury ochrony bazy i deployu opisano w [Operacjach](operations.md).
