/* Hojas inferiores (formularios). Cada una devuelve el HTML interior; app.js procesa el submit. */

function fieldNum(id, nombre, label, val, ph, df){ return '<div class="field"><label for="' + id + '">' + label + '</label><input class="input mono" id="' + id + '" name="' + nombre + '"' + (df ? ' data-f="' + df + '"' : '') + ' inputmode="decimal" autocomplete="off" value="' + esc(val) + '" placeholder="' + esc(ph || '') + '"></div>'; }

function sheetPila(){
  var p = ui.sheet.id ? pila(ui.sheet.id) : null, el = ui.rol === 'elaborador', sup = ui.rol === 'supervisor';
  var v = p || { contratista_id: el ? S.contratista_id : (ui.sheet.contr || ''), uso: 'pindo', especie_id: (especies()[0] || {}).id, tipo: 'grueso', largo_pies: 10, volumen_m3: '' };
  return '<h2>' + (p ? 'Actualizar pila' : 'Relevar pila') + '</h2><p class="hint">' + (p ? 'Cargá el stock medido hoy. Reemplaza el valor anterior.' : 'Stock pendiente de carga que dejó el contratista de elaboración.') + '</p><form data-form="pila" novalidate>' +
    '<div class="field"><label for="f-contr">Contratista</label>' + (sup ? '<select class="input" id="f-contr" name="contratista_id"><option value="">Elegí el contratista</option>' + contratistas().map(function(c){ return '<option value="' + c.id + '"' + (c.id === v.contratista_id ? ' selected' : '') + '>' + esc(c.nombre) + '</option>'; }).join('') + '</select>' : '<input class="input" id="f-contr" value="' + esc(contrNombre(v.contratista_id)) + '" readonly>') + '</div>' +
    '<div class="field"><span class="lb" id="lb-uso">Stock</span><div class="seg" role="radiogroup" aria-labelledby="lb-uso">' + [['pindo', 'Stock Pindó SA'], ['ventas', 'Stock de ventas']].map(function(u){ return '<label><input type="radio" name="uso" value="' + u[0] + '"' + (v.uso === u[0] ? ' checked' : '') + '>' + u[1] + '</label>'; }).join('') + '</div></div>' +
    '<div class="field"><label for="f-esp">Especie</label><select class="input" id="f-esp" name="especie_id">' + especies().map(function(e){ return '<option value="' + e.id + '"' + (e.id === v.especie_id ? ' selected' : '') + '>' + esc(e.nombre) + '</option>'; }).join('') + '</select></div>' +
    '<div class="field"><span class="lb" id="lb-tipo">Clasificación</span><div class="seg" role="radiogroup" aria-labelledby="lb-tipo">' + ['fino', 'grueso'].map(function(t){ return '<label><input type="radio" name="tipo" value="' + t + '"' + (v.tipo === t ? ' checked' : '') + '><i class="dot ' + t + '"></i>' + tipoLabel(t) + '</label>'; }).join('') + '</div></div>' +
    '<div class="two"><div class="field"><label for="f-largo">Largo</label><select class="input mono" id="f-largo" name="largo_pies">' + largos().map(function(l){ return '<option value="' + l + '"' + (l === v.largo_pies ? ' selected' : '') + '>' + fl(l) + '</option>'; }).join('') + '</select></div>' +
    fieldNum('f-m3', 'volumen_m3', 'Volumen (m³)', v.volumen_m3 === '' ? '' : String(v.volumen_m3).replace('.', ','), '0,0') + '</div>' +
    '<div class="two"><div class="field"><label for="f-por">Relevó</label><input class="input" id="f-por" name="relevado_por" autocomplete="off" value="' + esc(p ? p.relevado_por : API.usuario().nombre) + '"></div><div class="field"><label for="f-hora">Hora</label><input class="input mono" id="f-hora" name="hora" type="time" value="' + (p ? hm(p.relevado_en) : hhmm()) + '"></div></div>' +
    '<p class="note" style="margin:-4px 0 12px">Cierre del relevamiento: ' + S.cierres.relevamiento + ' hs. Después de esa hora el servidor no acepta cambios.</p>' + errHtml() +
    '<button class="btn primary block" type="submit">Guardar relevamiento</button>' + (p ? '<button type="button" class="btn warn block" data-action="del-pila" data-id="' + p.id + '" style="margin-top:8px">Quitar esta pila</button>' : '') + '</form>';
}

