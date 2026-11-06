"""Lee los correos de Servosa guardados por Power Automate (Servosa_*.html) y extrae la tabla de despachos.
Uso: python3 parse_servosa.py <carpeta_html> <salida.csv>
Salida: sede,fecha_gr,guia,cantidad,factura,fecha_ft,precio_igv,precio,archivo
- sede = PAITA si el asunto dice PAITA; si no, CALLAO.
- precio = precio unitario con IGV / 1.18 (sin IGV).
- Una fila por guía de remisión + factura (los correos repetidos no duplican).
"""
import sys, os, re, io, csv, datetime
import pandas as pd


def num(x):
    s = re.sub(r'[^0-9.,-]', '', str(x)).replace(',', '')
    return float(s) if s not in ('', '-', '.') else None


def fecha(x):
    try:
        return datetime.datetime.strptime(str(x).strip(), '%d/%m/%Y').date().isoformat()
    except ValueError:
        return None


def leer(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'ASUNTO: (.*?) \| RECIBIDO', s, re.S)
    asunto = (m.group(1) if m else '').upper()
    sede = 'PAITA' if 'PAITA' in asunto else 'CALLAO'
    filas = []
    try:
        tablas = pd.read_html(io.StringIO(s))
    except ValueError:
        return filas
    for t in tablas:
        t = t.astype(str)
        hdr = None
        for i in range(min(len(t), 5)):
            vals = [str(v).upper() for v in t.iloc[i].tolist()]
            if any('PRECIO' in v for v in vals) and any('GUIA' in v for v in vals):
                hdr = i
                cols = vals
                break
        if hdr is None:
            continue
        def col(nombre):
            return next(j for j, v in enumerate(cols) if nombre in v)
        jg, jc, jf, jp = col('GUIA'), col('CANTIDAD'), col('FACTURA'), col('PRECIO')
        jgr = next(j for j, v in enumerate(cols) if 'EMISION GR' in v)
        jft = next((j for j, v in enumerate(cols) if 'EMISION FT' in v), None)
        for i in range(hdr + 1, len(t)):
            r = [str(v) for v in t.iloc[i].tolist()]
            guia = r[jg].strip()
            if guia in ('', 'nan'):
                continue  # fila de totales
            p = num(r[jp]); q = num(r[jc]); fgr = fecha(r[jgr])
            if not (p and q and fgr):
                continue
            filas.append(dict(sede=sede, fecha_gr=fgr, guia=guia, cantidad=q,
                              factura=r[jf].strip().replace('-', ''), fecha_ft=fecha(r[jft]) if jft is not None else '',
                              precio_igv=p, precio=round(p / 1.18, 6), archivo=os.path.basename(path)))
    return filas


if __name__ == '__main__':
    carpeta, out = sys.argv[1], sys.argv[2]
    todas = {}
    n = 0
    for f in sorted(os.listdir(carpeta)):
        if f.lower().endswith('.html'):
            n += 1
            for r in leer(os.path.join(carpeta, f)):
                todas[(r['guia'], r['factura'])] = r
    filas = sorted(todas.values(), key=lambda r: (r['fecha_gr'], r['sede'], r['guia']))
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['sede', 'fecha_gr', 'guia', 'cantidad', 'factura', 'fecha_ft', 'precio_igv', 'precio', 'archivo'])
        w.writeheader(); w.writerows(filas)
    print(f'{n} correos leídos, {len(filas)} despachos únicos')
