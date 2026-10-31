/* Vistas por rol. Cada función devuelve HTML a partir de S (instantánea del servidor) y ui. */

// ---------- ingreso y registro ----------
function brand(){
  return '<div class="brand-header">' +
    '<img class="brand-img" src="/static/img/logo-pindo.png" alt="Pindó SA" width="96" height="71">' +
    '<div class="brand-title-wrap">' +
      '<h1 class="brand">Logística Forestal<span style="display:block;color:var(--accent)">Pindó SA</span></h1>' +
      '<span class="brand-tagline">Puerto Esperanza · Misiones</span>' +
    '</div>' +
  '</div>';
}
function viewLogin(){
  return '<div class="login">' + brand() + '<p class="lead">Ingresá con tu usuario.</p><form data-form="login" novalidate>' +
    '<div class="field"><label for="lg-u">Usuario</label><input class="input" id="lg-u" name="usuario" autocomplete="username" autocapitalize="none" spellcheck="false"></div>' +
    '<div class="field"><label for="lg-p">Contraseña</label><input class="input" id="lg-p" name="password" type="password" autocomplete="current-password"></div>' +
    errHtml() + '<button class="btn primary block" type="submit"' + (ui.cargando ? ' disabled' : '') + '>Ingresar</button></form>' +
    '<button class="btn block" data-action="ir-registro" style="margin-top:10px">No tengo usuario · Registrarme</button>' +
    '<p class="note" style="margin-top:16px">Un administrador de Pindó SA aprueba cada usuario nuevo antes del primer ingreso.</p></div>';
}
function viewRegistro(){
  var d = ui.draft || {};
  return '<div class="login">' + brand() + '<button class="backlink" data-action="ir-login">← Volver</button><p class="lead">Contanos quién sos.</p><form data-form="registro" novalidate>' +
    '<div class="field"><label for="rg-n">Nombre y apellido</label><input class="input" id="rg-n" name="nombre" autocomplete="name" value="' + esc(d.nombre) + '" placeholder="Ej.: Marcos Duarte"></div>' +
    '<div class="field"><label for="rg-e">Empresa a la que pertenecés</label><input class="input" id="rg-e" name="empresa" autocomplete="organization" value="' + esc(d.empresa) + '" placeholder="Razón social"></div>' +
    '<div class="field"><span class="lb" id="lb-te">Tipo de empresa</span><div class="seg" role="radiogroup" aria-labelledby="lb-te" style="flex-wrap:wrap">' + TIPOS_EMP.map(function(x){ return '<label><input type="radio" name="tipo_empresa" value="' + x[0] + '"' + (d.tipo_empresa === x[0] ? ' checked' : '') + '>' + x[1] + '</label>'; }).join('') + '</div></div>' +
    '<div class="field"><span class="lb" id="lb-pf">Puesto</span><div class="seg" role="radiogroup" aria-labelledby="lb-pf" style="flex-wrap:wrap">' + PUESTOS.map(function(x){ return '<label><input type="radio" name="puesto" value="' + esc(x) + '"' + (d.puesto === x ? ' checked' : '') + '>' + esc(x) + '</label>'; }).join('') + '</div></div>' +
    '<div class="two"><div class="field"><label for="rg-u">Usuario</label><input class="input" id="rg-u" name="usuario" autocomplete="username" autocapitalize="none" value="' + esc(d.usuario) + '" placeholder="ej. jperez"></div>' +
    '<div class="field"><label for="rg-p">Contraseña (8+)</label><input class="input" id="rg-p" name="password" type="password" autocomplete="new-password"></div></div>' +
    '<p class="note" style="margin:-4px 0 12px">Elegí "Otro" en puesto si sos operador de báscula; "Pindó SA" como tipo de empresa si trabajás en la empresa. Tu nombre queda registrado en relevamientos, cargas y remitos.</p>' +
    errHtml() + '<button class="btn primary block" type="submit"' + (ui.cargando ? ' disabled' : '') + '>Enviar registro</button></form></div>';
}
function viewPerfil(){
  var u = API.usuario();
  return '<div class="login">' + brand() + '<button class="backlink" data-action="cancelar-perfil">← Volver</button><p class="lead">Tus datos</p><form data-form="perfil" novalidate>' +
    '<div class="field"><label for="pf-n">Nombre y apellido</label><input class="input" id="pf-n" name="nombre" value="' + esc(u.nombre) + '"></div>' +
    '<div class="field"><label for="pf-e">Empresa</label><input class="input" id="pf-e" name="empresa" value="' + esc(u.empresa) + '"></div>' +
    '<div class="field"><span class="lb" id="lb-pf">Puesto</span><div class="seg" role="radiogroup" aria-labelledby="lb-pf" style="flex-wrap:wrap">' + PUESTOS.map(function(x){ return '<label><input type="radio" name="puesto" value="' + esc(x) + '"' + (u.puesto === x ? ' checked' : '') + '>' + esc(x) + '</label>'; }).join('') + '</div></div>' +
    errHtml() + '<button class="btn primary block" type="submit">Guardar cambios</button><button type="button" class="btn block" data-action="cancelar-perfil" style="margin-top:8px">Cancelar</button></form></div>';
}

// ---------- selección de rol ----------
function viewRol(){
  var u = API.usuario(), out = brand(), jefe = esJefePuesto();
  if(!ui.step){
    out += '<p class="note" style="margin:0 0 8px">Hola, <b>' + esc(u.nombre) + '</b> · ' + esc(u.puesto) + ' · ' + esc(u.empresa) + ' <button class="link" data-action="editar-perfil">Editar</button> <button class="link" data-action="salir">Salir</button></p><p class="lead">¿Con qué rol entrás?</p>';
    var cards = [['transportista', jefe ? 'Transporte · solo lectura: ver el panel de un camión con su viaje, programa y fletes.' : 'Ver tu carga programada y la disponibilidad del contratista. Avisar si descargaste, tenés una falla mecánica o una demora.'],
      ['elaborador', jefe ? 'Cosecha · solo lectura: ver el panel de un contratista con su stock, cola de carga, programa y pedido.' : 'Relevar el stock de tu contratista, ver la cola de camiones e iniciar y finalizar cargas.'],
      ['bascula', 'Registrar ingreso y salida de cada camión en planta, horarios y descansos.'],
      ['supervisor', 'Ver todo: stock, camiones, novedades y despachos. Armar y emitir el programa de carga.'],
      ['jefe', 'Cargar y actualizar el tarifario de fletes: rodales, destinos, km y tarifas por tipo de camión.'],
      ['admin', 'Aprobar usuarios nuevos, asignar roles y administrar catálogos.']];
    out += cards.filter(function(r){ return rolOk(r[0]) || (r[0] !== 'admin' && r[0] !== 'jefe'); }).map(function(r){
      if(!rolOk(r[0])) return '<div class="rolcard" aria-disabled="true" style="opacity:.5;cursor:not-allowed"><span class="rt">' + ROLES[r[0]] + ' · bloqueado</span><span class="rd">No corresponde a tu rubro.</span></div>';
      return '<button class="rolcard" data-action="rol" data-v="' + r[0] + '"><span class="rt">' + ROLES[r[0]] + '</span><span class="rd">' + r[1] + '</span></button>';
    }).join('');
    if(S && S.modo_prueba) out += '<p class="note" style="margin-top:14px">Modo de prueba activo: todos los roles están habilitados. En producción el rol sale del usuario.</p>';
  } else if(ui.step === 'transportista'){
    var cs = camiones();
    out += '<button class="backlink" data-action="rol-back">← Volver</button><p class="lead">' + (jefe ? '¿Qué camión querés ver?' : '¿Qué camión manejás?') + '</p>' +
      (ui.cargando ? '<p class="note"><span class="spinner"></span> Cargando…</p>' : cs.length ? '<div class="list" style="margin-top:0">' + cs.map(function(c){
        return '<button class="rolcard" style="margin:0" data-action="rol-camion" data-id="' + c.id + '"><span class="rt" style="font-family:var(--font-mono);font-size:19px;letter-spacing:.06em">' + esc(c.patente) + '</span><span class="rd">' + esc(c.chofer) + ' · ' + esc(c.empresa) + (c.alta_estado === 'pendiente' ? ' · alta pendiente de aprobación' : c.alta_estado === 'rechazada' ? ' · alta rechazada' : '') + '</span></button>';
      }).join('') + '</div>' : vacio('Todavía no diste de alta ningún camión con tu nombre.', 'margin-top:0')) +
      (jefe ? '' : '<button class="btn block" data-action="alta-camion" style="margin-top:14px">Mi camión no está en la lista · Darme de alta</button>');
  } else {
    out += '<button class="backlink" data-action="rol-back">← Volver</button><p class="lead">¿Qué contratista querés ver?</p><div class="list" style="margin-top:0">' +
      contratistas().map(function(c){ return '<button class="rolcard" style="margin:0" data-action="rol-contr" data-id="' + c.id + '"><span class="rt" style="font-size:21px">' + esc(c.nombre) + '</span></button>'; }).join('') + '</div>';
  }
  return '<div style="padding-bottom:30px">' + out + '</div>';
}
function viewAlta(c){
  var rech = c.alta_estado === 'rechazada';
  return '<div style="padding-bottom:30px">' + brand() + '<button class="backlink" data-action="cambiar-rol">← Volver</button><p class="lead">' + (rech ? 'Tu alta fue rechazada' : 'Alta pendiente de aprobación') + '</p>' +
    '<article class="truck"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span><span class="pill ' + (rech ? 'inc-mecanico' : 'inc-demora') + '">' + (rech ? 'Rechazada' : 'Pendiente') + '</span></div>' +
    '<div><div class="who">' + esc(c.chofer) + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b></span><span>Enviada ' + hm(c.alta_en) + '</span></div></div></article>' +
    '<p class="note" style="margin-top:12px">' + (rech ? 'El supervisor no aceptó el alta. Revisá los datos con él y volvé a cargarla.' : 'El supervisor tiene que aceptar tu alta para que puedas ver tu programa de carga. Volvé a abrir la app en unos minutos.') + '</p>' +
    (rech ? '<button class="btn primary block" data-action="alta-reintentar" data-id="' + c.id + '" style="margin-top:12px">Volver a cargar el alta</button>' : '') +
    '<button class="btn block" data-action="cambiar-rol" style="margin-top:8px">Volver</button></div>';
}

