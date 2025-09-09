#!/usr/bin/env python3

import requests
import json
import re
from urllib.parse import urlparse, parse_qs

# Original URL
URL = "https://www.laczynaspilka.pl/rozgrywki?season=e9d66181-d03e-4bb3-b889-4da848f4831d&leagueGroup=43da7ba1-b751-4295-814b-24bd37fd2d45&leagueId=5cc45e5f-744b-428c-b8af-cdefca38de29&enumType=Play&group=e5bc0d4f-1bc4-40f5-92f9-e55c859b5166&isAdvanceMode=false&genderType=Male"

# Parse URL parameters
parsed = urlparse(URL)
params = parse_qs(parsed.query)

print("URL Parameters:")
for key, value in params.items():
    print(f"  {key}: {value[0] if value else ''}")

print("\nTrying to find API endpoints...")

# Common API patterns for sports websites
api_patterns = [
    "https://www.laczynaspilka.pl/api/fixtures",
    "https://www.laczynaspilka.pl/api/matches",
    "https://www.laczynaspilka.pl/api/rozgrywki",
    "https://www.laczynaspilka.pl/api/schedule",
    f"https://www.laczynaspilka.pl/api/fixtures?season={params.get('season', [''])[0]}&leagueGroup={params.get('leagueGroup', [''])[0]}",
    f"https://www.laczynaspilka.pl/api/matches?season={params.get('season', [''])[0]}&leagueGroup={params.get('leagueGroup', [''])[0]}",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': URL
}

for api_url in api_patterns:
    try:
        print(f"\nTrying: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type:
                try:
                    data = response.json()
                    print(f"JSON response with {len(data) if isinstance(data, list) else 'object'} items")
                    if isinstance(data, list) and len(data) > 0:
                        print("Sample item:", json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
                    elif isinstance(data, dict):
                        print("Response keys:", list(data.keys()))
                except:
                    print("Response is not valid JSON")
            else:
                print(f"Content length: {len(response.text)}")
                if len(response.text) < 1000:
                    print("Response:", response.text[:500])
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*50)
print("Checking main page for JavaScript API calls...")

# Look for API endpoints in the main page
try:
    response = requests.get(URL, headers=headers, timeout=10)
    html = response.text
    
    # Look for API endpoints in JavaScript
    api_matches = re.findall(r'[\'"`]([^\'"`]*api[^\'"`]*)[\'"`]', html, re.IGNORECASE)
    if api_matches:
        print("Found potential API endpoints in page:")
        for match in set(api_matches):
            if len(match) > 10:  # Filter out short matches
                print(f"  {match}")
    
    # Look for common AJAX patterns
    ajax_patterns = [
        r'\.get\([\'"`]([^\'"`]+)[\'"`]',
        r'\.post\([\'"`]([^\'"`]+)[\'"`]',
        r'fetch\([\'"`]([^\'"`]+)[\'"`]',
        r'XMLHttpRequest.*open.*[\'"`]([^\'"`]+)[\'"`]'
    ]
    
    for pattern in ajax_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            print(f"\nFound AJAX calls:")
            for match in set(matches):
                if len(match) > 10:
                    print(f"  {match}")

except Exception as e:
    print(f"Error analyzing main page: {e}")
