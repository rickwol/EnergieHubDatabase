/* Minimal stand-in for the claude.ai Dashboard runtime, so the same page runs standalone. */
(function () {
  const sources = { hubs: 'energiehubs.json', provincies: 'provincies.json' };
  const DEFAULT_PARAMS = { prov: 'Alle', type: 'Alle' };
  let params = { ...DEFAULT_PARAMS };
  const store = {}; const calcs = {}; const listeners = [];
  const fire = () => listeners.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  const load = (id) => {
    if (store[id]) return;
    store[id] = { status: 'loading', data: [] };
    fetch(sources[id]).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((rows) => { store[id] = { status: 'ok', data: rows, columns: Object.keys(rows[0] || {}) }; fire(); })
      .catch((e) => { store[id] = { status: 'error', data: [], message: String(e) }; fire(); });
  };
  const readHash = () => {
    const q = new URLSearchParams(location.search);
    if (q.get('provincie')) params.prov = q.get('provincie');
    if (q.get('type')) params.type = q.get('type');
  };
  const writeUrl = () => {
    const q = new URLSearchParams();
    if (params.prov !== 'Alle') q.set('provincie', params.prov);
    if (params.type !== 'Alle') q.set('type', params.type);
    const s = q.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : '') + location.hash);
  };
  readHash();
  window.dash = {
    colors: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => `var(--cds-chart-${i})`),
    data(id) {
      if (calcs[id]) {
        const c = calcs[id];
        const ins = c.inputs.map((i) => window.dash.data(i));
        const bad = ins.find((d) => d.status !== 'ok');
        if (bad) return { status: bad.status, data: [] };
        if (!c.cache) { try { c.cache = { status: 'ok', data: c.fn(...ins.map((d) => d.data)) }; } catch (e) { console.error(e); c.cache = { status: 'error', data: [], message: String(e) }; } }
        return c.cache;
      }
      if (!sources[id]) return { status: 'missing', data: [] };
      load(id); return store[id];
    },
    calc(id, def) { calcs[id] = { ...def }; },
    loader() {},
    onData(fn) { listeners.push(fn); fn(); },
    params: () => ({ ...params }),
    setParams(p) { params = { ...params, ...p }; writeUrl(); fire(); },
    resetParams() { params = { ...DEFAULT_PARAMS }; writeUrl(); fire(); },
    setLink(name) { history.replaceState(null, '', location.pathname + location.search + '#' + name); },
    refresh() {},
  };
  let w = window.innerWidth;
  window.addEventListener('resize', () => { if (Math.abs(window.innerWidth - w) > 4) { w = window.innerWidth; fire(); } });
})();
