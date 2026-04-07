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

// ---- Pick best key reasons from selection_reasons ----
// Returns top N reasons: non-generic first, sorted by pts value
function bestKeyReasons(reasons, n = 2) {
  if (!Array.isArray(reasons) || reasons.length === 0) return [];
  const parsePts = r => { const m = r.match(/:\s*([+-]?\d+(?:\.\d+)?)\s*pts?/i); return m ? Math.abs(parseFloat(m[1])) : 0; };
  const isGeneric = r => /sweet spot|near optimal odds|short odds|long shot|\d+[-–]\d+\s*odds/i.test(r);
  const sorted = [...reasons].sort((a, b) => {
    const ag = isGeneric(a) ? 1 : 0, bg = isGeneric(b) ? 1 : 0;
    if (ag !== bg) return ag - bg;
    return parsePts(b) - parsePts(a);
  });
  return sorted.slice(0, n).map(r => r.replace(/:\s*[+-]?\d+(?:\.\d+)?\s*pts?/i, '').trim());
}

// Derive readable reasons from score_breakdown when selection_reasons is empty
const SB_LABELS = {
  going_suitability:    'Proven suited to today\'s going',
  cd_bonus:             'Course & distance winner',
  course_performance:   'Strong course record',
  total_wins:           'Multiple career wins',
  market_leader:        'Market leader (lowest odds)',
  jockey_quality:       'Top-quality jockey booking',
  jockey_course_bonus:  'Jockey excels at this course',
  distance_suitability: 'Proven at today\'s distance',
  consistency:          'Highly consistent performer',
  deep_form:            'Strong deep form',
  recent_win:           'Recent win in form',
  database_history:     'Strong historical record here',
  bounce_back:          'Due a bounce-back run',
  meeting_focus:        'Trainer targeting this meeting',
  unexposed_bonus:      'Lightly-raced & unexposed',
  age_bonus:            'Ideal peak racing age',
  optimal_odds:         'Near-optimal betting odds',
  sweet_spot:           'Odds in the model\'s sweet spot',
};
function reasonsFromBreakdown(sb, n = 2) {
  if (!sb || typeof sb !== 'object') return [];
  const generic = new Set(['sweet_spot','optimal_odds']);
  const entries = Object.entries(sb)
    .filter(([, v]) => parseFloat(v) > 0)
    .sort((a, b) => {
      const ag = generic.has(a[0]) ? 1 : 0, bg = generic.has(b[0]) ? 1 : 0;
      if (ag !== bg) return ag - bg;
      return parseFloat(b[1]) - parseFloat(a[1]);
    });
  return entries.slice(0, n).map(([k]) => SB_LABELS[k] || k.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase()));
}

// ---- Optimal Betting Window ----
// Parse UTC race_time string and display in BST (Europe/Dublin)
function fmtUtcTime(rt) {
  if (!rt) return '';
  const s = rt.length <= 16 ? rt + ':00Z' : (rt.endsWith('Z') || rt.includes('+') ? rt : rt + 'Z');
  const d = new Date(s);
  return isNaN(d) ? rt.substring(11,16) : d.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Europe/Dublin'});
}

function bettingWindow(pick, now) {
  const odds  = parseFloat(pick.odds || 0);
  const sb    = pick.score_breakdown || {};
  const isML  = parseFloat(sb.market_leader || 0) > 0;

  // Time to race in minutes
  let mins = null;
  if (pick.race_time) {
    try {
      const rawRt = pick.race_time || '';
    const rt = new Date(!rawRt.endsWith('Z') && !rawRt.includes('+') ? rawRt + 'Z' : rawRt);
      if (!isNaN(rt)) mins = Math.round((rt - now) / 60000);
    } catch {}
  }

  // Already past or within 15 mins — urgent
  if (mins !== null && mins <= 15 && mins >= -10) {
    return { label:'⏰ Bet Now', desc:'Race imminent', color:'#dc2626', bg:'#fef2f2', border:'#fca5a5' };
  }
  // Within 90 mins + short price — get in before it goes
  if (mins !== null && mins <= 90 && odds > 0 && odds <= 3.0) {
    return { label:'⏰ Bet Now', desc:'Short price + race soon', color:'#dc2626', bg:'#fef2f2', border:'#fca5a5' };
  }
  // Odds-on — price will only shorten
  if (odds > 0 && odds <= 1.8) {
    return { label:'⚡ Bet Early', desc:'Odds-on — lock in before it shortens', color:'#d97706', bg:'#fffbeb', border:'#fcd34d' };
  }
  // Up to 2/1 and market leader — sharp money will move it
  if (odds > 0 && odds <= 3.0 && isML) {
    return { label:'⚡ Bet Early', desc:'Market leader — sharp money expected', color:'#d97706', bg:'#fffbeb', border:'#fcd34d' };
  }
  // Sweet spot 2/1–5/1 — 1-2 hrs before is fine
  if (odds > 0 && odds <= 6.0) {
    return { label:'🕐 1-2hrs Before', desc:'Price stable until near off', color:'#059669', bg:'#f0fdf4', border:'#a7f3d0' };
  }
  // Bigger price — odds unlikely to move much
  return { label:'📅 Anytime Today', desc:'Long price — odds stable', color:'#6b7280', bg:'#f9fafb', border:'#e5e7eb' };
}

// ---- Race Intel summary generator ----
function raceIntelSummary(pick, now) {
  const sb        = pick.score_breakdown || {};
  const allHorses = pick.all_horses || [];
  const ourScore  = parseFloat(pick.score || pick.comprehensive_score || 0);
  const ourHorse  = (pick.horse || '').toLowerCase();

  // Last analysed time
  const analysedAt = pick.updated_at || pick.created_at || null;
  let analysedStr = null, freshness = null, freshnessOk = true;
  if (analysedAt) {
    const analysedDate = new Date(analysedAt);
    const minsAgo      = Math.round(((now || new Date()) - analysedDate) / 60000);
    analysedStr = minsAgo < 60
      ? `${minsAgo} min ago`
      : `${Math.floor(minsAgo / 60)}h ${minsAgo % 60}m ago`;

    // Gap between last analysis and race start
    // Parse race_time as UTC (bare ISO strings have no tz — treat as UTC)
    const raceDate = pick.race_time ? (() => { const _rt = pick.race_time; return new Date(!_rt.endsWith('Z') && !_rt.includes('+') ? _rt + 'Z' : _rt); })() : null;
    if (!isNaN(raceDate)) {
      const gapMins = Math.round((raceDate - analysedDate) / 60000);
      // How far is the race from NOW (not from analysis time)
      const minsToRace = Math.round((raceDate - (now || new Date())) / 60000);
      const analysisAgeHours = minsAgo / 60;

      if (minsToRace <= 0) {
        freshness = 'Race started';
        freshnessOk = false;
      } else if (minsToRace <= 30 && analysisAgeHours >= 2) {
        // Within 30 mins of race but analysis is >2h old — flag as stale
        freshness = `⚠ Last check ${Math.floor(analysisAgeHours)}h ago — re-run soon`;
        freshnessOk = false;
      } else if (gapMins <= 0) {
        freshness = 'Analysis after race start';
        freshnessOk = false;
      } else if (gapMins <= 30) {
        freshness = `✓ Final check: ${gapMins}min before race`;
        freshnessOk = true;
      } else if (gapMins <= 120) {
        freshness = `${gapMins}min before race`;
        freshnessOk = true;
      } else {
        const h = Math.floor(gapMins / 60), m = gapMins % 60;
        freshness = `${h}h ${m > 0 ? m + 'm' : ''} before race`.trim();
        freshnessOk = gapMins <= 180;
      }
    }
  }

  // Main rival
  const sorted  = [...allHorses].sort((a, b) => parseFloat(b.score||0) - parseFloat(a.score||0));
  const rival   = sorted.find(h => (h.horse||'').toLowerCase() !== ourHorse);
  const rivalGap = rival ? (ourScore - parseFloat(rival.score||0)).toFixed(0) : null;

  // Key edge from score_breakdown (top non-generic positive factor)
  const generic  = new Set(['sweet_spot', 'optimal_odds']);
  const topFactor = Object.entries(sb)
    .filter(([k, v]) => !generic.has(k) && parseFloat(v) > 0)
    .sort((a, b) => parseFloat(b[1]) - parseFloat(a[1]))[0];
  const keyEdge  = topFactor ? (SCORE_LABELS[topFactor[0]] || topFactor[0].replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())) + ` (+${parseFloat(topFactor[1]).toFixed(0)}pts)` : null;

  // Risk flag
  const penaltyTotal = Object.entries(sb).filter(([,v]) => parseFloat(v) < 0).reduce((s,[,v]) => s + parseFloat(v), 0);
  let riskStr = null;
  if (rivalGap !== null && parseInt(rivalGap) <= 3) riskStr = `Tight race — ${rival.horse} only ${rivalGap}pt${rivalGap==='1'?'':'s'} behind`;
  else if (penaltyTotal < -5) riskStr = `Penalty flags applied (${penaltyTotal.toFixed(0)}pts deducted)`;

  return { analysedStr, freshness, freshnessOk, keyEdge, rival, rivalGap, riskStr };
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
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' && window.innerWidth < 600);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 600);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return (
    <div className="App">
      <header className="App-header">
        <h1>BetBudAI.com</h1>
        <p style={{ fontSize: '14px', opacity: 0.8, margin: '4px 0 0' }}>AI-powered racing analysis \u00b7 UK &amp; Ireland</p>
      </header>
      <div style={{ display:'flex', justifyContent:'center', gap:'12px', marginBottom:'32px', flexWrap:'wrap' }}>
        {[
          { key:'picks',     label:"Today's Picks",    emoji:'\ud83c\udfaf', sub:'Top 5 value bets'     },
          { key:'yesterday', label:'Latest Results',    emoji:'\ud83d\udcca', sub:'Today & yesterday'    },
          { key:'laythe',    label:'Lay the Fav',       emoji:'\ud83d\udea8', sub:'Suspect favourites'   },
          { key:'majors',    label:'Major Races',       emoji:'\ud83c\udfc6', sub:'Group 1 calendar'    },
        ].map(tab => (
          <button key={tab.key} onClick={() => setPage(tab.key)} style={{
            background: tab.key==='laythe'
              ? (page===tab.key ? 'linear-gradient(135deg,#b91c1c 0%,#991b1b 100%)' : 'rgba(185,28,28,0.18)')
              : (page===tab.key ? 'linear-gradient(135deg,#059669 0%,#047857 100%)' : 'rgba(255,255,255,0.12)'),
            border: tab.key==='laythe'
              ? (page===tab.key ? '2px solid #ef4444' : '2px solid rgba(239,68,68,0.4)')
              : (page===tab.key ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.25)'),
            borderRadius:'10px', color:'white', cursor:'pointer',
            padding: isMobile ? '10px 12px' : '12px 24px',
            minWidth: isMobile ? 0 : '160px',
            flex: isMobile ? '0 0 calc(50% - 6px)' : undefined,
            textAlign:'center', transition:'all 0.2s',
          }}>
            <div style={{ fontSize:'16px', fontWeight:'700' }}>{tab.emoji} {tab.label}</div>
            <div style={{ fontSize:'11px', opacity:0.75, marginTop:'2px' }}>{tab.sub}</div>
          </button>
        ))}
      </div>
      <main style={{ maxWidth:'960px', margin:'0 auto', padding:'0 12px' }}>
        {page==='picks' ? <DailyPicksView />
          : page==='yesterday' ? <YesterdayResultsView />
          : page==='laythe' ? <LayTheFavView />
          : <MajorRacesView />}
      </main>
    </div>
  );
}

