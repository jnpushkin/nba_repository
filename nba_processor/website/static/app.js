// Auto-generated constants from Python
const TEAM_SHORT_NAMES = {"Boston Celtics": "Celtics", "Brooklyn Nets": "Nets", "New York Knicks": "Knicks", "Philadelphia 76ers": "76ers", "Toronto Raptors": "Raptors", "Chicago Bulls": "Bulls", "Cleveland Cavaliers": "Cavaliers", "Detroit Pistons": "Pistons", "Indiana Pacers": "Pacers", "Milwaukee Bucks": "Bucks", "Atlanta Hawks": "Hawks", "Charlotte Hornets": "Hornets", "Miami Heat": "Heat", "Orlando Magic": "Magic", "Washington Wizards": "Wizards", "Denver Nuggets": "Nuggets", "Minnesota Timberwolves": "Timberwolves", "Oklahoma City Thunder": "Thunder", "Portland Trail Blazers": "Trail Blazers", "Utah Jazz": "Jazz", "Golden State Warriors": "Warriors", "Los Angeles Clippers": "Clippers", "Los Angeles Lakers": "Lakers", "Phoenix Suns": "Suns", "Sacramento Kings": "Kings", "Dallas Mavericks": "Mavericks", "Houston Rockets": "Rockets", "Memphis Grizzlies": "Grizzlies", "New Orleans Pelicans": "Pelicans", "San Antonio Spurs": "Spurs"};
const TEAM_CODES = {"Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "New York Knicks": "NYK", "Philadelphia 76ers": "PHI", "Toronto Raptors": "TOR", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Detroit Pistons": "DET", "Indiana Pacers": "IND", "Milwaukee Bucks": "MIL", "Atlanta Hawks": "ATL", "Charlotte Hornets": "CHA", "Miami Heat": "MIA", "Orlando Magic": "ORL", "Washington Wizards": "WAS", "Denver Nuggets": "DEN", "Minnesota Timberwolves": "MIN", "Oklahoma City Thunder": "OKC", "Portland Trail Blazers": "POR", "Utah Jazz": "UTA", "Golden State Warriors": "GSW", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Phoenix Suns": "PHX", "Sacramento Kings": "SAC", "Dallas Mavericks": "DAL", "Houston Rockets": "HOU", "Memphis Grizzlies": "MEM", "New Orleans Pelicans": "NOP", "San Antonio Spurs": "SAS"};
const MILESTONE_CATEGORIES = {"multi": ["quadruple_doubles", "triple_doubles", "double_doubles", "near_triple_doubles", "near_double_doubles", "five_by_fives", "all_around_games"], "scoring": ["seventy_point_games", "sixty_point_games", "fifty_point_games", "forty_five_point_games", "forty_point_games", "thirty_five_point_games", "thirty_point_games", "twenty_five_point_games", "twenty_point_games"], "rebounding": ["twenty_five_rebound_games", "twenty_rebound_games", "eighteen_rebound_games", "fifteen_rebound_games", "twelve_rebound_games", "ten_rebound_games"], "assists": ["twenty_assist_games", "fifteen_assist_games", "twelve_assist_games", "ten_assist_games"], "steals": ["ten_steal_games", "seven_steal_games", "five_steal_games", "four_steal_games"], "blocks": ["ten_block_games", "seven_block_games", "five_block_games", "four_block_games"], "threes": ["ten_three_games", "eight_three_games", "seven_three_games", "six_three_games", "five_three_games", "perfect_from_three"], "efficiency": ["hot_shooting_games", "perfect_ft_games", "perfect_fg_games", "efficient_scoring_games", "high_game_score"], "combined": ["thirty_ten_games", "twenty_five_ten_games", "twenty_ten_games", "twenty_ten_five_games", "twenty_twenty_games", "points_assists_double_double"], "defensive": ["defensive_monster_games", "zero_turnover_games"], "plusminus": ["plus_25_games", "plus_20_games", "minus_25_games"]};

function getShortName(fullName) {
    return TEAM_SHORT_NAMES[fullName] || fullName;
}

function getTeamCode(fullName) {
    if (fullName && fullName.includes(', ')) {
        return fullName.split(', ').map(t => TEAM_CODES[t.trim()] || t.trim().slice(0,3).toUpperCase()).join(', ');
    }
    return TEAM_CODES[fullName] || fullName;
}

let arenaMap = null;
let filteredPlayers = [];
let playerSortCol = null;
let playerSortAsc = false;

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
        const awayTeam = getShortName(g.away_team) || g.away_team || 'Away';
        const homeTeam = getShortName(g.home_team) || g.home_team || 'Home';
        const awayScore = g.away_score || 0;
        const homeScore = g.home_score || 0;
        const gameType = g.game_type && g.game_type !== 'regular' ? `<span style="font-size:0.75rem;opacity:0.7;margin-left:0.5rem;">(${g.game_type})</span>` : '';

        // Format: "Away Team 105 @ Home Team 110" or show winner highlighted
        const awayWon = awayScore > homeScore;
        const awayClass = awayWon ? 'win' : '';
        const homeClass = !awayWon ? 'win' : '';

        return `
        <div class="game-card" onclick="showBoxScore('${g.game_id}')">
            <div class="game-card-date">${g.date}${gameType}</div>
            <div class="game-card-matchup">
                <span class="team-score ${awayClass}">${awayTeam} <strong>${awayScore}</strong></span>
                <span class="at-symbol">@</span>
                <span class="team-score ${homeClass}"><strong>${homeScore}</strong> ${homeTeam}</span>
            </div>
        </div>`;
    }).join('');
}

