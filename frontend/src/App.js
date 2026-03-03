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
  const [view, setView] = useState('picks'); // 'picks' or 'cheltenham'
  const [lastRefreshed, setLastRefreshed] = useState(null);

  useEffect(() => {
    fetchPicks();
    fetchTodaySummary();
    setLastRefreshed(new Date());
    // Auto-refresh every 30 minutes
    const interval = setInterval(() => {
      fetchPicks();
      fetchTodaySummary();
      setLastRefreshed(new Date());
    }, 30 * 60 * 1000);
    return () => clearInterval(interval);
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
        // Use summary from API if available, otherwise calculate from picks
        const picks = data.picks;
        
        // If API provides summary, use it directly
        if (data.summary) {
          setResults({
            success: true,
            date: data.date || 'Yesterday',
            picks: picks,
            summary: data.summary
          });
          setResultsLoading(false);
          return;
        }
        
        // Fallback: Calculate summary from picks (support both uppercase and lowercase outcomes)
        const normalizeOutcome = (p) => {
          const outcome = (p.outcome || p.result || p.status || '').toLowerCase();
          return outcome;
        };
        
        const wins = picks.filter(p => normalizeOutcome(p) === 'win').length;
        const places = picks.filter(p => normalizeOutcome(p) === 'placed').length;
        const losses = picks.filter(p => normalizeOutcome(p) === 'loss').length;
        const pending = picks.filter(p => {
          const outcome = normalizeOutcome(p);
          return !outcome || outcome === 'PENDING' || outcome === '';
        }).length;
        
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
            className={view === 'picks' ? 'active' : ''} 
            onClick={() => setView('picks')}
          >
            📅 Today's Picks
          </button>
          <button 
            className={view === 'cheltenham' ? 'active' : ''} 
            onClick={() => setView('cheltenham')}
          >
            🏆 Cheltenham 2026
          </button>
        </div>

        {view === 'picks' && (
          <div className="filter-buttons" style={{ marginTop: '10px' }}>
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
        )}
      </header>

      <main className="picks-container">
        {view === 'cheltenham' ? (
          <CheltenhamView apiUrl={API_BASE_URL} />
        ) : (
          <>
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
                    if (c >= 70) return 'Good';
                    if (c >= 55) return 'Fair';
                    return 'Poor';
                  };
                  
                  const confidenceBuckets = {
                    'Excellent': { count: 0, color: '#10b981', min: 85 },
                    'Good': { count: 0, color: '#FFB84D', min: 70 },
                    'Fair': { count: 0, color: '#FF8C00', min: 55 },
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
            {/* Bet of the Day Banner */}
            {(() => {
              // Find the best pending pick: highest comprehensive_score, not yet settled
              const pending = picks.filter(p => !p.outcome || p.outcome === '' || p.outcome === null);
              const best = pending.length > 0
                ? [...pending].sort((a, b) => (parseInt(b.comprehensive_score) || 0) - (parseInt(a.comprehensive_score) || 0))[0]
                : null;

              if (!best) return null;

              const score = Math.min(parseInt(best.comprehensive_score) || 0, 100);
              const odds = parseFloat(best.odds) || 0;
              const raceTime = best.race_time ? new Date(best.race_time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
              const reasons = (best.selection_reasons || []).slice(0, 3);

              // Next refresh time
              const nextCheck = lastRefreshed ? new Date(lastRefreshed.getTime() + 30 * 60 * 1000) : null;
              const nextCheckStr = nextCheck ? nextCheck.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
              const lastStr = lastRefreshed ? lastRefreshed.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';

              // Score label
              const scoreLabel = score >= 90 ? '🔥 Excellent' : score >= 85 ? '✅ Strong' : '👍 Good';

              // Gap analysis
              const gap = parseFloat(best.score_gap) || 0;
              const nextBestScore = parseFloat(best.next_best_score) || 0;
              const nextBestHorse = best.next_best_horse || '';
              const gapLabel = gap >= 15 ? { text: '🏆 Clear class advantage', color: 'rgba(74,222,128,0.25)', border: '#4ade80' }
                             : gap >= 8  ? { text: '✅ Good lead over rivals', color: 'rgba(250,204,21,0.2)', border: '#facc15' }
                             : gap >= 1  ? { text: '⚠️ Moderate edge — competitive race', color: 'rgba(251,146,60,0.2)', border: '#fb923c' }
                             : gap < 0   ? { text: '❗ Another horse rated higher in this race', color: 'rgba(239,68,68,0.2)', border: '#ef4444' }
                             : null;

              return (
                <div style={{
                  background: 'linear-gradient(135deg, #14532d 0%, #166534 100%)',
                  color: 'white',
                  padding: '16px 20px',
                  borderRadius: '12px',
                  margin: '20px auto',
                  maxWidth: '900px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                }}>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px'}}>
                    <div>
                      <div style={{fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.75, marginBottom: '4px'}}>
                        ⭐ Bet of the Day
                      </div>
                      <div style={{fontSize: '22px', fontWeight: 'bold', lineHeight: '1.2'}}>
                        {best.horse}
                      </div>
                      <div style={{fontSize: '14px', opacity: 0.9, marginTop: '3px'}}>
                        {best.course} · {raceTime} · {odds > 1 ? `${(odds - 1).toFixed(0)}/1 (${odds}dec)` : `${odds}dec`} · Score: {score} {scoreLabel}
                      </div>
                    </div>
                    <div style={{textAlign: 'right', fontSize: '11px', opacity: 0.7, whiteSpace: 'nowrap'}}>
                      <div>Checked: {lastStr}</div>
                      <div>Next: {nextCheckStr}</div>
                    </div>
                  </div>

                  {/* Gap indicator row */}
                  {nextBestScore > 0 && gapLabel && (
                    <div style={{
                      marginTop: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      flexWrap: 'wrap'
                    }}>
                      <div style={{
                        background: gapLabel.color,
                        border: `1px solid ${gapLabel.border}`,
                        borderRadius: '6px',
                        padding: '4px 10px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>
                        {gapLabel.text}
                      </div>
                      <div style={{fontSize: '12px', opacity: 0.8}}>
                        vs{nextBestHorse ? ` ${nextBestHorse}` : ''} · {Math.min(nextBestScore, 100).toFixed(0)}/100
                        {gap !== 0 && (
                          <span style={{marginLeft: '6px', fontWeight: 'bold', color: gap > 0 ? '#4ade80' : '#f87171'}}>
                            ({gap > 0 ? '+' : ''}{gap.toFixed(0)} pts)
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {reasons.length > 0 && (
                    <div style={{marginTop: '10px', fontSize: '13px', opacity: 0.9, display: 'flex', gap: '12px', flexWrap: 'wrap'}}>
                      {reasons.map((r, i) => (
                        <span key={i} style={{background: 'rgba(255,255,255,0.12)', borderRadius: '6px', padding: '2px 8px'}}>
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}

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
              // Safely extract values, handling objects
              const horseName = typeof pick.horse === 'string' ? pick.horse : 'Unknown';
              const courseName = typeof pick.course === 'string' ? pick.course : 'Unknown';
              
              // Extract probabilities and odds first
              const odds = parseFloat(pick.odds || 0);
              const pWin = parseFloat(pick.p_win || 0);
              const pPlace = parseFloat(pick.p_place || 0);
              
              // Calculate ROI from odds and win probability
              // ROI = (Expected Return - Stake) / Stake
              // For WIN bets: Expected Return = odds * p_win
              // ROI% = ((odds * p_win) - 1) * 100
              let roi = 0;
              if (odds > 0 && pWin > 0) {
                roi = ((odds * pWin) - 1);  // Decimal ROI (e.g., 0.25 = 25%)
              }
              
              const belowThreshold = roi < 0.05;  // Less than 5% ROI
              
              // BUDGET-BASED STAKE CALCULATION
              // Use global budget constants - only top 5 picks get budget allocation
              const baseBudgetPerPick = DAILY_BUDGET / MAX_PICKS_PER_DAY;
              const betType = (pick.bet_type || 'WIN').toUpperCase();
              // Use the best available score — prefer combined_confidence but
              // fall back to comprehensive_score so POOR/missing values don't
              // override a high-quality comprehensive score.
              const rawCombined = parseFloat(pick.combined_confidence || 0);
              const rawComp     = parseFloat(pick.comprehensive_score || 0);
              const confidence  = rawCombined >= 55 ? rawCombined
                                : rawComp     >= 55 ? rawComp
                                : Math.max(rawCombined, rawComp);
              const decisionRating = pick.decision_rating || 'RISKY';
              
              // Confidence multiplier: Higher confidence = bigger stake
              // EXCELLENT (85+): 40-50% win chance - 2.0x - GREEN
              // GOOD (70-84): 25-35% win chance - 1.5x - LIGHT AMBER
              // FAIR (55-69): 15-25% win chance - 1.0x - DARK AMBER
              // POOR (under 55): <15% win chance - 0.5x - RED
              let confidenceMultiplier = 1.0;
              let confColor = '#FF8C00'; // Default dark amber
              let confLabel = 'FAIR';
              
              if (confidence >= 85) {
                confidenceMultiplier = 2.0;
                confColor = '#10b981'; // Green
                confLabel = 'EXCELLENT';
              } else if (confidence >= 70) {
                confidenceMultiplier = 1.5;
                confColor = '#FFB84D'; // Light amber
                confLabel = 'GOOD';
              } else if (confidence >= 55) {
                confidenceMultiplier = 1.0;
                confColor = '#FF8C00'; // Dark amber
                confLabel = 'FAIR';
              } else {
                confidenceMultiplier = 0.5;
                confColor = '#ef4444'; // Red
                confLabel = 'POOR';
              }

              // Override for PREMIUM picks (flagged from today's learnings - going proven + high score)
              if (pick.confidence_color === 'gold') {
                confColor = '#B8860B'; // Dark gold
                confLabel = 'PREMIUM';
                if (confidence >= 100) confidenceMultiplier = 2.5;
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
              
              // Check if this is a recommended bet (85+ confidence)
              const isRecommended = pick.recommended_bet === true || confidence >= 85;
              
              return (
              <div key={pick.bet_id || index} className={`pick-card ${belowThreshold ? 'below-threshold' : ''}`}>
                {/* RECOMMENDED BET BANNER for 85+ picks */}
                {isRecommended && (
                  <div style={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: 'white',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    textAlign: 'center',
                    letterSpacing: '1px',
                    borderRadius: '8px 8px 0 0',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}>
                    ⭐ RECOMMENDED BET - Proven 85+ Threshold
                  </div>
                )}
                
                {/* PREMIUM ALERT NOTE - from today's going/form learnings */}
                {pick.alert_note && (
                  <div style={{
                    background: pick.confidence_color === 'gold'
                      ? 'linear-gradient(135deg, #92400e 0%, #b45309 100%)'
                      : '#1e40af',
                    color: 'white',
                    padding: '10px 16px',
                    fontSize: '13px',
                    fontWeight: '600',
                    textAlign: 'center',
                    borderBottom: '2px solid rgba(255,255,255,0.25)',
                    lineHeight: '1.4'
                  }}>
                    {pick.confidence_color === 'gold' ? '★ ' : 'ℹ '}{pick.alert_note}
                  </div>
                )}

                {/* COMBINED CONFIDENCE RATING - Top Prominent Display */}
                <div style={{
                  background: confColor,
                  color: 'white',
                  padding: '16px',
                  borderRadius: isRecommended ? '0 0 0 0' : '8px 8px 0 0',
                  borderRadius: '8px 8px 0 0',
                  marginBottom: '16px',
                  textAlign: 'center',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}>
                  <div style={{fontSize: '18px', fontWeight: 'bold', marginBottom: '8px', letterSpacing: '1px'}}>
                    {confLabel} - {Math.min(confidence, 100).toFixed(0)}/100
                  </div>
                  <div style={{fontSize: '13px', opacity: 0.95}}>
                    {confLabel === 'PREMIUM'   ? 'Premium confidence - going proven + high score ★' :
                     confLabel === 'EXCELLENT' ? 'Excellent confidence - back with 2.0x stake' :
                     confLabel === 'GOOD'      ? 'Good confidence - back with 1.5x stake' :
                     confLabel === 'FAIR'      ? 'Fair confidence - proceed with 1.0x stake' :
                                                'Low confidence - 0.5x stake only'}
                  </div>
                </div>
                
                <div className="pick-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '0 16px'}}>
                  <div>
                    <h2 style={{margin: 0}}>{horseName}</h2>
                    {/* ANALYSIS STATUS BADGE */}
                    {(() => {
                      const coverage = pick.coverage || pick.data_coverage || pick.race_coverage_pct || 0;
                      const isComplete = coverage >= 90;
                      const confScore = pick.comprehensive_score || pick.combined_confidence || 0;
                      const hasScore = confScore > 0;
                      
                      return (
                        <div style={{display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap'}}>
                          {/* Race Coverage Badge */}
                          <div style={{
                            display: 'inline-block',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 'bold',
                            background: isComplete ? '#dcfce7' : '#fee2e2',
                            color: isComplete ? '#166534' : '#991b1b',
                            border: isComplete ? '1px solid #86efac' : '1px solid #fca5a5'
                          }}>
                            {isComplete ? '✓ Analysis' : '⚠ Analysis'} ({coverage.toFixed(0)}% coverage)
                          </div>
                          
                          {/* Confidence Scoring Badge */}
                          <div style={{
                            display: 'inline-block',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 'bold',
                            background: hasScore ? '#dbeafe' : '#fee2e2',
                            color: hasScore ? '#1e40af' : '#991b1b',
                            border: hasScore ? '1px solid #93c5fd' : '1px solid #fca5a5'
                          }}>
                            {hasScore ? '✓ Scored' : '⚠ Not Scored'} ({Math.min(confScore, 100).toFixed(0)}/100)
                          </div>
                        </div>
                      );
                    })()}
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
                      📊 Confidence Details: {Math.min(pick.combined_confidence, 100).toFixed(0)}/100 ({pick.confidence_grade || 'N/A'})
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
                      
                      {/* Next Best Horse Competition Analysis */}
                      {pick.next_best_score > 0 && (
                        <div style={{
                          marginTop: '12px',
                          padding: '10px',
                          background: pick.score_gap < 0 ? '#eff6ff' : pick.score_gap > 10 ? '#dcfce7' : pick.score_gap > 5 ? '#fef3c7' : '#fee2e2',
                          borderRadius: '6px',
                          borderLeft: `3px solid ${pick.score_gap < 0 ? '#3b82f6' : pick.score_gap > 10 ? '#16a34a' : pick.score_gap > 5 ? '#f59e0b' : '#ef4444'}`
                        }}>
                          <div style={{
                            fontSize: '12px',
                            fontWeight: 'bold',
                            color: pick.score_gap < 0 ? '#1d4ed8' : pick.score_gap > 10 ? '#166534' : pick.score_gap > 5 ? '#92400e' : '#991b1b',
                            marginBottom: '4px'
                          }}>
                            🏇 Race Competition
                          </div>
                          <div style={{fontSize: '12px', color: '#374151'}}>
                            <strong>Next best:</strong>{' '}
                            {pick.next_best_horse ? <span style={{fontWeight: 'bold'}}>{pick.next_best_horse}</span> : null}
                            {pick.next_best_horse ? ' · ' : ''}
                            {Math.min(pick.next_best_score, 100).toFixed(0)}/100
                          </div>
                          <div style={{fontSize: '12px', color: '#374151'}}>
                            <strong>Score gap:</strong> {pick.score_gap > 0 ? '+' : ''}{pick.score_gap.toFixed(0)} points
                          </div>
                          <div style={{fontSize: '11px', color: '#6b7280', marginTop: '6px', fontStyle: 'italic'}}>
                            {pick.score_gap < 0 ? `ℹ We also back a higher-rated horse in this race (+${Math.abs(pick.score_gap).toFixed(0)} pts) - both are recommended picks` :
                             pick.score_gap > 10 ? '✓ Dominant position - clear class advantage' :
                             pick.score_gap > 5 ? '⚠ Good edge - moderate competition' :
                             '⚠ Tight race - strong competition from other runners'}
                          </div>
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
        </>
        )}
      </main>
    </div>
  );
}

// Cheltenham Festival Component
function CheltenhamView({ apiUrl }) {
  const [races, setRaces] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState('Tuesday_10_March');
  const [expandedRace, setExpandedRace] = useState(null);
  const [expandedScores, setExpandedScores] = useState({});
  const [raceHorses, setRaceHorses] = useState({});
  const [cheltenhamPicks, setCheltenhamPicks] = useState({});
  const [racesFromPicks, setRacesFromPicks] = useState({});
  const [picksDate, setPicksDate] = useState(null);
  const [totalChanges, setTotalChanges] = useState(0);
  const [savingPicks, setSavingPicks] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    loadRaces();
    loadPicks();
  }, []);

  const loadRaces = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/cheltenham/races`);
      const data = await response.json();
      if (data.success) {
        setRaces(data.races || {});
      }
    } catch (error) {
      console.error('Error loading Cheltenham races:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPicks = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/cheltenham/picks`);
      const data = await response.json();
      if (data.success) {
        // Flatten day-grouped picks into a race_name -> pick map
        const pickMap = {};
        Object.values(data.days || {}).forEach(dayPicks => {
          dayPicks.forEach(pick => {
            pickMap[pick.race_name] = pick;
          });
        });
        setCheltenhamPicks(pickMap);
        setPicksDate(data.pick_date || null);
        setTotalChanges(data.total_changes || 0);

        // Derive race structure from picks (used when DynamoDB races table is empty)
        const derived = {};
        Object.entries(data.days || {}).forEach(([day, dayArr]) => {
          derived[day] = dayArr
            .slice()
            .sort((a, b) => (a.race_time || '').localeCompare(b.race_time || ''))
            .map((p, i) => ({
              raceId:       `${day}_${i}`,
              raceName:     p.race_name,
              raceTime:     p.race_time || '',
              raceGrade:    p.grade,
              raceDistance: p.distance || '',
              totalHorses:  (p.all_horses || []).length,
            }));
        });
        setRacesFromPicks(derived);
      }
    } catch (error) {
      console.error('Error loading Cheltenham picks:', error);
    }
  };

  const triggerPickSave = async () => {
    setSavingPicks(true);
    setSaveMessage('');
    try {
      const response = await fetch(`${apiUrl}/api/cheltenham/picks/save`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        setSaveMessage('Picks saved! Refreshing...');
        await loadPicks();
        setSaveMessage('Picks updated successfully.');
      } else {
        setSaveMessage(`Error: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      setSaveMessage(`Error: ${error.message}`);
    } finally {
      setSavingPicks(false);
    }
  };

  const loadHorses = async (raceId) => {
    if (raceHorses[raceId]) {
      setExpandedRace(expandedRace === raceId ? null : raceId);
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/cheltenham/races/${raceId}`);
      const data = await response.json();
      if (data.success) {
        setRaceHorses({ ...raceHorses, [raceId]: data.horses });
        setExpandedRace(raceId);
      }
    } catch (error) {
      console.error('Error loading horses:', error);
    }
  };

  const getDaysUntil = () => {
    const festivalStart = new Date('2026-03-10T13:30:00');
    const now = new Date();
    const diff = Math.floor((festivalStart - now) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 'LIVE';
  };

  const dayTabs = [
    { key: 'Tuesday_10_March', label: 'Tuesday 10', subtitle: 'Champion Hurdle Day' },
    { key: 'Wednesday_11_March', label: 'Wednesday 11', subtitle: 'Queen Mother Day' },
    { key: 'Thursday_12_March', label: 'Thursday 12', subtitle: 'Stayers Day' },
    { key: 'Friday_13_March', label: 'Friday 13', subtitle: 'Gold Cup Day' }
  ];

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center' }}>Loading Cheltenham Festival...</div>;
  }

  const currentRaces = races[selectedDay] || racesFromPicks[selectedDay] || [];

  return (
    <div style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{ 
        background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
        color: 'white',
        padding: '30px',
        borderRadius: '12px',
        marginBottom: '30px',
        textAlign: 'center'
      }}>
        <h2 style={{ fontSize: '32px', marginBottom: '10px' }}>🏆 Cheltenham Festival 2026</h2>
        <p style={{ fontSize: '16px', opacity: 0.9 }}>Tuesday 10 - Friday 13 March 2026</p>
        <div style={{ 
          background: 'rgba(255,255,255,0.2)',
          padding: '15px',
          borderRadius: '8px',
          marginTop: '15px',
          display: 'inline-block'
        }}>
          <strong>{getDaysUntil()}</strong> days until the festival
        </div>
      </div>

      {/* Picks Summary Banner */}
      {Object.keys(cheltenhamPicks).length > 0 && (
        <div style={{
          background: totalChanges > 0
            ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
            : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          color: 'white',
          padding: '14px 20px',
          borderRadius: '10px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px',
        }}>
          <div>
            <strong style={{ fontSize: '16px' }}>
              {totalChanges > 0
                ? `⚡ ${totalChanges} pick${totalChanges > 1 ? 's' : ''} changed today`
                : '✓ All picks stable today'}
            </strong>
            <span style={{ opacity: 0.85, marginLeft: '12px', fontSize: '14px' }}>
              {Object.keys(cheltenhamPicks).length} races tracked
              {picksDate ? ` · ${picksDate}` : ''}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {saveMessage && (
              <span style={{ fontSize: '13px', opacity: 0.9 }}>{saveMessage}</span>
            )}
            <button
              onClick={triggerPickSave}
              disabled={savingPicks}
              style={{
                background: 'rgba(255,255,255,0.25)',
                color: 'white',
                border: '1px solid rgba(255,255,255,0.5)',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: savingPicks ? 'not-allowed' : 'pointer',
                fontWeight: '600',
                fontSize: '13px',
              }}
            >
              {savingPicks ? 'Saving...' : '↻ Refresh Picks'}
            </button>
          </div>
        </div>
      )}

      {/* Day Tabs */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px', flexWrap: 'wrap' }}>
        {dayTabs.map(day => (
          <button
            key={day.key}
            onClick={() => setSelectedDay(day.key)}
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '15px',
              background: selectedDay === day.key ? '#10b981' : '#f3f4f6',
              color: selectedDay === day.key ? 'white' : '#374151',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600',
              transition: 'all 0.3s'
            }}
          >
            <div>{day.label}</div>
            <div style={{ fontSize: '12px', marginTop: '5px', opacity: 0.8 }}>{day.subtitle}</div>
          </button>
        ))}
      </div>

      {/* Races */}
      {currentRaces.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
          No races loaded yet. Run: python cheltenham_festival_schema.py
        </div>
      ) : (
        currentRaces.map(race => (
          <div key={race.raceId} style={{
            background: '#f9fafb',
            border: '2px solid #e5e7eb',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '20px'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '15px',
              paddingBottom: '15px',
              borderBottom: '2px solid #e5e7eb'
            }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: '22px', marginBottom: '8px' }}>{race.raceName}</h3>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <span style={{ background: 'white', padding: '6px 12px', borderRadius: '6px', fontSize: '14px' }}>
                    ⏰ {race.raceTime}
                  </span>
                  <span style={{ background: '#fbbf24', color: '#92400e', padding: '6px 12px', borderRadius: '6px', fontSize: '14px', fontWeight: '600' }}>
                    {race.raceGrade}
                  </span>
                  <span style={{ background: 'white', padding: '6px 12px', borderRadius: '6px', fontSize: '14px' }}>
                    📏 {race.raceDistance}
                  </span>
                  <span style={{ background: 'white', padding: '6px 12px', borderRadius: '6px', fontSize: '14px' }}>
                    🐴 {race.totalHorses || 0} horses
                  </span>
                </div>
              </div>
              <button
                onClick={() => loadHorses(race.raceId)}
                style={{
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                {expandedRace === race.raceId ? 'Hide' : 'View'} Horses
              </button>
            </div>

            {/* TODAY'S PICK BANNER */}
            {cheltenhamPicks[race.raceName] && (() => {
              const pick = cheltenhamPicks[race.raceName];
              const confColour = pick.confidence === 'HIGH' ? '#d1fae5' : pick.confidence === 'MEDIUM' ? '#fef3c7' : '#fee2e2';
              const confText   = pick.confidence === 'HIGH' ? '#065f46' : pick.confidence === 'MEDIUM' ? '#92400e' : '#991b1b';
              return (
                <div style={{
                  background: confColour,
                  border: `2px solid ${confText}`,
                  borderRadius: '10px',
                  padding: '14px 18px',
                  marginBottom: '14px',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <span style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '1px', color: confText, textTransform: 'uppercase' }}>
                        Today's Pick
                      </span>
                      <div style={{ fontSize: '19px', fontWeight: '700', color: '#1f2937', marginTop: '4px' }}>
                        {pick.horse}
                        <span style={{ fontSize: '15px', fontWeight: '400', color: '#6b7280', marginLeft: '10px' }}>
                          @ {pick.odds}
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        {pick.trainer && <span>T: {pick.trainer}</span>}
                        {pick.jockey && <span style={{ marginLeft: '12px' }}>J: {pick.jockey}</span>}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{
                        background: confText,
                        color: 'white',
                        padding: '6px 14px',
                        borderRadius: '20px',
                        fontSize: '13px',
                        fontWeight: '700',
                      }}>
                        {pick.score} pts · {pick.tier || pick.confidence}
                      </div>
                      {pick.reasons && pick.reasons.length > 0 && (
                        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '6px', maxWidth: '260px', textAlign: 'right' }}>
                          {pick.reasons.slice(0, 2).join(' · ')}
                        </div>
                      )}
                    </div>
                  </div>
                  {pick.pick_changed && pick.previous_horse && (
                    <div style={{
                      marginTop: '10px',
                      paddingTop: '10px',
                      borderTop: '1px solid rgba(0,0,0,0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}>
                      <span style={{
                        background: '#f59e0b',
                        color: 'white',
                        padding: '3px 10px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: '700',
                        letterSpacing: '0.5px',
                      }}>
                        CHANGED
                      </span>
                      <span style={{ fontSize: '13px', color: '#6b7280' }}>
                        Previously: <strong>{pick.previous_horse}</strong>
                        {pick.previous_odds ? ` @ ${pick.previous_odds}` : ''}
                      </span>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* SCORE ANALYSIS PANEL */}
            {cheltenhamPicks[race.raceName] && (cheltenhamPicks[race.raceName].all_horses || []).length > 0 && (() => {
              const pick = cheltenhamPicks[race.raceName];
              const horses = pick.all_horses || [];
              const isOpen = !!expandedScores[race.raceName];
              const tierColor = (tier) => {
                if (!tier) return '#6b7280';
                if (tier.includes('A+'))  return '#7c3aed';
                if (tier.startsWith('A')) return '#1d4ed8';
                if (tier.startsWith('B')) return '#0891b2';
                if (tier.startsWith('C')) return '#059669';
                if (tier.startsWith('D')) return '#d97706';
                return '#6b7280';
              };
              return (
                <div style={{ marginBottom: '14px' }}>
                  <button
                    onClick={() => setExpandedScores(prev => ({ ...prev, [race.raceName]: !prev[race.raceName] }))}
                    style={{
                      width: '100%',
                      background: isOpen ? '#1e3a8a' : '#eff6ff',
                      color: isOpen ? 'white' : '#1e3a8a',
                      border: '2px solid #1e3a8a',
                      padding: '10px 20px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: '700',
                      fontSize: '14px',
                      textAlign: 'left',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <span>📊 Score Analysis — {horses.length} horses ranked</span>
                    <span>{isOpen ? '▲ Hide' : '▼ Show full field'}</span>
                  </button>

                  {isOpen && (
                    <div style={{
                      background: '#f8fafc',
                      border: '2px solid #1e3a8a',
                      borderTop: 'none',
                      borderRadius: '0 0 8px 8px',
                      padding: '16px',
                    }}>
                      {/* Score legend */}
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '14px', fontSize: '12px' }}>
                        {[['A+ ELITE','#7c3aed'],['A ELITE','#1d4ed8'],['B EXCELLENT','#0891b2'],['C STRONG','#059669'],['D FAIR','#d97706'],['E WEAK','#6b7280']].map(([label,col]) => (
                          <span key={label} style={{ background: col, color: 'white', padding: '3px 8px', borderRadius: '4px', fontWeight: '600' }}>{label}</span>
                        ))}
                      </div>

                      {horses.map((h, idx) => {
                        const tc = tierColor(h.tier);
                        return (
                          <div key={idx} style={{
                            background: h.is_surebet_pick ? '#fffbeb' : 'white',
                            border: h.is_surebet_pick ? '2px solid #f59e0b' : '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '12px 14px',
                            marginBottom: '8px',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                              {/* Rank */}
                              <span style={{
                                background: idx === 0 ? '#1e3a8a' : '#e5e7eb',
                                color: idx === 0 ? 'white' : '#6b7280',
                                borderRadius: '50%',
                                width: '28px', height: '28px',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontWeight: '700', fontSize: '13px', flexShrink: 0,
                              }}>{idx + 1}</span>

                              {/* Name */}
                              <span style={{ fontWeight: '700', fontSize: '16px', flex: 1 }}>
                                {h.name}
                                {h.is_surebet_pick && (
                                  <span style={{ background: '#f59e0b', color: 'white', fontSize: '10px', fontWeight: '700', padding: '2px 7px', borderRadius: '10px', marginLeft: '8px', letterSpacing: '0.5px' }}>
                                    PICK
                                  </span>
                                )}
                              </span>

                              {/* Score */}
                              <span style={{ fontWeight: '800', fontSize: '18px', color: tc, minWidth: '48px', textAlign: 'right' }}>
                                {h.score}
                              </span>

                              {/* Tier */}
                              <span style={{ background: tc, color: 'white', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '700', whiteSpace: 'nowrap' }}>
                                {(h.tier || '').trim()}
                              </span>

                              {/* Value rating */}
                              <span style={{ background: '#f3f4f6', color: '#374151', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '600', whiteSpace: 'nowrap' }}>
                                VR: {Number(h.value_rating || 0).toFixed(1)}
                              </span>
                            </div>

                            {/* Trainer / Jockey */}
                            <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '6px', marginLeft: '38px' }}>
                              T: {h.trainer || 'N/A'} &nbsp;|&nbsp; J: {h.jockey || 'N/A'}
                              {h.cheltenham_record && h.cheltenham_record !== 'First time' && (
                                <span style={{ marginLeft: '12px', color: '#059669', fontWeight: '600' }}>
                                  🏆 {h.cheltenham_record}
                                </span>
                              )}
                            </div>

                            {/* Tips */}
                            {(h.tips || []).length > 0 && (
                              <div style={{ marginTop: '8px', marginLeft: '38px', display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                                {h.tips.map((tip, ti) => (
                                  <span key={ti} style={{ background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>
                                    + {tip}
                                  </span>
                                ))}
                                {(h.warnings || []).map((w, wi) => (
                                  <span key={`w${wi}`} style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>
                                    ! {w}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })()}

            {expandedRace === race.raceId && (
              <div style={{ marginTop: '15px' }}>
                {!raceHorses[race.raceId] || raceHorses[race.raceId].length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '30px', color: '#9ca3af', fontStyle: 'italic' }}>
                    No horses added yet. Run: python cheltenham_festival_scraper.py --sample
                  </div>
                ) : (
                  raceHorses[race.raceId].map((horse, idx) => (
                    <div key={idx} style={{
                      background: 'white',
                      padding: '15px',
                      borderRadius: '8px',
                      marginBottom: '10px',
                      borderLeft: '4px solid #10b981',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '18px', fontWeight: '600', marginBottom: '5px' }}>
                          {horse.horseName}
                        </div>
                        <div style={{ display: 'flex', gap: '15px', fontSize: '14px', color: '#6b7280' }}>
                          <span>💰 {horse.currentOdds || 'N/A'}</span>
                          <span>👨‍🏫 {horse.trainer || 'N/A'}</span>
                          <span>🏇 {horse.jockey || 'N/A'}</span>
                          <span>📊 Form: {horse.form || 'N/A'}</span>
                        </div>
                        {horse.researchNotes && horse.researchNotes.length > 0 && (
                          <div style={{ marginTop: '10px', padding: '10px', background: '#f9fafb', borderRadius: '6px', fontSize: '14px' }}>
                            {horse.researchNotes[0]}
                          </div>
                        )}
                      </div>
                      <div style={{
                        padding: '8px 16px',
                        borderRadius: '20px',
                        fontWeight: '600',
                        fontSize: '14px',
                        background: horse.confidenceRank >= 75 ? '#10b981' : horse.confidenceRank >= 50 ? '#fbbf24' : '#ef4444',
                        color: 'white'
                      }}>
                        {horse.confidenceRank}% Confidence
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default App;