function progConteo(d){ var n = {}; Object.keys(d.sel).forEach(function(id){ n[d.sel[id]] = (n[d.sel[id]] || 0) + 1; }); return n; }
function sheetProgramar(){
  var s = ui.sheet, d = ui.draft, dd = s.dia || ui.fdia, libres = activos().filter(function(c){ return !progDe(c.id, dd); });
  if(!libres.length) return '<h2>Programar carga</h2>' + vacio(activos().length ? 'Todos los camiones ya tienen una carga programada.' : 'Todavía no hay camiones dados de alta. Agregalos desde la pestaña Camiones.');
  var n = progConteo(d), tot = Object.keys(d.sel).length;
  return '<h2>Programar carga</h2><p class="hint">Abrí cada contratista, tildá los camiones asignados y fijá la hora de carga · ' + (dd === 'manana' ? tomorrow() : 'hoy') + '.</p><form data-form="programar" novalidate>' +
    contratistas().map(function(ct){ var cid = ct.id, k = n[cid] || 0;
      return '<details class="acc" data-ci="' + cid + '"' + (d.open[cid] ? ' open' : '') + '><summary><span>' + esc(ct.nombre) + '</span><span class="acc-n' + (k ? ' on' : '') + '" id="pc-n-' + cid + '">' + (k ? k + (k === 1 ? ' camión' : ' camiones') : 'Sin asignar') + '</span></summary><div class="acc-b"><div class="field" style="margin-bottom:6px"><label for="ph-' + cid + '">Hora de carga</label><input class="input mono" id="ph-' + cid + '" type="time" data-f="proghora" data-ci="' + cid + '" value="' + esc(d.hora[cid] || hhmm()) + '"></div>' +
        libres.map(function(t){ var nd = dd === 'manana' && t.disp_manana && t.disp_manana.valor === 'no', bloq = (mecanico(t) && dd === 'hoy') || nd; return '<label class="chk"><input type="checkbox" data-f="progcam" data-id="' + t.id + '" data-ci="' + cid + '"' + (d.sel[t.id] === cid ? ' checked' : '') + (bloq ? ' disabled' : '') + '><span><b>' + esc(t.patente) + '</b> · ' + esc(t.chofer) + (nd ? ' · no disponible' : mecanico(t) && dd === 'hoy' ? ' · con falla mecánica' : dd === 'manana' ? (t.disp_manana ? ' · confirmó disponible' : ' · sin respuesta') : '') + '</span></label>'; }).join('') + '</div></details>'; }).join('') +
    errHtml() + '<button class="btn primary block" type="submit" id="prog-ok">' + (tot ? 'Agregar ' + tot + (tot === 1 ? ' camión' : ' camiones') + ' al programa' : 'Agregar al programa') + '</button></form>';
}
function actualizarProg(){
  var d = ui.draft, n = progConteo(d), tot = 0;
  contratistas().forEach(function(c){ var el = document.getElementById('pc-n-' + c.id), k = n[c.id] || 0; tot += k; if(el){ el.textContent = k ? k + (k === 1 ? ' camión' : ' camiones') : 'Sin asignar'; el.className = k ? 'acc-n on' : 'acc-n'; } });
  Array.prototype.forEach.call(document.querySelectorAll('input[data-f="progcam"]'), function(x){ x.checked = d.sel[x.getAttribute('data-id')] === x.getAttribute('data-ci'); });
  var bt = document.getElementById('prog-ok'); if(bt) bt.textContent = tot ? 'Agregar ' + tot + (tot === 1 ? ' camión' : ' camiones') + ' al programa' : 'Agregar al programa';
}

function sheetIncidencia(){
  var t = ui.sheet.tipo, mec = t === 'mecanico';
  return '<h2>' + (mec ? 'Problema mecánico' : 'Demora') + '</h2><p class="hint">' + (mec ? 'El camión no va a poder cargar hasta que cierres la novedad.' : 'Avisá el motivo para que el supervisor y el elaborador reprogramen.') + '</p><form data-form="incidencia" novalidate>' +
    '<div class="field"><label for="f-mot">Motivo</label><select class="input" id="f-mot" name="motivo">' + MOTIVOS[t].map(function(m){ return '<option>' + m + '</option>'; }).join('') + '</select></div><div class="field"><label for="f-det">Detalle (opcional)</label><input class="input" id="f-det" name="detalle" autocomplete="off" placeholder="Qué pasó"></div>' +
    (mec ? '' : '<div class="field"><label for="f-min">Demora estimada (minutos)</label><input class="input mono" id="f-min" name="minutos" inputmode="numeric" autocomplete="off" placeholder="30"></div>') + errHtml() + '<button class="btn primary block" type="submit">' + (mec ? 'Avisar problema mecánico' : 'Avisar demora') + '</button></form>';
}