// Format minutes (handles both decimal and MM:SS formats)
function formatMinutes(mp) {
    if (mp == null || mp === '' || mp === '-') return '-';
    if (typeof mp === 'string' && mp.includes(':')) return mp;
    const num = parseFloat(mp);
    if (isNaN(num)) return '-';
    const mins = Math.floor(num);
    const secs = Math.round((num - mins) * 60);
    return secs > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${mins}:00`;
}

// Box Score Modal
function showBoxScore(gameId) {
    const playerGames = (DATA.player_games || []).filter(p => p.game_id === gameId);
    const gameInfo = (DATA.games || []).find(g => g.game_id === gameId);

    if (!playerGames.length) { showToast('No box score data'); return; }

    const detail = document.getElementById('boxscore-detail');
    const gameType = gameInfo?.game_type && gameInfo.game_type !== 'regular' ? ` (${gameInfo.game_type})` : '';

    // Get away/home info
    const awayTeam = gameInfo?.away_team || '';
    const homeTeam = gameInfo?.home_team || '';
    const awayScore = gameInfo?.away_score || 0;
    const homeScore = gameInfo?.home_score || 0;

    // Group players by team, organizing into away and home
    const teams = {};
    playerGames.forEach(p => {
        const team = p.team || 'Unknown';
        if (!teams[team]) teams[team] = { starters: [], bench: [], isHome: team === homeTeam };
        if (p.starter) {
            teams[team].starters.push(p);
        } else {
            teams[team].bench.push(p);
        }
    });

    // Sort each group by minutes played (descending)
    Object.values(teams).forEach(t => {
        t.starters.sort((a, b) => (b.mp || 0) - (a.mp || 0));
        t.bench.sort((a, b) => (b.mp || 0) - (a.mp || 0));
    });

    // Sort teams: away first, then home
    const sortedTeams = Object.entries(teams).sort((a, b) => a[1].isHome - b[1].isHome);

    const awayWon = awayScore > homeScore;

    let html = `
    <div class="boxscore-header">
        <div class="boxscore-matchup">
            <span class="boxscore-team-away ${awayWon ? 'winner' : ''}">${awayTeam} <strong>${awayScore}</strong></span>
            <span class="boxscore-at">@</span>
            <span class="boxscore-team-home ${!awayWon ? 'winner' : ''}"><strong>${homeScore}</strong> ${homeTeam}</span>
        </div>
        <div class="date">${gameInfo?.date || ''}${gameType}</div>
    </div>`;

    // Render each team's box score (away first, then home)
    sortedTeams.forEach(([teamName, roster]) => {
        html += `
        <div class="boxscore-team-section">
            <div class="boxscore-team-title">${teamName}</div>
            <div class="table-container" style="max-height:none;">
                <table class="boxscore-table">
                    <thead><tr>
                        <th>Player</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th>
                        <th>STL</th><th>BLK</th><th>TO</th><th>FG</th><th>3P</th><th>FT</th><th>+/-</th>
                    </tr></thead>
                    <tbody>`;

        // Starters
        if (roster.starters.length > 0) {
            html += `<tr class="roster-divider"><td colspan="12">Starters</td></tr>`;
            roster.starters.forEach(p => {
                html += renderBoxScoreRow(p);
            });
        }

        // Bench
        if (roster.bench.length > 0) {
            html += `<tr class="roster-divider"><td colspan="12">Bench</td></tr>`;
            roster.bench.forEach(p => {
                html += renderBoxScoreRow(p);
            });
        }

        html += '</tbody></table></div></div>';
    });

    detail.innerHTML = html;
    openModal('boxscore-modal');
}

function renderBoxScoreRow(p) {
    return `<tr>
        <td><span class="player-link" onclick="event.stopPropagation();showPlayerDetail('${(p.player||'').replace(/'/g, "\'")}')">${p.player}</span></td>
        <td class="num">${formatMinutes(p.mp)}</td>
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
}

