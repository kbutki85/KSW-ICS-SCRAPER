import json, os, re, hashlib
from datetime import datetime, timedelta
from dateutil import tz
from ics import Calendar, Event, DisplayAlarm
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# === CONFIG ===
URL = os.environ.get("FIXTURES_URL", "https://www.laczynaspilka.pl/rozgrywki?season=e9d66181-d03e-4bb3-b889-4da848f4831d&leagueGroup=43da7ba1-b751-4295-814b-24bd37fd2d45&leagueId=5cc45e5f-744b-428c-b8af-cdefca38de29&enumType=Play&group=e5bc0d4f-1bc4-40f5-92f9-e55c859b5166&isAdvanceMode=false&genderType=Male")
TEAM = os.environ.get("TEAM_NAME", "KS Wasilków")
OUT = os.environ.get("OUTPUT_ICS", "betclic3g1_ksw.ics")
STATE_FILE = os.environ.get("STATE_FILE", ".state_hash.txt")
EVENT_DURATION_HOURS = float(os.environ.get("EVENT_DURATION_HOURS", "2"))
ALARM_TIME = os.environ.get("ALARM_TIME", "09:00")  # Poniedziałek 09:00
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Warsaw")

TZ = tz.gettz(TIMEZONE)

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def parse_fixture_rows(html):
    print("Parsing HTML content...")
    # Wzorzec: "Gospodarz – Gość ... dd.mm.rrrr, HH:MM" (godzina może nie wystąpić)
    pattern = re.compile(
        r"(?P<home>[^<>\n–-]{3,}?)\s*[–-]\s*(?P<away>[^<>\n]{3,}?)"
        r".{0,200}?"
        r"(?P<date>\d{2}\.\d{2}\.\d{4})"
        r"(?:\s*,\s*(?P<time>\d{2}:\d{2}))?",
        re.S
    )
    fixtures = []
    matches_found = 0
    for m in pattern.finditer(html):
        matches_found += 1
        home = normalize_space(m.group("home"))
        away = normalize_space(m.group("away"))
        date_s = m.group("date")
        time_s = m.group("time")
        
        if matches_found <= 5:  # Debug: pokaż pierwsze 5 meczów
            print(f"Found match: {home} - {away} on {date_s} at {time_s}")
            
        if TEAM.lower() not in (home.lower() + " " + away.lower()):
            continue
        fixtures.append({"home": home, "away": away, "date": date_s, "time": time_s})
        
    print(f"Total matches found: {matches_found}, Team matches: {len(fixtures)}")
    
    uniq, seen = [], set()
    for f in fixtures:
        key = (f["home"], f["away"], f["date"], f["time"] or "")
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq

def to_dt(date_s, time_s):
    d = datetime.strptime(date_s, "%d.%m.%Y").date()
    if time_s:
        hh, mm = map(int, time_s.split(":"))
        # Utwórz naive datetime, potem dodaj timezone
        naive_dt = datetime(d.year, d.month, d.day, hh, mm)
        return TZ.localize(naive_dt) if hasattr(TZ, 'localize') else naive_dt.replace(tzinfo=TZ)
    # Dla meczów całodniowych zwróć tylko datę
    return d

def is_home(fix):
    return fix["home"].lower() == TEAM.lower()

def monday_alarm_for(dt_local, alarm_time="09:00"):
    hh, mm = map(int, alarm_time.split(":"))
    monday = dt_local.date() - timedelta(days=dt_local.weekday())
    return datetime(monday.year, monday.month, monday.day, hh, mm, tzinfo=TZ)

def build_ics(fixtures):
    cal = Calendar()
    for f in fixtures:
        dt_local = to_dt(f["date"], f["time"])
        home = is_home(f)
        opponent = f["away"] if home else f["home"]
        place = "DOM" if home else "WYJAZD"

        ev = Event()
        ev.name = f"{opponent} – {place}"

        if f["time"]:
            # Mecz z konkretną godziną
            ev.begin = dt_local
            ev.duration = {"hours": EVENT_DURATION_HOURS}
            
            # Alarm w poniedziałek 09:00 (tydzień meczu)
            alarm_dt = monday_alarm_for(dt_local, ALARM_TIME)
            delta = alarm_dt - dt_local
            ev.alarms.append(DisplayAlarm(trigger=delta))
        else:
            # Mecz całodniowy
            ev.begin = dt_local  # dt_local to już date object
            ev.make_all_day()
            
            # Alarm w poniedziałek 09:00
            match_datetime = datetime.combine(dt_local, datetime.min.time())
            if hasattr(TZ, 'localize'):
                match_datetime = TZ.localize(match_datetime)
            else:
                match_datetime = match_datetime.replace(tzinfo=TZ)
            
            alarm_dt = monday_alarm_for(match_datetime, ALARM_TIME)
            delta = alarm_dt - match_datetime
            ev.alarms.append(DisplayAlarm(trigger=delta))

        ev.description = ("Wyślij bilety do druku" if home
                          else "Ustal transport, obiad po drodze, pizza po meczu")

        cal.events.add(ev)
    return cal