function sheetEmitir(){
  var issues = [], total = programa().filter(function(g){ return g.jornada === S.manana && g.estado === 'programado'; }).length;
  if(!relCerrado()) issues.push('Todavía no cerró el relevamiento de stock (' + S.cierres.relevamiento + ' hs). ' + cierreTexto());
  contratistas().forEach(function(c){ var r = relEstado(c.id); if(r.k === 'pendiente') issues.push(c.nombre + ': sin relevamiento de stock.'); else if(r.k === 'tarde') issues.push(c.nombre + ': relevó fuera de horario (' + r.hora + ' hs).'); else if(r.k === 'viejo') issues.push(c.nombre + ': el último relevamiento no es de hoy.'); });
  programa().filter(function(g){ return g.jornada === S.manana && g.estado === 'programado'; }).forEach(function(g){ var c = camion(g.camion_id); if(c && mecanico(c)) issues.push(c.patente + ': tiene un problema mecánico abierto.'); });
  var e = emitido('manana');
  return '<h2>' + (e ? 'Reemitir programa' : 'Emitir programa') + '</h2><p class="hint">Jornada: ' + tomorrow() + '. Al emitirlo, transportistas y elaboradores ven su asignación.</p>' +
    (!total ? vacio('El programa de mañana está vacío. Programá al menos un camión.', 'margin-top:0') : '<p class="note" style="margin-bottom:10px"><b style="color:var(--fg)">' + total + '</b> camiones programados.</p>' + (issues.length ? '<div class="incbox inc-demora" style="margin-bottom:14px"><b>Para revisar antes de emitir:</b><ul style="margin:6px 0 0;padding-left:18px">' + issues.map(function(x){ return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>' : '<p class="note" style="margin-bottom:14px">El relevamiento de todos los contratistas está dentro del horario.</p>')) +
    errHtml() + '<form data-form="emitir" novalidate><button class="btn primary block" type="submit"' + (total ? '' : ' disabled') + '>' + (issues.length ? 'Emitir igual' : (e ? 'Reemitir programa' : 'Emitir programa')) + '</button></form>';
}

function sheetCamion(){
  var c = ui.sheet.id ? camion(ui.sheet.id) : null, auto = !!ui.sheet.auto, u = API.usuario();
  var v = c || { patente: '', chofer: auto ? u.nombre : '', telefono: '', empresa: auto ? u.empresa : '', capacidad_tn: '', traccion: '6x4' };
  var empresas = []; camiones().forEach(function(x){ if(x.empresa && empresas.indexOf(x.empresa) < 0) empresas.push(x.empresa); });
  return '<h2>' + (c ? 'Editar camión' : auto ? 'Alta de mi camión' : 'Agregar camión') + '</h2><p class="hint">' + (auto ? 'Cargá los datos de tu camión. El supervisor tiene que aceptar el alta antes de que puedas usar la app.' : 'Datos del transporte y del chofer.') + '</p><form data-form="camion" novalidate>' +
    '<div class="field"><label for="t-pat">Patente</label><input class="input mono" id="t-pat" name="patente" autocomplete="off" autocapitalize="characters" value="' + esc(v.patente) + '" placeholder="AB 123 CD"></div>' +
    '<div class="field"><label for="t-cho">Chofer</label><input class="input" id="t-cho" name="chofer" autocomplete="off" value="' + esc(v.chofer) + '" placeholder="Nombre y apellido"></div>' +
    '<div class="field"><label for="t-tel">Teléfono del chofer</label><input class="input mono" id="t-tel" name="telefono" type="tel" inputmode="tel" autocomplete="off" value="' + esc(v.telefono || '') + '" placeholder="Opcional"></div>' +
    '<div class="two"><div class="field"><label for="t-emp">Empresa de transporte</label><input class="input" id="t-emp" name="empresa" list="dl-emp" autocomplete="off" value="' + esc(v.empresa) + '" placeholder="Razón social"><datalist id="dl-emp">' + empresas.map(function(e){ return '<option value="' + esc(e) + '">'; }).join('') + '</datalist></div>' + fieldNum('t-cap', 'capacidad_tn', 'Capacidad (tn)', String(v.capacidad_tn).replace('.', ','), '28') + '</div>' +
    '<div class="field"><span class="lb" id="lb-tr">Tracción del camión</span><div class="seg" role="radiogroup" aria-labelledby="lb-tr">' + ['4x2', '6x4'].map(function(x){ return '<label><input type="radio" name="traccion" value="' + x + '"' + (v.traccion === x ? ' checked' : '') + '>' + x + '</label>'; }).join('') + '</div></div>' +
    errHtml() + '<button class="btn primary block" type="submit">' + (c ? 'Guardar cambios' : auto ? 'Enviar solicitud de alta' : 'Agregar camión') + '</button></form>';
}
function sheetBaja(){
  var c = camion(ui.sheet.id), asign = programa().filter(function(g){ return g.camion_id === c.id && g.estado === 'programado'; }).length;
  var head = '<h2>Eliminar camión</h2><p class="hint"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(c.chofer) + ' · ' + esc(c.empresa) + '</p>';
  if(c.estado === 'cargando') return head + '<div class="incbox inc-demora">Este camión está cargando ahora. Finalizá la carga antes de eliminarlo.</div>';
  return head + '<ul class="note" style="padding-left:18px;margin:0 0 14px"><li>Se quita del programa de hoy y de mañana' + (asign ? ' (' + asign + ' asignación' + (asign === 1 ? '' : 'es') + ')' : '') + '.</li><li>Ya no aparece en listas ni para programar.</li><li>El historial de despachos se conserva.</li></ul>' + errHtml() + '<form data-form="baja" novalidate><button class="btn warn block" type="submit">Eliminar camión</button></form>';
}

function sheetSolic(){
  var sol = solicDe(S.contratista_id);
  return '<h2>Unidades mínimas necesarias</h2><p class="hint">' + esc(contrNombre(S.contratista_id)) + ' · ' + tomorrow() + '. El supervisor ve tu pedido al armar el programa.</p><form data-form="solic" novalidate>' +
    '<div class="field"><label for="s-n">Cantidad mínima de camiones</label><input class="input mono" id="s-n" name="n" inputmode="numeric" autocomplete="off" value="' + (sol ? sol.cantidad_minima : '') + '" placeholder="Ej.: 4"></div><div class="field"><label for="s-nota">Detalle (opcional)</label><input class="input" id="s-nota" name="nota" autocomplete="off" value="' + esc(sol ? sol.nota : '') + '" placeholder="Ej.: largos de 20 pies, trocha larga"></div>' +
    errHtml() + '<button class="btn primary block" type="submit">' + (sol ? 'Guardar cambios' : 'Enviar solicitud') + '</button>' + (sol ? '<button type="button" class="btn warn block" data-action="quitar-solic" style="margin-top:8px">Quitar solicitud</button>' : '') + '</form>';
}
function sheetInicio(){
  var cid = S.contratista_id, ie = inicioElabDe(cid, 'manana'), ini = inicioFrente(cid, 'manana');
  return '<h2>Hora de inicio de carga</h2><p class="hint">' + esc(contrNombre(cid)) + ' · ' + tomorrow() + '. Indicá a qué hora arranca la carga en tu frente.</p><form data-form="inicio" novalidate><div class="field"><label for="ic-h">Hora de inicio</label><input class="input mono" id="ic-h" name="hora" type="time" value="' + esc(ie ? ie.hora : (ini || '07:00')) + '"></div>' +
    errHtml() + '<button class="btn primary block" type="submit">Guardar hora</button>' + (ie ? '<button type="button" class="btn warn block" data-action="quitar-inicio" style="margin-top:8px">Quitar hora marcada</button>' : '') + '</form>';
}
function sheetBasHor(){
  var des = ui.sheet.kind === 'descanso';
  return '<h2>' + (des ? 'Descanso programado' : 'Horario disponible') + '</h2><p class="hint">' + (des ? 'Los transportistas lo ven en su panel para no llegar en ese horario.' : 'Franja en la que la báscula atiende. Los transportistas la ven en su panel.') + '</p><form data-form="bashor" novalidate><div class="two"><div class="field"><label for="bh-d">Desde</label><input class="input mono" id="bh-d" name="desde" type="time" value="' + (des ? '12:00' : '06:00') + '"></div><div class="field"><label for="bh-h">Hasta</label><input class="input mono" id="bh-h" name="hasta" type="time" value="' + (des ? '12:30' : '14:00') + '"></div></div>' +
    (des ? '<div class="field"><label for="bh-m">Motivo (opcional)</label><input class="input" id="bh-m" name="motivo" autocomplete="off" placeholder="Ej.: Almuerzo, mantenimiento"></div>' : '') + errHtml() + '<button class="btn primary block" type="submit">' + (des ? 'Guardar descanso' : 'Guardar horario') + '</button></form>';
}

function lineaHtml(prefix, l, i, puedeQuitar, delAction, extra){
  return '<div class="line"><div class="line-h"><span>' + prefix + ' ' + (i + 1) + '</span>' + (puedeQuitar ? '<button type="button" class="link" data-action="' + delAction + '" data-i="' + i + '">Quitar</button>' : '') + '</div>' +
    '<div class="seg" role="radiogroup" aria-label="Rollo fino o grueso">' + ['fino', 'grueso'].map(function(t){ return '<label><input type="radio" name="lt' + i + '" value="' + t + '" data-f="ltipo" data-i="' + i + '"' + (l.tipo === t ? ' checked' : '') + '><i class="dot ' + t + '"></i>' + tipoLabel(t) + '</label>'; }).join('') + '</div>' +
    '<div class="two"><div class="field" style="margin:0"><label for="l-l' + i + '">Largo</label><select class="input mono" id="l-l' + i + '" data-f="llargo" data-i="' + i + '">' + largos().map(function(x){ return '<option value="' + x + '"' + (x === l.largo_pies ? ' selected' : '') + '>' + fl(x) + '</option>'; }).join('') + '</select></div>' +
    '<div class="field" style="margin:0"><label for="l-m' + i + '">Volumen (m³)</label><input class="input mono" id="l-m' + i + '" data-f="m3" data-i="' + i + '" inputmode="decimal" autocomplete="off" value="' + esc(l.m3) + '" placeholder="0,0"></div></div>' + (extra || '') + '</div>';
}
function sheetPedido(){
  var d = ui.draft, tot = sum(d.lineas, function(l){ var n = numSimple(l.m3); return isFinite(n) ? n : 0; });
  return '<h2>Pedido de rollos</h2><p class="hint">' + esc(contrNombre(d.cid)) + '. Indicá qué largos y categorías tiene que elaborar. El avance se cuenta desde la fecha de creación del pedido.</p><form data-form="pedido" novalidate>' +
    d.lineas.map(function(l, i){ return lineaHtml('Línea', l, i, d.lineas.length > 1, 'del-linea'); }).join('') + '<button type="button" class="btn block" data-action="add-linea" style="margin-bottom:12px">+ Agregar otro largo o categoría</button>' +
    '<div class="field"><label for="pl-n">Indicación (opcional)</label><input class="input" id="pl-n" data-f="pnota" autocomplete="off" value="' + esc(d.nota) + '" placeholder="Ej.: priorizar largos de 12 pies"></div><div class="total-bar"><span>Total pedido</span><span><b id="tot">' + f1(tot) + '</b> m³</span></div>' +
    errHtml() + '<button class="btn primary block" type="submit">Guardar pedido</button>' + (pedidoDe(d.cid) ? '<button type="button" class="btn warn block" data-action="quitar-pedido" style="margin-top:8px">Quitar pedido</button>' : '') + '</form>';
}
function sheetFinalizar(){
  var k = carga(ui.sheet.id), c = camion(k.camion_id) || {}, d = ui.draft, disp = pilasDe(k.contratista_id), rods = rodalesDe(k.contratista_id);
  var tot = sum(d.lineas, function(l){ var n = numSimple(l.m3); return isFinite(n) ? n : 0; });
  return '<h2>Finalizar carga</h2><p class="hint"><span class="plate" style="font-size:14px">' + esc(c.patente) + '</span> &nbsp;' + esc(contrNombre(k.contratista_id)) + '</p><form data-form="finalizar" novalidate>' +
    (rods.length ? '<div class="field"><label for="f-rod">Rodal de carga</label><select class="input mono" id="f-rod" data-f="rodal">' + rods.map(function(r){ return '<option value="' + r.id + '"' + (r.id === d.rodal_id ? ' selected' : '') + '>' + esc(r.codigo) + '</option>'; }).join('') + '</select></div>' : '<p class="note">Este contratista no tiene rodales cargados en el tarifario.</p>') +
    '<div class="field"><span class="lb" id="lb-circ">Despacho para</span><div class="seg" role="radiogroup" aria-labelledby="lb-circ">' + ['industria', 'ventas'].map(function(x){ return '<label><input type="radio" name="circuito" value="' + x + '" data-f="circuito"' + (x === d.circuito ? ' checked' : '') + '>' + CIRC[x] + '</label>'; }).join('') + '</div></div>' +
    (!disp.length ? vacio('Este contratista no tiene stock relevado. Pedile que releve las pilas antes de finalizar.', 'margin-top:0') : '<span class="lb" style="display:block;margin-bottom:6px;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)">Qué cargó</span>' +
      d.lineas.map(function(l, i){ var av = stockDe(k.contratista_id, l.tipo, l.largo_pies, d.circuito); return lineaHtml('Carga', l, i, d.lineas.length > 1, 'del-linea', '<span style="font-size:12px;color:var(--muted)">' + (d.circuito === 'industria' ? 'Stock Pindó SA: ' : 'En pila: ') + f1(av) + ' m³ de ' + tipoLabel(l.tipo).toLowerCase() + ' de ' + fl(l.largo_pies) + '</span>'); }).join('') +
      '<button type="button" class="btn block" data-action="add-linea" style="margin-bottom:12px">+ Agregar otro largo o tipo</button>' +
      '<div class="field"><label for="f-dest">Destino</label><select class="input" id="f-dest" data-f="destino"' + (d.circuito ? '' : ' disabled') + '>' + (d.circuito ? destinos(d.circuito).map(function(x){ return '<option value="' + x.id + '"' + (x.id === d.destino_id ? ' selected' : '') + '>' + esc(x.nombre) + '</option>'; }).join('') : '<option>Elegí primero para quién es el despacho</option>') + '</select></div>' +
      '<div class="total-bar"><span>Total cargado</span><span><b id="tot">' + f1(tot) + '</b> m³</span></div>') + errHtml() + '<button class="btn primary block" type="submit"' + (disp.length ? '' : ' disabled') + '>Confirmar carga</button></form>';
}

function sheetRodal(){
  return '<h2>Nuevo rodal</h2><p class="hint">El rodal es el punto de carga. Cargá su código y la empresa de elaboración que trabaja en él.</p><form data-form="rodal" novalidate><div class="field"><label for="rd-c">Código del rodal</label><input class="input mono" id="rd-c" name="codigo" autocomplete="off" autocapitalize="characters" placeholder="Ej.: MMA07XC073"></div>' +
    '<div class="field"><label for="rd-e">Empresa de elaboración</label><select class="input" id="rd-e" name="contratista_id">' + contratistas().map(function(c){ return '<option value="' + c.id + '">' + esc(c.nombre) + '</option>'; }).join('') + '</select></div>' + errHtml() + '<button class="btn primary block" type="submit">Agregar rodal</button></form>';
}
function sheetRodalBaja(){
  var r = rodal(ui.sheet.rodal), n = tarifas().filter(function(t){ return t.rodal_id === ui.sheet.rodal; }).length;
  return '<h2>Quitar rodal</h2><p class="hint"><b class="mono">' + esc(r ? r.codigo : '') + '</b> y sus ' + n + ' tarifa' + (n === 1 ? '' : 's') + ' dejan de estar disponibles. Los despachos y remitos ya hechos conservan el código y la tarifa con la que se calcularon.</p>' + errHtml() + '<button class="btn warn block" data-action="rodal-del">Quitar rodal y sus tarifas</button>';
}
function sheetTarifa(){
  var lin = ui.sheet.lid ? tarifas().filter(function(t){ return t.id === ui.sheet.lid; })[0] : null, rid = lin ? lin.rodal_id : ui.sheet.rodal, r = rodal(rid);
  var v = lin || { destino_id: (destinos()[0] || {}).id, km_asfalto: '', km_tierra: '', tarifa_4x2: '', tarifa_6x4: '' };
  return '<h2>' + (lin ? 'Editar tarifa' : 'Nuevo destino') + '</h2><p class="hint">Rodal <b class="mono">' + esc(r ? r.codigo : '') + '</b>' + (lin ? ' · al guardar se crea una nueva vigencia desde hoy; los remitos anteriores conservan la tarifa vieja.' : '') + '</p><form data-form="tarifa" novalidate>' +
    '<div class="field"><label for="tf-d">Destino</label><select class="input" id="tf-d" name="destino_id"' + (lin ? ' disabled' : '') + '>' + destinos().map(function(x){ return '<option value="' + x.id + '"' + (x.id === v.destino_id ? ' selected' : '') + '>' + esc(x.nombre) + ' · ' + CIRC[x.circuito] + '</option>'; }).join('') + '</select></div>' +
    '<div class="two">' + fieldNum('tf-a', 'km_asfalto', 'Km de asfalto', v.km_asfalto, '0') + fieldNum('tf-t', 'km_tierra', 'Km de tierra', v.km_tierra, '0') + '</div><div class="two">' + fieldNum('tf-4', 'tarifa_4x2', 'Tarifa 4x2 ($/tn)', v.tarifa_4x2, '5500') + fieldNum('tf-6', 'tarifa_6x4', 'Tarifa 6x4 ($/tn)', v.tarifa_6x4, '5800') + '</div>' +
    errHtml() + '<button class="btn primary block" type="submit">' + (lin ? 'Guardar nueva vigencia' : 'Agregar destino') + '</button>' + (lin ? '<button type="button" class="btn warn block" data-action="tarifa-del" style="margin-top:8px">Quitar este destino</button>' : '') + '</form>';
}
function sheetImportar(){
  var d = ui.draft || {};
  if(d.res){
    var r = d.res;
    return '<h2>Importar tarifario</h2><p class="hint">Vista previa: ' + r.validas.length + ' fila' + (r.validas.length === 1 ? '' : 's') + ' válida' + (r.validas.length === 1 ? '' : 's') + ', ' + r.errores.length + ' con error' + (r.rodales_nuevos.length ? ', rodales nuevos: ' + r.rodales_nuevos.join(', ') : '') + '.</p>' +
      (r.errores.length ? '<div class="incbox inc-demora" style="margin-bottom:12px"><b>Filas con error (no se importan):</b><ul style="margin:6px 0 0;padding-left:18px">' + r.errores.slice(0, 20).map(function(e){ return '<li>Fila ' + e.fila + ': ' + esc(e.error) + '</li>'; }).join('') + (r.errores.length > 20 ? '<li>…</li>' : '') + '</ul></div>' : '') +
      (r.validas.length ? '<div class="rows" style="padding:4px 14px 6px;margin-bottom:12px;overflow-x:auto;max-height:40vh"><table class="tbl"><thead><tr><th>Rodal</th><th>Destino</th><th>4x2</th><th>6x4</th></tr></thead><tbody>' + r.validas.map(function(v){ return '<tr><td class="lg">' + esc(v.rodal) + '</td><td>' + esc(v.destino) + '</td><td>' + money(v.tarifa_4x2) + '</td><td>' + money(v.tarifa_6x4) + '</td></tr>'; }).join('') + '</tbody></table></div>' : '') +
      errHtml() + '<button class="btn primary block" data-action="importar-ok"' + (r.validas.length ? '' : ' disabled') + '>Confirmar e importar ' + r.validas.length + ' tarifa' + (r.validas.length === 1 ? '' : 's') + '</button>';
  }
  return '<h2>Importar tarifario</h2><p class="hint">Planilla .xlsx o .csv con las columnas: Empresa, Rodal, Destino, Km asfalto, Km tierra, 4x2, 6x4. Primero se muestra una vista previa con los errores.</p><form data-form="importar" novalidate><div class="field"><label for="imp-f">Archivo</label><input class="input" id="imp-f" name="archivo" type="file" accept=".xlsx,.csv" style="padding-top:9px"></div>' + errHtml() + '<button class="btn primary block" type="submit"' + (ui.cargando ? ' disabled' : '') + '>' + (ui.cargando ? 'Analizando…' : 'Ver vista previa') + '</button></form>';
}

function sheetRemito(){
  var d = ui.draft || { estado: 'manual' }, edit = !!(ui.sheet && ui.sheet.editId);
  if(d.estado === 'leyendo') return '<h2>Remito</h2>' + (d.foto ? '<img class="rembig" alt="Foto del remito" src="' + d.foto + '">' : '') + vacio('<span class="spinner"></span> Leyendo el remito…', 'margin-top:0');
  if(d.estado === 'error') return '<h2>Remito</h2><div class="incbox inc-demora">No se pudo abrir la foto. Probá sacarla de nuevo.</div>';
  var hint = edit ? 'Modificá los datos del remito. La foto guardada se conserva y la facturación se recalcula.' : d.estado === 'listo' ? 'La app leyó la foto. Revisá los datos y corregí lo que haga falta antes de guardar.' : d.estado === 'offline' ? 'Sin conexión: la foto queda guardada en el celular y se lee al reconectar. Completá los datos que veas en el remito.' : d.foto ? 'No se pudo leer la foto automáticamente. Completá los datos del remito.' : 'Cargá los datos del remito.';
  return '<h2>' + (edit ? 'Editar remito' : 'Datos del remito') + '</h2><p class="hint">' + hint + (d.patente_leida ? ' Patente leída: <b>' + esc(d.patente_leida) + '</b>.' : '') + '</p>' + (d.foto ? '<img class="rembig" alt="Foto del remito" src="' + d.foto + '" style="max-height:30vh">' : '') +
    (d.carga_info ? '<p class="note" style="margin:0 0 10px">Despacho vinculado: <b>' + esc(d.carga_info) + '</b></p>' : '') +
    '<form data-form="remito" novalidate><div class="two"><div class="field"><label for="rm-n">Número de remito</label><input class="input mono" id="rm-n" name="numero" autocomplete="off" value="' + esc(d.numero || '') + '"></div><div class="field"><label for="rm-f">Fecha</label><input class="input mono" id="rm-f" name="fecha" type="date" value="' + esc(d.fecha || S.hoy) + '"></div></div>' +
    '<div class="field"><label for="rm-r">Punto de carga (rodal)</label><select class="input mono" id="rm-r" name="rodal_id" data-f="rodal"><option value="">Elegir rodal</option>' + rodales().map(function(r){ return '<option value="' + r.id + '"' + (r.id === d.rodal_id ? ' selected' : '') + '>' + esc(r.codigo) + ' · ' + esc(r.contratista) + '</option>'; }).join('') + '</select></div>' +
    '<div class="field"><label for="rm-d">Destino</label><select class="input" id="rm-d" name="destino_id" data-f="destino"><option value="">Sin indicar</option>' + destinos().map(function(x){ return '<option value="' + x.id + '"' + (x.id === d.destino_id ? ' selected' : '') + '>' + esc(x.nombre) + '</option>'; }).join('') + '</select></div>' +
    fieldNum('rm-t', 'toneladas', 'Toneladas', d.toneladas != null && d.toneladas !== '' ? String(d.toneladas).replace('.', ',') : '', 'Ej.: 27,4', 'rtn') + (ui.rol === 'supervisor' ? '' : '<div class="total-bar" id="rimp">' + remitoImporteTxt(d) + '</div>') + errHtml() + '<button class="btn primary block" type="submit">' + (edit ? 'Guardar cambios' : 'Guardar remito') + '</button></form>';
}
function sheetRemitoVer(){
  var r = remitoAny(ui.sheet.rid);
  if(!r) return '<h2>Remito</h2>' + vacio('No se encontró el remito.');
  var imp = importeRem(r), c = camion(r.camion_id), sup = ui.rol === 'supervisor';
  return '<h2>Remito ' + esc(r.numero || 's/n') + '</h2>' + (r.foto_url ? '<img class="rembig" alt="Foto del remito" src="' + esc(r.foto_url) + '">' : vacio('Sin foto guardada.', 'margin-top:0')) +
    '<div class="rows" style="margin-bottom:12px"><div class="row" style="cursor:default"><span class="t"><b class="mono">' + esc(r.rodal) + '</b>' + (r.destino ? ' → ' + esc(r.destino) : '') + '</span><span class="s">' + (r.patente ? '<span><b>' + esc(r.patente) + '</b></span>' : '') + '<span>' + diaLabel(r.fecha) + '</span><span>Cargado ' + hm(r.cargado_en) + ' hs por ' + esc(r.cargado_por) + '</span><span>' + (r.origen_dato === 'ocr' ? 'Leído de la foto' : 'Carga manual') + '</span>' + (r.carga_id ? '<span>Trazado con despacho</span>' : '') + '</span><span class="m">' + f1(r.toneladas) + '<small>tn</small></span></div></div>' +
    (sup ? '' : '<p class="note" style="margin:0 0 12px">' + (imp ? 'Facturación de esta carga: <b>' + money(imp) + '</b> (' + (r.tarifa_aplicada ? money(r.tarifa_aplicada) + '/tn × ' + f1(r.toneladas) + ' tn · ' : '') + 'tarifa ' + tipoCam(c) + ')' : 'Sin tarifa para este rodal y destino: no suma a la facturación.') + '</p>') + errHtml() +
    (soloLectura() ? '' : '<div class="col"><button class="btn primary block" data-action="remito-edit" data-id="' + r.id + '">Editar datos del remito</button><button class="btn warn block" data-action="remito-del" data-id="' + r.id + '">Eliminar remito</button></div>');
}

function sheetUsuario(){
  var u = ui.draft.u, rolesU = u.roles;
  return '<h2>' + esc(u.nombre) + '</h2><p class="hint">@' + esc(u.usuario) + ' · ' + esc(u.empresa) + ' (' + esc(u.tipo_empresa) + ') · ' + esc(u.puesto) + ' · registrado ' + diaLabel(u.created_at) + '</p><form data-form="usuario" novalidate>' +
    '<div class="field"><span class="lb">Roles habilitados</span><div class="roles">' + ['transportista', 'elaborador', 'supervisor', 'bascula', 'jefe', 'admin'].map(function(r){ return '<label><input type="checkbox" name="roles" value="' + r + '"' + (rolesU.indexOf(r) >= 0 ? ' checked' : '') + '>' + ROLES[r] + '</label>'; }).join('') + '</div></div>' +
    '<div class="field"><label for="us-c">Contratista (para elaboradores)</label><select class="input" id="us-c" name="contratista_id"><option value="">Ninguno</option>' + contratistas().map(function(c){ return '<option value="' + c.id + '"' + (c.id === u.contratista_id ? ' selected' : '') + '>' + esc(c.nombre) + '</option>'; }).join('') + '</select></div>' +
    '<div class="field"><label for="us-p">Nueva contraseña (opcional, 8+)</label><input class="input" id="us-p" name="password" type="password" autocomplete="new-password"></div>' +
    '<label class="chk"><input type="checkbox" name="activo"' + (u.activo ? ' checked' : '') + '><span>Usuario activo (puede ingresar)</span></label>' + errHtml() + '<button class="btn primary block" type="submit">' + (u.activo ? 'Guardar usuario' : 'Guardar y aprobar acceso') + '</button></form>';
}
function sheetCatalogo(){
  var t = ui.sheet.tipo, lbl = { contratistas: 'contratista', destinos: 'destino', especies: 'especie', largos: 'largo' }[t];
  return '<h2>Nuevo ' + lbl + '</h2><form data-form="catalogo" novalidate>' + (t === 'largos' ? '<div class="field"><label for="ct-p">Largo en pies</label><input class="input mono" id="ct-p" name="pies" inputmode="numeric" autocomplete="off"></div>' : '<div class="field"><label for="ct-n">Nombre</label><input class="input" id="ct-n" name="nombre" autocomplete="off"></div>') +
    (t === 'destinos' ? '<div class="field"><span class="lb" id="lb-c">Circuito</span><div class="seg" role="radiogroup" aria-labelledby="lb-c"><label><input type="radio" name="circuito" value="industria" checked>Industria propia</label><label><input type="radio" name="circuito" value="ventas">Ventas</label></div></div>' : '') + errHtml() + '<button class="btn primary block" type="submit">Agregar ' + lbl + '</button></form>';
}

function sheetOutbox(){
  var ops = API.outbox(), fs = API.fallas(), off = ui.off || navigator.onLine === false;
  var out = '<h2>Pendientes de enviar</h2><p class="hint">Lo que está acá quedó <b>guardado en este dispositivo</b> pero todavía no está <b>confirmado en el servidor</b>. Se envía solo al recuperar la conexión; no cierres sesión hasta que se vacíe.</p>';
  out += '<h3 class="sec-h" style="margin-top:4px">Por enviar<span>' + ops.length + '</span></h3>';
  out += ops.length ? '<div class="rows" style="margin-top:8px">' + ops.map(function(o){ return '<div class="row" style="cursor:default"><span class="t">' + esc(o.desc || o.ruta) + '</span><span class="s"><span>Guardado ' + diaLabel(o.creado_en) + ' ' + hm(o.creado_en) + ' hs</span>' + (o.reintentos ? '<span>' + o.reintentos + ' reintento' + (o.reintentos === 1 ? '' : 's') + '</span>' : '') + (o.foto ? '<span>Incluye foto</span>' : '') + '</span><span class="m"><span class="pill inc-demora" style="font-size:11px;padding:0 6px">Pendiente</span></span></div>'; }).join('') + '</div>' : vacio('Nada pendiente: todo está confirmado en el servidor.', 'margin-top:8px');
  out += '<h3 class="sec-h">Con error de sincronización<span>' + fs.length + '</span></h3>';
  out += fs.length ? '<p class="note" style="margin:6px 0 0">El servidor rechazó estas operaciones: no se aplicaron. Revisá el motivo, volvé a hacer la operación con los datos correctos y quitá el aviso.</p><div class="rows" style="margin-top:8px">' + fs.map(function(f){ return '<div class="row" style="cursor:default"><span class="t">' + esc(f.desc) + '</span><span class="s"><span style="color:var(--danger)">' + esc(f.mensaje) + '</span><span>Hecho ' + diaLabel(f.creado_en) + ' ' + hm(f.creado_en) + ' hs · rechazado ' + hm(f.en) + ' hs</span></span><button class="link" data-action="falla-del" data-id="' + f.id + '" style="grid-column:2;grid-row:1/3;color:var(--danger)">Quitar aviso</button></div>'; }).join('') + '</div>' : vacio('Sin errores.', 'margin-top:8px');
  return out + (ops.length && !off ? '<button class="btn primary block" data-action="actualizar" style="margin-top:12px">Enviar ahora</button>' : '');
}

function remitoImporteTxt(d){
  if(ui.rol === 'supervisor') return '';
  var tn = numSimple(d.toneladas), t = d.rodal_id && d.destino_id ? tarifaLin(d.rodal_id, d.destino_id) : null, c = camion(ui.camionId), tc = tipoCam(c), unit = t ? (tc === '4x2' ? t.tarifa_4x2 : t.tarifa_6x4) : null;
  if(!d.rodal_id || !d.destino_id) return '<span>Importe estimado</span><span style="color:var(--muted);font-size:13px;font-weight:600">Elegí rodal y destino</span>';
  if(!unit) return '<span>Importe estimado</span><span style="color:var(--muted);font-size:13px;font-weight:600">Sin tarifa ' + tc + ' para este rodal y destino</span>';
  if(!isFinite(tn) || tn <= 0) return '<span>Tarifa ' + tc + ' <b style="font-size:16px">' + money(unit) + '</b>/tn</span><span style="color:var(--muted);font-size:13px;font-weight:600">Ingresá las toneladas</span>';
  return '<span>' + money(unit) + '/tn × ' + f1(tn) + ' tn</span><span><b>' + money(Math.round(unit * tn)) + '</b></span>';
}

function sheetHtml(){
  if(!ui.sheet) return '';
  var t = ui.sheet.type, body;
  var map = { pila: sheetPila, programar: sheetProgramar, incidencia: sheetIncidencia, emitir: sheetEmitir, camion: sheetCamion, baja: sheetBaja, solic: sheetSolic, bashor: sheetBasHor, pedido: sheetPedido, rodal: sheetRodal, remito: sheetRemito, remitover: sheetRemitoVer, rodalbaja: sheetRodalBaja, tarifa: sheetTarifa, importar: sheetImportar, inicio: sheetInicio, finalizar: sheetFinalizar, usuario: sheetUsuario, catalogo: sheetCatalogo, outbox: sheetOutbox };
  try{ body = (map[t] || function(){ return ''; })(); }catch(e){ body = '<h2>Error</h2><p class="note">' + esc(e.message) + '</p>'; }
  return '<div class="overlay" data-action="close-sheet"><div class="sheet" role="dialog" aria-modal="true" aria-label="Formulario"><div class="grab"></div>' + body + '<button class="btn block" data-action="close-sheet" style="margin-top:10px;border-color:transparent;background:transparent;color:var(--muted)">Cancelar</button></div></div>';
}
