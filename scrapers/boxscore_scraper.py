"""
Basketball Reference box score scraper with rate limiting.
"""

import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from pathlib import Path

import cloudscraper

from ..utils.constants import BASE_DIR, NBA_TEAMS, TEAM_CODES
from ..utils.log import info, warn, error, debug, success


# Rate limiting: Basketball Reference allows ~20 requests/minute
# Be conservative: 3-4 seconds between requests
MIN_DELAY = 3.0
MAX_DELAY = 5.0

# Base URL for box scores
BOXSCORE_URL = "https://www.basketball-reference.com/boxscores/{game_id}.html"
SCHEDULE_URL = "https://www.basketball-reference.com/leagues/NBA_{season}_games-{month}.html"


class BoxscoreScraper:
    """Scraper for Basketball Reference box scores."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize scraper.

        Args:
            output_dir: Directory to save HTML files (default: html_games)
        """
        self.output_dir = output_dir or (BASE_DIR / "html_games")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create cloudscraper session
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True,
            }
        )

        self.request_count = 0
        self.last_request_time = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self.last_request_time

        if elapsed < MIN_DELAY:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            sleep_time = delay - elapsed
            if sleep_time > 0:
                debug(f"  Rate limiting: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch a URL with rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on error
        """
        self._rate_limit()
        self.request_count += 1

        try:
            response = self.scraper.get(url, timeout=30)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                debug(f"  Not found: {url}")
                return None
            elif response.status_code == 429:
                warn(f"Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                return self._fetch_url(url)  # Retry
            else:
                warn(f"HTTP {response.status_code} for {url}")
                return None

        except Exception as e:
            error(f"Error fetching {url}: {e}")
            return None

    def download_game(self, date: str, home_team_code: str) -> Optional[str]:
        """
        Download a single game box score.

        Args:
            date: Date in YYYYMMDD format
            home_team_code: 3-letter home team code (e.g., 'GSW')

        Returns:
            Path to saved file or None on error
        """
        game_id = f"{date}0{home_team_code}"
        output_path = self.output_dir / f"{game_id}.html"

        # Skip if already downloaded
        if output_path.exists():
            debug(f"Already exists: {game_id}")
            return str(output_path)

        url = BOXSCORE_URL.format(game_id=game_id)

        html = self._fetch_url(url)
        if html:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            success(f"  Saved: {output_path.name}")
            return str(output_path)

        return None

    def download_games_for_team(
        self,
        team_code: str,
        start_date: str,
        end_date: str,
        home_only: bool = False
    ) -> List[str]:
        """
        Download all games for a team in a date range.

        Note: This downloads games where the team played at HOME.
        For away games, you'd need to know the opponent's home code.

        Args:
            team_code: 3-letter team code
            start_date: Start date YYYYMMDD
            end_date: End date YYYYMMDD
            home_only: If True, only download home games

        Returns:
            List of downloaded file paths
        """
        downloaded = []

        # Generate all dates in range
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')

        current = start
        while current <= end:
            date_str = current.strftime('%Y%m%d')
            result = self.download_game(date_str, team_code)
            if result:
                downloaded.append(result)
            current += timedelta(days=1)

        return downloaded

    def download_games_by_list(
        self,
        games: List[Tuple[str, str]]
    ) -> List[str]:
        """
        Download specific games by date and home team.

        Args:
            games: List of (date_YYYYMMDD, home_team_code) tuples

        Returns:
            List of downloaded file paths
        """
        downloaded = []

        total = len(games)
        for idx, (date, home_code) in enumerate(games, 1):
            info(f"[{idx}/{total}] Fetching {date}0{home_code}...")
            result = self.download_game(date, home_code)
            if result:
                downloaded.append(result)

        return downloaded

    def download_date_range(
        self,
        start_date: str,
        end_date: str,
        teams: Optional[List[str]] = None
    ) -> List[str]:
        """
        Download all games in a date range for specified teams.

        Args:
            start_date: Start date YYYYMMDD
            end_date: End date YYYYMMDD
            teams: List of team codes to download (default: all 30 teams)

        Returns:
            List of downloaded file paths
        """
        if teams is None:
            teams = list(TEAM_CODES.keys())

        downloaded = []

        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')

        current = start
        while current <= end:
            date_str = current.strftime('%Y%m%d')
            info(f"\nDate: {current.strftime('%B %d, %Y')}")

            for team_code in teams:
                result = self.download_game(date_str, team_code)
                if result:
                    downloaded.append(result)

            current += timedelta(days=1)

        return downloaded


def download_boxscores(
    games: Optional[List[Tuple[str, str]]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    teams: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> List[str]:
    """
    Convenience function to download box scores.

    Args:
        games: List of (date_YYYYMMDD, home_team_code) tuples
        start_date: Start date YYYYMMDD (used with end_date)
        end_date: End date YYYYMMDD (used with start_date)
        teams: Team codes to filter (default: all)
        output_dir: Output directory path

    Returns:
        List of downloaded file paths
    """
    output_path = Path(output_dir) if output_dir else None
    scraper = BoxscoreScraper(output_path)

    if games:
        return scraper.download_games_by_list(games)
    elif start_date and end_date:
        return scraper.download_date_range(start_date, end_date, teams)
    else:
        warn("Must provide either games list or start_date/end_date")
        return []


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download NBA box scores from Basketball Reference')
    parser.add_argument('--date', help='Single date YYYYMMDD')
    parser.add_argument('--start', help='Start date YYYYMMDD')
    parser.add_argument('--end', help='End date YYYYMMDD')
    parser.add_argument('--teams', nargs='+', help='Team codes (e.g., GSW LAL BOS)')
    parser.add_argument('--games', nargs='+', help='Specific games as DATE:TEAM (e.g., 20260119:GSW)')
    parser.add_argument('--output', help='Output directory')

    args = parser.parse_args()

    if args.games:
        # Parse games from DATE:TEAM format
        games = []
        for g in args.games:
            parts = g.split(':')
            if len(parts) == 2:
                games.append((parts[0], parts[1]))
        downloaded = download_boxscores(games=games, output_dir=args.output)
    elif args.date:
        # Single date, all specified teams (or all teams)
        downloaded = download_boxscores(
            start_date=args.date,
            end_date=args.date,
            teams=args.teams,
            output_dir=args.output
        )
    elif args.start and args.end:
        downloaded = download_boxscores(
            start_date=args.start,
            end_date=args.end,
            teams=args.teams,
            output_dir=args.output
        )
    else:
        parser.print_help()
        exit(1)

    info(f"\nDownloaded {len(downloaded)} box scores")
