"""
Main HTML parser for Basketball Reference NBA box scores.
"""

import re
import codecs
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup, Comment

from .stats_parser import (
    extract_player_stats,
    extract_team_totals,
    merge_basic_and_advanced_stats,
    find_box_score_tables,
)
from ..utils.helpers import safe_int, safe_float, get_team_code
from ..utils.constants import TEAM_CODES, TEAM_ALIASES, get_season_string


class HTMLParsingError(Exception):
    """Raised when HTML parsing fails due to invalid or incomplete data."""
    pass


def fix_encoding(text: str) -> str:
    """
    Fix double-encoded UTF-8 text.

    Sometimes UTF-8 content gets treated as Latin-1 and re-encoded,
    resulting in characters like "Å" instead of proper Unicode.
    """
    try:
        # Try to fix double-encoded UTF-8
        # First encode as latin-1 (which preserves the bytes), then decode as UTF-8
        fixed = text.encode('latin-1').decode('utf-8')
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def validate_html_content(html_content: str) -> None:
    """
    Validate that HTML content is suitable for parsing.

    Args:
        html_content: Raw HTML string

    Raises:
        HTMLParsingError: If content is invalid
    """
    if not html_content:
        raise HTMLParsingError("Empty HTML content provided")

    if not isinstance(html_content, str):
        raise HTMLParsingError(f"Expected string, got {type(html_content).__name__}")

    if len(html_content) < 1000:
        raise HTMLParsingError("HTML content too short to be a valid box score")

    if 'basketball-reference' not in html_content.lower() and 'scorebox' not in html_content.lower():
        raise HTMLParsingError("HTML does not appear to be a Basketball Reference box score")


def validate_game_data(game_data: Dict[str, Any]) -> List[str]:
    """
    Validate parsed game data and return list of warnings.

    Args:
        game_data: Parsed game dictionary

    Returns:
        List of warning messages (empty if all valid)
    """
    warnings = []
    basic_info = game_data.get('basic_info', {})

    if not basic_info.get('away_team'):
        warnings.append("Missing away team name")
    if not basic_info.get('home_team'):
        warnings.append("Missing home team name")
    if not basic_info.get('date'):
        warnings.append("Missing game date")

    away_score = basic_info.get('away_score', 0)
    home_score = basic_info.get('home_score', 0)
    if away_score == 0 and home_score == 0:
        warnings.append("Both team scores are 0 - possible parsing error")

    box_score = game_data.get('box_score', {})
    away_players = box_score.get('away', {}).get('players', [])
    home_players = box_score.get('home', {}).get('players', [])

    if not away_players:
        warnings.append("No away team player stats found")
    if not home_players:
        warnings.append("No home team player stats found")

    return warnings