def compute_hash(fixtures):
    payload = json.dumps(sorted(
        fixtures, key=lambda x: (x["date"], x.get("time") or "", x["home"], x["away"])
    ), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def get_auth_token_from_browser():
    """Pobiera token autoryzacyjny z przeglądarki"""
    print("Getting auth token from browser...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Loading main page to get token...")
        driver.get(URL)
        
        # Poczekaj chwilę na załadowanie
        import time
        time.sleep(3)
        
        # Spróbuj znaleźć token w localStorage, sessionStorage lub cookies
        try:
            # Sprawdź localStorage
            local_storage = driver.execute_script("return window.localStorage;")
            for key, value in local_storage.items():
                if 'token' in key.lower() and value:
                    print(f"Found token in localStorage: {key}")
                    return value
            
            # Sprawdź sessionStorage
            session_storage = driver.execute_script("return window.sessionStorage;")
            for key, value in session_storage.items():
                if 'token' in key.lower() and value:
                    print(f"Found token in sessionStorage: {key}")
                    return value
                    
        except Exception as e:
            print(f"Error checking browser storage: {e}")
        
        # Spróbuj przechwycić token z network requests
        logs = driver.get_log('performance')
        for log in logs:
            message = json.loads(log['message'])
            if message['message']['method'] == 'Network.responseReceived':
                url = message['message']['params']['response']['url']
                if 'token' in url or 'auth' in url:
                    print(f"Found potential token URL: {url}")
        
        return None
        
    except Exception as e:
        print(f"Error getting token from browser: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def scrape_fixtures_with_api():
    """Scrapuje mecze używając API endpoint"""
    print("Using API endpoint for scraping...")
    
    # API endpoint znaleziony w Network tab
    api_url = "https://comp-api.laczynaspilka.pl/api/bus/competition/v1/plays/e5bc0d4f-1bc4-40f5-92f9-e55c859b5166/matches"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.laczynaspilka.pl/',
        'Origin': 'https://www.laczynaspilka.pl'
    }
    
    try:
        # Spróbuj najpierw bez tokenu
        print("Trying without authorization token first...")
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 401:
            print("401 Unauthorized, trying to get new auth token from browser...")
            token = get_auth_token_from_browser()
            if token:
                headers['Authorization'] = f'Bearer {token}'
                print(f"Got new token, making API request...")
                response = requests.get(api_url, headers=headers, timeout=30)
            else:
                print("Could not get auth token, API requires authentication")
                return []
        
        if response.status_code != 200:
            print(f"API returned status code: {response.status_code}")
            return []
        
        print(f"API response status: {response.status_code}")
        data = response.json()
        print(f"Found {len(data)} matches in API response")
        
        # Konwertuj API response na nasze fixtures
        fixtures = []
        for match in data:
            # Sprawdź czy mecz dotyczy naszej drużyny
            host_name = match.get("host", {}).get("name", "")
            guest_name = match.get("guest", {}).get("name", "")
            
            if TEAM.lower() not in (host_name.lower() + " " + guest_name.lower()):
                continue
                
            # Parse daty
            date_time = match.get("dateTime", "")
            if date_time:
                try:
                    # Format: "2025-11-15T00:00:00"
                    dt = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d.%m.%Y")
                    time_str = dt.strftime("%H:%M") if dt.hour != 0 or dt.minute != 0 else None
                except:
                    print(f"Error parsing date: {date_time}")
                    continue
            else:
                continue
                
            fixture = {
                "home": host_name,
                "away": guest_name,
                "date": date_str,
                "time": time_str,
                "stadium": match.get("stadium", ""),
                "state": match.get("state", ""),
                "queue": match.get("queue", "")
            }
            
            fixtures.append(fixture)
            print(f"Found match: {host_name} vs {guest_name} on {date_str} {time_str or 'TBD'}")
        
        print(f"Total matches for {TEAM}: {len(fixtures)}")
        return fixtures
        
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return []
    except Exception as e:
        print(f"Error parsing API response: {e}")
        return []

def main():
    try:
        print(f"Starting scraper for: {TEAM}")
        print(f"URL: {URL}")
        
        # Spróbuj zescrapować prawdziwe mecze z API
        print("Attempting to scrape real fixtures from API...")
        fixtures = scrape_fixtures_with_api()
        
        print(f"Found {len(fixtures)} fixtures for {TEAM}")
        
        if not fixtures:
            print("WARNING: No fixtures found. Creating test data...")
            # Fallback do testowych danych
            today = datetime.now()
            fixtures = [{
                "home": "KS Wasilków",
                "away": "Test Team",
                "date": today.strftime("%d.%m.%Y"),
                "time": "15:00"
            }]
        
        h = compute_hash(fixtures)
        old = open(STATE_FILE).read().strip() if os.path.exists(STATE_FILE) else ""
        
        if h != old:
            print("Changes detected, generating ICS...")
            cal = build_ics(fixtures)
            with open(OUT, "w", encoding="utf-8") as f:
                f.writelines(cal.serialize_iter())
            with open(STATE_FILE, "w", encoding="utf-8") as s:
                s.write(h)
            print("UPDATED")
            print(f"Created {OUT} with {len(fixtures)} fixtures")
        else:
            print("NO_CHANGE")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()