// ---- Analysis Pipeline Checklist ----
function AnalysisPipeline({ stages, signalCoverage, runTime, isMobile }) {
  if (!stages || stages.length === 0) return null;
  const allOk     = stages.every(s => s.ok);
  const failCount = stages.filter(s => !s.ok).length;
  const headerColor = allOk ? '#34d399' : '#fbbf24';
  const headerBg    = allOk ? 'rgba(5,150,105,0.12)' : 'rgba(245,158,11,0.12)';
  const borderColor = allOk ? 'rgba(52,211,153,0.35)' : 'rgba(251,191,36,0.4)';
  const runTimeStr  = runTime
    ? new Date(runTime).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    : null;
  return (
    <div style={{ background: headerBg, border: `1px solid ${borderColor}`, borderRadius: '10px', padding: '12px 16px', marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: headerColor, fontWeight: '800' }}>
          {allOk ? '✓ Analysis complete — all signals active' : `⚠ ${failCount} analysis stage${failCount > 1 ? 's' : ''} incomplete`}
        </span>
        {runTimeStr && <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)' }}>Last run {runTimeStr}</span>}
      </div>
      {/* Stage pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: signalCoverage && Object.keys(signalCoverage).length > 0 ? '10px' : '0' }}>
        {stages.map(s => (
          <span key={s.id} title={s.detail} style={{
            background: s.ok ? 'rgba(5,150,105,0.2)' : 'rgba(234,179,8,0.15)',
            border: `1px solid ${s.ok ? 'rgba(52,211,153,0.4)' : 'rgba(251,191,36,0.5)'}`,
            borderRadius: '6px', padding: '3px 10px', fontSize: '11px', fontWeight: '700',
            color: s.ok ? '#34d399' : '#fbbf24', cursor: 'help', whiteSpace: 'nowrap',
          }}>
            {s.ok ? '✓' : '⚠'} {s.label}
          </span>
        ))}
      </div>
      {/* Signal coverage bars */}
      {signalCoverage && Object.keys(signalCoverage).length > 0 && (
        <div>
          <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: '6px' }}>
            Signal coverage (% of horses today where each factor fired)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4,1fr)', gap: '5px' }}>
            {Object.entries(signalCoverage).map(([label, pct]) => (
              <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'rgba(255,255,255,0.55)' }}>
                  <span>{label}</span><span style={{ color: pct > 30 ? '#34d399' : pct > 0 ? '#fbbf24' : '#ef4444', fontWeight: '700' }}>{pct}%</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.1)', borderRadius: '2px', height: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: pct > 30 ? '#059669' : pct > 0 ? '#d97706' : '#ef4444', borderRadius: '2px' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
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
  aw_low_class_penalty:  'AW Low Class Penalty',
  unexposed_bonus:         'Unexposed/Improving',
  claiming_jockey:         'Claiming Jockey Allowance',
  heavy_going_penalty:     'Heavy Going Penalty',
  official_rating_bonus:   'Official Rating',
  deep_form:               'Deep Form Analysis',
  short_form_improvement:  'Recent Improvement',
  meeting_focus:           'Meeting Focus',
  jockey_course_bonus:     'Jockey Course Record',
  cheltenham_festival:     'Cheltenham Festival',
};

