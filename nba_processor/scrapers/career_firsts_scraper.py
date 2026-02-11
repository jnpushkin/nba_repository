"""
NBA Career Firsts Scraper
=========================
Scrapes Basketball-Reference game logs to identify when players achieved
career firsts (first points, first rebound, etc.) and career milestones.

Usage:
    python3 -m nba_processor.scrapers.career_firsts_scraper
    python3 -m nba_processor.scrapers.career_firsts_scraper --player jamesle01
    python3 -m nba_processor.scrapers.career_firsts_scraper --refresh

Requirements:
    pip install requests beautifulsoup4 cloudscraper
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from bs4 import BeautifulSoup, Comment
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install beautifulsoup4")
    sys.exit(1)

# Try to import cloudscraper for Cloudflare bypass, fall back to requests
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    import requests
    HAS_CLOUDSCRAPER = False


# Career first milestones to track
CAREER_FIRSTS = {
    'PTS': 'First Career Points',
    'TRB': 'First Career Rebound',
    'AST': 'First Career Assist',
    'STL': 'First Career Steal',
    'BLK': 'First Career Block',
    'FG3': 'First Career 3-Pointer',
    'FT': 'First Career Free Throw',
    'TOV': 'First Career Turnover',  # Not really a milestone but tracks activity
}

# Career milestone thresholds to track
CAREER_MILESTONES = {
    'PTS': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
            11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000,
            21000, 22000, 23000, 24000, 25000, 26000, 27000, 28000, 29000, 30000,
            31000, 32000, 33000, 34000, 35000, 36000, 37000, 38000, 39000, 40000],
    'TRB': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
            11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000],
    'AST': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
            11000, 12000, 13000, 14000, 15000],
    'STL': [500, 1000, 1500, 2000, 2500, 3000],
    'BLK': [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000],
    'FG3': [500, 1000, 1500, 2000, 2500, 3000, 3500],
    'FT': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
    'G': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
          1100, 1200, 1300, 1400, 1500, 1600],
    'MP': [10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000],
}

# Milestone display names
STAT_NAMES = {
    'PTS': 'Point',
    'TRB': 'Rebound',
    'AST': 'Assist',
    'STL': 'Steal',
    'BLK': 'Block',
    'FG3': '3-Pointer',
    'FT': 'Free Throw',
    'G': 'Game',
    'MP': 'Minute',
    'TOV': 'Turnover',
}


def extract_commented_tables(soup: BeautifulSoup) -> list:
    """
    Basketball Reference hides some tables inside HTML comments for lazy loading.
    This function extracts and parses those hidden tables.

    Returns a list of BeautifulSoup table elements found in comments.
    """
    tables = []

    # Find all comments in the document
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        # Check if the comment contains a table
        if '<table' in comment:
            # Parse the comment content as HTML
            comment_soup = BeautifulSoup(comment, 'html.parser')
            # Find tables within the parsed comment
            for table in comment_soup.find_all('table'):
                tables.append(table)

    return tables


def find_table_by_id(soup: BeautifulSoup, table_ids: list[str]) -> BeautifulSoup:
    """
    Find a table by ID, checking both regular tables and commented-out tables.

    Args:
        soup: BeautifulSoup object of the page
        table_ids: List of table IDs to search for (in priority order)

    Returns:
        The found table or None
    """
    # First try to find visible tables
    for table_id in table_ids:
        table = soup.find('table', {'id': table_id})
        if table:
            return table

    # If not found, check tables hidden in comments
    commented_tables = extract_commented_tables(soup)
    for table in commented_tables:
        table_id = table.get('id', '')
        if table_id in table_ids:
            return table

    return None


def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / '.project_root').exists():
            return parent
        if (parent / 'nba_processor').is_dir() and (parent / 'cache').is_dir():
            return parent
    return Path.cwd()


def get_cache_path() -> Path:
    """Get the cache directory path."""
    return get_project_root() / 'cache' / 'career_firsts'


def load_career_firsts_cache() -> dict:
    """Load the career firsts cache from disk."""
    cache_file = get_cache_path() / 'career_firsts.json'
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}


def save_career_firsts_cache(cache: dict):
    """Save the career firsts cache to disk."""
    cache_path = get_cache_path()
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_file = cache_path / 'career_firsts.json'
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)


def create_scraper():
    """Create an HTTP scraper (cloudscraper or requests)."""
    if HAS_CLOUDSCRAPER:
        return cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
    return None


class RateLimitError(Exception):
    """Raised when Basketball-Reference rate limits us."""
    pass


class NotFoundError(Exception):
    """Raised when a player page is not found (legitimate 404)."""
    pass


def fetch_url(url: str, scraper=None, timeout: int = 30, max_retries: int = 3) -> Optional[str]:
    """
    Fetch a URL with appropriate headers and retry logic.

    Raises:
        RateLimitError: When rate limited (429, 403, or suspected blocking)
        NotFoundError: When page genuinely doesn't exist (404)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            if scraper and HAS_CLOUDSCRAPER:
                response = scraper.get(url, timeout=timeout)
            else:
                import requests
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
                response = requests.get(url, headers=headers, timeout=timeout)

            # Check for rate limiting
            if response.status_code == 429:
                raise RateLimitError("Rate limited (429 Too Many Requests)")

            if response.status_code == 403:
                if 'cloudflare' in response.text.lower() or 'captcha' in response.text.lower():
                    raise RateLimitError("Blocked by Cloudflare/CAPTCHA (403)")
                raise RateLimitError("Access forbidden (403) - likely rate limited")

            if response.status_code == 404:
                raise NotFoundError(f"Page not found: {url}")

            if response.status_code == 503:
                raise RateLimitError("Service unavailable (503) - server overloaded or blocking")

            response.raise_for_status()

            content = response.text
            rate_limit_indicators = [
                'rate limit', 'too many requests', 'slow down',
                'blocked', 'captcha', 'please wait', 'access denied'
            ]
            content_lower = content.lower()
            for indicator in rate_limit_indicators:
                if indicator in content_lower and len(content) < 5000:
                    raise RateLimitError(f"Rate limit detected in response: '{indicator}'")

            return content

        except RateLimitError:
            raise
        except NotFoundError:
            raise
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            if '429' in error_str or '403' in error_str or 'forbidden' in error_str:
                raise RateLimitError(f"Rate limited: {e}")

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"    Connection error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"  Error fetching {url}: {e}")
                return None

    return None


