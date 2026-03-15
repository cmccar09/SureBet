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
          { key:'picks',  label:"Today's Picks", emoji:'\ud83c\udfaf', sub:'Top 5 value bets'  },
          { key:'majors', label:'Major Races',    emoji:'\ud83c\udfc6', sub:'Group 1 calendar'  },
        ].map(tab => (
          <button key={tab.key} onClick={() => setPage(tab.key)} style={{
            background: page===tab.key ? 'linear-gradient(135deg,#059669 0%,#047857 100%)' : 'rgba(255,255,255,0.12)',
            border:     page===tab.key ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.25)',
            borderRadius:'10px', color:'white', cursor:'pointer',
            padding:'12px 28px', minWidth:'180px', textAlign:'center', transition:'all 0.2s',
          }}>
            <div style={{ fontSize:'16px', fontWeight:'700' }}>{tab.emoji} {tab.label}</div>
            <div style={{ fontSize:'11px', opacity:0.75, marginTop:'2px' }}>{tab.sub}</div>
          </button>
        ))}
      </div>
      <main style={{ maxWidth:'960px', margin:'0 auto', padding:'0 12px' }}>
        {page==='picks' ? <DailyPicksView /> : <MajorRacesView />}
      </main>
    </div>
  );
}

// ---- Daily Picks ----
function DailyPicksView() {
  const [picks, setPicks]             = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => { loadPicks(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    return             { bg: '#8b5cf6', label: 'VALUE'  };
  };

  if (loading) return (
    <div style={{ textAlign:'center', padding:'60px 20px', color:'white' }}>
      <div style={{ fontSize:'32px', marginBottom:'16px' }}>\u23f3</div>
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
          <div style={{ fontSize:'13px', textTransform:'uppercase', letterSpacing:'1px', opacity:0.75 }}>Today's Top Picks</div>
          <div style={{ fontSize:'22px', fontWeight:'800', marginTop:'4px' }}>{today}</div>
          {lastUpdated && <div style={{ fontSize:'12px', opacity:0.65, marginTop:'4px' }}>Last updated {lastUpdated} \u00b7 Auto-refreshes 12:00, 14:00, 16:00</div>}
        </div>
        <button onClick={loadPicks} style={{ background:'rgba(255,255,255,0.15)', border:'1px solid rgba(255,255,255,0.35)', borderRadius:'8px', color:'white', padding:'8px 18px', cursor:'pointer', fontSize:'13px', fontWeight:'600' }}>
          \ud83d\udd04 Refresh
        </button>
      </div>

      {picks.length === 0 ? (
        <div style={{ background:'rgba(255,255,255,0.08)', borderRadius:'12px', padding:'48px 24px', textAlign:'center', color:'rgba(255,255,255,0.7)' }}>
          <div style={{ fontSize:'40px', marginBottom:'16px' }}>\ud83d\udc0e</div>
          <div style={{ fontSize:'18px', fontWeight:'700', color:'white', marginBottom:'8px' }}>No picks yet today</div>
          <div style={{ fontSize:'14px' }}>Betfair odds are fetched at 12:00, 14:00 and 16:00 daily.<br/>The model scores all runners and selects the top 5 value bets.</div>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>
          {picks.map((pick, idx) => {
            const tier   = tierInfo(pick.score);
            const medals = ['\ud83e\udd47','\ud83e\udd48','\ud83e\udd49','4\ufe0f\u20e3','5\ufe0f\u20e3'];
            return (
              <div key={idx} style={{ background:'white', borderRadius:'12px', padding:'20px 22px', borderLeft:`5px solid ${tier.bg}`, boxShadow:'0 2px 12px rgba(0,0,0,0.1)' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'8px' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                    <span style={{ fontSize:'22px' }}>{medals[idx]}</span>
                    <div>
                      <div style={{ fontSize:'20px', fontWeight:'800', color:'#111' }}>{pick.horse || pick.horse_name || 'Unknown'}</div>
                      <div style={{ fontSize:'13px', color:'#6b7280', marginTop:'2px' }}>
                        {pick.course    && <span>\ud83d\udccd {pick.course}</span>}
                        {pick.race_time && <span style={{ marginLeft:'12px' }}>\u23f0 {pick.race_time}</span>}
                        {pick.race_name && <span style={{ marginLeft:'12px' }}>\ud83c\udfc1 {pick.race_name}</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'center' }}>
                    {pick.odds && <span style={{ background:'#1e3a5f', color:'white', padding:'5px 14px', borderRadius:'8px', fontWeight:'800', fontSize:'16px' }}>{pick.odds}</span>}
                    <span style={{ background:tier.bg, color:'white', padding:'5px 12px', borderRadius:'8px', fontSize:'12px', fontWeight:'700' }}>
                      {tier.label}{pick.score ? ' ' + parseFloat(pick.score).toFixed(0) : ''}
                    </span>
                  </div>
                </div>
                {(pick.trainer || pick.jockey) && (
                  <div style={{ fontSize:'13px', color:'#374151', marginTop:'12px', display:'flex', gap:'20px', flexWrap:'wrap' }}>
                    {pick.trainer  && <span>\ud83d\udc68\u200d\ud83c\udfeb <strong>T:</strong> {pick.trainer}</span>}
                    {pick.jockey   && <span>\ud83c\udfbd <strong>J:</strong> {pick.jockey}</span>}
                    {pick.going    && <span>\ud83c\udf31 <strong>Going:</strong> {pick.going}</span>}
                    {pick.distance && <span>\ud83d\udccf {pick.distance}</span>}
                  </div>
                )}
                {pick.score_gap && parseFloat(pick.score_gap) >= 3 && (
                  <div style={{ marginTop:'10px' }}>
                    <span style={{ background:'#f0fdf4', border:'1px solid #86efac', borderRadius:'6px', padding:'3px 10px', fontSize:'12px', color:'#166534', fontWeight:'600' }}>
                      +{parseFloat(pick.score_gap).toFixed(0)}pt ahead of next rival
                    </span>
                  </div>
                )}
                {(pick.research_notes || pick.analysis_notes || (pick.tips && pick.tips.length > 0)) && (
                  <div style={{ marginTop:'12px', padding:'10px 14px', background:'#f8fafc', borderRadius:'8px', borderLeft:`3px solid ${tier.bg}` }}>
                    <div style={{ fontSize:'10px', fontWeight:'700', color:tier.bg, textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:'4px' }}>Why this horse</div>
                    <div style={{ fontSize:'13px', color:'#374151', lineHeight:'1.5' }}>
                      {pick.research_notes || pick.analysis_notes || (pick.tips || []).join(' \u00b7 ')}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div style={{ marginTop:'28px', padding:'16px 20px', background:'rgba(255,255,255,0.07)', borderRadius:'10px', color:'rgba(255,255,255,0.6)', fontSize:'12px', textAlign:'center', lineHeight:'1.6' }}>
        Picks generated by AI analysis of Betfair odds, form, trainer &amp; jockey stats, going suitability and market movement.<br/>
        Top 5 from all races over the next 3 days. Always bet responsibly.
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