function DailyPicksView() {
  const [picks, setPicks]                 = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [lastUpdated, setLastUpdated]     = useState(null);
  const [expandedPick,  setExpandedPick]  = useState(null);
  const [expandedField, setExpandedField] = useState(null);
  const [raceFields,    setRaceFields]    = useState({});
  const [isMobile,      setIsMobile]      = useState(typeof window !== 'undefined' && window.innerWidth < 480);
  const [now,           setNow]           = useState(new Date());
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [analysisPending, setAnalysisPending] = useState(false);
  const [pendingReason,   setPendingReason]   = useState('');
  const [cumulRoi,        setCumulRoi]         = useState(null);

  // Tick every 60 s so "Analysed X ago" stays current without a page reload
  useEffect(() => {
    const ticker = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(ticker);
  }, []);

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
      // US-format times are stored as UTC — append Z so JS treats as UTC, then display in Dublin
      const d = new Date(`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}:00Z`);
      const tz = { timeZone: 'Europe/Dublin' };
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', year:'numeric', ...tz }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit', hour12: false, ...tz }),
      };
    }
    // ISO format — bare strings have no tz, treat as UTC; display in Dublin (BST = UTC+1)
    const isoM = rt.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
    if (isoM) {
      const [, datePart] = isoM;
      try {
        const d = new Date(rt.endsWith('Z') || rt.includes('+') ? rt : rt + 'Z');
        const tz = { timeZone: 'Europe/Dublin' };
        return {
          date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', year:'numeric', ...tz }),
          time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit', hour12: false, ...tz }),
        };
      } catch { return { date: datePart, time: rt.substring(11, 16) }; }
    }
    return { date: rt.substring(0,10), time: rt.substring(11,16) };
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
      const [res, roiRes] = await Promise.all([
        fetch(API_BASE_URL + '/api/picks/today'),
        fetch(API_BASE_URL + '/api/results/cumulative-roi'),
      ]);
      const data = await res.json();
      const roiData = await roiRes.json().catch(() => null);
      if (roiData?.success) setCumulRoi(roiData);
      if (data.success) {
        const sorted = (data.picks || [])
          .filter(p => p.show_in_ui !== false)
          .sort((a,b) => (a.race_time||'').localeCompare(b.race_time||''))
          .slice(0, 5);
        setPicks(sorted);
        setRaceFields(data.race_fields || {});
        setLastUpdated(new Date().toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }));
        if (data.analysis_status) setAnalysisStatus(data.analysis_status);
        // Health-check gate: API returns empty picks with analysis_pending=true when not ready
        setAnalysisPending(!!data.analysis_pending);
        setPendingReason(data.pending_reason || '');
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
    if (s >= 90) return { bg: '#059669', label: 'STRONG' };
    if (s >= 80) return { bg: '#3b82f6', label: 'GOOD'   };
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

      {(() => {
        const rv  = cumulRoi?.success ? (cumulRoi.roi ?? 0) : null;
        const rs  = cumulRoi?.success ? (cumulRoi.settled || 0) : null;
        const pos = rv === null || rv >= 0;
        return (
          <div style={{ background: rv === null ? 'rgba(99,102,241,0.12)' : rv >= 0 ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.13)', border: `1.5px solid ${rv === null ? 'rgba(99,102,241,0.35)' : rv >= 0 ? 'rgba(16,185,129,0.45)' : 'rgba(239,68,68,0.4)'}`, borderRadius: '14px', padding: isMobile ? '14px 16px' : '18px 24px', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '14px' : '20px' }}>
              <div style={{ fontSize: isMobile ? '28px' : '38px' }}>💰</div>
              <div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)', textTransform: 'uppercase', letterSpacing: '1.2px', fontWeight: '700', marginBottom: '4px' }}>Return on Investment</div>
                <div style={{ fontSize: isMobile ? '30px' : '40px', fontWeight: '900', color: rv === null ? '#818cf8' : rv >= 0 ? '#34d399' : '#f87171', lineHeight: 1 }}>
                  {rv === null ? 'Loading…' : `${rv >= 0 ? '+' : ''}${rv.toFixed(1)}%`}
                </div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginTop: '4px' }}>
                  {rv === null ? 'Fetching performance data…' : `Since 22 Mar · ${rs} settled`}
                </div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', fontStyle: 'italic', maxWidth: '160px', lineHeight: '1.5' }}>Profit per £1 staked.<br/>10%+ is good.</div>
            </div>
          </div>
        );
      })()}

      {analysisStatus && analysisStatus.available && (
        <AnalysisPipeline
          stages={analysisStatus.stages}
          signalCoverage={analysisStatus.signal_coverage}
          runTime={analysisStatus.run_time}
          isMobile={isMobile}
        />
      )}

      {picks.length === 0 ? (
        analysisPending ? (
          /* ── Analysis still running ─────────────────────────────────────── */
          <div style={{ background:'rgba(251,191,36,0.12)', border:'1px solid rgba(251,191,36,0.45)', borderRadius:'12px', padding:'32px 24px', textAlign:'center', color:'rgba(255,255,255,0.9)' }}>
            <div style={{ fontSize:'28px', marginBottom:'8px' }}>⏳</div>
            <div style={{ fontSize:'17px', fontWeight:'800', color:'#fbbf24', marginBottom:'8px' }}>Analysis in Progress</div>
            <div style={{ fontSize:'13px', opacity:0.85, marginBottom:'12px' }}>
              Picks are hidden until the full analysis is confirmed complete across all races and runners.
            </div>
            {pendingReason && (
              <div style={{ fontSize:'12px', background:'rgba(0,0,0,0.25)', borderRadius:'8px', padding:'8px 14px', display:'inline-block', color:'#fde68a' }}>
                {pendingReason}
              </div>
            )}
            <div style={{ fontSize:'11px', opacity:0.6, marginTop:'12px' }}>
              Analysis runs at 08:00, 14:00, 16:00 and 18:00 · Refresh to check status
            </div>
          </div>
        ) : (
        <div style={{ background:'rgba(255,255,255,0.08)', borderRadius:'12px', padding:'48px 24px', textAlign:'center', color:'rgba(255,255,255,0.7)' }}>
          <div style={{ fontSize:'18px', fontWeight:'700', color:'white', marginBottom:'8px' }}>No picks yet today</div>
          <div style={{ fontSize:'14px' }}>The model scores every horse in today's races and selects the 3 highest-confidence winners — one per race.<br/>Odds are fetched at 12:00, 14:00, 16:00 and 18:00 daily.<br/>Check the <strong>Top Naps</strong> tab for best picks across the next 5 days.</div>
        </div>
        )
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>
          {(() => {
            const sorted = [...picks].sort((a, b) => {
              const norm = s => { const m = (s||'').match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/); return m ? `${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}` : (s||''); };
              return norm(a.race_time).localeCompare(norm(b.race_time));
            });
            const morningPicks  = sorted.filter(p => p.pick_type !== 'intraday').slice(0, 3);
            const intradayPicks = sorted.filter(p => p.pick_type === 'intraday').slice(0, 2);
            const allPicks = [...morningPicks, ...intradayPicks];
            return allPicks.map((pick, idx) => {
            const tier = tierInfo(pick.score);
            const rank = parseInt(pick.pick_rank || (idx+1));
            const isIntraday = pick.pick_type === 'intraday';
            const rankLabels = {1:'#1 Best Bet', 2:'#2 Best Bet', 3:'#3 Best Bet'};
            const rankColors = {1:'#d97706', 2:'#6b7280', 3:'#92400e'};
            const intradayColor = '#7c3aed';
            return (
              <div key={idx} style={{ background:'white', borderRadius:'12px', padding:'20px 22px', borderLeft:`5px solid ${isIntraday ? intradayColor : (rankColors[rank]||tier.bg)}`, boxShadow:'0 2px 12px rgba(0,0,0,0.1)' }}>
                {isIntraday && (
                  <div style={{ marginBottom:'10px', display:'flex', alignItems:'center', gap:'8px' }}>
                    <span style={{ background:intradayColor, color:'white', borderRadius:'6px', padding:'4px 12px', fontSize:'11px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.5px' }}>
                      ⚡ Intraday Pick
                    </span>
                    <span style={{ fontSize:'11px', color:'#6b7280' }}>Added during the day</span>
                  </div>
                )}
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'8px' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                    <div style={{ background: isIntraday ? intradayColor : (rankColors[rank]||tier.bg), color:'white', borderRadius:'8px', padding:'6px 10px', textAlign:'center', minWidth:'44px', flexShrink:0 }}>
                      <div style={{ fontSize:'18px', fontWeight:'900' }}>{isIntraday ? '⚡' : `#${rank}`}</div>
                      <div style={{ fontSize:'9px', fontWeight:'700', opacity:0.85, textTransform:'uppercase', lineHeight:'1' }}>{isIntraday ? 'Live' : 'Pick'}</div>
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
                {/* Optimal bet timing badge */}
                {(() => {
                  const bw = bettingWindow(pick, now);
                  return (
                    <div style={{ marginTop:'10px', display:'inline-flex', alignItems:'center', gap:'6px', background:bw.bg, border:`1px solid ${bw.border}`, borderRadius:'7px', padding:'5px 12px' }}>
                      <span style={{ fontSize:'13px', fontWeight:'800', color:bw.color }}>{bw.label}</span>
                      <span style={{ fontSize:'11px', color:'#6b7280' }}>— {bw.desc}</span>
                    </div>
                  );
                })()}
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
                {(() => {
                  const hasReasons = Array.isArray(pick.selection_reasons) && pick.selection_reasons.length > 0;
                  const topReasons = hasReasons
                    ? bestKeyReasons(pick.selection_reasons, 2)
                    : reasonsFromBreakdown(pick.score_breakdown, 2);
                  const score = parseFloat(pick.score || pick.comprehensive_score || 0);
                  if (!topReasons.length && !score) return null;
                  const hasBd = pick.score_breakdown && typeof pick.score_breakdown === 'object' && Object.keys(pick.score_breakdown).length > 0;
                  return (
                    <div onClick={() => hasBd && setExpandedPick(expandedPick === idx ? null : idx)} style={{ marginTop:'10px', padding:'10px 14px', background: `${tier.bg}18`, borderRadius:'8px', borderLeft:`3px solid ${tier.bg}`, cursor: hasBd ? 'pointer' : 'default' }}>
                      <div style={{ display:'flex', alignItems:'center', gap:'8px', flexWrap:'wrap', marginBottom: topReasons.length ? '6px' : '0' }}>
                        <span style={{ background:tier.bg, color:'white', borderRadius:'5px', padding:'2px 9px', fontSize:'11px', fontWeight:'800', letterSpacing:'0.5px' }}>{tier.label}</span>
                        <span style={{ fontSize:'12px', fontWeight:'700', color:'#1e3a5f' }}>Score: {score.toFixed(0)}/100</span>
                        {hasBd && <span style={{ fontSize:'11px', color:'#1d4ed8', fontWeight:'700', marginLeft:'auto' }}>{expandedPick === idx ? '▲ Hide breakdown' : '▼ See breakdown'}</span>}
                      </div>
                      {topReasons.length > 0 && (
                        <div style={{ fontSize:'13px', color:'#374151', lineHeight:'1.55' }}>
                          {topReasons.map((r, i) => (
                            <div key={i} style={{ display:'flex', alignItems:'flex-start', gap:'6px' }}>
                              <span style={{ color:tier.bg, fontWeight:'800', marginTop:'1px' }}>›</span>
                              <span>{r}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
                {/* Race Intel Summary */}
                {(() => {
                  const { analysedStr, freshness, freshnessOk, keyEdge, rival, rivalGap, riskStr } = raceIntelSummary(pick, now);
                  if (!analysedStr && !keyEdge) return null;
                  return (
                    <div style={{ marginTop:'10px', padding:'10px 14px', background:'#f8fafc', borderRadius:'8px', border:'1px solid #e2e8f0', fontSize:'12px' }}>
                      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:'6px', marginBottom:'8px' }}>
                        <span style={{ fontWeight:'800', color:'#1e3a5f', fontSize:'11px', textTransform:'uppercase', letterSpacing:'0.7px' }}>📡 Race Intel</span>
                        <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'center' }}>
                          {analysedStr && (
                            <span style={{ background:'#eff6ff', border:'1px solid #bfdbfe', borderRadius:'5px', padding:'2px 8px', color:'#1d4ed8', fontWeight:'700', fontSize:'11px' }}>
                              🕐 Analysed {analysedStr}
                            </span>
                          )}
                          {freshness && (
                            <span style={{ background: freshnessOk ? '#f0fdf4' : '#fef3c7', border:`1px solid ${freshnessOk ? '#86efac' : '#fcd34d'}`, borderRadius:'5px', padding:'2px 8px', color: freshnessOk ? '#166534' : '#92400e', fontWeight:'700', fontSize:'11px' }}>
                              {freshness}
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display:'flex', flexDirection:'column', gap:'5px' }}>
                        {keyEdge && (
                          <div style={{ display:'flex', gap:'6px', alignItems:'flex-start' }}>
                            <span style={{ color:'#059669', fontWeight:'800', fontSize:'13px', lineHeight:'1.2' }}>✓</span>
                            <span style={{ color:'#065f46', fontWeight:'600' }}><strong>Key edge:</strong> {keyEdge}</span>
                          </div>
                        )}
                        {rival && rivalGap !== null && (
                          <div style={{ display:'flex', gap:'6px', alignItems:'flex-start' }}>
                            <span style={{ color:'#6b7280', fontWeight:'800', fontSize:'13px', lineHeight:'1.2' }}>→</span>
                            <span style={{ color:'#374151' }}><strong>Main rival:</strong> {rival.horse} ({parseFloat(rival.odds||0)>1 ? toFractional(parseFloat(rival.odds)) : '?'}) — {rivalGap}pt{rivalGap==='1'?'':'s'} behind</span>
                          </div>
                        )}
                        {riskStr && (
                          <div style={{ display:'flex', gap:'6px', alignItems:'flex-start' }}>
                            <span style={{ color:'#d97706', fontWeight:'800', fontSize:'13px', lineHeight:'1.2' }}>⚠</span>
                            <span style={{ color:'#92400e', fontWeight:'600' }}><strong>Risk:</strong> {riskStr}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
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
                              <div style={{ width: isMobile ? '90px' : '140px', fontSize:'11px', color:'#374151', fontWeight:'600', flexShrink:0, textAlign:'right' }}>{label}</div>
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
            });
          })()}
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
  const [cumulRoi, setCumulRoi]         = useState(null);
  const [layData,  setLayData]          = useState(null);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 480);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => { loadResults(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadResults = async () => {
    setLoading(true); setError(null);
    try {
      const [todayRes, yestRes, cumulRes] = await Promise.all([
        fetch(API_BASE_URL + '/api/results/today'),
        fetch(API_BASE_URL + '/api/results/yesterday'),
        fetch(API_BASE_URL + '/api/results/cumulative-roi'),
      ]);
      const [todayData, yestData, cumulData] = await Promise.all([todayRes.json(), yestRes.json(), cumulRes.json()]);
      if (cumulData.success) setCumulRoi(cumulData);

      const todayPicks = (todayData.success ? todayData.picks || [] : []).map(p => ({ ...p, _dayLabel: 'Today' }));
      const yestPicks  = (yestData.success  ? yestData.picks  || [] : []).map(p => ({ ...p, _dayLabel: 'Yesterday' }));
      // Deduplicate: same course + race_time[:16] => keep highest-scored version
      // Use course+time (not horse name) to handle name variants like apostrophes
      const deduped = {};
      [...todayPicks, ...yestPicks].forEach(p => {
        const rt = (p.race_time || '').substring(0, 16);
        const key = (p.course || p.race_course || '') + '|' + rt;
        const sc  = parseFloat(p.comprehensive_score || p.analysis_score || 0);
        if (!deduped[key] || sc > parseFloat(deduped[key].comprehensive_score || deduped[key].analysis_score || 0)) {
          deduped[key] = p;
        }
      });
      const allPicks = Object.values(deduped);

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

      // Recompute summary from deduplicated picks (more accurate than API summaries)
      const settled = allPicks.filter(p => {
        const oc = (p.result_emoji || p.outcome || '').toUpperCase();
        return oc === 'WIN' || oc === 'LOSS' || oc === 'PLACED' || oc === 'WON' || oc === 'LOST';
      });
      const recomputed = {
        total_picks: allPicks.length,
        wins:    settled.filter(p => ['WIN','WON'].includes((p.result_emoji||p.outcome||'').toUpperCase())).length,
        places:  settled.filter(p => (p.result_emoji||p.outcome||'').toUpperCase() === 'PLACED').length,
        losses:  settled.filter(p => ['LOSS','LOST'].includes((p.result_emoji||p.outcome||'').toUpperCase())).length,
        pending: allPicks.length - settled.length,
        profit:  combinedSummary.profit,
        total_stake: combinedSummary.total_stake,
        roi: combinedSummary.roi,
      };
      if (allPicks.length === 0 && !todayData.success && !yestData.success) {
        setError('Failed to load results');
      } else {
        setResults({ picks: allPicks, summary: recomputed });
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
    // Lay analysis — non-critical, silent fail
    try {
      const layRes  = await fetch(API_BASE_URL + '/api/favs-run');
      const layJson = await layRes.json();
      if (layJson.success) setLayData(layJson);
    } catch (_) {}
  };

  const formatRaceTime = rt => {
    if (!rt) return { date: '', time: '' };
    const m = rt.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/);
    if (m) {
      const d = new Date(`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}:00Z`);
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', timeZone:'Europe/Dublin' }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'Europe/Dublin' }),
      };
    }
    try {
      const d = new Date(rt.endsWith('Z') || rt.includes('+') ? rt : rt + 'Z');
      const tz = { timeZone: 'Europe/Dublin' };
      return {
        date: d.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', ...tz }),
        time: d.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit', hour12: false, ...tz }),
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
    if (n >= 90) return { bg:'#059669', label:'STRONG' };
    if (n >= 80) return { bg:'#3b82f6', label:'GOOD'   };
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
        const pnlPos       = profit >= 0;
        const cumulRoiVal  = cumulRoi?.success ? (cumulRoi.roi ?? 0) : null;
        const cumulSettled = cumulRoi?.success ? (cumulRoi.settled || 0) : null;
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
              <div style={{ background: cumulRoiVal === null ? 'rgba(99,102,241,0.1)' : cumulRoiVal >= 0 ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.13)', border:`1.5px solid ${cumulRoiVal === null ? 'rgba(99,102,241,0.3)' : cumulRoiVal >= 0 ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.35)'}`, borderRadius:'12px', padding: isMobile ? '10px 12px' : '14px 16px', display:'flex', alignItems:'center', justifyContent:'space-between', gap:'8px' }}>
                <div>
                  <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.55)', textTransform:'uppercase', letterSpacing:'1px', fontWeight:'600', marginBottom:'3px' }}>{isMobile ? 'ROI' : 'Return on Investment'}</div>
                  <div style={{ fontSize: isMobile ? '22px' : '30px', fontWeight:'900', color: cumulRoiVal === null ? '#818cf8' : cumulRoiVal >= 0 ? '#34d399' : '#f87171', lineHeight:1 }}>
                    {cumulRoiVal === null ? '—' : `${cumulRoiVal >= 0 ? '+' : ''}${cumulRoiVal.toFixed(1)}%`}
                  </div>
                  <div style={{ fontSize:'9px', color:'rgba(255,255,255,0.4)', marginTop:'4px', fontWeight:'500' }}>
                    {cumulRoiVal === null ? 'Loading…' : `Since 22 Mar · ${cumulSettled} settled`}
                  </div>
                  <div style={{ fontSize:'9px', color:'rgba(255,255,255,0.3)', marginTop:'2px', fontStyle:'italic' }}>Profit per £1 staked. 10%+ is good.</div>
                </div>
                <div style={{ fontSize: isMobile ? '22px' : '32px' }}>💰</div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── PERFORMANCE DASHBOARD ────────────────────────────────────── */}
      {false && cumulRoi?.success && (() => {
        const cr         = cumulRoi;
        const roi        = cr.roi ?? 0;
        const roiPos     = roi >= 0;
        const byDay      = cr.by_day || [];
        const maxAbsProfit = byDay.length > 0 ? Math.max(...byDay.map(d => Math.abs(d.profit)), 0.1) : 1;
        const avgWinSc   = cr.avg_win_score;
        const avgLossSc  = cr.avg_loss_score;
        const scoregap   = (avgWinSc && avgLossSc) ? (avgWinSc - avgLossSc).toFixed(1) : null;
        const winSR      = cr.settled > 0 ? Math.round(cr.wins / cr.settled * 100) : 0;
        const wpSR       = cr.settled > 0 ? Math.round((cr.wins + cr.places) / cr.settled * 100) : 0;
        let runningStake = 0; let runningRet = 0;
        const byDayWithRoi = byDay.map(d => {
          runningStake += d.settled;
          runningRet   += (d.settled + d.profit);
          const rRoi = runningStake > 0 ? ((runningRet - runningStake) / runningStake * 100) : 0;
          return { ...d, runningRoi: Math.round(rRoi * 10) / 10 };
        });
        return (
          <div style={{ marginBottom:'20px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'12px', padding:'16px 18px' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'14px', flexWrap:'wrap', gap:'8px' }}>
              <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1px', color:'rgba(255,255,255,0.4)', fontWeight:'700' }}>📊 Performance Dashboard</div>
              <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.3)' }}>Since {cr.start_date} · {cr.settled} settled</div>
            </div>

            {/* 4 stat tiles */}
            <div style={{ display:'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4,1fr)', gap:'8px', marginBottom:'14px' }}>
              <div style={{ background: roiPos ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.1)', border:`1.5px solid ${roiPos ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.3)'}`, borderRadius:'10px', padding:'12px 14px' }}>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', textTransform:'uppercase', letterSpacing:'0.8px', fontWeight:'600', marginBottom:'4px' }}>ROI</div>
                <div style={{ fontSize:'26px', fontWeight:'900', color: roiPos ? '#34d399' : '#f87171', lineHeight:1 }}>{roiPos ? '+' : ''}{roi.toFixed(1)}%</div>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.35)', marginTop:'5px', lineHeight:1.5 }}>£{cr.total_return?.toFixed(2)} returned<br/>on £{cr.total_stake?.toFixed(0)} staked</div>
              </div>
              <div style={{ background: cr.profit >= 0 ? 'rgba(16,185,129,0.10)' : 'rgba(239,68,68,0.08)', border:`1.5px solid ${cr.profit >= 0 ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.25)'}`, borderRadius:'10px', padding:'12px 14px' }}>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', textTransform:'uppercase', letterSpacing:'0.8px', fontWeight:'600', marginBottom:'4px' }}>Profit</div>
                <div style={{ fontSize:'26px', fontWeight:'900', color: cr.profit >= 0 ? '#34d399' : '#f87171', lineHeight:1 }}>{cr.profit >= 0 ? '+' : ''}{cr.profit?.toFixed(2)}u</div>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.35)', marginTop:'5px', lineHeight:1.5 }}>{cr.wins}W · {cr.places}P · {cr.losses}L<br/>{cr.pending > 0 ? `${cr.pending} pending` : 'all settled'}</div>
              </div>
              <div style={{ background:'rgba(96,165,250,0.08)', border:'1.5px solid rgba(96,165,250,0.25)', borderRadius:'10px', padding:'12px 14px' }}>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', textTransform:'uppercase', letterSpacing:'0.8px', fontWeight:'600', marginBottom:'4px' }}>Win Rate</div>
                <div style={{ fontSize:'26px', fontWeight:'900', color: winSR >= 25 ? '#34d399' : '#fbbf24', lineHeight:1 }}>{winSR}%</div>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.35)', marginTop:'5px', lineHeight:1.5 }}>Win+Place: {wpSR}%<br/>{cr.wins} wins from {cr.settled}</div>
              </div>
              <div style={{ background:'rgba(139,92,246,0.08)', border:'1.5px solid rgba(139,92,246,0.25)', borderRadius:'10px', padding:'12px 14px' }}>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.45)', textTransform:'uppercase', letterSpacing:'0.8px', fontWeight:'600', marginBottom:'4px' }}>Model Signal</div>
                <div style={{ fontSize:'26px', fontWeight:'900', color: scoregap >= 15 ? '#34d399' : scoregap >= 8 ? '#fbbf24' : '#f87171', lineHeight:1 }}>{scoregap ? `+${scoregap}` : '—'}</div>
                <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.35)', marginTop:'5px', lineHeight:1.5 }}>Winner avg: {avgWinSc ?? '—'}<br/>Loser avg: {avgLossSc ?? '—'}</div>
              </div>
            </div>

            {/* ROI formula explainer */}
            <div style={{ background:'rgba(59,130,246,0.07)', border:'1px solid rgba(59,130,246,0.18)', borderRadius:'8px', padding:'9px 13px', marginBottom:'14px', fontSize:'11px', color:'rgba(255,255,255,0.45)', lineHeight:1.6 }}>
              <span style={{ color:'rgba(255,255,255,0.7)', fontWeight:'700' }}>How ROI is calculated: </span>
              Level-stakes method — 1 unit wagered per pick (industry-standard tipster measure).
              Wins return stake × decimal odds. Place returns ½ stake at ¼ odds. Loss forfeits stake.
              <span style={{ color:'rgba(255,255,255,0.55)', display:'block', marginTop:'2px' }}>
                ROI = (total returned − total staked) ÷ total staked × 100
              </span>
            </div>

            {/* Day-by-day bar chart */}
            {byDay.length > 0 && (
              <div>
                <div style={{ fontSize:'10px', textTransform:'uppercase', letterSpacing:'0.8px', color:'rgba(255,255,255,0.3)', fontWeight:'700', marginBottom:'8px' }}>Daily breakdown</div>
                <div style={{ display:'flex', flexDirection:'column', gap:'5px' }}>
                  {[...byDayWithRoi].reverse().map((d, i) => {
                    const pos  = d.profit >= 0;
                    const barW = Math.round(Math.abs(d.profit) / maxAbsProfit * 100);
                    const dt   = new Date(d.date + 'T12:00:00');
                    const dow  = dt.toLocaleDateString('en-GB', { weekday:'short' });
                    const dom  = dt.toLocaleDateString('en-GB', { day:'numeric', month:'short' });
                    const isSat = dt.getDay() === 6;
                    const isSun = dt.getDay() === 0;
                    return (
                      <div key={i} style={{ display:'grid', gridTemplateColumns: isMobile ? '62px 1fr 46px' : '88px 1fr 56px', gap:'8px', alignItems:'center' }}>
                        <div style={{ fontSize:'11px', color: isSat ? '#f97316' : isSun ? '#38bdf8' : 'rgba(255,255,255,0.55)', fontWeight: (isSat||isSun) ? '700' : '400', lineHeight:1.3 }}>
                          <span style={{ fontWeight:'700' }}>{dow}</span> {dom}
                          <div style={{ fontSize:'9px', color:'rgba(255,255,255,0.3)', marginTop:'1px' }}>{d.wins}W {d.places}P {d.losses}L</div>
                        </div>
                        <div style={{ position:'relative', height:'20px', background:'rgba(255,255,255,0.05)', borderRadius:'4px', overflow:'hidden' }}>
                          <div style={{ position:'absolute', top:0, bottom:0, left:0, width:`${barW}%`, background: pos ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.45)', borderRadius:'4px' }}/>
                          <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', paddingLeft:'7px', fontSize:'10px', color:'rgba(255,255,255,0.7)', fontWeight:'600' }}>
                            {pos ? '+' : ''}{d.profit.toFixed(2)}u
                          </div>
                        </div>
                        <div style={{ fontSize:'10px', color: d.runningRoi >= 0 ? '#34d399' : '#f87171', fontWeight:'700', textAlign:'right' }}>
                          {d.runningRoi >= 0 ? '+' : ''}{d.runningRoi}%
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
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

      {/* Saturday / Sunday pattern panel — removed 2026-03-30 */}
      {false && picks.length > 0 && (() => {
        // Group settled picks by day-of-week, tracking scores + market-leader alignment
        const DOW_STATS = {};
        picks.forEach(p => {
          const rt = p.race_time;
          if (!rt) return;
          let d;
          try {
            const m = rt.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/);
            d = m ? new Date(`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}`) : new Date(rt);
          } catch { return; }
          const dow = d.toLocaleDateString('en-GB', { weekday:'long' });
          if (!DOW_STATS[dow]) DOW_STATS[dow] = {
            wins:0, places:0, losses:0, pending:0, picks:0,
            winScores:[], lossScores:[], mlCount:0, oddsAbove5:0
          };
          DOW_STATS[dow].picks++;
          const oc  = (p.result_emoji || p.outcome || '').toUpperCase();
          const sc  = parseFloat(p.comprehensive_score || p.analysis_score || 0);
          const sb  = p.score_breakdown || {};
          const ml  = parseFloat(sb.market_leader || 0) > 0;
          const odd = parseFloat(p.odds || 0);
          if (ml) DOW_STATS[dow].mlCount++;
          if (odd >= 5) DOW_STATS[dow].oddsAbove5++;
          if (oc === 'WIN' || oc === 'WON')        { DOW_STATS[dow].wins++;   if(sc) DOW_STATS[dow].winScores.push(sc); }
          else if (oc === 'PLACED')                { DOW_STATS[dow].places++; if(sc) DOW_STATS[dow].lossScores.push(sc); }
          else if (oc === 'LOSS' || oc === 'LOST') { DOW_STATS[dow].losses++; if(sc) DOW_STATS[dow].lossScores.push(sc); }
          else                                       DOW_STATS[dow].pending++;
        });
        const hasSat = DOW_STATS['Saturday'];
        const hasSun = DOW_STATS['Sunday'];
        if (!hasSat && !hasSun) return null;

        const avg = arr => arr.length ? Math.round(arr.reduce((a,b)=>a+b,0)/arr.length*10)/10 : null;

        const dayCard = (dow, st, emoji, col) => {
          const settled = st.wins + st.losses + st.places;
          const sr        = settled > 0 ? Math.round(st.wins / settled * 100) : null;
          const avgWin    = avg(st.winScores);
          const avgLoss   = avg(st.lossScores);
          const gap       = (avgWin && avgLoss) ? Math.round((avgWin - avgLoss)*10)/10 : null;
          const mlPct     = st.picks > 0 ? Math.round(st.mlCount / st.picks * 100) : null;
          const longPct   = settled > 0 ? Math.round(st.oddsAbove5 / settled * 100) : null;
          return (
            <div key={dow} style={{ flex:1, minWidth: isMobile ? '100%' : 0, background:'rgba(255,255,255,0.04)', border:`1px solid ${col}33`, borderRadius:'10px', padding:'14px 16px', borderLeft:`4px solid ${col}` }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'10px' }}>
                <div style={{ fontSize:'13px', fontWeight:'800', color:col }}>{emoji} {dow}</div>
                {sr !== null && (
                  <span style={{ background: sr >= 30 ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.15)', color: sr >= 30 ? '#34d399' : '#f87171', borderRadius:'5px', padding:'2px 8px', fontWeight:'800', fontSize:'13px' }}>
                    {sr}% win rate
                  </span>
                )}
              </div>
              {/* W / P / L row */}
              <div style={{ display:'flex', gap:'8px', fontSize:'13px', marginBottom:'10px' }}>
                <span style={{ color:'#34d399', fontWeight:'700' }}>{st.wins}W</span>
                <span style={{ color:'#818cf8', fontWeight:'700' }}>{st.places}P</span>
                <span style={{ color:'#f87171', fontWeight:'700' }}>{st.losses}L</span>
                {st.pending > 0 && <span style={{ color:'rgba(255,255,255,0.35)', fontSize:'12px' }}>{st.pending} pending</span>}
              </div>
              {/* Stats grid */}
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'6px 12px', fontSize:'11px' }}>
                {avgWin!=null && (
                  <div style={{ color:'rgba(255,255,255,0.5)' }}>
                    Avg winner score
                    <div style={{ color:'#34d399', fontWeight:'800', fontSize:'13px' }}>{avgWin}</div>
                  </div>
                )}
                {avgLoss!=null && (
                  <div style={{ color:'rgba(255,255,255,0.5)' }}>
                    Avg loser score
                    <div style={{ color:'#f87171', fontWeight:'800', fontSize:'13px' }}>{avgLoss}</div>
                  </div>
                )}
                {gap!=null && (
                  <div style={{ color:'rgba(255,255,255,0.5)' }}>
                    Model discrimination
                    <div style={{ color: gap >= 15 ? '#34d399' : gap >= 8 ? '#fbbf24' : '#f87171', fontWeight:'800', fontSize:'13px' }}>
                      {gap > 0 ? '+' : ''}{gap} pts gap
                    </div>
                  </div>
                )}
                {mlPct!=null && (
                  <div style={{ color:'rgba(255,255,255,0.5)' }}>
                    Market leader picks
                    <div style={{ color: mlPct >= 35 ? '#34d399' : '#fbbf24', fontWeight:'800', fontSize:'13px' }}>{mlPct}%</div>
                  </div>
                )}
              </div>
            </div>
          );
        };

        const satSt = hasSat || { wins:0, places:0, losses:0, pending:0, picks:0, winScores:[], lossScores:[], mlCount:0, oddsAbove5:0 };
        const sunSt = hasSun || { wins:0, places:0, losses:0, pending:0, picks:0, winScores:[], lossScores:[], mlCount:0, oddsAbove5:0 };
        const satSettled = satSt.wins + satSt.losses + satSt.places;
        const sunSettled = sunSt.wins + sunSt.losses + sunSt.places;
        const showExplainer = hasSat && hasSun && satSettled > 0 && sunSettled > 0 &&
          (sunSt.wins / Math.max(sunSettled,1)) > (satSt.wins / Math.max(satSettled,1));

        const satGap   = (avg(satSt.winScores) && avg(satSt.lossScores)) ? (avg(satSt.winScores) - avg(satSt.lossScores)).toFixed(1) : null;
        const sunGap   = (avg(sunSt.winScores) && avg(sunSt.lossScores)) ? (avg(sunSt.winScores) - avg(sunSt.lossScores)).toFixed(1) : null;
        const satML    = satSt.picks > 0 ? Math.round(satSt.mlCount / satSt.picks * 100) : null;
        const sunML    = sunSt.picks > 0 ? Math.round(sunSt.mlCount / sunSt.picks * 100) : null;

        return (
          <div style={{ marginBottom:'20px', background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.09)', borderRadius:'10px', padding:'14px 18px' }}>
            <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1px', color:'rgba(255,255,255,0.4)', marginBottom:'12px', fontWeight:'700' }}>
              📅 Weekend Day Breakdown
            </div>
            <div style={{ display:'flex', gap:'10px', flexWrap:'wrap', marginBottom: showExplainer ? '14px' : 0 }}>
              {hasSat && dayCard('Saturday', satSt, '🏆', '#f97316')}
              {hasSun && dayCard('Sunday',   sunSt, '☀️', '#38bdf8')}
            </div>

            {showExplainer && (
              <div style={{ display:'flex', flexDirection:'column', gap:'8px' }}>

                {/* Headline insight: score discrimination */}
                {satGap && sunGap && (
                  <div style={{ background:'rgba(59,130,246,0.1)', border:'1px solid rgba(59,130,246,0.3)', borderRadius:'8px', padding:'10px 14px' }}>
                    <div style={{ fontSize:'11px', fontWeight:'800', color:'#60a5fa', marginBottom:'8px' }}>🔬 Why the Model Performs Better on Sundays — Data Evidence</div>
                    <div style={{ display:'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap:'8px', marginBottom:'8px' }}>
                      <div style={{ background:'rgba(249,115,22,0.1)', borderRadius:'6px', padding:'8px 10px', borderLeft:'3px solid #f97316' }}>
                        <div style={{ fontSize:'11px', color:'#fb923c', fontWeight:'700', marginBottom:'4px' }}>Saturday — narrow gap</div>
                        <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.6)', lineHeight:1.5 }}>
                          Avg winner score: <b style={{color:'#34d399'}}>{avg(satSt.winScores)}</b><br/>
                          Avg loser score:  <b style={{color:'#f87171'}}>{avg(satSt.lossScores)}</b><br/>
                          <span style={{ color:'#fbbf24', fontWeight:'800' }}>Separation: only {satGap} pts</span><br/>
                          <span style={{ color:'rgba(255,255,255,0.45)', fontSize:'11px' }}>Model can barely tell winners from losers</span>
                        </div>
                      </div>
                      <div style={{ background:'rgba(56,189,248,0.1)', borderRadius:'6px', padding:'8px 10px', borderLeft:'3px solid #38bdf8' }}>
                        <div style={{ fontSize:'11px', color:'#38bdf8', fontWeight:'700', marginBottom:'4px' }}>Sunday — clear gap</div>
                        <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.6)', lineHeight:1.5 }}>
                          Avg winner score: <b style={{color:'#34d399'}}>{avg(sunSt.winScores)}</b><br/>
                          Avg loser score:  <b style={{color:'#f87171'}}>{avg(sunSt.lossScores)}</b><br/>
                          <span style={{ color:'#34d399', fontWeight:'800' }}>Separation: {sunGap} pts</span><br/>
                          <span style={{ color:'rgba(255,255,255,0.45)', fontSize:'11px' }}>Winning picks clearly stand out</span>
                        </div>
                      </div>
                    </div>
                    <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.5)', lineHeight:1.55 }}>
                      When the winner is only a few points ahead of the losers in our scoring model, it means the race conditions are too noisy for the model to edge out a reliable selection. Sunday cards produce a cleaner signal.
                    </div>
                  </div>
                )}

                {/* 4 structural reasons */}
                <div style={{ background:'rgba(249,115,22,0.07)', border:'1px solid rgba(249,115,22,0.22)', borderRadius:'8px', padding:'10px 14px' }}>
                  <div style={{ fontSize:'11px', fontWeight:'800', color:'#fb923c', marginBottom:'8px' }}>⚡ Why Saturdays are structurally harder</div>
                  <div style={{ display:'flex', flexDirection:'column', gap:'7px', fontSize:'12px', color:'rgba(255,255,255,0.55)', lineHeight:1.55 }}>
                    <div style={{ display:'flex', gap:'8px', alignItems:'flex-start' }}>
                      <span style={{ fontSize:'13px', flexShrink:0 }}>🎯</span>
                      <div><b style={{color:'rgba(255,255,255,0.8)'}}>Hyper-efficient markets.</b> Saturday showpiece meetings (Lincoln, Curragh, Kempton features) attract 5–10× more Betfair liquidity than Sunday cards. Prices get hammered close to true probability, leaving no exploitable edge for a form-based model.</div>
                    </div>
                    <div style={{ display:'flex', gap:'8px', alignItems:'flex-start' }}>
                      <span style={{ fontSize:'13px', flexShrink:0 }}>📋</span>
                      <div><b style={{color:'rgba(255,255,255,0.8)'}}>Season-openers &amp; raiders missing from database.</b> Big Saturday cards regularly feature horses returning from winter breaks (no recent UK form) and Irish cross-channel raiders. Our model scores them near-zero for database history — then they go and win.</div>
                    </div>
                    <div style={{ display:'flex', gap:'8px', alignItems:'flex-start' }}>
                      <span style={{ fontSize:'13px', flexShrink:0 }}>🎲</span>
                      <div><b style={{color:'rgba(255,255,255,0.8)'}}>Bigger, more chaotic fields.</b> Heritage handicaps (Lincoln 21 runners, Spring Cup 16+ runners) are deliberately designed to be competitive. Draw bias, pace scenarios and traffic in running override form signals — the model has no visibility of these factors.</div>
                    </div>
                    <div style={{ display:'flex', gap:'8px', alignItems:'flex-start' }}>
                      <span style={{ fontSize:'13px', flexShrink:0 }}>☀️</span>
                      <div><b style={{color:'rgba(255,255,255,0.8)'}}>Sunday = smaller fields, complete form records.</b> Provincial meetings (Naas, Carlisle, Stratford) run 6–10 runner fields where every horse has a full UK/Irish form profile, tighter odds and less chaos. The model's signals — consistency, going suitability, meeting focus — discriminate cleanly and {satML!=null && sunML!=null ? `our Sunday picks align with market opinion ${sunML}% of the time vs ${satML}% on Saturdays` : 'our picks align with the market far more often'}.
                      </div>
                    </div>
                  </div>
                </div>

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
          {(() => {
            const layMap = {};
            (layData?.races || []).forEach(r => {
              if (!r.outcome) return;
              const rt = r.race_time || '';
              const hhmm = rt.length >= 16 ? rt.substring(11, 16) : '';
              const course = (r.course || '').toLowerCase();
              if (hhmm && course) layMap[`${course}|${hhmm}`] = r.outcome;
            });
          return [...picks].sort((a, b) => {
            const ta = a.race_time || ''; const tb = b.race_time || '';
            // ISO strings sort lexicographically; US format needs normalising
            const norm = s => { const m = s.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})/); return m ? `${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}T${m[4].padStart(2,'0')}:${m[5]}` : s; };
            return norm(tb).localeCompare(norm(ta));
          }).map((pick, idx) => {
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
            const displayOdds = !isPending && pick.sp_odds ? parseFloat(pick.sp_odds) : parseFloat(pick.odds || 0);
            // Key reason: for settled picks show result_analysis; for pending show best pre-race reason
            const keyReason = !isPending && pick.result_analysis
              ? pick.result_analysis
              : (Array.isArray(pick.selection_reasons) && pick.selection_reasons.length > 0
                  ? bestKeyReasons(pick.selection_reasons, 1)[0] || ''
                  : (pick.result_analysis ? pick.result_analysis.substring(0,80) : ''));
            const winnerNote = !isPending && winner && winner !== pick.horse ? `Winner: ${winner}` : '';
            // Fav outcome from lay analysis
            const layOutcome = (() => {
              const hhmm = ft.time;
              const course = (pick.course || pick.race_course || '').toLowerCase();
              if (!hhmm || !course) return null;
              return layMap[`${course}|${hhmm}`] || null;
            })();
            const layFavWon = layOutcome ? ['win','won'].includes(layOutcome.toLowerCase()) : null;

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
                    <div style={{ fontSize:'11px', color:'#93c5fd', fontWeight:'700' }}>{displayOdds > 1 ? toFractional(displayOdds) : ''}</div>
                  </div>
                </div>
                {/* Row 2: key reason + winner note — no truncation on mobile */}
                {(keyReason || winnerNote) && (
                  <div style={{ marginTop:'5px', fontSize:'11px', lineHeight:1.4 }}>
                    {keyReason && <span style={{ color:'rgba(255,255,255,0.5)' }}>{keyReason}</span>}
                    {winnerNote && <div style={{ color:'#f87171', marginTop:'2px' }}>{winnerNote}</div>}
                  </div>
                )}
                {layFavWon !== null && (
                  <div style={{ marginTop:'4px' }}>
                    <span style={{ background: layFavWon ? 'rgba(248,113,113,0.18)' : 'rgba(52,211,153,0.18)', color: layFavWon ? '#f87171' : '#34d399', border:`1px solid ${layFavWon ? 'rgba(248,113,113,0.5)' : 'rgba(52,211,153,0.5)'}`, borderRadius:'4px', padding:'2px 8px', fontSize:'10px', fontWeight:'800' }}>
                      {layFavWon ? '✗ FAV WON' : '✓ FAV LOST'}
                    </span>
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

                {/* Key reason + winner note + fav outcome */}
                <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.6)', paddingRight:'8px', lineHeight:1.4 }}>
                  {keyReason && <span>{keyReason}</span>}
                  {winnerNote && <div style={{ fontSize:'11px', color:'#f87171', marginTop:'2px' }}>{winnerNote}</div>}
                  {layFavWon !== null && (
                    <div style={{ marginTop:'3px' }}>
                      <span style={{ background: layFavWon ? 'rgba(248,113,113,0.18)' : 'rgba(52,211,153,0.18)', color: layFavWon ? '#f87171' : '#34d399', border:`1px solid ${layFavWon ? 'rgba(248,113,113,0.5)' : 'rgba(52,211,153,0.5)'}`, borderRadius:'4px', padding:'2px 7px', fontSize:'10px', fontWeight:'800' }}>
                        {layFavWon ? '✗ FAV WON' : '✓ FAV LOST'}
                      </span>
                    </div>
                  )}
                </div>

                {/* Odds */}
                <div style={{ textAlign:'center', fontWeight:'700', color:'#93c5fd', fontSize:'13px' }}>
                  {displayOdds > 1 ? toFractional(displayOdds) : '—'}
                </div>

                {/* P&L */}
                <div style={{ textAlign:'right', fontWeight:'800', fontSize:'14px', color: pnl > 0 ? '#34d399' : pnl < 0 ? '#f87171' : 'rgba(255,255,255,0.4)' }}>
                  {isPending ? '—' : pnl >= 0 ? `+£${pnl.toFixed(2)}` : `-£${Math.abs(pnl).toFixed(2)}`}
                </div>
              </div>
            );
          });
          })()}
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

            {/* Systemic pattern summary */}
            {(() => {
              const patterns = [];
              const jockeyZero    = nonWins.filter(p => parseFloat((p.score_breakdown||{}).jockey_quality||0) === 0).length;
              const dbZero        = nonWins.filter(p => parseFloat((p.score_breakdown||{}).database_history||0) === 0).length;
              const unknownTrn    = nonWins.filter(p => parseFloat((p.score_breakdown||{}).unknown_trainer_penalty||0) < 0).length;
              const bottomWinners = nonWins.filter(p => {
                const fld = [...(p.all_horses||[])].sort((a,b)=>parseFloat(b.score||0)-parseFloat(a.score||0));
                if (fld.length < 3) return false;
                const wn = (p.result_winner_name||'').toLowerCase();
                const wi = fld.findIndex(h=>(h.horse||'').toLowerCase()===wn);
                return wi !== -1 && wi >= Math.ceil(fld.length / 2);
              }).length;
              const bigField = nonWins.filter(p => {
                const m = (p.result_analysis||'').match(/of (\d+)/);
                return m && parseInt(m[1]) >= 16;
              }).length;
              if (jockeyZero === nonWins.length)
                patterns.push({ icon:'🏇', col:'#93c5fd', title:'Jockey scoring inactive', detail:`${jockeyZero}/${nonWins.length} picks scored 0 for jockey quality — strong jockey bookings, course specialists and first-time big-stable rides are not factored in at all` });
              if (dbZero === nonWins.length)
                patterns.push({ icon:'📂', col:'#fbbf24', title:'No historical database data', detail:`${dbZero}/${nonWins.length} picks had zero DB history score — the model has no recorded win-rate data for any of these horses at this course/distance combination` });
              if (unknownTrn > 0)
                patterns.push({ icon:'❓', col:'#f97316', title:`Unknown trainer penalty insufficient`, detail:`${unknownTrn}/${nonWins.length} picks received -8pts unknown trainer penalty yet were still selected — if the trainer has no verified track record, selection confidence should be reduced further` });
              if (bottomWinners > 0)
                patterns.push({ icon:'📉', col:'#f87171', title:`Winner ranked bottom half of field`, detail:`${bottomWinners} race${bottomWinners>1?'s':''} won by a horse ranked in the bottom half of our model — winner likely had limited form data or first run at this trip/going; low model score ≠ no chance` });
              if (bigField > 0)
                patterns.push({ icon:'🎲', col:'#a78bfa', title:`Large-field handicap risk`, detail:`${bigField} race${bigField>1?'s':''} run in fields of 16+ runners — big handicaps carry inherent chaos; pace, draw and luck have outsized influence the model cannot capture` });
              if (patterns.length === 0) return null;
              return (
                <div style={{ background:'rgba(30,58,95,0.35)', border:'1px solid rgba(59,130,246,0.3)', borderRadius:'10px', padding:'16px 20px', marginBottom:'20px' }}>
                  <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1px', color:'#93c5fd', marginBottom:'12px', fontWeight:'800' }}>🔬 Systemic Patterns Found in These Losses</div>
                  <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                    {patterns.map((pt, pi) => (
                      <div key={pi} style={{ display:'flex', gap:'10px', alignItems:'flex-start' }}>
                        <span style={{ fontSize:'15px', flexShrink:0, lineHeight:'1.3' }}>{pt.icon}</span>
                        <div>
                          <div style={{ fontWeight:'700', color:pt.col, fontSize:'13px', marginBottom:'2px' }}>{pt.title}</div>
                          <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.55)', lineHeight:1.5 }}>{pt.detail}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {nonWins.map((pick, idx) => {
              const sb       = pick.score_breakdown || {};
              const odds     = parseFloat(pick.odds || 0);
              const score    = parseFloat(pick.comprehensive_score || pick.analysis_score || 0);
              const winner   = pick.result_winner_name || pick.winner_name || '?';
              const ft       = formatRaceTime(pick.race_time);
              const wa       = (() => {
                const stored = pick.winner_analysis || {};
                if (stored.winner_found) return stored;
                // Compute from all_horses when backend hasn't populated winner_analysis
                const field = [...(pick.all_horses || [])]
                  .map(h => ({ ...h, score: parseFloat(h.score || 0), odds: parseFloat(h.odds || 0) }))
                  .sort((a, b) => b.score - a.score);
                const winnerName = (pick.result_winner_name || pick.winner_name || '').toLowerCase();
                if (!winnerName || field.length === 0) return stored;
                const winnerIdx = field.findIndex(h => (h.horse || '').toLowerCase() === winnerName);
                if (winnerIdx === -1) return stored;
                const winnerH  = field[winnerIdx];
                const ourScore = parseFloat(pick.comprehensive_score || pick.analysis_score || 0);
                const gap      = ourScore - winnerH.score;
                const sb2      = pick.score_breakdown || {};
                const why      = [];
                if (winnerIdx === 0) {
                  why.push(`${winnerH.horse} also ranked #1 in our model — race was a genuine toss-up on paper`);
                } else {
                  why.push(`${winnerH.horse} ranked #${winnerIdx + 1} of ${field.length} in our model (score ${winnerH.score.toFixed(0)}) — model over-favoured our pick by ${gap.toFixed(0)}pts`);
                }
                if (winnerH.score < 35) why.push(`Winner score only ${winnerH.score.toFixed(0)}/100 — likely limited UK/IE recorded form in our database; unproven horses can still win`);
                if (parseFloat(sb2.unknown_trainer_penalty || 0) < 0) why.push(`Unknown trainer penalty (-${Math.abs(parseFloat(sb2.unknown_trainer_penalty)).toFixed(0)}pts) applied to our pick but score still high enough to select — trainer track record absent`);
                if (parseFloat(sb2.going_suitability || 0) >= 16) why.push(`Going Suitability scored +${parseFloat(sb2.going_suitability).toFixed(0)}pts — may be over-weighted vs actual ground impact on the day`);
                if (winnerH.odds > 8) why.push(`Winner was ${toFractional(winnerH.odds)} — market also underestimated them; race pace or trainer booking likely key`);
                return {
                  winner_found: true,
                  winner_name: winnerH.horse,
                  winner_score: winnerH.score.toFixed(0),
                  winner_rank: winnerIdx + 1,
                  winner_rank_of: field.length,
                  winner_odds_fractional: winnerH.odds > 1 ? toFractional(winnerH.odds) : '?',
                  score_gap: gap,
                  why_missed: why,
                };
              })();
              const isPlaced = (pick.result_emoji || pick.outcome || '').toUpperCase().includes('PLACED');

              const topBreakdown = Object.entries(sb)
                .filter(([,v]) => parseFloat(v) > 0)
                .sort(([,a],[,b]) => parseFloat(b) - parseFloat(a))
                .slice(0, 5);

              return (
                <div key={idx} style={{ background:'#1a1a2e', border:`1px solid ${isPlaced ? 'rgba(59,130,246,0.4)' : 'rgba(239,68,68,0.4)'}`, borderRadius:'12px', padding: isMobile ? '14px' : '20px 24px', marginBottom:'18px', borderLeft:`4px solid ${isPlaced ? '#3b82f6' : '#ef4444'}` }}>

                  {/* Header row */}
                  <div style={{ display:'flex', flexDirection: isMobile ? 'column' : 'row', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:'8px', marginBottom:'16px' }}>
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
                    {/* result_analysis: full-width block on mobile, inline badge on desktop */}
                    {(pick.result_analysis || winner !== '?') && (
                      isMobile ? (
                        <div style={{ width:'100%', background: isPlaced ? 'rgba(59,130,246,0.15)' : 'rgba(239,68,68,0.15)', border:`1px solid ${isPlaced ? 'rgba(59,130,246,0.4)' : 'rgba(239,68,68,0.4)'}`, borderRadius:'8px', padding:'10px 12px', fontSize:'12px', color: isPlaced ? '#93c5fd' : '#fca5a5', lineHeight:1.6, fontWeight:'500' }}>
                          {pick.result_analysis || `Winner: ${winner}`}
                        </div>
                      ) : (
                        <div style={{ background: isPlaced ? 'rgba(59,130,246,0.2)' : 'rgba(239,68,68,0.2)', border:`1px solid ${isPlaced ? 'rgba(59,130,246,0.45)' : 'rgba(239,68,68,0.45)'}`, color: isPlaced ? '#93c5fd' : '#fca5a5', borderRadius:'7px', padding:'6px 12px', fontSize:'11px', fontWeight:'700', lineHeight:1.5, textAlign:'right', flexShrink:0 }}>
                          {pick.result_analysis || (winner !== '?' ? `Winner: ${winner}` : 'Result recorded')}
                        </div>
                      )
                    )}
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

      {/* ── Strong Lay Possibilities ─────────────────────────────── */}
      {layData && (() => {
        const LAY_WEIGHTS = {
          class_up:4, trip_new:2, going_unproven:2, draw_poor:1, layoff:1, pace_doubt:1,
          rivals_close:2, drift:1, short_price:1, trainer_track:1, trainer_cold:1, trainer_multiple:1,
        };
        const LAY_LABELS = {
          class_up:         { label:'Class',        desc:'Moving up in Class',             colour:'#c084fc' },
          trip_new:         { label:'Trip',          desc:'New Distance (Up or Down)',      colour:'#6ee7b7' },
          going_unproven:   { label:'Going',         desc:'Unproven on current going',      colour:'#34d399' },
          draw_poor:        { label:'Draw',          desc:'Poor draw on this track',        colour:'#fbbf24' },
          layoff:           { label:'Layoff',        desc:'>30\u201390 days off',                colour:'#fca5a5' },
          pace_doubt:       { label:'Pace',          desc:'Pace may not suit',              colour:'#93c5fd' },
          rivals_close:     { label:'Rivals',        desc:'Creditable 2nd/3rd threats',     colour:'#60a5fa' },
          drift:            { label:'Drift',         desc:'Open vs current price',          colour:'#fcd34d' },
          short_price:      { label:'Price',         desc:'5/4 or less / odds-on',          colour:'#a78bfa' },
          trainer_track:    { label:'Trainer@Track', desc:'Trainer win rate at this track', colour:'#a5b4fc' },
          trainer_cold:     { label:'TrainerCold',   desc:'Last 14 days win rate (Cold)',   colour:'#818cf8' },
          trainer_multiple: { label:'MultiRunner',   desc:'Multiple runners same race',     colour:'#e879f9' },
        };
        const FACTOR_ORDER = ['class_up','trip_new','going_unproven','draw_poor','layoff','pace_doubt',
                               'rivals_close','drift','short_price','trainer_track','trainer_cold','trainer_multiple'];
        const VC = {
          RED:    { fg:'#f87171', bg:'rgba(248,113,113,0.12)', border:'rgba(248,113,113,0.35)' },
          AMBER:  { fg:'#f97316', bg:'rgba(249,115,22,0.12)',  border:'rgba(249,115,22,0.35)'  },
          YELLOW: { fg:'#fbbf24', bg:'rgba(251,191,36,0.10)',  border:'rgba(251,191,36,0.35)'  },
          GREEN:  { fg:'#34d399', bg:'rgba(52,211,153,0.10)',  border:'rgba(52,211,153,0.3)'   },
        };
        const caution  = (layData.races || []).filter(r => r.lay_score >= 4)
                                               .sort((a,b) => b.lay_score - a.lay_score);
        const genTime  = layData.generated
          ? new Date(layData.generated).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})
          : '';
        return (
          <div style={{ marginTop:'36px' }}>
            {/* Section header */}
            <div style={{ background:'linear-gradient(135deg,rgba(185,28,28,0.22) 0%,rgba(127,29,29,0.15) 100%)', border:'1px solid rgba(239,68,68,0.3)', borderRadius:'12px', padding:'20px 24px', marginBottom:'18px' }}>
              <div style={{ fontSize:'10px', letterSpacing:'2px', textTransform:'uppercase', color:'rgba(255,255,255,0.4)', marginBottom:'4px' }}>Lay Analysis \u00b7 Read-only parallel view</div>
              <div style={{ fontSize:'18px', fontWeight:'800', color:'white', marginBottom:'4px' }}>\ud83d\udea8 Strong Possibilities to Lay Suspect Favourites (5/4 or less)</div>
              <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.5)', marginBottom:'14px' }}>Is this Favourite overpriced relative to its true win probability?</div>
              <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'center' }}>
                {[{r:'0\u20133',l:'Leave Alone',c:'#34d399'},{r:'4\u20139',l:'Caution / Look',c:'#fbbf24'},{r:'10\u201312',l:'Strong Lay',c:'#f97316'},{r:'13+',l:'Strong Lay Candidate',c:'#f87171'}].map(x=>(
                  <div key={x.r} style={{display:'flex',alignItems:'center',gap:'5px',background:'rgba(255,255,255,0.06)',borderRadius:'6px',padding:'4px 10px',fontSize:'11px',color:'rgba(255,255,255,0.65)'}}>
                    <span style={{background:x.c,width:'7px',height:'7px',borderRadius:'50%',display:'inline-block'}}/>
                    <b style={{color:x.c}}>{x.r}</b>&nbsp;{x.l}
                  </div>
                ))}
                <span style={{marginLeft:'auto',fontSize:'11px',color:'rgba(255,255,255,0.35)'}}>
                  {caution.length} caution+ of {(layData.races||[]).length} analysed
                  {genTime && <span> \u00b7 {genTime}</span>}
                </span>
              </div>
            </div>

            {/* Scoring factors key */}
            <div style={{ background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'10px', padding:'14px 18px', marginBottom:'14px' }}>
              <div style={{ fontSize:'10px', textTransform:'uppercase', letterSpacing:'1px', color:'rgba(255,255,255,0.35)', marginBottom:'9px' }}>Factor \u00b7 Condition \u00b7 Score</div>
              <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(215px,1fr))', gap:'5px 20px' }}>
                {FACTOR_ORDER.map(k => {
                  const fl = LAY_LABELS[k];
                  return (
                    <div key={k} style={{ display:'flex', alignItems:'center', gap:'6px', fontSize:'11px' }}>
                      <span style={{ color:'#fbbf24', fontWeight:'700', minWidth:'22px' }}>+{LAY_WEIGHTS[k]}</span>
                      <span style={{ color:fl.colour, fontWeight:'600', minWidth:'88px' }}>{fl.label}</span>
                      <span style={{ color:'rgba(255,255,255,0.38)', fontSize:'10px' }}>{fl.desc}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Interpretation */}
            <div style={{ background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'8px', padding:'10px 16px', marginBottom:'16px', display:'flex', gap:'20px', flexWrap:'wrap', fontSize:'11px', color:'rgba(255,255,255,0.5)' }}>
              <span><b style={{color:'#34d399'}}>0\u20133</b> = Leave horse alone (Green)</span>
              <span><b style={{color:'#fbbf24'}}>4\u20139</b> = Caution \u2013 take a look if vulnerable (Yellow)</span>
              <span><b style={{color:'#f97316'}}>10\u201312</b> = Strong Lay (Amber)</span>
              <span><b style={{color:'#f87171'}}>13+</b> = Strong Lay Candidate (Red)</span>
            </div>

            {/* Lay candidate cards */}
            {caution.length === 0 ? (
              <div style={{ textAlign:'center', padding:'32px', color:'rgba(255,255,255,0.4)', background:'rgba(255,255,255,0.04)', borderRadius:'10px', fontSize:'13px' }}>
                No favourites meet the caution threshold (4+) today.
              </div>
            ) : caution.map((r, i) => {
              const vc = VC[r.verdict_colour] || VC.GREEN;
              const activeFlags = r.flags || [];
              return (
                <div key={i} style={{ background:'rgba(22,27,34,0.95)', border:`1px solid ${vc.border}`, borderLeft:`4px solid ${vc.fg}`, borderRadius:'10px', marginBottom:'12px', overflow:'hidden' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:'10px', flexWrap:'wrap', padding:'10px 16px', borderBottom:'1px solid rgba(255,255,255,0.07)', background:'rgba(255,255,255,0.02)' }}>
                    <span style={{ fontWeight:'800', color:'#58a6ff', fontSize:'14px' }}>{fmtUtcTime(r.race_time)}</span>
                    <span style={{ fontWeight:'700', color:'white' }}>{r.course}</span>
                    <span style={{ flex:1, fontSize:'11px', color:'rgba(255,255,255,0.45)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.race_name}</span>
                    {r.our_pick && <span style={{ background:'rgba(88,166,255,0.18)', color:'#58a6ff', border:'1px solid rgba(88,166,255,0.4)', borderRadius:'4px', padding:'2px 6px', fontSize:'10px', fontWeight:'700' }}>\u26a1 OUR PICK</span>}
                    <span style={{ background:vc.bg, color:vc.fg, border:`1px solid ${vc.border}`, borderRadius:'5px', padding:'2px 9px', fontSize:'10px', fontWeight:'700', textTransform:'uppercase', letterSpacing:'0.5px' }}>{r.verdict}</span>
                  </div>
                  <div style={{ display:'flex', gap:'16px', padding:'12px 16px', alignItems:'center', flexWrap:'wrap' }}>
                    <div style={{ flex:1 }}>
                      <div style={{ fontSize:'17px', fontWeight:'800', color:'white', marginBottom:'5px' }}>{r.favourite}</div>
                      <div style={{ display:'flex', flexWrap:'wrap', gap:'3px 14px', fontSize:'11px', color:'rgba(255,255,255,0.5)', marginBottom:'6px' }}>
                        <span>@ <b style={{color:'#e6edf3'}}>{r.fav_odds?.toFixed(2)}</b></span>
                        <span>Score <b style={{color:'#e6edf3'}}>{r.fav_sys_score?.toFixed(0)}</b></span>
                        <span>Gap <b style={{color:'#e6edf3'}}>{r.score_gap?.toFixed(0)}</b></span>
                        {r.form && <span>Form <b style={{color:'#e6edf3'}}>{r.form}</b></span>}
                        <span>Runners <b style={{color:'#e6edf3'}}>{r.runners}</b></span>
                        {r.trainer && <span>Trainer <b style={{color:'rgba(255,255,255,0.7)'}}>{r.trainer}</b></span>}
                      </div>
                      <div style={{ display:'flex', flexWrap:'wrap', gap:'4px' }}>
                        {activeFlags.map(flag => {
                          const fl = LAY_LABELS[flag] || { label:flag, colour:'#94a3b8' };
                          return (
                            <span key={flag} style={{ background:'rgba(255,255,255,0.08)', border:`1px solid ${fl.colour}55`, color:fl.colour, borderRadius:'4px', padding:'2px 7px', fontSize:'10px', fontWeight:'600' }}>
                              {fl.label} +{LAY_WEIGHTS[flag] || 1}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                    <div style={{ textAlign:'center', minWidth:'64px' }}>
                      <div style={{ fontSize:'36px', fontWeight:'800', lineHeight:1, color:vc.fg }}>{r.lay_score}</div>
                      <div style={{ fontSize:'10px', color:'rgba(255,255,255,0.4)', marginBottom:'4px' }}>/ 18</div>
                      <div style={{ background:vc.bg, color:vc.fg, border:`1px solid ${vc.border}`, borderRadius:'5px', padding:'2px 7px', fontSize:'10px', fontWeight:'700', textTransform:'uppercase' }}>{r.verdict}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}

      <div style={{ marginTop:'16px', padding:'14px 18px', background:'rgba(255,255,255,0.06)', borderRadius:'10px', color:'rgba(255,255,255,0.45)', fontSize:'12px', textAlign:'center', lineHeight:'1.6' }}>
        Results are recorded after each race. Pending picks update as results come in. · Always bet responsibly.
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

// ---- Lay the Fav View ----
function LayTheFavView() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [filter, setFilter] = useState('all'); // all | caution | strong

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE_URL}/api/favs-run`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const VERDICT_COLOURS = {
    RED:    { fg:'#f87171', bg:'rgba(248,113,113,0.12)', border:'rgba(248,113,113,0.35)' },
    AMBER:  { fg:'#f97316', bg:'rgba(249,115,22,0.12)',  border:'rgba(249,115,22,0.35)'  },
    YELLOW: { fg:'#fbbf24', bg:'rgba(251,191,36,0.10)',  border:'rgba(251,191,36,0.35)'  },
    GREEN:  { fg:'#34d399', bg:'rgba(52,211,153,0.10)',  border:'rgba(52,211,153,0.3)'   },
  };

  const FLAG_LABELS = {
    short_price:      { label:'Price',         colour:'#a78bfa' },
    rivals_close:     { label:'Rivals',        colour:'#60a5fa' },
    trip_new:         { label:'Trip',          colour:'#6ee7b7' },
    going_unproven:   { label:'Going',         colour:'#34d399' },
    draw_poor:        { label:'Draw',          colour:'#fbbf24' },
    layoff:           { label:'Layoff',        colour:'#fca5a5' },
    pace_doubt:       { label:'Pace',          colour:'#93c5fd' },
    drift:            { label:'Drift',         colour:'#fcd34d' },
    class_up:         { label:'Class',         colour:'#c084fc' },
    trainer_track:    { label:'Trainer@Track', colour:'#a5b4fc' },
    trainer_cold:     { label:'TrainerCold',   colour:'#818cf8' },
    trainer_multiple: { label:'MultiRunner',   colour:'#e879f9' },
  };

  const FLAG_WEIGHTS = { short_price:1, rivals_close:2, trip_new:2, going_unproven:2,
    draw_poor:1, layoff:1, pace_doubt:1, drift:1, class_up:4,
    trainer_track:1, trainer_cold:1, trainer_multiple:1 };

  if (loading) return (
    <div style={{ textAlign:'center', padding:'60px', color:'rgba(255,255,255,0.5)' }}>
      <div style={{ fontSize:'32px', marginBottom:'12px' }}>🚨</div>
      <div>Loading lay analysis…</div>
    </div>
  );

  if (error || !data?.success) return (
    <div style={{ textAlign:'center', padding:'60px', color:'#f87171' }}>
      <div style={{ fontSize:'28px', marginBottom:'12px' }}>⚠️</div>
      <div>{error || data?.error || 'Failed to load'}</div>
    </div>
  );

  const { summary, races, generated } = data;
  const genTime = generated ? new Date(generated).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'}) : '';

  const filtered = races.filter(r =>
    filter === 'red'     ? r.lay_score >= 13 :
    filter === 'strong'  ? r.lay_score >= 10 :
    filter === 'caution' ? r.lay_score >= 4 :
    true
  );

  return (
    <div style={{ paddingBottom:'40px' }}>

      {/* Header */}
      <div style={{ background:'linear-gradient(135deg,rgba(185,28,28,0.25) 0%,rgba(127,29,29,0.18) 100%)', border:'1px solid rgba(239,68,68,0.3)', borderRadius:'14px', padding:'24px 28px', marginBottom:'24px' }}>
        <div style={{ fontSize:'11px', letterSpacing:'2px', textTransform:'uppercase', color:'rgba(255,255,255,0.4)', marginBottom:'6px' }}>Favs-Run · Read-only parallel analysis</div>
        <div style={{ fontSize:'22px', fontWeight:'800', color:'white', marginBottom:'4px' }}>🚨 Lay the Favourite</div>
        <div style={{ fontSize:'13px', color:'rgba(255,255,255,0.55)', marginBottom:'18px' }}>Identifies short-price favourites with structural vulnerabilities. Does <strong style={{color:'rgba(255,255,255,0.8)'}}>not</strong> affect picks, weights or UI.</div>

        {/* Score legend */}
        <div style={{ display:'flex', gap:'10px', flexWrap:'wrap', marginBottom:'18px' }}>
          {[{score:'0–3', label:'Leave Alone', c:'#34d399'}, {score:'4–9', label:'Caution / Look', c:'#fbbf24'}, {score:'10–12', label:'Strong Lay', c:'#f97316'}, {score:'13+', label:'Strong Lay Candidate', c:'#f87171'}].map(l => (
            <div key={l.score} style={{ display:'flex', alignItems:'center', gap:'6px', background:'rgba(255,255,255,0.06)', borderRadius:'8px', padding:'5px 12px', fontSize:'12px', color:'rgba(255,255,255,0.7)' }}>
              <span style={{ background:l.c, width:'8px', height:'8px', borderRadius:'50%', display:'inline-block' }} />
              <b style={{ color:l.c }}>{l.score}</b>&nbsp;{l.label}
            </div>
          ))}
        </div>

        {/* Stats */}
        <div style={{ display:'flex', gap:'16px', flexWrap:'wrap' }}>
          {[{v:summary.total, lbl:'Analysed', c:'#94a3b8'}, {v:summary.caution, lbl:'Caution+', c:'#fbbf24'}, {v:summary.strong, lbl:'Strong Lay (10+)', c:'#f97316'}, {v:summary.red_flag, lbl:'Red Flag (13+)', c:'#f87171'}].map(s => (
            <div key={s.lbl} style={{ background:'rgba(255,255,255,0.07)', borderRadius:'10px', padding:'10px 18px', textAlign:'center' }}>
              <div style={{ fontSize:'24px', fontWeight:'800', color:s.c }}>{s.v}</div>
              <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.5)', marginTop:'2px' }}>{s.lbl}</div>
            </div>
          ))}
          {genTime && <div style={{ marginLeft:'auto', fontSize:'11px', color:'rgba(255,255,255,0.35)', alignSelf:'flex-end', paddingBottom:'4px' }}>Updated {genTime}</div>}
        </div>
      </div>

      {/* Factor scoring key */}
      <div style={{ background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'10px', padding:'16px 20px', marginBottom:'20px' }}>
        <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1px', color:'rgba(255,255,255,0.35)', marginBottom:'10px' }}>Scoring Factors</div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(220px, 1fr))', gap:'5px 24px' }}>
          {Object.entries(FLAG_WEIGHTS).map(([k, pts]) => {
            const fl = FLAG_LABELS[k] || { label: k, colour: '#94a3b8' };
            return (
              <div key={k} style={{ display:'flex', alignItems:'center', gap:'6px', fontSize:'12px' }}>
                <span style={{ color:'#fbbf24', fontWeight:'700', minWidth:'20px' }}>+{pts}</span>
                <span style={{ color:fl.colour, fontWeight:'600' }}>{fl.label}</span>
                <span style={{ color:'rgba(255,255,255,0.35)' }}>—</span>
                <span style={{ color:'rgba(255,255,255,0.5)', fontSize:'11px' }}>{
                  ({ short_price:'5/4 or less / odds-on', rivals_close:'2nd/3rd within 25% score', trip_new:'Unproven distance',
                     going_unproven:'Unproven going', draw_poor:'Poor draw', layoff:'30-90 day break',
                     pace_doubt:'Pace may not suit', drift:'Open vs current price', class_up:'Moving up in class',
                     trainer_track:'No tier status at this track', trainer_cold:'No meeting focus & no recent win', trainer_multiple:'Trainer has multiple runners' })[k]
                }</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter buttons */}
      <div style={{ display:'flex', gap:'8px', marginBottom:'16px', flexWrap:'wrap' }}>
        {[{k:'all',label:'All'},{ k:'caution',label:'Caution+ (4+)'},{ k:'strong',label:'Strong Lay (10+)'},{ k:'red',label:'Red Flag (13+)'}].map(f => (
          <button key={f.k} onClick={() => setFilter(f.k)} style={{
            background: filter===f.k ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.07)',
            border: filter===f.k ? '1px solid #f87171' : '1px solid rgba(255,255,255,0.15)',
            borderRadius:'6px', color:'white', cursor:'pointer', padding:'6px 14px', fontSize:'12px', fontWeight: filter===f.k ? '700' : '400',
          }}>{f.label}</button>
        ))}
        <span style={{ marginLeft:'auto', fontSize:'12px', color:'rgba(255,255,255,0.4)', alignSelf:'center' }}>{filtered.length} race{filtered.length!==1?'s':''}</span>
      </div>

      {/* Race cards */}
      {filtered.length === 0 && (
        <div style={{ textAlign:'center', padding:'40px', color:'rgba(255,255,255,0.4)', background:'rgba(255,255,255,0.04)', borderRadius:'10px' }}>
          No favourites match this filter today.
        </div>
      )}

      {filtered.map((r, i) => {
        const vc = VERDICT_COLOURS[r.verdict_colour] || VERDICT_COLOURS.GREEN;
        const barPct = Math.min(100, Math.round(r.lay_score / 18 * 100));
        return (
          <div key={i} style={{ background:'rgba(22,27,34,0.95)', border:`1px solid ${vc.border}`, borderLeft:`4px solid ${vc.fg}`, borderRadius:'10px', marginBottom:'14px', overflow:'hidden' }}>

            {/* Card header */}
            <div style={{ display:'flex', alignItems:'center', gap:'10px', flexWrap:'wrap', padding:'12px 18px', borderBottom:'1px solid rgba(255,255,255,0.07)', background:'rgba(255,255,255,0.02)' }}>
              <span style={{ fontWeight:'800', color:'#58a6ff', fontSize:'15px', minWidth:'40px' }}>{fmtUtcTime(r.race_time)}</span>
              <span style={{ fontWeight:'700', color:'white' }}>{r.course}</span>
              <span style={{ flex:1, fontSize:'12px', color:'rgba(255,255,255,0.45)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.race_name}</span>
              {r.our_pick && <span style={{ background:'rgba(88,166,255,0.18)', color:'#58a6ff', border:'1px solid rgba(88,166,255,0.4)', borderRadius:'4px', padding:'2px 8px', fontSize:'11px', fontWeight:'700' }}>⚡ OUR PICK</span>}
              {r.outcome && (() => {
                const oc = r.outcome.toLowerCase();
                const favWon = ['win','won'].includes(oc);
                return (
                  <span style={{
                    background: favWon ? 'rgba(248,113,113,0.18)' : 'rgba(52,211,153,0.18)',
                    color:       favWon ? '#f87171' : '#34d399',
                    border:      `1px solid ${favWon ? 'rgba(248,113,113,0.5)' : 'rgba(52,211,153,0.5)'}`,
                    borderRadius:'4px', padding:'2px 10px', fontSize:'11px', fontWeight:'800',
                    whiteSpace:'nowrap', letterSpacing:'0.3px',
                  }}>
                    {favWon ? '✗ FAV WON' : '✓ FAV LOST'}
                  </span>
                );
              })()}
              <span style={{ background:vc.bg, color:vc.fg, border:`1px solid ${vc.border}`, borderRadius:'5px', padding:'2px 10px', fontSize:'11px', fontWeight:'700', textTransform:'uppercase', letterSpacing:'0.5px', whiteSpace:'nowrap' }}>{r.verdict}</span>
            </div>

            {/* Card body */}
            <div style={{ display:'flex', alignItems:'center', gap:'20px', padding:'14px 18px' }}>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:'20px', fontWeight:'800', color:'white', marginBottom:'6px' }}>{r.favourite}</div>
                <div style={{ display:'flex', flexWrap:'wrap', gap:'4px 16px', fontSize:'12px', color:'rgba(255,255,255,0.5)', marginBottom:'4px' }}>
                  <span>@ <b style={{color:'#e6edf3'}}>{r.fav_odds?.toFixed(2)}</b></span>
                  <span>Sys Score <b style={{color:'#e6edf3'}}>{r.fav_sys_score?.toFixed(0)}</b></span>
                  <span>Score Gap <b style={{color:'#e6edf3'}}>{r.score_gap?.toFixed(0)}</b></span>
                  <span>Form <b style={{color:'#e6edf3'}}>{r.form || '—'}</b></span>
                  <span>Runners <b style={{color:'#e6edf3'}}>{r.runners}</b></span>
                </div>
                <div style={{ display:'flex', flexWrap:'wrap', gap:'4px 16px', fontSize:'12px', color:'rgba(255,255,255,0.5)' }}>
                  <span>Trainer <b style={{color:'rgba(255,255,255,0.75)'}}>{r.trainer || '—'}</b></span>
                  <span>Jockey <b style={{color:'rgba(255,255,255,0.75)'}}>{r.jockey || '—'}</b></span>
                </div>
              </div>

              {/* Score circle */}
              <div style={{ textAlign:'center', minWidth:'72px' }}>
                <div style={{ fontSize:'38px', fontWeight:'800', lineHeight:1, color:vc.fg }}>{r.lay_score}</div>
                <div style={{ fontSize:'11px', color:'rgba(255,255,255,0.4)', marginBottom:'6px' }}>/ 18</div>
                <div style={{ width:'64px', height:'6px', background:'rgba(255,255,255,0.1)', borderRadius:'3px', overflow:'hidden', margin:'0 auto' }}>
                  <div style={{ width:`${barPct}%`, height:'100%', background:vc.fg, borderRadius:'3px' }} />
                </div>
              </div>
            </div>

            {/* Flags */}
            {r.flags && r.flags.length > 0 && (
              <div style={{ display:'flex', flexWrap:'wrap', gap:'6px', padding:'4px 18px 10px' }}>
                {r.flags.map(f => {
                  const fl = FLAG_LABELS[f] || { label: f, colour: '#94a3b8' };
                  const pts = FLAG_WEIGHTS[f] || 0;
                  return (
                    <span key={f} style={{ background:'rgba(255,255,255,0.07)', border:`1px solid rgba(255,255,255,0.15)`, color:fl.colour, borderRadius:'4px', padding:'2px 8px', fontSize:'11px', fontWeight:'600' }}>
                      {fl.label} +{pts}
                    </span>
                  );
                })}
              </div>
            )}

            {/* Details */}
            {r.details && r.details.length > 0 && (
              <ul style={{ margin:'0 18px 14px 30px', padding:0, listStyle:'disc' }}>
                {r.details.map((d, di) => (
                  <li key={di} style={{ fontSize:'12px', color:'rgba(255,255,255,0.5)', marginBottom:'3px' }}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        );
      })}

      {/* Summary table */}
      {races.length > 0 && (
        <div style={{ marginTop:'24px' }}>
          <div style={{ fontSize:'11px', textTransform:'uppercase', letterSpacing:'1px', color:'rgba(255,255,255,0.35)', marginBottom:'10px' }}>Summary Table</div>
          <div style={{ overflowX:'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', background:'rgba(22,27,34,0.95)', border:'1px solid rgba(255,255,255,0.1)', borderRadius:'8px', overflow:'hidden' }}>
              <thead>
                <tr style={{ background:'rgba(255,255,255,0.06)' }}>
                  {['Time','Course','Favourite','Odds','SysScore','Gap','Lay Score','Verdict','Result'].map(h => (
                    <th key={h} style={{ padding:'9px 12px', fontSize:'11px', textTransform:'uppercase', letterSpacing:'0.7px', color:'rgba(255,255,255,0.4)', textAlign:'left', borderBottom:'1px solid rgba(255,255,255,0.1)', whiteSpace:'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {races.map((r, i) => {
                  const vc = VERDICT_COLOURS[r.verdict_colour] || VERDICT_COLOURS.GREEN;
                  return (
                    <tr key={i} style={{ borderBottom:'1px solid rgba(255,255,255,0.06)' }}>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'#58a6ff', fontWeight:'700' }}>{fmtUtcTime(r.race_time)}</td>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'rgba(255,255,255,0.8)' }}>{r.course}</td>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'white', fontWeight:'600' }}>{r.favourite}</td>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'rgba(255,255,255,0.7)' }}>{r.fav_odds?.toFixed(2)}</td>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'rgba(255,255,255,0.7)' }}>{r.fav_sys_score?.toFixed(0)}</td>
                      <td style={{ padding:'9px 12px', fontSize:'13px', color:'rgba(255,255,255,0.7)' }}>{r.score_gap?.toFixed(0)}</td>
                      <td style={{ padding:'9px 12px', fontSize:'14px', fontWeight:'800', color:vc.fg }}>{r.lay_score}</td>
                      <td style={{ padding:'9px 12px' }}><span style={{ background:vc.bg, color:vc.fg, border:`1px solid ${vc.border}`, borderRadius:'4px', padding:'2px 8px', fontSize:'11px', fontWeight:'700' }}>{r.verdict}</span></td>
                      <td style={{ padding:'9px 12px' }}>{r.outcome ? (() => { const favWon = ['win','won'].includes(r.outcome.toLowerCase()); return <span style={{ color: favWon ? '#f87171' : '#34d399', fontWeight:'700', fontSize:'12px' }}>{favWon ? '✗ Won' : '✓ Lost'}</span>; })() : <span style={{ color:'rgba(255,255,255,0.25)', fontSize:'12px' }}>—</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
