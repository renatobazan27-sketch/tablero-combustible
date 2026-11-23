"""Análisis RAM: camionetas a GNV (TERCERO NO DPWL_GNV, Grifo Redcol) vs. camionetas a diésel.
Uso: python3 ram_desde_kardex.py "DPWL Reporte de combustible 2026.xlsx" carpeta_salida
Salida: ram_gnv.csv (mes, placa, cargas, m3, m3_km, km) y ram_diesel_pickup.csv (mes, placas, km, gal).
km = suma de los avances de odómetro entre cargas seguidas de la misma placa (0 < avance < 1500 km);
m3_km / gal = cantidad de esas cargas (la primera carga de cada placa no tiene avance y no entra al ratio)."""
import sys, os
import openpyxl, pandas as pd
src, out = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
it = wb['Data'].iter_rows(values_only=True); h = next(it)
df = pd.DataFrame([r for r in it if r and r[0]], columns=h)
df['placa'] = df.PLACA.astype(str).str.replace('-', '').str.strip().str.upper()
df['f'] = pd.to_datetime(df.FECHA, errors='coerce')
df['km'] = pd.to_numeric(df.KM, errors='coerce'); df['q'] = pd.to_numeric(df.CANTIDAD, errors='coerce')
df = df.dropna(subset=['f', 'q'])
def avance(x, lo, hi):
    x = x.sort_values(['placa', 'f', 'km']).copy()
    x['dk'] = x.groupby('placa').km.diff()
    x['ok'] = (x.dk > 0) & (x.dk < 1500)
    if lo is not None:
        r = x.dk / x.q
        x['ok'] &= (r > lo) & (r < hi)
    x['mes'] = x.f.dt.strftime('%Y-%m'); return x
g = avance(df[df['TIPO ACTIVO'].astype(str).str.strip() == 'TERCERO NO DPWL_GNV'], None, None)
a = g.groupby(['mes', 'placa']).agg(cargas=('q', 'size'), m3=('q', 'sum')).join(
    g[g.ok].groupby(['mes', 'placa']).agg(m3_km=('q', 'sum'), km=('dk', 'sum'))).fillna(0).reset_index()
a.round(3).to_csv(os.path.join(out, 'ram_gnv.csv'), index=False)
d = avance(df[(df['TIPO ACTIVO'].astype(str).str.strip() == 'PICK UP [CAMIONETA]') & (df.UMD.astype(str).str.upper() == 'GAL')], 3, 80)
b = d[d.ok].groupby('mes').agg(placas=('placa', 'nunique'), km=('dk', 'sum'), gal=('q', 'sum')).reset_index()
b.round(3).to_csv(os.path.join(out, 'ram_diesel_pickup.csv'), index=False)
print(a.groupby('mes')[['m3', 'm3_km', 'km']].sum()); print(b); print('ratio diésel', round(b.km.sum() / b.gal.sum(), 2))
