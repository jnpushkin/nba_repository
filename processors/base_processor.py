"""
Base processor class for NBA game data processing.
"""

from typing import Dict, List, Any, Optional
import pandas as pd

from ..utils.helpers import get_team_code, safe_int, safe_float


class BaseProcessor:
    """Base class for all NBA game data processors."""

    def __init__(self, games: List[Dict[str, Any]]):
        """
        Initialize processor with games data.

        Args:
            games: List of parsed game dictionaries
        """
        self.games = games
        self.game_count = len(games)

    def create_dataframe(self, rows: List[Dict], columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Create a DataFrame from rows with optional column ordering.

        Args:
            rows: List of row dictionaries
            columns: Optional list of column names for ordering

        Returns:
            pandas DataFrame
        """
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if columns:
            existing_cols = [c for c in columns if c in df.columns]
            extra_cols = [c for c in df.columns if c not in columns]
            df = df[existing_cols + extra_cols]

        return df

    def get_basic_info(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely extract basic info from a game.

        Args:
            game: Game dictionary

        Returns:
            Basic info dictionary or empty dict
        """
        return game.get('basic_info', {})

    def get_game_id(self, game: Dict[str, Any]) -> str:
        """
        Extract game ID safely.

        Args:
            game: Game dictionary

        Returns:
            Game ID string or 'UNKNOWN'
        """
        return game.get('game_id', 'UNKNOWN')

    def get_team_code(self, game: Dict[str, Any], side: str) -> str:
        """
        Get team code for home or away team.

        Args:
            game: Game dictionary
            side: 'home' or 'away'

        Returns:
            Team code string
        """
        basic_info = self.get_basic_info(game)
        team_name = basic_info.get(f'{side}_team', '')
        return get_team_code(team_name)

    def get_team_name(self, game: Dict[str, Any], side: str) -> str:
        """
        Get team name for home or away team.

        Args:
            game: Game dictionary
            side: 'home' or 'away'

        Returns:
            Team name string
        """
        basic_info = self.get_basic_info(game)
        return basic_info.get(f'{side}_team', '')

    def get_score(self, game: Dict[str, Any]) -> str:
        """
        Get formatted score string.

        Args:
            game: Game dictionary

        Returns:
            Score string like "110-105"
        """
        basic_info = self.get_basic_info(game)
        away = safe_int(basic_info.get('away_score', 0))
        home = safe_int(basic_info.get('home_score', 0))
        return f"{away}-{home}"

    def get_winner(self, game: Dict[str, Any]) -> str:
        """
        Determine the winning team.

        Args:
            game: Game dictionary

        Returns:
            'home', 'away', or 'tie'
        """
        basic_info = self.get_basic_info(game)
        away = safe_int(basic_info.get('away_score', 0))
        home = safe_int(basic_info.get('home_score', 0))

        if away > home:
            return 'away'
        elif home > away:
            return 'home'
        return 'tie'

    def get_players_for_side(self, game: Dict[str, Any], side: str) -> List[Dict[str, Any]]:
        """
        Get player stats for a side (home/away).

        Args:
            game: Game dictionary
            side: 'home' or 'away'

        Returns:
            List of player stat dictionaries
        """
        box_score = game.get('box_score', {})
        side_data = box_score.get(side, {})

        players = side_data.get('players', [])
        if not players:
            players = side_data.get('basic', [])

        return players

    def get_game_type(self, game: Dict[str, Any]) -> str:
        """
        Get game type (regular, playoff, playin, etc.).

        Args:
            game: Game dictionary

        Returns:
            Game type string
        """
        basic_info = self.get_basic_info(game)
        return basic_info.get('game_type', 'regular')

    def filter_games_by_type(self, game_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filter games by type.

        Args:
            game_type: 'regular', 'playoff', 'playin', or None for all

        Returns:
            Filtered list of games
        """
        if not game_type:
            return self.games

        return [g for g in self.games if self.get_game_type(g) == game_type]

    def filter_games_by_team(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Filter games involving a specific team.

        Args:
            team_name: Team name to filter by

        Returns:
            Filtered list of games
        """
        filtered = []
        for game in self.games:
            basic_info = self.get_basic_info(game)
            home_team = basic_info.get('home_team', '')
            away_team = basic_info.get('away_team', '')
            if team_name in (home_team, away_team):
                filtered.append(game)
        return filtered

    def sort_by_date(self, ascending: bool = False) -> List[Dict[str, Any]]:
        """
        Sort games by date.

        Args:
            ascending: True for oldest first, False for newest first

        Returns:
            Sorted list of games
        """
        def get_date_key(game):
            basic_info = game.get('basic_info', {})
            return basic_info.get('date_yyyymmdd', '00000000')

        return sorted(self.games, key=get_date_key, reverse=not ascending)

    def get_season(self, game: Dict[str, Any]) -> str:
        """
        Get season string for a game.

        Args:
            game: Game dictionary

        Returns:
            Season string like "2024-25"
        """
        basic_info = self.get_basic_info(game)
        return basic_info.get('season', '')
