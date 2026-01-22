"""
Website generator for interactive NBA stats HTML output with travel tracking.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Set
import pandas as pd

from ..utils.log import info
from ..utils.constants import EXCEL_COLORS, NBA_ARENAS, NBA_TEAMS, TEAM_CODES


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

    # Build games summary (one row per game, not per player)
    games_df = processed_data.get('player_games', pd.DataFrame())
    data['games'] = _build_games_summary(games_df)

    # Calculate venue/travel stats
    venue_stats = _calculate_venue_stats(games_df)
    data['venues'] = venue_stats['venues']

    # Calculate summary stats
    players_df = processed_data.get('players', pd.DataFrame())

    summary = {
        'totalPlayers': len(players_df) if not players_df.empty else 0,
        'totalGames': len(data['games']),
        'totalPoints': int(players_df['Total PTS'].sum()) if not players_df.empty and 'Total PTS' in players_df.columns else 0,
        'tripleDoubles': len(processed_data.get('triple_doubles', pd.DataFrame())),
        'doubleDoubles': len(processed_data.get('double_doubles', pd.DataFrame())),
        'arenasVisited': venue_stats['arenas_visited'],
        'totalArenas': 30,
        'statesVisited': venue_stats['states_visited'],
        'citiesVisited': venue_stats['cities_visited'],
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


def _build_games_summary(games_df: pd.DataFrame) -> List[Dict]:
    """Build one row per game with aggregated info."""
    if games_df.empty:
        return []

    games = []
    if 'game_id' not in games_df.columns:
        return []

    for game_id, group in games_df.groupby('game_id'):
        first = group.iloc[0]
        games.append({
            'game_id': game_id,
            'date': first.get('date', ''),
            'team': first.get('team', ''),
            'opponent': first.get('opponent', ''),
            'result': first.get('result', ''),
            'players': len(group),
        })

    # Sort by date descending
    games.sort(key=lambda x: x.get('date', ''), reverse=True)
    return games


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
        <div class="stats-overview">
            <div class="stat-box">
                <div class="icon">&#127936;</div>
                <div class="number">{summary.get('totalGames', 0)}</div>
                <div class="label">Games</div>
            </div>
            <div class="stat-box">
                <div class="icon">&#128101;</div>
                <div class="number">{summary.get('totalPlayers', 0)}</div>
                <div class="label">Players</div>
            </div>
            <div class="stat-box highlight">
                <div class="icon">&#127967;</div>
                <div class="number">{summary.get('arenasVisited', 0)}/30</div>
                <div class="label">Arenas</div>
            </div>
            <div class="stat-box">
                <div class="icon">&#127758;</div>
                <div class="number">{summary.get('statesVisited', 0)}</div>
                <div class="label">States</div>
            </div>
            <div class="stat-box">
                <div class="icon">&#11088;</div>
                <div class="number">{summary.get('tripleDoubles', 0)}</div>
                <div class="label">Triple-Dbl</div>
            </div>
        </div>
    </header>

    <div class="container">
        <nav class="tabs">
            <button class="tab active" onclick="showSection('games')" data-section="games">Games</button>
            <button class="tab" onclick="showSection('players')" data-section="players">Players</button>
            <button class="tab" onclick="showSection('venues')" data-section="venues">Venues</button>
            <button class="tab" onclick="showSection('map')" data-section="map">Arena Map</button>
            <button class="tab" onclick="showSection('achievements')" data-section="achievements">Achievements</button>
        </nav>

        <!-- Games Section -->
        <div id="games" class="section active">
            <h2>Games Attended</h2>
            <div class="games-grid" id="games-grid"></div>
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
            <h2>Achievements</h2>
            <div class="achievements-grid">
                <div class="sub-section">
                    <h3>Triple-Doubles ({summary.get('tripleDoubles', 0)})</h3>
                    <div class="table-container"><table id="triple-doubles-table"><thead></thead><tbody></tbody></table></div>
                </div>
                <div class="sub-section">
                    <h3>Double-Doubles ({summary.get('doubleDoubles', 0)})</h3>
                    <div class="table-container"><table id="double-doubles-table"><thead></thead><tbody></tbody></table></div>
                </div>
            </div>
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


def _get_css() -> str:
    return '''
:root {
    --bg-primary: #f5f5f5;
    --bg-secondary: #ffffff;
    --bg-header: linear-gradient(135deg, #1D428A 0%, #C8102E 100%);
    --text-primary: #333333;
    --text-secondary: #666666;
    --text-muted: #999999;
    --border-color: #e0e0e0;
    --accent-color: #1D428A;
    --hover-color: #f8f9fa;
    --shadow: 0 4px 6px rgba(0,0,0,0.1);
    --success: #27ae60;
}

[data-theme="dark"] {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-header: linear-gradient(135deg, #0f3460, #1a1a2e);
    --text-primary: #eaeaea;
    --text-secondary: #b0b0b0;
    --text-muted: #777777;
    --border-color: #2a2a4a;
    --accent-color: #4a9eff;
    --hover-color: #1e2a4a;
    --shadow: 0 4px 6px rgba(0,0,0,0.3);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
}

.header {
    background: var(--bg-header);
    color: white;
    padding: 2rem;
    text-align: center;
    position: relative;
}
.header h1 { font-size: 2rem; margin-bottom: 0.25rem; }
.header-subtitle { font-size: 0.9rem; opacity: 0.8; margin-bottom: 1.5rem; }
.header-controls { position: absolute; top: 1rem; right: 1rem; }
.theme-toggle {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 10px;
    width: 40px; height: 40px;
    cursor: pointer;
    font-size: 1.1rem;
    color: white;
}

.stats-overview { display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap; }
.stat-box {
    background: rgba(255,255,255,0.1);
    padding: 0.75rem 1.25rem;
    border-radius: 12px;
    text-align: center;
    min-width: 90px;
}
.stat-box .icon { font-size: 1.1rem; margin-bottom: 0.2rem; }
.stat-box .number { font-size: 1.5rem; font-weight: 700; }
.stat-box .label { font-size: 0.65rem; opacity: 0.8; text-transform: uppercase; }
.stat-box.highlight .number { color: #ffd700; }

.container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }

.tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; justify-content: center; }
.tab {
    padding: 0.6rem 1.2rem;
    background: var(--bg-secondary);
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.95rem;
    color: var(--text-primary);
    box-shadow: var(--shadow);
}
.tab:hover { background: var(--hover-color); }
.tab.active { background: var(--accent-color); color: white; }

.section {
    display: none;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--shadow);
}
.section.active { display: block; }
.section h2 {
    margin-bottom: 1rem;
    color: var(--accent-color);
    border-bottom: 2px solid var(--accent-color);
    padding-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Games Grid */
.games-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
}
.game-card {
    background: var(--bg-primary);
    border-radius: 10px;
    padding: 1.25rem;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    border-left: 4px solid var(--accent-color);
}
.game-card:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.game-card-date { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem; }
.game-card-teams { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; }
.game-card-result { font-size: 0.9rem; color: var(--text-secondary); }
.game-card-result .win { color: var(--success); font-weight: 600; }
.game-card-result .loss { color: #e74c3c; font-weight: 600; }

/* Filters */
.filters {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    align-items: flex-end;
    padding: 1rem;
    background: var(--bg-primary);
    border-radius: 8px;
}
.filter-group { display: flex; flex-direction: column; gap: 0.25rem; }
.filter-group label { font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; }
.filter-group input, .filter-group select {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    min-width: 120px;
}
.clear-filters {
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
    color: var(--text-secondary);
}
.btn { padding: 0.5rem 1rem; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-secondary { background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); }
.section-actions { display: flex; gap: 0.5rem; }

/* Tables */
.table-container { overflow-x: auto; max-height: 600px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.6rem; text-align: left; border-bottom: 1px solid var(--border-color); }
th {
    background: var(--bg-primary);
    font-weight: 600;
    position: sticky;
    top: 0;
    cursor: pointer;
    white-space: nowrap;
    z-index: 10;
}
th:hover { background: var(--hover-color); }
tr:hover { background: var(--hover-color); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.player-link { color: var(--accent-color); cursor: pointer; text-decoration: underline; }

/* Arena Progress */
.arena-progress { margin-bottom: 1.5rem; text-align: center; }
.progress-bar { background: var(--bg-primary); border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 0.5rem; }
.progress-fill { background: linear-gradient(90deg, #27ae60, #2ecc71); height: 100%; border-radius: 10px; }
.progress-text { font-size: 1rem; font-weight: 600; }
.status-visited { color: var(--success); font-weight: 600; }
.status-not-visited { color: var(--text-muted); }

/* Map */
#arena-map { height: 500px; border-radius: 8px; border: 1px solid var(--border-color); }
.map-legend { display: flex; gap: 1.5rem; margin-bottom: 1rem; justify-content: center; }
.legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
.legend-dot { width: 16px; height: 16px; border-radius: 50%; }
.legend-dot.visited { background: #27ae60; }
.legend-dot.not-visited { background: #95a5a6; }

/* Achievements */
.achievements-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; }
.sub-section h3 { font-size: 1.1rem; margin-bottom: 0.75rem; color: var(--accent-color); }

/* Modals */
.modal {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    justify-content: center;
    align-items: center;
}
.modal.active { display: flex; }
.modal-content {
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 700px;
    max-height: 85vh;
    overflow-y: auto;
    width: 95%;
    position: relative;
}
.modal-content.modal-large { max-width: 1000px; }
.modal-close {
    position: absolute;
    top: 1rem; right: 1rem;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-secondary);
}

/* Box Score */
.boxscore-header { text-align: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid var(--border-color); }
.boxscore-header h2 { font-size: 1.4rem; margin-bottom: 0.25rem; }
.boxscore-header .date { color: var(--text-secondary); }
.boxscore-header .result { font-size: 1.2rem; font-weight: 600; margin-top: 0.5rem; }
.boxscore-section { margin-bottom: 1.5rem; }
.boxscore-section h4 { margin-bottom: 0.5rem; color: var(--accent-color); }

.toast {
    position: fixed;
    bottom: 2rem; right: 2rem;
    background: var(--text-primary);
    color: var(--bg-secondary);
    padding: 1rem 1.5rem;
    border-radius: 8px;
    transform: translateY(100px);
    opacity: 0;
    transition: all 0.3s;
    z-index: 2000;
}
.toast.show { transform: translateY(0); opacity: 1; }

footer { text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.8rem; }

@media (max-width: 768px) {
    .header { padding: 1.5rem 1rem; }
    .header h1 { font-size: 1.5rem; }
    .stats-overview { gap: 0.5rem; }
    .stat-box { padding: 0.5rem 0.75rem; min-width: 70px; }
    .stat-box .number { font-size: 1.25rem; }
    .container { padding: 1rem; }
    .games-grid { grid-template-columns: 1fr; }
    .achievements-grid { grid-template-columns: 1fr; }
    #arena-map { height: 350px; }
}
    '''


def _get_javascript() -> str:
    return '''
let arenaMap = null;
let filteredPlayers = [];

// Theme
function toggleTheme() {
    const html = document.documentElement;
    const newTheme = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    if (arenaMap) setTimeout(() => arenaMap.invalidateSize(), 100);
}
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
    else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
        document.documentElement.setAttribute('data-theme', 'dark');
})();

// Sections
function showSection(id) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelector(`[data-section="${id}"]`).classList.add('active');
    document.getElementById(id).classList.add('active');
    if (id === 'map' && !arenaMap) initMap();
}

// Modals
function openModal(id) { document.getElementById(id).classList.add('active'); document.body.style.overflow = 'hidden'; }
function closeModal(id) { document.getElementById(id).classList.remove('active'); document.body.style.overflow = ''; }
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// Games Grid
function renderGamesGrid() {
    const games = DATA.games || [];
    const grid = document.getElementById('games-grid');

    if (!games.length) {
        grid.innerHTML = '<p style="text-align:center;padding:2rem;color:var(--text-muted);">No games found</p>';
        return;
    }

    grid.innerHTML = games.map((g, i) => {
        const resultClass = g.result && g.result.toLowerCase().startsWith('w') ? 'win' : 'loss';
        return `
        <div class="game-card" onclick="showBoxScore('${g.game_id}')">
            <div class="game-card-date">${g.date}</div>
            <div class="game-card-teams">${g.team} vs ${g.opponent}</div>
            <div class="game-card-result"><span class="${resultClass}">${g.result || ''}</span></div>
        </div>`;
    }).join('');
}

// Box Score Modal
function showBoxScore(gameId) {
    const playerGames = (DATA.player_games || []).filter(p => p.game_id === gameId);
    const gameInfo = (DATA.games || []).find(g => g.game_id === gameId);

    if (!playerGames.length) { showToast('No box score data'); return; }

    const detail = document.getElementById('boxscore-detail');

    let html = `
    <div class="boxscore-header">
        <h2>${gameInfo?.team || ''} vs ${gameInfo?.opponent || ''}</h2>
        <div class="date">${gameInfo?.date || ''}</div>
        <div class="result">${gameInfo?.result || ''}</div>
    </div>
    <div class="boxscore-section">
        <h4>Box Score (${playerGames.length} players)</h4>
        <div class="table-container">
            <table>
                <thead><tr>
                    <th>Player</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th>
                    <th>STL</th><th>BLK</th><th>TO</th><th>FG</th><th>3P</th><th>FT</th><th>+/-</th>
                </tr></thead>
                <tbody>`;

    playerGames.forEach(p => {
        html += `<tr>
            <td><span class="player-link" onclick="event.stopPropagation();showPlayerDetail('${p.player}')">${p.player}</span></td>
            <td class="num">${p.mp || '-'}</td>
            <td class="num">${p.pts || 0}</td>
            <td class="num">${p.trb || 0}</td>
            <td class="num">${p.ast || 0}</td>
            <td class="num">${p.stl || 0}</td>
            <td class="num">${p.blk || 0}</td>
            <td class="num">${p.tov || 0}</td>
            <td class="num">${p.fg || 0}-${p.fga || 0}</td>
            <td class="num">${p.fg3 || 0}-${p.fg3a || 0}</td>
            <td class="num">${p.ft || 0}-${p.fta || 0}</td>
            <td class="num">${p.plus_minus || 0}</td>
        </tr>`;
    });

    html += '</tbody></table></div></div>';
    detail.innerHTML = html;
    openModal('boxscore-modal');
}

// Players Table
const playerCols = [
    'Player', 'Team', 'Games', 'MPG', 'PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TOPG',
    'FG%', '3P%', 'FT%', 'TS%', 'eFG%', 'Total PTS', 'Total REB', 'Total AST'
];

function renderPlayersTable() {
    const table = document.getElementById('players-table');
    const data = filteredPlayers;

    if (!data || !data.length) {
        table.innerHTML = '<tr><td colspan="20" style="text-align:center;padding:2rem;">No players</td></tr>';
        return;
    }

    let html = '<thead><tr>' + playerCols.map(c => `<th onclick="sortPlayersTable('${c}')">${c}</th>`).join('') + '</tr></thead><tbody>';
    data.forEach(row => {
        html += '<tr>';
        playerCols.forEach(col => {
            let v = row[col];
            if (v == null) v = '';
            if (typeof v === 'number') {
                v = Number.isInteger(v) ? v : v.toFixed(col.includes('%') ? 3 : 1);
                html += `<td class="num">${v}</td>`;
            } else if (col === 'Player') {
                html += `<td><span class="player-link" onclick="showPlayerDetail('${v}')">${v}</span></td>`;
            } else {
                html += `<td>${v}</td>`;
            }
        });
        html += '</tr>';
    });
    table.innerHTML = html + '</tbody>';
}

function sortPlayersTable(col) {
    filteredPlayers.sort((a, b) => {
        let av = a[col], bv = b[col];
        if (av == null) av = '';
        if (bv == null) bv = '';
        if (typeof av === 'number' && typeof bv === 'number') return bv - av;
        return String(av).localeCompare(String(bv));
    });
    renderPlayersTable();
}

function filterPlayersTable() {
    const search = document.getElementById('players-search').value.toLowerCase();
    const team = document.getElementById('players-team').value;
    const minG = parseInt(document.getElementById('players-min-games').value) || 0;

    filteredPlayers = (DATA.players || []).filter(p => {
        if (search && !Object.values(p).some(v => String(v).toLowerCase().includes(search))) return false;
        if (team && !String(p.Team || '').includes(team)) return false;
        if (minG && (p.Games || 0) < minG) return false;
        return true;
    });
    renderPlayersTable();
}

function clearPlayersFilters() {
    document.getElementById('players-search').value = '';
    document.getElementById('players-team').value = '';
    document.getElementById('players-min-games').value = '';
    filterPlayersTable();
}

function populateTeamDropdown() {
    const teams = new Set();
    (DATA.players || []).forEach(p => { if (p.Team) p.Team.split(', ').forEach(t => teams.add(t)); });
    const sel = document.getElementById('players-team');
    Array.from(teams).sort().forEach(t => {
        const o = document.createElement('option'); o.value = t; o.textContent = t; sel.appendChild(o);
    });
}

// Player Detail
function showPlayerDetail(name) {
    const games = (DATA.player_games || []).filter(g => g.player === name);
    const stats = (DATA.players || []).find(p => p.Player === name);

    if (!stats && !games.length) { showToast('Player not found'); return; }

    let html = `<h2>${name}</h2>`;
    if (stats) {
        html += `<p style="color:var(--text-secondary);margin-bottom:1rem;">${stats.Team || ''} | ${stats.Games || 0} games</p>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1.5rem;">
            <div class="stat-box" style="background:var(--bg-primary);"><div class="number">${(stats.PPG||0).toFixed(1)}</div><div class="label">PPG</div></div>
            <div class="stat-box" style="background:var(--bg-primary);"><div class="number">${(stats.RPG||0).toFixed(1)}</div><div class="label">RPG</div></div>
            <div class="stat-box" style="background:var(--bg-primary);"><div class="number">${(stats.APG||0).toFixed(1)}</div><div class="label">APG</div></div>
            <div class="stat-box" style="background:var(--bg-primary);"><div class="number">${(stats.MPG||0).toFixed(1)}</div><div class="label">MPG</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1.5rem;">
            <div style="text-align:center;"><strong>${((stats['FG%']||0)*100).toFixed(1)}%</strong><br><small>FG%</small></div>
            <div style="text-align:center;"><strong>${((stats['3P%']||0)*100).toFixed(1)}%</strong><br><small>3P%</small></div>
            <div style="text-align:center;"><strong>${((stats['FT%']||0)*100).toFixed(1)}%</strong><br><small>FT%</small></div>
        </div>`;
    }
    if (games.length) {
        html += '<h4 style="margin-bottom:0.5rem;">Game Log</h4><div class="table-container"><table><thead><tr><th>Date</th><th>Opp</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>FG</th><th>+/-</th></tr></thead><tbody>';
        games.forEach(g => html += `<tr><td>${g.date||''}</td><td>${g.opponent||''}</td><td>${g.mp||'-'}</td><td>${g.pts||0}</td><td>${g.trb||0}</td><td>${g.ast||0}</td><td>${g.stl||0}</td><td>${g.blk||0}</td><td>${g.fg||0}-${g.fga||0}</td><td>${g.plus_minus||0}</td></tr>`);
        html += '</tbody></table></div>';
    }
    document.getElementById('player-detail').innerHTML = html;
    openModal('player-modal');
}

// Venues
function renderVenuesTable() {
    const venues = DATA.venues || [];
    const visited = venues.filter(v => v.visited).length;
    document.getElementById('arena-progress-fill').style.width = `${(visited/30)*100}%`;
    document.getElementById('arena-progress-text').textContent = `${visited}/30 Arenas Visited`;
    filterVenuesTable();
}

function filterVenuesTable() {
    const filter = document.getElementById('venues-filter').value;
    let venues = DATA.venues || [];
    if (filter === 'visited') venues = venues.filter(v => v.visited);
    else if (filter === 'unvisited') venues = venues.filter(v => !v.visited);

    const tbody = document.querySelector('#venues-table tbody');
    tbody.innerHTML = venues.map(v => `
        <tr>
            <td>${v.team}</td>
            <td>${v.name}</td>
            <td>${v.city}</td>
            <td>${v.state}</td>
            <td class="num">${v.games}</td>
            <td>${v.first_visit || '-'}</td>
            <td class="${v.visited ? 'status-visited' : 'status-not-visited'}">${v.visited ? '✓ Visited' : 'Not Yet'}</td>
        </tr>
    `).join('');
}

// Map
function initMap() {
    arenaMap = L.map('arena-map').setView([39.8, -98.5], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(arenaMap);
    (DATA.venues || []).forEach(v => {
        const color = v.visited ? '#27ae60' : '#95a5a6';
        L.circleMarker([v.lat, v.lng], { radius: 10, fillColor: color, color: '#fff', weight: 2, fillOpacity: 0.9 })
            .addTo(arenaMap)
            .bindPopup(`<strong>${v.team}</strong><br>${v.name}<br>${v.city}, ${v.state}<br><em>${v.visited ? v.games + ' games' : 'Not visited'}</em>`);
    });
}

// Achievements
function renderAchievements() {
    const tdCols = ['date','player','team','opponent','result','pts','trb','ast','stl','blk'];
    const ddCols = ['date','player','team','opponent','result','pts','trb','ast'];
    renderSimpleTable('triple-doubles-table', DATA.triple_doubles, tdCols);
    renderSimpleTable('double-doubles-table', DATA.double_doubles, ddCols);
}

function renderSimpleTable(tableId, data, cols) {
    const table = document.getElementById(tableId);
    if (!data || !data.length) {
        table.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:1rem;color:var(--text-muted);">None recorded</td></tr>';
        return;
    }
    let html = '<thead><tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
    data.forEach(row => {
        html += '<tr>';
        cols.forEach(col => {
            let v = row[col]; if (v == null) v = '';
            html += typeof v === 'number' ? `<td class="num">${v}</td>` : `<td>${v}</td>`;
        });
        html += '</tr>';
    });
    table.innerHTML = html + '</tbody>';
}

// CSV Download
function downloadCSV(type) {
    const data = type === 'players' ? filteredPlayers : null;
    if (!data || !data.length) { showToast('No data'); return; }
    const headers = playerCols;
    const csv = [headers.join(','), ...data.map(r => headers.map(h => {
        let v = r[h]; if (v == null) v = '';
        if (typeof v === 'string' && (v.includes(',') || v.includes('"'))) v = '"' + v.replace(/"/g, '""') + '"';
        return v;
    }).join(','))].join('\\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = 'nba_players.csv'; a.click();
    showToast('Download started');
}

// Init
document.addEventListener('DOMContentLoaded', function() {
    renderGamesGrid();
    populateTeamDropdown();
    filteredPlayers = DATA.players ? [...DATA.players] : [];
    renderPlayersTable();
    renderVenuesTable();
    renderAchievements();
});

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.active').forEach(m => closeModal(m.id));
});
    '''
