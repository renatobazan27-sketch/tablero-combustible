"""Consumo de diésel 2026 desde el Reporte de combustible (hoja Data).
Uso: python3 consumo_desde_kardex.py "DPWL Reporte de combustible 2026.xlsx" consumo_actual.csv tarifarios.csv tarifa_compras.csv salida.csv
- Conserva tal cual las filas anteriores a 2026 y vuelve a armar 2026 (solo UMD = GAL) por fecha, grifo, sede, tipo y placa.
- Costo real: precio del día ya publicado para ese grifo (consumo_actual); si no existe:
  Primax = tarifario Coesti del día × factor (compra Primax ÷ tarifario del último mes con compras Primax);
  internos/IBC = último precio conocido del grifo (arrastre). Costo base con los precios base de Impacto."""
import sys, csv, bisect, collections, openpyxl, pandas as pd
xl, act, tar, comp, out = sys.argv[1:6]
TIPO = {'TRUCKS': 'Trucks', 'REACH STAKER': 'Reach Stacker', 'TERCERO DPWL': 'Tercero DPWL', 'UNDERLAND DPWL': 'Underland DPWL', 'PICK UP [CAMIONETA]': 'Pick Up (camioneta)', 'TERCERO NO DPWL': 'Tercero no DPWL', 'TERCERNO NO DPWL': 'Tercero no DPWL', 'RUBBER TIRED GANTRY': 'Rubber Tired Gantry', 'UNDERLAND ALQUILADO': 'Underland Alquilado', 'GENERADOR': 'Generador', 'VAN DPWL': 'Van DPWL', 'TRUCKS-V': 'Trucks-V', 'FORKLIFT': 'Forklift', 'OTROS DPWL': 'Otros DPWL', 'TERCERO DPWL-EXTERNO': 'Tercero DPWL'}
gname = lambda g: (lambda u: 'Primax' if u == 'PRIMAX' else u.capitalize())(str(g).upper().replace('GRIFO', '').strip())
BASE = lambda g: 11.47 if g == 'Primax' else (12.53 if g in ('Paita2', 'Gambetta2', 'Gambetta3') else 10.58)
old = list(csv.DictReader(open(act)))
pr = {}
for r in old:
    if float(r['galones']) > 0: pr.setdefault((r['grifo'], r['fecha']), float(r['costo_real']) / float(r['galones']))
byg = collections.defaultdict(list)
for (g, f), p in pr.items(): byg[g].append((f, p))
for g in byg: byg[g].sort()
t = pd.read_csv(tar); ext = t[t.grupo == 'Externo (Coesti)'].groupby('fecha').apply(lambda x: x.suma.sum() / x.n.sum()).to_dict()
c = pd.read_csv(comp); c['m'] = c.fecha.astype(str).str[:7]; cp = c[c.grifo == 'Primax']
mP = cp.m.max(); q = cp[cp.m == mP]; tv = pd.Series({k: v for k, v in ext.items() if k[:7] == mP}).mean()
fac = (q.total.sum() / q.galones.sum()) / tv if tv == tv else 1.0
print('factor Primax', mP, round(fac, 4))
wb = openpyxl.load_workbook(xl, read_only=True, data_only=True); it = wb['Data'].iter_rows(values_only=True); h = [str(x).strip() if x else '' for x in next(it)]
agg = collections.defaultdict(float)
for row in it:
    r = dict(zip(h, row))
    if str(r.get('UMD')).upper() != 'GAL' or not hasattr(r.get('FECHA'), 'strftime'): continue
    f = r['FECHA'].strftime('%Y-%m-%d')
    if f < '2026-01-01': continue
    g = gname(r['GRIFO']); tp = str(r.get('TIPO ACTIVO') or '').replace('\xa0', ' ').strip().upper(); tp = TIPO.get(tp, tp.title())
    agg[(f, g, 'Paita' if g.startswith('Paita') else 'Callao', tp, str(r['PLACA']).strip())] += float(r.get('CANTIDAD') or 0)
def price(g, f):
    if (g, f) in pr: return pr[(g, f)], ''
    if g == 'Primax' and f in ext: return ext[f] * fac, 'tarifario'
    L = byg.get(g) or byg.get('Gambetta2'); i = bisect.bisect_right(L, (f, 9e9)) - 1
    return L[max(i, 0)][1], 'arrastre'
res = [r for r in old if r['fecha'] < '2026-01-01']; est = collections.Counter()
for k in sorted(agg):
    f, g, s, tp, pl = k; gal = round(agg[k], 3)
    if gal <= 0: continue
    p, e = price(g, f)
    if e: est[(g, f[:7], e)] += 1
    res.append({'fecha': f, 'grifo': g, 'sede': s, 'tipo': tp, 'placa': pl, 'galones': gal, 'costo_real': round(gal * p, 2), 'costo_base': round(gal * BASE(g), 2)})
w = csv.DictWriter(open(out, 'w', newline=''), fieldnames=list(old[0].keys())); w.writeheader(); w.writerows(res)
print('precios estimados', dict(est))
d = pd.DataFrame(res); d['galones'] = d.galones.astype(float); print(d[d.fecha >= '2026-01'].groupby(d.fecha.str[:7]).galones.sum().round(0).to_string())
print('último dato:', d.groupby('grifo').fecha.max().to_dict())
