# Tryb przerwy technicznej

Tryb maintenance jest ustawiany podczas budowania frontendu przez zmienna `VITE_MAINTENANCE`.

## Wlaczenie na VPS

W pliku `/opt/wymiana-zajec/.env` ustaw lokalnie:

```dotenv
VITE_MAINTENANCE=true
```

Przebuduj tylko frontend:

```bash
docker compose -f /opt/wymiana-zajec/docker/compose.prod.yaml up -d --build frontend
```

Frontend pokazuje komunikat przerwy, a backend i baza nadal dzialaja.

## Wylaczenie

Ustaw:

```dotenv
VITE_MAINTENANCE=false
```

albo usun zmienna, a nastepnie wykonaj:

```bash
docker compose -f /opt/wymiana-zajec/docker/compose.prod.yaml up -d --build frontend
```

Nie uzywaj `docker compose down -v`; maintenance nie wymaga zatrzymywania backendu ani usuwania wolumenu.
