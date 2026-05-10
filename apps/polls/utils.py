import hashlib
import uuid

from django.conf import settings


POLL_VOTER_COOKIE_NAME = "poll_voter_id"
POLL_VOTER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def generate_voter_id():
    """
    Vygeneruje anonymné ID hlasujúceho zariadenia / prehliadača.

    Príklad:
    9f2b7e6e-18de-43c5-9c52-d31d942db1a2
    """
    return str(uuid.uuid4())


def get_or_create_voter_id(request):
    """
    Skúsi nájsť voter_id v cookie.

    Ak cookie existuje:
    - vráti existujúce voter_id
    - created bude False

    Ak cookie neexistuje:
    - vygeneruje nové voter_id
    - created bude True
    """
    voter_id = request.COOKIES.get(POLL_VOTER_COOKIE_NAME)

    if voter_id:
        return voter_id, False

    return generate_voter_id(), True


def hash_value(value):
    """
    Z hodnoty spraví bezpečný hash.

    Nepoužívame to na blokovanie hlasovania,
    iba na pomocné uloženie user-agentu bez čistého textu.
    """
    if not value:
        return ""

    secret = getattr(settings, "SECRET_KEY", "")
    raw_value = f"{secret}:{value}"

    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def get_client_ip(request):
    """
    Zistí IP adresu klienta z requestu.

    Ak aplikácia beží za proxy, HTTP_X_FORWARDED_FOR môže obsahovať zoznam IP.
    Vtedy berieme prvú adresu zo zoznamu.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "")


def get_ip_hash(request):
    """
    Vráti hash IP adresy bez ukladania čistej IP do databázy.
    """
    return hash_value(get_client_ip(request))


def get_user_agent_hash(request):
    """
    Zoberie informáciu o prehliadači / zariadení a uloží ju ako hash.

    Napríklad:
    Safari na iPhone, Chrome na Macu, atď.

    Nepoužívame to ako hlavnú ochranu.
    Hlavná ochrana je voter_id cookie.
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return hash_value(user_agent)


def set_voter_cookie(response, voter_id):
    """
    Nastaví voter_id cookie do odpovede.

    httponly=True:
    - frontend JavaScript ju nevie čítať
    - je to bezpečnejšie

    secure=not settings.DEBUG:
    - v produkcii sa cookie posiela iba cez HTTPS

    samesite="Lax":
    - rozumná ochrana proti niektorým cross-site útokom
    """
    response.set_cookie(
        key=POLL_VOTER_COOKIE_NAME,
        value=voter_id,
        max_age=POLL_VOTER_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )

    return response