// ---------- cabecera y navegación ----------
function header(){
  var t = ui.tab, r = ui.rol, title = '', sub = '', act = '', ro = soloLectura();
  var nov = activos().filter(function(c){ return c.inc; }).length;
  if(t === 'stock'){
    var all = r === 'elaborador' ? pilas() : pilas();
    title = r === 'elaborador' ? 'Mi stock' : 'Stock en pila';
    sub = (r === 'elaborador' ? esc(contrNombre(S.contratista_id)) : today()) + ' · <b>' + f1(sum(all, function(p){ return p.volumen_m3; })) + ' m³</b> pendientes';
    if(!ro) act = '<button class="btn primary" data-action="new-pila">+ Relevar</button>';
  } else if(t === 'camiones'){ title = 'Camiones'; sub = '<b>' + activos().filter(function(c){ return c.estado === 'disponible' && !c.inc; }).length + '</b> disponibles · <b>' + nov + '</b> con novedad'; act = '<button class="btn primary" data-action="nuevo-camion">+ Camión</button>'; }
  else if(t === 'programa'){
    title = 'Programa de carga'; sub = '<b>' + programa().filter(function(g){ return g.jornada === jk(ui.fdia) && (g.estado === 'programado' || g.estado === 'cargando'); }).length + '</b> camiones programados ' + (ui.fdia === 'hoy' ? 'hoy' : 'para mañana');
    if(r === 'supervisor') act = '<button class="btn primary" data-action="programar">+ Programar</button>';
    if(r === 'elaborador') sub = esc(contrNombre(S.contratista_id)) + ' · ' + tomorrow();
    if(r === 'transportista') sub = esc((camion(ui.camionId) || {}).patente) + ' · ' + (ui.fdia === 'manana' ? tomorrow() : 'hoy');
  }
  else if(t === 'pedidos'){ title = 'Pedidos de rollos'; sub = '<b>' + contratistas().filter(function(c){ return pedidoDe(c.id); }).length + '</b> de ' + contratistas().length + ' contratistas con pedido · ' + tomorrow(); }
  else if(t === 'pedido'){ title = 'Pedido de rollos'; sub = esc(contrNombre(S.contratista_id)) + ' · ' + tomorrow(); }
  else if(t === 'tarifas'){ title = 'Tarifario de fletes'; sub = '<b>' + rodales().length + '</b> rodales · ' + tarifas().length + ' tarifas'; act = '<button class="btn primary" data-action="rodal-new">+ Rodal</button>'; }
  else if(t === 'fletes'){ var cf = camion(ui.camionId); title = 'Mis fletes'; sub = esc(cf ? cf.patente : '') + ' · ' + tipoCam(cf) + ' · tarifas y facturación'; }
  else if(t === 'analisis'){ title = 'Análisis de transportistas'; sub = 'Ciclo de salida y retorno al punto de carga'; }
  else if(t === 'cola'){ title = 'Cola de carga'; sub = esc(contrNombre(S.contratista_id)); }
  else if(t === 'pend'){ title = 'Báscula Pindó'; sub = '<b>' + enCamino().length + '</b> en camino · <b>' + enDescarga().length + '</b> en descarga'; }
  else if(t === 'industria'){ var ki = cargas().filter(function(k){ return k.estado === 'finalizada' && k.circuito === 'industria' && k.jornada === S.hoy; }); title = 'Cargados a industria'; sub = '<b>' + ki.filter(function(k){ return !k.salida_en; }).length + '</b> por descargar · ' + ki.length + ' hoy'; }
  else if(t === 'hist'){ title = 'Horarios de báscula'; sub = 'Ingresos, salidas y tiempos de descarga'; }
  else if(t === 'viaje'){ var cv = camion(ui.camionId); title = 'Mi viaje'; sub = esc(cv ? cv.patente + ' · ' + cv.chofer : ''); }
  else if(t === 'usuarios'){ title = 'Usuarios'; sub = '<b>' + ((ui.usuarios || []).filter(function(u){ return !u.activo; }).length) + '</b> pendientes de aprobación'; }
  else if(t === 'catalogos'){ title = 'Catálogos'; sub = 'Contratistas, destinos, especies y largos'; }

  var defT = defaultTab(r);
  var backBtn = '';
  if(t !== defT){
    backBtn = '<button class="backlink-hdr" data-action="nav-back" title="Volver a la vista principal">← Volver</button>';
  } else if(r === 'transportista' && ui.camionId){
    backBtn = '<button class="backlink-hdr" data-action="cambiar-camion" title="Elegir otro camión">← Camiones</button>';
  } else if(r === 'elaborador' && (esJefePuesto() || (contratistas().length > 1))){
    backBtn = '<button class="backlink-hdr" data-action="cambiar-contr" title="Elegir otro contratista">← Contratistas</button>';
  } else {
    backBtn = '<button class="backlink-hdr" data-action="cambiar-rol" title="Volver a selección de roles">← Roles</button>';
  }

  return '<header class="top">' +
    '<div class="hdr-title-group">' +
      backBtn +
      '<div style="min-width:0"><h1>' + title + '</h1><p class="sub">' + sub + '</p></div>' +
    '</div>' +
    (ro ? '' : act) +
  '</header>';
}
function connChip(){
  var off = ui.off || navigator.onLine === false, n = API.pendientes(), f = API.fallas().length;
  var txt = off ? 'Sin conexión · Guardado en este dispositivo' + (n ? ' · ' + n + ' pendiente' + (n === 1 ? '' : 's') + ' sin enviar' : '') : (n ? n + ' pendiente' + (n === 1 ? '' : 's') + ' sin enviar · sincronizando…' : 'En línea · Confirmado en servidor');
  if(f) txt += ' · ' + f + ' con error';
  var cls = 'conn' + (f ? ' err' : off ? ' off' : n ? ' sync' : ' ok');
  return (n || f) ? '<button class="' + cls + '" data-action="outbox" title="Ver operaciones pendientes y errores de sincronización">' + txt + ' · ver</button>' : '<span class="' + cls + '" role="status">' + txt + '</span>';
}
function flujoSupervisorBar(){
  var ac = activos(), progHoy = programa().filter(function(g){ return g.jornada === S.hoy; });
  var nProg = progHoy.filter(function(g){ return g.estado === 'programado' && (!camion(g.camion_id) || camion(g.camion_id).estado === 'disponible'); }).length;
  var nFila = ac.filter(function(c){ return c.estado === 'fila'; }).length;
  var nCarga = ac.filter(function(c){ return c.estado === 'cargando'; }).length;
  var nRuta = ac.filter(function(c){ return c.estado === 'ruta'; }).length;
  var nBasc = (cargas().filter(function(k){ return k.jornada === S.hoy && k.ingreso_en; })).length;
  var novs = ac.filter(function(c){ return c.inc; }).length;

  return '<section class="op-stream" aria-label="Flujo operativo en tiempo real">' +
    '<div class="op-stream-h"><b>Flujo operativo de hoy</b><span>' + progHoy.length + ' camiones programados</span></div>' +
    '<div class="op-stream-flow">' +
      '<div class="op-step"><span class="op-val">' + nProg + '</span><span class="op-lbl">Programados</span></div>' +
      '<div class="op-arrow">→</div>' +
      '<div class="op-step"><span class="op-val' + (nFila ? ' warn' : '') + '">' + nFila + '</span><span class="op-lbl">En espera</span></div>' +
      '<div class="op-arrow">→</div>' +
      '<div class="op-step"><span class="op-val' + (nCarga ? ' busy' : '') + '">' + nCarga + '</span><span class="op-lbl">Cargando</span></div>' +
      '<div class="op-arrow">→</div>' +
      '<div class="op-step"><span class="op-val' + (nRuta ? ' info' : '') + '">' + nRuta + '</span><span class="op-lbl">En viaje</span></div>' +
      '<div class="op-arrow">→</div>' +
      '<div class="op-step"><span class="op-val ok">' + nBasc + '</span><span class="op-lbl">En planta</span></div>' +
    '</div>' +
    (novs ? '<div class="op-alert"><span class="pill inc-mecanico">Novedades</span> <b>' + novs + '</b> camión' + (novs === 1 ? '' : 'es') + ' con falla mecánica o demora reportada.</div>' : '') +
  '</section>';
}
function roleBar(){
  var u = API.usuario();
  var who = esc(u.nombre) + ' · ' + ROLES[ui.rol] + (ui.rol === 'transportista' && camion(ui.camionId) ? ' · ' + esc(camion(ui.camionId).patente) : ui.rol === 'elaborador' ? ' · ' + esc(contrNombre(S.contratista_id)) : '');
  var esDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  var iconTema = esDark ? ICON.sun : ICON.moon;
  var titleTema = esDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
  return '<div class="bar-pindo-strip" aria-hidden="true"></div>' +
    '<div class="bar">' + (S && S.modo_prueba ? '<span class="demo">Modo de prueba</span>' : '') + connChip() +
    '<div class="bar-actions">' +
    '<button class="rolbtn icon-only" data-action="toggle-theme" title="' + titleTema + '" aria-label="' + titleTema + '">' + iconTema + '</button>' +
    '<button class="rolbtn" data-action="actualizar" aria-label="Actualizar datos">' + (ui.cargando ? '<span class="spinner"></span>' : '<svg class="ico-refresh" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>') + ' Actualizar · ' + esc(ui.updAt || '--:--') + '</button>' +
    (ui.rol === 'transportista' && ui.camionId ? '<button class="rolbtn" data-action="cambiar-camion" title="Elegir otro camión">🚚 Cambiar camión</button>' : '') +
    (ui.rol === 'elaborador' && (esJefePuesto() || (contratistas().length > 1)) ? '<button class="rolbtn" data-action="cambiar-contr" title="Elegir otro contratista">🌲 Cambiar contratista</button>' : '') +
    '<button class="rolbtn" data-action="cambiar-rol"><b>' + who + '</b> · cambiar rol</button>' +
    '</div></div>';
}
function nav(){
  var tabs = TABS[ui.rol] || [], nov = activos().filter(function(c){ return c.inc; }).length, curso = cargas().filter(function(k){ return k.estado === 'en_curso'; }).length;
  var pendN = ui.rol === 'bascula' ? enCamino().length + enDescarga().length : 0, cola = ui.rol === 'elaborador' ? colaDe(S.contratista_id).filter(function(g){ return g.estado === 'programado'; }).length : 0;
  var usrs = ui.rol === 'admin' ? (ui.usuarios || []).filter(function(u){ return !u.activo; }).length : 0;
  return '<nav class="nav" aria-label="Secciones"><div class="nav-in" style="grid-template-columns:repeat(' + tabs.length + ',1fr)">' + tabs.map(function(t){
    var badge = t[0] === 'camiones' ? ((nov + altasPend().length) || '') : t[0] === 'cola' ? (cola || curso || '') : t[0] === 'pend' ? (pendN || '') : t[0] === 'usuarios' ? (usrs || '') : '';
    return '<button class="tab" data-action="tab" data-v="' + t[0] + '"' + (ui.tab === t[0] ? ' aria-current="page"' : '') + '>' + ICON[t[2]] + '<span>' + t[1] + (badge ? '<span class="badge">' + badge + '</span>' : '') + '</span></button>';
  }).join('') + '</div></nav>';
}

// ---------- stock ----------
function cierreHtml(cids){
  return '<section class="cierre"><div class="cierre-h"><b>Relevamiento de stock · cierre ' + S.cierres.relevamiento + ' hs</b><span>' + cierreTexto() + ' · actualizado ' + esc(ui.updAt || hhmm()) + '</span></div>' +
    cids.map(function(c){ var r = relEstado(c); return '<div class="crow"><span>' + esc(contrNombre(c)) + '</span><span class="pill ' + (r.k === 'ok' ? 'st-disponible' : r.k === 'tarde' || r.k === 'viejo' ? 'inc-demora' : 'inc-mecanico') + '">' + r.t + '</span></div>'; }).join('') + '</section>';
}
function viewStock(){
  var el = ui.rol === 'elaborador', base = pilas(), ids = el ? [S.contratista_id] : contratistas().map(function(c){ return c.id; });
  var fino = sum(base.filter(function(p){ return p.tipo === 'fino'; }), function(p){ return p.volumen_m3; }), grueso = sum(base.filter(function(p){ return p.tipo === 'grueso'; }), function(p){ return p.volumen_m3; }), vt = sum(base.filter(esVentas), function(p){ return p.volumen_m3; });
  var out = (ui.rol === 'supervisor' ? flujoSupervisorBar() : '') + cierreHtml(ids) + '<section class="summary"><div class="big"><span class="n">' + f1(fino + grueso) + '</span><span class="u">m³</span><span class="l">' + (el ? 'Pendiente de carga en tus pilas, según tu último relevamiento' : 'Pendiente de carga en pila, según último relevamiento de cada contratista') + '</span></div>' + splitBar(fino, grueso) +
    '<div class="legend" style="margin-top:10px"><span>Stock Pindó SA <b>' + f1(fino + grueso - vt) + ' m³</b></span><span>Stock de ventas <b>' + f1(vt) + ' m³</b></span></div></section>';
  if(!el) out += '<button class="btn block" data-action="reporte" style="margin-top:12px">Generar reporte en PDF</button>';
  if(el && relCerrado()) out += '<div class="incbox inc-demora" style="margin-top:12px"><b>Relevamiento cerrado</b> · Cerró a las ' + S.cierres.relevamiento + ' hs. Mañana podés volver a relevar.</div>';
  var nTipo = function(t){ return base.filter(function(p){ return t === 'todos' || p.tipo === t; }).length; };
  out += '<div class="chips" role="group" aria-label="Filtrar por tipo">' + [['todos', 'Todas'], ['fino', 'Rollo fino'], ['grueso', 'Rollo grueso']].map(function(x){ return '<button class="chip" data-action="ftipo" data-v="' + x[0] + '" aria-pressed="' + (ui.ftipo === x[0]) + '">' + x[1] + '<span class="c">' + nTipo(x[0]) + '</span></button>'; }).join('') + '</div>';
  var list = base.filter(function(p){ return ui.ftipo === 'todos' || p.tipo === ui.ftipo; });
  if(!list.length && ui.ftipo !== 'todos') return out + vacio('No hay pilas de este tipo relevadas.');
  var groups = {}, order = [];
  if(ui.ftipo === 'todos') ids.forEach(function(c){ groups[c] = []; order.push(c); });
  list.forEach(function(p){ if(!groups[p.contratista_id]){ groups[p.contratista_id] = []; order.push(p.contratista_id); } groups[p.contratista_id].push(p); });
  order.forEach(function(cid){
    var ps = groups[cid];
    out += '<section class="group"><div class="group-h"><h2>' + esc(contrNombre(cid)) + '</h2><span style="display:flex;gap:12px;align-items:baseline">' + f1(sum(ps, function(p){ return p.volumen_m3; })) + ' m³' + (soloLectura() ? '' : '<button class="link ok" data-action="new-pila" data-contr="' + cid + '">+ Pila</button>') + '</span></div>' +
      (!ps.length ? vacio('Sin relevamiento cargado.', 'margin-top:0') : '<div class="rows">' + ps.map(function(p){
        return '<button class="row" data-action="edit-pila" data-id="' + p.id + '"><span class="t">' + esc(p.especie) + '</span>' +
          '<span class="s"><span class="tag ' + p.tipo + '">' + tipoLabel(p.tipo) + '</span>' + (esVentas(p) ? '<span class="pill st-cargando" style="font-size:11px;padding:0 5px">Stock de ventas</span>' : '') + '<span>Largo ' + fl(p.largo_pies) + '</span><span>Relevó ' + esc(p.relevado_por || 'sin dato') + ' · ' + (dia(p.relevado_en) === S.hoy ? '' : diaLabel(p.relevado_en) + ' ') + hm(p.relevado_en) + '</span>' + (dia(p.relevado_en) === S.hoy && hm(p.relevado_en) > S.cierres.relevamiento ? '<span class="pill inc-demora" style="font-size:11px;padding:0 5px">Tarde</span>' : '') + '</span>' +
          '<span class="m">' + f1(p.volumen_m3) + '<small>m³</small></span></button>';
      }).join('') + '</div>') + '</section>';
  });
  return out;
}
function dispHtml(cid){
  var ps = pilasDe(cid);
  if(!ps.length) return vacio('Este contratista no tiene stock relevado.', 'margin-top:12px');
  var fino = sum(ps.filter(function(p){ return p.tipo === 'fino'; }), function(p){ return p.volumen_m3; }), grueso = sum(ps.filter(function(p){ return p.tipo === 'grueso'; }), function(p){ return p.volumen_m3; }), vt = sum(ps.filter(esVentas), function(p){ return p.volumen_m3; });
  var last = ps.slice().sort(function(a, b){ return a.relevado_en < b.relevado_en ? 1 : -1; })[0];
  return '<section class="summary" style="margin-top:12px"><div class="big"><span class="n">' + f1(fino + grueso) + '</span><span class="u">m³</span><span class="l">Disponible para cargar · relevado ' + hm(last.relevado_en) + ' por ' + esc(last.relevado_por || 'sin dato') + '</span></div>' + splitBar(fino, grueso) +
    '<div class="legend" style="margin-top:10px"><span>Stock Pindó SA <b>' + f1(fino + grueso - vt) + ' m³</b></span><span>Stock de ventas <b>' + f1(vt) + ' m³</b></span></div></section><div class="rows" style="padding:4px 14px 6px;margin-top:12px">' + tablaItems(ps) + '</div>';
}
function dispResumenHtml(){
  var ac = activos(), grp = [['si', 'Disponibles', ac.filter(function(c){ return c.disp_manana && c.disp_manana.valor === 'si'; })], ['no', 'No disponibles', ac.filter(function(c){ return c.disp_manana && c.disp_manana.valor === 'no'; })], ['sr', 'Sin respuesta', ac.filter(function(c){ return !c.disp_manana; })]];
  return '<section class="group"><div class="group-h"><h2>Disponibilidad para mañana</h2><span>Actualizado ' + esc(ui.updAt || hhmm()) + '</span></div><p class="note" style="margin:6px 0 0">Respuestas hasta las ' + S.cierres.disponibilidad + ' hs' + (dispAbierta() ? '' : ' · cerrado') + '</p>' +
    '<div class="circ" style="grid-template-columns:repeat(3,minmax(0,1fr))">' + grp.map(function(x){ return '<div class="circ-b"><span class="circ-l">' + x[1] + '</span><span class="circ-n">' + x[2].length + '</span></div>'; }).join('') + '</div>' +
    grp.map(function(x){
      return '<details class="acc" style="margin-top:8px"' + (x[0] !== 'sr' && x[2].length ? ' open' : '') + '><summary><span>' + x[1] + '</span><span class="acc-n' + (x[0] === 'si' ? ' on' : '') + '">' + x[2].length + '</span></summary><div class="acc-b" style="padding-top:4px">' +
        (x[2].length ? x[2].map(function(c){ var pg = progDe(c.id, 'manana'); return '<div class="chk" style="justify-content:space-between;gap:10px"><span><b>' + esc(c.patente) + '</b> · ' + esc(c.chofer) + '</span><span class="acc-n">' + (c.disp_manana ? hm(c.disp_manana.respondida_en) + ' hs' : '') + (pg ? ' · ' + esc(contrNombre(pg.contratista_id)) : '') + '</span></div>'; }).join('') : '<p class="note" style="margin:8px 0">Ninguno.</p>') + '</div></details>';
    }).join('') + '</section>';
}
function stockPrioHtml(cid, d){
  var u = stockUso(cid), pr = prioDe(cid, d);
  return '<div class="circ" style="margin-top:12px">' + ['pindo', 'ventas'].map(function(k){
    var t = u[k].fino + u[k].grueso, on = pr === k;
    return '<div class="circ-b" aria-pressed="' + on + '"><span class="circ-l">' + PRIO[k] + '</span><span class="circ-n">' + f1(t) + '<small> m³</small></span><span class="circ-s">Fino ' + f1(u[k].fino) + ' · Grueso ' + f1(u[k].grueso) + '</span>' + (on ? '<span class="pill st-cargando" style="font-size:11px;padding:1px 6px;align-self:flex-start;margin-top:4px">Prioridad de carga</span>' : '') + '</div>';
  }).join('') + '</div>' + (pr ? '' : '<p class="note" style="margin-top:6px">Sin prioridad de carga definida para este frente.</p>');
}
function prioChips(cid, d){
  var pr = prioDe(cid, d), conf = pilasDe(cid).length > 0, bloq = d === 'manana' && !conf, u = stockUso(cid);
  return '<div style="margin-top:10px">' + (conf ? '<p class="note" style="margin:0 0 6px">Stock confirmado ' + esc(relEstado(cid).hora) + ' hs · Stock Pindó SA <b>' + f1(u.pindo.fino + u.pindo.grueso) + ' m³</b> · Ventas <b>' + f1(u.ventas.fino + u.ventas.grueso) + ' m³</b></p>' : '<p class="note" style="margin:0 0 6px;color:var(--danger)">Esperando el relevamiento de stock de este contratista para definir la prioridad.</p>') +
    '<div class="chips" role="group" aria-label="Prioridad de carga"><span class="note" style="align-self:center;margin:0 4px 0 0">Prioridad de carga:</span>' + [['ninguna', 'Ninguna'], ['pindo', PRIO.pindo], ['ventas', 'Ventas']].map(function(x){
      return '<button class="chip" data-action="prio" data-id="' + cid + '" data-v="' + x[0] + '" aria-pressed="' + ((pr || 'ninguna') === x[0]) + '"' + (bloq ? ' disabled' : '') + '>' + x[1] + '</button>'; }).join('') + '</div></div>';
}

