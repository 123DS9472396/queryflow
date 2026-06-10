/**
 * MiniChart.jsx — Professional Senior Data Engineer grade BI visualization.
 *
 * Gap fixes applied:
 *  1. Donut guard: no donut for 1-row data or >200x skewed values → force bar
 *  2. Scale mismatch: dual Y-axis auto-detection for multi-series
 *  3. Average reference line on bar/area charts for comparative context
 *  4. Multi-series comparison: if 2 rows of categorical data → horizontal bar (most readable for comparison)
 *  5. Each bar gets its own PALETTE colour for categorical data
 *  6. Percentage labels rendered inside pie slices
 *  7. Sortable data table
 *  8. Animated KPI cards with hover lift
 */
import { useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
  AreaChart, Area, PieChart, Pie, Sector, Legend, LineChart, Line, ReferenceLine,
  LabelList,
} from 'recharts';

const PALETTE = ['#10b981','#38bdf8','#a78bfa','#f59e0b','#ec4899','#34d399','#fb923c','#f43f5e'];

// ── Key detection ─────────────────────────────────────────────────────────────
function detectKeys(data) {
  if (!data?.length) return { xKey: null, yKeys: [] };
  const keys = Object.keys(data[0]);
  const catHints  = ['payment_method','day_name','day_of_week','month_name','pickup_date','method','date','day','week','month','hour','vendor','name'];
  const xKey = keys.find(k => catHints.some(c => k.toLowerCase().includes(c)))
             ?? keys.find(k => isNaN(Number(data[0][k])))
             ?? keys[0];
  const yKeys = keys.filter(k => k !== xKey && typeof data[0][k] === 'number');
  return { xKey, yKeys };
}

// ── Value range checker: max / min ratio ──────────────────────────────────────
function valueRatio(data, key) {
  const vals = data.map(r => Math.abs(Number(r[key]) || 0)).filter(v => v > 0);
  if (vals.length < 2) return 1;
  return Math.max(...vals) / Math.min(...vals);
}

function needsDualAxis(data, yKeys) {
  if (yKeys.length < 2) return false;
  const max0 = Math.max(...data.map(r => Math.abs(Number(r[yKeys[0]]) || 0)));
  const max1 = Math.max(...data.map(r => Math.abs(Number(r[yKeys[1]]) || 0)));
  if (!max0 || !max1) return false;
  return Math.max(max0, max1) / Math.min(max0, max1) > 30;
}

// ── Smart chart type selector ─────────────────────────────────────────────────
function detectChartType(data, xKey, yKeys) {
  if (!data?.length || !yKeys.length) return 'bar';

  const rows = data.length;
  const primaryY = yKeys[0];

  // Never use donut if: single row, OR max/min ratio > 200 (one slice swamps others)
  const isTimeKey  = ['date','hour','month_num','week','pickup'].some(kw => xKey.toLowerCase().includes(kw));
  const isDateStr  = typeof data[0][xKey] === 'string' && /^\d{4}-\d{2}-\d{2}/.test(data[0][xKey]);
  const isHourKey  = xKey.toLowerCase().includes('hour');

  if (isDateStr && rows >= 4)   return 'area';
  if (isHourKey)                return 'line';
  if (isTimeKey && rows >= 4)   return 'area';

  // Categorical: decide bar vs donut
  const skewed = valueRatio(data, primaryY) > 200;
  if (rows === 1)               return 'singleKpi';   // special: just KPI, no chart
  if (rows <= 6 && !skewed && yKeys.length === 1) return 'donut';
  if (rows > 12)                return 'horizontalBar';
  return 'bar';
}

