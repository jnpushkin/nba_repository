"""
Main entry point for the NBA Stats Processor.
"""

import os
import sys
import json
import argparse
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils.constants import BASE_DIR, DEFAULT_INPUT_DIR, CACHE_DIR, DEFAULT_HTML_OUTPUT, SURGE_DOMAIN


def deploy_to_surge(output_html: str) -> bool:
    """
    Deploy the website to Surge.

    Args:
        output_html: Path to the generated HTML file

    Returns:
        True if deployment succeeded, False otherwise
    """
    from .utils.log import info, warn, success

    docs_dir = os.path.dirname(output_html)
    if not docs_dir:
        docs_dir = '.'

    info(f"Deploying to {SURGE_DOMAIN}...")

    try:
        result = subprocess.run(
            ['surge', docs_dir, SURGE_DOMAIN],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            success(f"Deployed to https://{SURGE_DOMAIN}")
            return True
        else:
            warn(f"Deployment failed: {result.stderr}")
            return False

    except FileNotFoundError:
        warn("Surge CLI not found. Install with: npm install -g surge")
        return False
    except subprocess.TimeoutExpired:
        warn("Deployment timed out")
        return False
    except Exception as e:
        warn(f"Deployment error: {e}")
        return False
from .utils.log import info, warn, error, success, debug, set_verbosity, set_use_emoji
from .parsers.html_parser import parse_basketball_reference_boxscore, HTMLParsingError


def process_html_file(file_path: str) -> Dict[str, Any]:
    """
    Process a single Basketball Reference HTML file.

    Args:
        file_path: Path to HTML file

    Returns:
        Parsed game data dictionary or error dict
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        game_data = parse_basketball_reference_boxscore(html_content)
        game_id = game_data.get("game_id", "UNKNOWN")
        debug(f"  Parsed game: {game_id}")

        # Report any parsing warnings
        warnings = game_data.get('_parsing_warnings', [])
        if warnings:
            for warning in warnings:
                warn(f"  {os.path.basename(file_path)}: {warning}")

        # Cache the parsed data
        if game_id != 'UNKNOWN':
            cache_path = CACHE_DIR / f"{game_id}.json"
            with open(cache_path, 'w', encoding='utf-8') as cf:
                json.dump(game_data, cf, indent=2)

        return game_data

    except HTMLParsingError as e:
        error(f"Invalid HTML in {file_path}: {e}")
        return {"_error": True, "file": file_path, "error": str(e)}
    except Exception as e:
        from .utils.log import exception
        exception(f"Error processing {file_path}", e)
        return {"_error": True, "file": file_path, "error": str(e)}


def process_json_file(file_path: str) -> Dict[str, Any]:
    """
    Process a single JSON game file (cached data).

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed game data dictionary or error dict
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)

        game_id = game_data.get("game_id", "UNKNOWN")
        debug(f"  Loaded game: {game_id}")

        return game_data

    except json.JSONDecodeError as e:
        error(f"Invalid JSON in {file_path}: {e}")
        return {"_error": True, "file": file_path, "error": str(e)}
    except Exception as e:
        from .utils.log import exception
        exception(f"Error processing {file_path}", e)
        return {"_error": True, "file": file_path, "error": str(e)}


