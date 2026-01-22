"""NBA Processor data scrapers."""

from .boxscore_scraper import BoxscoreScraper, download_boxscores

__all__ = ['BoxscoreScraper', 'download_boxscores']