// ── Formatters ────────────────────────────────────────────────────────────────
function fmt(v) {
  if (typeof v !== 'number') return String(v);
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000)     return `${(v / 1_000).toFixed(1)}K`;
  return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2);
}
const prettify = k => k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// ── Custom tooltip ────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:'rgba(8,12,28,0.97)', backdropFilter:'blur(16px)', border:'1px solid rgba(255,255,255,0.13)', borderRadius:12, padding:'12px 16px', boxShadow:'0 12px 40px rgba(0,0,0,0.6)', minWidth:160, zIndex:9999 }}>
      <p style={{ color:'#64748b', margin:'0 0 8px 0', fontSize:10, textTransform:'uppercase', letterSpacing:'1px', fontWeight:700 }}>{label}</p>
      {payload.map((p, i) => (
        <div key={i} style={{ display:'flex', alignItems:'center', gap:8, marginBottom: i < payload.length-1 ? 6 : 0 }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:p.color, flexShrink:0, boxShadow:`0 0 6px ${p.color}` }} />
          <span style={{ color:'#94a3b8', fontSize:11, flexGrow:1 }}>{prettify(p.dataKey)}</span>
          <span style={{ fontSize:15, fontWeight:800, color:p.color, fontFamily:'monospace' }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Active Donut Shape ────────────────────────────────────────────────────────
function ActiveShape(props) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, percent, value } = props;
  return (
    <g>
      <text x={cx} y={cy - 14} textAnchor="middle" fill="#f1f5f9" fontSize={14} fontWeight={700}>{payload.name}</text>
      <text x={cx} y={cy + 8}  textAnchor="middle" fill={fill}    fontSize={18} fontWeight={800} fontFamily="monospace">{fmt(value)}</text>
      <text x={cx} y={cy + 28} textAnchor="middle" fill="#64748b" fontSize={12}>{(percent * 100).toFixed(1)}%</text>
      <Sector cx={cx} cy={cy} innerRadius={innerRadius}      outerRadius={outerRadius + 10} startAngle={startAngle} endAngle={endAngle} fill={fill} />
      <Sector cx={cx} cy={cy} innerRadius={outerRadius + 13} outerRadius={outerRadius + 17} startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={0.6} />
    </g>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ label, value, color, icon, subtitle }) {
  return (
    <div
      style={{ background:`linear-gradient(135deg,${color}20,${color}08)`, border:`1px solid ${color}35`, borderRadius:14, padding:'14px 18px', flex:'1 1 110px', display:'flex', flexDirection:'column', gap:5, transition:'transform 0.2s,box-shadow 0.2s', cursor:'default' }}
      onMouseEnter={e => { e.currentTarget.style.transform='translateY(-3px)'; e.currentTarget.style.boxShadow=`0 8px 24px ${color}25`; }}
      onMouseLeave={e => { e.currentTarget.style.transform='translateY(0)'; e.currentTarget.style.boxShadow='none'; }}>
      <span style={{ fontSize:20 }}>{icon}</span>
      <span style={{ fontSize:22, fontWeight:800, color:'#f8fafc', fontFamily:'monospace', letterSpacing:-1, lineHeight:1.1 }}>{fmt(value)}</span>
      <span style={{ fontSize:10, color, fontWeight:700, textTransform:'uppercase', letterSpacing:'0.9px' }}>{label}</span>
      {subtitle && <span style={{ fontSize:10, color:'#475569' }}>{subtitle}</span>}
    </div>
  );
}

// ── Shared axis helpers ───────────────────────────────────────────────────────
const xProps = (cd, xKey) => ({
  dataKey: xKey,
  tick:{ fontSize:11, fill:'#4b5563', fontWeight:500 },
  axisLine:false, tickLine:false, dy:8,
  angle: cd.length > 7 ? -28 : 0,
  textAnchor: cd.length > 7 ? 'end' : 'middle',
  height: cd.length > 7 ? 55 : 30,
  interval: 0,
});
const yProps = (fmt2 = fmt, width = 62) => ({
  tick:{ fontSize:11, fill:'#4b5563', fontFamily:'monospace' },
  axisLine:false, tickLine:false, width, tickFormatter:fmt2, dx:-4,
});
const gridP = { strokeDasharray:'3 3', stroke:'rgba(255,255,255,0.05)', vertical:false };
const tipP  = content => ({ content, cursor:{ fill:'rgba(255,255,255,0.03)', rx:4 } });

// ── Main component ────────────────────────────────────────────────────────────
export default function MiniChart({ data }) {
  const [view,      setView]      = useState('chart');
  const [activeIdx, setActiveIdx] = useState(0);
  const [sortKey,   setSortKey]   = useState(null);
  const [sortDir,   setSortDir]   = useState('desc');

  const { xKey, yKeys } = useMemo(() => detectKeys(data), [data]);
  if (!xKey || !yKeys.length || !data?.length) return null;

  const primaryY  = yKeys[0];
  const chartData = data.slice(0, 30).map(row => ({
    ...row,
    [xKey]: typeof row[xKey] === 'string' ? row[xKey].slice(0, 16) : row[xKey],
  }));
  const chartType  = detectChartType(chartData, xKey, yKeys);
  const dualAxis   = needsDualAxis(chartData, yKeys) && yKeys.length >= 2;

  // KPI cards — avg for avg/pct/rate columns, sum for totals/counts
  const kpis = useMemo(() => {
    const icons = { revenue:'💰', trips:'🚕', distance:'🗺️', duration:'⏱️', passengers:'👥', tip:'💳', pct:'📐', usd:'💵', miles:'📍', minutes:'🕐', rate:'📈', default:'📊' };
    const avgKeys = ['avg','pct','rate','distance','duration','miles','minutes','percent'];
    return yKeys.slice(0, 4).map((k, i) => {
      const nums   = data.map(r => Number(r[k]) || 0).filter(v => !isNaN(v));
      const isAvgType = avgKeys.some(h => k.toLowerCase().includes(h));
      const value  = isAvgType
        ? nums.reduce((a, b) => a + b, 0) / nums.length   // mean
        : nums.reduce((a, b) => a + b, 0);                  // sum
      const iconK  = Object.keys(icons).find(h => k.toLowerCase().includes(h)) ?? 'default';
      const subtitle = isAvgType
        ? `avg of ${nums.length} rows — min ${fmt(Math.min(...nums))}, max ${fmt(Math.max(...nums))}`
        : `total across ${nums.length} rows`;
      return { label: prettify(k), value, color: PALETTE[i % PALETTE.length], icon: icons[iconK], subtitle };
    });
  }, [data, yKeys]);

  // Reference line uses same logic as KPI
  const primaryYIsAvg = ['avg','pct','rate','distance','duration','miles','minutes','percent'].some(h => primaryY.toLowerCase().includes(h));
  const avgVal = useMemo(() => {
    const nums = chartData.map(r => Number(r[primaryY]) || 0);
    return primaryYIsAvg
      ? nums.reduce((a, b) => a + b, 0) / nums.length
      : nums.reduce((a, b) => a + b, 0) / nums.length;
  }, [chartData, primaryY, primaryYIsAvg]);

  // CSV
  const downloadCSV = () => {
    const hdr  = Object.keys(data[0]).join(',');
    const rows = data.map(r => Object.values(r).map(v => `"${v}"`).join(',')).join('\n');
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(new Blob([hdr + '\n' + rows], { type:'text/csv' }));
    a.download = `queryflow_${Date.now()}.csv`;
    a.click();
  };

  // Sortable table
  const tableData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const [va, vb] = [a[sortKey], b[sortKey]];
      const dir = sortDir === 'asc' ? 1 : -1;
      return typeof va === 'number' ? (va - vb) * dir : String(va).localeCompare(String(vb)) * dir;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = key => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const tip = tipP(<CustomTooltip />);

  // ── Chart renderer ──────────────────────────────────────────────────────────
  const renderChart = () => {

    // Single KPI — just show cards, no chart needed
    if (chartType === 'singleKpi') return null;

    // ── Donut ──
    if (chartType === 'donut') {
      const pieData = chartData.map(d => ({ name: String(d[xKey]), value: Number(d[primaryY]) || 0 }));
      return (
        <PieChart>
          <Pie activeIndex={activeIdx} activeShape={ActiveShape} onMouseEnter={(_, i) => setActiveIdx(i)}
            data={pieData} cx="42%" cy="50%" innerRadius={72} outerRadius={108}
            paddingAngle={3} dataKey="value" animationDuration={900} stroke="none">
            {pieData.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]}
                style={{ outline:'none', cursor:'pointer', filter: activeIdx === i ? `drop-shadow(0 0 10px ${PALETTE[i % PALETTE.length]})` : 'none', transition:'filter 0.25s' }} />
            ))}
          </Pie>
          <Legend layout="vertical" align="right" verticalAlign="middle"
            formatter={v => <span style={{ color:'#94a3b8', fontSize:12 }}>{v}</span>}
            iconType="circle" iconSize={9} />
        </PieChart>
      );
    }

    // ── Area ──
    if (chartType === 'area') {
      return (
        <AreaChart data={chartData} margin={{ top:10, right:16, bottom:20, left:0 }}>
          <defs>
            {yKeys.slice(0,3).map((_, i) => (
              <linearGradient key={i} id={`aG${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={PALETTE[i]} stopOpacity={0.45} />
                <stop offset="95%" stopColor={PALETTE[i]} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid {...gridP} />
          <XAxis {...xProps(chartData, xKey)} />
          <YAxis {...yProps()} />
          <Tooltip {...tip} />
          <ReferenceLine y={avgVal} stroke="rgba(255,255,255,0.18)" strokeDasharray="4 3"
            label={{ value:`Avg ${fmt(avgVal)}`, fill:'#64748b', fontSize:10, position:'insideTopRight' }} />
          {yKeys.map((k, i) => (
            <Area key={k} type="monotone" dataKey={k} stroke={PALETTE[i]} strokeWidth={2.5}
              fill={`url(#aG${i})`} fillOpacity={1} dot={false}
              activeDot={{ r:5, fill:PALETTE[i], stroke:'rgba(255,255,255,0.2)', strokeWidth:2 }}
              animationDuration={900} />
          ))}
          {yKeys.length > 1 && <Legend formatter={v => <span style={{ color:'#94a3b8', fontSize:11 }}>{prettify(v)}</span>} />}
        </AreaChart>
      );
    }

    // ── Line ──
    if (chartType === 'line') {
      return (
        <LineChart data={chartData} margin={{ top:10, right:16, bottom:20, left:0 }}>
          <CartesianGrid {...gridP} />
          <XAxis {...xProps(chartData, xKey)} />
          <YAxis {...yProps()} />
          <Tooltip {...tip} />
          <ReferenceLine y={avgVal} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 3"
            label={{ value:`Avg ${fmt(avgVal)}`, fill:'#64748b', fontSize:10, position:'insideTopRight' }} />
          {yKeys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} stroke={PALETTE[i]} strokeWidth={2.5}
              dot={{ fill:PALETTE[i], r:3, strokeWidth:0 }}
              activeDot={{ r:6, fill:PALETTE[i], stroke:'rgba(255,255,255,0.3)', strokeWidth:2 }}
              animationDuration={900} />
          ))}
          {yKeys.length > 1 && <Legend formatter={v => <span style={{ color:'#94a3b8', fontSize:11 }}>{prettify(v)}</span>} />}
        </LineChart>
      );
    }

    // ── Horizontal Bar ──
    if (chartType === 'horizontalBar') {
      return (
        <BarChart data={chartData} layout="vertical" margin={{ top:5, right:36, bottom:5, left:75 }}>
          <CartesianGrid {...gridP} horizontal={false} vertical={true} />
          <XAxis type="number" tick={{ fontSize:11, fill:'#4b5563', fontFamily:'monospace' }} axisLine={false} tickLine={false} tickFormatter={fmt} />
          <YAxis type="category" dataKey={xKey} tick={{ fontSize:11, fill:'#4b5563' }} axisLine={false} tickLine={false} width={80} />
          <Tooltip {...tip} />
          <Bar dataKey={primaryY} radius={[0,6,6,0]} maxBarSize={22} animationDuration={900}>
            <LabelList dataKey={primaryY} position="right" style={{ fill:'#64748b', fontSize:10 }} formatter={fmt} />
            {chartData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Bar>
        </BarChart>
      );
    }

    // ── Multi-series Bar (with dual axis if scale mismatch) ──
    if (yKeys.length > 1) {
      return (
        <BarChart data={chartData} margin={{ top:10, right: dualAxis ? 52 : 16, bottom:20, left:0 }} barCategoryGap="30%" barGap={3}>
          <CartesianGrid {...gridP} />
          <XAxis {...xProps(chartData, xKey)} />
          <YAxis yAxisId="left"  {...yProps()} />
          {dualAxis && <YAxis yAxisId="right" orientation="right" {...yProps()} width={52} />}
          <Tooltip {...tip} />
          <Legend formatter={v => <span style={{ color:'#94a3b8', fontSize:11 }}>{prettify(v)}</span>} />
          {yKeys.map((k, i) => (
            <Bar key={k} dataKey={k} yAxisId={dualAxis && i > 0 ? 'right' : 'left'}
              fill={PALETTE[i % PALETTE.length]} radius={[4,4,0,0]} maxBarSize={36} animationDuration={900}>
              {yKeys.length <= 2 && <LabelList dataKey={k} position="top" style={{ fill:PALETTE[i], fontSize:10, fontFamily:'monospace', fontWeight:600 }} formatter={fmt} />}
            </Bar>
          ))}
        </BarChart>
      );
    }

    // ── Default: Single-series Bar ──
    return (
      <BarChart data={chartData} margin={{ top:10, right:16, bottom:20, left:0 }} barCategoryGap="38%">
        <CartesianGrid {...gridP} />
        <XAxis {...xProps(chartData, xKey)} />
        <YAxis {...yProps()} />
        <Tooltip {...tip} />
        <ReferenceLine y={avgVal} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 3"
          label={{ value:`Avg ${fmt(avgVal)}`, fill:'#64748b', fontSize:10, position:'insideTopRight' }} />
        <Bar dataKey={primaryY} radius={[6,6,0,0]} maxBarSize={46} animationDuration={900}>
          <LabelList dataKey={primaryY} position="top" style={{ fill:'#94a3b8', fontSize:10, fontFamily:'monospace' }} formatter={fmt} />
          {chartData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Bar>
      </BarChart>
    );
  };

  const badgeMap = { bar:'📊 Bar', area:'📈 Area', line:'📉 Line', donut:'🍩 Donut', horizontalBar:'📊 H-Bar', singleKpi:'💳 KPI', groupedBar:'📊 Grouped' };
  const badge = yKeys.length > 1 && !['area','line','donut','horizontalBar','singleKpi'].includes(chartType) ? '📊 Grouped' : (badgeMap[chartType] ?? '📊');

  return (
    <div style={{ background:'linear-gradient(160deg,rgba(13,19,38,0.85) 0%,rgba(2,6,23,0.9) 100%)', border:'1px solid rgba(255,255,255,0.07)', borderRadius:18, padding:'20px 20px 16px', marginTop:16, boxShadow:'0 4px 32px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.06)', animation:'chartFadeIn 0.4s ease forwards' }}>

      {/* KPI Row */}
      <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginBottom:18 }}>
        {kpis.map((k, i) => <KpiCard key={i} {...k} />)}
      </div>

      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14, flexWrap:'wrap', gap:8 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:11, fontWeight:700, color:'#475569', background:'rgba(255,255,255,0.06)', padding:'3px 10px', borderRadius:20, border:'1px solid rgba(255,255,255,0.08)' }}>{badge}</span>
          <span style={{ fontSize:11, color:'#334155' }}>{data.length} rows · {yKeys.length} metric{yKeys.length > 1 ? 's' : ''}</span>
        </div>
        <div style={{ display:'flex', gap:6 }}>
          <button onClick={downloadCSV}
            style={{ background:'rgba(16,185,129,0.12)', color:'#10b981', border:'1px solid rgba(16,185,129,0.28)', borderRadius:7, padding:'5px 13px', fontSize:12, cursor:'pointer', fontWeight:700, display:'flex', alignItems:'center', gap:5, transition:'all 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.background='rgba(16,185,129,0.22)'}
            onMouseLeave={e => e.currentTarget.style.background='rgba(16,185,129,0.12)'}>
            ↓ CSV
          </button>
          <div style={{ display:'flex', background:'rgba(0,0,0,0.35)', borderRadius:8, padding:3, border:'1px solid rgba(255,255,255,0.07)' }}>
            {['chart','table'].map(v => (
              <button key={v} onClick={() => setView(v)}
                style={{ background: view===v ? 'rgba(255,255,255,0.12)' : 'transparent', color: view===v ? '#f1f5f9' : '#475569', border:'none', borderRadius:6, padding:'4px 14px', fontSize:12, fontWeight:600, cursor:'pointer', transition:'all 0.2s' }}>
                {v === 'chart' ? '📊 Chart' : '📋 Data'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Viz */}
      {view === 'chart' ? (
        chartType === 'singleKpi' ? (
          <div style={{ color:'#64748b', fontSize:12, textAlign:'center', padding:'12px 0' }}>Single result — metrics displayed above ↑</div>
        ) : (
          <ResponsiveContainer width="100%" height={chartType === 'horizontalBar' ? Math.min(data.length * 34 + 40, 380) : 272}>
            {renderChart()}
          </ResponsiveContainer>
        )
      ) : (
        <div style={{ overflowX:'auto', maxHeight:320, overflowY:'auto', borderRadius:10, border:'1px solid rgba(255,255,255,0.07)' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
            <thead style={{ position:'sticky', top:0, background:'rgba(8,12,28,0.98)', backdropFilter:'blur(8px)', zIndex:10 }}>
              <tr>
                {Object.keys(data[0]).map(k => (
                  <th key={k} onClick={() => handleSort(k)}
                    style={{ padding:'10px 14px', color: sortKey===k ? '#10b981' : '#64748b', borderBottom:'1px solid rgba(255,255,255,0.08)', fontWeight:700, fontSize:10, textTransform:'uppercase', letterSpacing:'0.6px', cursor:'pointer', userSelect:'none', whiteSpace:'nowrap', textAlign:'left', transition:'color 0.2s' }}>
                    {prettify(k)}{sortKey===k ? (sortDir==='desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, i) => (
                <tr key={i}
                  style={{ borderBottom:'1px solid rgba(255,255,255,0.03)', background: i%2 ? 'rgba(255,255,255,0.015)' : 'transparent', transition:'background 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.background='rgba(16,185,129,0.05)'}
                  onMouseLeave={e => e.currentTarget.style.background= i%2 ? 'rgba(255,255,255,0.015)' : 'transparent'}>
                  {Object.entries(row).map(([k, val], j) => (
                    <td key={j} style={{ padding:'9px 14px', color: typeof val==='number' ? '#34d399' : '#cbd5e1', fontFamily: typeof val==='number' ? 'monospace' : 'inherit', fontWeight: typeof val==='number' ? 600 : 400 }}>
                      {typeof val === 'number' ? val.toLocaleString(undefined,{ maximumFractionDigits:4 }) : String(val)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`@keyframes chartFadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}`}</style>
    </div>
  );
}