def get_player_debut_year(player_id: str, scraper=None, verbose: bool = False) -> Optional[int]:
    """
    Get a player's debut year from their main page.

    Raises:
        RateLimitError: If rate limited by the server
    """
    first_letter = player_id[0]
    url = f"https://www.basketball-reference.com/players/{first_letter}/{player_id}.html"

    try:
        html = fetch_url(url, scraper)
    except NotFoundError:
        if verbose:
            print(f"    Player page not found: {url}")
        return None
    if not html:
        if verbose:
            print(f"    Failed to fetch player page: {url}")
        return None

    if verbose:
        print(f"    Fetched {len(html)} bytes from player page")

    soup = BeautifulSoup(html, 'html.parser')

    # Look for the per_game table to find first year
    # BREF may hide tables in HTML comments for lazy loading
    table = find_table_by_id(soup, ['per_game', 'per_game_stats', 'totals', 'totals_stats'])

    if not table:
        # Try finding any table with season data (visible tables first)
        for t in soup.find_all('table', class_='stats_table'):
            if t.find('th', {'data-stat': 'season'}):
                table = t
                break

    if not table:
        # Check commented tables too
        for t in extract_commented_tables(soup):
            if t.find('th', {'data-stat': 'season'}):
                table = t
                break

    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                if 'thead' in row.get('class', []):
                    continue
                # Try multiple possible data-stat values for season
                year_cell = row.find('th', {'data-stat': 'season'})
                if not year_cell:
                    year_cell = row.find('th', {'data-stat': 'year_id'})
                if not year_cell:
                    year_cell = row.find('td', {'data-stat': 'season'})
                if not year_cell:
                    year_cell = row.find('td', {'data-stat': 'year_id'})
                if not year_cell:
                    # Try first th or td with a year-like pattern
                    first_cell = row.find(['th', 'td'])
                    if first_cell:
                        text = first_cell.get_text(strip=True)
                        if len(text) >= 4 and text[:4].isdigit():
                            year_cell = first_cell
                if year_cell:
                    year_text = year_cell.get_text(strip=True)
                    # Format is like "2009-10" - get the first year
                    try:
                        return int(year_text[:4])
                    except ValueError:
                        pass

    return None


