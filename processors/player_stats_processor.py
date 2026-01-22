"""
Player statistics aggregation processor for NBA data.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from collections import defaultdict

from .base_processor import BaseProcessor
from ..utils.helpers import (
    safe_int, safe_float, normalize_name, calculate_game_score,
    is_triple_double, is_double_double, parse_minutes,
    calculate_true_shooting, calculate_effective_fg_pct
)


class PlayerStatsProcessor(BaseProcessor):
    """Process and aggregate NBA player statistics across games."""

    def __init__(self, games: List[Dict[str, Any]]):
        super().__init__(games)
        self.player_totals = defaultdict(lambda: defaultdict(int))
        self.player_games = defaultdict(list)
        self.player_teams = defaultdict(set)
        self.player_ids = {}
        # Track starters vs bench
        self.starter_totals = defaultdict(lambda: defaultdict(int))
        self.bench_totals = defaultdict(lambda: defaultdict(int))
        # Track season highs
        self.player_season_highs = defaultdict(lambda: {
            'pts': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'trb': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'ast': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'stl': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'blk': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'fg3': {'value': 0, 'game_id': '', 'date': '', 'opponent': ''},
            'game_score': {'value': -999, 'game_id': '', 'date': '', 'opponent': ''},
            'plus_minus': {'value': -999, 'game_id': '', 'date': '', 'opponent': ''},
        })
        # Track special achievements
        self.triple_doubles = []
        self.double_doubles = []

    def process_all_player_stats(self) -> Dict[str, pd.DataFrame]:
        """
        Process all player statistics from all games.

        Returns:
            Dictionary containing:
            - 'players': DataFrame with aggregated player stats
            - 'player_games': DataFrame with per-game player stats
            - 'starters_vs_bench': DataFrame with starters vs bench splits
            - 'season_highs': DataFrame with season high performances
            - 'triple_doubles': DataFrame with triple-double games
            - 'double_doubles': DataFrame with double-double games
        """
        self._aggregate_player_stats()

        players_df = self._create_players_dataframe()
        player_games_df = self._create_player_games_dataframe()
        starters_bench_df = self._create_starters_bench_dataframe()
        season_highs_df = self._create_season_highs_dataframe()
        triple_doubles_df = self._create_triple_doubles_dataframe()
        double_doubles_df = self._create_double_doubles_dataframe()

        return {
            'players': players_df,
            'player_games': player_games_df,
            'starters_vs_bench': starters_bench_df,
            'season_highs': season_highs_df,
            'triple_doubles': triple_doubles_df,
            'double_doubles': double_doubles_df,
        }

    def _aggregate_player_stats(self) -> None:
        """Aggregate statistics for each player across all games."""
        stat_keys = [
            'pts', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf',
            'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta',
            'orb', 'drb', 'plus_minus',
        ]

        for game in self.games:
            basic_info = self.get_basic_info(game)
            game_id = self.get_game_id(game)
            date = basic_info.get('date', '')
            date_yyyymmdd = basic_info.get('date_yyyymmdd', '')
            game_type = basic_info.get('game_type', 'regular')
            season = basic_info.get('season', '')

            for side in ['away', 'home']:
                team = basic_info.get(f'{side}_team', '')
                opponent = basic_info.get('home_team' if side == 'away' else 'away_team', '')
                team_score = safe_int(basic_info.get(f'{side}_score', 0))
                opp_score = safe_int(basic_info.get('home_score' if side == 'away' else 'away_score', 0))
                won = team_score > opp_score

                players = self.get_players_for_side(game, side)

                for player in players:
                    player_name = player.get('name', '')
                    player_id = player.get('player_id', '')

                    if not player_name:
                        continue

                    key = player_id if player_id else normalize_name(player_name)

                    if player_id:
                        self.player_ids[key] = player_id

                    self.player_teams[key].add(team)
                    self.player_totals[key]['name'] = player_name

                    # Aggregate stats
                    for stat in stat_keys:
                        value = safe_int(player.get(stat, 0))
                        self.player_totals[key][stat] += value

                    # Track minutes
                    mp = player.get('mp', 0)
                    minutes = parse_minutes(mp)

                    if minutes > 0 or safe_int(player.get('pts', 0)) > 0:
                        self.player_totals[key]['games'] += 1
                        self.player_totals[key]['minutes'] += minutes

                    if won:
                        self.player_totals[key]['wins'] += 1

                    # Calculate game score
                    player_stats = {stat: safe_int(player.get(stat, 0)) for stat in stat_keys}
                    player_stats['mp'] = minutes
                    game_score = calculate_game_score(player_stats)

                    # Track starters vs bench
                    is_starter = player.get('starter', False)
                    split_dict = self.starter_totals if is_starter else self.bench_totals

                    for stat in stat_keys:
                        value = safe_int(player.get(stat, 0))
                        split_dict[team][stat] += value
                    split_dict[team]['games'] += 1
                    split_dict[team]['minutes'] += minutes

                    # Track season highs
                    highs = self.player_season_highs[key]
                    for stat in ['pts', 'trb', 'ast', 'stl', 'blk', 'fg3']:
                        value = safe_int(player.get(stat, 0))
                        if value > highs[stat]['value']:
                            highs[stat] = {
                                'value': value,
                                'game_id': game_id,
                                'date': date,
                                'opponent': opponent,
                            }

                    plus_minus = safe_int(player.get('plus_minus', -999))
                    if plus_minus > highs['plus_minus']['value']:
                        highs['plus_minus'] = {
                            'value': plus_minus,
                            'game_id': game_id,
                            'date': date,
                            'opponent': opponent,
                        }

                    if game_score > highs['game_score']['value']:
                        highs['game_score'] = {
                            'value': game_score,
                            'game_id': game_id,
                            'date': date,
                            'opponent': opponent,
                        }

                    # Track triple-doubles and double-doubles
                    if is_triple_double(player_stats):
                        self.triple_doubles.append({
                            'player': player_name,
                            'player_id': player_id,
                            'date': date,
                            'team': team,
                            'opponent': opponent,
                            'pts': player_stats['pts'],
                            'trb': player_stats['trb'],
                            'ast': player_stats['ast'],
                            'stl': player_stats['stl'],
                            'blk': player_stats['blk'],
                            'game_id': game_id,
                            'result': 'W' if won else 'L',
                        })
                    elif is_double_double(player_stats):
                        self.double_doubles.append({
                            'player': player_name,
                            'player_id': player_id,
                            'date': date,
                            'team': team,
                            'opponent': opponent,
                            'pts': player_stats['pts'],
                            'trb': player_stats['trb'],
                            'ast': player_stats['ast'],
                            'game_id': game_id,
                            'result': 'W' if won else 'L',
                        })

                    # Store per-game record
                    self.player_games[key].append({
                        'player': player_name,
                        'player_id': player_id,
                        'date': date,
                        'date_yyyymmdd': date_yyyymmdd,
                        'team': team,
                        'opponent': opponent,
                        'result': 'W' if won else 'L',
                        'score': f"{team_score}-{opp_score}",
                        'game_id': game_id,
                        'game_type': game_type,
                        'season': season,
                        'starter': is_starter,
                        **player_stats,
                        'game_score': game_score,
                    })

    def _create_players_dataframe(self) -> pd.DataFrame:
        """Create aggregated players DataFrame."""
        rows = []

        for key, totals in self.player_totals.items():
            games = totals.get('games', 0)
            if games == 0:
                continue

            player_id = self.player_ids.get(key, key)
            teams = ', '.join(sorted(self.player_teams[key]))

            # Per-game averages
            ppg = round(totals['pts'] / games, 1) if games > 0 else 0
            rpg = round(totals['trb'] / games, 1) if games > 0 else 0
            apg = round(totals['ast'] / games, 1) if games > 0 else 0
            spg = round(totals['stl'] / games, 1) if games > 0 else 0
            bpg = round(totals['blk'] / games, 1) if games > 0 else 0
            mpg = round(totals['minutes'] / games, 1) if games > 0 else 0
            topg = round(totals['tov'] / games, 1) if games > 0 else 0

            # Shooting percentages
            fg_pct = round(totals['fg'] / totals['fga'], 3) if totals['fga'] > 0 else 0
            fg3_pct = round(totals['fg3'] / totals['fg3a'], 3) if totals['fg3a'] > 0 else 0
            ft_pct = round(totals['ft'] / totals['fta'], 3) if totals['fta'] > 0 else 0

            # Advanced stats
            ts_pct = calculate_true_shooting(totals['pts'], totals['fga'], totals['fta'])
            efg_pct = calculate_effective_fg_pct(totals['fg'], totals['fg3'], totals['fga'])

            rows.append({
                'Player': totals['name'],
                'Player ID': player_id,
                'Team': teams,
                'Games': games,
                'Wins': totals.get('wins', 0),
                'MPG': mpg,
                'PPG': ppg,
                'RPG': rpg,
                'APG': apg,
                'SPG': spg,
                'BPG': bpg,
                'TOPG': topg,
                'FG%': fg_pct,
                '3P%': fg3_pct,
                'FT%': ft_pct,
                'TS%': ts_pct or 0,
                'eFG%': efg_pct or 0,
                'Total PTS': totals['pts'],
                'Total REB': totals['trb'],
                'Total AST': totals['ast'],
                'Total STL': totals['stl'],
                'Total BLK': totals['blk'],
                'Total TOV': totals['tov'],
                'FGM': totals['fg'],
                'FGA': totals['fga'],
                '3PM': totals['fg3'],
                '3PA': totals['fg3a'],
                'FTM': totals['ft'],
                'FTA': totals['fta'],
                'Total +/-': totals['plus_minus'],
            })

        rows.sort(key=lambda x: x['Total PTS'], reverse=True)

        columns = [
            'Player', 'Player ID', 'Team', 'Games', 'Wins', 'MPG',
            'PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TOPG',
            'FG%', '3P%', 'FT%', 'TS%', 'eFG%',
            'Total PTS', 'Total REB', 'Total AST', 'Total STL', 'Total BLK', 'Total TOV',
            'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'Total +/-',
        ]

        return self.create_dataframe(rows, columns)

    def _create_player_games_dataframe(self) -> pd.DataFrame:
        """Create per-game player stats DataFrame."""
        all_game_rows = []

        for key, games in self.player_games.items():
            all_game_rows.extend(games)

        all_game_rows.sort(key=lambda x: x.get('date_yyyymmdd', ''), reverse=True)

        columns = [
            'player', 'player_id', 'date', 'team', 'opponent', 'result', 'score',
            'game_type', 'starter', 'mp', 'pts', 'trb', 'ast', 'stl', 'blk',
            'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'tov', 'pf',
            'plus_minus', 'game_score', 'game_id'
        ]

        return self.create_dataframe(all_game_rows, columns)

    def _create_starters_bench_dataframe(self) -> pd.DataFrame:
        """Create starters vs bench splits DataFrame by team."""
        rows = []

        all_teams = set(self.starter_totals.keys()) | set(self.bench_totals.keys())

        for team in sorted(all_teams):
            starter = self.starter_totals.get(team, {})
            bench = self.bench_totals.get(team, {})

            starter_games = starter.get('games', 0)
            bench_games = bench.get('games', 0)

            if starter_games == 0 and bench_games == 0:
                continue

            def calc_avg(totals: Dict[str, int], games: int, stat: str) -> float:
                if games == 0:
                    return 0
                return round(totals.get(stat, 0) / games, 1)

            rows.append({
                'Team': team,
                'Type': 'Starters',
                'Games': starter_games,
                'PPG': calc_avg(starter, starter_games, 'pts'),
                'RPG': calc_avg(starter, starter_games, 'trb'),
                'APG': calc_avg(starter, starter_games, 'ast'),
                'MPG': calc_avg(starter, starter_games, 'minutes'),
                'Total PTS': starter.get('pts', 0),
                'Total REB': starter.get('trb', 0),
                'Total AST': starter.get('ast', 0),
            })
            rows.append({
                'Team': team,
                'Type': 'Bench',
                'Games': bench_games,
                'PPG': calc_avg(bench, bench_games, 'pts'),
                'RPG': calc_avg(bench, bench_games, 'trb'),
                'APG': calc_avg(bench, bench_games, 'ast'),
                'MPG': calc_avg(bench, bench_games, 'minutes'),
                'Total PTS': bench.get('pts', 0),
                'Total REB': bench.get('trb', 0),
                'Total AST': bench.get('ast', 0),
            })

        columns = ['Team', 'Type', 'Games', 'PPG', 'RPG', 'APG', 'MPG',
                   'Total PTS', 'Total REB', 'Total AST']

        return self.create_dataframe(rows, columns)

    def _create_season_highs_dataframe(self) -> pd.DataFrame:
        """Create season highs DataFrame."""
        rows = []

        for key, highs in self.player_season_highs.items():
            player_name = self.player_totals[key].get('name', key)
            teams = ', '.join(sorted(self.player_teams.get(key, set())))

            if highs['pts']['value'] == 0 and highs['game_score']['value'] <= -999:
                continue

            rows.append({
                'Player': player_name,
                'Player ID': key,
                'Team': teams,
                'High PTS': highs['pts']['value'],
                'PTS Game': highs['pts']['date'],
                'PTS Opponent': highs['pts']['opponent'],
                'High REB': highs['trb']['value'],
                'REB Game': highs['trb']['date'],
                'REB Opponent': highs['trb']['opponent'],
                'High AST': highs['ast']['value'],
                'AST Game': highs['ast']['date'],
                'AST Opponent': highs['ast']['opponent'],
                'High 3PM': highs['fg3']['value'],
                '3PM Game': highs['fg3']['date'],
                'High +/-': highs['plus_minus']['value'] if highs['plus_minus']['value'] > -999 else 0,
                '+/- Game': highs['plus_minus']['date'],
                'Best Game Score': highs['game_score']['value'] if highs['game_score']['value'] > -999 else 0,
                'Best GS Date': highs['game_score']['date'],
            })

        rows.sort(key=lambda x: x['High PTS'], reverse=True)

        columns = ['Player', 'Player ID', 'Team', 'High PTS', 'PTS Game', 'PTS Opponent',
                   'High REB', 'REB Game', 'REB Opponent',
                   'High AST', 'AST Game', 'AST Opponent',
                   'High 3PM', '3PM Game', 'High +/-', '+/- Game',
                   'Best Game Score', 'Best GS Date']

        return self.create_dataframe(rows, columns)

    def _create_triple_doubles_dataframe(self) -> pd.DataFrame:
        """Create triple-doubles DataFrame."""
        rows = sorted(self.triple_doubles, key=lambda x: x.get('date', ''), reverse=True)

        columns = ['player', 'player_id', 'date', 'team', 'opponent', 'result',
                   'pts', 'trb', 'ast', 'stl', 'blk', 'game_id']

        return self.create_dataframe(rows, columns)

    def _create_double_doubles_dataframe(self) -> pd.DataFrame:
        """Create double-doubles DataFrame."""
        rows = sorted(self.double_doubles, key=lambda x: x.get('date', ''), reverse=True)

        columns = ['player', 'player_id', 'date', 'team', 'opponent', 'result',
                   'pts', 'trb', 'ast', 'game_id']

        return self.create_dataframe(rows, columns)

    def get_top_scorers(self, n: int = 10) -> pd.DataFrame:
        """Get top N scorers by total points."""
        players_df = self._create_players_dataframe()
        return players_df.nlargest(n, 'Total PTS')

    def get_top_rebounders(self, n: int = 10) -> pd.DataFrame:
        """Get top N rebounders by total rebounds."""
        players_df = self._create_players_dataframe()
        return players_df.nlargest(n, 'Total REB')

    def get_top_by_average(self, stat: str = 'PPG', n: int = 10, min_games: int = 10) -> pd.DataFrame:
        """Get top N players by per-game average."""
        players_df = self._create_players_dataframe()
        filtered = players_df[players_df['Games'] >= min_games]
        return filtered.nlargest(n, stat)
