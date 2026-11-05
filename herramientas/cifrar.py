"""Cifra el tablero (HTML independiente) con una clave y genera index.html para GitHub Pages.
Uso: python3 cifrar.py Tablero_Combustible_DPWL.html "<clave>" salida/index.html
- AES-256-GCM; la llave se deriva de la clave con PBKDF2-SHA256 (600 000 iteraciones).
- La sal es fija (derivada de un texto constante) para que "Recordar en este equipo" siga
  funcionando después de cada actualización nocturna; el IV es nuevo en cada cifrado.
- El HTML se comprime con gzip antes de cifrar (el navegador lo descomprime).
"""
import sys, os, gzip, base64, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

src, clave, out = sys.argv[1:4]
ITER = 600000
salt = hashlib.sha256(b'dpwl-tablero-combustible-v1').digest()[:16]
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(clave.encode('utf-8'))
iv = os.urandom(12)
plain = gzip.compress(open(src, 'rb').read(), 9)
ct = AESGCM(key).encrypt(iv, plain, None)
kid = hashlib.sha256(key).hexdigest()[:12]  # identifica la llave para invalidar "recordar" si cambia la clave
b64 = lambda b: base64.b64encode(b).decode()

page = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Centro de combustible DPWL</title>
<style>
:root{--bg:#f4f6f9;--panel:#fff;--fg:#16202b;--muted:#5b6672;--line:rgba(0,0,0,.12);--navy:#004071;--orange:#F15922;--bad:#c8372d;color-scheme:light}
@media (prefers-color-scheme: dark){:root{--bg:#14181d;--panel:#1c2229;--fg:#e8ecf0;--muted:#9aa5b1;--line:rgba(255,255,255,.14);--navy:#5aa7e0;color-scheme:dark}}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%;background:var(--bg);color:var(--fg);font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{min-height:100vh;display:grid;place-items:center;padding:24px 16px}
form{width:100%;max-width:360px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:28px 24px;display:grid;gap:14px}
.logo{width:48px;height:48px;border-radius:12px;background:var(--navy);display:grid;place-items:center}
.logo svg{width:26px;height:26px;fill:var(--orange)}
h1{font-size:1.15rem;margin:0}
p{margin:0;color:var(--muted);font-size:.875rem;line-height:1.45}
label{font-size:.8rem;color:var(--muted);display:grid;gap:6px}
input[type=password]{font:inherit;font-size:1rem;padding:10px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg)}
.row{display:flex;align-items:center;gap:8px;font-size:.85rem;color:var(--muted)}
button{font:inherit;font-weight:600;padding:11px 14px;border:0;border-radius:8px;background:var(--navy);color:#fff;cursor:pointer}
button:disabled{opacity:.6;cursor:progress}
.err{color:var(--bad);font-size:.85rem;min-height:1.2em}
</style>
</head>
<body>
<main>
<form id="f" autocomplete="off">
  <div class="logo"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5c3.5 4.6 7 8.6 7 12.6a7 7 0 0 1-14 0c0-4 3.5-8 7-12.6z"/></svg></div>
  <h1>Centro de combustible · DPWL</h1>
  <p>Uso interno de DP World Logistics. Escribe la clave del equipo para ver el tablero.</p>
  <label>Clave<input type="password" id="k" required autofocus></label>
  <label class="row"><input type="checkbox" id="r"> Recordar en este equipo</label>
  <button id="b" type="submit">Entrar</button>
  <div class="err" id="e" role="alert"></div>
</form>
</main>
<script>
const SALT='__SALT__', IV='__IV__', CT='__CT__', ITER=__ITER__, KID='__KID__';
const ub=(s)=>Uint8Array.from(atob(s),(c)=>c.charCodeAt(0));
const LS='dpwl-comb-key';
async function abrir(key){
  const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:ub(IV)},key,ub(CT));
  const html=await new Response(new Blob([plain]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
  document.open(); document.write(html); document.close();
}
async function derivar(clave){
  const base=await crypto.subtle.importKey('raw',new TextEncoder().encode(clave),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt:ub(SALT),iterations:ITER,hash:'SHA-256'},base,{name:'AES-GCM',length:256},true,['decrypt']);
}
(async()=>{
  try{ const s=JSON.parse(localStorage.getItem(LS)||'null');
    if(s&&s.kid===KID){ const key=await crypto.subtle.importKey('raw',ub(s.k),{name:'AES-GCM'},false,['decrypt']); await abrir(key); return; } }catch(e){ try{localStorage.removeItem(LS);}catch(_){} }
})();
document.getElementById('f').addEventListener('submit',async(ev)=>{
  ev.preventDefault();
  const b=document.getElementById('b'), e=document.getElementById('e');
  b.disabled=true; b.textContent='Abriendo…'; e.textContent='';
  try{
    const key=await derivar(document.getElementById('k').value);
    if(document.getElementById('r').checked){
      try{ const raw=new Uint8Array(await crypto.subtle.exportKey('raw',key)); localStorage.setItem(LS,JSON.stringify({kid:KID,k:btoa(String.fromCharCode(...raw))})); }catch(_){}
    }
    await abrir(key);
  }catch(err){ e.textContent='Clave incorrecta.'; b.disabled=false; b.textContent='Entrar'; try{localStorage.removeItem(LS);}catch(_){} }
});
</script>
</body>
</html>
"""
page = (page.replace('__SALT__', b64(salt)).replace('__IV__', b64(iv)).replace('__CT__', b64(ct))
        .replace('__ITER__', str(ITER)).replace('__KID__', kid))
os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
open(out, 'w', encoding='utf-8').write(page)
print(out, round(os.path.getsize(out) / 1e6, 2), 'MB')
