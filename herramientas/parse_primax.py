"""Lee cartas Primax (Carta_DPWL_*.pdf) y devuelve precios sin IGV por vigencia.
Uso: python3 parse_primax.py <carpeta_pdfs> <salida.csv>
Columnas salida: fecha,gambeta,argentina,piura,paita_planta,archivo
"""
import sys, os, re, datetime, csv
import pdfplumber

MESES = {m: i for i, m in enumerate(
    ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
     'septiembre', 'octubre', 'noviembre', 'diciembre'], 1)}
MESES['setiembre'] = 9


def leer(path):
    with pdfplumber.open(path) as p:
        txt = '\n'.join((pg.extract_text() or '') for pg in p.pages)
    # año confiable: encabezado "Surco,martes, 03 de Noviembre de 2026"
    m = re.search(r'(\d{1,2}) de ([A-Za-zé]+) de (\d{4})', txt)
    hdr = datetime.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
    v = re.search(r'vigente desde el (\d{1,2})/(\d{1,2})/(\d{4})', txt)
    if v:
        d, mo = int(v.group(1)), int(v.group(2))
        y = hdr.year
        if mo == 12 and hdr.month == 1: y -= 1
        if mo == 1 and hdr.month == 12: y += 1
        fecha = datetime.date(y, mo, d)
    else:
        fecha = hdr
    line = next(l for l in txt.splitlines() if 'Precio Final sin IGV' in l)
    nums = [float(x) for x in re.findall(r'(-?\d+\.\d+)', line)]
    if len(nums) < 3:
        raise ValueError('sin precios')
    paita = nums[3] if len(nums) >= 4 else None
    return dict(fecha=fecha.isoformat(), gambeta=nums[0], argentina=nums[1],
                piura=nums[2], paita_planta=paita, archivo=os.path.basename(path))


if __name__ == '__main__':
    carpeta, out = sys.argv[1], sys.argv[2]
    filas, errores = [], []
    for f in sorted(os.listdir(carpeta)):
        if not f.lower().endswith('.pdf') or 'DPWL' not in f:
            continue
        try:
            filas.append(leer(os.path.join(carpeta, f)))
        except Exception as e:
            errores.append((f, str(e)))
    # una fila por fecha de vigencia (si hay duplicados, se queda la última por nombre)
    por_fecha = {}
    for r in filas:
        por_fecha[r['fecha']] = r
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fecha', 'gambeta', 'argentina', 'piura', 'paita_planta', 'archivo'])
        w.writeheader()
        for k in sorted(por_fecha):
            w.writerow(por_fecha[k])
    print(f'{len(filas)} PDFs leídos, {len(por_fecha)} fechas únicas, {len(errores)} errores')
    for e in errores:
        print('ERROR', e)
