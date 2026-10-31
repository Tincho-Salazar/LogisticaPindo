/* Estado de la app (S = última instantánea del servidor) y utilidades de formato y consulta. */
var S = API.estadoCache() || null;
var ui = { vista: 'app', rol: null, step: null, tab: null, camionId: null, contrId: null, fdia: 'hoy', ftipo: 'todos', festado: 'todos', fcirc: 'industria', acirc: 'todos', avista: 'punto',
           sheet: null, draft: null, error: '', open: {}, msg: '', msgErr: false, updAt: '', off: !navigator.onLine, cargando: false, analisis: null, analisisCirc: null, basPat: '', basErr: '', remTok: 0, editPerfil: false, tema: 'auto' };
try{
  var _p = JSON.parse(localStorage.getItem('lf.pref'));
  if(_p){
    ui.rol = _p.rol || null;
    ui.camionId = _p.camionId || null;
    ui.contrId = _p.contrId || null;
    ui.tema = _p.tema || 'auto';
  }
}catch(e){}
if(ui.tema && ui.tema !== 'auto'){
  document.documentElement.setAttribute('data-theme', ui.tema);
}
if(S && S.rol !== ui.rol) S = null;

var TIPOS_EMP = [['transporte', 'Transporte'], ['elaborador', 'Elaborador'], ['pindo', 'Pindó SA']];
var PUESTOS = ['Capataz', 'Mecánico', 'Maquinista', 'Chofer', 'Supervisor', 'Jefe de Área Forestal', 'Otro'];
var CIRC = { industria: 'Industria propia', ventas: 'Ventas' };
var ESTADOS = { disponible: 'Disponible', fila: 'En fila de espera', cargando: 'Cargando', ruta: 'En ruta · cargado', vacio: 'Vacío · retorno' };
var ESTADOS_CHIP = { disponible: 'Disponibles', fila: 'En fila', cargando: 'Cargando', ruta: 'En ruta', vacio: 'Vacíos' };
var MOTIVOS = { mecanico: ['Neumático', 'Frenos', 'Motor', 'Sistema eléctrico', 'Acoplado o pluma', 'Otro'], demora: ['Espera en balanza', 'Espera para descargar', 'Ruta o camino cortado', 'Clima', 'Documentación', 'Otro'] };
var ROLES = { supervisor: 'Supervisor', transportista: 'Transportista', elaborador: 'Elaborador', bascula: 'Báscula Pindó', jefe: 'Jefe de Área Forestal', admin: 'Administración' };
var PRIO = { pindo: 'Stock Pindó SA', ventas: 'Stock de ventas' };
var TABS = {
  jefe: [['tarifas', 'Tarifario', 'cargas']],
  admin: [['usuarios', 'Usuarios', 'truck'], ['catalogos', 'Catálogos', 'cargas']],
  supervisor: [['stock', 'Stock', 'stock'], ['camiones', 'Camiones', 'truck'], ['programa', 'Programa', 'programa'], ['pedidos', 'Pedidos', 'cargas'], ['analisis', 'Análisis', 'cargas']],
  elaborador: [['stock', 'Mi stock', 'stock'], ['cola', 'Cola de carga', 'cola'], ['programa', 'Programa', 'programa'], ['pedido', 'Pedido', 'cargas']],
  transportista: [['viaje', 'Mi viaje', 'viaje'], ['programa', 'Programa', 'programa'], ['fletes', 'Fletes', 'cargas']],
  bascula: [['pend', 'Báscula', 'balanza'], ['industria', 'A industria', 'viaje'], ['hist', 'Horarios', 'programa']]
};
var ICON = {
  stock: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16M6 4v16M18 4v16" stroke-linecap="round"/></svg>',
  truck: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h11v11H3zM14 9h4l3 3v5h-7z"/><circle cx="7.5" cy="17.5" r="2"/><circle cx="17.5" cy="17.5" r="2"/></svg>',
  cargas: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4z"/><path d="M4 9h16M9 4v16M14 9v11"/></svg>',
  programa: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="17" rx="3"/><path d="M3 9h18M8 2v4M16 2v4"/><circle cx="8" cy="14" r="1.2" fill="currentColor"/><circle cx="12" cy="14" r="1.2" fill="currentColor"/><circle cx="16" cy="14" r="1.2" fill="currentColor"/></svg>',
  cola: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke-linecap="round"/></svg>',
  balanza: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v18M5 21h14M3 8h18"/><path d="M3 8l3.5 6h5L8 8zM12.5 8l3.5 6h5L17.5 8z"/></svg>',
  viaje: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-5.5-7-10.5a7 7 0 1 1 14 0c0 5-7 10.5-7 10.5z"/><circle cx="12" cy="10.5" r="2.5"/></svg>',
  sun: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" stroke-linecap="round"/></svg>',
  moon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
  chev: '<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};

// ---------- formato ----------
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
function f1(n){ return Number(n || 0).toLocaleString('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); }
function fl(n){ return Number(n).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + ' pies'; }
function num(s){ var v = parseFloat(String(s == null ? '' : s).replace(/\./g, function(m, i, str){ return str.indexOf(',') >= 0 ? '' : m; }).replace(',', '.')); return isFinite(v) ? v : NaN; }
function numSimple(s){ var v = parseFloat(String(s == null ? '' : s).replace(',', '.')); return isFinite(v) ? v : NaN; }
function sum(a, fn){ return (a || []).reduce(function(t, x){ return t + (fn ? fn(x) : x); }, 0); }
function money(n){ return '$ ' + String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }
function pad(n){ return ('0' + n).slice(-2); }
function hhmm(d){ d = d || new Date(); return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
function isoLocal(d){ d = d || new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()); }
function hm(iso){ return iso ? String(iso).slice(11, 16) : ''; }
function dia(iso){ return iso ? String(iso).slice(0, 10) : ''; }
function diaLabel(k){ if(!k) return ''; var a = String(k).slice(0, 10).split('-'); return a[2] + '/' + a[1]; }
function fechaLarga(k){ var s = new Date(k + 'T12:00:00').toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }); return s.charAt(0).toUpperCase() + s.slice(1); }
function today(){ return S ? fechaLarga(S.hoy) : ''; }
function tomorrow(){ return S ? fechaLarga(S.manana) : ''; }
function mins(s){ if(!s) return 0; var a = String(s).split(':'); return parseInt(a[0], 10) * 60 + parseInt(a[1], 10); }
function fmtMin(m){ m = Math.round(m || 0); return m >= 60 ? Math.floor(m / 60) + ' h ' + pad(m % 60) + ' min' : m + ' min'; }
function lleva(iso){ if(!iso) return 0; return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)); }
function jk(d){ return d === 'manana' ? S.manana : S.hoy; }
function dKey(off){ var d = new Date(); d.setDate(d.getDate() - (off || 0)); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
function uid(){ return API.uuid(); }
function tipoLabel(t){ return t === 'fino' ? 'Rollo fino' : 'Rollo grueso'; }
function tipoCam(c){ return c && c.traccion === '4x2' ? '4x2' : '6x4'; }
function normPat(x){ return String(x || '').toUpperCase().replace(/[^A-Z0-9]/g, ''); }
function errorTexto(e){ return e && e.mensaje ? e.mensaje : 'No se pudo completar la acción'; }

// ---------- consultas sobre S ----------
function camiones(){ return (S && S.camiones) || []; }
function activos(){ return camiones().filter(function(c){ return c.alta_estado === 'aprobada'; }); }
function altasPend(){ return camiones().filter(function(c){ return c.alta_estado === 'pendiente'; }); }
function camion(id){ return camiones().filter(function(c){ return c.id === id; })[0] || null; }
function contratistas(){ return (S && S.contratistas) || []; }
function contrNombre(id){ var c = contratistas().filter(function(x){ return x.id === id; })[0]; return c ? c.nombre : ''; }
function destinos(circ){ return ((S && S.destinos) || []).filter(function(d){ return !circ || d.circuito === circ; }); }
function destino(id){ return destinos().filter(function(d){ return d.id === id; })[0] || null; }
function especies(){ return (S && S.especies) || []; }
function largos(){ return (S && S.largos) || [8, 10, 12, 14, 16, 18, 20]; }
function rodales(){ return (S && (S.rodales || S.rodales_catalogo)) || []; }
function rodal(id){ return rodales().filter(function(r){ return r.id === id; })[0] || null; }
function rodalesDe(cid){ return rodales().filter(function(r){ return r.contratista_id === cid; }); }
function tarifas(){ return (S && S.tarifas) || []; }
function tarifaLin(rid, did){ return tarifas().filter(function(t){ return t.rodal_id === rid && t.destino_id === did; })[0] || null; }
function pilas(){ return (S && S.pilas) || []; }
function pilasDe(cid){ return pilas().filter(function(p){ return p.contratista_id === cid && p.volumen_m3 > 0; }); }
function pila(id){ return pilas().filter(function(p){ return p.id === id; })[0]; }
function esVentas(p){ return p.uso === 'ventas'; }
function cargas(){ return (S && S.cargas) || []; }
function carga(id){ return cargas().filter(function(k){ return k.id === id; })[0]; }
function cargasHoy(){ return cargas().filter(function(k){ return k.jornada === S.hoy || k.estado === 'en_curso'; }); }
function cargaTotal(k){ return sum(k.lineas, function(l){ return l.volumen_m3; }); }
function cargaTipo(k, t){ return sum((k.lineas || []).filter(function(l){ return l.tipo === t; }), function(l){ return l.volumen_m3; }); }
function programa(){ return (S && S.programa) || []; }
function prog(id){ return programa().filter(function(g){ return g.id === id; })[0]; }
function progDe(camionId, d){ var j = jk(d || 'hoy'); return programa().filter(function(g){ return g.jornada === j && g.camion_id === camionId && (g.estado === 'programado' || g.estado === 'cargando'); })[0]; }
function colaDe(cid, d){ var j = jk(d || 'hoy'); return programa().filter(function(g){ return g.jornada === j && g.contratista_id === cid && (g.estado === 'programado' || g.estado === 'cargando'); }).sort(function(a, b){ return a.hora < b.hora ? -1 : a.hora > b.hora ? 1 : 0; }); }
function emitido(d){ return S && S.emitido ? S.emitido[d || 'manana'] : null; }
function prioDe(cid, d){ var m = S && S.prioridad && S.prioridad[jk(d || 'manana')]; return (m && m[cid]) || null; }
function solicDe(cid){ var m = S && S.solicitud && S.solicitud[S.manana]; return (m && m[cid]) || null; }
function inicioElabDe(cid, d){ var m = S && S.inicio_carga && S.inicio_carga[jk(d || 'manana')]; return (m && m[cid]) || null; }
function inicioFrente(cid, d){ var m = inicioElabDe(cid, d); if(m) return m.hora; var q = colaDe(cid, d); return q.length ? q[0].hora : null; }
function pedidoDe(cid){ if(!S) return null; if(S.pedido !== undefined) return S.pedido && S.pedido.contratista_id === cid ? S.pedido : null; return (S.pedidos && S.pedidos[cid]) || null; }
function mecanico(c){ return !!(c && c.inc && c.inc.tipo === 'mecanico'); }
function ultCarga(c){ return cargas().filter(function(x){ return x.camion_id === c.id && x.estado === 'finalizada'; }).sort(function(a, b){ return a.fin_en < b.fin_en ? 1 : -1; })[0]; }
function avisoDescargaOk(c){ var u = ultCarga(c); return !u || u.circuito === 'ventas'; }
function filaDe(cid){ return activos().filter(function(c){ return c.estado === 'fila' && c.fila_contratista_id === cid; }).sort(function(a, b){ return a.fila_desde < b.fila_desde ? -1 : 1; }); }
function stockDe(cid, tipo, largo, circ){ return sum(pilas().filter(function(p){ return p.contratista_id === cid && p.tipo === tipo && p.largo_pies === largo && !(circ === 'industria' && esVentas(p)); }), function(p){ return p.volumen_m3; }); }
function stockUso(cid){ var r = { pindo: { fino: 0, grueso: 0 }, ventas: { fino: 0, grueso: 0 } }; pilasDe(cid).forEach(function(p){ r[esVentas(p) ? 'ventas' : 'pindo'][p.tipo] += p.volumen_m3; }); return r; }
function relEstado(cid){
  var ps = pilas().filter(function(p){ return p.contratista_id === cid; });
  if(!ps.length) return { k: 'pendiente', t: 'Pendiente', hora: '' };
  var lp = ps.slice().sort(function(a, b){ return a.relevado_en < b.relevado_en ? 1 : -1; })[0], hora = hm(lp.relevado_en), quien = lp.relevado_por ? ' · ' + esc(lp.relevado_por) : '';
  if(dia(lp.relevado_en) < S.hoy) return { k: 'viejo', t: 'Relevó ' + diaLabel(lp.relevado_en) + ' ' + hora + quien, hora: hora };
  return hora > S.cierres.relevamiento ? { k: 'tarde', t: 'Tarde · ' + hora + quien, hora: hora } : { k: 'ok', t: 'Relevó ' + hora + quien, hora: hora };
}
function cierreTexto(){
  var m = mins(S.cierres.relevamiento) - mins(hhmm());
  if(m <= 0) return 'El horario de relevamiento ya cerró.';
  return 'Faltan ' + Math.floor(m / 60) + ' h ' + pad(m % 60) + ' min para el cierre.';
}
function relCerrado(){ return mins(hhmm()) >= mins(S.cierres.relevamiento); }
function dispAbierta(){ return mins(hhmm()) < mins(S.cierres.disponibilidad); }
function dispTxt(c){ var d = c.disp_manana; return !d ? 'Sin respuesta' : d.valor === 'si' ? 'Disponible (' + hm(d.respondida_en) + ')' : 'No disponible (' + hm(d.respondida_en) + ')'; }
function durProm(){ var xs = cargasHoy().filter(function(k){ return k.estado === 'finalizada' && k.inicio_en && k.fin_en; }).map(function(k){ return Math.max(0, (new Date(k.fin_en) - new Date(k.inicio_en)) / 60000); }); return xs.length ? Math.round(sum(xs) / xs.length) : 35; }
function estimado(cid, pos){ var curso = cargas().some(function(k){ return k.estado === 'en_curso' && k.contratista_id === cid; }); var d = durProm(); return Math.round((curso ? d / 2 : 0) + pos * d); }
function esperaProm(cid){ var xs = cargasHoy().filter(function(k){ return k.estado === 'finalizada' && k.espera_min != null && k.contratista_id === cid; }).map(function(k){ return k.espera_min; }); return xs.length ? Math.round(sum(xs) / xs.length) : null; }
function importeRem(r){ return r.importe || null; }
function remitos(){ return (S && S.remitos) || []; }
function remitosControl(){ return (S && S.remitos_control) || []; }
function remitoAny(id){ return remitos().concat(remitosControl()).filter(function(x){ return x.id === id; })[0] || null; }
function etaBadge(k){
  if(!k || k.circuito !== 'industria' || k.ingreso_en || k.retorno_en || !k.eta_en || k.jornada !== S.hoy) return '';
  var km = (k.km_asfalto || 0) + (k.km_tierra || 0);
  return '<span class="eta-badge">ETA <b>' + hm(k.eta_en) + ' hs</b>' + (k.viaje_est_min ? ' · ~' + k.viaje_est_min + ' min' : '') + (km > 0 ? ' (' + Math.round(km) + ' km)' : '') + '</span>';
}
function trazaSteps(k, conBotonRemito){
  if(!k) return '';
  var s1 = 'done', t1 = hm(k.fin_en) + ' · ' + f1(cargaTotal(k)) + ' m³';
  var s2 = 'pend', t2 = '';
  if(k.circuito === 'ventas'){ s2 = 'done'; t2 = 'Ventas directo'; }
  else if(k.salida_en){ s2 = 'done'; t2 = hm(k.ingreso_en) + '–' + hm(k.salida_en); }
  else if(k.ingreso_en){ s2 = 'act'; t2 = 'En planta ' + hm(k.ingreso_en); }
  else if(k.retorno_en){ s2 = 'done'; t2 = 'Ciclo cerrado'; }
  else { s2 = 'act'; t2 = (k.eta_en && k.jornada === S.hoy) ? 'ETA ' + hm(k.eta_en) : 'En ruta'; }
  var s3 = k.remito_id ? 'done' : 'pend';
  var t3 = k.remito_id ? ((k.remito_numero ? 'N° ' + esc(k.remito_numero) : 'Cargado') + ' · ' + f1(k.remito_tn) + ' tn') : 'Falta remito';
  return '<div class="traza-steps" aria-label="Trazabilidad del viaje">' +
    '<div class="tz-step ' + s1 + '"><span class="tz-dot">1</span><div class="tz-txt"><b>Monte</b><span>' + t1 + '</span></div></div>' +
    '<div class="tz-line ' + (s2 !== 'pend' ? 'on' : '') + '"></div>' +
    '<div class="tz-step ' + s2 + '"><span class="tz-dot">2</span><div class="tz-txt"><b>' + (k.circuito === 'ventas' ? 'Destino' : 'Báscula') + '</b><span>' + t2 + '</span></div></div>' +
    '<div class="tz-line ' + (s3 === 'done' ? 'on' : '') + '"></div>' +
    '<div class="tz-step ' + s3 + '">' + (conBotonRemito && k.remito_id ? '<button type="button" class="tz-btn" data-action="remito-ver" data-id="' + k.remito_id + '"><span class="tz-dot">3</span><div class="tz-txt"><b>Remito</b><span>' + t3 + '</span></div></button>' : '<span class="tz-dot">3</span><div class="tz-txt"><b>Remito</b><span>' + t3 + '</span></div>') + '</div>' +
  '</div>';
}
function soloLectura(){ return !!(S && S.solo_lectura); }
function esJefePuesto(){ var u = API.usuario(); return !!(u && (u.puesto === 'Jefe de Área Forestal' || misRoles().indexOf('admin') >= 0)); }
function misRoles(){ var u = API.usuario(); return (u && u.roles) || []; }
function rolOk(r){ var rs = misRoles(); return rs.indexOf(r) >= 0 || (rs.indexOf('jefe') >= 0 && (r === 'transportista' || r === 'elaborador')); }
function defaultTab(r){ return r === 'jefe' ? 'tarifas' : r === 'admin' ? 'usuarios' : r === 'elaborador' ? 'cola' : r === 'transportista' ? 'viaje' : r === 'bascula' ? 'pend' : 'stock'; }

// ---------- fragmentos de HTML reutilizables ----------
function estadoPill(c){ return '<span class="pill st-' + c.estado + '">' + ESTADOS[c.estado] + '</span>'; }
function incPill(c){ if(!c.inc) return ''; var t = c.inc.tipo === 'mecanico' ? 'Problema mecánico' : 'Demora' + (c.inc.minutos ? ' · ' + c.inc.minutos + ' min' : ''); return '<span class="pill inc-' + c.inc.tipo + '">' + t + '</span>'; }
function incBox(c){
  if(!c.inc) return ''; var i = c.inc;
  return '<div class="incbox inc-' + i.tipo + '"><b>' + (i.tipo === 'mecanico' ? 'Problema mecánico' : 'Demora') + ':</b> ' + esc(i.motivo) + (i.detalle ? ' · ' + esc(i.detalle) : '') +
    ' <span style="color:var(--muted)">(desde ' + hm(i.desde) + (i.minutos ? ', estimada ' + i.minutos + ' min' : '') + ')</span></div>';
}
function splitBar(fino, grueso){
  var t = fino + grueso, a = t ? fino / t * 100 : 0, b = t ? grueso / t * 100 : 0;
  return '<div class="split" role="img" aria-label="Fino ' + f1(fino) + ' m³, grueso ' + f1(grueso) + ' m³"><i style="width:' + a + '%;background:var(--fino)"></i><i style="width:' + b + '%;background:var(--grueso)"></i></div>' +
    '<div class="legend"><span><i class="dot fino"></i>Fino <b>' + f1(fino) + ' m³</b></span><span><i class="dot grueso"></i>Grueso <b>' + f1(grueso) + ' m³</b></span></div>';
}
function resumenItems(items){
  var map = {}, keys = [];
  (items || []).forEach(function(l){ var key = l.tipo + '|' + l.largo_pies; if(!map[key]){ map[key] = { tipo: l.tipo, largo_pies: l.largo_pies, m3: 0 }; keys.push(key); } map[key].m3 += (l.volumen_m3 || 0); });
  return keys.map(function(x){ return map[x]; }).sort(function(a, b){ return a.tipo === b.tipo ? a.largo_pies - b.largo_pies : (a.tipo === 'grueso' ? -1 : 1); });
}
function tablaItems(items){
  return '<table class="tbl"><thead><tr><th>Tipo</th><th>Largo</th><th>m³</th></tr></thead><tbody>' + resumenItems(items).map(function(r){
    return '<tr><td><span class="tag ' + r.tipo + '">' + tipoLabel(r.tipo) + '</span></td><td class="lg">' + fl(r.largo_pies) + '</td><td>' + f1(r.m3) + '</td></tr>';
  }).join('') + '</tbody></table>';
}
function progBar(pct){ return '<div class="prog" role="img" aria-label="Avance ' + pct + '%"><i style="width:' + pct + '%"></i></div>'; }
function errHtml(){ return ui.error ? '<p class="err" role="alert">' + esc(ui.error) + '</p>' : ''; }
function vacio(t, st){ return '<div class="empty"' + (st ? ' style="' + st + '"' : '') + '>' + t + '</div>'; }
function pendHtml(){ var n = API.pendientes(), f = API.fallas().length; if(!n && !f) return ''; return '<button type="button" class="pend' + (f ? ' err' : '') + '" data-action="outbox">' + (n ? n + ' cambio' + (n === 1 ? '' : 's') + ' guardado' + (n === 1 ? '' : 's') + ' en este dispositivo, pendiente' + (n === 1 ? '' : 's') + ' de enviar' : '') + (n && f ? ' · ' : '') + (f ? f + ' con error de sincronización' : '') + ' · ver</button>'; }