def scrape_game_log(player_id: str, year: int, scraper=None) -> list[dict]:
    """
    Scrape a player's game log for a specific season.

    Args:
        player_id: Basketball Reference player ID
        year: The ending year of the season (e.g., 2024 for 2023-24 season)
        scraper: HTTP scraper instance

    Returns:
        List of game dictionaries with stats

    Raises:
        RateLimitError: If rate limited by the server
    """
    first_letter = player_id[0]
    url = f"https://www.basketball-reference.com/players/{first_letter}/{player_id}/gamelog/{year}"

    try:
        html = fetch_url(url, scraper)
    except NotFoundError:
        return []
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Find the game log table - BREF uses various IDs and may hide in comments
    table = find_table_by_id(soup, ['pgl_basic', 'player_game_log_reg'])

    if not table:
        # Try finding by class (visible tables first)
        for t in soup.find_all('table', class_='stats_table'):
            # Game log tables have date_game column
            if t.find('td', {'data-stat': 'date_game'}) or t.find('th', {'data-stat': 'date_game'}):
                table = t
                break

    if not table:
        # Check commented tables for game log data
        for t in extract_commented_tables(soup):
            if t.find('td', {'data-stat': 'date_game'}) or t.find('th', {'data-stat': 'date_game'}):
                table = t
                break

    if not table:
        return []

    games = []
    tbody = table.find('tbody')
    if not tbody:
        return []

    # Stat mapping from BREF data-stat attributes
    STAT_MAP = {
        'PTS': 'pts',
        'TRB': 'trb',
        'AST': 'ast',
        'STL': 'stl',
        'BLK': 'blk',
        'FG3': 'fg3',
        'FT': 'ft',
        'TOV': 'tov',
        'MP': 'mp',
        'FG': 'fg',
        'FGA': 'fga',
        'FG3A': 'fg3a',
        'FTA': 'fta',
        'ORB': 'orb',
        'DRB': 'drb',
        'PF': 'pf',
        'PLUS_MINUS': 'plus_minus',
    }

    for row in tbody.find_all('tr'):
        row_class = row.get('class', [])
        if 'thead' in row_class or 'partial_table' in row_class:
            continue

        # Skip inactive games (DNP, Did Not Dress, etc.)
        reason_cell = row.find('td', {'data-stat': 'reason'})
        if reason_cell and reason_cell.get_text(strip=True):
            continue

        game = {}

        # Get game date - BREF uses 'date' not 'date_game'
        date_cell = row.find('td', {'data-stat': 'date'})
        if not date_cell:
            date_cell = row.find('td', {'data-stat': 'date_game'})
        if date_cell:
            game['date'] = date_cell.get_text(strip=True)
            # Date format is YYYY-MM-DD, convert to YYYYMMDD
            date_text = game['date'].replace('-', '')
            if len(date_text) == 8:
                game['date_full'] = date_text
            # Try to get game ID from link if present
            link = date_cell.find('a')
            if link:
                href = link.get('href', '')
                if '/boxscores/' in href:
                    game_id = href.split('/')[-1].replace('.html', '')
                    game['game_id'] = game_id

        # Get opponent - BREF uses 'opp_name_abbr' not 'opp_id'
        opp_cell = row.find('td', {'data-stat': 'opp_name_abbr'})
        if not opp_cell:
            opp_cell = row.find('td', {'data-stat': 'opp_id'})
        if opp_cell:
            game['opponent'] = opp_cell.get_text(strip=True)

        # Get stats
        for stat, attr in STAT_MAP.items():
            stat_cell = row.find('td', {'data-stat': attr})
            if stat_cell:
                text = stat_cell.get_text(strip=True)
                try:
                    if stat == 'MP':
                        # Minutes can be "32:45" format - convert to decimal
                        if ':' in text:
                            parts = text.split(':')
                            game[stat] = int(parts[0]) + int(parts[1]) / 60
                        else:
                            game[stat] = float(text) if text else 0
                    else:
                        game[stat] = int(text) if text else 0
                except ValueError:
                    game[stat] = 0

        # Only add if we have a date and the player actually played
        if game.get('date') and game.get('MP', 0) > 0:
            games.append(game)

    return games


