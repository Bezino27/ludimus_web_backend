import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup


# # ZÁKLADNÉ NASTAVENIA

BASE_URL = "https://www.szfb.sk"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# # POMOCNÉ FUNKCIE

def normalize_spaces(value: str) -> str:
    """
    Vyčistí text zo stránky.
    Z viacerých medzier, enterov a tabulátorov spraví jednu medzeru.
    """
    return re.sub(r"\s+", " ", value or "").strip()


COMMON_FIRST_NAMES = {
    "adam",
    "andrej",
    "boris",
    "david",
    "dominik",
    "erik",
    "filip",
    "jakub",
    "jan",
    "janko",
    "jozef",
    "juraj",
    "ladislav",
    "lukas",
    "marek",
    "martin",
    "matej",
    "matias",
    "matus",
    "michal",
    "milan",
    "miroslav",
    "oliver",
    "patrik",
    "peter",
    "richard",
    "robert",
    "roman",
    "samuel",
    "simon",
    "stanislav",
    "stefan",
    "tomas",
    "viktor",
}


def normalize_name_part(value: str) -> str:
    return value[:1].upper() + value[1:].lower() if value else ""


def normalize_name_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    return value.encode("ascii", "ignore").decode("ascii").lower()


def format_player_name(value: str, *, source_order: str = "auto") -> str:
    """
    Prevedie SZFB meno na čitateľný formát.
    Napríklad: "KUBÍK RICHARD" alebo "Kubík Richard" -> "Richard Kubík".
    """
    value = normalize_spaces(value).replace(",", "")

    if not value:
        return ""

    parts = value.split(" ")
    should_flip = source_order == "surname_first"

    if source_order == "auto" and len(parts) > 1:
        first_part = normalize_name_key(parts[0])
        second_part = normalize_name_key(parts[1]) if len(parts) == 2 else ""
        should_flip = parts[0].isupper() or (
            len(parts) == 2
            and first_part not in COMMON_FIRST_NAMES
            and second_part in COMMON_FIRST_NAMES
        )

    if len(parts) > 1 and should_flip:
        parts = [*parts[1:], parts[0]]

    return " ".join(normalize_name_part(part) for part in parts)


def get_soup(url: str) -> BeautifulSoup:
    """
    Stiahne HTML stránku zo SZFB a vráti BeautifulSoup objekt,
    s ktorým vieme ďalej čítať tabuľky, linky a text.
    """
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def parse_date(text: str):
    """
    Skúsi premeniť textový dátum zo SZFB na Python date objekt.
    Podporuje formáty napr. 06.05.2026 alebo 06.05.26.
    """
    text = normalize_spaces(text)

    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    return None


def parse_time(text: str):
    """
    Skúsi premeniť čas zo SZFB na Python time objekt.
    Napríklad 18:30.
    """
    text = normalize_spaces(text)

    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return None


def parse_int(value: str, default: int = 0) -> int:
    """
    Bezpečne vytiahne celé číslo z textu.
    Ak tam číslo nie je, vráti default.
    """
    value = normalize_spaces(value)
    match = re.search(r"\d+", value)

    if not match:
        return default

    try:
        return int(match.group(0))
    except ValueError:
        return default


def parse_decimal(value: str) -> Decimal:
    """
    Bezpečne prevedie desatinné číslo zo SZFB na Decimal.
    SZFB používa čiarku, napr. 1,71, preto ju meníme na bodku.
    """
    value = normalize_spaces(value).replace(",", ".")

    if not value:
        return Decimal("0")

    try:
        return Decimal(value)
    except Exception:
        return Decimal("0")


def slugify_competition_name(name: str) -> str:
    """
    Z názvu súťaže vytvorí URL slug.
    Napríklad:
    'Florbalová extraliga mužov' -> 'florbalova-extraliga-muzov'
    """
    value = normalize_spaces(name).lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


# # URL BUILDER PRE PRODUKTIVITU HRÁČOV