// Players Table
const playerCols = [
    'Player', 'Team', 'Games', 'MPG', 'PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TOPG',
    'FG%', '3P%', 'FT%', 'TS%', 'eFG%', 'Total PTS', 'Total REB', 'Total AST', 'Total +/-'
];

// Tooltips for stat abbreviations
const statTooltips = {
    'MPG': 'Minutes Per Game',
    'PPG': 'Points Per Game',
    'RPG': 'Rebounds Per Game',
    'APG': 'Assists Per Game',
    'SPG': 'Steals Per Game',
    'BPG': 'Blocks Per Game',
    'TOPG': 'Turnovers Per Game',
    'FG%': 'Field Goal Percentage',
    '3P%': 'Three-Point Percentage',
    'FT%': 'Free Throw Percentage',
    'TS%': 'True Shooting Percentage',
    'eFG%': 'Effective Field Goal Percentage',
    'Total PTS': 'Total Points Scored',
    'Total REB': 'Total Rebounds',
    'Total AST': 'Total Assists',
    'Total +/-': 'Cumulative Plus/Minus'
};

// Columns that should show 1 decimal (per-game stats)
const perGameCols = ['MPG', 'PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TOPG'];
// Columns that should show 3 decimals (percentages)
const pctCols = ['FG%', '3P%', 'FT%', 'TS%', 'eFG%'];

function formatStatValue(val, col) {
    if (val == null || val === '') return '';
    if (typeof val !== 'number') return val;
    if (pctCols.includes(col)) return val.toFixed(3);
    if (perGameCols.includes(col)) return val.toFixed(1);
    return Number.isInteger(val) ? val : val.toFixed(1);
}

