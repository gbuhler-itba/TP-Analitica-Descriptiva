/* Gráficos en SVG sin librerías: barras horizontales y verticales con eje desde 0, etiquetas directas
   y tooltip. Un mensaje por gráfico; nada de 3D ni ejes secundarios. */
(function (global) {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const fmtEntero = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });

  function el(nombre, atributos, texto) {
    const e = document.createElementNS(NS, nombre);
    for (const k in atributos) e.setAttribute(k, atributos[k]);
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  const tooltip = () => document.getElementById("tooltip");
  function conTooltip(nodo, texto) {
    nodo.addEventListener("mousemove", (ev) => {
      const t = tooltip();
      t.textContent = texto;
      t.hidden = false;
      const x = Math.min(ev.clientX + 14, window.innerWidth - 300);
      t.style.left = x + "px";
      t.style.top = (ev.clientY + 14) + "px";
    });
    nodo.addEventListener("mouseleave", () => { tooltip().hidden = true; });
  }

  /* Barras horizontales. filas: [{etiqueta, valor, color, detalle, extra}]. Eje desde 0. */
  function barrasHorizontales(contenedor, filas, opciones) {
    const o = Object.assign({ ancho: 560, altoFila: 26, margenIzq: 170, margenDer: 70, formato: fmtEntero.format,
                              maximo: null, extraAncho: 0 }, opciones || {});
    const alto = filas.length * o.altoFila + 8;
    const svg = el("svg", { viewBox: `0 0 ${o.ancho} ${alto}`, role: "img" });
    const max = o.maximo || Math.max(...filas.map(f => f.valor), 1);
    const anchoBarra = o.ancho - o.margenIzq - o.margenDer - o.extraAncho;
    svg.appendChild(el("line", { x1: o.margenIzq, x2: o.margenIzq, y1: 0, y2: alto - 8, class: "eje" }));
    filas.forEach((f, i) => {
      const y = i * o.altoFila + 4;
      const w = Math.max(0, anchoBarra * f.valor / max);
      svg.appendChild(el("text", { x: o.margenIzq - 8, y: y + o.altoFila * 0.62, "text-anchor": "end", class: "etiqueta-cat" },
                         f.etiqueta));
      const barra = el("rect", { x: o.margenIzq, y, width: w, height: o.altoFila - 8,
                                 fill: f.color || "var(--senal)", class: "barra" });
      svg.appendChild(barra);
      svg.appendChild(el("text", { x: o.margenIzq + w + 6, y: y + o.altoFila * 0.62, class: "etiqueta-valor" }, o.formato(f.valor)));
      if (f.extra !== undefined) {
        svg.appendChild(el("text", { x: o.ancho - 4, y: y + o.altoFila * 0.62, "text-anchor": "end", class: "etiqueta-cat" }, f.extra));
      }
      conTooltip(barra, f.detalle || `${f.etiqueta}: ${o.formato(f.valor)}`);
    });
    contenedor.innerHTML = "";
    contenedor.appendChild(svg);
    return svg;
  }

  /* Barras verticales con intervalo opcional. columnas: [{etiqueta, valor, inf, sup, color, detalle}]. Eje desde 0. */
  function barrasVerticales(contenedor, columnas, opciones) {
    const o = Object.assign({ ancho: 560, alto: 260, margenIzq: 44, margenInf: 46, margenSup: 14, unidad: "%",
                              maximo: null, tituloY: "" }, opciones || {});
    const svg = el("svg", { viewBox: `0 0 ${o.ancho} ${o.alto}`, role: "img" });
    const max = o.maximo || Math.max(...columnas.map(c => c.sup || c.valor)) * 1.1;
    const areaAlto = o.alto - o.margenInf - o.margenSup;
    const areaAncho = o.ancho - o.margenIzq - 10;
    const paso = areaAncho / columnas.length;
    const escala = v => o.margenSup + areaAlto - areaAlto * v / max;
    // Líneas de referencia horizontales, pocas y livianas
    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = max * t / ticks;
      const y = escala(v);
      svg.appendChild(el("line", { x1: o.margenIzq, x2: o.ancho - 10, y1: y, y2: y, class: "eje" }));
      svg.appendChild(el("text", { x: o.margenIzq - 6, y: y + 4, "text-anchor": "end", class: "etiqueta-cat" },
                         Math.round(v) + o.unidad));
    }
    columnas.forEach((c, i) => {
      const x = o.margenIzq + i * paso + paso * 0.18;
      const w = paso * 0.64;
      const y = escala(c.valor);
      const barra = el("rect", { x, y, width: w, height: o.margenSup + areaAlto - y,
                                 fill: c.color || "var(--senal)", class: "barra" });
      svg.appendChild(barra);
      if (c.inf !== undefined && c.sup !== undefined) {
        const cx = x + w / 2;
        svg.appendChild(el("line", { x1: cx, x2: cx, y1: escala(c.sup), y2: escala(c.inf), class: "ic" }));
        svg.appendChild(el("line", { x1: cx - 4, x2: cx + 4, y1: escala(c.sup), y2: escala(c.sup), class: "ic" }));
        svg.appendChild(el("line", { x1: cx - 4, x2: cx + 4, y1: escala(c.inf), y2: escala(c.inf), class: "ic" }));
      }
      svg.appendChild(el("text", { x: x + w / 2, y: o.alto - o.margenInf + 16, "text-anchor": "middle", class: "etiqueta-cat" },
                         c.etiqueta));
      conTooltip(barra, c.detalle || `${c.etiqueta}: ${c.valor}${o.unidad}`);
    });
    if (o.tituloY) {
      svg.appendChild(el("text", { x: o.margenIzq, y: o.alto - 6, class: "etiqueta-cat" }, o.tituloY));
    }
    contenedor.innerHTML = "";
    contenedor.appendChild(svg);
    return svg;
  }

  /* Una barra de proporción: valor sobre total, con una marca de referencia. */
  function barraProporcion(contenedor, valor, total, referencia, etiquetaRef) {
    const ancho = 600, alto = 44;
    const svg = el("svg", { viewBox: `0 0 ${ancho} ${alto}` });
    svg.appendChild(el("rect", { x: 0, y: 14, width: ancho, height: 16, fill: "var(--linea-suave)" }));
    svg.appendChild(el("rect", { x: 0, y: 14, width: ancho * valor / total, height: 16, fill: "var(--candidato)" }));
    if (referencia !== undefined) {
      const xr = ancho * referencia / total;
      svg.appendChild(el("line", { x1: xr, x2: xr, y1: 8, y2: 36, stroke: "#333", "stroke-width": 2 }));
      svg.appendChild(el("text", { x: Math.min(xr + 5, ancho - 150), y: 10, class: "etiqueta-cat" }, etiquetaRef));
    }
    svg.appendChild(el("text", { x: 0, y: 42, class: "etiqueta-cat" }, "0"));
    svg.appendChild(el("text", { x: ancho, y: 42, "text-anchor": "end", class: "etiqueta-cat" }, `${fmtEntero.format(total)} señales`));
    contenedor.innerHTML = "";
    contenedor.appendChild(svg);
  }

  /* Rango del precio esperado por m²: una línea base con toda la escala y, sobre ella y a la misma altura,
     la banda del rango del 80% [inf, sup], la marca del esperado y el rombo del publicado.
     Etiquetas: "esperado" y "publicado" arriba, "piso" y "techo" abajo; si dos chocan, se corre una. */
  function rangoPrecio(contenedor, publicado, esperado, inf, sup, formato) {
    const ancho = 600, alto = 96, yBase = 52, margen = 10, anchoLetra = 6.6;
    const lo = Math.min(publicado, inf), hi = Math.max(publicado, sup);
    const holgura = (hi - lo) * 0.04 || 1;
    const x = v => margen + (ancho - 2 * margen) * (v - lo + holgura) / (hi - lo + 2 * holgura);
    const svg = el("svg", { viewBox: `0 0 ${ancho} ${alto}` });

    svg.appendChild(el("line", { x1: x(lo) - 6, x2: x(hi) + 6, y1: yBase, y2: yBase, stroke: "var(--linea)", "stroke-width": 1.5 }));
    svg.appendChild(el("rect", { x: x(inf), y: yBase - 7, width: x(sup) - x(inf), height: 14, fill: "var(--linea)" }));
    svg.appendChild(el("line", { x1: x(esperado), x2: x(esperado), y1: yBase - 12, y2: yBase + 12, stroke: "var(--tinta-2)", "stroke-width": 3 }));
    // El publicado es un rombo en tinta: no usa la forma ni el color de ningún nivel
    const xp = x(publicado);
    svg.appendChild(el("polygon", { points: `${xp},${yBase - 8} ${xp + 8},${yBase} ${xp},${yBase + 8} ${xp - 8},${yBase}`,
                                    fill: "var(--tinta)", stroke: "var(--crema)", "stroke-width": 1.5 }));

    // Una etiqueta ocupa [izq, der]; se ancla al centro y se corre si se sale del gráfico o choca con otra
    const caja = (cx, texto, anclaPreferida) => {
      const w = texto.length * anchoLetra;
      let izq = anclaPreferida === "end" ? cx - w : anclaPreferida === "start" ? cx : cx - w / 2;
      izq = Math.max(2, Math.min(ancho - 2 - w, izq));
      return { izq, der: izq + w, w, texto };
    };
    const chocan = (a, b) => a.izq < b.der + 6 && b.izq < a.der + 6;
    const correr = (movil, fija) => {   // corre la móvil al lado de la fija que tenga lugar; si no hay, baja de fila
      const aIzq = fija.izq - 6 - movil.w, aDer = fija.der + 6;
      if (movil.izq + movil.w / 2 <= fija.izq + fija.w / 2 && aIzq >= 2) { movil.izq = aIzq; movil.der = aIzq + movil.w; return false; }
      if (aDer + movil.w <= ancho - 2) { movil.izq = aDer; movil.der = aDer + movil.w; return false; }
      if (aIzq >= 2) { movil.izq = aIzq; movil.der = aIzq + movil.w; return false; }
      return true;
    };
    const dibujar = (c, y, clase) => svg.appendChild(el("text", { x: c.izq, y, "text-anchor": "start", class: clase }, c.texto));

    const eEsperado = caja(x(esperado), `esperado ${formato(esperado)}`, "middle");
    const ePublicado = caja(xp, `publicado ${formato(publicado)}`, "middle");
    let filaAparte = false;
    if (chocan(ePublicado, eEsperado)) filaAparte = correr(ePublicado, eEsperado);
    dibujar(eEsperado, 18, "etiqueta-cat");
    dibujar(ePublicado, filaAparte ? 34 : 18, "etiqueta-valor");

    const ePiso = caja(x(inf), `piso ${formato(inf)}`, "start");
    const eTecho = caja(x(sup), `techo ${formato(sup)}`, "end");
    let techoAparte = false;
    if (chocan(ePiso, eTecho)) techoAparte = correr(eTecho, ePiso);
    dibujar(ePiso, 78, "etiqueta-cat");
    dibujar(eTecho, techoAparte ? 92 : 78, "etiqueta-cat");

    contenedor.innerHTML = "";
    contenedor.appendChild(svg);
  }

  global.Graficos = { barrasHorizontales, barrasVerticales, barraProporcion, rangoPrecio, conTooltip };
})(window);
