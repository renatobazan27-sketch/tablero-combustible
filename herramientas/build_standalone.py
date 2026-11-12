"""Arma el tablero de combustible como UN archivo HTML independiente (sin Claude).
Uso: python3 build_standalone.py plantilla.html d3.min.js carpeta_fuentes carpeta_csv salida.html
carpeta_csv debe tener: consumo.csv compras.csv tarifarios.csv flota_mensual.csv error_proyeccion.csv
(y si existen: gnv_mensual.csv gnv_estacion_mes.csv gnv_placa_mes.csv tarifa_compras.csv)
(un CSV por dataset del tablero de Claude, con el id del dataset como nombre)
"""
import sys, os, json, base64, datetime

tpl, d3p, fontdir, csvdir, out = sys.argv[1:6]
html = open(tpl, encoding='utf-8').read()
html = html.replace('<meta name="dash-one-writer">\n', '').replace('<link rel="stylesheet" href="fonts.css">\n', '')

DATA = {k: k + '.csv' for k in ('consumo', 'compras', 'tarifarios', 'flota_mensual', 'error_proyeccion',
                               'gnv_mensual', 'gnv_estacion_mes', 'gnv_placa_mes', 'tarifa_compras')}
raw = {k: open(os.path.join(csvdir, f), encoding='utf-8').read() for k, f in DATA.items() if os.path.exists(os.path.join(csvdir, f))}

fonts = ''
for w in (400, 500, 700):
    b = base64.b64encode(open(os.path.join(fontdir, f'montserrat-latin-{w}-normal.woff2'), 'rb').read()).decode()
    fonts += f"@font-face{{font-family:'Montserrat';font-style:normal;font-weight:{w};font-display:swap;src:url(data:font/woff2;base64,{b}) format('woff2');}}\n"

tokens = """
:root{--cds-rem-scale:1;--font-anthropic-sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
--color-bg:#f4f6f9;--color-panel:#ffffff;--color-fg:#16202b;--color-fg-muted:#5b6672;--color-border-line:rgba(0,0,0,.10);
--color-ok:#1e8e5a;--color-bad:#c8372d;--color-warn:#c77a00;--color-text-secondary:#5b6672;--cds-text-secondary:#5b6672;
--cds-font-size-caption:.75rem;--cds-font-size-body:.875rem;--cds-font-size-heading:.9375rem;--cds-font-size-title:1.375rem;--cds-font-weight-medium:500;
--cds-gap-xs:.375rem;--cds-gap-sm:.5rem;--cds-gap-md:.75rem;--cds-gap-xl:2rem;--cds-pad-xs:.25rem;--cds-pad-sm:.5rem;--cds-pad-md:.75rem;--cds-pad-lg:1rem;--cds-radius:.5rem;
--cds-dur-slow:.45s;--cds-ease-out:cubic-bezier(0,0,.2,1);
--cds-chart-grid:rgba(0,0,0,.08);--cds-chart-axis:#c9ced4;--cds-chart-reference:#9aa3ad;--cds-chart-muted:#d5d9de;--cds-chart-status-critical:#d6453a;
--cds-surface-popover:#ffffff;--cds-shadow-popover:0 8px 24px #0000001f,0 2px 6px #00000014;--cds-border:rgba(0,0,0,.08);color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--color-bg:#14181d;--color-panel:#1c2229;--color-fg:#e8ecf0;--color-fg-muted:#9aa5b1;--color-border-line:rgba(255,255,255,.10);
--color-text-secondary:#9aa5b1;--cds-text-secondary:#9aa5b1;--cds-chart-grid:rgba(255,255,255,.08);--cds-chart-axis:#4a535d;--cds-chart-reference:#6b7682;--cds-chart-muted:#3a424b;
--cds-surface-popover:#262d35;--cds-shadow-popover:0 8px 24px #00000052,0 2px 6px #0003;--cds-border:rgba(255,255,255,.06);color-scheme:dark}}
html,body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:'Montserrat',var(--font-anthropic-sans);font-size:var(--cds-font-size-body)}
body{padding:24px 16px;max-width:1400px;margin:0 auto;box-sizing:border-box}
.fz-card,.fz-sec{background:var(--color-panel);border:1px solid var(--color-border-line);border-radius:12px;padding:16px}
.dash-skeleton{min-height:120px;background:linear-gradient(90deg,transparent,var(--color-border-line),transparent);background-size:200% 100%;animation:sk 1.4s infinite}
@keyframes sk{to{background-position:-200% 0}}
.fz-stamp{font-size:var(--cds-font-size-caption);color:var(--color-fg-muted);text-align:right;margin-top:24px}
"""

