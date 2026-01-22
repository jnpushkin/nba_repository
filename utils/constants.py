"""
NBA constants, team codes, and configuration.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


# === Directory and File Path Configuration ===
def _find_project_root() -> Path:
    """Find the project root directory."""
    env_base = os.environ.get("NBA_TRACKER_DIR")
    if env_base:
        path = Path(env_base).expanduser()
        if path.exists():
            return path

    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        marker = parent / ".project_root"
        if marker.exists():
            return parent

    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _find_project_root()
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_INPUT_DIR = BASE_DIR / "html_games"
DEFAULT_HTML_OUTPUT = BASE_DIR / "docs" / "index.html"

# === Deployment Configuration ===
SURGE_DOMAIN = "nba-processor.surge.sh"

# === NBA STAT COLUMNS ===
BASIC_STATS = [
    'mp',       # Minutes Played
    'fg',       # Field Goals Made
    'fga',      # Field Goal Attempts
    'fg_pct',   # Field Goal Percentage
    'fg3',      # 3-Point Field Goals Made
    'fg3a',     # 3-Point Field Goal Attempts
    'fg3_pct',  # 3-Point Field Goal Percentage
    'ft',       # Free Throws Made
    'fta',      # Free Throw Attempts
    'ft_pct',   # Free Throw Percentage
    'orb',      # Offensive Rebounds
    'drb',      # Defensive Rebounds
    'trb',      # Total Rebounds
    'ast',      # Assists
    'stl',      # Steals
    'blk',      # Blocks
    'tov',      # Turnovers
    'pf',       # Personal Fouls
    'pts',      # Points
    'plus_minus',  # Plus/Minus (NBA-specific)
]

ADVANCED_STATS = [
    'efg_pct',      # Effective Field Goal Percentage
    'ts_pct',       # True Shooting Percentage
    'usg_pct',      # Usage Percentage
    'ortg',         # Offensive Rating
    'drtg',         # Defensive Rating
    'bpm',          # Box Plus/Minus
    'vorp',         # Value Over Replacement Player
    'per',          # Player Efficiency Rating
    'ws',           # Win Shares
    'ws_48',        # Win Shares per 48 Minutes
]

ALL_STATS = BASIC_STATS + ADVANCED_STATS

# Date formats for parsing
DATE_FORMATS = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]

# === NBA TEAMS ===
# All 30 NBA teams with codes
NBA_TEAMS: Dict[str, Dict[str, str]] = {
    # Eastern Conference - Atlantic Division
    'Boston Celtics': {'code': 'BOS', 'conference': 'East', 'division': 'Atlantic'},
    'Brooklyn Nets': {'code': 'BKN', 'conference': 'East', 'division': 'Atlantic'},
    'New York Knicks': {'code': 'NYK', 'conference': 'East', 'division': 'Atlantic'},
    'Philadelphia 76ers': {'code': 'PHI', 'conference': 'East', 'division': 'Atlantic'},
    'Toronto Raptors': {'code': 'TOR', 'conference': 'East', 'division': 'Atlantic'},

    # Eastern Conference - Central Division
    'Chicago Bulls': {'code': 'CHI', 'conference': 'East', 'division': 'Central'},
    'Cleveland Cavaliers': {'code': 'CLE', 'conference': 'East', 'division': 'Central'},
    'Detroit Pistons': {'code': 'DET', 'conference': 'East', 'division': 'Central'},
    'Indiana Pacers': {'code': 'IND', 'conference': 'East', 'division': 'Central'},
    'Milwaukee Bucks': {'code': 'MIL', 'conference': 'East', 'division': 'Central'},

    # Eastern Conference - Southeast Division
    'Atlanta Hawks': {'code': 'ATL', 'conference': 'East', 'division': 'Southeast'},
    'Charlotte Hornets': {'code': 'CHA', 'conference': 'East', 'division': 'Southeast'},
    'Miami Heat': {'code': 'MIA', 'conference': 'East', 'division': 'Southeast'},
    'Orlando Magic': {'code': 'ORL', 'conference': 'East', 'division': 'Southeast'},
    'Washington Wizards': {'code': 'WAS', 'conference': 'East', 'division': 'Southeast'},

    # Western Conference - Northwest Division
    'Denver Nuggets': {'code': 'DEN', 'conference': 'West', 'division': 'Northwest'},
    'Minnesota Timberwolves': {'code': 'MIN', 'conference': 'West', 'division': 'Northwest'},
    'Oklahoma City Thunder': {'code': 'OKC', 'conference': 'West', 'division': 'Northwest'},
    'Portland Trail Blazers': {'code': 'POR', 'conference': 'West', 'division': 'Northwest'},
    'Utah Jazz': {'code': 'UTA', 'conference': 'West', 'division': 'Northwest'},

    # Western Conference - Pacific Division
    'Golden State Warriors': {'code': 'GSW', 'conference': 'West', 'division': 'Pacific'},
    'Los Angeles Clippers': {'code': 'LAC', 'conference': 'West', 'division': 'Pacific'},
    'Los Angeles Lakers': {'code': 'LAL', 'conference': 'West', 'division': 'Pacific'},
    'Phoenix Suns': {'code': 'PHX', 'conference': 'West', 'division': 'Pacific'},
    'Sacramento Kings': {'code': 'SAC', 'conference': 'West', 'division': 'Pacific'},

    # Western Conference - Southwest Division
    'Dallas Mavericks': {'code': 'DAL', 'conference': 'West', 'division': 'Southwest'},
    'Houston Rockets': {'code': 'HOU', 'conference': 'West', 'division': 'Southwest'},
    'Memphis Grizzlies': {'code': 'MEM', 'conference': 'West', 'division': 'Southwest'},
    'New Orleans Pelicans': {'code': 'NOP', 'conference': 'West', 'division': 'Southwest'},
    'San Antonio Spurs': {'code': 'SAS', 'conference': 'West', 'division': 'Southwest'},
}

# Team code to full name mapping
TEAM_CODES: Dict[str, str] = {info['code']: name for name, info in NBA_TEAMS.items()}

# Team aliases
TEAM_ALIASES: Dict[str, str] = {
    # Common abbreviations
    'Celtics': 'Boston Celtics',
    'Nets': 'Brooklyn Nets',
    'Knicks': 'New York Knicks',
    'Sixers': 'Philadelphia 76ers',
    '76ers': 'Philadelphia 76ers',
    'Raptors': 'Toronto Raptors',
    'Bulls': 'Chicago Bulls',
    'Cavs': 'Cleveland Cavaliers',
    'Cavaliers': 'Cleveland Cavaliers',
    'Pistons': 'Detroit Pistons',
    'Pacers': 'Indiana Pacers',
    'Bucks': 'Milwaukee Bucks',
    'Hawks': 'Atlanta Hawks',
    'Hornets': 'Charlotte Hornets',
    'Heat': 'Miami Heat',
    'Magic': 'Orlando Magic',
    'Wizards': 'Washington Wizards',
    'Nuggets': 'Denver Nuggets',
    'Timberwolves': 'Minnesota Timberwolves',
    'Wolves': 'Minnesota Timberwolves',
    'Thunder': 'Oklahoma City Thunder',
    'OKC': 'Oklahoma City Thunder',
    'Trail Blazers': 'Portland Trail Blazers',
    'Blazers': 'Portland Trail Blazers',
    'Jazz': 'Utah Jazz',
    'Warriors': 'Golden State Warriors',
    'Dubs': 'Golden State Warriors',
    'Clippers': 'Los Angeles Clippers',
    'Lakers': 'Los Angeles Lakers',
    'Suns': 'Phoenix Suns',
    'Kings': 'Sacramento Kings',
    'Mavericks': 'Dallas Mavericks',
    'Mavs': 'Dallas Mavericks',
    'Rockets': 'Houston Rockets',
    'Grizzlies': 'Memphis Grizzlies',
    'Pelicans': 'New Orleans Pelicans',
    'Pels': 'New Orleans Pelicans',
    'Spurs': 'San Antonio Spurs',

    # Historical names
    'New Jersey Nets': 'Brooklyn Nets',
    'Seattle SuperSonics': 'Oklahoma City Thunder',
    'SuperSonics': 'Oklahoma City Thunder',
    'Sonics': 'Oklahoma City Thunder',
    'Vancouver Grizzlies': 'Memphis Grizzlies',
    'New Orleans Hornets': 'New Orleans Pelicans',
    'Charlotte Bobcats': 'Charlotte Hornets',
}


def get_team_code(team_name: str) -> str:
    """Get team code for a team name."""
    canonical = TEAM_ALIASES.get(team_name, team_name)
    if canonical in NBA_TEAMS:
        return NBA_TEAMS[canonical]['code']
    return team_name[:3].upper()


def get_team_conference(team_name: str) -> Optional[str]:
    """Get conference for a team."""
    canonical = TEAM_ALIASES.get(team_name, team_name)
    if canonical in NBA_TEAMS:
        return NBA_TEAMS[canonical]['conference']
    return None


def get_team_division(team_name: str) -> Optional[str]:
    """Get division for a team."""
    canonical = TEAM_ALIASES.get(team_name, team_name)
    if canonical in NBA_TEAMS:
        return NBA_TEAMS[canonical]['division']
    return None


# === MILESTONE THRESHOLDS ===
MILESTONE_THRESHOLDS = {
    # Scoring
    'twenty_points': 20,
    'thirty_points': 30,
    'forty_points': 40,
    'fifty_points': 50,
    'sixty_points': 60,
    'seventy_points': 70,

    # Rebounds
    'ten_rebounds': 10,
    'fifteen_rebounds': 15,
    'twenty_rebounds': 20,
    'twenty_five_rebounds': 25,

    # Assists
    'ten_assists': 10,
    'fifteen_assists': 15,
    'twenty_assists': 20,

    # Defense
    'five_blocks': 5,
    'five_steals': 5,
    'ten_blocks': 10,

    # Three-pointers
    'five_threes': 5,
    'seven_threes': 7,
    'ten_threes': 10,

    # Triple-double thresholds
    'triple_double_pts': 10,
    'triple_double_reb': 10,
    'triple_double_ast': 10,

    # Margin
    'blowout_margin': 20,
}

# === MILESTONE STAT CONFIGS ===
MILESTONE_STAT_CONFIGS: Dict[str, List[tuple]] = {
    'scoring': [
        ('seventy_point_games', 'pts', 70, None, '{value} points'),
        ('sixty_point_games', 'pts', 60, None, '{value} points'),
        ('fifty_point_games', 'pts', 50, None, '{value} points'),
        ('forty_point_games', 'pts', 40, None, '{value} points'),
        ('thirty_point_games', 'pts', 30, None, '{value} points'),
        ('twenty_point_games', 'pts', 20, None, '{value} points'),
    ],
    'rebounding': [
        ('twenty_five_rebound_games', 'trb', 25, None, '{value} rebounds'),
        ('twenty_rebound_games', 'trb', 20, None, '{value} rebounds'),
        ('fifteen_rebound_games', 'trb', 15, None, '{value} rebounds'),
        ('ten_rebound_games', 'trb', 10, None, '{value} rebounds'),
    ],
    'assists': [
        ('twenty_assist_games', 'ast', 20, None, '{value} assists'),
        ('fifteen_assist_games', 'ast', 15, None, '{value} assists'),
        ('ten_assist_games', 'ast', 10, None, '{value} assists'),
    ],
    'blocks': [
        ('ten_block_games', 'blk', 10, None, '{value} blocks'),
        ('five_block_games', 'blk', 5, None, '{value} blocks'),
    ],
    'steals': [
        ('ten_steal_games', 'stl', 10, None, '{value} steals'),
        ('five_steal_games', 'stl', 5, None, '{value} steals'),
    ],
    'three_pointers': [
        ('ten_three_games', 'fg3', 10, None, '{value} three-pointers'),
        ('seven_three_games', 'fg3', 7, None, '{value} three-pointers'),
        ('five_three_games', 'fg3', 5, None, '{value} three-pointers'),
    ],
}

# === EXCEL COLOR SCHEME ===
EXCEL_COLORS = {
    'primary_blue': '#1D428A',      # NBA blue
    'secondary_red': '#C8102E',     # NBA red
    'light_blue': '#E8F4F8',
    'accent_gold': '#FDB927',
    'light_gold': '#FFF8E1',
    'neutral_gray': '#757575',
    'light_gray': '#F5F5F5',
    'white': '#FFFFFF',
    'header_blue': '#17408B',
    'alt_row': '#F0F8FF',
}

# === GAME TYPES ===
GAME_TYPES = {
    'regular': 'Regular Season',
    'playoff': 'Playoffs',
    'playin': 'Play-In Tournament',
    'preseason': 'Preseason',
    'allstar': 'All-Star Game',
}

# === NBA ARENAS ===
# All 30 NBA arenas with coordinates, city, state
NBA_ARENAS: Dict[str, Dict] = {
    'BOS': {
        'name': 'TD Garden',
        'team': 'Boston Celtics',
        'city': 'Boston',
        'state': 'MA',
        'lat': 42.3662,
        'lng': -71.0621,
    },
    'BKN': {
        'name': 'Barclays Center',
        'team': 'Brooklyn Nets',
        'city': 'Brooklyn',
        'state': 'NY',
        'lat': 40.6826,
        'lng': -73.9754,
    },
    'NYK': {
        'name': 'Madison Square Garden',
        'team': 'New York Knicks',
        'city': 'New York',
        'state': 'NY',
        'lat': 40.7505,
        'lng': -73.9934,
    },
    'PHI': {
        'name': 'Wells Fargo Center',
        'team': 'Philadelphia 76ers',
        'city': 'Philadelphia',
        'state': 'PA',
        'lat': 39.9012,
        'lng': -75.1720,
    },
    'TOR': {
        'name': 'Scotiabank Arena',
        'team': 'Toronto Raptors',
        'city': 'Toronto',
        'state': 'ON',
        'lat': 43.6435,
        'lng': -79.3791,
    },
    'CHI': {
        'name': 'United Center',
        'team': 'Chicago Bulls',
        'city': 'Chicago',
        'state': 'IL',
        'lat': 41.8807,
        'lng': -87.6742,
    },
    'CLE': {
        'name': 'Rocket Mortgage FieldHouse',
        'team': 'Cleveland Cavaliers',
        'city': 'Cleveland',
        'state': 'OH',
        'lat': 41.4965,
        'lng': -81.6882,
    },
    'DET': {
        'name': 'Little Caesars Arena',
        'team': 'Detroit Pistons',
        'city': 'Detroit',
        'state': 'MI',
        'lat': 42.3411,
        'lng': -83.0553,
    },
    'IND': {
        'name': 'Gainbridge Fieldhouse',
        'team': 'Indiana Pacers',
        'city': 'Indianapolis',
        'state': 'IN',
        'lat': 39.7640,
        'lng': -86.1555,
    },
    'MIL': {
        'name': 'Fiserv Forum',
        'team': 'Milwaukee Bucks',
        'city': 'Milwaukee',
        'state': 'WI',
        'lat': 43.0451,
        'lng': -87.9174,
    },
    'ATL': {
        'name': 'State Farm Arena',
        'team': 'Atlanta Hawks',
        'city': 'Atlanta',
        'state': 'GA',
        'lat': 33.7573,
        'lng': -84.3963,
    },
    'CHA': {
        'name': 'Spectrum Center',
        'team': 'Charlotte Hornets',
        'city': 'Charlotte',
        'state': 'NC',
        'lat': 35.2251,
        'lng': -80.8392,
    },
    'MIA': {
        'name': 'Kaseya Center',
        'team': 'Miami Heat',
        'city': 'Miami',
        'state': 'FL',
        'lat': 25.7814,
        'lng': -80.1870,
    },
    'ORL': {
        'name': 'Kia Center',
        'team': 'Orlando Magic',
        'city': 'Orlando',
        'state': 'FL',
        'lat': 28.5392,
        'lng': -81.3839,
    },
    'WAS': {
        'name': 'Capital One Arena',
        'team': 'Washington Wizards',
        'city': 'Washington',
        'state': 'DC',
        'lat': 38.8981,
        'lng': -77.0209,
    },
    'DEN': {
        'name': 'Ball Arena',
        'team': 'Denver Nuggets',
        'city': 'Denver',
        'state': 'CO',
        'lat': 39.7487,
        'lng': -105.0077,
    },
    'MIN': {
        'name': 'Target Center',
        'team': 'Minnesota Timberwolves',
        'city': 'Minneapolis',
        'state': 'MN',
        'lat': 44.9795,
        'lng': -93.2761,
    },
    'OKC': {
        'name': 'Paycom Center',
        'team': 'Oklahoma City Thunder',
        'city': 'Oklahoma City',
        'state': 'OK',
        'lat': 35.4634,
        'lng': -97.5151,
    },
    'POR': {
        'name': 'Moda Center',
        'team': 'Portland Trail Blazers',
        'city': 'Portland',
        'state': 'OR',
        'lat': 45.5316,
        'lng': -122.6668,
    },
    'UTA': {
        'name': 'Delta Center',
        'team': 'Utah Jazz',
        'city': 'Salt Lake City',
        'state': 'UT',
        'lat': 40.7683,
        'lng': -111.9011,
    },
    'GSW': {
        'name': 'Chase Center',
        'team': 'Golden State Warriors',
        'city': 'San Francisco',
        'state': 'CA',
        'lat': 37.7680,
        'lng': -122.3877,
    },
    'LAC': {
        'name': 'Intuit Dome',
        'team': 'Los Angeles Clippers',
        'city': 'Inglewood',
        'state': 'CA',
        'lat': 33.9425,
        'lng': -118.3419,
    },
    'LAL': {
        'name': 'Crypto.com Arena',
        'team': 'Los Angeles Lakers',
        'city': 'Los Angeles',
        'state': 'CA',
        'lat': 34.0430,
        'lng': -118.2673,
    },
    'PHX': {
        'name': 'Footprint Center',
        'team': 'Phoenix Suns',
        'city': 'Phoenix',
        'state': 'AZ',
        'lat': 33.4457,
        'lng': -112.0712,
    },
    'SAC': {
        'name': 'Golden 1 Center',
        'team': 'Sacramento Kings',
        'city': 'Sacramento',
        'state': 'CA',
        'lat': 38.5802,
        'lng': -121.4997,
    },
    'DAL': {
        'name': 'American Airlines Center',
        'team': 'Dallas Mavericks',
        'city': 'Dallas',
        'state': 'TX',
        'lat': 32.7905,
        'lng': -96.8103,
    },
    'HOU': {
        'name': 'Toyota Center',
        'team': 'Houston Rockets',
        'city': 'Houston',
        'state': 'TX',
        'lat': 29.7508,
        'lng': -95.3621,
    },
    'MEM': {
        'name': 'FedExForum',
        'team': 'Memphis Grizzlies',
        'city': 'Memphis',
        'state': 'TN',
        'lat': 35.1382,
        'lng': -90.0506,
    },
    'NOP': {
        'name': 'Smoothie King Center',
        'team': 'New Orleans Pelicans',
        'city': 'New Orleans',
        'state': 'LA',
        'lat': 29.9490,
        'lng': -90.0821,
    },
    'SAS': {
        'name': 'Frost Bank Center',
        'team': 'San Antonio Spurs',
        'city': 'San Antonio',
        'state': 'TX',
        'lat': 29.4270,
        'lng': -98.4375,
    },
}

# Historical arena names (for parsing old games)
ARENA_ALIASES: Dict[str, str] = {
    # Current arenas with previous names
    'American Airlines Arena': 'MIA',  # Now Kaseya Center
    'FTX Arena': 'MIA',
    'Amway Center': 'ORL',  # Now Kia Center
    'Verizon Center': 'WAS',  # Now Capital One Arena
    'Pepsi Center': 'DEN',  # Now Ball Arena
    'Oracle Arena': 'GSW',  # Warriors old arena
    'Staples Center': 'LAL',  # Now Crypto.com Arena (also LAC before)
    'Quicken Loans Arena': 'CLE',  # Now Rocket Mortgage FieldHouse
    'Bankers Life Fieldhouse': 'IND',  # Now Gainbridge Fieldhouse
    'Vivint Arena': 'UTA',  # Now Delta Center
    'Vivint Smart Home Arena': 'UTA',
    'AT&T Center': 'SAS',  # Now Frost Bank Center
    'Chesapeake Energy Arena': 'OKC',  # Now Paycom Center
    'Moda Center': 'POR',
    'Rose Garden': 'POR',  # Old name
    'Bradley Center': 'MIL',  # Old arena
    'BMO Harris Bradley Center': 'MIL',
    'The Palace of Auburn Hills': 'DET',  # Old arena
    'Continental Airlines Arena': 'BKN',  # Old Nets arena (NJ)
    'Izod Center': 'BKN',
    'Prudential Center': 'BKN',  # Temporary
}


# === SEASON FORMAT ===
# NBA season spans two calendar years (e.g., 2024-25)
def get_season_string(year: int, month: int) -> str:
    """Get season string for a date.

    Args:
        year: Calendar year
        month: Month (1-12)

    Returns:
        Season string like "2024-25"
    """
    # NBA season starts in October
    if month >= 10:
        return f"{year}-{str(year + 1)[-2:]}"
    else:
        return f"{year - 1}-{str(year)[-2:]}"