def find_career_firsts(player_id: str, scraper=None, verbose: bool = True) -> dict:
    """
    Find all career firsts and milestones for a player by scanning their game logs.

    Returns dict with structure:
    {
        'player_id': str,
        'firsts': {
            'PTS': {'date': 'YYYYMMDD', 'game_id': str, ...},
            ...
        },
        'milestones': {
            'PTS': [{'number': 1000, 'date': ..., ...}, ...],
            ...
        },
        'career_totals': {'PTS': 12345, 'TRB': 6789, ...}
    }
    """
    if verbose:
        print(f"  Finding career firsts & milestones for {player_id}...")

    # Get debut year first (before creating result dict)
    debut_year = get_player_debut_year(player_id, scraper, verbose=verbose)
    if verbose:
        print(f"    Debut year: {debut_year}")
    if not debut_year:
        debut_year = 2015  # Fallback
        if verbose:
            print(f"    Using fallback debut year: {debut_year}")

    result = {
        'player_id': player_id,
        'firsts': {},
        'milestones': {},
        'career_totals': {},
        'games_played': 0,
        'scraped_at': datetime.now().isoformat(),
    }

    # NBA seasons span two years (e.g., 2009-10) and game log URLs use the ending year
    # So debut year 2009 means first game log is at /gamelog/2010
    start_year = debut_year + 1
    current_year = datetime.now().year + 1  # +1 because NBA season spans years
    if verbose:
        print(f"    Scanning seasons {debut_year}-{start_year} to {current_year-1}-{current_year}...")

    # Track which firsts we still need to find
    firsts_needed = set(CAREER_FIRSTS.keys())

    # Running totals for milestone tracking
    totals = {stat: 0 for stat in CAREER_MILESTONES.keys()}
    totals['G'] = 0  # Games played

    # Track which milestones we've already recorded
    milestones_reached = {stat: set() for stat in CAREER_MILESTONES.keys()}

    # Initialize milestone lists
    for stat in CAREER_MILESTONES.keys():
        result['milestones'][stat] = []

    # Scan years from debut to present (using ending year of each season)
    for year in range(start_year, current_year + 1):
        time.sleep(3.05)  # BREF rate limit
        games = scrape_game_log(player_id, year, scraper)
        if verbose and games:
            print(f"    {year}: {len(games)} games")
        elif verbose and year <= datetime.now().year:
            print(f"    {year}: 0 games (no data or fetch failed)")

        for game in games:
            # Increment games played
            totals['G'] += 1

            # Check for firsts
            for stat in list(firsts_needed):
                if game.get(stat, 0) > 0:
                    result['firsts'][stat] = {
                        'date': game.get('date_full', game.get('date', '')),
                        'game_id': game.get('game_id', ''),
                        'opponent': game.get('opponent', ''),
                        'year': year,
                        'milestone': CAREER_FIRSTS[stat],
                    }
                    firsts_needed.discard(stat)
                    if verbose:
                        print(f"    Found {CAREER_FIRSTS[stat]}: {game.get('date', '')}")

            # Update running totals and check for milestones
            for stat in CAREER_MILESTONES.keys():
                if stat == 'G':
                    # Games already counted above at line 550, just check milestone
                    old_total = totals[stat] - 1  # Before this game was added
                    new_total = totals[stat]
                else:
                    game_value = game.get(stat, 0)
                    if game_value <= 0:
                        continue
                    old_total = totals[stat]
                    totals[stat] += game_value
                    new_total = totals[stat]

                # Check if we crossed any milestone thresholds
                for threshold in CAREER_MILESTONES[stat]:
                    if old_total < threshold <= new_total:
                        if threshold not in milestones_reached[stat]:
                            milestones_reached[stat].add(threshold)
                            stat_name = STAT_NAMES.get(stat, stat)
                            milestone_name = f"Career {stat_name} #{threshold}"
                            result['milestones'][stat].append({
                                'number': threshold,
                                'date': game.get('date_full', game.get('date', '')),
                                'game_id': game.get('game_id', ''),
                                'opponent': game.get('opponent', ''),
                                'year': year,
                                'milestone': milestone_name,
                                'career_total_after': new_total,
                            })
                            if verbose:
                                print(f"    Found {milestone_name}: {game.get('date', '')}")

    # Store final career totals
    result['career_totals'] = {k: v for k, v in totals.items() if v > 0}
    result['games_played'] = totals['G']

    # Clean up empty milestone lists
    result['milestones'] = {k: v for k, v in result['milestones'].items() if v}

    return result


