# NBA Game Tracker

Track NBA games you've attended, with stats, milestones, and career firsts you witnessed.

## Setup

```bash
pip install -r requirements.txt
```

## Running the Processor

From the parent directory of `nba_processor`:

```bash
cd /path/to/parent
python3 -m nba_processor [options]
```

### Options

| Flag | Description |
|------|-------------|
| `--from-cache-only` | Use cached game data (skip HTML parsing) |
| `--website-only` | Generate only website, skip Excel |
| `--excel-only` | Generate only Excel, skip website |
| `--scrape-firsts` | Scrape career firsts for players in new games |
| `--no-deploy` | Skip automatic Surge deployment |
| `--verbose` | Enable debug output |

### Examples

```bash
# Process games and deploy website
python3 -m nba_processor --from-cache-only

# Process without deploying
python3 -m nba_processor --from-cache-only --no-deploy

# Process and scrape career firsts for new players
python3 -m nba_processor --from-cache-only --scrape-firsts
```

## Scraping Career Firsts

Scrape career milestone data from Basketball Reference:

```bash
# Scrape all players from your attended games
python3 -m nba_processor.scrapers.career_firsts_scraper

# Scrape a specific player
python3 -m nba_processor.scrapers.career_firsts_scraper --player curryst01

# Force refresh cached data
python3 -m nba_processor.scrapers.career_firsts_scraper --refresh

# Check witnessed career firsts
python3 -m nba_processor.scrapers.career_firsts_scraper --check-witnessed
```

**Note:** Basketball Reference rate limits requests. The scraper uses 3+ second delays between requests.

## Output

- **Website:** `docs/index.html` (auto-deploys to nba-processor.surge.sh)
- **Excel:** `NBA_Stats.xlsx`

## Project Structure

- `cache/` - Cached game data and career firsts
- `docs/` - Generated website
- `html_games/` - Raw HTML boxscores from Basketball Reference
- `engines/` - Milestone detection (55+ types)
- `parsers/` - HTML parsing
- `processors/` - Stats aggregation
- `scrapers/` - Web scrapers
- `website/` - Website generation
- `tests/` - Test suite
