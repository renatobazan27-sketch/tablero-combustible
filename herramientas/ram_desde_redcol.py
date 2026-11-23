"""Análisis RAM: cargas de las camionetas TERCERO NO DPWL_GNV en Redcol (GNV y gasolina) con su odómetro.
Uso: python3 ram_desde_redcol.py "<carpeta Fecha Normal>" "DPWL Reporte de combustible 2026.xlsx" salida.csv [desde=202606]
Lee los reportes mensuales de Redcol (AAAAMM.xlsx, hoja REPORTE DE CONSUMO): columnas fecha (C), placa (G), producto (H),
precio sin IGV (J), cantidad (K), total sin IGV (L), odómetro (T). Las placas son las TERCERO NO DPWL_GNV que tienen cargas en la hoja Data del Reporte de combustible.
km = avance de odómetro desde la carga anterior de la misma placa (0 < avance < 1500); ok = 1 si la carga tiene avance válido."""
import sys, os, glob, datetime
import openpyxl, pandas as pd
carp, rep, out = sys.argv[1], sys.argv[2], sys.argv[3]
desde = sys.argv[4] if len(sys.argv) > 4 else '202606'
wb = openpyxl.load_workbook(rep, read_only=True, data_only=True)
it = wb['Data'].iter_rows(values_only=True); h = list(next(it)); ip, it_ = h.index('PLACA'), h.index('TIPO ACTIVO')
P = {str(r[ip]).replace('-', '').strip().upper() for r in it if r and str(r[it_]).strip() == 'TERCERO NO DPWL_GNV'}  # placas con cargas en el Kardex
rows = []
for f in sorted(glob.glob(os.path.join(carp, '2*.xlsx'))):
    ym = os.path.basename(f)[:6]
    if ym < desde: continue
    for r in openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True):
        if not r or len(r) < 20: continue
        f0 = r[2]
        if isinstance(f0, str):
            try: f0 = datetime.datetime.strptime(f0.strip() + ' ' + str(r[3] or '0:00:00').strip()[:8], '%d/%m/%Y %H:%M:%S')
            except ValueError:
                try: f0 = datetime.datetime.strptime(f0.strip(), '%d/%m/%Y')
                except ValueError: continue
        if not isinstance(f0, datetime.datetime): continue
        pl = str(r[6] or '').replace('-', '').strip().upper()
        if pl not in P: continue
        prod = 'GNV' if 'GNV' in str(r[7]).upper() else 'GASOLINA'
        rows.append(dict(fecha=f0, placa=pl, producto=prod, unidad='m3' if prod == 'GNV' else 'gal', cantidad=float(r[10] or 0), total=float(r[11] or 0), odometro=pd.to_numeric(str(r[19]).replace(',', ''), errors='coerce')))
df = pd.DataFrame(rows).drop_duplicates().sort_values(['placa', 'fecha'])
# cargas sin importe en el reporte: precio mediano del mismo producto y mes
df['m'] = df.fecha.dt.strftime('%Y-%m'); pm = df[df.total > 0].assign(p=lambda x: x.total / x.cantidad).groupby(['producto', 'm']).p.median()
df['precio_est'] = (df.total <= 0).astype(int)
df.loc[df.total <= 0, 'total'] = [c * pm.get((pr, m), float('nan')) for c, pr, m in df.loc[df.total <= 0, ['cantidad', 'producto', 'm']].itertuples(index=False)]
df['km'] = df.groupby('placa').odometro.diff()
df['ok'] = ((df.km > 0) & (df.km < 1500)).astype(int); df.loc[df.ok == 0, 'km'] = 0
df['fecha'] = df.fecha.dt.strftime('%Y-%m-%d %H:%M')
df[['fecha', 'placa', 'producto', 'unidad', 'cantidad', 'total', 'odometro', 'km', 'ok', 'precio_est']].round(4).to_csv(out, index=False)
d = df.assign(m=df.fecha.str[:7]); print(sorted(P)); print(d.groupby(['m', 'producto']).agg(q=('cantidad', 'sum'), tot=('total', 'sum'), km=('km', 'sum'))); print('última carga', df.fecha.max())