function renderPlayersTable() {
    const table = document.getElementById('players-table');
    const data = filteredPlayers;

    if (!data || !data.length) {
        table.innerHTML = '<tr><td colspan="20" style="text-align:center;padding:2rem;">No players</td></tr>';
        return;
    }

    let html = '<thead><tr>' + playerCols.map(c => {
        const tooltip = statTooltips[c] ? ` title="${statTooltips[c]}"` : '';
        const sortIndicator = playerSortCol === c ? (playerSortAsc ? ' \u25B2' : ' \u25BC') : '';
        const activeClass = playerSortCol === c ? ' class="sort-active"' : '';
        return `<th onclick="sortPlayersTable('${c}')"${tooltip}${activeClass}>${c}${sortIndicator}</th>`;
    }).join('') + '</tr></thead><tbody>';
    data.forEach(row => {
        html += '<tr>';
        playerCols.forEach(col => {
            let v = row[col];
            if (v == null) v = '';
            if (typeof v === 'number') {
                v = formatStatValue(v, col);
                html += `<td class="num">${v}</td>`;
            } else if (col === 'Player') {
                html += `<td><span class="player-link" onclick="showPlayerDetail('${(v||'').replace(/'/g, "\\'")}')">${v}</span></td>`;
            } else if (col === 'Team') {
                html += `<td>${getTeamCode(v)}</td>`;
            } else {
                html += `<td>${v}</td>`;
            }
        });
        html += '</tr>';
    });
    table.innerHTML = html + '</tbody>';
}

function sortPlayersTable(col) {
    // Toggle direction if same column, otherwise default to descending for numbers, ascending for text
    if (playerSortCol === col) {
        playerSortAsc = !playerSortAsc;
    } else {
        playerSortCol = col;
        // Default: numbers sort descending (highest first), text sorts ascending (A-Z)
        const isNumericCol = filteredPlayers.length > 0 && typeof filteredPlayers[0][col] === 'number';
        playerSortAsc = !isNumericCol;
    }

    filteredPlayers.sort((a, b) => {
        let av = a[col], bv = b[col];
        if (av == null) av = '';
        if (bv == null) bv = '';

        let result;
        if (typeof av === 'number' && typeof bv === 'number') {
            result = av - bv;
        } else {
            result = String(av).localeCompare(String(bv));
        }

        return playerSortAsc ? result : -result;
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
    playerSortCol = null;
    playerSortAsc = false;
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

// Player Detail with Chart
let playerChart = null;

function showPlayerDetail(name) {
    const games = (DATA.player_games || []).filter(g => g.player === name).sort((a,b) => (b.date_yyyymmdd||'').localeCompare(a.date_yyyymmdd||''));
    const stats = (DATA.players || []).find(p => p.Player === name);

    if (!stats && !games.length) { showToast('Player not found'); return; }

    let html = `<h2>${name}</h2>`;
    if (stats) {
        html += `<p style="color:var(--text-secondary);margin-bottom:1rem;">${stats.Team || ''} | ${stats.Games || 0} games</p>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1.5rem;">
            <div class="player-stat-box"><div class="number">${(stats.PPG||0).toFixed(1)}</div><div class="label">PPG</div></div>
            <div class="player-stat-box"><div class="number">${(stats.RPG||0).toFixed(1)}</div><div class="label">RPG</div></div>
            <div class="player-stat-box"><div class="number">${(stats.APG||0).toFixed(1)}</div><div class="label">APG</div></div>
            <div class="player-stat-box"><div class="number">${(stats.MPG||0).toFixed(1)}</div><div class="label">MPG</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1.5rem;">
            <div style="text-align:center;"><strong>${((stats['FG%']||0)*100).toFixed(1)}%</strong><br><small>FG%</small></div>
            <div style="text-align:center;"><strong>${((stats['3P%']||0)*100).toFixed(1)}%</strong><br><small>3P%</small></div>
            <div style="text-align:center;"><strong>${((stats['FT%']||0)*100).toFixed(1)}%</strong><br><small>FT%</small></div>
        </div>`;
    }

    // Add chart section if multiple games
    if (games.length > 1) {
        html += `
        <div class="chart-section">
            <div class="chart-header">
                <h4>Performance Trend</h4>
                <div class="chart-toggles">
                    <button class="chart-toggle active" data-stat="pts">PTS</button>
                    <button class="chart-toggle" data-stat="trb">REB</button>
                    <button class="chart-toggle" data-stat="ast">AST</button>
                    <button class="chart-toggle" data-stat="game_score">GmSc</button>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="player-chart"></canvas>
            </div>
        </div>`;
    }

    if (games.length) {
        html += '<h4 style="margin-top:1.5rem;margin-bottom:0.5rem;">Game Log</h4><div class="table-container" style="max-height:250px;"><table><thead><tr><th>Date</th><th>Opp</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>FG</th><th>+/-</th></tr></thead><tbody>';
        games.forEach(g => html += `<tr><td>${g.date||''}</td><td>${g.opponent||''}</td><td>${formatMinutes(g.mp)}</td><td>${g.pts||0}</td><td>${g.trb||0}</td><td>${g.ast||0}</td><td>${g.stl||0}</td><td>${g.blk||0}</td><td>${g.fg||0}-${g.fga||0}</td><td>${g.plus_minus||0}</td></tr>`);
        html += '</tbody></table></div>';
    }

    document.getElementById('player-detail').innerHTML = html;
    openModal('player-modal');

    // Initialize chart after DOM update
    if (games.length > 1) {
        setTimeout(() => initPlayerChart(games, 'pts'), 100);

        // Add toggle listeners
        document.querySelectorAll('.chart-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.chart-toggle').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                initPlayerChart(games, e.target.dataset.stat);
            });
        });
    }
}

