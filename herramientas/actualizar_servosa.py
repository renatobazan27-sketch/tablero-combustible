"""Agrega los despachos nuevos de Servosa al Excel y rearma el grupo IBC del tarifario.
Uso: python3 actualizar_servosa.py servosa_correos.csv Listado_Precios_Servosa.xlsx tarifarios_actual.csv YYYY-MM-DD tarifarios_salida.csv
- Excel (hoja Hoja1, tabla Tabla1): CLIENTE (CALLAO/PAITA) | FECHA DE EMISION GR | CANTIDAD | FACTURA | PRECIO UNITARIO (sin IGV) | TOTAL (=E*C)
  Solo agrega filas que no estén (misma sede + fecha + cantidad; Servosa a veces refactura el mismo despacho con otro número) y cuya fecha sea posterior a 15 días antes de la última fila.
- Tarifario IBC: precio sin IGV por día y sede (promedio si hay varios en el día), arrastrado hasta la fecha de corte.
  Callao -> ubicacion Callao / sede Callao ; Paita -> ubicacion Paita / sede Paita.
"""
import sys, re, copy, datetime
import pandas as pd
import openpyxl

csv_correos, xlsx, tar_in, corte, tar_out = sys.argv[1:6]


def fkey(f):
    m = re.search(r'FA0?5\D*0*(\d+)', str(f).upper())
    return int(m.group(1)) if m else str(f).strip().upper()


def as_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.datetime.strptime(str(v).strip(), '%d/%m/%Y').date()
    except ValueError:
        return None


wb = openpyxl.load_workbook(xlsx)
ws = wb['Hoja1']
tab = ws.tables['Tabla1']
first, last = tab.ref.split(':')
last_row = int(re.sub(r'\D', '', last))
existentes = set()
fechas = []
for r in range(2, last_row + 1):
    d = as_date(ws.cell(r, 2).value)
    if d:
        fechas.append(d)
    existentes.add((str(ws.cell(r, 1).value or '').strip().upper(), d, float(ws.cell(r, 3).value or 0)))
desde = max(fechas) - datetime.timedelta(days=15)

nuevos = pd.read_csv(csv_correos)
nuevos['d'] = pd.to_datetime(nuevos.fecha_gr).dt.date
agregar = []
for _, x in nuevos.sort_values(['d', 'sede', 'guia']).iterrows():
    k = (str(x.sede).upper(), x.d, float(x.cantidad))
    if x.d >= desde and k not in existentes:
        agregar.append(x)
        existentes.add(k)

r = last_row
for x in agregar:
    r += 1
    q = int(x.cantidad) if float(x.cantidad).is_integer() else float(x.cantidad)
    vals = [x.sede, datetime.datetime.combine(x.d, datetime.time()), q, str(x.factura), float(x.precio), f'=+E{r}*C{r}']
    for c, v in enumerate(vals, 1):
        cell = ws.cell(r, c, v)
        src = ws.cell(last_row, c)
        if src.has_style:
            cell._style = copy.copy(src._style)
if agregar:
    tab.ref = f'{first}:{re.sub(r"[0-9]", "", last)}{r}'
    wb.save(xlsx)
print(f'Excel: {len(agregar)} filas nuevas (hasta la fila {r})')

# --- tarifario IBC desde el Excel completo ---
filas = []
for i in range(2, r + 1):
    d = as_date(ws.cell(i, 2).value)
    p = ws.cell(i, 5).value
    s = str(ws.cell(i, 1).value or '').strip().upper()
    if d and isinstance(p, (int, float)) and s in ('CALLAO', 'PAITA'):
        filas.append(dict(fecha=d.isoformat(), sede=s.title(), precio=float(p)))
INICIO = '2026-10-01'  # desde aquí el IBC sale del Excel/correos; antes se conserva el historial que ya cuadra con Power BI
ibc = pd.DataFrame(filas)
ibc = ibc[ibc.fecha >= INICIO].groupby(['sede', 'fecha'], as_index=False).precio.mean()
t = pd.read_csv(tar_in)
viejo = t[(t.grupo == 'IBC') & (t.fecha < INICIO)]
dias = pd.date_range(INICIO, corte).strftime('%Y-%m-%d')
partes = [viejo]
for s in ('Callao', 'Paita'):
    base = viejo[viejo.ubicacion == s].sort_values('fecha').precio.iloc[-1]
    d = ibc[ibc.sede == s].set_index('fecha')[['precio']].reindex(dias)
    if pd.isna(d.precio.iloc[0]):
        d.iloc[0, 0] = base
    d = d.ffill()
    d['grupo'], d['ubicacion'], d['sede'] = 'IBC', s, s
    d['precio'] = d.precio.round(4)
    d['suma'], d['n'] = d.precio, 1
    partes.append(d.reset_index(names='fecha'))
nuevo_ibc = pd.concat(partes)
res = pd.concat([t[t.grupo != 'IBC'], nuevo_ibc])[['fecha', 'grupo', 'ubicacion', 'sede', 'suma', 'n', 'precio']]
res = res.sort_values(['fecha', 'grupo', 'ubicacion'])
res.to_csv(tar_out, index=False, float_format='%.4f')
print(res[(res.grupo == 'IBC') & (res.fecha == corte)].to_string(index=False))
