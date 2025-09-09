import json, os, re, hashlib
from datetime import datetime, timedelta
from dateutil import tz
from ics import Calendar, Event, DisplayAlarm
import requests

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
        return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
    return datetime(d.year, d.month, d.day, 0, 0, tzinfo=TZ)

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
        ev.name = f"{opponent} \u2013 {place}"

        if f["time"]:
            ev.begin = dt_local
            ev.duration = {"hours": EVENT_DURATION_HOURS}
        else:
            ev.begin = dt_local.date()
            ev.make_all_day()

        ev.description = ("Wyślij bilety do druku" if home
                          else "Ustal transport, obiad po drodze, pizza po meczu")

        # Alarm w poniedziałek 09:00 (tydzień meczu)
        alarm_dt = monday_alarm_for(dt_local, ALARM_TIME)
        start_ref = (dt_local if f["time"]
                     else datetime(dt_local.year, dt_local.month, dt_local.day, 0, 0, tzinfo=TZ))
        delta = alarm_dt - start_ref
        ev.alarms.append(DisplayAlarm(trigger=delta))

        cal.events.add(ev)
    return cal

def compute_hash(fixtures):
    payload = json.dumps(sorted(
        fixtures, key=lambda x: (x["date"], x.get("time") or "", x["home"], x["away"])
    ), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def main():
    try:
        print(f"Starting scraper for: {TEAM}")
        print(f"URL: {URL}")
        
        # Użyj requests zamiast Playwright
        print("Making HTTP request...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        
        print(f"Got response, content length: {len(html)}")
        
        print("Parsing fixtures...")
        fixtures = parse_fixture_rows(html)
            
        print(f"Found {len(fixtures)} fixtures for {TEAM}")
        
        if not fixtures:
            print("WARNING: No fixtures parsed. Check selectors or page layout.")
            # Zapisz fragment HTML do debugowania
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html[:5000])  # Pierwsze 5000 znaków
            print("Saved first 5000 chars to debug.html")
            return

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
        else:
            print("NO_CHANGE")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()