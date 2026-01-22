"""
Stats parser for extracting player and team statistics from NBA box score tables.
"""

import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup, Tag

from ..utils.helpers import safe_int, safe_float


def fix_encoding(text: str) -> str:
    """
    Fix double-encoded UTF-8 text.

    Sometimes UTF-8 content gets treated as Latin-1 and re-encoded,
    resulting in characters like "Å" instead of proper Unicode.
    """
    if not text:
        return text
    try:
        # Try to fix double-encoded UTF-8
        # First encode as latin-1 (which preserves the bytes), then decode as UTF-8
        fixed = text.encode('latin-1').decode('utf-8')
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def extract_player_id_from_href(href: str) -> str:
    """Extract player ID from Sports Reference player link."""
    if not href:
        return ''
    # Pattern: /players/x/xyzabc01.html
    match = re.search(r'/players/\w/([^/]+?)\.html', href)
    if match:
        return match.group(1)
    return ''


def extract_player_stats(soup: BeautifulSoup, team_slug: str, is_basic: bool = True) -> List[Dict[str, Any]]:
    """
    Extract player statistics from a box score table.

    Args:
        soup: BeautifulSoup object of the page
        team_slug: Team slug used in table ID (e.g., 'MIA', 'GSW')
        is_basic: True for basic stats, False for advanced stats

    Returns:
        List of player stat dictionaries
    """
    table_type = "basic" if is_basic else "advanced"
    table_id = f"box-{team_slug}-game-{table_type}"

    table = soup.find('table', {'id': table_id})
    if not table:
        # Try alternate ID formats
        table = soup.find('table', {'id': f'box_{team_slug}_basic'})
        if not table:
            table = soup.find('table', {'id': re.compile(f'box.*{team_slug}.*{table_type}', re.IGNORECASE)})

    if not table:
        return []

    players = []
    tbody = table.find('tbody')
    if not tbody:
        return []

    is_starter = True

    for row in tbody.find_all('tr'):
        # Check if this is a "Reserves" header row
        if 'thead' in row.get('class', []):
            is_starter = False
            continue

        # Skip rows without player data
        player_cell = row.find(['th', 'td'], {'data-stat': 'player'})
        if not player_cell:
            continue

        # Extract player info
        player_link = player_cell.find('a')
        if player_link:
            player_name = fix_encoding(player_link.get_text(strip=True))
            player_href = player_link.get('href', '')
            player_id = extract_player_id_from_href(player_href)
        else:
            player_name = fix_encoding(player_cell.get_text(strip=True))
            player_id = player_cell.get('data-append-csv', '')

        # Skip if no player name or it's a header
        if not player_name or player_name in ['Starters', 'Reserves', 'Team Totals']:
            continue

        # Get player ID from data-append-csv if not from link
        if not player_id:
            player_id = player_cell.get('data-append-csv', '')

        player_stats = {
            'name': player_name,
            'player_id': player_id,
            'starter': is_starter,
        }

        # Extract all stat cells
        for cell in row.find_all(['th', 'td']):
            stat_name = cell.get('data-stat')
            if stat_name and stat_name != 'player':
                cell_text = cell.get_text(strip=True)
                player_stats[stat_name] = _parse_stat_value(stat_name, cell_text)

        players.append(player_stats)

    return players


def extract_team_totals(soup: BeautifulSoup, team_slug: str, is_basic: bool = True) -> Dict[str, Any]:
    """
    Extract team totals from the footer of a box score table.

    Args:
        soup: BeautifulSoup object
        team_slug: Team slug
        is_basic: True for basic stats

    Returns:
        Dictionary of team total stats
    """
    table_type = "basic" if is_basic else "advanced"
    table_id = f"box-{team_slug}-game-{table_type}"

    table = soup.find('table', {'id': table_id})
    if not table:
        table = soup.find('table', {'id': f'box_{team_slug}_basic'})
        if not table:
            table = soup.find('table', {'id': re.compile(f'box.*{team_slug}.*{table_type}', re.IGNORECASE)})

    if not table:
        return {}

    tfoot = table.find('tfoot')
    if not tfoot:
        return {}

    totals_row = tfoot.find('tr')
    if not totals_row:
        return {}

    totals = {}
    for cell in totals_row.find_all(['th', 'td']):
        stat_name = cell.get('data-stat')
        if stat_name and stat_name != 'player':
            cell_text = cell.get_text(strip=True)
            totals[stat_name] = _parse_stat_value(stat_name, cell_text)

    return totals


def merge_basic_and_advanced_stats(
    basic_stats: List[Dict[str, Any]],
    advanced_stats: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge basic and advanced stats for players.

    Args:
        basic_stats: List of basic stat dictionaries
        advanced_stats: List of advanced stat dictionaries

    Returns:
        List of merged player dictionaries
    """
    advanced_lookup = {p['player_id']: p for p in advanced_stats if p.get('player_id')}

    merged = []
    for player in basic_stats:
        player_id = player.get('player_id')
        if player_id and player_id in advanced_lookup:
            adv = advanced_lookup[player_id]
            for key, value in adv.items():
                if key not in player or player[key] is None:
                    player[key] = value
        merged.append(player)

    return merged


def _parse_stat_value(stat_name: str, value: str) -> Any:
    """
    Parse a stat value to the appropriate type.

    Args:
        stat_name: Name of the stat
        value: String value from the cell

    Returns:
        Parsed value (int, float, or string)
    """
    if not value or value.strip() == '':
        return None

    value = value.strip()

    # Percentage stats
    pct_stats = ['fg_pct', 'fg2_pct', 'fg3_pct', 'ft_pct', 'ts_pct', 'efg_pct',
                 'fg3a_per_fga_pct', 'fta_per_fga_pct', 'orb_pct', 'drb_pct',
                 'trb_pct', 'ast_pct', 'stl_pct', 'blk_pct', 'tov_pct', 'usg_pct']

    # Integer stats
    int_stats = ['fg', 'fga', 'fg2', 'fg2a', 'fg3', 'fg3a', 'ft', 'fta',
                 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts',
                 'off_rtg', 'def_rtg', 'plus_minus']

    # Float stats
    float_stats = ['game_score', 'bpm']

    if stat_name in pct_stats:
        return safe_float(value, None)
    elif stat_name in int_stats:
        return safe_int(value, 0)
    elif stat_name in float_stats:
        return safe_float(value, None)
    elif stat_name == 'mp':
        # Minutes can be "MM:SS" format
        return value
    else:
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value


def extract_team_slug_from_table_id(table_id: str) -> Optional[str]:
    """
    Extract team slug from a table ID.

    Example: 'box-MIA-game-basic' -> 'MIA'

    Args:
        table_id: Full table ID

    Returns:
        Team slug or None
    """
    match = re.search(r'box-([A-Z]{3})-game-(?:basic|advanced)', table_id)
    if match:
        return match.group(1)
    return None


def find_box_score_tables(soup: BeautifulSoup) -> List[str]:
    """
    Find all box score table IDs in the page.

    Returns:
        List of team slugs found (e.g., ['MIA', 'GSW'])
    """
    # NBA Basketball Reference uses format: box-XXX-game-basic
    tables = soup.find_all('table', {'id': re.compile(r'^box-[A-Z]{3}-game-basic')})
    team_slugs = []

    for table in tables:
        table_id = table.get('id', '')
        slug = extract_team_slug_from_table_id(table_id)
        if slug:
            team_slugs.append(slug)

    return team_slugs