// ---------- camiones (supervisor) ----------
function viewCamiones(){
  var counts = { todos: activos().length, novedad: activos().filter(function(c){ return c.inc; }).length };
  Object.keys(ESTADOS).forEach(function(k){ counts[k] = activos().filter(function(c){ return c.estado === k; }).length; });
  var chips = [['todos', 'Todos']].concat(Object.keys(ESTADOS).map(function(k){ return [k, ESTADOS_CHIP[k]]; })).concat([['novedad', 'Novedades']]);
  var ap = altasPend();
  var out = flujoSupervisorBar() + (ap.length ? '<section class="group"><div class="group-h"><h2>Altas pendientes</h2><span>' + ap.length + '</span></div><div class="list" style="margin-top:0">' + ap.map(function(c){
    return '<article class="truck"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span><span class="pill inc-demora">Pendiente</span></div><div><div class="who">' + esc(c.chofer) + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b> · ' + c.traccion + '</span>' + (c.telefono ? '<span>Tel. <b>' + esc(c.telefono) + '</b></span>' : '') + '<span>Solicitada ' + diaLabel(c.alta_en) + ' ' + hm(c.alta_en) + '</span></div></div>' +
      '<div class="acts"><button class="btn primary" data-action="alta-ok" data-id="' + c.id + '">Aceptar</button><button class="btn warn" data-action="alta-no" data-id="' + c.id + '">Rechazar</button></div></article>'; }).join('') + '</div></section>' : '');
  out += dispResumenHtml() + '<div class="chips" role="group" aria-label="Filtrar por estado">' + chips.map(function(x){ return '<button class="chip" data-action="festado" data-v="' + x[0] + '" aria-pressed="' + (ui.festado === x[0]) + '">' + x[1] + '<span class="c">' + counts[x[0]] + '</span></button>'; }).join('') + '</div>';
  var list = activos().filter(function(c){ return ui.festado === 'todos' || (ui.festado === 'novedad' ? !!c.inc : c.estado === ui.festado); });
  if(!list.length) return out + vacio('No hay camiones en este estado.');
  return out + '<div class="list">' + list.map(function(c){
    var g = progDe(c.id), acts = '';
    if(!g) acts += '<button class="btn primary block" data-action="programar" data-id="' + c.id + '">Programar carga</button>';
    if(c.inc) acts += '<button class="btn block" data-action="resolver-inc" data-id="' + c.id + '">Cerrar novedad</button>';
    acts += '<div class="acts"><button class="btn" data-action="editar-camion" data-id="' + c.id + '">Editar datos</button><button class="btn warn" data-action="baja-camion" data-id="' + c.id + '">Eliminar</button></div>';
    return '<article class="truck"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span>' + estadoPill(c) + '</div><div><div class="who">' + esc(c.chofer) + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b> · ' + c.traccion + '</span>' +
      (c.telefono ? '<span>Tel. <b>' + esc(c.telefono) + '</b></span>' : '') + (g ? '<span>Programado: <b>' + esc(contrNombre(g.contratista_id)) + ' · ' + esc(g.hora) + '</b></span>' : '<span>Sin programa</span>') + '<span>Mañana: <b>' + dispTxt(c) + '</b></span></div></div>' +
      incBox(c) + (c.estado === 'fila' && c.fila_desde ? '<p class="note">En fila de ' + esc(contrNombre(c.fila_contratista_id)) + ' desde las ' + hm(c.fila_desde) + ' · lleva ' + lleva(c.fila_desde) + ' min</p>' : '') + '<div class="col">' + acts + '</div></article>';
  }).join('') + '</div>';
}

