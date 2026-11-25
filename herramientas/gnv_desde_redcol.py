"""GNV desde los reportes mensuales de Redcol (Archivos GNV/Fecha Normal/AAAAMM.xlsx).
Uso: python3 gnv_desde_redcol.py "<carpeta Fecha Normal>" <carpeta csv actuales> <carpeta salida> [desde=202610]
Rehace, desde el mes indicado, gnv_mensual.csv, gnv_estacion_mes.csv y gnv_placa_mes.csv (los meses anteriores se conservan
del Power BI). Solo filas de producto GNV: cantidad (K) m³, subtotal sin IGV (L), placa (G), estación (Q)."""
import sys, os, glob, collections, openpyxl, pandas as pd
carp, cur, out = sys.argv[1:4]; desde = sys.argv[4] if len(sys.argv) > 4 else '202610'
EST = [('GAMBETA', 'Gambeta H'), ('ULTRAGRIFOS', 'Ultragrifos'), ('CANTOLAO', 'Cantolao'), ('HUACHO', 'Huacho'),
       ('LA MARINA', 'La Marina Gaspetrol'), ('ZED PAITA', 'Zed Paita'), ('CHINCHA', 'Chincha')]
est = lambda s: next((v for k, v in EST if k in s.upper()), 'Otras')
rows = []
for f in sorted(glob.glob(os.path.join(carp, '2*.xlsx'))):
    ym = os.path.basename(f)[:6]
    if ym < desde: continue
    m = ym[:4] + '-' + ym[4:6]
    for r in openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True):
        if not r or len(r) < 20 or not r[7] or 'GNV' not in str(r[7]).upper(): continue
        try: q, t = float(r[10] or 0), float(r[11] or 0)
        except (TypeError, ValueError): continue
        rows.append(dict(mes=m, placa=str(r[6] or '').replace('-', '').strip().upper(), estacion=est(str(r[16] or '')), m3=q, costo=t))
d = pd.DataFrame(rows)
gm = pd.read_csv(os.path.join(cur, 'gnv_mensual.csv')); ge = pd.read_csv(os.path.join(cur, 'gnv_estacion_mes.csv')); gp = pd.read_csv(os.path.join(cur, 'gnv_placa_mes.csv'))
lim = desde[:4] + '-' + desde[4:6]
tipo = gp.sort_values('mes').groupby('placa').tipo.last().to_dict()
nm = d.groupby('mes').agg(m3=('m3', 'sum'), costo=('costo', 'sum'), placas=('placa', 'nunique')).reset_index()
nm['m3_consumo'] = nm.m3; nm['precio'] = nm.costo / nm.m3
ne = d.groupby(['mes', 'estacion']).agg(m3=('m3', 'sum'), costo=('costo', 'sum')).reset_index(); ne['precio'] = ne.costo / ne.m3
npl = d.groupby(['mes', 'placa']).m3.sum().reset_index(); npl['tipo'] = npl.placa.map(tipo).fillna('TERCERO NO DPWL_GNV')
os.makedirs(out, exist_ok=True)
pd.concat([gm[gm.mes < lim], nm[gm.columns]]).round(4).to_csv(os.path.join(out, 'gnv_mensual.csv'), index=False)
pd.concat([ge[ge.mes < lim], ne[ge.columns]]).round(4).to_csv(os.path.join(out, 'gnv_estacion_mes.csv'), index=False)
pd.concat([gp[gp.mes < lim], npl[gp.columns]]).round(3).to_csv(os.path.join(out, 'gnv_placa_mes.csv'), index=False)
print(nm.round(2).to_string(index=False)); print(ne.round(1).to_string(index=False)); print('placas sin tipo:', sorted(set(npl.placa) - set(tipo)))
