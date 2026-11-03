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

  /* Rango del precio esperado por m²: [inf, sup] con la marca del esperado y la del publicado. */
  function rangoPrecio(contenedor, publicado, esperado, inf, sup, formato) {
    const ancho = 600, alto = 64;
    const min = Math.min(publicado, inf) * 0.9, max = Math.max(publicado, sup) * 1.05;
    const x = v => 10 + (ancho - 20) * (v - min) / (max - min);
    const svg = el("svg", { viewBox: `0 0 ${ancho} ${alto}` });
    svg.appendChild(el("rect", { x: x(inf), y: 26, width: x(sup) - x(inf), height: 14, fill: "var(--linea)" }));
    svg.appendChild(el("line", { x1: x(esperado), x2: x(esperado), y1: 20, y2: 46, stroke: "var(--tinta-2)", "stroke-width": 3 }));
    svg.appendChild(el("text", { x: x(esperado), y: 14, "text-anchor": "middle", class: "etiqueta-cat" }, `esperado ${formato(esperado)}`));
    svg.appendChild(el("text", { x: x(inf), y: 58, "text-anchor": "start", class: "etiqueta-cat" }, `piso ${formato(inf)}`));
    svg.appendChild(el("text", { x: x(sup), y: 58, "text-anchor": "end", class: "etiqueta-cat" }, `techo ${formato(sup)}`));
    const g = el("g");
    // El publicado es un rombo en tinta: no usa la forma ni el color de ningún nivel
    g.appendChild(el("polygon", { points: `${x(publicado)},22 ${x(publicado) + 7},33 ${x(publicado)},44 ${x(publicado) - 7},33`, fill: "var(--tinta)", stroke: "var(--crema)", "stroke-width": 1.5 }));
    g.appendChild(el("text", { x: x(publicado), y: 48, "text-anchor": "middle", class: "etiqueta-valor" }, `publicado ${formato(publicado)}`));
    svg.appendChild(g);
    contenedor.innerHTML = "";
    contenedor.appendChild(svg);
  }

  global.Graficos = { barrasHorizontales, barrasVerticales, barraProporcion, rangoPrecio, conTooltip };
})(window);
