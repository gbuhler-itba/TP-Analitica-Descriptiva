/* Regla de decisión en el navegador: el mismo cálculo que src/regla.py (calcular y decidir),
   con los parámetros por escenario que exporta src/exportar_dashboard.py (resumen.parametros_costos).
   Recibe un aviso de avisos.json y devuelve los componentes en USD y la brecha neta. */
(function (global) {
  "use strict";

  const NIVELES_QUE_QUITAN_LA_PRIMA = new Set(["media", "integral"]);

  function sellos(monto, p, proporcion) {
    const alicuota = monto <= p.sellos_umbral_usd ? p.sellos_hasta_umbral : p.sellos_sobre_umbral;
    return alicuota * proporcion * monto;
  }

  function costoEntrada(precio, p) {
    const escribano = Math.max(p.escribano * precio, p.escribano_minimo_usd);
    return escribano + sellos(precio, p, p.sellos_comprador) + (p.comision_comprador + p.otros_entrada) * precio;
  }

  function costoRefaccion(nivel, m2, p) {
    if (nivel === "liviana") return p.liviana_m2 * m2;
    if (nivel === "media") return p.bano_cocina_usd + p.liviana_m2 * m2;
    if (nivel === "integral") return p.integral_m2 * m2;
    return 0;
  }

  function costoSalida(venta, p) {
    return (p.comision_vendedor + p.certificados) * venta + sellos(venta, p, p.sellos_vendedor);
  }

  /* opciones: { parametros, refaccion: "central"|"baja"|"alta", valorSalida: "esperado"|"piso",
                 ganancias: alícuota (0 a 1) o null, negociacion: proporción o null } */
  function calcular(aviso, opciones) {
    const p = Object.assign({}, opciones.parametros);
    if (opciones.ganancias !== null && opciones.ganancias !== undefined) p.ganancias = opciones.ganancias;
    if (opciones.negociacion !== null && opciones.negociacion !== undefined) p.negociacion = opciones.negociacion;
    const nivel = aviso.nivel_refaccion[opciones.refaccion || "central"];
    const precioM2 = opciones.valorSalida === "piso" ? aviso.precio_m2_inf : aviso.precio_m2_esperado;
    const prima = Math.min(aviso.prima_estado || 0, 0);
    const valor = precioM2 * aviso.m2 * Math.exp(NIVELES_QUE_QUITAN_LA_PRIMA.has(nivel) ? -prima : 0);
    const venta = valor * (1 - p.negociacion);
    const salida = costoSalida(venta, p);
    const entrada = costoEntrada(aviso.precio_usd, p);
    const obra = costoRefaccion(nivel, aviso.m2, p);
    const total = aviso.precio_usd + entrada + obra;
    const ganancia = venta - salida - total;
    const impuesto = p.ganancias * Math.max(ganancia, 0);
    const resultado = ganancia - impuesto;
    return { nivel, entrada, refaccion: obra, total, valor_salida: valor, venta_cierre: venta, salida, impuesto,
             resultado, brecha_neta: resultado / total };
  }

  /* Una señal es candidata si deja el margen mínimo y no tiene riesgo legal de descarte. */
  function esCandidato(aviso, calculo, umbral) {
    return calculo.brecha_neta >= umbral && !(aviso.riesgo_descartar && aviso.riesgo_descartar.length);
  }

  global.Regla = { calcular, esCandidato, costoEntrada, costoRefaccion, costoSalida };
})(window);
