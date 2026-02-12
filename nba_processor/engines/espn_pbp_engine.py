"""
ESPN play-by-play analysis engine for NBA games.

Analyzes ESPN PBP data for:
- Team scoring runs (consecutive team points)
- Player point streaks (consecutive player points)
- Biggest comebacks
- Clutch scoring (final 5 minutes)
- Game-winning shots
"""

from typing import Dict, Any, List, Optional
import re


class ESPNPlayByPlayEngine:
    """Analyze ESPN play-by-play data for advanced statistics."""

    def __init__(self, espn_pbp: Dict[str, Any], game_data: Dict[str, Any]):
        """
        Initialize the engine.

        Args:
            espn_pbp: Parsed ESPN play-by-play data from espn_pbp_scraper
            game_data: Game data dictionary with basic_info, etc.
        """
        self.espn_pbp = espn_pbp
        self.game_data = game_data
        self.plays = espn_pbp.get('plays', [])
        self.away_team = espn_pbp.get('away_team', '')
        self.home_team = espn_pbp.get('home_team', '')
        self.final_away = espn_pbp.get('away_score', 0)
        self.final_home = espn_pbp.get('home_score', 0)

        # Determine winner from actual game scores (more reliable than PBP last play)
        basic_info = game_data.get('basic_info', {})
        actual_away_score = basic_info.get('away_score', 0)
        actual_home_score = basic_info.get('home_score', 0)

        if actual_away_score > 0 or actual_home_score > 0:
            self.winner_side = 'home' if actual_home_score > actual_away_score else 'away'
        else:
            self.winner_side = 'home' if self.final_home > self.final_away else 'away'
        self.winner_team = self.home_team if self.winner_side == 'home' else self.away_team

    def analyze(self) -> Dict[str, Any]:
        """Run all analyses and return combined results."""
        if not self.plays:
            return {}

        return {
            'team_scoring_runs': self.analyze_team_scoring_runs(),
            'player_point_streaks': self.analyze_player_point_streaks(),
            'biggest_comeback': self.analyze_biggest_comeback(),
            'clutch_scoring': self.analyze_clutch_scoring(),
            'game_winning_shots': self.analyze_game_winning_shots(),
        }

    def analyze_team_scoring_runs(self, min_points: int = 8) -> List[Dict[str, Any]]:
        """
        Find consecutive team scoring runs.

        A scoring run is consecutive points by one team with no opponent scoring.
        """
        runs = []
        if not self.plays:
            return runs

        current_run = {
            'team': None, 'team_side': None, 'points': 0,
            'start_time': '', 'end_time': '',
            'start_period': 0, 'end_period': 0,
            'start_score': '', 'end_score': '',
        }

        prev_away = 0
        prev_home = 0

        for play in self.plays:
            if not play.get('scoring_play'):
                continue

            away_score = play['away_score']
            home_score = play['home_score']
            team_side = play.get('team_side', '')

            away_scored = away_score - prev_away
            home_scored = home_score - prev_home

            if team_side == 'away' and away_scored > 0:
                scoring_side = 'away'
                points = away_scored
            elif team_side == 'home' and home_scored > 0:
                scoring_side = 'home'
                points = home_scored
            else:
                if current_run['team'] and current_run['points'] >= min_points:
                    runs.append(current_run.copy())
                current_run = {'team': None, 'team_side': None, 'points': 0, 'start_time': '', 'end_time': '', 'start_period': 0, 'end_period': 0, 'start_score': '', 'end_score': ''}
                prev_away = away_score
                prev_home = home_score
                continue

            if current_run['team_side'] == scoring_side:
                current_run['points'] += points
                current_run['end_time'] = play['time']
                current_run['end_period'] = play['period']
                current_run['end_score'] = f"{away_score}-{home_score}"
            else:
                if current_run['team'] and current_run['points'] >= min_points:
                    runs.append(current_run.copy())

                current_run = {
                    'team': play['team'], 'team_side': scoring_side,
                    'points': points,
                    'start_time': play['time'], 'end_time': play['time'],
                    'start_period': play['period'], 'end_period': play['period'],
                    'start_score': f"{prev_away}-{prev_home}",
                    'end_score': f"{away_score}-{home_score}",
                }

            prev_away = away_score
            prev_home = home_score

        if current_run['team'] and current_run['points'] >= min_points:
            runs.append(current_run)

        runs.sort(key=lambda x: x['points'], reverse=True)
        return runs

    def analyze_player_point_streaks(self, min_points: int = 6) -> List[Dict[str, Any]]:
        """
        Find consecutive individual player scoring streaks.

        Resets when ANY other player scores.
        """
        streaks = []
        if not self.plays:
            return streaks

        current_streak = {
            'player': None, 'team': None, 'team_side': None,
            'points': 0, 'start_time': '', 'end_time': '',
            'start_period': 0, 'end_period': 0,
            'start_score': '', 'end_score': '',
        }

        prev_away = 0
        prev_home = 0

        for play in self.plays:
            if not play.get('scoring_play'):
                continue

            player = play.get('player', '')
            team_side = play.get('team_side', '')
            away_score = play['away_score']
            home_score = play['home_score']

            points = play.get('score_value', 0)
            if points == 0:
                points = (away_score - prev_away) + (home_score - prev_home)

            if not player or points <= 0:
                prev_away = away_score
                prev_home = home_score
                continue

            if current_streak['player'] == player:
                current_streak['points'] += points
                current_streak['end_time'] = play['time']
                current_streak['end_period'] = play['period']
                current_streak['end_score'] = f"{away_score}-{home_score}"
            else:
                if current_streak['player'] and current_streak['points'] >= min_points:
                    streaks.append(current_streak.copy())

                current_streak = {
                    'player': player, 'team': play['team'], 'team_side': team_side,
                    'points': points,
                    'start_time': play['time'], 'end_time': play['time'],
                    'start_period': play['period'], 'end_period': play['period'],
                    'start_score': f"{prev_away}-{prev_home}",
                    'end_score': f"{away_score}-{home_score}",
                }

            prev_away = away_score
            prev_home = home_score

        if current_streak['player'] and current_streak['points'] >= min_points:
            streaks.append(current_streak)

        streaks.sort(key=lambda x: x['points'], reverse=True)
        return streaks

    def analyze_biggest_comeback(self) -> Optional[Dict[str, Any]]:
        """Find the biggest comeback (largest deficit overcome by winning team)."""
        if not self.plays:
            return None

        max_deficit = 0
        max_deficit_time = ''
        max_deficit_period = 0
        max_deficit_score = ''

        for play in self.plays:
            away_score = play['away_score']
            home_score = play['home_score']
            margin = away_score - home_score

            if self.winner_side == 'away':
                deficit = -margin if margin < 0 else 0
            else:
                deficit = margin if margin > 0 else 0

            if deficit > max_deficit:
                max_deficit = deficit
                max_deficit_time = play['time']
                max_deficit_period = play['period']
                max_deficit_score = f"{away_score}-{home_score}"

        if max_deficit == 0:
            return {
                'team': self.winner_team, 'team_side': self.winner_side,
                'deficit': 0, 'deficit_time': '', 'deficit_period': 0,
                'deficit_score': '', 'won': True, 'never_trailed': True,
                'final_score': f"{self.final_away}-{self.final_home}",
            }

        return {
            'team': self.winner_team, 'team_side': self.winner_side,
            'deficit': max_deficit,
            'deficit_time': max_deficit_time,
            'deficit_period': max_deficit_period,
            'deficit_score': max_deficit_score,
            'won': True, 'never_trailed': False,
            'final_score': f"{self.final_away}-{self.final_home}",
        }

    def analyze_clutch_scoring(self, final_minutes: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Find points scored in final minutes of regulation (Q4)."""
        result = {'away': [], 'home': []}
        if not self.plays:
            return result

        # NBA uses 4 quarters - Q4 is the final regulation period
        final_period = 4

        clutch_stats = {'away': {}, 'home': {}}

        for play in self.plays:
            if play['period'] != final_period:
                continue
            time_str = play.get('time', '')
            minutes = self._parse_time_minutes(time_str)
            if minutes is None or minutes >= final_minutes:
                continue
            if not play.get('scoring_play'):
                continue

            player = play.get('player', '')
            team_side = play.get('team_side', '')
            points = play.get('score_value', 0)
            play_type = play.get('play_type', '')

            if not player or not team_side or points == 0:
                continue

            if player not in clutch_stats[team_side]:
                clutch_stats[team_side][player] = {
                    'player': player, 'points': 0, 'fg': 0, 'ft': 0, 'three': 0,
                }

            stats = clutch_stats[team_side][player]
            stats['points'] += points

            if 'ft' in play_type or 'free_throw' in play_type:
                stats['ft'] += 1
            elif 'three' in play_type:
                stats['fg'] += 1
                stats['three'] += 1
            elif 'made' in play_type:
                stats['fg'] += 1

        for side in ['away', 'home']:
            result[side] = sorted(
                clutch_stats[side].values(),
                key=lambda x: x['points'],
                reverse=True
            )
        return result

    def analyze_game_winning_shots(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Find game-winning shots (clutch go-ahead in final 2 min, and last decisive shot)."""
        result = {'clutch_go_ahead': None, 'decisive_shot': None}
        if not self.plays:
            return result

        # NBA: Q4 is final regulation period
        final_period = 4
        last_go_ahead = None
        clutch_go_ahead = None

        prev_away = 0
        prev_home = 0

        for play in self.plays:
            if not play.get('scoring_play'):
                prev_away = play['away_score']
                prev_home = play['home_score']
                continue

            away_score = play['away_score']
            home_score = play['home_score']
            team_side = play.get('team_side', '')

            prev_margin = prev_away - prev_home
            curr_margin = away_score - home_score
            is_go_ahead = False

            if team_side == 'away' and self.winner_side == 'away':
                if prev_margin <= 0 and curr_margin > 0:
                    is_go_ahead = True
            elif team_side == 'home' and self.winner_side == 'home':
                if prev_margin >= 0 and curr_margin < 0:
                    is_go_ahead = True

            if is_go_ahead:
                shot_info = {
                    'player': play.get('player', ''),
                    'team': play.get('team', ''),
                    'team_side': team_side,
                    'time': play['time'],
                    'period': play['period'],
                    'points': play.get('score_value', 0),
                    'play_type': play.get('play_type', ''),
                    'score': f"{away_score}-{home_score}",
                    'text': play.get('text', ''),
                }
                last_go_ahead = shot_info

                if play['period'] == final_period:
                    minutes = self._parse_time_minutes(play['time'])
                    if minutes is not None and minutes < 2:
                        clutch_go_ahead = shot_info

            prev_away = away_score
            prev_home = home_score

        result['decisive_shot'] = last_go_ahead
        result['clutch_go_ahead'] = clutch_go_ahead
        return result

    def _parse_time_minutes(self, time_str: str) -> Optional[float]:
        """Parse time string to minutes remaining."""
        if not time_str:
            return None
        match = re.match(r'(\d+):(\d+)', time_str)
        if not match:
            return None
        return int(match.group(1)) + int(match.group(2)) / 60.0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the ESPN PBP analysis."""
        analysis = self.analyze()

        summary = {'has_espn_pbp': True, 'play_count': len(self.plays)}

        runs = analysis.get('team_scoring_runs', [])
        if runs:
            best_run = runs[0]
            summary['best_team_run'] = {
                'team': best_run['team'],
                'points': best_run['points'],
                'period': best_run['end_period'],
            }

        streaks = analysis.get('player_point_streaks', [])
        if streaks:
            best_streak = streaks[0]
            summary['best_player_streak'] = {
                'player': best_streak['player'],
                'team': best_streak['team'],
                'points': best_streak['points'],
            }

        comeback = analysis.get('biggest_comeback')
        if comeback and comeback['deficit'] > 0:
            summary['comeback'] = {
                'team': comeback['team'],
                'deficit': comeback['deficit'],
            }

        clutch = analysis.get('clutch_scoring', {})
        top_clutch = []
        for side in ['away', 'home']:
            if clutch.get(side):
                top_clutch.extend(clutch[side][:2])
        if top_clutch:
            top_clutch.sort(key=lambda x: x['points'], reverse=True)
            summary['top_clutch_scorer'] = top_clutch[0]

        gws = analysis.get('game_winning_shots', {})
        if gws.get('clutch_go_ahead'):
            summary['clutch_go_ahead'] = {
                'player': gws['clutch_go_ahead']['player'],
                'time': gws['clutch_go_ahead']['time'],
                'points': gws['clutch_go_ahead']['points'],
            }
        if gws.get('decisive_shot'):
            summary['decisive_shot'] = {
                'player': gws['decisive_shot']['player'],
                'time': gws['decisive_shot']['time'],
                'period': gws['decisive_shot']['period'],
            }

        return summary
