# SZFB sync commandy

Tento súbor slúži iba ako poznámka, aby som vedel rýchlo aktualizovať dáta zo SZFB.

Sync aktualizuje:
- tabuľku súťaže,
- zápasy sledovaného tímu,
- produktivitu hráčov, ak má `SzfbTeamWatch` vyplnené `competitor_id`.

---

## Muži

```bash
python manage.py sync_szfb --url "https://www.szfb.sk/sk/stats/home/1164/florbalova-extraliga-muzov"

## Juniori

```bash
python manage.py sync_szfb --url "https://www.szfb.sk/sk/stats/home/1166"