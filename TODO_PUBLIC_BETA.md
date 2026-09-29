# TODO: Public Beta

Checklist przed udostepnieniem aplikacji szerszej grupie uzytkownikow.

## Priorytet 1: bezpieczenstwo sesji

- [x] Przeniesc token sesji z `localStorage` do ciasteczka `HttpOnly`.
- [x] Ustawic dla ciasteczka `Secure` na produkcji i `SameSite=Lax`.
- [x] Dodac ochrone CSRF dla operacji zmieniajacych dane.
- [x] Dodac testy logowania, wylogowania, wygasania sesji i CSRF.
- [x] Sprawdzic, ze token sesji nie pojawia sie w URL, logach ani odpowiedziach frontendu.

## Priorytet 2: wdrozenie produkcyjne

- [ ] Wypchnac na VPS aktualna wersje backendu i frontendu.
- [ ] Wykonac backup SQLite przed wdrozeniem.
- [ ] Przebudowac backend i frontend przez produkcyjny Compose.
- [ ] Potwierdzic, ze backend ma status `healthy`.
- [ ] Potwierdzic, ze frontend ma status `healthy`.
- [ ] Sprawdzic `https://spindel.pl/api/health`.
- [ ] Sprawdzic `https://spindel.pl/nginx-health`.
- [ ] Sprawdzic certyfikat HTTPS i przekierowanie HTTP -> HTTPS.
- [ ] Sprawdzic logi backendu, frontendu i Certbota po wdrozeniu.
- [ ] Sprawdzic timer healthchecka i timer backupu.
- [ ] Potwierdzic, ze backup poza VPS oraz test odtworzenia nadal dzialaja.

## Priorytet 3: test produkcyjny

- [ ] Zarejestrowac konto testowe z adresem PW.
- [ ] Otrzymac i kliknac link aktywacyjny.
- [ ] Zalogowac sie na konto testowe.
- [ ] Utworzyc ogloszenie.
- [ ] Sprawdzic filtrowanie i widocznosc ogloszenia jako niezalogowany uzytkownik.
- [ ] Wyslac zgloszenie z drugiego konta.
- [ ] Potwierdzic albo odrzucic zgloszenie.
- [ ] Sprawdzic maile rejestracyjne, wymiany i potwierdzenia.
- [ ] Sprawdzic reset hasla i jednorazowosc linku resetujacego.
- [ ] Sprawdzic wersje mobilna na telefonie.
- [ ] Sprawdzic jezyk polski i angielski.
- [ ] Sprawdzic maintenance mode oraz powrot do normalnej pracy.
- [ ] Sprawdzic neutralne komunikaty rejestracji i resend.

## Priorytet 4: niezawodnosc i obserwowalnosc

- [ ] Zainstalowac monitor zewnetrzny na Raspberry Pi i sprawdzic alert awarii oraz powrotu uslug.
- [ ] Potwierdzic alerty HTTPS/backend z zewnetrznego monitora.
- [ ] Ustawic alert dla nieudanego backupu.
- [ ] Sprawdzic retencje backupow i okresowo wykonywac test restore.
- [ ] Ustalic procedure rollbacku do poprzedniego obrazu lub commita.
- [ ] Ustalic procedure wlaczenia maintenance podczas wdrozenia.

## Priorytet 5: formalnosci i tresci

- [ ] Zlecic przeglad regulaminu i polityki prywatnosci.
- [ ] Uzupelnic dane administratora danych i kontakt do zgloszen.
- [ ] Ustalic zasady usuwania konta i danych uzytkownika.
- [ ] Ustalic zasady moderacji i zglaszania tresci.
- [ ] Dopracowac docelowe logo Spindel.
- [ ] Dopracowac szablony maili transakcyjnych: branding, HTML, mobile i CTA.

## Priorytet 6: UI UX
- [ ] Dodać do maila potwierdzającego wymianę i maila o wysłaniu aplikacji także numer indeksu studenta, oraz przygotować gotowy szablon do wysłania przez USOS/ePodania.

## Kryterium startu publicznej bety

Publiczna beta moze wystartowac, gdy:

- sesja jest chroniona przez `HttpOnly` cookie i CSRF,
- backend i frontend sa `healthy` na VPS,
- HTTPS oraz endpointy health dzialaja,
- backup i restore byly sprawdzone,
- pelny smoke test produkcyjny przeszedl,
- dokumenty formalne zostaly przejrzane,
- istnieje monitoring niezalezny od VPS albo zaakceptowano jego brak jako ryzyko.

## Procedura po kazdym wdrozeniu

```bash
cd /opt/wymiana-zajec
git pull --ff-only
sudo systemctl start wymiana-zajec-backup.service
docker compose -f docker/compose.prod.yaml build backend frontend
docker compose -f docker/compose.prod.yaml up -d
docker compose -f docker/compose.prod.yaml ps
curl -fsS https://spindel.pl/api/health
curl -fsS https://spindel.pl/nginx-health
```

Nie uzywac `docker compose down -v`, jezeli baza SQLite ma pozostac zachowana.
