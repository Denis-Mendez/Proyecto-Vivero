(function () {
  const $ = (id) => document.getElementById(id);
  const latIn = $("lat"), lonIn = $("lon");
  const fmt = (v, d = 1) => (v === null || v === undefined) ? "–" : Number(v).toFixed(d).replace(".", ",");
  const suma = (arr) => arr.reduce((a, b) => a + (b ?? 0), 0);

  // --- Mapa ---
  const map = L.map("map").setView([+latIn.value || -33, +lonIn.value || -56], 9);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "&copy; OpenStreetMap"
  }).addTo(map);
  let marker = L.marker([+latIn.value, +lonIn.value]).addTo(map);
  map.on("click", (e) => {
    marker.setLatLng(e.latlng);
    latIn.value = e.latlng.lat.toFixed(4);
    lonIn.value = e.latlng.lng.toFixed(4);
  });
  setTimeout(() => map.invalidateSize(), 300);

  // --- Gráfico ---
  let grafico = null;
  function dibujar(filas) {
    const etiquetas = filas.map((f) => f.fecha.slice(8, 10) + "/" + f.fecha.slice(5, 7));
    const datos = {
      labels: etiquetas,
      datasets: [
        { type: "bar", label: "Lluvia (mm)", data: filas.map((f) => f.precip), yAxisID: "y2",
          backgroundColor: "rgba(56,128,200,0.35)", borderRadius: 3, order: 3 },
        { type: "line", label: "ET₀ Penman-Monteith (mm)", data: filas.map((f) => f.et0_pm),
          borderColor: "#2e7d32", backgroundColor: "#2e7d32", tension: 0.3, borderWidth: 2.5, pointRadius: 2, order: 1 },
        { type: "line", label: "ET₀ Hargreaves (mm)", data: filas.map((f) => f.et0_hs),
          borderColor: "#9e9e9e", borderDash: [5, 4], tension: 0.3, borderWidth: 1.5, pointRadius: 0, order: 2 },
      ],
    };
    const opciones = {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
      scales: {
        y: { title: { display: true, text: "ET₀ (mm/día)" }, beginAtZero: true, grid: { color: "#eee" } },
        y2: { position: "right", title: { display: true, text: "Lluvia (mm)" }, beginAtZero: true, grid: { display: false } },
        x: { grid: { display: false } },
      },
    };
    if (grafico) grafico.destroy();
    grafico = new Chart($("grafico"), { data: datos, options: opciones });
  }

  function llenarTabla(filas) {
    $("tabla").innerHTML = filas.map((f) => `<tr>
      <td>${f.fecha.split("-").reverse().join("/")}</td><td>${fmt(f.tmax)}</td><td>${fmt(f.tmin)}</td>
      <td>${fmt(f.hr_max, 0)}</td><td>${fmt(f.hr_min, 0)}</td><td>${fmt(f.u2)}</td><td>${fmt(f.rs)}</td>
      <td>${fmt(f.precip)}</td><td class="fw-semibold">${fmt(f.et0_pm)}</td><td>${fmt(f.et0_hs)}</td>
      <td class="text-secondary">${fmt(f.et0_ref)}</td><td>${fmt(f.gd)}</td></tr>`).join("");
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
      $("aviso-fuente").innerHTML = `Fuente: <b>${t.fuente}</b> · punto ${t.lat.toFixed(3)}, ${t.lon.toFixed(3)} · elevación ${t.elevacion ?? "?"} m · consultado ${cuando}` +
        (t.desde_cache ? ' · <span class="badge text-bg-warning">datos guardados</span>' : "") +
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
  consultar();
})();