def build_players_productivity_url(
    competition_id: int,
    competition_name: str,
    competitor_id: int,
    stats_type: str = "points",
) -> str:
    """
    Poskladá URL na produktivitu hráčov konkrétneho tímu.

    Výsledok bude napríklad:
    https://www.szfb.sk/sk/stats/players/1164/florbalova-extraliga-muzov?StatsType=points&CompetitorID=669426
    """
    slug = slugify_competition_name(competition_name)

    query = urlencode(
        {
            "StatsType": stats_type,
            "CompetitorID": competitor_id,
        }
    )

    return f"{BASE_URL}/sk/stats/players/{competition_id}/{slug}?{query}"


# # INFO O SÚŤAŽI

def extract_competition_info(home_url: str) -> dict:
    """
    Zo základnej SZFB home URL súťaže vytiahne:
    - ID súťaže,
    - názov súťaže,
    - sezónu,
    - URL tabuľky,
    - URL programu a výsledkov.
    """
    soup = get_soup(home_url)

    title_el = soup.find("h1")
    name = normalize_spaces(title_el.get_text()) if title_el else ""

    full_text = normalize_spaces(soup.get_text(" ", strip=True))
    season_match = re.search(r"Sezóna\s+(\d{4}/\d{4})", full_text)
    season = season_match.group(1) if season_match else ""

    comp_id_match = re.search(r"/stats/home/(\d+)", home_url)
    szfb_competition_id = int(comp_id_match.group(1)) if comp_id_match else None

    standings_url = ""
    results_url = ""

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = normalize_spaces(a.get_text())

        if "Tabuľky" in text and "/stats/standings/" in href:
            standings_url = urljoin(BASE_URL, href)

        if "Program a výsledky" in text and "/stats/results/" in href:
            results_url = urljoin(BASE_URL, href)

    if not standings_url and szfb_competition_id and name:
        standings_url = (
            f"{BASE_URL}/sk/stats/standings/"
            f"{szfb_competition_id}/{slugify_competition_name(name)}"
        )

    if not results_url and szfb_competition_id and name:
        results_url = (
            f"{BASE_URL}/sk/stats/results/"
            f"{szfb_competition_id}/{slugify_competition_name(name)}"
        )

    return {
        "szfb_competition_id": szfb_competition_id,
        "name": name,
        "season": season,
        "source_url": home_url,
        "standings_url": standings_url,
        "results_url": results_url,
    }


# # TABUĽKA SÚŤAŽE

def fetch_standings(standings_url: str) -> list[dict]:
    """
    Zo stránky tabuľky vytiahne poradie tímov.

    Vracia zoznam:
    [
        {
            "position": 1,
            "team_name": "...",
            "played": 10,
            "points": 25,
        }
    ]
    """
    soup = get_soup(standings_url)
    rows = []

    table_rows = soup.select("table.table.table-hover.table-logos tbody tr")

    for row in table_rows:
        cells = row.find_all("td", recursive=False)

        if len(cells) < 10:
            continue

        position_text = normalize_spaces(cells[0].get_text(" ", strip=True))

        team_link = cells[1].find("a")
        team_name = (
            normalize_spaces(team_link.get_text(" ", strip=True))
            if team_link
            else normalize_spaces(cells[1].get_text(" ", strip=True))
        )

        played_text = normalize_spaces(cells[2].get_text(" ", strip=True))
        points_text = normalize_spaces(cells[9].get_text(" ", strip=True))

        try:
            position = int(position_text)
            played = int(played_text)
            points = int(points_text)
        except ValueError:
            continue

        rows.append(
            {
                "position": position,
                "team_name": team_name,
                "played": played,
                "points": points,
            }
        )

    return rows


# # PRODUKTIVITA HRÁČOV