def get_players_from_games() -> tuple[set[str], dict[str, str]]:
    """Extract all unique player IDs and names from cached game data.

    Returns:
        Tuple of (player_ids set, player_names dict mapping id -> name)
    """
    player_ids = set()
    player_names = {}
    cache_dir = get_project_root() / 'cache'

    if not cache_dir.exists():
        print(f"Cache directory not found: {cache_dir}")
        return player_ids, player_names

    for json_file in cache_dir.glob('*.json'):
        if json_file.name == 'career_firsts.json':
            continue
        if json_file.parent.name == 'career_firsts':
            continue

        try:
            with open(json_file, 'r') as f:
                game_data = json.load(f)

            # Extract player IDs from box_score structure
            box_score = game_data.get('box_score', {})
            for side in ['away', 'home']:
                players = box_score.get(side, {}).get('players', [])
                if not players:
                    players = box_score.get(side, {}).get('basic', [])
                for player in players:
                    if player.get('player_id'):
                        player_ids.add(player['player_id'])
                        if player.get('name'):
                            player_names[player['player_id']] = player['name']

        except (json.JSONDecodeError, KeyError):
            continue

    return player_ids, player_names


def get_attended_game_ids() -> dict[str, dict]:
    """Get all attended game IDs and their details from cache."""
    games = {}
    cache_dir = get_project_root() / 'cache'

    for json_file in cache_dir.glob('*.json'):
        if json_file.name == 'career_firsts.json':
            continue
        if json_file.parent.name == 'career_firsts':
            continue

        try:
            with open(json_file, 'r') as f:
                game_data = json.load(f)

            game_id = game_data.get('game_id', '')
            basic_info = game_data.get('basic_info', {})

            if game_id:
                games[game_id] = {
                    'game_id': game_id,
                    'home_team': basic_info.get('home_team', ''),
                    'away_team': basic_info.get('away_team', ''),
                    'venue': basic_info.get('venue', ''),
                    'date': basic_info.get('date', ''),
                }

        except (json.JSONDecodeError, KeyError):
            continue

    return games


def find_witnessed_firsts(career_firsts_cache: dict, attended_games: dict) -> list[dict]:
    """Find career firsts and milestones that were witnessed at attended games."""
    witnessed = []

    for player_id, data in career_firsts_cache.items():
        # Skip metadata keys like _processed_games
        if player_id.startswith('_'):
            continue
        if not isinstance(data, dict):
            continue
        player_name = data.get('player_name', player_id)

        # Check firsts
        for stat, first_info in data.get('firsts', {}).items():
            game_id = first_info.get('game_id', '')
            game = attended_games.get(game_id)
            if game:
                witnessed.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'milestone': first_info.get('milestone', ''),
                    'date': first_info.get('date', ''),
                    'game_id': game_id,
                    'opponent': first_info.get('opponent', ''),
                    'venue': game.get('venue', ''),
                    'category': 'first',
                })

        # Check milestones
        for stat, milestones_list in data.get('milestones', {}).items():
            for milestone_info in milestones_list:
                game_id = milestone_info.get('game_id', '')
                game = attended_games.get(game_id)
                if game:
                    witnessed.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'milestone': milestone_info.get('milestone', ''),
                        'date': milestone_info.get('date', ''),
                        'game_id': game_id,
                        'opponent': milestone_info.get('opponent', ''),
                        'venue': game.get('venue', ''),
                        'category': 'milestone',
                    })

    return witnessed


