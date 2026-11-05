/* Tablero de avisos a investigar: carga los JSON de data/, arma las cinco páginas y la ficha.
   No recalcula nada del modelo; solo la regla de decisión del simulador (js/regla.js). */
(function () {
  "use strict";

  const REPO = "https://github.com/gbuhler-itba/TP-Analitica-Descriptiva/blob/main/";
  // Paleta del informe: verde oscuro, oro y ocre (separables por luminancia y por forma), grises cálidos
  const COLOR = { senal: "#1f3a2e", candidato: "#c9a227", firme: "#b5651d", gris: "#b8afa0", fondo: "#9e968a" };
  const NOMBRE_NIVEL = { senal: "Señal a investigar", candidato: "Candidato después de costos", firme: "Candidato firme" };
  const D = {};            // datos cargados
  let mapa = null;         // estado del mapa (se arma la primera vez que se abre)
  let pendienteVolar = null;

  /* ---------- formato de números (Argentina: punto de miles, coma decimal) ---------- */
  const nf = (dec) => new Intl.NumberFormat("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const F0 = nf(0), F1 = nf(1);
  const menos = (s) => s.replace("-", "−");
  const num = (v, dec = 0) => v === null || v === undefined || Number.isNaN(v) ? "s/d" : menos((dec ? F1 : F0).format(v));
  const usd = (v) => v === null || v === undefined ? "s/d" : "USD " + menos(F0.format(Math.round(v)));
  const pct = (v, dec = 1, signo = false) => {
    if (v === null || v === undefined || Number.isNaN(v)) return "s/d";
    const s = menos((dec ? F1 : F0).format(v)) + "%";
    return signo && v > 0 ? "+" + s : s;
  };
  const plural = (n, singular, pl) => `${num(n)} ${n === 1 ? singular : pl}`;
  const html = (strings, ...vals) => strings.reduce((a, s, i) => a + s + (i < vals.length ? vals[i] : ""), "");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- niveles ---------- */
  const esCandidato = (a) => a.nivel === "candidato después de costos";
  const nivelDe = (a) => a.firme ? "firme" : esCandidato(a) ? "candidato" : "senal";
  const chipNivel = (a) => { const n = nivelDe(a); return `<span class="chip chip-${n}">${NOMBRE_NIVEL[n]}</span>`; };
  // Motivos por los que un aviso no entra a la lista destacada (vienen del exportador): se muestran siempre
  // Alerta descriptiva del notebook 06: el tipo de departamento con más error del modelo. No excluye de nada.
  const textoSegmentoAlerta = () => `Tipo de departamento con más error del modelo (${pct(D.resumen.indicadores.error_mediano_segmento_alerta_pct, 1)} contra ${pct(D.resumen.indicadores.error_mediano_pct, 1)} de la ciudad): el precio esperado tiende a quedar alto. Revisar con más cuidado.`;
  const chipSegmento = (a, corto) => a.segmento && a.segmento === D.resumen.indicadores.segmento_alerta
    ? (corto ? `<span class="chip chip-revisar" title="${esc(textoSegmentoAlerta())}">Revisar: tipo con más error del modelo</span>`
             : `<span class="chip chip-revisar chip-largo">Revisar: ${esc(textoSegmentoAlerta())}</span>`)
    : "";
  const chipsExclusion = (a) => a.exclusiones.map(e => `<span class="chip chip-exclusion" title="No entra a la lista destacada del resumen">${esc(e[0].toUpperCase() + e.slice(1))}</span>`).join("");
  const destacable = (a) => esCandidato(a) && a.consenso && a.exclusiones.length === 0;
  const prioridad = (a) => (a.firme ? 2 : esCandidato(a) ? 1 : 0) * 10 + (a.consenso ? 1 : 0);
  const ordenar = (lista) => lista.slice().sort((x, y) => prioridad(y) - prioridad(x) || (y.brecha_neta_pct ?? -999) - (x.brecha_neta_pct ?? -999));
  // Lista destacada: primero los firmes, después por brecha neta
  const ordenarDestacados = (lista) => lista.slice().sort((x, y) => (y.firme - x.firme) || (y.brecha_neta_pct ?? -999) - (x.brecha_neta_pct ?? -999));

  /* ---------- carga ---------- */
  async function cargar() {
    const [avisos, resumen, estaciones, fondo] = await Promise.all(
      ["avisos.json", "resumen.json", "estaciones.json", "fondo.json"].map(n => fetch("data/" + n).then(r => r.json())));
    Object.assign(D, { avisos, resumen, estaciones, fondo });
    D.porId = new Map(avisos.map(a => [a.id, a]));
    D.barrios = resumen.barrios.slice().sort((x, y) => x.nombre.localeCompare(y.nombre, "es"));
    document.getElementById("cargando").hidden = true;
    armarResumen();
    armarBuscador();
    armarTendencias();
    armarLeer();
    window.addEventListener("hashchange", enrutar);
    enrutar();
  }

  function enrutar() {
    const pagina = (location.hash || "#resumen").slice(1).split("/")[0];
    const valida = ["resumen", "mapa", "buscador", "tendencias", "leer"].includes(pagina) ? pagina : "resumen";
    document.querySelectorAll(".pagina").forEach(p => { p.hidden = p.id !== "pagina-" + valida; });
    document.querySelectorAll(".pestanas a").forEach(a => a.classList.toggle("activa", a.dataset.pagina === valida));
    if (valida === "mapa") {
      if (!mapa) armarMapa();
      setTimeout(() => { mapa.mapa.invalidateSize(); if (pendienteVolar) { volar(pendienteVolar); pendienteVolar = null; } }, 50);
    }
    window.scrollTo(0, 0);
  }

  /* ---------- tabla de avisos (resumen y buscador) ---------- */
  function tablaAvisos(lista, contenedor, maximo) {
    if (!lista.length) { contenedor.innerHTML = '<p class="vacio">Ningún aviso cumple con esos filtros.</p>'; return; }
    const filas = lista.slice(0, maximo || lista.length).map(a => html`
      <tr class="fila" data-id="${a.id}">
        <td><div class="chips-fila">${chipNivel(a)}${a.consenso ? '<span class="chip chip-consenso" title="Lo marcan los dos modelos">2 modelos</span>' : ""}${chipsExclusion(a)}${a.riesgo_descartar ? `<span class="chip chip-alerta">Riesgo legal</span>` : ""}${chipSegmento(a, true)}</div></td>
        <td>${esc(a.barrio_nombre)}<span class="titulo-aviso" title="${esc(a.titulo)}">${esc(a.titulo)}</span></td>
        <td class="num">${usd(a.precio_usd)}</td>
        <td class="num">${num(a.m2)} m² · ${num(a.ambientes)} amb.</td>
        <td class="num">${num(a.precio_m2)} / ${num(a.precio_m2_esperado)}</td>
        <td class="num neg">${pct(a.brecha_pct, 0)}</td>
        <td class="num ${a.brecha_neta_pct >= 0 ? "pos" : "neg"}">${pct(a.brecha_neta_pct, 0, true)}</td>
        <td><button class="chico secundario" data-ficha="${a.id}">Ficha</button></td>
      </tr>`).join("");
    contenedor.innerHTML = html`<table class="avisos">
      <thead><tr><th>Nivel</th><th>Barrio y aviso</th><th class="num">Precio</th><th class="num">Tamaño</th>
      <th class="num">USD/m² publicado / esperado</th><th class="num">Brecha</th><th class="num">Brecha neta</th><th></th></tr></thead>
      <tbody>${filas}</tbody></table>`;
    contenedor.querySelectorAll("tr.fila").forEach(tr => tr.addEventListener("click", () => abrirFicha(tr.dataset.id)));
  }

  /* ---------- resumen ---------- */
  function armarResumen() {
    const i = D.resumen.indicadores, m = D.resumen.metadatos;
    document.getElementById("indicadores").innerHTML = html`
      <div class="tarjeta"><div class="etiqueta">Avisos analizados</div><div class="numero">${num(i.avisos_analizados)}</div>
        <div class="detalle">${num(i.unidades_analizadas)} unidades · MercadoLibre, ${fecha(m.relevamiento_1)}</div></div>
      <div class="tarjeta nivel-senal"><div class="etiqueta">Señales a investigar</div><div class="numero">${num(i.senales_unidades)}</div>
        <div class="detalle">más de 25% por debajo del esperado, también en su barrio, sin errores de carga</div></div>
      <div class="tarjeta nivel-candidato"><div class="etiqueta">Candidatos después de costos</div><div class="numero">${num(i.candidatos_unidades)}</div>
        <div class="detalle">margen de al menos ${pct(100 * m.umbral_brecha_neta, 0)} con costos base y Ganancias en 0</div></div>
      <div class="tarjeta nivel-firme"><div class="etiqueta">Candidatos firmes</div><div class="numero">${num(i.candidatos_firmes_unidades)}</div>
        <div class="detalle">el margen se sostiene vendiendo al piso del rango del 80%</div></div>
      <div class="tarjeta"><div class="etiqueta">Error del precio esperado</div><div class="numero">${pct(i.error_mediano_pct)}</div>
        <div class="detalle">mediano, fuera de muestra; el rango del 80% cubre el publicado el ${pct(i.cobertura_intervalo_pct, 1)} de las veces</div></div>`;
    const lista = ordenarDestacados(D.avisos.filter(destacable));
    tablaAvisos(lista, document.getElementById("lista-resumen"), 10);
    document.getElementById("lista-resumen").insertAdjacentHTML("beforeend",
      `<p class="nota">Se muestran 10 de ${plural(lista.length, "aviso destacado", "avisos destacados")} (${plural(lista.filter(a => a.firme).length, "firme", "firmes")}). Los ${num(D.avisos.filter(a => esCandidato(a) && a.consenso && a.exclusiones.length).length)} candidatos de los dos modelos con alguna de esas alertas están en el <a href="#buscador">buscador</a>.</p>`);
    graficoEmbudo(document.getElementById("embudo-resumen"));
  }

  function fecha(iso) { const [a, m, d] = iso.split("-"); return `${d}/${m}/${a}`; }

  function graficoEmbudo(contenedor) {
    const pasos = D.resumen.embudo;
    const i = D.resumen.indicadores;
    const nombres = { analizados: "Avisos analizados", marcado: "Más de 25% por debajo del esperado",
                      marcado_barrio: "También bajo el umbral de su barrio", cumple_regla: "Sin errores de carga: señales",
                      candidato: "Con margen después de costos: candidatos" };
    const colores = { analizados: COLOR.gris, marcado: COLOR.gris, marcado_barrio: COLOR.gris, cumple_regla: COLOR.senal, candidato: COLOR.candidato };
    const filas = pasos.map(p => ({ etiqueta: nombres[p.paso] || p.paso, valor: p.unidades, color: colores[p.paso],
                                    detalle: `${p.filtro}: ${num(p.unidades)} unidades (${num(p.avisos)} avisos)` }));
    filas.push({ etiqueta: "Y también al piso del rango: firmes", valor: i.candidatos_firmes_unidades, color: COLOR.firme,
                 detalle: `Candidatos que siguen dejando margen vendiendo al límite inferior del rango del 80%: ${num(i.candidatos_firmes_unidades)} unidades` });
    // Ancho del viewBox parecido al del contenedor, para que el texto quede del tamaño del resto de la página
    Graficos.barrasHorizontales(contenedor, filas, { margenIzq: 300, ancho: 1100, altoFila: 26 });
  }

  /* ---------- buscador ---------- */
  function armarBuscador() {
    const sel = document.getElementById("f-barrio");
    D.barrios.forEach(b => sel.add(new Option(`${b.nombre} (${b.senales})`, b.barrio)));
    const estados = [...new Set(D.avisos.map(a => a.estado))];
    const selE = document.getElementById("f-estado");
    estados.forEach(e => selE.add(new Option(D.avisos.find(a => a.estado === e).estado_nombre, e)));
    const form = document.getElementById("filtros");
    form.addEventListener("input", buscar);
    form.addEventListener("reset", () => setTimeout(buscar, 0));
    buscar();
  }

  function buscar() {
    const v = (id) => document.getElementById(id).value;
    const chk = (id) => document.getElementById(id).checked;
    const barrio = v("f-barrio"), amb = v("f-ambientes"), precio = +v("f-precio"), m2min = +v("f-m2min"), m2max = +v("f-m2max");
    const estado = v("f-estado"), nivel = v("f-nivel");
    const lista = D.avisos.filter(a =>
      (!barrio || a.barrio === barrio) &&
      (!amb || (amb === "5" ? a.ambientes >= 5 : a.ambientes === +amb)) &&
      (!precio || a.precio_usd <= precio) &&
      (!m2min || a.m2 >= m2min) && (!m2max || a.m2 <= m2max) &&
      (!estado || a.estado === estado) &&
      (!nivel || (nivel === "firme" ? a.firme : esCandidato(a))) &&
      (!chk("f-sinriesgo") || (!a.riesgo_descartar && !a.riesgo_revisar)) &&
      (!chk("f-consenso") || a.consenso) &&
      (!chk("f-sinalertas") || a.exclusiones.length === 0));
    const ordenada = ordenar(lista);
    const tope = 60;
    document.getElementById("buscador-conteo").textContent =
      `${plural(lista.length, "señal cumple", "señales cumplen")} los filtros, de ${num(D.avisos.length)}` + (lista.length > tope ? `; se muestran las ${tope} mejores.` : ".");
    tablaAvisos(ordenada, document.getElementById("lista-buscador"), tope);
  }

  /* ---------- mapa ---------- */
  function iconoNivel(nivel) {
    const c = COLOR[nivel];
    const t = nivel === "firme" ? 18 : 14;   // los firmes, un poco más grandes: son pocos y son el mensaje
    const forma = nivel === "senal" ? `<circle cx="7" cy="7" r="5.5" fill="${c}" stroke="#222" stroke-width="1"/>`
      : nivel === "candidato" ? `<rect x="1.5" y="1.5" width="11" height="11" fill="${c}" stroke="#222" stroke-width="1"/>`
      : `<polygon points="7,0.5 13.8,13.2 0.2,13.2" fill="${c}" stroke="#222" stroke-width="1.2"/>`;
    return L.divIcon({ className: "marcador", html: `<svg width="${t}" height="${t}" viewBox="0 0 14 14">${forma}</svg>`,
                       iconSize: [t, t], iconAnchor: [t / 2, t / 2] });
  }

  function armarMapa() {
    const m = L.map("mapa", { preferCanvas: true, zoomControl: true }).setView([-34.615, -58.445], 12);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 19, opacity: 0.75 }).addTo(m);
    L.control.scale({ imperial: false }).addTo(m);

    // Fondo: todos los avisos con coordenadas, en gris y liviano (canvas)
    const fondo = L.layerGroup();
    const puntosPorBarrio = new Map();
    D.fondo.puntos.forEach(([lat, lon, b]) => {
      const slug = D.fondo.barrios[b];
      if (!puntosPorBarrio.has(slug)) puntosPorBarrio.set(slug, []);
      puntosPorBarrio.get(slug).push([lat, lon]);
      L.circleMarker([lat, lon], { radius: 2.2, color: COLOR.fondo, weight: 0, fillOpacity: 0.55, interactive: false }).addTo(fondo);
    });
    fondo.addTo(m);

    // Señales, candidatos y firmes, con forma y color propios
    const capas = { senal: L.layerGroup().addTo(m), candidato: L.layerGroup().addTo(m), firme: L.layerGroup().addTo(m) };
    const marcadores = new Map();
    D.avisos.filter(a => a.lat !== null && a.lon !== null).forEach(a => {
      const n = nivelDe(a);
      const mk = L.marker([a.lat, a.lon], { icon: iconoNivel(n), title: a.barrio_nombre });
      mk.bindTooltip(`${NOMBRE_NIVEL[n]} · ${esc(a.barrio_nombre)}<br>${usd(a.precio_usd)} · ${num(a.m2)} m² · brecha ${pct(a.brecha_pct, 0)}`);
      mk.on("click", () => abrirFicha(a.id));
      mk.addTo(capas[n]);
      marcadores.set(a.id, mk);
    });

    // Transporte: una forma por modo, mismo gris oscuro
    const transporte = {};
    const formas = { subte: "●", tren: "■", metrobus: "◆", premetro: "▲" };
    for (const modo of ["subte", "tren", "metrobus", "premetro"]) {
      transporte[modo] = L.layerGroup();
      D.estaciones[modo].forEach(e => {
        L.marker([e.lat, e.lon], { icon: L.divIcon({ className: "marcador", html: `<span style="font-size:11px;color:#444">${formas[modo]}</span>`, iconSize: [12, 12], iconAnchor: [6, 6] }),
                                   interactive: true }).bindTooltip(`${modo === "subte" ? "Subte" : modo === "tren" ? "Tren" : modo === "metrobus" ? "Metrobus" : "Premetro"}: ${esc(e.nombre)}${e.linea ? " (" + esc(e.linea) + ")" : ""}`).addTo(transporte[modo]);
      });
    }

    const alternar = (id, capa) => document.getElementById(id).addEventListener("change", ev => ev.target.checked ? capa.addTo(m) : m.removeLayer(capa));
    alternar("capa-fondo", fondo); alternar("capa-senal", capas.senal); alternar("capa-candidato", capas.candidato); alternar("capa-firme", capas.firme);
    for (const modo in transporte) alternar("capa-" + modo, transporte[modo]);

    const sel = document.getElementById("mapa-barrio");
    D.barrios.forEach(b => sel.add(new Option(b.nombre, b.barrio)));
    sel.addEventListener("change", () => {
      const slug = sel.value;
      for (const n in capas) {
        capas[n].eachLayer(mk => { const a = D.porId.get([...marcadores].find(([, v]) => v === mk)[0]); mk.setOpacity(!slug || a.barrio === slug ? 1 : 0.15); });
      }
      if (slug && puntosPorBarrio.has(slug)) m.fitBounds(L.latLngBounds(puntosPorBarrio.get(slug)).pad(0.05));
      else m.setView([-34.615, -58.445], 12);
      conteoMapa(slug);
    });
    conteoMapa("");
    mapa = { mapa: m, marcadores };
  }

  function conteoMapa(slug) {
    const lista = D.avisos.filter(a => !slug || a.barrio === slug);
    const conCoord = lista.filter(a => a.lat !== null).length;
    const b = slug ? D.resumen.barrios.find(x => x.barrio === slug) : null;
    document.getElementById("mapa-conteo").textContent = (b ? `${b.nombre}: ` : "Toda la ciudad: ") +
      `${plural(lista.length, "señal", "señales")} (${num(conCoord)} en el mapa), ${plural(lista.filter(esCandidato).length, "candidato", "candidatos")}, ${plural(lista.filter(a => a.firme).length, "firme", "firmes")}.`;
  }

  function volar(id) {
    const a = D.porId.get(id);
    if (!a || a.lat === null) return;
    mapa.mapa.flyTo([a.lat, a.lon], 16, { duration: 0.8 });
    const mk = mapa.marcadores.get(id);
    if (mk) setTimeout(() => mk.openTooltip(), 900);
  }

  function irAlMapa(id) {
    pendienteVolar = id;
    document.getElementById("ficha").close();
    if (location.hash === "#mapa") { volar(id); pendienteVolar = null; } else location.hash = "#mapa";
  }

  /* ---------- tendencias ---------- */
  function armarTendencias() {
    const deciles = D.resumen.salida_por_brecha || [];
    Graficos.barrasVerticales(document.getElementById("g-salida"), deciles.map(d => ({
      etiqueta: pct(d.brecha_mediana_pct, 0, true), valor: d.tasa_pct, inf: d.ic_inf_pct, sup: d.ic_sup_pct,
      color: d.marcado ? COLOR.senal : COLOR.gris,
      detalle: `Decil ${d.decil} (brecha de ${pct(d.brecha_min_pct, 0)} a ${pct(d.brecha_max_pct, 0)}): salieron ${pct(d.tasa_pct)} de ${num(d.avisos)} avisos (IC ${pct(d.ic_inf_pct)} a ${pct(d.ic_sup_pct)})` })),
      { maximo: 60, tituloY: "Decil de brecha (mediana). Verde oscuro: más de 25% por debajo del esperado." });
    const i = D.resumen.indicadores;
    document.getElementById("g-salida").insertAdjacentHTML("beforeend",
      `<p class="nota">En total salieron ${pct(i.tasa_salida_marcados_pct)} de los avisos marcados contra ${pct(i.tasa_salida_resto_pct)} del resto.</p>`);

    const top = D.resumen.barrios.filter(b => b.senales > 0).sort((x, y) => y.senales - x.senales).slice(0, 15);
    Graficos.barrasHorizontales(document.getElementById("g-barrios"), top.map(b => ({
      etiqueta: b.nombre, valor: b.senales, color: COLOR.senal, extra: plural(b.firmes, "firme", "firmes"),
      detalle: `${b.nombre}: ${plural(b.senales, "señal", "señales")} de ${num(b.unidades)} unidades (${pct(100 * b.senales / b.unidades)}); ${plural(b.candidatos, "candidato", "candidatos")}, ${plural(b.firmes, "firme", "firmes")}; error del modelo ${pct(b.error_mediano_pct)}` })),
      { margenIzq: 130, margenDer: 60, extraAncho: 70, altoFila: 24 });

    // Error del modelo por barrio, mismos barrios y mismo orden que el gráfico de señales (responde "dónde confiar")
    const errorCiudad = D.resumen.indicadores.error_mediano_pct;
    Graficos.barrasHorizontales(document.getElementById("g-error"), top.map(b => ({
      etiqueta: b.nombre, valor: b.error_mediano_pct, color: b.error_mediano_pct > errorCiudad ? "#5c6b62" : COLOR.gris,   // no es un nivel: sin el ocre de los firmes
      detalle: `${b.nombre}: error mediano ${pct(b.error_mediano_pct)} sobre ${num(b.avisos)} avisos (ciudad: ${pct(errorCiudad)})` })),
      { margenIzq: 130, margenDer: 60, altoFila: 24, formato: (v) => pct(v), maximo: 25 });
    document.getElementById("g-error").insertAdjacentHTML("beforeend",
      `<p class="nota">En gris oscuro, los barrios con error mayor que el de la ciudad (${pct(errorCiudad)}).</p>`);

    const s = D.resumen.sensibilidad;
    const esc_ = [["Base", s.base, COLOR.candidato], ["Costos optimistas", s.costos_optimistas], ["Costos pesimistas", s.costos_pesimistas],
                  ["Refacción baja", s.refaccion_baja], ["Refacción alta", s.refaccion_alta], ["Ganancias 15%", s.ganancias_15],
                  ["Ganancias 35%", s.ganancias_35], ["Margen mínimo 0%", s.umbral_0], ["Margen mínimo 20%", s.umbral_20],
                  ["Venta al piso del rango (conservador)", s.conservador, COLOR.firme]];
    Graficos.barrasHorizontales(document.getElementById("g-sensibilidad"), esc_.map(([e, v, c]) => ({ etiqueta: e, valor: v, color: c || COLOR.gris })),
      { margenIzq: 250, ancho: 640, altoFila: 24, maximo: D.resumen.indicadores.senales_unidades });

    armarSimulador();
  }

  function armarSimulador() {
    const p = D.resumen.parametros_costos;
    const neg = document.getElementById("s-negociacion"), umb = document.getElementById("s-umbral");
    neg.value = (100 * p.base.negociacion).toFixed(2);
    umb.value = Math.round(100 * D.resumen.metadatos.umbral_brecha_neta);
    document.getElementById("simulador").addEventListener("input", simular);
    document.getElementById("s-costos").addEventListener("change", () => { neg.value = (100 * p[document.getElementById("s-costos").value].negociacion).toFixed(2); simular(); });
    simular();
  }

  function simular() {
    const v = (id) => document.getElementById(id).value;
    const escenario = v("s-costos");
    const opciones = { parametros: D.resumen.parametros_costos[escenario], refaccion: v("s-refaccion"), valorSalida: v("s-salida"),
                       ganancias: +v("s-ganancias"), negociacion: +v("s-negociacion") / 100 };
    const umbral = +v("s-umbral") / 100;
    document.getElementById("s-negociacion-valor").textContent = menos(new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(+v("s-negociacion"))) + "%";
    document.getElementById("s-umbral-valor").textContent = pct(+v("s-umbral"), 0);
    let candidatos = 0;
    for (const a of D.avisos) if (Regla.esCandidato(a, Regla.calcular(a, opciones), umbral)) candidatos++;
    const total = D.avisos.length, base = D.resumen.sensibilidad.base;
    const r = document.getElementById("s-resultado");
    r.innerHTML = html`<div><div class="numero">${num(candidatos)}</div><div class="nota">${candidatos === 1 ? "candidato" : "candidatos"} de ${num(total)} señales (${pct(100 * candidatos / total, 0)})</div></div>
      <div class="barra-sim"></div>`;
    Graficos.barraProporcion(r.querySelector(".barra-sim"), candidatos, total, base, `base: ${num(base)}`);
  }

  /* ---------- cómo leer ---------- */
  function armarLeer() {
    const m = D.resumen.metadatos;
    const nbs = [["01_calidad_y_limpieza", "Limpieza y calidad del dato"], ["04_validacion_modelos", "Modelos, intervalo, primas y SHAP"],
                 ["05_hipotesis", "Hipótesis H1, H2 y H3 y el segundo relevamiento"], ["07_regla_de_decision", "Regla de decisión con costos"],
                 ["06_segmentos_exploratorio", "Índice de equipamiento y micro-mercados (exploratorio)"]];
    document.getElementById("enlaces-notebooks").innerHTML = nbs.map(([n, t]) => `<li><a href="${REPO}notebooks/${n}.ipynb" target="_blank" rel="noopener">${t}</a> (<code>${n}</code>)</li>`).join("") +
      `<li><a href="${REPO}README.md" target="_blank" rel="noopener">README del proyecto</a> y <a href="${REPO}docs/pipeline.md" target="_blank" rel="noopener">pipeline de datos</a></li>`;
    document.getElementById("pie-datos").textContent =
      `Datos generados el ${fecha(m.generado)} (commit ${m.commit}) con el modelo ${m.modelo_oficial}. Relevamientos del ${fecha(m.relevamiento_1)} y del ${fecha(m.relevamiento_2)}.`;
  }

  /* ---------- ficha ---------- */
  function abrirFicha(id) {
    const a = D.porId.get(id);
    if (!a) return;
    const n = nivelDe(a);
    const factores = a.factores.map(f => f.efecto_pct).map(Math.abs);
    const maxF = Math.max(...factores, 1);
    const filaFactor = (f) => html`<li><span>${esc(f.factor)}</span>
      <span class="barrita ${f.efecto_pct >= 0 ? "pos" : "neg"}" style="width:${Math.max(4, 70 * Math.abs(f.efecto_pct) / maxF)}px"></span>
      <span class="pct ${f.efecto_pct >= 0 ? "pos" : "neg"}">${pct(f.efecto_pct, 1, true)}</span></li>`;
    const suben = a.factores.filter(f => f.efecto_pct > 0), bajan = a.factores.filter(f => f.efecto_pct < 0);
    const c = a.costos;
    const alertas = [];
    if (a.estado !== "sin_marca") alertas.push(`<span class="chip">Título: ${esc(a.estado_nombre)}</span>`);
    if (a.bajo_de_precio) alertas.push(`<span class="chip">Bajó de precio</span>`);
    if (a.dist_barrio_popular_m !== null && a.dist_barrio_popular_m < 1000) alertas.push(`<span class="chip">Barrio popular más cercano a ${num(a.dist_barrio_popular_m)} m</span>`);
    if (a.avisos_discordantes) alertas.push(`<span class="chip chip-revisar">Otros avisos de la unidad no están marcados</span>`);
    if (a.avisos_de_la_unidad > 1) alertas.push(`<span class="chip">${a.avisos_de_la_unidad} avisos de la misma unidad</span>`);
    if (a.geo_dudoso) alertas.push(`<span class="chip chip-revisar">Geocodificación dudosa</span>`);
    if (a.debajo_del_intervalo) alertas.push(`<span class="chip">Publicado por debajo del rango del 80%</span>`);
    alertas.push(a.consenso ? `<span class="chip chip-consenso">Lo marcan los dos modelos</span>` : `<span class="chip">Solo lo marca el modelo oficial (gradient boosting: ${pct(a.brecha_otro_modelo_pct, 0)})</span>`);
    if (!a.lat) alertas.push(`<span class="chip">Sin coordenadas: comparado con su barrio</span>`);

    document.getElementById("ficha-contenido").innerHTML = html`
      <div class="ficha-cabecera">
        <div><h2 id="ficha-titulo">${esc(a.titulo)}</h2>
          <div class="sub">${esc(a.barrio_nombre)} · ${usd(a.precio_usd)} · ${num(a.m2)} m² · ${num(a.ambientes)} ambientes · ${a.antiguedad === null ? "antigüedad s/d" : num(a.antiguedad) + " años"} · posición ${a.posicion} de ${num(D.avisos.length)}</div>
          <div class="chips">${chipNivel(a)}${a.consenso ? '<span class="chip chip-consenso">2 modelos</span>' : ""}${a.motivo ? `<span class="chip">${esc(a.motivo)}</span>` : ""}${chipsExclusion(a)}${a.riesgo_descartar ? `<span class="chip chip-alerta">Riesgo legal (descarta): ${esc(a.riesgo_descartar)}</span>` : ""}${a.riesgo_revisar ? `<span class="chip chip-revisar">Revisar: ${esc(a.riesgo_revisar)}</span>` : ""}${chipSegmento(a, false)}</div>
          ${a.exclusiones.length ? `<p class="nota">No entra a la lista destacada del resumen: ${esc(a.exclusiones.join(", "))}. El modelo lo compara con departamentos comunes de su zona y ese comparable puede no aplicar.</p>` : ""}</div>
        <div class="ficha-acciones">
          <a class="boton secundario" href="${esc(a.link)}" target="_blank" rel="noopener">Ver en MercadoLibre</a>
          <button class="secundario" id="ficha-mapa" ${a.lat === null ? "disabled title='Sin coordenadas'" : ""}>Ver en el mapa</button>
          <button id="ficha-cerrar">Cerrar</button></div>
      </div>
      <div class="ficha-grilla">
        <div class="ficha-bloque-ancho"><h3>Publicado contra esperado (USD por m²)</h3>
          <div class="rango" id="ficha-rango"></div>
          <div class="cifras">
            <div>Publicado<strong>${num(a.precio_m2)}</strong></div>
            <div>Esperado<strong>${num(a.precio_m2_esperado)}</strong></div>
            <div>Rango del 80%<strong>${num(a.precio_m2_inf)} a ${num(a.precio_m2_sup)}</strong></div>
            <div>Brecha<strong class="neg">${pct(a.brecha_pct)}</strong></div>
            <div>Típico de la zona<strong>${num(a.precio_m2_referencia_zona)}</strong></div>
          </div>
          <p class="nota">El rango del 80% es la incertidumbre del precio esperado para este aviso: el precio publicado cae adentro en 8 de cada 10 avisos.</p></div>
        <div><h3>Qué suma al precio esperado</h3><ul class="factores">${suben.map(filaFactor).join("") || "<li>Nada relevante</li>"}</ul>
          <h3>Qué resta</h3><ul class="factores">${bajan.map(filaFactor).join("") || "<li>Nada relevante</li>"}</ul>
          <p class="nota">Respecto de un aviso típico de la zona, según el modelo oficial. Explica al modelo, no causas.</p></div>
        <div><h3>De la compra a la brecha neta (escenario base)</h3>
          <table class="cascada">
            <tr><td>Precio publicado (se compra sin negociar)</td><td class="num">${usd(a.precio_usd)}</td></tr>
            <tr><td>+ Costos de entrada (escribano, Sellos, comisión)</td><td class="num">${usd(c.entrada)}</td></tr>
            <tr><td>+ Refacción (${esc(a.nivel_refaccion.central)}, según el título)</td><td class="num">${usd(c.refaccion)}</td></tr>
            <tr class="total"><td>Costo total</td><td class="num">${usd(c.total)}</td></tr>
            <tr><td>Valor de salida (precio esperado${a.nivel_refaccion.central === "media" || a.nivel_refaccion.central === "integral" ? ", ya refaccionado" : ""})</td><td class="num">${usd(c.valor_salida)}</td></tr>
            <tr><td>− Negociación al vender (${pct(100 * D.resumen.parametros_costos.base.negociacion, 2)})</td><td class="num">${usd(c.venta_cierre)}</td></tr>
            <tr><td>− Costos de salida (comisión, Sellos, certificados)</td><td class="num">${usd(c.salida)}</td></tr>
            <tr><td>− Impuesto a las ganancias (0%, supuesto)</td><td class="num">USD 0</td></tr>
            <tr class="total"><td>Resultado</td><td class="num ${c.resultado >= 0 ? "pos" : "neg"}">${usd(c.resultado)}</td></tr>
            <tr class="total"><td>Brecha neta (resultado sobre costo total)</td><td class="num ${a.brecha_neta_pct >= 0 ? "pos" : "neg"}">${pct(a.brecha_neta_pct, 1, true)}</td></tr>
          </table>
          <p class="nota">Vendiendo al piso del rango del 80%: ${pct(100 * Regla.calcular(a, { parametros: D.resumen.parametros_costos.base, valorSalida: "piso" }).brecha_neta, 0, true)} de brecha neta${a.firme ? " (candidato firme)" : ""}. No incluye el costo de tenencia.</p></div>
        <div class="ficha-bloque-ancho"><h3>Contexto</h3><div class="chips">${alertas.join("")}</div>
          <p class="nota">Liquidez de referencia: de los avisos de ${num(a.ambientes)} ambientes, el ${pct(a.tasa_salida_ambientes_pct, 0)} salió del portal en 74 días (salir no es venderse). Completitud de la ficha: ${pct(100 * a.tasa_completitud, 0)}.</p></div>
      </div>`;
    Graficos.rangoPrecio(document.getElementById("ficha-rango"), a.precio_m2, a.precio_m2_esperado, a.precio_m2_inf, a.precio_m2_sup, (v) => num(v));
    document.getElementById("ficha-cerrar").addEventListener("click", () => document.getElementById("ficha").close());
    document.getElementById("ficha-mapa").addEventListener("click", () => irAlMapa(a.id));
    const dlg = document.getElementById("ficha");
    if (!dlg.open) dlg.showModal();
    dlg.scrollTop = 0;
  }

  document.getElementById("ficha").addEventListener("click", (ev) => { if (ev.target.id === "ficha") ev.target.close(); });
  document.addEventListener("click", (ev) => { const b = ev.target.closest("[data-ficha]"); if (b) { ev.stopPropagation(); abrirFicha(b.dataset.ficha); } }, true);

  cargar().catch(err => { document.getElementById("cargando").textContent = "No se pudieron cargar los datos: " + err; console.error(err); });
})();
