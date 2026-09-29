# Model danych i API

API jest udostepnione przez FastAPI. Lokalny Swagger: `http://127.0.0.1:8000/docs`; OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`.

## Uwierzytelnianie i ochrona CSRF

Sesja trwa 7 dni. `POST /login` ustawia cookie `spindel_session` z `HttpOnly`, `SameSite=Lax` oraz `Secure` na produkcji; surowy token nie jest zwracany w JSON. `POST /logout` uniewaznia sesje serwerowo i usuwa cookie.

Przed operacjami modyfikujacymi klient pobiera `GET /csrf`. Odpowiedz zawiera token, a cookie `spindel_csrf` przechowuje jego kopie. Klient dodaje wartosc w naglowku `X-CSRF-Token`. Backend sprawdza cookie/header i, gdy jest obecny, `Origin`. Nieprawidlowy CSRF lub obcy origin zwraca `403`.

Wszystkie metody `POST`, `PUT`, `PATCH`, `DELETE` wymagaja tokenu CSRF — takze rejestracja, logowanie i reset hasla. Bez sesji endpoint chroniony zwraca `401`.

## Endpointy

| Metoda i sciezka | Dostep | Opis |
|---|---|---|
| `POST /register` | Publiczny + CSRF | Tworzy konto i wysyla link aktywacyjny. Odpowiedz `201` jest neutralna wobec duplikatu; blad wysylki moze zwrocic `503`. |
| `GET /verify?token=...` | Publiczny | Jednorazowa aktywacja konta; token wazny 7 dni. |
| `POST /resend-verification` | Publiczny + CSRF | Neutralna odpowiedz `200`; limit `3/hour` na IP. |
| `GET /csrf` | Publiczny | Ustawia cookie CSRF i zwraca token. |
| `POST /login` | Publiczny + CSRF | Logowanie konta zweryfikowanego; ustawia cookie sesyjne; limit `10/minute` na IP. |
| `POST /logout` | Sesja + CSRF | Uniewaznia sesje, zwraca `204`. |
| `POST /password-reset/request` | Publiczny + CSRF | Zawsze neutralny wynik `202`; limit `3/hour` na IP. |
| `POST /password-reset/confirm` | Publiczny + CSRF | Jednorazowo zmienia haslo i uniewaznia sesje; limit `10/hour` na IP. |
| `GET /listings` | Publiczny | Lista tylko aktywnych ogloszen; `limit` 1–100, `offset` od 0. |
| `GET /listings/{listing_id}` | Publiczny | Szczegoly aktywnego ogloszenia; nieaktywne zwracaja `404`. |
| `POST /listings` | Sesja + CSRF | Tworzy ogloszenie wlasciciela. Maksymalnie 8 aktywnych/oczekujacych ofert. |
| `PATCH /listings/{listing_id}` | Sesja + CSRF + wlasciciel | Edytuje ogloszenie; statusu nie zmienia sie przez PATCH. |
| `DELETE /listings/{listing_id}` | Sesja + CSRF + wlasciciel | Usuwa ogloszenie; `204`. |
| `POST /listings/{listing_id}/requests` | Sesja + CSRF | Zglasza zainteresowanie aktywnym cudzym ogloszeniem. |
| `GET /listings/{listing_id}/requests` | Sesja + wlasciciel | Zwraca zgloszenia do ogloszenia. |
| `POST /exchange-requests/{request_id}/confirm` | Sesja + CSRF + wlasciciel | Potwierdza wymiane, ustawia ogloszenie `fulfilled`. |
| `POST /exchange-requests/{request_id}/reject` | Sesja + CSRF + wlasciciel | Anuluje zgloszenie i ogloszenie. |
| `POST /listings/{listing_id}/cancel` | Sesja + CSRF + wlasciciel | Anuluje aktywne lub oczekujace ogloszenie. |
| `GET /me/exchange-requests` | Sesja | Zgloszenia wyslane i otrzymane przez uzytkownika. |
| `GET /me/listings` | Sesja | Wszystkie ogloszenia zalogowanego uzytkownika, takze zakonczone. |
| `GET /enums?lang=pl\|en` | Publiczny | Etykiety enumow PL/EN. |
| `GET /stats` | Publiczny | Publiczne statystyki zakonczonych wymian. |
| `GET /health` | Publiczny | Status aplikacji i polaczenia z SQLite; awaria bazy daje `503`. |

## Reguly domenowe

### Konto

- Email ma format `8-cyfr@pw.edu.pl`; numer indeksu sklada sie z 6 cyfr.
- Haslo ma od 8 do 128 znakow.
- Link aktywacyjny jest jednorazowy i wazny 7 dni.
- Token resetu hasla jest jednorazowy i wazny 1 godzine.
- Odpowiedzi rejestracji/resend/reset nie powinny ujawniac, czy konto istnieje.

### Ogłoszenia

- `group_have` to jedna grupa, `group_want` to lista maksymalnie 5 grup; numery grup maja maksymalnie 2 cyfry.
- Backend usuwa duplikaty i sortuje `group_want`; SQLite przechowuje liste jako tekst rozdzielony przecinkami.
- Grupa posiadana i szukana musza byc rozne.
- Jedno konto moze miec maksymalnie 8 ogloszen ze statusem `active` albo `pending`.
- Tworzenie odwrotnej, konfliktowej zamiany zwraca `409` z `conflicting_listing_id`.
- Aktywne ogloszenie starsze niz 90 dni staje sie `stale`.

Statusy ogloszenia: `active`, `pending`, `fulfilled`, `stale`, `cancelled`.

### Wymiana

- Zgloszenie jest mozliwe tylko do ogloszenia `active` i nie do wlasnej oferty.
- Zmiana `active -> pending` jest atomowa; drugie zgloszenie nie przechodzi.
- Zgloszenie wygasa po 48 godzinach. Wtedy ogloszenie wraca do `active`, a wlasciciel ma cooldown 4 dni.
- Potwierdzenie ustawia zgloszenie `confirmed` i ogloszenie `fulfilled`; dopiero wtedy ujawniane sa kontakty.
- Odrzucenie anuluje oferte: zgloszenie i ogloszenie otrzymuja `cancelled`. Nie ma statusu ogloszenia `rejected`.

Statusy zgloszenia: `pending`, `confirmed`, `expired`, `cancelled`.

## E-maile

`EmailDelivery` reprezentuje logiczna dostawe, a `EmailDeliveryAttempt` konkretna probe. Nieudany e-mail nie cofa zapisanej rejestracji ani wymiany. Wysylka wykorzystuje Brevo Transactional API.