function initPlayerChart(games, stat) {
    const ctx = document.getElementById('player-chart');
    if (!ctx) return;

    if (playerChart) {
        playerChart.destroy();
    }

    // Reverse for chart (oldest to newest, left to right)
    const chartGames = [...games].reverse();

    const labels = chartGames.map(g => {
        const d = g.date || '';
        // Shorten date for display
        const parts = d.split(' ');
        return parts.length >= 2 ? `${parts[0].slice(0,3)} ${parts[1]}` : d;
    });

    const data = chartGames.map(g => g[stat] || 0);
    const avg = data.reduce((a,b) => a+b, 0) / data.length;

    const statLabels = { pts: 'Points', trb: 'Rebounds', ast: 'Assists', game_score: 'Game Score' };
    const statColors = { pts: '#4ade80', trb: '#60a5fa', ast: '#f472b6', game_score: '#fbbf24' };

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
    const textColor = isDark ? '#b0b0b0' : '#666666';

    playerChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: statLabels[stat] || stat,
                data: data,
                borderColor: statColors[stat] || '#4ade80',
                backgroundColor: (statColors[stat] || '#4ade80') + '20',
                fill: true,
                tension: 0.3,
                pointRadius: 5,
                pointHoverRadius: 7,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => chartGames[items[0].dataIndex]?.date || '',
                        afterLabel: (item) => `vs ${chartGames[item.dataIndex]?.opponent || ''}`
                    }
                },
                annotation: {
                    annotations: {
                        avgLine: {
                            type: 'line',
                            yMin: avg,
                            yMax: avg,
                            borderColor: 'rgba(255,255,255,0.5)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            label: {
                                display: true,
                                content: `Avg: ${avg.toFixed(1)}`,
                                position: 'end'
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, maxRotation: 45 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                }
            }
        }
    });
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

// Constants are auto-generated at the start of this script

// Team Checklist
let currentChecklistView = 'all';

function renderTeamChecklist() {
    const checklist = DATA.teamChecklist || {};
    const teams = checklist.teams || [];
    const divisions = checklist.divisions || {};
    const conferences = checklist.conferences || {};
    const summary = checklist.summary || { teamsSeen: 0, totalTeams: 30 };

    // Update progress bar
    document.getElementById('team-progress-fill').style.width = `${(summary.teamsSeen/30)*100}%`;
    document.getElementById('team-progress-text').textContent = `${summary.teamsSeen}/30 Teams Seen`;

    showChecklistView(currentChecklistView);
}

