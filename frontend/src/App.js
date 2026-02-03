import React, { useState, useEffect } from 'react';
import './App.css';

// Use API Gateway in eu-west-1
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                     'https://mnybvagd5m.execute-api.eu-west-1.amazonaws.com';

// Budget configuration - €100 daily budget on top 5 picks only
const DAILY_BUDGET = 100;
const MAX_PICKS_PER_DAY = 5;

function App() {
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('today');
  const [results, setResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [todaySummary, setTodaySummary] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);

  useEffect(() => {
    fetchPicks();
    fetchTodaySummary(); // Fetch summary stats on load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const fetchPicks = async () => {
    setLoading(true);
    setError(null);

    try {
      let endpoint;
      if (filter === 'today') {
        // Use /picks/today to show only FUTURE races (upcoming bets)
        endpoint = `${API_BASE_URL}/api/picks/today`;
      } else if (filter === 'greyhounds') {
        endpoint = `${API_BASE_URL}/api/picks/greyhounds`;
      } else {
        endpoint = `${API_BASE_URL}/api/picks`;
      }
      
      console.log('Fetching from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.success !== false) {
        setPicks(data.picks || []);
        // Store system status for "no picks" message
        if (data.last_run && data.next_run) {
          setSystemStatus({
            lastRun: data.last_run,
            nextRun: data.next_run,
            message: data.message
          });
        }
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

  const fetchTodaySummary = async () => {
    try {
      const endpoint = `${API_BASE_URL}/api/results/today`;
      console.log('Fetching summary from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();

      if (data.success && data.summary) {
        setTodaySummary(data.summary);
      }
    } catch (err) {
      console.error('Error fetching summary:', err);
      // Don't set error - summary is optional
    }
  };

  const checkResults = async (dateFilter = 'today') => {
    setResultsLoading(true);
    setError(null);

    try {
      // Fetch results based on date filter
      const endpoint = dateFilter === 'yesterday' 
        ? `${API_BASE_URL}/api/picks/yesterday` 
        : `${API_BASE_URL}/api/results`;
      console.log('Checking results from:', endpoint);
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.success && data.picks) {
        // Calculate summary from picks
        const picks = data.picks;
        // Use lowercase outcome values to match database format
        const wins = picks.filter(p => p.outcome === 'win' || p.outcome === 'placed').length; // Count placed as wins
        const places = picks.filter(p => p.outcome === 'placed').length;
        const losses = picks.filter(p => p.outcome === 'loss').length;
        const pending = picks.filter(p => !p.outcome || p.outcome === 'pending').length;
        
        // Calculate profit/loss based on outcome, stake, and odds
        let totalPL = 0;
        let totalStake = 0;
        picks.forEach(p => {
          const stake = parseFloat(p.stake || 0);
          const odds = parseFloat(p.odds || 0);
          const outcome = p.outcome;
          
          // Check if there's a pre-calculated profit field first
          if (p.profit !== undefined && p.profit !== null) {
            totalPL += parseFloat(p.profit);
            totalStake += stake;
          } else if (outcome === 'win') {
            // Win profit = stake * (odds - 1)
            totalPL += stake * (odds - 1);
            totalStake += stake;
          } else if (outcome === 'placed') {
            // Place profit (assume 1/4 odds for simplicity)
            const placeOdds = 1 + ((odds - 1) * 0.25);
            totalPL += stake * (placeOdds - 1);
            totalStake += stake;
          } else if (outcome === 'loss') {
            // Loss = -stake
            totalPL -= stake;
            totalStake += stake;
          }
          // Pending bets don't count toward P/L or stake
        });
        
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
            🏇 Horses
          </button>
          <button onClick={() => checkResults('today')} className="results-btn" disabled={resultsLoading}>
            {resultsLoading ? '⏳ Checking...' : '📊 Today\'s Results'}
          </button>
          <button onClick={() => checkResults('yesterday')} className="results-btn" disabled={resultsLoading}>
            {resultsLoading ? '⏳ Checking...' : '📈 Yesterday\'s Results'}
          </button>
        </div>
      </header>

      <main className="picks-container">
        {/* Results Summary */}
        {results && results.summary && (
          <div className="results-summary">
            <h2>📊 Today's Results {results.date && `(${results.date})`}</h2>
            
            {/* Separate sections for Horses and Greyhounds */}
            {results.horses && results.horses.summary && (
              <div style={{ marginBottom: '32px' }}>
                <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#333' }}>🏇 Horse Racing</h3>
                <div className="results-grid">
                  <div className="result-stat">
                    <div className="stat-label">Total Picks</div>
                    <div className="stat-value">{results.horses.summary.total_picks}</div>
                  </div>
                  <div className="result-stat win">
                    <div className="stat-label">Wins</div>
                    <div className="stat-value">{results.horses.summary.wins}</div>
                  </div>
                  <div className="result-stat loss">
                    <div className="stat-label">Losses</div>
                    <div className="stat-value">{results.horses.summary.losses}</div>
                  </div>
                  <div className="result-stat pending">
                    <div className="stat-label">Pending</div>
                    <div className="stat-value">{results.horses.summary.pending}</div>
                  </div>
                  <div className="result-stat">
                    <div className="stat-label">Win Rate</div>
                    <div className="stat-value">{results.horses.summary.strike_rate}%</div>
                  </div>
                  <div className={`result-stat ${results.horses.summary.profit >= 0 ? 'profit' : 'loss'}`}>
                    <div className="stat-label">P/L</div>
                    <div className="stat-value">
                      {results.horses.summary.profit >= 0 ? '+' : ''}€{results.horses.summary.profit}
                    </div>
                  </div>
                  <div className={`result-stat ${results.horses.summary.roi >= 0 ? 'profit' : 'loss'}`}>
                    <div className="stat-label">ROI</div>
                    <div className="stat-value">{results.horses.summary.roi}%</div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Combined Summary */}
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '22px', marginBottom: '20px', color: '#1f2937', fontWeight: 'bold' }}>📈 Overall Performance</h3>
              
              {/* Key Performance Indicators - Large Display */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px',
                marginBottom: '24px'
              }}>
                <div style={{
                  background: results.summary.profit >= 0 ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  color: 'white',
                  padding: '24px',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}>
                  <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px', fontWeight: '600' }}>TOTAL PROFIT/LOSS</div>
                  <div style={{ fontSize: '36px', fontWeight: 'bold' }}>
                    {results.summary.profit >= 0 ? '+' : ''}£{results.summary.profit}
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.85, marginTop: '4px' }}>
                    From £{results.summary.total_stake} staked
                  </div>
                </div>
                
                <div style={{
                  background: results.summary.roi >= 0 ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)',
                  color: 'white',
                  padding: '24px',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}>
                  <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px', fontWeight: '600' }}>RETURN ON INVESTMENT</div>
                  <div style={{ fontSize: '36px', fontWeight: 'bold' }}>
                    {results.summary.roi >= 0 ? '+' : ''}{results.summary.roi}%
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.85, marginTop: '4px' }}>
                    Total return: £{results.summary.total_return}
                  </div>
                </div>
                
                <div style={{
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
                  color: 'white',
                  padding: '24px',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}>
                  <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px', fontWeight: '600' }}>WIN RATE</div>
                  <div style={{ fontSize: '36px', fontWeight: 'bold' }}>
                    {results.summary.strike_rate}%
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.85, marginTop: '4px' }}>
                    {results.summary.wins} wins from {results.summary.total_picks} picks
                  </div>
                </div>
              </div>
              
              {/* Detailed Stats Grid */}
              <h4 style={{ fontSize: '16px', marginBottom: '12px', color: '#4b5563', fontWeight: '600' }}>Detailed Breakdown</h4>
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
            
            {/* Bet Type and Confidence Breakdown */}
            <div style={{ marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              {/* Bet Type Breakdown */}
              <div style={{ 
                background: 'white', 
                borderRadius: '12px', 
                padding: '20px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
              }}>
                <h4 style={{ fontSize: '16px', marginBottom: '16px', color: '#1f2937', fontWeight: '600' }}>
                  📊 Bet Type Distribution
                </h4>
                {(() => {
                  const ewBets = results.picks.filter(p => {
                    const bt = (p.bet_type || '').toUpperCase();
                    return bt === 'EW' || bt === 'EACH-WAY' || bt === 'EACH WAY';
                  });
                  const winBets = results.picks.filter(p => {
                    const bt = (p.bet_type || 'WIN').toUpperCase();
                    return bt === 'WIN' || bt === 'W';
                  });
                  const totalBets = results.picks.length;
                  const ewPercent = totalBets > 0 ? ((ewBets.length / totalBets) * 100).toFixed(1) : 0;
                  const winPercent = totalBets > 0 ? ((winBets.length / totalBets) * 100).toFixed(1) : 0;
                  
                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '14px', color: '#6b7280' }}>Each-Way (EW)</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#f59e0b' }}>
                            {ewBets.length}
                          </span>
                          <span style={{ fontSize: '14px', color: '#9ca3af' }}>
                            ({ewPercent}%)
                          </span>
                        </div>
                      </div>
                      <div style={{ 
                        width: '100%', 
                        height: '8px', 
                        background: '#e5e7eb', 
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{ 
                          width: `${ewPercent}%`, 
                          height: '100%', 
                          background: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)',
                          transition: 'width 0.5s ease'
                        }}></div>
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                        <span style={{ fontSize: '14px', color: '#6b7280' }}>Win</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#10b981' }}>
                            {winBets.length}
                          </span>
                          <span style={{ fontSize: '14px', color: '#9ca3af' }}>
                            ({winPercent}%)
                          </span>
                        </div>
                      </div>
                      <div style={{ 
                        width: '100%', 
                        height: '8px', 
                        background: '#e5e7eb', 
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{ 
                          width: `${winPercent}%`, 
                          height: '100%', 
                          background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                          transition: 'width 0.5s ease'
                        }}></div>
                      </div>
                    </div>
                  );
                })()}
              </div>
              
              {/* Confidence Level Breakdown */}
              <div style={{ 
                background: 'white', 
                borderRadius: '12px', 
                padding: '20px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
              }}>
                <h4 style={{ fontSize: '16px', marginBottom: '16px', color: '#1f2937', fontWeight: '600' }}>
                  🎯 Confidence Distribution
                </h4>
                {(() => {
                  const getConfidenceLevel = (conf) => {
                    const c = parseFloat(conf) || 0;
                    if (c >= 85) return 'Excellent';
                    if (c >= 70) return 'Very Good';
                    if (c >= 55) return 'Good';
                    if (c >= 45) return 'Moderate';
                    return 'Poor';
                  };
                  
                  const confidenceBuckets = {
                    'Excellent': { count: 0, color: '#10b981', min: 85 },
                    'Very Good': { count: 0, color: '#90EE90', min: 70 },
                    'Good': { count: 0, color: '#FFB84D', min: 55 },
                    'Moderate': { count: 0, color: '#FF8C00', min: 45 },
                    'Poor': { count: 0, color: '#ef4444', min: 0 }
                  };
                  
                  results.picks.forEach(p => {
                    const level = getConfidenceLevel(p.combined_confidence || p.confidence);
                    if (confidenceBuckets[level]) {
                      confidenceBuckets[level].count++;
                    }
                  });
                  
                  const totalBets = results.picks.length;
                  
                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {Object.entries(confidenceBuckets).map(([level, data]) => {
                        const percent = totalBets > 0 ? ((data.count / totalBets) * 100).toFixed(1) : 0;
                        return (
                          <div key={level}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                              <span style={{ fontSize: '13px', color: '#6b7280' }}>
                                {level} ({data.min}%+)
                              </span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '16px', fontWeight: 'bold', color: data.color }}>
                                  {data.count}
                                </span>
                                <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                                  ({percent}%)
                                </span>
                              </div>
                            </div>
                            <div style={{ 
                              width: '100%', 
                              height: '6px', 
                              background: '#e5e7eb', 
                              borderRadius: '3px',
                              overflow: 'hidden'
                            }}>
                              <div style={{ 
                                width: `${percent}%`, 
                                height: '100%', 
                                background: data.color,
                                transition: 'width 0.5s ease'
                              }}></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            </div>
            </div>

            {/* Detailed picks list - mobile-friendly card layout */}
            {results.picks && results.picks.length > 0 && (
              <div style={{ marginTop: '24px' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#333' }}>Detailed Results</h3>
                <div style={{ 
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
                  gap: '12px'
                }}>
                  {results.picks.map((pick, index) => {
                    const outcome = pick.outcome || 'pending';
                    
                    // Calculate P/L for this pick
                    const stake = parseFloat(pick.stake || 0);
                    const odds = parseFloat(pick.odds || 0);
                    let pl = 0;
                    
                    if (pick.profit !== undefined && pick.profit !== null) {
                      pl = parseFloat(pick.profit);
                    } else if (outcome === 'win') {
                      pl = stake * (odds - 1);
                    } else if (outcome === 'placed') {
                      const placeOdds = 1 + ((odds - 1) * 0.25);
                      pl = stake * (placeOdds - 1);
                    } else if (outcome === 'loss') {
                      pl = -stake;
                    }
                    
                    const outcomeColor = 
                      outcome === 'win' || outcome === 'placed' ? '#10b981' : 
                      outcome === 'loss' ? '#ef4444' : '#6b7280';
                    const outcomeIcon = 
                      outcome === 'win' ? '🏆' : 
                      outcome === 'placed' ? '📍' : 
                      outcome === 'loss' ? '❌' : '⏳';

                    return (
                      <div key={index} style={{
                        background: 'white',
                        borderRadius: '12px',
                        padding: '16px',
                        borderLeft: `4px solid ${outcomeColor}`,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                        transition: 'transform 0.2s, box-shadow 0.2s'
                      }}>
                        {/* Header: Horse name and outcome */}
                        <div style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          alignItems: 'center',
                          marginBottom: '12px'
                        }}>
                          <div style={{ 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            color: '#111',
                            flex: 1
                          }}>
                            {outcomeIcon} {pick.horse || 'Unknown Horse'}
                          </div>
                          <div style={{
                            background: outcomeColor,
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: 'bold'
                          }}>
                            {outcome}
                          </div>
                        </div>

                        {/* Race Details */}
                        <div style={{ 
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: '8px',
                          marginBottom: '12px',
                          fontSize: '13px',
                          color: '#6b7280'
                        }}>
                          <div>
                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>VENUE</div>
                            <div style={{ fontWeight: '500', color: '#374151' }}>{pick.course}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>TIME</div>
                            <div style={{ fontWeight: '500', color: '#374151' }}>{formatTime(pick.race_time)}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>BET TYPE</div>
                            <div style={{ fontWeight: '500', color: '#374151' }}>{pick.bet_type || 'WIN'}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>ODDS</div>
                            <div style={{ fontWeight: '500', color: '#374151' }}>{pick.odds}</div>
                          </div>
                        </div>

                        {/* P/L Banner */}
                        <div style={{
                          background: pl >= 0 ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                          color: 'white',
                          padding: '10px',
                          borderRadius: '8px',
                          textAlign: 'center'
                        }}>
                          <div style={{ fontSize: '11px', opacity: 0.9, marginBottom: '2px' }}>PROFIT/LOSS</div>
                          <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                            {pl >= 0 ? '+' : ''}€{pl.toFixed(2)}
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
            <h3>No Selections Available</h3>
            {systemStatus ? (
              <>
                <p style={{marginBottom: '10px'}}>
                  <strong>Last Run:</strong> {new Date(systemStatus.lastRun).toLocaleString()}
                </p>
                <p style={{marginBottom: '10px'}}>
                  {systemStatus.message || 'No selections met the criteria'}
                </p>
                <p style={{color: '#3b82f6', fontWeight: 'bold'}}>
                  <strong>Running again at:</strong> {new Date(systemStatus.nextRun).toLocaleString()}
                </p>
              </>
            ) : (
              <p>No selections available today</p>
            )}
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
              <div style={{fontSize: '16px', fontWeight: 'bold', marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                <span style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  💰 Daily Budget Management
                </span>
                {picks.length > 0 && picks[0].created_at && (
                  <span style={{fontSize: '14px', opacity: 0.95, fontWeight: 'normal'}}>
                    Last run time: {new Date(picks[0].created_at).toLocaleString('en-GB', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                )}
              </div>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px', fontSize: '14px'}}>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Daily Budget</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>€{DAILY_BUDGET}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Max Picks/Day</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>{MAX_PICKS_PER_DAY}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Today's Picks</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>{Math.min(picks.length, MAX_PICKS_PER_DAY)}</div>
                </div>
                <div>
                  <div style={{opacity: 0.9, marginBottom: '4px', fontSize: '12px'}}>Base per Pick</div>
                  <div style={{fontSize: '20px', fontWeight: 'bold'}}>€{(DAILY_BUDGET / MAX_PICKS_PER_DAY).toFixed(0)}</div>
                </div>
              </div>
              <div style={{marginTop: '12px', fontSize: '12px', opacity: 0.9, lineHeight: '1.5'}}>
                Stakes: EXCELLENT (85+) = 2.5x, VERY GOOD (70-84) = 2.0x, GOOD (55-69) = 1.5x, MODERATE (45-54) = 1.0x, POOR (under 45) = 0.5x. ROI bonus: 150%+ = 1.5x, 100-149% = 1.25x
              </div>
            </div>

            <div className="picks-summary" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <span>Showing top {Math.min(5, picks.length)} of {picks.length} selections</span>
              {picks.length > 0 && picks[0].timestamp && (
                <span style={{fontSize: '11px', opacity: 0.7}}>
                  Last run: {new Date(picks[0].timestamp).toLocaleString('en-GB', {
                    day: '2-digit',
                    month: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              )}
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
              // Use global budget constants - only top 5 picks get budget allocation
              const baseBudgetPerPick = DAILY_BUDGET / MAX_PICKS_PER_DAY;
              
              const odds = parseFloat(pick.odds || 0);
              const pWin = parseFloat(pick.p_win || 0);
              const pPlace = parseFloat(pick.p_place || 0);
              const betType = (pick.bet_type || 'WIN').toUpperCase();
              const confidence = parseFloat(pick.combined_confidence || 0);
              const decisionRating = pick.decision_rating || 'RISKY';
              
              // Confidence multiplier: Higher confidence = bigger stake
              // EXCELLENT (85+): 2.5x - GREEN (exceptional)
              // VERY GOOD (70-84): 2.0x - LIGHT GREEN (strong)
              // GOOD (55-69): 1.5x - LIGHT AMBER (solid)
              // MODERATE (45-54): 1.0x - DARK AMBER (marginal)
              // POOR (under 45): 0.5x - RED (avoid)
              let confidenceMultiplier = 1.0;
              let confColor = '#FF8C00'; // Default dark amber
              let confLabel = 'MODERATE';
              
              if (confidence >= 85) {
                confidenceMultiplier = 2.5;
                confColor = '#10b981'; // Green
                confLabel = 'EXCELLENT';
              } else if (confidence >= 70) {
                confidenceMultiplier = 2.0;
                confColor = '#90EE90'; // Light green
                confLabel = 'VERY GOOD';
              } else if (confidence >= 55) {
                confidenceMultiplier = 1.5;
                confColor = '#FFB84D'; // Light amber
                confLabel = 'GOOD';
              } else if (confidence >= 45) {
                confidenceMultiplier = 1.0;
                confColor = '#FF8C00'; // Dark amber
                confLabel = 'MODERATE';
              } else {
                confidenceMultiplier = 0.5;
                confColor = '#ef4444'; // Red
                confLabel = 'POOR';
              }
              
              // ROI multiplier: Better value = bigger stake
              // 150%+ ROI: 1.5x
              // 100-149% ROI: 1.25x
              // 50-99% ROI: 1.0x
              // <50% ROI: 0.75x
              let roiMultiplier = 1.0;
              if (roi >= 1.5) {
                roiMultiplier = 1.5;
              } else if (roi >= 1.0) {
                roiMultiplier = 1.25;
              } else if (roi < 0.5) {
                roiMultiplier = 0.75;
              }
              
              // Calculate final stake
              let stake = baseBudgetPerPick * confidenceMultiplier * roiMultiplier;
              
              // Each Way bets need double (half on win, half on place)
              if (betType === 'EW') {
                stake = stake * 2;
              }
              
              // Round to nearest €1
              stake = Math.round(stake);
              
              // Apply sensible min/max limits
              if (betType === 'EW') {
                stake = Math.max(4, Math.min(stake, 100)); // €2-50 each way (€4-100 total)
              } else {
                stake = Math.max(2, Math.min(stake, 50)); // €2-50 win
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
                {/* COMBINED CONFIDENCE RATING - Top Prominent Display */}
                <div style={{
                  background: confColor,
                  color: 'white',
                  padding: '16px',
                  borderRadius: '8px 8px 0 0',
                  marginBottom: '16px',
                  textAlign: 'center',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}>
                  <div style={{fontSize: '18px', fontWeight: 'bold', marginBottom: '8px', letterSpacing: '1px'}}>
                    {confLabel} - {confidence.toFixed(0)}/100
                  </div>
                  <div style={{fontSize: '13px', opacity: 0.95}}>
                    {confidence >= 60 ? 'Strong confidence - 2.0x stake' :
                     confidence >= 40 ? 'Good bet - 1.3x stake' :
                     confidence >= 25 ? 'Proceed with caution - 0.8x stake' :
                     'Weak signals - 0.4x stake'}
                  </div>
                </div>
                
                <div className="pick-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '0 16px'}}>
                  <div>
                    <h2 style={{margin: 0}}>{horseName}</h2>
                  </div>
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
                    💰 RECOMMENDED STAKE (from €100/day budget)
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '20px'}}>
                    <div style={{flex: 1}}>
                      <div style={{fontSize: '36px', fontWeight: 'bold', marginBottom: '8px'}}>
                        €{stake.toFixed(0)}
                      </div>
                      <div style={{fontSize: '13px', opacity: 0.9, lineHeight: '1.4'}}>
                        {betType === 'EW' 
                          ? `€${(stake/2).toFixed(0)} Win + €${(stake/2).toFixed(0)} Place (Each Way)` 
                          : `Win bet (confidence: ${confidence.toFixed(0)}%)`
                        }
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '6px', fontStyle: 'italic'}}>
                        Top {MAX_PICKS_PER_DAY} picks selected • <span style={{color: confColor, fontWeight: 'bold'}}>{confLabel}</span> confidence ({confidence.toFixed(0)}%)
                      </div>
                    </div>
                    <div style={{textAlign: 'right', borderLeft: '2px solid rgba(255,255,255,0.3)', paddingLeft: '20px'}}>
                      <div style={{fontSize: '13px', opacity: 0.9, marginBottom: '4px'}}>
                        Potential Win:
                      </div>
                      <div style={{fontSize: '24px', fontWeight: 'bold', color: '#a7f3d0'}}>
                        €{profit.toFixed(0)}
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.85, marginTop: '6px'}}>
                        Expected Value: {expectedProfit > 0 ? '+' : ''}€{expectedProfit.toFixed(0)}
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
