import React, { useState, useEffect } from 'react';
import './App.css';

// Use Lambda URL for production (Amplify), fallback to local for dev
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                     'https://lk2iyjgzwxhks4lq35bfxziylq0xwcfv.lambda-url.us-east-1.on.aws/api';

function App() {
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('today');
  const [results, setResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);

  useEffect(() => {
    fetchPicks();
  }, [filter]);

  const fetchPicks = async () => {
    setLoading(true);
    setError(null);

    try {
      const endpoint = filter === 'today' 
        ? `${API_BASE_URL}/picks/today`
        : `${API_BASE_URL}/picks`;
      
      console.log('Fetching from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.success) {
        setPicks(data.picks || []);
      } else {
        setError(data.error || 'Failed to load picks');
      }
    } catch (err) {
      console.error('Error fetching picks:', err);
      setError(`Cannot load picks: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const checkResults = async () => {
    setResultsLoading(true);
    setError(null);

    try {
      const endpoint = `${API_BASE_URL}/results/today`;
      console.log('Checking results from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.success) {
        setResults(data);
      } else {
        setError(data.error || 'Failed to load results');
      }
    } catch (err) {
      console.error('Error checking results:', err);
      setError(`Cannot load results: ${err.message}`);
    } finally {
      setResultsLoading(false);
    }
  };

  const formatOdds = (odds) => {
    if (!odds) return 'N/A';
    try {
      // Handle if odds is an object (e.g., {fractional, decimal, overround})
      if (typeof odds === 'object') {
        if (odds.fractional) return String(odds.fractional);
        if (odds.decimal) odds = odds.decimal;
        else return 'N/A';
      }
      
      const decimal = parseFloat(odds);
      if (isNaN(decimal)) return String(odds);
      
      // Convert decimal to fractional
      const fractional = decimal - 1;
      if (fractional < 1) {
        return `${Math.round(1/fractional)}/${1}`;
      }
      return `${Math.round(fractional)}/${1}`;
    } catch (e) {
      return 'N/A';
    }
  };

  const formatTime = (timeStr) => {
    if (!timeStr) return 'TBC';
    try {
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) return timeStr;
      // Dublin/Ireland time (Europe/Dublin timezone)
      return date.toLocaleTimeString('en-IE', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false,
        timeZone: 'Europe/Dublin'
      });
    } catch (e) {
      return timeStr;
    }
  };

  const getBetTypeBadge = (betType) => {
    const type = (betType || 'WIN').toUpperCase();
    const color = type === 'EW' ? '#f59e0b' : '#10b981';
    return (
      <span style={{
        background: color,
        color: 'white',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 'bold'
      }}>
        {type}
      </span>
    );
  };

  const getConfidenceColor = (confidence) => {
    const conf = parseFloat(confidence) || 0;
    if (conf >= 70) return '#10b981';
    if (conf >= 50) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🏇 Today's Betting Picks</h1>
        <p>Value opportunities from AI analysis</p>
        
        <div className="filter-buttons">
          <button 
            className={filter === 'today' ? 'active' : ''} 
            onClick={() => setFilter('today')}
          >
            Today Only
          </button>
          <button 
            className={filter === 'all' ? 'active' : ''} 
            onClick={() => setFilter('all')}
          >
            All Picks
          </button>
          <button onClick={fetchPicks} className="refresh-btn">
            🔄 Refresh
          </button>
          <button onClick={checkResults} className="results-btn" disabled={resultsLoading}>
            {resultsLoading ? '⏳ Checking...' : '📊 Check Results'}
          </button>
        </div>
      </header>

      <main className="picks-container">
        {/* Results Summary */}
        {results && results.summary && (
          <div className="results-summary">
            <h2>📊 Today's Performance</h2>
            <div className="results-grid">
              <div className="result-stat">
                <div className="stat-label">Total Picks</div>
                <div className="stat-value">{results.summary.total_picks}</div>
              </div>
              <div className="result-stat win">
                <div className="stat-label">Wins</div>
                <div className="stat-value">{results.summary.wins}</div>
              </div>
              <div className="result-stat place">
                <div className="stat-label">Places</div>
                <div className="stat-value">{results.summary.places}</div>
              </div>
              <div className="result-stat loss">
                <div className="stat-label">Losses</div>
                <div className="stat-value">{results.summary.losses}</div>
              </div>
              <div className="result-stat pending">
                <div className="stat-label">Pending</div>
                <div className="stat-value">{results.summary.pending}</div>
              </div>
              <div className="result-stat">
                <div className="stat-label">Strike Rate</div>
                <div className="stat-value">{results.summary.strike_rate}%</div>
              </div>
              <div className="result-stat">
                <div className="stat-label">Total Stake</div>
                <div className="stat-value">€{results.summary.total_stake}</div>
              </div>
              <div className="result-stat">
                <div className="stat-label">Total Return</div>
                <div className="stat-value">€{results.summary.total_return}</div>
              </div>
              <div className={`result-stat ${results.summary.profit >= 0 ? 'profit' : 'loss'}`}>
                <div className="stat-label">Profit/Loss</div>
                <div className="stat-value">
                  {results.summary.profit >= 0 ? '+' : ''}€{results.summary.profit}
                </div>
              </div>
              <div className={`result-stat ${results.summary.roi >= 0 ? 'profit' : 'loss'}`}>
                <div className="stat-label">ROI</div>
                <div className="stat-value">{results.summary.roi}%</div>
              </div>
            </div>
            <button onClick={() => setResults(null)} className="close-results">
              ✕ Close Results
            </button>
          </div>
        )}
        
        {loading && <div className="loading">Loading picks...</div>}
        
        {error && (
          <div className="error">
            <h3>Error loading picks</h3>
            <p>{error}</p>
            <p className="hint">Check AWS credentials are configured</p>
          </div>
        )}

        {!loading && !error && picks.length === 0 && (
          <div className="no-picks">
            <h3>No picks found</h3>
            <p>No selections available today</p>
          </div>
        )}

        {!loading && !error && picks.length > 0 && (
          <>
            <div className="picks-summary">
              Showing top {Math.min(5, picks.length)} of {picks.length} selections
            </div>
            <div className="picks-grid">
            {picks.slice(0, 5).map((pick, index) => {
              const roi = parseFloat(pick.roi || 0);
              const belowThreshold = roi < 0.05;
              
              // Safely extract values, handling objects
              const horseName = typeof pick.horse === 'string' ? pick.horse : 'Unknown';
              const courseName = typeof pick.course === 'string' ? pick.course : 'Unknown';
              
              // Calculate bet amounts and returns
              const stake = parseFloat(pick.stake || 2.0);
              const odds = parseFloat(pick.odds || 0);
              const pWin = parseFloat(pick.p_win || 0);
              const pPlace = parseFloat(pick.p_place || 0);
              const betType = (pick.bet_type || 'WIN').toUpperCase();
              
              // Calculate potential returns
              let potentialWin = 0;
              let expectedReturn = 0;
              
              if (betType === 'WIN') {
                potentialWin = stake * odds;
                expectedReturn = potentialWin * pWin;
              } else if (betType === 'EW') {
                const ewFraction = parseFloat(pick.ew_fraction || 0.2);
                const halfStake = stake / 2;
                const winReturn = halfStake * odds;
                const placeOdds = 1 + ((odds - 1) * ewFraction);
                const placeReturn = halfStake * placeOdds;
                potentialWin = winReturn + placeReturn;
                expectedReturn = (winReturn * pWin) + (placeReturn * pPlace);
              }
              
              const profit = potentialWin - stake;
              const expectedProfit = expectedReturn - stake;
              
              return (
              <div key={pick.bet_id || index} className={`pick-card ${belowThreshold ? 'below-threshold' : ''}`}>
                <div className="pick-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
                  <h2 style={{margin: 0}}>{horseName}</h2>
                  <div style={{display: 'flex', gap: '8px', alignItems: 'center'}}>
                    {getBetTypeBadge(pick.bet_type)}
                    {/* ROI INDICATOR BADGE */}
                    <div style={{
                      background: belowThreshold ? '#f59e0b' : '#10b981',
                      color: 'white',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontWeight: 'bold',
                      fontSize: '14px',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                      whiteSpace: 'nowrap'
                    }}>
                      {belowThreshold ? '⚠️' : '✓'} {(roi * 100).toFixed(1)}% ROI
                    </div>
                  </div>
                </div>
                
                <div className="pick-venue">
                  <span className="venue-icon">📍</span>
                  <span>{courseName}</span>
                  <span className="time">{formatTime(pick.race_time)} (Dublin)</span>
                </div>
                
                {/* BET RECOMMENDATION BOX */}
                <div className="bet-recommendation-box" style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '16px',
                  borderRadius: '8px',
                  marginTop: '12px',
                  marginBottom: '12px'
                }}>
                  <div style={{fontSize: '14px', opacity: 0.9, marginBottom: '8px'}}>
                    💰 Recommended Bet
                  </div>
                  <div style={{fontSize: '28px', fontWeight: 'bold', marginBottom: '8px'}}>
                    €{stake.toFixed(2)}
                  </div>
                  <div style={{fontSize: '13px', opacity: 0.85, marginBottom: '12px'}}>
                    {betType === 'EW' ? `€${(stake/2).toFixed(2)} Win + €${(stake/2).toFixed(2)} Place` : 'Win bet'}
                  </div>
                  <div style={{borderTop: '1px solid rgba(255,255,255,0.3)', paddingTop: '12px'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '6px'}}>
                      <span style={{fontSize: '13px', opacity: 0.9}}>If wins:</span>
                      <span style={{fontSize: '16px', fontWeight: 'bold'}}>
                        +€{profit.toFixed(2)}
                      </span>
                    </div>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{fontSize: '13px', opacity: 0.9}}>Expected value:</span>
                      <span style={{fontSize: '16px', fontWeight: 'bold', color: expectedProfit > 0 ? '#a7f3d0' : '#fca5a5'}}>
                        {expectedProfit > 0 ? '+' : ''}€{expectedProfit.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pick-odds">
                  <div className="odds-item">
                    <span className="label">Odds:</span>
                    <span className="value">{formatOdds(pick.odds)}</span>
                  </div>
                  <div className="odds-item">
                    <span className="label">Win Prob:</span>
                    <span className="value">{(parseFloat(pick.p_win || 0) * 100).toFixed(0)}%</span>
                  </div>
                  {pick.p_place && (
                    <div className="odds-item">
                      <span className="label">Place Prob:</span>
                      <span className="value">{(parseFloat(pick.p_place) * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>

                {pick.ew_places && pick.ew_places > 0 && (
                  <div className="ew-terms">
                    <span>EW: {pick.ew_places} places @ 1/{Math.round(1/parseFloat(pick.ew_fraction || 0.2))}</span>
                  </div>
                )}

                {pick.confidence && (
                  <div className="confidence-bar">
                    <div 
                      className="confidence-fill" 
                      style={{
                        width: `${pick.confidence}%`,
                        background: getConfidenceColor(pick.confidence)
                      }}
                    />
                    <span className="confidence-text">
                      {Math.round(pick.confidence)}% confidence
                    </span>
                  </div>
                )}

                {pick.why_now && (
                  <div className="rationale">
                    <strong>Why Now:</strong> {pick.why_now}
                  </div>
                )}

                {pick.expected_roi && (
                  <div className="expected-roi" style={{marginTop: '8px'}}>
                    Expected ROI: <span className={pick.expected_roi > 0 ? 'positive' : 'negative'}>
                      {pick.expected_roi > 0 ? '+' : ''}{pick.expected_roi}%
                    </span>
                  </div>
                )}

                {pick.tags && pick.tags.length > 0 && (
                  <div className="tags">
                    {(Array.isArray(pick.tags) ? pick.tags : pick.tags.split(',')).map((tag, i) => (
                      <span key={i} className="tag">{tag.trim()}</span>
                    ))}
                  </div>
                )}

                <div className="pick-footer">
                  <span className="timestamp">
                    {new Date(pick.timestamp).toLocaleString('en-GB')}
                  </span>
                </div>
              </div>
            );
            })}
          </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
