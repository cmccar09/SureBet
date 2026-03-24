import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL ||
  'https://mnybvagd5m.execute-api.eu-west-1.amazonaws.com';

// -- Upcoming major races calendar --
const MAJOR_RACES = [
  // -- NATIONAL HUNT --
  { date: '2026-04-09', meeting: 'Aintree', name: 'Aintree Hurdle',             grade: 'G1',   type: 'NH',   distance: '2m4f',   purse: '\u00a3250,000',     notes: 'Champion Hurdle horses next \u2014 festival opener for top hurdlers' },
  { date: '2026-04-09', meeting: 'Aintree', name: "Manifesto Novices' Chase",   grade: 'G1',   type: 'NH',   distance: '2m1f',   purse: '\u00a3100,000',     notes: 'Arkle/Novices Chase graduates chase Grade 1 glory at Liverpool' },
  { date: '2026-04-09', meeting: 'Aintree', name: "Mersey Novices' Hurdle",     grade: 'G1',   type: 'NH',   distance: '2m4f',   purse: '\u00a3100,000',     notes: 'Top novice hurdlers step up after Cheltenham; Mullins usually loads up' },
  { date: '2026-04-10', meeting: 'Aintree', name: 'Liverpool Hurdle',           grade: 'G1',   type: 'NH',   distance: '3m1f',   purse: '\u00a3150,000',     notes: "Stayers' Hurdle horses rerouted \u2014 tests champion staying hurdlers" },
  { date: '2026-04-10', meeting: 'Aintree', name: "Mildmay Novices' Chase",     grade: 'G1',   type: 'NH',   distance: '3m1f',   purse: '\u00a3100,000',     notes: 'RSA/Brown Advisory graduates over the Mildmay fences' },
  { date: '2026-04-11', meeting: 'Aintree', name: 'Grand National',             grade: 'Hcap', type: 'NH',   distance: '4m2\u00bdf', purse: '\u00a31,000,000', notes: "The world's most famous race \u2014 30 fences, 40 runners", highlight: true },
  { date: '2026-04-11', meeting: 'Aintree', name: "Maghull Novices' Chase",     grade: 'G1',   type: 'NH',   distance: '2m',     purse: '\u00a3100,000',     notes: 'Two-mile novice championship at Liverpool \u2014 Arkle horses return' },
  { date: '2026-04-18', meeting: 'Ayr',     name: 'Scottish Grand National',   grade: 'G3',   type: 'NH',   distance: '4m',     purse: '\u00a3180,000',     notes: 'The Scottish equivalent of the National \u2014 testing marathon chase' },
  { date: '2026-04-29', meeting: 'Punchestown', name: 'Punchestown Champion Chase',  grade: 'G1', type: 'NH', distance: '2m',   purse: '\u20ac300,000', notes: 'Queen Mother Champion Chase re-match \u2014 Majborough expected to defend' },
  { date: '2026-04-30', meeting: 'Punchestown', name: 'Punchestown Gold Cup',         grade: 'G1', type: 'NH', distance: '3m1f', purse: '\u20ac300,000', notes: 'Grade 1 Gold Cup equivalent \u2014 Gaelic Warrior favourite after Cheltenham win', highlight: true },
  { date: '2026-05-01', meeting: 'Punchestown', name: 'Punchestown Champion Hurdle',  grade: 'G1', type: 'NH', distance: '2m',   purse: '\u20ac250,000', notes: 'Champion Hurdle horses head to Ireland for the season finale' },
  { date: '2026-05-01', meeting: 'Punchestown', name: 'World Series Hurdle',           grade: 'G1', type: 'NH', distance: '3m',   purse: '\u20ac200,000', notes: "Stayers' championship continues \u2014 Teahupoo expected to defend" },
  { date: '2026-05-02', meeting: 'Punchestown', name: 'Champion Bumper',               grade: 'G1', type: 'NH', distance: '2m',   purse: '\u20ac100,000', notes: 'Final Grade 1 NH bumper of the season' },
  // -- FLAT --
  { date: '2026-04-14', meeting: 'Newmarket', name: 'Craven Stakes',        grade: 'G3', type: 'Flat', distance: '1m',   purse: '\u00a380,000',    notes: 'Key Classic trial \u2014 opens the Flat season at HQ' },
  { date: '2026-05-02', meeting: 'Newmarket', name: '2000 Guineas',         grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3600,000',   notes: 'First colts Classic of the season \u2014 one of the original five', highlight: true },
  { date: '2026-05-03', meeting: 'Newmarket', name: '1000 Guineas',         grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3500,000',   notes: 'First fillies Classic \u2014 Newmarket straight on fast ground', highlight: true },
  { date: '2026-05-08', meeting: 'Chester',   name: 'Chester Vase',         grade: 'G3', type: 'Flat', distance: '1m4f', purse: '\u00a380,000',    notes: "Premier Derby trial on Chester's unique tight circuit" },
  { date: '2026-05-14', meeting: 'York',      name: 'Dante Stakes',         grade: 'G2', type: 'Flat', distance: '1m2f', purse: '\u00a3175,000',   notes: 'Most important Derby trial \u2014 last major stepping stone before Epsom' },
  { date: '2026-05-15', meeting: 'York',      name: 'Musidora Stakes',      grade: 'G3', type: 'Flat', distance: '1m2f', purse: '\u00a390,000',    notes: 'Key Oaks trial for fillies at York' },
  { date: '2026-06-05', meeting: 'Epsom',     name: 'Coronation Cup',       grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a3350,000',   notes: 'Older horses over the Derby course \u2014 Champion older middle-distance' },
  { date: '2026-06-05', meeting: 'Epsom',     name: 'The Oaks',             grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a3800,000',   notes: "Second Classic \u2014 fillies only over Epsom's undulating 1m4f", highlight: true },
  { date: '2026-06-06', meeting: 'Epsom',     name: 'The Derby',            grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a31,500,000', notes: "The greatest Flat race in the world \u2014 3yo colts & fillies over the Downs", highlight: true },
  { date: '2026-06-16', meeting: 'Royal Ascot', name: 'Queen Anne Stakes',          grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3600,000', notes: 'Royal Ascot opener \u2014 top milers on the straight mile', highlight: true },
  { date: '2026-06-16', meeting: 'Royal Ascot', name: "King's Stand Stakes",        grade: 'G1', type: 'Flat', distance: '5f',   purse: '\u00a3600,000', notes: "Premier sprint \u2014 world's best five-furlong horses clash" },
  { date: '2026-06-17', meeting: 'Royal Ascot', name: "Prince of Wales's Stakes",   grade: 'G1', type: 'Flat', distance: '1m2f', purse: '\u00a3900,000', notes: 'Mid-week showpiece \u2014 top older horses over ten furlongs', highlight: true },
  { date: '2026-06-17', meeting: 'Royal Ascot', name: "St James's Palace Stakes",   grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3600,000', notes: "Guineas re-match at Ascot \u2014 3yo colts over the round mile" },
  { date: '2026-06-18', meeting: 'Royal Ascot', name: 'Ascot Gold Cup',              grade: 'G1', type: 'Flat', distance: '2m4f', purse: '\u00a3700,000', notes: 'The staying championship \u2014 Gold Cup Day centrepiece', highlight: true },
  { date: '2026-06-18', meeting: 'Royal Ascot', name: 'Coronation Stakes',           grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3600,000', notes: "Fillies' Guineas graduates \u2014 round mile at Ascot in mid-summer" },
  { date: '2026-06-19', meeting: 'Royal Ascot', name: 'Commonwealth Cup',            grade: 'G1', type: 'Flat', distance: '6f',   purse: '\u00a3600,000', notes: '3yo sprint championship \u2014 hottest young sprinters of the season' },
  { date: '2026-06-20', meeting: 'Royal Ascot', name: 'Golden Jubilee Stakes',       grade: 'G1', type: 'Flat', distance: '6f',   purse: '\u00a3600,000', notes: 'Open sprint finale to Royal Ascot \u2014 global sprinters assemble' },
  { date: '2026-07-09', meeting: 'Sandown',   name: 'Eclipse Stakes',         grade: 'G1', type: 'Flat', distance: '1m2f', purse: '\u00a3750,000',   notes: 'Derby horses meet older Classic generation \u2014 midsummer championship', highlight: true },
  { date: '2026-07-25', meeting: 'Ascot',     name: 'King George VI & Queen Elizabeth Stakes', grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a31,000,000', notes: 'Mid-season championship \u2014 best horses of all ages over 1m4f', highlight: true },
  { date: '2026-07-29', meeting: 'Goodwood',  name: 'Sussex Stakes',          grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3600,000',   notes: 'Glorious Goodwood highlight \u2014 milers from all generations clash', highlight: true },
  { date: '2026-07-30', meeting: 'Goodwood',  name: 'Goodwood Cup',           grade: 'G1', type: 'Flat', distance: '2m',   purse: '\u00a3400,000',   notes: 'Staying championship at Goodwood \u2014 Gold Cup horses return' },
  { date: '2026-08-20', meeting: 'York',      name: 'Juddmonte International', grade: 'G1', type: 'Flat', distance: '1m2f', purse: '\u00a31,000,000', notes: 'Richest race in Britain \u2014 the definitive middle-distance championship', highlight: true },
  { date: '2026-08-20', meeting: 'York',      name: 'Yorkshire Oaks',          grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a3500,000',   notes: 'Top fillies and mares over 1m4f at York \u2014 Ebor Festival showpiece' },
  { date: '2026-08-21', meeting: 'York',      name: 'Nunthorpe Stakes',         grade: 'G1', type: 'Flat', distance: '5f',   purse: '\u00a3350,000',   notes: 'Sprint championship \u2014 five furlongs at York, all ages' },
  { date: '2026-09-12', meeting: 'Doncaster', name: 'St Leger',                grade: 'G1', type: 'Flat', distance: '1m6f', purse: '\u00a3500,000',   notes: 'The oldest Classic \u2014 final leg of the Triple Crown', highlight: true },
  { date: '2026-09-26', meeting: 'Newmarket', name: 'Sun Chariot Stakes',      grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a3350,000',   notes: 'Top fillies and mares over a mile on the Rowley Mile' },
  { date: '2026-10-03', meeting: 'Newmarket', name: 'Middle Park Stakes',      grade: 'G1', type: 'Flat', distance: '6f',   purse: '\u00a3250,000',   notes: 'Two-year-old sprint championship \u2014 Guineas market springs to life' },
  { date: '2026-10-03', meeting: 'Newmarket', name: 'Cheveley Park Stakes',    grade: 'G1', type: 'Flat', distance: '6f',   purse: '\u00a3250,000',   notes: '2yo fillies sprint championship \u2014 key Guineas trial' },
  { date: '2026-10-17', meeting: 'Ascot',     name: 'QIPCO Champion Stakes',             grade: 'G1', type: 'Flat', distance: '1m2f', purse: '\u00a31,300,000', notes: 'Season finale \u2014 the definitive autumn championship at British Champions Day', highlight: true },
  { date: '2026-10-17', meeting: 'Ascot',     name: 'Queen Elizabeth II Stakes',         grade: 'G1', type: 'Flat', distance: '1m',   purse: '\u00a31,100,000', notes: "Milers' Championship on Champions Day \u2014 season finale for mile stars", highlight: true },
  { date: '2026-10-17', meeting: 'Ascot',     name: 'British Champions Sprint',          grade: 'G1', type: 'Flat', distance: '6f',   purse: '\u00a3700,000',   notes: "Sprint Championship \u2014 season finale for Britain's best sprinters" },
  { date: '2026-10-17', meeting: 'Ascot',     name: 'British Champions Fillies & Mares', grade: 'G1', type: 'Flat', distance: '1m4f', purse: '\u00a3700,000',   notes: 'Fillies and mares season finale' },
];

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}

function daysUntil(dateStr) {
  const today = new Date(); today.setHours(0,0,0,0);
  const diff = Math.round((new Date(dateStr + 'T00:00:00') - today) / 86400000);
  if (diff < 0) return null;
  if (diff === 0) return 'TODAY';
  if (diff === 1) return 'Tomorrow';
  return diff + ' days';
}

function isPast(dateStr) {
  const today = new Date(); today.setHours(0,0,0,0);
  return new Date(dateStr + 'T00:00:00') < today;
}

function groupByMeeting(races) {
  const meetings = {};
  races.forEach(r => {
    const key = r.date + '__' + r.meeting;
    if (!meetings[key]) meetings[key] = { date: r.date, meeting: r.meeting, races: [] };
    meetings[key].races.push(r);
  });
  return Object.values(meetings).sort((a,b) => a.date.localeCompare(b.date));
}

// ---- Decimal → Fractional odds converter ----
function toFractional(decimal) {
  if (!decimal) return '';
  const d = parseFloat(decimal);
  if (isNaN(d) || d <= 1.0) return 'SP';
  const tbl = [
    [1.07,'1/14'],[1.09,'1/11'],[1.11,'1/9'],[1.13,'1/8'],[1.17,'1/6'],
    [1.20,'1/5'],[1.25,'1/4'],[1.29,'2/7'],[1.33,'1/3'],[1.36,'4/11'],
    [1.40,'2/5'],[1.44,'4/9'],[1.50,'1/2'],[1.53,'8/15'],[1.57,'4/7'],
    [1.62,'4/6'],[1.67,'2/3'],[1.72,'8/11'],[1.80,'4/5'],[1.91,'10/11'],
    [2.00,'EVS'],[2.10,'11/10'],[2.20,'6/5'],[2.25,'5/4'],[2.38,'11/8'],
    [2.50,'6/4'],[2.63,'13/8'],[2.75,'7/4'],[2.88,'15/8'],[3.00,'2/1'],
    [3.25,'9/4'],[3.38,'19/8'],[3.50,'5/2'],[3.75,'11/4'],[4.00,'3/1'],
    [4.33,'10/3'],[4.50,'7/2'],[5.00,'4/1'],[5.50,'9/2'],[6.00,'5/1'],
    [6.50,'11/2'],[7.00,'6/1'],[7.50,'13/2'],[8.00,'7/1'],[8.50,'15/2'],
    [9.00,'8/1'],[9.50,'17/2'],[10.0,'9/1'],[11.0,'10/1'],[12.0,'11/1'],
    [13.0,'12/1'],[14.0,'13/1'],[15.0,'14/1'],[17.0,'16/1'],[21.0,'20/1'],
    [26.0,'25/1'],[34.0,'33/1'],[51.0,'50/1'],[101.0,'100/1'],
  ];
  let best = tbl[0], bestDiff = Math.abs(d - tbl[0][0]);
  for (const [dec, frac] of tbl) {
    const diff = Math.abs(d - dec);
    if (diff < bestDiff) { bestDiff = diff; best = [dec, frac]; }
  }
  if (bestDiff / d <= 0.08) return best[1];
  // fallback: compute nearest simple fraction
  const n = Math.round((d - 1) * 20);
  const gcd = (a, b) => b ? gcd(b, a % b) : a;
  const g = gcd(n, 20);
  return `${n/g}/${20/g}`;
}

// ---- App ----
function App() {
  const [page, setPage] = useState('picks');
  return (
    <div className="App">
      <header className="App-header">
        <h1>SureBet AI</h1>
        <p style={{ fontSize: '14px', opacity: 0.8, margin: '4px 0 0' }}>AI-powered racing analysis \u00b7 UK &amp; Ireland</p>
      </header>
      <div style={{ display:'flex', justifyContent:'center', gap:'12px', marginBottom:'32px', flexWrap:'wrap' }}>
        {[
          { key:'picks',  label:"Today's Picks",    emoji:'\ud83c\udfaf', sub:'Top 5 value bets'     },
          { key:'yesterday', label:'Latest Results', emoji:'\ud83d\udcca', sub:'Today & yesterday'     },
          { key:'majors', label:'Major Races',        emoji:'\ud83c\udfc6', sub:'Group 1 calendar'    },
        ].map(tab => (
          <button key={tab.key} onClick={() => setPage(tab.key)} style={{
            background: page===tab.key ? 'linear-gradient(135deg,#059669 0%,#047857 100%)' : 'rgba(255,255,255,0.12)',
            border:     page===tab.key ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.25)',
            borderRadius:'10px', color:'white', cursor:'pointer',
            padding:'12px 24px', minWidth:'160px', textAlign:'center', transition:'all 0.2s',
          }}>
            <div style={{ fontSize:'16px', fontWeight:'700' }}>{tab.emoji} {tab.label}</div>
            <div style={{ fontSize:'11px', opacity:0.75, marginTop:'2px' }}>{tab.sub}</div>
          </button>
        ))}
      </div>
      <main style={{ maxWidth:'960px', margin:'0 auto', padding:'0 12px' }}>
        {page==='picks' ? <DailyPicksView /> : page==='yesterday' ? <YesterdayResultsView /> : <MajorRacesView />}
      </main>
    </div>
  );
}

// ---- Daily Picks ----
const SCORE_LABELS = {
  form:              'Recent Form',
  form_score:        'Recent Form',
  recent_win:        'Last Race Win',
  total_wins:        'Form Wins',
  consistency:       'Form Places',
  market_position:   'Market Position',
  market_leader:     'Market Leader Bonus',
  market_bonus:      'Market Bonus',
  optimal_odds:      'Odds Position',
  sweet_spot:        'Odds Sweet Spot',
  trainer:           'Trainer Quality',
  trainer_score:     'Trainer Quality',
  trainer_reputation:'Trainer Quality',
  jockey:            'Jockey Quality',
  jockey_score:      'Jockey Quality',
  jockey_quality:    'Jockey Quality',
  going:             'Going Suitability',
  going_score:       'Going Suitability',
  going_suitability: 'Going Suitability',
  class:             'Class Level',
  class_score:       'Class Level',
  distance_suitability: 'Distance Suitability',
  distance:          'Distance Suitability',
  distance_score:    'Distance Suitability',
  cd_bonus:          'Course+Distance Winner',
  headgear:          'Headgear Change',
  course:            'Course Form',
  course_score:      'Course Form',
  course_performance:'Course Performance',
  weight:            'Weight Advantage',
  weight_penalty:    'Weight Penalty',
  draw:              'Draw Advantage',
  age:               'Age Profile',
  age_bonus:         'Age Bonus',
  bounce_back:       'Bounce-Back Pattern',
  history_bonus:     'DB History Bonus',
  history:           'DB History Bonus',
  database_history:  'DB History Bonus',
  base:              'Base Score',
  odds_value:        'Odds Value',
  price_move:        'Price Move',
  favorite_correction:'Favourite Bonus',
  track_pattern_bonus:'Track Pattern',
  novice_penalty:    'Novice Race Penalty',
  aw_low_class_penalty: 'AW Low Class Penalty',
};

function DailyPicksView() {
  const [picks, setPicks]             = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [expandedPick,  setExpandedPick]  = useState(null);
  const [expandedField, setExpandedField] = useState(null);
  const [raceFields,    setRaceFields]    = useState({});
  const [isMobile,      setIsMobile]      = useState(typeof window !== 'undefined' && window.innerWidth < 480);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 480);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const formatRaceTime = rt => {
    if (!rt) return { date: '', time: '' };
    // US format: MM/DD/YYYY HH:MM:SS
    const m = rt.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/);
    if (m) {
      const d = new Date(`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}:00`);
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', year:'numeric' }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }),
      };
    }
    // ISO format
    try {
      const d = new Date(rt.replace('Z',''));
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', year:'numeric' }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }),
      };
    } catch { return { date: rt.substring(0,10), time: rt.substring(11,16) }; }
  };

  useEffect(() => {
    loadPicks();
    // Auto-refresh every 30 min when within 12:00-18:00 window
    const interval = setInterval(() => {
      const h = new Date().getHours();
      if (h >= 12 && h <= 18) loadPicks();
    }, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadPicks = async () => {
    setLoading(true); setError(null);
    try {
      const res  = await fetch(API_BASE_URL + '/api/picks/today');
      const data = await res.json();
      if (data.success) {
        const sorted = (data.picks || [])
          .filter(p => p.show_in_ui !== false)
          .sort((a,b) => parseFloat(b.score||0) - parseFloat(a.score||0))
          .slice(0, 5);
        setPicks(sorted);
        setRaceFields(data.race_fields || {});
        setLastUpdated(new Date().toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }));
      } else {
        setError(data.error || 'Failed to load picks');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toLocaleDateString('en-GB', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

  const tierInfo = score => {
    const s = parseFloat(score || 0);
    if (s >= 95) return { bg: '#d97706', label: 'ELITE'  };
    if (s >= 85) return { bg: '#059669', label: 'STRONG' };
    if (s >= 75) return { bg: '#3b82f6', label: 'GOOD'   };
    return             { bg: '#0891b2', label: 'VALUE'  };
  };

  if (loading) return (
    <div style={{ textAlign:'center', padding:'60px 20px', color:'white' }}>
      <div style={{ fontSize:'18px', opacity:0.8 }}>Loading today's picks...</div>
    </div>
  );

  if (error) return (
    <div style={{ background:'rgba(239,68,68,0.15)', border:'1px solid #ef4444', borderRadius:'10px', padding:'24px', color:'white', textAlign:'center' }}>
      <div style={{ fontWeight:'700', marginBottom:'6px' }}>Error loading picks</div>
      <div style={{ fontSize:'13px', opacity:0.8, marginBottom:'16px' }}>{error}</div>
      <button onClick={loadPicks} style={{ background:'#059669', border:'none', borderRadius:'6px', color:'white', padding:'8px 20px', cursor:'pointer', fontWeight:'700' }}>Retry</button>
    </div>
  );

  return (
    <div>
      <div style={{ background:'linear-gradient(135deg,#047857 0%,#065f46 100%)', borderRadius:'12px', padding:'24px 28px', marginBottom:'24px', color:'white', display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'12px' }}>
        <div>
          <div style={{ fontSize:'13px', textTransform:'uppercase', letterSpacing:'1px', opacity:0.75 }}>Today's Daily 3 — Best Bet From Each Race</div>
          <div style={{ fontSize:'22px', fontWeight:'800', marginTop:'4px' }}>{today}</div>
          {lastUpdated && <div style={{ fontSize:'12px', opacity:0.65, marginTop:'4px' }}>Last updated {lastUpdated} \u00b7 Data refreshes 12:00, 14:00, 16:00, 18:00 \u00b7 Page auto-reloads every 30 min</div>}
        </div>
        <button onClick={loadPicks} style={{ background:'rgba(255,255,255,0.15)', border:'1px solid rgba(255,255,255,0.35)', borderRadius:'8px', color:'white', padding:'8px 18px', cursor:'pointer', fontSize:'13px', fontWeight:'600' }}>
          Refresh
        </button>
      </div>

      {picks.length === 0 ? (
        <div style={{ background:'rgba(255,255,255,0.08)', borderRadius:'12px', padding:'48px 24px', textAlign:'center', color:'rgba(255,255,255,0.7)' }}>
          <div style={{ fontSize:'18px', fontWeight:'700', color:'white', marginBottom:'8px' }}>No picks yet today</div>
          <div style={{ fontSize:'14px' }}>The model scores every horse in today's races and selects the 3 highest-confidence winners — one per race.<br/>Odds are fetched at 12:00, 14:00, 16:00 and 18:00 daily.<br/>Check the <strong>Top Naps</strong> tab for best picks across the next 5 days.</div>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>
          {[...picks]
            .sort((a,b) => (parseInt(a.pick_rank||99) - parseInt(b.pick_rank||99)))
            .slice(0,3)
            .map((pick, idx) => {
            const tier = tierInfo(pick.score);
            const rank = parseInt(pick.pick_rank || (idx+1));
            const rankLabels = {1:'#1 Best Bet', 2:'#2 Best Bet', 3:'#3 Best Bet'};
            const rankColors = {1:'#d97706', 2:'#6b7280', 3:'#92400e'};
            return (
              <div key={idx} style={{ background:'white', borderRadius:'12px', padding:'20px 22px', borderLeft:`5px solid ${rankColors[rank]||tier.bg}`, boxShadow:'0 2px 12px rgba(0,0,0,0.1)' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'8px' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                    <div style={{ background:rankColors[rank]||tier.bg, color:'white', borderRadius:'8px', padding:'6px 10px', textAlign:'center', minWidth:'44px', flexShrink:0 }}>
                      <div style={{ fontSize:'18px', fontWeight:'900' }}>#{rank}</div>
                      <div style={{ fontSize:'9px', fontWeight:'700', opacity:0.85, textTransform:'uppercase', lineHeight:'1' }}>Pick</div>
                    </div>
                    <div>
                      <div style={{ fontSize:'20px', fontWeight:'800', color:'#111' }}>{pick.horse || pick.horse_name || 'Unknown'}</div>
                      <div style={{ display:'flex', flexWrap:'wrap', gap:'6px', marginTop:'6px', alignItems:'center' }}>
                        {(pick.course || pick.venue) && (
                          <span style={{ background:'#1e3a5f', color:'white', padding:'3px 10px', borderRadius:'6px', fontSize:'12px', fontWeight:'700' }}>
                            {pick.course || pick.venue}
                          </span>
                        )}
                        {pick.race_time && (() => {
                          const { date, time } = formatRaceTime(pick.race_time);
                          return (
                            <>
                              <span style={{ background:'#f3f4f6', color:'#374151', padding:'3px 10px', borderRadius:'6px', fontSize:'12px', fontWeight:'600' }}>
                                {date}
                              </span>
                              <span style={{ background:'#ecfdf5', color:'#065f46', padding:'3px 10px', borderRadius:'6px', fontSize:'12px', fontWeight:'700', border:'1px solid #a7f3d0' }}>
                                {time}
                              </span>
                            </>
                          );
                        })()}
                        {pick.race_name && <span style={{ color:'#6b7280', fontSize:'12px' }}>{pick.race_name}</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'center' }}>
                    {pick.odds && (
                      <div style={{ textAlign:'center' }}>
                        <div style={{ background:'#1e3a5f', color:'white', padding:'5px 14px', borderRadius:'8px', fontWeight:'900', fontSize:'22px', letterSpacing:'0.5px' }}>{toFractional(pick.odds)}</div>
                        <div style={{ fontSize:'10px', color:'#6b7280', marginTop:'2px', fontWeight:'600' }}>ODDS</div>
                      </div>
                    )}
                    <div style={{ textAlign:'center' }}>
                      <span style={{ background:tier.bg, color:'white', padding:'5px 12px', borderRadius:'8px', fontSize:'12px', fontWeight:'700', display:'block' }}>
                        {tier.label}
                      </span>
                      {pick.score && (
                        <div
                          onClick={() => setExpandedPick(expandedPick === idx ? null : idx)}
                          style={{ fontSize:'11px', color:'#1d4ed8', marginTop:'4px', fontWeight:'700', cursor:'pointer', userSelect:'none', display:'flex', alignItems:'center', justifyContent:'center', gap:'3px' }}
                        >
                          Score: {parseFloat(pick.score).toFixed(0)}/100 {expandedPick === idx ? '\u25b2' : '\u25bc'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                {/* Trainer / Jockey / Form row */}
                <div style={{ fontSize:'13px', color:'#374151', marginTop:'12px', display:'flex', gap:'18px', flexWrap:'wrap', alignItems:'center' }}>
                  {pick.trainer  && <span><strong>Trainer:</strong> {pick.trainer}</span>}
                  {pick.jockey   && <span><strong>Jockey:</strong> {pick.jockey}</span>}
                  {pick.form     && <span style={{ background:'#f3f4f6', borderRadius:'5px', padding:'2px 8px', fontFamily:'monospace', fontWeight:'700', color:'#1e3a5f', letterSpacing:'1px' }}>Form: {pick.form}</span>}
                  {pick.score_gap > 0 && (
                    <span style={{ background:'#f0fdf4', border:'1px solid #86efac', borderRadius:'5px', padding:'2px 8px', fontSize:'12px', color:'#166534', fontWeight:'700' }}>
                      +{parseFloat(pick.score_gap).toFixed(0)}pt clear of field
                    </span>
                  )}
                  {pick.history_win_rate > 0 && (
                    <span style={{ background:'#eff6ff', border:'1px solid #bfdbfe', borderRadius:'5px', padding:'2px 8px', fontSize:'12px', color:'#1d4ed8', fontWeight:'700' }}>
                      DB: {parseFloat(pick.history_win_rate * 100).toFixed(0)}% win rate ({pick.history_wins}/{pick.history_runs} runs)
                    </span>
                  )}
                </div>
                {/* Why this wins — scoring reasons */}
                {Array.isArray(pick.selection_reasons) && pick.selection_reasons.length > 0 && (
                  <div style={{ marginTop:'12px', padding:'12px 16px', background:'#f8fafc', borderRadius:'8px', borderLeft:`3px solid ${tier.bg}` }}>
                    <div style={{ fontSize:'10px', fontWeight:'800', color:tier.bg, textTransform:'uppercase', letterSpacing:'0.8px', marginBottom:'8px' }}>Why this horse wins</div>
                    <div style={{ display:'flex', flexWrap:'wrap', gap:'6px' }}>
                      {pick.selection_reasons.slice(0,8).map((r, i) => (
                        <span key={i} style={{ background:'white', border:'1px solid #e5e7eb', borderRadius:'6px', padding:'3px 10px', fontSize:'12px', color:'#374151', lineHeight:'1.4' }}>
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {/* Full race card — all runners ranked by score */}
                {(() => {
                  // Use all_horses from pick data (DynamoDB), fall back to raceFields from API
                  const raceKey  = `${pick.venue || pick.course}|${pick.race_time}`;
                  const rawField = (pick.all_horses && pick.all_horses.length > 0)
                    ? pick.all_horses
                    : (raceFields[raceKey] || []);
                  if (!rawField.length) return null;

                  // Sort by score descending; mark our pick
                  const ourHorse = (pick.horse || pick.horse_name || '').toLowerCase();
                  const field = [...rawField]
                    .map(h => ({ ...h, score: parseFloat(h.score || 0), odds: parseFloat(h.odds || 0) }))
                    .sort((a, b) => b.score - a.score);
                  const topScore  = field[0]?.score || 1;
                  const open      = expandedField === idx;
                  const ourRank   = field.findIndex(h => (h.horse||'').toLowerCase() === ourHorse);
                  const nextBest  = field.find(h => (h.horse||'').toLowerCase() !== ourHorse);
                  const gap       = ourRank === 0 && nextBest ? (field[0].score - nextBest.score).toFixed(0) : null;

                  return (
                    <div style={{ marginTop:'10px' }}>
                      <button
                        onClick={() => setExpandedField(open ? null : idx)}
                        style={{ background: open ? '#f0fdf4' : 'none', border:`1px solid ${open ? '#86efac' : '#d1d5db'}`, borderRadius:'6px', padding:'6px 14px', fontSize:'12px', fontWeight:'700', color: open ? '#166534' : '#374151', cursor:'pointer', width:'100%', textAlign:'left', display:'flex', justifyContent:'space-between', alignItems:'center', transition:'all 0.15s' }}
                      >
                        <span>
                          🏇 See how all {field.length} runners rated
                          {gap && <span style={{ marginLeft:'8px', background:'#dcfce7', color:'#166534', borderRadius:'4px', padding:'1px 7px', fontSize:'11px' }}>+{gap}pt clear</span>}
                        </span>
                        <span style={{ fontSize:'10px', color:'#6b7280' }}>{open ? '▲ Hide' : '▼ Show'}</span>
                      </button>

                      {open && (
                        <div style={{ marginTop:'6px', background:'#f8fafc', borderRadius:'10px', overflow:'hidden', border:'1px solid #e5e7eb' }}>
                          {/* Column headers */}
                          <div style={{ display:'grid', gridTemplateColumns: isMobile ? '22px 1fr 42px 52px' : '28px 1fr 64px 160px 60px', gap:'0', background:'#1e3a5f', padding:'7px 12px', fontSize:'10px', fontWeight:'800', color:'rgba(255,255,255,0.7)', textTransform:'uppercase', letterSpacing:'0.8px', alignItems:'center' }}>
                            <span>#</span>
                            <span>Horse</span>
                            <span style={{ textAlign:'center' }}>Odds</span>
                            <span style={{ textAlign:'center' }}>{isMobile ? 'Pts' : 'Model Score'}</span>
                            {!isMobile && <span style={{ textAlign:'center' }}>Tier</span>}
                          </div>
                          {field.map((runner, ri) => {
                            const rScore    = runner.score;
                            const t         = tierInfo(rScore);
                            const isOurPick = (runner.horse||'').toLowerCase() === ourHorse;
                            const barPct    = topScore > 0 ? Math.min(rScore / topScore * 100, 100) : 0;
                            const scoreDiff = ri > 0 ? (rScore - field[0].score).toFixed(0) : null;
                            return (
                              <div key={ri} style={{ display:'grid', gridTemplateColumns: isMobile ? '22px 1fr 42px 52px' : '28px 1fr 64px 160px 60px', gap:'0', padding: isMobile ? '7px 10px' : '8px 12px', alignItems:'center', background: isOurPick ? 'rgba(5,150,105,0.08)' : ri % 2 === 0 ? 'white' : '#f9fafb', borderBottom:'1px solid #f0f0f0', borderLeft: isOurPick ? '3px solid #059669' : '3px solid transparent' }}>
                                {/* Rank */}
                                <span style={{ fontSize:'11px', fontWeight:'800', color: ri === 0 ? '#d97706' : '#9ca3af' }}>
                                  {ri === 0 ? '★' : ri + 1}
                                </span>
                                {/* Horse name */}
                                <div>
                                  <div style={{ display:'flex', alignItems:'center', gap:'5px', flexWrap:'wrap' }}>
                                    <span style={{ fontWeight: isOurPick ? '800' : '600', color: isOurPick ? '#065f46' : '#111', fontSize:'13px' }}>
                                      {runner.horse}
                                    </span>
                                    {isOurPick && (
                                      <span style={{ background:'#059669', color:'white', borderRadius:'3px', padding:'1px 6px', fontSize:'9px', fontWeight:'800', textTransform:'uppercase' }}>Our Pick</span>
                                    )}
                                  </div>
                                  {(runner.jockey || runner.trainer) && (
                                    <div style={{ fontSize:'10px', color:'#9ca3af', marginTop:'2px' }}>
                                      {runner.jockey  && `J: ${runner.jockey}`}
                                      {runner.jockey && runner.trainer && ' · '}
                                      {runner.trainer && `T: ${runner.trainer}`}
                                    </div>
                                  )}
                                </div>
                                {/* Odds */}
                                <div style={{ textAlign:'center', fontWeight:'700', color:'#1e3a5f', fontSize:'12px' }}>
                                  {runner.odds > 1 ? toFractional(runner.odds) : '—'}
                                </div>
                                {/* Score bar — full on desktop, compact number on mobile */}
                                {isMobile ? (
                                  <div style={{ textAlign:'center' }}>
                                    <span style={{ fontSize:'13px', fontWeight:'900', color: isOurPick ? '#065f46' : t.bg }}>{rScore.toFixed(0)}</span>
                                    {scoreDiff !== null && <div style={{ fontSize:'9px', fontWeight:'700', color:'#ef4444', lineHeight:1 }}>{scoreDiff}</div>}
                                  </div>
                                ) : (
                                  <div style={{ display:'flex', alignItems:'center', gap:'7px' }}>
                                    <div style={{ flex:1, height:'10px', background:'#e5e7eb', borderRadius:'5px', overflow:'hidden' }}>
                                      <div style={{ width:`${barPct}%`, height:'100%', background: isOurPick ? '#059669' : t.bg, borderRadius:'5px', transition:'width 0.3s' }} />
                                    </div>
                                    <span style={{ fontSize:'12px', fontWeight:'800', color: isOurPick ? '#065f46' : '#374151', minWidth:'26px', textAlign:'right' }}>
                                      {rScore.toFixed(0)}
                                    </span>
                                    {scoreDiff !== null && (
                                      <span style={{ fontSize:'10px', fontWeight:'700', color:'#ef4444', minWidth:'28px', textAlign:'right' }}>
                                        {scoreDiff}
                                      </span>
                                    )}
                                  </div>
                                )}
                                {/* Tier badge — desktop only */}
                                {!isMobile && (
                                  <div style={{ textAlign:'center' }}>
                                    <span style={{ background: isOurPick ? '#059669' : t.bg, color:'white', borderRadius:'4px', padding:'2px 6px', fontSize:'10px', fontWeight:'700' }}>
                                      {t.label}
                                    </span>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                          <div style={{ padding:'8px 14px', background:'#f1f5f9', fontSize:'11px', color:'#64748b', textAlign:'right' }}>
                            Score = AI model rating out of 100 · Red numbers = points behind our pick
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
                {/* Score Breakdown Panel — toggled by clicking the score badge */}
                {expandedPick === idx && pick.score_breakdown && typeof pick.score_breakdown === 'object' && (() => {
                  const entries = Object.entries(pick.score_breakdown)
                    .filter(([,v]) => parseFloat(v) !== 0)
                    .sort(([,a],[,b]) => parseFloat(b)-parseFloat(a));
                  const maxVal = entries.reduce((m,[,v]) => Math.max(m, Math.abs(parseFloat(v))), 1);
                  const total  = parseFloat(pick.score || 0);
                  return (
                    <div style={{ marginTop:'14px', padding:'16px 18px', background:'#f0f4ff', borderRadius:'10px', border:'1px solid #c7d7f8' }}>
                      <div style={{ fontSize:'11px', fontWeight:'800', color:'#1e3a5f', textTransform:'uppercase', letterSpacing:'0.8px', marginBottom:'12px' }}>
                        Score Breakdown &mdash; how {total.toFixed(0)} pts was calculated
                      </div>
                      <div style={{ display:'flex', flexDirection:'column', gap:'7px' }}>
                        {entries.map(([k, v]) => {
                          const pts   = parseFloat(v);
                          const label = SCORE_LABELS[k] || k.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
                          const pct   = Math.round(Math.abs(pts) / maxVal * 100);
                          const pos   = pts >= 0;
                          return (
                            <div key={k} style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                              <div style={{ width:'140px', fontSize:'11px', color:'#374151', fontWeight:'600', flexShrink:0, textAlign:'right' }}>{label}</div>
                              <div style={{ flex:1, height:'16px', background:'#dde5f7', borderRadius:'4px', overflow:'hidden' }}>
                                <div style={{ width: pct+'%', height:'100%', background: pos ? '#1d6f4e' : '#dc2626', borderRadius:'4px' }} />
                              </div>
                              <div style={{ width:'44px', fontSize:'12px', fontWeight:'800', color: pos ? '#166534' : '#dc2626', textAlign:'right', flexShrink:0 }}>
                                {pts >= 0 ? '+' : ''}{pts.toFixed(0)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div style={{ marginTop:'10px', paddingTop:'10px', borderTop:'1px solid #c7d7f8', display:'flex', justifyContent:'flex-end', alignItems:'center', gap:'8px' }}>
                        <span style={{ fontSize:'12px', color:'#374151', fontWeight:'600' }}>Total Score</span>
                        <span style={{ background:'#1e3a5f', color:'white', padding:'3px 12px', borderRadius:'6px', fontSize:'14px', fontWeight:'900' }}>{total.toFixed(0)} pts</span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            );
          })}
        </div>
      )}

      <div style={{ marginTop:'28px', padding:'16px 20px', background:'rgba(255,255,255,0.07)', borderRadius:'10px', color:'rgba(255,255,255,0.6)', fontSize:'12px', textAlign:'center', lineHeight:'1.6' }}>
        Picks generated by AI analysis of Betfair odds, form, trainer &amp; jockey stats, going suitability and market movement.<br/>
        Model self-learns daily from race results · Top picks from all races over the next 5 days · Always bet responsibly.
      </div>
    </div>
  );
}

// ---- Yesterday's Results ----
function YesterdayResultsView() {
  const [results, setResults]         = useState(null);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [isMobile, setIsMobile]       = useState(typeof window !== 'undefined' && window.innerWidth < 480);
  const [learningStatus, setLearning] = useState({ state: 'idle', message: '', changes: {} });

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 480);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => { loadResults(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadResults = async () => {
    setLoading(true); setError(null);
    try {
      const [todayRes, yestRes] = await Promise.all([
        fetch(API_BASE_URL + '/api/results/today'),
        fetch(API_BASE_URL + '/api/results/yesterday'),
      ]);
      const [todayData, yestData] = await Promise.all([todayRes.json(), yestRes.json()]);

      const todayPicks = (todayData.success ? todayData.picks || [] : []).map(p => ({ ...p, _dayLabel: 'Today' }));
      const yestPicks  = (yestData.success  ? yestData.picks  || [] : []).map(p => ({ ...p, _dayLabel: 'Yesterday' }));
      const allPicks   = [...todayPicks, ...yestPicks];

      const allRaceFields = { ...(yestData.race_fields || {}), ...(todayData.race_fields || {}) }; // eslint-disable-line no-unused-vars

      const ts = todayData.success ? (todayData.summary || {}) : {};
      const ys = yestData.success  ? (yestData.summary  || {}) : {};
      const combinedSummary = {
        total_picks:  (ts.total_picks  || 0) + (ys.total_picks  || 0),
        wins:         (ts.wins         || 0) + (ys.wins         || 0),
        places:       (ts.places       || 0) + (ys.places       || 0),
        losses:       (ts.losses       || 0) + (ys.losses       || 0),
        pending:      (ts.pending      || 0) + (ys.pending      || 0),
        profit:       (ts.profit       || 0) + (ys.profit       || 0),
        total_stake:  (ts.total_stake  || 0) + (ys.total_stake  || 0),
      };
      // ROI = profit / total_stake * 100  (standard financial ROI)
      combinedSummary.roi = combinedSummary.total_stake > 0
        ? (combinedSummary.profit / combinedSummary.total_stake * 100) : 0;

      if (allPicks.length === 0 && !todayData.success && !yestData.success) {
        setError('Failed to load results');
      } else {
        setResults({ picks: allPicks, summary: combinedSummary });
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatRaceTime = rt => {
    if (!rt) return { date: '', time: '' };
    const m = rt.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/);
    if (m) {
      const d = new Date(`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}:00`);
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short' }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }),
      };
    }
    try {
      const d = new Date(rt.replace('Z',''));
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short' }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }),
      };
    } catch { return { date: rt.substring(0,10), time: rt.substring(11,16) }; }
  };

  const outcomeStyle = emoji => {
    if (emoji === 'WIN')     return { bg:'#059669', border:'#10b981', text:'WIN \u2713',     card:'rgba(16,185,129,0.08)' };
    if (emoji === 'PLACED')  return { bg:'#3b82f6', border:'#60a5fa', text:'PLACED',          card:'rgba(59,130,246,0.08)' };
    if (emoji === 'LOSS')    return { bg:'#ef4444', border:'#f87171', text:'LOSS \u2715',     card:'rgba(239,68,68,0.06)'  };
    return                          { bg:'#6b7280', border:'#9ca3af', text:'PENDING \u23F3',  card:'rgba(107,114,128,0.06)' };
  };

  const scoreLabel = s => {
    const n = parseFloat(s || 0);
    if (n >= 95) return { bg:'#d97706', label:'ELITE'  };
    if (n >= 85) return { bg:'#059669', label:'STRONG' };
    if (n >= 75) return { bg:'#3b82f6', label:'GOOD'   };
    return             { bg:'#8b5cf6', label:'VALUE'  };
  };

  const dateRangeLabel = () => {
    const today = new Date();
    const yest  = new Date(); yest.setDate(yest.getDate() - 1);
    const fmt = d => d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short' });
    return `${fmt(yest)} – ${fmt(today)}`;
  };

  if (loading) return (
    <div style={{ textAlign:'center', padding:'60px 20px', color:'white' }}>
      <div style={{ fontSize:'18px', opacity:0.8 }}>Loading latest results...</div>
    </div>
  );

  if (error) return (
    <div style={{ background:'rgba(239,68,68,0.15)', border:'1px solid #ef4444', borderRadius:'10px', padding:'24px', color:'white', textAlign:'center' }}>
      <div style={{ fontWeight:'700', marginBottom:'6px' }}>Error loading results</div>
      <div style={{ fontSize:'13px', opacity:0.8, marginBottom:'16px' }}>{error}</div>
      <button onClick={loadResults} style={{ background:'#059669', border:'none', borderRadius:'6px', color:'white', padding:'8px 20px', cursor:'pointer', fontWeight:'700' }}>Retry</button>
    </div>
  );

  const picks   = results?.picks   || [];
  const summary = results?.summary || {};
  const profit  = summary.profit   || 0;

  return (
    <div>
      {/* Header */}
      <div style={{ background:'linear-gradient(135deg,#1e3a5f 0%,#1e40af 50%,#1e3a5f 100%)', border:'2px solid #3b82f6', borderRadius:'12px', padding:'24px 28px', marginBottom:'24px', color:'white', display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'12px' }}>
        <div>
          <div style={{ fontSize:'13px', textTransform:'uppercase', letterSpacing:'1px', color:'#93c5fd', opacity:0.9 }}>Post-Race Analysis</div>
          <div style={{ fontSize:'22px', fontWeight:'800', marginTop:'4px' }}>Latest Results</div>
          <div style={{ fontSize:'13px', opacity:0.75, marginTop:'4px' }}>{dateRangeLabel()}</div>
        </div>
        <button onClick={loadResults} style={{ background:'rgba(255,255,255,0.15)', border:'1px solid rgba(255,255,255,0.4)', borderRadius:'8px', color:'white', padding:'8px 18px', cursor:'pointer', fontSize:'13px', fontWeight:'600' }}>
          Refresh
        </button>
      </div>

      {/* Summary bar */}
      {picks.length > 0 && (() => {
        const statsLeft = [
          { label:'Picks',  value: summary.total_picks || 0, color:'#93c5fd', bg:'rgba(96,165,250,0.12)', border:'rgba(96,165,250,0.3)',  icon:'🎯' },
          { label:'Won',    value: summary.wins || 0,        color:'#34d399', bg:'rgba(16,185,129,0.15)', border:'rgba(16,185,129,0.4)',  icon:'✅' },
          { label:'Placed', value: summary.places || 0,      color:'#818cf8', bg:'rgba(99,102,241,0.15)', border:'rgba(99,102,241,0.35)', icon:'🥈' },
          { label:'Lost',   value: summary.losses || 0,      color:'#f87171', bg:'rgba(239,68,68,0.13)',  border:'rgba(239,68,68,0.35)',  icon:'❌' },
        ];
        const pnlPos   = profit >= 0;
        const roiVal   = summary.roi || 0;
        return (
          <div style={{ marginBottom:'24px' }}>
            {/* Top row: 4 count stats */}
            <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap: isMobile ? '6px' : '10px', marginBottom:'10px' }}>
              {statsLeft.map((stat, i) => (
                <div key={i} style={{ background:stat.bg, border:`1.5px solid ${stat.border}`, borderRadius:'10px', padding: isMobile ? '10px 4px 8px' : '16px 10px 12px', textAlign:'center' }}>
                  <div style={{ fontSize: isMobile ? '14px' : '12px', marginBottom:'2px' }}>{stat.icon}</div>
                  <div style={{ fontSize: isMobile ? '20px' : '28px', fontWeight:'900', color:stat.color, lineHeight:1 }}>{stat.value}</div>
                  <div style={{ fontSize: isMobile ? '9px' : '11px', color:'rgba(255,255,255,0.55)', marginTop: isMobile ? '3px' : '5px', textTransform:'uppercase', letterSpacing: isMobile ? '0.5px' : '1px', fontWeight:'600' }}>{stat.label}</div>
                </div>
              ))}
            </div>
            {/* Bottom row: P&L + ROI spanning full width */}
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'10px' }}>
              <div style={{ background: pnlPos ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.13)', border:`1.5px solid ${pnlPos ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.35)'}`, borderRadius:'12px', padding: isMobile ? '10px 12px' : '14px 16px', display:'flex', alignItems:'center', justifyContent:'space-between', gap:'8px' }}>
                <div>
                  <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.55)', textTransform:'uppercase', letterSpacing:'1px', fontWeight:'600', marginBottom:'3px' }}>Profit / Loss</div>
                  <div style={{ fontSize: isMobile ? '22px' : '30px', fontWeight:'900', color: pnlPos ? '#34d399' : '#f87171', lineHeight:1 }}>
                    {pnlPos ? '+' : ''}£{Math.abs(profit).toFixed(2)}
                  </div>
                </div>
                <div style={{ fontSize: isMobile ? '22px' : '32px' }}>{pnlPos ? '📈' : '📉'}</div>
              </div>
              <div style={{ background: roiVal >= 0 ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.13)', border:`1.5px solid ${roiVal >= 0 ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.35)'}`, borderRadius:'12px', padding: isMobile ? '10px 12px' : '14px 16px', display:'flex', alignItems:'center', justifyContent:'space-between', gap:'8px' }}>
                <div>
                  <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.55)', textTransform:'uppercase', letterSpacing:'1px', fontWeight:'600', marginBottom:'3px' }}>{isMobile ? 'ROI' : 'Return on Investment'}</div>
                  <div style={{ fontSize: isMobile ? '22px' : '30px', fontWeight:'900', color: roiVal >= 0 ? '#34d399' : '#f87171', lineHeight:1 }}>
                    {roiVal >= 0 ? '+' : ''}{roiVal.toFixed(1)}%
                  </div>
                </div>
                <div style={{ fontSize: isMobile ? '22px' : '32px' }}>💰</div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Win summary headline */}
      {picks.length > 0 && (() => {
        const settled = (summary.wins || 0) + (summary.losses || 0) + (summary.places || 0);
        const winPct  = settled > 0 ? Math.round((summary.wins || 0) / settled * 100) : 0;
        const isGood  = winPct >= 33;
        return (
          <div style={{ background: isGood ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.10)', border:`1px solid ${isGood ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.3)'}`, borderRadius:'10px', padding: isMobile ? '10px 14px' : '13px 22px', marginBottom:'20px', textAlign:'center', color:'white', fontSize: isMobile ? '14px' : '17px', fontWeight:'700', letterSpacing:'0.2px', lineHeight:1.4 }}>
            {summary.wins || 0} win{(summary.wins || 0) !== 1 ? 's' : ''} from {settled} settled &mdash; {winPct}% strike rate
            {(summary.pending || 0) > 0 && (
              <div style={{ fontSize: isMobile ? '11px' : '13px', color:'rgba(255,255,255,0.55)', fontWeight:'500', marginTop: isMobile ? '3px' : '0', display: isMobile ? 'block' : 'inline' }}>
                {isMobile ? '' : <span style={{marginLeft:'12px'}} />}({summary.pending} still pending)
              </div>
            )}
          </div>
        );
      })()}

      {picks.length === 0 ? (
        <div style={{ background:'rgba(255,255,255,0.08)', borderRadius:'12px', padding:'48px 24px', textAlign:'center', color:'rgba(255,255,255,0.7)' }}>
          <div style={{ fontSize:'18px', fontWeight:'700', color:'white', marginBottom:'8px' }}>No picks found for today or yesterday</div>
          <div style={{ fontSize:'14px' }}>Today's and yesterday's AI selections will appear here once picks have been generated and results recorded.</div>
        </div>
      ) : (
        <div style={{ background:'rgba(255,255,255,0.05)', borderRadius:'14px', overflow:'hidden', border:'1px solid rgba(255,255,255,0.12)' }}>
          {/* Table header — desktop only */}
          {!isMobile && (
          <div style={{ display:'grid', gridTemplateColumns:'90px 55px 110px 1fr 70px minmax(0,2fr) 80px 70px', gap:'0', background:'rgba(30,58,95,0.9)', padding:'10px 16px', fontSize:'11px', fontWeight:'800', color:'rgba(255,255,255,0.55)', textTransform:'uppercase', letterSpacing:'0.8px', alignItems:'center' }}>
            <span>Result</span>
            <span>Day</span>
            <span>Time / Course</span>
            <span>Horse</span>
            <span style={{textAlign:'center'}}>Rating</span>
            <span>Key Reason</span>
            <span style={{textAlign:'center'}}>Odds</span>
            <span style={{textAlign:'right'}}>P&amp;L</span>
          </div>
          )}
          {picks.map((pick, idx) => {
            // Derive display emoji: prefer stored result_emoji, fall back to outcome field
            const rawOutcome = pick.result_emoji
              || (pick.outcome === 'win'    || pick.outcome === 'WON'   ? 'WIN'
                : pick.outcome === 'placed'                             ? 'PLACED'
                : pick.outcome === 'loss'   || pick.outcome === 'LOST'  ? 'LOSS'
                : null);
            const oc    = outcomeStyle(rawOutcome);
            const tier  = scoreLabel(pick.comprehensive_score || pick.analysis_score);
            const ft    = formatRaceTime(pick.race_time);
            const score = parseFloat(pick.comprehensive_score || pick.analysis_score || 0);
            const winner = pick.result_winner_name || pick.winner_name;
            const pnl   = parseFloat(pick.profit || 0);
            const isPending = !rawOutcome || rawOutcome === 'PENDING';
            // Key reason: for settled picks show result_analysis; for pending show pre-race reason
            const keyReason = !isPending && pick.result_analysis
              ? pick.result_analysis
              : (Array.isArray(pick.selection_reasons) && pick.selection_reasons.length > 0
                  ? pick.selection_reasons[0].replace(/:\s*[+-]?\d+pts?/i,'').trim()
                  : (pick.result_analysis ? pick.result_analysis.substring(0,80) : ''));
            const winnerNote = !isPending && winner && winner !== pick.horse ? `Winner: ${winner}` : '';

            if (isMobile) return (
              /* ── Mobile card layout ── */
              <div key={idx} style={{ padding:'12px 14px', borderBottom:'1px solid rgba(255,255,255,0.08)', background: idx % 2 === 0 ? 'rgba(255,255,255,0.03)' : 'transparent', borderLeft:`3px solid ${oc.border}` }}>
                {/* Row 1: result + horse + P&L */}
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:'8px' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:'8px', flex:1, minWidth:0 }}>
                    <span style={{ flexShrink:0, display:'inline-block', background:oc.bg, color:'white', padding:'3px 7px', borderRadius:'5px', fontSize:'10px', fontWeight:'800' }}>
                      {isPending ? '⏳' : oc.text}
                    </span>
                    <div style={{ minWidth:0 }}>
                      <div style={{ fontWeight:'800', color:'white', fontSize:'14px', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{pick.horse || '—'}</div>
                      <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.45)', marginTop:'1px' }}>
                        {ft.time}{ft.time && pick.course ? ' · ' : ''}{pick.course || ''}
                        {score > 0 && <span style={{ marginLeft:'6px', background:tier.bg, color:'white', padding:'1px 6px', borderRadius:'4px', fontSize:'10px', fontWeight:'700' }}>{score.toFixed(0)} {tier.label}</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign:'right', flexShrink:0 }}>
                    <div style={{ fontWeight:'900', fontSize:'15px', color: pnl > 0 ? '#34d399' : pnl < 0 ? '#f87171' : 'rgba(255,255,255,0.4)' }}>
                      {isPending ? '—' : pnl >= 0 ? `+£${pnl.toFixed(2)}` : `-£${Math.abs(pnl).toFixed(2)}`}
                    </div>
                    <div style={{ fontSize:'11px', color:'#93c5fd', fontWeight:'700' }}>{pick.odds ? toFractional(pick.odds) : ''}</div>
                  </div>
                </div>
                {/* Row 2: key reason + winner note */}
                {(keyReason || winnerNote) && (
                  <div style={{ marginTop:'5px', fontSize:'11px', lineHeight:1.4 }}>
                    {keyReason && <span style={{ color:'rgba(255,255,255,0.5)' }}>{keyReason.length > 90 ? keyReason.substring(0,90)+'…' : keyReason}</span>}
                    {winnerNote && <div style={{ color:'#f87171', marginTop:'2px' }}>{winnerNote}</div>}
                  </div>
                )}
              </div>
            );
            return (
              /* ── Desktop table row ── */
              <div key={idx} style={{ display:'grid', gridTemplateColumns:'90px 55px 110px 1fr 70px minmax(0,2fr) 80px 70px', gap:'0', padding:'11px 16px', alignItems:'center', borderBottom:'1px solid rgba(255,255,255,0.07)', background: idx % 2 === 0 ? 'rgba(255,255,255,0.03)' : 'transparent', borderLeft:`3px solid ${oc.border}` }}>

                {/* Result badge */}
                <span style={{ display:'inline-block', background:oc.bg, color:'white', padding:'4px 8px', borderRadius:'6px', fontSize:'11px', fontWeight:'800', letterSpacing:'0.3px', textAlign:'center', width:'fit-content' }}>
                  {isPending ? '⏳ PENDING' : oc.text}
                </span>

                {/* Day */}
                <span style={{ background: pick._dayLabel === 'Today' ? '#7c3aed' : '#374151', color:'white', padding:'3px 7px', borderRadius:'5px', fontSize:'10px', fontWeight:'800', textTransform:'uppercase', textAlign:'center', width:'fit-content' }}>
                  {pick._dayLabel === 'Today' ? 'Today' : 'Yest'}
                </span>

                {/* Time + Course */}
                <div style={{ lineHeight:1.3 }}>
                  <div style={{ fontWeight:'700', color:'white', fontSize:'13px' }}>{ft.time || '—'}</div>
                  <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.5)', marginTop:'1px' }}>{pick.course || ''}</div>
                </div>

                {/* Horse */}
                <div style={{ fontWeight:'800', color:'white', fontSize:'14px', paddingRight:'8px' }}>
                  {pick.horse || '—'}
                  {pick.trainer && <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.45)', fontWeight:'400', marginTop:'1px' }}>{pick.trainer}</div>}
                </div>

                {/* Rating */}
                <div style={{ textAlign:'center' }}>
                  {score > 0 && (
                    <span style={{ background:tier.bg, color:'white', padding:'3px 7px', borderRadius:'5px', fontSize:'11px', fontWeight:'800', display:'block', textAlign:'center' }}>
                      {score.toFixed(0)}
                    </span>
                  )}
                  {score > 0 && <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.4)', marginTop:'2px', textAlign:'center' }}>{tier.label}</div>}
                </div>

                {/* Key reason + winner note */}
                <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.6)', paddingRight:'8px', lineHeight:1.4 }}>
                  {keyReason && <span>{keyReason}</span>}
                  {winnerNote && <div style={{ fontSize:'11px', color:'#f87171', marginTop:'2px' }}>{winnerNote}</div>}
                </div>

                {/* Odds */}
                <div style={{ textAlign:'center', fontWeight:'700', color:'#93c5fd', fontSize:'13px' }}>
                  {pick.odds ? toFractional(pick.odds) : '—'}
                </div>

                {/* P&L */}
                <div style={{ textAlign:'right', fontWeight:'800', fontSize:'14px', color: pnl > 0 ? '#34d399' : pnl < 0 ? '#f87171' : 'rgba(255,255,255,0.4)' }}>
                  {isPending ? '—' : pnl >= 0 ? `+£${pnl.toFixed(2)}` : `-£${Math.abs(pnl).toFixed(2)}`}
                </div>
              </div>
            );
          })}
        </div>

      )}

      {/* ── Loss / Placed Analysis ───────────────────────────────── */}
      {(() => {
        const nonWins = picks.filter(p => {
          const re = p.result_emoji
            || (p.outcome === 'loss'   || p.outcome === 'LOSS'   || p.outcome === 'LOST'   ? 'LOSS'
              : p.outcome === 'placed' || p.outcome === 'PLACED'                           ? 'PLACED'
              : null);
          return re === 'LOSS' || re === 'PLACED';
        });
        if (nonWins.length === 0) return null;

        const SCORE_LABELS_MAP = {
          going_suitability:'Going Suitability', recent_win:'Last Race Win', total_wins:'Form Wins',
          form:'Recent Form', form_score:'Recent Form', sweet_spot:'Odds Sweet Spot',
          consistency:'Consistency', course_performance:'C&D Wins', cd_bonus:'C&D Bonus',
          trainer_strike_rate:'Trainer Strike Rate', meeting_focus_trainer:'Trainer @ Meeting',
          jockey_quality:'Jockey Quality', database_history:'DB History', age_factor:'Age Factor',
        };

        const applyLearning = async () => {
          setLearning({ state: 'loading', message: 'Analysing missed winners and updating model weights…', changes: {} });
          try {
            const res  = await fetch(API_BASE_URL + '/api/learning/apply', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({}) });
            const data = await res.json();
            if (data.success) {
              setLearning({ state: 'done', message: data.message, changes: data.changes || {} });
            } else {
              setLearning({ state: 'error', message: data.error || 'Unknown error', changes: {} });
            }
          } catch (e) {
            setLearning({ state: 'error', message: 'Network error: ' + e.message, changes: {} });
          }
        };

        return (
          <div style={{ marginTop:'32px' }}>
            <div style={{ marginBottom:'16px' }}>
              <div style={{ fontSize:'17px', fontWeight:'800', color:'white', marginBottom:'3px' }}>🔍 Why We Missed — &amp; What The Model Learned</div>
              <div style={{ fontSize:'13px', color:'rgba(255,255,255,0.45)' }}>
                For each non-win: how the real winner ranked in our model, and which scoring factors to adjust
              </div>
            </div>

            {nonWins.map((pick, idx) => {
              const sb       = pick.score_breakdown || {};
              const odds     = parseFloat(pick.odds || 0);
              const score    = parseFloat(pick.comprehensive_score || pick.analysis_score || 0);
              const winner   = pick.result_winner_name || pick.winner_name || '?';
              const ft       = formatRaceTime(pick.race_time);
              const wa       = pick.winner_analysis || {};
              const isPlaced = (pick.result_emoji || pick.outcome || '').toUpperCase().includes('PLACED');

              const topBreakdown = Object.entries(sb)
                .filter(([,v]) => parseFloat(v) > 0)
                .sort(([,a],[,b]) => parseFloat(b) - parseFloat(a))
                .slice(0, 5);

              return (
                <div key={idx} style={{ background:'#1a1a2e', border:`1px solid ${isPlaced ? 'rgba(59,130,246,0.4)' : 'rgba(239,68,68,0.4)'}`, borderRadius:'12px', padding: isMobile ? '14px' : '20px 24px', marginBottom:'18px', borderLeft:`4px solid ${isPlaced ? '#3b82f6' : '#ef4444'}` }}>

                  {/* Header row */}
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'8px', marginBottom:'16px' }}>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontSize: isMobile ? '15px' : '18px', fontWeight:'800', color:'white' }}>
                        {isPlaced ? '🥈' : '✗'} {pick.horse}
                        <span style={{ marginLeft:'8px', fontSize:'12px', fontWeight:'600', color: isPlaced ? '#60a5fa' : '#f87171' }}>{isPlaced ? 'PLACED' : 'LOSS'}</span>
                      </div>
                      <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.5)', marginTop:'3px' }}>
                        {ft.time} · {pick.course}
                        &nbsp;·&nbsp;Our score: <strong style={{color:'white'}}>{score.toFixed(0)}/100</strong>
                        &nbsp;·&nbsp;Odds: <strong style={{color:'#93c5fd'}}>{(odds-1).toFixed(0)}/1</strong>
                      </div>
                    </div>
                    <div style={{ background: isPlaced ? 'rgba(59,130,246,0.2)' : 'rgba(239,68,68,0.2)', border:`1px solid ${isPlaced ? 'rgba(59,130,246,0.45)' : 'rgba(239,68,68,0.45)'}`, color: isPlaced ? '#93c5fd' : '#fca5a5', borderRadius:'7px', padding:'6px 12px', fontSize:'11px', fontWeight:'700', lineHeight:1.5, textAlign:'right', flexShrink:0 }}>
                      {pick.result_analysis || (winner !== '?' ? `Winner: ${winner}` : 'Result recorded')}
                    </div>
                  </div>

                  {/* Winner comparison bar */}
                  {wa.winner_found && (
                    <div style={{ background:'rgba(255,255,255,0.06)', borderRadius:'10px', padding:'14px 16px', marginBottom:'16px' }}>
                      <div style={{ fontSize:'10px', fontWeight:'800', color:'#fbbf24', textTransform:'uppercase', letterSpacing:'1px', marginBottom:'12px' }}>🏆 Winner Comparison — {wa.winner_name}</div>
                      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                        {/* Our pick */}
                        <div style={{ background:'rgba(239,68,68,0.12)', borderRadius:'8px', padding:'10px 12px', border:'1px solid rgba(239,68,68,0.25)' }}>
                          <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', marginBottom:'4px', textTransform:'uppercase', letterSpacing:'0.8px' }}>Our Pick</div>
                          <div style={{ fontWeight:'800', color:'white', fontSize:'14px' }}>{pick.horse}</div>
                          <div style={{ fontSize:'20px', fontWeight:'900', color:'#f87171', marginTop:'4px' }}>{score.toFixed(0)}<span style={{fontSize:'11px',fontWeight:'500',color:'rgba(255,255,255,0.4)'}}>/100</span></div>
                          <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.45)', marginTop:'2px' }}>Ranked #1 in field · {(odds-1).toFixed(0)}/1</div>
                        </div>
                        {/* Actual winner */}
                        <div style={{ background:'rgba(16,185,129,0.12)', borderRadius:'8px', padding:'10px 12px', border:'1px solid rgba(16,185,129,0.25)' }}>
                          <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', marginBottom:'4px', textTransform:'uppercase', letterSpacing:'0.8px' }}>Actual Winner</div>
                          <div style={{ fontWeight:'800', color:'white', fontSize:'14px' }}>{wa.winner_name}</div>
                          <div style={{ fontSize:'20px', fontWeight:'900', color:'#34d399', marginTop:'4px' }}>{wa.winner_score}<span style={{fontSize:'11px',fontWeight:'500',color:'rgba(255,255,255,0.4)'}}>/100</span></div>
                          <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.45)', marginTop:'2px' }}>Ranked #{wa.winner_rank} of {wa.winner_rank_of} · {wa.winner_odds_fractional}</div>
                        </div>
                      </div>
                      {/* Score gap bar */}
                      <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.45)', marginBottom:'6px' }}>
                        Model gap: <strong style={{color: wa.score_gap > 10 ? '#fbbf24' : '#a3a3a3'}}>{wa.score_gap > 0 ? '+' : ''}{wa.score_gap} pts</strong> in favour of our pick
                      </div>
                      {/* Why missed bullets */}
                      {(wa.why_missed || []).map((reason, ri) => (
                        <div key={ri} style={{ display:'flex', gap:'7px', alignItems:'flex-start', marginTop:'6px' }}>
                          <span style={{ color:'#fbbf24', flexShrink:0, marginTop:'1px' }}>›</span>
                          <span style={{ fontSize:'12px', color:'rgba(255,255,255,0.65)', lineHeight:1.5 }}>{reason}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Score breakdown */}
                  {topBreakdown.length > 0 && (
                    <div>
                      <div style={{ fontSize:'10px', fontWeight:'800', color:'#f59e0b', textTransform:'uppercase', letterSpacing:'1px', marginBottom:'8px' }}>📊 What inflated our score</div>
                      {topBreakdown.map(([k, v], bi) => {
                        const pts    = parseFloat(v);
                        const pct    = score > 0 ? pts / score * 100 : 0;
                        const isHigh = k === 'going_suitability' || pts > 22;
                        const label  = SCORE_LABELS_MAP[k] || k.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
                        return (
                          <div key={bi} style={{ marginBottom:'7px' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'3px' }}>
                              <span style={{ fontSize:'11px', color: isHigh ? '#fbbf24' : 'rgba(255,255,255,0.5)' }}>{isHigh ? '⚠️ ' : ''}{label}</span>
                              <span style={{ fontSize:'11px', fontWeight:'700', color: isHigh ? '#fbbf24' : '#93c5fd' }}>+{pts.toFixed(0)} pts ({pct.toFixed(0)}%)</span>
                            </div>
                            <div style={{ background:'rgba(255,255,255,0.08)', borderRadius:'3px', height:'5px', overflow:'hidden' }}>
                              <div style={{ width:`${Math.min(pct,100)}%`, height:'100%', background: isHigh ? '#f59e0b' : '#3b82f6', borderRadius:'3px' }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Apply Learning button + status */}
            <div style={{ background:'rgba(16,185,129,0.08)', border:'1px solid rgba(16,185,129,0.3)', borderRadius:'12px', padding:'20px 24px' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'12px', marginBottom: learningStatus.state !== 'idle' ? '16px' : '0' }}>
                <div>
                  <div style={{ fontSize:'13px', fontWeight:'800', color:'#34d399', marginBottom:'4px' }}>🧠 Auto-Update Model Weights</div>
                  <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.5)', lineHeight:1.5 }}>
                    Analyses every missed winner above and nudges the scoring weights in DynamoDB so tomorrow's picks improve.
                  </div>
                </div>
                <button
                  onClick={applyLearning}
                  disabled={learningStatus.state === 'loading'}
                  style={{ background: learningStatus.state === 'done' ? '#059669' : '#1d4ed8', border:'none', borderRadius:'8px', color:'white', padding:'10px 20px', cursor: learningStatus.state === 'loading' ? 'not-allowed' : 'pointer', fontWeight:'700', fontSize:'13px', opacity: learningStatus.state === 'loading' ? 0.7 : 1, flexShrink:0, whiteSpace:'nowrap' }}
                >
                  {learningStatus.state === 'loading' ? '⏳ Updating…' : learningStatus.state === 'done' ? '✅ Applied' : '⚡ Apply Learning Now'}
                </button>
              </div>
              {learningStatus.state === 'done' && (
                <div>
                  <div style={{ fontSize:'12px', color:'#34d399', marginBottom:'10px', fontWeight:'700' }}>{learningStatus.message}</div>
                  {Object.keys(learningStatus.changes).length > 0 && (
                    <div style={{ display:'flex', flexWrap:'wrap', gap:'8px' }}>
                      {Object.entries(learningStatus.changes).map(([factor, ch]) => (
                        <div key={factor} style={{ background:'rgba(255,255,255,0.07)', borderRadius:'6px', padding:'5px 10px', fontSize:'11px' }}>
                          <span style={{ color:'rgba(255,255,255,0.5)', textTransform:'capitalize' }}>{factor.replace(/_/g,' ')}</span>
                          <span style={{ marginLeft:'6px', fontWeight:'800', color: ch.nudge > 0 ? '#34d399' : '#f87171' }}>
                            {ch.from.toFixed(1)} → {ch.to.toFixed(1)} ({ch.nudge > 0 ? '+' : ''}{ch.nudge.toFixed(2)})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {learningStatus.state === 'error' && (
                <div style={{ fontSize:'12px', color:'#f87171', marginTop:'8px' }}>⚠️ {learningStatus.message}</div>
              )}
            </div>
          </div>
        );
      })()}

      <div style={{ marginTop:'28px', padding:'14px 18px', background:'rgba(255,255,255,0.06)', borderRadius:'10px', color:'rgba(255,255,255,0.45)', fontSize:'12px', textAlign:'center', lineHeight:'1.6' }}>
        Results are recorded after each race. Pending picks update as results come in. \u00b7 Always bet responsibly.
      </div>
    </div>
  );
}

// ---- Major Races ----
function MajorRacesView() {
  const [filter,   setFilter]   = useState('all');
  const [showPast, setShowPast] = useState(false);

  const filtered = MAJOR_RACES.filter(r => {
    if (!showPast && isPast(r.date)) return false;
    if (filter === 'NH')        return r.type === 'NH';
    if (filter === 'Flat')      return r.type === 'Flat';
    if (filter === 'highlight') return r.highlight;
    return true;
  });

  const grouped       = groupByMeeting(filtered);
  const upcomingCount = MAJOR_RACES.filter(r => !isPast(r.date)).length;
  const nextRace      = MAJOR_RACES.filter(r => !isPast(r.date)).sort((a,b) => a.date.localeCompare(b.date))[0];

  const meetingColour = m => ({
    Aintree:'#c2410c', Punchestown:'#047857', Newmarket:'#1d4ed8', Epsom:'#7c3aed',
    'Royal Ascot':'#b45309', Goodwood:'#065f46', York:'#1e40af', Doncaster:'#3f3f46',
    Ascot:'#92400e', Sandown:'#0f766e', Chester:'#6b21a8', Ayr:'#064e3b',
  }[m] || '#374151');

  return (
    <div>
      <div style={{ background:'linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e1b4b 100%)', border:'2px solid #818cf8', borderRadius:'12px', padding:'24px 28px', marginBottom:'24px', color:'white' }}>
        <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1.5px', color:'#a5b4fc', marginBottom:'6px' }}>2026 Major Race Calendar</div>
        <div style={{ fontSize:'24px', fontWeight:'800', marginBottom:'8px' }}>Group 1 &amp; Feature Races</div>
        <div style={{ fontSize:'14px', color:'rgba(255,255,255,0.75)', marginBottom: nextRace ? '16px' : '0' }}>
          {upcomingCount} upcoming major races \u00b7 UK &amp; Ireland
        </div>
        {nextRace && (
          <div style={{ background:'rgba(255,255,255,0.1)', border:'1px solid rgba(255,255,255,0.2)', borderRadius:'8px', padding:'12px 16px', display:'inline-flex', gap:'20px', flexWrap:'wrap', alignItems:'center' }}>
            <div>
              <div style={{ fontSize:'10px', color:'#a5b4fc', textTransform:'uppercase', letterSpacing:'1px' }}>Next Major Race</div>
              <div style={{ fontSize:'16px', fontWeight:'800', marginTop:'2px' }}>{nextRace.name}</div>
              <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.75)' }}>{nextRace.meeting} \u00b7 {formatDate(nextRace.date)}</div>
            </div>
            <div style={{ background:'#818cf8', borderRadius:'8px', padding:'8px 18px', fontSize:'20px', fontWeight:'800', minWidth:'100px', textAlign:'center' }}>{daysUntil(nextRace.date)}</div>
          </div>
        )}
      </div>

      <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', marginBottom:'20px', alignItems:'center' }}>
        {[
          { key:'all',       label:'All Races'       },
          { key:'highlight', label:'\u2b50 Highlights' },
          { key:'NH',        label:'National Hunt'   },
          { key:'Flat',      label:'Flat Racing'     },
        ].map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} style={{
            background: filter===f.key ? 'rgba(129,140,248,0.3)' : 'rgba(255,255,255,0.08)',
            border:     filter===f.key ? '2px solid #818cf8' : '2px solid rgba(255,255,255,0.15)',
            borderRadius:'8px', color:'white', cursor:'pointer', padding:'8px 16px', fontSize:'13px',
            fontWeight: filter===f.key ? '700' : '400', transition:'all 0.15s',
          }}>{f.label}</button>
        ))}
        <button onClick={() => setShowPast(!showPast)} style={{ background: showPast?'rgba(107,114,128,0.3)':'rgba(255,255,255,0.05)', border:'2px solid rgba(255,255,255,0.15)', borderRadius:'8px', color:'rgba(255,255,255,0.6)', cursor:'pointer', padding:'8px 16px', fontSize:'12px', marginLeft:'auto' }}>
          {showPast ? 'Hide Past' : 'Show Past'}
        </button>
      </div>

      {grouped.length === 0 ? (
        <div style={{ textAlign:'center', padding:'48px', color:'rgba(255,255,255,0.5)', fontSize:'16px' }}>No races match the filter.</div>
      ) : grouped.map(({ date, meeting, races }) => {
        const past = isPast(date);
        const col  = meetingColour(meeting);
        return (
          <div key={date + '__' + meeting} style={{ background: past ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.08)', borderRadius:'12px', marginBottom:'20px', overflow:'hidden', opacity: past ? 0.65 : 1 }}>
            <div style={{ background: past ? '#374151' : col, padding:'14px 20px', display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
              <div>
                <span style={{ fontSize:'18px', fontWeight:'800', color:'white' }}>{meeting}</span>
                <span style={{ fontSize:'13px', color:'rgba(255,255,255,0.8)', marginLeft:'12px' }}>{formatDate(date)}</span>
              </div>
              {past
                ? <span style={{ background:'rgba(0,0,0,0.25)', color:'white', padding:'4px 12px', borderRadius:'6px', fontSize:'12px', fontWeight:'600' }}>Complete</span>
                : <span style={{ background:'rgba(255,255,255,0.25)', color:'white', padding:'4px 14px', borderRadius:'6px', fontSize:'13px', fontWeight:'800' }}>{daysUntil(date)}</span>
              }
            </div>
            <div style={{ padding:'12px 16px', display:'flex', flexDirection:'column', gap:'10px' }}>
              {races.map((race, i) => (
                <div key={i} style={{
                  background: race.highlight && !past ? 'linear-gradient(135deg,rgba(217,119,6,0.12) 0%,rgba(255,255,255,0.08) 100%)' : 'rgba(255,255,255,0.05)',
                  border:     race.highlight && !past ? '1px solid rgba(217,119,6,0.4)' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius:'8px', padding:'12px 16px',
                }}>
                  <div style={{ display:'flex', alignItems:'flex-start', gap:'8px', flexWrap:'wrap' }}>
                    {race.highlight && !past && <span>\u2b50</span>}
                    <div style={{ flex:1 }}>
                      <div style={{ display:'flex', alignItems:'center', gap:'8px', flexWrap:'wrap', marginBottom:'4px' }}>
                        <span style={{ fontSize:'16px', fontWeight:'700', color:'white' }}>{race.name}</span>
                        <span style={{
                          background: race.grade==='G1' ? 'linear-gradient(135deg,#d97706,#b45309)' : race.grade==='G2' ? '#1d4ed8' : '#374151',
                          color:'white', padding:'2px 8px', borderRadius:'5px', fontSize:'11px', fontWeight:'700',
                        }}>{race.grade}</span>
                        <span style={{
                          background: race.type==='NH' ? 'rgba(4,120,87,0.3)' : 'rgba(29,78,216,0.3)',
                          border: `1px solid ${race.type==='NH' ? '#059669' : '#3b82f6'}`,
                          color:  race.type==='NH' ? '#6ee7b7' : '#93c5fd',
                          padding:'2px 8px', borderRadius:'5px', fontSize:'11px',
                        }}>{race.type==='NH' ? 'Jump' : 'Flat'}</span>
                      </div>
                      <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.55)', display:'flex', gap:'14px', flexWrap:'wrap', marginBottom: race.notes ? '5px' : '0' }}>
                        <span>{race.distance}</span>
                        {race.purse && <span>{race.purse}</span>}
                      </div>
                      {race.notes && <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.65)', lineHeight:'1.5' }}>{race.notes}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div style={{ marginTop:'20px', padding:'14px 18px', background:'rgba(255,255,255,0.06)', borderRadius:'10px', color:'rgba(255,255,255,0.5)', fontSize:'12px', display:'flex', gap:'20px', flexWrap:'wrap', justifyContent:'center' }}>
        <span><span style={{ background:'linear-gradient(135deg,#d97706,#b45309)', color:'white', padding:'1px 7px', borderRadius:'4px', fontSize:'11px', fontWeight:'700', marginRight:'6px' }}>G1</span>Group 1</span>
        <span><span style={{ background:'#1d4ed8', color:'white', padding:'1px 7px', borderRadius:'4px', fontSize:'11px', fontWeight:'700', marginRight:'6px' }}>G2</span>Group 2</span>
        <span>\u2b50 Must-watch highlight races</span>
        <span>Dates are indicative and may change</span>
      </div>
    </div>
  );
}

export default App;
