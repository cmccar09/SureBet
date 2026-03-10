import React, { useState, useEffect } from 'react';
import './App.css';

// Use API Gateway in eu-west-1
const API_BASE_URL = process.env.REACT_APP_API_URL || 
                     'https://mnybvagd5m.execute-api.eu-west-1.amazonaws.com';

// Budget configuration - €100 daily budget on top 5 picks only
const DAILY_BUDGET = 100;
const MAX_PICKS_PER_DAY = 5; // eslint-disable-line no-unused-vars

// Known mares for gender-aware label
const KNOWN_MARES = new Set([
  'Lossiemouth','Bambino Fever','Dinoblue','Wodhooh','Jade De Grugy',
  'Brighterdaysahead','Honeysuckle','Epatante','Impaire Et Passe',
]);

function buildWhyWins(pick) {
  if (!pick) return null;

  // Horse-specific overrides — full curated text
  const OVERRIDES = {
    'Old Park Star': 'Nicky Henderson / Nico de Boinville · 3+ consecutive wins · score 139 · dominant 51pt lead over next rival',
  };
  if (OVERRIDES[pick.horse]) return OVERRIDES[pick.horse];

  const reasons = pick.reasons || [];
  const parts = [];

  // Trainer / jockey
  if (pick.trainer && pick.jockey) {
    parts.push(`${pick.trainer} / ${pick.jockey}`);
  } else if (pick.trainer) {
    parts.push(pick.trainer);
  }

  // Key scoring signals → plain English
  const r = reasons.map(s => s.toLowerCase());
  if (r.some(s => s.includes('defending')))         parts.push('defending champion');
  if (r.some(s => s.includes('won this exact race'))) parts.push('has won this exact race before');
  if (r.some(s => s.includes('festival winner') || s.includes('previous festival'))) parts.push('previous Festival winner');
  if (r.some(s => s.includes('grade 1 winner')))    parts.push('Grade 1 winner');
  if (r.some(s => s.includes('graded winner')))     parts.push('graded winner this season');
  if (r.some(s => s.includes('unbeaten') || s.includes('4+ wins'))) parts.push('unbeaten run in form');
  if (r.some(s => s.includes('3+ consecutive') || s.includes('4+ consecutive'))) parts.push('3+ consecutive wins');
  else if (r.some(s => s.includes('2 consecutive'))) parts.push('2 consecutive wins');
  if (r.some(s => s.includes('ground suits')))      parts.push('ground suits perfectly');
  if (r.some(s => s.includes('strong market confidence') || s.includes('odds-on'))) parts.push('strongly backed in market');
  if (r.some(s => s.includes('improving')))         parts.push('on the upgrade');
  if (r.some(s => s.includes('finishes strongly'))) parts.push('finishes strongly — festival stamina');
  if (r.some(s => s.includes('up in distance')))    parts.push('step up in distance suits');

  // Score / gap context
  const score = parseFloat(pick.score || 0);
  const gap   = parseFloat(pick.score_gap || 0);
  const tier  = (pick.tier || '');
  if (tier.includes('A+'))      parts.push(`A+ ELITE — score ${score}`);
  else if (tier.includes('A ') || tier.startsWith('A ')) parts.push(`A ELITE — score ${score}`);
  else if (score > 0)           parts.push(`score ${score}`);
  if (gap >= 20) parts.push(`dominant ${gap}pt lead over next rival`);
  else if (gap >= 10) parts.push(`${gap}pt clear of next rival`);
  else if (gap >= 5)  parts.push(`${gap}pt advantage`);

  if (parts.length === 0) return null;
  return parts.join(' · ');
}

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>🏆 Cheltenham Festival 2026</h1>
        <p>10–13 March 2026 · AI-Powered Race Analysis</p>
      </header>

      <main className="picks-container">
        <CheltenhamView apiUrl={API_BASE_URL} />
      </main>
    </div>
  );
}

