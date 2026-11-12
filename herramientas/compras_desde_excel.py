"""Arma tarifa_compras.csv (fecha,grifo,galones,total) desde DPWL Precio Combustible.xlsx, hoja Data.
Uso: python3 compras_desde_excel.py "DPWL Precio Combustible.xlsx" tarifa_compras.csv [desde=2024-01-01]
Solo diésel (TIPO COMBUSTIBLE = DIESEL; se excluye REDCOL/GNV). Precio = TOTAL S/ / CANTIDAD (sin IGV)."""
import sys, csv, datetime, collections, openpyxl
src, out = sys.argv[1], sys.argv[2]; desde = sys.argv[3] if len(sys.argv) > 3 else '2024-01-01'
NOM = {'GRIFO PRIMAX': 'Primax', 'GRIFO ARGENTINA': 'Argentina', 'GRIFO GAMBETTA1': 'Gambetta1', 'GRIFO GAMBETTA2': 'Gambetta2',
       'GRIFO GAMBETTA3': 'Gambetta3', 'GRIFO PAITA': 'Paita', 'GRIFO PAITA2': 'Paita2'}
ws = openpyxl.load_workbook(src, read_only=True, data_only=True)['Data']
it = ws.iter_rows(values_only=True); h = [str(x).strip() if x else '' for x in next(it)]
ix = {k: h.index(k) for k in ('GRIFO', 'FECHA', 'CANTIDAD', 'TOTAL S/', 'TIPO COMBUSTIBLE')}
agg = collections.defaultdict(lambda: [0.0, 0.0]); n = 0
for r in it:
    g = NOM.get(str(r[ix['GRIFO']] or '').strip().upper())
    if not g or str(r[ix['TIPO COMBUSTIBLE']] or '').strip().upper() != 'DIESEL': continue
    f = r[ix['FECHA']]
    if isinstance(f, (int, float)): f = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=f)
    if not isinstance(f, datetime.datetime): continue
    f = f.strftime('%Y-%m-%d')
    if f < desde: continue
    try: q, t = float(r[ix['CANTIDAD']] or 0), float(r[ix['TOTAL S/']] or 0)
    except (TypeError, ValueError): continue
    a = agg[(f, g)]; a[0] += q; a[1] += t; n += 1
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['fecha', 'grifo', 'galones', 'total'])
    for (f, g) in sorted(agg): q, t = agg[(f, g)]; w.writerow([f, g, round(q, 3), round(t, 2)])
print(f'{n} filas -> {len(agg)} días-grifo; última fecha {max(f for f, _ in agg)}')
