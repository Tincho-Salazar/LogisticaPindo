/* Cliente de la API: sesión (JWT + refresh rotativo), llamadas, caché del último estado y cola de salida (outbox)
   para trabajar sin conexión. Todo lo que se envía lleva un id generado acá (idempotente en el servidor). */
var API = (function(){
  var BASE = '/api/v1', TK = 'lf.sesion', SK = 'lf.estado', OK = 'lf.outbox';
  var sesion = leer(TK) || null;

  function leer(k){ try{ return JSON.parse(localStorage.getItem(k)); }catch(e){ return null; } }
  function guardar(k, v){ try{ if(v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  function uuid(){
    if(window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var b = new Uint8Array(16); crypto.getRandomValues(b); b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    var h = Array.prototype.map.call(b, function(x){ return ('0' + x.toString(16)).slice(-2); }).join('');
    return h.slice(0, 8) + '-' + h.slice(8, 12) + '-' + h.slice(12, 16) + '-' + h.slice(16, 20) + '-' + h.slice(20);
  }

  function ErrorApi(status, body){ this.status = status; this.codigo = body && body.codigo || 'error'; this.mensaje = body && body.mensaje || ('Error ' + status); this.detalle = body && body.detalle || {}; this.offline = status === 0; }
  ErrorApi.prototype = Object.create(Error.prototype);

  var refrescando = null;
  function refrescar(){
    if(refrescando) return refrescando;
    if(!sesion || !sesion.refresh_token) return Promise.reject(new ErrorApi(401, { codigo: 'no_autenticado', mensaje: 'Iniciá sesión' }));
    refrescando = fetch(BASE + '/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: sesion.refresh_token }) })
      .then(function(r){ return r.json().then(function(j){ if(!r.ok) throw new ErrorApi(r.status, j); return j; }); })
      .then(function(j){ sesion = j; guardar(TK, j); return j; })
      .catch(function(e){ if(!e.offline && e.status !== 0 && e.status < 500) cerrar(); throw e; })
      .finally(function(){ refrescando = null; });
    return refrescando;
  }

  function llamar(metodo, ruta, body, opts){
    opts = opts || {};
    var h = {};
    if(sesion && sesion.access_token) h['Authorization'] = 'Bearer ' + sesion.access_token;
    var init = { method: metodo, headers: h };
    if(body instanceof FormData){ init.body = body; }
    else if(body !== undefined && body !== null){ h['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
    return fetch(BASE + ruta, init).catch(function(){ throw new ErrorApi(0, { codigo: 'sin_conexion', mensaje: 'Sin conexión' }); }).then(function(r){
      if(r.status === 401 && !opts.reintento && sesion){
        return refrescar().then(function(){ return llamar(metodo, ruta, body, { reintento: true, blob: opts.blob }); });
      }
      if(opts.blob){ if(!r.ok) return r.json().then(function(j){ throw new ErrorApi(r.status, j); }); return r.blob(); }
      return r.text().then(function(t){ var j = null; try{ j = t ? JSON.parse(t) : null; }catch(e){ j = { mensaje: t }; } if(!r.ok) throw new ErrorApi(r.status, j); return j; });
    });
  }

  function login(usuario, password){
    return llamar('POST', '/auth/login', { usuario: usuario, password: password, dispositivo: navigator.userAgent.slice(0, 160) }).then(function(j){ sesion = j; guardar(TK, j); return j; });
  }
  function cerrar(){
    var rt = sesion && sesion.refresh_token;
    sesion = null; guardar(TK, null); guardar(SK, null);
    if(rt && navigator.onLine) fetch(BASE + '/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }) }).catch(function(){});
  }

  // ---------- cola de salida ----------
  var outbox = leer(OK) || [], FK = 'lf.fallas', fallasPersist = leer(FK) || [];
  function isoAhora(){
    var d = new Date(), p = function(n){ return ('0' + n).slice(-2); };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  function encolar(op){
    op.id = op.id || uuid();
    op.creado_en = op.creado_en || isoAhora();
    if(op.body && typeof op.body === 'object' && !(op.body instanceof FormData) && !op.body.ocurrido_en){
      op.body.ocurrido_en = op.creado_en;
    } else if(!op.body && (op.metodo === 'POST' || op.metodo === 'PUT')){
      op.body = { ocurrido_en: op.creado_en };
    } else if(op.metodo === 'DELETE' && op.ruta.indexOf('ocurrido_en=') < 0){
      op.ruta += (op.ruta.indexOf('?') >= 0 ? '&' : '?') + 'ocurrido_en=' + encodeURIComponent(op.creado_en);
    }
    op.reintentos = 0;
    outbox.push(op);
    try{
      localStorage.setItem(OK, JSON.stringify(outbox));
    }catch(e){
      // Si se llenó localStorage por fotos pesadas, quitar la foto base64 y conservar los datos del remito
      if(op.foto){ delete op.foto; try{ localStorage.setItem(OK, JSON.stringify(outbox)); }catch(x){} }
    }
    return op;
  }
  function pendientes(){ return outbox.length; }
  var enviando = false;
  function enviarCola(onCada){
    if(enviando || !outbox.length || !navigator.onLine) return Promise.resolve(0);
    enviando = true;
    var n = 0, fallas = [];
    function paso(){
      if(!outbox.length){ enviando = false; guardar(OK, outbox); return Promise.resolve({ enviados: n, fallas: fallas }); }
      var op = outbox[0];
      var p = op.foto ? subirYCrearRemito(op) : llamar(op.metodo, op.ruta, op.body);
      return p.then(function(){ outbox.shift(); n++; guardar(OK, outbox); if(onCada) onCada(op, null); return paso(); }, function(e){
        // Error de red o error transitorio del servidor (5xx / 429): NO se descarta de la cola, se reintenta luego
        if(e.offline || e.status === 0 || e.status >= 500 || e.status === 429){
          op.reintentos = (op.reintentos || 0) + 1;
          enviando = false; guardar(OK, outbox); return { enviados: n, fallas: fallas };
        }
        // Error de negocio definitivo (409, 422...): se retira de la cola, queda registrado como "error de sincronización" y se notifica a la app
        outbox.shift(); guardar(OK, outbox); fallas.push({ op: op, error: e });
        fallasPersist.push({ id: op.id, desc: op.desc || op.ruta, creado_en: op.creado_en, en: isoAhora(), mensaje: e.mensaje, codigo: e.codigo }); guardar(FK, fallasPersist);
        if(onCada) onCada(op, e); return paso();
      });
    }
    return paso();
  }
  function subirYCrearRemito(op){
    if(op.borrador_id){
      return llamar('POST', '/remitos', Object.assign({}, op.body, { borrador_id: op.borrador_id }));
    }
    var fd = new FormData();
    fd.append('archivo', dataUrlABlob(op.foto), 'remito.jpg');
    return llamar('POST', '/remitos/foto?camion_id=' + encodeURIComponent(op.body.camion_id), fd).then(function(b){
      op.borrador_id = b.borrador_id;
      delete op.foto; // libera espacio en localStorage y evita re-subir la foto si se corta antes de POST /remitos
      guardar(OK, outbox);
      return llamar('POST', '/remitos', Object.assign({}, op.body, { borrador_id: b.borrador_id }));
    });
  }
  function dataUrlABlob(u){
    var p = u.split(','), bin = atob(p[1]), arr = new Uint8Array(bin.length);
    for(var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new Blob([arr], { type: 'image/jpeg' });
  }

  return {
    uuid: uuid, ErrorApi: ErrorApi, llamar: llamar, login: login, cerrar: cerrar, refrescar: refrescar,
    sesion: function(){ return sesion; }, usuario: function(){ return sesion && sesion.usuario; },
    estadoCache: function(){ return leer(SK); }, guardarEstado: function(s){ guardar(SK, s); },
    encolar: encolar, pendientes: pendientes, enviarCola: enviarCola, outbox: function(){ return outbox; },
    fallas: function(){ return fallasPersist; }, quitarFalla: function(id){ fallasPersist = fallasPersist.filter(function(f){ return f.id !== id; }); guardar(FK, fallasPersist); },
    descargar: function(ruta, nombre){
      return llamar('GET', ruta, null, { blob: true }).then(function(b){
        var u = URL.createObjectURL(b), a = document.createElement('a'); a.href = u; a.download = nombre; document.body.appendChild(a); a.click();
        setTimeout(function(){ URL.revokeObjectURL(u); a.remove(); }, 4000);
      });
    }
  };
})();