def fetch_player_productivity(players_url: str) -> list[dict]:
    """
    Zo stránky produktivity hráčov vytiahne hráčske štatistiky.

    Dôležitá oprava:
    SZFB pri niektorých hráčoch nezobrazuje poradie v prvom stĺpci.
    Preto hráčov nevyhadzujeme podľa ranku zo stránky.

    Postup:
    1. načítame všetkých hráčov,
    2. údaje vytiahneme podľa stĺpcov,
    3. zoradíme ich podľa bodov od najvyššieho po najnižší,
    4. rank vytvoríme sami.
    """
    soup = get_soup(players_url)
    rows = []

    table_rows = soup.select("table tbody tr")

    def get_cell_text(cells, index: int) -> str:
        """
        Bezpečne vytiahne text z bunky tabuľky.
        Ak bunka neexistuje, vráti prázdny string.
        """
        if index >= len(cells):
            return ""

        return normalize_spaces(cells[index].get_text(" ", strip=True))

    for row in table_rows:
        cells = row.find_all("td", recursive=False)

        # Potrebujeme aspoň základné stĺpce po body:
        # rank | meno | rok | tím | post | Z | G | A | B
        #
        # Nepoužívame len(cells) < 14, lebo niektoré ďalšie štatistiky
        # môžu byť prázdne alebo sa štruktúra mierne zmení.
        if len(cells) < 9:
            continue

        player_name = format_player_name(
            get_cell_text(cells, 1),
            source_order="surname_first",
        )
        birth_year_text = get_cell_text(cells, 2)
        team_short_name = get_cell_text(cells, 3)
        player_position = get_cell_text(cells, 4)

        if not player_name:
            continue

        games = parse_int(get_cell_text(cells, 5))
        goals = parse_int(get_cell_text(cells, 6))
        assists = parse_int(get_cell_text(cells, 7))
        points = parse_int(get_cell_text(cells, 8))

        rows.append(
            {
                "rank": 0,
                "player_name": player_name,
                "birth_year": parse_int(birth_year_text, default=0) or None,
                "team_short_name": team_short_name,
                "player_position": player_position,
                "games": games,
                "goals": goals,
                "assists": assists,
                "points": points,
                "points_avg": parse_decimal(get_cell_text(cells, 9)),
                "esp": parse_int(get_cell_text(cells, 10)),
                "ppp": parse_int(get_cell_text(cells, 11)),
                "shp": parse_int(get_cell_text(cells, 12)),
                "pim": parse_int(get_cell_text(cells, 13)),
            }
        )

    # Zoradenie podľa produktivity.
    # Najprv body, potom góly, potom asistencie, potom počet zápasov.
    rows.sort(
        key=lambda player: (
            player["points"],
            player["goals"],
            player["assists"],
            player["games"],
        ),
        reverse=True,
    )

    # Vlastné poradie, aby boli očíslovaní všetci hráči.
    for index, player in enumerate(rows, start=1):
        player["rank"] = index

    return rows


# # POMOCNÉ FUNKCIE PRE ZÁPASY

def _extract_clean_lines(url: str) -> list[str]:
    """
    Staršia pomocná funkcia.
    Vytiahne čisté textové riadky zo stránky.
    Aktuálne ju nechávame, keby sme ju ešte potrebovali pri debugovaní.
    """
    soup = get_soup(url)

    return [
        normalize_spaces(line)
        for line in soup.get_text("\n", strip=True).splitlines()
        if normalize_spaces(line)
    ]


def _is_match_number(line: str) -> bool:
    return bool(re.fullmatch(r"\d+", normalize_spaces(line)))


def _is_score(line: str) -> bool:
    return bool(re.fullmatch(r"\d+\s*:\s*\d+(\s*[A-Za-z]+)?", normalize_spaces(line)))


def _is_vs(line: str) -> bool:
    return normalize_spaces(line).upper() == "VS"


def _is_date(line: str) -> bool:
    return bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", normalize_spaces(line)))


def _is_time(line: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}:\d{2}", normalize_spaces(line)))


def _clean_team_line(line: str) -> str:
    """
    Pomocná funkcia na čistenie názvov tímov.
    Nechávame ju kvôli prípadným rozdielom v HTML SZFB.
    """
    line = normalize_spaces(line)

    # Odstráni "Image: ..." úseky.
    line = re.sub(r"Image:\s.*?(?=(?:\b[A-Z]{2,4}\b\s)|$)", " ", line)

    # Odstráni osamotené klubové skratky typu FCT, ATU, FKN, LID.
    line = re.sub(r"\b[A-Z]{2,4}\b", " ", line)

    # Odstráni zvyšné nadbytočné značky na začiatku.
    line = re.sub(r"^[^A-Za-zÁ-ž0-9]+", "", line)

    return normalize_spaces(line)