def scrape_career_firsts_for_players(
    player_ids: set[str],
    refresh: bool = False,
    delay: float = 3.05,
    verbose: bool = True,
    player_names: dict[str, str] = None
) -> dict:
    """
    Scrape career firsts for a set of players.

    Args:
        player_ids: Set of player IDs to scrape
        refresh: If True, re-scrape even if cached
        delay: Delay between requests in seconds
        verbose: Print progress
        player_names: Optional dict mapping player_id -> name for display

    Returns:
        Updated cache dictionary
    """
    cache = load_career_firsts_cache()
    scraper = create_scraper()
    player_names = player_names or {}

    total = len(player_ids)
    consecutive_errors = 0
    max_consecutive_errors = 3

    for i, player_id in enumerate(sorted(player_ids), 1):
        name = player_names.get(player_id, player_id)
        display_name = f"{name} ({player_id})" if name != player_id else player_id

        if not refresh and player_id in cache:
            if verbose:
                print(f"[{i}/{total}] {display_name}: cached, skipping")
            continue

        if verbose:
            print(f"[{i}/{total}] Scraping {display_name}...")

        try:
            firsts = find_career_firsts(player_id, scraper, verbose)
            firsts['player_name'] = name
            cache[player_id] = firsts

            # Save after each player
            save_career_firsts_cache(cache)
            consecutive_errors = 0

            if i < total:
                time.sleep(delay)

        except RateLimitError as e:
            print(f"\n{'='*60}")
            print(f"⚠️  RATE LIMITED: {e}")
            print(f"{'='*60}")
            print(f"\nStopping scraper to avoid being blocked.")
            print(f"Progress saved: {len(cache)} players cached.")
            print(f"\nTo resume: python3 -m nba_processor.scrapers.career_firsts_scraper")
            break

        except NotFoundError:
            if verbose:
                print(f"  Player not found, skipping")
            continue

        except Exception as e:
            consecutive_errors += 1
            print(f"  Error processing {player_id}: {e}")

            if consecutive_errors >= max_consecutive_errors:
                print(f"\n{'='*60}")
                print(f"⚠️  TOO MANY CONSECUTIVE ERRORS ({consecutive_errors})")
                print(f"{'='*60}")
                print(f"\nProgress saved: {len(cache)} players cached.")
                break

            continue

    return cache


def main():
    parser = argparse.ArgumentParser(
        description="Scrape NBA career firsts from Basketball-Reference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scrape career firsts for all players in your games
    python3 -m nba_processor.scrapers.career_firsts_scraper

    # Scrape a specific player
    python3 -m nba_processor.scrapers.career_firsts_scraper --player jamesle01

    # Force refresh all cached data
    python3 -m nba_processor.scrapers.career_firsts_scraper --refresh

    # Check for witnessed firsts
    python3 -m nba_processor.scrapers.career_firsts_scraper --check-witnessed
        """
    )

    parser.add_argument(
        '--player', '-p',
        type=str,
        help="Scrape a specific player by ID (e.g., jamesle01)"
    )

    parser.add_argument(
        '--refresh', '-r',
        action='store_true',
        help="Refresh cached data even if already scraped"
    )

    parser.add_argument(
        '--check-witnessed', '-c',
        action='store_true',
        dest='check_witnessed',
        help="Check for career firsts witnessed at attended games"
    )

    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=3.05,
        help="Delay between requests in seconds (default: 3.05)"
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help="Suppress progress messages"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if args.check_witnessed:
        cache = load_career_firsts_cache()
        attended = get_attended_game_ids()
        witnessed = find_witnessed_firsts(cache, attended)

        if witnessed:
            print(f"\n{'='*60}")
            print("CAREER FIRSTS YOU WITNESSED")
            print(f"{'='*60}\n")

            for w in sorted(witnessed, key=lambda x: x['date']):
                print(f"  {w['milestone']}")
                print(f"    Player: {w['player_name']}")
                print(f"    Date: {w['date']}")
                print(f"    Venue: {w['venue']}")
                print()
        else:
            print("No career firsts found in attended games (or cache is empty).")
        return

    if args.player:
        player_ids = {args.player}
        player_names = {}
        refresh = args.refresh
    else:
        if verbose:
            print("Extracting player IDs from cached game data...")
        player_ids, player_names = get_players_from_games()
        if verbose:
            print(f"Found {len(player_ids)} unique players\n")
        refresh = args.refresh

    if not player_ids:
        print("No player IDs found. Run the main processor first to cache game data.")
        sys.exit(1)

    cache = scrape_career_firsts_for_players(
        player_ids,
        refresh=refresh,
        delay=args.delay,
        verbose=verbose,
        player_names=player_names
    )

    if verbose:
        print(f"\nScraped {len(cache)} players total")
        print(f"Cache saved to: {get_cache_path() / 'career_firsts.json'}")

        # Show witnessed firsts if any
        attended = get_attended_game_ids()
        witnessed = find_witnessed_firsts(cache, attended)

        if witnessed:
            print(f"\n{'='*60}")
            print(f"CAREER FIRSTS YOU WITNESSED: {len(witnessed)}")
            print(f"{'='*60}\n")
            for w in sorted(witnessed, key=lambda x: x['date'])[:10]:
                print(f"  • {w['milestone']} - {w['player_name']} ({w['date']})")
            if len(witnessed) > 10:
                print(f"  ... and {len(witnessed) - 10} more")


if __name__ == "__main__":
    main()