// ---------- programa ----------
function qCard(g, acts){
  var c = camion(g.camion_id); if(!c) return '';
  var me = ui.rol === 'transportista' && c.id === ui.camionId;
  return '<article class="truck' + (me ? ' me' : '') + '"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span><span class="hora">' + esc(g.hora) + ' hs</span></div>' +
    '<div><div class="who">' + esc(c.chofer) + (me ? ' · tu camión' : '') + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b></span></div></div>' +
    '<div class="pills">' + (g.estado === 'cargando' ? '<span class="pill st-cargando">Cargando ahora</span>' : g.estado === 'cumplido' ? '<span class="pill st-ruta">Cumplido</span>' : estadoPill(c)) + incPill(c) + '</div>' + incBox(c) +
    (c.estado === 'fila' && c.fila_desde && g.estado !== 'cargando' ? '<p class="note">En fila desde las ' + hm(c.fila_desde) + ' · lleva ' + lleva(c.fila_desde) + ' min</p>' : '') + (acts ? '<div class="col">' + acts + '</div>' : '') + '</article>';
}
function esperaHtml(cids){
  return '<section class="cierre"><div class="cierre-h"><b>Esperas de hoy</b><span>Duración promedio de una carga: ' + durProm() + ' min</span></div>' + cids.map(function(c){
    var f = filaDe(c).length, p = esperaProm(c); return '<div class="crow"><span>' + esc(contrNombre(c)) + '</span><span class="hora" style="font-size:14px">' + f + ' en fila · ' + (p == null ? 'sin datos' : 'espera prom. ' + p + ' min') + '</span></div>'; }).join('') + '</section>';
}
function emisionHtml(){
  var n = programa().filter(function(g){ return g.jornada === S.manana && g.estado === 'programado'; }).length, e = emitido('manana');
  var f = contratistas().filter(function(c){ var so = solicDe(c.id); return so && colaDe(c.id, 'manana').length < so.cantidad_minima; });
  return cierreHtml(contratistas().map(function(c){ return c.id; })) + '<div class="assign"><span class="pos">' + (e ? 'Programa emitido a las <b>' + hm(e.emitido_en) + ' hs</b>. Transportistas y elaboradores ya ven su asignación.' : 'Programa sin emitir. Transportistas y elaboradores no lo ven hasta que lo emitas.') + '</span>' +
    '<span class="pos"><b>' + n + '</b> camiones programados para mañana</span>' + (f.length ? '<span class="pos" style="color:var(--danger)">Con menos camiones que los solicitados: <b>' + f.map(function(c){ return esc(c.nombre); }).join(', ') + '</b></span>' : '') +
    '<button class="btn primary block" data-action="emitir" style="margin-top:6px">' + (e ? 'Reemitir programa' : 'Emitir programa') + '</button></div>';
}
function diaChips(){
  return '<div class="chips" role="group" aria-label="Jornada del programa">' + [['hoy', 'Hoy'], ['manana', 'Mañana']].map(function(x){ return '<button class="chip" data-action="fdia" data-v="' + x[0] + '" aria-pressed="' + (ui.fdia === x[0]) + '">' + x[1] + '</button>'; }).join('') + '</div>';
}
function viewPrograma(){
  var edit = ui.rol === 'supervisor', d = ui.fdia, out = diaChips() + '<p class="note" style="margin-top:6px">' + (d === 'hoy' ? today() + ' · jornada en curso' : tomorrow() + ' · jornada siguiente') + '</p>';
  if(d === 'manana'){
    if(edit) out += dispResumenHtml() + emisionHtml();
    else if(!emitido('manana')) return out + vacio('El supervisor todavía no emitió el programa de mañana. Se emite después del cierre del relevamiento de stock (' + S.cierres.relevamiento + ' hs).');
    else out += '<div class="assign"><span class="pos">Programa emitido a las <b>' + hm(emitido('manana').emitido_en) + ' hs</b></span></div>';
  }
  if(d === 'hoy' && edit) out += esperaHtml(contratistas().map(function(c){ return c.id; }));
  contratistas().forEach(function(ct){
    var cid = ct.id, q = colaDe(cid, d), ini = inicioFrente(cid, d), prG = prioDe(cid, d), so = solicDe(cid);
    out += '<section class="group"><div class="group-h"><h2>' + esc(ct.nombre) + '</h2><span>' + q.length + ' camión' + (q.length === 1 ? '' : 'es') + '</span></div>' +
      (ini ? '<p class="note" style="margin:6px 0 0">Inicio de carga del frente: <b>' + esc(ini) + ' hs</b></p>' : '') +
      (d === 'manana' && so ? '<p class="note" style="margin:6px 0 0">Solicitó <b>' + so.cantidad_minima + ' unidad' + (so.cantidad_minima === 1 ? '' : 'es') + '</b> como mínimo (' + esc(so.solicitada_por) + ', ' + hm(so.solicitada_en) + ' hs)' + (so.nota ? ' · ' + esc(so.nota) : '') + (q.length < so.cantidad_minima ? ' · <span style="color:var(--danger);font-weight:600">faltan ' + (so.cantidad_minima - q.length) + '</span>' : ' · <b>cubierto</b>') + '</p>' : '') +
      (edit ? prioChips(cid, d) : (prG ? '<p class="note" style="margin:6px 0 0">Prioridad de carga: <b>' + PRIO[prG] + '</b></p>' : ''));
    out += !q.length ? vacio('Sin camiones programados.', 'margin-top:0') : '<div class="list" style="margin-top:0">' + q.map(function(g){ return qCard(g, (edit && g.estado === 'programado') ? '<button class="btn block" data-action="quitar-prog" data-id="' + g.id + '">Quitar del programa</button>' : ''); }).join('') + '</div>';
    out += '</section>';
  });
  return out;
}
function viewProgTransp(){
  var c = camion(ui.camionId), d = ui.fdia, g = progDe(c.id, d);
  var out = diaChips() + '<p class="note" style="margin-top:6px">' + (d === 'hoy' ? today() + ' · tu carga de hoy' : tomorrow() + ' · tu carga de mañana') + '</p>';
  if(d === 'manana' && !emitido('manana')) return out + vacio('El supervisor todavía no emitió el programa de mañana. Se emite después del cierre del relevamiento de stock (' + S.cierres.relevamiento + ' hs).');
  if(!g) return out + vacio('No tenés carga programada ' + (d === 'hoy' ? 'para hoy' : 'para mañana') + '.');
  var ini = inicioFrente(g.contratista_id, d), pr = prioDe(g.contratista_id, d), q = colaDe(g.contratista_id, d).filter(function(x){ return x.estado === 'programado'; }), pos = 0;
  q.forEach(function(x, i){ if(x.id === g.id) pos = i + 1; });
  out += '<div class="assign"><span class="cn">' + esc(contrNombre(g.contratista_id)) + '</span><span class="pos">Tu hora de carga <b>' + esc(g.hora) + ' hs</b></span>' + (ini ? '<span class="pos">Inicio de carga del frente <b>' + esc(ini) + ' hs</b></span>' : '') +
    (d === 'hoy' ? '<span class="pos">' + (g.estado === 'cargando' ? '<b>Cargando ahora</b>' : 'Lugar en la cola: <b>' + pos + ' de ' + q.length + '</b>') + '</span>' : '') + '<span class="pos">Prioridad de carga <b>' + (pr ? PRIO[pr] : 'Ninguna') + '</b></span></div>';
  if(d === 'manana') out += '<h2 class="sec-h">Stock en ' + esc(contrNombre(g.contratista_id)) + '</h2><p class="note" style="margin:4px 0 0">Según el último relevamiento.</p>' + stockPrioHtml(g.contratista_id, 'manana');
  return out;
}
function viewProgElab(){
  var cid = S.contratista_id, sol = solicDe(cid), q = colaDe(cid, 'manana'), ie = inicioElabDe(cid, 'manana'), ro = soloLectura(), out = '';
  out += '<section class="group"><div class="group-h"><h2>Hora de inicio de carga</h2><span>' + tomorrow() + '</span></div><div class="assign"><span class="pos">' + (ie ? 'Marcaste el inicio a las <b>' + esc(ie.hora) + ' hs</b> · ' + hm(ie.marcado_en) + ' hs · ' + esc(ie.marcado_por) : 'Todavía no marcaste a qué hora arranca la carga mañana.') + '</span><span class="pos">Los transportistas y el supervisor ven este horario en el programa.</span>' +
    (ro ? '' : '<button class="btn primary block" data-action="inicio-carga" style="margin-top:6px">' + (ie ? 'Modificar hora de inicio' : 'Marcar hora de inicio') + '</button>') + '</div></section>';
  out += '<section class="group"><div class="group-h"><h2>Unidades mínimas necesarias</h2><span>' + tomorrow() + '</span></div><div class="assign"><span class="pos">' + (sol ? 'Solicitaste <b>' + sol.cantidad_minima + ' unidad' + (sol.cantidad_minima === 1 ? '' : 'es') + '</b> como mínimo · ' + hm(sol.solicitada_en) + ' hs · ' + esc(sol.solicitada_por) : 'Todavía no solicitaste unidades para mañana.') + '</span>' + (sol && sol.nota ? '<span class="pos">' + esc(sol.nota) + '</span>' : '') +
    (ro ? '' : '<button class="btn primary block" data-action="solicitar" style="margin-top:6px">' + (sol ? 'Modificar solicitud' : 'Solicitar unidades mínimas') + '</button>') + '</div></section>';
  out += '<h2 class="sec-h">Programa asignado</h2>';
  if(!emitido('manana')) return out + vacio('El supervisor todavía no emitió el programa de mañana. Se emite después del cierre del relevamiento (' + S.cierres.relevamiento + ' hs).', 'margin-top:12px');
  var ini = inicioFrente(cid, 'manana'), cap = sum(q, function(g){ var c = camion(g.camion_id); return c ? c.capacidad_tn : 0; });
  out += '<div class="assign"><span class="pos">Programa emitido a las <b>' + hm(emitido('manana').emitido_en) + ' hs</b></span><span class="pos">Camiones asignados <b>' + q.length + '</b>' + (sol ? ' de <b>' + sol.cantidad_minima + '</b> solicitados' : '') + ' · capacidad <b>' + cap + ' tn</b></span>' +
    (ini ? '<span class="pos">Inicio de carga <b>' + esc(ini) + ' hs</b>' + (ie ? ' · marcado por vos' : '') + '</span>' : '') + (sol && q.length < sol.cantidad_minima ? '<span class="pill inc-demora" style="align-self:flex-start">Faltan ' + (sol.cantidad_minima - q.length) + ' unidad' + (sol.cantidad_minima - q.length === 1 ? '' : 'es') + '</span>' : '') + '</div>';
  if(!q.length) return out + vacio('No hay camiones asignados a tu frente para mañana.', 'margin-top:12px');
  return out + '<div class="list">' + q.map(function(g){ var c = camion(g.camion_id); if(!c) return ''; return '<article class="truck"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span><span class="hora">' + esc(g.hora) + ' hs</span></div><div><div class="who">' + esc(c.chofer) + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b></span>' + (c.telefono ? '<span>Tel. <b>' + esc(c.telefono) + '</b></span>' : '') + '<span>Disponibilidad: <b>' + dispTxt(c) + '</b></span></div></div></article>'; }).join('') + '</div>';
}

// ---------- pedidos ----------
function pedidoTabla(av, conPila){
  return '<div class="rows" style="padding:4px 14px 6px;margin-top:8px;overflow-x:auto"><table class="tbl"><thead><tr><th>Tipo</th><th>Largo</th><th>Pedido</th><th>Enviado</th><th>Avance</th>' + (conPila ? '<th>En pila</th>' : '') + '</tr></thead><tbody>' +
    av.lineas.map(function(r){ var falta = r.pedido - r.enviado; return '<tr><td><span class="tag ' + r.tipo + '">' + tipoLabel(r.tipo) + '</span></td><td class="lg">' + fl(r.largo_pies) + '</td><td>' + f1(r.pedido) + '</td><td>' + f1(r.enviado) + '</td><td><b>' + r.avance_pct + '%</b><div class="prog mini"><i style="width:' + r.avance_pct + '%"></i></div></td>' + (conPila ? '<td' + (falta > r.stock_pila ? ' style="color:var(--danger)"' : '') + '>' + f1(r.stock_pila) + '</td>' : '') + '</tr>'; }).join('') + '</tbody></table></div>' +
    (av.fuera_de_pedido > 0 ? '<p class="note" style="margin:6px 0 0">Además se despacharon ' + f1(av.fuera_de_pedido) + ' m³ de largos o categorías que no estaban en el pedido.</p>' : '');
}
function viewPedido(){
  var pd = pedidoDe(S.contratista_id);
  if(!pd) return vacio('El supervisor todavía no cargó el pedido de rollos a elaborar para ' + tomorrow() + '.');
  var av = pd.avance, fino = sum(pd.lineas.filter(function(l){ return l.tipo === 'fino'; }), function(l){ return l.volumen_m3; }), grueso = sum(pd.lineas.filter(function(l){ return l.tipo === 'grueso'; }), function(l){ return l.volumen_m3; });
  var out = '<section class="summary"><div class="big"><span class="n">' + av.cumplimiento_pct + '</span><span class="u">%</span><span class="l">Cumplimiento del pedido · ' + f1(av.enviado_total) + ' de ' + f1(av.pedido_total) + ' m³ enviados' + (av.faltante > 0 ? ' · faltan ' + f1(av.faltante) + ' m³' : ' · completo') + '</span></div>' + progBar(av.cumplimiento_pct) +
    '<p class="note" style="margin:8px 0 6px">Pedido de ' + f1(av.pedido_total) + ' m³ · cargado por ' + esc(pd.creado_por) + ' el ' + diaLabel(pd.actualizado_en) + ' a las ' + hm(pd.actualizado_en) + ' hs · despachos desde el ' + diaLabel(pd.desde) + '</p>' + splitBar(fino, grueso) + '</section>';
  if(pd.nota) out += '<div class="assign"><span class="pos">Indicación del supervisor</span><span class="pos"><b>' + esc(pd.nota) + '</b></span></div>';
  return out + '<h2 class="sec-h">Avance por largo y categoría<span>' + av.lineas.length + '</span></h2>' + pedidoTabla(av, true) + '<p class="note" style="margin-top:10px">"Enviado" se descuenta solo con cada despacho finalizado desde que se cargó el pedido. "En pila" es tu último relevamiento; en rojo, lo que falta y no alcanza con el stock.</p>';
}
function viewPedidos(){
  var out = '<p class="hint" style="margin:0 0 10px">Asigná a cada contratista los largos y categorías a elaborar. El elaborador lo ve en su pestaña Pedido.</p>';
  contratistas().forEach(function(ct){
    var pd = pedidoDe(ct.id), av = pd && pd.avance;
    out += '<section class="group"><div class="group-h"><h2>' + esc(ct.nombre) + '</h2><span>' + (pd ? av.cumplimiento_pct + '% cumplido' : 'sin pedido') + '</span></div>';
    if(pd) out += progBar(av.cumplimiento_pct) + '<p class="note" style="margin:6px 0 0"><b>' + f1(av.enviado_total) + '</b> de <b>' + f1(av.pedido_total) + ' m³</b> enviados' + (av.faltante > 0 ? ' · faltan ' + f1(av.faltante) + ' m³' : ' · pedido completo') + '</p>' + pedidoTabla(av, false) + (pd.nota ? '<p class="note" style="margin:6px 0 0">Indicación: <b>' + esc(pd.nota) + '</b></p>' : '') + '<p class="note" style="margin:4px 0 0">Cargado por ' + esc(pd.creado_por) + ' · ' + diaLabel(pd.actualizado_en) + ' ' + hm(pd.actualizado_en) + ' hs</p>';
    else out += '<p class="note" style="margin:0">Todavía no hay pedido de rollos para este contratista.</p>';
    out += '<button class="btn ' + (pd ? '' : 'primary ') + 'block" data-action="pedido-edit" data-id="' + ct.id + '" style="margin-top:8px">' + (pd ? 'Modificar pedido' : 'Asignar pedido') + '</button></section>';
  });
  return out;
}

// ---------- cola de carga (elaborador) ----------
function cursoHtml(k){
  var c = camion(k.camion_id) || {};
  return '<article class="carga"><div class="carga-btn" style="cursor:default"><div class="carga-top"><div><span class="plate">' + esc(c.patente) + '</span></div><span class="pill st-cargando">Cargando</span></div><div><div class="dest">' + esc(c.chofer) + '</div><div class="hr">Desde ' + hm(k.inicio_en) + ' · ' + esc(contrNombre(k.contratista_id)) + (k.espera_min != null ? ' · esperó ' + k.espera_min + ' min' : '') + '</div></div></div>' +
    (soloLectura() ? '' : '<div class="carga-act"><button class="btn primary block" data-action="finalizar" data-id="' + k.id + '">Finalizar carga</button></div>') + '</article>';
}
function finHtml(k){
  var c = camion(k.camion_id) || {}, isOpen = !!ui.open[k.id], fi = cargaTipo(k, 'fino'), gr = cargaTipo(k, 'grueso');
  var out = '<article class="carga' + (isOpen ? ' open' : '') + '"><button class="carga-btn" data-action="toggle-carga" data-id="' + k.id + '" aria-expanded="' + isOpen + '"><div class="carga-top"><div style="min-width:0"><span class="plate">' + esc(c.patente) + '</span><div class="dest" style="margin-top:8px">' + esc(k.destino) + ' · ' + CIRC[k.circuito] + '</div><div class="hr">' + esc(contrNombre(k.contratista_id)) + ' · ' + esc(c.chofer) + ' · salió ' + hm(k.fin_en) + (k.espera_min != null ? ' · esperó ' + k.espera_min + ' min' : '') + (k.rodal ? ' · rodal ' + esc(k.rodal) : '') + '</div></div><div class="tot">' + f1(cargaTotal(k)) + '<small>m³</small></div></div>' + splitBar(fi, gr) + '<span style="display:flex;justify-content:center">' + ICON.chev + '</span></button>';
  if(isOpen) out += '<div class="detail"><h3>Detalle por largo y tipo</h3>' + tablaItems(k.lineas) + '<p class="note" style="margin-top:10px">' + (k.fila_desde ? 'Entró en la fila ' + hm(k.fila_desde) + ' · ' : '') + 'inició ' + hm(k.inicio_en) + ' · salió ' + hm(k.fin_en) + (k.ingreso_en ? ' · báscula ' + hm(k.ingreso_en) + (k.salida_en ? ' a ' + hm(k.salida_en) : '') : '') + '</p></div>';
  return out + '</article>';
}
function viewCola(){
  var cid = S.contratista_id, out = cierreHtml([cid]), ro = soloLectura();
  var curso = cargas().filter(function(k){ return k.estado === 'en_curso' && k.contratista_id === cid; });
  var fin = cargas().filter(function(k){ return k.estado === 'finalizada' && k.contratista_id === cid && k.jornada === S.hoy; }).sort(function(a, b){ return a.fin_en < b.fin_en ? 1 : -1; });
  var enFila = filaDe(cid).map(function(c){ return progDe(c.id); }).filter(function(g){ return g && g.contratista_id === cid && g.estado === 'programado'; });
  var cola = colaDe(cid).filter(function(g){ return g.estado === 'programado' && enFila.indexOf(g) < 0; });
  out += '<h2 class="sec-h">Cargando ahora<span>' + curso.length + '</span></h2><div class="list">' + (curso.length ? curso.map(cursoHtml).join('') : vacio('No hay camiones cargando.', 'margin-top:0')) + '</div>' + esperaHtml([cid]);
  out += '<h2 class="sec-h">En fila de espera<span>' + enFila.length + '</span></h2><div class="list">' + (enFila.length ? enFila.map(function(g, i){ var c = camion(g.camion_id); return qCard(g, '<p class="note">Llegó <b>' + hm(c.fila_desde) + '</b> · lleva <b>' + lleva(c.fila_desde) + ' min</b> · espera estimada ~' + estimado(cid, i) + ' min</p>' + (ro ? '' : '<button class="btn primary block" data-action="iniciar" data-id="' + g.id + '"' + (mecanico(c) ? ' disabled' : '') + '>Iniciar carga</button>')); }).join('') : vacio('No hay camiones esperando en la fila.', 'margin-top:0')) + '</div>';
  out += '<h2 class="sec-h">Programados · aún no llegaron<span>' + cola.length + '</span></h2><div class="list">' + (cola.length ? cola.map(function(g){
    var c = camion(g.camion_id) || {}, why = mecanico(c) ? 'Tiene un problema mecánico: no puede cargar todavía.' : c.estado === 'ruta' ? 'Todavía no descargó: viene en ruta con carga.' : c.estado === 'cargando' ? 'Está cargando en otro contratista.' : '';
    return qCard(g, (ro ? '' : '<button class="btn primary block" data-action="iniciar" data-id="' + g.id + '"' + (why ? ' disabled' : '') + '>Iniciar carga</button>') + (why ? '<p class="note">' + why + '</p>' : '')); }).join('') : vacio('No hay camiones programados para tu contratista.', 'margin-top:0')) + '</div>';
  out += '<h2 class="sec-h">Despachado hoy<span>' + f1(sum(fin, cargaTotal)) + ' m³</span></h2><div class="list">' + (fin.length ? fin.map(finHtml).join('') : vacio('Todavía no despachaste camiones hoy.', 'margin-top:0')) + '</div><h2 class="sec-h">Programa de mañana</h2>';
  if(!emitido('manana')) out += vacio('Todavía no fue emitido. El supervisor lo emite después del cierre de relevamiento (' + S.cierres.relevamiento + ' hs).', 'margin-top:12px');
  else { var qm = colaDe(cid, 'manana'); out += '<p class="note" style="margin-top:8px">' + tomorrow() + ' · emitido a las ' + hm(emitido('manana').emitido_en) + ' hs</p>' + (qm.length ? '<div class="list">' + qm.map(function(g){ return qCard(g, ''); }).join('') + '</div>' : vacio('No hay camiones programados para tu contratista mañana.', 'margin-top:12px')); }
  return out;
}

// ---------- báscula ----------
function enCamino(){ return cargas().filter(function(k){ return k.estado === 'finalizada' && k.circuito === 'industria' && !k.ingreso_en; }); }
function enDescarga(){ return ((S && S.movimientos) || []).filter(function(m){ return !m.salida_en; }); }
function basCard(k){
  var c = camion(k.camion_id) || {};
  return '<div class="row" style="cursor:default"><span class="t"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + '</span><span class="s"><span>' + esc(c.empresa) + '</span><span>' + CIRC[k.circuito] + ' · ' + esc(k.destino) + '</span>' + (k.rodal ? '<span>Rodal <b>' + esc(k.rodal) + '</b></span>' : '') + etaBadge(k) + '</span><span class="m" style="font-size:15px">' + hm(k.fin_en) + '<small>salió</small></span></div>';
}
function viewPend(){
  var cam = enCamino().sort(function(a, b){ return a.fin_en < b.fin_en ? -1 : 1; }), movs = (S.movimientos || []), des = movs.filter(function(m){ return !m.salida_en; }), hoyK = movs.filter(function(m){ return m.jornada === S.hoy; }), sals = hoyK.filter(function(m){ return m.salida_en; });
  var lista = [];
  hoyK.forEach(function(m){ lista.push({ m: m, tipo: 'Ingreso', hora: m.ingreso_en }); if(m.salida_en) lista.push({ m: m, tipo: 'Salida', hora: m.salida_en }); });
  lista.sort(function(a, b){ return a.hora < b.hora ? 1 : -1; });
  var out = '<section class="summary"><div class="big"><span class="n">' + hoyK.length + '</span><span class="u">ingresos</span><span class="l">Ingresos y salidas de báscula hoy</span></div><div class="legend" style="margin-top:10px"><span>Ingresaron <b>' + hoyK.length + '</b></span><span>Salieron <b>' + sals.length + '</b></span><span>En planta <b>' + des.length + '</b></span></div></section>';
  out += '<h2 class="sec-h">Descargando en planta<span>' + des.length + '</span></h2><div class="list">' + (des.length ? des.map(function(m){
    var c = camion(m.camion_id) || {}, k = m.carga_id ? carga(m.carga_id) : null;
    return '<article class="carga"><div class="carga-btn" style="cursor:default"><div class="carga-top"><div style="min-width:0"><span class="plate">' + esc(c.patente) + '</span><div class="dest" style="margin-top:8px">' + esc(c.chofer) + ' · ' + esc(c.empresa) + '</div>' + (k ? '<div class="hr">' + CIRC[k.circuito] + ' · ' + esc(k.destino) + ' · ' + esc(contrNombre(k.contratista_id)) + '</div>' : '<div class="hr">Sin carga asociada</div>') +
      '<div class="hr"><span class="pill st-cargando" style="font-size:11px;padding:0 6px">Descargando</span> &nbsp;<b>Ingresó ' + hm(m.ingreso_en) + '</b> · lleva ' + lleva(m.ingreso_en) + ' min en planta</div></div></div></div><div class="carga-act"><button class="btn primary block" data-action="bas-salida" data-id="' + m.id + '">Registrar salida</button></div></article>'; }).join('') : vacio('No hay camiones en planta.', 'margin-top:0')) + '</div>';
  var en = {}; cam.forEach(function(k){ en[k.camion_id] = true; });
  var ls = activos().slice().sort(function(a, b){ return (en[b.id] ? 1 : 0) - (en[a.id] ? 1 : 0) || (a.patente < b.patente ? -1 : 1); });
  out += '<h2 class="sec-h">Ingreso de camión</h2><form data-form="basing" novalidate style="margin-top:12px"><div class="field"><label for="bi-p">Camión que ingresa</label><select class="input" id="bi-p" name="camion_id"><option value="">Elegí el camión</option>' + ls.map(function(c){ return '<option value="' + c.id + '"' + (ui.basPat === c.id ? ' selected' : '') + '>' + esc(c.patente) + ' · ' + esc(c.chofer) + (en[c.id] ? ' · en camino' : '') + '</option>'; }).join('') + '</select></div>' + (ui.basErr ? '<p class="err" role="alert">' + esc(ui.basErr) + '</p>' : '') + '<button class="btn primary block" type="submit">Registrar ingreso a descarga</button></form>';
  out += '<h2 class="sec-h">En camino a báscula<span>' + cam.length + '</span></h2>' + (cam.length ? '<div class="rows" style="margin-top:12px">' + cam.map(basCard).join('') + '</div>' : vacio('No hay camiones cargados en camino.', 'margin-top:12px'));
  out += '<h2 class="sec-h">Ingresos y salidas de hoy<span>' + lista.length + '</span></h2>';
  if(!lista.length) return out + vacio('Todavía no se registraron movimientos hoy.');
  return out + '<div class="rows" style="margin-top:12px">' + lista.map(function(x){
    var c = camion(x.m.camion_id) || {}, k = x.m.carga_id ? carga(x.m.carga_id) : null, ing = x.tipo === 'Ingreso', perm = !ing ? Math.round((new Date(x.m.salida_en) - new Date(x.m.ingreso_en)) / 60000) : null;
    return '<div class="row" style="cursor:default"><span class="t"><span class="pill ' + (ing ? 'st-disponible' : 'inc-demora') + '" style="font-size:11px;padding:0 6px">' + x.tipo + '</span> &nbsp;<span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + '</span><span class="s">' + (k ? '<span>' + esc(k.destino) + '</span><span>' + CIRC[k.circuito] + '</span>' : '') + (perm != null && perm >= 0 ? '<span>Permanencia ' + fmtMin(perm) + '</span>' : '') + (ing && !x.m.salida_en ? '<span class="pill st-cargando" style="font-size:11px;padding:0 6px">Descargando · lleva ' + lleva(x.m.ingreso_en) + ' min</span>' : '') + '</span><span class="m">' + hm(x.hora) + '<small>hs</small></span></div>'; }).join('') + '</div>';
}
function viewIndustria(){
  var ks = cargas().filter(function(k){ return k.estado === 'finalizada' && k.circuito === 'industria'; }).sort(function(a, b){ return a.fin_en < b.fin_en ? 1 : -1; });
  var cam = ks.filter(function(k){ return !k.ingreso_en; }), des = ks.filter(function(k){ return k.ingreso_en && !k.salida_en; }), ok = ks.filter(function(k){ return k.salida_en; }), pend = cam.concat(des);
  var out = '<section class="summary"><div class="big"><span class="n">' + pend.length + '</span><span class="u">camiones</span><span class="l">Cargados con destino a industria propia, por descargar · ' + f1(sum(pend, cargaTotal)) + ' m³</span></div></section>' +
    '<div class="circ" style="grid-template-columns:repeat(3,minmax(0,1fr))">' + [['En camino', cam.length], ['En descarga', des.length], ['Descargados', ok.length]].map(function(x){ return '<div class="circ-b"><span class="circ-l">' + x[0] + '</span><span class="circ-n">' + x[1] + '</span></div>'; }).join('') + '</div><h2 class="sec-h">Camiones<span>' + ks.length + '</span></h2>';
  if(!ks.length) return out + vacio('Todavía no hay cargas para industria.');
  return out + '<div class="rows" style="margin-top:12px">' + ks.map(function(k){ var c = camion(k.camion_id) || {}, est = k.salida_en ? 'Descargó ' + hm(k.salida_en) : k.ingreso_en ? 'Descargando desde ' + hm(k.ingreso_en) : 'En camino · salió ' + hm(k.fin_en); return '<div class="row" style="cursor:default"><span class="t"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + '</span><span class="s"><span>' + esc(k.destino) + '</span><span>' + esc(contrNombre(k.contratista_id)) + (k.jornada !== S.hoy ? ' · ' + diaLabel(k.jornada) : '') + '</span><span><b>' + est + '</b></span>' + etaBadge(k) + '</span><span class="m">' + f1(cargaTotal(k)) + '<small>m³</small></span><div style="grid-column:1/3;margin-top:6px">' + trazaSteps(k, false) + '</div></div>'; }).join('') + '</div>';
}
function horariosHtml(edit){
  var b = S.bascula || { estado: { k: 'cerr', t: '' }, turnos: [], descansos: [] }, e = b.estado;
  var fila = function(x, k, lab){ return '<div class="row" style="cursor:default;padding:10px 14px"><span class="t">' + esc(x.desde) + ' a ' + esc(x.hasta) + ' hs</span>' + (lab ? '<span class="s"><span>' + esc(lab) + '</span></span>' : '') + (edit ? '<button class="link" data-action="bas-hor-del" data-k="' + k + '" data-id="' + x.id + '" style="grid-column:2;grid-row:1/3;color:var(--danger)">Quitar</button>' : '') + '</div>'; };
  return '<section class="group"><div class="group-h"><h2>Horarios de báscula</h2><span class="pill ' + (e.k === 'ok' ? 'st-disponible' : e.k === 'desc' ? 'inc-demora' : 'inc-mecanico') + '">' + (e.k === 'ok' ? 'Atendiendo' : e.k === 'desc' ? 'En descanso' : 'Cerrada') + '</span></div><p class="note" style="margin:6px 0 0"><b>' + esc(e.t) + '</b></p>' +
    '<h3 class="note" style="margin:12px 0 6px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Horarios disponibles</h3>' + (b.turnos.length ? '<div class="rows">' + b.turnos.map(function(x){ return fila(x, 'turno', ''); }).join('') + '</div>' : vacio('Sin horarios cargados.', 'margin-top:0')) +
    '<h3 class="note" style="margin:12px 0 6px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Descansos programados</h3>' + (b.descansos.length ? '<div class="rows">' + b.descansos.map(function(x){ return fila(x, 'descanso', x.motivo); }).join('') + '</div>' : vacio('Sin descansos programados.', 'margin-top:0')) +
    (edit ? '<div class="acts" style="margin-top:10px"><button class="btn primary" data-action="bas-hor-add" data-v="turno">+ Horario</button><button class="btn" data-action="bas-hor-add" data-v="descanso">+ Descanso</button></div>' : '') + '</section>';
}
function viewHist(){
  var h = (S.bascula && S.bascula.hist) || { total: 0 }, out = horariosHtml(true);
  if(!h.total) return out + vacio('Todavía no hay ingresos registrados.');
  var mx = 0; Object.keys(h.por_hora).forEach(function(k){ if(h.por_hora[k] > mx) mx = h.por_hora[k]; });
  out += '<section class="summary"><div class="big"><span class="n">' + (h.prom_min == null ? '—' : h.prom_min) + '</span><span class="u">min</span><span class="l">Tiempo promedio de descarga por camión · ' + h.dias_n + ' día' + (h.dias_n === 1 ? '' : 's') + ' de datos</span></div><div class="legend" style="margin-top:12px"><span>Camiones por día <b>' + h.camiones_por_dia.toLocaleString('es-AR') + '</b></span>' + (h.pico_h != null ? '<span>Hora pico <b>' + pad(h.pico_h) + ':00–' + pad(h.pico_h + 1) + ':00</b></span>' : '') + '</div></section>';
  out += '<h2 class="sec-h">Ingresos por hora<span>promedio por día</span></h2><div class="hbars" role="img" aria-label="Ingresos a báscula por hora">';
  for(var H = 5; H <= 20; H++){ var v = h.por_hora[String(H)] || 0; out += '<div class="hcol"><span class="hv">' + (v ? v.toLocaleString('es-AR') : '') + '</span><div class="hb' + (H === h.pico_h ? ' pk' : '') + '" style="height:' + Math.max(2, Math.round(v / (mx || 1) * 100)) + '%"></div><span class="hl">' + H + '</span></div>'; }
  out += '</div><h2 class="sec-h">Por día<span>' + h.dias.length + '</span></h2><div class="rows" style="margin-top:12px">' + h.dias.map(function(d){ var pp = d.jornada.split('-'), lab = new Date(+pp[0], +pp[1] - 1, +pp[2]).toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'numeric' }); return '<div class="row"><span class="t">' + esc(lab) + (d.jornada === S.hoy ? ' · hoy' : '') + '</span><span class="s"><span>' + d.n + ' camiones</span>' + (d.pico_h != null ? '<span>Pico ' + pad(d.pico_h) + ':00 (' + d.pico_n + ')</span>' : '') + '</span><span class="m">' + (d.prom_min == null ? '—' : d.prom_min) + '<small>min prom.</small></span></div>'; }).join('') + '</div>';
  return out;
}

// ---------- transportista ----------
function viewViaje(){
  var c = camion(ui.camionId), g = progDe(c.id), ro = soloLectura(), out = horariosHtml(false), acts = '', nota = '', aviso = avisoDescargaOk(c), u0 = ultCarga(c);
  if(!ro){
    if(c.estado === 'ruta' && aviso) acts += '<button class="btn primary block" data-action="set-estado" data-v="vacio">Descargué · voy vacío</button>';
    if(c.estado === 'vacio' && aviso) acts += '<button class="btn primary block" data-action="set-estado" data-v="disponible">Estoy disponible para carga</button>';
    if((c.estado === 'vacio' || c.estado === 'disponible') && g && g.estado === 'programado' && !mecanico(c)) acts += '<button class="btn primary block" data-action="entrar-fila">Llegué · entrar en la fila de espera</button>';
    if(c.estado === 'fila') acts += '<button class="btn block" data-action="salir-fila">Salir de la fila de espera</button>';
  }
  if(c.estado === 'cargando') nota = '<p class="note">Estás cargando' + (g ? ' en ' + esc(contrNombre(g.contratista_id)) : '') + '. Cuando terminen se marca como en ruta.</p>';
  else if(c.estado === 'fila' && c.fila_desde){ var f = filaDe(c.fila_contratista_id), pos = 0; f.forEach(function(x, i){ if(x.id === c.id) pos = i + 1; }); nota = '<p class="note">En fila de <b>' + esc(contrNombre(c.fila_contratista_id)) + '</b> desde las <b>' + hm(c.fila_desde) + '</b> · lleva ' + lleva(c.fila_desde) + ' min' + (pos ? ' · lugar ' + pos + ' de ' + f.length + ' · espera estimada ~' + estimado(c.fila_contratista_id, pos - 1) + ' min' : '') + '.</p>'; }
  if(c.estado === 'ruta' && u0 && u0.circuito === 'industria') nota += '<p class="note">Tu carga va a industria propia: la descarga y tu disponibilidad las registra la báscula de Pindó' + (u0.ingreso_en && !u0.salida_en ? ' · ingresaste a las ' + hm(u0.ingreso_en) : '') + '.</p>';
  var traza = u0 && (c.estado === 'ruta' || u0.jornada === S.hoy) ? '<div style="margin-top:4px">' + (c.estado === 'ruta' ? etaBadge(u0) : '') + trazaSteps(u0, true) + '</div>' : '';
  var inc = ro ? '' : (c.inc ? '<button class="btn primary block" data-action="resolver-inc">Ya estoy operativo · cerrar novedad</button>' : '<div class="acts"><button class="btn warn" data-action="inc" data-v="mecanico">Problema mecánico</button><button class="btn demora" data-action="inc" data-v="demora">Tengo una demora</button></div>');
  out += '<article class="truck" style="margin-top:16px"><div class="truck-top"><span class="plate">' + esc(c.patente) + '</span>' + estadoPill(c) + '</div><div><div class="who">' + esc(c.chofer) + '</div><div class="meta"><span>' + esc(c.empresa) + '</span><span>Capacidad <b>' + c.capacidad_tn + ' tn</b> · ' + c.traccion + '</span></div></div>' + traza + incBox(c) + '<div class="col">' + acts + nota + inc + pendHtml() + '</div></article>';
  out += '<h2 class="sec-h">Carga programada</h2>';
  if(!g) out += vacio('Todavía no tenés carga programada. El supervisor te va a asignar un contratista.', 'margin-top:12px');
  else { var q = colaDe(g.contratista_id).filter(function(x){ return x.estado === 'programado'; }), p2 = 0; q.forEach(function(x, i){ if(x.id === g.id) p2 = i + 1; });
    out += '<div class="assign"><span class="cn">' + esc(contrNombre(g.contratista_id)) + '</span><span class="pos">Hora programada <b>' + esc(g.hora) + ' hs</b></span><span class="pos">' + (g.estado === 'cargando' ? '<b>Cargando ahora</b>' : 'Lugar en la cola: <b>' + p2 + ' de ' + q.length + '</b>') + '</span></div><h2 class="sec-h">Disponibilidad en ' + esc(contrNombre(g.contratista_id)) + '</h2>' + dispHtml(g.contratista_id); }
  var ab = dispAbierta(), dm = c.disp_manana;
  out += '<h2 class="sec-h">Disponibilidad para mañana</h2><p class="note" style="margin:4px 0 0">' + (ab ? 'Avisá hasta las ' + S.cierres.disponibilidad + ' hs si vas a estar disponible para el programa de ' + tomorrow() + '. Podés cambiar tu respuesta hasta esa hora.' : 'La respuesta cerró a las ' + S.cierres.disponibilidad + ' hs.') + '</p>' +
    (ro ? '' : '<div class="acts" style="margin-top:10px">' + [['si', 'Voy a estar disponible'], ['no', 'No voy a estar disponible']].map(function(x){ return '<button class="btn' + (dm && dm.valor === x[0] ? ' primary' : '') + '" data-action="dispm" data-v="' + x[0] + '" aria-pressed="' + !!(dm && dm.valor === x[0]) + '"' + (ab ? '' : ' disabled') + '>' + x[1] + '</button>'; }).join('') + '</div>') +
    (dm ? '<p class="note" style="margin:6px 0 0">Tu respuesta: <b>' + dispTxt(c) + '</b></p>' : '<p class="note" style="margin:6px 0 0">' + (ab ? 'Todavía no respondiste.' : 'No respondiste a tiempo.') + '</p>');
  out += '<h2 class="sec-h">Programa de mañana</h2>';
  var gm = progDe(c.id, 'manana');
  if(!emitido('manana')) out += vacio('Todavía no fue emitido. Se emite después del cierre de relevamiento (' + S.cierres.relevamiento + ' hs).', 'margin-top:12px');
  else if(!gm) out += vacio('No tenés carga programada para mañana.', 'margin-top:12px');
  else { var ini2 = inicioFrente(gm.contratista_id, 'manana'); out += '<div class="assign"><span class="cn">' + esc(contrNombre(gm.contratista_id)) + '</span><span class="pos">' + tomorrow() + '</span><span class="pos">Inicio de carga del frente <b>' + esc(ini2 || gm.hora) + ' hs</b></span><span class="pos">Tu hora de carga <b>' + esc(gm.hora) + ' hs</b></span></div><h2 class="sec-h">Stock en ' + esc(contrNombre(gm.contratista_id)) + '</h2><p class="note" style="margin:4px 0 0">Según el último relevamiento · el relevamiento de hoy cierra a las ' + S.cierres.relevamiento + ' hs.</p>' + stockPrioHtml(gm.contratista_id, 'manana'); }
  return out;
}

// ---------- fletes ----------
function tablaTarifas(lins, mio){
  return '<div class="rows" style="padding:4px 14px 6px;margin-top:8px;overflow-x:auto"><table class="tbl"><thead><tr><th>Destino</th><th>Km asf.</th><th>Km tierra</th><th' + (mio === '4x2' ? ' style="color:var(--accent)"' : '') + '>4x2 ($/tn)</th><th' + (mio === '6x4' ? ' style="color:var(--accent)"' : '') + '>6x4 ($/tn)</th>' + (mio ? '' : '<th></th>') + '</tr></thead><tbody>' +
    lins.map(function(t){ var d = destino(t.destino_id); return '<tr><td>' + esc(d ? d.nombre : '?') + '</td><td>' + t.km_asfalto + '</td><td>' + t.km_tierra + '</td><td' + (mio === '4x2' ? ' style="font-weight:700"' : '') + '>' + (t.tarifa_4x2 ? money(t.tarifa_4x2) : t.tarifa_4x2 === null ? '·' : '-') + '</td><td' + (mio === '6x4' ? ' style="font-weight:700"' : '') + '>' + (t.tarifa_6x4 ? money(t.tarifa_6x4) : t.tarifa_6x4 === null ? '·' : '-') + '</td>' + (mio ? '' : '<td><button class="link" data-action="tarifa-edit" data-id="' + t.id + '">Editar</button></td>') + '</tr>'; }).join('') + '</tbody></table></div>';
}
function remitosHtml(){
  var rs = remitos(), mesK = S.hoy.slice(0, 8) + '01', mes = rs.filter(function(r){ return r.fecha >= mesK; }), acum = {}, run = 0;
  mes.slice().sort(function(a, b){ return a.fecha === b.fecha ? (a.cargado_en < b.cargado_en ? -1 : 1) : (a.fecha < b.fecha ? -1 : 1); }).forEach(function(r){ run += importeRem(r) || 0; acum[r.id] = run; });
  var out = '<h2 class="sec-h">Remitos y facturación por carga<span>' + rs.length + '</span></h2><p class="note" style="margin:4px 0 10px">Sacale una foto al remito: la app lee el número, el rodal, el destino y las toneladas, y la facturación de cada carga se calcula multiplicando la tarifa por tonelada ($/tn) según tu tipo de camión por las toneladas del remito.</p>' +
    (soloLectura() ? '' : '<label class="btn primary block" for="rem-file" role="button">Escanear remito con la cámara</label><input type="file" id="rem-file" accept="image/*" capture="environment" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none"><button class="btn block" data-action="remito-manual" style="margin-top:8px">Cargar remito sin foto</button>');
  if(mes.length){
    var by = {}; mes.forEach(function(r){ by[r.rodal] = by[r.rodal] || { n: 0, tn: 0, imp: 0 }; by[r.rodal].n++; by[r.rodal].tn += r.toneladas; by[r.rodal].imp += importeRem(r) || 0; });
    out += '<h2 class="sec-h">Por punto de carga · mes<span>' + f1(sum(mes, function(r){ return r.toneladas; })) + ' tn</span></h2><div class="rows" style="padding:4px 14px 6px;margin-top:8px;overflow-x:auto"><table class="tbl"><thead><tr><th>Rodal</th><th>Remitos</th><th>Toneladas</th><th>Facturado</th></tr></thead><tbody>' + Object.keys(by).sort().map(function(k){ return '<tr><td class="lg">' + esc(k) + '</td><td>' + by[k].n + '</td><td>' + f1(by[k].tn) + '</td><td><b>' + money(by[k].imp) + '</b></td></tr>'; }).join('') + '</tbody></table></div>';
  }
  return out + (rs.length ? '<div style="margin-top:12px">' + rs.map(function(r){ var imp = importeRem(r); return '<button class="rem" data-action="remito-ver" data-id="' + r.id + '">' + (r.foto_mini_url ? '<img class="th" alt="" src="' + esc(r.foto_mini_url) + '">' : '<span class="th">sin foto</span>') + '<span class="tx"><b>' + esc(r.numero || 'Sin número') + (r.carga_id ? ' <span class="pill st-disponible" style="font-size:10px;padding:0 5px;vertical-align:middle">Trazado</span>' : '') + '</b><span class="note" style="margin:0"><span class="mono">' + esc(r.rodal) + '</span>' + (r.destino ? ' → ' + esc(r.destino) : ' · sin destino') + ' · ' + diaLabel(r.fecha) + '</span><span class="note" style="margin:0">' + f1(r.toneladas) + ' tn' + (r.tarifa_aplicada ? ' × ' + money(r.tarifa_aplicada) + '/tn' : '') + (acum[r.id] != null ? ' · acum. ' + money(acum[r.id]) : '') + '</span></span><span class="tn"' + (imp ? '' : ' style="color:var(--muted);font-size:13px"') + '>' + (imp ? money(imp) : 'Sin tarifa') + '</span></button>'; }).join('') + '</div>' : vacio('Todavía no cargaste remitos.'));
}
function seguimientoHtml(){
  var rs = remitos(), buckets = {}, order = [], cur = S.hoy.slice(0, 7), MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  rs.forEach(function(r){ var k = r.fecha.slice(0, 7); if(!buckets[k]) buckets[k] = { imp: 0, n: 0, tn: 0 }; buckets[k].imp += importeRem(r) || 0; buckets[k].n++; buckets[k].tn += r.toneladas; });
  for(var i = 5; i >= 0; i--){ var d = new Date(cur + '-15T12:00:00'); d.setMonth(d.getMonth() - i); order.push(d.getFullYear() + '-' + pad(d.getMonth() + 1)); }
  var mx = Math.max.apply(null, order.map(function(k){ return buckets[k] ? buckets[k].imp : 0; }).concat([1]));
  return '<h2 class="sec-h">Seguimiento de facturación<span>por mes</span></h2><div class="rows" style="margin-top:12px">' + order.slice().reverse().map(function(k, idx){
    var b = buckets[k] || { imp: 0, n: 0, tn: 0 }, prevK = order[order.length - 2 - idx], pb = prevK && buckets[prevK] ? buckets[prevK].imp : 0, esCur = k === cur, vr = pb > 0 && !esCur ? Math.round((b.imp - pb) / pb * 100) : null;
    return '<div class="row" style="cursor:default"><span class="t"><b>' + MES[parseInt(k.slice(5), 10) - 1] + ' ' + k.slice(0, 4) + '</b>' + (esCur ? ' <span class="note" style="margin:0">· en curso</span>' : '') + '</span><span class="s"><span>' + b.n + ' remito' + (b.n === 1 ? '' : 's') + '</span><span>' + f1(b.tn) + ' tn</span>' + (vr != null ? '<span style="color:' + (vr < 0 ? 'var(--danger)' : 'var(--accent)') + '">' + (vr > 0 ? '+' : '') + vr + '% vs mes anterior</span>' : '') + '</span><span class="m">' + money(b.imp) + '<small>facturado</small></span><span style="grid-column:1/3;height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:6px"><span style="display:block;height:100%;width:' + Math.round(b.imp / mx * 100) + '%;background:var(--accent);opacity:' + (esCur ? 1 : .6) + '"></span></span></div>'; }).join('') + '</div>';
}
function viewFletes(){
  var cm = camion(ui.camionId), mio = tipoCam(cm), rs = remitos(), mesK = S.hoy.slice(0, 8) + '01', mes = rs.filter(function(r){ return r.fecha >= mesK; });
  var tot = function(a){ return sum(a, function(r){ return importeRem(r) || 0; }); }, sinT = mes.filter(function(r){ return !importeRem(r); }).length, desp = S.despachos_mes || 0, faltan = Math.max(0, desp - mes.length);
  var out = '<section class="summary"><div class="big"><span class="n">' + money(tot(mes)) + '</span><span class="l">Facturado este mes · ' + mes.length + ' remito' + (mes.length === 1 ? '' : 's') + ' · ' + f1(sum(mes, function(r){ return r.toneladas; })) + ' tn</span></div><div class="legend" style="margin-top:12px"><span>Acumulado general <b>' + money(tot(rs)) + '</b></span><span>Remitos en total <b>' + rs.length + '</b></span><span>Tu camión <b>' + mio + '</b></span></div></section>' +
    '<button class="btn block" data-action="rep-fletes" style="margin-top:10px">Descargar reporte PDF de rendimiento y facturación</button>' + pendHtml();
  if(sinT) out += '<p class="note" style="margin-top:8px">' + sinT + ' remito' + (sinT === 1 ? '' : 's') + ' del mes sin tarifa (falta el destino o el tarifario del rodal): no suma' + (sinT === 1 ? '' : 'n') + ' a la facturación.</p>';
  if(faltan) out += '<p class="note" style="margin-top:8px;color:var(--st-cargando)">Control: tenés ' + desp + ' despachos este mes y ' + mes.length + ' remitos cargados. Faltan ' + faltan + ' remito' + (faltan === 1 ? '' : 's') + ' por escanear.</p>';
  out += seguimientoHtml() + remitosHtml() + '<h2 class="sec-h">Tarifas por rodal y destino<span>por tonelada</span></h2>';
  rodales().forEach(function(r){ var lins = tarifas().filter(function(t){ return t.rodal_id === r.id; }); out += '<section class="group"><div class="group-h"><h2 class="mono">' + esc(r.codigo) + '</h2><span>' + esc(r.contratista) + '</span></div>' + (lins.length ? tablaTarifas(lins, mio) : '<p class="note" style="margin:0">Sin tarifas cargadas.</p>') + '</section>'; });
  return out + '<p class="note" style="margin-top:10px">La facturación sale de los remitos cargados: cada remito se calcula multiplicando la tarifa por tonelada ($/tn) del rodal y el destino para tu tipo de camión (4x2 o 6x4) por las toneladas netas del remito.</p>';
}

// ---------- tarifario (jefe) ----------
function viewTarifas(){
  var out = '<p class="hint" style="margin:0 0 10px">Cada rodal es un punto de carga con su código. Cargá los rodales y, para cada uno, los destinos con km de asfalto, km de tierra y la tarifa en pesos por tonelada ($/tn) para camión 4x2 y 6x4.</p><button class="btn block" data-action="importar" style="margin-bottom:12px">Importar desde planilla (.xlsx o .csv)</button>';
  if(!rodales().length) out += vacio('Todavía no cargaste rodales. Tocá + Rodal para empezar.');
  rodales().forEach(function(r){ var lins = tarifas().filter(function(t){ return t.rodal_id === r.id; }); out += '<section class="group"><div class="group-h"><h2 class="mono">' + esc(r.codigo) + '</h2><span>' + esc(r.contratista) + '</span></div>' + (lins.length ? tablaTarifas(lins, null) : '<p class="note" style="margin:0">Sin destinos con tarifa todavía.</p>') + '<div class="two" style="margin-top:8px"><button class="btn primary" data-action="tarifa-new" data-id="' + r.id + '">+ Destino</button><button class="btn" data-action="rodal-baja" data-id="' + r.id + '">Quitar rodal</button></div></section>'; });
  return out;
}

// ---------- análisis (supervisor) ----------
function filasRank(rank, gen, labelFn, extraFn, unidad){
  var mx = rank[rank.length - 1].prom || 1;
  return '<div class="rows" style="margin-top:12px">' + rank.map(function(r, i){ var dif = r.prom - gen; return '<div class="row" style="cursor:default"><span class="t"><span style="color:var(--muted);font-family:var(--font-mono);font-size:12px">' + (i + 1) + '.</span> ' + labelFn(r) + '</span><span class="s"><span>' + r.n + ' ' + (r.n === 1 ? unidad : unidad + 's') + '</span>' + (extraFn ? extraFn(r) : '') + '<span>Rango ' + fmtMin(r.min) + ' - ' + fmtMin(r.max) + '</span>' + (r.esp != null ? '<span>Espera ' + fmtMin(r.esp) + '</span>' : '') + '<span style="color:' + (dif > 10 ? 'var(--danger)' : dif < -10 ? 'var(--accent)' : 'var(--muted)') + '">' + (Math.abs(dif) <= 10 ? 'En el promedio' : (dif > 0 ? '+' : '-') + fmtMin(Math.abs(dif)) + ' vs promedio') + '</span></span><span class="m">' + fmtMin(r.prom) + '<small>prom. ' + unidad + '</small></span><span style="grid-column:1/3;height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:6px"><span style="display:block;height:100%;width:' + Math.round(r.prom / mx * 100) + '%;background:var(--accent);opacity:.75"></span></span></div>'; }).join('') + '</div>';
}
function viewAnalisis(){
  var f = ui.acirc, vista = ui.avista, A = ui.analisis;
  var out = '<div class="chips" role="group" aria-label="Comparar por">' + [['punto', 'Puntos de carga'], ['destino', 'Industrias y destinos'], ['cruce', 'Cruce'], ['transp', 'Transportistas'], ['tcarga', 'Tiempos de carga'], ['demoras', 'Demoras de inicio'], ['traza', 'Trazabilidad y remitos']].map(function(x){ return '<button class="chip" data-action="avista" data-v="' + x[0] + '" aria-pressed="' + (vista === x[0]) + '">' + x[1] + '</button>'; }).join('') + '</div>' +
    (vista === 'demoras' || vista === 'traza' ? '' : '<div class="chips" role="group" aria-label="Circuito" style="margin-top:8px">' + [['todos', 'Todos'], ['industria', 'Industria propia'], ['ventas', 'Ventas']].map(function(x){ return '<button class="chip" data-action="acirc" data-v="' + x[0] + '" aria-pressed="' + (f === x[0]) + '">' + x[1] + '</button>'; }).join('') + '</div>');
  if(vista === 'traza'){
    var allKs = cargas().filter(function(k){ return k.estado === 'finalizada'; }).sort(function(a, b){ return (b.remito_id ? 1 : 0) - (a.remito_id ? 1 : 0) || (a.fin_en < b.fin_en ? 1 : -1); });
    var ks = allKs.slice(0, 12), conRem = allKs.filter(function(k){ return k.remito_id; }).length, sinRem = allKs.length - conRem, rc = remitosControl();
    out += '<section class="summary"><div class="big"><span class="n">' + conRem + '</span><span class="u">trazados</span><span class="l">Remitos vinculados a despachos de los últimos 7 días · ' + sinRem + ' pendientes de remito</span></div>' +
      '<div class="legend" style="margin-top:10px"><span>Despachos (7 días) <b>' + allKs.length + '</b></span><span>Con remito <b>' + conRem + '</b></span><span>Sin remito <b>' + sinRem + '</b></span></div></section>';
    out += '<h2 class="sec-h">Trazabilidad Monte → Báscula → Remito<span>últimos ' + ks.length + '</span></h2>';
    out += ks.length ? '<div class="rows" style="margin-top:12px">' + ks.map(function(k){
      var c = camion(k.camion_id) || {};
      return '<div class="row" style="cursor:default"><span class="t"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + '</span>' +
        '<span class="s"><span>' + esc(contrNombre(k.contratista_id)) + (k.rodal ? ' · <b class="mono">' + esc(k.rodal) + '</b>' : '') + '</span><span>' + esc(k.destino) + ' (' + CIRC[k.circuito] + ')</span><span>' + diaLabel(k.jornada) + '</span>' + etaBadge(k) + '</span>' +
        '<span class="m">' + f1(cargaTotal(k)) + '<small>m³</small></span>' +
        '<div style="grid-column:1/3;margin-top:8px">' + trazaSteps(k, true) + '</div></div>';
    }).join('') + '</div>' : vacio('Todavía no hay despachos finalizados para auditar.');
    out += '<h2 class="sec-h">Remitos cargados recientemente<span>' + rc.length + '</span></h2>';
    out += rc.length ? '<div style="margin-top:12px">' + rc.map(function(r){
      return '<button class="rem" data-action="remito-ver" data-id="' + r.id + '">' +
        (r.foto_mini_url ? '<img class="th" alt="" src="' + esc(r.foto_mini_url) + '">' : '<span class="th">sin foto</span>') +
        '<span class="tx"><b>' + esc(r.numero || 'Sin número') + ' · <span class="mono">' + esc(r.patente) + '</span></b>' +
        '<span class="note" style="margin:0"><span class="mono">' + esc(r.rodal) + '</span>' + (r.destino ? ' → ' + esc(r.destino) : '') + ' · ' + diaLabel(r.fecha) + ' · ' + esc(r.chofer) + '</span>' +
        '<span class="note" style="margin:0">' + (r.carga_id ? 'Vinculado a despacho' : 'Sin despacho vinculado') + ' · ' + (r.origen_dato === 'ocr' ? 'OCR' : 'Manual') + '</span></span>' +
        '<span class="tn">' + f1(r.toneladas) + ' tn</span></button>';
    }).join('') + '</div>' : vacio('Todavía no hay remitos cargados.');
    return out;
  }
  if(!A || A.circuito !== f) return out + '<p class="note" style="margin-top:16px"><span class="spinner"></span> Calculando…</p>';
  var cam = function(r){ return '<span class="plate" style="font-size:14px">' + esc(r.patente) + '</span> &nbsp;' + esc(r.chofer); }, nCam = function(r){ return '<span>' + r.camiones + (r.camiones === 1 ? ' camión' : ' camiones') + '</span>'; };
  var nota = '<p class="note" style="margin-top:10px">El ciclo se mide desde que termina la carga y el camión sale del punto de carga hasta que vuelve a él (cuando entra en la fila de espera). Incluye viaje, descarga y regreso. Últimos ' + A.dias + ' días.</p>';
  if(vista === 'demoras'){
    var D = A.demoras;
    if(!D.n) return out + vacio('Todavía no hay inicios de carga registrados para comparar con el horario confirmado.');
    out += '<section class="summary"><div class="big"><span class="n">' + fmtMin(D.gen) + '</span><span class="l">Demora promedio de inicio de carga · ' + D.n + ' inicios</span></div><div class="legend" style="margin-top:12px"><span>Inicios a horario <b>' + D.pct_horario + '%</b></span>' + (D.rank.length ? '<span>Mayor demora <b>' + esc(D.rank[0].nombre) + ' · ' + fmtMin(D.rank[0].prom) + '</b></span>' : '') + '</div></section><h2 class="sec-h">Hoy<span>' + today() + '</span></h2>';
    out += D.hoy.length ? '<div class="rows" style="margin-top:12px">' + D.hoy.map(function(x){ return '<div class="row" style="cursor:default"><span class="t"><b>' + esc(x.contratista) + '</b></span><span class="s"><span>Confirmado ' + esc(x.hora_plan) + ' hs' + (x.fuente === 'programa' ? ' (programa)' : '') + '</span><span>Inició ' + esc(x.hora_real) + ' hs</span></span><span class="m" style="color:' + (x.dem > 15 ? 'var(--danger)' : !x.a_horario ? 'var(--st-cargando)' : 'var(--accent)') + '">' + (x.a_horario ? 'A horario' : '+' + fmtMin(x.dem)) + '<small>' + (x.dif < 0 ? 'adelantó ' + fmtMin(-x.dif) : 'demora') + '</small></span></div>'; }).join('') + '</div>' : vacio('Todavía no empezó la carga en ningún frente hoy.');
    var mx = Math.max(D.rank.length ? D.rank[0].prom : 1, 1);
    out += '<h2 class="sec-h">Demora por contratista de elaboración<span>' + D.rank.length + '</span></h2><div class="rows" style="margin-top:12px">' + D.rank.map(function(r, i){ var dif = r.prom - D.gen; return '<div class="row" style="cursor:default"><span class="t"><span style="color:var(--muted);font-family:var(--font-mono);font-size:12px">' + (i + 1) + '.</span> <b>' + esc(r.nombre) + '</b></span><span class="s"><span>' + r.n + ' inicio' + (r.n === 1 ? '' : 's') + '</span><span>A horario ' + r.pt + '%</span><span>Máx. ' + fmtMin(r.max) + '</span><span style="color:' + (dif > 10 ? 'var(--danger)' : dif < -10 ? 'var(--accent)' : 'var(--muted)') + '">' + (Math.abs(dif) <= 10 ? 'En el promedio' : (dif > 0 ? '+' : '-') + fmtMin(Math.abs(dif)) + ' vs promedio') + '</span></span><span class="m">' + fmtMin(r.prom) + '<small>prom. demora</small></span><span style="grid-column:1/3;height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:6px"><span style="display:block;height:100%;width:' + Math.round(r.prom / mx * 100) + '%;background:var(--accent);opacity:.75"></span></span></div>'; }).join('') + '</div>';
    return out + '<p class="note" style="margin-top:10px">La demora es la diferencia entre el horario de inicio confirmado por el elaborador y la hora en que arranca la primera carga del frente. Hasta ' + D.tolerancia + ' min se considera a horario; si el frente arranca antes, no cuenta como demora.</p>';
  }
  if(vista === 'tcarga'){
    var T = A.tcarga;
    if(!T.n) return out + vacio('Todavía no hay cargas finalizadas para medir tiempos.');
    out += '<section class="summary"><div class="big"><span class="n">' + fmtMin(T.gen) + '</span><span class="l">Tiempo de carga promedio · ' + T.n + ' cargas</span></div><div class="legend" style="margin-top:12px"><span>Más rápido <b>' + esc(T.por_camion[0].patente) + ' · ' + fmtMin(T.por_camion[0].prom) + '</b></span><span>Más lento <b>' + esc(T.por_camion[T.por_camion.length - 1].patente) + ' · ' + fmtMin(T.por_camion[T.por_camion.length - 1].prom) + '</b></span>' + (T.espera_prom != null ? '<span>Espera en fila <b>' + fmtMin(T.espera_prom) + '</b></span>' : '') + '</div></section><h2 class="sec-h">Cargas de hoy<span>' + T.hoy.length + '</span></h2>';
    out += T.hoy.length ? '<div class="rows" style="margin-top:12px">' + T.hoy.map(function(c){ var dif = c.min - T.gen; return '<div class="row" style="cursor:default"><span class="t"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + '</span><span class="s"><span>' + esc(c.contratista) + '</span><span>' + esc(c.ini) + ' a ' + esc(c.fin) + ' hs</span><span style="color:' + (dif > 10 ? 'var(--danger)' : dif < -10 ? 'var(--accent)' : 'var(--muted)') + '">' + (Math.abs(dif) <= 10 ? 'En el promedio' : (dif > 0 ? '+' : '-') + fmtMin(Math.abs(dif)) + ' vs promedio') + '</span></span><span class="m">' + fmtMin(c.min) + '<small>carga</small></span></div>'; }).join('') + '</div>' : vacio('Todavía no se finalizó ninguna carga hoy.');
    return out + '<h2 class="sec-h">Por punto de carga<span>' + T.por_punto.length + '</span></h2>' + filasRank(T.por_punto, T.gen, function(r){ return '<b>' + esc(r.nombre) + '</b>'; }, nCam, 'carga') + '<p class="note" style="margin-top:10px">El tiempo de carga va desde que el camión empieza a cargar hasta que el operador finaliza la carga.</p>';
  }
  if(!A.n_ciclos) return out + vacio('Todavía no hay ciclos completos registrados.');
  var head = function(txt){ return '<section class="summary"><div class="big"><span class="n">' + fmtMin(A.gen_ciclo) + '</span><span class="l">Ciclo promedio general · ' + A.n_ciclos + ' ciclos</span></div>' + (txt || '') + '</section>'; };
  if(vista === 'punto'){ var rp = A.por_punto; return out + head('<div class="legend" style="margin-top:12px"><span>Más ágil <b>' + esc(rp[0].nombre) + ' · ' + fmtMin(rp[0].prom) + '</b></span><span>Más lento <b>' + esc(rp[rp.length - 1].nombre) + ' · ' + fmtMin(rp[rp.length - 1].prom) + '</b></span>' + (A.espera_prom != null ? '<span>Espera promedio en carga <b>' + fmtMin(A.espera_prom) + '</b></span>' : '') + '</div>') + '<h2 class="sec-h">Por punto de carga<span>' + rp.length + '</span></h2>' + filasRank(rp, A.gen_ciclo, function(r){ return '<b>' + esc(r.nombre) + '</b>'; }, nCam, 'ciclo') + nota; }
  if(vista === 'destino'){ var rd = A.por_destino, pc = A.por_circuito; return out + head('<div class="legend" style="margin-top:12px">' + (pc.industria != null ? '<span>Industria propia <b>' + fmtMin(pc.industria) + '</b></span>' : '') + (pc.ventas != null ? '<span>Ventas <b>' + fmtMin(pc.ventas) + '</b></span>' : '') + '</div>') + '<h2 class="sec-h">Por industria y destino<span>' + rd.length + '</span></h2>' + filasRank(rd, A.gen_ciclo, function(r){ return '<b>' + esc(r.nombre) + '</b> <span class="note" style="margin:0">· ' + CIRC[r.circuito] + '</span>'; }, nCam, 'ciclo') + nota; }
  if(vista === 'cruce'){
    var X = A.cruce, vals = Object.keys(X.celdas).map(function(k){ return X.celdas[k]; }), vmin = Math.min.apply(null, vals), vmax = Math.max.apply(null, vals);
    return out + head() + '<h2 class="sec-h">Punto de carga × destino<span>prom. ciclo</span></h2><div class="rows" style="margin-top:12px;overflow-x:auto;padding:6px 10px"><table class="tbl" style="min-width:' + (130 + X.destinos.length * 78) + 'px"><thead><tr><th>Punto de carga</th>' + X.destinos.map(function(d){ return '<th style="text-align:right">' + esc(d.nombre.replace(' (puerto)', '')) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      X.contratistas.map(function(ct){ return '<tr><td>' + esc(ct.nombre) + '</td>' + X.destinos.map(function(d){ var v = X.celdas[ct.id + '|' + d.id]; if(v == null) return '<td style="text-align:right;color:var(--muted)">-</td>'; var rel = vmax > vmin ? (v - vmin) / (vmax - vmin) : 0; return '<td style="text-align:right;font-family:var(--font-mono);font-weight:600;' + (rel > .75 ? 'color:var(--danger)' : rel < .25 ? 'color:var(--accent)' : '') + '">' + fmtMin(v) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div><p class="note" style="margin-top:10px">En rojo las combinaciones más lentas y en verde las más rápidas. "-" indica que todavía no hay ciclos de esa combinación.</p>' + nota;
  }
  var rk = A.por_camion;
  return out + head('<div class="legend" style="margin-top:12px"><span>Más rápido <b>' + esc(rk[0].patente) + ' · ' + fmtMin(rk[0].prom) + '</b></span><span>Más lento <b>' + esc(rk[rk.length - 1].patente) + ' · ' + fmtMin(rk[rk.length - 1].prom) + '</b></span></div>') + '<h2 class="sec-h">Ranking por transportista<span>' + rk.length + '</span></h2>' + filasRank(rk, A.gen_ciclo, cam, null, 'ciclo') + nota;
}

// ---------- administración ----------
function viewUsuarios(){
  var us = ui.usuarios;
  if(!us) return '<p class="note" style="margin-top:16px"><span class="spinner"></span> Cargando usuarios…</p>';
  var pend = us.filter(function(u){ return !u.activo; }), act = us.filter(function(u){ return u.activo; });
  var card = function(u){ return '<article class="truck"><div class="truck-top"><span class="who">' + esc(u.nombre) + '</span><span class="pill ' + (u.activo ? 'st-disponible' : 'inc-demora') + '">' + (u.activo ? 'Activo' : 'Pendiente') + '</span></div><div class="meta"><span>@' + esc(u.usuario) + '</span><span>' + esc(u.empresa) + ' (' + esc(u.tipo_empresa) + ')</span><span>' + esc(u.puesto) + '</span>' + (u.contratista ? '<span>Contratista: <b>' + esc(u.contratista) + '</b></span>' : '') + '<span>Roles: <b>' + (u.roles.length ? u.roles.map(function(r){ return ROLES[r] || r; }).join(', ') : 'ninguno') + '</b></span>' + (u.ultimo_acceso ? '<span>Último acceso ' + diaLabel(u.ultimo_acceso) + ' ' + hm(u.ultimo_acceso) + '</span>' : '') + '</div><button class="btn block" data-action="usuario-edit" data-id="' + u.id + '">' + (u.activo ? 'Editar' : 'Revisar y aprobar') + '</button></article>'; };
  return '<section class="group"><div class="group-h"><h2>Pendientes de aprobación</h2><span>' + pend.length + '</span></div><div class="list" style="margin-top:0">' + (pend.length ? pend.map(card).join('') : vacio('No hay usuarios pendientes.', 'margin-top:0')) + '</div></section><section class="group"><div class="group-h"><h2>Usuarios activos</h2><span>' + act.length + '</span></div><div class="list" style="margin-top:0">' + act.map(card).join('') + '</div></section>';
}
function viewCatalogos(){
  var sec = function(titulo, items, tipo, extra){ return '<section class="group"><div class="group-h"><h2>' + titulo + '</h2><span style="display:flex;gap:12px;align-items:baseline">' + items.length + '<button class="link ok" data-action="cat-new" data-v="' + tipo + '">+ Agregar</button></span></div><div class="rows">' + (items.length ? items.map(function(x){ return '<div class="row" style="cursor:default"><span class="t">' + esc(x.nombre != null ? x.nombre : x) + '</span>' + (extra ? '<span class="s"><span>' + extra(x) + '</span></span>' : '') + '<button class="link" data-action="cat-del" data-v="' + tipo + '" data-id="' + (x.id || x) + '" style="grid-column:2;grid-row:1/3;color:var(--danger)">Quitar</button></div>'; }).join('') : vacio('Vacío.', 'margin:0')) + '</div></section>'; };
  return '<p class="hint" style="margin:0 0 10px">Los catálogos se administran acá, nunca en el código. Las bajas son lógicas: el historial se conserva.</p>' + sec('Contratistas (elaboración)', contratistas(), 'contratistas') + sec('Destinos', destinos(), 'destinos', function(d){ return CIRC[d.circuito]; }) + sec('Especies', especies(), 'especies') + sec('Largos (pies)', largos(), 'largos');
}

function bodyHtml(){
  var t = ui.tab;
  if(t === 'stock') return viewStock(); if(t === 'camiones') return viewCamiones(); if(t === 'analisis') return viewAnalisis(); if(t === 'pedido') return viewPedido(); if(t === 'pedidos') return viewPedidos();
  if(t === 'tarifas') return viewTarifas(); if(t === 'fletes') return viewFletes(); if(t === 'cola') return viewCola(); if(t === 'pend') return viewPend(); if(t === 'industria') return viewIndustria(); if(t === 'hist') return viewHist();
  if(t === 'usuarios') return viewUsuarios(); if(t === 'catalogos') return viewCatalogos();
  if(t === 'programa') return ui.rol === 'elaborador' ? viewProgElab() : ui.rol === 'transportista' ? viewProgTransp() : viewPrograma();
  return viewViaje();
}
