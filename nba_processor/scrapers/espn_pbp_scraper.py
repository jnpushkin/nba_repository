"""
ESPN play-by-play scraper for NBA games.

Fetches play-by-play data from ESPN API for detailed game analysis.
Uses ESPN's scoreboard API to find game IDs, then fetches PBP from the summary endpoint.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests

from ..utils.constants import BASE_DIR

# Rate limiting
RATE_LIMIT_DELAY = 1.0  # seconds between requests
_last_request_time = 0.0

# ESPN API endpoints
ESPN_NBA_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
ESPN_NBA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

# Cache directory
CACHE_DIR = BASE_DIR / "cache" / "espn_pbp"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# NBA team name normalization for matching ESPN teams to Basketball Reference teams
NBA_TEAM_ALIASES = {
    'boston celtics': 'celtics', 'celtics': 'celtics',
    'brooklyn nets': 'nets', 'nets': 'nets',
    'new york knicks': 'knicks', 'knicks': 'knicks',
    'philadelphia 76ers': '76ers', '76ers': '76ers', 'sixers': '76ers',
    'toronto raptors': 'raptors', 'raptors': 'raptors',
    'chicago bulls': 'bulls', 'bulls': 'bulls',
    'cleveland cavaliers': 'cavaliers', 'cavaliers': 'cavaliers', 'cavs': 'cavaliers',
    'detroit pistons': 'pistons', 'pistons': 'pistons',
    'indiana pacers': 'pacers', 'pacers': 'pacers',
    'milwaukee bucks': 'bucks', 'bucks': 'bucks',
    'atlanta hawks': 'hawks', 'hawks': 'hawks',
    'charlotte hornets': 'hornets', 'hornets': 'hornets',
    'miami heat': 'heat', 'heat': 'heat',
    'orlando magic': 'magic', 'magic': 'magic',
    'washington wizards': 'wizards', 'wizards': 'wizards',
    'denver nuggets': 'nuggets', 'nuggets': 'nuggets',
    'minnesota timberwolves': 'timberwolves', 'timberwolves': 'timberwolves', 'wolves': 'timberwolves',
    'oklahoma city thunder': 'thunder', 'thunder': 'thunder', 'okc thunder': 'thunder',
    'portland trail blazers': 'trail blazers', 'trail blazers': 'trail blazers', 'blazers': 'trail blazers',
    'utah jazz': 'jazz', 'jazz': 'jazz',
    'golden state warriors': 'warriors', 'warriors': 'warriors',
    'los angeles clippers': 'clippers', 'la clippers': 'clippers', 'clippers': 'clippers',
    'los angeles lakers': 'lakers', 'la lakers': 'lakers', 'lakers': 'lakers',
    'phoenix suns': 'suns', 'suns': 'suns',
    'sacramento kings': 'kings', 'kings': 'kings',
    'dallas mavericks': 'mavericks', 'mavericks': 'mavericks', 'mavs': 'mavericks',
    'houston rockets': 'rockets', 'rockets': 'rockets',
    'memphis grizzlies': 'grizzlies', 'grizzlies': 'grizzlies',
    'new orleans pelicans': 'pelicans', 'pelicans': 'pelicans',
    'san antonio spurs': 'spurs', 'spurs': 'spurs',
}


def _normalize_nba_team(name: str) -> str:
    """Normalize NBA team name for matching."""
    return NBA_TEAM_ALIASES.get(name.lower().strip(), name.lower().strip())


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _lookup_espn_id_from_scoreboard(
    away_team: str,
    home_team: str,
    date_yyyymmdd: str,
    verbose: bool = False
) -> Optional[str]:
    """
    Look up ESPN game ID from ESPN's NBA scoreboard API.

    Args:
        away_team: Away team name
        home_team: Home team name
        date_yyyymmdd: Game date in YYYYMMDD format
        verbose: Print status messages

    Returns:
        ESPN game ID or None if not found
    """
    _rate_limit()

    url = f"{ESPN_NBA_SCOREBOARD_URL}?dates={date_yyyymmdd}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            if verbose:
                print(f"  Scoreboard request failed: {response.status_code}")
            return None

        data = response.json()
        events = data.get('events', [])

        away_norm = _normalize_nba_team(away_team)
        home_norm = _normalize_nba_team(home_team)

        for event in events:
            competitions = event.get('competitions', [])
            if not competitions:
                continue

            comp = competitions[0]
            competitors = comp.get('competitors', [])

            espn_home = None
            espn_away = None

            for c in competitors:
                team = c.get('team', {})
                team_names = [
                    _normalize_nba_team(team.get('displayName', '')),
                    _normalize_nba_team(team.get('shortDisplayName', '')),
                    _normalize_nba_team(team.get('name', '')),
                ]
                if c.get('homeAway') == 'home':
                    espn_home = team_names
                else:
                    espn_away = team_names

            if espn_home and espn_away:
                home_match = any(home_norm == n or home_norm in n or n in home_norm for n in espn_home if n)
                away_match = any(away_norm == n or away_norm in n or n in away_norm for n in espn_away if n)

                if home_match and away_match:
                    return event.get('id')

    except (requests.RequestException, json.JSONDecodeError) as e:
        if verbose:
            print(f"  Scoreboard lookup error: {e}")

    return None


def fetch_espn_play_by_play(
    game_id: str,
    use_cache: bool = True,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Fetch play-by-play data from ESPN API.

    Args:
        game_id: ESPN game ID
        use_cache: Whether to use cached data if available
        verbose: Print status messages

    Returns:
        Parsed play-by-play data or None on failure
    """
    if not game_id:
        return None

    # Check cache first
    cache_file = CACHE_DIR / f"{game_id}.json"
    if use_cache and cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            if verbose:
                print(f"  Using cached PBP for game {game_id}")
            return cached
        except (json.JSONDecodeError, IOError):
            pass

    _rate_limit()

    url = f"{ESPN_NBA_SUMMARY_URL}?event={game_id}"

    if verbose:
        print(f"  Fetching ESPN PBP for game {game_id}...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            if verbose:
                print(f"  ESPN API returned status {response.status_code}")
            return None

        raw_data = response.json()
        parsed = parse_espn_plays(raw_data)

        if parsed and parsed.get('plays'):
            if verbose:
                print(f"  Got {len(parsed['plays'])} plays from ESPN API")

            # Cache the parsed data
            try:
                with open(cache_file, 'w') as f:
                    json.dump(parsed, f, indent=2)
            except IOError as e:
                if verbose:
                    print(f"  Warning: Could not cache PBP: {e}")

            return parsed

    except (requests.RequestException, json.JSONDecodeError) as e:
        if verbose:
            print(f"  ESPN PBP request error: {e}")

    return None


def parse_espn_plays(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse ESPN API response into standardized play format.

    Args:
        raw_data: Raw ESPN API response

    Returns:
        Standardized play-by-play data
    """
    if not raw_data:
        return None

    # Get teams info
    teams_data = raw_data.get('boxscore', {}).get('teams', [])
    teams = {}
    for team in teams_data:
        team_info = team.get('team', {})
        team_id = team_info.get('id')
        home_away = team.get('homeAway', '')
        if team_id and home_away:
            teams[str(team_id)] = {
                'name': team_info.get('displayName', ''),
                'short_name': team_info.get('shortDisplayName', ''),
                'abbreviation': team_info.get('abbreviation', ''),
                'side': home_away,
            }

    # Get plays
    plays_data = raw_data.get('plays', [])
    if not plays_data:
        return None

    parsed_plays = []

    for play in plays_data:
        play_text = play.get('text', '')
        if not play_text:
            continue

        clock = play.get('clock', {})
        display_value = clock.get('displayValue', '')

        period = play.get('period', {})
        period_number = period.get('number', 1)

        away_score = play.get('awayScore', 0)
        home_score = play.get('homeScore', 0)

        team_id = str(play.get('team', {}).get('id', ''))
        team_info = teams.get(team_id, {})
        team_name = team_info.get('name', '')
        team_side = team_info.get('side', '')

        scoring_play = play.get('scoringPlay', False)
        score_value = play.get('scoreValue', 0)

        # Try participants first for player name
        player_name = ''
        participants = play.get('participants', [])
        for p in participants:
            athlete = p.get('athlete', {})
            if athlete.get('displayName'):
                player_name = athlete.get('displayName')
                break

        if not player_name:
            player_name = _extract_player_from_text(play_text)

        play_type = _classify_espn_play(play_text, play.get('type', {}))

        parsed_plays.append({
            'time': display_value,
            'period': period_number,
            'team': team_name,
            'team_side': team_side,
            'player': player_name,
            'text': play_text,
            'play_type': play_type,
            'scoring_play': scoring_play,
            'score_value': score_value,
            'away_score': away_score,
            'home_score': home_score,
        })

    final_away = parsed_plays[-1]['away_score'] if parsed_plays else 0
    final_home = parsed_plays[-1]['home_score'] if parsed_plays else 0

    away_team = None
    home_team = None
    for tid, tinfo in teams.items():
        if tinfo['side'] == 'away':
            away_team = tinfo['name']
        elif tinfo['side'] == 'home':
            home_team = tinfo['name']

    return {
        'espn_id': raw_data.get('header', {}).get('id', ''),
        'away_team': away_team or '',
        'home_team': home_team or '',
        'away_score': final_away,
        'home_score': final_home,
        'plays': parsed_plays,
        'play_count': len(parsed_plays),
    }


def _extract_player_from_text(text: str) -> str:
    """Extract player name from ESPN play text."""
    if not text:
        return ''

    name_pattern = r"[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*(?:\s+(?:Jr\.|Sr\.|III|IV|II|V))?"

    patterns = [
        (rf'^({name_pattern})\s+(?:made|missed|makes|misses)', 1),
        (rf'Foul on\s+({name_pattern})', 1),
        (rf'(?:shot|layup|dunk|jumper|pointer|throw)\s+by\s+({name_pattern})', 1),
        (rf'(?<!Assisted\s)(?<!assists\s)by\s+({name_pattern})\s*\.?\s*$', 1),
        (rf'(?<!Assisted\s)(?<!assists\s)by\s+({name_pattern})', 1),
        (rf'^({name_pattern})\s+(?:Assist|Offensive Rebound|Defensive Rebound|Steal|Block|Turnover)', 1),
    ]

    for pattern, group in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(group).strip()
            if ' ' in name or name.endswith('.'):
                return name

    return ''


def _classify_espn_play(text: str, play_type_info: Dict) -> str:
    """Classify ESPN play into a type category."""
    text_lower = text.lower()

    if 'made' in text_lower:
        if 'three point' in text_lower or '3pt' in text_lower or '3-pt' in text_lower:
            return 'made_three'
        elif 'free throw' in text_lower:
            return 'made_ft'
        elif 'dunk' in text_lower:
            return 'made_dunk'
        elif 'layup' in text_lower:
            return 'made_layup'
        elif 'jumper' in text_lower or 'jump shot' in text_lower:
            return 'made_jumper'
        else:
            return 'made_fg'

    if 'missed' in text_lower:
        if 'three point' in text_lower or '3pt' in text_lower or '3-pt' in text_lower:
            return 'missed_three'
        elif 'free throw' in text_lower:
            return 'missed_ft'
        else:
            return 'missed_fg'

    if 'rebound' in text_lower:
        if 'offensive' in text_lower:
            return 'offensive_rebound'
        elif 'defensive' in text_lower:
            return 'defensive_rebound'
        return 'rebound'

    if 'turnover' in text_lower: return 'turnover'
    if 'steal' in text_lower: return 'steal'
    if 'block' in text_lower: return 'block'
    if 'foul' in text_lower: return 'foul'
    if 'assist' in text_lower: return 'assist'
    if 'timeout' in text_lower: return 'timeout'
    if 'jump ball' in text_lower: return 'jump_ball'
    if 'end' in text_lower and ('quarter' in text_lower or 'period' in text_lower or 'game' in text_lower):
        return 'period_end'

    return 'other'


def get_espn_pbp_for_game(
    away_team: str,
    home_team: str,
    date_yyyymmdd: str,
    verbose: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get ESPN PBP for a game by team names and date.

    Args:
        away_team: Away team name
        home_team: Home team name
        date_yyyymmdd: Game date in YYYYMMDD format
        verbose: Print status messages

    Returns:
        Parsed play-by-play data or None
    """
    espn_id = _lookup_espn_id_from_scoreboard(away_team, home_team, date_yyyymmdd, verbose)

    if not espn_id:
        if verbose:
            print(f"  ESPN ID not found for {away_team} @ {home_team} ({date_yyyymmdd})")
        return None

    if verbose:
        print(f"  Found ESPN ID {espn_id} for {away_team} @ {home_team}")

    return fetch_espn_play_by_play(espn_id, use_cache=True, verbose=verbose)


def clear_pbp_cache():
    """Clear the ESPN play-by-play cache."""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Cleared ESPN PBP cache at {CACHE_DIR}")
