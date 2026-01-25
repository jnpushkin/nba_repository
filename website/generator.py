"""
Website generator for interactive NBA stats HTML output with travel tracking.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Set
from pathlib import Path
import pandas as pd

from ..utils.log import info
from ..utils.constants import (
    EXCEL_COLORS, NBA_ARENAS, NBA_TEAMS, TEAM_CODES,
    NBA_DIVISIONS, NBA_CONFERENCES, DIVISION_TO_CONFERENCE,
    TEAM_CODE_TO_DIVISION, TEAM_CODE_ALIASES
)


def _get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / '.project_root').exists():
            return parent
        if (parent / 'nba_processor').is_dir() or (parent / '__main__.py').exists():
            return parent
    return Path.cwd()


def _load_career_firsts_cache() -> dict:
    """Load the career firsts cache from disk."""
    cache_file = _get_project_root() / 'cache' / 'career_firsts' / 'career_firsts.json'
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _find_witnessed_career_firsts(games_df: pd.DataFrame, career_firsts_cache: dict) -> List[Dict]:
    """
    Find career firsts and milestones that were witnessed at attended games.

    Args:
        games_df: DataFrame of player games with game_id column
        career_firsts_cache: Dict mapping player_id to their career firsts/milestones

    Returns:
        List of witnessed career firsts/milestones
    """
    witnessed = []

    if games_df.empty or not career_firsts_cache:
        return witnessed

    # Build set of attended game IDs
    attended_game_ids = set()
    if 'game_id' in games_df.columns:
        attended_game_ids = set(games_df['game_id'].dropna().unique())

    # Build player name lookup from games
    player_names = {}
    if 'player_id' in games_df.columns and 'name' in games_df.columns:
        for _, row in games_df.iterrows():
            if row.get('player_id') and row.get('name'):
                player_names[row['player_id']] = row['name']

    # Check each player's career firsts
    for player_id, data in career_firsts_cache.items():
        # Skip metadata keys like _processed_games
        if player_id.startswith('_'):
            continue
        if not isinstance(data, dict):
            continue
        player_name = data.get('player_name', player_names.get(player_id, player_id))

        # Check firsts (first points, first rebound, etc.)
        for stat, first_info in data.get('firsts', {}).items():
            game_id = first_info.get('game_id', '')
            if game_id in attended_game_ids:
                witnessed.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'milestone': first_info.get('milestone', ''),
                    'stat': stat,
                    'date': first_info.get('date', ''),
                    'game_id': game_id,
                    'opponent': first_info.get('opponent', ''),
                    'year': first_info.get('year', ''),
                    'category': 'first',
                })

        # Check milestones (1000th point, etc.)
        for stat, milestones_list in data.get('milestones', {}).items():
            for milestone_info in milestones_list:
                game_id = milestone_info.get('game_id', '')
                if game_id in attended_game_ids:
                    witnessed.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'milestone': milestone_info.get('milestone', ''),
                        'milestone_number': milestone_info.get('number', 0),
                        'stat': stat,
                        'date': milestone_info.get('date', ''),
                        'game_id': game_id,
                        'opponent': milestone_info.get('opponent', ''),
                        'year': milestone_info.get('year', ''),
                        'category': 'milestone',
                        'career_total_after': milestone_info.get('career_total_after', 0),
                    })

    # Sort by date (most recent first), then by milestone importance
    def sort_key(x):
        date = x.get('date', '')
        milestone_num = x.get('milestone_number', 0)
        return (date, milestone_num)

    witnessed.sort(key=sort_key, reverse=True)
    return witnessed

# Path to static assets
STATIC_DIR = Path(__file__).parent / 'static'


def _load_static_file(filename: str) -> str:
    """Load content from a static file."""
    filepath = STATIC_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding='utf-8')
    return ''


def _get_css() -> str:
    """Load CSS from external file."""
    return _load_static_file('styles.css')


def _get_javascript() -> str:
    """Load JavaScript from external file, prepending dynamic constants."""
    js_content = _load_static_file('app.js')
    # The app.js already includes everything, just return it
    return js_content


def _generate_js_constants() -> str:
    """Generate JavaScript constants from Python constants."""
    # Team codes mapping (full name -> code)
    team_codes_js = {name: info['code'] for name, info in NBA_TEAMS.items()}

    # Team short names (full name -> mascot)
    team_short_names = {}
    for name in NBA_TEAMS.keys():
        # Extract mascot (last word(s) after city)
        parts = name.split()
        # Handle special cases
        if 'Trail Blazers' in name:
            team_short_names[name] = 'Trail Blazers'
        elif '76ers' in name:
            team_short_names[name] = '76ers'
        else:
            team_short_names[name] = parts[-1]

    # Milestone categories for filtering
    milestone_categories = {
        'multi': ['quadruple_doubles', 'triple_doubles', 'double_doubles', 'near_triple_doubles',
                  'near_double_doubles', 'five_by_fives', 'all_around_games'],
        'scoring': ['seventy_point_games', 'sixty_point_games', 'fifty_point_games',
                    'forty_five_point_games', 'forty_point_games', 'thirty_five_point_games',
                    'thirty_point_games', 'twenty_five_point_games', 'twenty_point_games'],
        'rebounding': ['twenty_five_rebound_games', 'twenty_rebound_games', 'eighteen_rebound_games',
                       'fifteen_rebound_games', 'twelve_rebound_games', 'ten_rebound_games'],
        'assists': ['twenty_assist_games', 'fifteen_assist_games', 'twelve_assist_games', 'ten_assist_games'],
        'steals': ['ten_steal_games', 'seven_steal_games', 'five_steal_games', 'four_steal_games'],
        'blocks': ['ten_block_games', 'seven_block_games', 'five_block_games', 'four_block_games'],
        'threes': ['ten_three_games', 'eight_three_games', 'seven_three_games',
                   'six_three_games', 'five_three_games', 'perfect_from_three'],
        'efficiency': ['hot_shooting_games', 'perfect_ft_games', 'perfect_fg_games',
                       'efficient_scoring_games', 'high_game_score'],
        'combined': ['thirty_ten_games', 'twenty_five_ten_games', 'twenty_ten_games',
                     'twenty_ten_five_games', 'twenty_twenty_games', 'points_assists_double_double'],
        'defensive': ['defensive_monster_games', 'zero_turnover_games'],
        'plusminus': ['plus_25_games', 'plus_20_games', 'minus_25_games']
    }

    import json
    return f'''
// Auto-generated constants from Python
const TEAM_SHORT_NAMES = {json.dumps(team_short_names)};
const TEAM_CODES = {json.dumps(team_codes_js)};
const MILESTONE_CATEGORIES = {json.dumps(milestone_categories)};

function getShortName(fullName) {{
    return TEAM_SHORT_NAMES[fullName] || fullName;
}}

function getTeamCode(fullName) {{
    if (fullName && fullName.includes(', ')) {{
        return fullName.split(', ').map(t => TEAM_CODES[t.trim()] || t.trim().slice(0,3).toUpperCase()).join(', ');
    }}
    return TEAM_CODES[fullName] || fullName;
}}
'''


def generate_website_from_data(processed_data: Dict[str, pd.DataFrame], output_path: str) -> None:
    """
    Generate interactive HTML website from processed data.
    """
    info(f"Generating website: {output_path}")

    # Serialize DataFrames to JSON
    data = {}
    for key, df in processed_data.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            if key == 'player_games' and 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            data[key] = df.to_dict(orient='records')

    # Include milestones and descriptions (already dicts, not DataFrames)
    if 'milestones' in processed_data and isinstance(processed_data['milestones'], dict):
        data['milestones'] = processed_data['milestones']
    if 'milestone_descriptions' in processed_data and isinstance(processed_data['milestone_descriptions'], dict):
        data['milestone_descriptions'] = processed_data['milestone_descriptions']

    # Build games summary (one row per game, not per player)
    games_df = processed_data.get('player_games', pd.DataFrame())
    data['games'] = _build_games_summary(games_df)

    # Calculate venue/travel stats
    venue_stats = _calculate_venue_stats(games_df)
    data['venues'] = venue_stats['venues']

    # Calculate team checklist (teams/divisions/conferences seen)
    team_checklist = _calculate_team_checklist(games_df)
    data['teamChecklist'] = team_checklist

    # Load career firsts and find witnessed ones
    career_firsts_cache = _load_career_firsts_cache()
    witnessed_firsts = _find_witnessed_career_firsts(games_df, career_firsts_cache)
    data['careerFirsts'] = witnessed_firsts
    if witnessed_firsts:
        info(f"  Found {len(witnessed_firsts)} witnessed career firsts/milestones")

    # Calculate summary stats
    players_df = processed_data.get('players', pd.DataFrame())

    # Count milestones from the milestones dict
    milestones = data.get('milestones', {})
    total_milestones = sum(len(v) for v in milestones.values() if isinstance(v, list))

    summary = {
        'totalPlayers': len(players_df) if not players_df.empty else 0,
        'totalGames': len(data['games']),
        'totalPoints': int(players_df['Total PTS'].sum()) if not players_df.empty and 'Total PTS' in players_df.columns else 0,
        'tripleDoubles': len(milestones.get('triple_doubles', [])),
        'doubleDoubles': len(milestones.get('double_doubles', [])),
        'totalMilestones': total_milestones,
        'arenasVisited': venue_stats['arenas_visited'],
        'totalArenas': 30,
        'statesVisited': venue_stats['states_visited'],
        'citiesVisited': venue_stats['cities_visited'],
        'teamsSeen': team_checklist['summary']['teamsSeen'],
        'totalTeams': 30,
        'careerFirsts': len(witnessed_firsts),
    }
    data['summary'] = summary

    json_data = json.dumps(data, default=str)

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    html = _generate_html(json_data, summary)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    info(f"Website saved: {output_path}")


def _build_games_summary(games_df: pd.DataFrame, all_games: List[Dict] = None) -> List[Dict]:
    """Build one row per game with aggregated info."""
    if games_df.empty:
        return []

    games = []
    if 'game_id' not in games_df.columns:
        return []

    # Build a lookup from game_id to original game data for accurate home/away info
    game_lookup = {}
    if all_games:
        for g in all_games:
            gid = g.get('game_id', '')
            if gid:
                game_lookup[gid] = g

    for game_id, group in games_df.groupby('game_id'):
        first = group.iloc[0]

        # Try to get accurate home/away from original game data
        original = game_lookup.get(game_id, {})
        basic_info = original.get('basic_info', {})

        if basic_info:
            away_team = basic_info.get('away_team', '')
            home_team = basic_info.get('home_team', '')
            away_score = basic_info.get('away_score', 0)
            home_score = basic_info.get('home_score', 0)
        else:
            # Fallback to player data - determine home team from game_id
            # game_id format: YYYYMMDD0XXX where XXX is home team code
            home_code = game_id[9:12] if len(game_id) >= 12 else ''

            # Get unique teams from this game's players
            teams_in_game = group['team'].unique().tolist()

            # Try to match home team by code
            home_team = ''
            away_team = ''
            for t in teams_in_game:
                t_code = _get_team_code_from_name(t)
                if t_code and t_code.upper() == home_code.upper():
                    home_team = t
                else:
                    away_team = t

            # If we couldn't determine, just use what we have
            if not home_team and teams_in_game:
                home_team = teams_in_game[0]
            if not away_team and len(teams_in_game) > 1:
                away_team = teams_in_game[1]

            # Get scores from player data
            home_players = group[group['team'] == home_team] if home_team else group
            away_players = group[group['team'] == away_team] if away_team else group

            # Parse score from first player of each team
            home_score = 0
            away_score = 0
            if not home_players.empty:
                score_str = home_players.iloc[0].get('score', '')
                if score_str and '-' in str(score_str):
                    parts = str(score_str).split('-')
                    home_score = int(parts[0]) if home_players.iloc[0].get('team') == home_team else int(parts[1])
                    away_score = int(parts[1]) if home_players.iloc[0].get('team') == home_team else int(parts[0])

        games.append({
            'game_id': game_id,
            'date': first.get('date', ''),
            'date_yyyymmdd': first.get('date_yyyymmdd', ''),
            'away_team': away_team,
            'home_team': home_team,
            'away_score': away_score,
            'home_score': home_score,
            'game_type': first.get('game_type', 'regular'),
            'players': len(group),
        })

    # Sort by date descending (use date_yyyymmdd for proper sorting)
    games.sort(key=lambda x: x.get('date_yyyymmdd', ''), reverse=True)
    return games


def _normalize_team_code(code: str) -> str:
    """Normalize team code using aliases."""
    if not code:
        return ''
    code = code.upper().strip()
    return TEAM_CODE_ALIASES.get(code, code)


def _get_team_code_from_name(name: str) -> str:
    """Get team code from team name."""
    if not name:
        return ''
    for team_name, info in NBA_TEAMS.items():
        if name == team_name or team_name in name or name in team_name:
            return info['code']
    return ''


def _calculate_team_checklist(games_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate team/division/conference progress checklist."""
    if games_df.empty:
        return {
            'teams': [],
            'divisions': {},
            'conferences': {},
            'summary': {'teamsSeen': 0, 'totalTeams': 30}
        }

    # Get unique games
    if 'game_id' in games_df.columns:
        unique_games = games_df.drop_duplicates(subset=['game_id'])
    else:
        unique_games = games_df

    # Track teams seen and visit counts
    teams_seen: Set[str] = set()
    team_visit_counts: Dict[str, int] = {}

    for _, game in unique_games.iterrows():
        game_id = str(game.get('game_id', ''))
        team = str(game.get('team', ''))
        opponent = str(game.get('opponent', ''))

        # Extract home team code from game_id (format: YYYYMMDD0XXX)
        home_code = None
        if len(game_id) >= 12 and game_id[8] == '0':
            home_code = _normalize_team_code(game_id[9:12])

        # Get team codes from names
        team_code = _get_team_code_from_name(team)
        opp_code = _get_team_code_from_name(opponent)

        # Add home team from game_id
        if home_code and home_code in TEAM_CODES:
            teams_seen.add(home_code)
            team_visit_counts[home_code] = team_visit_counts.get(home_code, 0) + 1

        # Add team (might be same as home, might be away)
        if team_code and team_code in TEAM_CODES:
            teams_seen.add(team_code)
            if team_code != home_code:  # Avoid double counting
                team_visit_counts[team_code] = team_visit_counts.get(team_code, 0) + 1

        # Add opponent
        if opp_code and opp_code in TEAM_CODES:
            teams_seen.add(opp_code)
            if opp_code != home_code and opp_code != team_code:
                team_visit_counts[opp_code] = team_visit_counts.get(opp_code, 0) + 1

    # Build team data for each team
    teams_data = []
    for team_name, info in NBA_TEAMS.items():
        code = info['code']
        division = info['division']
        conference = info['conference']

        teams_data.append({
            'code': code,
            'name': team_name,
            'division': division,
            'conference': conference,
            'seen': code in teams_seen,
            'visitCount': team_visit_counts.get(code, 0),
        })

    # Build division summaries
    divisions = {}
    for div_name, team_codes in NBA_DIVISIONS.items():
        div_teams = [t for t in teams_data if t['code'] in team_codes]
        teams_seen_count = sum(1 for t in div_teams if t['seen'])
        divisions[div_name] = {
            'name': div_name,
            'conference': DIVISION_TO_CONFERENCE[div_name],
            'teams': div_teams,
            'teamsSeen': teams_seen_count,
            'totalTeams': len(team_codes),
            'complete': teams_seen_count == len(team_codes),
        }

    # Build conference summaries
    conferences = {}
    for conf_name, div_names in NBA_CONFERENCES.items():
        conf_teams = [t for t in teams_data if t['conference'] == conf_name]
        teams_seen_count = sum(1 for t in conf_teams if t['seen'])
        conferences[conf_name] = {
            'name': conf_name,
            'divisions': div_names,
            'teamsSeen': teams_seen_count,
            'totalTeams': 15,
            'complete': teams_seen_count == 15,
        }

    return {
        'teams': teams_data,
        'divisions': divisions,
        'conferences': conferences,
        'summary': {
            'teamsSeen': len(teams_seen),
            'totalTeams': 30,
        }
    }


