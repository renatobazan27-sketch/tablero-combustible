"""Reemplaza el grupo Interno de tarifarios.csv con los precios de las cartas Primax
y arrastra el último precio de cada grupo/ubicación hasta la fecha de corte.
Uso: python3 build_tarifarios.py tarifarios_actual.csv interno_pdf.csv YYYY-MM-DD salida.csv
Interno: Callao = columna Argentina, Gambetta = columna Gambeta,
Piura (sede Paita) = promedio de Piura-Piura y Piura-Paita (si la carta no trae Paita, solo Piura).
"""
import sys
import pandas as pd

actual, pdfcsv, corte, out = sys.argv[1:5]
t = pd.read_csv(actual)
p = pd.read_csv(pdfcsv).sort_values('fecha')
p['paita_prom'] = p[['piura', 'paita_planta']].mean(axis=1).round(4)

rows = []
for _, r in p.iterrows():
    for ubic, sede, val in (('Callao', 'Callao', r.argentina), ('Gambetta', 'Callao', r.gambeta),
                            ('Piura', 'Paita', r.paita_prom)):
        rows.append(dict(fecha=r.fecha, grupo='Interno', ubicacion=ubic, sede=sede, suma=val, n=1, precio=val))
nuevo = pd.concat([t[t.grupo != 'Interno'], pd.DataFrame(rows)], ignore_index=True)

# arrastre diario hasta la fecha de corte para cada grupo/ubicación
dias = pd.date_range(nuevo.fecha.min(), corte).strftime('%Y-%m-%d')
partes = []
for (g, u, s), d in nuevo.groupby(['grupo', 'ubicacion', 'sede']):
    d = d.drop_duplicates('fecha', keep='last').set_index('fecha').sort_index()
    d = d.reindex([x for x in dias if x >= d.index.min()]).ffill()
    d['grupo'], d['ubicacion'], d['sede'] = g, u, s
    partes.append(d.reset_index(names='fecha'))
res = pd.concat(partes).sort_values(['fecha', 'grupo', 'ubicacion'])
res['n'] = res['n'].astype(int)
res[['fecha', 'grupo', 'ubicacion', 'sede', 'suma', 'n', 'precio']].to_csv(out, index=False, float_format='%.4f')
ult = res[res.fecha == corte]
print(ult.to_string(index=False))
