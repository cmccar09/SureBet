import React, { useState, useEffect } from 'react';
import './App.css';

// Use Lambda Function URL in eu-west-1
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                     'https://lq7f6d45qygsvjqaej3w2xdlbu0cibvk.lambda-url.eu-west-1.on.aws';

function App() {
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('today');
  const [results, setResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

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

  const triggerWorkflow = async () => {
    setRefreshing(true);
    setError(null);
    
    try {
      // Call cloud API to trigger workflow Lambda
      const response = await fetch(`${API_BASE_URL}/api/workflow/run`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setError('✓ Generating new picks... Refreshing in 90 seconds...');
        
        // Auto-refresh after 90 seconds
        setTimeout(() => {
          fetchPicks();
          setError(null);
        }, 90000);
      } else {
        setError(data.error || data.message || 'Failed to trigger workflow');
      }
    } catch (err) {
      console.error('Error triggering workflow:', err);
      setError(`Cannot trigger workflow: ${err.message}`);
    } finally {
      setRefreshing(false);
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
          <button onClick={triggerWorkflow} className="refresh-btn" disabled={refreshing}>
            {refreshing ? '⏳ Generating...' : '🔄 Generate New Picks'}
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
              
              // Calculate recommended bet size using fractional Kelly Criterion
              const odds = parseFloat(pick.odds || 0);
              const pWin = parseFloat(pick.p_win || 0);
              const pPlace = parseFloat(pick.p_place || 0);
              const betType = (pick.bet_type || 'WIN').toUpperCase();
              
              // Kelly Criterion: (odds * p_win - 1) / (odds - 1)
              // We use fractional Kelly (1/4 Kelly) for safety
              const bankroll = 100; // Assume €100 bankroll
              let kellyFraction = 0;
              
              if (betType === 'WIN' && odds > 1 && pWin > 0) {
                kellyFraction = ((odds * pWin) - 1) / (odds - 1);
              } else if (betType === 'EW' && odds > 1 && pWin > 0) {
                // For EW bets, use ROI to calculate Kelly
                // Kelly = edge / odds
                const edge = roi / 100; // Convert ROI percentage to decimal
                kellyFraction = Math.max(0, edge / (odds - 1));
              }
              
              // Use 1/4 Kelly for conservative sizing, cap at 5% of bankroll
              const recommendedFraction = Math.max(0, Math.min(kellyFraction * 0.25, 0.05));
              let stake = Math.round(bankroll * recommendedFraction * 2) / 2; // Round to nearest €0.50
              
              // Apply minimum stakes based on bet type and quality
              if (betType === 'EW') {
                // EW bets: minimum €10 each way = €20 total
                stake = Math.max(20, stake);
              } else {
                // WIN bets: minimum €25, but €30 for really good prospects (ROI > 10%)
                if (roi > 10) {
                  stake = Math.max(30, stake);
                } else {
                  stake = Math.max(25, stake);
                }
              }
              
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
              
              // Get decision rating styling
              const decisionRating = pick.decision_rating || 'RISKY';
              const decisionScore = pick.decision_score || 50;
              
              let decisionBg, decisionIcon, decisionText;
              if (decisionRating === 'DO IT') {
                decisionBg = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                decisionIcon = '🟢';
                decisionText = 'Strong Bet';
              } else if (decisionRating === 'RISKY') {
                decisionBg = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                decisionIcon = '🟠';
                decisionText = 'Moderate Risk';
              } else {
                decisionBg = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
                decisionIcon = '🔴';
                decisionText = 'Skip This';
              }
              
              return (
              <div key={pick.bet_id || index} className={`pick-card ${belowThreshold ? 'below-threshold' : ''}`}>
                {/* DECISION RATING - Top Prominent Display */}
                <div style={{
                  background: decisionBg,
                  color: 'white',
                  padding: '16px',
                  borderRadius: '8px 8px 0 0',
                  marginBottom: '16px',
                  textAlign: 'center',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}>
                  <div style={{fontSize: '18px', fontWeight: 'bold', marginBottom: '8px', letterSpacing: '1px'}}>
                    {decisionIcon} {decisionRating} - {decisionScore.toFixed(0)}/100
                  </div>
                  <div style={{fontSize: '13px', opacity: 0.95}}>
                    {decisionText}
                  </div>
                </div>
                
                <div className="pick-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '0 16px'}}>
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
                      {belowThreshold ? '⚠️' : '✓'} {roi.toFixed(1)}% ROI
                    </div>
                  </div>
                </div>
                
                <div className="pick-venue" style={{padding: '0 16px'}}>
                  <span className="venue-icon">📍</span>
                  <span>{courseName}</span>
                  <span className="time">{formatTime(pick.race_time)} (Dublin)</span>
                </div>
                
                {/* RECOMMENDED STAKE - Simplified */}
                <div style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '16px',
                  borderRadius: '8px',
                  margin: '16px',
                  marginBottom: '12px'
                }}>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                    <div>
                      <div style={{fontSize: '14px', opacity: 0.9, marginBottom: '4px'}}>
                        💰 Recommended Stake
                      </div>
                      <div style={{fontSize: '28px', fontWeight: 'bold'}}>
                        €{stake.toFixed(2)}
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '4px'}}>
                        {betType === 'EW' ? `€${(stake/2).toFixed(2)} Win + €${(stake/2).toFixed(2)} Place` : 'Win bet'}
                      </div>
                    </div>
                    <div style={{textAlign: 'right'}}>
                      <div style={{fontSize: '13px', opacity: 0.9, marginBottom: '4px'}}>
                        If wins:
                      </div>
                      <div style={{fontSize: '20px', fontWeight: 'bold', color: '#a7f3d0'}}>
                        +€{profit.toFixed(2)}
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '4px'}}>
                        EV: {expectedProfit > 0 ? '+' : ''}€{expectedProfit.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* KEY STATS - Compact */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: '12px',
                  padding: '0 16px',
                  marginBottom: '16px'
                }}>
                  <div style={{textAlign: 'center'}}>
                    <div style={{fontSize: '12px', color: '#6b7280', marginBottom: '4px'}}>Odds</div>
                    <div style={{fontSize: '18px', fontWeight: 'bold'}}>{formatOdds(pick.odds)}</div>
                  </div>
                  <div style={{textAlign: 'center'}}>
                    <div style={{fontSize: '12px', color: '#6b7280', marginBottom: '4px'}}>Win</div>
                    <div style={{fontSize: '18px', fontWeight: 'bold'}}>{(parseFloat(pick.p_win || 0) * 100).toFixed(0)}%</div>
                  </div>
                  <div style={{textAlign: 'center'}}>
                    <div style={{fontSize: '12px', color: '#6b7280', marginBottom: '4px'}}>Place</div>
                    <div style={{fontSize: '18px', fontWeight: 'bold'}}>{(parseFloat(pick.p_place || 0) * 100).toFixed(0)}%</div>
                  </div>
                </div>
                
                {/* COMBINED CONFIDENCE - Collapsed by default, expandable */}
                {pick.combined_confidence && (
                  <details style={{margin: '0 16px', marginBottom: '16px'}}>
                    <summary style={{
                      cursor: 'pointer',
                      padding: '12px',
                      background: '#f3f4f6',
                      borderRadius: '6px',
                      fontWeight: '600',
                      fontSize: '14px',
                      userSelect: 'none'
                    }}>
                      📊 Confidence Details: {pick.combined_confidence.toFixed(0)}/100 ({pick.confidence_grade || 'N/A'})
                    </summary>
                    <div style={{
                      padding: '12px',
                      background: '#f9fafb',
                      borderRadius: '0 0 6px 6px',
                      marginTop: '4px',
                      fontSize: '13px'
                    }}>
                      <div style={{marginBottom: '8px'}}>
                        {pick.confidence_explanation || 'Multiple confidence signals consolidated'}
                      </div>
                      {pick.confidence_breakdown && (
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: '6px',
                          fontSize: '12px',
                          color: '#6b7280'
                        }}>
                          <div>Win: {pick.confidence_breakdown.win_component?.toFixed(1) || 0}</div>
                          <div>Place: {pick.confidence_breakdown.place_component?.toFixed(1) || 0}</div>
                          <div>Edge: {pick.confidence_breakdown.edge_component?.toFixed(1) || 0}</div>
                          <div>Consistency: {pick.confidence_breakdown.consistency_component?.toFixed(1) || 0}</div>
                        </div>
                      )}
                    </div>
                  </details>
                )}

                {pick.why_now && (
                  <div className="rationale" style={{margin: '0 16px', marginBottom: '16px'}}>
                    <strong>Why Now:</strong> {pick.why_now}
                  </div>
                )}

                {pick.tags && pick.tags.length > 0 && (
                  <div className="tags" style={{margin: '0 16px', marginBottom: '16px'}}>
                    {(Array.isArray(pick.tags) ? pick.tags : pick.tags.split(',')).map((tag, i) => (
                      <span key={i} className="tag">{tag.trim()}</span>
                    ))}
                  </div>
                )}

                <div className="pick-footer" style={{padding: '0 16px'}}>
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
