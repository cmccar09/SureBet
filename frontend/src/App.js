import React, { useState, useEffect } from 'react';
import './App.css';

// Use API Gateway in eu-west-1
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                     'https://e5na6ldp35.execute-api.eu-west-1.amazonaws.com/prod';

// Budget configuration - £500 monthly budget
const MONTHLY_BUDGET = 500;
const DAILY_BUDGET = MONTHLY_BUDGET / 30;

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
    // Show instructions for running greyhound picks locally
    setError('🐕 To generate Greyhound picks, run on your local machine: .\\generate_todays_picks.ps1 -Sport greyhounds');
    
    // Auto-refresh after user has time to run it
    setTimeout(() => {
      setError('Refreshing picks...');
      fetchPicks();
      setTimeout(() => setError(null), 2000);
    }, 30000); // 30 seconds
  };

  const checkResults = async () => {
    setResultsLoading(true);
    setError(null);

    try {
      // Fetch yesterday's results
      const endpoint = `${API_BASE_URL}/picks/yesterday`;
      console.log('Checking yesterday results from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.success && data.picks) {
        // Calculate summary from picks
        const picks = data.picks;
        const wins = picks.filter(p => p.outcome === 'WON').length;
        const places = picks.filter(p => p.outcome === 'PLACED').length;
        const losses = picks.filter(p => p.outcome === 'LOST').length;
        const pending = picks.filter(p => !p.outcome || p.outcome === 'PENDING').length;
        
        const totalPL = picks.reduce((sum, p) => sum + (parseFloat(p.profit_loss) || 0), 0);
        const totalStake = picks.length; // £1 per pick
        const totalReturn = totalStake + totalPL;
        const roi = totalStake > 0 ? ((totalPL / totalStake) * 100) : 0;
        const strikeRate = (wins + places) > 0 && picks.length > 0 ? 
          (((wins + places) / picks.length) * 100) : 0;

        setResults({
          success: true,
          date: data.date || 'Yesterday',
          picks: picks,
          summary: {
            total_picks: picks.length,
            wins: wins,
            places: places,
            losses: losses,
            pending: pending,
            total_stake: totalStake.toFixed(2),
            total_return: totalReturn.toFixed(2),
            profit: totalPL.toFixed(2),
            roi: roi.toFixed(1),
            strike_rate: strikeRate.toFixed(1)
          }
        });
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
      // UK/Ireland time (Europe/Dublin timezone = GMT/IST)
      const time = date.toLocaleTimeString('en-IE', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false,
        timeZone: 'Europe/Dublin'
      });
      
      // Determine if GMT or IST (Irish Summer Time)
      const month = date.getMonth();
      const isWinter = month < 2 || month > 9; // Jan, Feb, Nov, Dec = GMT
      const timezone = isWinter ? 'GMT' : 'IST';
      
      return `${time} ${timezone}`;
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
        <h1>🏇 SureBet Betting</h1>
        <p>The most advanced super Intelligence AI Betting Platform</p>
        
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
            {refreshing ? '⏳ Generating...' : '� Greyhounds'}
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
            <h2>📊 Yesterday's Results {results.date && `(${results.date})`}</h2>
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

            {/* Detailed picks list */}
            {results.picks && results.picks.length > 0 && (
              <div style={{ marginTop: '24px' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '16px', color: '#333' }}>Detailed Results</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {results.picks.map((pick, index) => {
                    const outcome = pick.outcome || 'PENDING';
                    const pl = parseFloat(pick.profit_loss) || 0;
                    const outcomeColor = 
                      outcome === 'WON' ? '#10b981' : 
                      outcome === 'PLACED' ? '#f59e0b' : 
                      outcome === 'LOST' ? '#ef4444' : '#6b7280';
                    const outcomeIcon = 
                      outcome === 'WON' ? '🏆' : 
                      outcome === 'PLACED' ? '📍' : 
                      outcome === 'LOST' ? '❌' : '⏳';

                    return (
                      <div key={index} style={{
                        background: 'white',
                        padding: '16px',
                        borderRadius: '8px',
                        border: `2px solid ${outcomeColor}`,
                        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px' }}>
                              {outcomeIcon} {pick.horse || 'Unknown Horse'}
                            </div>
                            <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '4px' }}>
                              {pick.course} • {formatTime(pick.race_time)} • {pick.bet_type}
                            </div>
                            <div style={{ fontSize: '14px', color: '#6b7280' }}>
                              Odds: {pick.odds}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ 
                              fontSize: '18px', 
                              fontWeight: 'bold', 
                              color: outcomeColor,
                              marginBottom: '4px'
                            }}>
                              {outcome}
                            </div>
                            <div style={{ 
                              fontSize: '16px', 
                              fontWeight: 'bold',
                              color: pl >= 0 ? '#10b981' : '#ef4444'
                            }}>
                              {pl >= 0 ? '+' : ''}€{pl.toFixed(2)}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

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
            {/* Budget Summary Banner */}
            <div style={{
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              color: 'white',
              padding: '20px',
              borderRadius: '12px',
              margin: '20px auto',
              maxWidth: '900px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}>
              <div style={{fontSize: '16px', fontWeight: 'bold', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px'}}>
                💰 Daily Budget Management
              </div>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px', fontSize: '14px'}}>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Monthly Budget</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>£{MONTHLY_BUDGET}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Daily Allocation</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>£{DAILY_BUDGET.toFixed(2)}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Total Picks</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>{picks.length}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Base per Pick</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>£{(DAILY_BUDGET / picks.length).toFixed(2)}</div>
                </div>
              </div>
              <div style={{marginTop: '12px', fontSize: '12px', opacity: 0.9, lineHeight: '1.5'}}>
                ℹ️ Stakes are adjusted by confidence (0.5x-2.0x) and ROI (0.75x-1.5x). GREEN picks (75%+ confidence, 20%+ ROI) get 2x stake!
              </div>
            </div>

            <div className="picks-summary">
              Showing top {Math.min(5, picks.length)} of {picks.length} selections
            </div>
            <div className="picks-grid">
            {picks
              .sort((a, b) => {
                // Sort by race_time - soonest first
                const timeA = new Date(a.race_time || '9999-12-31').getTime();
                const timeB = new Date(b.race_time || '9999-12-31').getTime();
                return timeA - timeB;
              })
              .slice(0, 5).map((pick, index) => {
              const roi = parseFloat(pick.roi || 0);
              const belowThreshold = roi < 0.05;
              
              // Safely extract values, handling objects
              const horseName = typeof pick.horse === 'string' ? pick.horse : 'Unknown';
              const courseName = typeof pick.course === 'string' ? pick.course : 'Unknown';
              
              // BUDGET-BASED STAKE CALCULATION
              // Use global budget constants defined at top of file
              const totalPicks = picks.length;
              const baseBudgetPerPick = DAILY_BUDGET / Math.max(totalPicks, 1);
              
              const odds = parseFloat(pick.odds || 0);
              const pWin = parseFloat(pick.p_win || 0);
              const pPlace = parseFloat(pick.p_place || 0);
              const betType = (pick.bet_type || 'WIN').toUpperCase();
              const confidence = parseFloat(pick.combined_confidence || 0);
              const decisionRating = pick.decision_rating || 'RISKY';
              
              // Confidence multiplier: Higher confidence = bigger stake
              // GREEN (DO IT, 75%+ conf): 2.0x
              // HIGH (60-74% conf): 1.5x
              // MODERATE (45-59% conf): 1.0x
              // LOW (<45% conf): 0.5x
              let confidenceMultiplier = 1.0;
              if (decisionRating === 'DO IT' && confidence >= 75) {
                confidenceMultiplier = 2.0; // Double stake for GREEN picks
              } else if (confidence >= 60) {
                confidenceMultiplier = 1.5; // 50% more for HIGH confidence
              } else if (confidence < 45) {
                confidenceMultiplier = 0.5; // Half stake for LOW confidence
              }
              
              // ROI multiplier: Better value = bigger stake
              // 20%+ ROI: 1.5x
              // 15-19% ROI: 1.25x
              // 10-14% ROI: 1.0x
              // <10% ROI: 0.75x
              let roiMultiplier = 1.0;
              if (roi >= 20) {
                roiMultiplier = 1.5;
              } else if (roi >= 15) {
                roiMultiplier = 1.25;
              } else if (roi < 10) {
                roiMultiplier = 0.75;
              }
              
              // Calculate final stake
              let stake = baseBudgetPerPick * confidenceMultiplier * roiMultiplier;
              
              // Each Way bets need double (half on win, half on place)
              if (betType === 'EW') {
                stake = stake * 2;
              }
              
              // Round to nearest £1
              stake = Math.round(stake);
              
              // Apply sensible min/max limits
              if (betType === 'EW') {
                stake = Math.max(4, Math.min(stake, 100)); // £2-50 each way (£4-100 total)
              } else {
                stake = Math.max(2, Math.min(stake, 50)); // £2-50 win
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
              
              // Get decision rating styling (already declared above, just get score here)
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
                  <span className="time">{formatTime(pick.race_time)}</span>
                </div>
                
                {/* RECOMMENDED STAKE - Clear and Prominent */}
                <div style={{
                  background: decisionRating === 'DO IT' 
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' 
                    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '20px',
                  borderRadius: '12px',
                  margin: '16px',
                  marginBottom: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}>
                  <div style={{fontSize: '14px', opacity: 0.95, marginBottom: '8px', fontWeight: '600', letterSpacing: '0.5px'}}>
                    💰 RECOMMENDED STAKE (from £500/month budget)
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '20px'}}>
                    <div style={{flex: 1}}>
                      <div style={{fontSize: '36px', fontWeight: 'bold', marginBottom: '8px'}}>
                        £{stake.toFixed(0)}
                      </div>
                      <div style={{fontSize: '13px', opacity: 0.9, lineHeight: '1.4'}}>
                        {betType === 'EW' 
                          ? `£${(stake/2).toFixed(0)} Win + £${(stake/2).toFixed(0)} Place (Each Way)` 
                          : `Win bet (confidence: ${confidence.toFixed(0)}%)`
                        }
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '6px', fontStyle: 'italic'}}>
                        {totalPicks} picks today • {confidenceMultiplier === 2.0 ? '🟢 GREEN - Double stake!' : 
                         confidenceMultiplier === 1.5 ? '🟡 HIGH confidence' : 
                         confidenceMultiplier === 0.5 ? '🔴 LOW confidence - reduced' : 
                         '🟠 MODERATE confidence'}
                      </div>
                    </div>
                    <div style={{textAlign: 'right', borderLeft: '2px solid rgba(255,255,255,0.3)', paddingLeft: '20px'}}>
                      <div style={{fontSize: '13px', opacity: 0.9, marginBottom: '4px'}}>
                        Potential Win:
                      </div>
                      <div style={{fontSize: '24px', fontWeight: 'bold', color: '#a7f3d0'}}>
                        £{profit.toFixed(0)}
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '6px'}}>
                        Expected Value: {expectedProfit > 0 ? '+' : ''}£{expectedProfit.toFixed(0)}
                      </div>
                      <div style={{fontSize: '11px', opacity: 0.75, marginTop: '4px'}}>
                        ({roi.toFixed(1)}% ROI × {roiMultiplier.toFixed(2)}x)
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

                <div className="pick-footer" style={{padding: '0 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <span className="timestamp">
                    Last updated: {new Date(pick.timestamp).toLocaleString('en-GB', { 
                      hour: '2-digit', 
                      minute: '2-digit',
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric'
                    })}
                  </span>
                  <span style={{fontSize: '11px', color: '#10b981', fontWeight: 'bold'}}>
                    ✓ ACTIVE
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