def format_date_yyyymmdd(date_str: str) -> str:
    """Convert date string to YYYYMMDD format."""
    import re
    from datetime import datetime

    if not date_str:
        return ''

    # Try common formats
    formats = [
        '%B %d, %Y',      # January 19, 2026
        '%b %d, %Y',      # Jan 19, 2026
        '%m/%d/%Y',       # 01/19/2026
        '%Y-%m-%d',       # 2026-01-19
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y%m%d')
        except ValueError:
            continue

    return ''


def generate_game_id(date_str: str, home_team: str) -> str:
    """Generate a unique game ID."""
    date_yyyymmdd = format_date_yyyymmdd(date_str)
    team_code = get_team_code(home_team)
    return f"{date_yyyymmdd}0{team_code}"


def parse_basketball_reference_boxscore(html_content: str) -> Dict[str, Any]:
    """
    Parse a Basketball Reference NBA box score HTML file.

    Args:
        html_content: Raw HTML string

    Returns:
        game_data dictionary with all extracted information

    Raises:
        HTMLParsingError: If HTML content is invalid
    """
    validate_html_content(html_content)

    soup = BeautifulSoup(html_content, 'html.parser')

    game_data = {
        'basic_info': {},
        'linescore': {},
        'box_score': {
            'away': {'basic': [], 'advanced': []},
            'home': {'basic': [], 'advanced': []},
        },
        'team_totals': {
            'away': {},
            'home': {},
        },
        'officials': [],
    }

    # Extract basic game info
    game_data['basic_info'] = extract_basic_info(soup)

    # Extract linescore (NBA uses 4 quarters)
    game_data['linescore'] = extract_linescore(soup)

    # Fallback: If team names are empty, try to extract from title
    if not game_data['basic_info'].get('away_team') or not game_data['basic_info'].get('home_team'):
        away_name, home_name = get_team_names_from_title(soup)
        if away_name and not game_data['basic_info'].get('away_team'):
            game_data['basic_info']['away_team'] = away_name
            game_data['basic_info']['away_team_code'] = get_team_code(away_name)
        if home_name and not game_data['basic_info'].get('home_team'):
            game_data['basic_info']['home_team'] = home_name
            game_data['basic_info']['home_team_code'] = get_team_code(home_name)

    # Fallback: If scores are 0, try to get from linescore totals
    if game_data['basic_info'].get('away_score', 0) == 0:
        linescore_away_total = game_data['linescore'].get('away', {}).get('total', 0)
        if linescore_away_total > 0:
            game_data['basic_info']['away_score'] = linescore_away_total
    if game_data['basic_info'].get('home_score', 0) == 0:
        linescore_home_total = game_data['linescore'].get('home', {}).get('total', 0)
        if linescore_home_total > 0:
            game_data['basic_info']['home_score'] = linescore_home_total

    # Generate game ID
    game_data['game_id'] = generate_game_id(
        game_data['basic_info'].get('date', ''),
        game_data['basic_info'].get('home_team', '')
    )

    # Determine season
    date_yyyymmdd = game_data['basic_info'].get('date_yyyymmdd', '')
    if date_yyyymmdd and len(date_yyyymmdd) == 8:
        year = int(date_yyyymmdd[:4])
        month = int(date_yyyymmdd[4:6])
        game_data['basic_info']['season'] = get_season_string(year, month)

    # Find team slugs from box score tables
    team_slugs = find_box_score_tables(soup)

    if len(team_slugs) >= 2:
        away_slug = team_slugs[0]
        home_slug = team_slugs[1]

        # Extract player stats
        game_data['box_score']['away']['basic'] = extract_player_stats(soup, away_slug, is_basic=True)
        game_data['box_score']['away']['advanced'] = extract_player_stats(soup, away_slug, is_basic=False)
        game_data['box_score']['home']['basic'] = extract_player_stats(soup, home_slug, is_basic=True)
        game_data['box_score']['home']['advanced'] = extract_player_stats(soup, home_slug, is_basic=False)

        # Merge basic and advanced stats
        game_data['box_score']['away']['players'] = merge_basic_and_advanced_stats(
            game_data['box_score']['away']['basic'],
            game_data['box_score']['away']['advanced']
        )
        game_data['box_score']['home']['players'] = merge_basic_and_advanced_stats(
            game_data['box_score']['home']['basic'],
            game_data['box_score']['home']['advanced']
        )

        # Extract team totals
        game_data['team_totals']['away'] = extract_team_totals(soup, away_slug, is_basic=True)
        game_data['team_totals']['home'] = extract_team_totals(soup, home_slug, is_basic=True)

        # Store team slugs
        game_data['basic_info']['away_team_slug'] = away_slug
        game_data['basic_info']['home_team_slug'] = home_slug

    # Extract officials
    game_data['officials'] = extract_officials(soup)

    # Validate and store warnings
    warnings = validate_game_data(game_data)
    if warnings:
        game_data['_parsing_warnings'] = warnings

    return game_data


def extract_basic_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract basic game information from the scorebox.

    Returns:
        Dictionary with game metadata
    """
    info = {
        'away_team': '',
        'home_team': '',
        'away_score': 0,
        'home_score': 0,
        'date': '',
        'date_yyyymmdd': '',
        'venue': '',
        'attendance': None,
        'away_record': '',
        'home_record': '',
        'game_type': 'regular',
        'bball_ref_url': '',
    }

    # Extract canonical URL
    canonical_link = soup.find('link', rel='canonical')
    if canonical_link and canonical_link.get('href'):
        info['bball_ref_url'] = canonical_link['href']

    # Find scorebox
    scorebox = soup.find('div', class_='scorebox')
    if not scorebox:
        return info

    # Extract team info
    team_divs = scorebox.find_all('div', recursive=False)

    teams_found = []
    for div in team_divs:
        # Look for team name - NBA uses /teams/ path
        team_link = div.find('a', href=re.compile(r'/teams/'))
        if team_link:
            team_name = team_link.get_text(strip=True)

            # Get score
            score_div = div.find('div', class_='score')
            score = 0
            if score_div:
                score = safe_int(score_div.get_text(strip=True), 0)

            # Get record
            record = ''
            record_match = re.search(r'\((\d+-\d+)\)', div.get_text())
            if record_match:
                record = record_match.group(1)

            teams_found.append({
                'name': team_name,
                'score': score,
                'record': record,
            })

    # First team is away, second is home
    if len(teams_found) >= 2:
        info['away_team'] = teams_found[0]['name']
        info['away_score'] = teams_found[0]['score']
        info['away_record'] = teams_found[0]['record']
        info['away_team_code'] = get_team_code(teams_found[0]['name'])

        info['home_team'] = teams_found[1]['name']
        info['home_score'] = teams_found[1]['score']
        info['home_record'] = teams_found[1]['record']
        info['home_team_code'] = get_team_code(teams_found[1]['name'])

    # Extract date, venue, attendance from scorebox_meta
    meta_div = scorebox.find('div', class_='scorebox_meta')
    if meta_div:
        meta_text = meta_div.get_text(separator='\n')
        lines = [line.strip() for line in meta_text.split('\n') if line.strip()]

        for i, line in enumerate(lines):
            # First line is usually the date
            if i == 0 and re.match(r'^[A-Za-z]+ \d+, \d{4}', line):
                info['date'] = line
                info['date_yyyymmdd'] = format_date_yyyymmdd(line)

            # Look for venue
            if 'Arena' in line or 'Center' in line or 'Garden' in line or 'Stadium' in line or 'Forum' in line:
                info['venue'] = line

            # Look for attendance
            attendance_match = re.search(r'Attendance:?\s*([\d,]+)', line)
            if attendance_match:
                info['attendance'] = safe_int(attendance_match.group(1).replace(',', ''), None)

    # Detect game type from URL or page content
    page_text = soup.get_text().lower()
    if 'playoff' in page_text or 'postseason' in page_text:
        info['game_type'] = 'playoff'
    elif 'play-in' in page_text:
        info['game_type'] = 'playin'
    elif 'preseason' in page_text:
        info['game_type'] = 'preseason'

    # Also try date from title
    if not info['date']:
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            date_match = re.search(r'(\w+ \d+, \d{4})', title_text)
            if date_match:
                info['date'] = date_match.group(1)
                info['date_yyyymmdd'] = format_date_yyyymmdd(info['date'])

    return info


def extract_linescore(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract quarter-by-quarter scoring (NBA uses 4 quarters).

    Returns:
        Dictionary with linescore data including quarters and OT
    """
    linescore = {
        'away': {'quarters': [], 'OT': [], 'total': 0},
        'home': {'quarters': [], 'OT': [], 'total': 0},
    }

    # Find linescore table
    linescore_table = soup.find('table', {'id': 'line_score'})

    if not linescore_table:
        # Check for commented out content
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if 'line_score' in comment or 'line-score' in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                linescore_table = comment_soup.find('table', {'id': re.compile(r'line.?score', re.IGNORECASE)})
                if linescore_table:
                    break

    if not linescore_table:
        return linescore

    rows = linescore_table.find_all('tr')
    team_index = 0

    for row in rows:
        cells = row.find_all(['th', 'td'])
        if len(cells) < 3:
            continue

        team_cell = cells[0]
        has_td_cells = any(cell.name == 'td' for cell in cells[1:])
        is_team_row = (team_cell.name == 'th' and has_td_cells and
                       (team_cell.find('a') or team_cell.get('data-stat') == 'team'))

        if is_team_row and team_index < 2:
            team_key = 'away' if team_index == 0 else 'home'
            team_index += 1

            period_scores = []
            for cell in cells[1:-1]:
                score = safe_int(cell.get_text(strip=True), 0)
                period_scores.append(score)

            total = safe_int(cells[-1].get_text(strip=True), 0)

            # NBA has 4 quarters, rest are OT
            if len(period_scores) >= 4:
                linescore[team_key]['quarters'] = period_scores[:4]
                if len(period_scores) > 4:
                    linescore[team_key]['OT'] = period_scores[4:]
            else:
                linescore[team_key]['quarters'] = period_scores

            linescore[team_key]['total'] = total

    return linescore


def extract_officials(soup: BeautifulSoup) -> List[str]:
    """
    Extract referee/officials information.

    Returns:
        List of official names
    """
    officials = []

    meta_div = soup.find('div', class_='scorebox_meta')
    if meta_div:
        meta_text = meta_div.get_text()
        officials_match = re.search(r'Officials?:?\s*(.+?)(?:\n|$)', meta_text, re.IGNORECASE)
        if officials_match:
            officials_text = officials_match.group(1)
            officials = [o.strip() for o in re.split(r',|and', officials_text) if o.strip()]

    return officials


def get_team_names_from_title(soup: BeautifulSoup) -> Tuple[str, str]:
    """
    Extract team names from page title as fallback.

    Returns:
        Tuple of (away_team, home_team)
    """
    title = soup.find('title')
    if not title:
        return ('', '')

    title_text = title.get_text()

    # Pattern: "Team1 vs. Team2 Box Score"
    match = re.search(r'(.+?)\s+(?:vs\.?|at)\s+(.+?)\s+Box Score', title_text, re.IGNORECASE)
    if match:
        return (match.group(1).strip(), match.group(2).strip())

    return ('', '')