function showChecklistView(view) {
    currentChecklistView = view;
    const container = document.getElementById('team-checklist-container');
    const checklist = DATA.teamChecklist || {};
    const teams = checklist.teams || [];
    const divisions = checklist.divisions || {};
    const conferences = checklist.conferences || {};

    // Update tab styling
    document.querySelectorAll('.checklist-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-view="${view}"]`)?.classList.add('active');

    let html = '';

    if (view === 'all') {
        // Show all teams in a single grid
        const seen = teams.filter(t => t.seen).length;
        html = `
            <div class="division-card ${seen === 30 ? 'complete' : ''}">
                <div class="division-header">
                    <h4>All NBA Teams</h4>
                    <span class="badge ${seen === 30 ? 'badge-complete' : 'badge-progress'}">${seen}/30</span>
                </div>
                <div class="team-grid">
                    ${teams.sort((a,b) => a.name.localeCompare(b.name)).map(t => `
                        <div class="team-item ${t.seen ? 'seen' : ''}">
                            <span class="${t.seen ? 'check' : 'not-seen'}">${t.seen ? '✓' : '○'}</span>
                            <span>${getShortName(t.name)}</span>
                            ${t.visitCount > 0 ? `<span class="visit-count">${t.visitCount}x</span>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>`;
    } else if (view === 'east' || view === 'west') {
        const conf = view === 'east' ? 'East' : 'West';
        const confData = conferences[conf] || { teamsSeen: 0, totalTeams: 15, divisions: [] };
        const divNames = view === 'east' ? ['Atlantic', 'Central', 'Southeast'] : ['Northwest', 'Pacific', 'Southwest'];

        html = `
            <div class="conference-summary">
                <div class="conference-box ${confData.teamsSeen === 15 ? 'complete' : ''}">
                    <h5>${conf}ern Conference</h5>
                    <div class="count">${confData.teamsSeen}/15</div>
                </div>
            </div>`;

        divNames.forEach(divName => {
            const div = divisions[divName] || { teams: [], teamsSeen: 0, totalTeams: 5 };
            html += `
                <div class="division-card ${div.complete ? 'complete' : ''}">
                    <div class="division-header">
                        <h4>${divName} Division</h4>
                        <span class="badge ${div.complete ? 'badge-complete' : 'badge-progress'}">${div.teamsSeen}/${div.totalTeams}</span>
                    </div>
                    <div class="team-grid">
                        ${(div.teams || []).map(t => `
                            <div class="team-item ${t.seen ? 'seen' : ''}">
                                <span class="${t.seen ? 'check' : 'not-seen'}">${t.seen ? '✓' : '○'}</span>
                                <span>${getShortName(t.name)}</span>
                                ${t.visitCount > 0 ? `<span class="visit-count">${t.visitCount}x</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>`;
        });
    } else if (view === 'divisions') {
        // Show conference summaries first
        html = `<div class="conference-summary">`;
        ['East', 'West'].forEach(conf => {
            const confData = conferences[conf] || { teamsSeen: 0, totalTeams: 15 };
            html += `
                <div class="conference-box ${confData.teamsSeen === 15 ? 'complete' : ''}">
                    <h5>${conf}ern</h5>
                    <div class="count">${confData.teamsSeen}/15</div>
                </div>`;
        });
        html += '</div>';

        // Show all divisions
        const divOrder = ['Atlantic', 'Central', 'Southeast', 'Northwest', 'Pacific', 'Southwest'];
        divOrder.forEach(divName => {
            const div = divisions[divName] || { teams: [], teamsSeen: 0, totalTeams: 5, conference: '' };
            html += `
                <div class="division-card ${div.complete ? 'complete' : ''}">
                    <div class="division-header">
                        <h4>${divName} <small style="font-weight:normal;color:var(--text-muted);">(${div.conference || ''})</small></h4>
                        <span class="badge ${div.complete ? 'badge-complete' : 'badge-progress'}">${div.teamsSeen}/${div.totalTeams}</span>
                    </div>
                    <div class="team-grid">
                        ${(div.teams || []).map(t => `
                            <div class="team-item ${t.seen ? 'seen' : ''}">
                                <span class="${t.seen ? 'check' : 'not-seen'}">${t.seen ? '✓' : '○'}</span>
                                <span>${getShortName(t.name)}</span>
                                ${t.visitCount > 0 ? `<span class="visit-count">${t.visitCount}x</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>`;
        });
    }

    container.innerHTML = html;
}

// MILESTONE_CATEGORIES is auto-generated from Python constants

// Master order for displaying all milestones (grouped by category)
const MILESTONE_ORDER = [
    // Multi-stat achievements
    'quadruple_doubles', 'triple_doubles', 'near_triple_doubles', 'double_doubles', 'near_double_doubles',
    'five_by_fives', 'all_around_games',
    // Scoring (high to low)
    'seventy_point_games', 'sixty_point_games', 'fifty_point_games', 'forty_five_point_games',
    'forty_point_games', 'thirty_five_point_games', 'thirty_point_games', 'twenty_five_point_games', 'twenty_point_games',
    // Combined stats
    'twenty_twenty_games', 'thirty_ten_games', 'twenty_five_ten_games', 'twenty_ten_five_games',
    'twenty_ten_games', 'points_assists_double_double',
    // Rebounding (high to low)
    'twenty_five_rebound_games', 'twenty_rebound_games', 'eighteen_rebound_games',
    'fifteen_rebound_games', 'twelve_rebound_games', 'ten_rebound_games',
    // Assists (high to low)
    'twenty_assist_games', 'fifteen_assist_games', 'twelve_assist_games', 'ten_assist_games',
    // Three-pointers
    'ten_three_games', 'eight_three_games', 'seven_three_games', 'six_three_games', 'five_three_games', 'perfect_from_three',
    // Steals (high to low)
    'ten_steal_games', 'seven_steal_games', 'five_steal_games', 'four_steal_games',
    // Blocks (high to low)
    'ten_block_games', 'seven_block_games', 'five_block_games', 'four_block_games',
    // Efficiency
    'high_game_score', 'efficient_scoring_games', 'hot_shooting_games', 'perfect_fg_games', 'perfect_ft_games',
    // Defensive
    'defensive_monster_games', 'zero_turnover_games',
    // Plus/Minus
    'plus_25_games', 'plus_20_games', 'minus_25_games'
];

function renderMilestones() {
    filterMilestones();
}

function filterMilestones() {
    const category = document.getElementById('milestone-category').value;
    const search = document.getElementById('milestone-search').value.toLowerCase();
    const container = document.getElementById('milestones-container');
    const milestones = DATA.milestones || {};
    const descriptions = DATA.milestone_descriptions || {};

    let keysToShow = [];
    if (category === 'all') {
        // Use master order for "all" view to group related stats together
        keysToShow = MILESTONE_ORDER.filter(k => milestones[k] && milestones[k].length > 0);
        // Also include any milestones not in the master order
        Object.keys(milestones).forEach(k => {
            if (!keysToShow.includes(k) && milestones[k] && milestones[k].length > 0) {
                keysToShow.push(k);
            }
        });
    } else {
        keysToShow = (MILESTONE_CATEGORIES[category] || []).filter(k => milestones[k] && milestones[k].length > 0);
    }

    let html = '';
    keysToShow.forEach(key => {
        let data = milestones[key] || [];

        // Sort by date descending (most recent first)
        data = [...data].sort((a, b) => (b.date_yyyymmdd || '').localeCompare(a.date_yyyymmdd || ''));

        // Filter by search
        if (search) {
            data = data.filter(m => m.player?.toLowerCase().includes(search) || m.team?.toLowerCase().includes(search));
        }

        if (data.length === 0 && search) return;

        const title = descriptions[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        html += `<div class="milestone-card">
            <h4>${title} <span class="count">${data.length}</span></h4>`;

        if (data.length === 0) {
            html += '<p class="empty">None recorded</p>';
        } else {
            html += '<div class="table-container" style="max-height:300px;"><table><thead><tr><th>Date</th><th>Player</th><th>Team</th><th>vs</th><th>Detail</th></tr></thead><tbody>';
            data.slice(0, 50).forEach(m => {
                html += `<tr>
                    <td>${m.date || ''}</td>
                    <td><span class="player-link" onclick="showPlayerDetail('${(m.player||'').replace(/'/g, "\\'")}')">${m.player || ''}</span></td>
                    <td>${m.team || ''}</td>
                    <td>${m.opponent || ''}</td>
                    <td>${m.detail || ''}</td>
                </tr>`;
            });
            if (data.length > 50) html += `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">...and ${data.length - 50} more</td></tr>`;
            html += '</tbody></table></div>';
        }
        html += '</div>';
    });

    if (!html) {
        html = '<p style="text-align:center;padding:2rem;color:var(--text-muted);">No milestones found</p>';
    }

    container.innerHTML = html;
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
    }).join(','))].join('\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = 'nba_players.csv'; a.click();
    showToast('Download started');
}

// Stat Leaders
function renderLeaders() {
    const players = DATA.players || [];
    const grid = document.getElementById('leaders-grid');

    if (!players.length) {
        grid.innerHTML = '<p style="text-align:center;padding:2rem;color:var(--text-muted);">No player data</p>';
        return;
    }

    const categories = [
        { key: 'PPG', label: 'Points Per Game', format: v => v.toFixed(1) },
        { key: 'RPG', label: 'Rebounds Per Game', format: v => v.toFixed(1) },
        { key: 'APG', label: 'Assists Per Game', format: v => v.toFixed(1) },
        { key: 'SPG', label: 'Steals Per Game', format: v => v.toFixed(1) },
        { key: 'BPG', label: 'Blocks Per Game', format: v => v.toFixed(1) },
        { key: 'FG%', label: 'Field Goal %', format: v => (v * 100).toFixed(1) + '%' },
        { key: '3P%', label: 'Three-Point %', format: v => (v * 100).toFixed(1) + '%' },
        { key: 'FT%', label: 'Free Throw %', format: v => (v * 100).toFixed(1) + '%' },
        { key: 'Total PTS', label: 'Total Points', format: v => v.toLocaleString() },
        { key: 'Total REB', label: 'Total Rebounds', format: v => v.toLocaleString() },
        { key: 'Total AST', label: 'Total Assists', format: v => v.toLocaleString() },
        { key: 'Total +/-', label: 'Total Plus/Minus', format: v => (v >= 0 ? '+' : '') + v },
    ];

    grid.innerHTML = categories.map(cat => {
        // Sort players by this stat and take top 5
        const sorted = [...players]
            .filter(p => p[cat.key] != null && p.Games >= 2)
            .sort((a, b) => b[cat.key] - a[cat.key])
            .slice(0, 5);

        return `
        <div class="leader-card">
            <h4>${cat.label}</h4>
            <ul class="leader-list">
                ${sorted.map((p, i) => `
                    <li class="leader-item">
                        <span class="leader-rank">${i + 1}</span>
                        <span class="leader-name" onclick="showPlayerDetail('${(p.Player||'').replace(/'/g, "\\'")}')">${p.Player}</span>
                        <span class="leader-team">${getTeamCode(p.Team)}</span>
                        <span class="leader-value">${cat.format(p[cat.key])}</span>
                    </li>
                `).join('')}
            </ul>
        </div>`;
    }).join('');
}

// Init
document.addEventListener('DOMContentLoaded', function() {
    renderGamesGrid();
    renderLeaders();
    populateTeamDropdown();
    filteredPlayers = DATA.players ? [...DATA.players] : [];
    renderPlayersTable();
    renderTeamChecklist();
    renderVenuesTable();
    renderMilestones();
});

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.active').forEach(m => closeModal(m.id));
});