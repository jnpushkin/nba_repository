"""
Helper utilities for NBA data processing.
"""

import re
from typing import Any, Optional, Union

from .constants import TEAM_ALIASES, NBA_TEAMS


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            # Handle strings like "12.0"
            return int(float(value.strip()))
        except (ValueError, AttributeError):
            return default
    return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return default
    return default


def normalize_name(name: str) -> str:
    """Normalize a player name for consistent matching."""
    if not name:
        return ""
    # Remove suffixes like Jr., Sr., III, etc.
    name = re.sub(r'\s+(Jr\.?|Sr\.?|III|II|IV)$', '', name, flags=re.IGNORECASE)
    # Remove periods
    name = name.replace('.', '')
    # Normalize whitespace
    name = ' '.join(name.split())
    return name.strip().lower()


def get_team_code(team_name: str) -> str:
    """Get team abbreviation code."""
    canonical = TEAM_ALIASES.get(team_name, team_name)
    if canonical in NBA_TEAMS:
        return NBA_TEAMS[canonical]['code']
    # Fallback: first 3 letters uppercased
    return team_name[:3].upper()


def parse_minutes(mp: Union[str, int, float]) -> float:
    """Parse minutes played from various formats.

    Args:
        mp: Minutes in format "MM:SS", decimal, or integer

    Returns:
        Minutes as float
    """
    if isinstance(mp, (int, float)):
        return float(mp)

    if isinstance(mp, str):
        if ':' in mp:
            parts = mp.split(':')
            try:
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
                return minutes + seconds / 60.0
            except ValueError:
                return 0.0
        try:
            return float(mp)
        except ValueError:
            return 0.0

    return 0.0


def calculate_game_score(stats: dict) -> float:
    """Calculate John Hollinger's Game Score.

    Game Score = PTS + 0.4*FGM - 0.7*FGA - 0.4*(FTA-FTM) + 0.7*ORB + 0.3*DRB
                 + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV

    Args:
        stats: Dictionary with player stats

    Returns:
        Game score value
    """
    pts = safe_int(stats.get('pts', 0))
    fg = safe_int(stats.get('fg', 0))
    fga = safe_int(stats.get('fga', 0))
    ft = safe_int(stats.get('ft', 0))
    fta = safe_int(stats.get('fta', 0))
    orb = safe_int(stats.get('orb', 0))
    drb = safe_int(stats.get('drb', 0))
    stl = safe_int(stats.get('stl', 0))
    ast = safe_int(stats.get('ast', 0))
    blk = safe_int(stats.get('blk', 0))
    pf = safe_int(stats.get('pf', 0))
    tov = safe_int(stats.get('tov', 0))

    game_score = (
        pts
        + 0.4 * fg
        - 0.7 * fga
        - 0.4 * (fta - ft)
        + 0.7 * orb
        + 0.3 * drb
        + stl
        + 0.7 * ast
        + 0.7 * blk
        - 0.4 * pf
        - tov
    )

    return round(game_score, 1)


def is_triple_double(stats: dict, threshold: int = 10) -> bool:
    """Check if stats constitute a triple-double.

    Args:
        stats: Dictionary with player stats
        threshold: Minimum value for each category (default 10)

    Returns:
        True if triple-double achieved
    """
    categories = ['pts', 'trb', 'ast', 'stl', 'blk']
    counts = sum(1 for cat in categories if safe_int(stats.get(cat, 0)) >= threshold)
    return counts >= 3


def is_double_double(stats: dict, threshold: int = 10) -> bool:
    """Check if stats constitute a double-double.

    Args:
        stats: Dictionary with player stats
        threshold: Minimum value for each category (default 10)

    Returns:
        True if double-double achieved
    """
    categories = ['pts', 'trb', 'ast', 'stl', 'blk']
    counts = sum(1 for cat in categories if safe_int(stats.get(cat, 0)) >= threshold)
    return counts >= 2


def calculate_true_shooting(pts: int, fga: int, fta: int) -> Optional[float]:
    """Calculate true shooting percentage.

    TS% = PTS / (2 * (FGA + 0.44 * FTA))

    Args:
        pts: Points scored
        fga: Field goal attempts
        fta: Free throw attempts

    Returns:
        True shooting percentage or None if not calculable
    """
    denominator = 2 * (fga + 0.44 * fta)
    if denominator == 0:
        return None
    return round(pts / denominator, 3)


def calculate_effective_fg_pct(fg: int, fg3: int, fga: int) -> Optional[float]:
    """Calculate effective field goal percentage.

    eFG% = (FG + 0.5 * 3PM) / FGA

    Args:
        fg: Field goals made
        fg3: Three-pointers made
        fga: Field goal attempts

    Returns:
        Effective FG% or None if not calculable
    """
    if fga == 0:
        return None
    return round((fg + 0.5 * fg3) / fga, 3)
