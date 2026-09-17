# TODO: Beta Tests

Plan kontrolowanej bety aplikacji Spindel po udostepnieniu informacji na Facebooku i Instagramie.

## Cel bety

Sprawdzic, czy prawdziwi uzytkownicy potrafia bez pomocy:

- zalozyc i aktywowac konto,
- zalogowac sie,
- znalezc ogloszenie,
- utworzyc wlasne ogloszenie,
- wyslac zgloszenie wymiany,
- potwierdzic albo odrzucic wymiane,
- zrozumiec komunikaty aplikacji i maile.

## Grupa 1: znajomi i testerzy techniczni

**Liczba:** 3-5 osob  
**Czas:** 1-2 dni

- [ ] Przekazac link do aplikacji i krotka instrukcje.
- [ ] Poprosic o osobne konta, jezeli testerzy maja dostep do swoich skrzynek PW.
- [ ] Przetestowac rejestracje i aktywacje przez email.
- [ ] Przetestowac logowanie, wylogowanie i reset hasla.
- [ ] Utworzyc ogloszenia z roznymi kierunkami, semestrami i grupami.
- [ ] Wykonac przynajmniej jedna pelna wymiane miedzy dwoma kontami.
- [ ] Sprawdzic maile o rejestracji, zgloszeniu i potwierdzeniu.
- [ ] Zbierac bledy techniczne i niejasne komunikaty.

## Grupa 2: zwykli uzytkownicy PW

**Liczba:** 5-10 osob  
**Czas:** 3-5 dni

- [ ] Nie tlumaczyc szczegolowo interfejsu przed pierwszym uzyciem.
- [ ] Sprawdzic, czy uzytkownik rozumie glowny cel strony.
- [ ] Sprawdzic wyszukiwanie i filtrowanie ogloszen.
- [ ] Sprawdzic, czy formularz ogloszenia jest zrozumialy.
- [ ] Sprawdzic, czy uzytkownik rozumie statusy wymiany.
- [ ] Sprawdzic wersje polska i angielska.
- [ ] Zbierac problemy UX, nie tylko bledy techniczne.
- [ ] Zmierzyc, ile osob konczy podstawowy scenariusz bez pomocy.

## Grupa 3: testy mobilne

**Liczba:** 3-5 osob  
**Czas:** 2-3 dni, rownolegle z Grupa 2

- [ ] Przetestowac Androida i iPhone'a.
- [ ] Sprawdzic Chrome, Safari i Firefox mobilny.
- [ ] Sprawdzic formularze, checkboxy kierunkow i przyciski.
- [ ] Sprawdzic czy tekst nie jest obcinany ani zaslaniany.
- [ ] Sprawdzic jasny i ciemny motyw systemowy.
- [ ] Sprawdzic maile i linki aktywacyjne na telefonie.

## Grupa 4: stabilnosc po poprawkach

**Liczba:** 2-3 osoby
**Czas:** 1 dzien po kazdej wiekszej poprawce

- [ ] Uruchomic testy backendu.
- [ ] Uruchomic build frontendu.
- [ ] Wykonac smoke test produkcyjny.
- [ ] Sprawdzic status kontenerow i endpointy health.
- [ ] Powtorzyc scenariusz, ktorego dotyczyla poprawka.
- [ ] Sprawdzic logi po zakonczeniu testu.

## Format zgloszenia bledu

```text
Tytul:
Priorytet: blokujacy / wazny / kosmetyczny / pomysl
Uzytkownik:
Urzadzenie i przegladarka:
Jezyk i motyw:
Kroki:
Co sie stalo:
Co powinno sie stac:
Screenshot lub nagranie:
Data i godzina:
```

Nie wysylac hasel, tokenow, zawartosci `.env` ani pelnych logow zawierajacych dane uzytkownikow.

## Priorytety bledow

- **Blokujacy:** rejestracja, logowanie, aktywacja, utworzenie ogloszenia albo wymiana nie dziala.
- **Wazny:** funkcja dziala, ale prowadzi do blednego stanu albo uzytkownik nie moze samodzielnie wykonac zadania.
- **Kosmetyczny:** problem wygladu, tekstu, ukladu albo responsywnosci.
- **Pomysl:** sugestia nowej funkcji lub zmiany procesu.

## Przewidywany harmonogram

### Minimalna beta

**2-3 dni:**

- Grupa 1,
- jedna pelna wymiana,
- najwazniejsze poprawki,
- ponowny smoke test.

### Rozsadna beta zamknieta

**7-10 dni:**

- Grupa 1 przez 1-2 dni,
- poprawki po pierwszych zgloszeniach,
- Grupy 2 i 3 przez 3-5 dni,
- dzien stabilizacji i ponownej weryfikacji.

### Beta przed szerszym publicznym udostepnieniem

**2-3 tygodnie:**

- 15-30 aktywnych testerow,
- co najmniej kilka realnych prob wymiany,
- testy mobilne i desktopowe,
- obserwacja maili, backupow i healthcheckow,
- zamkniecie bledow blokujacych i waznych,
- przeglad regulaminu i polityki prywatnosci.

## Kryterium zakonczenia bety

- [ ] Brak otwartych bledow blokujacych.
- [ ] Najwazniejsze bledy maja obejscie albo poprawke.
- [ ] Co najmniej 10 osob przeszlo podstawowy scenariusz.
- [ ] Co najmniej 2 pelne wymiany zakonczyly sie poprawnie.
- [ ] Rejestracja, maile i reset hasla dzialaja na produkcji.
- [ ] Wersja mobilna nie ma bledow uniemozliwiajacych uzycie.
- [ ] Ostatni deploy przeszedl CI i healthchecki.
- [ ] Zebrane uwagi zostaly przeniesione do issue albo TODO.