// Cheltenham Festival Component
function CheltenhamView({ apiUrl }) {
  const [races, setRaces] = useState({});
  const [loading, setLoading] = useState(true);
  // Auto-select the current/next festival day (advances after ~18:00 each race day)
  const getInitialDay = () => {
    const now = new Date();
    const cutoffs = [
      { key: 'Tuesday_10_March',   cutoff: new Date('2026-03-10T18:00:00') },
      { key: 'Wednesday_11_March', cutoff: new Date('2026-03-11T18:00:00') },
      { key: 'Thursday_12_March',  cutoff: new Date('2026-03-12T18:00:00') },
      { key: 'Friday_13_March',    cutoff: new Date('2026-03-13T23:59:00') },
    ];
    const active = cutoffs.find(d => now < d.cutoff);
    return active ? active.key : 'Friday_13_March';
  };
  const [selectedDay, setSelectedDay] = useState(getInitialDay);
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
        const newRaceHorses = {};
        Object.entries(data.days || {}).forEach(([day, dayArr]) => {
          const sorted = dayArr
            .slice()
            .sort((a, b) => (a.race_time || '').localeCompare(b.race_time || ''));
          derived[day] = sorted.map((p, i) => ({
            raceId:       `${day}_${i}`,
            raceName:     p.race_name,
            raceTime:     p.race_time || '',
            raceGrade:    p.grade,
            raceDistance: p.distance || '',
            totalHorses:  (p.all_horses || []).length,
          }));
          // Pre-populate expanded horse view from all_horses already in picks data
          sorted.forEach((p, i) => {
            const raceId = `${day}_${i}`;
            if (p.all_horses && p.all_horses.length > 0) {
              newRaceHorses[raceId] = p.all_horses.map(h => ({
                horseName:         h.name,
                currentOdds:       h.odds || 'N/A',
                trainer:           h.trainer || '',
                jockey:            h.jockey || '',
                form:              '',
                score:             h.score,
                tier:              h.tier,
                value_rating:      h.value_rating,
                tips:              h.tips || [],
                warnings:          h.warnings || [],
                cheltenham_record: h.cheltenham_record || '',
                is_surebet_pick:   h.is_surebet_pick,
                confidenceRank:    Math.min(100, Math.round(((h.score || 0) / 211) * 100)),
                researchNotes:     (h.tips || []),
              }));
            }
          });
        });
        setRacesFromPicks(derived);
        setRaceHorses(prev => ({ ...prev, ...newRaceHorses }));
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

  const loadHorses = async (raceId, raceName) => {
    // Toggle off if already open
    if (expandedRace === raceId) {
      setExpandedRace(null);
      return;
    }
    // Use cheltenhamPicks all_horses if available (avoids raceId key-mismatch problem)
    if (raceName && cheltenhamPicks[raceName]?.all_horses?.length > 0) {
      setExpandedRace(raceId);
      return;
    }
    // Fall back to raceHorses cache
    if (raceHorses[raceId]) {
      setExpandedRace(raceId);
      return;
    }
    // Last resort: fetch from API
    try {
      const response = await fetch(`${apiUrl}/api/cheltenham/races/${raceId}`);
      const data = await response.json();
      if (data.success && data.horses) {
        setRaceHorses({ ...raceHorses, [raceId]: data.horses });
      }
      setExpandedRace(raceId);
    } catch (error) {
      console.error('Error loading horses:', error);
      setExpandedRace(raceId);
    }
  };

  const getDaysUntil = () => {
    const festivalStart = new Date('2026-03-10T13:30:00');
    const now = new Date();
    const diff = Math.floor((festivalStart - now) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 'LIVE';
  };

  // Mark days as complete once their races are done
  const now_tabs = new Date();
  const dayTabs = [
    { key: 'Tuesday_10_March',   label: 'Tuesday 10',   subtitle: now_tabs >= new Date('2026-03-10T18:00:00') ? '✅ Complete — 7/7 races' : 'Champion Hurdle Day',  complete: now_tabs >= new Date('2026-03-10T18:00:00') },
    { key: 'Wednesday_11_March', label: 'Wednesday 11', subtitle: now_tabs >= new Date('2026-03-11T18:00:00') ? '✅ Complete — 7/7 races' : 'Ladies Day',             complete: now_tabs >= new Date('2026-03-11T18:00:00') },
    { key: 'Thursday_12_March',  label: 'Thursday 12',  subtitle: now_tabs >= new Date('2026-03-12T18:00:00') ? '✅ Complete — 7/7 races' : 'St Patrick\'s Day Eve',  complete: now_tabs >= new Date('2026-03-12T18:00:00') },
    { key: 'Friday_13_March',    label: 'Friday 13',    subtitle: now_tabs >= new Date('2026-03-13T18:00:00') ? '✅ Complete — 7/7 races' : 'Gold Cup Day',           complete: now_tabs >= new Date('2026-03-13T18:00:00') },
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

      {/* ── FESTIVAL TOP 3 NAPS ── */}
      {Object.keys(cheltenhamPicks).length > 0 && (() => {
        // Only include picks from days that haven't finished yet (cutoff 18:00 each day)
        const now_naps = new Date();
        const dayCutoffs = {
          Tuesday_10_March:   new Date('2026-03-10T18:00:00'),
          Wednesday_11_March: new Date('2026-03-11T18:00:00'),
          Thursday_12_March:  new Date('2026-03-12T18:00:00'),
          Friday_13_March:    new Date('2026-03-13T23:59:00'),
        };
        const allPicks = Object.values(cheltenhamPicks).filter(p => {
          if (p.bet_tier !== 'BETTING_PICK' && p.recommendation !== 'BETTING_PICK') return false;
          const cutoff = dayCutoffs[p.day];
          return cutoff && now_naps < cutoff; // skip completed days
        });
        const top3 = allPicks
          .slice()
          .sort((a, b) => parseFloat(b.score || 0) - parseFloat(a.score || 0))
          .slice(0, 3);
        if (top3.length === 0) return null;
        const dayLabel = (day) => {
          const map = {
            Tuesday_10_March: 'Tue 10 Mar',
            Wednesday_11_March: 'Wed 11 Mar',
            Thursday_12_March: 'Thu 12 Mar',
            Friday_13_March: 'Fri 13 Mar',
          };
          return map[day] || day;
        };
        const medals = ['🥇', '🥈', '🥉'];
        const colours = [
          { bg: 'linear-gradient(135deg,#78350f 0%,#92400e 100%)', border: '#d97706', badge: '#d97706' },
          { bg: 'linear-gradient(135deg,#1e3a5f 0%,#1e40af 100%)', border: '#3b82f6', badge: '#3b82f6' },
          { bg: 'linear-gradient(135deg,#1a0d2e 0%,#2d1b4e 100%)', border: '#9333ea', badge: '#9333ea' },
        ];
        return (
          <div style={{
            background: 'linear-gradient(135deg,#0d1117 0%,#1a2035 60%,#0d1117 100%)',
            border: '2px solid #d97706',
            borderRadius: '12px',
            padding: '18px 22px',
            marginBottom: '20px',
          }}>
            <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '1.5px',
              textTransform: 'uppercase', color: '#d97706', marginBottom: '4px' }}>
              ⭐ Festival NAPs — Top 3 Picks of the Week
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))',
              gap: '12px', marginTop: '10px' }}>
              {top3.map((pick, i) => (
                <div key={pick.race_name} style={{
                  background: colours[i].bg,
                  border: `2px solid ${colours[i].border}`,
                  borderRadius: '10px',
                  padding: '14px 16px',
                  color: 'white',
                }}>
                  <div style={{ fontSize: '11px', opacity: 0.75, marginBottom: '3px' }}>
                    {medals[i]} {pick.race_name} · {dayLabel(pick.day)}
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: '800', marginBottom: '4px' }}>
                    {pick.horse}
                  </div>
                  <div style={{ fontSize: '13px', opacity:0.85, marginBottom:'6px' }}>
                    {pick.trainer && <span>T: {pick.trainer}</span>}
                    {pick.jockey && <span style={{ marginLeft: '10px' }}>J: {pick.jockey}</span>}
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.35)',
                      borderRadius: '6px', padding: '3px 9px', fontSize: '13px', fontWeight: '700',
                    }}>
                      Score {pick.score}
                    </span>
                    <span style={{
                      background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.35)',
                      borderRadius: '6px', padding: '3px 9px', fontSize: '13px', fontWeight: '700',
                    }}>
                      +{pick.score_gap} gap
                    </span>
                    <span style={{
                      background: colours[i].badge, borderRadius: '6px',
                      padding: '3px 9px', fontSize: '13px', fontWeight: '800',
                    }}>
                      {pick.odds}
                    </span>
                  </div>
                  {/* WHY THIS WINS — NAP card */}
                  {(() => {
                    const whyText = buildWhyWins(pick);
                    if (!whyText) return null;
                    const isMare = KNOWN_MARES.has(pick.horse);
                    return (
                      <div style={{
                        marginTop: '10px',
                        padding: '7px 10px',
                        background: 'rgba(0,0,0,0.2)',
                        borderRadius: '5px',
                        borderLeft: `3px solid ${colours[i].border}`,
                      }}>
                        <div style={{ fontSize: '9px', fontWeight: '700', textTransform: 'uppercase',
                          letterSpacing: '0.08em', color: colours[i].border, marginBottom: '2px' }}>
                          {isMare ? 'Why She Wins' : 'Why He Wins'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.8)', lineHeight: '1.5' }}>
                          {whyText}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── TODAY'S TOP 3 BETS ── */}
      {Object.keys(cheltenhamPicks).length > 0 && (() => {
        // Use same 18:00 cutoff as getInitialDay — advance to next day after races finish
        const now = new Date();
        const festivalDays = [
          { key: 'Tuesday_10_March',   cutoff: new Date('2026-03-10T18:00:00'), label: 'Champion Day',       short: 'Tue 10 Mar' },
          { key: 'Wednesday_11_March', cutoff: new Date('2026-03-11T18:00:00'), label: "Ladies' Day",         short: 'Wed 11 Mar' },
          { key: 'Thursday_12_March',  cutoff: new Date('2026-03-12T18:00:00'), label: "St Patrick's Thu",    short: 'Thu 12 Mar' },
          { key: 'Friday_13_March',    cutoff: new Date('2026-03-13T23:59:00'), label: 'Gold Cup Day',         short: 'Fri 13 Mar' },
        ];
        const activeFestDay = festivalDays.find(fd => now < fd.cutoff);
        if (!activeFestDay) return null; // festival over

        const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const cutoffMidnight = new Date(activeFestDay.cutoff.getFullYear(), activeFestDay.cutoff.getMonth(), activeFestDay.cutoff.getDate());
        const isToday = todayMidnight.getTime() === cutoffMidnight.getTime();
        const titleTag = isToday ? "🔥 TODAY'S TOP 3 BETS" : `⏳ NEXT UP — ${activeFestDay.label.toUpperCase()}`;
        const subtitleTag = isToday
          ? `${activeFestDay.label} · ${activeFestDay.short} · Back these NOW`
          : `${activeFestDay.short} · Prepare your bets`;

        // Get all BETTING_PICK picks for that day, sorted by soonest upcoming race time
        const nowHHMM = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        const isLiveDay = isToday;
        const dayPicks = Object.values(cheltenhamPicks)
          .filter(p => p.day === activeFestDay.key && (p.bet_tier === 'BETTING_PICK' || p.recommendation === 'BETTING_PICK'))
          .sort((a, b) => (a.race_time || '').localeCompare(b.race_time || ''))
          .filter(p => !isLiveDay || !p.race_time || p.race_time >= nowHHMM)
          .slice(0, 3);

        if (dayPicks.length === 0) return null;

        const tierColour = score => {
          const s = parseFloat(score || 0);
          if (s >= 155) return '#d97706';
          if (s >= 140) return '#3b82f6';
          if (s >= 120) return '#10b981';
          if (s >= 100) return '#8b5cf6';
          return '#6b7280';
        };
        const medals = ['🥇', '🥈', '🥉'];

        return (
          <div style={{
            background: isToday
              ? 'linear-gradient(135deg,#0d1f0d 0%,#052e16 60%,#0d1117 100%)'
              : 'linear-gradient(135deg,#0d1520 0%,#161b22 100%)',
            border: `2px solid ${isToday ? '#10b981' : '#3b82f6'}`,
            borderRadius: '12px',
            padding: '18px 22px',
            marginBottom: '20px',
          }}>
            <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '1.5px',
              textTransform: 'uppercase', color: isToday ? '#10b981' : '#3b82f6', marginBottom: '2px' }}>
              {titleTag}
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '14px' }}>
              {subtitleTag}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '12px' }}>
              {dayPicks.map((pick, i) => (
                <div key={pick.race_name} style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: `1px solid ${tierColour(pick.score)}55`,
                  borderLeft: `4px solid ${tierColour(pick.score)}`,
                  borderRadius: '10px',
                  padding: '14px 16px',
                  color: 'white',
                }}>
                  <div style={{ fontSize: '11px', opacity: 0.65, marginBottom: '4px' }}>
                    {medals[i]} {pick.race_time} · {pick.race_name}
                  </div>
                  <div style={{ fontSize: '19px', fontWeight: '800', marginBottom: '4px', lineHeight: '1.1' }}>
                    {pick.horse}
                  </div>
                  <div style={{ fontSize: '12px', opacity: 0.75, marginBottom: '8px' }}>
                    {pick.trainer && <span>T: {pick.trainer}</span>}
                    {pick.jockey && <span style={{ marginLeft: '8px' }}>J: {pick.jockey}</span>}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <span style={{
                      background: `${tierColour(pick.score)}22`,
                      border: `1px solid ${tierColour(pick.score)}66`,
                      borderRadius: '6px', padding: '2px 8px', fontSize: '12px', fontWeight: '700',
                      color: tierColour(pick.score),
                    }}>
                      Score {pick.score}
                    </span>
                    <span style={{
                      background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.25)',
                      borderRadius: '6px', padding: '2px 8px', fontSize: '12px', fontWeight: '800', color: 'white',
                    }}>
                      {pick.odds || '?'}
                    </span>
                    {parseFloat(pick.score_gap || 0) >= 5 && (
                      <span style={{
                        background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)',
                        borderRadius: '6px', padding: '2px 8px', fontSize: '11px', color: '#10b981',
                      }}>
                        +{pick.score_gap} gap
                      </span>
                    )}
                  </div>
                  {/* WHY THIS WINS — Top 3 card */}
                  {(() => {
                    const whyText = buildWhyWins(pick);
                    if (!whyText) return null;
                    const isMare = KNOWN_MARES.has(pick.horse);
                    const accent = tierColour(pick.score);
                    return (
                      <div style={{
                        marginTop: '10px',
                        padding: '7px 10px',
                        background: 'rgba(255,255,255,0.06)',
                        borderRadius: '5px',
                        borderLeft: `3px solid ${accent}`,
                      }}>
                        <div style={{ fontSize: '9px', fontWeight: '700', textTransform: 'uppercase',
                          letterSpacing: '0.08em', color: accent, marginBottom: '2px' }}>
                          {isMare ? 'Why She Wins' : 'Why He Wins'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.75)', lineHeight: '1.5' }}>
                          {whyText}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ))}
            </div>
            {isToday && (
              <div style={{ marginTop: '12px', fontSize: '11px', color: 'rgba(255,255,255,0.45)',
                borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '10px' }}>
                ⚠ Always verify final jockey declarations before placing bets · Refreshes daily at 8am
              </div>
            )}
          </div>
        );
      })()}

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
              background: selectedDay === day.key
                ? (day.complete ? '#6b7280' : '#10b981')
                : (day.complete ? '#e5e7eb' : '#f3f4f6'),
              color: selectedDay === day.key ? 'white' : (day.complete ? '#9ca3af' : '#374151'),
              border: day.complete && selectedDay !== day.key ? '1px solid #d1d5db' : 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600',
              transition: 'all 0.3s',
              opacity: day.complete && selectedDay !== day.key ? 0.7 : 1,
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
                onClick={() => loadHorses(race.raceId, race.raceName)}
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
                      {/* Next-best competitor */}
                      {(() => {
                        const secondName = pick.second_horse_name
                          || (pick.all_horses && pick.all_horses[1] && pick.all_horses[1].name)
                          || null;
                        const gap = pick.score_gap != null ? pick.score_gap : (pick.score - pick.second_score);
                        if (!secondName) return null;
                        return (
                          <div style={{ fontSize: '13px', color: '#4b5563', marginTop: '8px' }}>
                            <span style={{ color: confText, fontWeight: '600' }}>Next best: </span>
                            {secondName}
                            <span style={{
                              marginLeft: '8px',
                              background: 'rgba(0,0,0,0.08)',
                              padding: '2px 7px',
                              borderRadius: '10px',
                              fontSize: '12px',
                              fontWeight: '600'
                            }}>
                              {pick.second_score} pts
                            </span>
                            <span style={{
                              marginLeft: '6px',
                              fontSize: '12px',
                              fontWeight: '700',
                              color: gap > 20 ? '#059669' : gap > 10 ? '#d97706' : '#dc2626'
                            }}>
                              +{gap} gap
                            </span>
                          </div>
                        );
                      })()}
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
                  {/* WHY THIS WINS */}
                  {(() => {
                    const whyText = buildWhyWins(pick);
                    if (!whyText) return null;
                    const isMare = KNOWN_MARES.has(pick.horse);
                    const label  = isMare ? 'Why She Wins' : 'Why He Wins';
                    const accent = confText;
                    return (
                      <div style={{
                        marginTop: '12px',
                        padding: '8px 12px',
                        background: 'rgba(0,0,0,0.04)',
                        borderRadius: '6px',
                        borderLeft: `3px solid ${accent}`,
                      }}>
                        <div style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          letterSpacing: '0.08em',
                          color: accent,
                          marginBottom: '3px',
                        }}>
                          {label}
                        </div>
                        <div style={{ fontSize: '12px', color: '#374151', lineHeight: '1.5' }}>
                          {whyText}
                        </div>
                      </div>
                    );
                  })()}
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

            {expandedRace === race.raceId && (() => {
              // Prefer all_horses from cheltenhamPicks (always populated from DynamoDB);
              // fall back to the legacy raceHorses cache populated by loadHorses API call.
              const pickHorses = cheltenhamPicks[race.raceName]?.all_horses || [];
              const legacyHorses = raceHorses[race.raceId] || [];
              const horses = pickHorses.length > 0 ? pickHorses : legacyHorses;
              if (horses.length === 0) {
                return (
                  <div style={{ textAlign: 'center', padding: '30px', color: '#9ca3af', fontStyle: 'italic', marginTop: '15px' }}>
                    No horses added yet. Run: python cheltenham_festival_scraper.py --sample
                  </div>
                );
              }
              return (
                <div style={{ marginTop: '15px' }}>
                  {horses.map((h, idx) => {
                    // Support both all_horses field names (h.name) and legacy raceHorses field names (h.horseName)
                    const name = h.name || h.horseName || 'Unknown';
                    const odds = h.odds || h.currentOdds || 'N/A';
                    const trainer = h.trainer || 'N/A';
                    const jockey = h.jockey || 'N/A';
                    const score = h.score != null ? parseFloat(h.score).toFixed(1) : null;
                    const scoreGap = h.score_gap != null ? parseFloat(h.score_gap).toFixed(1) : null;
                    const isBettingPick = h.bet_tier === 'BETTING_PICK' || h.recommendation === 'BETTING_PICK';
                    const borderColor = isBettingPick ? '#10b981' : idx === 0 ? '#3b82f6' : '#e5e7eb';
                    return (
                      <div key={idx} style={{
                        background: 'white',
                        padding: '14px 16px',
                        borderRadius: '8px',
                        marginBottom: '10px',
                        borderLeft: `4px solid ${borderColor}`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        gap: '12px',
                      }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: '#6b7280', minWidth: '22px' }}>
                              #{idx + 1}
                            </span>
                            <span style={{ fontSize: '17px', fontWeight: '700', color: '#111' }}>
                              {name}
                            </span>
                            {isBettingPick && (
                              <span style={{ background: '#10b981', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700' }}>
                                ✓ NAP
                              </span>
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: '14px', fontSize: '13px', color: '#6b7280', flexWrap: 'wrap', marginLeft: '30px' }}>
                            <span>💰 {odds}</span>
                            <span>👨‍🏫 {trainer}</span>
                            <span>🏇 {jockey}</span>
                            {score && <span style={{ color: '#059669', fontWeight: '600' }}>Score {score}{scoreGap ? ` (+${scoreGap})` : ''}</span>}
                          </div>
                          {h.cheltenham_record && h.cheltenham_record !== 'First time' && (
                            <div style={{ fontSize: '12px', color: '#059669', fontWeight: '600', marginLeft: '30px', marginTop: '4px' }}>
                              🏆 {h.cheltenham_record}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        ))
      )}
    </div>
  );
}

export default App;

