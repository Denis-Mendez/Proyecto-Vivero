(function () {
  const $ = (id) => document.getElementById(id);
  const latIn = $("lat"), lonIn = $("lon");
  const fmt = (v, d = 1) => (v === null || v === undefined) ? "–" : Number(v).toFixed(d).replace(".", ",");
  const suma = (arr) => arr.reduce((a, b) => a + (b ?? 0), 0);
  const C = { verde: "#17954E", petroleo: "#194E50", azul: "#007AFF", grid: "#E3ECEE" };
  const esCelular = () => window.matchMedia("(max-width: 767.98px)").matches;

  // --- Mapa: arranca centrado en el vivero ---
  const zoom = +$("map").dataset.zoom || 16;
  const map = L.map("map", { scrollWheelZoom: !esCelular() }).setView([+latIn.value, +lonIn.value], zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "&copy; OpenStreetMap"
  }).addTo(map);
  const marker = L.marker([+latIn.value, +lonIn.value]).addTo(map);
  function moverA(lat, lon, centrar) {
    marker.setLatLng([lat, lon]);
    latIn.value = (+lat).toFixed(4);
    lonIn.value = (+lon).toFixed(4);
    if (centrar) map.setView([lat, lon], zoom);
  }
  map.on("click", (e) => moverA(e.latlng.lat, e.latlng.lng, false));
  setTimeout(() => map.invalidateSize(), 300);

  // --- Gráfico ---
  let grafico = null;
  function dibujar(filas) {
    const cel = esCelular();
    const etiquetas = filas.map((f) => f.fecha.slice(8, 10) + "/" + f.fecha.slice(5, 7));
    const datos = {
      labels: etiquetas,
      datasets: [
        { type: "bar", label: "Lluvia (mm)", data: filas.map((f) => f.precip), yAxisID: "y2",
          backgroundColor: "rgba(0,122,255,0.30)", borderRadius: 3, order: 3 },
        { type: "line", label: "ET₀ Penman-Monteith", data: filas.map((f) => f.et0_pm),
          borderColor: C.verde, backgroundColor: C.verde, tension: 0.3, borderWidth: 2.5, pointRadius: cel ? 0 : 2, order: 1 },
        { type: "line", label: "ET₀ Hargreaves", data: filas.map((f) => f.et0_hs),
          borderColor: C.petroleo, borderDash: [5, 4], tension: 0.3, borderWidth: 1.5, pointRadius: 0, order: 2 },
      ],
    };
    const opciones = {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: cel ? 10 : 12 } } } },
      scales: {
        y: { title: { display: !cel, text: "ET₀ (mm/día)" }, beginAtZero: true, grid: { color: C.grid } },
        y2: { position: "right", title: { display: !cel, text: "Lluvia (mm)" }, beginAtZero: true, grid: { display: false } },
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, autoSkipPadding: cel ? 6 : 10 } },
      },
    };
    if (grafico) grafico.destroy();
    grafico = new Chart($("grafico"), { data: datos, options: opciones });
  }

  const md = "d-none d-md-table-cell", sm = "d-none d-sm-table-cell", lg = "d-none d-lg-table-cell";
  function llenarTabla(filas) {
    $("tabla").innerHTML = filas.map((f) => `<tr>
      <td>${f.fecha.slice(8, 10)}/${f.fecha.slice(5, 7)}</td><td>${fmt(f.tmax)}</td><td>${fmt(f.tmin)}</td>
      <td class="${md}">${fmt(f.hr_max, 0)}</td><td class="${md}">${fmt(f.hr_min, 0)}</td><td class="${md}">${fmt(f.u2)}</td>
      <td class="${sm}">${fmt(f.rs)}</td><td>${fmt(f.precip)}</td><td class="destacado">${fmt(f.et0_pm)}</td>
      <td class="${md}">${fmt(f.et0_hs)}</td><td class="${lg} text-secondary">${fmt(f.et0_ref)}</td><td>${fmt(f.gd)}</td></tr>`).join("");
  }

  async function consultar() {
    const lat = latIn.value.replace(",", "."), lon = lonIn.value.replace(",", ".");
    $("estado").textContent = "Consultando…"; $("estado").className = "small mt-2 text-secondary";
    try {
      const r = await fetch("/api/pronostico", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat, lon }),
      });
      const t = await r.json();
      if (!r.ok) throw new Error(t.error || r.statusText);
      const f = t.filas;
      const et0 = f.map((x) => x.et0_pm ?? x.et0_hs);
      $("k-et0").textContent = fmt(et0[0]);
      $("k-et07").textContent = fmt(suma(et0.slice(0, 7)), 0);
      $("k-lluvia").textContent = fmt(suma(f.map((x) => x.precip)), 0);
      $("k-lluvia-u").textContent = `mm en ${f.length} días`;
      $("k-gd").textContent = fmt(t.gd_total, 0);
      dibujar(f); llenarTabla(f);
      const cuando = t.consultado.replace("T", " ").slice(0, 16);
      $("aviso-fuente").innerHTML = `Fuente: <b>${t.fuente}</b> · ${t.lat.toFixed(3)}, ${t.lon.toFixed(3)} · ${t.elevacion ?? "?"} m · ${cuando}` +
        (t.desde_cache ? ' · <span class="badge text-bg-light border">datos guardados</span>' : "") +
        (t.hay_radiacion ? "" : ' · <span class="badge text-bg-secondary">sin radiación: solo Hargreaves</span>');
      $("estado").textContent = "";
      const q = `lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
      $("btn-csv").href = `/exportar.csv?${q}`; $("btn-csv").classList.remove("disabled");
      $("link-gd").href = `/grados-dia?${q}`;
    } catch (e) {
      $("estado").textContent = "Error: " + e.message; $("estado").className = "small mt-2 text-danger";
    }
  }

  $("btn-consultar").addEventListener("click", consultar);
  $("btn-vivero").addEventListener("click", (e) => {
    moverA(e.currentTarget.dataset.lat, e.currentTarget.dataset.lon, true);
    consultar();
  });
  let ancho = window.innerWidth;
  window.addEventListener("resize", () => {           // redibujar al girar el celular
    if (Math.abs(window.innerWidth - ancho) > 80 && grafico) { ancho = window.innerWidth; grafico.resize(); }
  });
  consultar();
})();
