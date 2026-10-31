/* Controlador: render, carga de estado, acciones (con cola sin conexión) y arranque. */
(function(){
  var toastTimer = null;
  function toast(msg, err){ ui.msg = msg; ui.msgErr = !!err; render(); clearTimeout(toastTimer); toastTimer = setTimeout(function(){ ui.msg = ''; render(); }, err ? 5000 : 3000); }
  function savePref(){ try{ localStorage.setItem('lf.pref', JSON.stringify({ rol: ui.rol, camionId: ui.camionId, contrId: ui.contrId, tema: ui.tema })); }catch(e){} }

  // ---------- render ----------
  function render(){
    var y = window.scrollY, html, app = document.getElementById('app');
    if(!API.sesion()){ html = ui.vista === 'registro' ? viewRegistro() : viewLogin(); }
    else if(ui.editPerfil){ html = viewPerfil(); }
    else if(!ui.rol){ html = viewRol(); }
    else if(!S){ html = '<div class="empty" style="margin-top:40px">' + (ui.off ? 'Sin conexión y sin datos guardados para este rol. Conectate para cargar la información.' : '<span class="spinner"></span> Cargando…') + '</div><button class="btn block" data-action="cambiar-rol" style="margin-top:12px">Cambiar rol</button>'; }
    else if(ui.rol === 'transportista' && !ui.camionId){ ui.step = 'transportista'; html = viewRol(); }
    else if(ui.rol === 'elaborador' && !S.contratista_id){ ui.step = 'elaborador'; html = viewRol(); }
    else if(ui.rol === 'transportista' && camion(ui.camionId) && camion(ui.camionId).alta_estado !== 'aprobada'){ html = viewAlta(camion(ui.camionId)); }
    else if(ui.rol === 'transportista' && !camion(ui.camionId)){ ui.camionId = null; ui.step = 'transportista'; html = viewRol(); }
    else {
      if(!TABS[ui.rol].some(function(t){ return t[0] === ui.tab; })) ui.tab = defaultTab(ui.rol);
      var ro = soloLectura();
      var body; try{ body = bodyHtml(); }catch(e){ body = '<div class="empty">No se pudo dibujar esta pantalla: ' + esc(e.message) + '</div>'; console.error(e); }
      html = '<div' + (ro ? ' class="ro"' : '') + '>' + header() + roleBar() + (ro ? '<p class="note" style="margin:8px 0 0"><b>Vista de solo lectura</b> · ' + (misRoles().indexOf('admin') >= 0 ? 'Administración' : 'Jefe de Área Forestal') + '. Podés mirar este panel pero no modificar datos.</p>' : '') + body + nav() + '</div>';
    }
    app.innerHTML = html + sheetHtml() + (ui.msg ? '<div class="toast' + (ui.msgErr ? ' err' : '') + '" role="status">' + esc(ui.msg) + '</div>' : '');
    window.scrollTo(0, y);
  }

  // ---------- carga del estado ----------
  function paramsEstado(){
    var p = 'rol=' + encodeURIComponent(ui.rol);
    if(ui.rol === 'transportista' && ui.camionId) p += '&camion_id=' + encodeURIComponent(ui.camionId);
    if(ui.rol === 'elaborador' && ui.contrId) p += '&contratista_id=' + encodeURIComponent(ui.contrId);
    return p;
  }
  var cargandoEstado = null;
  function cargarEstado(manual){
    if(!API.sesion() || !ui.rol) return Promise.resolve();
    if(cargandoEstado) return cargandoEstado;
    ui.cargando = true; if(manual) render();
    cargandoEstado = API.llamar('GET', '/estado?' + paramsEstado()).then(function(s){
      S = s; ui.off = false; ui.updAt = hm(S.ahora); API.guardarEstado(S);
      if(S.me && S.me.roles){ var ses = API.sesion(); if(ses && ses.usuario){ ses.usuario.roles = S.me.roles; try{ if(localStorage.getItem('lf.sesion')) localStorage.setItem('lf.sesion', JSON.stringify(ses)); }catch(x){} } } // roles vigentes sin re-login; no revive una sesión ya cerrada
      if(ui.rol === 'transportista' && ui.camionId && !S.camion_id){ ui.camionId = null; savePref(); }
      if(manual) toast('Datos actualizados');
      if(ui.tab === 'analisis') cargarAnalisis(true);
    }).catch(function(e){
      if(e.status === 401 || e.status === 403 && e.codigo === 'usuario_inactivo'){ salir(); return; }
      if(e.offline){ ui.off = true; if(manual) toast('Sin conexión: se muestran los últimos datos guardados', true); }
      else if(e.status === 403){ toast(e.mensaje, true); ui.rol = null; savePref(); }
      else toast(errorTexto(e), true);
    }).finally(function(){ ui.cargando = false; cargandoEstado = null; render(); });
    return cargandoEstado;
  }
  function cargarAnalisis(silencioso){
    var circ = ui.acirc;
    if(ui.analisis && ui.analisis.circuito === circ && silencioso) return;
    API.llamar('GET', '/analisis?circuito=' + circ + '&dias=30').then(function(a){ ui.analisis = a; render(); }).catch(function(e){ if(!silencioso) toast(errorTexto(e), true); });
  }
  function cargarUsuarios(){ API.llamar('GET', '/usuarios').then(function(u){ ui.usuarios = u; render(); }).catch(function(e){ toast(errorTexto(e), true); }); }

  // ---------- acciones con cola sin conexión ----------
  function accion(metodo, ruta, body, opt){
    opt = opt || {};
    return API.llamar(metodo, ruta, body).then(function(r){ if(opt.exito) opt.exito(r); return cargarEstado(false).then(function(){ return r; }); }).catch(function(e){
      if(e.offline && opt.offline !== false){
        API.encolar({ metodo: metodo, ruta: ruta, body: body, desc: opt.desc || '' });
        if(opt.optimista){ try{ opt.optimista(); }catch(x){ console.error(x); } }
        if(S) API.guardarEstado(S);
        ui.off = true; toast('Guardado en este dispositivo · se envía al servidor cuando vuelva la conexión'); render();
        return null;
      }
      throw e;
    });
  }
  function enviarPendientes(){
    if(!API.pendientes() || !navigator.onLine) return;
    var conflictoCarga = null;
    API.enviarCola(function(op, err){
      if(err){
        toast('No se pudo enviar "' + (op.desc || op.ruta) + '": ' + errorTexto(err), true);
        if(err.codigo === 'stock_insuficiente' && op.ruta && op.ruta.indexOf('/cargas/') === 0 && op.body) conflictoCarga = { kid: op.ruta.split('/')[2], body: op.body, msg: err.mensaje };
      }
    }).then(function(r){
      if(r && r.enviados) toast('Se enviaron ' + r.enviados + ' cambio' + (r.enviados === 1 ? '' : 's'));
      cargarEstado(false).then(function(){
        if(conflictoCarga && carga(conflictoCarga.kid)){
          var b = conflictoCarga.body;
          ui.draft = { circuito: b.circuito || '', destino_id: b.destino_id || '', rodal_id: b.rodal_id || '', lineas: (b.lineas || []).map(function(l){ return { tipo: l.tipo, largo_pies: l.largo_pies, m3: String(l.volumen_m3).replace('.', ',') }; }) };
          openSheet({ type: 'finalizar', id: conflictoCarga.kid });
          ui.error = conflictoCarga.msg + '. Ajustá los volúmenes al stock actual y volvé a confirmar.';
          render();
        }
      });
    });
  }
  function salir(){ API.cerrar(); S = null; ui.rol = null; ui.step = null; ui.sheet = null; ui.camionId = null; ui.contrId = null; ui.vista = 'login'; savePref(); render(); }
  function entrar(rol){ ui.rol = rol; ui.step = null; ui.tab = defaultTab(rol); ui.fdia = rol === 'supervisor' ? 'manana' : 'hoy'; ui.analisis = null; ui.usuarios = null; S = null; savePref(); window.scrollTo(0, 0); render(); cargarEstado(false).then(function(){ if(rol === 'admin') cargarUsuarios(); }); }
  function openSheet(s){ ui.sheet = s; ui.error = ''; render(); var f = document.querySelector('.sheet input:not([type=radio]):not([type=checkbox]):not([type=file]), .sheet select'); if(f){ try{ f.focus({ preventScroll: true }); }catch(e){} } }
  function closeSheet(){ ui.remTok++; ui.sheet = null; ui.draft = null; ui.error = ''; render(); }
  function fallo(e){ ui.error = errorTexto(e); if(e && e.detalle && e.detalle.remito_id) ui.error += ' (podés abrirlo desde la lista)'; render(); }
  function ok(fn){ return function(r){ closeSheet(); if(fn) fn(r); }; }
  function cid(){ return ui.camionId; }

  function reducirImg(file, max, q){
    return new Promise(function(res, rej){
      var url = URL.createObjectURL(file), im = new Image();
      im.onload = function(){ var k = Math.min(1, max / Math.max(im.width, im.height)), c = document.createElement('canvas'); c.width = Math.max(1, Math.round(im.width * k)); c.height = Math.max(1, Math.round(im.height * k)); c.getContext('2d').drawImage(im, 0, 0, c.width, c.height); URL.revokeObjectURL(url); c.toBlob(function(b){ if(!b){ rej(new Error('img')); return; } var fr = new FileReader(); fr.onload = function(){ res({ blob: b, url: fr.result }); }; fr.onerror = rej; fr.readAsDataURL(b); }, 'image/jpeg', q); };
      im.onerror = function(){ URL.revokeObjectURL(url); rej(new Error('img')); };
      im.src = url;
    });
  }
  function prefillRemitoDraft(base){
    var cm = camion(cid()), u = cm ? ultCarga(cm) : null;
    var vinc = u && !u.remito_id ? u : null;
    return Object.assign({
      fecha: S.hoy,
      rodal_id: vinc && vinc.rodal_id ? vinc.rodal_id : '',
      destino_id: vinc && vinc.destino_id ? vinc.destino_id : '',
      carga_id: vinc ? vinc.id : null,
      carga_info: vinc ? ((vinc.rodal ? vinc.rodal + ' → ' : '') + vinc.destino + ' · ' + f1(cargaTotal(vinc)) + ' m³ (' + hm(vinc.fin_en) + ' hs)') : ''
    }, base || {});
  }
  function procesarRemito(file){
    var tok = ++ui.remTok;
    ui.draft = { estado: 'leyendo', foto: null };
    openSheet({ type: 'remito' });
    reducirImg(file, 1600, 0.8).then(function(r){
      if(tok !== ui.remTok) return;
      ui.draft.foto = r.url; render();
      if(!navigator.onLine){ ui.draft = prefillRemitoDraft({ estado: 'offline', foto: r.url }); render(); return; }
      var fd = new FormData(); fd.append('archivo', r.blob, 'remito.jpg');
      return API.llamar('POST', '/remitos/foto?camion_id=' + encodeURIComponent(cid()), fd).then(function(b){
        if(tok !== ui.remTok || !ui.sheet || ui.sheet.type !== 'remito') return;
        var d = b.datos || {}, pre = prefillRemitoDraft();
        ui.draft = { estado: b.estado_ocr === 'leido' ? 'listo' : 'manual', foto: r.url, borrador_id: b.borrador_id, numero: d.numero || '', fecha: d.fecha || S.hoy, rodal_id: d.rodal_id || pre.rodal_id, destino_id: d.destino_id || pre.destino_id, carga_id: pre.carga_id, carga_info: pre.carga_info, toneladas: d.toneladas != null ? d.toneladas : '', patente_leida: d.patente_leida || '' };
        if(b.estado_ocr === 'sin_cupo') toast('Se alcanzó el límite diario de lecturas: cargá los datos a mano', true);
        render();
      }).catch(function(e){
        if(tok !== ui.remTok || !ui.sheet || ui.sheet.type !== 'remito') return;
        if(e.offline){ ui.draft = prefillRemitoDraft({ estado: 'offline', foto: r.url }); render(); return; }
        ui.draft = prefillRemitoDraft({ estado: 'manual', foto: r.url }); ui.error = errorTexto(e); render();
      });
    }).catch(function(){ if(tok !== ui.remTok || !ui.sheet || ui.sheet.type !== 'remito') return; ui.draft = { estado: 'error' }; render(); });
  }

  // ---------- clics ----------
  document.addEventListener('click', function(e){
    var el = e.target.closest('[data-action]'); if(!el) return;
    var a = el.getAttribute('data-action'), id = el.getAttribute('data-id'), v = el.getAttribute('data-v');
    if(a === 'close-sheet'){ if(el.classList.contains('overlay') && e.target !== el) return; closeSheet(); return; }
    if(a === 'toggle-theme'){
      var act = document.documentElement.getAttribute('data-theme');
      var darkPref = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      var curDark = act === 'dark' || (!act && darkPref);
      var nuevo = curDark ? 'light' : 'dark';
      ui.tema = nuevo;
      document.documentElement.setAttribute('data-theme', nuevo);
      savePref();
      render();
      return;
    }
    if(a === 'ir-registro'){ ui.vista = 'registro'; ui.error = ''; ui.draft = {}; render(); return; }
    if(a === 'ir-login'){ ui.vista = 'login'; ui.error = ''; render(); return; }
    if(a === 'salir'){ salir(); return; }
    if(a === 'editar-perfil'){ ui.editPerfil = true; ui.error = ''; render(); return; }
    if(a === 'cancelar-perfil'){ ui.editPerfil = false; ui.error = ''; render(); return; }
    if(a === 'rol'){
      if(!rolOk(v)) return;
      if(v === 'transportista' || v === 'elaborador'){
        var u = API.usuario();
        if(v === 'elaborador' && u.contratista_id && !esJefePuesto()){ ui.contrId = u.contratista_id; entrar('elaborador'); return; }
        ui.step = v; ui.rol = v; ui.camionId = null; ui.contrId = null; S = null; ui.cargando = true; render();
        API.llamar('GET', '/estado?rol=' + v).then(function(s){ S = s; ui.updAt = hm(S.ahora); }).catch(function(e){ if(e.offline) S = API.estadoCache(); else toast(errorTexto(e), true); }).finally(function(){ ui.cargando = false; render(); });
      } else entrar(v);
      return;
    }
    if(a === 'rol-back'){ ui.step = null; ui.rol = null; S = null; savePref(); render(); return; }
    if(a === 'rol-camion'){ ui.camionId = id; entrar('transportista'); return; }
    if(a === 'rol-contr'){ ui.contrId = id; entrar('elaborador'); return; }
    if(a === 'cambiar-rol'){ ui.rol = null; ui.step = null; ui.sheet = null; S = null; savePref(); window.scrollTo(0, 0); render(); return; }
    if(a === 'tab'){ ui.tab = v; window.scrollTo(0, 0); render(); if(v === 'analisis') cargarAnalisis(true); if(v === 'usuarios' && !ui.usuarios) cargarUsuarios(); return; }
    if(a === 'actualizar'){ cargarEstado(true); if(ui.rol === 'admin') cargarUsuarios(); enviarPendientes(); return; }
    if(a === 'ftipo'){ ui.ftipo = v; render(); return; }
    if(a === 'fcirc'){ ui.fcirc = v; render(); return; }
    if(a === 'fdia'){ ui.fdia = v; render(); return; }
    if(a === 'festado'){ ui.festado = v; render(); return; }
    if(a === 'acirc'){ ui.acirc = v; render(); cargarAnalisis(true); return; }
    if(a === 'avista'){ ui.avista = v; render(); return; }
    if(a === 'toggle-carga'){ ui.open[id] = !ui.open[id]; render(); return; }
    if(a === 'outbox'){ openSheet({ type: 'outbox' }); return; }
    if(a === 'falla-del'){ API.quitarFalla(id); render(); return; }
    if(soloLectura()){ toast('Vista de solo lectura', true); return; }
    var c = camion(cid());
    if(a === 'dispm'){ if(!dispAbierta()) return; accion('PUT', '/camiones/' + cid() + '/disponibilidad-manana', { valor: v }, { desc: 'disponibilidad', optimista: function(){ c.disp_manana = { valor: v, respondida_en: isoLocal() }; } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'entrar-fila'){ accion('POST', '/camiones/' + cid() + '/entrar-fila', null, { desc: 'entrar en fila', optimista: function(){ var g = progDe(c.id); c.estado = 'fila'; c.fila_desde = isoLocal(); c.fila_contratista_id = g ? g.contratista_id : null; } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'salir-fila'){ accion('POST', '/camiones/' + cid() + '/salir-fila', null, { desc: 'salir de fila', optimista: function(){ c.estado = 'disponible'; c.fila_desde = null; c.fila_contratista_id = null; } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'set-estado'){ accion('POST', '/camiones/' + cid() + '/estado', { estado: v }, { desc: 'aviso de descarga', optimista: function(){ c.estado = v; } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'inc'){ openSheet({ type: 'incidencia', tipo: v }); }
    else if(a === 'resolver-inc'){ var ci = camion(id || cid()); accion('POST', '/camiones/' + ci.id + '/incidencias/resolver', null, { desc: 'cerrar novedad', optimista: function(){ ci.inc = null; } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'alta-camion'){ openSheet({ type: 'camion', id: null, auto: true }); }
    else if(a === 'alta-reintentar'){ API.llamar('POST', '/camiones/' + id + '/reintentar-alta').then(function(){ ui.camionId = null; ui.step = 'transportista'; savePref(); return API.llamar('GET', '/estado?rol=transportista').then(function(s){ S = s; render(); }); }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'alta-ok'){ accion('POST', '/camiones/' + id + '/aprobar', null, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'alta-no'){ accion('POST', '/camiones/' + id + '/rechazar', null, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'nuevo-camion'){ openSheet({ type: 'camion', id: null }); }
    else if(a === 'editar-camion'){ openSheet({ type: 'camion', id: id }); }
    else if(a === 'baja-camion'){ openSheet({ type: 'baja', id: id }); }
    else if(a === 'new-pila'){ openSheet({ type: 'pila', id: null, contr: el.getAttribute('data-contr') || '' }); }
    else if(a === 'edit-pila'){ openSheet({ type: 'pila', id: id }); }
    else if(a === 'del-pila'){ if(!confirm('¿Quitar esta pila del relevamiento? Su volumen deja de contarse como stock disponible.')) return; var p = pila(id); accion('DELETE', '/pilas/' + id, null, { desc: 'quitar pila', optimista: function(){ S.pilas = pilas().filter(function(x){ return x.id !== id; }); } }).then(ok()).catch(fallo); }
    else if(a === 'reporte' || a === 'rep-pdf'){ toast('Generando el reporte…'); API.descargar('/reportes/stock.pdf', 'Stock-Pindo-' + S.hoy + '.pdf').then(function(){ toast('Reporte descargado'); }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'rep-fletes'){ toast('Generando el reporte…'); API.descargar('/camiones/' + cid() + '/reportes/fletes.pdf', 'Fletes-' + normPat(c.patente) + '-' + S.hoy + '.pdf').then(function(){ toast('Reporte descargado'); }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'programar'){ ui.draft = { sel: {}, hora: {}, open: {} }; if(id){ var c0 = contratistas()[0]; if(c0){ ui.draft.sel[id] = c0.id; ui.draft.open[c0.id] = true; } } openSheet({ type: 'programar', dia: id ? 'hoy' : ui.fdia }); }
    else if(a === 'quitar-prog'){ if(!confirm('¿Quitar este camión del programa?')) return; accion('DELETE', '/programa/items/' + id, null, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'emitir'){ openSheet({ type: 'emitir' }); }
    else if(a === 'prio'){ if(el.disabled) return; accion('PUT', '/programa/' + ui.fdia + '/prioridad/' + id, { prioridad: v }, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'solicitar'){ openSheet({ type: 'solic' }); }
    else if(a === 'quitar-solic'){ accion('DELETE', '/programa/manana/solicitud', null, { desc: 'quitar solicitud', optimista: function(){ if(S.solicitud && S.solicitud[S.manana]) delete S.solicitud[S.manana][S.contratista_id]; } }).then(ok()).catch(fallo); }
    else if(a === 'inicio-carga'){ openSheet({ type: 'inicio' }); }
    else if(a === 'quitar-inicio'){ accion('DELETE', '/programa/manana/inicio', null, { desc: 'quitar hora de inicio', optimista: function(){ if(S.inicio_carga && S.inicio_carga[S.manana]) delete S.inicio_carga[S.manana][S.contratista_id]; } }).then(ok()).catch(fallo); }
    else if(a === 'pedido-edit'){ var pd = pedidoDe(id); ui.draft = { cid: id, nota: pd ? (pd.nota || '') : '', lineas: pd ? pd.lineas.map(function(l){ return { tipo: l.tipo, largo_pies: l.largo_pies, m3: String(l.volumen_m3).replace('.', ',') }; }) : [{ tipo: 'grueso', largo_pies: 10, m3: '' }] }; openSheet({ type: 'pedido' }); }
    else if(a === 'quitar-pedido'){ accion('DELETE', '/pedidos/' + ui.draft.cid, null, { offline: false }).then(ok()).catch(fallo); }
    else if(a === 'add-linea'){ ui.draft.lineas.push({ tipo: 'fino', largo_pies: 8, m3: '' }); ui.error = ''; render(); }
    else if(a === 'del-linea'){ ui.draft.lineas.splice(parseInt(el.getAttribute('data-i'), 10), 1); ui.error = ''; render(); }
    else if(a === 'iniciar'){
      var g = prog(id), cg = g && camion(g.camion_id); if(!g || !cg || mecanico(cg)) return;
      var kid = uid(), ahoraIso = isoLocal();
      accion('POST', '/cargas', { id: kid, programa_item_id: g.id }, { desc: 'iniciar carga', optimista: function(){ var esp = cg.estado === 'fila' && cg.fila_desde ? lleva(cg.fila_desde) : null; g.estado = 'cargando'; cg.estado = 'cargando'; S.cargas.push({ id: kid, camion_id: cg.id, contratista_id: g.contratista_id, programa_id: g.id, estado: 'en_curso', jornada: S.hoy, fila_desde: cg.fila_desde, espera_min: esp, inicio_en: ahoraIso, lineas: [] }); cg.fila_desde = null; cg.fila_contratista_id = null; } }).catch(function(e){ toast(errorTexto(e), true); });
    }
    else if(a === 'finalizar'){ var k = carga(id), r0 = rodalesDe(k.contratista_id)[0]; ui.draft = { circuito: '', destino_id: '', rodal_id: r0 ? r0.id : '', lineas: [{ tipo: 'grueso', largo_pies: 10, m3: '' }] }; openSheet({ type: 'finalizar', id: id }); }
    else if(a === 'bas-salida'){ var m = (S.movimientos || []).filter(function(x){ return x.id === id; })[0]; accion('POST', '/bascula/ingresos/' + id + '/salida', null, { desc: 'salida de báscula', optimista: function(){ if(m){ m.salida_en = isoLocal(); var cm = camion(m.camion_id); if(cm && cm.estado === 'ruta') cm.estado = 'disponible'; } } }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'bas-hor-add'){ openSheet({ type: 'bashor', kind: v }); }
    else if(a === 'bas-hor-del'){ if(!confirm('¿Quitar este horario?')) return; var kk = el.getAttribute('data-k'); accion('DELETE', '/bascula/' + (kk === 'turno' ? 'turnos' : 'descansos') + '/' + id, null, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
    else if(a === 'rodal-new'){ openSheet({ type: 'rodal' }); }
    else if(a === 'rodal-baja'){ openSheet({ type: 'rodalbaja', rodal: id }); }
    else if(a === 'rodal-del'){ accion('DELETE', '/rodales/' + ui.sheet.rodal, null, { offline: false }).then(ok()).catch(fallo); }
    else if(a === 'tarifa-new'){ openSheet({ type: 'tarifa', rodal: id, lid: null }); }
    else if(a === 'tarifa-edit'){ openSheet({ type: 'tarifa', lid: id }); }
    else if(a === 'tarifa-del'){ var tl = tarifas().filter(function(t){ return t.id === ui.sheet.lid; })[0]; accion('DELETE', '/rodales/' + tl.rodal_id + '/tarifas/' + tl.destino_id, null, { offline: false }).then(ok()).catch(fallo); }
    else if(a === 'importar'){ ui.draft = {}; openSheet({ type: 'importar' }); }
    else if(a === 'importar-ok'){ var fd2 = new FormData(); fd2.append('archivo', ui.draft.archivo); ui.cargando = true; render(); API.llamar('POST', '/tarifas/importar?modo=confirmar', fd2).then(function(r){ ui.cargando = false; closeSheet(); toast('Se importaron ' + r.aplicadas + ' tarifas'); cargarEstado(false); }).catch(function(e){ ui.cargando = false; fallo(e); }); }
    else if(a === 'remito-manual'){ ui.draft = prefillRemitoDraft({ estado: 'manual' }); openSheet({ type: 'remito' }); }
    else if(a === 'remito-ver'){ openSheet({ type: 'remitover', rid: id }); }
    else if(a === 'remito-edit'){
      var re = remitoAny(id);
      if(re){
        ui.draft = { estado: 'manual', foto: re.foto_url || null, numero: re.numero || '', fecha: re.fecha || S.hoy, rodal_id: re.rodal_id || '', destino_id: re.destino_id || '', carga_id: re.carga_id || null, toneladas: re.toneladas != null ? re.toneladas : '' };
        openSheet({ type: 'remito', editId: re.id });
      }
    }
    else if(a === 'remito-del'){ if(!confirm('¿Eliminar este remito? Se descuenta de la facturación y no se puede deshacer.')) return; accion('DELETE', '/remitos/' + id, null, { desc: 'eliminar remito', optimista: function(){ S.remitos = remitos().filter(function(x){ return x.id !== id; }); if(S.remitos_control) S.remitos_control = S.remitos_control.filter(function(x){ return x.id !== id; }); } }).then(ok()).catch(fallo); }
    else if(a === 'usuario-edit'){ var uu = (ui.usuarios || []).filter(function(x){ return x.id === id; })[0]; if(uu){ ui.draft = { u: uu }; openSheet({ type: 'usuario' }); } }
    else if(a === 'cat-new'){ openSheet({ type: 'catalogo', tipo: v }); }
    else if(a === 'cat-del'){ if(!confirm('¿Quitar este elemento del catálogo?')) return; accion('DELETE', '/catalogos/' + v + '/' + id, null, { offline: false }).catch(function(e){ toast(errorTexto(e), true); }); }
  });

  // ---------- inputs ----------
  document.addEventListener('input', function(e){
    var t = e.target, f = t.getAttribute && t.getAttribute('data-f'); if(!ui.draft || !f) return;
    if(f === 'm3'){ ui.draft.lineas[parseInt(t.getAttribute('data-i'), 10)].m3 = t.value; var tot = sum(ui.draft.lineas, function(l){ var n = numSimple(l.m3); return isFinite(n) ? n : 0; }), el = document.getElementById('tot'); if(el) el.textContent = f1(tot); }
    else if(f === 'pnota') ui.draft.nota = t.value;
    else if(f === 'proghora') ui.draft.hora[t.getAttribute('data-ci')] = t.value;
    else if(f === 'rtn'){ ui.draft.toneladas = t.value; refrescarImporte(); }
  });
  function refrescarImporte(){ var ri = document.getElementById('rimp'); if(ri && ui.draft) ri.innerHTML = remitoImporteTxt(ui.draft); }
  document.addEventListener('change', function(e){
    var t = e.target;
    if(t.id === 'rem-file'){ var fl0 = t.files && t.files[0]; t.value = ''; if(fl0) procesarRemito(fl0); return; }
    var f = t.getAttribute && t.getAttribute('data-f'); if(!ui.draft || !f) return;
    if(f === 'ltipo'){ ui.draft.lineas[parseInt(t.getAttribute('data-i'), 10)].tipo = t.value; ui.error = ''; render(); }
    else if(f === 'llargo'){ ui.draft.lineas[parseInt(t.getAttribute('data-i'), 10)].largo_pies = parseInt(t.value, 10); ui.error = ''; render(); }
    else if(f === 'progcam'){ var pid = t.getAttribute('data-id'); if(t.checked) ui.draft.sel[pid] = t.getAttribute('data-ci'); else delete ui.draft.sel[pid]; ui.error = ''; actualizarProg(); }
    else if(f === 'proghora') ui.draft.hora[t.getAttribute('data-ci')] = t.value;
    else if(f === 'destino'){ ui.draft.destino_id = t.value; refrescarImporte(); }
    else if(f === 'rodal'){ ui.draft.rodal_id = t.value; refrescarImporte(); }
    else if(f === 'circuito'){ ui.draft.circuito = t.value; var d0 = destinos(t.value)[0]; ui.draft.destino_id = d0 ? d0.id : ''; ui.error = ''; render(); }
  });
  document.addEventListener('toggle', function(e){ var t = e.target; if(ui.draft && ui.draft.open && t.classList && t.classList.contains('acc')) ui.draft.open[t.getAttribute('data-ci')] = t.open; }, true);
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape' && ui.sheet) closeSheet(); });

  // ---------- formularios ----------
  document.addEventListener('submit', function(e){
    e.preventDefault();
    var form = e.target, kind = form.getAttribute('data-form'), fd = new FormData(form), g = function(k){ return String(fd.get(k) == null ? '' : fd.get(k)).trim(); };
    // Anti doble envío: el formulario queda bloqueado hasta el próximo render (éxito, error o validación lo redibujan).
    if(form.getAttribute('data-busy')) return;
    form.setAttribute('data-busy', '1'); var sb = form.querySelector('button[type=submit]'); if(sb) sb.disabled = true;
    if(kind === 'login'){
      ui.cargando = true; ui.error = ''; render();
      API.login(g('usuario').toLowerCase(), g('password')).then(function(){ ui.cargando = false; ui.rol = null; ui.step = null; S = null; render(); }).catch(function(e){ ui.cargando = false; ui.error = e.offline ? 'Sin conexión. Para ingresar por primera vez hace falta señal.' : errorTexto(e); render(); });
      return;
    }
    if(kind === 'registro'){
      ui.draft = { usuario: g('usuario'), nombre: g('nombre'), empresa: g('empresa'), tipo_empresa: g('tipo_empresa'), puesto: g('puesto') };
      if(ui.draft.nombre.split(/\s+/).length < 2){ ui.error = 'Ingresá nombre y apellido.'; render(); return; }
      if(!ui.draft.empresa){ ui.error = 'Indicá la empresa a la que pertenecés.'; render(); return; }
      if(!ui.draft.tipo_empresa){ ui.error = 'Indicá si tu empresa es de transporte, elaborador o Pindó SA.'; render(); return; }
      if(!ui.draft.puesto){ ui.error = 'Elegí tu puesto.'; render(); return; }
      if(g('password').length < 8){ ui.error = 'La contraseña debe tener al menos 8 caracteres.'; render(); return; }
      ui.cargando = true; ui.error = ''; render();
      API.llamar('POST', '/auth/registro', Object.assign({}, ui.draft, { usuario: ui.draft.usuario.toLowerCase(), password: g('password') })).then(function(r){ ui.cargando = false; ui.vista = 'login'; ui.draft = null; toast(r.mensaje); }).catch(function(e){ ui.cargando = false; ui.error = errorTexto(e); render(); });
      return;
    }
    if(kind === 'perfil'){
      API.llamar('PUT', '/me', { nombre: g('nombre'), empresa: g('empresa'), puesto: g('puesto') }).then(function(u){ var s = API.sesion(); s.usuario = u; try{ localStorage.setItem('lf.sesion', JSON.stringify(s)); }catch(x){} ui.editPerfil = false; render(); }).catch(fallo);
      return;
    }
    if(soloLectura()) return;
    if(kind === 'pila'){
      var m3 = numSimple(g('volumen_m3')), pid = ui.sheet.id || uid(), contr = ui.rol === 'supervisor' ? g('contratista_id') : S.contratista_id;
      if(!contr){ ui.error = 'Elegí el contratista.'; render(); return; }
      if(!isFinite(m3) || m3 <= 0){ ui.error = 'Ingresá un volumen mayor que cero.'; render(); return; }
      if(!g('relevado_por')){ ui.error = 'Indicá quién relevó la pila.'; render(); return; }
      var body = { id: pid, contratista_id: contr, especie_id: g('especie_id'), tipo: g('tipo'), largo_pies: parseInt(g('largo_pies'), 10), volumen_m3: Math.round(m3 * 10) / 10, uso: g('uso'), relevado_por: g('relevado_por'), hora: g('hora') };
      accion('POST', '/pilas', body, { desc: 'relevamiento', optimista: function(){ var ex = pila(pid), esp = especies().filter(function(x){ return x.id === body.especie_id; })[0]; var nv = Object.assign(ex || { id: pid, contratista_id: contr }, body, { especie: esp ? esp.nombre : '', relevado_en: S.hoy + 'T' + (body.hora || hhmm()) + ':00' }); if(!ex) S.pilas.push(nv); } }).then(ok()).catch(fallo);
    }
    else if(kind === 'programar'){
      var dp = ui.draft, ids = Object.keys(dp.sel), items = [];
      if(!ids.length){ ui.error = 'Tildá al menos un camión.'; render(); return; }
      ids.forEach(function(id){ var ci = dp.sel[id]; items.push({ camion_id: id, contratista_id: ci, hora: dp.hora[ci] || hhmm() }); });
      accion('POST', '/programa/' + ui.sheet.dia + '/items', { items: items }, { offline: false }).then(ok()).catch(fallo);
    }
    else if(kind === 'emitir'){ accion('POST', '/programa/manana/emitir', null, { offline: false }).then(ok(function(){ ui.fdia = 'manana'; toast('Programa emitido'); })).catch(fallo); }
    else if(kind === 'camion'){
      var cap = numSimple(g('capacidad_tn'));
      if(!g('patente')){ ui.error = 'Ingresá la patente.'; render(); return; }
      if(!g('chofer') || !g('empresa')){ ui.error = 'Completá el chofer y la empresa de transporte.'; render(); return; }
      if(!isFinite(cap) || cap <= 0){ ui.error = 'Ingresá la capacidad en toneladas.'; render(); return; }
      var bc = { patente: g('patente').toUpperCase(), chofer: g('chofer'), telefono: g('telefono'), empresa: g('empresa'), capacidad_tn: cap, traccion: g('traccion') || '6x4' };
      if(ui.sheet.id) accion('PUT', '/camiones/' + ui.sheet.id, bc, { offline: false }).then(ok()).catch(fallo);
      else { var nid = uid(); bc.id = nid; API.llamar('POST', '/camiones', bc).then(function(){ var auto = ui.sheet.auto; ui.sheet = null; ui.draft = null; ui.error = ''; if(auto){ ui.camionId = nid; entrar('transportista'); } else cargarEstado(false); }).catch(fallo); }
    }
    else if(kind === 'baja'){ accion('DELETE', '/camiones/' + ui.sheet.id, null, { offline: false }).then(ok()).catch(fallo); }
    else if(kind === 'incidencia'){
      var mn = parseInt(g('minutos'), 10), iid = uid(), tipoI = ui.sheet.tipo, bi = { id: iid, tipo: tipoI, motivo: g('motivo'), detalle: g('detalle'), minutos: tipoI === 'demora' && isFinite(mn) && mn > 0 ? mn : null };
      accion('POST', '/camiones/' + cid() + '/incidencias', bi, { desc: 'novedad', optimista: function(){ var cc = camion(cid()); cc.inc = Object.assign({ id: iid, desde: isoLocal() }, bi); if(tipoI === 'mecanico' && cc.estado === 'fila'){ cc.estado = 'disponible'; cc.fila_desde = null; } } }).then(ok()).catch(fallo);
    }
    else if(kind === 'solic'){
      var ns = parseInt(g('n'), 10);
      if(!isFinite(ns) || ns < 1 || ns > 99){ ui.error = 'Ingresá un número de camiones entre 1 y 99.'; render(); return; }
      accion('PUT', '/programa/manana/solicitud', { cantidad_minima: ns, nota: g('nota') }, { desc: 'solicitud de unidades', optimista: function(){ S.solicitud = S.solicitud || {}; S.solicitud[S.manana] = S.solicitud[S.manana] || {}; S.solicitud[S.manana][S.contratista_id] = { cantidad_minima: ns, nota: g('nota'), solicitada_por: API.usuario().nombre, solicitada_en: isoLocal() }; } }).then(ok()).catch(fallo);
    }
    else if(kind === 'inicio'){
      var hi = g('hora');
      if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(hi)){ ui.error = 'Ingresá una hora válida.'; render(); return; }
      accion('PUT', '/programa/manana/inicio', { hora: hi }, { desc: 'hora de inicio', optimista: function(){ S.inicio_carga = S.inicio_carga || {}; S.inicio_carga[S.manana] = S.inicio_carga[S.manana] || {}; S.inicio_carga[S.manana][S.contratista_id] = { hora: hi, marcado_por: API.usuario().nombre, marcado_en: isoLocal() }; } }).then(ok()).catch(fallo);
    }
    else if(kind === 'pedido'){
      var dpe = ui.draft, ls = [];
      for(var q2 = 0; q2 < dpe.lineas.length; q2++){ var nn = numSimple(dpe.lineas[q2].m3); if(!isFinite(nn) || nn <= 0){ ui.error = 'Revisá la línea ' + (q2 + 1) + ': ingresá un volumen mayor a cero.'; render(); return; } ls.push({ tipo: dpe.lineas[q2].tipo, largo_pies: dpe.lineas[q2].largo_pies, volumen_m3: Math.round(nn * 10) / 10 }); }
      accion('PUT', '/pedidos/' + dpe.cid, { lineas: ls, nota: dpe.nota }, { offline: false }).then(ok()).catch(fallo);
    }
    else if(kind === 'finalizar'){
      var d = ui.draft, k = carga(ui.sheet.id), need = {}, lineas = [];
      if(!d.circuito){ ui.error = 'Indicá si el despacho es para industria propia o ventas.'; render(); return; }
      for(var i = 0; i < d.lineas.length; i++){
        var l = d.lineas[i], n = numSimple(l.m3), key = l.tipo + '|' + l.largo_pies;
        if(!isFinite(n) || n <= 0){ ui.error = 'Revisá la carga ' + (i + 1) + ': ingresá un volumen mayor a cero.'; render(); return; }
        need[key] = (need[key] || 0) + n;
        var av = stockDe(k.contratista_id, l.tipo, l.largo_pies, d.circuito);
        if(need[key] > av + 0.0001){ ui.error = 'Solo hay ' + f1(av) + ' m³ de ' + tipoLabel(l.tipo).toLowerCase() + ' de ' + fl(l.largo_pies) + ' relevados.' + (d.circuito === 'industria' ? ' Las pilas de ventas no se usan para industria.' : ''); render(); return; }
        lineas.push({ tipo: l.tipo, largo_pies: l.largo_pies, volumen_m3: Math.round(n * 10) / 10 });
      }
      if(!d.destino_id){ ui.error = 'Elegí el destino.'; render(); return; }
      var bf = { circuito: d.circuito, rodal_id: d.rodal_id || null, destino_id: d.destino_id, lineas: lineas };
      accion('POST', '/cargas/' + k.id + '/finalizar', bf, { desc: 'finalizar carga', optimista: function(){
        lineas.forEach(function(x){ var rest = x.volumen_m3; pilas().filter(function(p){ return p.contratista_id === k.contratista_id && p.tipo === x.tipo && p.largo_pies === x.largo_pies && p.volumen_m3 > 0 && !(d.circuito === 'industria' && esVentas(p)); }).sort(function(a, b){ return d.circuito === 'ventas' ? (esVentas(b) ? 1 : 0) - (esVentas(a) ? 1 : 0) : (esVentas(a) ? 1 : 0) - (esVentas(b) ? 1 : 0); }).forEach(function(p){ var take = Math.min(p.volumen_m3, rest); p.volumen_m3 = Math.round((p.volumen_m3 - take) * 10) / 10; rest = Math.round((rest - take) * 10) / 10; }); });
        var ds = destino(d.destino_id), rd = rodal(d.rodal_id); k.estado = 'finalizada'; k.circuito = d.circuito; k.destino_id = d.destino_id; k.destino = ds ? ds.nombre : ''; k.rodal_id = d.rodal_id; k.rodal = rd ? rd.codigo : ''; k.lineas = lineas; k.fin_en = isoLocal(); k.jornada = S.hoy;
        var ck = camion(k.camion_id); if(ck) ck.estado = 'ruta'; var gg = k.programa_id && prog(k.programa_id); if(gg) gg.estado = 'cumplido'; ui.open[k.id] = true;
      } }).then(ok()).catch(function(e){ if(e.codigo === 'stock_insuficiente') ui.error = e.mensaje + '. Corregí los volúmenes y volvé a confirmar.'; else ui.error = errorTexto(e); render(); });
    }
    else if(kind === 'basing'){
      var camId = g('camion_id'); ui.basPat = camId;
      if(!camId){ ui.basErr = 'Elegí el camión que ingresa.'; render(); return; }
      var mid = uid();
      accion('POST', '/bascula/ingresos', { id: mid, camion_id: camId }, { desc: 'ingreso a báscula', optimista: function(){ var kk = enCamino().filter(function(x){ return x.camion_id === camId; })[0]; S.movimientos = S.movimientos || []; S.movimientos.push({ id: mid, carga_id: kk ? kk.id : null, camion_id: camId, jornada: S.hoy, ingreso_en: isoLocal(), salida_en: null }); if(kk) kk.ingreso_en = isoLocal(); } }).then(function(){ ui.basErr = ''; ui.basPat = ''; render(); }).catch(function(e){ ui.basErr = errorTexto(e); render(); });
    }
    else if(kind === 'bashor'){
      var des = ui.sheet.kind === 'descanso';
      accion('POST', '/bascula/' + (des ? 'descansos' : 'turnos'), { desde: g('desde'), hasta: g('hasta'), motivo: des ? g('motivo') : null }, { offline: false }).then(ok()).catch(fallo);
    }
    else if(kind === 'rodal'){ accion('POST', '/rodales', { codigo: g('codigo'), contratista_id: g('contratista_id') }, { offline: false }).then(ok()).catch(fallo); }
    else if(kind === 'tarifa'){
      var lin = ui.sheet.lid ? tarifas().filter(function(t){ return t.id === ui.sheet.lid; })[0] : null, rid = lin ? lin.rodal_id : ui.sheet.rodal, did = lin ? lin.destino_id : g('destino_id');
      var ka = numSimple(g('km_asfalto')), kt = numSimple(g('km_tierra')), a42 = numSimple(g('tarifa_4x2')), a64 = numSimple(g('tarifa_6x4'));
      if(!isFinite(ka) || ka < 0 || !isFinite(kt) || kt < 0){ ui.error = 'Ingresá los km de asfalto y de tierra (0 si no hay).'; render(); return; }
      if(!(a42 > 0) && !(a64 > 0)){ ui.error = 'Cargá al menos una tarifa (4x2 o 6x4) mayor a cero.'; render(); return; }
      accion('PUT', '/rodales/' + rid + '/tarifas/' + did, { km_asfalto: ka, km_tierra: kt, tarifa_4x2: a42 > 0 ? Math.round(a42) : 0, tarifa_6x4: a64 > 0 ? Math.round(a64) : 0 }, { offline: false }).then(ok()).catch(fallo);
    }
    else if(kind === 'importar'){
      var fi = form.querySelector('input[type=file]'), file = fi && fi.files && fi.files[0];
      if(!file){ ui.error = 'Elegí un archivo .xlsx o .csv.'; render(); return; }
      var fdi = new FormData(); fdi.append('archivo', file); ui.cargando = true; ui.error = ''; render();
      API.llamar('POST', '/tarifas/importar?modo=previsualizar', fdi).then(function(r){ ui.cargando = false; ui.draft = { archivo: file, res: r }; render(); }).catch(function(e){ ui.cargando = false; fallo(e); });
    }
    else if(kind === 'remito'){
      var tn = numSimple(g('toneladas')), rr = g('rodal_id'), editId = ui.sheet && ui.sheet.editId;
      if(!rr){ ui.error = 'Elegí el rodal (punto de carga) del remito.'; render(); return; }
      if(!isFinite(tn) || tn <= 0){ ui.error = 'Ingresá las toneladas del remito.'; render(); return; }
      var dr = ui.draft || {}, rid2 = editId || uid(), tnRound = Math.round(tn * 10) / 10;
      if(g('numero') && remitos().some(function(x){ return x.numero === g('numero') && x.id !== editId; })){ ui.error = 'Ya cargaste un remito con el número ' + g('numero') + '.'; render(); return; }
      if(editId){
        var bEdit = { numero: g('numero') || null, fecha: g('fecha') || S.hoy, rodal_id: rr, destino_id: g('destino_id') || null, carga_id: dr.carga_id || null, toneladas: tnRound };
        accion('PUT', '/remitos/' + editId, bEdit, { desc: 'editar remito', optimista: function(){
          var ex = remitoAny(editId);
          if(ex){
            var rdE = rodal(rr), dsE = destino(bEdit.destino_id), tE = tarifaLin(rr, bEdit.destino_id), ctE = camion(ex.camion_id || cid()), unitE = tE ? (tipoCam(ctE) === '4x2' ? tE.tarifa_4x2 : tE.tarifa_6x4) : null;
            Object.assign(ex, bEdit, { rodal: rdE ? rdE.codigo : ex.rodal, destino: dsE ? dsE.nombre : null, tarifa_aplicada: unitE || null, importe: unitE ? Math.round(unitE * tnRound) : null });
          }
        } }).then(ok()).catch(fallo);
        return;
      }
      var br = { id: rid2, camion_id: cid(), borrador_id: dr.borrador_id || null, carga_id: dr.carga_id || null, numero: g('numero') || null, fecha: g('fecha') || S.hoy, rodal_id: rr, destino_id: g('destino_id') || null, toneladas: tnRound };
      var optim = function(){ var rd = rodal(rr), ds = destino(br.destino_id), t = tarifaLin(rr, br.destino_id), ct = camion(cid()), unit = t ? (tipoCam(ct) === '4x2' ? t.tarifa_4x2 : t.tarifa_6x4) : null, imp = unit ? Math.round(unit * br.toneladas) : null; S.remitos.unshift({ id: rid2, camion_id: cid(), carga_id: br.carga_id, numero: br.numero, fecha: br.fecha, rodal_id: rr, rodal: rd ? rd.codigo : '', destino_id: br.destino_id, destino: ds ? ds.nombre : '', toneladas: br.toneladas, tarifa_aplicada: unit || null, importe: imp || null, cargado_por: API.usuario().nombre, cargado_en: isoLocal(), foto: !!dr.foto }); };
      if(!navigator.onLine && dr.foto && !dr.borrador_id){ API.encolar({ metodo: 'POST', ruta: '/remitos', body: br, foto: dr.foto, desc: 'remito con foto' }); optim(); API.guardarEstado(S); toast('Sin conexión: el remito y su foto quedan pendientes de enviar'); closeSheet(); return; }
      accion('POST', '/remitos', br, { desc: 'remito', optimista: optim }).then(ok()).catch(fallo);
    }
    else if(kind === 'usuario'){
      var roles = fd.getAll('roles').map(String), uid2 = ui.draft.u.id, bu = { roles: roles, contratista_id: g('contratista_id') || '', activo: !!fd.get('activo') };
      if(g('password')) bu.password = g('password');
      API.llamar('PUT', '/usuarios/' + uid2, bu).then(function(){ closeSheet(); cargarUsuarios(); }).catch(fallo);
    }
    else if(kind === 'catalogo'){
      var tp = ui.sheet.tipo, bc2 = tp === 'largos' ? { pies: parseInt(g('pies'), 10) } : tp === 'destinos' ? { nombre: g('nombre'), circuito: g('circuito') } : { nombre: g('nombre') };
      accion('POST', '/catalogos/' + tp, bc2, { offline: false }).then(ok()).catch(fallo);
    }
  });

  // ---------- conexión, refresco y arranque ----------
  window.addEventListener('offline', function(){ ui.off = true; render(); });
  window.addEventListener('online', function(){ ui.off = false; render(); enviarPendientes(); if(!API.pendientes()) cargarEstado(false); });
  setInterval(function(){ if(!document.hidden && API.sesion() && ui.rol && !ui.sheet && !ui.draft && navigator.onLine){ enviarPendientes(); cargarEstado(false); } }, 30000);
  document.addEventListener('visibilitychange', function(){ if(!document.hidden && API.sesion() && ui.rol && !ui.sheet && navigator.onLine){ enviarPendientes(); cargarEstado(false); } });
  if('serviceWorker' in navigator){ navigator.serviceWorker.register('/sw.js').catch(function(){}); }

  if(API.sesion()){
    if(ui.rol === 'transportista' && !ui.camionId) ui.rol = null;
    if(ui.rol === 'elaborador' && !ui.contrId && !(API.usuario() && API.usuario().contratista_id)) ui.rol = null;
    if(ui.rol === 'elaborador' && !ui.contrId) ui.contrId = API.usuario().contratista_id;
    if(ui.rol) ui.tab = defaultTab(ui.rol);
    if(ui.rol === 'supervisor') ui.fdia = 'manana';
  } else ui.vista = 'login';
  render();
  if(API.sesion() && ui.rol){ cargarEstado(false).then(function(){ if(ui.rol === 'admin') cargarUsuarios(); }); enviarPendientes(); }
})();
