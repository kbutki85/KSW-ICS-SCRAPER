#!/usr/bin/env python3

import re
from requests_html import HTMLSession

URL = "https://www.laczynaspilka.pl/rozgrywki?season=e9d66181-d03e-4bb3-b889-4da848f4831d&leagueGroup=43da7ba1-b751-4295-814b-24bd37fd2d45&leagueId=5cc45e5f-744b-428c-b8af-cdefca38de29&enumType=Play&group=e5bc0d4f-1bc4-40f5-92f9-e55c859b5166&isAdvanceMode=false&genderType=Male"

print("Getting rendered content...")
session = HTMLSession()
response = session.get(URL, timeout=30)
response.html.render(timeout=10, wait=1)  # Shorter wait time
html = response.html.html

print(f"Rendered content length: {len(html)}")

# Save rendered content
with open("full_rendered.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Saved full rendered content to full_rendered.html")

# Look for team name patterns
team_patterns = [
    "KS Wasilków",
    "Wasilków", 
    "wasilkow",
    "wasilków"
]

for pattern in team_patterns:
    matches = len(re.findall(pattern, html, re.IGNORECASE))
    print(f"Found '{pattern}': {matches} times")

# Look for date patterns
date_pattern = r'\d{2}\.\d{2}\.\d{4}'
date_matches = re.findall(date_pattern, html)
print(f"Found dates: {len(date_matches)} - first few: {date_matches[:5]}")

# Look for common match indicators
match_indicators = [
    r'vs\.?',
    r' - ',
    r' – ',
    r'mecz',
    r'match',
    r'fixture'
]

for indicator in match_indicators:
    matches = len(re.findall(indicator, html, re.IGNORECASE))
    print(f"Found '{indicator}': {matches} times")

print("\nLooking for table/list structures...")
# Look for table or list structures that might contain matches
table_matches = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
tr_matches = len(re.findall(r'<tr[^>]*>', html, re.IGNORECASE))
li_matches = len(re.findall(r'<li[^>]*>', html, re.IGNORECASE))
div_matches = len(re.findall(r'<div[^>]*>', html, re.IGNORECASE))

print(f"Tables: {table_matches}, Rows: {tr_matches}, List items: {li_matches}, Divs: {div_matches}")