gen = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime('%d/%m/%Y %H:%M')
runtime = """
<script>
(function(){
  const RAW = __RAW__;
  const parse = (t) => d3.csvParse(t, d3.autoType).map((r) => { for (const k in r) if (r[k] instanceof Date) r[k] = r[k].toISOString().slice(0, 10); return r; });
  const DS = {}; for (const k in RAW) DS[k] = { status: 'ok', data: parse(RAW[k]) };
  const calcs = {}, draws = {}, onD = [];
  let params = { desde: null, hasta: null, sede: null, tipo: null, tgrifo: null, horiz: 3 };
  try { const s = JSON.parse(localStorage.getItem('dpwl-comb-params') || 'null'); if (s) params = Object.assign(params, s); } catch (e) {}
  const one = (id) => { for (const el of document.querySelectorAll('[data-draw="' + id + '"]')) {
      const f = draws[id]; if (!f) continue;
      try { if (typeof f === 'function') f(el); else { if (!el.__m) el.__m = f.mount(el); if (f.update) f.update(el, el.__m); } }
      catch (e) { console.error('draw', id, e); } } };
  const run = () => { for (const id in draws) one(id); onD.forEach((f) => { try { f(); } catch (e) { console.error(e); } }); };
  let rt = null; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(run, 150); });
  window.dash = {
    data: (id) => { if (DS[id]) return DS[id]; const c = calcs[id]; if (!c) return { status: 'missing', data: [] };
      if (!c.v) c.v = { status: 'ok', data: c.fn(...c.inputs.map((i) => window.dash.data(i).data)) }; return c.v; },
    calc: (id, o) => { calcs[id] = o; },
    draw: (id, f) => { if (f === undefined) { one(id); return; } draws[id] = f; },
    params: () => params,
    setParams: (p) => { params = Object.assign({}, params, p); try { localStorage.setItem('dpwl-comb-params', JSON.stringify(params)); } catch (e) {} run(); },
    setLink: () => {}, onData: (f) => { onD.push(f); },
  };
  window.addEventListener('DOMContentLoaded', () => setTimeout(() => {
    run();
    const ro = new ResizeObserver((ents) => { for (const e of ents) { const el = e.target, w = Math.round(e.contentRect.width);
      if (w > 0 && w !== el.__w) { const first = el.__w === undefined; el.__w = w; if (!first || el.__drawnAt0) one(el.dataset.draw); } } });
    for (const el of document.querySelectorAll('[data-draw]')) { el.__drawnAt0 = el.clientWidth === 0; ro.observe(el); }
  }, 0));
})();
</script>
""".replace('__RAW__', json.dumps(raw))

d3src = open(d3p, encoding='utf-8').read()
head = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Centro de combustible DPWL</title>\n'
        f'<style>{fonts}{tokens}</style>\n<script>{d3src}</script>\n{runtime}\n</head>\n<body>\n')
foot = f'\n<p class="fz-stamp">Archivo generado el {gen} (hora de Lima). Datos internos de DP World Logistics: no compartir fuera de la empresa.</p>\n</body>\n</html>\n'
open(out, 'w', encoding='utf-8').write(head + html + foot)
print(out, round(os.path.getsize(out) / 1e6, 2), 'MB')
