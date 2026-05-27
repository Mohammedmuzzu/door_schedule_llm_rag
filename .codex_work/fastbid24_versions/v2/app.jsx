/* eslint-disable no-undef */
/* ====================================================================
   FastBid24 Door Analyzer — single-file app
   Real PDF text extraction (pdf.js) + OpenAI extraction
   ==================================================================== */
const { useState, useEffect, useRef, useMemo, useCallback, Fragment } = React;

/* ---------- Icons (lucide-derived, compact) ---------- */
const ICONS = {
  'door': 'p:M13 4h3a2 2 0 0 1 2 2v14|p:M2 20h20|p:M13 20V4a1 1 0 0 0-.5-.86l-5-2.5A1 1 0 0 0 6 1.5V20|d:9,12,0.8',
  'upload': 'p:M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4|p:M17 8 12 3 7 8|p:M12 3v12',
  'file-text': 'p:M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z|p:M14 2v6h6|p:M16 13H8|p:M16 17H8',
  'layout-grid': 'r:3,3,7,7|r:14,3,7,7|r:14,14,7,7|r:3,14,7,7',
  'library': 'p:M16 6l4 14|p:M12 6v14|p:M8 8v12|p:M4 4v16',
  'link': 'p:M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71|p:M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71',
  'file-check': 'p:M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z|p:M14 2v6h6|p:m9 15 2 2 4-4',
  'send': 'p:m22 2-7 20-4-9-9-4Z|p:M22 2 11 13',
  'settings': 'p:M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z|c:12,12,3',
  'home': 'p:m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z|p:M9 22V12h6v10',
  'chevron-right': 'p:m9 18 6-6-6-6',
  'chevron-down': 'p:m6 9 6 6 6-6',
  'check': 'p:M20 6 9 17l-5-5',
  'x': 'p:M18 6 6 18|p:M6 6l12 12',
  'plus': 'p:M12 5v14|p:M5 12h14',
  'trash': 'p:M3 6h18|p:m19 6-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6|p:M10 11v6|p:M14 11v6',
  'edit': 'p:M12 20h9|p:M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z',
  'search': 'c:11,11,8|p:m21 21-4.35-4.35',
  'filter': 'p:M22 3H2l8 9.46V19l4 2v-8.54L22 3z',
  'download': 'p:M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4|p:m7 10 5 5 5-5|p:M12 15V3',
  'print': 'p:M6 9V2h12v7|p:M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2|r:6,14,12,8',
  'copy': 'r:9,9,13,13|p:M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1',
  'loader': 'p:M21 12a9 9 0 1 1-6.219-8.56',
  'sparkles': 'p:m12 3-1.9 5.8a2 2 0 0 1-1.287 1.288L3 12l5.8 1.9a2 2 0 0 1 1.288 1.287L12 21l1.9-5.8a2 2 0 0 1 1.287-1.288L21 12l-5.8-1.9a2 2 0 0 1-1.288-1.287Z',
  'more': 'c:12,12,1|c:12,5,1|c:12,19,1',
  'bell': 'p:M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9|p:M10.3 21a1.94 1.94 0 0 0 3.4 0',
  'circle-check': 'c:12,12,10|p:m9 12 2 2 4-4',
  'circle-x': 'c:12,12,10|p:m15 9-6 6|p:m9 9 6 6',
  'circle-dot': 'c:12,12,10|d:12,12,1',
  'alert': 'p:M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z|p:M12 9v4|p:M12 17h.01',
  'sun': 'c:12,12,4|p:M12 2v2|p:M12 20v2|p:m4.93 4.93 1.41 1.41|p:m17.66 17.66 1.41 1.41|p:M2 12h2|p:M20 12h2|p:m6.34 17.66-1.41 1.41|p:m19.07 4.93-1.41 1.41',
  'moon': 'p:M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  'sliders': 'p:M4 21V14|p:M4 10V3|p:M12 21v-9|p:M12 8V3|p:M20 21v-5|p:M20 12V3|p:M1 14h6|p:M9 8h6|p:M17 16h6',
  'arrow-right': 'p:M5 12h14|p:m12 5 7 7-7 7',
  'arrow-left': 'p:M19 12H5|p:m12 19-7-7 7-7',
  'package': 'p:m7.5 4.27 9 5.15|p:M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z|p:m3.3 7 8.7 5 8.7-5|p:M12 22V12',
  'info': 'c:12,12,10|p:M12 16v-4|p:M12 8h.01',
  'mail': 'r:2,4,20,16|p:m22 7-10 5L2 7',
  'refresh': 'p:M23 4v6h-6|p:M1 20v-6h6|p:M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15',
  'key': 'c:7.5,15.5,5.5|p:m21 2-9.6 9.6|p:m15.5 7.5 3 3L22 7l-3-3',
  'shield': 'p:M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  'briefcase': 'r:2,7,20,14|p:M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16',
  'building': 'r:4,2,16,20|p:M9 22v-4h6v4',
  'open': 'p:M15 3h6v6|p:M10 14 21 3|p:M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5',
  'inbox': 'p:M22 12h-6l-2 3h-4l-2-3H2|p:M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
};
const Icon = ({ name, size = 16, ...rest }) => {
  const def = ICONS[name];
  if (!def) return <svg width={size} height={size}/>;
  const parts = def.split('|').map((s, i) => {
    if (s.startsWith('r:')) { const [x,y,w,h] = s.slice(2).split(',').map(Number); return <rect key={i} x={x} y={y} width={w} height={h} rx="1"/>; }
    if (s.startsWith('c:')) { const [cx,cy,r] = s.slice(2).split(',').map(Number); return <circle key={i} cx={cx} cy={cy} r={r}/>; }
    if (s.startsWith('d:')) { const [cx,cy,r] = s.slice(2).split(',').map(Number); return <circle key={i} cx={cx} cy={cy} r={r} fill="currentColor" stroke="none"/>; }
    return <path key={i} d={s.slice(2)}/>;
  });
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...rest}>{parts}</svg>
  );
};

/* ---------- Helpers ---------- */
const fmt = (n) => n == null || isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
const fmt0 = (n) => n == null || isNaN(n) ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
const setTotal = (set) => (set?.items || []).reduce((s, i) => s + (i.qty || 0) * (i.unitPrice || 0), 0);

function useLocal(key, initial) {
  const [v, setV] = useState(() => {
    try { const raw = localStorage.getItem(key); return raw == null ? initial : JSON.parse(raw); } catch { return initial; }
  });
  useEffect(() => { try { localStorage.setItem(key, JSON.stringify(v)); } catch {} }, [key, v]);
  return [v, setV];
}

/* ---------- IndexedDB analysis history ---------- */
const DB_NAME = 'fastbid24';
const DB_VERSION = 1;
const STORE_ANALYSIS = 'analyses';

function openDB() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) return reject(new Error('IndexedDB not available'));
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_ANALYSIS)) {
        const store = db.createObjectStore(STORE_ANALYSIS, { keyPath: 'id' });
        store.createIndex('createdAt', 'createdAt', { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function dbPut(record) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ANALYSIS, 'readwrite');
    tx.objectStore(STORE_ANALYSIS).put(record);
    tx.oncomplete = () => resolve(record);
    tx.onerror = () => reject(tx.error);
  });
}
async function dbGet(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ANALYSIS, 'readonly');
    const req = tx.objectStore(STORE_ANALYSIS).get(id);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}
async function dbList() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ANALYSIS, 'readonly');
    const req = tx.objectStore(STORE_ANALYSIS).getAll();
    req.onsuccess = () => {
      const arr = req.result || [];
      arr.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
      resolve(arr);
    };
    req.onerror = () => reject(req.error);
  });
}
async function dbDelete(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ANALYSIS, 'readwrite');
    tx.objectStore(STORE_ANALYSIS).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/* ---------- Excel exporter (XLSX with cell styling via xlsx-js-style) ---------- */
const XL_PALETTE = {
  // Brand
  NAVY:   '0F172A',  // titles
  BRAND:  '2F68F5',  // section headers / accents
  BRAND_DARK: '1E4FDB',
  SLATE:  '475569',  // column headers
  // Status
  RED:    'DC2626',  RED_BG:    'FEE2E2',
  AMBER:  'B45309',  AMBER_BG:  'FEF3C7',
  GREEN:  '047857',  GREEN_BG:  'DCFCE7',
  BLUE:   '1E40AF',  BLUE_BG:   'DBEAFE',
  // Neutral
  WHITE:  'FFFFFF',
  ZEBRA:  'F8FAFC',
  GRID:   'E2E8F0',
  TEXT:   '0F172A',
  MUTED:  '64748B',
};
const XL = {
  title:    { font:{ name:'Calibri', sz:18, bold:true, color:{rgb:XL_PALETTE.WHITE} }, fill:{ fgColor:{rgb:XL_PALETTE.NAVY} }, alignment:{ vertical:'center', horizontal:'left' } },
  subtitle: { font:{ name:'Calibri', sz:10, color:{rgb:XL_PALETTE.WHITE} }, fill:{ fgColor:{rgb:XL_PALETTE.NAVY} }, alignment:{ vertical:'center', horizontal:'left' } },
  section:  { font:{ name:'Calibri', sz:11, bold:true, color:{rgb:XL_PALETTE.WHITE} }, fill:{ fgColor:{rgb:XL_PALETTE.BRAND} }, alignment:{ vertical:'center', horizontal:'left' } },
  header:   { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.WHITE} }, fill:{ fgColor:{rgb:XL_PALETTE.SLATE} }, alignment:{ vertical:'center', horizontal:'left', wrapText:true }, border:{ bottom:{ style:'medium', color:{rgb:XL_PALETTE.NAVY} } } },
  cell:     { font:{ name:'Calibri', sz:10, color:{rgb:XL_PALETTE.TEXT} }, alignment:{ vertical:'top', wrapText:true }, border:{ bottom:{ style:'hair', color:{rgb:XL_PALETTE.GRID} }, right:{ style:'hair', color:{rgb:XL_PALETTE.GRID} } } },
  zebra:    { font:{ name:'Calibri', sz:10, color:{rgb:XL_PALETTE.TEXT} }, alignment:{ vertical:'top', wrapText:true }, fill:{ fgColor:{rgb:XL_PALETTE.ZEBRA} }, border:{ bottom:{ style:'hair', color:{rgb:XL_PALETTE.GRID} }, right:{ style:'hair', color:{rgb:XL_PALETTE.GRID} } } },
  bold:     { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.TEXT} }, alignment:{ vertical:'top' } },
  mono:     { font:{ name:'Consolas', sz:10, color:{rgb:XL_PALETTE.TEXT} }, alignment:{ vertical:'top' } },
  label:    { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.MUTED} }, alignment:{ vertical:'top' } },
  metricVal:{ font:{ name:'Calibri', sz:14, bold:true, color:{rgb:XL_PALETTE.TEXT} }, alignment:{ vertical:'center' } },
  high:     { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.RED} }, fill:{ fgColor:{rgb:XL_PALETTE.RED_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  medium:   { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.AMBER} }, fill:{ fgColor:{rgb:XL_PALETTE.AMBER_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  low:      { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.GREEN} }, fill:{ fgColor:{rgb:XL_PALETTE.GREEN_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  okStatus: { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.GREEN} }, fill:{ fgColor:{rgb:XL_PALETTE.GREEN_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  badStatus:{ font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.RED} }, fill:{ fgColor:{rgb:XL_PALETTE.RED_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  warn:     { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.AMBER} }, fill:{ fgColor:{rgb:XL_PALETTE.AMBER_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
  chip:     { font:{ name:'Calibri', sz:10, bold:true, color:{rgb:XL_PALETTE.BLUE} }, fill:{ fgColor:{rgb:XL_PALETTE.BLUE_BG} }, alignment:{ vertical:'center', horizontal:'center' } },
};

function styleForLevel(lvl) {
  const v = String(lvl || '').toLowerCase();
  if (v === 'high') return XL.high;
  if (v === 'medium' || v === 'med') return XL.medium;
  if (v === 'low') return XL.low;
  return XL.cell;
}
function styleForMappingStatus(s) {
  if (!s) return XL.cell;
  if (s === 'OK') return XL.okStatus;
  if (s.startsWith('FAILED')) return XL.badStatus;
  if (s === 'NO_HW_SET') return XL.warn;
  return XL.cell;
}
function styleForHWStatus(s) {
  const v = String(s || '').toLowerCase();
  if (v === 'complete') return XL.okStatus;
  if (v === 'missing') return XL.badStatus;
  if (v === 'incomplete' || v.includes('review') || v === 'unclear') return XL.warn;
  return XL.cell;
}

/* Infer a category for an RFI when the model didn't return one — keyword-based bucket. */
function inferCategoryFromText(text) {
  const t = String(text || '').toLowerCase();
  if (/hardware set|hw set|missing.*set|no hardware/i.test(t)) return 'Hardware mapping';
  if (/electrified|access control|card reader|maglock|electric strike|EAC|low.?voltage/i.test(t)) return 'Access control / electrified';
  if (/panic|exit device|egress/i.test(t)) return 'Egress / panic hardware';
  if (/fire.?rated|UL|smoke gasket|self.?closing|positive latching/i.test(t)) return 'Fire / smoke rating';
  if (/storefront|aluminum|curtain wall|exterior|threshold|weather/i.test(t)) return 'Exterior / storefront';
  if (/operator|automatic|ADA|closer/i.test(t)) return 'ADA / operator';
  if (/finish/i.test(t)) return 'Finish coordination';
  if (/lead time|long.?lead|substitution|specialty/i.test(t)) return 'Supply / lead-time';
  return 'General coordination';
}

function exportAnalysisToExcel({ analysis, project, tweaks }) {
  if (!window.XLSX) { alert('Excel library failed to load. Refresh the page and try again.'); return; }
  const XLSX = window.XLSX;
  const wb = XLSX.utils.book_new();
  const ps = analysis.project_summary || {};
  const today = new Date().toISOString().slice(0, 10);

  // Helper — build a sheet from a structured spec:
  //   spec.title       : optional title row text
  //   spec.subtitle    : optional subtitle row text
  //   spec.cols        : [{ key, label, width }]
  //   spec.rows        : array of objects keyed to cols
  //   spec.cellStyle   : (row, colKey, value) => style | null  (overrides default)
  //   spec.cols + sections : array of { header, cols, rows } to support multi-section sheets
  //   spec.freeze      : number of frozen top rows
  function buildSheet(spec) {
    const ws = {};
    const merges = [];
    let r = 0;
    const setCell = (R, C, val, style, type) => {
      const addr = XLSX.utils.encode_cell({ r: R, c: C });
      const cell = { v: val ?? '' };
      if (type) cell.t = type;
      else if (typeof val === 'number') cell.t = 'n';
      else cell.t = 's';
      if (style) cell.s = style;
      ws[addr] = cell;
    };
    const rowHeight = (h) => {
      if (!ws['!rows']) ws['!rows'] = [];
      ws['!rows'][r] = { hpt: h };
    };

    const widthArr = [];
    const writeCols = (cols) => cols.forEach((c, i) => { widthArr[i] = Math.max(widthArr[i] || 8, c.width || 14); });

    // Title bar
    if (spec.title) {
      const cols = spec.cols || (spec.sections?.[0]?.cols ?? []);
      const span = Math.max(1, cols.length || 1);
      for (let c = 0; c < span; c++) setCell(r, c, c === 0 ? spec.title : '', XL.title);
      if (span > 1) merges.push({ s: { r, c: 0 }, e: { r, c: span - 1 } });
      rowHeight(28);
      r++;
      if (spec.subtitle) {
        for (let c = 0; c < span; c++) setCell(r, c, c === 0 ? spec.subtitle : '', XL.subtitle);
        if (span > 1) merges.push({ s: { r, c: 0 }, e: { r, c: span - 1 } });
        rowHeight(18);
        r++;
      }
      r++; // blank line
    }

    const renderTable = (cols, rows, cellStyleFn, sectionTitle) => {
      if (sectionTitle) {
        const span = Math.max(1, cols.length);
        for (let c = 0; c < span; c++) setCell(r, c, c === 0 ? sectionTitle : '', XL.section);
        if (span > 1) merges.push({ s: { r, c: 0 }, e: { r, c: span - 1 } });
        rowHeight(22);
        r++;
      }
      // header row
      cols.forEach((col, c) => setCell(r, c, col.label, XL.header));
      rowHeight(22);
      r++;
      // data rows
      rows.forEach((row, i) => {
        cols.forEach((col, c) => {
          const v = row[col.key];
          const override = cellStyleFn ? cellStyleFn(row, col.key, v) : null;
          const baseStyle = i % 2 === 0 ? XL.cell : XL.zebra;
          const style = override
            ? { ...baseStyle, ...override, alignment: override.alignment || baseStyle.alignment }
            : baseStyle;
          setCell(r, c, v ?? '', style);
        });
        r++;
      });
      writeCols(cols);
      r++; // blank line after each table
    };

    if (spec.cols && spec.rows) {
      renderTable(spec.cols, spec.rows, spec.cellStyle);
    }
    if (spec.sections) {
      spec.sections.forEach(sec => renderTable(sec.cols, sec.rows, sec.cellStyle, sec.header));
    }
    if (spec.keyValue) {
      // key-value layout for dashboard etc.
      spec.keyValue.forEach(kv => {
        if (kv.section) {
          for (let c = 0; c < 4; c++) setCell(r, c, c === 0 ? kv.section : '', XL.section);
          merges.push({ s: { r, c: 0 }, e: { r, c: 3 } });
          rowHeight(22);
          r++;
        } else if (kv.spacer) {
          r++;
        } else {
          setCell(r, 0, kv.label, XL.label);
          setCell(r, 1, kv.value, kv.style || XL.cell);
          if (kv.fullWidth) {
            merges.push({ s: { r, c: 1 }, e: { r, c: 3 } });
          }
          rowHeight(kv.height || 18);
          r++;
        }
      });
      widthArr[0] = 26; widthArr[1] = 30; widthArr[2] = 20; widthArr[3] = 20;
    }

    ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: Math.max(r - 1, 0), c: Math.max(widthArr.length - 1, 0) } });
    ws['!cols'] = widthArr.map(w => ({ wch: Math.min(Math.max(w, 8), 64) }));
    if (merges.length) ws['!merges'] = merges;
    if (spec.freeze) ws['!freeze'] = { xSplit: 0, ySplit: spec.freeze };
    return ws;
  }

  // ---------- 1) DASHBOARD ----------
  const dashSheet = buildSheet({
    title: 'FastBid24 — Senior Estimator Analysis',
    subtitle: `${ps.project_name || project.name || 'Project'} · Analysis ${project.proposalId || ''} · Generated ${today}`,
    keyValue: [
      { section: 'PROJECT' },
      { label: 'Project Name', value: ps.project_name || project.name || '', style: XL.bold },
      { label: 'Project Number', value: ps.project_number || '' },
      { label: 'Architect', value: ps.architect || '' },
      { label: 'Address', value: ps.address || '' },
      { label: 'Drawing Reference', value: ps.drawing || '' },
      { label: 'Scope', value: ps.scope_type || tweaks.scope || '', style: XL.chip },
      { label: 'Date', value: today },
      { spacer: true },
      { section: 'EXTRACTION' },
      { label: 'Status', value: analysis.status || 'OK', style: analysis.status === 'REVIEW_REQUIRED' ? XL.warn : XL.okStatus },
      { label: 'Workbook Completeness', value: (analysis.qa?.extraction_complete === false) ? 'INCOMPLETE — re-run or review manually' : 'Complete', style: (analysis.qa?.extraction_complete === false) ? XL.warn : XL.okStatus },
      { label: 'Extraction Failures', value: analysis.qa?.extraction_failures?.length || 0, style: (analysis.qa?.extraction_failures?.length || 0) > 0 ? XL.warn : XL.cell },
      { label: 'Reason', value: analysis.reason || '—' },
      { label: 'PDF Type', value: analysis.qa?.pdf_type || 'TEXT_BASED_PDF' },
      { label: 'Pages Rendered', value: analysis.qa?.pages_rendered || 0 },
      { label: 'Regions Detected', value: analysis.qa?.regions_detected?.length || 0 },
      { label: 'Crops Processed', value: analysis.qa?.crops?.length || 0 },
      { label: 'Failed Mappings', value: analysis.qa?.validation?.failedMappings?.length || 0 },
      { spacer: true },
      { section: 'SUMMARY METRICS' },
      { label: 'Total Openings', value: ps.total_openings_found || analysis.door_analysis?.length || 0, style: XL.metricVal, height: 24 },
      { label: 'Hardware Sets Referenced', value: ps.total_hardware_sets_referenced || 0, style: XL.metricVal, height: 24 },
      { label: 'HW Sets Missing/Unclear', value: ps.hardware_sets_missing_or_unclear || 0, style: (ps.hardware_sets_missing_or_unclear || 0) > 0 ? XL.warn : XL.cell, height: 24 },
      { label: 'High Risk Openings', value: ps.high_risk_openings || 0, style: (ps.high_risk_openings || 0) > 0 ? XL.high : XL.cell, height: 24 },
      { label: 'Medium Risk Openings', value: ps.medium_risk_openings || 0, style: (ps.medium_risk_openings || 0) > 0 ? XL.medium : XL.cell, height: 24 },
      { label: 'Low Risk Openings', value: ps.low_risk_openings || 0, style: XL.low, height: 24 },
      { label: 'Access Control Openings', value: ps.access_control_openings || 0 },
      { label: 'Exterior Openings', value: ps.exterior_openings || 0 },
      { label: 'Fire-rated Openings', value: ps.fire_rated_openings || 0 },
      { label: 'Overall Bid Risk', value: ps.overall_bid_risk || '—', style: styleForLevel(ps.overall_bid_risk) },
      { spacer: true },
      { section: 'ESTIMATOR OVERVIEW' },
      { label: '', value: ps.estimator_summary || '—', fullWidth: true, height: 60 },
    ],
  });
  XLSX.utils.book_append_sheet(wb, dashSheet, 'Dashboard');

  // ---------- 2) DOOR SCHEDULE ----------
  const doorCols = [
    { key: 'mark', label: 'Mark', width: 10 },
    { key: 'room', label: 'Room / Location', width: 26 },
    { key: 'type', label: 'Type', width: 8 },
    { key: 'opening', label: 'Opening', width: 10 },
    { key: 'intext', label: 'Int/Ext', width: 8 },
    { key: 'w', label: 'W', width: 8 },
    { key: 'h', label: 'H', width: 8 },
    { key: 'thk', label: 'Thk', width: 8 },
    { key: 'mat', label: 'Material', width: 14 },
    { key: 'fin', label: 'Finish', width: 10 },
    { key: 'glaze', label: 'Glazing', width: 12 },
    { key: 'frType', label: 'Frame Type', width: 10 },
    { key: 'frMat', label: 'Frame Mat', width: 12 },
    { key: 'frFin', label: 'Frame Fin', width: 10 },
    { key: 'fire', label: 'Fire', width: 8 },
    { key: 'hwset', label: 'HW Set', width: 10 },
    { key: 'risk', label: 'Risk', width: 9 },
    { key: 'install', label: 'Install', width: 9 },
    { key: 'hwStatus', label: 'HW Status', width: 12 },
    { key: 'rfi', label: 'RFI?', width: 6 },
    { key: 'special', label: 'Special Conditions', width: 24 },
    { key: 'remarks', label: 'Remarks', width: 24 },
    { key: 'issues', label: 'Issues', width: 24 },
    { key: 'recs', label: 'Recommendations', width: 24 },
    { key: 'conf', label: 'Conf.', width: 7 },
  ];
  const doorRows = (analysis.door_analysis || []).map(d => ({
    mark: d.mark || '', room: d.room_or_location || '', type: d.door_type || '',
    opening: d.opening_type || '', intext: d.interior_or_exterior || '',
    w: d.size?.width || '', h: d.size?.height || '', thk: d.size?.thickness || '',
    mat: d.door_material || '', fin: d.door_finish || '', glaze: d.glazing || '',
    frType: d.frame_type || '', frMat: d.frame_material || '', frFin: d.frame_finish || '',
    fire: d.fire_rating || '', hwset: d.hardware_set || '',
    risk: d.risk_level || '', install: d.install_complexity || '', hwStatus: d.hardware_status || '',
    rfi: d.rfi_required ? 'Yes' : '', special: (d.special_conditions || []).join(', '),
    remarks: (d.remarks || []).join(' · '), issues: (d.issues || []).join(' · '),
    recs: (d.recommendations || []).join(' · '),
    conf: Math.round((d.confidence ?? 1) * 100) + '%',
  }));
  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'Door Schedule',
    subtitle: `${doorRows.length} opening(s)`,
    cols: doorCols, rows: doorRows,
    cellStyle: (row, key) => {
      if (key === 'risk' || key === 'install') return styleForLevel(row[key]);
      if (key === 'hwStatus') return styleForHWStatus(row[key]);
      if (key === 'rfi' && row[key] === 'Yes') return XL.warn;
      if (key === 'fire' && row[key]) return XL.chip;
      return null;
    },
    freeze: 3,
  }), 'Door Schedule');

  // ---------- 3) HARDWARE SETS ----------
  const setCols = [
    { key: 'id', label: 'Set ID', width: 10 },
    { key: 'status', label: 'Status', width: 12 },
    { key: 'doorCount', label: '# Doors', width: 9 },
    { key: 'itemCount', label: '# Items', width: 9 },
    { key: 'refs', label: 'Referenced by Doors', width: 28 },
    { key: 'coord', label: 'Special Coordination', width: 28 },
    { key: 'missing', label: 'Missing / Unclear', width: 28 },
    { key: 'note', label: 'Estimator Note', width: 28 },
    { key: 'conf', label: 'Conf.', width: 7 },
  ];
  const setRows = (analysis.hardware_set_review || []).map(s => ({
    id: s.hardware_set || '',
    status: s.status || '',
    doorCount: (s.referenced_by_doors || []).length,
    itemCount: (s.items || []).length,
    refs: (s.referenced_by_doors || []).join(', '),
    coord: (s.special_coordination || []).join(' · '),
    missing: (s.missing_or_unclear_items || []).join(' · '),
    note: s.estimator_note || '',
    conf: Math.round((s.confidence ?? 1) * 100) + '%',
  }));
  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'Hardware Sets',
    subtitle: `${setRows.length} set(s)`,
    cols: setCols, rows: setRows,
    cellStyle: (row, key) => key === 'status' ? styleForHWStatus(row[key]) : null,
    freeze: 3,
  }), 'Hardware Sets');

  // ---------- 4) HARDWARE ITEMS (grouped by set, each set as a section) ----------
  const itemCols = [
    { key: 'idx', label: '#', width: 5 },
    { key: 'qty', label: 'Qty', width: 6 },
    { key: 'unit', label: 'Unit', width: 7 },
    { key: 'desc', label: 'Description', width: 36 },
    { key: 'part', label: 'Part Number', width: 18 },
    { key: 'mfr', label: 'Manufacturer', width: 18 },
    { key: 'finish', label: 'Finish', width: 12 },
  ];
  const itemSections = (analysis.hardware_set_review || []).map(s => {
    const items = s.items || [];
    return {
      header: `${fmtSetId(s.hardware_set)} · ${items.length} item(s) · referenced by ${(s.referenced_by_doors||[]).length} door(s): ${(s.referenced_by_doors||[]).join(', ') || '—'}`,
      cols: itemCols,
      rows: items.map((it, i) => ({
        idx: i + 1,
        qty: it.qty ?? '',
        unit: it.unit || '',
        desc: it.desc || '',
        part: it.part || '',
        mfr: it.mfr || '',
        finish: it.finish || '',
      })),
    };
  });
  const itemSheet = buildSheet({
    title: 'Hardware Items',
    subtitle: 'Line items for each hardware set — qty / description / part / mfr / finish',
    sections: itemSections.length ? itemSections : [{ header: 'No hardware items extracted', cols: itemCols, rows: [] }],
  });
  XLSX.utils.book_append_sheet(wb, itemSheet, 'Hardware Items');

  // ---------- 5) DOOR-HARDWARE MAPPING (one row per door per item) ----------
  const mapCols = [
    { key: 'mark', label: 'Door Mark', width: 10 },
    { key: 'hw', label: 'HW Set', width: 9 },
    { key: 'item_no', label: 'Item #', width: 6 },
    { key: 'qty', label: 'Qty', width: 6 },
    { key: 'desc', label: 'Description', width: 32 },
    { key: 'part', label: 'Catalog #', width: 16 },
    { key: 'mfr', label: 'Manufacturer', width: 16 },
    { key: 'finish', label: 'Finish', width: 10 },
    { key: 'notes', label: 'Notes', width: 18 },
    { key: 'status', label: 'Mapping Status', width: 24 },
    { key: 'page', label: 'Src Page', width: 8 },
  ];
  const dhmRows = Array.isArray(analysis.door_hardware_mapping) && analysis.door_hardware_mapping.length
    ? analysis.door_hardware_mapping.map(m => ({
        mark: m.door_mark, hw: m.hardware_set || '—', item_no: m.item_no ?? '',
        qty: m.qty ?? '', desc: m.description || '', part: m.catalog_number || '',
        mfr: m.manufacturer || '', finish: m.finish || '', notes: m.notes || '',
        status: m.status || 'OK', page: m.source_page ?? '',
      }))
    : (analysis.door_analysis || []).flatMap(d => {
        const set = (analysis.hardware_set_review || []).find(s => s.hardware_set === d.hardware_set);
        const items = set?.items || [];
        if (!d.hardware_set) return [{ mark: d.mark, hw: '—', item_no: '', qty: '', desc: '(no hardware set assigned)', part: '', mfr: '', finish: '', notes: '', status: 'NO_HW_SET', page: '' }];
        if (!set) return [{ mark: d.mark, hw: d.hardware_set, item_no: '', qty: '', desc: '(hardware set not found in spec)', part: '', mfr: '', finish: '', notes: '', status: 'FAILED_EXTRACTION_REVIEW_REQUIRED', page: '' }];
        if (!items.length) return [{ mark: d.mark, hw: d.hardware_set, item_no: '', qty: '', desc: '(hardware set has no extracted items)', part: '', mfr: '', finish: '', notes: '', status: 'FAILED_EXTRACTION_REVIEW_REQUIRED', page: set.source_page ?? '' }];
        return items.map((it, i) => ({ mark: d.mark, hw: d.hardware_set, item_no: it.item_no ?? (i + 1), qty: it.qty ?? '', desc: it.desc || '', part: it.part || '', mfr: it.mfr || '', finish: it.finish || '', notes: it.notes || '', status: 'OK', page: it.source_page ?? '' }));
      });
  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'Door-Hardware Mapping',
    subtitle: `${dhmRows.length} mapping row(s) — one row per door per hardware item`,
    cols: mapCols, rows: dhmRows,
    cellStyle: (row, key) => key === 'status' ? styleForMappingStatus(row[key]) : null,
    freeze: 3,
  }), 'Door-Hardware Mapping');

  // ---------- 7) TAKEOFF ROLLUP ----------
  const counts = {};
  (analysis.door_analysis || []).forEach(d => { if (d.hardware_set) counts[d.hardware_set] = (counts[d.hardware_set] || 0) + 1; });
  const totalQtyByItem = new Map(); // item key → { qty, desc, part, mfr, finish, setIds: Set }
  (analysis.door_analysis || []).forEach(d => {
    const set = (analysis.hardware_set_review || []).find(s => s.hardware_set === d.hardware_set);
    (set?.items || []).forEach(it => {
      const key = (it.desc || '').toLowerCase() + '|' + (it.part || '').toLowerCase() + '|' + (it.finish || '').toLowerCase();
      const existing = totalQtyByItem.get(key) || { qty: 0, desc: it.desc || '', part: it.part || '', mfr: it.mfr || '', finish: it.finish || '', setIds: new Set() };
      existing.qty += (typeof it.qty === 'number' ? it.qty : (Number(it.qty) || 1));
      existing.setIds.add(d.hardware_set);
      totalQtyByItem.set(key, existing);
    });
  });
  const sumByMaterial = {}, sumByType = {}, sumByFire = {}, sumByRisk = {}, sumByExt = {};
  (analysis.door_analysis || []).forEach(d => {
    sumByMaterial[d.door_material || 'Unspecified'] = (sumByMaterial[d.door_material || 'Unspecified'] || 0) + 1;
    sumByType[d.door_type || 'Unspecified'] = (sumByType[d.door_type || 'Unspecified'] || 0) + 1;
    sumByFire[d.fire_rating || 'Not rated'] = (sumByFire[d.fire_rating || 'Not rated'] || 0) + 1;
    sumByRisk[d.risk_level || 'unknown'] = (sumByRisk[d.risk_level || 'unknown'] || 0) + 1;
    sumByExt[d.interior_or_exterior || 'Unspecified'] = (sumByExt[d.interior_or_exterior || 'Unspecified'] || 0) + 1;
  });
  const toRows = (obj, keyLabel) => Object.entries(obj).map(([k, v]) => ({ key: k, count: v })).sort((a, b) => b.count - a.count);

  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'Takeoff Rollup',
    subtitle: 'Quantities for ordering and check-totals',
    sections: [
      {
        header: 'TOTAL HARDWARE ITEM QUANTITY (rolled across all doors)',
        cols: [
          { key: 'qty', label: 'Total Qty', width: 10 },
          { key: 'desc', label: 'Description', width: 36 },
          { key: 'part', label: 'Part #', width: 18 },
          { key: 'mfr', label: 'Manufacturer', width: 18 },
          { key: 'finish', label: 'Finish', width: 10 },
          { key: 'sets', label: 'Used in HW Sets', width: 18 },
        ],
        rows: [...totalQtyByItem.values()].sort((a, b) => b.qty - a.qty).map(it => ({
          qty: it.qty, desc: it.desc, part: it.part, mfr: it.mfr, finish: it.finish,
          sets: [...it.setIds].join(', '),
        })),
      },
      { header: 'HARDWARE SET TAKEOFF', cols: [{ key: 'key', label: 'Set ID', width: 12 }, { key: 'count', label: 'Door Count', width: 12 }], rows: Object.entries(counts).map(([k, v]) => ({ key: k, count: v })).sort((a, b) => b.count - a.count) },
      { header: 'BY DOOR TYPE', cols: [{ key: 'key', label: 'Type', width: 18 }, { key: 'count', label: 'Count', width: 10 }], rows: toRows(sumByType) },
      { header: 'BY MATERIAL', cols: [{ key: 'key', label: 'Material', width: 24 }, { key: 'count', label: 'Count', width: 10 }], rows: toRows(sumByMaterial) },
      { header: 'BY FIRE RATING', cols: [{ key: 'key', label: 'Rating', width: 18 }, { key: 'count', label: 'Count', width: 10 }], rows: toRows(sumByFire) },
      { header: 'BY RISK LEVEL', cols: [{ key: 'key', label: 'Risk', width: 12 }, { key: 'count', label: 'Count', width: 10 }],
        rows: toRows(sumByRisk),
        cellStyle: (row, key) => key === 'key' ? styleForLevel(row.key) : null,
      },
      { header: 'INTERIOR vs EXTERIOR', cols: [{ key: 'key', label: 'Where', width: 18 }, { key: 'count', label: 'Count', width: 10 }], rows: toRows(sumByExt) },
    ],
  }), 'Takeoff Rollup');

  // ---------- 8) RFIs & COORDINATION ----------
  const rfiSections = [
    {
      header: `RFI LOG (${(analysis.rfi_log || []).length})`,
      cols: [
        { key: 'id', label: 'RFI #', width: 10 },
        { key: 'priority', label: 'Priority', width: 10 },
        { key: 'category', label: 'Category', width: 22 },
        { key: 'question', label: 'Issue / Question', width: 50 },
        { key: 'affected', label: 'Affected Doors', width: 24 },
        { key: 'recommendation', label: 'Recommendation', width: 40 },
        { key: 'status', label: 'Status', width: 12 },
        { key: 'source', label: 'Source', width: 18 },
      ],
      rows: (analysis.rfi_log || []).map((r, i) => ({
        id: 'RFI-' + String(i+1).padStart(3, '0'),
        priority: r.priority || '',
        category: r.category || inferCategoryFromText(r.question || r.reason || ''),
        question: r.question || '',
        affected: (r.affected_openings || []).join(', '),
        recommendation: r.recommendation || r.reason || '',
        status: r.status || 'Open',
        source: r.source || 'Senior estimator analysis',
      })),
      cellStyle: (row, key) => {
        if (key === 'priority') return styleForLevel(row[key]);
        if (key === 'status') return /closed|answered|resolved/i.test(row.status) ? XL.okStatus : XL.warn;
        return null;
      },
    },
    {
      header: `PROJECT RISKS (${(analysis.project_risks || []).length})`,
      cols: [
        { key: 'severity', label: 'Severity', width: 10 },
        { key: 'category', label: 'Category', width: 22 },
        { key: 'issue', label: 'Issue', width: 50 },
        { key: 'affected', label: 'Affected Doors', width: 22 },
        { key: 'rec', label: 'Recommendation', width: 50 },
      ],
      rows: (analysis.project_risks || []).map(r => ({
        severity: r.severity || '', category: r.category || '', issue: r.issue || '',
        affected: (r.affected_openings || []).join(', '), rec: r.recommendation || '',
      })),
      cellStyle: (row, key) => key === 'severity' ? styleForLevel(row[key]) : null,
    },
    {
      header: 'BID RECOMMENDATIONS & COORDINATION',
      cols: [
        { key: 'cat', label: 'Category', width: 26 },
        { key: 'item', label: 'Item', width: 70 },
      ],
      rows: ['supply_only_notes', 'installation_only_notes', 'supply_and_installation_notes', 'exclusions_to_consider', 'allowances_to_consider', 'coordination_items'].flatMap(k =>
        (analysis.bid_recommendations?.[k] || []).map(item => ({ cat: k, item }))
      ),
    },
  ];
  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'RFIs & Coordination',
    subtitle: 'Outstanding questions, risks, and bid-level guidance',
    sections: rfiSections,
  }), 'RFIs & Coordination');

  // ---------- 9) SOURCE NOTES ----------
  XLSX.utils.book_append_sheet(wb, buildSheet({
    title: 'Extraction QA',
    subtitle: 'Pipeline trace, page classifications, source crops, and extraction metadata',
    sections: [
      {
        header: 'EXTRACTION METADATA',
        cols: [{ key: 'k', label: 'Property', width: 26 }, { key: 'v', label: 'Value', width: 60 }],
        rows: [
          { k: 'PDF Type', v: analysis.qa?.pdf_type || '' },
          { k: 'Source File', v: analysis.qa?.file_name || '' },
          { k: 'File Size (KB)', v: Math.round((analysis.qa?.file_size || 0) / 1024) },
          { k: 'Model', v: analysis.qa?.chat_model || '' },
          { k: 'Pages Rendered', v: analysis.qa?.pages_rendered || 0 },
          { k: 'Render DPI Target', v: RENDER_TARGET_DPI },
          { k: 'Scope', v: analysis.qa?.scope || '' },
          { k: 'Status', v: analysis.status || 'OK' },
          { k: 'Reason', v: analysis.reason || '' },
          { k: 'Avg Confidence', v: analysis.qa?.validation?.avgConfidence != null ? Math.round(analysis.qa.validation.avgConfidence * 100) + '%' : '' },
          { k: 'Failed Mappings', v: analysis.qa?.validation?.failedMappings?.length || 0 },
          { k: 'Reasoning Pass Succeeded', v: analysis.qa?.reasoning_succeeded ? 'Yes' : 'No' },
          { k: 'Extracted At', v: analysis.qa?.extracted_at || '' },
        ],
      },
      {
        header: 'PAGE CLASSIFICATIONS',
        cols: [
          { key: 'page', label: 'Page', width: 8 },
          { key: 'roles', label: 'Detected Roles', width: 40 },
          { key: 'count', label: '# Regions', width: 11 },
          { key: 'notes', label: 'Sheet Notes', width: 40 },
        ],
        rows: (analysis.qa?.classifications || []).map(c => ({
          page: c.pageNum,
          roles: (c.regions || []).map(r => r.role).join(', ') || '(none)',
          count: (c.regions || []).length,
          notes: c.sheet_notes || '',
        })),
      },
      {
        header: 'DOOR SCHEDULE REGIONS',
        cols: [
          { key: 'cropId', label: 'Crop ID', width: 24 },
          { key: 'page', label: 'Page', width: 8 },
          { key: 'label', label: 'Label', width: 30 },
          { key: 'strips', label: '# Strips', width: 10 },
          { key: 'rows', label: 'Rows Extracted', width: 14 },
        ],
        rows: (analysis.qa?.door_regions || []).map(d => ({
          cropId: d.crop_id, page: d.pageNum, label: d.label || '',
          strips: (d.strips || []).length, rows: d.totalRows || 0,
        })),
      },
      {
        header: 'HARDWARE SET BLOCKS',
        cols: [
          { key: 'cropId', label: 'Crop ID', width: 28 },
          { key: 'page', label: 'Page', width: 8 },
          { key: 'setId', label: 'Set ID', width: 12 },
          { key: 'header', label: 'Header Text', width: 32 },
          { key: 'items', label: 'Items Extracted', width: 16 },
        ],
        rows: (analysis.qa?.hw_blocks || []).map(b => ({
          cropId: b.crop_id, page: b.pageNum, setId: b.set_id, header: b.header || '', items: b.items || 0,
        })),
      },
      {
        header: `ESTIMATOR NOTES (${(analysis.estimator_notes || []).length})`,
        cols: [{ key: 'note', label: 'Note', width: 100 }],
        rows: (analysis.estimator_notes || []).map(n => ({ note: n })),
      },
    ],
  }), 'Extraction QA');

  // Save
  const safeName = (ps.project_name || project.name || 'analysis').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 40);
  const filename = `FastBid24_${safeName}_${project.proposalId || today}.xlsx`;
  XLSX.writeFile(wb, filename);
}

/* ---------- Comsense-style Door & Frame Schedule CSV exporter ----------
   Spec reference:
     https://support.comsenseinc.com/hc/en-us/articles/360040769334-Door-Frame-Schedule-Data-Table-Requirements
   Comsense's importer (Advantage) reads a flat tabular schedule and uses a per-project
   field-mapping UI to map column headers → Comsense fields. We emit the canonical set
   of mappable column headers so a Comsense user can do a one-click map.
   - Each opening is one row (no merged cells, no spacers).
   - Doors & frames live on the same row (per Comsense's "Door & Frame Schedule" model).
   - Hardware Set is a single reference per row (the door-level hardware_set string).
   - We default to RFC-4180 CSV (comma + CRLF + quoted fields). Pass {delimiter: '\t', ext: 'txt'}
     to produce the tab-delimited TXT that Comsense's docs prefer.
*/
const COMSENSE_COLUMNS = [
  'Section',         'Opening Number',  'Floor',           'From',            'To',
  'Quantity',        'Hand',
  'Door Width',      'Door Height',     'Door Thickness',
  'Door Material',   'Door Type',       'Door Series',     'Door Core',       'Door Finish',
  'Door Glass',      'Door Label',      'Door Notes',
  'Frame Material',  'Frame Type',      'Frame Profile',   'Frame Throat',    'Frame Finish',
  'Frame Label',     'Frame Notes',
  'Hardware Set',
  'Remarks',         'Source Page',
];

function _csvEscape(v, delimiter) {
  if (v == null) return '';
  let s = String(v);
  // Comsense doesn't accept embedded newlines; collapse to space.
  s = s.replace(/\r?\n/g, ' ').trim();
  const needsQuote = s.includes(delimiter) || s.includes('"') || s.includes('\r') || s.includes(',') || s.includes('\t');
  if (needsQuote) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function _splitFromTo(loc) {
  if (!loc) return { from: '', to: '' };
  const s = String(loc).trim();
  // Common separators in schedules: " / ", " - ", " to ", " → "
  const m = s.split(/\s*(?:\/|→|—|–|-|\bto\b)\s*/i);
  if (m.length >= 2) return { from: m[0], to: m.slice(1).join(' / ') };
  return { from: '', to: s };
}

function buildComsenseRows(analysis) {
  const doors = analysis?.door_analysis || [];
  return doors.map(d => {
    const { from, to } = _splitFromTo(d.room_or_location);
    const remarksArr = Array.isArray(d.remarks) ? d.remarks : (d.remarks ? [String(d.remarks)] : []);
    const remarks = [
      ...remarksArr,
      d.closer ? `Closer: ${d.closer}` : null,
      d.electric_or_access_control ? `EAC: ${d.electric_or_access_control}` : null,
      d.existing_to_remain ? 'EXISTING TO REMAIN' : null,
    ].filter(Boolean).join('; ');
    return {
      'Section':         '',
      'Opening Number':  d.mark || '',
      'Floor':           '',
      'From':            from,
      'To':              to,
      'Quantity':        1,
      'Hand':            '',
      'Door Width':      d.size?.width || '',
      'Door Height':     d.size?.height || '',
      'Door Thickness':  d.size?.thickness || '',
      'Door Material':   d.door_material || '',
      'Door Type':       d.door_type || '',
      'Door Series':     '',
      'Door Core':       '',
      'Door Finish':     d.door_finish || '',
      'Door Glass':      d.glazing || '',
      'Door Label':      d.fire_rating || '',
      'Door Notes':      '',
      'Frame Material':  d.frame_material || '',
      'Frame Type':      d.frame_type || '',
      'Frame Profile':   '',
      'Frame Throat':    '',
      'Frame Finish':    d.frame_finish || '',
      'Frame Label':     d.fire_rating || '',
      'Frame Notes':     '',
      'Hardware Set':    d.hardware_set || '',
      'Remarks':         remarks,
      'Source Page':     d.source_page ?? '',
    };
  });
}

function exportAnalysisToComsenseCSV({ analysis, project, tweaks, delimiter = ',', ext = 'csv' } = {}) {
  if (!analysis || !Array.isArray(analysis.door_analysis) || analysis.door_analysis.length === 0) {
    alert('No door schedule to export. Run an analysis first.');
    return;
  }
  const rows = buildComsenseRows(analysis);
  const lines = [];
  lines.push(COMSENSE_COLUMNS.map(c => _csvEscape(c, delimiter)).join(delimiter));
  for (const r of rows) {
    lines.push(COMSENSE_COLUMNS.map(c => _csvEscape(r[c], delimiter)).join(delimiter));
  }
  const blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: ext === 'csv' ? 'text/csv;charset=utf-8' : 'text/plain;charset=utf-8' });
  const ps = analysis.project_summary || {};
  const safeName = (ps.project_name || project?.name || 'schedule').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 40);
  const today = new Date().toISOString().slice(0, 10);
  const filename = `Comsense_${safeName}_${project?.proposalId || today}.${ext}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ---------- PDF text extraction (browser-side) ---------- */
async function extractPdfText(file, onProgress) {
  if (!window.pdfjsLib) throw new Error('pdf.js not loaded');
  const buf = await file.arrayBuffer();
  const pdf = await window.pdfjsLib.getDocument({ data: buf }).promise;
  let allText = '';
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const tc = await page.getTextContent();
    const items = tc.items.map(i => i.str).join(' ');
    allText += `\n\n--- Page ${p} ---\n${items}`;
    onProgress?.({ page: p, pages: pdf.numPages, sample: items.slice(0, 120) });
  }
  return { text: allText.trim(), pages: pdf.numPages, pdf, arrayBuffer: buf };
}

/* ---------- PDF page rendering for image-based PDFs ---------- */
const RENDER_TARGET_DPI    = 300;     // Minimum 300 DPI per spec
const MAX_RENDER_LONG_EDGE = 4200;    // higher cap for 300dpi arch sheets
const PREVIEW_LONG_EDGE    = 720;     // QA preview size
const MAX_CANVAS_AREA      = 16777216;// 16M px — safe across browsers
const TEXT_THRESHOLD_CHARS = 500;     // (unused in current pipeline; kept for legacy)

/* Decide if a PDF should go through the vision pipeline.
   Returns { isImageBased, pdfType, reason, metrics } so we can show the user WHY. */
function detectPdfMode({ text, forceVision }) {
  if (forceVision) return { isImageBased: true, pdfType: 'IMAGE_BASED_PDF', reason: 'forced_by_user', metrics: { length: text.length } };
  const len = text.length;
  // Count alpha characters and unique meaningful tokens
  const alphaCount = (text.match(/[a-zA-Z]/g) || []).length;
  const tokens = text.toLowerCase().match(/[a-z0-9]{3,}/g) || [];
  const uniqueTokens = new Set(tokens).size;
  const alphaRatio = len ? alphaCount / len : 0;
  const metrics = { length: len, alphaCount, alphaRatio: +alphaRatio.toFixed(3), uniqueTokens, totalTokens: tokens.length };

  if (len < TEXT_THRESHOLD_CHARS) return { isImageBased: true, pdfType: 'IMAGE_BASED_PDF', reason: 'text_too_short', metrics };
  // Garbage-OCR sniff: lots of chars but tiny vocabulary or very low alpha ratio
  if (uniqueTokens < 80 && len < 4000) return { isImageBased: true, pdfType: 'IMAGE_BASED_PDF', reason: 'low_vocabulary', metrics };
  if (alphaRatio < 0.35) return { isImageBased: true, pdfType: 'IMAGE_BASED_PDF', reason: 'low_alpha_ratio', metrics };
  return { isImageBased: false, pdfType: 'TEXT_BASED_PDF', reason: 'sufficient_text', metrics };
}

/* Vision models — OpenAI multimodal-capable. If the configured chat model isn't in this list,
   fall back to a known vision model for the vision passes. */
const VISION_MODEL_HINTS = [/^gpt-4o/i, /^gpt-4\.1/i, /^gpt-5/i, /^o1/i, /^o3/i, /^o4/i, /vision/i, /^chatgpt-4o/i];
function isLikelyVisionModel(model) {
  return !!model && VISION_MODEL_HINTS.some(re => re.test(model));
}

async function renderPdfPages(fileOrBuffer, onProgress, opts = {}) {
  if (!window.pdfjsLib) throw new Error('pdf.js not loaded');
  let arrayBuffer;
  if (fileOrBuffer instanceof Blob) {
    arrayBuffer = await fileOrBuffer.arrayBuffer();
  } else if (fileOrBuffer instanceof ArrayBuffer) {
    arrayBuffer = fileOrBuffer.slice(0);
  } else if (fileOrBuffer && fileOrBuffer.byteLength != null) {
    arrayBuffer = fileOrBuffer.slice ? fileOrBuffer.slice(0) : fileOrBuffer;
  } else {
    throw new Error('renderPdfPages: pass a File/Blob or ArrayBuffer');
  }
  const tileMode = !!opts.tileMode;
  const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const out = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    // Pick the highest scale that fits both MAX_RENDER_LONG_EDGE and MAX_CANVAS_AREA constraints.
    const baseV = page.getViewport({ scale: 1 });
    let scale = RENDER_TARGET_DPI / 72;
    let testV = page.getViewport({ scale });
    // cap by longest edge
    let longest = Math.max(testV.width, testV.height);
    if (longest > MAX_RENDER_LONG_EDGE) scale *= (MAX_RENDER_LONG_EDGE / longest);
    // cap by canvas area (Safari has ~16M px area cap; respect it)
    testV = page.getViewport({ scale });
    const area = testV.width * testV.height;
    if (area > MAX_CANVAS_AREA) scale *= Math.sqrt(MAX_CANVAS_AREA / area);
    const viewport = page.getViewport({ scale });

    const canvas = document.createElement('canvas');
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext('2d', { alpha: false });
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // 'print' intent renders without highlights/annotations & uses sharper text
    await page.render({ canvasContext: ctx, viewport, intent: 'print' }).promise;

    // PNG output — lossless, much better for vision OCR on small text
    const dataUrl = canvas.toDataURL('image/png');

    // preview
    const pcanvas = document.createElement('canvas');
    const pscale = PREVIEW_LONG_EDGE / Math.max(canvas.width, canvas.height);
    pcanvas.width = Math.max(1, Math.round(canvas.width * pscale));
    pcanvas.height = Math.max(1, Math.round(canvas.height * pscale));
    pcanvas.getContext('2d').drawImage(canvas, 0, 0, pcanvas.width, pcanvas.height);
    const previewUrl = pcanvas.toDataURL('image/jpeg', 0.8);

    const pageData = {
      pageNum: p,
      width: canvas.width,
      height: canvas.height,
      dpi: Math.round(scale * 72),
      orientation: canvas.width >= canvas.height ? 'landscape' : 'portrait',
      dataUrl,
      previewUrl,
      tiles: null,
    };

    // Tile mode — generate 2×2 overlapping crops for dense arch sheets
    if (tileMode) {
      const tiles = [];
      const tileW = Math.ceil(canvas.width * 0.6);   // 60% wide
      const tileH = Math.ceil(canvas.height * 0.6);  // 60% tall (40% overlap)
      const positions = [
        [0, 0, 'TL'], [canvas.width - tileW, 0, 'TR'],
        [0, canvas.height - tileH, 'BL'], [canvas.width - tileW, canvas.height - tileH, 'BR'],
      ];
      for (const [x, y, label] of positions) {
        const tc = document.createElement('canvas');
        tc.width = tileW; tc.height = tileH;
        tc.getContext('2d').drawImage(canvas, x, y, tileW, tileH, 0, 0, tileW, tileH);
        tiles.push({
          label,
          dataUrl: tc.toDataURL('image/png'),
          bbox: [x / canvas.width, y / canvas.height, tileW / canvas.width, tileH / canvas.height],
        });
      }
      pageData.tiles = tiles;
    }

    out.push(pageData);
    onProgress?.({ page: p, pages: pdf.numPages, width: canvas.width, height: canvas.height, dpi: pageData.dpi });
  }
  return out;
}

/* Crop a region (bbox in normalized 0..1 coords) out of a page image */
async function cropRegion(pageImageDataUrl, bbox) {
  const img = await new Promise((res, rej) => {
    const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = pageImageDataUrl;
  });
  const [x, y, w, h] = bbox;
  const sx = Math.max(0, Math.round(x * img.width));
  const sy = Math.max(0, Math.round(y * img.height));
  const sw = Math.max(1, Math.round(w * img.width));
  const sh = Math.max(1, Math.round(h * img.height));
  const canvas = document.createElement('canvas');
  canvas.width = sw; canvas.height = sh;
  canvas.getContext('2d').drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
  return { dataUrl: canvas.toDataURL('image/jpeg', 0.88), width: sw, height: sh };
}

/* ---------- Vision extraction (image-based PDFs) ---------- */
const REGION_DETECT_SYSTEM = `You are a senior Division 8 estimator reviewing scanned architectural sheets.
Identify the visible regions on this sheet that contain Division 8 information.
Region types: "door_schedule", "hardware_schedule", "hardware_set", "door_details", "frame_details", "legend", "notes", "other".

Return STRICTLY valid JSON only:
{
  "regions": [
    { "type": string, "label": string, "bbox": [x, y, w, h], "confidence": number }
  ],
  "sheet_orientation": "landscape"|"portrait",
  "sheet_notes": string
}

bbox is normalized to the image (0..1). Be generous — slightly oversize crops are better than tight ones that miss rows. If no Div 8 content is visible, return regions: [].`;

const REGION_EXTRACT_SYSTEM = `You are a senior Division 8 estimator transcribing a CROPPED region of a scanned architectural sheet.

YOUR JOB IS TRANSCRIPTION, NOT SUMMARIZATION.
- Read EVERY visible row, top to bottom. Do not stop early. Do not abbreviate. Do not say "etc." or "additional doors".
- If a column for a row is unreadable, set that field to null. Do NOT skip the row — emit it with nulls.
- Preserve marks/IDs character-for-character as written (e.g. "101A", "A.103", "DR-1.02").
- Never invent door marks, hardware set IDs, part numbers, prices, manufacturers, or finishes.
- Set confidence ≥ 0.85 only when you can read the row clearly. Use 0.5–0.84 for partial reads, < 0.5 for guesses.

Return STRICTLY valid JSON. Pick the schema matching the crop:

If door schedule rows are visible:
{ "kind": "door_schedule", "row_count_visible": number, "rows": [{
    "mark": string, "room_or_location": string|null, "door_type": string|null,
    "size": {"width": string|null, "height": string|null, "thickness": string|null},
    "door_material": string|null, "door_finish": string|null,
    "glazing": string|null, "frame_type": string|null, "frame_material": string|null, "frame_finish": string|null,
    "fire_rating": string|null, "hardware_set": string|null,
    "remarks": [string], "confidence": number
}] }

If a hardware set / hardware items table is visible:
{ "kind": "hardware_set", "sets": [{
    "id": string, "name": string|null,
    "items": [{ "qty": number|null, "desc": string, "part": string|null, "mfr": string|null, "finish": string|null }],
    "confidence": number
}] }

If general notes/legends:
{ "kind": "notes", "notes": [string] }

If you genuinely cannot identify any of the above:
{ "kind": "unknown", "raw_text": "verbatim text you can read, line by line" }

CRITICAL: rows.length MUST equal the number of rows you can see in the schedule. row_count_visible MUST be your honest count of rows visible in the crop. If those differ, your output is invalid.`;

async function callOpenAIVision({ apiKey, model, system, userText, imageDataUrls, detail = 'high', maxTokens = 16000 }) {
  const content = [{ type: 'text', text: userText }];
  for (const url of imageDataUrls) {
    content.push({ type: 'image_url', image_url: { url, detail } });
  }
  const body = {
    model,
    messages: [
      { role: 'system', content: system },
      { role: 'user', content },
    ],
    response_format: { type: 'json_object' },
    max_completion_tokens: maxTokens,
  };
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
    body: JSON.stringify(body),
  });
  let data;
  try { data = await res.json(); } catch { throw new Error('Network error contacting OpenAI'); }
  // Older chat models reject max_completion_tokens — retry with max_tokens
  if (!res.ok && /max_completion_tokens/i.test(data?.error?.message || '')) {
    delete body.max_completion_tokens; body.max_tokens = maxTokens;
    const res2 = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    data = await res2.json();
    if (!res2.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res2.status));
  } else if (!res.ok) {
    throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
  }
  const text = data.choices?.[0]?.message?.content || '{}';
  const finishReason = data.choices?.[0]?.finish_reason;
  try {
    const parsed = JSON.parse(text);
    parsed.__finish_reason = finishReason;
    return parsed;
  } catch {
    throw new Error('Vision returned invalid JSON' + (finishReason === 'length' ? ' (output truncated — increase max tokens)' : ''));
  }
}

/* Crop a region using a normalized bbox AND a vertical slice (for splitting tall door schedules into row strips) */
async function cropRegionStrip(pageImageDataUrl, bbox, stripStartY, stripEndY) {
  // bbox is the region within the page; stripStartY/stripEndY are 0..1 within the region (vertical slice)
  const [bx, by, bw, bh] = bbox;
  const stripBbox = [bx, by + bh * stripStartY, bw, bh * (stripEndY - stripStartY)];
  return cropRegion(pageImageDataUrl, stripBbox);
}

async function extractWithVision({ apiKey, model, scope, pages, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required.');

  // PASS 1 — region detection per page (or per tile when tiles are present)
  const allRegions = []; // {pageNum, type, label, bbox (page coords), confidence, source}
  const pageMeta = [];   // {pageNum, regionsFound, sheetOrientation}

  // Map a tile-local bbox (0..1 within tile) to page-level coords using tile.bbox.
  const tileToPage = (tileBbox, localBbox) => {
    const [tx, ty, tw, th] = tileBbox;
    const [lx, ly, lw, lh] = localBbox;
    return [tx + lx * tw, ty + ly * th, lw * tw, lh * th];
  };

  for (const page of pages) {
    let totalRegions = 0;
    const detectFor = async (imageUrl, label, mapBack) => {
      let res;
      try {
        res = await callOpenAIVision({
          apiKey, model,
          system: REGION_DETECT_SYSTEM,
          userText: `Identify all Division 8 regions on ${label}. Sheet appears ${page.orientation}.`,
          imageDataUrls: [imageUrl],
        });
      } catch (e) {
        onProgress?.({ kind: 'warn', text: `Region detection failed on ${label}: ${e.message}` });
        res = { regions: [] };
      }
      const regs = Array.isArray(res?.regions) ? res.regions : [];
      regs.forEach(r => {
        if (Array.isArray(r.bbox) && r.bbox.length === 4) {
          const pageBbox = mapBack ? mapBack(r.bbox) : r.bbox;
          allRegions.push({ pageNum: page.pageNum, type: r.type || 'other', label: r.label || r.type, bbox: pageBbox, confidence: r.confidence ?? 0.7, source: label });
        }
      });
      return { regs, sheetOrientation: res?.sheet_orientation || page.orientation, sheetNotes: res?.sheet_notes || '' };
    };

    if (page.tiles && page.tiles.length) {
      // Tile mode — run detection on each tile, then also once on full page (cheaper context)
      onProgress?.({ kind: 'info', text: `Pass 1 · page ${page.pageNum}: detecting regions on ${page.tiles.length} tile(s)…` });
      for (const tile of page.tiles) {
        const r = await detectFor(tile.dataUrl, `page ${page.pageNum} tile ${tile.label}`, (b) => tileToPage(tile.bbox, b));
        totalRegions += r.regs.length;
      }
      const full = await detectFor(page.dataUrl, `page ${page.pageNum} full`, null);
      totalRegions += full.regs.length;
      pageMeta.push({ pageNum: page.pageNum, regionsFound: totalRegions, sheetOrientation: full.sheetOrientation, sheetNotes: full.sheetNotes });
    } else {
      onProgress?.({ kind: 'info', text: `Pass 1 · identifying regions on page ${page.pageNum} (${page.width}×${page.height})…` });
      const r = await detectFor(page.dataUrl, `page ${page.pageNum}`, null);
      totalRegions = r.regs.length;
      pageMeta.push({ pageNum: page.pageNum, regionsFound: totalRegions, sheetOrientation: r.sheetOrientation, sheetNotes: r.sheetNotes });
    }
    onProgress?.({ kind: 'ok', text: `Page ${page.pageNum}: ${totalRegions} region(s) detected` });
  }

  // Deduplicate regions that overlap heavily AND share a type (tile + full-page often both find the door schedule)
  const deduped = [];
  for (const r of allRegions) {
    const dup = deduped.find(d => d.pageNum === r.pageNum && d.type === r.type && iou(d.bbox, r.bbox) > 0.55);
    if (!dup) deduped.push(r);
    else if ((r.confidence ?? 0) > (dup.confidence ?? 0)) Object.assign(dup, r);
  }

  // PASS 2 — crop each region and extract structured data
  const cropExtractions = [];
  for (let i = 0; i < deduped.length; i++) {
    const region = deduped[i];
    const page = pages.find(p => p.pageNum === region.pageNum);
    if (!page) continue;
    onProgress?.({ kind: 'info', text: `Pass 2 · extracting ${region.type} from page ${region.pageNum} (${i + 1}/${deduped.length})…` });
    let crop;
    try { crop = await cropRegion(page.dataUrl, region.bbox); }
    catch (e) { onProgress?.({ kind: 'warn', text: `Crop failed for ${region.type}: ${e.message}` }); continue; }
    // preview for QA panel
    const previewCanvas = document.createElement('canvas');
    const pscale = PREVIEW_LONG_EDGE / Math.max(crop.width, crop.height);
    previewCanvas.width = Math.max(1, Math.round(crop.width * pscale));
    previewCanvas.height = Math.max(1, Math.round(crop.height * pscale));
    const pimg = await new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = crop.dataUrl; });
    previewCanvas.getContext('2d').drawImage(pimg, 0, 0, previewCanvas.width, previewCanvas.height);
    const cropPreview = previewCanvas.toDataURL('image/jpeg', 0.8);

    let res;
    try {
      res = await callOpenAIVision({
        apiKey, model,
        system: REGION_EXTRACT_SYSTEM,
        userText: `This is a CROPPED region of type "${region.type}" from page ${region.pageNum}. Project scope: ${scope}. Read EVERY row visible — do not summarize. Extract structured data per the schema.`,
        imageDataUrls: [crop.dataUrl],
      });
    } catch (e) {
      onProgress?.({ kind: 'warn', text: `Extraction failed on ${region.type}: ${e.message}` });
      res = { kind: 'failed', error: e.message };
    }

    // If this is a door schedule and we got fewer rows than the model claims it saw (or 0), strip-split and retry
    if (region.type === 'door_schedule' && res?.kind === 'door_schedule') {
      const claimed = res.row_count_visible ?? 0;
      const got = (res.rows || []).length;
      const tall = crop.height >= 1400; // tall crops are likely truncated
      const truncated = res.__finish_reason === 'length';
      if (tall || truncated || (claimed > 0 && got < claimed * 0.7)) {
        onProgress?.({ kind: 'info', text: `Door schedule appears under-extracted (got ${got}/${claimed || '?'} rows${tall ? ', tall crop' : ''}${truncated ? ', truncated' : ''}) — splitting into row strips…` });
        const stripCount = Math.min(4, Math.max(2, Math.ceil(crop.height / 1100)));
        const stripOverlap = 0.08;
        const stripRows = [];
        for (let s = 0; s < stripCount; s++) {
          const y0 = Math.max(0, s / stripCount - stripOverlap);
          const y1 = Math.min(1, (s + 1) / stripCount + stripOverlap);
          let strip;
          try { strip = await cropRegionStrip(page.dataUrl, region.bbox, y0, y1); }
          catch (e) { continue; }
          try {
            const sr = await callOpenAIVision({
              apiKey, model,
              system: REGION_EXTRACT_SYSTEM,
              userText: `This is STRIP ${s+1}/${stripCount} of a door schedule (page ${region.pageNum}). The strip overlaps neighbors by ~8% so rows aren't bisected. Read EVERY row visible in THIS strip only.`,
              imageDataUrls: [strip.dataUrl],
            });
            if (sr?.kind === 'door_schedule' && Array.isArray(sr.rows)) {
              stripRows.push(...sr.rows);
              onProgress?.({ kind: 'ok', text: `Strip ${s+1}: ${sr.rows.length} row(s)` });
            }
          } catch (e) {
            onProgress?.({ kind: 'warn', text: `Strip ${s+1} extraction failed: ${e.message}` });
          }
        }
        // Dedupe by mark, prefer highest confidence
        const map = new Map();
        [...(res.rows || []), ...stripRows].forEach(r => {
          if (!r.mark) return;
          const prev = map.get(r.mark);
          if (!prev || (r.confidence ?? 0) > (prev.confidence ?? 0)) map.set(r.mark, r);
        });
        res.rows = [...map.values()];
        res.row_count_visible = res.rows.length;
        res.__strip_split = { strips: stripCount, recovered: res.rows.length };
        onProgress?.({ kind: 'ok', text: `After strip merge: ${res.rows.length} unique door row(s)` });
      }
    }

    // If this is a hardware_set crop and no items were extracted, strip-split & retry with item-focused prompt
    if ((region.type === 'hardware_set' || region.type === 'hardware_schedule') && res?.kind === 'hardware_set') {
      const totalItems = (res.sets || []).reduce((n, s) => n + (s.items?.length || 0), 0);
      const truncated = res.__finish_reason === 'length';
      if (totalItems === 0 || truncated || crop.height >= 1400) {
        onProgress?.({ kind: 'info', text: `Hardware set crop returned ${totalItems} item(s)${truncated ? ' (truncated)' : ''} — running item-focused strip pass…` });
        const stripCount = Math.min(4, Math.max(2, Math.ceil(crop.height / 1100)));
        const stripOverlap = 0.10;
        const allSets = new Map();
        // seed with whatever we already have
        (res.sets || []).forEach(s => { if (s.id) allSets.set(s.id, { id: s.id, name: s.name || null, items: [...(s.items || [])], confidence: s.confidence ?? 0.6 }); });
        for (let i2 = 0; i2 < stripCount; i2++) {
          const y0 = Math.max(0, i2 / stripCount - stripOverlap);
          const y1 = Math.min(1, (i2 + 1) / stripCount + stripOverlap);
          let strip;
          try { strip = await cropRegionStrip(page.dataUrl, region.bbox, y0, y1); }
          catch (e) { continue; }
          try {
            const sr = await callOpenAIVision({
              apiKey, model,
              system: REGION_EXTRACT_SYSTEM,
              userText: `This is STRIP ${i2+1}/${stripCount} of a HARDWARE SET / hardware schedule (page ${region.pageNum}). Transcribe EVERY line item visible: qty, full description, part number, manufacturer, finish. If a set ID/heading is visible at the top of this strip, return that as the set id. If a set continues from a previous strip without a header in this strip, use the most recent set id you can see, or "continued".`,
              imageDataUrls: [strip.dataUrl],
            });
            if (sr?.kind === 'hardware_set' && Array.isArray(sr.sets)) {
              sr.sets.forEach(s => {
                if (!s.id) return;
                const existing = allSets.get(s.id) || { id: s.id, name: s.name || null, items: [], confidence: s.confidence ?? 0.6 };
                existing.items = [...existing.items, ...(s.items || [])];
                if (!existing.name && s.name) existing.name = s.name;
                allSets.set(s.id, existing);
              });
              const stripItems = sr.sets.reduce((n, s) => n + (s.items?.length || 0), 0);
              onProgress?.({ kind: 'ok', text: `HW strip ${i2+1}: ${sr.sets.length} set(s) / ${stripItems} item(s)` });
            }
          } catch (e) {
            onProgress?.({ kind: 'warn', text: `HW strip ${i2+1} extraction failed: ${e.message}` });
          }
        }
        // Dedupe items per set by (desc + part)
        allSets.forEach(s => {
          const seen = new Set();
          s.items = s.items.filter(it => {
            const key = (it.desc || '').toLowerCase() + '|' + (it.part || '').toLowerCase() + '|' + (it.qty || '');
            if (seen.has(key)) return false;
            seen.add(key); return true;
          });
        });
        res.sets = [...allSets.values()];
        const final = res.sets.reduce((n, s) => n + (s.items?.length || 0), 0);
        res.__strip_split = { strips: stripCount, recovered: final };
        onProgress?.({ kind: 'ok', text: `After HW strip merge: ${res.sets.length} set(s) / ${final} item(s)` });
      }
    }

    cropExtractions.push({ region, kind: res?.kind || 'unknown', data: res, cropPreview });
  }

  const merged = mergeVisionExtractions(cropExtractions, scope);
  return { analysis: merged, qa: { pageMeta, regions: deduped, cropExtractions: cropExtractions.map(c => ({ region: c.region, kind: c.kind, cropPreview: c.cropPreview, data: c.data })) } };
}

/* Intersection over union of two normalized bboxes [x,y,w,h] */
function iou(a, b) {
  const ax2 = a[0] + a[2], ay2 = a[1] + a[3];
  const bx2 = b[0] + b[2], by2 = b[1] + b[3];
  const ix1 = Math.max(a[0], b[0]), iy1 = Math.max(a[1], b[1]);
  const ix2 = Math.min(ax2, bx2), iy2 = Math.min(ay2, by2);
  const iw = Math.max(0, ix2 - ix1), ih = Math.max(0, iy2 - iy1);
  const inter = iw * ih;
  const union = a[2]*a[3] + b[2]*b[3] - inter;
  return union > 0 ? inter / union : 0;
}

/* Merge per-region vision results into the senior-estimator analysis schema */
function mergeVisionExtractions(cropExtractions, scope) {
  const doorRows = [];
  const hardwareSets = [];
  const notes = [];
  for (const ce of cropExtractions) {
    if (ce.kind === 'door_schedule' && Array.isArray(ce.data?.rows)) doorRows.push(...ce.data.rows);
    else if (ce.kind === 'hardware_set' && Array.isArray(ce.data?.sets)) hardwareSets.push(...ce.data.sets);
    else if (ce.kind === 'notes' && Array.isArray(ce.data?.notes)) notes.push(...ce.data.notes);
  }
  // dedupe doors by mark, keep highest confidence
  const doorMap = new Map();
  doorRows.forEach(d => {
    if (!d.mark) return;
    const prev = doorMap.get(d.mark);
    if (!prev || (d.confidence ?? 0) > (prev.confidence ?? 0)) doorMap.set(d.mark, d);
  });
  // dedupe HW sets by id (merge items if duplicate)
  const setMap = new Map();
  hardwareSets.forEach(s => {
    if (!s.id) return;
    const prev = setMap.get(s.id);
    if (!prev) setMap.set(s.id, s);
    else { prev.items = [...(prev.items || []), ...(s.items || [])]; }
  });

  // Build door_analysis with risk inference (basic — we don't have a full estimator pass over the merged data yet)
  const door_analysis = [...doorMap.values()].map(d => ({
    mark: d.mark,
    room_or_location: d.room_or_location,
    door_type: d.door_type,
    opening_type: null,
    interior_or_exterior: null,
    size: d.size || { width: null, height: null, thickness: null },
    door_material: d.door_material,
    door_finish: d.door_finish,
    glazing: d.glazing,
    frame_type: d.frame_type,
    frame_material: d.frame_material,
    frame_finish: d.frame_finish,
    fire_rating: d.fire_rating,
    hardware_set: d.hardware_set,
    remarks: d.remarks || [],
    hardware_status: 'review required',
    install_complexity: 'medium',
    risk_level: (d.fire_rating && d.fire_rating !== '-') ? 'medium' : 'low',
    special_conditions: [],
    issues: [],
    recommendations: [],
    rfi_required: false,
    rfi_questions: [],
    confidence: d.confidence ?? 0.6,
  }));

  // hardware_set_review from the extracted sets — INCLUDING items
  const referencedByDoors = (id) => door_analysis.filter(d => d.hardware_set === id).map(d => d.mark);
  const hardware_set_review = [...setMap.values()].map(s => {
    const items = Array.isArray(s.items) ? s.items.filter(it => it && (it.desc || it.part)) : [];
    return {
      hardware_set: s.id,
      referenced_by_doors: referencedByDoors(s.id),
      status: items.length ? 'complete' : 'incomplete',
      items,
      missing_or_unclear_items: items.length ? [] : ['no hardware items extracted from crop'],
      special_coordination: [],
      estimator_note: s.name || null,
      confidence: s.confidence ?? 0.6,
    };
  });

  return {
    project_summary: {
      scope_type: scope,
      project_name: null,
      project_number: null,
      architect: null,
      address: null,
      drawing: null,
      date: null,
      total_openings_found: door_analysis.length,
      total_hardware_sets_referenced: new Set(door_analysis.map(d => d.hardware_set).filter(Boolean)).size,
      hardware_sets_missing_or_unclear: hardware_set_review.filter(s => s.status !== 'complete').length,
      high_risk_openings: door_analysis.filter(d => d.risk_level === 'high').length,
      medium_risk_openings: door_analysis.filter(d => d.risk_level === 'medium').length,
      low_risk_openings: door_analysis.filter(d => d.risk_level === 'low').length,
      complex_installations: 0,
      access_control_openings: 0,
      exterior_openings: 0,
      fire_rated_openings: door_analysis.filter(d => d.fire_rating && d.fire_rating !== '-').length,
      overall_bid_risk: 'Medium',
      estimator_summary: `Image-based PDF processed via vision. Extracted ${door_analysis.length} opening(s) and ${hardware_set_review.length} hardware set(s) across ${cropExtractions.length} region(s). Manually verify all entries against source sheets before bidding.`,
    },
    door_analysis,
    hardware_set_review,
    project_risks: [],
    rfi_log: [],
    estimator_notes: notes,
    bid_recommendations: {
      supply_only_notes: [], installation_only_notes: [], supply_and_installation_notes: [],
      exclusions_to_consider: [], allowances_to_consider: [], coordination_items: [],
    },
  };
}

/* ---------- Validation — flag failed mappings & decide completeness ---------- */
function validateAnalysis(analysis) {
  const issues = []; // {type, mark?, set?, message}
  const doors = analysis.door_analysis || [];
  const sets = analysis.hardware_set_review || [];
  const setById = new Map(sets.map(s => [s.hardware_set, s]));

  // FAILED_MAPPING: door references HW set, but set is missing OR set has no items
  doors.forEach(d => {
    if (!d.hardware_set) return;
    const s = setById.get(d.hardware_set);
    if (!s) {
      issues.push({ type: 'FAILED_MAPPING', code: 'HW_SET_MISSING_FROM_SPEC', mark: d.mark, set: d.hardware_set, message: `Door ${d.mark} references hardware set ${d.hardware_set} which is not in the extracted hardware schedule.` });
    } else if (String(s.status||'').toLowerCase() === 'missing') {
      issues.push({ type: 'FAILED_MAPPING', code: 'HW_SET_MISSING', mark: d.mark, set: d.hardware_set, message: `Hardware set ${d.hardware_set} is marked missing.` });
    } else if (!Array.isArray(s.items) || s.items.length === 0) {
      issues.push({ type: 'FAILED_MAPPING', code: 'HW_SET_NO_ITEMS', mark: d.mark, set: d.hardware_set, message: `Hardware set ${d.hardware_set} has no extracted line items.` });
    }
  });

  // Missing fields per door
  const missingFields = [];
  doors.forEach(d => {
    const miss = [];
    if (!d.hardware_set) miss.push('hardware_set');
    if (!d.size?.width) miss.push('size.width');
    if (!d.size?.height) miss.push('size.height');
    if (!d.door_material) miss.push('door_material');
    if (miss.length) missingFields.push({ mark: d.mark, fields: miss });
  });

  const failedMappings = issues.filter(i => i.type === 'FAILED_MAPPING');
  const avgConf = doors.length ? doors.reduce((s,d)=>s+(d.confidence ?? 0.7),0) / doors.length : 0;

  const hasDoors = doors.length > 0;
  const hasHardware = sets.some(s => Array.isArray(s.items) && s.items.length > 0);
  const hasMapping = doors.some(d => d.hardware_set);

  let status = 'OK';
  let reason = null;
  if (!hasDoors) { status = 'REVIEW_REQUIRED'; reason = 'NO_DOORS_EXTRACTED'; }
  else if (!hasHardware) { status = 'REVIEW_REQUIRED'; reason = 'NO_HARDWARE_EXTRACTED'; }
  else if (!hasMapping) { status = 'REVIEW_REQUIRED'; reason = 'NO_DOOR_HARDWARE_MAPPING'; }
  else if (failedMappings.length > doors.length * 0.3) { status = 'REVIEW_REQUIRED'; reason = 'TOO_MANY_FAILED_MAPPINGS'; }
  else if (avgConf < 0.6) { status = 'REVIEW_REQUIRED'; reason = 'LOW_CONFIDENCE'; }

  return { status, reason, failedMappings, missingFields, avgConfidence: avgConf, hasDoors, hasHardware, hasMapping };
}

/* ---------- OpenAI extraction (senior estimator analysis) ---------- */
/* ---------- Senior Estimator System Prompt (per user spec — verbatim) ---------- */
const EXTRACTION_SYSTEM = `You are a senior Division 8 Doors, Frames & Hardware estimator with 15+ years of experience in commercial construction.

I am uploading a project PDF that may contain:
- Door schedules
- Hardware sets
- Door/frame/glazing notes
- Door remarks
- Special Division 8 conditions

Your job is NOT just to extract text.
Your job is to analyze the document like a real estimator preparing a bid.

--------------------------------------------------
PRIMARY OBJECTIVE
--------------------------------------------------

Analyze the uploaded PDF and produce a practical senior-estimator review covering:

1. Door schedule interpretation
2. Hardware set mapping
3. Hardware completeness review
4. Installation complexity
5. Risk identification
6. RFIs / clarification items
7. Estimator notes
8. Structured bid-ready JSON output

--------------------------------------------------
CRITICAL ANTI-HALLUCINATION RULES
--------------------------------------------------

- Extract only what is clearly visible in the PDF.
- Do not invent door marks, hardware sets, quantities, finishes, ratings, or remarks.
- Do not complete missing numbering sequences.
- Preserve door marks and hardware set names exactly as written.
- If something is unclear, return null or "review required".
- Prefer missing data over wrong data.
- Do not assume hardware scope unless it is shown in the schedule or hardware set.
- If a door has remarks like CR, EH, VI, AO, EL, DPS, panic, access control, etc., flag it as a coordination item.
- If a hardware set referenced in the door schedule is missing from the hardware set page, flag it.
- If a hardware set exists but has unclear/incomplete products, flag it.

--------------------------------------------------
DOCUMENT ANALYSIS METHOD
--------------------------------------------------

Step 1: Identify document sections:
- Door schedule
- Hardware set descriptions
- Door panel legend
- Door remarks legend
- Frame types
- Glazing types
- Any notes affecting scope

Step 2: Extract each door schedule row:
For each opening, capture:
- Door mark
- Room / location
- Door type
- Interior/exterior
- Width
- Height
- Thickness
- Door material
- Door finish
- Glazing type
- Frame type
- Frame material
- Frame finish
- Fire rating
- Hardware set
- Remarks
- Details if visible

Step 3: Cross-reference:
- Match each door's hardware set to the hardware set descriptions.
- Identify whether the hardware set appears complete, incomplete, or unclear.
- Identify special remarks that affect supply, install, or coordination.

Step 4: Analyze each opening as an estimator:
For each door, determine:
- Opening type: single, double, pair, exterior, interior, fire-rated, storefront/aluminum, hollow metal, wood, etc.
- Hardware completeness: complete / incomplete / review required
- Installation complexity: low / medium / high
- Risk level: low / medium / high
- Special conditions
- Issues
- Recommendations
- Confidence score

--------------------------------------------------
SCOPE-SPECIFIC LOGIC
--------------------------------------------------

If scope = Supply Only:

Focus on:
- Door, frame, hardware, glazing, finish, and material scope
- Hardware completeness
- Missing hardware sets
- Unclear finishes
- Fire-rated products
- Access control/electrified hardware supply exclusions
- Substitution risks
- Long-lead or specialty items

Ignore:
- Detailed field labor difficulty unless it affects supply risk.

--------------------------------------------------

If scope = Installation Only:

Focus on:
- Installation difficulty
- Door/frame type
- Exterior openings
- Aluminum/storefront coordination
- Access control coordination
- Electrified hardware coordination
- Panic/egress hardware
- Fire-rated installation requirements
- ADA/closer/operator concerns
- Double-door alignment
- Sequencing and site coordination

Assume material may be supplied by others unless the PDF clearly says otherwise.

--------------------------------------------------

If scope = Supply & Installation:

Perform both supply and install analysis together.

Focus on:
- Full material scope
- Hardware completeness
- Labor complexity
- Access control coordination
- Field sequencing risks
- Exterior/opening risk
- Missing information affecting bid accuracy
- Items requiring RFI before final bid

--------------------------------------------------
SPECIAL CONDITIONS TO FLAG
--------------------------------------------------

Flag any opening with:
- CR / card reader
- EH / egress hardware
- VI / video intercom
- EL / electrified lock
- DPS / door position switch
- AO / automatic operator
- Panic device
- Magnetic hold open
- Delayed egress
- Fire rating
- Smoke rating
- Exterior door
- Aluminum/storefront door
- Double door or uneven pair
- Hidden door
- Curtain wall/frame coordination
- New frame in existing condition
- Hardware by manufacturer
- Missing or unclear hardware set

--------------------------------------------------
RISK LOGIC
--------------------------------------------------

High risk:
- Exterior aluminum/storefront openings with access control or egress hardware
- Missing hardware set
- Electrified/access control hardware without clear responsibility
- Automatic operator or video intercom coordination
- Fire/smoke rated door with unclear hardware
- Double doors with panic/electrified hardware
- Existing frame/new frame coordination
- Hidden/specialty doors

Medium risk:
- Standard exterior hollow metal doors
- Interior doors with card reader
- Double doors with standard hardware
- Doors with glazing requiring coordination
- Doors with unclear remarks or incomplete finish data

Low risk:
- Standard interior single wood or hollow metal doors with clear hardware set and no special remarks

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return structured JSON only. Do not include explanation outside JSON.

Use this structure:

{
  "project_summary": {
    "scope_type": "",
    "project_name": "",
    "total_openings_found": 0,
    "total_hardware_sets_referenced": 0,
    "hardware_sets_missing_or_unclear": 0,
    "high_risk_openings": 0,
    "medium_risk_openings": 0,
    "low_risk_openings": 0,
    "complex_installations": 0,
    "access_control_openings": 0,
    "exterior_openings": 0,
    "fire_rated_openings": 0,
    "overall_bid_risk": "",
    "estimator_summary": ""
  },

  "door_analysis": [
    {
      "mark": "",
      "room_or_location": "",
      "door_type": "",
      "opening_type": "",
      "interior_or_exterior": "",
      "size": { "width": "", "height": "", "thickness": "" },
      "door_material": "",
      "door_finish": "",
      "glazing": "",
      "frame_type": "",
      "frame_material": "",
      "frame_finish": "",
      "fire_rating": "",
      "hardware_set": "",
      "remarks": [],
      "hardware_status": "",
      "install_complexity": "",
      "risk_level": "",
      "special_conditions": [],
      "issues": [],
      "recommendations": [],
      "rfi_required": true,
      "rfi_questions": [],
      "confidence": 0.0
    }
  ],

  "hardware_set_review": [
    {
      "hardware_set": "",
      "referenced_by_doors": [],
      "status": "",
      "missing_or_unclear_items": [],
      "special_coordination": [],
      "estimator_note": "",
      "confidence": 0.0
    }
  ],

  "project_risks": [
    {
      "severity": "",
      "category": "",
      "issue": "",
      "affected_openings": [],
      "recommendation": ""
    }
  ],

  "rfi_log": [
    {
      "priority": "",
      "question": "",
      "affected_openings": [],
      "reason": ""
    }
  ],

  "estimator_notes": [""],

  "bid_recommendations": {
    "supply_only_notes": [],
    "installation_only_notes": [],
    "supply_and_installation_notes": [],
    "exclusions_to_consider": [],
    "allowances_to_consider": [],
    "coordination_items": []
  }
}

--------------------------------------------------
QUALITY STANDARD
--------------------------------------------------

Think like a real estimator asking:

- Can I price this opening confidently?
- Is the hardware set complete?
- Is access control clearly defined?
- Is this a material risk, labor risk, or coordination risk?
- Will this create field issues?
- Should this be excluded, carried as allowance, or sent as RFI?
- Could this affect bid profitability?

Be practical, conservative, and construction-focused.

The final result should feel like:
"A senior doors and hardware estimator reviewed this project instantly."`;

async function extractWithOpenAI({ apiKey, model, scope, pdfText, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');
  onProgress?.({ kind: 'info', text: `Sending ${(pdfText.length/1024).toFixed(1)} KB of extracted text to ${model}…` });
  // NOTE: omit `temperature` — newer OpenAI models reject anything but the default (1).
  const body = {
    model,
    messages: [
      { role: 'system', content: EXTRACTION_SYSTEM },
      { role: 'user', content: `The selected project scope is: ${scope || 'Supply & Installation'}\n\nAnalyze the following PDF text as a senior Division 8 estimator. Return the structured JSON described in your instructions.\n\n---PDF TEXT BEGIN---\n${pdfText.slice(0, 80000)}\n---PDF TEXT END---` },
    ],
    response_format: { type: 'json_object' },
  };
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
    body: JSON.stringify(body),
  });
  let data;
  try { data = await res.json(); } catch { throw new Error('Network error contacting OpenAI'); }
  if (!res.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
  const content = data.choices?.[0]?.message?.content || '{}';
  let parsed;
  try { parsed = JSON.parse(content); } catch { throw new Error('Model returned invalid JSON'); }
  parsed.project_summary = parsed.project_summary || {};
  parsed.door_analysis = Array.isArray(parsed.door_analysis) ? parsed.door_analysis : [];
  parsed.hardware_set_review = Array.isArray(parsed.hardware_set_review) ? parsed.hardware_set_review : [];
  parsed.project_risks = Array.isArray(parsed.project_risks) ? parsed.project_risks : [];
  parsed.rfi_log = Array.isArray(parsed.rfi_log) ? parsed.rfi_log : [];
  parsed.estimator_notes = Array.isArray(parsed.estimator_notes) ? parsed.estimator_notes : [];
  parsed.bid_recommendations = parsed.bid_recommendations || {};
  onProgress?.({ kind: 'ok', text: `Received ${parsed.door_analysis.length} openings, ${parsed.hardware_set_review.length} hardware sets, ${parsed.project_risks.length} risks, ${parsed.rfi_log.length} RFIs` });
  return parsed;
}

/* ---------- NEW: Direct PDF upload to OpenAI ----------
   Sends the PDF as base64 inside a chat-completion message. The model reads the PDF
   end-to-end (no browser-side text/image extraction) and returns the same senior-estimator
   JSON schema. Replaces both extractWithOpenAI and extractWithVision for the standard flow. */
const REQUIRED_MODEL = 'gpt-5.5';  // Mandated — do not fall back to any other model

/* ===========================================================================
   IMAGE-BASED EXTRACTION PIPELINE (300 DPI, classify → extract → map → validate)
   =========================================================================== */

const TITLE_BLOCK_EXTRACT_SYSTEM = `You are reviewing the title block / cover sheet of a construction document.

Return STRICTLY valid JSON with the project metadata you can read from the title block. Read what is literally visible — never invent values. Use null if a field is not present.

{
  "project_name": string|null,
  "project_number": string|null,
  "architect": string|null,
  "architect_firm": string|null,
  "owner": string|null,
  "address": string|null,
  "drawing_title": string|null,
  "drawing_number": string|null,
  "sheet_number": string|null,
  "date": string|null,
  "revision": string|null,
  "scale": string|null,
  "raw_text_seen": string
}

raw_text_seen = a verbatim transcription of the title block area, line by line, so a reviewer can verify.`;

const PAGE_CLASSIFIER_SYSTEM = `You are reviewing one page of a construction document at 300 DPI.

Identify which Division 8 content appears on this page and where. Possible roles:
- "door_schedule"   — a tabular schedule of openings (rows with door marks, sizes, materials, hardware set refs)
- "hardware_sets"   — descriptions of hardware sets / hardware groups / finish hardware sets. Identifying cues (any ONE is sufficient):
                      • 2+ visible headings that look like "HW-NN", "HW SET NN", "SET N", "GROUP N", "FHW-N", "Hardware Set N" stacked down the page or laid out in columns
                      • Each heading is followed by line items naming hardware components (hinges, locks, closers, exit devices, kick plates, weatherstrip, thresholds, silencers, stops, holders, electric strikes, card readers, power supplies, etc.)
                      • A sheet titled "HARDWARE SETS", "HARDWARE GROUPS", "FINISH HARDWARE SETS", "HARDWARE SCHEDULE", "DOOR HARDWARE GROUPS"
                      • Specification-book prose blocks where each section starts with a hardware set ID and lists components beneath
                      A page that is wall-to-wall hardware sets in 1, 2, or 3 columns is STILL ONE region — return a single hardware_sets region covering the full block of columns, NOT one region per column. Hardware-sets content commonly spans MULTIPLE consecutive sheets in a set — classify every such page as hardware_sets.
- "door_details"    — door type elevations, panel diagrams
- "frame_details"   — frame type elevations
- "legend"          — legend / symbol key
- "notes"           — text notes (general notes, hardware notes, finish notes). Do NOT use this role for a page full of hardware-set blocks — that is "hardware_sets".
- "cover"           — title block, cover sheet
- "other"           — none of the above

Return STRICTLY valid JSON only:
{
  "regions": [{ "role": string, "label": string, "bbox": [x, y, w, h], "confidence": number }],
  "sheet_notes": string
}
- bbox is normalized (0..1) within the page image.
- If a single page contains BOTH a door schedule AND hardware set descriptions, return two separate regions.
- For a hardware_sets page that is purely hardware content, return ONE region with bbox covering all columns of sets — e.g. [0.02, 0.05, 0.96, 0.92]. Do NOT split by column.
- Be generous with bboxes — slightly oversize crops are better than tight ones that miss rows.
- If the page is purely cover/notes/legend, return appropriate roles with bbox covering the relevant area.
- If you see absolutely no Division 8 content, return regions: [].`;

const DOOR_ROW_EXTRACT_SYSTEM = `You are TRANSCRIBING a cropped door schedule. This is NOT a summarization task.

Read EVERY visible row top-to-bottom. For every row, emit one object — even if some columns are unreadable (set those fields to null). Do NOT skip rows. Do NOT abbreviate. Do NOT say "etc.".

Preserve door marks character-for-character (e.g. "101A", "A.103", "DR-1.02"). Never invent a mark, a size, a hardware set ID, or a fire rating.

Return STRICTLY valid JSON:
{
  "row_count_visible": number,
  "rows": [{
    "mark": string,
    "room_or_location": string|null,
    "door_type": string|null,
    "interior_or_exterior": "Interior"|"Exterior"|null,
    "size": { "width": string|null, "height": string|null, "thickness": string|null },
    "door_material": string|null,
    "door_finish": string|null,
    "glazing": string|null,
    "frame_type": string|null,
    "frame_material": string|null,
    "frame_finish": string|null,
    "fire_rating": string|null,
    "hardware_set": string|null,
    "remarks": [string],
    "raw_text_seen": string,
    "confidence": number
  }]
}

raw_text_seen = the literal cells in row order as you read them (so a reviewer can verify).
confidence ≥ 0.85 only for clear rows; 0.5–0.84 partial; < 0.5 guesses.
row_count_visible MUST equal rows.length.`;

const HW_BLOCK_DETECT_SYSTEM = `You are looking at a cropped hardware-sets page. Identify EVERY individual hardware set block on it. Missing a set is the worst possible failure of this task.

A "block" = one hardware set heading (e.g. "HW-01", "HW SET #3", "Set 4", "Group 12", "FHW-7") plus its line items, plus any "opening note" that lists which door marks the set applies to.

STEP 1 — Enumerate every visible set heading on the page FIRST, before drawing any bboxes. Scan the page top-to-bottom. If the page is multi-column, scan column-by-column LEFT-TO-RIGHT, and within each column top-to-bottom. List every heading you see — even ones at the very bottom of a column, even ones that look partial or continued from another page. A heading is any of: "HW-NN", "HW SET NN", "SET N", "GROUP N", "FHW-N", "HARDWARE SET N", "DOOR HARDWARE GROUP N", or similar followed by an ID.

STEP 2 — For each enumerated ID, return the block.

Return STRICTLY valid JSON:
{
  "layout": "single-column" | "two-column" | "three-column" | "tabular" | "mixed",
  "set_ids_visible": [string],   // exhaustive list of every set ID/heading visible (step 1) — in reading order
  "total_blocks_visible": number, // = set_ids_visible.length, redundant safety count
  "blocks": [{
    "set_id": string,
    "header_text": string,
    "opening_note_text": string|null,
    "is_crossed_out": boolean,
    "is_voided_or_removed": boolean,
    "bbox": [x, y, w, h],
    "confidence": number
  }]
}
- blocks.length MUST equal total_blocks_visible. If you cannot draw a confident bbox for a set you enumerated, still emit a block for it with your best-guess bbox and confidence < 0.5 — DO NOT drop it.
- bbox is normalized (0..1) within the cropped image, sized to enclose the heading, the opening note (if any), AND all items belonging to this set.
- For multi-column layouts: a block's bbox stays inside ONE column — it does NOT span across columns. Two adjacent columns produce two side-by-side blocks at similar y, not one wide block.
- opening_note_text = the literal line that lists which openings the set applies to (e.g. "OPENING: 103A, 201, 202A" or "Doors: 100, 100B, 101"). Use null if no such line is visible.
- is_crossed_out: true if the block has a visible strike-through, red X, or "VOID" stamp across it.
- is_voided_or_removed: true if a section is missing or the item list is empty / "N/A".
- Preserve set_id exactly as written (e.g. "HW-1", "Set 3A", "01"). Preserve typos in header_text as visible (e.g. "DOUBLE ENDRY/EGRESS").
- Generous bboxes — overlapping is OK.`;

const HW_ITEMS_EXTRACT_SYSTEM = `You are TRANSCRIBING one hardware set block. Read EVERY line item visible. Missing an item is the worst possible failure of this task.

A "line item" = one numbered/bulleted/quantified line inside the block that names a hardware component (hinges, locks, closers, exit devices, kick plates, weatherstripping, threshold, silencers, stop, holder, electric strike, power supply, card reader, mag lock, gasketing, sweep, astragal, coordinator, flush bolts, dust proof strike, push/pull, pivot, etc.). Sub-headings like "EACH TO HAVE:" / "PROVIDE FOLLOWING:" / a manufacturer banner are NOT items — skip them.

STEP 1 — Scan top-to-bottom and count every line item line in the image. Even if the line is partially unreadable or wraps across two visual rows, COUNT IT ONCE. Set lines_counted_in_block = that integer.

STEP 2 — Emit one entry in items[] for every counted line. items.length MUST equal lines_counted_in_block. Never drop a line because the part number is unreadable — emit it with description filled and the unreadable fields set to null. Never abbreviate the list with "etc." or "…".

Return STRICTLY valid JSON:
{
  "set_id": string,
  "set_name": string|null,
  "header_text_verbatim": string,
  "opening_note_doors": [string],
  "visual_flags": [string],
  "lines_counted_in_block": number,
  "items": [{
    "item_no": string|number|null,
    "qty": number|null,
    "unit": string|null,
    "description": string,
    "catalog_number": string|null,
    "manufacturer": string|null,
    "finish": string|null,
    "notes": string|null,
    "raw_text_seen": string,
    "is_crossed_out": boolean,
    "confidence": number
  }]
}

Rules:
- Read every visible line. "3 Hinges  T4A3786  McKinney  US26D" → qty=3, unit=null, description="Hinges", catalog_number="T4A3786", manufacturer="McKinney", finish="US26D".
- "3 EA  Hinges  T4A3786  McKinney  US26D" → qty=3, unit="EA", description="Hinges".
- "1 PR Flush Bolts  282 12" Ives" → qty=1, unit="PR", description="Flush Bolts", catalog_number="282 12\"", manufacturer="Ives".
- "1 SET Continuous Hinge" → qty=1, unit="SET", description="Continuous Hinge".
- A line with only "1 Closer" or "1 EA Closer  by manufacturer" is still a valid item — emit it with qty=1, description="Closer", others=null.
- A line that wraps onto two visual rows (long part number / long description) counts as ONE item — combine the two rows into one entry.
- Continuation rows ("…cont'd" or items continued on next column/page) — emit them anyway.
- header_text_verbatim = the set's heading line(s) preserving spelling exactly (typos included — e.g. "DOUBLE ENDRY/EGRESS", "CONTINOUS PERIMETER").
- opening_note_doors = if a line near the heading lists which door marks this set applies to (e.g. "OPENING NOTE: 103A, 201, 202A" or "Doors: 100B"), parse it and return the marks as an array. If no such line, return [].
- visual_flags = list any of: "crossed_out", "voided", "red_x_mark", "strikethrough", "marked_unused", "typo_in_heading" (only if the heading clearly contains a misspelling — e.g. ENDRY vs ENTRY).
- is_crossed_out on an item line: true if that specific line has a strike-through.
- Never invent qty, part numbers, manufacturers, or finishes. If unreadable, null. But the LINE must still be emitted.
- Preserve set_id exactly as written.
- raw_text_seen = the literal line as you read it.`;

const ESTIMATOR_REASONING_SYSTEM = EXTRACTION_SYSTEM; // re-use senior-estimator prompt for the final reasoning pass

const HW_FULL_REGION_EXTRACT_SYSTEM = `You are reading an entire hardware-sets region (or a single column of one) from a construction drawing rendered at 300 DPI. The image shows ONE OR MORE hardware sets stacked vertically. Missing a set or an item is the worst possible failure of this task.

OBJECTIVE: Transcribe EVERY hardware set visible AND EVERY line item under each set, in one structured response.

STEP 1 — Enumerate every set heading visible. Scan top-to-bottom. Include partial / continued / crossed-out / VOID-stamped sets — flag them but DO NOT drop them. List the IDs first in set_ids_visible. Common heading formats: "Hardware Group No. XXX", "HW-NN", "HW SET NN", "SET N", "GROUP N", "FHW-N".

STEP 2 — For EACH enumerated set, read EVERY line item beneath its heading until you hit the next set heading (or the bottom of the image). A line item is one line naming a hardware component (hinges, locks, closers, exit devices, kick plates, weatherstripping, threshold, silencers, stops, holders, electric strikes, power supplies, card readers, mag locks, gasketing, sweep, astragal, coordinators, flush bolts, dust proof strike, push/pull, pivot, etc.). Sub-headings like "EACH TO HAVE:" or a manufacturer banner are NOT items — skip them.

Return STRICTLY valid JSON:
{
  "layout": "single-column" | "two-column" | "three-column" | "four-column" | "five-column" | "many-column" | "tabular" | "mixed",
  "set_ids_visible": [string],            // exhaustive list from step 1, reading order
  "sets_visible_count": number,           // = set_ids_visible.length
  "sets": [
    {
      "set_id": string,
      "set_name": string|null,
      "header_text_verbatim": string,
      "opening_note_doors": [string],     // door marks listed near the heading (e.g. "OPENING: 103A, 201" → ["103A","201"])
      "opening_note_text": string|null,
      "visual_flags": [string],           // any of: "crossed_out","voided","red_x_mark","strikethrough","marked_unused","typo_in_heading"
      "is_crossed_out": boolean,
      "is_voided_or_removed": boolean,
      "lines_counted_in_block": number,   // raw line count under this heading BEFORE filtering
      "items": [
        {
          "item_no": string|number|null,
          "qty": number|null,
          "unit": string|null,
          "description": string,
          "catalog_number": string|null,
          "manufacturer": string|null,
          "finish": string|null,
          "notes": string|null,
          "raw_text_seen": string,
          "is_crossed_out": boolean,
          "confidence": number
        }
      ],
      "confidence": number
    }
  ]
}

Rules:
- sets.length MUST equal sets_visible_count. If you cannot draw items for a set you enumerated, still emit an entry for it with items: [] and confidence < 0.5 — DO NOT drop it.
- For EACH set, items.length MUST equal lines_counted_in_block. Never drop a line because the part number is unreadable — emit it with description filled and unreadable fields set to null. Never abbreviate the list with "etc." or "…".
- A line that wraps onto two visual rows (long part number / long description) is ONE item — combine the two rows.
- Continuation rows ("…cont'd") still emit as items.
- Preserve set IDs character-for-character ("Hardware Group No. C265", "HW-1", "Set 3A", "FHW-7", "01").
- Preserve typos in header_text_verbatim exactly as visible (e.g. "DOUBLE ENDRY/EGRESS", "CONTINOUS PERIMETER").
- visual_flags: emit "typo_in_heading" only when the heading clearly contains a misspelling.
- Never invent qty, part numbers, manufacturers, or finishes. If unreadable, null. But the LINE must still be emitted.
- raw_text_seen = the literal line as you read it.`;

const HW_COLUMN_DETECT_SYSTEM = `You are looking at a hardware-sets region from a construction drawing. Your only job: count the columns and locate them.

A hardware-sets sheet may lay sets out in 1, 2, 3, 4, 5 or 6 vertical columns. You must:
1. Count the number of vertical columns of hardware-set content in this image.
2. For each column, return its horizontal extent as normalized x-coordinates (0=left edge, 1=right edge).

Return STRICTLY valid JSON:
{
  "column_count": number,
  "columns": [
    { "x0": number, "x1": number }   // x0 = left edge of column, x1 = right edge, both 0..1
  ]
}

Rules:
- columns.length MUST equal column_count.
- Columns are in left-to-right order.
- Be generous with column widths — slight overlap with the neighbor is fine; tight columns that clip content are worse.
- If you only see one continuous flow of sets top-to-bottom, return column_count=1 with columns=[{x0:0, x1:1}].
- Title blocks / borders on the right edge of an architectural sheet are NOT a column — exclude them.`;

// Canonical key used to dedupe hardware-set IDs across extraction passes AND
// to match door-schedule references against extracted sets. The schedule often
// says "C265" while the spec page header reads "Hardware Group No. C265" or
// "HW-C265" — these must collapse to the same key, otherwise the same set
// gets entered twice (once with items, once as "missing") and doors never
// resolve to their items.
function canonicalSetKey(id) {
  const s = String(id == null ? '' : id).trim();
  if (!s) return '';
  const stripped = s
    .replace(/^(hardware\s+group\s+(?:no\.?\s*)?|hardware\s+set\s*(?:#|no\.?)?\s*|hw\s*set\s*(?:#|no\.?)?\s*|set\s+(?:no\.?\s*)?|group\s+(?:no\.?\s*)?|fhw[-\s]?|hw[-\s]?|#)/i, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase();
  return stripped || s.toUpperCase();
}

/* Format a hardware set id for display: only prepend "HW-" if it isn't already
   prefixed with something hardware-like (avoids "HW-HARDWARE SET 9"). */
function fmtSetId(id) {
  if (id == null || id === '') return '';
  const s = String(id).trim();
  if (/^(hw[-\s]|hardware\b|set\b|group\b|fhw|#)/i.test(s)) return s;
  return 'HW-' + s;
}

async function extractFromPdfPipeline({ apiKey, scope, file, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');

  const callVision = async (system, userText, imageDataUrls, maxTokens = 16000) => {
    const content = [{ type: 'text', text: userText }];
    for (const url of imageDataUrls) content.push({ type: 'image_url', image_url: { url, detail: 'high' } });
    const body = {
      model: REQUIRED_MODEL,
      messages: [
        { role: 'system', content: system },
        { role: 'user', content },
      ],
      response_format: { type: 'json_object' },
      max_completion_tokens: maxTokens,
    };
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
    const text = data.choices?.[0]?.message?.content || '{}';
    const finish = data.choices?.[0]?.finish_reason || null;
    try {
      const parsed = JSON.parse(text);
      Object.defineProperty(parsed, '__finish_reason', { value: finish, enumerable: false });
      return parsed;
    } catch { throw new Error('Model returned invalid JSON'); }
  };

  // ----- PASS 1: Render -----
  onProgress?.({ kind: 'info', text: `Rendering PDF at ${RENDER_TARGET_DPI} DPI (cap ${MAX_RENDER_LONG_EDGE}px long edge)…` });
  // Tracks extraction quality flags — used to mark the workbook as INCOMPLETE
  // when any critical vision call failed silently (caught exception path).
  const extractionFailures = []; // [{ stage, page, region?, message }]
  const recordFailure = (stage, ctx, message) => {
    extractionFailures.push({ stage, ...ctx, message });
    onProgress?.({ kind: 'warn', text: `[INCOMPLETE] ${stage}: ${message}` });
  };
  const pages = await renderPdfPages(file, ({ page, pages, width, height, dpi }) => {
    onProgress?.({ kind: 'ok', text: `Page ${page}/${pages} rendered ${width}×${height} @ ${dpi}dpi` });
  });

  // ----- PASS 2: Classify each page (PARALLEL) -----
  onProgress?.({ kind: 'info', text: `Classifying ${pages.length} page(s) in parallel…` });
  const classifications = await Promise.all(pages.map(async (p) => {
    let res;
    try {
      res = await callVision(PAGE_CLASSIFIER_SYSTEM, `This is page ${p.pageNum} of ${pages.length}, rendered at ${p.dpi} DPI.`, [p.dataUrl]);
    } catch (e) {
      onProgress?.({ kind: 'warn', text: `Classification failed on page ${p.pageNum}: ${e.message}` });
      recordFailure('page_classification', { page: p.pageNum }, e.message);
      res = { regions: [] };
    }
    const regs = Array.isArray(res?.regions) ? res.regions : [];
    regs.forEach((r, idx) => { r.crop_id = `P${p.pageNum}-R${idx + 1}-${r.role || 'other'}`; });
    onProgress?.({ kind: 'ok', text: `Page ${p.pageNum}: ${regs.map(r => r.role).join(', ') || '(no Div 8 content)'}` });
    return { pageNum: p.pageNum, regions: regs, sheet_notes: res?.sheet_notes || '' };
  }));

  // ----- PASS 2b: Title-block extraction (PARALLEL across all pages — title blocks are usually in the bottom-right of every sheet) -----
  onProgress?.({ kind: 'info', text: `Extracting project metadata from title block(s)…` });
  const titleBlockResults = await Promise.all(pages.map(async (p) => {
    try {
      // Title blocks live in bottom-right ~30% of arch sheets. Crop and send.
      const crop = await cropRegion(p.dataUrl, [0.65, 0.65, 0.35, 0.35]);
      const tb = await callVision(TITLE_BLOCK_EXTRACT_SYSTEM, `Title block region from page ${p.pageNum}. Read every visible field.`, [crop.dataUrl]);
      return { pageNum: p.pageNum, ...tb };
    } catch (e) {
      return { pageNum: p.pageNum, error: e.message };
    }
  }));
  // Merge metadata — first non-null per field wins (later pages override only if earlier had null)
  const projectMeta = {};
  titleBlockResults.forEach(tb => {
    ['project_name', 'project_number', 'architect', 'architect_firm', 'owner', 'address', 'drawing_title', 'drawing_number', 'sheet_number', 'date', 'revision'].forEach(k => {
      if (!projectMeta[k] && tb && tb[k]) projectMeta[k] = tb[k];
    });
  });
  // If architect_firm filled but architect didn't, use firm as architect
  if (!projectMeta.architect && projectMeta.architect_firm) projectMeta.architect = projectMeta.architect_firm;
  onProgress?.({ kind: 'ok', text: `Project metadata: ${projectMeta.project_name || '(no name)'} · ${projectMeta.architect || '(no architect)'} · ${projectMeta.project_number || '(no number)'}` });

  // ----- PASS 3: Door schedule rows per page -----
  const doorRows = []; // { ...row, source_page, source_crop_id }
  const doorRegionsTrace = []; // for QA panel
  for (const c of classifications) {
    const doorRegions = c.regions.filter(r => r.role === 'door_schedule');
    if (!doorRegions.length) continue;
    const page = pages.find(p => p.pageNum === c.pageNum);
    for (const reg of doorRegions) {
      let crop;
      try { crop = await cropRegion(page.dataUrl, reg.bbox); }
      catch (e) { onProgress?.({ kind: 'warn', text: `Door region crop failed on page ${c.pageNum}: ${e.message}` }); continue; }
      const stripCount = crop.height >= 1400 ? Math.min(4, Math.max(2, Math.ceil(crop.height / 1200))) : 1;
      const overlap = 0.08;
      const stripCrops = [];
      onProgress?.({ kind: 'info', text: `Extracting door rows from ${reg.crop_id} (${crop.width}×${crop.height}px, ${stripCount} strip${stripCount === 1 ? '' : 's'})…` });
      for (let s = 0; s < stripCount; s++) {
        const y0 = stripCount === 1 ? 0 : Math.max(0, s / stripCount - overlap);
        const y1 = stripCount === 1 ? 1 : Math.min(1, (s + 1) / stripCount + overlap);
        let strip;
        try { strip = await cropRegionStrip(page.dataUrl, reg.bbox, y0, y1); }
        catch (e) { continue; }
        let res;
        try {
          res = await callVision(
            DOOR_ROW_EXTRACT_SYSTEM,
            `This is ${stripCount === 1 ? 'a cropped door schedule' : `STRIP ${s + 1}/${stripCount} of a door schedule`} from page ${c.pageNum}. Transcribe every row visible in THIS image.`,
            [strip.dataUrl],
          );
        } catch (e) {
          onProgress?.({ kind: 'warn', text: `Door row extract failed: ${e.message}` });
          recordFailure('door_row_extract', { page: c.pageNum, region: reg.crop_id }, e.message);
          continue;
        }
        const stripCropPrev = await makePreview(strip.dataUrl);
        stripCrops.push({ strip: s + 1, of: stripCount, preview: stripCropPrev, rowsExtracted: res?.rows?.length || 0 });
        (res?.rows || []).forEach(row => {
          if (!row.mark) return;
          doorRows.push({ ...row, source_page: c.pageNum, source_crop_id: reg.crop_id, source_strip: s + 1 });
        });
      }
      doorRegionsTrace.push({ crop_id: reg.crop_id, pageNum: c.pageNum, label: reg.label, bbox: reg.bbox, strips: stripCrops, totalRows: stripCrops.reduce((n, x) => n + x.rowsExtracted, 0) });
      onProgress?.({ kind: 'ok', text: `${reg.crop_id}: ${stripCrops.reduce((n, x) => n + x.rowsExtracted, 0)} row(s)` });
    }
  }
  // Dedupe by mark, keep highest confidence
  const doorByMark = new Map();
  doorRows.forEach(r => {
    if (!r.mark) return;
    const prev = doorByMark.get(r.mark);
    if (!prev || (r.confidence ?? 0) > (prev.confidence ?? 0)) doorByMark.set(r.mark, r);
  });
  const doors = [...doorByMark.values()];
  onProgress?.({ kind: 'ok', text: `${doors.length} unique door mark(s) after dedupe` });

  // ----- PASS 4: Hardware set blocks per page -----
  const hwSets = new Map(); // set_id -> { id, name, items[], source_page, source_crop_id }
  const hwBlocksTrace = [];
  for (const c of classifications) {
    const hwRegions = c.regions.filter(r => r.role === 'hardware_sets');
    if (!hwRegions.length) continue;
    const page = pages.find(p => p.pageNum === c.pageNum);
    for (const reg of hwRegions) {
      let crop;
      try { crop = await cropRegion(page.dataUrl, reg.bbox); }
      catch (e) {
        onProgress?.({ kind: 'warn', text: `HW region crop failed: ${e.message}` });
        recordFailure('hw_region_crop', { page: c.pageNum, region: reg.crop_id }, e.message);
        continue;
      }

      // ---------- PRIMARY: column-detect → per-column extraction ----------
      // Dense hardware-set sheets often have 4-6 columns of ~30 sets total. Sending the
      // whole region in one call (or a tight per-block crop) loses context. Instead:
      //   1) cheap column-detect call returns horizontal column boundaries
      //   2) for each column, run the all-in-one extractor on a tall narrow strip
      //   3) merge results by set_id
      // This is the same shape the chat UI works in: one focused chunk per call, full
      // vertical context preserved, no block fragmentation.
      onProgress?.({ kind: 'info', text: `Detecting columns within ${reg.crop_id} (${crop.width}×${crop.height}px)…` });
      let colDetectRes;
      try {
        colDetectRes = await callVision(
          HW_COLUMN_DETECT_SYSTEM,
          `Hardware-sets region from page ${c.pageNum}. Count and locate the vertical columns.`,
          [crop.dataUrl],
          2000,
        );
      } catch (e) {
        onProgress?.({ kind: 'warn', text: `Column detect failed for ${reg.crop_id}: ${e.message}. Falling back to single-column extraction.` });
        recordFailure('hw_column_detect', { page: c.pageNum, region: reg.crop_id }, e.message);
        colDetectRes = { column_count: 1, columns: [{ x0: 0, x1: 1 }] };
      }
      let columns = Array.isArray(colDetectRes?.columns) && colDetectRes.columns.length
        ? colDetectRes.columns.map(co => ({
            x0: Math.max(0, Number(co.x0) || 0),
            x1: Math.min(1, Number(co.x1) || 1),
          })).filter(co => co.x1 > co.x0 + 0.02).sort((a, b) => a.x0 - b.x0)
        : [{ x0: 0, x1: 1 }];
      // Pad columns slightly so heading IDs at the column edges aren't clipped
      const padX = 0.015;
      columns = columns.map(co => ({ x0: Math.max(0, co.x0 - padX), x1: Math.min(1, co.x1 + padX) }));
      onProgress?.({ kind: 'ok', text: `${reg.crop_id}: ${columns.length} column(s) detected` });

      // Run extraction on each column in parallel
      const columnResults = await Promise.all(columns.map(async (co, ci) => {
        const colCropId = `${reg.crop_id}-COL${ci + 1}`;
        const [rx, ry, rw, rh] = reg.bbox;
        const colBbox = [rx + co.x0 * rw, ry, (co.x1 - co.x0) * rw, rh];
        let colCrop;
        try { colCrop = await cropRegion(page.dataUrl, colBbox); }
        catch (e) {
          onProgress?.({ kind: 'warn', text: `Column crop failed for ${colCropId}: ${e.message}` });
          recordFailure('hw_column_crop', { page: c.pageNum, region: colCropId }, e.message);
          return null;
        }
        let colRes;
        try {
          colRes = await callVision(
            HW_FULL_REGION_EXTRACT_SYSTEM,
            `Column ${ci + 1}/${columns.length} of a hardware-sets region from page ${c.pageNum}. Read this single column top-to-bottom and transcribe every hardware set heading AND every line item beneath each. Crop dimensions: ${colCrop.width}×${colCrop.height} px at 300 DPI.`,
            [colCrop.dataUrl],
            16000,
          );
        } catch (e) {
          onProgress?.({ kind: 'warn', text: `Column ${ci + 1} extract failed: ${e.message}` });
          recordFailure('hw_column_extract', { page: c.pageNum, region: colCropId }, e.message);
          return null;
        }
        const colSets = Array.isArray(colRes?.sets) ? colRes.sets : [];
        const colTruncated = colRes?.__finish_reason === 'length';
        const colItems = colSets.reduce((n, s) => n + (Array.isArray(s.items) ? s.items.length : 0), 0);
        const colIdsVisible = Array.isArray(colRes?.set_ids_visible) ? colRes.set_ids_visible : [];
        onProgress?.({ kind: 'ok', text: `${colCropId}: ${colSets.length} set(s), ${colItems} item(s)${colTruncated ? ' [TRUNCATED]' : ''}${colIdsVisible.length > colSets.length ? ` (${colIdsVisible.length - colSets.length} ID(s) enumerated but not emitted)` : ''}` });
        return { colCropId, sets: colSets, idsVisible: colIdsVisible, truncated: colTruncated, crop: colCrop };
      }));

      // Aggregate everything into a single fullSets-like shape so the merge logic below
      // can stay shared with the block-detect fallback.
      const fullSets = [];
      const fullIdsVisible = [];
      let fullTruncated = false;
      columnResults.forEach((cr) => {
        if (!cr) return;
        fullSets.push(...cr.sets);
        fullIdsVisible.push(...cr.idsVisible);
        if (cr.truncated) fullTruncated = true;
      });
      const fullItemsTotal = fullSets.reduce((n, s) => n + (Array.isArray(s.items) ? s.items.length : 0), 0);
      const fullLayout = columns.length === 1 ? 'single-column'
        : columns.length === 2 ? 'two-column'
        : columns.length === 3 ? 'three-column'
        : columns.length === 4 ? 'four-column'
        : columns.length === 5 ? 'five-column'
        : 'many-column';

      if (fullSets.length) {
        onProgress?.({ kind: 'ok', text: `${reg.crop_id} TOTAL: ${fullSets.length} set(s), ${fullItemsTotal} item(s) across ${columns.length} column(s)${fullTruncated ? ' [SOME COLUMNS TRUNCATED]' : ''}` });
      }

      const ingestSet = (setObj, sourceCropId) => {
        const id = String(setObj.set_id || '').trim();
        if (!id) return;
        // Canonical key for dedup: strip common prefixes & whitespace so "Hardware Group No. C265",
        // "HARDWARE GROUP C265", "Group C265", and "C265" all merge into the same entry.
        const dedupKey = canonicalSetKey(id) || id;
        const incomingItems = (Array.isArray(setObj.items) ? setObj.items : [])
          .map(it => ({ ...it, source_page: c.pageNum, source_crop_id: sourceCropId }));
        const existing = hwSets.get(dedupKey);
        if (!existing) {
          hwSets.set(dedupKey, {
            id, // keep the original display string from whichever column found it first
            name: setObj.set_name || null,
            header_verbatim: setObj.header_text_verbatim || '',
            opening_note_doors: Array.isArray(setObj.opening_note_doors) ? setObj.opening_note_doors : [],
            opening_note_text: setObj.opening_note_text || null,
            visual_flags: Array.isArray(setObj.visual_flags) ? setObj.visual_flags : [],
            is_crossed_out: !!setObj.is_crossed_out,
            is_voided: !!setObj.is_voided_or_removed,
            items: incomingItems,
            source_page: c.pageNum,
            source_crop_id: sourceCropId,
          });
        } else {
          // Prefer the longer header text (more informative)
          if ((setObj.header_text_verbatim || '').length > (existing.header_verbatim || '').length) {
            existing.header_verbatim = setObj.header_text_verbatim;
          }
          // Merge items by description+catalog+qty
          const seen = new Set(existing.items.map(it => (it.description || '').toLowerCase().replace(/\s+/g,' ').trim() + '|' + (it.catalog_number || '').toLowerCase().trim() + '|' + (it.qty ?? '')));
          incomingItems.forEach(it => {
            const k = (it.description || '').toLowerCase().replace(/\s+/g,' ').trim() + '|' + (it.catalog_number || '').toLowerCase().trim() + '|' + (it.qty ?? '');
            if (!seen.has(k)) { existing.items.push(it); seen.add(k); }
          });
          if (!existing.opening_note_doors?.length && Array.isArray(setObj.opening_note_doors) && setObj.opening_note_doors.length) existing.opening_note_doors = setObj.opening_note_doors;
          existing.visual_flags = [...new Set([...(existing.visual_flags || []), ...(Array.isArray(setObj.visual_flags) ? setObj.visual_flags : [])])];
        }
      };
      fullSets.forEach(s => {
        const sourceCropId = `${reg.crop_id}-${String(s.set_id || '').replace(/\s+/g,'_')}`;
        ingestSet(s, sourceCropId);
        hwBlocksTrace.push({
          crop_id: sourceCropId,
          pageNum: c.pageNum,
          set_id: s.set_id,
          header: s.header_text_verbatim || '',
          preview: null,
          items: (s.items || []).length,
          opening_note_doors: s.opening_note_doors || [],
          visual_flags: s.visual_flags || [],
          pass: 'all-in-one',
        });
      });

      // Run the block-detect fallback ONLY when column-based extraction got NOTHING for this
      // region. Truncation or partial column under-reads are acceptable (the per-column trust
      // is already higher than per-block fragmenting); we don't want stub entries that bypass
      // dedup and double-count sets.
      const needFallback = fullSets.length === 0;
      if (!needFallback) continue;

      onProgress?.({ kind: 'warn', text: `${reg.crop_id} column extraction returned 0 sets — falling back to block-detect pipeline.` });

      onProgress?.({ kind: 'info', text: `Detecting hardware blocks within ${reg.crop_id} (${crop.width}×${crop.height}px)…` });
      let blockRes;
      try {
        blockRes = await callVision(HW_BLOCK_DETECT_SYSTEM, `Detect each hardware set block within this cropped region from page ${c.pageNum}.`, [crop.dataUrl]);
      } catch (e) {
        onProgress?.({ kind: 'warn', text: `Block detect failed: ${e.message}` });
        recordFailure('hw_block_detect', { page: c.pageNum, region: reg.crop_id }, e.message);
        blockRes = { blocks: [], set_ids_visible: [], total_blocks_visible: 0, layout: 'single-column' };
      }
      let blocks = Array.isArray(blockRes?.blocks) ? blockRes.blocks : [];
      const idsVisible = Array.isArray(blockRes?.set_ids_visible) ? blockRes.set_ids_visible.filter(Boolean) : [];
      const layout = String(blockRes?.layout || '').toLowerCase();
      onProgress?.({ kind: 'ok', text: `${reg.crop_id}: ${blocks.length} block(s) drawn · ${idsVisible.length} ID(s) enumerated · layout=${layout || '?'}` });

      // Fallback sweep — only fires when the first pass under-counts.
      // Triggers: (a) detector returned 0 blocks; (b) detector enumerated more IDs than it drew blocks for;
      // (c) detector claims multi-column layout (which the single-shot pass routinely under-counts).
      const knownIds = new Set(blocks.map(b => String(b.set_id || '').trim()).filter(Boolean));
      const missingFromEnum = idsVisible.filter(id => !knownIds.has(String(id).trim()));
      const layoutColumns = layout.includes('three') ? 3 : layout.includes('two') ? 2 : 1;
      const shouldSweep = blocks.length === 0
        || missingFromEnum.length > 0
        || layoutColumns > 1
        || (idsVisible.length && blocks.length < idsVisible.length);

      if (shouldSweep) {
        const sweepCols = Math.max(2, layoutColumns || 2);
        onProgress?.({ kind: 'warn', text: `${reg.crop_id}: re-sweeping in ${sweepCols} column strip(s) (initial pass found ${blocks.length}/${idsVisible.length || '?'} sets${missingFromEnum.length ? `, missing: ${missingFromEnum.slice(0,6).join(', ')}${missingFromEnum.length>6?'…':''}` : ''})…` });
        const colOverlap = 0.04;
        const colResults = await Promise.all(
          Array.from({ length: sweepCols }, async (_, col) => {
            const x0 = Math.max(0, col / sweepCols - colOverlap);
            const x1 = Math.min(1, (col + 1) / sweepCols + colOverlap);
            const [rx, ry, rw, rh] = reg.bbox;
            const colBbox = [rx + x0 * rw, ry, (x1 - x0) * rw, rh];
            let colCrop;
            try { colCrop = await cropRegion(page.dataUrl, colBbox); }
            catch (e) { return { col, x0, x1, blocks: [] }; }
            let colRes;
            try {
              colRes = await callVision(
                HW_BLOCK_DETECT_SYSTEM,
                `Column ${col + 1}/${sweepCols} of a hardware-sets region from page ${c.pageNum}. Treat THIS image as a single column — enumerate every set ID visible top-to-bottom.`,
                [colCrop.dataUrl],
              );
            } catch (e) { return { col, x0, x1, blocks: [] }; }
            const cb = Array.isArray(colRes?.blocks) ? colRes.blocks : [];
            // Reproject each column-local bbox back to region-relative coords
            cb.forEach(b => {
              const [bx, by, bw, bh] = b.bbox || [0, 0, 1, 1];
              b.bbox = [x0 + bx * (x1 - x0), by, bw * (x1 - x0), bh];
            });
            return { col, x0, x1, blocks: cb, idsVisible: Array.isArray(colRes?.set_ids_visible) ? colRes.set_ids_visible : [] };
          }),
        );
        // Merge: dedupe by set_id, prefer higher confidence; keep originals where no column hit
        const merged = new Map();
        const pushBlock = (b) => {
          const id = String(b.set_id || '').trim();
          if (!id) return;
          const prev = merged.get(id);
          if (!prev || (b.confidence ?? 0) > (prev.confidence ?? 0)) merged.set(id, b);
        };
        blocks.forEach(pushBlock);
        colResults.forEach(cr => cr.blocks.forEach(pushBlock));
        const mergedBlocks = [...merged.values()];
        const colIdsEnum = colResults.flatMap(cr => cr.idsVisible || []);
        const allIdsEnum = [...new Set([...idsVisible, ...colIdsEnum])];
        // If after merging we still see fewer blocks than IDs enumerated by ANY pass, emit stub blocks
        // so we at least record the set IDs we know are there (items pass will try to read them).
        allIdsEnum.forEach(id => {
          const k = String(id).trim();
          if (!k || merged.has(k)) return;
          merged.set(k, { set_id: k, header_text: k, bbox: [0, 0, 1, 1], confidence: 0.3, _stub: true });
        });
        const finalBlocks = [...merged.values()];
        onProgress?.({ kind: 'ok', text: `${reg.crop_id}: re-sweep merged → ${finalBlocks.length} block(s) (${mergedBlocks.length} drawn + ${finalBlocks.length - mergedBlocks.length} stub).` });
        blocks = finalBlocks;
      }

      // Last-resort fallback: if STILL nothing, treat the whole region as one block
      const blocksToProcess = blocks.length ? blocks : [{ set_id: '(unknown)', header_text: '', bbox: [0, 0, 1, 1], confidence: 0.5 }];

      // PARALLEL extract items for each block
      const blockResults = await Promise.all(blocksToProcess.map(async (b, bi) => {
        const blockCropId = `${reg.crop_id}-B${bi + 1}-${b.set_id}`;
        // Pad bbox by ~3% on each side so items near edges aren't clipped, then clamp to region
        const padBlock = ([x, y, w, h]) => {
          const px = 0.03, py = 0.04;
          const nx = Math.max(0, x - px);
          const ny = Math.max(0, y - py);
          const nw = Math.min(1 - nx, w + px * 2);
          const nh = Math.min(1 - ny, h + py * 2);
          return [nx, ny, nw, nh];
        };
        const paddedBlockBbox = padBlock(b.bbox || [0, 0, 1, 1]);
        const [rx, ry, rw, rh] = reg.bbox;
        const [bx, by, bw, bh] = paddedBlockBbox;
        const pageBbox = [rx + bx * rw, ry + by * rh, bw * rw, bh * rh];
        let blockCrop;
        try { blockCrop = await cropRegion(page.dataUrl, pageBbox); }
        catch (e) { return null; }

        // Helper: one items-extraction call against a (sub)crop
        const callItems = async (imgDataUrl, label) => {
          try {
            return await callVision(
              HW_ITEMS_EXTRACT_SYSTEM,
              `This is ${label} of hardware block "${b.set_id}" from page ${c.pageNum}. Transcribe every line item visible AND capture the opening_note_doors and any visual_flags (crossed_out, typo, voided).`,
              [imgDataUrl],
            );
          } catch (e) {
            onProgress?.({ kind: 'warn', text: `Item extract failed for ${b.set_id} (${label}): ${e.message}` });
            recordFailure('hw_item_extract', { page: c.pageNum, set: b.set_id, label }, e.message);
            return null;
          }
        };

        // First attempt: whole block in one shot — unless it's clearly tall enough to risk truncation
        const tallThreshold = 1400;
        const isTall = blockCrop.height >= tallThreshold;
        let itemRes = isTall ? null : await callItems(blockCrop.dataUrl, 'this block');

        // Detect undercount / truncation / silent-zero; trigger strip fallback if any of:
        //   - tall block from the start
        //   - response truncated (finish_reason = length)
        //   - model self-reports more lines than items emitted
        //   - first pass returned ZERO items but block isn't marked void/crossed-out
        //     (silent-zero is the dominant failure mode for unusual block layouts)
        const linesCounted = itemRes?.lines_counted_in_block ?? null;
        const truncated = itemRes?.__finish_reason === 'length';
        const itemsEmitted = Array.isArray(itemRes?.items) ? itemRes.items.length : 0;
        const undercount = typeof linesCounted === 'number' && linesCounted > itemsEmitted + 1;
        const isMarkedVoid = !!b.is_crossed_out || !!b.is_voided_or_removed;
        const silentZero = itemsEmitted === 0 && !isMarkedVoid;

        let aggregatedItems = Array.isArray(itemRes?.items) ? itemRes.items : [];
        let aggregatedHeader = itemRes?.header_text_verbatim || '';
        let aggregatedFlags = Array.isArray(itemRes?.visual_flags) ? itemRes.visual_flags : [];
        let aggregatedOpenDoors = Array.isArray(itemRes?.opening_note_doors) ? itemRes.opening_note_doors : [];
        let aggregatedConf = itemRes?.confidence ?? b.confidence ?? 0.6;

        if (isTall || truncated || undercount || silentZero) {
          const reason = isTall ? `tall (${blockCrop.height}px)`
            : truncated ? 'truncated'
            : silentZero ? 'first-pass returned 0 items'
            : `undercount (${itemsEmitted}/${linesCounted})`;
          // For silent-zero on a normal-size block, try 2 strips. For tall blocks, more.
          const stripCount = silentZero && !isTall
            ? 2
            : Math.min(4, Math.max(2, Math.ceil(blockCrop.height / 900)));
          onProgress?.({ kind: 'warn', text: `${blockCropId}: re-extracting in ${stripCount} strip(s) (${reason})…` });
          const stripOverlap = 0.10;
          const stripResults = await Promise.all(
            Array.from({ length: stripCount }, async (_, s) => {
              const y0 = Math.max(0, s / stripCount - stripOverlap);
              const y1 = Math.min(1, (s + 1) / stripCount + stripOverlap);
              let strip;
              try { strip = await cropRegionStrip(page.dataUrl, pageBbox, y0, y1); }
              catch (e) { return null; }
              return callItems(strip.dataUrl, `STRIP ${s + 1}/${stripCount}`);
            }),
          );
          // Merge: dedupe items by (description + catalog_number + qty + raw_text_seen prefix)
          const seen = new Set();
          const merged = [];
          const pushUnique = (it) => {
            const key = (it.description || '').toLowerCase().replace(/\s+/g, ' ').trim() + '|'
                      + (it.catalog_number || '').toLowerCase().trim() + '|'
                      + (it.qty ?? '') + '|'
                      + String(it.raw_text_seen || '').toLowerCase().replace(/\s+/g, ' ').trim().slice(0, 60);
            if (seen.has(key)) return;
            seen.add(key);
            merged.push(it);
          };
          // Keep first-attempt items first (if any), then strip items
          aggregatedItems.forEach(pushUnique);
          stripResults.forEach(sr => {
            if (!sr) return;
            (Array.isArray(sr.items) ? sr.items : []).forEach(pushUnique);
            if (!aggregatedHeader && sr.header_text_verbatim) aggregatedHeader = sr.header_text_verbatim;
            if (Array.isArray(sr.visual_flags)) aggregatedFlags = [...new Set([...aggregatedFlags, ...sr.visual_flags])];
            if (!aggregatedOpenDoors.length && Array.isArray(sr.opening_note_doors)) aggregatedOpenDoors = sr.opening_note_doors;
          });
          aggregatedItems = merged;
          onProgress?.({ kind: 'ok', text: `${blockCropId}: strip pass → ${aggregatedItems.length} item(s)` });
        }

        if (!aggregatedItems.length && !itemRes) return null;

        aggregatedItems.forEach(it => { it.source_page = c.pageNum; it.source_crop_id = blockCropId; });
        const blockPreview = await makePreview(blockCrop.dataUrl);
        return {
          blockCropId,
          setId: itemRes?.set_id || b.set_id,
          setName: itemRes?.set_name || b.header_text || null,
          headerVerbatim: aggregatedHeader || b.header_text || '',
          openingNoteDoors: aggregatedOpenDoors,
          openingNoteText: b.opening_note_text || null,
          visualFlags: aggregatedFlags,
          isCrossedOut: !!b.is_crossed_out,
          isVoided: !!b.is_voided_or_removed,
          headerText: b.header_text || '',
          preview: blockPreview,
          items: aggregatedItems,
          confidence: aggregatedConf,
        };
      }));

      for (const r of blockResults) {
        if (!r) continue;
        hwBlocksTrace.push({ crop_id: r.blockCropId, pageNum: c.pageNum, set_id: r.setId, header: r.headerText || r.headerVerbatim, preview: r.preview, items: r.items.length, opening_note_doors: r.openingNoteDoors, visual_flags: r.visualFlags });
        // Route through the same canonical-key dedup as the column pass.
        ingestSet({
          set_id: r.setId,
          set_name: r.setName,
          header_text_verbatim: r.headerVerbatim,
          opening_note_doors: r.openingNoteDoors,
          opening_note_text: r.openingNoteText,
          visual_flags: r.visualFlags,
          is_crossed_out: r.isCrossedOut,
          is_voided_or_removed: r.isVoided,
          items: r.items,
        }, r.blockCropId);
        onProgress?.({ kind: 'ok', text: `${r.blockCropId}: ${r.items.length} item(s)${r.openingNoteDoors.length ? ` · opening note: ${r.openingNoteDoors.join(', ')}` : ''}${r.visualFlags.length ? ` · flags: ${r.visualFlags.join(', ')}` : ''}` });
      }
    }
  }
  const hwSetsArr = [...hwSets.values()];
  const totalItems = hwSetsArr.reduce((n, s) => n + s.items.length, 0);
  onProgress?.({ kind: 'ok', text: `${hwSetsArr.length} hardware set(s) extracted with ${totalItems} total item(s)` });
  const emptySets = hwSetsArr.filter(s => (!s.items || s.items.length === 0) && !s.is_crossed_out && !s.is_voided);
  if (emptySets.length) {
    onProgress?.({ kind: 'warn', text: `${emptySets.length} set(s) returned 0 items (not voided): ${emptySets.map(s => s.id).join(', ')}. Check the QA panel for source crops; consider re-running on those pages alone.` });
  }

  // ----- Reconcile door references to extracted hardware sets via canonical key.
  // Doors come in with raw hardware_set strings from the schedule (e.g. "C265", "10", "1.0").
  // hwSets is keyed by canonicalSetKey which strips prefixes like "Hardware Group No."
  // and uppercases. If the schedule's string and the spec page's header don't match
  // verbatim, the door looks like it references a "missing" set — even though the
  // set exists with items. Rewrite each door.hardware_set to point at the set.id
  // chosen during dedup, so downstream lookups (hwSets.get, door_analysis.filter,
  // extractedSetIds, mapping) all resolve correctly without further special-casing.
  const canonicalToDisplayId = new Map();
  hwSets.forEach((set, key) => { canonicalToDisplayId.set(key, set.id); });
  doors.forEach(d => {
    if (!d.hardware_set) return;
    const key = canonicalSetKey(d.hardware_set);
    if (!key) return;
    const displayId = canonicalToDisplayId.get(key);
    if (displayId && displayId !== d.hardware_set) {
      d.raw_hardware_set = d.hardware_set; // keep original for source trace
      d.hardware_set = displayId;
    }
  });
  // Rebuild hwSets index by display id so hwSets.get(d.hardware_set) works.
  const hwSetsByDisplayId = new Map();
  hwSets.forEach(set => { if (set.id) hwSetsByDisplayId.set(set.id, set); });

  // ----- PASS 5: Build Door↔Hardware Mapping -----
  const mapping = []; // { door_mark, hardware_set, item_no, qty, description, catalog_number, manufacturer, finish, notes, status }
  for (const d of doors) {
    if (!d.hardware_set) {
      mapping.push({ door_mark: d.mark, hardware_set: null, item_no: null, qty: null, description: '(no hardware set assigned to this door)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'NO_HW_SET', source_page: d.source_page });
      continue;
    }
    const set = hwSetsByDisplayId.get(d.hardware_set) || hwSets.get(canonicalSetKey(d.hardware_set));
    if (!set) {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: '(hardware set not found in spec)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED', source_page: d.source_page });
      continue;
    }
    if (!set.items.length) {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: '(hardware set has no extracted items)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED', source_page: set.source_page });
      continue;
    }
    set.items.forEach((it, i) => {
      mapping.push({
        door_mark: d.mark,
        hardware_set: d.hardware_set,
        item_no: it.item_no ?? (i + 1),
        qty: it.qty,
        description: it.description || '',
        catalog_number: it.catalog_number || null,
        manufacturer: it.manufacturer || null,
        finish: it.finish || null,
        notes: it.notes || null,
        status: 'OK',
        source_page: it.source_page,
        source_crop_id: it.source_crop_id,
      });
    });
  }

  // ----- PASS 6: Estimator reasoning over the assembled data -----
  // Pre-compute concrete findings (mismatches, voided sets, typos) so the reasoning model can
  // produce SPECIFIC RFIs like the reference output rather than generic ones.
  const sourcePageRef = pages.length ? `A${901 + (pages[0]?.pageNum || 1) - 1}` : 'A901';

  const findings = [];
  // 1. Set opening-note vs door-schedule mismatches
  hwSetsArr.forEach(s => {
    if (!s.opening_note_doors?.length) return;
    const setDoorsFromSchedule = doors.filter(d => d.hardware_set === s.id).map(d => d.mark);
    const inNoteOnly = s.opening_note_doors.filter(m => !setDoorsFromSchedule.includes(m));
    const inScheduleOnly = setDoorsFromSchedule.filter(m => !s.opening_note_doors.includes(m));
    if (inScheduleOnly.length || inNoteOnly.length) {
      findings.push({
        kind: 'schedule_set_mismatch',
        set_id: s.id,
        opening_note_doors: s.opening_note_doors,
        schedule_mapped_doors: setDoorsFromSchedule,
        in_note_only: inNoteOnly,
        in_schedule_only: inScheduleOnly,
        source: `${sourcePageRef} · ${s.source_crop_id || ''}`,
      });
    }
  });
  // 2. Hardware sets flagged as crossed-out / voided
  hwSetsArr.forEach(s => {
    if (s.is_crossed_out || s.is_voided || (s.visual_flags || []).some(f => /cross|void|strike|red_x/i.test(f))) {
      findings.push({ kind: 'voided_set', set_id: s.id, header: s.header_verbatim || s.name, flags: s.visual_flags || [], source: `${sourcePageRef} · ${s.source_crop_id || ''}` });
    }
  });
  // 3. Header typos detected by vision
  hwSetsArr.forEach(s => {
    if ((s.visual_flags || []).some(f => /typo/i.test(f))) {
      findings.push({ kind: 'header_typo', set_id: s.id, header_verbatim: s.header_verbatim, source: `${sourcePageRef} · ${s.source_crop_id || ''}` });
    }
  });
  // 4. Hardware sets referenced in opening notes but not assigned to any door in the schedule
  hwSetsArr.forEach(s => {
    const setDoorsFromSchedule = doors.filter(d => d.hardware_set === s.id).map(d => d.mark);
    if (s.items.length > 0 && setDoorsFromSchedule.length === 0 && (!s.opening_note_doors || s.opening_note_doors.length === 0)) {
      findings.push({ kind: 'unused_set', set_id: s.id, header: s.header_verbatim || s.name, source: `${sourcePageRef} · ${s.source_crop_id || ''}` });
    }
  });
  // 5. Door schedule references HW set with no extracted items
  doors.forEach(d => {
    if (!d.hardware_set) return;
    const s = hwSets.get(d.hardware_set);
    if (!s || s.items.length === 0) {
      findings.push({ kind: 'set_no_items', set_id: d.hardware_set, door_mark: d.mark, source: `${sourcePageRef} · ${d.source_crop_id || ''}` });
    }
  });
  // 6. Door type vs set mismatch (e.g. double door mapped to single-door set name)
  doors.forEach(d => {
    if (!d.hardware_set) return;
    const s = hwSets.get(d.hardware_set);
    if (!s) return;
    const isDouble = /double|pair|GL\/MFT|GL.MFT/i.test(`${d.door_type || ''} ${d.opening_type || ''} ${(d.remarks || []).join(' ')}`);
    const setLooksSingle = /single|office|interior office/i.test(s.header_verbatim || s.name || '');
    if (isDouble && setLooksSingle) {
      findings.push({ kind: 'double_door_single_set', door_mark: d.mark, set_id: d.hardware_set, set_header: s.header_verbatim || s.name, source: `${sourcePageRef}` });
    }
  });

  onProgress?.({ kind: 'info', text: `Pre-computed ${findings.length} concrete finding(s) for reasoning pass` });

  // Build a compact JSON payload of raw doors + sets, then ask gpt-5.5 to produce the full senior-estimator JSON.
  onProgress?.({ kind: 'info', text: `Running estimator reasoning on assembled data…` });
  const reasoningPayload = {
    scope_type: scope || 'Supply & Installation',
    source_page_ref: sourcePageRef,
    project_meta: projectMeta,
    findings,
    doors: doors.map(d => ({
      mark: d.mark, room_or_location: d.room_or_location, door_type: d.door_type,
      interior_or_exterior: d.interior_or_exterior, size: d.size,
      door_material: d.door_material, door_finish: d.door_finish, glazing: d.glazing,
      frame_type: d.frame_type, frame_material: d.frame_material, frame_finish: d.frame_finish,
      fire_rating: d.fire_rating, hardware_set: d.hardware_set,
      remarks: d.remarks || [], confidence: d.confidence ?? 0.7,
    })),
    hardware_sets: hwSetsArr.map(s => ({
      id: s.id, name: s.name, header_verbatim: s.header_verbatim,
      opening_note_doors: s.opening_note_doors || [],
      visual_flags: s.visual_flags || [],
      is_crossed_out: !!s.is_crossed_out, is_voided: !!s.is_voided,
      items: s.items.map(it => ({ qty: it.qty, description: it.description, catalog_number: it.catalog_number, manufacturer: it.manufacturer, finish: it.finish })),
    })),
  };
  let reasoning;
  try {
    const body = {
      model: REQUIRED_MODEL,
      messages: [
        { role: 'system', content: ESTIMATOR_REASONING_SYSTEM },
        { role: 'user', content: `The selected project scope is: ${scope || 'Supply & Installation'}

The door schedule and hardware sets below were transcribed from the project PDF by an image-based extraction pipeline. The system has ALSO pre-computed concrete findings (mismatches, voided sets, typos, unused sets, single-vs-double-door mismatches) — use them as the primary source of truth for risks and RFIs.

CRITICAL — YOU MUST PRODUCE SPECIFIC, GROUNDED RFIs. Generic warnings are unacceptable.

For EACH item in the "findings" array, emit one RFI in rfi_log with:
  - priority: high (for schedule_set_mismatch / set_no_items / voided_set / double_door_single_set), medium (for header_typo / unused_set)
  - category: a short bucket like "Schedule / hardware set mismatch", "Voided hardware set", "Typo / exact wording", "Unused hardware sets", "Egress set usage mismatch", "Fire riser room", "Double door mapped to single set"
  - question: a specific, grounded sentence referencing the exact set IDs and door marks involved. Use the form of the reference RFIs (e.g. "Set 1 opening note lists 103A, 201, 202A, but the door schedule maps multiple doors to Set 1. <-- ACTUAL DOORS -->"). Quote text verbatim from header_verbatim when relevant.
  - affected_openings: the door marks from in_schedule_only / in_note_only / affected door for the finding
  - recommendation: what to confirm / do (e.g. "Confirm intended Set 1 usage before final pricing.", "Do not carry Set 9 unless architect confirms it is active.")
  - status: "Open"
  - source: use the source field from the finding (e.g. "A901 · P3-R2-hardware_sets-B4-Set 4")
  - reason: same as recommendation or a short justification

Then, beyond findings, GENERATE ADDITIONAL RFIs across as many of the following categories as the data supports — emit at least one RFI per category that has any matching openings:

  • Fire / smoke rating — UL listing across door + frame + hardware; smoke gasketing per egress path; temperature-rise cores at exit stair enclosures (IBC 716). Cite door marks with non-empty fire_rating.
  • Egress / exit devices — exit device type (rim/mortise/CVR/SVR), trim function (passage/classroom/storeroom/nightlatch), dogging vs non-dogging, alarm features. Cite doors with panic/exit/CVR/SVR remarks.
  • Access control / electrified hardware — power supply provision, low-voltage cabling, EAC head-end, fire-alarm release tie-in, commissioning responsibility. Trigger on CR/EL/DPS/RX/EH/maglock/electric strike/AO remarks.
  • ADA / automatic operators — ANSI A156.10 vs A156.19, push-plate / wave-plate actuator location and mounting heights, vestibule interlock, 120 V provision.
  • Exterior / weather — threshold detail, weatherstrip, sweep, drip cap; HM vs storefront/aluminum scope split; finish + colour.
  • Pair / double-leaf openings — coordinators for rated pairs, astragal type, flush bolts at inactive leaf, active/inactive trim.
  • Keying / cylinders — master-key structure, keyway, SFIC vs LFIC vs conventional, restricted keyway, construction core changeover, key counts.
  • Acoustic / STC-rated — STC value, certified assembly, automatic door bottom, perimeter gasketing, third-party test report at submittal.
  • High-security / sensitive rooms — server / electrical / vault / safe-room; restricted keyway, key-management, ballistic/forced-entry rating.
  • Existing / remodel conditions — re-use vs new for door / frame / hardware, frame prep condition, field-measure requirement, keying continuity.
  • Glazing / vision lites — tempered vs laminated vs wired vs fire-rated ceramic, thickness, film/tint, UL listing for rated glazing.
  • Schedule completeness — missing sizes, missing finishes, ambiguous frame type, unreadable rows.
  • Submittal / lead time — submittal due dates, hardware approval turn-around, ROJ dates for HM frames, wood doors, finish hardware, electrified components.
  • Scope split — Div 08 vs Div 26 (power) vs Div 27/28 (low-voltage / head-end) vs Div 10 (toilet partitions) vs Div 12 (window treatments) where overlap exists.
  • Submittal coordination — anchor templates, electrified hardware riser diagram, keying meeting attendance.

Aim for 12-25 RFIs total for a typical project. Quality and specificity matter — every RFI must reference concrete door marks or set IDs from the data.

ALSO populate:
- project_risks: minimum 6 entries (more if data supports) covering the same categories as the RFIs — each with severity, category, issue (with concrete refs), affected_openings as door marks, and a specific recommendation
- door_analysis: opening_type, hardware_status, install_complexity, risk_level, special_conditions (use the remarks field as a hint — CR/EL/DPS/panic/AO etc.), issues, recommendations, rfi_required (true for any door referenced in a finding), rfi_questions, confidence
- hardware_set_review: referenced_by_doors, status, missing_or_unclear_items (cite specific items like "Set 9 listed as Passage Lock but crossed out"), special_coordination, estimator_note (use header_verbatim if it contains useful info)
- estimator_notes: 4-8 specific observations
- bid_recommendations: scope-relevant notes + exclusions + allowances + coordination items, grounded in the actual data
- project_summary: all counts + overall_bid_risk verdict + a meaty 4-6 sentence estimator_summary

DO NOT INVENT doors or hardware items not in the input. Stick to what is present. Cite door marks and set IDs verbatim.

DATA:
${JSON.stringify(reasoningPayload)}` },
      ],
      response_format: { type: 'json_object' },
      max_completion_tokens: 16000,
    };
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
    reasoning = JSON.parse(data.choices?.[0]?.message?.content || '{}');
    const got = (reasoning.project_risks?.length || 0) + (reasoning.rfi_log?.length || 0);
    onProgress?.({ kind: 'ok', text: `Reasoning pass returned ${reasoning.project_risks?.length || 0} risk(s), ${reasoning.rfi_log?.length || 0} RFI(s)` });
    if (got === 0) onProgress?.({ kind: 'warn', text: 'Reasoning pass returned 0 risks and 0 RFIs — will synthesize from raw data' });
  } catch (e) {
    onProgress?.({ kind: 'warn', text: `Reasoning pass failed: ${e.message} — synthesizing from raw data` });
    reasoning = null;
  }

  // ----- Assemble final analysis -----
  // Prefer reasoning output but ensure doors/sets are present + carry source trace
  const reasoningDoors = reasoning?.door_analysis || [];
  const reasoningSets = reasoning?.hardware_set_review || [];
  const reasoningDoorByMark = new Map(reasoningDoors.map(d => [d.mark, d]));
  const reasoningSetById = new Map(reasoningSets.map(s => [s.hardware_set, s]));

  const door_analysis = doors.map(d => {
    const r = reasoningDoorByMark.get(d.mark) || {};
    return {
      mark: d.mark,
      room_or_location: d.room_or_location || r.room_or_location || null,
      door_type: d.door_type || r.door_type || null,
      opening_type: r.opening_type || null,
      interior_or_exterior: d.interior_or_exterior || r.interior_or_exterior || null,
      size: d.size || r.size || { width: null, height: null, thickness: null },
      door_material: d.door_material || r.door_material || null,
      door_finish: d.door_finish || r.door_finish || null,
      glazing: d.glazing || r.glazing || null,
      frame_type: d.frame_type || r.frame_type || null,
      frame_material: d.frame_material || r.frame_material || null,
      frame_finish: d.frame_finish || r.frame_finish || null,
      fire_rating: d.fire_rating || r.fire_rating || null,
      hardware_set: d.hardware_set || r.hardware_set || null,
      remarks: d.remarks || r.remarks || [],
      hardware_status: r.hardware_status || 'review required',
      install_complexity: r.install_complexity || 'medium',
      risk_level: r.risk_level || (d.fire_rating ? 'medium' : 'low'),
      special_conditions: r.special_conditions || [],
      issues: r.issues || [],
      recommendations: r.recommendations || [],
      rfi_required: !!r.rfi_required,
      rfi_questions: r.rfi_questions || [],
      confidence: d.confidence ?? r.confidence ?? 0.7,
      // Source trace
      source_page: d.source_page,
      source_crop_id: d.source_crop_id,
      raw_text_seen: d.raw_text_seen || '',
    };
  });

  const hardware_set_review = hwSetsArr.map(s => {
    const r = reasoningSetById.get(s.id) || {};
    const refs = door_analysis.filter(d => d.hardware_set === s.id).map(d => d.mark);
    return {
      hardware_set: s.id,
      referenced_by_doors: refs,
      status: r.status || (s.items.length ? 'complete' : 'incomplete'),
      items: s.items.map((it, i) => ({
        item_no: it.item_no ?? (i + 1),
        qty: it.qty,
        unit: it.unit || '',
        desc: it.description || '',
        part: it.catalog_number || '',
        mfr: it.manufacturer || '',
        finish: it.finish || '',
        notes: it.notes || '',
        source_page: it.source_page,
        source_crop_id: it.source_crop_id,
        raw_text_seen: it.raw_text_seen || '',
        confidence: it.confidence ?? 0.7,
      })),
      missing_or_unclear_items: r.missing_or_unclear_items || (s.items.length ? [] : ['no hardware items extracted from crop']),
      special_coordination: r.special_coordination || [],
      estimator_note: r.estimator_note || s.name || null,
      confidence: r.confidence ?? 0.7,
      source_page: s.source_page,
      source_crop_id: s.source_crop_id,
    };
  });

  // Also flag hardware sets referenced by doors but not extracted as a set at all
  const extractedSetIds = new Set(hardware_set_review.map(s => s.hardware_set));
  door_analysis.forEach(d => {
    if (d.hardware_set && !extractedSetIds.has(d.hardware_set)) {
      hardware_set_review.push({
        hardware_set: d.hardware_set,
        referenced_by_doors: door_analysis.filter(x => x.hardware_set === d.hardware_set).map(x => x.mark),
        status: 'missing',
        items: [],
        missing_or_unclear_items: ['hardware set referenced by doors but not found on any hardware-sets page'],
        special_coordination: [],
        estimator_note: null,
        confidence: 0.4,
        source_page: null,
        source_crop_id: null,
      });
      extractedSetIds.add(d.hardware_set);
    }
  });

  const ps = reasoning?.project_summary || {};
  const project_summary = {
    scope_type: scope,
    project_name: ps.project_name || projectMeta.project_name || null,
    project_number: ps.project_number || projectMeta.project_number || null,
    architect: ps.architect || projectMeta.architect || projectMeta.architect_firm || null,
    address: ps.address || projectMeta.address || null,
    drawing: ps.drawing || projectMeta.drawing_number || projectMeta.drawing_title || projectMeta.sheet_number || null,
    date: ps.date || projectMeta.date || null,
    total_openings_found: door_analysis.length,
    total_hardware_sets_referenced: new Set(door_analysis.map(d => d.hardware_set).filter(Boolean)).size,
    hardware_sets_missing_or_unclear: hardware_set_review.filter(s => s.status !== 'complete').length,
    high_risk_openings: door_analysis.filter(d => d.risk_level === 'high').length,
    medium_risk_openings: door_analysis.filter(d => d.risk_level === 'medium').length,
    low_risk_openings: door_analysis.filter(d => d.risk_level === 'low').length,
    complex_installations: door_analysis.filter(d => d.install_complexity === 'high').length,
    access_control_openings: door_analysis.filter(d => (d.special_conditions || []).some(c => /CR|EL|DPS|card|access/i.test(c))).length,
    exterior_openings: door_analysis.filter(d => d.interior_or_exterior === 'Exterior').length,
    fire_rated_openings: door_analysis.filter(d => d.fire_rating && d.fire_rating !== '-').length,
    overall_bid_risk: ps.overall_bid_risk || 'Medium',
    estimator_summary: ps.estimator_summary || `Image-based pipeline processed ${pages.length} page(s) at ${RENDER_TARGET_DPI} DPI. Extracted ${door_analysis.length} opening(s) and ${hardware_set_review.length} hardware set(s) with ${totalItems} total line items. Verify all data against the source PDF before bidding.`,
  };

  return {
    analysis: {
      project_summary,
      door_analysis,
      hardware_set_review,
      door_hardware_mapping: mapping,
      // ALWAYS merge LLM reasoning with heuristic synthesis so risks/RFIs are comprehensive
      ...((() => {
        const synth = synthesizeRisksAndRFIs(door_analysis, hardware_set_review, scope);
        const merged = mergeRisksAndRFIs(reasoning, synth);
        return {
          project_risks: merged.risks,
          rfi_log: merged.rfis,
          estimator_notes: merged.notes,
          bid_recommendations: merged.recs,
        };
      })()),
    },
    qa: {
      pdf_type: 'IMAGE_PIPELINE',
      pages_rendered: pages.length,
      page_dimensions: pages.map(p => ({ pageNum: p.pageNum, width: p.width, height: p.height, dpi: p.dpi, orientation: p.orientation, previewUrl: p.previewUrl })),
      classifications,
      door_regions: doorRegionsTrace,
      hw_blocks: hwBlocksTrace,
      title_blocks: titleBlockResults,
      project_meta: projectMeta,
      findings,
      reasoning_succeeded: !!reasoning,
      extraction_complete: extractionFailures.length === 0,
      extraction_failures: extractionFailures,
    },
  };
}

/* Helper: small preview from a data URL */
async function makePreview(dataUrl, maxEdge = PREVIEW_LONG_EDGE) {
  const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = dataUrl; });
  const canvas = document.createElement('canvas');
  const scale = maxEdge / Math.max(img.width, img.height);
  canvas.width = Math.max(1, Math.round(img.width * scale));
  canvas.height = Math.max(1, Math.round(img.height * scale));
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.8);
}

/* Synthesize risks + RFIs from raw door + hardware data — runs ALWAYS and merges
   with the LLM reasoning output. Each entry carries a `source: 'heuristic'` tag
   so it can be deduped against LLM-generated ones with the same category. */
function synthesizeRisksAndRFIs(door_analysis, hardware_set_review, scope, sheet_context) {
  const risks = [];
  const rfis = [];
  const notes = [];
  const recs = { supply_only_notes: [], installation_only_notes: [], supply_and_installation_notes: [], exclusions_to_consider: [], allowances_to_consider: [], coordination_items: [] };

  const all = door_analysis || [];
  const sets = hardware_set_review || [];
  const setById = new Map(sets.map(s => [s.hardware_set, s]));

  // ===== Sheet-level context (general notes / preamble / keying / legend) =====
  const ctx = sheet_context || {};
  const generalNotes = Array.isArray(ctx.general_notes) ? ctx.general_notes : [];
  const hwPreamble   = Array.isArray(ctx.hardware_preamble) ? ctx.hardware_preamble : [];
  const keyingNotes  = Array.isArray(ctx.keying_notes) ? ctx.keying_notes : [];
  const legend       = (ctx.legend && typeof ctx.legend === 'object') ? ctx.legend : {};
  const allCtxText   = [...generalNotes, ...hwPreamble, ...keyingNotes].join(' \n ');
  const hasCtx       = (regex) => regex.test(allCtxText);
  // Note phrases that often resolve scope ambiguity — used to skip RFIs the notes already answer.
  const ctxSaysECPower      = /\b(EC|electrical contractor|division\s*26|div\.?\s*26)\b[^.]{0,80}\b(provide|supply|by)\b[^.]{0,40}\b(120\s*v|power|line\s*voltage)\b/i.test(allCtxText) || /\b120\s*v[^.]{0,40}\b(by|provided by)\b[^.]{0,30}\b(EC|electrical contractor)\b/i.test(allCtxText);
  const ctxSaysLVByOthers   = /\b(low[-\s]?voltage|cabling|access\s*control|EAC|head[-\s]?end)\b[^.]{0,60}\b(by|provided by|N\.?I\.?C\.?|not in contract)\b/i.test(allCtxText);
  const ctxSaysOwnerKeying  = /\b(owner|owner[-\s]?supplied|by owner|N\.?I\.?C\.?)\b[^.]{0,40}\b(cylinder|key|keying|core)/i.test(allCtxText);
  const ctxSaysKeyingDefined = keyingNotes.length > 0 && /\b(master|grand\s*master|sub[-\s]?master|keyway|SFIC|LFIC|construction\s*core|restricted)\b/i.test(keyingNotes.join(' '));

  const marks = (arr, n = 8) => {
    const list = arr.slice(0, n).join(', ');
    return arr.length > n ? `${list}, …+${arr.length - n} more` : list;
  };
  const pushRisk = (severity, category, issue, affected, recommendation) =>
    risks.push({ severity, category, issue, affected_openings: affected, recommendation, status: 'Open', source: 'heuristic' });
  const pushRfi = (priority, category, question, affected, recommendation, reason) =>
    rfis.push({ priority, category, question, affected_openings: affected, recommendation, status: 'Open', reason: reason || recommendation, source: 'heuristic' });

  /* ===================== HARDWARE MAPPING / SET DEFINITIONS ===================== */
  const noSet = all.filter(d => !d.hardware_set);
  if (noSet.length) {
    pushRisk('high', 'Hardware mapping', `${noSet.length} opening(s) have no hardware set assigned in the schedule.`, noSet.map(d => d.mark),
      'Issue RFI to architect/owner to confirm hardware set assignments before bidding.');
    pushRfi('high', 'Hardware mapping', `The door schedule does not show a hardware set for the following openings: ${marks(noSet.map(d => d.mark))}. Please confirm the intended hardware set for each.`,
      noSet.map(d => d.mark),
      'Hardware set assignments must be confirmed before bid close to avoid scope gap.',
      'Door schedule shows these openings without a hardware set reference.');
  }
  const failedMap = all.filter(d => d.hardware_set && (!setById.get(d.hardware_set) || (setById.get(d.hardware_set)?.items?.length || 0) === 0));
  if (failedMap.length) {
    const setIds = [...new Set(failedMap.map(d => d.hardware_set))];
    pushRisk('high', 'Hardware set definitions', `${setIds.length} hardware set(s) referenced by ${failedMap.length} door(s) have no extracted line items.`, failedMap.map(d => d.mark),
      'Locate full hardware set definitions in spec book / hardware schedule; bid carries risk until items are confirmed.');
    pushRfi('high', 'Hardware set definitions', `Provide the complete line-item list for hardware set(s): ${setIds.join(', ')}. The door schedule references them but no item list could be extracted.`,
      failedMap.map(d => d.mark),
      'Carry as allowance until confirmed.',
      'Hardware set IDs referenced in the schedule but item lists are missing or unreadable.');
  }
  // Hardware sets flagged void / crossed out
  const voidedSets = sets.filter(s => /void|cross|strike|withdrawn|deleted/i.test([s.status, s.estimator_note, (s.missing_or_unclear_items||[]).join(' '), s.header_verbatim || ''].join(' ')));
  if (voidedSets.length) {
    const ids = voidedSets.map(s => s.hardware_set);
    pushRisk('high', 'Voided hardware set', `${ids.length} hardware set(s) appear crossed out or voided on the spec page: ${ids.join(', ')}.`, [],
      'Do NOT carry these sets unless architect confirms they are still active.');
    pushRfi('high', 'Voided hardware set', `Hardware set(s) ${ids.join(', ')} appear crossed out / voided on the spec page. Please confirm whether they are still required for this project.`, [],
      'Skip these in pricing if confirmed inactive; otherwise treat as live.',
      'Visual flag from extraction indicates the set may have been struck through.');
  }

  /* ===================== FIRE / SMOKE RATING ===================== */
  const fireDoors = all.filter(d => d.fire_rating && d.fire_rating !== '-' && !/^non|^n\/a$/i.test(String(d.fire_rating)));
  if (fireDoors.length) {
    pushRisk('medium', 'Fire-rated openings', `${fireDoors.length} fire-rated opening(s) require UL-listed assemblies (door + frame + hardware all matching the labelled rating).`, fireDoors.map(d => d.mark),
      'Confirm UL labels on door, frame and hardware match for each rating. Carry positive-latching, self-closing hardware and smoke gasketing where required by IBC/NFPA 80/105.');
    pushRfi('medium', 'Fire / smoke rating', `Confirm UL-listed assembly requirements for fire-rated openings (${marks(fireDoors.map(d => d.mark))}). Are smoke gasketing and S-label hardware required for the 20-minute and corridor doors? Are temperature-rise cores required at exit stair doors?`,
      fireDoors.map(d => d.mark),
      'Coordinate UL listings across door, frame and hardware; add smoke gaskets where the egress path requires S-label.',
      'Fire-rated assemblies require coordinated UL listings and gasketing per code.');
    // Stair / temperature-rise sub-RFI when ratings ≥ 60 min
    const stairDoors = fireDoors.filter(d => /stair|exit stair|stairwell/i.test([d.room_or_location, d.door_type, (d.remarks||[]).join(' ')].join(' ')));
    if (stairDoors.length) {
      pushRfi('medium', 'Fire / smoke rating', `Stair-enclosure openings (${marks(stairDoors.map(d => d.mark))}) — confirm temperature-rise core requirement (250°F / 30 min) and that frames/hardware carry matching UL labels.`,
        stairDoors.map(d => d.mark),
        'Stair doors typically require temperature-rise core per IBC; verify rating per code path.',
        'IBC 716 typically requires temperature-rise cores at exit stair enclosures.');
    }
  }

  /* ===================== EXTERIOR / WEATHER ===================== */
  const ext = all.filter(d => d.interior_or_exterior === 'Exterior' || /exterior|exit\s*to\s*exterior|out\s*to\s*grade/i.test([d.room_or_location, (d.remarks||[]).join(' ')].join(' ')));
  if (ext.length) {
    pushRisk('medium', 'Exterior / weather', `${ext.length} exterior opening(s) require weatherstripping, sweeps, thresholds and (if applicable) drip caps. Hollow-metal vs aluminum/storefront assembly type and finish must be confirmed.`, ext.map(d => d.mark),
      'Confirm exterior assembly type (HM vs aluminum), thresholds, weatherstrip, sweeps; coordinate with envelope / curtain wall installer.');
    pushRfi('medium', 'Exterior / weather', `For exterior openings (${marks(ext.map(d => d.mark))}): please confirm threshold detail, weatherstrip type, door sweep, and finish/color. Are any openings part of an aluminum storefront system (excluded from Div 8 scope) versus hollow-metal (included)?`,
      ext.map(d => d.mark),
      'Identify which exterior openings are storefront (other section) vs HM (Div 8) before pricing.',
      'Exterior assemblies have envelope and finish implications that aren’t resolved in the schedule alone.');
    recs.coordination_items.push('Coordinate exterior openings with envelope / curtain wall / storefront installer.');
  }

  /* ===================== ACCESS CONTROL / ELECTRIFIED HARDWARE ===================== */
  // Build the regex from the project's own legend if it's defined; otherwise fall back
  // to the industry-standard abbreviations. Project-specific abbreviations join the
  // generic detector (e.g. some projects use "ACR" for card reader).
  const projectAbbrevs = Object.keys(legend).filter(k => /reader|card|electric|maglock|magnetic|access|operator|REX|EPT|power\s*transfer|delayed\s*egress|panic|exit/i.test(legend[k] || ''));
  const projectAbbrevRe = projectAbbrevs.length ? new RegExp(`\\b(${projectAbbrevs.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'i') : null;
  const acRemarks = /\bCR\b|\bEL\b|\bDPS\b|\bRX\b|\bEH\b|\bAO\b|panic|card reader|access control|electrified|magnetic\s*lock|maglock|electric\s*strike|electric\s*latch|automatic\s*operator|push\s*paddle|power\s*supply|power\s*transfer|EPT|REX|request[-\s]to[-\s]exit|delayed\s*egress|stand[-\s]?alone\s*lock/i;
  const ac = all.filter(d => {
    const txt = [(d.remarks||[]).join(' '), d.door_type, d.room_or_location].join(' ');
    return acRemarks.test(txt) || (projectAbbrevRe && projectAbbrevRe.test(txt));
  });
  if (ac.length) {
    pushRisk('high', 'Access control / electrified', `${ac.length} opening(s) involve electrified hardware (card readers, electric strikes/locks, maglocks, REX, DPS, power transfer, automatic operators, etc.). Power, low-voltage cabling, EAC head-end and commissioning must be split between trades.`, ac.map(d => d.mark),
      'Confirm scope split between Div 8 (hardware supply + integration), Div 26 (power), Div 27/28 (low-voltage / EAC head-end) BEFORE bidding. Carry power transfers, power supplies and EPTs as required.');
    // Only push the scope-split RFI if the drawings don't already resolve it.
    if (!(ctxSaysECPower && ctxSaysLVByOthers)) {
      pushRfi('high', 'Access control / electrified', `For openings with electrified hardware (${marks(ac.map(d => d.mark))}): please confirm scope responsibility for (a) 120V power to power supplies, (b) low-voltage cabling, (c) credential readers and head-end, (d) integration with fire alarm release, (e) final commissioning and programming. Provide single-line diagrams if available.`,
        ac.map(d => d.mark),
        'Carry electrified hardware components on the Div 8 side only; exclude head-end + cabling unless explicitly priced.',
        'Electrified hardware coordination is the single most common bid-risk area in Div 8.');
    } else {
      notes.push(`Project notes resolve electrified-hardware scope split (EC provides 120 V; low-voltage by others). Skipping generic scope-split RFI; ${ac.length} opening(s) still need integration coordination.`);
    }
    recs.coordination_items.push('Coordinate electrified hardware split: Div 08 (hardware) / Div 26 (120 V) / Div 27-28 (low-voltage + head-end).');
    recs.coordination_items.push('Confirm fire alarm release tie-in for any maglocks or delayed-egress hardware.');
  }

  /* ===================== AUTOMATIC OPERATORS / ADA ===================== */
  const ada = all.filter(d => /\bAO\b|automatic\s*operator|low\s*energy\s*operator|push\s*paddle|barrier[-\s]?free|accessible|ADA/i.test([(d.remarks||[]).join(' '), d.door_type, d.room_or_location].join(' ')));
  if (ada.length) {
    pushRisk('medium', 'ADA / automatic operators', `${ada.length} opening(s) are flagged for automatic operators or barrier-free use. Verify ANSI A156.19 low-energy vs A156.10 full-power operator, push-plate / wave-plate locations, and power requirements.`, ada.map(d => d.mark),
      'Confirm operator type (low energy vs full power), control type (push plate vs touchless wave), and power source for each.');
    pushRfi('medium', 'ADA / automatic operators', `For automatic-operator openings (${marks(ada.map(d => d.mark))}): confirm (a) ANSI A156.10 vs A156.19 classification, (b) push-plate / touchless actuator location and mounting heights, (c) 120 V power provision, (d) interlocks at vestibule pairs.`,
      ada.map(d => d.mark),
      'Specify operator series and actuator type to lock pricing.',
      'Operator class and actuator placement drive both hardware cost and EC scope.');
  }

  /* ===================== EGRESS / EXIT DEVICES ===================== */
  const panic = all.filter(d => /panic|exit\s*device|crash\s*bar|push\s*pad|cvr|cvr\b|surface\s*vertical\s*rod|mortise\s*exit|rim\s*exit/i.test([(d.remarks||[]).join(' '), d.door_type, d.room_or_location].join(' ')));
  if (panic.length) {
    pushRisk('medium', 'Egress / exit devices', `${panic.length} opening(s) carry exit devices / panic hardware. Verify egress code path (IBC 1010), fire-rated vs non-rated, single vs double, and trim function (passage / classroom / storeroom).`, panic.map(d => d.mark),
      'Confirm exit device function (rim, mortise, CVR, SVR), fire-rated vs non-rated, trim, and outside trim function for each.');
    pushRfi('medium', 'Egress / exit devices', `For panic / exit-device openings (${marks(panic.map(d => d.mark))}): confirm device type (rim / mortise / CVR / SVR), trim function (passage / classroom / storeroom / nightlatch), and any dogging or alarm features. Are fire-rated exits required to be non-dogging?`,
      panic.map(d => d.mark),
      'Lock device series and trim function before tender close.',
      'Function/trim variations have significant cost impact and field implications.');
  }

  /* ===================== DOUBLE-DOOR PAIRS / COORDINATORS ===================== */
  const pairs = all.filter(d => /pair|double|2[\s-]?leaf|astragal|coordinator|flush\s*bolt/i.test([(d.remarks||[]).join(' '), d.door_type, d.opening_type || ''].join(' ')));
  if (pairs.length) {
    pushRisk('medium', 'Pair / double-leaf openings', `${pairs.length} pair (double-leaf) opening(s). Coordinators, astragals, flush bolts and active/inactive trim must be priced.`, pairs.map(d => d.mark),
      'Verify each pair has coordinator (if rated), astragal type (overlapping vs split), flush bolts / auto flush bolts at inactive leaf.');
    pushRfi('medium', 'Pair / double-leaf openings', `For pair openings (${marks(pairs.map(d => d.mark))}): confirm astragal type, coordinator requirement (for rated pairs), and active/inactive leaf trim. Are auto flush bolts required at any inactive leaves?`,
      pairs.map(d => d.mark),
      'Add coordinators + astragals to bid where required by rating/spec.',
      'Pairs without coordinators on rated openings fail UL listing.');
  }

  /* ===================== SECURITY / DETENTION / VAULT / BULLET ===================== */
  const security = all.filter(d => /vault|safe\s*room|secure|secured\s*entry|bullet|ballistic|detention|holding|interview|interrogation|server|IDF|MDF|telecom|comm\s*room|electrical\s*closet/i.test([(d.remarks||[]).join(' '), d.door_type, d.room_or_location || ''].join(' ')));
  if (security.length) {
    pushRisk('medium', 'High-security openings', `${security.length} opening(s) at high-security or sensitive rooms (server, electrical, vault, safe-room). Often require restricted-keyway cylinders, key-management, and possibly bullet/forced-entry ratings.`, security.map(d => d.mark),
      'Confirm restricted/patented keyway requirement, key-management system, and any ballistic/forced-entry ratings.');
    pushRfi('medium', 'High-security openings', `For security-sensitive openings (${marks(security.map(d => d.mark))}): confirm cylinder/keyway specification (restricted, patented, interchangeable core, etc.), key system structure (master/sub-master keying), and any ballistic or forced-entry rating requirements.`,
      security.map(d => d.mark),
      'Lock restricted-keyway brand and supplier before bidding.',
      'Restricted keyways have single-source supply implications and lead times.');
  }

  /* ===================== KEYING SYSTEM ===================== */
  if (all.length >= 5) {
    if (ctxSaysKeyingDefined) {
      // The drawings already define the keying system — surface the notes and skip the generic RFI.
      notes.push(`Keying notes captured from the drawings (${keyingNotes.length} line(s)) — no generic keying RFI generated. Verify the captured notes cover keyway, master structure, cylinder format, construction core and key counts.`);
      if (ctxSaysOwnerKeying) {
        recs.exclusions_to_consider.push('Cylinders / keying noted as owner-supplied or by-others on the drawings — exclude cylinder + keying scope from base bid unless otherwise directed.');
      } else {
        recs.allowances_to_consider.push('Allowance for construction cylinders and final keying meeting attendance (per project keying notes).');
      }
    } else {
      pushRisk('medium', 'Keying / cylinders', `Keying schedule, master-key system, construction core requirement and SFIC vs conventional cylinder format are not visible in the door schedule.`, [],
        'Issue RFI for keying system. Carry construction cores allowance separately.');
      pushRfi('medium', 'Keying / cylinders', `Please provide the complete keying schedule: (a) master / sub-master / grand-master structure, (b) keyway (e.g. Schlage Everest, Medeco X4, Yale 8000), (c) cylinder format (SFIC / LFIC / conventional), (d) construction core requirement and changeover, (e) restricted vs standard keyway, (f) number of operating keys and master keys.`,
        [],
        'Carry construction cylinders as an allowance until keying meeting is held.',
        'Keying impacts cost and lead time but is rarely shown on door schedules.');
      recs.allowances_to_consider.push('Allowance for construction cylinders and final keying meeting attendance.');
    }
  }

  /* ===================== SOUND / STC RATING ===================== */
  const stc = all.filter(d => /STC|acoustic|sound\s*(?:seal|rated|attenuat)/i.test([(d.remarks||[]).join(' '), d.door_type, d.room_or_location].join(' ')));
  if (stc.length) {
    pushRisk('medium', 'Acoustic / STC-rated', `${stc.length} opening(s) require STC / acoustic-rated assemblies. Door, frame, gasketing, automatic door bottom and threshold must all match the listed STC.`, stc.map(d => d.mark),
      'Confirm STC value, assembly type, and source of certified test report.');
    pushRfi('medium', 'Acoustic / STC-rated', `For STC-rated openings (${marks(stc.map(d => d.mark))}): confirm STC value, door manufacturer's listed assembly, automatic door-bottom requirement, perimeter gasketing, and whether a third-party test report is required at submittal.`,
      stc.map(d => d.mark),
      'Carry full STC-listed assembly per spec; do not substitute components.',
      'Mixing components voids the STC rating.');
  }

  /* ===================== EXISTING / REMODEL CONDITIONS ===================== */
  const existing = all.filter(d => /existing|EX\b|re-?use|salvage|relocate|infill/i.test([(d.remarks||[]).join(' '), d.door_type, d.room_or_location || ''].join(' ')));
  if (existing.length) {
    pushRisk('medium', 'Existing conditions', `${existing.length} opening(s) reference existing/relocated/salvaged conditions. Field measure required; prep conditions and frame condition are unknowns.`, existing.map(d => d.mark),
      'Field-measure each existing opening before fabrication. Carry rework allowance.');
    pushRfi('medium', 'Existing conditions', `For existing/relocated openings (${marks(existing.map(d => d.mark))}): confirm what is being re-used (door / frame / hardware), what is new, condition of existing prep, and whether existing keying continues.`,
      existing.map(d => d.mark),
      'Add a frame-prep / rework allowance until field survey is complete.',
      'Existing conditions are the largest source of change orders in remodel work.');
    recs.allowances_to_consider.push('Allowance for existing-frame prep, modification or replacement at remodel openings.');
  }

  /* ===================== GLAZED / LITE DOORS ===================== */
  const glass = all.filter(d => d.glazing && !/^(none|-|n\/a)$/i.test(String(d.glazing)));
  if (glass.length) {
    pushRfi('low', 'Glazing / vision lites', `For glazed openings (${marks(glass.map(d => d.mark))}): confirm glazing type (tempered / laminated / wired / fire-rated ceramic), thickness, and any film/tint requirement. Fire-rated glazing must carry matching UL listing.`,
      glass.map(d => d.mark),
      'Specify glazing type per opening; fire-rated glass requires UL-listed assembly.',
      'Glazing type drives cost (especially fire-rated ceramic) and lead time.');
  }

  /* ===================== SCHEDULE QUALITY ===================== */
  const lowConf = all.filter(d => (d.confidence ?? 1) < 0.6);
  if (lowConf.length) {
    pushRisk('low', 'Schedule legibility', `${lowConf.length} schedule row(s) extracted at low confidence — likely unclear scan or handwritten markup.`, lowConf.map(d => d.mark),
      'Manually verify these rows against the source PDF before bid submission.');
  }
  const missingSize = all.filter(d => !d.size?.width || !d.size?.height);
  if (missingSize.length && missingSize.length < all.length) {
    pushRfi('low', 'Schedule completeness', `Opening size is missing for ${missingSize.length} door(s): ${marks(missingSize.map(d => d.mark))}. Please provide width × height × thickness for each.`,
      missingSize.map(d => d.mark),
      'Carry as TBD until sizes are confirmed.',
      'Missing nominal size prevents door material take-off.');
  }

  /* ===================== SUBMITTAL / LEAD TIME ===================== */
  if (all.length) {
    pushRisk('low', 'Submittal / lead time', `Hardware submittal review cycle (typically 4–6 weeks) and door/frame fabrication lead time (8–12 weeks for HM, 10–14 weeks for restricted-keyway hardware) must align with the construction schedule.`, [],
      'Confirm submittal due dates and ROJ (required on jobsite) dates with GC; flag any expedite costs.');
    pushRfi('low', 'Submittal / lead time', `Please confirm hardware/door submittal due dates, hardware approval turn-around, and required on-jobsite (ROJ) dates for: (a) hollow metal frames, (b) wood doors, (c) finish hardware, (d) electrified hardware components.`,
      [],
      'Lock these dates in the schedule baseline.',
      'Lead-time misses are the dominant Div 8 schedule risk.');
  }

  /* ===================== NOTES ===================== */
  if (all.length) notes.push(`${all.length} opening(s) extracted from the schedule. Verify all marks against the source PDF before submitting bid.`);
  if (sets.length) notes.push(`${sets.length} hardware set(s) identified; ${sets.filter(s => s.items?.length).length} have a complete extracted item list.`);
  if (failedMap.length) notes.push(`${failedMap.length} door(s) reference a hardware set with no items — bid risk if not resolved before tender close.`);
  if (fireDoors.length) notes.push(`${fireDoors.length} fire-rated opening(s) — UL listing & smoke gasketing must be coordinated across door, frame and hardware.`);
  if (ac.length) notes.push(`${ac.length} opening(s) with electrified / access-control hardware — Div 26/27/28 scope split must be clarified before bidding.`);
  if (ada.length) notes.push(`${ada.length} opening(s) with automatic operators — verify ANSI class and EC scope.`);

  /* ===================== SCOPE-SPECIFIC RECOMMENDATIONS ===================== */
  if (scope === 'Supply Only' || scope === 'Supply & Installation') {
    recs.supply_only_notes.push('Submittal package: door, frame and hardware schedules with manufacturer cut sheets, keying schedule, electrified hardware riser, anchor templates.');
    // Only push the generic exclusions when the drawings haven't already established them
    if (!ctxSaysECPower && !ctxSaysLVByOthers) {
      recs.exclusions_to_consider.push('Exclude 120 V power, low-voltage cabling, access-control head-end, intrusion detection programming, fire-alarm tie-in (NIC).');
    } else {
      recs.exclusions_to_consider.push('Exclude 120 V power, low-voltage cabling, access-control head-end (per drawing notes — confirmed by EC / others).');
    }
    recs.exclusions_to_consider.push('Exclude permits, demolition, painting, drywall patching at frame anchors, floor preparation at thresholds.');
    if (fireDoors.length) recs.allowances_to_consider.push('Allowance for fire-rated assembly coordination, S-label gasketing and any UL field-modification charges.');
    if (stc.length) recs.allowances_to_consider.push('Allowance for STC-rated assembly testing / certification at acoustic openings.');
  }
  if (scope === 'Installation Only' || scope === 'Supply & Installation') {
    recs.installation_only_notes.push('Field-measure all openings before fabrication release. Verify rough-opening size, frame anchor type, and floor condition.');
    recs.installation_only_notes.push('Storage and protection of doors / frames / hardware on site is by GC unless otherwise noted.');
    if (ac.length) recs.coordination_items.push('Schedule electrified-hardware integration window with EC + low-voltage contractor; sequence with ceiling close-up.');
    if (ext.length) recs.coordination_items.push('Sequence exterior openings with envelope / storefront install; coordinate threshold details with concrete / flooring.');
    if (existing.length) recs.coordination_items.push('Field-survey existing openings before submittal; document existing-frame condition with photos.');
  }
  // Always-on coordination items
  recs.coordination_items.push('Attend pre-installation meeting with GC, EC, low-voltage, fire alarm and security trades.');
  recs.coordination_items.push('Hold formal keying meeting with owner before cylinder fabrication.');

  // ===== Surface captured drawing notes into the estimator notes feed =====
  if (generalNotes.length) {
    notes.push(`${generalNotes.length} general note(s) captured from the door-schedule sheet — review verbatim text on the Bid Recommendations screen.`);
  }
  if (hwPreamble.length) {
    notes.push(`${hwPreamble.length} hardware-preamble note(s) captured from the hardware-set sheet(s) — review verbatim text on the Bid Recommendations screen.`);
  }
  if (Object.keys(legend).length) {
    notes.push(`Schedule legend captured (${Object.keys(legend).length} abbreviation${Object.keys(legend).length === 1 ? '' : 's'} defined on the drawings) — project-specific abbreviations now factored into the electrified-hardware detector.`);
  }

  return { risks, rfis, notes, recs };
}

/* Merge LLM reasoning output with heuristic synthesis. The LLM is good at
   specific findings-based RFIs; the heuristic is good at coverage. Combine
   them, dedupe by category + affected-opening signature, and keep both. */
function mergeRisksAndRFIs(reasoning, synth) {
  const sigRisk = (r) => `${String(r.category||'').toLowerCase().trim()}|${String(r.severity||'').toLowerCase().trim()}|${(r.affected_openings||[]).slice().sort().join(',')}`;
  const sigRfi = (r) => `${String(r.category||r.question||'').toLowerCase().trim().slice(0,80)}|${(r.affected_openings||[]).slice().sort().join(',')}`;
  const seen = new Set();
  const out = [];
  const pushUnique = (items, sigFn) => {
    for (const it of items) {
      if (!it) continue;
      const sig = sigFn(it);
      if (seen.has(sig)) continue;
      seen.add(sig);
      out.push(it);
    }
  };

  // LLM first (it tends to be more specific), heuristic fills gaps
  const llmRisks = Array.isArray(reasoning?.project_risks) ? reasoning.project_risks : [];
  const llmRfis  = Array.isArray(reasoning?.rfi_log) ? reasoning.rfi_log : [];
  const llmNotes = Array.isArray(reasoning?.estimator_notes) ? reasoning.estimator_notes : [];

  const risks = [];
  const rfis = [];
  const notes = [];

  // Risks
  const seenRisk = new Set();
  for (const r of [...llmRisks, ...synth.risks]) {
    if (!r) continue;
    const sig = sigRisk(r);
    if (seenRisk.has(sig)) continue;
    seenRisk.add(sig);
    risks.push({ ...r, status: r.status || 'Open' });
  }

  // RFIs
  const seenRfi = new Set();
  for (const r of [...llmRfis, ...synth.rfis]) {
    if (!r) continue;
    const sig = sigRfi(r);
    if (seenRfi.has(sig)) continue;
    seenRfi.add(sig);
    rfis.push({ ...r, status: r.status || 'Open' });
  }

  // Notes (dedupe by lowercase text)
  const seenNote = new Set();
  for (const n of [...llmNotes, ...synth.notes]) {
    const k = String(n || '').toLowerCase().trim();
    if (!k || seenNote.has(k)) continue;
    seenNote.add(k);
    notes.push(n);
  }

  // Bid recommendations — merge each bucket
  const llmRecs = reasoning?.bid_recommendations || {};
  const recs = { supply_only_notes: [], installation_only_notes: [], supply_and_installation_notes: [], exclusions_to_consider: [], allowances_to_consider: [], coordination_items: [] };
  Object.keys(recs).forEach(bucket => {
    const seenB = new Set();
    [...(Array.isArray(llmRecs[bucket]) ? llmRecs[bucket] : []), ...(synth.recs[bucket] || [])].forEach(line => {
      const k = String(line || '').toLowerCase().trim();
      if (!k || seenB.has(k)) return;
      seenB.add(k);
      recs[bucket].push(line);
    });
  });

  return { risks, rfis, notes, recs };
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

/* ---------- Native pipeline prompts (ChatGPT-style PDF reading) ---------- */

/* Pass 0: Discovery — scan whole PDF, return page-level index of relevant content. */
const PDF_DISCOVERY_SYSTEM = `You are a senior Division 8 estimator scanning a project PDF to build a content index.

Read EVERY page of the PDF. For each page, classify what's on it. We need the index to plan a thorough extraction pass.

Return STRICTLY valid JSON only:
{
  "project_meta": {
    "project_name": string|null,
    "project_number": string|null,
    "architect": string|null,
    "address": string|null,
    "drawing": string|null,
    "date": string|null,
    "scope_notes_observed": [string]
  },
  "pages": [{
    "page": number,
    "sheet_number": string|null,
    "sheet_title": string|null,
    "roles": [
      "door_schedule"
      | "hardware_sets"
      | "hardware_schedule"
      | "door_details"
      | "door_elevations"
      | "frame_details"
      | "frame_elevations"
      | "legend"
      | "general_notes"
      | "hardware_notes"
      | "keying"
      | "specifications"
      | "cover"
      | "other"
    ],
    "visible_door_marks": [string],
    "visible_hardware_set_ids": [string],
    "row_count_estimate": number|null,
    "notes": string|null
  }],
  "estimated_door_total": number|null,
  "estimated_hardware_set_total": number|null
}

Be thorough. List EVERY page, even cover/legend pages. Enumerate door marks and HW set IDs you can see — even if just headers. If multiple roles apply to a page, list all of them.`;

/* Pass A: lean transcription — transcription only, no reasoning */
const EXTRACTION_ONLY_SYSTEM = `You are a senior Division 8 estimator transcribing a project PDF.

Your job is ONLY to extract structured raw data — no reasoning, no risks, no RFIs, no recommendations. Those happen in a separate pass.

Read EVERY door schedule row and EVERY hardware set with every line item visible. Do not skip rows. Do not summarize. Read all columns of multi-column hardware-set pages top-to-bottom, left-to-right.

CRITICAL ANTI-HALLUCINATION:
- Extract only what is clearly visible. Never invent door marks, hardware sets, qty, finishes, ratings, or part numbers.
- Preserve all marks/IDs character-for-character.
- If a field is unreadable, return null.
- Capture remarks verbatim per door (CR, EH, EL, DPS, AO, panic, etc. should all be in remarks if visible).
- For hardware sets: capture the FULL header verbatim (e.g. "Hardware Group No. C265 — Office") plus the canonical id ("C265"). Capture EVERY line item.
- If a hardware set heading is crossed out / voided, capture the id and mark it with a remark "VOIDED".

Return STRICTLY valid JSON only:
{
  "project_meta": {
    "project_name": string|null,
    "project_number": string|null,
    "architect": string|null,
    "address": string|null,
    "drawing": string|null,
    "date": string|null
  },
  "doors": [{
    "mark": string,
    "room_or_location": string|null,
    "door_type": string|null,
    "interior_or_exterior": "Interior"|"Exterior"|null,
    "size": { "width": string|null, "height": string|null, "thickness": string|null },
    "door_material": string|null,
    "door_finish": string|null,
    "glazing": string|null,
    "frame_type": string|null,
    "frame_material": string|null,
    "frame_finish": string|null,
    "fire_rating": string|null,
    "hardware_set": string|null,
    "remarks": [string]
  }],
  "hardware_sets": [{
    "id": string,
    "name": string|null,
    "header_verbatim": string|null,
    "opening_note_doors": [string],
    "items": [{
      "qty": number|null,
      "desc": string,
      "part": string|null,
      "mfr": string|null,
      "finish": string|null
    }]
  }]
}

Pure transcription. No analysis fields. No reasoning. No prose.`;

/* Pass A2: completeness check — given current extraction, find what's missing */
const COMPLETENESS_CHECK_SYSTEM = `You are a senior Division 8 estimator verifying that an extraction pass is complete.

You will be given:
  1. The full project PDF
  2. A list of door marks and hardware set IDs already extracted
  3. A list of discovered marks/IDs from the page index

Your job: find what is MISSING. Look at the PDF page-by-page and return ONLY the doors AND hardware sets that were NOT in the existing extraction. Do not re-emit what's already there. Do not skip anything that's actually missing.

Pay special attention to:
- Multi-column hardware-set pages where a column was skipped
- Schedule continuation rows on a second page
- Hardware sets referenced by doors but not yet extracted as a set
- Line items at the bottom of a hardware set that the first pass cut off
- Hardware sets buried in spec book prose (look for "HARDWARE SET", "HW-", "GROUP", "FHW-" patterns)

Return STRICTLY valid JSON in the SAME schema as the original transcription (doors[], hardware_sets[]), containing ONLY the missing entries. If nothing is missing, return { "doors": [], "hardware_sets": [] }.`;

/* ---------- FAST single-shot pipeline (mimics native ChatGPT-5.5 with extended thinking) ----------
   One call. PDF in, full senior-estimator JSON out. Uses reasoning.effort = "high"
   so the model spends its compute on extended thinking rather than us spending it
   on multiple round-trips. Designed to finish in ~60-120s like the native UI. */

const SINGLE_SHOT_SYSTEM = `You are a senior Division 8 Doors, Frames & Hardware estimator with 15+ years of experience in commercial construction. A project PDF has been uploaded for you to read directly. Use extended thinking — read every page, every door schedule row, every hardware set with every line item, every relevant note.

Your output is a SINGLE comprehensive senior-estimator JSON that combines:
  (a) verbatim transcription of doors + hardware sets + items
  (b) opening-by-opening analysis (risk, complexity, special conditions)
  (c) project-level risks + RFIs + recommendations + bid notes

CRITICAL ANTI-HALLUCINATION:
- Extract only what is clearly visible. Never invent door marks, hardware set IDs, qty, finishes, ratings, or part numbers.
- Preserve all marks/IDs character-for-character.
- If a field is unreadable, return null.
- Capture remarks verbatim per door (CR, EH, EL, DPS, AO, panic, etc.).
- For hardware sets: capture the FULL header verbatim (e.g. "Hardware Group No. C265 — Office Door"), the canonical id ("C265"), AND every line item.
- Read multi-column hardware-set pages top-to-bottom, left-to-right. Do not skip a column.
- If a hardware set heading is crossed out / voided, capture the id and add "VOIDED" to a remark.

CANONICAL HARDWARE SET MATCHING:
- The door schedule may say "C265" while the spec page header reads "Hardware Group No. C265" or "HW-C265". These are the SAME set. When you fill door.hardware_set, use whichever form appears in the schedule. The id field of a hardware set should be the canonical short form (e.g. "C265", not "Hardware Group No. C265").

COMPREHENSIVE RFI GENERATION:
Build a thorough RFI log (target 15-25 entries, minimum 12 unless the project is trivial). For EACH category below that has any matching openings, emit at least one specific, grounded RFI citing actual door marks / set IDs:

  • Fire / smoke rating — UL listing across door + frame + hardware; smoke gasketing per egress path; temperature-rise cores at exit stair enclosures (IBC 716).
  • Egress / exit devices — device type (rim/mortise/CVR/SVR), trim function (passage/classroom/storeroom/nightlatch), dogging vs non-dogging.
  • Access control / electrified hardware — power supply, low-voltage cabling, EAC head-end, fire-alarm release, commissioning. Trigger on CR/EL/DPS/RX/EH/maglock/electric strike/AO remarks.
  • ADA / automatic operators — ANSI A156.10 vs A156.19, actuator location + mounting heights, 120 V provision, vestibule interlock.
  • Exterior / weather — threshold, weatherstrip, sweep, drip cap; HM vs storefront/aluminum scope split.
  • Pair / double-leaf — coordinators for rated pairs, astragal type, flush bolts at inactive leaf.
  • Keying / cylinders — master-key structure, keyway, SFIC vs LFIC, restricted keyway, construction core.
  • Acoustic / STC-rated — STC value, certified assembly, automatic door bottom, perimeter gasketing.
  • High-security rooms — server / electrical / vault; restricted keyway, key-management, ballistic.
  • Existing / remodel conditions — re-use scope, frame prep, field-measure, keying continuity.
  • Glazing / vision lites — tempered / laminated / wired / fire-rated ceramic, UL listing for rated.
  • Schedule completeness — missing sizes, unreadable rows, ambiguous frame type.
  • Submittal / lead time — submittal due dates, approval turn-around, ROJ dates.
  • Scope split — Div 08 vs Div 26 (power) vs Div 27/28 (low-voltage / head-end).
  • Hardware set mismatches — doors referencing missing/voided sets, set opening-note vs schedule mismatches, sets with no items.

Project_risks: minimum 6 entries covering the same categories. Each with severity, category, concrete issue + affected_openings + recommendation.

RETURN STRICTLY VALID JSON in this exact shape:
{
  "project_summary": {
    "scope_type": string,
    "project_name": string|null, "project_number": string|null,
    "architect": string|null, "address": string|null,
    "drawing": string|null, "date": string|null,
    "total_openings_found": number,
    "total_hardware_sets_referenced": number,
    "hardware_sets_missing_or_unclear": number,
    "high_risk_openings": number, "medium_risk_openings": number, "low_risk_openings": number,
    "complex_installations": number,
    "access_control_openings": number,
    "exterior_openings": number,
    "fire_rated_openings": number,
    "overall_bid_risk": "Low"|"Medium"|"High",
    "estimator_summary": string
  },
  "door_analysis": [{
    "mark": string,
    "room_or_location": string|null,
    "door_type": string|null,
    "opening_type": string|null,
    "interior_or_exterior": "Interior"|"Exterior"|null,
    "size": { "width": string|null, "height": string|null, "thickness": string|null },
    "door_material": string|null, "door_finish": string|null, "glazing": string|null,
    "frame_type": string|null, "frame_material": string|null, "frame_finish": string|null,
    "fire_rating": string|null, "hardware_set": string|null,
    "remarks": [string],
    "hardware_status": "complete"|"incomplete"|"review required",
    "install_complexity": "low"|"medium"|"high",
    "risk_level": "low"|"medium"|"high",
    "special_conditions": [string], "issues": [string], "recommendations": [string],
    "rfi_required": boolean, "rfi_questions": [string],
    "confidence": number
  }],
  "hardware_set_review": [{
    "hardware_set": string,
    "header_verbatim": string|null,
    "referenced_by_doors": [string],
    "status": "complete"|"incomplete"|"missing"|"voided",
    "items": [{
      "item_no": number|null, "qty": number|null, "unit": string|null,
      "desc": string, "part": string|null, "mfr": string|null, "finish": string|null,
      "notes": string|null
    }],
    "missing_or_unclear_items": [string],
    "special_coordination": [string],
    "estimator_note": string|null,
    "confidence": number
  }],
  "project_risks": [{
    "severity": "low"|"medium"|"high",
    "category": string,
    "issue": string,
    "affected_openings": [string],
    "recommendation": string,
    "status": "Open"
  }],
  "rfi_log": [{
    "priority": "low"|"medium"|"high",
    "category": string,
    "question": string,
    "affected_openings": [string],
    "recommendation": string,
    "status": "Open",
    "reason": string
  }],
  "estimator_notes": [string],
  "bid_recommendations": {
    "supply_only_notes": [string],
    "installation_only_notes": [string],
    "supply_and_installation_notes": [string],
    "exclusions_to_consider": [string],
    "allowances_to_consider": [string],
    "coordination_items": [string]
  }
}

No prose outside the JSON. No markdown. No code fences. Strict JSON only.`;

async function extractFromPdfFast({ apiKey, scope, file, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');
  onProgress?.({ kind: 'info', text: `Reading ${file.name} (${(file.size/1024).toFixed(1)} KB)…` });
  const arrayBuffer = await file.arrayBuffer();
  const base64 = arrayBufferToBase64(arrayBuffer);
  const dataUrl = `data:application/pdf;base64,${base64}`;

  const userInstruction = `Project scope: ${scope || 'Supply & Installation'}

Read the attached PDF end-to-end. Transcribe every door schedule row and every hardware set with every line item. Then run senior-estimator analysis and produce the complete JSON per your system instructions.

Take your time. Use extended thinking. Read multi-column hardware-set pages thoroughly. Cross-reference door schedule hardware_set values against the hardware set ids (canonical match — strip prefixes like "Hardware Group No.", "HW-", "Set ").

Return the comprehensive JSON.`;

  const startedAt = Date.now();
  let tickInterval;
  try {
    tickInterval = setInterval(() => {
      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      onProgress?.({ kind: 'info', text: `gpt-5.5 thinking · ${elapsed}s elapsed…` });
    }, 15000);

    const body = {
      model: REQUIRED_MODEL,
      input: [
        { role: 'system', content: SINGLE_SHOT_SYSTEM },
        { role: 'user', content: [
          { type: 'input_file', filename: file.name, file_data: dataUrl },
          { type: 'input_text', text: userInstruction },
        ] },
      ],
      reasoning: { effort: 'high' },
      text: { format: { type: 'json_object' } },
      max_output_tokens: 64000,
    };
    onProgress?.({ kind: 'info', text: `Sending PDF to ${REQUIRED_MODEL} (single-pass with extended thinking)…` });
    const res = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    let data;
    try { data = await res.json(); } catch { throw new Error('Network error contacting OpenAI'); }
    if (!res.ok) {
      // If gpt-5.5 rejects the reasoning param or other field, retry without it
      const msg = data?.error?.message || '';
      if (/reasoning|effort|parameter/i.test(msg)) {
        onProgress?.({ kind: 'warn', text: `Retrying without reasoning param: ${msg}` });
        delete body.reasoning;
        const res2 = await fetch('https://api.openai.com/v1/responses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
          body: JSON.stringify(body),
        });
        data = await res2.json();
        if (!res2.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res2.status));
      } else {
        throw new Error(msg || ('OpenAI error ' + res.status));
      }
    }
    let text = data.output_text || '';
    if (!text && Array.isArray(data.output)) {
      for (const item of data.output) {
        if (item?.content) for (const c of item.content) if (typeof c?.text === 'string') text += c.text;
      }
    }
    if (!text) text = '{}';
    const incompleteReason = data.incomplete_details?.reason;
    const elapsed = Math.round((Date.now() - startedAt) / 1000);
    onProgress?.({ kind: 'ok', text: `gpt-5.5 returned in ${elapsed}s · ${(text.length/1024).toFixed(1)} KB JSON${incompleteReason ? ' · ' + incompleteReason : ''}` });
    if (incompleteReason === 'max_output_tokens') onProgress?.({ kind: 'warn', text: `Output was truncated at max_output_tokens — large project. Consider running again or splitting.` });

    let parsed;
    try { parsed = JSON.parse(text); }
    catch (e) {
      // Try to recover: find last complete JSON object
      const lastBrace = text.lastIndexOf('}');
      if (lastBrace > 0) {
        try { parsed = JSON.parse(text.slice(0, lastBrace + 1)); }
        catch { throw new Error('Model returned invalid JSON' + (incompleteReason ? ' (' + incompleteReason + ')' : '')); }
      } else throw new Error('Model returned invalid JSON');
    }

    // Post-process: canonical-key reconciliation + door↔hardware mapping + heuristic risk merge
    const door_analysis = Array.isArray(parsed.door_analysis) ? parsed.door_analysis : [];
    let hardware_set_review = Array.isArray(parsed.hardware_set_review) ? parsed.hardware_set_review : [];

    // Reconcile: rewrite door.hardware_set to match the set's display id when canonical keys match
    const setByCanonical = new Map();
    hardware_set_review.forEach(s => { if (s.hardware_set) setByCanonical.set(canonicalSetKey(s.hardware_set), s); });
    door_analysis.forEach(d => {
      if (!d.hardware_set) return;
      const key = canonicalSetKey(d.hardware_set);
      const matching = setByCanonical.get(key);
      if (matching && matching.hardware_set !== d.hardware_set) {
        d.raw_hardware_set = d.hardware_set;
        d.hardware_set = matching.hardware_set;
      }
    });
    // Refresh referenced_by_doors
    hardware_set_review.forEach(s => {
      s.referenced_by_doors = door_analysis.filter(d => d.hardware_set === s.hardware_set).map(d => d.mark);
    });
    // Add stub entries for sets referenced but not extracted
    const extractedSetIds = new Set(hardware_set_review.map(s => s.hardware_set));
    door_analysis.forEach(d => {
      if (d.hardware_set && !extractedSetIds.has(d.hardware_set)) {
        hardware_set_review.push({
          hardware_set: d.hardware_set,
          header_verbatim: null,
          referenced_by_doors: door_analysis.filter(x => x.hardware_set === d.hardware_set).map(x => x.mark),
          status: 'missing',
          items: [],
          missing_or_unclear_items: ['hardware set referenced by doors but not found in spec'],
          special_coordination: [],
          estimator_note: null,
          confidence: 0.4,
        });
        extractedSetIds.add(d.hardware_set);
      }
    });

    // Build door↔hardware mapping
    const setByDisplayId = new Map(hardware_set_review.map(s => [s.hardware_set, s]));
    const door_hardware_mapping = [];
    door_analysis.forEach(d => {
      if (!d.hardware_set) {
        door_hardware_mapping.push({ door_mark: d.mark, hardware_set: null, item_no: null, qty: null, description: '(no hardware set assigned)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'NO_HW_SET' });
        return;
      }
      const set = setByDisplayId.get(d.hardware_set);
      if (!set || !set.items || !set.items.length) {
        door_hardware_mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: set ? '(hardware set has no extracted items)' : '(hardware set not found in spec)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED' });
        return;
      }
      set.items.forEach((it, i) => {
        door_hardware_mapping.push({
          door_mark: d.mark,
          hardware_set: d.hardware_set,
          item_no: it.item_no ?? (i + 1),
          qty: it.qty,
          description: it.desc || '',
          catalog_number: it.part || null,
          manufacturer: it.mfr || null,
          finish: it.finish || null,
          notes: it.notes || null,
          status: 'OK',
        });
      });
    });

    // Merge heuristic risks/RFIs for coverage
    const synth = synthesizeRisksAndRFIs(door_analysis, hardware_set_review, scope);
    const merged = mergeRisksAndRFIs(parsed, synth);

    // Project summary with derived counts
    const ps = parsed.project_summary || {};
    const project_summary = {
      scope_type: scope,
      project_name: ps.project_name || null,
      project_number: ps.project_number || null,
      architect: ps.architect || null,
      address: ps.address || null,
      drawing: ps.drawing || null,
      date: ps.date || null,
      total_openings_found: door_analysis.length,
      total_hardware_sets_referenced: new Set(door_analysis.map(d => d.hardware_set).filter(Boolean)).size,
      hardware_sets_missing_or_unclear: hardware_set_review.filter(s => s.status !== 'complete').length,
      high_risk_openings: door_analysis.filter(d => d.risk_level === 'high').length,
      medium_risk_openings: door_analysis.filter(d => d.risk_level === 'medium').length,
      low_risk_openings: door_analysis.filter(d => d.risk_level === 'low').length,
      complex_installations: door_analysis.filter(d => d.install_complexity === 'high').length,
      access_control_openings: door_analysis.filter(d => (d.special_conditions || []).some(c => /CR|EL|DPS|card|access|electrified/i.test(c))).length,
      exterior_openings: door_analysis.filter(d => d.interior_or_exterior === 'Exterior').length,
      fire_rated_openings: door_analysis.filter(d => d.fire_rating && d.fire_rating !== '-' && !/^non/i.test(String(d.fire_rating))).length,
      overall_bid_risk: ps.overall_bid_risk || 'Medium',
      estimator_summary: ps.estimator_summary || `Single-pass native pipeline (${REQUIRED_MODEL}, extended thinking, ${elapsed}s) extracted ${door_analysis.length} opening(s) and ${hardware_set_review.length} hardware set(s) with ${hardware_set_review.reduce((n,s)=>n+(s.items?.length||0),0)} line items. Verify against source PDF before bidding.`,
    };

    const totalItems = hardware_set_review.reduce((n, s) => n + (s.items?.length || 0), 0);
    onProgress?.({ kind: 'ok', text: `Done · ${door_analysis.length} doors · ${hardware_set_review.length} sets · ${totalItems} items · ${merged.risks.length} risks · ${merged.rfis.length} RFIs · ${elapsed}s total` });

    return {
      analysis: {
        project_summary,
        door_analysis,
        hardware_set_review,
        door_hardware_mapping,
        project_risks: merged.risks,
        rfi_log: merged.rfis,
        estimator_notes: merged.notes,
        bid_recommendations: merged.recs,
      },
      qa: {
        pdf_type: 'NATIVE_SINGLE_SHOT',
        pipeline: 'native-single-shot',
        model: REQUIRED_MODEL,
        elapsed_seconds: elapsed,
        reasoning_effort: 'high',
        raw_transcription: { doors: door_analysis.map(d => ({ mark: d.mark })), hardware_sets: hardware_set_review.map(s => ({ id: s.hardware_set, item_count: s.items?.length || 0 })) },
        truncated: incompleteReason === 'max_output_tokens',
        reasoning_succeeded: true,
        extraction_complete: !incompleteReason,
        extraction_failures: [],
      },
    };
  } finally {
    if (tickInterval) clearInterval(tickInterval);
  }
}

/* ====================================================================
   STAGED PIPELINE — per user spec
     Call 1: door schedule extraction         (prompts/door_schedule_extraction.md)
     Call 2: hardware set extraction          (prompts/hardware_set_extraction.md)
     Code  : mapping (door → hardware set)    (prompts/door_hardware_mapping.md)
     Code  : rollup (project summary metrics)
     Call 3: RFI / coordination review (opt.) (prompts/rfi_coordination_review.md)
     Code  : Excel generation (existing exporter)
   The three prompt files in /prompts are the source of truth — these
   constants are kept in lockstep with them.
==================================================================== */

const STAGED_DOOR_SYSTEM = `You are extracting a door schedule from a construction drawing.

Return structured JSON only.

First, capture project-level header information from any cover sheet, title block, or schedule header visible in the drawing:
- project_name
- architect

Also capture, if visible anywhere on the door-schedule sheet(s):
- general_notes: array of free-text notes adjacent to or above the door schedule. Include sheet-level "General Notes", "Door Schedule Notes", "Door Notes", finish notes, "see drawings for X" callouts, alternates, allowances, and scope statements that affect Division 8. One string per logical note. Preserve text verbatim.
- schedule_legend: object mapping each abbreviation defined on the schedule (e.g. "CR", "EL", "DPS", "RX", "AO", "EH") to its expanded meaning verbatim from the legend panel. Empty object if no legend is visible.
- keying_notes: array of any keying-related instructions visible on the door-schedule sheet (master/sub-master structure, keyway, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, etc.). Verbatim. Empty array if none.

Then extract every visible door schedule row.

For each door, capture:
- mark
- room_or_location
- width
- height
- thickness
- door_type
- door_material
- door_finish
- frame_type
- frame_material
- frame_finish
- glazing
- fire_rating
- hardware_set
- closer
- electric_or_access_control
- remarks
- source_page
- source_crop_id
- confidence

Rules:
- Preserve text exactly as shown.
- Do not infer missing values.
- Use null if unclear.
- Do not complete missing door numbers.
- Do not assume hardware items from the hardware set name.
- Existing-to-remain doors must be marked as existing_to_remain.
- If the row is partially unclear, still extract visible fields and mark confidence below 0.75.
- For project_name and architect: read verbatim from the title block / cover sheet. Use null if not visible. Do not abbreviate or paraphrase.
- For general_notes, schedule_legend, and keying_notes: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent abbreviation meanings — only include legend entries that are explicitly defined on the sheet.

Return JSON only in this exact shape:
{ "project_name": string|null, "architect": string|null, "general_notes": [string], "schedule_legend": { [abbrev: string]: string }, "keying_notes": [string], "doors": [ { "mark": string|null, "room_or_location": string|null, "width": string|null, "height": string|null, "thickness": string|null, "door_type": string|null, "door_material": string|null, "door_finish": string|null, "frame_type": string|null, "frame_material": string|null, "frame_finish": string|null, "glazing": string|null, "fire_rating": string|null, "hardware_set": string|null, "closer": string|null, "electric_or_access_control": string|null, "remarks": string|null, "existing_to_remain": boolean, "source_page": number|string|null, "source_crop_id": string|null, "confidence": number } ] }`;

const STAGED_HW_SYSTEM = `You are extracting hardware set descriptions from a construction drawing crop.

Return structured JSON only.

First, capture any sheet-level context visible alongside the hardware sets:
- hardware_preamble: array of free-text notes that appear above, beside, or below the hardware sets — e.g. "All hardware to comply with ANSI A156.x", manufacturer/finish standards, substitution rules, scope notes for electrified hardware, "EC to provide 120 V", etc. One string per logical note. Verbatim. Empty array if none.
- keying_notes: array of keying-related instructions visible on the hardware-set sheet(s) (master/sub-master structure, keyway brand, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, allowance counts, etc.). Verbatim. Empty array if none.
- hardware_legend: object mapping any abbreviations defined on the hardware sheet (e.g. "REX", "DPS", "EPT", "AO") to their expanded meanings. Empty object if no legend.

Then extract every visible hardware set or hardware group in this crop.

For each hardware set, capture:
- hardware_set
- set_title
- referenced_doors
- status: active / not_used / existing / void / review_required
- set_notes
- items

For each item, capture:
- item_seq
- qty
- unit
- description
- manufacturer
- model_or_catalog
- finish
- notes
- confidence

Rules:
- Extract item rows exactly as visible.
- Do not guess manufacturer or model.
- Do not merge multiple hardware sets.
- Do NOT emit the same hardware_set id more than once. If the same set appears across multiple pages or columns, combine its visible items into a single entry.
- Do NOT emit the same item line twice within a set. If the same item appears twice in the same set on the drawing, list it once.
- If text is unclear, return null and lower confidence.
- If a hardware set says NOT USED, mark status as not_used.
- If existing hardware is to remain, mark status as existing.
- Do not map doors in this step.
- Do not create RFIs in this step.
- For hardware_preamble, keying_notes, and hardware_legend: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent legend meanings.
- Return only the extracted hardware set JSON.

Return JSON only in this exact shape:
{ "hardware_preamble": [string], "keying_notes": [string], "hardware_legend": { [abbrev: string]: string }, "hardware_sets": [ { "hardware_set": string, "set_title": string|null, "referenced_doors": [string], "status": "active"|"not_used"|"existing"|"void"|"review_required", "set_notes": string|null, "items": [ { "item_seq": number|string|null, "qty": number|string|null, "unit": string|null, "description": string|null, "manufacturer": string|null, "model_or_catalog": string|null, "finish": string|null, "notes": string|null, "confidence": number } ] } ] }`;

const STAGED_RFI_SYSTEM = `You are a senior doors, frames, and hardware estimator.

Review the extracted door schedule, hardware sets, door-to-hardware mapping, and any sheet-level context that was captured (general notes, schedule legend, keying notes, hardware preamble).

Use the sheet-level context as your source of truth for project-specific conventions:
- The schedule_legend / hardware_legend tells you what each abbreviation means for THIS project. Use those meanings — do not assume the industry-standard meaning if the project defines its own.
- The general_notes and hardware_preamble may explicitly include or exclude scope (e.g. "EC provides 120 V", "owner-supplied cylinders", "alternate #3 deletes hardware sets 9-12"). Reflect those in your RFIs and coordination notes — do NOT generate an RFI for something the notes already resolve.
- The keying_notes may already answer questions about keyway / master-key / construction cores. Skip RFIs the notes already answer.

Create RFIs and coordination notes only for real issues.

Flag:
- Missing hardware set
- Hardware set referenced but no item rows extracted
- Existing door with new hardware ambiguity
- Exterior door without threshold/weatherstrip/sweep
- Access control / card reader / electrified hardware
- Panic / egress hardware
- Double door missing pair hardware components
- Fire-rated or smoke-rated opening requiring verification
- Door remarks that conflict with hardware set
- Door type that does not match assigned hardware set
- Hardware set marked not used but referenced by door
- Storefront or aluminum entrance coordination

Return:
- severity
- category
- issue
- affected_doors
- recommendation

Return JSON only in this exact shape:
{ "rfis": [ { "severity": "low"|"medium"|"high", "category": string, "issue": string, "affected_doors": [string], "recommendation": string } ] }`;

/* Shared response-API caller. system+user → parsed JSON. */
async function _stagedOpenAICall({ apiKey, label, input, onProgress, maxTokens = 32000, reasoningEffort = 'high' }) {
  const startedAt = Date.now();
  const body = {
    model: REQUIRED_MODEL,
    input,
    reasoning: { effort: reasoningEffort },
    text: { format: { type: 'json_object' } },
    max_output_tokens: maxTokens,
  };
  let tickInterval;
  try {
    tickInterval = setInterval(() => {
      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      onProgress?.({ kind: 'info', text: `${label} · gpt-5.5 thinking · ${elapsed}s elapsed…` });
    }, 15000);
    let res = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    let data;
    try { data = await res.json(); } catch { throw new Error(`${label}: network error`); }
    if (!res.ok) {
      const msg = data?.error?.message || '';
      if (/reasoning|effort|parameter/i.test(msg)) {
        onProgress?.({ kind: 'warn', text: `${label} · retrying without reasoning param: ${msg}` });
        delete body.reasoning;
        res = await fetch('https://api.openai.com/v1/responses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
          body: JSON.stringify(body),
        });
        data = await res.json();
        if (!res.ok) throw new Error(`${label}: ${data?.error?.message || ('OpenAI error ' + res.status)}`);
      } else {
        throw new Error(`${label}: ${msg || ('OpenAI error ' + res.status)}`);
      }
    }
    let text = data.output_text || '';
    if (!text && Array.isArray(data.output)) {
      for (const item of data.output) {
        if (item?.content) for (const c of item.content) if (typeof c?.text === 'string') text += c.text;
      }
    }
    if (!text) text = '{}';
    const truncated = data.incomplete_details?.reason === 'max_output_tokens';
    const elapsed = Math.round((Date.now() - startedAt) / 1000);
    onProgress?.({ kind: 'ok', text: `${label} · returned in ${elapsed}s · ${(text.length/1024).toFixed(1)} KB${truncated ? ' · TRUNCATED' : ''}` });
    let parsed;
    try { parsed = JSON.parse(text); }
    catch {
      const lastBrace = text.lastIndexOf('}');
      if (lastBrace > 0) { try { parsed = JSON.parse(text.slice(0, lastBrace + 1)); } catch { throw new Error(`${label}: invalid JSON`); } }
      else throw new Error(`${label}: invalid JSON`);
    }
    return { parsed, elapsed, truncated };
  } finally {
    if (tickInterval) clearInterval(tickInterval);
  }
}

/* Normalize Call 1 door row → the app's expected door_analysis shape. */
function _stagedNormalizeDoor(d) {
  const remarksRaw = d.remarks;
  const remarks = Array.isArray(remarksRaw) ? remarksRaw.filter(Boolean) : (remarksRaw ? [String(remarksRaw)] : []);
  const remarksStr = remarks.join(' ');
  const etrExplicit = d.existing_to_remain === true;
  const etrInferred = /existing[\s_-]*to[\s_-]*remain|\bETR\b/i.test(remarksStr);
  return {
    mark: d.mark ?? null,
    room_or_location: d.room_or_location ?? null,
    door_type: d.door_type ?? null,
    opening_type: d.door_type ?? null,
    interior_or_exterior: null,
    size: { width: d.width ?? null, height: d.height ?? null, thickness: d.thickness ?? null },
    door_material: d.door_material ?? null,
    door_finish: d.door_finish ?? null,
    glazing: d.glazing ?? null,
    frame_type: d.frame_type ?? null,
    frame_material: d.frame_material ?? null,
    frame_finish: d.frame_finish ?? null,
    fire_rating: d.fire_rating ?? null,
    hardware_set: d.hardware_set ?? null,
    closer: d.closer ?? null,
    electric_or_access_control: d.electric_or_access_control ?? null,
    remarks,
    existing_to_remain: etrExplicit || etrInferred,
    hardware_status: 'review required',
    install_complexity: 'medium',
    risk_level: 'medium',
    special_conditions: [],
    issues: [],
    recommendations: [],
    rfi_required: false,
    rfi_questions: [],
    source_page: d.source_page ?? null,
    source_crop_id: d.source_crop_id ?? null,
    confidence: typeof d.confidence === 'number' ? d.confidence : 0.7,
  };
}

/* Normalize Call 2 hardware set → the app's expected hardware_set_review shape. */
function _stagedNormalizeSet(s) {
  const rawItems = Array.isArray(s.items) ? s.items : [];
  const seenItemSigs = new Set();
  const items = [];
  rawItems.forEach((it, i) => {
    const item = {
      item_no: it.item_seq ?? it.item_no ?? (i + 1),
      qty: it.qty ?? null,
      unit: it.unit ?? null,
      desc: it.description ?? it.desc ?? '',
      part: it.model_or_catalog ?? it.part ?? null,
      mfr: it.manufacturer ?? it.mfr ?? null,
      finish: it.finish ?? null,
      notes: it.notes ?? null,
      confidence: typeof it.confidence === 'number' ? it.confidence : null,
    };
    // Dedup within-set by (item_no, desc, part)
    const sig = `${item.item_no ?? ''}|${(item.desc || '').trim().toLowerCase()}|${(item.part || '').trim().toLowerCase()}`;
    if (seenItemSigs.has(sig)) return;
    seenItemSigs.add(sig);
    items.push(item);
  });
  const rawStatus = String(s.status || '').toLowerCase().trim();
  let status = 'incomplete';
  if (rawStatus === 'active') status = items.length ? 'complete' : 'incomplete';
  else if (rawStatus === 'not_used' || rawStatus === 'void') status = 'voided';
  else if (rawStatus === 'existing') status = items.length ? 'complete' : 'incomplete';
  else if (rawStatus === 'review_required') status = 'incomplete';
  else if (items.length) status = 'complete';
  const missing = [];
  if (!items.length && rawStatus !== 'not_used' && rawStatus !== 'void') missing.push('no hardware items extracted');
  return {
    hardware_set: s.hardware_set ?? s.id ?? null,
    header_verbatim: s.set_title ?? null,
    referenced_by_doors: Array.isArray(s.referenced_doors) ? s.referenced_doors : [],
    status,
    raw_status: rawStatus || null,
    items,
    missing_or_unclear_items: missing,
    special_coordination: [],
    estimator_note: s.set_notes ?? null,
    confidence: typeof s.confidence === 'number' ? s.confidence : 0.7,
  };
}

/* Code-step: door → hardware set mapping per prompts/door_hardware_mapping.md */
function _stagedMapDoorsHardware(doors, sets) {
  const qaIssues = [];
  const setByCanonical = new Map();
  sets.forEach(s => { if (s.hardware_set) setByCanonical.set(canonicalSetKey(s.hardware_set), s); });
  // canonical-key reconciliation
  doors.forEach(d => {
    if (!d.hardware_set) return;
    const k = canonicalSetKey(d.hardware_set);
    const m = setByCanonical.get(k);
    if (m && m.hardware_set !== d.hardware_set) {
      d.raw_hardware_set = d.hardware_set;
      d.hardware_set = m.hardware_set;
    }
  });
  // refresh references
  sets.forEach(s => { s.referenced_by_doors = doors.filter(d => d.hardware_set === s.hardware_set).map(d => d.mark); });
  // stub missing sets + QA
  const haveIds = new Set(sets.map(s => s.hardware_set));
  doors.forEach(d => {
    if (d.hardware_set && !haveIds.has(d.hardware_set)) {
      sets.push({
        hardware_set: d.hardware_set,
        header_verbatim: null,
        referenced_by_doors: doors.filter(x => x.hardware_set === d.hardware_set).map(x => x.mark),
        status: 'missing',
        raw_status: null,
        items: [],
        missing_or_unclear_items: ['hardware set referenced by doors but not found in spec'],
        special_coordination: [],
        estimator_note: null,
        confidence: 0.3,
      });
      haveIds.add(d.hardware_set);
      qaIssues.push({ kind: 'missing_set', set: d.hardware_set, mark: d.mark, message: `Door ${d.mark} references hardware set ${d.hardware_set} but the set was not extracted.` });
    }
  });
  // build door↔hw mapping
  const mapping = [];
  const setByDisplayId = new Map(sets.map(s => [s.hardware_set, s]));
  doors.forEach(d => {
    if (d.existing_to_remain) {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set || null, item_no: null, qty: null, description: '(existing door — hardware to remain; not mapped per rule)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'EXISTING_TO_REMAIN' });
      return;
    }
    if (!d.hardware_set) {
      mapping.push({ door_mark: d.mark, hardware_set: null, item_no: null, qty: null, description: '(no hardware set assigned)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'NO_HW_SET' });
      qaIssues.push({ kind: 'no_hw_set', mark: d.mark, message: `Door ${d.mark} has no hardware set assigned.` });
      return;
    }
    const set = setByDisplayId.get(d.hardware_set);
    if (!set) {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: '(hardware set not found in spec)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED' });
      return;
    }
    if (set.raw_status === 'not_used' || set.raw_status === 'void') {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: '(hardware set marked NOT USED / VOID)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'SET_NOT_USED' });
      qaIssues.push({ kind: 'set_not_used_but_referenced', set: d.hardware_set, mark: d.mark, message: `Door ${d.mark} references set ${d.hardware_set} which is marked NOT USED.` });
      return;
    }
    if (!set.items || !set.items.length) {
      mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: '(hardware set has no extracted items)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED' });
      qaIssues.push({ kind: 'set_empty', set: d.hardware_set, mark: d.mark, message: `Door ${d.mark}: hardware set ${d.hardware_set} has zero items.` });
      return;
    }
    set.items.forEach((it, i) => {
      mapping.push({
        door_mark: d.mark,
        hardware_set: d.hardware_set,
        item_no: it.item_no ?? (i + 1),
        qty: it.qty,
        description: it.desc || '',
        catalog_number: it.part || null,
        manufacturer: it.mfr || null,
        finish: it.finish || null,
        notes: it.notes || null,
        status: 'OK',
      });
    });
  });
  return { mapping, qaIssues };
}

/* Code-step: rollup project summary metrics. */
function _stagedRollupSummary(doors, sets, scope, elapsedSeconds, meta = {}) {
  const isAccessCtrl = (d) => {
    const v = String(d.electric_or_access_control || '').trim();
    if (!v) return false;
    return !/^(no|none|n\/a|null|-)$/i.test(v);
  };
  const isFireRated = (d) => {
    const v = String(d.fire_rating || '').trim();
    if (!v) return false;
    return !/^(none|non|n\/a|null|-)$/i.test(v);
  };
  return {
    scope_type: scope,
    project_name: meta.project_name || null,
    project_number: meta.project_number || null,
    architect: meta.architect || null,
    address: meta.address || null,
    drawing: meta.drawing || null,
    date: meta.date || null,
    total_openings_found: doors.length,
    total_hardware_sets_referenced: new Set(doors.map(d => d.hardware_set).filter(Boolean)).size,
    hardware_sets_missing_or_unclear: sets.filter(s => s.status !== 'complete').length,
    high_risk_openings: doors.filter(d => d.risk_level === 'high').length,
    medium_risk_openings: doors.filter(d => d.risk_level === 'medium').length,
    low_risk_openings: doors.filter(d => d.risk_level === 'low').length,
    complex_installations: doors.filter(d => d.install_complexity === 'high').length,
    access_control_openings: doors.filter(isAccessCtrl).length,
    exterior_openings: doors.filter(d => d.interior_or_exterior === 'Exterior').length,
    fire_rated_openings: doors.filter(isFireRated).length,
    overall_bid_risk: 'Medium',
    estimator_summary: `Staged pipeline (Call 1 doors · Call 2 hardware · code mapping + rollup${elapsedSeconds ? ` · ${elapsedSeconds}s` : ''}) extracted ${doors.length} opening(s) and ${sets.length} hardware set(s). Verify against source PDF before bidding.`,
  };
}

async function extractFromPdfStaged({ apiKey, scope, file, onProgress, runRFIs = true }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');
  onProgress?.({ kind: 'info', text: `Reading ${file.name} (${(file.size/1024).toFixed(1)} KB)…` });
  const arrayBuffer = await file.arrayBuffer();
  const dataUrl = `data:application/pdf;base64,${arrayBufferToBase64(arrayBuffer)}`;
  const scopeStr = scope || 'Supply & Installation';

  // ---------- CALL 1 — door schedule extraction ----------
  onProgress?.({ kind: 'info', text: `Call 1 / Door schedule extraction — sending PDF…` });
  const call1 = await _stagedOpenAICall({
    apiKey,
    label: 'Call 1 (doors)',
    onProgress,
    maxTokens: 32000,
    input: [
      { role: 'system', content: STAGED_DOOR_SYSTEM },
      { role: 'user', content: [
        { type: 'input_file', filename: file.name, file_data: dataUrl },
        { type: 'input_text', text: `Project scope: ${scopeStr}\n\nRead the attached PDF end-to-end. Extract every visible door schedule row per your system instructions. Preserve text exactly as shown — do not infer. Use null for unclear values.\n\nAlso capture, if visible on the door-schedule sheet(s):\n- general_notes (verbatim free-text notes adjacent to the schedule)\n- schedule_legend (abbreviation → meaning map for codes like CR / EL / DPS / RX / AO defined on the legend panel)\n- keying_notes (verbatim keying-related instructions)\n\nReturn JSON: { "project_name": ..., "architect": ..., "general_notes": [...], "schedule_legend": {...}, "keying_notes": [...], "doors": [...] }` },
      ] },
    ],
  });
  const rawDoors = Array.isArray(call1.parsed.doors) ? call1.parsed.doors
                 : Array.isArray(call1.parsed.rows)  ? call1.parsed.rows
                 : Array.isArray(call1.parsed.door_analysis) ? call1.parsed.door_analysis : [];
  const doors = rawDoors.map(_stagedNormalizeDoor);
  const projectMeta = {
    project_name: call1.parsed.project_name ?? call1.parsed.project?.name ?? null,
    architect:    call1.parsed.architect    ?? call1.parsed.project?.architect ?? null,
  };
  // Sheet-level context from Call 1 (door-schedule sheets).
  const doorSheetContext = {
    general_notes: Array.isArray(call1.parsed.general_notes) ? call1.parsed.general_notes.filter(x => typeof x === 'string' && x.trim()) : [],
    schedule_legend: (call1.parsed.schedule_legend && typeof call1.parsed.schedule_legend === 'object' && !Array.isArray(call1.parsed.schedule_legend)) ? call1.parsed.schedule_legend : {},
    keying_notes: Array.isArray(call1.parsed.keying_notes) ? call1.parsed.keying_notes.filter(x => typeof x === 'string' && x.trim()) : [],
  };
  onProgress?.({ kind: 'ok', text: `Call 1 done · ${doors.length} door row(s) extracted${projectMeta.project_name ? ` · project: ${projectMeta.project_name}` : ''}${projectMeta.architect ? ` · architect: ${projectMeta.architect}` : ''}${doorSheetContext.general_notes.length ? ` · ${doorSheetContext.general_notes.length} general note(s)` : ''}${Object.keys(doorSheetContext.schedule_legend).length ? ` · ${Object.keys(doorSheetContext.schedule_legend).length} legend entries` : ''}.` });

  // ---------- CALL 2 — hardware set extraction ----------
  onProgress?.({ kind: 'info', text: `Call 2 / Hardware set extraction — sending PDF…` });
  const call2 = await _stagedOpenAICall({
    apiKey,
    label: 'Call 2 (hardware sets)',
    onProgress,
    maxTokens: 48000,
    input: [
      { role: 'system', content: STAGED_HW_SYSTEM },
      { role: 'user', content: [
        { type: 'input_file', filename: file.name, file_data: dataUrl },
        { type: 'input_text', text: `Project scope: ${scopeStr}\n\nRead the attached PDF end-to-end. Extract every visible hardware set / hardware group per your system instructions, with every line item. Do not map doors and do not create RFIs in this step.\n\nAlso capture sheet-level context: hardware_preamble (verbatim notes above/beside the hardware sets), keying_notes (verbatim keying instructions), and hardware_legend (abbreviation → meaning map for codes defined on the hardware sheet).\n\nReturn JSON: { "hardware_preamble": [...], "keying_notes": [...], "hardware_legend": {...}, "hardware_sets": [...] }` },
      ] },
    ],
  });
  const rawSets = Array.isArray(call2.parsed.hardware_sets) ? call2.parsed.hardware_sets
                : Array.isArray(call2.parsed.sets) ? call2.parsed.sets : [];
  const setsBeforeDedup = rawSets.map(_stagedNormalizeSet);
  // Sheet-level context from Call 2 (hardware-set sheets).
  const hwSheetContext = {
    hardware_preamble: Array.isArray(call2.parsed.hardware_preamble) ? call2.parsed.hardware_preamble.filter(x => typeof x === 'string' && x.trim()) : [],
    keying_notes: Array.isArray(call2.parsed.keying_notes) ? call2.parsed.keying_notes.filter(x => typeof x === 'string' && x.trim()) : [],
    hardware_legend: (call2.parsed.hardware_legend && typeof call2.parsed.hardware_legend === 'object' && !Array.isArray(call2.parsed.hardware_legend)) ? call2.parsed.hardware_legend : {},
  };

  // ----- Dedup hardware sets by canonical key (Call 2 sometimes returns the same set
  //       more than once when it spans multiple pages / columns). Merge items by
  //       (item_no, desc) signature so legitimate distinct items survive but
  //       verbatim repeats collapse. -----
  const setsByCanon = new Map();
  for (const s of setsBeforeDedup) {
    if (!s.hardware_set) { setsByCanon.set(`__unkeyed_${setsByCanon.size}`, s); continue; }
    const key = canonicalSetKey(s.hardware_set) || s.hardware_set;
    const existing = setsByCanon.get(key);
    if (!existing) { setsByCanon.set(key, s); continue; }
    // Merge into existing
    const itemSig = (it) => `${it.item_no ?? ''}|${(it.desc || '').trim().toLowerCase()}`;
    const seenSigs = new Set((existing.items || []).map(itemSig));
    for (const it of s.items || []) {
      const sig = itemSig(it);
      if (!seenSigs.has(sig)) { existing.items.push(it); seenSigs.add(sig); }
    }
    // Prefer the more-populated header / status
    if (!existing.header_verbatim && s.header_verbatim) existing.header_verbatim = s.header_verbatim;
    if (existing.status !== 'complete' && s.status === 'complete') existing.status = s.status;
    if (!existing.raw_status && s.raw_status) existing.raw_status = s.raw_status;
    if (!existing.estimator_note && s.estimator_note) existing.estimator_note = s.estimator_note;
    // Union referenced doors
    existing.referenced_by_doors = Array.from(new Set([...(existing.referenced_by_doors || []), ...(s.referenced_by_doors || [])]));
  }
  const sets = Array.from(setsByCanon.values());
  const dupCount = setsBeforeDedup.length - sets.length;
  const totalItems = sets.reduce((n, s) => n + (s.items?.length || 0), 0);
  onProgress?.({ kind: 'ok', text: `Call 2 done · ${sets.length} hardware set(s) · ${totalItems} line item(s)${dupCount > 0 ? ` · ${dupCount} duplicate set(s) merged` : ''}.` });

  // ---------- CONSOLIDATED SHEET CONTEXT ----------
  // Merge the two captures (door-schedule sheet + hardware-set sheet) into one
  // object. Both passes may surface keying notes; dedupe by lowercase text.
  const _dedupeStrings = (arr) => {
    const seen = new Set();
    const out = [];
    for (const s of arr) {
      const k = String(s || '').toLowerCase().trim();
      if (!k || seen.has(k)) continue;
      seen.add(k);
      out.push(s);
    }
    return out;
  };
  const _mergeLegend = (a, b) => {
    const out = {};
    Object.entries(a || {}).forEach(([k, v]) => { if (typeof v === 'string' && v.trim()) out[String(k).trim().toUpperCase()] = v.trim(); });
    Object.entries(b || {}).forEach(([k, v]) => {
      const key = String(k).trim().toUpperCase();
      if (!out[key] && typeof v === 'string' && v.trim()) out[key] = v.trim();
    });
    return out;
  };
  const sheetContext = {
    general_notes: _dedupeStrings(doorSheetContext.general_notes),
    hardware_preamble: _dedupeStrings(hwSheetContext.hardware_preamble),
    keying_notes: _dedupeStrings([...doorSheetContext.keying_notes, ...hwSheetContext.keying_notes]),
    legend: _mergeLegend(doorSheetContext.schedule_legend, hwSheetContext.hardware_legend),
  };
  onProgress?.({ kind: 'ok', text: `Sheet context captured · ${sheetContext.general_notes.length} general note(s) · ${sheetContext.hardware_preamble.length} preamble note(s) · ${sheetContext.keying_notes.length} keying note(s) · ${Object.keys(sheetContext.legend).length} legend entries.` });

  // ---------- CODE — mapping (door → hardware set) ----------
  onProgress?.({ kind: 'info', text: `Mapping · door → hardware set…` });
  const { mapping, qaIssues } = _stagedMapDoorsHardware(doors, sets);
  onProgress?.({ kind: 'ok', text: `Mapping done · ${mapping.length} mapping row(s) · ${qaIssues.length} QA issue(s).` });

  // ---------- CODE — rollup ----------
  const elapsedCore = (call1.elapsed || 0) + (call2.elapsed || 0);
  const project_summary = _stagedRollupSummary(doors, sets, scopeStr, elapsedCore, projectMeta);

  // ---------- CALL 3 — RFI / coordination review (optional) ----------
  let project_risks = [], rfi_log = [], call3Elapsed = 0, call3Skipped = !runRFIs;
  if (runRFIs) {
    try {
      onProgress?.({ kind: 'info', text: `Call 3 / RFI + coordination review — sending extracted data…` });
      const payload = {
        scope: scopeStr,
        sheet_context: sheetContext,
        doors: doors.map(d => ({
          mark: d.mark, room_or_location: d.room_or_location,
          door_type: d.door_type, size: d.size,
          door_material: d.door_material, fire_rating: d.fire_rating,
          hardware_set: d.hardware_set,
          closer: d.closer, electric_or_access_control: d.electric_or_access_control,
          remarks: d.remarks, existing_to_remain: d.existing_to_remain,
        })),
        hardware_sets: sets.map(s => ({
          hardware_set: s.hardware_set, status: s.status, raw_status: s.raw_status,
          item_count: s.items?.length || 0,
          item_descriptions: (s.items || []).map(it => it.desc).filter(Boolean),
        })),
        mapping_qa: qaIssues,
      };
      const call3 = await _stagedOpenAICall({
        apiKey,
        label: 'Call 3 (RFIs)',
        onProgress,
        maxTokens: 16000,
        reasoningEffort: 'medium',
        input: [
          { role: 'system', content: STAGED_RFI_SYSTEM },
          { role: 'user', content: [
            { type: 'input_text', text: `Review the following extracted data (already in canonical form). Produce only real-issue RFIs and coordination notes per your system instructions. Do not invent issues for clean rows.\n\nEXTRACTED_DATA:\n${JSON.stringify(payload)}\n\nReturn JSON: { "rfis": [...] }` },
          ] },
        ],
      });
      call3Elapsed = call3.elapsed || 0;
      const rfis = Array.isArray(call3.parsed.rfis) ? call3.parsed.rfis : [];
      rfi_log = rfis.map(r => ({
        priority: String(r.severity || 'medium').toLowerCase(),
        category: r.category || 'General',
        question: r.issue || '',
        affected_openings: Array.isArray(r.affected_doors) ? r.affected_doors : [],
        recommendation: r.recommendation || '',
        status: 'Open',
        reason: r.issue || '',
      }));
      project_risks = rfis.map(r => ({
        severity: String(r.severity || 'medium').toLowerCase(),
        category: r.category || 'General',
        issue: r.issue || '',
        affected_openings: Array.isArray(r.affected_doors) ? r.affected_doors : [],
        recommendation: r.recommendation || '',
        status: 'Open',
      }));
      onProgress?.({ kind: 'ok', text: `Call 3 done · ${rfis.length} RFI(s) / coordination note(s).` });
    } catch (e) {
      onProgress?.({ kind: 'warn', text: `Call 3 (RFI review) failed: ${e.message}. Continuing without RFIs.` });
      call3Skipped = true;
    }
  } else {
    onProgress?.({ kind: 'info', text: `Call 3 skipped (RFI review disabled).` });
  }

  const totalElapsed = elapsedCore + call3Elapsed;
  onProgress?.({ kind: 'ok', text: `Staged pipeline done · ${doors.length} doors · ${sets.length} sets · ${totalItems} items · ${project_risks.length} risks · ${rfi_log.length} RFIs · ${totalElapsed}s total.` });

  // Populate bid recommendations via heuristic synthesis (staged pipeline does not
  // ask the LLM for bid recs — we generate them from the extracted data + scope).
  const stagedSynth = synthesizeRisksAndRFIs(doors, sets, scopeStr, sheetContext);
  const stagedRecs = stagedSynth.recs;
  // Surface any mapping QA issues as coordination items so users see them here too.
  qaIssues.forEach(q => {
    const msg = q?.message;
    if (msg && !stagedRecs.coordination_items.includes(msg)) {
      stagedRecs.coordination_items.push(msg);
    }
  });

  return {
    analysis: {
      project_summary,
      door_analysis: doors,
      hardware_set_review: sets,
      door_hardware_mapping: mapping,
      sheet_context: sheetContext,
      project_risks,
      rfi_log,
      estimator_notes: stagedSynth.notes || [],
      bid_recommendations: stagedRecs,
    },
    qa: {
      pdf_type: 'STAGED_PIPELINE',
      pipeline: 'staged',
      pipeline_steps: [
        { step: 1, kind: 'llm', label: 'Door schedule extraction', prompt_file: 'prompts/door_schedule_extraction.md', elapsed_seconds: call1.elapsed, truncated: !!call1.truncated, output_count: doors.length },
        { step: 2, kind: 'llm', label: 'Hardware set extraction',   prompt_file: 'prompts/hardware_set_extraction.md', elapsed_seconds: call2.elapsed, truncated: !!call2.truncated, output_count: sets.length },
        { step: 3, kind: 'code', label: 'Door → hardware mapping', prompt_file: 'prompts/door_hardware_mapping.md', output_count: mapping.length },
        { step: 4, kind: 'code', label: 'Rollup' },
        { step: 5, kind: 'llm', label: 'RFI / coordination review', prompt_file: 'prompts/rfi_coordination_review.md', skipped: call3Skipped, elapsed_seconds: call3Elapsed, output_count: rfi_log.length },
        { step: 6, kind: 'code', label: 'Excel generation (on export)' },
      ],
      model: REQUIRED_MODEL,
      elapsed_seconds: totalElapsed,
      mapping_qa_issues: qaIssues,
      raw_transcription: {
        doors: doors.map(d => ({ mark: d.mark })),
        hardware_sets: sets.map(s => ({ id: s.hardware_set, item_count: s.items?.length || 0 })),
      },
      truncated: !!call1.truncated || !!call2.truncated,
      reasoning_succeeded: true,
      extraction_complete: !call1.truncated && !call2.truncated,
      extraction_failures: [],
    },
  };
}

/* ---------- Multi-pass native pipeline (fallback when fast pass truncates) ---------- */
async function extractFromPdfDirect({ apiKey, scope, file, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');
  onProgress?.({ kind: 'info', text: `Reading ${file.name} (${(file.size/1024).toFixed(1)} KB)…` });
  const arrayBuffer = await file.arrayBuffer();
  const base64 = arrayBufferToBase64(arrayBuffer);
  const dataUrl = `data:application/pdf;base64,${base64}`;
  const pdfFileBlock = { type: 'input_file', filename: file.name, file_data: dataUrl };

  const callResponses = async (system, userBlocks, maxTokens = 32000, label = '') => {
    const body = {
      model: REQUIRED_MODEL,
      input: [
        { role: 'system', content: system },
        { role: 'user', content: userBlocks },
      ],
      text: { format: { type: 'json_object' } },
      max_output_tokens: maxTokens,
    };
    const res = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    let data;
    try { data = await res.json(); } catch { throw new Error('Network error contacting OpenAI'); }
    if (!res.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
    let text = data.output_text || '';
    if (!text && Array.isArray(data.output)) {
      for (const item of data.output) {
        if (item?.content) {
          for (const c of item.content) {
            if (typeof c?.text === 'string') text += c.text;
          }
        }
      }
    }
    if (!text) text = '{}';
    const incompleteReason = data.incomplete_details?.reason;
    try {
      const parsed = JSON.parse(text);
      return { parsed, status: data.status, incompleteReason, raw_text_len: text.length, label };
    } catch {
      throw new Error('Model returned invalid JSON' + (incompleteReason === 'max_output_tokens' ? ' (output truncated — increase max_output_tokens)' : ''));
    }
  };

  /* ===== PASS 0 — Discovery: build a page index ===== */
  onProgress?.({ kind: 'info', text: `Pass 0 · scanning ${file.name} for content map…` });
  let discovery;
  try {
    const r = await callResponses(
      PDF_DISCOVERY_SYSTEM,
      [
        pdfFileBlock,
        { type: 'input_text', text: 'Scan every page and return the JSON index per your schema.' },
      ],
      16000,
      'discovery',
    );
    discovery = r.parsed || {};
    const pageCount = (discovery.pages || []).length;
    const schedPages = (discovery.pages || []).filter(p => (p.roles || []).some(rl => rl === 'door_schedule')).map(p => p.page);
    const hwPages = (discovery.pages || []).filter(p => (p.roles || []).some(rl => rl === 'hardware_sets' || rl === 'hardware_schedule')).map(p => p.page);
    const seenMarks = [...new Set((discovery.pages || []).flatMap(p => p.visible_door_marks || []))];
    const seenSetIds = [...new Set((discovery.pages || []).flatMap(p => p.visible_hardware_set_ids || []))];
    onProgress?.({ kind: 'ok', text: `Pass 0 · indexed ${pageCount} page(s) · schedule on p.${schedPages.join(',') || '—'} · hardware on p.${hwPages.join(',') || '—'} · ${seenMarks.length} door mark(s), ${seenSetIds.length} HW set id(s) visible` });
    if (r.incompleteReason) onProgress?.({ kind: 'warn', text: `Pass 0 incomplete: ${r.incompleteReason}` });
  } catch (e) {
    onProgress?.({ kind: 'warn', text: `Pass 0 discovery failed: ${e.message}. Continuing without page index.` });
    discovery = { pages: [], project_meta: {} };
  }

  /* ===== PASS A — Comprehensive transcription ===== */
  onProgress?.({ kind: 'info', text: `Pass A · transcribing every door + hardware set + line item…` });
  const discoveryHints = (() => {
    const seenMarks = [...new Set((discovery.pages || []).flatMap(p => p.visible_door_marks || []))];
    const seenSetIds = [...new Set((discovery.pages || []).flatMap(p => p.visible_hardware_set_ids || []))];
    let s = '';
    if (seenMarks.length) s += `\n\nFrom the discovery pass, these door marks are known to exist (read every one): ${seenMarks.join(', ')}`;
    if (seenSetIds.length) s += `\n\nFrom the discovery pass, these hardware set IDs are known to exist (capture every one with all line items): ${seenSetIds.join(', ')}`;
    if (discovery.estimated_door_total) s += `\n\nEstimated door count: ${discovery.estimated_door_total}.`;
    if (discovery.estimated_hardware_set_total) s += `\n\nEstimated hardware set count: ${discovery.estimated_hardware_set_total}.`;
    return s;
  })();

  const passA = await callResponses(
    EXTRACTION_ONLY_SYSTEM,
    [
      pdfFileBlock,
      { type: 'input_text', text: `Transcribe every door schedule row and every hardware set with all items. Return JSON per your schema.${discoveryHints}` },
    ],
    48000,
    'passA',
  );
  let raw = passA.parsed || {};
  let rawDoors = Array.isArray(raw.doors) ? raw.doors : [];
  let rawSets = Array.isArray(raw.hardware_sets) ? raw.hardware_sets : [];
  let rawTotalItems = rawSets.reduce((n, s) => n + (s.items?.length || 0), 0);
  onProgress?.({ kind: 'ok', text: `Pass A · ${rawDoors.length} door(s), ${rawSets.length} HW set(s), ${rawTotalItems} item(s)${passA.status ? ' · status=' + passA.status : ''}` });
  if (passA.incompleteReason) onProgress?.({ kind: 'warn', text: `Pass A incomplete: ${passA.incompleteReason} — verification pass will recover` });

  /* ===== PASS A2 — Verification: find what's missing, up to 3 iterations ===== */
  const seenMarksFromDiscovery = [...new Set((discovery.pages || []).flatMap(p => p.visible_door_marks || []))];
  const seenSetIdsFromDiscovery = [...new Set((discovery.pages || []).flatMap(p => p.visible_hardware_set_ids || []))];
  let verifyIter = 0;
  const MAX_VERIFY_ITERS = 3;
  while (verifyIter < MAX_VERIFY_ITERS) {
    verifyIter++;
    const haveMarks = rawDoors.map(d => d.mark).filter(Boolean);
    const haveSetIds = rawSets.map(s => s.id).filter(Boolean);
    const expectedMarks = seenMarksFromDiscovery;
    const expectedSetIds = seenSetIdsFromDiscovery;
    const missingMarksFromDiscovery = expectedMarks.filter(m => !haveMarks.includes(m));
    const missingSetIdsFromDiscovery = expectedSetIds.filter(s => !haveSetIds.includes(s));
    const referencedSetIdsFromDoors = [...new Set(rawDoors.map(d => d.hardware_set).filter(Boolean))];
    const orphanRefs = referencedSetIdsFromDoors.filter(setId => !haveSetIds.some(have =>
      canonicalSetKey(have) === canonicalSetKey(setId)
    ));
    const setsWithNoItems = rawSets.filter(s => !s.items || s.items.length === 0).map(s => s.id);

    // Decide if verification is worth running this iteration
    const expectedDoors = discovery.estimated_door_total ?? null;
    const expectedSets = discovery.estimated_hardware_set_total ?? null;
    const doorShortfall = expectedDoors && rawDoors.length < Math.max(1, Math.floor(expectedDoors * 0.95));
    const setShortfall = expectedSets && rawSets.length < Math.max(1, Math.floor(expectedSets * 0.95));
    const need =
         missingMarksFromDiscovery.length > 0
      || missingSetIdsFromDiscovery.length > 0
      || orphanRefs.length > 0
      || setsWithNoItems.length > 0
      || doorShortfall
      || setShortfall
      || (verifyIter === 1); // always run at least once

    if (!need) {
      onProgress?.({ kind: 'ok', text: `Verification ${verifyIter}: nothing flagged as missing — extraction looks complete.` });
      break;
    }

    onProgress?.({ kind: 'info', text: `Verification ${verifyIter}/${MAX_VERIFY_ITERS} · checking for missed entries (missing ${missingMarksFromDiscovery.length} marks, ${missingSetIdsFromDiscovery.length} sets, ${orphanRefs.length} orphan refs, ${setsWithNoItems.length} empty sets)…` });

    const verifyInstruction = `EXISTING EXTRACTION (DO NOT RE-EMIT THESE):
- Doors already extracted (by mark): ${haveMarks.join(', ') || '(none)'}
- Hardware sets already extracted (by id): ${haveSetIds.join(', ') || '(none)'}

KNOWN-TO-EXIST FROM PDF SCAN (from discovery pass — MUST be in final output):
- Door marks visible in PDF: ${expectedMarks.join(', ') || '(none enumerated)'}
- Hardware set IDs visible in PDF: ${expectedSetIds.join(', ') || '(none enumerated)'}

POTENTIAL ISSUES FLAGGED:
${missingMarksFromDiscovery.length ? `- Door marks seen in scan but not extracted: ${missingMarksFromDiscovery.join(', ')}` : ''}
${missingSetIdsFromDiscovery.length ? `- Hardware set IDs seen in scan but not extracted: ${missingSetIdsFromDiscovery.join(', ')}` : ''}
${orphanRefs.length ? `- Doors reference these set IDs but the set wasn't extracted: ${orphanRefs.join(', ')}. Look for them in the spec book or hardware-sets page.` : ''}
${setsWithNoItems.length ? `- These sets were extracted but with NO line items — re-read them and emit the items: ${setsWithNoItems.join(', ')}. (If they appear voided/crossed out, mark a remark "VOIDED" and still emit zero items.)` : ''}

Return JSON in the same schema as the original transcription, containing ONLY missing doors and missing/incomplete hardware sets. If a hardware set was already extracted but missing items, RE-EMIT THE WHOLE SET with the full item list. If a door's hardware_set field was blank, re-emit the door with the correct hardware_set if you can read it.`;

    let passVerify;
    try {
      passVerify = await callResponses(
        COMPLETENESS_CHECK_SYSTEM,
        [
          pdfFileBlock,
          { type: 'input_text', text: verifyInstruction },
        ],
        32000,
        `verify-${verifyIter}`,
      );
    } catch (e) {
      onProgress?.({ kind: 'warn', text: `Verification ${verifyIter} failed: ${e.message}` });
      break;
    }
    const vRaw = passVerify.parsed || {};
    const vDoors = Array.isArray(vRaw.doors) ? vRaw.doors : [];
    const vSets = Array.isArray(vRaw.hardware_sets) ? vRaw.hardware_sets : [];
    if (passVerify.incompleteReason) onProgress?.({ kind: 'warn', text: `Verification ${verifyIter} incomplete: ${passVerify.incompleteReason}` });

    // Merge — doors: dedupe by mark, prefer non-null fields from verification
    let addedDoors = 0;
    const doorByMark = new Map(rawDoors.map(d => [d.mark, d]));
    vDoors.forEach(d => {
      if (!d.mark) return;
      if (!doorByMark.has(d.mark)) {
        doorByMark.set(d.mark, d);
        addedDoors++;
      } else {
        // Fill nulls from verify pass
        const existing = doorByMark.get(d.mark);
        Object.keys(d).forEach(k => {
          if (existing[k] == null && d[k] != null) existing[k] = d[k];
        });
        if (Array.isArray(d.remarks) && d.remarks.length && (!existing.remarks || !existing.remarks.length)) existing.remarks = d.remarks;
      }
    });
    rawDoors = [...doorByMark.values()];

    // Merge — hardware sets: dedupe by canonical key, merge items
    let addedSets = 0, addedItems = 0;
    const setByCanonical = new Map();
    rawSets.forEach(s => { if (s.id) setByCanonical.set(canonicalSetKey(s.id), s); });
    vSets.forEach(s => {
      if (!s.id) return;
      const key = canonicalSetKey(s.id);
      const existing = setByCanonical.get(key);
      if (!existing) {
        setByCanonical.set(key, s);
        addedSets++;
        addedItems += (s.items || []).length;
      } else {
        // Merge items by (desc + part + qty)
        const seen = new Set((existing.items || []).map(it => (it.desc||'').toLowerCase().replace(/\s+/g,' ').trim() + '|' + (it.part||'').toLowerCase().trim() + '|' + (it.qty ?? '')));
        (s.items || []).forEach(it => {
          const k = (it.desc||'').toLowerCase().replace(/\s+/g,' ').trim() + '|' + (it.part||'').toLowerCase().trim() + '|' + (it.qty ?? '');
          if (!seen.has(k)) {
            existing.items = [...(existing.items || []), it];
            seen.add(k);
            addedItems++;
          }
        });
        if (!existing.header_verbatim && s.header_verbatim) existing.header_verbatim = s.header_verbatim;
        if (!existing.name && s.name) existing.name = s.name;
      }
    });
    rawSets = [...setByCanonical.values()];
    rawTotalItems = rawSets.reduce((n, s) => n + (s.items?.length || 0), 0);

    onProgress?.({ kind: 'ok', text: `Verification ${verifyIter} · +${addedDoors} door(s), +${addedSets} set(s), +${addedItems} item(s) · totals: ${rawDoors.length}/${rawSets.length}/${rawTotalItems}` });

    if (addedDoors === 0 && addedSets === 0 && addedItems === 0) {
      onProgress?.({ kind: 'ok', text: `Verification converged after ${verifyIter} iteration(s).` });
      break;
    }
  }

  raw = { ...raw, doors: rawDoors, hardware_sets: rawSets };
  if (!raw.project_meta || Object.keys(raw.project_meta || {}).length === 0) raw.project_meta = discovery.project_meta || {};

  /* ===== PASS B — Senior estimator reasoning over assembled data ===== */
  onProgress?.({ kind: 'info', text: `Pass B · senior-estimator reasoning on ${rawDoors.length} doors + ${rawSets.length} sets + ${rawTotalItems} items…` });
  const reasoningInstruction = `The selected project scope is: ${scope || 'Supply & Installation'}

The door schedule and hardware sets below were transcribed from the source PDF. Run the senior-estimator analysis on this data and return the full JSON per your system instructions.

For each door, fill in opening_type, hardware_status, install_complexity, risk_level, special_conditions (CR/EL/DPS/AO/panic/etc. — pull from remarks), issues, recommendations, rfi_required, rfi_questions, confidence.
For each hardware set, fill in referenced_by_doors, status, missing_or_unclear_items, special_coordination, estimator_note.
Build project_risks (minimum 6 entries), rfi_log (minimum 12 entries, ideally 15-25), estimator_notes, and bid_recommendations as a senior estimator would.

GENERATE RFIs across as many of the following categories as the data supports — emit at least one RFI per category that has any matching openings:
  • Fire / smoke rating — UL listing across door + frame + hardware; smoke gasketing per egress path; temperature-rise cores at exit stair enclosures (IBC 716). Cite door marks with non-empty fire_rating.
  • Egress / exit devices — exit device type (rim/mortise/CVR/SVR), trim function, dogging vs non-dogging, alarm features. Trigger on panic/exit/CVR/SVR remarks.
  • Access control / electrified hardware — power supply, low-voltage cabling, EAC head-end, fire-alarm release, commissioning. Trigger on CR/EL/DPS/RX/EH/maglock/electric strike/AO remarks.
  • ADA / automatic operators — ANSI A156.10 vs A156.19, actuator location, 120 V provision, vestibule interlock.
  • Exterior / weather — threshold, weatherstrip, sweep, drip cap; HM vs storefront/aluminum split.
  • Pair / double-leaf openings — coordinators, astragals, flush bolts, active/inactive trim.
  • Keying / cylinders — master-key structure, keyway, SFIC vs LFIC, restricted keyway, construction core.
  • Acoustic / STC-rated — STC value, certified assembly, automatic door bottom, perimeter gasketing.
  • High-security rooms — server/electrical/vault; restricted keyway, key-management, ballistic.
  • Existing / remodel — re-use scope, frame prep, field-measure, keying continuity.
  • Glazing / vision lites — tempered/laminated/wired/fire-rated ceramic, UL listing for rated.
  • Schedule completeness — missing sizes, unreadable rows, ambiguous frame type.
  • Submittal / lead time — submittal due dates, approval turn-around, ROJ dates.
  • Scope split — Div 08 vs Div 26 (power) vs Div 27/28 (low-voltage / head-end).
  • Hardware set mismatches — doors referencing missing/voided sets, set opening-note vs schedule mismatches.

Every RFI must cite concrete door marks or set IDs from the data. Every risk must specify affected_openings.

DO NOT INVENT doors or hardware items not present in the data. Cite door marks and set IDs verbatim.

RAW DATA:
${JSON.stringify(raw)}`;

  let passB;
  try {
    passB = await callResponses(
      EXTRACTION_SYSTEM,
      [{ type: 'input_text', text: reasoningInstruction }],
      48000,
      'passB',
    );
  } catch (e) {
    onProgress?.({ kind: 'warn', text: `Pass B reasoning failed: ${e.message}. Will synthesize from raw data.` });
    passB = { parsed: {} };
  }
  const reasoning = passB.parsed || {};
  if (passB.incompleteReason) onProgress?.({ kind: 'warn', text: `Pass B incomplete: ${passB.incompleteReason}` });

  /* ===== Reconciliation: canonical key matching of door references to extracted sets ===== */
  const setByCanonicalKey = new Map();
  rawSets.forEach(s => { if (s.id) setByCanonicalKey.set(canonicalSetKey(s.id), s); });
  rawDoors.forEach(d => {
    if (!d.hardware_set) return;
    const key = canonicalSetKey(d.hardware_set);
    const matching = setByCanonicalKey.get(key);
    if (matching && matching.id !== d.hardware_set) {
      d.raw_hardware_set = d.hardware_set;
      d.hardware_set = matching.id;
    }
  });

  /* ===== Merge raw transcription with reasoning analysis ===== */
  const reasoningDoors = Array.isArray(reasoning.door_analysis) ? reasoning.door_analysis : [];
  const reasoningSets  = Array.isArray(reasoning.hardware_set_review) ? reasoning.hardware_set_review : [];
  const rDoorByMark = new Map(reasoningDoors.map(d => [d.mark, d]));
  const rSetById   = new Map(reasoningSets.map(s => [s.hardware_set, s]));

  const door_analysis = rawDoors.map(d => {
    const r = rDoorByMark.get(d.mark) || {};
    return {
      mark: d.mark,
      room_or_location: d.room_or_location ?? r.room_or_location ?? null,
      door_type: d.door_type ?? r.door_type ?? null,
      opening_type: r.opening_type || null,
      interior_or_exterior: d.interior_or_exterior ?? r.interior_or_exterior ?? null,
      size: d.size ?? r.size ?? { width: null, height: null, thickness: null },
      door_material: d.door_material ?? r.door_material ?? null,
      door_finish: d.door_finish ?? r.door_finish ?? null,
      glazing: d.glazing ?? r.glazing ?? null,
      frame_type: d.frame_type ?? r.frame_type ?? null,
      frame_material: d.frame_material ?? r.frame_material ?? null,
      frame_finish: d.frame_finish ?? r.frame_finish ?? null,
      fire_rating: d.fire_rating ?? r.fire_rating ?? null,
      hardware_set: d.hardware_set ?? r.hardware_set ?? null,
      raw_hardware_set: d.raw_hardware_set || null,
      remarks: d.remarks ?? r.remarks ?? [],
      hardware_status: r.hardware_status || 'review required',
      install_complexity: r.install_complexity || 'medium',
      risk_level: r.risk_level || 'low',
      special_conditions: r.special_conditions || [],
      issues: r.issues || [],
      recommendations: r.recommendations || [],
      rfi_required: !!r.rfi_required,
      rfi_questions: r.rfi_questions || [],
      confidence: r.confidence ?? 0.8,
    };
  });

  const hardware_set_review = rawSets.map(s => {
    const r = rSetById.get(s.id) || {};
    const refs = door_analysis.filter(d => d.hardware_set === s.id).map(d => d.mark);
    return {
      hardware_set: s.id,
      header_verbatim: s.header_verbatim || null,
      referenced_by_doors: r.referenced_by_doors?.length ? r.referenced_by_doors : refs,
      status: r.status || (s.items?.length ? 'complete' : 'incomplete'),
      items: (s.items || []).map((it, i) => ({
        item_no: it.item_no ?? (i + 1),
        qty: it.qty,
        unit: it.unit || '',
        desc: it.desc || '',
        part: it.part || '',
        mfr: it.mfr || '',
        finish: it.finish || '',
        notes: it.notes || '',
      })),
      missing_or_unclear_items: r.missing_or_unclear_items || (s.items?.length ? [] : ['no hardware items extracted']),
      special_coordination: r.special_coordination || [],
      estimator_note: r.estimator_note || s.header_verbatim || s.name || null,
      confidence: r.confidence ?? 0.8,
    };
  });

  // Flag missing sets (doors reference an id that has no set)
  const extractedSetIds = new Set(hardware_set_review.map(s => s.hardware_set));
  door_analysis.forEach(d => {
    if (d.hardware_set && !extractedSetIds.has(d.hardware_set)) {
      hardware_set_review.push({
        hardware_set: d.hardware_set,
        header_verbatim: null,
        referenced_by_doors: door_analysis.filter(x => x.hardware_set === d.hardware_set).map(x => x.mark),
        status: 'missing',
        items: [],
        missing_or_unclear_items: ['hardware set referenced by doors but not found in spec'],
        special_coordination: [],
        estimator_note: null,
        confidence: 0.4,
      });
      extractedSetIds.add(d.hardware_set);
    }
  });

  /* ===== Build door↔hardware mapping (one row per door per item) ===== */
  const setByDisplayId = new Map(hardware_set_review.map(s => [s.hardware_set, s]));
  const door_hardware_mapping = [];
  door_analysis.forEach(d => {
    if (!d.hardware_set) {
      door_hardware_mapping.push({ door_mark: d.mark, hardware_set: null, item_no: null, qty: null, description: '(no hardware set assigned)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'NO_HW_SET' });
      return;
    }
    const set = setByDisplayId.get(d.hardware_set);
    if (!set || !set.items || !set.items.length) {
      door_hardware_mapping.push({ door_mark: d.mark, hardware_set: d.hardware_set, item_no: null, qty: null, description: set ? '(hardware set has no extracted items)' : '(hardware set not found in spec)', catalog_number: null, manufacturer: null, finish: null, notes: null, status: 'FAILED_EXTRACTION_REVIEW_REQUIRED' });
      return;
    }
    set.items.forEach((it, i) => {
      door_hardware_mapping.push({
        door_mark: d.mark,
        hardware_set: d.hardware_set,
        item_no: it.item_no ?? (i + 1),
        qty: it.qty,
        description: it.desc || '',
        catalog_number: it.part || null,
        manufacturer: it.mfr || null,
        finish: it.finish || null,
        notes: it.notes || null,
        status: 'OK',
      });
    });
  });

  /* ===== Project summary ===== */
  const ps = reasoning.project_summary || {};
  const meta = raw.project_meta || {};
  const project_summary = {
    scope_type: scope,
    project_name: meta.project_name || ps.project_name || null,
    project_number: meta.project_number || ps.project_number || null,
    architect: meta.architect || ps.architect || null,
    address: meta.address || ps.address || null,
    drawing: meta.drawing || ps.drawing || null,
    date: meta.date || ps.date || null,
    total_openings_found: door_analysis.length,
    total_hardware_sets_referenced: new Set(door_analysis.map(d => d.hardware_set).filter(Boolean)).size,
    hardware_sets_missing_or_unclear: hardware_set_review.filter(s => s.status !== 'complete').length,
    high_risk_openings: door_analysis.filter(d => d.risk_level === 'high').length,
    medium_risk_openings: door_analysis.filter(d => d.risk_level === 'medium').length,
    low_risk_openings: door_analysis.filter(d => d.risk_level === 'low').length,
    complex_installations: door_analysis.filter(d => d.install_complexity === 'high').length,
    access_control_openings: door_analysis.filter(d => (d.special_conditions || []).some(c => /CR|EL|DPS|card|access|electrified/i.test(c))).length,
    exterior_openings: door_analysis.filter(d => d.interior_or_exterior === 'Exterior').length,
    fire_rated_openings: door_analysis.filter(d => d.fire_rating && d.fire_rating !== '-' && !/^non/i.test(String(d.fire_rating))).length,
    overall_bid_risk: ps.overall_bid_risk || 'Medium',
    estimator_summary: ps.estimator_summary || `Native PDF pipeline (gpt-5.5) read ${(discovery.pages || []).length} page(s) and extracted ${door_analysis.length} opening(s) and ${hardware_set_review.length} hardware set(s) with ${hardware_set_review.reduce((n,s)=>n+(s.items?.length||0),0)} line items. Verify against source PDF before bidding.`,
  };

  /* ===== Merge LLM risks/RFIs with heuristic synthesis for comprehensiveness ===== */
  const synth = synthesizeRisksAndRFIs(door_analysis, hardware_set_review, scope);
  const merged = mergeRisksAndRFIs(reasoning, synth);

  const totalItems = hardware_set_review.reduce((n, s) => n + (s.items?.length || 0), 0);
  onProgress?.({ kind: 'ok', text: `Native pipeline complete · ${door_analysis.length} doors · ${hardware_set_review.length} sets · ${totalItems} items · ${merged.risks.length} risks · ${merged.rfis.length} RFIs` });

  return {
    analysis: {
      project_summary,
      door_analysis,
      hardware_set_review,
      door_hardware_mapping,
      project_risks: merged.risks,
      rfi_log: merged.rfis,
      estimator_notes: merged.notes,
      bid_recommendations: merged.recs,
    },
    qa: {
      pdf_type: 'NATIVE_PIPELINE',
      pipeline: 'native-multi-pass',
      model: REQUIRED_MODEL,
      discovery,
      raw_transcription: raw,
      verify_iterations: verifyIter,
      reasoning_succeeded: !!reasoning && Object.keys(reasoning).length > 0,
      extraction_complete: true,
      extraction_failures: [],
    },
  };
}

/* Old single-shot version kept under a different name for the image pipeline fallback path */
async function extractFromPdfDirectLegacy({ apiKey, scope, file, onProgress }) {
  if (!apiKey) throw new Error('OpenAI API key required. Open Settings to add one.');
  onProgress?.({ kind: 'info', text: `Reading ${file.name} (${(file.size/1024).toFixed(1)} KB)…` });
  const arrayBuffer = await file.arrayBuffer();
  const base64 = arrayBufferToBase64(arrayBuffer);
  const dataUrl = `data:application/pdf;base64,${base64}`;

  const callResponses = async (system, userBlocks, maxTokens = 32000) => {
    const body = {
      model: REQUIRED_MODEL,
      input: [
        { role: 'system', content: system },
        { role: 'user', content: userBlocks },
      ],
      text: { format: { type: 'json_object' } },
      max_output_tokens: maxTokens,
    };
    const res = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
      body: JSON.stringify(body),
    });
    let data;
    try { data = await res.json(); } catch { throw new Error('Network error contacting OpenAI'); }
    if (!res.ok) throw new Error(data?.error?.message || ('OpenAI error ' + res.status));
    let text = data.output_text || '';
    if (!text && Array.isArray(data.output)) {
      for (const item of data.output) {
        if (item?.content) {
          for (const c of item.content) {
            if (typeof c?.text === 'string') text += c.text;
          }
        }
      }
    }
    if (!text) text = '{}';
    const incompleteReason = data.incomplete_details?.reason;
    try { return { parsed: JSON.parse(text), status: data.status, incompleteReason }; }
    catch { throw new Error('Model returned invalid JSON' + (incompleteReason === 'max_output_tokens' ? ' (output truncated — increase max_output_tokens)' : '')); }
  };

  // ===== PASS A — Pure transcription (PDF → raw doors + hardware) =====
  onProgress?.({ kind: 'info', text: `Pass A · uploading PDF to ${REQUIRED_MODEL} for transcription…` });
  const passA = await callResponses(
    EXTRACTION_ONLY_SYSTEM,
    [
      { type: 'input_file', filename: file.name, file_data: dataUrl },
      { type: 'input_text', text: `Transcribe every door schedule row and every hardware set with all items. Return JSON per your schema.` },
    ],
    32000,
  );
  const raw = passA.parsed;
  const rawDoors = Array.isArray(raw.doors) ? raw.doors : [];
  const rawSets = Array.isArray(raw.hardware_sets) ? raw.hardware_sets : [];
  const rawTotalItems = rawSets.reduce((n, s) => n + (s.items?.length || 0), 0);
  onProgress?.({ kind: 'ok', text: `Pass A done: ${rawDoors.length} door(s), ${rawSets.length} HW set(s), ${rawTotalItems} item(s)${passA.status ? ' · status=' + passA.status : ''}` });
  if (passA.incompleteReason) onProgress?.({ kind: 'warn', text: `Pass A incomplete: ${passA.incompleteReason}` });

  // ===== PASS B — Reasoning (raw data → risks / RFIs / recommendations / notes) =====
  onProgress?.({ kind: 'info', text: `Pass B · running senior-estimator reasoning on extracted data…` });
  const reasoningInstruction = `The selected project scope is: ${scope || 'Supply & Installation'}

The door schedule and hardware sets below were transcribed from the source PDF. Run the senior-estimator analysis on this data and return the full JSON per your system instructions.

For each door, fill in opening_type, hardware_status, install_complexity, risk_level, special_conditions (CR/EL/DPS/AO/panic/etc.), issues, recommendations, rfi_required, rfi_questions, confidence.
For each hardware set, fill in referenced_by_doors, status, missing_or_unclear_items, special_coordination, estimator_note.
Build project_risks (minimum 3 unless trivial), rfi_log (minimum 3 unless trivial), estimator_notes, and bid_recommendations as a senior estimator would.

DO NOT INVENT doors or hardware items not present in the data. Cite door marks and set IDs verbatim.

RAW DATA:
${JSON.stringify(raw)}`;

  const passB = await callResponses(
    EXTRACTION_SYSTEM,
    [{ type: 'input_text', text: reasoningInstruction }],
    32000,
  );
  const reasoning = passB.parsed;
  if (passB.incompleteReason) onProgress?.({ kind: 'warn', text: `Pass B incomplete: ${passB.incompleteReason}` });

  // ===== Merge: raw transcription is the source of truth for doors+items;
  //              reasoning adds risk/complexity/RFIs/recommendations =====
  const reasoningDoors = Array.isArray(reasoning.door_analysis) ? reasoning.door_analysis : [];
  const reasoningSets  = Array.isArray(reasoning.hardware_set_review) ? reasoning.hardware_set_review : [];
  const rDoorByMark = new Map(reasoningDoors.map(d => [d.mark, d]));
  const rSetById   = new Map(reasoningSets.map(s => [s.hardware_set, s]));

  const door_analysis = rawDoors.map(d => {
    const r = rDoorByMark.get(d.mark) || {};
    return {
      mark: d.mark,
      room_or_location: d.room_or_location ?? r.room_or_location ?? null,
      door_type: d.door_type ?? r.door_type ?? null,
      opening_type: r.opening_type || null,
      interior_or_exterior: d.interior_or_exterior ?? r.interior_or_exterior ?? null,
      size: d.size ?? r.size ?? { width: null, height: null, thickness: null },
      door_material: d.door_material ?? r.door_material ?? null,
      door_finish: d.door_finish ?? r.door_finish ?? null,
      glazing: d.glazing ?? r.glazing ?? null,
      frame_type: d.frame_type ?? r.frame_type ?? null,
      frame_material: d.frame_material ?? r.frame_material ?? null,
      frame_finish: d.frame_finish ?? r.frame_finish ?? null,
      fire_rating: d.fire_rating ?? r.fire_rating ?? null,
      hardware_set: d.hardware_set ?? r.hardware_set ?? null,
      remarks: d.remarks ?? r.remarks ?? [],
      hardware_status: r.hardware_status || 'review required',
      install_complexity: r.install_complexity || 'medium',
      risk_level: r.risk_level || 'low',
      special_conditions: r.special_conditions || [],
      issues: r.issues || [],
      recommendations: r.recommendations || [],
      rfi_required: !!r.rfi_required,
      rfi_questions: r.rfi_questions || [],
      confidence: r.confidence ?? 0.8,
    };
  });

  const hardware_set_review = rawSets.map(s => {
    const r = rSetById.get(s.id) || {};
    const refs = door_analysis.filter(d => d.hardware_set === s.id).map(d => d.mark);
    return {
      hardware_set: s.id,
      referenced_by_doors: r.referenced_by_doors?.length ? r.referenced_by_doors : refs,
      status: r.status || (s.items?.length ? 'complete' : 'incomplete'),
      items: s.items || [],
      missing_or_unclear_items: r.missing_or_unclear_items || (s.items?.length ? [] : ['no hardware items extracted']),
      special_coordination: r.special_coordination || [],
      estimator_note: r.estimator_note || s.header_verbatim || s.name || null,
      confidence: r.confidence ?? 0.8,
    };
  });

  // Project summary — prefer transcribed metadata, fall back to reasoning's project_summary
  const ps = reasoning.project_summary || {};
  const meta = raw.project_meta || {};
  const project_summary = {
    scope_type: scope,
    project_name: meta.project_name || ps.project_name || null,
    project_number: meta.project_number || ps.project_number || null,
    architect: meta.architect || ps.architect || null,
    address: meta.address || ps.address || null,
    drawing: meta.drawing || ps.drawing || null,
    date: meta.date || ps.date || null,
    total_openings_found: door_analysis.length,
    total_hardware_sets_referenced: new Set(door_analysis.map(d => d.hardware_set).filter(Boolean)).size,
    hardware_sets_missing_or_unclear: hardware_set_review.filter(s => s.status !== 'complete').length,
    high_risk_openings: ps.high_risk_openings ?? door_analysis.filter(d => d.risk_level === 'high').length,
    medium_risk_openings: ps.medium_risk_openings ?? door_analysis.filter(d => d.risk_level === 'medium').length,
    low_risk_openings: ps.low_risk_openings ?? door_analysis.filter(d => d.risk_level === 'low').length,
    complex_installations: ps.complex_installations ?? door_analysis.filter(d => d.install_complexity === 'high').length,
    access_control_openings: ps.access_control_openings ?? 0,
    exterior_openings: ps.exterior_openings ?? door_analysis.filter(d => d.interior_or_exterior === 'Exterior').length,
    fire_rated_openings: ps.fire_rated_openings ?? door_analysis.filter(d => d.fire_rating && d.fire_rating !== '-').length,
    overall_bid_risk: ps.overall_bid_risk || 'Medium',
    estimator_summary: ps.estimator_summary || '',
  };

  const synth = synthesizeRisksAndRFIs(door_analysis, hardware_set_review, scope);
  const merged = mergeRisksAndRFIs(reasoning, synth);
  const parsed = {
    project_summary,
    door_analysis,
    hardware_set_review,
    project_risks: merged.risks,
    rfi_log: merged.rfis,
    estimator_notes: merged.notes,
    bid_recommendations: merged.recs,
  };

  const totalItems = (parsed.hardware_set_review || []).reduce((n, s) => n + (s.items?.length || 0), 0);
  onProgress?.({ kind: 'ok', text: `Pass B done · ${parsed.door_analysis.length} doors · ${parsed.hardware_set_review.length} sets · ${totalItems} items · ${parsed.project_risks.length} risks · ${parsed.rfi_log.length} RFIs` });
  return parsed;
}

/* Map the new analysis schema → legacy `doors` and `hardwareSets` used by the proposal/export flow */
function analysisToLegacy(analysis) {
  const doors = (analysis.door_analysis || []).map(d => ({
    number: d.mark,
    fromTo: d.room_or_location || '',
    type: d.door_type || '',
    width: d.size?.width || null,
    height: d.size?.height || null,
    thk: d.size?.thickness || null,
    faceMatl: d.door_material || '',
    coreMatl: '',
    finish: d.door_finish || '',
    frameMatl: d.frame_material || '',
    frameType: d.frame_type || '',
    frameFinish: d.frame_finish || '',
    label: d.fire_rating || '-',
    hwSet: d.hardware_set || '',
    glazing: d.glazing || '-',
    notes: (d.remarks || []).join('; '),
    confidence: d.confidence ?? 1,
  }));
  const hardwareSets = (analysis.hardware_set_review || []).map(s => ({
    id: s.hardware_set,
    name: s.estimator_note || s.hardware_set,
    description: (s.special_coordination || []).join('; '),
    items: Array.isArray(s.items) ? s.items.map(it => ({
      qty: typeof it.qty === 'number' ? it.qty : (Number(it.qty) || 1),
      desc: it.desc || '',
      part: it.part || '',
      mfr: it.mfr || '',
      finish: it.finish || '',
      unitPrice: it.unitPrice ?? null,
    })) : [],
  }));
  return { doors, hardwareSets };
}

/* ---------- UI primitives ---------- */
const Button = ({ kind = 'default', size = '', children, ...rest }) => {
  const cls = ['btn', kind === 'primary' && 'btn-primary', kind === 'ghost' && 'btn-ghost', kind === 'danger' && 'btn-danger', size === 'sm' && 'btn-sm', size === 'lg' && 'btn-lg'].filter(Boolean).join(' ');
  return <button className={cls} {...rest}>{children}</button>;
};
const IconButton = ({ children, ...rest }) => <button className="icon-btn" {...rest}>{children}</button>;
const Badge = ({ tone = '', mono, children, ...rest }) => <span className={'badge' + (tone ? ' badge-' + tone : '') + (mono ? ' badge-mono' : '')} {...rest}>{children}</span>;
const Modal = ({ title, children, footer, onClose, width = 520 }) => (
  <div className="modal-backdrop" onMouseDown={onClose}>
    <div className="modal" style={{ width, maxWidth: '92vw' }} onMouseDown={e => e.stopPropagation()}>
      <div className="modal-header">
        <div className="modal-title">{title}</div>
        <IconButton onClick={onClose}><Icon name="x"/></IconButton>
      </div>
      <div className="modal-body">{children}</div>
      {footer && <div className="modal-footer">{footer}</div>}
    </div>
  </div>
);
const EmptyState = ({ icon, title, body, action }) => (
  <div style={{ textAlign: 'center', padding: '64px 24px', color: 'var(--fg-muted)' }}>
    <div style={{ width: 72, height: 72, borderRadius: 18, background: 'var(--bg-sunken)', color: 'var(--fg-faint)', display: 'grid', placeItems: 'center', margin: '0 auto 16px' }}>
      <Icon name={icon} size={32}/>
    </div>
    <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg)', marginBottom: 4 }}>{title}</div>
    <div style={{ maxWidth: 420, margin: '0 auto 20px' }}>{body}</div>
    {action}
  </div>
);

/* ---------- Estimator-specific helpers ---------- */
const SCOPE_OPTIONS = ['Supply Only', 'Installation Only', 'Supply & Installation'];

const RiskPill = ({ level }) => {
  const v = String(level || '').toLowerCase();
  const tone = v === 'high' ? 'red' : v === 'medium' ? 'amber' : v === 'low' ? 'green' : '';
  return <Badge tone={tone}>{v ? v[0].toUpperCase() + v.slice(1) : '—'}</Badge>;
};
const StatusPill = ({ status }) => {
  const v = String(status || '').toLowerCase();
  const tone = v === 'complete' ? 'green' : (v === 'incomplete' || v === 'unclear' || v.includes('review')) ? 'amber' : v === 'missing' ? 'red' : '';
  return <Badge tone={tone}>{v ? v[0].toUpperCase() + v.slice(1) : '—'}</Badge>;
};
const SeverityDot = ({ severity }) => {
  const v = String(severity || '').toLowerCase();
  const color = v === 'high' ? 'var(--accent-red)' : v === 'medium' ? 'var(--accent-amber)' : 'var(--accent-green)';
  return <span style={{display:'inline-block', width: 8, height: 8, borderRadius: 999, background: color, marginRight: 8}}/>;
};
const ChipList = ({ items, tone, empty = '—' }) => {
  if (!items || !items.length) return <span className="muted" style={{fontSize: 12}}>{empty}</span>;
  return (
    <div style={{display:'flex', flexWrap:'wrap', gap: 4}}>
      {items.map((c, i) => <Badge key={i} tone={tone}>{c}</Badge>)}
    </div>
  );
};

/* ---------- Sidebar / Topbar ---------- */
const Sidebar = ({ route, setRoute, companyName, hasProject, projectName }) => {
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: 'home' },
    { id: 'upload', label: 'New Analysis', icon: 'upload' },
  ];
  const projectItems = [
    { id: 'summary', label: 'Project Summary', icon: 'briefcase' },
    { id: 'doors', label: 'Door Analysis', icon: 'door' },
    { id: 'mapping', label: 'Hardware Review', icon: 'link' },
    { id: 'risks', label: 'Risks & RFIs', icon: 'alert' },
    { id: 'bidrecs', label: 'Bid Recommendations', icon: 'file-check' },
    { id: 'qa', label: 'Extraction QA', icon: 'shield' },
    { id: 'proposal', label: 'Proposal', icon: 'file-text' },
    { id: 'export', label: 'Export & Send', icon: 'send' },
  ];
  const otherItems = [
    { id: 'catalog', label: 'Hardware Catalog', icon: 'library' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ];

  const NavItem = ({ it, disabled }) => (
    <button className={'nav-item' + (route === it.id ? ' active' : '')}
            disabled={disabled} style={disabled ? { opacity: 0.4, cursor: 'not-allowed' } : null}
            onClick={() => !disabled && setRoute(it.id)}>
      <Icon name={it.icon}/><span>{it.label}</span>
    </button>
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark"><Icon name="door" size={18}/></div>
        <div>
          <div className="brand-name">FastBid24</div>
          <div className="brand-tag">Door &amp; Hardware</div>
        </div>
      </div>
      <div className="nav-section">{items.map(it => <NavItem key={it.id} it={it}/>)}</div>
      <div className="nav-section">
        <div className="nav-section-label">Current Project</div>
        <div style={{padding:'4px 10px 8px', fontSize:12, color:'rgba(255,255,255,0.55)'}}>
          {hasProject ? (projectName || 'Untitled') : <em style={{opacity:.6}}>None loaded</em>}
        </div>
        {projectItems.map(it => <NavItem key={it.id} it={it} disabled={!hasProject}/>)}
      </div>
      <div className="nav-section">
        <div className="nav-section-label">Workspace</div>
        {otherItems.map(it => <NavItem key={it.id} it={it}/>)}
      </div>
      <div className="sidebar-footer">
        <div className="user-chip">
          <div className="user-avatar">{(companyName || 'FB').slice(0,2).toUpperCase()}</div>
          <div className="user-meta">
            <div className="user-name">{companyName || 'FastBid24'}</div>
            <div className="user-role">Estimator</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

const Topbar = ({ crumbs = [], onToggleTheme, theme, onOpenSettings, hasApiKey }) => (
  <div className="topbar">
    <div className="crumb">
      {crumbs.map((c, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="crumb-sep"><Icon name="chevron-right" size={12}/></span>}
          {i === crumbs.length - 1 ? <strong>{c}</strong> : <span>{c}</span>}
        </Fragment>
      ))}
    </div>
    <div className="topbar-actions">
      {!hasApiKey && (
        <Button kind="ghost" size="sm" onClick={onOpenSettings}>
          <Icon name="alert" size={14} style={{color: 'var(--accent-amber)'}}/> Connect OpenAI
        </Button>
      )}
      <IconButton onClick={onOpenSettings} title="Settings"><Icon name="settings"/></IconButton>
      <IconButton onClick={onToggleTheme} title="Toggle theme"><Icon name={theme === 'dark' ? 'sun' : 'moon'}/></IconButton>
    </div>
  </div>
);

/* ---------- Settings Modal ---------- */
const SettingsModal = ({ tweaks, setTweaks, onClose }) => {
  const set = (k, v) => setTweaks(t => ({ ...t, [k]: v }));
  return (
    <Modal title="Settings" onClose={onClose} width={560}
           footer={<Button kind="primary" onClick={onClose}>Done</Button>}>
      <div style={{display:'flex', flexDirection:'column', gap: 18}}>
        <div>
          <div style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.08, color: 'var(--fg-muted)', marginBottom: 8}}>OpenAI</div>
          <div style={{padding: 12, background: 'var(--accent-amber-light)', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, marginBottom: 12, display: 'flex', gap: 8}}>
            <Icon name="shield" size={14} style={{color:'#92400e', flexShrink: 0, marginTop: 2}}/>
            <div style={{color:'#92400e'}}>
              <strong>Stored locally.</strong> Your API key is kept in this browser's localStorage and sent directly from your browser to api.openai.com. Do not use a shared device.
            </div>
          </div>
          <label style={{display:'block', fontSize: 12, fontWeight: 600, color:'var(--fg-muted)', marginBottom: 4}}>API Key</label>
          <input className="input" type="password" placeholder="sk-…"
                 value={tweaks.apiKey || ''} onChange={e => set('apiKey', e.target.value)}/>
          <label style={{display:'block', fontSize: 12, fontWeight: 600, color:'var(--fg-muted)', marginTop: 12, marginBottom: 4}}>Model</label>
          <div className="input" style={{display:'flex', alignItems:'center', gap: 8, opacity: 0.85}}>
            <span className="mono" style={{fontWeight: 600}}>{REQUIRED_MODEL}</span>
            <Badge tone="blue">mandated</Badge>
          </div>
          <div style={{fontSize: 11, color: 'var(--fg-muted)', marginTop: 6}}>This analyzer is locked to {REQUIRED_MODEL}. No fallback to other models.</div>
        </div>

        <div>
          <div style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.08, color: 'var(--fg-muted)', marginBottom: 8}}>Company</div>
          <label style={{display:'block', fontSize: 12, fontWeight: 600, color:'var(--fg-muted)', marginBottom: 4}}>Name on proposals</label>
          <input className="input" value={tweaks.companyName} onChange={e => set('companyName', e.target.value)}/>
          <label style={{display:'block', fontSize: 12, fontWeight: 600, color:'var(--fg-muted)', marginTop: 12, marginBottom: 4}}>Default markup %</label>
          <input className="input" type="number" min="0" max="100" value={tweaks.markup} onChange={e => set('markup', Number(e.target.value))}/>
        </div>
      </div>
    </Modal>
  );
};

/* ---------- Tweaks Panel (in-page) ---------- */
const TweaksPanel = ({ tweaks, setTweaks, onClose }) => {
  const setKey = (k, v) => {
    setTweaks(t => ({ ...t, [k]: v }));
    try { window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [k]: v } }, '*'); } catch {}
  };
  const palettes = [
    ['Blueprint Blue', '#2f68f5', '#1e4fdb', '#5a8fff', '#153eb0'],
    ['Steel', '#64748b', '#475569', '#94a3b8', '#334155'],
    ['Safety Amber', '#f59e0b', '#d97706', '#fbbf24', '#b45309'],
    ['Forest', '#10b981', '#059669', '#34d399', '#047857'],
    ['Crimson', '#ef4444', '#dc2626', '#f87171', '#b91c1c'],
  ];
  return (
    <div className="tweaks-panel">
      <div className="tweaks-header">
        <div className="row"><Icon name="sliders"/><strong>Tweaks</strong></div>
        <IconButton onClick={onClose}><Icon name="x"/></IconButton>
      </div>
      <div className="tweaks-body">
        <div className="tweak-row">
          <label className="tweak-label">Theme</label>
          <div className="row">
            <Button size="sm" kind={tweaks.theme === 'light' ? 'primary' : 'default'} onClick={() => setKey('theme', 'light')}><Icon name="sun" size={12}/> Light</Button>
            <Button size="sm" kind={tweaks.theme === 'dark' ? 'primary' : 'default'} onClick={() => setKey('theme', 'dark')}><Icon name="moon" size={12}/> Dark</Button>
          </div>
        </div>
        <div className="tweak-row">
          <label className="tweak-label">Brand color</label>
          <div className="swatch-row">
            {palettes.map(p => (
              <div key={p[0]}
                   className={'swatch' + (tweaks.brandName === p[0] ? ' selected' : '')}
                   style={{background: p[1]}} title={p[0]}
                   onClick={() => { setKey('brandName', p[0]); setKey('brand500', p[1]); setKey('brand600', p[2]); setKey('brand400', p[3]); setKey('brand700', p[4]); }}/>
            ))}
          </div>
        </div>
        <div className="tweak-row">
          <label className="tweak-label">Company name</label>
          <input className="input input-sm" value={tweaks.companyName} onChange={e => setKey('companyName', e.target.value)}/>
        </div>
        <div className="tweak-row">
          <label className="tweak-label">Markup ({tweaks.markup}%)</label>
          <input type="range" min="0" max="50" step="1" value={tweaks.markup} onChange={e => setKey('markup', Number(e.target.value))}/>
        </div>
        <div className="tweak-row">
          <label className="tweak-label">Proposal template</label>
          <div className="row">
            {['Classic','Modern','Minimal'].map(t => (
              <Button key={t} size="sm" kind={tweaks.template === t ? 'primary' : 'default'} onClick={() => setKey('template', t)}>{t}</Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* expose part 1 - everything is in scope as we're one file */
window.__fb_part1 = true;


/* ====================================================================
   Screens
   ==================================================================== */

/* ---------- Dashboard ---------- */
const Dashboard = ({ proposals, setRoute, onOpen, onDelete, onExportExcel, onExportComsenseCsv }) => {
  const totalValue = proposals.reduce((s, p) => s + (p.total || 0), 0);
  const active = proposals.filter(p => ['Draft','Sent','In Review'].includes(p.status)).length;
  const won = proposals.filter(p => p.status === 'Accepted').length;
  const finished = proposals.filter(p => ['Accepted','Lost'].includes(p.status)).length;
  const winRate = finished ? Math.round((won / finished) * 100) : 0;

  const statusBadge = (s) => {
    const map = { 'Accepted': 'green', 'Sent': 'blue', 'In Review': 'amber', 'Draft': '', 'Lost': 'red' };
    return <Badge tone={map[s] || ''}>{s}</Badge>;
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Door Analyses</h1>
          <div className="page-subtitle">Senior-estimator reviews of Division 8 packages — doors, frames, hardware, risks, and RFIs.</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={() => setRoute('upload')}><Icon name="plus"/> New Analysis</Button>
        </div>
      </div>

      {proposals.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="inbox"
            title="No analyses yet"
            body="Upload an architectural PDF and FastBid24 will deliver a senior-estimator review of the door schedule, hardware sets, risks, and RFIs."
            action={<Button kind="primary" onClick={() => setRoute('upload')}><Icon name="upload"/> Upload your first PDF</Button>}
          />
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-label">Total analyses</div><div className="stat-value">{proposals.length}</div></div>
            <div className="stat-card"><div className="stat-label">Active</div><div className="stat-value">{active}</div></div>
            <div className="stat-card"><div className="stat-label">Total openings analyzed</div><div className="stat-value">{proposals.reduce((s,p)=>s+(p.doors||0),0)}</div></div>
            <div className="stat-card"><div className="stat-label">High-risk projects</div><div className="stat-value" style={{color: 'var(--accent-red)'}}>{proposals.filter(p => String(p.risk||'').toLowerCase() === 'high').length}</div></div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">All proposals</div>
            </div>
            <div style={{overflow:'auto'}}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Analysis</th><th>Project</th><th>Architect</th><th>Scope</th><th>Openings</th>
                    <th>PDF</th><th>Risk</th><th>Status</th><th>Date</th>
                    <th style={{width:100}}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {proposals.map(p => (
                    <tr key={p.id} style={{cursor:'pointer'}} onClick={() => onOpen(p)}>
                      <td className="mono">{p.id}</td>
                      <td><strong>{p.project}</strong>{p.address && <div className="mono-small">{p.address}</div>}</td>
                      <td>{p.client || '—'}</td>
                      <td>{p.scope ? <Badge tone="blue">{p.scope}</Badge> : <span className="muted">—</span>}</td>
                      <td>{p.doors || 0}</td>
                      <td>{p.pdfType === 'IMAGE_BASED_PDF' ? <Badge tone="amber">Image</Badge> : p.pdfType === 'PDF_DIRECT' ? <Badge tone="blue">Direct</Badge> : <Badge>Text</Badge>}</td>
                      <td>{p.risk && p.risk !== '—' ? <RiskPill level={p.risk}/> : <span className="muted">—</span>}</td>
                      <td>{p.extractionStatus === 'REVIEW_REQUIRED' ? <Badge tone="amber">Review</Badge> : statusBadge(p.status)}</td>
                      <td className="muted">{p.date}</td>
                      <td onClick={(e) => e.stopPropagation()} style={{whiteSpace: 'nowrap'}}>
                        <IconButton onClick={() => onExportExcel?.(p)} title="Export Excel"><Icon name="download" size={14}/></IconButton>
                        <IconButton onClick={() => onExportComsenseCsv?.(p)} title="Export Comsense-style CSV"><Icon name="file-text" size={14}/></IconButton>
                        <IconButton onClick={() => { if (confirm('Delete this analysis from history?')) onDelete(p.id); }} title="Delete"><Icon name="trash" size={14}/></IconButton>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

/* ---------- Upload ---------- */
const UploadScreen = ({ onStartParse, hasApiKey, onOpenSettings, tweaks, setTweaks }) => {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const inputRef = useRef();
  const pickFile = (f) => f && setFile(f);
  const scope = tweaks.scope || 'Supply & Installation';
  const setScope = (s) => setTweaks(t => ({ ...t, scope: s }));

  return (
    <div className="fade-in" style={{maxWidth: 860, margin: '0 auto'}}>
      <div className="page-header">
        <div>
          <h1 className="page-title">New Analysis</h1>
          <div className="page-subtitle">Upload an architectural PDF — we'll deliver a senior-estimator review of doors, hardware, risks, and RFIs.</div>
        </div>
      </div>

      {!hasApiKey && (
        <div className="card" style={{marginBottom: 16, borderColor: 'var(--accent-amber)'}}>
          <div className="card-body" style={{display:'flex', gap:12, alignItems:'center'}}>
            <div style={{width:40, height:40, borderRadius:8, background:'var(--accent-amber-light)', color:'#92400e', display:'grid', placeItems:'center'}}>
              <Icon name="key"/>
            </div>
            <div style={{flex:1}}>
              <div style={{fontWeight:600}}>Connect OpenAI to enable analysis</div>
              <div className="muted" style={{fontSize:13}}>Add your API key in Settings. Analysis runs against your configured model.</div>
            </div>
            <Button kind="primary" onClick={onOpenSettings}><Icon name="settings"/> Open Settings</Button>
          </div>
        </div>
      )}

      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header"><div className="card-title">1 · Project scope</div></div>
        <div className="card-body">
          <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap: 12}}>
            {SCOPE_OPTIONS.map(opt => {
              const selected = scope === opt;
              const desc = {
                'Supply Only': 'Materials only. Focus: HW completeness, finishes, fire-rated products, long-lead items.',
                'Installation Only': 'Labor only. Focus: install difficulty, exterior coord, access control, sequencing.',
                'Supply & Installation': 'Both. Full material + labor analysis including all coordination items.',
              }[opt];
              return (
                <button key={opt} type="button" onClick={() => setScope(opt)}
                        style={{
                          textAlign: 'left', padding: 16, borderRadius: 10, cursor: 'pointer',
                          border: '2px solid ' + (selected ? 'var(--brand-600)' : 'var(--border)'),
                          background: selected ? 'var(--brand-50)' : 'var(--bg-raised)',
                          color: 'var(--fg)', display:'flex', flexDirection:'column', gap: 6,
                        }}>
                  <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
                    <strong style={{fontSize: 13}}>{opt}</strong>
                    <span style={{width: 18, height: 18, borderRadius: 999, border: '2px solid ' + (selected ? 'var(--brand-600)' : 'var(--border)'), display:'grid', placeItems:'center'}}>
                      {selected && <span style={{width: 8, height: 8, borderRadius:999, background:'var(--brand-600)'}}/>}
                    </span>
                  </div>
                  <div className="muted" style={{fontSize: 12, lineHeight: 1.5}}>{desc}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header"><div className="card-title">2 · Upload PDF</div></div>
        <div className="card-body">
          <div className={'dropzone' + (dragging ? ' dragging' : '')}
               onDragOver={e => { e.preventDefault(); setDragging(true); }}
               onDragLeave={() => setDragging(false)}
               onDrop={e => { e.preventDefault(); setDragging(false); pickFile(e.dataTransfer.files[0]); }}
               onClick={() => inputRef.current.click()}>
            <div className="dropzone-icon"><Icon name="upload" size={28}/></div>
            <div className="dropzone-title">{file ? file.name : 'Drop architectural PDF here'}</div>
            <div className="dropzone-sub">
              {file ? `${(file.size/1024).toFixed(0)} KB · ready to analyze` : 'Drawings (A-series) and spec books (CSI Div 08 71 00). Up to 200 MB.'}
            </div>
            <input ref={inputRef} type="file" accept="application/pdf" hidden onChange={e => pickFile(e.target.files[0])}/>
          </div>
          <div className="row" style={{marginTop: 20, justifyContent:'space-between', alignItems:'center'}}>
            <div className="muted" style={{fontSize:12, display:'flex', alignItems:'center', gap:6}}>
              <Icon name="info" size={14}/> Scope: <strong style={{color:'var(--fg)'}}>{scope}</strong> · PDF is uploaded directly to OpenAI for senior-estimator analysis (no browser-side text extraction).
            </div>
            <Button kind="primary" size="lg" disabled={!file || !hasApiKey}
                    style={!file || !hasApiKey ? {opacity:.5, cursor:'not-allowed'} : null}
                    onClick={() => onStartParse(file)}>
              <Icon name="sparkles"/> Analyze as senior estimator
            </Button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><div className="card-title">What you'll get back</div></div>
        <div className="card-body" style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap: 16}}>
          {[
            { icon:'briefcase', t:'Project summary', d:'Scope, totals, risk distribution, estimator overview.' },
            { icon:'door', t:'Door-by-door analysis', d:'Risk, install complexity, special conditions, issues, RFI flags.' },
            { icon:'package', t:'Hardware review', d:'Each HW set: complete / incomplete / missing, coordination notes.' },
            { icon:'alert', t:'Risks + RFIs + bid notes', d:'Prioritized risks, RFI log, estimator notes, scope-specific recommendations.' },
          ].map(x => (
            <div key={x.t} style={{padding:12}}>
              <div style={{width:36, height:36, borderRadius:8, background:'var(--brand-50)', color:'var(--brand-600)', display:'grid', placeItems:'center', marginBottom:10}}>
                <Icon name={x.icon} size={18}/>
              </div>
              <div style={{fontWeight:600, marginBottom:4, fontSize: 13}}>{x.t}</div>
              <div className="muted" style={{fontSize:12, lineHeight: 1.5}}>{x.d}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ---------- Parsing ---------- */
const ParsingScreen = ({ file, tweaks, onDone, onError, onCancel }) => {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const startedRef = useRef(false);

  const steps = [
    { label: 'Uploading PDF', detail: `${file?.name || ''} (${file ? (file.size/1024).toFixed(0) + ' KB' : ''})` },
    { label: 'Call 1 · Door schedule extraction', detail: `gpt-5.5 reads PDF · prompts/door_schedule_extraction.md` },
    { label: 'Call 2 · Hardware set extraction', detail: `gpt-5.5 reads PDF · prompts/hardware_set_extraction.md` },
    { label: 'Mapping + rollup', detail: 'Code · door↔hardware mapping · summary metrics' },
    { label: 'Call 3 · RFI review (optional)', detail: `gpt-5.5 · prompts/rfi_coordination_review.md` },
    { label: 'Done', detail: 'Ready for review' },
  ];

  const pushLog = (kind, text) => setLogs(prev => [...prev, { kind, text, ts: new Date() }]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        if (!file) throw new Error('No file provided');
        const scope = tweaks.scope || 'Supply & Installation';

        setStep(0);
        setProgress(8);
        pushLog('info', `Preparing ${file.name} (${(file.size/1024).toFixed(0)} KB) — staged pipeline (Call 1 doors · Call 2 hardware · code mapping/rollup · Call 3 RFIs)…`);

        let pipelineResult;
        let pipelineSource = 'staged';
        const forceVision = !!tweaks.forceVision;
        const skipRFIs = !!tweaks.skipRFIs;

        if (forceVision) {
          pushLog('info', `forceVision is on — using image pipeline instead of staged pipeline.`);
          pipelineSource = 'image-forced';
          setStep(1);
          setProgress(20);
          pipelineResult = await extractFromPdfPipeline({
            apiKey: tweaks.apiKey,
            scope,
            file,
            onProgress: ({ kind, text }) => {
              pushLog(kind, text);
              setProgress(p => Math.min(85, p + 3));
            },
          });
        } else {
          try {
            setStep(1);
            setProgress(15);
            pipelineResult = await extractFromPdfStaged({
              apiKey: tweaks.apiKey,
              scope,
              file,
              runRFIs: !skipRFIs,
              onProgress: ({ kind, text }) => {
                pushLog(kind, text);
                if (/^Call 1/i.test(text))      { setStep(1); setProgress(p => Math.max(p, 25)); }
                else if (/^Call 2/i.test(text)) { setStep(2); setProgress(p => Math.max(p, 50)); }
                else if (/^Mapping/i.test(text)){ setStep(3); setProgress(p => Math.max(p, 75)); }
                else if (/^Call 3/i.test(text)) { setStep(4); setProgress(p => Math.max(p, 85)); }
                else setProgress(p => Math.min(90, p + 1));
              },
            });
          } catch (eStaged) {
            // Staged pipeline failed — fall through to the legacy single-shot / multipass / image chain
            pushLog('warn', `Staged pipeline failed: ${eStaged.message}. Falling back to single-shot…`);
            pipelineSource = 'native-fast';
            try {
              setStep(1);
              setProgress(20);
              pipelineResult = await extractFromPdfFast({
                apiKey: tweaks.apiKey,
                scope,
                file,
                onProgress: ({ kind, text }) => {
                  pushLog(kind, text);
                  if (/thinking/i.test(text)) setProgress(p => Math.min(70, p + 1));
                  else if (/Done|returned/i.test(text)) { setStep(3); setProgress(80); }
                  else setProgress(p => Math.min(70, p + 3));
                },
              });
            } catch (e) {
              // Fast pipeline failed (truncation, network, etc.) — try multi-pass native, then image pipeline
              pushLog('warn', `Fast pipeline failed: ${e.message}. Trying multi-pass native…`);
              pipelineSource = 'native-multipass';
              try {
                pipelineResult = await extractFromPdfDirect({
                  apiKey: tweaks.apiKey,
                  scope,
                  file,
                  onProgress: ({ kind, text }) => {
                    pushLog(kind, text);
                    setProgress(p => Math.min(85, p + 2));
                  },
                });
              } catch (e2) {
                pushLog('warn', `Multi-pass native failed: ${e2.message}. Falling back to image pipeline…`);
                pipelineSource = 'image-fallback';
                pipelineResult = await extractFromPdfPipeline({
                  apiKey: tweaks.apiKey,
                  scope,
                  file,
                  onProgress: ({ kind, text }) => {
                    pushLog(kind, text);
                    setProgress(p => Math.min(85, p + 3));
                  },
                });
              }
            }
          }
        }

        const result = {
          ...pipelineResult.analysis,
          qa: { ...pipelineResult.qa, pipeline_source: pipelineSource },
        };

        setStep(5);
        setProgress(95);
        pushLog('info', 'Validating analysis…');
        if (!Array.isArray(result.door_analysis)) throw new Error('Missing door_analysis[] in response');
        const validation = validateAnalysis(result);
        result.qa = {
          ...result.qa,
          chat_model: REQUIRED_MODEL,
          vision_model: REQUIRED_MODEL,
          validation,
          extracted_at: new Date().toISOString(),
          file_name: file.name,
          file_size: file.size,
          scope,
        };
        result.status = validation.status;
        result.reason = validation.reason || null;

        const totalItems = (result.hardware_set_review || []).reduce((n, s) => n + (s.items?.length || 0), 0);
        const lowConf = result.door_analysis.filter(d => (d.confidence ?? 1) < 0.85).length;
        if (lowConf) pushLog('warn', `${lowConf} opening(s) flagged for review (confidence < 85%)`);
        if (validation.failedMappings.length) pushLog('warn', `${validation.failedMappings.length} FAILED_MAPPING — see Extraction QA`);
        if (validation.status === 'REVIEW_REQUIRED') pushLog('warn', `Status: REVIEW_REQUIRED · ${result.reason}`);
        const highRisk = result.door_analysis.filter(d => String(d.risk_level||'').toLowerCase() === 'high').length;
        if (highRisk) pushLog('warn', `${highRisk} HIGH-risk opening(s) — see Risks & RFIs`);
        pushLog('ok', `${result.door_analysis.length} openings · ${result.hardware_set_review.length} HW sets · ${totalItems} items · ${result.project_risks.length} risks · ${result.rfi_log.length} RFIs`);

        setStep(5);
        setProgress(100);
        pushLog('ok', 'Done.');
        setTimeout(() => onDone(result), 500);
      } catch (e) {
        setError(e.message || String(e));
        pushLog('warn', 'Error: ' + (e.message || String(e)));
      }
    })();
  }, []);

  return (
    <div className="fade-in" style={{maxWidth: 860, margin: '0 auto'}}>
      <div className="page-header">
        <div>
          <h1 className="page-title">{error ? 'Extraction failed' : 'Analyzing document'}</h1>
          <div className="page-subtitle">{file?.name}</div>
        </div>
        <div className="row">
          <Button onClick={onCancel}><Icon name="arrow-left"/> Back</Button>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card-body">
          <div style={{display:'flex', alignItems:'center', gap: 12, marginBottom: 12}}>
            {!error ? (
              <Icon name="loader" className="spin" size={20} style={{color:'var(--brand-600)'}}/>
            ) : (
              <Icon name="alert" size={20} style={{color:'var(--accent-red)'}}/>
            )}
            <div style={{flex:1}}>
              <div style={{fontWeight:600, fontSize:14}}>{steps[step]?.label || 'Working'}</div>
              <div className="muted" style={{fontSize:12}}>{steps[step]?.detail}</div>
            </div>
            <div className="mono" style={{fontVariantNumeric:'tabular-nums', fontWeight:600}}>{Math.round(progress)}%</div>
          </div>
          <div className="progress-track"><div className="progress-bar" style={{width: progress + '%', background: error ? 'var(--accent-red)' : null}}/></div>

          <div style={{display:'grid', gridTemplateColumns:`repeat(${steps.length}, 1fr)`, gap: 8, marginTop: 16}}>
            {steps.map((s, i) => (
              <div key={i} style={{
                padding: 8, borderRadius: 6,
                background: i < step ? 'var(--accent-green-light)' : (i === step ? 'var(--brand-50)' : 'var(--bg-sunken)'),
                border: '1px solid ' + (i < step ? '#a7f3d0' : (i === step ? 'var(--brand-100)' : 'var(--border)')),
                fontSize: 11, color: i <= step ? 'var(--fg)' : 'var(--fg-muted)'
              }}>
                <div style={{display:'flex', alignItems:'center', gap:4, marginBottom:2}}>
                  {i < step ? <Icon name="check" size={12} style={{color:'var(--accent-green)'}}/> : <Icon name="circle-dot" size={12} style={{color: i === step ? 'var(--brand-600)' : 'var(--fg-faint)'}}/>}
                  <span style={{fontWeight:600, fontSize:10, textTransform:'uppercase', letterSpacing:0.04}}>Step {i+1}</span>
                </div>
                <div>{s.label}</div>
              </div>
            ))}
          </div>

          {error && (
            <div style={{marginTop: 16, padding: 12, background:'var(--accent-red-light)', borderRadius: 8, color:'#991b1b', fontSize: 13}}>
              <strong>Extraction failed:</strong> {error}
              <div style={{marginTop: 8}}>
                <Button kind="primary" onClick={onCancel}>Back to upload</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header"><div className="card-title">Activity</div></div>
        <div style={{padding:16}}>
          <div className="log-stream">
            {logs.map((l, i) => (
              <div key={i} className="log-line">
                <span className="log-ts">{l.ts.toLocaleTimeString('en-US', {hour12:false})}</span>
                <span className={'log-' + (l.kind === 'warn' ? 'warn' : l.kind === 'ok' ? 'ok' : 'info')}>
                  {l.kind === 'warn' ? '! ' : l.kind === 'ok' ? '✓ ' : '· '}
                </span>
                {l.text}
              </div>
            ))}
            {!error && <div style={{opacity:0.5}}>▋</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

window.__fb_part2 = true;


/* ---------- Project Summary ---------- */
const SummaryScreen = ({ analysis, project, tweaks, setRoute }) => {
  if (!analysis) return null;
  const ps = analysis.project_summary || {};
  const scope = ps.scope_type || tweaks.scope || 'Supply & Installation';
  const overall = String(ps.overall_bid_risk || '').toLowerCase();
  const overallTone = overall === 'high' ? 'var(--accent-red)' : overall === 'medium' ? 'var(--accent-amber)' : 'var(--accent-green)';
  const Stat = ({ label, value, tone, sub }) => (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={tone ? {color: tone} : null}>{value ?? '—'}</div>
      {sub && <div className="stat-delta">{sub}</div>}
    </div>
  );

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">{ps.project_name || project.name || 'Project'}</h1>
          <div className="page-subtitle">
            <Badge tone="blue">{scope}</Badge>
            {ps.project_number && <span style={{marginLeft: 8}} className="mono">{ps.project_number}</span>}
            {ps.architect && <span style={{marginLeft: 8}} className="muted">· {ps.architect}</span>}
            {analysis.qa?.pdf_type === 'IMAGE_BASED_PDF' && <Badge tone="amber" style={{marginLeft: 8}}>Image-based PDF</Badge>}
          </div>
        </div>
        <div className="row">
          <Button onClick={() => exportAnalysisToExcel({ analysis, project, tweaks })}><Icon name="download"/> Export Excel</Button>
          <Button onClick={() => exportAnalysisToComsenseCSV({ analysis, project, tweaks })} title="Comsense-style Door & Frame Schedule CSV (importable into Comsense Advantage)"><Icon name="file-text"/> Comsense CSV</Button>
          <Button onClick={() => setRoute('doors')}>Door analysis <Icon name="arrow-right"/></Button>
          <Button kind="primary" onClick={() => setRoute('risks')}>Risks &amp; RFIs <Icon name="arrow-right"/></Button>
        </div>
      </div>

      {analysis.status === 'REVIEW_REQUIRED' && (
        <div className="card" style={{marginBottom: 16, borderLeft: '4px solid var(--accent-amber)'}}>
          <div className="card-body" style={{display:'flex', gap: 12, alignItems:'center'}}>
            <Icon name="alert" style={{color: 'var(--accent-amber)'}}/>
            <div style={{flex: 1}}>
              <div style={{fontWeight: 600}}>Status: REVIEW_REQUIRED</div>
              <div className="muted" style={{fontSize: 13}}>Reason: <span className="mono">{analysis.reason || 'unspecified'}</span> · Open the Extraction QA tab to see what was extracted, failed mappings, and page crops.</div>
            </div>
            <Button kind="primary" onClick={() => setRoute('qa')}><Icon name="shield"/> Open Extraction QA</Button>
          </div>
        </div>
      )}

      <div className="card" style={{marginBottom: 16, borderLeft: '4px solid ' + overallTone}}>
        <div className="card-body" style={{display:'flex', gap: 16, alignItems:'flex-start'}}>
          <div style={{width: 48, height: 48, borderRadius: 10, background: 'var(--brand-50)', color: overallTone, display:'grid', placeItems:'center', flexShrink: 0}}>
            <Icon name="briefcase" size={22}/>
          </div>
          <div style={{flex: 1}}>
            <div style={{display:'flex', alignItems:'center', gap: 10, marginBottom: 6}}>
              <strong style={{fontSize: 14}}>Estimator overview</strong>
              <RiskPill level={ps.overall_bid_risk}/>
              <span className="muted" style={{fontSize: 12}}>overall bid risk</span>
            </div>
            <div style={{fontSize: 13, lineHeight: 1.65, color: 'var(--fg)'}}>
              {ps.estimator_summary || <span className="muted">No overview provided by the analysis.</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <Stat label="Total openings" value={ps.total_openings_found ?? analysis.door_analysis.length}/>
        <Stat label="Hardware sets referenced" value={ps.total_hardware_sets_referenced ?? analysis.hardware_set_review.length}/>
        <Stat label="HW sets missing/unclear" value={ps.hardware_sets_missing_or_unclear ?? 0} tone={ps.hardware_sets_missing_or_unclear ? 'var(--accent-amber)' : null}/>
        <Stat label="Complex installations" value={ps.complex_installations ?? 0}/>
      </div>
      <div className="stats-grid">
        <Stat label="High risk openings" value={ps.high_risk_openings ?? 0} tone={ps.high_risk_openings ? 'var(--accent-red)' : null}/>
        <Stat label="Medium risk" value={ps.medium_risk_openings ?? 0} tone={ps.medium_risk_openings ? 'var(--accent-amber)' : null}/>
        <Stat label="Low risk" value={ps.low_risk_openings ?? 0} tone="var(--accent-green)"/>
        <Stat label="Access control" value={ps.access_control_openings ?? 0}/>
      </div>
      <div className="stats-grid">
        <Stat label="Exterior openings" value={ps.exterior_openings ?? 0}/>
        <Stat label="Fire-rated openings" value={ps.fire_rated_openings ?? 0}/>
        <Stat label="Risks flagged" value={analysis.project_risks.length}/>
        <Stat label="RFIs to send" value={analysis.rfi_log.length} tone={analysis.rfi_log.length ? 'var(--accent-amber)' : null}/>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap: 12, marginTop: 8}}>
        <div className="card">
          <div className="card-header"><div className="card-title">Top risks</div></div>
          <div style={{padding: 4}}>
            {analysis.project_risks.slice(0, 5).map((r, i) => (
              <div key={i} style={{padding: '10px 14px', borderBottom: i === 4 ? 'none' : '1px solid var(--border)', fontSize: 13}}>
                <div style={{display:'flex', alignItems:'center', marginBottom: 4}}>
                  <SeverityDot severity={r.severity}/>
                  <strong style={{flex: 1}}>{r.category || 'Risk'}</strong>
                  <RiskPill level={r.severity}/>
                </div>
                <div className="muted" style={{fontSize: 12}}>{r.issue}</div>
              </div>
            ))}
            {analysis.project_risks.length === 0 && <div style={{padding: 24, textAlign: 'center'}} className="muted">No project-level risks flagged.</div>}
          </div>
          {analysis.project_risks.length > 5 && (
            <div style={{padding: 10, borderTop: '1px solid var(--border)', textAlign: 'right'}}>
              <Button size="sm" onClick={() => setRoute('risks')}>View all {analysis.project_risks.length} risks <Icon name="arrow-right" size={12}/></Button>
            </div>
          )}
        </div>
        <div className="card" style={{borderLeft: '3px solid var(--accent-red)'}}>
          <div className="card-header"><div className="card-title">High priority RFIs</div></div>
          <div style={{padding: 4}}>
            {(() => {
              const highRfis = (analysis.rfi_log || []).filter(r => String(r.priority || '').toLowerCase() === 'high');
              const shown = highRfis.length ? highRfis.slice(0, 5) : (analysis.rfi_log || []).slice(0, 5);
              if (!shown.length) return <div style={{padding: 24, textAlign: 'center'}} className="muted">No RFIs flagged.</div>;
              return shown.map((r, i) => (
                <div key={i} style={{padding: '10px 14px', borderBottom: i === shown.length - 1 ? 'none' : '1px solid var(--border)', fontSize: 13}}>
                  <div style={{display:'flex', alignItems:'center', marginBottom: 4, gap: 8}}>
                    <Badge mono>RFI-{String(i+1).padStart(3,'0')}</Badge>
                    <RiskPill level={r.priority}/>
                    <span className="muted" style={{fontSize: 11, marginLeft: 'auto'}}>{r.category || ''}</span>
                  </div>
                  <div style={{fontSize: 12, fontWeight: 600, lineHeight: 1.45}}>{r.question}</div>
                  {r.affected_openings?.length > 0 && <div className="mono-small" style={{marginTop: 4}}>Affected: {r.affected_openings.slice(0,6).join(', ')}{r.affected_openings.length>6?'…':''}</div>}
                </div>
              ));
            })()}
          </div>
          {analysis.rfi_log.length > 5 && (
            <div style={{padding: 10, borderTop: '1px solid var(--border)', textAlign: 'right'}}>
              <Button size="sm" onClick={() => setRoute('risks')}>View all {analysis.rfi_log.length} RFIs <Icon name="arrow-right" size={12}/></Button>
            </div>
          )}
        </div>
      </div>

      {(analysis.estimator_notes && analysis.estimator_notes.length > 0) && (
        <div className="card" style={{marginTop: 12}}>
          <div className="card-header"><div className="card-title">Estimator Review Summary</div></div>
          <div style={{padding: '4px 4px 8px'}}>
            {analysis.estimator_notes.slice(0, 6).map((n, i) => (
              <div key={i} style={{padding: '8px 18px', borderBottom: i === Math.min(analysis.estimator_notes.length, 6) - 1 ? 'none' : '1px solid var(--border)', fontSize: 13, lineHeight: 1.6, display: 'flex', gap: 12}}>
                <span style={{color: 'var(--brand-600)', fontWeight: 700, flexShrink: 0}}>·</span>
                <span>{n}</span>
              </div>
            ))}
            {analysis.estimator_notes.length > 6 && (
              <div style={{padding: 10, borderTop: '1px solid var(--border)', textAlign: 'right'}}>
                <Button size="sm" onClick={() => setRoute('risks')}>View all {analysis.estimator_notes.length} notes <Icon name="arrow-right" size={12}/></Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/* ---------- Door Analysis ---------- */
const DoorAnalysisScreen = ({ analysis, setAnalysis, onContinue }) => {
  const doors = analysis?.door_analysis || [];
  const [q, setQ] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [expanded, setExpanded] = useState(null);

  const filtered = useMemo(() => {
    const qq = q.toLowerCase();
    return doors.filter(d => {
      if (riskFilter !== 'all' && String(d.risk_level||'').toLowerCase() !== riskFilter) return false;
      if (!qq) return true;
      return (
        (d.mark||'').toLowerCase().includes(qq) ||
        (d.room_or_location||'').toLowerCase().includes(qq) ||
        (d.hardware_set||'').toLowerCase().includes(qq) ||
        (d.special_conditions||[]).join(' ').toLowerCase().includes(qq) ||
        (d.remarks||[]).join(' ').toLowerCase().includes(qq)
      );
    });
  }, [doors, q, riskFilter]);

  const updateDoor = (mark, patch) => setAnalysis({ ...analysis, door_analysis: doors.map(d => d.mark === mark ? { ...d, ...patch } : d) });

  const counts = useMemo(() => {
    const c = { high: 0, medium: 0, low: 0, rfi: 0 };
    doors.forEach(d => { const r = String(d.risk_level||'').toLowerCase(); if (c[r] != null) c[r]++; if (d.rfi_required) c.rfi++; });
    return c;
  }, [doors]);

  const Conf = ({ v }) => {
    const val = v ?? 1;
    const cls = val >= 0.9 ? 'high' : val >= 0.85 ? 'med' : 'low';
    return <span className={'confidence ' + cls}>
      <span className="confidence-track"><span className="confidence-fill" style={{width: (val*100)+'%'}}/></span>
      {Math.round(val*100)}%
    </span>;
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Door Analysis</h1>
          <div className="page-subtitle">{doors.length} openings · click any row to see issues, recommendations, and RFIs</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={onContinue}>Hardware review <Icon name="arrow-right"/></Button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-label">Total openings</div><div className="stat-value">{doors.length}</div></div>
        <div className="stat-card"><div className="stat-label">High risk</div><div className="stat-value" style={{color: counts.high ? 'var(--accent-red)' : null}}>{counts.high}</div></div>
        <div className="stat-card"><div className="stat-label">Medium risk</div><div className="stat-value" style={{color: counts.medium ? 'var(--accent-amber)' : null}}>{counts.medium}</div></div>
        <div className="stat-card"><div className="stat-label">RFI required</div><div className="stat-value" style={{color: counts.rfi ? 'var(--accent-amber)' : null}}>{counts.rfi}</div></div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="row" style={{flex: 1, gap: 8}}>
            <div style={{position:'relative'}}>
              <Icon name="search" size={14} style={{position:'absolute', left:8, top:'50%', transform:'translateY(-50%)', color:'var(--fg-faint)'}}/>
              <input className="input input-sm" style={{paddingLeft:28, width: 280}} placeholder="Search mark, room, HW set, condition…" value={q} onChange={e => setQ(e.target.value)}/>
            </div>
            <div className="row" style={{marginLeft: 8}}>
              {['all', 'high', 'medium', 'low'].map(r => (
                <Button key={r} size="sm" kind={riskFilter === r ? 'primary' : 'default'} onClick={() => setRiskFilter(r)}>
                  {r === 'all' ? 'All' : r[0].toUpperCase() + r.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </div>
        {doors.length === 0 ? (
          <EmptyState icon="door" title="No openings yet" body="Upload a PDF to extract a door schedule."/>
        ) : (
          <div style={{overflow:'auto'}}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{width: 30}}></th>
                  <th>Mark</th>
                  <th>Room / Location</th>
                  <th>Type</th>
                  <th>Int/Ext</th>
                  <th>Size (W×H)</th>
                  <th>Fire</th>
                  <th>HW Set</th>
                  <th>HW Status</th>
                  <th>Install</th>
                  <th>Risk</th>
                  <th>Special</th>
                  <th>RFI</th>
                  <th>Conf.</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => {
                  const isOpen = expanded === d.mark + '-' + i;
                  return (
                    <Fragment key={d.mark + '-' + i}>
                      <tr style={{cursor: 'pointer'}} onClick={() => setExpanded(isOpen ? null : d.mark + '-' + i)}>
                        <td><Icon name={isOpen ? 'chevron-down' : 'chevron-right'} size={12} style={{color:'var(--fg-faint)'}}/></td>
                        <td className="mono"><strong>{d.mark}</strong></td>
                        <td style={{maxWidth: 220}}>{d.room_or_location || '—'}</td>
                        <td>{d.door_type ? <Badge>{d.door_type}</Badge> : <span className="muted">—</span>}</td>
                        <td><span className="muted" style={{fontSize: 12}}>{d.interior_or_exterior || '—'}</span></td>
                        <td className="mono">{d.size?.width || '—'} × {d.size?.height || '—'}</td>
                        <td>{d.fire_rating && d.fire_rating !== '-' ? <Badge tone="red">{d.fire_rating}</Badge> : <span className="muted">—</span>}</td>
                        <td>{d.hardware_set ? <Badge tone="blue" mono>{fmtSetId(d.hardware_set)}</Badge> : <span className="muted">—</span>}</td>
                        <td><StatusPill status={d.hardware_status}/></td>
                        <td><RiskPill level={d.install_complexity}/></td>
                        <td><RiskPill level={d.risk_level}/></td>
                        <td><ChipList items={(d.special_conditions||[]).slice(0,2)} tone="amber" empty="—"/></td>
                        <td>{d.rfi_required ? <Badge tone="amber">RFI</Badge> : <span className="muted">—</span>}</td>
                        <td><Conf v={d.confidence}/></td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={14} style={{padding: 0, background: 'var(--bg-sunken)'}}>
                            <div style={{padding: 18, display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 18}}>
                              <DetailBlock label="Door build">
                                <Kv k="Material" v={d.door_material}/>
                                <Kv k="Finish" v={d.door_finish}/>
                                <Kv k="Glazing" v={d.glazing}/>
                                <Kv k="Thickness" v={d.size?.thickness}/>
                              </DetailBlock>
                              <DetailBlock label="Frame">
                                <Kv k="Type" v={d.frame_type}/>
                                <Kv k="Material" v={d.frame_material}/>
                                <Kv k="Finish" v={d.frame_finish}/>
                                <Kv k="Opening type" v={d.opening_type}/>
                              </DetailBlock>
                              <DetailBlock label="Remarks (as written)">
                                <ChipList items={d.remarks} tone="" empty="No remarks"/>
                              </DetailBlock>
                              <DetailBlock label="Special conditions">
                                <ChipList items={d.special_conditions} tone="amber" empty="None"/>
                              </DetailBlock>
                              <DetailBlock label="Issues">
                                {d.issues?.length ? <ul style={{margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6}}>
                                  {d.issues.map((x, j) => <li key={j}>{x}</li>)}
                                </ul> : <span className="muted">None</span>}
                              </DetailBlock>
                              <DetailBlock label="Recommendations">
                                {d.recommendations?.length ? <ul style={{margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6}}>
                                  {d.recommendations.map((x, j) => <li key={j}>{x}</li>)}
                                </ul> : <span className="muted">None</span>}
                              </DetailBlock>
                              {(() => {
                                const assignedSet = (analysis.hardware_set_review || []).find(s => s.hardware_set === d.hardware_set);
                                const assignedItems = assignedSet?.items || [];
                                if (!d.hardware_set) return null;
                                return (
                                  <div style={{gridColumn: '1 / -1'}}>
                                    <DetailBlock label={`Assigned hardware — ${fmtSetId(d.hardware_set)} (${assignedItems.length} item${assignedItems.length === 1 ? '' : 's'})`}>
                                      {assignedItems.length === 0 ? (
                                        <div style={{padding: 8, fontSize: 12, background: 'var(--accent-amber-light)', color: '#92400e', borderRadius: 6}}>
                                          No items extracted for set HW-{d.hardware_set}. This is a FAILED_MAPPING — see Extraction QA.
                                        </div>
                                      ) : (
                                        <table className="table" style={{marginTop: 4}}>
                                          <thead>
                                            <tr>
                                              <th style={{width: 30}}>#</th>
                                              <th style={{width: 50}}>Qty</th>
                                              <th>Description</th>
                                              <th>Part #</th>
                                              <th>Manufacturer</th>
                                              <th>Finish</th>
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {assignedItems.map((it, j) => (
                                              <tr key={j}>
                                                <td className="mono" style={{color: 'var(--fg-faint)'}}>{j + 1}</td>
                                                <td className="mono">{it.qty ?? '—'}</td>
                                                <td>{it.desc || '—'}</td>
                                                <td className="mono">{it.part || '—'}</td>
                                                <td>{it.mfr || '—'}</td>
                                                <td>{it.finish ? <Badge>{it.finish}</Badge> : <span className="muted">—</span>}</td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      )}
                                    </DetailBlock>
                                  </div>
                                );
                              })()}
                              {d.rfi_required && (
                                <div style={{gridColumn: '1 / -1'}}>
                                  <DetailBlock label="RFI questions">
                                    {d.rfi_questions?.length ? <ol style={{margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.6}}>
                                      {d.rfi_questions.map((x, j) => <li key={j}>{x}</li>)}
                                    </ol> : <span className="muted">RFI flagged but no specific question provided.</span>}
                                  </DetailBlock>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
                {filtered.length === 0 && doors.length > 0 && (
                  <tr><td colSpan={14} style={{padding: 32, textAlign:'center'}} className="muted">No openings match this filter.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const DetailBlock = ({ label, children }) => (
  <div>
    <div style={{fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--fg-muted)', fontWeight: 700, marginBottom: 8}}>{label}</div>
    <div style={{fontSize: 13, lineHeight: 1.5}}>{children}</div>
  </div>
);
const Kv = ({ k, v }) => (
  <div style={{display: 'grid', gridTemplateColumns: '120px 1fr', gap: 6, padding: '2px 0', fontSize: 12}}>
    <span className="muted">{k}</span>
    <span>{v || '—'}</span>
  </div>
);

/* ---------- Hardware Catalog ---------- */
const HardwareCatalogScreen = ({ catalog, setCatalog, markup, currentSetIds }) => {
  const [expanded, setExpanded] = useState(new Set());
  const [search, setSearch] = useState('');

  const toggle = (id) => {
    const n = new Set(expanded); n.has(id) ? n.delete(id) : n.add(id); setExpanded(n);
  };

  const update = (id, patch) => setCatalog(catalog.map(s => s.id === id ? { ...s, ...patch } : s));
  const updateItem = (setId, idx, patch) => setCatalog(catalog.map(s => s.id !== setId ? s : { ...s, items: s.items.map((it, i) => i === idx ? { ...it, ...patch } : it) }));
  const removeItem = (setId, idx) => setCatalog(catalog.map(s => s.id !== setId ? s : { ...s, items: s.items.filter((_, i) => i !== idx) }));
  const addItem = (setId) => setCatalog(catalog.map(s => s.id !== setId ? s : { ...s, items: [...s.items, { qty: 1, desc: '', part: '', mfr: '', finish: '', unitPrice: null }] }));
  const addSet = () => setCatalog([...catalog, { id: 'NEW' + (catalog.length + 1), name: 'New hardware set', description: '', items: [] }]);
  const removeSet = (id) => { if (confirm('Delete this hardware set?')) setCatalog(catalog.filter(s => s.id !== id)); };

  const filtered = catalog.filter(s => !search ||
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.id.toLowerCase().includes(search.toLowerCase()) ||
    s.items.some(i => (i.desc||'').toLowerCase().includes(search.toLowerCase()) || (i.part||'').toLowerCase().includes(search.toLowerCase())));

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Hardware Catalog</h1>
          <div className="page-subtitle">{catalog.length} set{catalog.length === 1 ? '' : 's'} · editable part numbers & pricing</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={addSet}><Icon name="plus"/> New set</Button>
        </div>
      </div>

      {catalog.length > 0 && (
        <div style={{marginBottom: 12, maxWidth: 360, position:'relative'}}>
          <Icon name="search" size={14} style={{position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'var(--fg-faint)'}}/>
          <input className="input" style={{paddingLeft: 32}} placeholder="Search sets, parts, manufacturers…" value={search} onChange={e => setSearch(e.target.value)}/>
        </div>
      )}

      {catalog.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="library"
            title="No hardware sets yet"
            body="Sets populate automatically when you extract a spec book PDF, or add them manually."
            action={<Button kind="primary" onClick={addSet}><Icon name="plus"/> Add a set</Button>}
          />
        </div>
      ) : (
        <div style={{display:'grid', gap: 10}}>
          {filtered.map(set => {
            const isOpen = expanded.has(set.id);
            const base = setTotal(set);
            const withMarkup = base * (1 + markup/100);
            const usedHere = currentSetIds?.has(set.id);
            return (
              <div key={set.id} className="card">
                <div className="card-header" style={{cursor:'pointer'}} onClick={() => toggle(set.id)}>
                  <div className="row" style={{gap:12}}>
                    <Icon name={isOpen ? 'chevron-down' : 'chevron-right'} size={14}/>
                    <Badge tone="blue" mono>{fmtSetId(set.id)}</Badge>
                    <div>
                      <div style={{fontWeight:600}}>{set.name}</div>
                      <div className="muted" style={{fontSize:12}}>{set.description || 'No description'}</div>
                    </div>
                  </div>
                  <div className="row">
                    {usedHere && <Badge tone="green">In use</Badge>}
                    <span className="muted" style={{fontSize:12}}>{set.items.length} items</span>
                    <span className="mono" style={{fontWeight:600, fontSize:14}}>{base > 0 ? fmt0(withMarkup) : <em style={{fontStyle:'italic', color:'var(--fg-muted)', fontSize:12}}>add prices</em>}</span>
                  </div>
                </div>
                {isOpen && (
                  <>
                    <div style={{padding: '8px 16px', borderBottom:'1px solid var(--border)', display:'grid', gridTemplateColumns:'120px 1fr', gap: 12, fontSize: 12}}>
                      <label className="tweak-label">Set ID</label>
                      <input className="input input-sm" value={set.id} onChange={e => update(set.id, { id: e.target.value })} style={{maxWidth: 100}}/>
                      <label className="tweak-label">Name</label>
                      <input className="input input-sm" value={set.name} onChange={e => update(set.id, { name: e.target.value })}/>
                      <label className="tweak-label">Description</label>
                      <input className="input input-sm" value={set.description || ''} onChange={e => update(set.id, { description: e.target.value })}/>
                    </div>
                    <div style={{overflow: 'auto'}}>
                      <table className="table">
                        <thead>
                          <tr>
                            <th style={{width:50}}>Qty</th><th>Description</th><th>Part #</th>
                            <th>Mfr</th><th>Finish</th>
                            <th style={{textAlign:'right'}}>Unit price</th>
                            <th style={{textAlign:'right'}}>Line</th>
                            <th style={{width:40}}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {set.items.map((it, i) => (
                            <tr key={i}>
                              <td><input className="input input-sm" style={{width:50}} type="number" value={it.qty || 0} onChange={e => updateItem(set.id, i, { qty: Number(e.target.value) })}/></td>
                              <td><input className="input input-sm" value={it.desc || ''} onChange={e => updateItem(set.id, i, { desc: e.target.value })}/></td>
                              <td><input className="input input-sm mono" style={{width:130}} value={it.part || ''} onChange={e => updateItem(set.id, i, { part: e.target.value })}/></td>
                              <td><input className="input input-sm" style={{width:110}} value={it.mfr || ''} onChange={e => updateItem(set.id, i, { mfr: e.target.value })}/></td>
                              <td><input className="input input-sm" style={{width:60}} value={it.finish || ''} onChange={e => updateItem(set.id, i, { finish: e.target.value })}/></td>
                              <td><input className="input input-sm mono" type="number" style={{width:90, textAlign:'right'}} value={it.unitPrice ?? ''} placeholder="—" onChange={e => updateItem(set.id, i, { unitPrice: e.target.value === '' ? null : Number(e.target.value) })}/></td>
                              <td className="mono" style={{textAlign:'right', fontWeight:600}}>{it.unitPrice ? fmt(it.qty * it.unitPrice) : '—'}</td>
                              <td><IconButton onClick={() => removeItem(set.id, i)}><Icon name="trash" size={14}/></IconButton></td>
                            </tr>
                          ))}
                          <tr>
                            <td colSpan="8">
                              <Button size="sm" onClick={() => addItem(set.id)}><Icon name="plus" size={12}/> Add item</Button>
                            </td>
                          </tr>
                          {base > 0 && (
                            <>
                              <tr style={{background:'var(--bg-sunken)'}}>
                                <td colSpan="6" style={{fontWeight:600, textAlign:'right'}}>Subtotal (base)</td>
                                <td className="mono" style={{textAlign:'right', fontWeight:700}}>{fmt(base)}</td>
                                <td></td>
                              </tr>
                              <tr style={{background:'var(--bg-sunken)'}}>
                                <td colSpan="6" style={{fontWeight:600, textAlign:'right'}}>With {markup}% markup</td>
                                <td className="mono" style={{textAlign:'right', fontWeight:700, color:'var(--brand-700)'}}>{fmt(withMarkup)}</td>
                                <td></td>
                              </tr>
                            </>
                          )}
                        </tbody>
                      </table>
                    </div>
                    <div style={{padding: '10px 16px', borderTop:'1px solid var(--border)', display:'flex', justifyContent:'flex-end'}}>
                      <Button kind="danger" size="sm" onClick={() => removeSet(set.id)}><Icon name="trash" size={12}/> Delete set</Button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/* ---------- Hardware Review ---------- */
const HardwareReviewScreen = ({ analysis, onContinue }) => {
  const sets = analysis?.hardware_set_review || [];
  const doors = analysis?.door_analysis || [];
  const [expanded, setExpanded] = useState(new Set());

  const referencedSets = useMemo(() => {
    const m = {};
    doors.forEach(d => { if (d.hardware_set) m[d.hardware_set] = (m[d.hardware_set] || 0) + 1; });
    return m;
  }, [doors]);

  const orphans = Object.keys(referencedSets).filter(id => !sets.find(s => s.hardware_set === id));

  const toggle = (id) => {
    const n = new Set(expanded); n.has(id) ? n.delete(id) : n.add(id); setExpanded(n);
  };

  const counts = {
    complete: sets.filter(s => String(s.status||'').toLowerCase() === 'complete').length,
    incomplete: sets.filter(s => String(s.status||'').toLowerCase() === 'incomplete').length,
    unclear: sets.filter(s => ['unclear', 'review required'].includes(String(s.status||'').toLowerCase())).length,
    missing: sets.filter(s => String(s.status||'').toLowerCase() === 'missing').length + orphans.length,
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Hardware Review</h1>
          <div className="page-subtitle">{sets.length} hardware sets · coordination, completeness, and gaps</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={onContinue}>Risks &amp; RFIs <Icon name="arrow-right"/></Button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-label">Complete</div><div className="stat-value" style={{color:'var(--accent-green)'}}>{counts.complete}</div></div>
        <div className="stat-card"><div className="stat-label">Incomplete</div><div className="stat-value" style={{color: counts.incomplete ? 'var(--accent-amber)' : null}}>{counts.incomplete}</div></div>
        <div className="stat-card"><div className="stat-label">Unclear / review</div><div className="stat-value" style={{color: counts.unclear ? 'var(--accent-amber)' : null}}>{counts.unclear}</div></div>
        <div className="stat-card"><div className="stat-label">Missing</div><div className="stat-value" style={{color: counts.missing ? 'var(--accent-red)' : null}}>{counts.missing}</div></div>
      </div>

      {orphans.length > 0 && (
        <div className="card" style={{marginBottom: 12, borderColor: 'var(--accent-red)'}}>
          <div className="card-body" style={{display:'flex', gap: 12}}>
            <Icon name="alert" style={{color:'var(--accent-red)', flexShrink: 0, marginTop: 2}}/>
            <div style={{fontSize: 13}}>
              <strong>Doors reference {orphans.length} hardware set(s) that are missing from the spec:</strong>{' '}
              <span className="mono">{orphans.join(', ')}</span>. Flag as RFI before bidding.
            </div>
          </div>
        </div>
      )}

      <div className="card">
        {sets.length === 0 ? (
          <EmptyState icon="package" title="No hardware sets reviewed" body="The analysis returned no hardware set review entries."/>
        ) : (
          <div>
            {sets.map(s => {
              const isOpen = expanded.has(s.hardware_set);
              const refCount = s.referenced_by_doors?.length || referencedSets[s.hardware_set] || 0;
              return (
                <div key={s.hardware_set} style={{borderBottom: '1px solid var(--border)'}}>
                  <div onClick={() => toggle(s.hardware_set)}
                       style={{padding: '14px 18px', cursor: 'pointer', display: 'grid', gridTemplateColumns: '20px 110px 1fr auto auto auto', gap: 14, alignItems: 'center'}}>
                    <Icon name={isOpen ? 'chevron-down' : 'chevron-right'} size={14} style={{color: 'var(--fg-faint)'}}/>
                    <Badge tone="blue" mono>{fmtSetId(s.hardware_set)}</Badge>
                    <div>
                      <div style={{fontWeight: 600, fontSize: 13}}>{s.estimator_note || 'Hardware set ' + s.hardware_set}</div>
                      {s.special_coordination?.length > 0 && (
                        <div className="mono-small" style={{marginTop: 2}}>
                          {s.special_coordination.slice(0, 3).join(' · ')}{s.special_coordination.length > 3 ? ' …' : ''}
                        </div>
                      )}
                    </div>
                    <span className="muted" style={{fontSize: 12}}>{refCount} opening{refCount === 1 ? '' : 's'} · {(s.items || []).length} item{(s.items || []).length === 1 ? '' : 's'}</span>
                    <StatusPill status={s.status}/>
                    <span className="muted" style={{fontSize: 11}}>Conf {Math.round((s.confidence ?? 1) * 100)}%</span>
                  </div>
                  {isOpen && (
                    <div style={{padding: '14px 18px 18px 52px', background: 'var(--bg-sunken)', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 18}}>
                      <DetailBlock label="Referenced by openings">
                        <ChipList items={s.referenced_by_doors} tone="" empty="No opening references found"/>
                      </DetailBlock>
                      <DetailBlock label="Status">
                        <StatusPill status={s.status}/>
                      </DetailBlock>
                      <div style={{gridColumn: '1 / -1'}}>
                        <DetailBlock label={`Hardware items (${(s.items || []).length})`}>
                          {(s.items && s.items.length) ? (
                            <table className="table" style={{marginTop: 4}}>
                              <thead>
                                <tr>
                                  <th style={{width: 30}}>#</th>
                                  <th style={{width: 50}}>Qty</th>
                                  <th>Description</th>
                                  <th>Part #</th>
                                  <th>Manufacturer</th>
                                  <th>Finish</th>
                                </tr>
                              </thead>
                              <tbody>
                                {s.items.map((it, i) => (
                                  <tr key={i}>
                                    <td className="mono" style={{color: 'var(--fg-faint)'}}>{i + 1}</td>
                                    <td className="mono">{it.qty ?? '—'}</td>
                                    <td>{it.desc || '—'}</td>
                                    <td className="mono">{it.part || '—'}</td>
                                    <td>{it.mfr || '—'}</td>
                                    <td>{it.finish ? <Badge>{it.finish}</Badge> : <span className="muted">—</span>}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : <span className="muted" style={{fontSize: 13}}>No items extracted for this set.</span>}
                        </DetailBlock>
                      </div>
                      <DetailBlock label="Missing or unclear items">
                        {s.missing_or_unclear_items?.length ? <ul style={{margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6}}>
                          {s.missing_or_unclear_items.map((x, i) => <li key={i}>{x}</li>)}
                        </ul> : <span className="muted">None — set appears complete</span>}
                      </DetailBlock>
                      <DetailBlock label="Special coordination">
                        <ChipList items={s.special_coordination} tone="amber" empty="None"/>
                      </DetailBlock>
                      {s.estimator_note && (
                        <div style={{gridColumn: '1 / -1'}}>
                          <DetailBlock label="Estimator note">
                            <div style={{fontSize: 13, lineHeight: 1.6}}>{s.estimator_note}</div>
                          </DetailBlock>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

/* ---------- Risks & RFIs ---------- */
const RisksScreen = ({ analysis, tweaks, onContinue }) => {
  const risks = analysis?.project_risks || [];
  const rfis = analysis?.rfi_log || [];
  const notes = analysis?.estimator_notes || [];

  const sortBySeverity = (a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[String(a.severity||'').toLowerCase()] ?? 3) - (order[String(b.severity||'').toLowerCase()] ?? 3);
  };
  const sortedRisks = [...risks].sort(sortBySeverity);
  const sortedRfis = [...rfis].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[String(a.priority||'').toLowerCase()] ?? 3) - (order[String(b.priority||'').toLowerCase()] ?? 3);
  });

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Risks &amp; RFIs</h1>
          <div className="page-subtitle">{risks.length} project-level risks · {rfis.length} RFIs · {notes.length} estimator notes</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={onContinue}>Bid recommendations <Icon name="arrow-right"/></Button>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
        <div className="card">
          <div className="card-header"><div className="card-title">Project risks ({risks.length})</div></div>
          {risks.length === 0 ? (
            <div style={{padding: 32, textAlign:'center'}} className="muted">No project-level risks flagged.</div>
          ) : (
            <div style={{maxHeight: 720, overflow: 'auto'}}>
              {sortedRisks.map((r, i) => (
                <div key={i} style={{padding: 16, borderBottom: i === sortedRisks.length - 1 ? 'none' : '1px solid var(--border)'}}>
                  <div style={{display:'flex', alignItems:'center', gap: 8, marginBottom: 6}}>
                    <SeverityDot severity={r.severity}/>
                    <strong style={{flex:1, fontSize: 13}}>{r.category || 'Risk'}</strong>
                    <RiskPill level={r.severity}/>
                  </div>
                  <div style={{fontSize: 13, marginBottom: 8, lineHeight: 1.55}}>{r.issue}</div>
                  {r.affected_openings?.length > 0 && (
                    <div style={{fontSize: 11, marginBottom: 8}}>
                      <span className="muted">Affected: </span>
                      <span className="mono">{r.affected_openings.join(', ')}</span>
                    </div>
                  )}
                  {r.recommendation && (
                    <div style={{fontSize: 12, padding: '8px 12px', background: 'var(--bg-sunken)', borderLeft: '3px solid var(--brand-600)', borderRadius: 4, lineHeight: 1.5}}>
                      <strong>Recommendation: </strong>{r.recommendation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">RFI log ({rfis.length})</div></div>
          {rfis.length === 0 ? (
            <div style={{padding: 32, textAlign:'center'}} className="muted">No RFIs flagged.</div>
          ) : (
            <div style={{maxHeight: 720, overflow: 'auto'}}>
              {sortedRfis.map((r, i) => {
                const category = r.category || inferCategoryFromText(r.question || r.reason || '');
                const status = r.status || 'Open';
                const source = r.source || 'Senior estimator analysis';
                const recommendation = r.recommendation || r.reason || '';
                return (
                  <div key={i} style={{padding: 16, borderBottom: i === sortedRfis.length - 1 ? 'none' : '1px solid var(--border)'}}>
                    <div style={{display:'flex', alignItems:'center', gap: 8, marginBottom: 8, flexWrap: 'wrap'}}>
                      <Badge mono>RFI-{String(i+1).padStart(3,'0')}</Badge>
                      <RiskPill level={r.priority}/>
                      <Badge tone="blue">{category}</Badge>
                      <Badge tone={/closed|answered|resolved/i.test(status) ? 'green' : 'amber'}>{status}</Badge>
                      <span className="muted" style={{fontSize: 11, marginLeft: 'auto'}}>{source}</span>
                    </div>
                    <div style={{fontSize: 13, fontWeight: 600, marginBottom: 8, lineHeight: 1.5}}>{r.question}</div>
                    {recommendation && (
                      <div style={{fontSize: 12, padding: '8px 12px', background: 'var(--bg-sunken)', borderLeft: '3px solid var(--brand-600)', borderRadius: 4, lineHeight: 1.5, marginBottom: 8}}>
                        <strong>Recommendation: </strong>{recommendation}
                      </div>
                    )}
                    {r.affected_openings?.length > 0 && (
                      <div style={{fontSize: 11}}>
                        <span className="muted">Affected doors: </span>
                        <span className="mono">{r.affected_openings.join(', ')}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {notes.length > 0 && (
        <div className="card" style={{marginTop: 12}}>
          <div className="card-header"><div className="card-title">Estimator notes</div></div>
          <div style={{padding: '8px 4px'}}>
            {notes.map((n, i) => (
              <div key={i} style={{padding: '10px 18px', borderBottom: i === notes.length - 1 ? 'none' : '1px solid var(--border)', fontSize: 13, lineHeight: 1.6, display: 'flex', gap: 12}}>
                <span style={{color: 'var(--brand-600)', fontWeight: 700, flexShrink: 0}}>·</span>
                <span>{n}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ---------- Bid Recommendations ---------- */
const BidRecommendationsScreen = ({ analysis, tweaks, onContinue }) => {
  const scope = tweaks.scope || 'Supply & Installation';

  // Compute bid recs LIVE from the extracted door + hardware data + current scope,
  // so toggling Supply Only / Installation Only / Both updates this screen without
  // re-running the pipeline. Falls back to whatever the pipeline stored if synth
  // is unavailable (defensive).
  const br = useMemo(() => {
    const stored = analysis?.bid_recommendations || {};
    try {
      const synth = synthesizeRisksAndRFIs(
        analysis?.door_analysis || [],
        analysis?.hardware_set_review || [],
        scope,
        analysis?.sheet_context || null,
      );
      // Merge: stored buckets (from LLM, if any) + synth, deduped per bucket.
      const buckets = ['supply_only_notes','installation_only_notes','supply_and_installation_notes','exclusions_to_consider','allowances_to_consider','coordination_items'];
      const merged = {};
      buckets.forEach(b => {
        const seen = new Set();
        const out = [];
        [...(Array.isArray(stored[b]) ? stored[b] : []), ...(synth.recs[b] || [])].forEach(line => {
          const k = String(line || '').toLowerCase().trim();
          if (!k || seen.has(k)) return;
          seen.add(k);
          out.push(line);
        });
        merged[b] = out;
      });
      return merged;
    } catch {
      return stored;
    }
  }, [analysis, scope]);

  const sections = [
    { key: 'supply_only_notes', label: 'Supply-only notes', icon: 'package', active: scope === 'Supply Only' || scope === 'Supply & Installation' },
    { key: 'installation_only_notes', label: 'Installation-only notes', icon: 'briefcase', active: scope === 'Installation Only' || scope === 'Supply & Installation' },
    { key: 'supply_and_installation_notes', label: 'Supply & installation', icon: 'layout-grid', active: scope === 'Supply & Installation' },
    { key: 'exclusions_to_consider', label: 'Exclusions to consider', icon: 'circle-x', active: true },
    { key: 'allowances_to_consider', label: 'Allowances to consider', icon: 'circle-dot', active: true },
    { key: 'coordination_items', label: 'Coordination items', icon: 'link', active: true },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Bid Recommendations</h1>
          <div className="page-subtitle">Scope: <strong style={{color:'var(--fg)'}}>{scope}</strong> · scope-specific notes, exclusions, allowances, and coordination</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={onContinue}>Build proposal <Icon name="arrow-right"/></Button>
        </div>
      </div>

      <CapturedDrawingNotes sheetContext={analysis?.sheet_context} />

      <div style={{display:'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12}}>
        {sections.map(s => {
          const items = br[s.key] || [];
          return (
            <div key={s.key} className="card" style={{opacity: s.active ? 1 : 0.55}}>
              <div className="card-header">
                <div className="row" style={{gap: 8}}>
                  <Icon name={s.icon} size={14} style={{color:'var(--brand-600)'}}/>
                  <div className="card-title">{s.label}</div>
                </div>
                <Badge>{items.length}</Badge>
              </div>
              <div style={{padding: 8}}>
                {items.length === 0 ? (
                  <div style={{padding: 20, textAlign: 'center', fontSize: 12}} className="muted">No items in this category.</div>
                ) : (
                  <ul style={{margin: 0, padding: '4px 18px', fontSize: 13, lineHeight: 1.6}}>
                    {items.map((it, i) => <li key={i} style={{marginBottom: 6}}>{it}</li>)}
                  </ul>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ---------- Captured drawing notes (general notes / legend / preamble / keying) ---------- */
const CapturedDrawingNotes = ({ sheetContext }) => {
  const ctx = sheetContext || {};
  const generalNotes = Array.isArray(ctx.general_notes) ? ctx.general_notes : [];
  const preamble = Array.isArray(ctx.hardware_preamble) ? ctx.hardware_preamble : [];
  const keying = Array.isArray(ctx.keying_notes) ? ctx.keying_notes : [];
  const legend = (ctx.legend && typeof ctx.legend === 'object' && !Array.isArray(ctx.legend)) ? ctx.legend : {};
  const legendEntries = Object.entries(legend);
  const total = generalNotes.length + preamble.length + keying.length + legendEntries.length;

  if (total === 0) {
    return (
      <div className="card" style={{marginBottom: 12, borderLeft: '4px solid var(--accent-amber)'}}>
        <div className="card-body" style={{display:'flex', gap: 12, alignItems:'center'}}>
          <Icon name="alert" style={{color: 'var(--accent-amber)'}}/>
          <div style={{fontSize: 13, lineHeight: 1.5}}>
            <strong>No sheet-level context captured.</strong>
            <span className="muted"> No general notes, hardware preamble, keying notes, or legend abbreviations were extracted from the drawings. The analysis below relies on the door rows + hardware sets only — manually verify any project-specific scope language before bid.</span>
          </div>
        </div>
      </div>
    );
  }

  const Section = ({ title, icon, items, mono }) => (
    items.length === 0 ? null : (
      <div style={{padding: 12, borderBottom: '1px solid var(--border)'}}>
        <div className="row" style={{gap: 8, marginBottom: 8}}>
          <Icon name={icon} size={14} style={{color: 'var(--brand-600)'}}/>
          <div style={{fontSize: 12, fontWeight: 600, letterSpacing: 0.4, textTransform: 'uppercase', color: 'var(--fg-muted, var(--fg))'}}>{title}</div>
          <Badge>{items.length}</Badge>
        </div>
        <ul style={{margin: 0, padding: '0 0 0 18px', fontSize: 13, lineHeight: 1.6}}>
          {items.map((s, i) => <li key={i} style={{marginBottom: 4, fontFamily: mono ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : 'inherit', fontSize: mono ? 12 : 13}}>{s}</li>)}
        </ul>
      </div>
    )
  );

  return (
    <div className="card" style={{marginBottom: 12}}>
      <div className="card-header">
        <div className="row" style={{gap: 8}}>
          <Icon name="file-text" size={14} style={{color: 'var(--brand-600)'}}/>
          <div className="card-title">Captured from the drawings</div>
        </div>
        <Badge>{total}</Badge>
      </div>
      <div style={{padding: 4}}>
        <Section title="General notes (door-schedule sheet)" icon="file-text" items={generalNotes} />
        <Section title="Hardware preamble" icon="package" items={preamble} />
        <Section title="Keying notes" icon="key" items={keying} />
        {legendEntries.length > 0 && (
          <div style={{padding: 12}}>
            <div className="row" style={{gap: 8, marginBottom: 8}}>
              <Icon name="library" size={14} style={{color: 'var(--brand-600)'}}/>
              <div style={{fontSize: 12, fontWeight: 600, letterSpacing: 0.4, textTransform: 'uppercase', color: 'var(--fg-muted, var(--fg))'}}>Schedule / hardware legend</div>
              <Badge>{legendEntries.length}</Badge>
            </div>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 6}}>
              {legendEntries.map(([abbrev, meaning]) => (
                <div key={abbrev} style={{display: 'flex', gap: 8, fontSize: 12, lineHeight: 1.5, padding: '6px 8px', background: 'var(--bg-sunken)', borderRadius: 4}}>
                  <span className="mono" style={{fontWeight: 700, color: 'var(--brand-600)', flexShrink: 0}}>{abbrev}</span>
                  <span style={{color: 'var(--fg)'}}>{meaning}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ---------- Extraction QA ---------- */
const ExtractionQAScreen = ({ analysis }) => {
  const qa = analysis?.qa || {};
  const validation = qa.validation || {};
  const status = analysis?.status || 'OK';
  const reason = analysis?.reason;
  const isImage = qa.pdf_type === 'IMAGE_BASED_PDF';
  const [activePage, setActivePage] = useState(null);

  const StatusBanner = () => {
    if (status === 'OK') {
      return (
        <div className="card" style={{marginBottom: 12, borderLeft: '4px solid var(--accent-green)'}}>
          <div className="card-body" style={{display:'flex', gap: 12, alignItems:'center'}}>
            <Icon name="circle-check" style={{color: 'var(--accent-green)'}}/>
            <div>
              <div style={{fontWeight: 600}}>Extraction OK</div>
              <div className="muted" style={{fontSize: 12}}>Door schedule, hardware items, and door→hardware mapping all extracted. Manually spot-check before bidding.</div>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="card" style={{marginBottom: 12, borderLeft: '4px solid var(--accent-amber)'}}>
        <div className="card-body" style={{display:'flex', gap: 12, alignItems:'flex-start'}}>
          <Icon name="alert" style={{color: 'var(--accent-amber)', marginTop: 2}}/>
          <div>
            <div style={{fontWeight: 600}}>Status: REVIEW_REQUIRED</div>
            <div className="muted" style={{fontSize: 13, marginTop: 2}}>Reason: <span className="mono" style={{color: 'var(--fg)'}}>{reason || 'unspecified'}</span></div>
            <div className="muted" style={{fontSize: 12, marginTop: 6, lineHeight: 1.5}}>
              {reason === 'IMAGE_BASED_PDF_LOW_CONFIDENCE' && 'Image-based PDF processed via vision but average confidence is below threshold. Review the page crops below and re-upload a higher-resolution source if possible.'}
              {reason === 'NO_DOORS_EXTRACTED' && 'No door schedule rows were extracted. Check that the PDF contains a door schedule and try a higher-resolution source.'}
              {reason === 'NO_HARDWARE_EXTRACTED' && 'No hardware set items were extracted. Hardware set page may be missing or unreadable.'}
              {reason === 'NO_DOOR_HARDWARE_MAPPING' && 'Doors extracted, but none have a hardware set assigned. Mapping pass failed.'}
              {reason === 'TOO_MANY_FAILED_MAPPINGS' && 'Multiple doors reference hardware sets that could not be extracted.'}
              {reason === 'LOW_CONFIDENCE' && 'Average extraction confidence is below 60%. Manual review required.'}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Extraction QA</h1>
          <div className="page-subtitle">PDF type, regions, confidence, missing fields, and mapping failures</div>
        </div>
      </div>

      <StatusBanner/>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">PDF type</div>
          <div className="stat-value" style={{fontSize: 18, color: isImage ? 'var(--accent-amber)' : 'var(--accent-green)'}}>{qa.pdf_type || 'TEXT_BASED_PDF'}</div>
          <div className="stat-delta">{qa.file_name}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Detection reason</div>
          <div className="stat-value" style={{fontSize: 14}}>{qa.detection?.reason || '—'}</div>
          {qa.detection?.metrics && (
            <div className="stat-delta mono-small">
              {qa.detection.metrics.length} chars · {qa.detection.metrics.uniqueTokens || 0} unique tokens · α={qa.detection.metrics.alphaRatio}
            </div>
          )}
        </div>
        <div className="stat-card">
          <div className="stat-label">Vision model</div>
          <div className="stat-value mono" style={{fontSize: 14}}>{qa.vision_model || '—'}</div>
          {qa.chat_model && <div className="stat-delta mono-small">chat: {qa.chat_model}</div>}
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg confidence</div>
          <div className="stat-value" style={{color: validation.avgConfidence < 0.6 ? 'var(--accent-red)' : validation.avgConfidence < 0.85 ? 'var(--accent-amber)' : 'var(--accent-green)'}}>
            {validation.avgConfidence != null ? Math.round(validation.avgConfidence * 100) + '%' : '—'}
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Pages rendered</div>
          <div className="stat-value">{qa.pages_rendered ?? 0}</div>
          {isImage && <div className="stat-delta">@ {RENDER_TARGET_DPI} DPI (capped {MAX_RENDER_LONG_EDGE}px)</div>}
        </div>
        <div className="stat-card">
          <div className="stat-label">Regions detected</div>
          <div className="stat-value">{(qa.regions_detected || []).length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Crops processed</div>
          <div className="stat-value">{qa.crops?.length || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Failed mappings</div>
          <div className="stat-value" style={{color: (validation.failedMappings?.length || 0) ? 'var(--accent-red)' : 'var(--accent-green)'}}>
            {validation.failedMappings?.length || 0}
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Door schedule</div>
          <div className="stat-value" style={{fontSize: 18, color: validation.hasDoors ? 'var(--accent-green)' : 'var(--accent-red)'}}>
            {validation.hasDoors ? 'Extracted' : 'Missing'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Hardware items</div>
          <div className="stat-value" style={{fontSize: 18, color: validation.hasHardware ? 'var(--accent-green)' : 'var(--accent-red)'}}>
            {validation.hasHardware ? 'Extracted' : 'Missing'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Door → HW mapping</div>
          <div className="stat-value" style={{fontSize: 18, color: validation.hasMapping ? 'var(--accent-green)' : 'var(--accent-red)'}}>
            {validation.hasMapping ? 'Extracted' : 'Missing'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Status</div>
          <div className="stat-value" style={{fontSize: 18, color: status === 'OK' ? 'var(--accent-green)' : 'var(--accent-amber)'}}>{status}</div>
          {reason && <div className="stat-delta mono-small">{reason}</div>}
        </div>
      </div>

      {/* Failed mappings */}
      {validation.failedMappings?.length > 0 && (
        <div className="card" style={{marginBottom: 12}}>
          <div className="card-header"><div className="card-title">Failed mappings ({validation.failedMappings.length})</div></div>
          <div style={{overflow:'auto'}}>
            <table className="table">
              <thead><tr><th>Door</th><th>Hardware set</th><th>Code</th><th>Message</th></tr></thead>
              <tbody>
                {validation.failedMappings.map((f, i) => (
                  <tr key={i}>
                    <td className="mono"><strong>{f.mark}</strong></td>
                    <td><Badge tone="blue" mono>{fmtSetId(f.set)}</Badge></td>
                    <td><Badge tone="red">{f.code}</Badge></td>
                    <td style={{fontSize: 12}}>{f.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Missing fields */}
      {validation.missingFields?.length > 0 && (
        <div className="card" style={{marginBottom: 12}}>
          <div className="card-header"><div className="card-title">Doors with missing fields ({validation.missingFields.length})</div></div>
          <div style={{overflow:'auto', maxHeight: 320}}>
            <table className="table">
              <thead><tr><th>Door</th><th>Missing fields</th></tr></thead>
              <tbody>
                {validation.missingFields.map((m, i) => (
                  <tr key={i}>
                    <td className="mono"><strong>{m.mark}</strong></td>
                    <td><ChipList items={m.fields} tone="amber"/></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Image-based: rendered pages + regions detected */}
      {isImage && qa.page_dimensions?.length > 0 && (
        <div className="card" style={{marginBottom: 12}}>
          <div className="card-header"><div className="card-title">Rendered pages ({qa.page_dimensions.length})</div></div>
          <div style={{padding: 12, display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(220px, 1fr))', gap: 12}}>
            {qa.page_dimensions.map(p => {
              const regions = (qa.regions_detected || []).filter(r => r.pageNum === p.pageNum);
              return (
                <div key={p.pageNum} style={{border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', background: 'var(--bg-sunken)'}}>
                  <div style={{position: 'relative', background: '#000'}}>
                    <img src={p.previewUrl} alt={`Page ${p.pageNum}`} style={{width: '100%', display: 'block'}}/>
                    {/* region overlays */}
                    {regions.map((r, i) => (
                      <div key={i} style={{
                        position: 'absolute',
                        left: (r.bbox[0]*100) + '%', top: (r.bbox[1]*100) + '%',
                        width: (r.bbox[2]*100) + '%', height: (r.bbox[3]*100) + '%',
                        border: '2px solid ' + regionColor(r.type),
                        background: regionColor(r.type) + '20',
                        boxSizing: 'border-box', pointerEvents: 'none',
                      }}>
                        <span style={{position:'absolute', top: -16, left: 0, fontSize: 9, padding: '1px 4px', background: regionColor(r.type), color:'#000', borderRadius: 2, fontWeight: 700, whiteSpace: 'nowrap'}}>
                          {r.type}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div style={{padding: 8, fontSize: 11}}>
                    <strong>Page {p.pageNum}</strong>
                    <div className="muted mono-small">{p.width}×{p.height}px · {p.dpi} DPI · {p.orientation}</div>
                    <div style={{marginTop: 4}}>{regions.length} region{regions.length === 1 ? '' : 's'}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Region crops with extractions */}
      {isImage && qa.crops?.length > 0 && (
        <div className="card">
          <div className="card-header"><div className="card-title">Region crops & extractions ({qa.crops.length})</div></div>
          <div style={{padding: 12, display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(280px, 1fr))', gap: 12}}>
            {qa.crops.map((c, i) => {
              // count what was actually extracted
              let yieldText = '—';
              if (c.kind === 'door_schedule') yieldText = `${c.data?.rows?.length || 0} row${c.data?.rows?.length === 1 ? '' : 's'}`;
              else if (c.kind === 'hardware_set') {
                const setN = c.data?.sets?.length || 0;
                const itemN = (c.data?.sets || []).reduce((s, x) => s + (x.items?.length || 0), 0);
                yieldText = `${setN} set${setN === 1 ? '' : 's'} / ${itemN} item${itemN === 1 ? '' : 's'}`;
              } else if (c.kind === 'notes') yieldText = `${c.data?.notes?.length || 0} note${c.data?.notes?.length === 1 ? '' : 's'}`;
              else if (c.kind === 'failed') yieldText = 'failed';
              const splitInfo = c.data?.__strip_split;
              return (
                <div key={i} style={{border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', background: 'var(--bg-raised)'}}>
                  <div style={{background: '#fff'}}>
                    <img src={c.cropPreview} alt={c.region.type} style={{width: '100%', display: 'block'}}/>
                  </div>
                  <div style={{padding: 10, fontSize: 12}}>
                    <div style={{display:'flex', gap: 6, alignItems:'center', marginBottom: 4}}>
                      <Badge mono>P{c.region.pageNum}</Badge>
                      <span style={{padding: '2px 6px', background: regionColor(c.region.type) + '22', color: 'var(--fg)', borderRadius: 4, fontSize: 10, fontWeight: 700, border: '1px solid ' + regionColor(c.region.type)}}>{c.region.type}</span>
                      <span className="muted" style={{marginLeft: 'auto', fontSize: 10}}>Conf {Math.round((c.region.confidence ?? 0.7) * 100)}%</span>
                    </div>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                      <span className="muted" style={{fontSize: 11}}>Extracted: <strong style={{color: 'var(--fg)'}}>{c.kind}</strong></span>
                      <span style={{fontSize: 11, fontWeight: 700, color: c.kind === 'failed' ? 'var(--accent-red)' : 'var(--brand-600)'}}>{yieldText}</span>
                    </div>
                    {splitInfo && <div className="mono-small" style={{marginTop: 4, color: 'var(--accent-amber)'}}>Strip-split: {splitInfo.strips} strips → {splitInfo.recovered} rows</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!isImage && (
        <div className="card">
          <div className="card-header"><div className="card-title">Direct PDF extraction</div></div>
          <div className="card-body" style={{fontSize: 13, lineHeight: 1.7}}>
            This PDF was uploaded directly to OpenAI as a single file. The model read the document end-to-end (text + visual layout) and returned the structured senior-estimator JSON — no browser-side text extraction or per-page image rendering was needed.
            <div style={{marginTop: 12, padding: 12, background: 'var(--bg-sunken)', borderRadius: 8, fontSize: 12}}>
              <strong>Extracted at:</strong> {qa.extracted_at}<br/>
              <strong>File:</strong> {qa.file_name} ({((qa.file_size || 0) / 1024).toFixed(0)} KB)<br/>
              <strong>Model:</strong> {qa.chat_model || '—'}<br/>
              <strong>Scope:</strong> {qa.scope}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function regionColor(type) {
  const map = {
    door_schedule: '#3b82f6',
    hardware_schedule: '#10b981',
    hardware_set: '#10b981',
    door_details: '#a855f7',
    frame_details: '#a855f7',
    legend: '#f59e0b',
    notes: '#f59e0b',
    other: '#94a3b8',
  };
  return map[type] || '#94a3b8';
}

/* ---------- Mapping (legacy fallback, kept for proposal flow) ---------- */
const MappingScreen = ({ doors, hardwareSets, onContinue }) => {
  const [hovered, setHovered] = useState(null);
  const setCounts = useMemo(() => {
    const m = {};
    doors.forEach(d => { if (d.hwSet) m[d.hwSet] = (m[d.hwSet] || 0) + 1; });
    return m;
  }, [doors]);
  const unmappedDoors = doors.filter(d => !d.hwSet);
  const orphanSets = Object.keys(setCounts).filter(id => !hardwareSets.find(s => s.id === id));

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Hardware Mapping</h1>
          <div className="page-subtitle">Each door linked to its hardware set. Hover to see the connection.</div>
        </div>
        <div className="row">
          <Button kind="primary" onClick={onContinue}>Generate proposal <Icon name="arrow-right"/></Button>
        </div>
      </div>

      {(unmappedDoors.length > 0 || orphanSets.length > 0) && (
        <div className="card" style={{marginBottom: 12, borderColor: 'var(--accent-amber)'}}>
          <div className="card-body" style={{display:'flex', gap: 12, alignItems:'flex-start'}}>
            <Icon name="alert" style={{color:'var(--accent-amber)', flexShrink: 0, marginTop: 2}}/>
            <div style={{fontSize: 13}}>
              {unmappedDoors.length > 0 && <div>{unmappedDoors.length} door(s) have no hardware set assigned: <span className="mono">{unmappedDoors.slice(0, 6).map(d => d.number).join(', ')}{unmappedDoors.length > 6 ? '…' : ''}</span></div>}
              {orphanSets.length > 0 && <div style={{marginTop: 4}}>Doors reference {orphanSets.length} unknown set(s): <span className="mono">{orphanSets.join(', ')}</span>. Add them to the Hardware Catalog.</div>}
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap: 0}}>
          <div style={{borderRight:'1px solid var(--border)', maxHeight: 620, overflow:'auto'}}>
            <div style={{padding:'12px 20px', background:'var(--bg-sunken)', borderBottom:'1px solid var(--border)', position:'sticky', top: 0, zIndex: 2}}>
              <strong>Doors ({doors.length})</strong>
            </div>
            {doors.map(d => (
              <div key={d.number} onMouseEnter={() => setHovered({ door: d.number, set: d.hwSet })} onMouseLeave={() => setHovered(null)}
                   style={{padding:'10px 20px', borderBottom:'1px solid var(--border)', display:'grid', gridTemplateColumns:'80px 1fr auto auto', alignItems:'center', gap: 12,
                           background: hovered?.door === d.number || (hovered?.set && hovered.set === d.hwSet) ? 'var(--brand-50)' : 'transparent', transition: 'background 120ms'}}>
                <span className="mono" style={{fontWeight:700}}>{d.number}</span>
                <div>
                  <div style={{fontSize: 13}}>{d.fromTo}</div>
                  <div className="mono-small">{[d.type, d.width && d.height && (d.width + '×' + d.height), d.faceMatl].filter(Boolean).join(' · ')}</div>
                </div>
                <Icon name="arrow-right" size={14} style={{color:'var(--fg-faint)'}}/>
                {d.hwSet ? <Badge tone="blue" mono>{fmtSetId(d.hwSet)}</Badge> : <span className="muted" style={{fontSize:11}}>unmapped</span>}
              </div>
            ))}
          </div>
          <div style={{maxHeight: 620, overflow:'auto'}}>
            <div style={{padding:'12px 20px', background:'var(--bg-sunken)', borderBottom:'1px solid var(--border)', position:'sticky', top:0, zIndex: 2}}>
              <strong>Hardware sets in use ({Object.keys(setCounts).length})</strong>
            </div>
            {Object.keys(setCounts).map(setId => {
              const s = hardwareSets.find(x => x.id === setId);
              return (
                <div key={setId} onMouseEnter={() => setHovered({ set: setId })} onMouseLeave={() => setHovered(null)}
                     style={{padding:'10px 20px', borderBottom:'1px solid var(--border)', display:'grid', gridTemplateColumns:'90px 1fr auto', alignItems:'center', gap: 12,
                             background: hovered?.set === setId ? 'var(--brand-50)' : 'transparent'}}>
                  <Badge tone="blue" mono>{fmtSetId(setId)}</Badge>
                  <div>
                    {s ? (
                      <>
                        <div style={{fontSize: 13, fontWeight: 600}}>{s.name}</div>
                        <div className="mono-small">{s.items.length} items · {setTotal(s) > 0 ? fmt0(setTotal(s)) : 'unpriced'}</div>
                      </>
                    ) : (
                      <>
                        <div style={{fontSize: 13, fontWeight: 600, color: 'var(--accent-amber)'}}>Not in catalog</div>
                        <div className="mono-small">Add this set to price it</div>
                      </>
                    )}
                  </div>
                  <Badge>{setCounts[setId]} door{setCounts[setId] > 1 ? 's' : ''}</Badge>
                </div>
              );
            })}
            {Object.keys(setCounts).length === 0 && (
              <div style={{padding: '40px 20px', textAlign:'center', color:'var(--fg-muted)', fontSize: 13}}>
                No hardware sets assigned yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

window.__fb_part3 = true;


/* ---------- Proposal: builders + templates + screen ---------- */
function buildProposalLines(doors, hardwareSets, markup) {
  const counts = {};
  doors.forEach(d => { if (d.hwSet) counts[d.hwSet] = (counts[d.hwSet] || 0) + 1; });
  const lines = [];
  Object.entries(counts).forEach(([setId, count]) => {
    const set = hardwareSets.find(s => s.id === setId);
    if (!set) {
      lines.push({ setId, name: 'Unknown set HW-' + setId, count, items: [], baseTotal: 0, unpriced: true });
      return;
    }
    lines.push({ setId, name: set.name, count, items: set.items, baseTotal: setTotal(set), unpriced: setTotal(set) === 0 });
  });
  const subtotal = lines.reduce((s, l) => s + l.count * l.baseTotal, 0);
  const labor = doors.length * 85;
  const markupAmt = subtotal * (markup / 100);
  return { lines, subtotal, labor, markupAmt, total: subtotal + markupAmt + labor };
}

const ProposalScreen = ({ doors, hardwareSets, project, tweaks, onContinue, onSaveProposal }) => {
  const totals = buildProposalLines(doors, hardwareSets, tweaks.markup);
  const [view, setView] = useState('preview');

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Proposal</h1>
          <div className="page-subtitle">{doors.length} doors · {totals.lines.length} hardware sets · {tweaks.template} template</div>
        </div>
        <div className="row">
          <Button onClick={() => window.print()}><Icon name="print"/> Print</Button>
          <Button kind="primary" onClick={onContinue}>Export &amp; send <Icon name="arrow-right"/></Button>
        </div>
      </div>

      {totals.lines.some(l => l.unpriced) && (
        <div className="card" style={{marginBottom: 12, borderColor: 'var(--accent-amber)'}}>
          <div className="card-body" style={{display:'flex', gap: 12, alignItems:'center'}}>
            <Icon name="alert" style={{color: 'var(--accent-amber)'}}/>
            <div style={{flex: 1, fontSize: 13}}>
              {totals.lines.filter(l => l.unpriced).length} hardware set(s) have no prices yet — they appear at $0. Add unit prices in Hardware Catalog.
            </div>
          </div>
        </div>
      )}

      <div className="tabs">
        <button className={'tab' + (view==='preview'?' active':'')} onClick={()=>setView('preview')}>Proposal preview</button>
        <button className={'tab' + (view==='table'?' active':'')} onClick={()=>setView('table')}>Interactive table</button>
        <button className={'tab' + (view==='formal'?' active':'')} onClick={()=>setView('formal')}>Formal CSI bid</button>
      </div>

      {view === 'preview' && <ProposalDocument doors={doors} totals={totals} tweaks={tweaks} project={project}/>}
      {view === 'table' && <ProposalTable totals={totals}/>}
      {view === 'formal' && <FormalBidView doors={doors} totals={totals} tweaks={tweaks} project={project}/>}
    </div>
  );
};

const ProposalDocument = ({ doors, totals, tweaks, project }) => {
  const today = new Date().toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric'});
  const bid = project.proposalId;
  const tmpl = tweaks.template || 'Classic';
  const accent = tweaks.brand500 || '#2f68f5';
  const accentDark = tweaks.brand700 || '#153eb0';

  if (tmpl === 'Minimal') return <MinimalDoc {...{today, bid, accent, accentDark, totals, tweaks, project, doors}}/>;
  if (tmpl === 'Modern') return <ModernDoc {...{today, bid, accent, accentDark, totals, tweaks, project, doors}}/>;
  return <ClassicDoc {...{today, bid, accent, accentDark, totals, tweaks, project, doors}}/>;
};

const ClassicDoc = ({ today, bid, accent, accentDark, totals, tweaks, project, doors }) => (
  <div className="proposal-page">
    <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom: 32, paddingBottom: 16, borderBottom: '2px solid ' + accent}}>
      <div>
        <div style={{display:'flex', alignItems:'center', gap: 10, marginBottom: 12}}>
          <div style={{width: 32, height: 32, borderRadius: 6, background: accent, color:'white', display:'grid', placeItems:'center'}}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h20"/><path d="M13 20V4a1 1 0 0 0-.5-.86l-5-2.5A1 1 0 0 0 6 1.5V20"/></svg>
          </div>
          <strong style={{fontSize: 14}}>{tweaks.companyName || 'FastBid24 Hardware Co.'}</strong>
        </div>
        <div style={{fontSize: 11, color:'#444', lineHeight: 1.6}}>quotes@fastbid24.co</div>
      </div>
      <div style={{textAlign:'right'}}>
        <div style={{fontSize: 22, fontWeight: 700, color: accentDark}}>HARDWARE PROPOSAL</div>
        <div style={{fontSize: 11, color:'#444', marginTop: 4}}>Proposal #: <strong>{bid}</strong></div>
        <div style={{fontSize: 11, color:'#444'}}>Date: {today}</div>
        <div style={{fontSize: 11, color:'#444'}}>Valid: 30 days</div>
      </div>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap: 24, marginBottom: 32}}>
      <div>
        <div style={{fontSize: 10, textTransform:'uppercase', letterSpacing: 1, color:'#666', marginBottom: 4}}>Project</div>
        <div style={{fontSize: 13, fontWeight: 600}}>{project.name || 'Untitled Project'}</div>
        {project.address && <div style={{fontSize: 11, color:'#444'}}>{project.address}</div>}
        {project.drawing && <div style={{fontSize: 11, color:'#444'}}>Ref: {project.drawing}</div>}
      </div>
      <div>
        <div style={{fontSize: 10, textTransform:'uppercase', letterSpacing: 1, color:'#666', marginBottom: 4}}>To</div>
        <div style={{fontSize: 13, fontWeight: 600}}>{project.architect || '—'}</div>
        {project.number && <div style={{fontSize: 11, color:'#444'}}>Project #: {project.number}</div>}
      </div>
    </div>

    <div style={{marginBottom: 20, padding: 12, background:'#f8fafc', borderLeft:'3px solid ' + accent, fontSize: 11, lineHeight: 1.6}}>
      We are pleased to quote the following door hardware per the project schedule.
      Quote covers {doors.length} openings across {totals.lines.length} hardware sets.
      All materials new, factory-finished, manufacturer-warranted.
    </div>

    <table style={{width:'100%', borderCollapse:'collapse', fontSize: 11}}>
      <thead>
        <tr style={{background: accent, color:'white'}}>
          <th style={{padding:'8px 10px', textAlign:'left'}}>HW Set</th>
          <th style={{padding:'8px 10px', textAlign:'left'}}>Description</th>
          <th style={{padding:'8px 10px', textAlign:'right', width:60}}>Qty</th>
          <th style={{padding:'8px 10px', textAlign:'right', width:90}}>Unit</th>
          <th style={{padding:'8px 10px', textAlign:'right', width:100}}>Extended</th>
        </tr>
      </thead>
      <tbody>
        {totals.lines.map(l => (
          <tr key={l.setId} style={{borderBottom:'1px solid #e2e8f0'}}>
            <td style={{padding:'10px', fontFamily:'JetBrains Mono, monospace', verticalAlign:'top'}}>HW-{l.setId}</td>
            <td style={{padding:'10px', verticalAlign:'top'}}>
              <strong>{l.name}</strong>
              {l.items.length > 0 && (
                <div style={{fontSize: 10, color: '#666', marginTop: 4}}>
                  {l.items.slice(0,3).map(i => i.desc).join(' · ')}{l.items.length > 3 ? ` · +${l.items.length - 3} more` : ''}
                </div>
              )}
            </td>
            <td style={{padding:'10px', textAlign:'right', verticalAlign:'top'}}>{l.count}</td>
            <td style={{padding:'10px', textAlign:'right', verticalAlign:'top', fontFamily:'JetBrains Mono, monospace'}}>{l.baseTotal > 0 ? fmt(l.baseTotal) : '—'}</td>
            <td style={{padding:'10px', textAlign:'right', verticalAlign:'top', fontFamily:'JetBrains Mono, monospace', fontWeight: 600}}>{fmt(l.count * l.baseTotal)}</td>
          </tr>
        ))}
      </tbody>
    </table>

    <table style={{width:'100%', marginTop:16, fontSize:11}}>
      <tbody>
        <tr><td style={{padding:'4px 10px', textAlign:'right', color:'#444'}}>Subtotal</td><td style={{padding:'4px 10px', textAlign:'right', width: 100, fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.subtotal)}</td></tr>
        <tr><td style={{padding:'4px 10px', textAlign:'right', color:'#444'}}>Markup ({tweaks.markup}%)</td><td style={{padding:'4px 10px', textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.markupAmt)}</td></tr>
        <tr><td style={{padding:'4px 10px', textAlign:'right', color:'#444'}}>Installation coordination</td><td style={{padding:'4px 10px', textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.labor)}</td></tr>
        <tr style={{borderTop: '2px solid ' + accent}}><td style={{padding:10, textAlign:'right', fontWeight:700, fontSize:14}}>TOTAL</td><td style={{padding:10, textAlign:'right', fontWeight:700, fontFamily:'JetBrains Mono, monospace', color: accent, fontSize:14}}>{fmt(totals.total)}</td></tr>
      </tbody>
    </table>

    <div style={{marginTop: 32, paddingTop: 20, borderTop: '1px solid #e2e8f0', fontSize: 10, color:'#666', lineHeight: 1.6}}>
      <strong style={{color:'#0b1220'}}>Terms &amp; Conditions</strong><br/>
      Prices firm for 30 days. Net 30 payment. Lead time 6–8 weeks from approved submittal. Installation by others unless noted.
    </div>
  </div>
);

const ModernDoc = ({ today, bid, accent, accentDark, totals, tweaks, project, doors }) => (
  <div className="proposal-page" style={{padding: 0, overflow:'hidden'}}>
    <div style={{background: `linear-gradient(135deg, ${accentDark}, ${accent})`, color:'white', padding: '48px 64px 40px'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
        <div>
          <div style={{fontSize: 11, textTransform:'uppercase', letterSpacing: 2, opacity: 0.7}}>Hardware Proposal · {bid}</div>
          <div style={{fontSize: 36, fontWeight: 700, marginTop: 12, letterSpacing: -1}}>{project.name || 'Project'}</div>
          {project.address && <div style={{opacity: 0.85, marginTop: 4, fontSize: 13}}>{project.address}</div>}
        </div>
        <div style={{textAlign:'right'}}>
          <div style={{marginTop: 12, fontWeight: 600}}>{tweaks.companyName}</div>
          <div style={{fontSize: 11, opacity: 0.8}}>{today}</div>
        </div>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap: 16, marginTop: 36, paddingTop: 24, borderTop:'1px solid rgba(255,255,255,0.15)'}}>
        {[['Doors', doors.length],['HW Sets', totals.lines.length],['Subtotal', fmt0(totals.subtotal)],['Total', fmt0(totals.total)]].map(([l,v]) => (
          <div key={l}>
            <div style={{fontSize: 10, textTransform:'uppercase', letterSpacing: 1.5, opacity: 0.7}}>{l}</div>
            <div style={{fontSize: 20, fontWeight: 700, marginTop: 4}}>{v}</div>
          </div>
        ))}
      </div>
    </div>
    <div style={{padding: '32px 64px'}}>
      <div style={{fontSize: 11, textTransform:'uppercase', letterSpacing: 1.5, color:'#64748b', marginBottom: 12, fontWeight: 600}}>Hardware sets</div>
      {totals.lines.map(l => (
        <div key={l.setId} style={{display:'grid', gridTemplateColumns:'80px 1fr auto', gap: 16, padding:'14px 0', borderBottom:'1px solid #f1f5f9', alignItems:'center'}}>
          <div><span style={{padding:'2px 8px', background: accent, color:'white', borderRadius: 4, fontSize: 10, fontWeight: 700, fontFamily:'JetBrains Mono, monospace'}}>HW-{l.setId}</span></div>
          <div>
            <div style={{fontWeight: 600}}>{l.name}</div>
            <div style={{fontSize: 10, color:'#64748b', marginTop: 2}}>{l.count} × set · {l.items.length} items</div>
          </div>
          <div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace', fontWeight: 700}}>{fmt(l.count * l.baseTotal)}</div>
        </div>
      ))}
      <div style={{marginTop: 24, padding: 20, background: '#f8fafc', borderRadius: 8, display:'grid', gridTemplateColumns:'1fr auto', gap: 4, fontSize: 12}}>
        <div>Subtotal</div><div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.subtotal)}</div>
        <div>Markup ({tweaks.markup}%)</div><div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.markupAmt)}</div>
        <div>Installation coordination</div><div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.labor)}</div>
        <div style={{fontWeight:700, fontSize:16, marginTop: 8, paddingTop: 8, borderTop:'1px solid #e2e8f0'}}>Total</div>
        <div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace', fontWeight: 700, fontSize:16, color: accent, marginTop: 8, paddingTop: 8, borderTop:'1px solid #e2e8f0'}}>{fmt(totals.total)}</div>
      </div>
    </div>
  </div>
);

const MinimalDoc = ({ today, bid, totals, tweaks, project }) => (
  <div className="proposal-page">
    <div style={{borderBottom: '1px solid #111', paddingBottom: 16, marginBottom: 32, display:'flex', justifyContent:'space-between', alignItems:'flex-end'}}>
      <div>
        <div style={{fontSize: 10, textTransform:'uppercase', letterSpacing: 2, color:'#666'}}>Proposal {bid}</div>
        <div style={{fontSize: 28, fontWeight: 300, marginTop: 8, letterSpacing:-1}}>{project.name || 'Project'}</div>
      </div>
      <div style={{fontSize: 11, textAlign:'right', color:'#444'}}>
        <div style={{fontWeight: 600}}>{tweaks.companyName}</div>
        <div>{today}</div>
      </div>
    </div>
    {totals.lines.map(l => (
      <div key={l.setId} style={{display:'grid', gridTemplateColumns:'60px 1fr 40px 100px', gap: 12, padding:'10px 0', borderBottom:'1px solid #e2e8f0', fontSize: 12, alignItems:'center'}}>
        <div style={{fontFamily:'JetBrains Mono, monospace', color:'#666'}}>HW-{l.setId}</div>
        <div>{l.name}</div>
        <div style={{textAlign:'right'}}>×{l.count}</div>
        <div style={{textAlign:'right', fontFamily:'JetBrains Mono, monospace'}}>{fmt(l.count * l.baseTotal)}</div>
      </div>
    ))}
    <div style={{marginTop: 24, paddingTop: 16, borderTop: '1px solid #111', fontSize: 12}}>
      <div style={{display:'grid', gridTemplateColumns:'1fr 100px', gap: 8}}>
        <div style={{textAlign:'right', color:'#666'}}>Subtotal</div><div style={{textAlign:'right', fontFamily:'mono'}}>{fmt(totals.subtotal)}</div>
        <div style={{textAlign:'right', color:'#666'}}>Markup {tweaks.markup}%</div><div style={{textAlign:'right'}}>{fmt(totals.markupAmt)}</div>
        <div style={{textAlign:'right', color:'#666'}}>Installation</div><div style={{textAlign:'right'}}>{fmt(totals.labor)}</div>
        <div style={{textAlign:'right', fontWeight: 700, fontSize: 14, marginTop: 8}}>Total</div>
        <div style={{textAlign:'right', fontWeight: 700, fontSize: 14, marginTop: 8, fontFamily:'JetBrains Mono, monospace'}}>{fmt(totals.total)}</div>
      </div>
    </div>
  </div>
);

const ProposalTable = ({ totals }) => (
  <div className="card">
    <div className="card-header">
      <div className="card-title">All line items by hardware set</div>
    </div>
    <div style={{overflow:'auto', maxHeight: 600}}>
      <table className="table">
        <thead>
          <tr>
            <th>Set</th><th>Part #</th><th>Description</th><th>Mfr</th><th>Finish</th>
            <th style={{textAlign:'right'}}>Qty/Set</th><th>×Sets</th>
            <th style={{textAlign:'right'}}>Total Qty</th><th style={{textAlign:'right'}}>Unit</th><th style={{textAlign:'right'}}>Extended</th>
          </tr>
        </thead>
        <tbody>
          {totals.lines.flatMap(l => l.items.map((it, i) => (
            <tr key={l.setId + '-' + i}>
              <td><Badge tone="blue" mono>HW-{l.setId}</Badge></td>
              <td className="mono">{it.part || '—'}</td>
              <td>{it.desc}</td>
              <td>{it.mfr || '—'}</td>
              <td>{it.finish && <Badge>{it.finish}</Badge>}</td>
              <td className="mono" style={{textAlign:'right'}}>{it.qty}</td>
              <td className="mono">×{l.count}</td>
              <td className="mono" style={{textAlign:'right'}}>{it.qty * l.count}</td>
              <td className="mono" style={{textAlign:'right'}}>{it.unitPrice ? fmt(it.unitPrice) : '—'}</td>
              <td className="mono" style={{textAlign:'right', fontWeight: 600}}>{it.unitPrice ? fmt(it.qty * it.unitPrice * l.count) : '—'}</td>
            </tr>
          )))}
          {totals.lines.length === 0 && (
            <tr><td colSpan="10"><EmptyState icon="package" title="No line items" body="Assign hardware sets to your doors first."/></td></tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);

const FormalBidView = ({ doors, totals, tweaks, project }) => (
  <div className="card">
    <div className="card-body" style={{maxWidth: 820, margin:'0 auto'}}>
      <div style={{fontSize: 10, textTransform:'uppercase', letterSpacing: 2, color:'var(--fg-muted)', marginBottom: 4}}>CSI Division 08 71 00</div>
      <h2 style={{margin:0, marginBottom: 20}}>Door Hardware — Bid Schedule</h2>
      <div style={{padding: 16, background:'var(--bg-sunken)', borderRadius: 8, marginBottom: 24, fontSize: 13}}>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap: 12}}>
          <div><strong>Project:</strong> {project.name}</div>
          {project.drawing && <div><strong>Ref:</strong> {project.drawing}</div>}
          {project.architect && <div><strong>Architect:</strong> {project.architect}</div>}
          <div><strong>Date:</strong> {new Date().toLocaleDateString()}</div>
        </div>
      </div>
      {totals.lines.map(l => (
        <div key={l.setId} style={{marginBottom: 24}}>
          <div style={{padding:'8px 12px', background:'var(--brand-50)', borderLeft:'3px solid var(--brand-600)', fontSize: 13, fontWeight: 600}}>
            HW-{l.setId} — {l.name} <span style={{float:'right', fontWeight: 500}}>{l.count} opening{l.count>1?'s':''}</span>
          </div>
          <table className="table" style={{marginTop: 4}}>
            <thead><tr><th style={{width:50}}>Qty</th><th>Description</th><th>Part #</th><th>Mfr</th><th>Finish</th></tr></thead>
            <tbody>
              {l.items.map((it, i) => (
                <tr key={i}>
                  <td className="mono">{it.qty}</td><td>{it.desc}</td>
                  <td className="mono">{it.part || '—'}</td><td>{it.mfr || '—'}</td>
                  <td>{it.finish && <Badge>{it.finish}</Badge>}</td>
                </tr>
              ))}
              {l.items.length === 0 && <tr><td colSpan="5" className="muted" style={{padding:12, fontStyle:'italic'}}>No items in this set</td></tr>}
            </tbody>
          </table>
          <div style={{padding:'6px 12px', background:'var(--bg-sunken)', fontSize: 12, display:'flex', justifyContent:'space-between'}}>
            <span className="muted">Openings: <span className="mono">{doors.filter(d => d.hwSet === l.setId).map(d => d.number).join(', ')}</span></span>
            <span className="mono" style={{fontWeight: 600}}>{l.baseTotal > 0 ? `${fmt(l.baseTotal)} × ${l.count} = ${fmt(l.baseTotal * l.count)}` : 'Unpriced'}</span>
          </div>
        </div>
      ))}
      <div style={{borderTop: '2px solid var(--fg)', marginTop: 20, paddingTop: 16}}>
        <table style={{width:'100%', fontSize: 13}}>
          <tbody>
            <tr><td>Materials subtotal</td><td style={{textAlign:'right'}} className="mono">{fmt(totals.subtotal)}</td></tr>
            <tr><td>Markup ({tweaks.markup}%)</td><td style={{textAlign:'right'}} className="mono">{fmt(totals.markupAmt)}</td></tr>
            <tr><td>Installation coordination</td><td style={{textAlign:'right'}} className="mono">{fmt(totals.labor)}</td></tr>
            <tr style={{borderTop:'1px solid var(--border)'}}>
              <td style={{fontSize:16, fontWeight:700, paddingTop:10}}>BID TOTAL</td>
              <td style={{textAlign:'right', fontSize:16, fontWeight:700, paddingTop:10, color:'var(--brand-700)'}} className="mono">{fmt(totals.total)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

/* ---------- Export ---------- */
const ExportScreen = ({ doors, hardwareSets, project, tweaks, onFinish, onSave }) => {
  const totals = buildProposalLines(doors, hardwareSets, tweaks.markup);
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({
    to: project.contactEmail || '',
    cc: '',
    subject: `Hardware Proposal — ${project.name || 'Project'} (${project.proposalId})`,
    body: `Hi,\n\nPlease find attached our hardware proposal for ${project.name || 'this project'}. We've priced ${doors.length} openings across ${totals.lines.length} hardware sets.\n\nHappy to walk through any questions.\n\nBest,\n${tweaks.companyName}`,
  });

  const exportCsv = () => {
    const rows = [['Set', 'Part #', 'Description', 'Mfr', 'Finish', 'Qty/Set', '×Sets', 'Total Qty', 'Unit', 'Extended']];
    totals.lines.forEach(l => l.items.forEach(it => {
      rows.push(['HW-' + l.setId, it.part || '', it.desc || '', it.mfr || '', it.finish || '',
                 it.qty, l.count, it.qty * l.count, it.unitPrice ?? '', (it.unitPrice ?? 0) * it.qty * l.count]);
    }));
    const csv = rows.map(r => r.map(c => /[,"\n]/.test(String(c)) ? `"${String(c).replace(/"/g, '""')}"` : c).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = (project.proposalId || 'proposal') + '.csv'; a.click();
  };
  const copyToClipboard = async () => {
    const lines = [];
    totals.lines.forEach(l => { lines.push(`HW-${l.setId}\t${l.name}\t${l.count}\t${l.baseTotal * l.count}`); });
    await navigator.clipboard.writeText(lines.join('\n'));
    alert('Copied to clipboard');
  };

  if (sent) {
    return (
      <div className="fade-in" style={{maxWidth: 560, margin: '80px auto', textAlign:'center'}}>
        <div style={{width: 72, height: 72, borderRadius: 20, background:'var(--accent-green-light)', color:'var(--accent-green)', display:'grid', placeItems:'center', margin: '0 auto 20px'}}>
          <Icon name="check" size={36}/>
        </div>
        <h2 style={{margin:0}}>Proposal sent</h2>
        <p className="muted">{project.proposalId} delivered to {form.to}.</p>
        <div className="row" style={{justifyContent:'center', marginTop: 24}}>
          <Button onClick={onFinish}><Icon name="home"/> Back to dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{maxWidth: 860, margin: '0 auto'}}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Export &amp; Send</h1>
          <div className="page-subtitle">Deliver the proposal — {fmt0(totals.total)} total for {doors.length} doors</div>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap: 16, marginBottom: 16}}>
        <div className="card" style={{padding: 16, display:'flex', gap: 12, alignItems:'center', cursor:'pointer'}} onClick={() => window.print()}>
          <div style={{width:40, height:40, borderRadius:8, background:'var(--brand-50)', color:'var(--brand-600)', display:'grid', placeItems:'center'}}><Icon name="print"/></div>
          <div style={{flex:1}}><div style={{fontWeight:600}}>Print / Save as PDF</div><div className="muted" style={{fontSize:12}}>Branded proposal document</div></div>
        </div>
        <div className="card" style={{padding: 16, display:'flex', gap: 12, alignItems:'center', cursor:'pointer'}} onClick={exportCsv}>
          <div style={{width:40, height:40, borderRadius:8, background:'var(--brand-50)', color:'var(--brand-600)', display:'grid', placeItems:'center'}}><Icon name="layout-grid"/></div>
          <div style={{flex:1}}><div style={{fontWeight:600}}>Export CSV</div><div className="muted" style={{fontSize:12}}>Line items for takeoffs</div></div>
        </div>
        <div className="card" style={{padding: 16, display:'flex', gap: 12, alignItems:'center', cursor:'pointer'}} onClick={copyToClipboard}>
          <div style={{width:40, height:40, borderRadius:8, background:'var(--brand-50)', color:'var(--brand-600)', display:'grid', placeItems:'center'}}><Icon name="copy"/></div>
          <div style={{flex:1}}><div style={{fontWeight:600}}>Copy to clipboard</div><div className="muted" style={{fontSize:12}}>Tab-separated bid summary</div></div>
        </div>
        <div className="card" style={{padding: 16, display:'flex', gap: 12, alignItems:'center'}}>
          <div style={{width:40, height:40, borderRadius:8, background:'var(--brand-50)', color:'var(--brand-600)', display:'grid', placeItems:'center'}}><Icon name="mail"/></div>
          <div style={{flex:1}}><div style={{fontWeight:600}}>Send via email</div><div className="muted" style={{fontSize:12}}>Use the composer below</div></div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><div className="card-title">Email composer</div></div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap: 12}}>
          <div><label className="tweak-label">To</label><input className="input" value={form.to} onChange={e => setForm({...form, to: e.target.value})}/></div>
          <div><label className="tweak-label">CC</label><input className="input" value={form.cc} onChange={e => setForm({...form, cc: e.target.value})}/></div>
          <div><label className="tweak-label">Subject</label><input className="input" value={form.subject} onChange={e => setForm({...form, subject: e.target.value})}/></div>
          <div><label className="tweak-label">Message</label><textarea className="input" rows="7" value={form.body} onChange={e => setForm({...form, body: e.target.value})}/></div>
          <div className="row" style={{justifyContent:'flex-end', marginTop: 6}}>
            <span className="muted" style={{fontSize: 12, marginRight:'auto'}}><Icon name="file-check" size={12}/> Attaching: {project.proposalId}.pdf</span>
            <Button onClick={() => onSave('Draft')}>Save draft</Button>
            <Button kind="primary" onClick={() => { onSave('Sent'); setSent(true); }}><Icon name="send"/> Send proposal</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

window.__fb_part4 = true;


/* ====================================================================
   App — router + state
   ==================================================================== */

const DEFAULT_TWEAKS = /*EDITMODE-BEGIN*/{
  "theme": "dark",
  "brandName": "Steel",
  "brand500": "#64748b",
  "brand600": "#475569",
  "brand400": "#94a3b8",
  "brand700": "#334155",
  "companyName": "FastBid24 Hardware Co.",
  "markup": 20,
  "template": "Modern",
  "apiKey": "",
  "model": "gpt-5.5",
  "visionModel": "",
  "forceVision": false,
  "tileMode": false,
  "scope": "Supply & Installation"
}/*EDITMODE-END*/;

function nextProposalId(existing) {
  const year = new Date().getFullYear();
  const nums = existing.filter(p => p.id?.startsWith('P-' + year)).map(p => Number(p.id.split('-')[2]) || 0);
  const next = (Math.max(0, ...nums) + 1).toString().padStart(3, '0');
  return `P-${year}-${next}`;
}

function App() {
  const [tweaks, setTweaks] = useLocal('fb24-tweaks', DEFAULT_TWEAKS);
  const [tweaksOpen, setTweaksOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [route, setRoute] = useLocal('fb24-route', 'dashboard');
  const [analysis, setAnalysis] = useLocal('fb24-analysis', null);
  const [doors, setDoors] = useLocal('fb24-doors', []);
  const [hardwareSets, setHardwareSets] = useLocal('fb24-hardware-sets', []);
  const [proposals, setProposals] = useLocal('fb24-proposals', []);
  const [project, setProject] = useLocal('fb24-project', { name: '', proposalId: '' });
  const [uploadFile, setUploadFile] = useState(null);

  // Apply theme + brand colors
  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
    const r = document.documentElement;
    if (tweaks.brand500) r.style.setProperty('--brand-500', tweaks.brand500);
    if (tweaks.brand600) r.style.setProperty('--brand-600', tweaks.brand600);
    if (tweaks.brand400) r.style.setProperty('--brand-400', tweaks.brand400);
    if (tweaks.brand700) r.style.setProperty('--brand-700', tweaks.brand700);
  }, [tweaks]);

  // Tweaks panel protocol
  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === '__activate_edit_mode') setTweaksOpen(true);
      if (e.data?.type === '__deactivate_edit_mode') setTweaksOpen(false);
    };
    window.addEventListener('message', handler);
    try { window.parent.postMessage({ type: '__edit_mode_available' }, '*'); } catch {}
    return () => window.removeEventListener('message', handler);
  }, []);

  const toggleTheme = () => setTweaks(t => ({ ...t, theme: t.theme === 'dark' ? 'light' : 'dark' }));

  const onStartParse = (file) => { setUploadFile(file); setRoute('parsing'); };

  const onParseDone = async (result) => {
    // result is the senior-estimator analysis JSON
    const ps = result.project_summary || {};
    const newProject = {
      name: ps.project_name || '',
      number: ps.project_number || '',
      address: ps.address || '',
      architect: ps.architect || '',
      drawing: ps.drawing || '',
      date: ps.date || '',
      proposalId: nextProposalId(proposals),
      createdAt: new Date().toISOString(),
    };
    setProject(newProject);
    setAnalysis(result);

    // map analysis → legacy structures so the existing proposal/export flow still works
    const { doors: legacyDoors, hardwareSets: legacyHardware } = analysisToLegacy(result);
    setDoors(legacyDoors);
    const existing = new Map(hardwareSets.map(s => [s.id, s]));
    legacyHardware.forEach(s => { if (!existing.has(s.id)) existing.set(s.id, s); });
    setHardwareSets([...existing.values()]);

    // save draft proposal index
    const draft = {
      id: newProject.proposalId,
      project: newProject.name || 'Untitled',
      address: newProject.address || '',
      client: newProject.architect || '',
      doors: legacyDoors.length,
      total: 0,
      status: 'Draft',
      scope: ps.scope_type || tweaks.scope,
      risk: ps.overall_bid_risk || '—',
      extractionStatus: result.status || 'OK',
      pdfType: result.qa?.pdf_type || 'TEXT_BASED_PDF',
      date: new Date().toISOString().slice(0, 10),
      createdAt: newProject.createdAt,
    };
    setProposals(prev => [draft, ...prev.filter(p => p.id !== draft.id)]);

    // Persist FULL analysis to IndexedDB for long-term history
    try {
      await dbPut({
        id: newProject.proposalId,
        createdAt: newProject.createdAt,
        project: newProject,
        analysis: result,
        tweaksSnapshot: { scope: tweaks.scope, model: tweaks.model, visionModel: tweaks.visionModel },
      });
    } catch (e) {
      console.warn('IndexedDB save failed:', e);
    }

    setRoute('summary');
  };

  const onSaveProposalStatus = (status) => {
    const totals = buildProposalLines(doors, hardwareSets, tweaks.markup);
    setProposals(prev => prev.map(p => p.id === project.proposalId ? { ...p, status, total: totals.total, doors: doors.length } : p));
  };

  // Hydrate dashboard from IndexedDB on mount (so history survives even if localStorage was cleared)
  useEffect(() => {
    (async () => {
      try {
        const records = await dbList();
        if (!records.length) return;
        setProposals(prev => {
          const byId = new Map(prev.map(p => [p.id, p]));
          records.forEach(r => {
            const ps = r.analysis?.project_summary || {};
            const summary = {
              id: r.id,
              project: r.project?.name || ps.project_name || 'Untitled',
              address: r.project?.address || ps.address || '',
              client: r.project?.architect || ps.architect || '',
              doors: r.analysis?.door_analysis?.length || 0,
              total: 0,
              status: byId.get(r.id)?.status || 'Draft',
              scope: ps.scope_type || r.tweaksSnapshot?.scope || '',
              risk: ps.overall_bid_risk || '—',
              extractionStatus: r.analysis?.status || 'OK',
              pdfType: r.analysis?.qa?.pdf_type || 'TEXT_BASED_PDF',
              date: (r.createdAt || '').slice(0, 10),
              createdAt: r.createdAt,
            };
            byId.set(r.id, { ...byId.get(r.id), ...summary });
          });
          return [...byId.values()].sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
        });
      } catch (e) {
        console.warn('Dashboard hydrate failed:', e);
      }
    })();
  }, []);

  const onOpenProposal = async (p) => {
    try {
      const record = await dbGet(p.id);
      if (!record) { alert('This analysis was not found in the local database. It may have been created before history was enabled.'); return; }
      setProject(record.project || { proposalId: p.id });
      setAnalysis(record.analysis || null);
      // restore legacy doors/sets so proposal/export screens work
      if (record.analysis) {
        const { doors: legacyDoors, hardwareSets: legacyHardware } = analysisToLegacy(record.analysis);
        setDoors(legacyDoors);
        setHardwareSets(legacyHardware);
      }
      setRoute('summary');
    } catch (e) {
      alert('Failed to open analysis: ' + e.message);
    }
  };

  const onDeleteProposal = async (id) => {
    setProposals(prev => prev.filter(p => p.id !== id));
    try { await dbDelete(id); } catch (e) { console.warn('IndexedDB delete failed:', e); }
  };

  const onExportProposalExcel = async (p) => {
    try {
      const record = await dbGet(p.id);
      if (!record) { alert('Analysis data not found in local database.'); return; }
      exportAnalysisToExcel({ analysis: record.analysis, project: record.project || { proposalId: p.id }, tweaks });
    } catch (e) {
      alert('Excel export failed: ' + e.message);
    }
  };

  const onExportProposalComsenseCsv = async (p) => {
    try {
      const record = await dbGet(p.id);
      if (!record) { alert('Analysis data not found in local database.'); return; }
      exportAnalysisToComsenseCSV({ analysis: record.analysis, project: record.project || { proposalId: p.id }, tweaks });
    } catch (e) {
      alert('Comsense CSV export failed: ' + e.message);
    }
  };

  const hasProject = !!doors.length || !!project?.name || !!analysis;

  const crumbMap = {
    dashboard: ['FastBid24', 'Dashboard'],
    upload: ['FastBid24', 'New Analysis', 'Upload'],
    parsing: ['FastBid24', 'New Analysis', 'Analyzing'],
    summary: ['FastBid24', project.name || 'Project', 'Summary'],
    doors: ['FastBid24', project.name || 'Project', 'Door Analysis'],
    mapping: ['FastBid24', project.name || 'Project', 'Hardware Review'],
    risks: ['FastBid24', project.name || 'Project', 'Risks & RFIs'],
    bidrecs: ['FastBid24', project.name || 'Project', 'Bid Recommendations'],
    qa: ['FastBid24', project.name || 'Project', 'Extraction QA'],
    proposal: ['FastBid24', project.name || 'Project', 'Proposal'],
    export: ['FastBid24', project.name || 'Project', 'Export & Send'],
    catalog: ['FastBid24', 'Hardware Catalog'],
    settings: ['FastBid24', 'Settings'],
  };

  const currentSetIds = new Set(doors.map(d => d.hwSet).filter(Boolean));

  return (
    <div className="app">
      <Sidebar route={route} setRoute={setRoute} companyName={tweaks.companyName} hasProject={hasProject} projectName={project.name}/>
      <div className="main">
        <Topbar crumbs={crumbMap[route] || []} theme={tweaks.theme} onToggleTheme={toggleTheme} onOpenSettings={() => setSettingsOpen(true)} hasApiKey={!!tweaks.apiKey}/>
        <div className="content">
          {route === 'dashboard' && <Dashboard proposals={proposals} setRoute={setRoute} onOpen={onOpenProposal} onDelete={onDeleteProposal} onExportExcel={onExportProposalExcel} onExportComsenseCsv={onExportProposalComsenseCsv}/>}
          {route === 'upload' && <UploadScreen onStartParse={onStartParse} hasApiKey={!!tweaks.apiKey} onOpenSettings={() => setSettingsOpen(true)} tweaks={tweaks} setTweaks={setTweaks}/>}
          {route === 'parsing' && <ParsingScreen file={uploadFile} tweaks={tweaks} onDone={onParseDone} onCancel={() => setRoute('upload')}/>}
          {route === 'summary' && (analysis ? <SummaryScreen analysis={analysis} project={project} tweaks={tweaks} setRoute={setRoute}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'doors' && (analysis ? <DoorAnalysisScreen analysis={analysis} setAnalysis={setAnalysis} onContinue={() => setRoute('mapping')}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'mapping' && (analysis ? <HardwareReviewScreen analysis={analysis} onContinue={() => setRoute('risks')}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'risks' && (analysis ? <RisksScreen analysis={analysis} tweaks={tweaks} onContinue={() => setRoute('bidrecs')}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'bidrecs' && (analysis ? <BidRecommendationsScreen analysis={analysis} tweaks={tweaks} onContinue={() => setRoute('proposal')}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'qa' && (analysis ? <ExtractionQAScreen analysis={analysis}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'proposal' && (hasProject ? <ProposalScreen doors={doors} hardwareSets={hardwareSets} project={project} tweaks={tweaks} onContinue={() => setRoute('export')}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'export' && (hasProject ? <ExportScreen doors={doors} hardwareSets={hardwareSets} project={project} tweaks={tweaks} onFinish={() => setRoute('dashboard')} onSave={onSaveProposalStatus}/> : <NoProjectState setRoute={setRoute}/>)}
          {route === 'catalog' && <HardwareCatalogScreen catalog={hardwareSets} setCatalog={setHardwareSets} markup={tweaks.markup} currentSetIds={currentSetIds}/>}
          {route === 'settings' && <SettingsScreen tweaks={tweaks} setTweaks={setTweaks}/>}
        </div>
      </div>
      {tweaksOpen && <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} onClose={() => setTweaksOpen(false)}/>}
      {settingsOpen && <SettingsModal tweaks={tweaks} setTweaks={setTweaks} onClose={() => setSettingsOpen(false)}/>}
    </div>
  );
}

const NoProjectState = ({ setRoute }) => (
  <div className="card">
    <EmptyState
      icon="inbox"
      title="No project loaded"
      body="Upload a PDF to extract a door schedule first."
      action={<Button kind="primary" onClick={() => setRoute('upload')}><Icon name="upload"/> Upload PDF</Button>}
    />
  </div>
);

const SettingsScreen = ({ tweaks, setTweaks }) => {
  const set = (k, v) => setTweaks(t => ({ ...t, [k]: v }));
  return (
    <div className="fade-in" style={{maxWidth: 720}}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <div className="page-subtitle">Configure OpenAI access, company details, and proposal defaults.</div>
        </div>
      </div>
      <div className="card" style={{marginBottom: 16}}>
        <div className="card-header"><div className="card-title">OpenAI</div></div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap: 12}}>
          <div style={{padding: 12, background: 'var(--accent-amber-light)', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, display: 'flex', gap: 8}}>
            <Icon name="shield" size={14} style={{color:'#92400e', flexShrink: 0, marginTop: 2}}/>
            <div style={{color:'#92400e'}}>
              <strong>Local storage only.</strong> Your API key is kept in this browser and sent directly from here to api.openai.com. Don't use a shared device.
            </div>
          </div>
          <div><label className="tweak-label">API Key</label><input className="input" type="password" placeholder="sk-…" value={tweaks.apiKey || ''} onChange={e => set('apiKey', e.target.value)}/></div>
          <div>
            <label className="tweak-label">Model</label>
            <div className="input" style={{display:'flex', alignItems:'center', gap: 8}}>
              <span className="mono" style={{fontWeight: 600}}>{REQUIRED_MODEL}</span>
              <Badge tone="blue">mandated</Badge>
            </div>
            <div style={{fontSize: 11, color: 'var(--fg-muted)', marginTop: 4}}>This analyzer is locked to {REQUIRED_MODEL}. No fallback.</div>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><div className="card-title">Company &amp; defaults</div></div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap: 12}}>
          <div><label className="tweak-label">Company name (appears on proposals)</label><input className="input" value={tweaks.companyName} onChange={e => set('companyName', e.target.value)}/></div>
          <div><label className="tweak-label">Default markup %</label><input className="input" type="number" min="0" max="100" value={tweaks.markup} onChange={e => set('markup', Number(e.target.value))}/></div>
          <div><label className="tweak-label">Proposal template</label>
            <select className="select" value={tweaks.template} onChange={e => set('template', e.target.value)}>
              <option>Classic</option><option>Modern</option><option>Minimal</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