def process_directory_or_file(input_path: str) -> List[Dict[str, Any]]:
    """
    Process game files from directory or single file.

    Args:
        input_path: Path to file or directory

    Returns:
        List of parsed game dictionaries
    """
    all_games_data = []
    failed_files = []

    if os.path.isfile(input_path):
        if input_path.endswith('.html'):
            game_data = process_html_file(input_path)
            if game_data:
                if game_data.get("_error"):
                    failed_files.append(game_data)
                else:
                    all_games_data.append(game_data)
        elif input_path.endswith('.json'):
            game_data = process_json_file(input_path)
            if game_data:
                if game_data.get("_error"):
                    failed_files.append(game_data)
                else:
                    all_games_data.append(game_data)
        else:
            warn(f"File must be an HTML or JSON file: {input_path}")

    elif os.path.isdir(input_path):
        # Process HTML files first, then JSON
        html_files = [f for f in os.listdir(input_path) if f.endswith('.html')]
        json_files = [f for f in os.listdir(input_path) if f.endswith('.json')]

        total_html = len(html_files)
        total_json = len(json_files)

        if total_html > 0:
            info(f"Processing {total_html} HTML files...")
            for idx, filename in enumerate(html_files, start=1):
                file_path = os.path.join(input_path, filename)
                game_data = process_html_file(file_path)
                if game_data:
                    if game_data.get("_error"):
                        failed_files.append(game_data)
                    else:
                        all_games_data.append(game_data)

                if idx == total_html or (total_html >= 10 and idx % max(1, total_html // 10) == 0):
                    pct = idx * 100 // total_html
                    debug(f"  Progress: {idx}/{total_html} ({pct}%)")

        if total_json > 0 and total_html == 0:
            # Only process JSON if no HTML files found
            info(f"Processing {total_json} JSON files...")
            for idx, filename in enumerate(json_files, start=1):
                file_path = os.path.join(input_path, filename)
                game_data = process_json_file(file_path)
                if game_data:
                    if game_data.get("_error"):
                        failed_files.append(game_data)
                    else:
                        all_games_data.append(game_data)

                if idx == total_json or (total_json >= 10 and idx % max(1, total_json // 10) == 0):
                    pct = idx * 100 // total_json
                    debug(f"  Progress: {idx}/{total_json} ({pct}%)")
    else:
        warn(f"Invalid path: {input_path}")
        return []

    info(f"Loaded {len(all_games_data)} games")

    if failed_files:
        warn(f"\nFailed to process {len(failed_files)} file(s):")
        for failed in failed_files:
            file_name = os.path.basename(failed["file"])
            error_msg = failed["error"]
            warn(f"   {file_name}: {error_msg}")

    return all_games_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NBA Game Processor - Parse game data and generate statistics"
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        default=str(DEFAULT_INPUT_DIR),
        help='Directory containing JSON files or single JSON file'
    )
    parser.add_argument(
        '--output-excel',
        default=str(BASE_DIR / 'NBA_Stats.xlsx'),
        help='Excel output filename'
    )
    parser.add_argument(
        '--output-html',
        default=str(DEFAULT_HTML_OUTPUT),
        help='HTML website output filename'
    )
    parser.add_argument(
        '--game-type',
        choices=['regular', 'playoff', 'playin', 'all'],
        default='all',
        help='Filter by game type'
    )
    parser.add_argument(
        '--save-json',
        action='store_true',
        help='Save intermediate JSON data file'
    )
    parser.add_argument(
        '--from-cache-only',
        action='store_true',
        help='Load all games from cached JSON files'
    )
    parser.add_argument(
        '--excel-only',
        action='store_true',
        help='Generate only Excel workbook, skip website generation'
    )
    parser.add_argument(
        '--website-only',
        action='store_true',
        help='Generate only website, skip Excel workbook'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable extra debug output'
    )
    parser.add_argument(
        '--no-emoji',
        action='store_true',
        help='Disable emoji in console output'
    )
    parser.add_argument(
        '--no-deploy',
        action='store_true',
        help='Skip automatic surge deployment'
    )
    parser.add_argument(
        '--scrape-firsts',
        action='store_true',
        help='Scrape career firsts for new players (not already cached)'
    )
    parser.add_argument(
        '--scrape-pbp',
        action='store_true',
        help='Scrape ESPN play-by-play data for games'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Write logs to file'
    )

    args = parser.parse_args()

    # Configure logging
    set_verbosity(args.verbose)
    set_use_emoji(not args.no_emoji)
    if args.log_file:
        from .utils.log import set_log_file
        set_log_file(args.log_file)
        info(f"Logging to file: {args.log_file}")

    # Validate flags
    if args.excel_only and args.website_only:
        warn("Error: Cannot use both --excel-only and --website-only flags")
        return

    if not os.path.exists(args.input_path) and not args.from_cache_only:
        warn(f"Input path does not exist: {args.input_path}")
        return

    info("Starting NBA Game Processor...")
    info(f"Input: {args.input_path}")

    if not args.website_only:
        info(f"Output Excel: {args.output_excel}")
        args.output_excel = os.path.expanduser(args.output_excel)

    # Load game data
    if args.from_cache_only:
        info("Loading games from cache only...")
        games_data = []
        skip_files = {'metadata.json', 'config.json'}
        for file in CACHE_DIR.glob("*.json"):
            if file.name in skip_files:
                continue
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    game = json.load(f)
                basic_info = game.get('basic_info')
                if not basic_info or not isinstance(basic_info, dict):
                    continue
                if not basic_info.get('home_team') or not basic_info.get('away_team'):
                    continue
                games_data.append(game)
            except (json.JSONDecodeError, Exception):
                continue
    else:
        games_data = process_directory_or_file(args.input_path)

    if not games_data:
        warn("No games data to process. Exiting.")
        return

    # Filter by game type if specified
    if args.game_type != 'all':
        games_data = [
            g for g in games_data
            if g.get('basic_info', {}).get('game_type', 'regular') == args.game_type
        ]
        info(f"Filtered to {len(games_data)} {args.game_type} games")

    # Save intermediate JSON
    if args.save_json:
        json_output = os.path.join(os.path.dirname(args.output_excel), "all_games_data.json")
        with open(json_output, 'w', encoding='utf-8') as json_file:
            json.dump(games_data, json_file, indent=2)
        info(f"JSON data saved to {json_output}")

    # Determine what to generate
    generate_excel = not args.website_only
    generate_website = not args.excel_only

    # Generate outputs
    try:
        from .processors.player_stats_processor import PlayerStatsProcessor

        info(f"\nProcessing {len(games_data)} games...")

        # Process player stats
        player_processor = PlayerStatsProcessor(games_data)
        player_data = player_processor.process_all_player_stats()

        if generate_excel:
            # Remove existing Excel file
            if os.path.exists(args.output_excel):
                debug(f"Removing existing file: {args.output_excel}")
                os.remove(args.output_excel)

            # Generate Excel workbook
            try:
                from .excel.workbook_generator import generate_excel_workbook
                generate_excel_workbook(player_data, args.output_excel)
                info(f"Excel: {os.path.abspath(args.output_excel)}")
            except ImportError:
                warn("Excel generation not available (missing openpyxl or xlsxwriter)")
                # Fallback: save as CSV
                csv_dir = os.path.dirname(args.output_excel)
                for name, df in player_data.items():
                    csv_path = os.path.join(csv_dir, f"nba_{name}.csv")
                    df.to_csv(csv_path, index=False)
                    info(f"CSV: {csv_path}")

        # Run career firsts scraper if requested (before website generation)
        if args.scrape_firsts:
            try:
                from .scrapers.career_firsts_scraper import (
                    get_players_from_games,
                    load_career_firsts_cache,
                    save_career_firsts_cache,
                    scrape_career_firsts_for_players,
                    get_cache_path
                )
                info("\nScraping career firsts...")

                # Get all players and games from cache
                player_ids, player_names = get_players_from_games()
                cache = load_career_firsts_cache()

                # Track which games we've processed for career firsts
                processed_games = cache.get('_processed_games', set())
                if isinstance(processed_games, list):
                    processed_games = set(processed_games)

                # Get current game IDs from the data we just processed
                current_game_ids = {g.get('game_id') for g in games_data if g.get('game_id')}

                # Find new games (not yet processed for career firsts)
                new_game_ids = current_game_ids - processed_games

                if new_game_ids:
                    info(f"Found {len(new_game_ids)} new games to process")

                    # Get players who played in new games
                    players_to_refresh = set()
                    for game in games_data:
                        if game.get('game_id') in new_game_ids:
                            box_score = game.get('box_score', {})
                            for side in ['away', 'home']:
                                players = box_score.get(side, {}).get('players', [])
                                for p in players:
                                    if p.get('player_id'):
                                        players_to_refresh.add(p['player_id'])

                    # Also add any completely new players not in cache
                    new_players = player_ids - set(k for k in cache.keys() if not k.startswith('_'))
                    players_to_refresh.update(new_players)

                    if players_to_refresh:
                        info(f"Refreshing career firsts for {len(players_to_refresh)} players...")
                        scrape_career_firsts_for_players(
                            players_to_refresh,
                            refresh=True,  # Force refresh for players with new games
                            delay=3.1,
                            verbose=True,
                            player_names=player_names
                        )

                    # Update processed games
                    cache = load_career_firsts_cache()  # Reload after scraping
                    cache['_processed_games'] = list(current_game_ids)
                    save_career_firsts_cache(cache)
                else:
                    info("No new games to process for career firsts")

            except ImportError as e:
                warn(f"Career firsts scraper not available: {e}")
            except Exception as e:
                warn(f"Career firsts scraping failed: {e}")

        # Scrape ESPN play-by-play data if requested
        if args.scrape_pbp:
            try:
                from .scrapers.espn_pbp_scraper import get_espn_pbp_for_game
                from .engines.espn_pbp_engine import ESPNPlayByPlayEngine
                info("\nScraping ESPN play-by-play data...")

                pbp_count = 0
                for game in games_data:
                    basic_info = game.get('basic_info', {})
                    away_team = basic_info.get('away_team', '')
                    home_team = basic_info.get('home_team', '')
                    date_str = basic_info.get('date_yyyymmdd', '')

                    if not away_team or not home_team or not date_str:
                        continue

                    # Skip if already has PBP analysis
                    if game.get('espn_pbp_analysis'):
                        pbp_count += 1
                        continue

                    espn_pbp = get_espn_pbp_for_game(
                        away_team, home_team, date_str, verbose=args.verbose
                    )
                    if espn_pbp and espn_pbp.get('plays'):
                        engine = ESPNPlayByPlayEngine(espn_pbp, game)
                        game['espn_pbp_analysis'] = engine.analyze()
                        pbp_count += 1

                        # Update cache with PBP analysis
                        game_id = game.get('game_id', '')
                        if game_id:
                            cache_path = CACHE_DIR / f"{game_id}.json"
                            if cache_path.exists():
                                try:
                                    with open(cache_path, 'r') as f:
                                        cached = json.load(f)
                                    cached['espn_pbp_analysis'] = game['espn_pbp_analysis']
                                    with open(cache_path, 'w') as f:
                                        json.dump(cached, f, indent=2)
                                except (json.JSONDecodeError, IOError):
                                    pass

                info(f"  ESPN PBP data for {pbp_count}/{len(games_data)} games")

            except ImportError as e:
                warn(f"ESPN PBP scraper not available: {e}")
            except Exception as e:
                warn(f"ESPN PBP scraping failed: {e}")

        if generate_website:
            try:
                from .website.generator import generate_website_from_data
                generate_website_from_data(player_data, args.output_html, games_data=games_data)
                info(f"Website: {os.path.abspath(args.output_html)}")

                # Deploy to Surge unless --no-deploy flag is set
                if not args.no_deploy:
                    deploy_to_surge(args.output_html)

            except ImportError:
                warn("Website generation not available")

        success("\nProcessing complete!")

    except Exception as e:
        from .utils.log import exception
        exception("Error during processing", e)


if __name__ == '__main__':
    main()