def _calculate_venue_stats(games_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate venue and travel statistics from games."""
    if games_df.empty:
        return {'venues': [], 'arenas_visited': 0, 'states_visited': 0, 'cities_visited': 0}

    if 'game_id' in games_df.columns:
        unique_games = games_df.drop_duplicates(subset=['game_id'])
    else:
        unique_games = games_df

    visited_codes: Set[str] = set()
    visited_cities: Set[str] = set()
    visited_states: Set[str] = set()
    venue_games: Dict[str, List] = {}

    for _, game in unique_games.iterrows():
        game_id = str(game.get('game_id', ''))
        date_str = str(game.get('date', ''))

        home_code = None
        if len(game_id) >= 12 and game_id[8] == '0':
            home_code = game_id[9:12].upper()

        if not home_code:
            continue

        actual_arena_code = home_code
        year = None
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str.split(',')[-1].strip()) if ',' in date_str else int(date_str[:4])
            except:
                pass

        if home_code == 'LAC' and year and year < 2024:
            actual_arena_code = 'LAL'

        if actual_arena_code in NBA_ARENAS:
            arena = NBA_ARENAS[actual_arena_code]
            visited_codes.add(actual_arena_code)
            visited_cities.add(arena['city'])
            visited_states.add(arena['state'])

            if actual_arena_code not in venue_games:
                venue_games[actual_arena_code] = []
            venue_games[actual_arena_code].append({'date': date_str, 'game_id': game_id})

    venues = []
    for code, arena in NBA_ARENAS.items():
        games = venue_games.get(code, [])
        venues.append({
            'code': code,
            'name': arena['name'],
            'team': arena['team'],
            'city': arena['city'],
            'state': arena['state'],
            'lat': arena['lat'],
            'lng': arena['lng'],
            'visited': code in visited_codes,
            'games': len(games),
            'first_visit': min(g['date'] for g in games) if games else None,
            'last_visit': max(g['date'] for g in games) if games else None,
        })

    return {
        'venues': venues,
        'arenas_visited': len(visited_codes),
        'states_visited': len(visited_states),
        'cities_visited': len(visited_cities),
    }


def _generate_html(json_data: str, summary: Dict[str, Any]) -> str:
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Stats Tracker</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
{_get_css()}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-controls">
            <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">&#127769;</button>
        </div>
        <h1>NBA Stats Tracker</h1>
        <p class="header-subtitle">Game-by-game statistics & arena tracking</p>
        <div class="dashboard-grid">
            <div class="progress-ring-container">
                <svg class="progress-ring" viewBox="0 0 100 100">
                    <circle class="progress-ring-bg" cx="50" cy="50" r="42"/>
                    <circle class="progress-ring-fill" cx="50" cy="50" r="42"
                        style="--progress: {(summary.get('teamsSeen', 0) / 30) * 100}"/>
                </svg>
                <div class="progress-ring-text">
                    <div class="progress-ring-value">{summary.get('teamsSeen', 0)}<span class="progress-ring-total">/30</span></div>
                    <div class="progress-ring-label">Teams</div>
                </div>
            </div>
            <div class="progress-ring-container">
                <svg class="progress-ring" viewBox="0 0 100 100">
                    <circle class="progress-ring-bg" cx="50" cy="50" r="42"/>
                    <circle class="progress-ring-fill arenas" cx="50" cy="50" r="42"
                        style="--progress: {(summary.get('arenasVisited', 0) / 30) * 100}"/>
                </svg>
                <div class="progress-ring-text">
                    <div class="progress-ring-value">{summary.get('arenasVisited', 0)}<span class="progress-ring-total">/30</span></div>
                    <div class="progress-ring-label">Arenas</div>
                </div>
            </div>
            <div class="progress-ring-container">
                <svg class="progress-ring" viewBox="0 0 100 100">
                    <circle class="progress-ring-bg" cx="50" cy="50" r="42"/>
                    <circle class="progress-ring-fill milestones" cx="50" cy="50" r="42"
                        style="--progress: {min((summary.get('totalMilestones', 0) / 100) * 100, 100)}"/>
                </svg>
                <div class="progress-ring-text">
                    <div class="progress-ring-value">{summary.get('totalMilestones', 0)}</div>
                    <div class="progress-ring-label">Milestones</div>
                </div>
            </div>
            <div class="stats-column">
                <div class="mini-stat">
                    <span class="mini-stat-value">{summary.get('totalGames', 0)}</span>
                    <span class="mini-stat-label">Games</span>
                </div>
                <div class="mini-stat">
                    <span class="mini-stat-value">{summary.get('totalPlayers', 0)}</span>
                    <span class="mini-stat-label">Players</span>
                </div>
                <div class="mini-stat">
                    <span class="mini-stat-value">{summary.get('statesVisited', 0)}</span>
                    <span class="mini-stat-label">States</span>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <nav class="tabs">
            <button class="tab active" onclick="showSection('games')" data-section="games">Games</button>
            <button class="tab" onclick="showSection('leaders')" data-section="leaders">Leaders</button>
            <button class="tab" onclick="showSection('players')" data-section="players">Players</button>
            <button class="tab" onclick="showSection('teams')" data-section="teams">Teams</button>
            <button class="tab" onclick="showSection('venues')" data-section="venues">Arenas</button>
            <button class="tab" onclick="showSection('map')" data-section="map">Map</button>
            <button class="tab" onclick="showSection('achievements')" data-section="achievements">Achievements</button>
            <button class="tab" onclick="showSection('career-firsts')" data-section="career-firsts">Career Firsts</button>
        </nav>

        <!-- Games Section -->
        <div id="games" class="section active">
            <h2>Games Attended</h2>
            <div class="games-grid" id="games-grid"></div>
        </div>

        <!-- Leaders Section -->
        <div id="leaders" class="section">
            <h2>Stat Leaders</h2>
            <div class="leaders-grid" id="leaders-grid"></div>
        </div>

        <!-- Players Section -->
        <div id="players" class="section">
            <h2>Player Statistics
                <div class="section-actions">
                    <button class="btn btn-secondary" onclick="downloadCSV('players')">Download CSV</button>
                </div>
            </h2>
            <div class="filters">
                <div class="filter-group">
                    <label>Search</label>
                    <input type="text" id="players-search" placeholder="Search..." onkeyup="filterPlayersTable()">
                </div>
                <div class="filter-group">
                    <label>Team</label>
                    <select id="players-team" onchange="filterPlayersTable()"><option value="">All Teams</option></select>
                </div>
                <div class="filter-group">
                    <label>Min Games</label>
                    <input type="number" id="players-min-games" min="1" placeholder="1" onchange="filterPlayersTable()">
                </div>
                <button class="clear-filters" onclick="clearPlayersFilters()">Clear</button>
            </div>
            <div class="table-container">
                <table id="players-table"><thead></thead><tbody></tbody></table>
            </div>
        </div>

        <!-- Teams Section -->
        <div id="teams" class="section">
            <h2>Team Checklist</h2>
            <div class="team-progress">
                <div class="progress-bar"><div class="progress-fill" id="team-progress-fill"></div></div>
                <div class="progress-text" id="team-progress-text">0/30 Teams Seen</div>
            </div>
            <div class="checklist-tabs">
                <button class="checklist-tab active" onclick="showChecklistView('all')" data-view="all">All Teams</button>
                <button class="checklist-tab" onclick="showChecklistView('east')" data-view="east">Eastern</button>
                <button class="checklist-tab" onclick="showChecklistView('west')" data-view="west">Western</button>
                <button class="checklist-tab" onclick="showChecklistView('divisions')" data-view="divisions">By Division</button>
            </div>
            <div id="team-checklist-container" class="team-checklist-container"></div>
        </div>

        <!-- Venues Section -->
        <div id="venues" class="section">
            <h2>Arena Checklist</h2>
            <div class="arena-progress">
                <div class="progress-bar"><div class="progress-fill" id="arena-progress-fill"></div></div>
                <div class="progress-text" id="arena-progress-text">0/30 Arenas Visited</div>
            </div>
            <div class="filters">
                <div class="filter-group">
                    <label>Show</label>
                    <select id="venues-filter" onchange="filterVenuesTable()">
                        <option value="all">All Arenas</option>
                        <option value="visited">Visited Only</option>
                        <option value="unvisited">Not Visited</option>
                    </select>
                </div>
            </div>
            <div class="table-container">
                <table id="venues-table">
                    <thead><tr><th>Team</th><th>Arena</th><th>City</th><th>State</th><th>Games</th><th>First Visit</th><th>Status</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <!-- Map Section -->
        <div id="map" class="section">
            <h2>Arena Map</h2>
            <div class="map-legend">
                <span class="legend-item"><span class="legend-dot visited"></span> Visited</span>
                <span class="legend-item"><span class="legend-dot not-visited"></span> Not Visited</span>
            </div>
            <div id="arena-map"></div>
        </div>

        <!-- Achievements Section -->
        <div id="achievements" class="section">
            <h2>Milestones & Achievements ({summary.get('totalMilestones', 0)} total)</h2>
            <div class="milestone-filters">
                <div class="filter-group">
                    <label>Category</label>
                    <select id="milestone-category" onchange="filterMilestones()">
                        <option value="all">All Categories</option>
                        <option value="multi">Multi-Category</option>
                        <option value="scoring">Scoring</option>
                        <option value="rebounding">Rebounding</option>
                        <option value="assists">Assists</option>
                        <option value="steals">Steals</option>
                        <option value="blocks">Blocks</option>
                        <option value="threes">Three-Pointers</option>
                        <option value="efficiency">Efficiency</option>
                        <option value="combined">Combined</option>
                        <option value="defensive">Defensive</option>
                        <option value="plusminus">Plus/Minus</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Search Player</label>
                    <input type="text" id="milestone-search" placeholder="Search..." onkeyup="filterMilestones()">
                </div>
            </div>
            <div id="milestones-container" class="milestones-container"></div>
        </div>

        <!-- Career Firsts Section -->
        <div id="career-firsts" class="section">
            <h2>Career Firsts & Milestones ({summary.get('careerFirsts', 0)} witnessed)</h2>
            <p class="section-description">Career milestones you witnessed players achieve - first career points, 1000th career rebound, etc.</p>
            <div class="milestone-filters">
                <div class="filter-group">
                    <label>Category</label>
                    <select id="career-firsts-category" onchange="filterCareerFirsts()">
                        <option value="all">All</option>
                        <option value="first">Career Firsts</option>
                        <option value="milestone">Career Milestones</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Search Player</label>
                    <input type="text" id="career-firsts-search" placeholder="Search..." onkeyup="filterCareerFirsts()">
                </div>
            </div>
            <div id="career-firsts-container" class="milestones-container"></div>
        </div>
    </div>

    <!-- Box Score Modal -->
    <div class="modal" id="boxscore-modal" onclick="if(event.target === this) closeModal('boxscore-modal')">
        <div class="modal-content modal-large">
            <button class="modal-close" onclick="closeModal('boxscore-modal')">&times;</button>
            <div id="boxscore-detail"></div>
        </div>
    </div>

    <!-- Player Modal -->
    <div class="modal" id="player-modal" onclick="if(event.target === this) closeModal('player-modal')">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal('player-modal')">&times;</button>
            <div id="player-detail"></div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <footer><p>Generated: {generated_time}</p></footer>

    <script>
const DATA = {json_data};
{_get_javascript()}
    </script>
</body>
</html>'''