def _extract_team_name_from_cell(cell):
    """
    Zo zápasovej tabuľky vytiahne názov tímu.
    SZFB často dáva plný názov do span.hidden-xs.
    """
    hidden = cell.select_one("span.hidden-xs")

    if hidden:
        return normalize_spaces(hidden.get_text(" ", strip=True))

    return normalize_spaces(cell.get_text(" ", strip=True))


def _extract_score_from_cell(cell):
    """
    Zo zápasovej tabuľky vytiahne výsledok.
    Ak je zápas ešte neodohraný, vráti VS.
    """
    results = cell.select("span.matchresult")

    if len(results) >= 2:
        return (
            f"{normalize_spaces(results[0].get_text())}:"
            f"{normalize_spaces(results[1].get_text())}"
        )

    text = normalize_spaces(cell.get_text(" ", strip=True))

    if "VS" in text.upper():
        return "VS"

    match = re.search(r"(\d+)\s*[-:]\s*(\d+)", text)

    if match:
        return f"{match.group(1)}:{match.group(2)}"

    return ""


# # ZÁPASY

def fetch_matches(results_url: str) -> list[dict]:
    """
    Zo stránky Program a výsledky vytiahne všetky zápasy v súťaži.

    Vracia zoznam:
    [
        {
            "match_type": "finished" alebo "upcoming",
            "match_date": date alebo None,
            "match_time": time alebo None,
            "team1": "Domáci tím",
            "team2": "Hosťujúci tím",
            "venue": "Hala",
            "result": "5:3" alebo "VS",
        }
    ]
    """
    soup = get_soup(results_url)
    matches = []

    rows = soup.select("div.program-results table tbody tr")

    for row in rows:
        cells = row.find_all("td", recursive=False)

        if len(cells) < 5:
            continue

        home_cell = cells[1]
        score_cell = cells[2]
        away_cell = cells[3]
        info_cell = cells[4]

        home_team = _extract_team_name_from_cell(home_cell)
        away_team = _extract_team_name_from_cell(away_cell)
        result = _extract_score_from_cell(score_cell)

        if not home_team or not away_team or not result:
            continue

        date_value = None
        time_value = None
        venue = ""

        date_el = info_cell.select_one("div.match-date")

        if date_el:
            date_text = normalize_spaces(date_el.get_text(" ", strip=True))
            date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_text)

            if date_match:
                date_value = parse_date(date_match.group(1))

        if not date_value:
            for div in info_cell.find_all("div"):
                text = normalize_spaces(div.get_text(" ", strip=True))

                if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", text):
                    date_value = parse_date(text)
                    break

        for div in info_cell.find_all("div"):
            text = normalize_spaces(div.get_text(" ", strip=True))

            if _is_time(text):
                time_value = parse_time(text)
                break

        venue_el = info_cell.select_one("div.td-box")

        if venue_el:
            venue = normalize_spaces(venue_el.get_text(" ", strip=True))

        match_type = "upcoming" if result.upper() == "VS" else "finished"

        matches.append(
            {
                "match_type": match_type,
                "match_date": date_value,
                "match_time": time_value,
                "team1": home_team,
                "team2": away_team,
                "venue": venue,
                "result": result,
            }
        )

    return matches


def filter_matches_for_team(matches: list[dict], team_name: str) -> list[dict]:
    """
    Z celého zoznamu zápasov vyfiltruje iba zápasy sledovaného tímu.

    Napríklad:
    team_name = "FaBK ATU Košice"

    Výsledkom budú iba zápasy, kde hrá ATU.
    """
    team_name_normalized = normalize_spaces(team_name).lower()
    filtered = []

    for match in matches:
        t1 = normalize_spaces(match["team1"]).lower()
        t2 = normalize_spaces(match["team2"]).lower()

        if team_name_normalized not in t1 and team_name_normalized not in t2:
            continue

        is_home = team_name_normalized in t1
        opponent = match["team2"] if is_home else match["team1"]

        filtered.append(
            {
                "match_type": match["match_type"],
                "match_date": match["match_date"],
                "match_time": match["match_time"],
                "venue": match["venue"],
                "opponent": opponent,
                "result": match["result"],
                "is_home": is_home,
                "external_key": (
                    f"{team_name}|{match['match_type']}|{match['match_date']}|"
                    f"{match['match_time']}|{opponent}|{match['result']}"
                ),
            }
        )

    return filtered
