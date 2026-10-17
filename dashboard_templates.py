"""Jinja2 templates for the dashboard, as Python string constants in a DictLoader
(not on-disk files) - this gets real autoescaping over arXiv-sourced paper titles/
authors, and sidesteps the repo's `.gitignore` `*.html` glob rules that would
otherwise silently swallow real template files from a deploy.

Three-level inheritance: base.html (doctype/head/css only) -> shell.html (the
authenticated sidebar layout) -> each page template (page-specific content).
The login page extends base.html directly - it has no sidebar, since the user
isn't authenticated yet.
"""

from jinja2 import DictLoader, Environment, select_autoescape

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}ArXiv Research Assistant{% endblock %}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f5f7fb; --surface: #ffffff; --card: rgba(255,255,255,0.78);
    --border: #e4e7ef; --border-strong: #d3d8e3;
    --text: #0e1120; --text-2: #3d4255; --muted: #6b7185;
    --primary: #2a78d6; --primary-dark: #1c5cab; --violet: #6250d6;
    --danger: #e34948; --ok: #1baf7a; --warn: #eda100;
    --grad: linear-gradient(135deg, #2a78d6 0%, #6250d6 100%);
    --shadow: 0 1px 2px rgba(16,24,40,0.04), 0 8px 24px -12px rgba(16,24,40,0.12);
  }
  * { box-sizing: border-box; }
  html { -webkit-font-smoothing: antialiased; }
  body {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0; color: var(--text); background-color: var(--bg); min-height: 100vh;
    background-image:
      radial-gradient(800px 420px at 0% -10%, rgba(42,120,214,0.12), transparent 60%),
      radial-gradient(700px 420px at 100% 0%, rgba(98,80,214,0.10), transparent 60%),
      linear-gradient(rgba(14,17,32,0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(14,17,32,0.035) 1px, transparent 1px);
    background-size: auto, auto, 32px 32px, 32px 32px;
    background-attachment: fixed;
  }
  h1, h2, h3 { color: var(--text); margin-top: 0; letter-spacing: -0.02em; }
  h1 { font-size: 30px; font-weight: 800; margin-bottom: 6px; }
  h3 { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  a { color: var(--primary); text-decoration: none; transition: color .15s; }
  a:hover { color: var(--primary-dark); }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 18px;
    padding: 22px 24px; margin-bottom: 20px; backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    box-shadow: var(--shadow);
  }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 12px 10px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: top; }
  th { color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(42,120,214,0.04); }
  .table-wrap { overflow-x: auto; }
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    background: var(--grad); color: white; border: none; padding: 10px 20px;
    border-radius: 11px; cursor: pointer; font-size: 14px; font-weight: 600; font-family: inherit;
    box-shadow: 0 8px 20px -8px rgba(42,120,214,0.55); transition: transform .15s, box-shadow .15s, filter .15s;
    text-decoration: none;
  }
  .btn:hover { transform: translateY(-1px); filter: brightness(1.06); box-shadow: 0 12px 26px -8px rgba(42,120,214,0.6); color: white; }
  .btn:active { transform: translateY(0); }
  .btn-danger { background: #fff; color: var(--danger); border: 1px solid #f3c4c4; box-shadow: none; }
  .btn-danger:hover { background: #fdeeee; color: #b83231; box-shadow: none; }
  .btn-secondary { background: #fff; color: var(--text); border: 1px solid var(--border-strong); box-shadow: 0 1px 2px rgba(16,24,40,0.05); }
  .btn-secondary:hover { background: #f7f8fb; color: var(--text); box-shadow: 0 1px 2px rgba(16,24,40,0.05); }
  .btn-sm { padding: 6px 12px; font-size: 13px; border-radius: 9px; }
  .btn-lg { padding: 14px 26px; font-size: 16px; border-radius: 13px; }
  .muted { color: var(--muted); font-size: 13px; line-height: 1.55; }
  input, textarea, select {
    width: 100%; padding: 10px 12px; border: 1px solid var(--border-strong); border-radius: 10px;
    font-family: inherit; font-size: 14px; background: #fff; color: var(--text);
    transition: border-color .15s, box-shadow .15s;
  }
  input:focus, textarea:focus, select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(42,120,214,0.18); }
  input:disabled, textarea[readonly] { background: #f7f8fb; }
  textarea { resize: vertical; line-height: 1.6; }
  label { display: block; font-weight: 600; font-size: 12px; margin-bottom: 6px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .field { margin-bottom: 16px; }
  .banner { border-radius: 12px; padding: 13px 16px; margin-bottom: 18px; font-size: 14px; border: 1px solid; }
  .banner-error { background: #fdeeee; border-color: #f3c4c4; color: #9c1f1e; }
  .banner-info { background: #eef4fd; border-color: #c9dcf5; color: #1c4f8f; }
  .banner-ok { background: #e9f8f1; border-color: #bfe8d6; color: #106b45; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .badge-edited { background: #fff6dd; color: #8a6100; border: 1px solid #f3dfa4; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; background: #eef4fd; color: #1c5cab; border: 1px solid #d5e4f7; }
  .chip .sw { width: 8px; height: 8px; border-radius: 3px; }
  img { max-width: 100%; border-radius: 10px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
  .stat-tile { position: relative; overflow: hidden; background: var(--card); backdrop-filter: blur(14px); border: 1px solid var(--border); border-radius: 18px; padding: 18px 20px; box-shadow: var(--shadow); }
  .stat-tile .label { font-size: 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; }
  .stat-tile .value { font-size: 30px; font-weight: 800; letter-spacing: -0.03em; margin-top: 8px; color: var(--text); font-variant-numeric: tabular-nums; }
  .stat-tile .sub { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
  .stat-tile .ico { position: absolute; top: 16px; right: 16px; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; background: #eef4fd; font-size: 16px; }
  .row-actions { display: flex; gap: 8px; white-space: nowrap; }
  .topic-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border); }
  .topic-row:last-child { border-bottom: none; }
  .page-sub { color: var(--muted); margin: 0 0 24px; font-size: 15px; }
  @media (max-width: 760px) {
    h1 { font-size: 24px; }
    .card { padding: 18px 16px; }
  }
</style>
</head>
<body>
{% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<style>
  .hero { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 40px 16px; }
  .hero-inner { max-width: 780px; width: 100%; text-align: center; }
  .pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 500; color: var(--text-2); background: rgba(255,255,255,0.8); border: 1px solid var(--border); box-shadow: var(--shadow); margin-bottom: 26px; }
  .pill .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 0 4px rgba(27,175,122,0.18); animation: pulse 2s infinite; }
  @keyframes pulse { 50% { box-shadow: 0 0 0 7px rgba(27,175,122,0.05); } }
  .hero h1 { font-size: clamp(36px, 6vw, 62px); line-height: 1.04; font-weight: 800; letter-spacing: -0.045em; margin-bottom: 18px; }
  .grad-text { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .hero .lead { font-size: 18px; color: var(--text-2); line-height: 1.6; max-width: 590px; margin: 0 auto 32px; }
  .owner { max-width: 380px; margin: 0 auto; }
  .owner summary { list-style: none; cursor: pointer; color: var(--muted); font-size: 13px; }
  .owner summary::-webkit-details-marker { display: none; }
  .owner summary:hover { color: var(--text); }
</style>
<div class="hero">
  <div class="hero-inner">
    <div class="pill"><span class="dot"></span> Live MCP server · powered by Claude</div>
    <h1>Your AI research<br><span class="grad-text">assistant for arXiv</span></h1>
    <p class="lead">Search papers, extract key findings, discover hidden research topics with NMF, and generate cited literature reviews - all from one MCP server.</p>
    <form method="post" action="/dashboard/demo">
      <button class="btn btn-lg" type="submit">Explore the live demo &rarr;</button>
    </form>
    <details class="owner" style="margin-top: 36px;"{% if error %} open{% endif %}>
      <summary>Owner sign-in</summary>
      <form method="post" action="/dashboard/login" style="margin-top: 14px; display: flex; gap: 8px;">
        <input type="hidden" name="next" value="{{ next }}">
        <input type="password" name="token" placeholder="Access token" required>
        <button class="btn btn-secondary" type="submit">Sign in</button>
      </form>
      {% if error %}<p style="color: var(--danger); margin-top: 10px; font-size: 13px;">{{ error }}</p>{% endif %}
    </details>
  </div>
</div>
{% endblock %}
"""

SHELL_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<style>
  .layout { display: flex; min-height: 100vh; }
  .side { width: 240px; flex-shrink: 0; padding: 22px 14px; position: sticky; top: 0; height: 100vh; border-right: 1px solid var(--border); background: rgba(255,255,255,0.72); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); display: flex; flex-direction: column; }
  .brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 26px; font-weight: 800; font-size: 15px; letter-spacing: -0.01em; }
  .brand .logo { width: 32px; height: 32px; border-radius: 10px; background: var(--grad); display: grid; place-items: center; font-size: 16px; box-shadow: 0 6px 16px -6px rgba(42,120,214,0.6); }
  .nav a { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 4px; border-radius: 10px; color: var(--text-2); font-size: 14px; font-weight: 500; transition: background .15s, color .15s; }
  .nav a:hover { background: #f1f4f9; color: var(--text); }
  .nav a.active { background: #eef4fd; color: var(--primary-dark); font-weight: 600; box-shadow: inset 0 0 0 1px #d5e4f7; }
  .side-foot { margin-top: auto; padding: 14px 12px 0; border-top: 1px solid var(--border); font-size: 13px; }
  .side-foot a { color: var(--muted); }
  .main { flex: 1; min-width: 0; padding: 34px 40px; max-width: 1200px; }
  @media (max-width: 760px) {
    .layout { flex-direction: column; }
    .side { width: 100%; height: auto; flex-direction: row; align-items: center; padding: 10px 12px; border-right: none; border-bottom: 1px solid var(--border); z-index: 10; overflow-x: auto; }
    .brand { padding: 0 8px 0 0; }
    .brand span { display: none; }
    .nav { display: flex; gap: 4px; }
    .nav a { margin: 0; padding: 8px 10px; white-space: nowrap; }
    .side-foot { margin: 0 0 0 auto; padding: 0 0 0 10px; border: none; white-space: nowrap; }
    .main { padding: 22px 16px; }
  }
</style>
<div class="layout">
  <nav class="side">
    <div class="brand"><div class="logo">🎓</div><span>ArXiv Assistant</span></div>
    <div class="nav">
    {% for href, label, key, ico in [("/", "Overview", "overview", "◈"), ("/dashboard/papers", "Papers", "papers", "▤"), ("/dashboard/topics", "Topics", "topics", "◎"), ("/dashboard/review", "Review", "review", "✎")] %}
      <a href="{{ href }}" class="{{ 'active' if active == key }}"><span>{{ ico }}</span>{{ label }}</a>
    {% endfor %}
    </div>
    <div class="side-foot"><a href="/dashboard/logout">{{ "Exit demo" if is_guest else "Sign out" }}</a></div>
  </nav>
  <main class="main">
    {% if is_guest %}<div class="banner banner-info">✨ <strong>Demo mode</strong> - browse freely. Editing is off, and the AI buttons (Recompute Topics, Regenerate Review) have a small daily limit.</div>{% endif %}
    {% if error %}<div class="banner banner-error"><strong>Error:</strong> {{ error }}</div>{% endif %}
    {% if info %}<div class="banner banner-info">{{ info }}</div>{% endif %}
    {% if ok %}<div class="banner banner-ok">{{ ok }}</div>{% endif %}
    {% block page %}{% endblock %}
  </main>
</div>
{% endblock %}
"""

OVERVIEW_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<style>
  .grid-2 { display: grid; grid-template-columns: 1.6fr 1fr; gap: 20px; }
  @media (max-width: 960px) { .grid-2 { grid-template-columns: 1fr; } }
  .grid-2 > .card { margin-bottom: 0; }
  .chart-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
  .seg { display: inline-flex; background: #f1f4f9; border: 1px solid var(--border); border-radius: 10px; padding: 3px; }
  .seg button { border: none; background: transparent; padding: 6px 12px; border-radius: 8px; font: inherit; font-size: 13px; font-weight: 600; color: var(--muted); cursor: pointer; transition: background .15s, color .15s; }
  .seg button[aria-pressed="true"] { background: #fff; color: var(--text); box-shadow: 0 1px 3px rgba(16,24,40,0.12); }
  .chart-box { position: relative; height: 300px; }
  .chart-box.tall { height: 340px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 12px; }
  .legend button { display: inline-flex; align-items: center; gap: 7px; border: none; background: none; padding: 2px 0; font: inherit; font-size: 12.5px; color: var(--text-2); cursor: pointer; }
  .legend button .sw { width: 10px; height: 10px; border-radius: 3px; }
  .legend button[aria-pressed="false"] { opacity: .4; }
  .table-view { margin-top: 12px; }
  .table-view summary { cursor: pointer; font-size: 12.5px; color: var(--muted); }
  .table-view table td, .table-view table th { padding: 6px 8px; font-size: 12.5px; }
  .empty { display: grid; place-items: center; height: 100%; color: var(--muted); font-size: 14px; text-align: center; }
</style>

<h1>Overview</h1>
<p class="page-sub">A live snapshot of the research bibliography.</p>

<div class="stat-grid" style="margin: 0 0 20px;">
  <div class="stat-tile"><div class="ico">📄</div><div class="label">Papers</div><div class="value">{{ paper_count }}</div><div class="sub">saved to the bibliography</div></div>
  <div class="stat-tile"><div class="ico">🧭</div><div class="label">Topics</div><div class="value">{{ topic_count }}</div><div class="sub">discovered with NMF</div></div>
  <div class="stat-tile"><div class="ico">👥</div><div class="label">Authors</div><div class="value">{{ author_count }}</div><div class="sub">unique researchers</div></div>
  <div class="stat-tile"><div class="ico">📅</div><div class="label">Year span</div><div class="value" style="font-size: 24px;">{{ year_span }}</div><div class="sub">publication range</div></div>
  <div class="stat-tile"><div class="ico">📝</div><div class="label">Review</div><div class="value" style="font-size: 20px;">{{ review_status }}</div><div class="sub">last generated</div></div>
</div>

<div class="grid-2" style="margin-bottom: 20px;">
  <div class="card">
    <div class="chart-head">
      <div><h3>Research topics over time</h3><div class="muted">Papers per year, stacked by topic. Click a legend item to hide it.</div></div>
      <div class="seg" role="group" aria-label="Chart type">
        <button type="button" data-trend-mode="bar" aria-pressed="true">Stacked</button>
        <button type="button" data-trend-mode="line" aria-pressed="false">Lines</button>
      </div>
    </div>
    <div class="chart-box tall"><canvas id="trendsChart" aria-label="Research topics over time"></canvas></div>
    <div class="legend" id="trendsLegend"></div>
    <details class="table-view"><summary>Show as table</summary><div class="table-wrap" id="trendsTable"></div></details>
  </div>
  <div class="card">
    <div class="chart-head"><div><h3>Topic share</h3><div class="muted">Papers assigned to each topic</div></div></div>
    <div class="chart-box tall"><canvas id="shareChart" aria-label="Topic share"></canvas></div>
    <details class="table-view"><summary>Show as table</summary><div class="table-wrap" id="shareTable"></div></details>
  </div>
</div>

<div class="card">
  <div class="chart-head">
    <div><h3>Top keywords</h3><div class="muted">Most frequent terms in the extracted findings</div></div>
    <div class="seg" role="group" aria-label="Keyword source">
      <button type="button" data-kw="method" aria-pressed="true">Methods</button>
      <button type="button" data-kw="problem" aria-pressed="false">Problems</button>
    </div>
  </div>
  <div class="chart-box"><canvas id="kwChart" aria-label="Top keywords"></canvas></div>
  <details class="table-view"><summary>Show as table</summary><div class="table-wrap" id="kwTable"></div></details>
</div>

<div class="card">
  <h3 style="margin-bottom: 10px;">Recently saved</h3>
  {% if recent_papers %}
  <div class="table-wrap"><table>
    <tr><th>Title</th><th>Published</th><th>Topic</th></tr>
    {% for p in recent_papers %}
    <tr>
      <td><a href="/dashboard/papers/{{ p.id }}/edit">{{ p.title }}</a></td>
      <td style="white-space: nowrap;">{{ p.published or "—" }}</td>
      <td>{% if p.topic_label %}<span class="chip">{{ p.topic_label }}</span>{% else %}—{% endif %}</td>
    </tr>
    {% endfor %}
  </table></div>
  {% else %}
  <p class="muted">No papers saved yet. Ask your assistant to search ArXiv and save some.</p>
  {% endif %}
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
(function () {
  // Categorical slots in fixed order (validated light palette); "Other" is neutral gray.
  var PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
  var OTHER = "#898781";
  var INK = "#0e1120", INK2 = "#3d4255", MUTED = "#6b7185", GRID = "rgba(14,17,32,0.06)";

  if (!window.Chart) return;
  Chart.defaults.font.family = "Inter, -apple-system, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = MUTED;

  var tooltip = {
    backgroundColor: "#ffffff", titleColor: INK, bodyColor: INK2, borderColor: "#e4e7ef", borderWidth: 1,
    padding: 12, cornerRadius: 10, boxPadding: 5, usePointStyle: true,
    titleFont: { weight: "700" }, bodyFont: { size: 12.5 },
  };

  function el(tag, text) { var e = document.createElement(tag); if (text != null) e.textContent = text; return e; }
  function table(target, head, rows) {
    var t = el("table"), tr = el("tr");
    head.forEach(function (h) { tr.appendChild(el("th", h)); });
    t.appendChild(tr);
    rows.forEach(function (r) { var row = el("tr"); r.forEach(function (c) { row.appendChild(el("td", c)); }); t.appendChild(row); });
    document.getElementById(target).replaceChildren(t);
  }
  function empty(canvasId, msg) {
    var box = document.getElementById(canvasId).parentNode;
    box.replaceChildren(el("div", msg)); box.firstChild.className = "empty";
  }

  fetch("/dashboard/api/charts.json", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(render)
    .catch(function () { ["trendsChart", "shareChart", "kwChart"].forEach(function (id) { empty(id, "Couldn't load chart data."); }); });

  function render(data) {
    // Color follows the topic, so the same topic is the same color in every chart.
    var topicColor = {};
    (data.trends.topics || []).forEach(function (t, i) { topicColor[t.topic_label] = t.topic_label === "Other" ? OTHER : PALETTE[i % PALETTE.length]; });
    (data.topic_share || []).forEach(function (t) { if (!topicColor[t.label]) topicColor[t.label] = PALETTE[Object.keys(topicColor).length % PALETTE.length]; });

    // --- Topics over time ---
    var trendsChart = null, mode = "bar";
    function trendDatasets() {
      return data.trends.topics.map(function (t) {
        var c = topicColor[t.topic_label];
        return mode === "bar"
          ? { label: t.topic_label, data: t.counts_by_year, backgroundColor: c, borderColor: "#ffffff", borderWidth: 2, borderRadius: 4, borderSkipped: false, maxBarThickness: 46 }
          : { label: t.topic_label, data: t.counts_by_year, borderColor: c, backgroundColor: c, borderWidth: 2, tension: 0.35, pointRadius: 4, pointHoverRadius: 6, pointBorderColor: "#fff", pointBorderWidth: 2 };
      });
    }
    function drawTrends() {
      if (trendsChart) trendsChart.destroy();
      trendsChart = new Chart(document.getElementById("trendsChart"), {
        type: mode,
        data: { labels: data.trends.years, datasets: trendDatasets() },
        options: {
          maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
          plugins: { legend: { display: false }, tooltip: Object.assign({}, tooltip, {
            itemSort: function (a, b) { return b.raw - a.raw; },
            callbacks: { label: function (c) { return " " + c.raw + " · " + c.dataset.label; } } }) },
          scales: {
            x: { stacked: mode === "bar", grid: { display: false }, border: { color: "#d3d8e3" } },
            y: { stacked: mode === "bar", beginAtZero: true, ticks: { precision: 0 }, grid: { color: GRID }, border: { display: false },
                 title: { display: true, text: "Papers", color: MUTED } },
          },
        },
      });
      var legend = document.getElementById("trendsLegend");
      legend.replaceChildren();
      trendsChart.data.datasets.forEach(function (ds, i) {
        var b = el("button"), sw = el("span"); sw.className = "sw"; sw.style.background = ds.borderColor === "#ffffff" ? ds.backgroundColor : ds.borderColor;
        b.type = "button"; b.setAttribute("aria-pressed", "true"); b.appendChild(sw); b.appendChild(document.createTextNode(ds.label));
        b.onclick = function () { var vis = trendsChart.isDatasetVisible(i); trendsChart.setDatasetVisibility(i, !vis); trendsChart.update(); b.setAttribute("aria-pressed", String(!vis)); };
        legend.appendChild(b);
      });
    }
    if (data.trends.error || !data.trends.years.length) { empty("trendsChart", data.trends.error || "No dated papers yet."); }
    else {
      drawTrends();
      table("trendsTable", ["Topic"].concat(data.trends.years), data.trends.topics.map(function (t) { return [t.topic_label].concat(t.counts_by_year); }));
      document.querySelectorAll("[data-trend-mode]").forEach(function (b) {
        b.onclick = function () {
          mode = b.dataset.trendMode;
          document.querySelectorAll("[data-trend-mode]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          drawTrends();
        };
      });
    }

    // --- Topic share ---
    var share = data.topic_share || [];
    if (!share.length) { empty("shareChart", "No topics yet. Recompute topics to discover them."); }
    else {
      var total = share.reduce(function (a, t) { return a + t.count; }, 0);
      new Chart(document.getElementById("shareChart"), {
        type: "bar",
        data: { labels: share.map(function (t) { return t.label; }),
                datasets: [{ data: share.map(function (t) { return t.count; }), backgroundColor: share.map(function (t) { return topicColor[t.label]; }),
                             borderRadius: 4, borderSkipped: "start", maxBarThickness: 22 }] },
        options: {
          indexAxis: "y", maintainAspectRatio: false, layout: { padding: { left: 6 } },
          plugins: { legend: { display: false }, tooltip: Object.assign({}, tooltip, { callbacks: {
            label: function (c) { return " " + c.raw + " papers · " + Math.round(c.raw / total * 100) + "%"; } } }) },
          scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: GRID }, border: { display: false } },
                    y: { grid: { display: false }, border: { display: false }, ticks: { color: INK2,
                         callback: function (v) { var l = this.getLabelForValue(v); return l.length > 18 ? l.slice(0, 17) + "…" : l; } } } },
        },
      });
      table("shareTable", ["Topic", "Papers", "Share"], share.map(function (t) { return [t.label, t.count, Math.round(t.count / total * 100) + "%"]; }));
    }

    // --- Keywords ---
    var kwChart = null;
    function drawKw(kind) {
      var rows = (data.keywords[kind] || []);
      if (kwChart) kwChart.destroy();
      kwChart = new Chart(document.getElementById("kwChart"), {
        type: "bar",
        data: { labels: rows.map(function (r) { return r[0]; }),
                datasets: [{ label: kind === "method" ? "Method mentions" : "Problem mentions", data: rows.map(function (r) { return r[1]; }),
                             backgroundColor: kind === "method" ? PALETTE[0] : PALETTE[6], hoverBackgroundColor: kind === "method" ? "#1c5cab" : "#4a3aa7",
                             borderRadius: 4, borderSkipped: "start", maxBarThickness: 40 }] },
        options: {
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: Object.assign({}, tooltip, { callbacks: { label: function (c) { return " " + c.raw + " mentions"; } } }) },
          scales: { x: { grid: { display: false }, border: { color: "#d3d8e3" }, ticks: { color: INK2 } },
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: GRID }, border: { display: false } } },
        },
      });
      table("kwTable", ["Keyword", "Mentions"], rows);
    }
    if (data.keywords.error) { empty("kwChart", data.keywords.error); }
    else {
      drawKw("method");
      document.querySelectorAll("[data-kw]").forEach(function (b) {
        b.onclick = function () {
          document.querySelectorAll("[data-kw]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          drawKw(b.dataset.kw);
        };
      });
    }
  }
})();
</script>
{% endblock %}
"""

PAPERS_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<h1>Papers <span class="chip" style="vertical-align: middle; font-size: 14px;">{{ papers|length }}</span></h1>

<div class="card">
  <form method="get" action="/dashboard/papers" style="display: flex; gap: 10px; margin-bottom: 4px;">
    <input type="text" name="q" placeholder="Search title, authors, problem, method, result..." value="{{ q }}" style="flex: 1;">
    <select name="sort" style="width: 180px;">
      {% for value, label in [("id", "Newest first"), ("title", "Title A-Z"), ("published", "Published date"), ("topic", "Topic")] %}
      <option value="{{ value }}" {{ "selected" if sort == value }}>{{ label }}</option>
      {% endfor %}
    </select>
    <button class="btn" type="submit">Filter</button>
  </form>
</div>

<div class="card">
  {% if papers %}
  <div class="table-wrap"><table>
    <tr><th>Title</th><th>Authors</th><th>Published</th><th>Topic</th><th>Problem</th><th></th></tr>
    {% for p in papers %}
    <tr>
      <td><a href="/dashboard/papers/{{ p.id }}/edit">{{ p.title }}</a></td>
      <td>{{ p.authors|join(", ") }}</td>
      <td>{{ p.published or "—" }}</td>
      <td>{% if p.topic_label %}<span class="chip">{{ p.topic_label }}</span>{% else %}—{% endif %}</td>
      <td class="muted">{{ (p.problem or "—")[:100] }}{{ "…" if p.problem and p.problem|length > 100 }}</td>
      <td class="row-actions">
        <a href="/dashboard/papers/{{ p.id }}/edit" class="btn btn-secondary btn-sm">{{ "View" if is_guest else "Edit" }}</a>
        {% if not is_guest %}<form method="post" action="/dashboard/papers/{{ p.id }}/delete" onsubmit="return confirm('Delete this paper?')" style="display:inline;">
          <button class="btn btn-danger btn-sm" type="submit">Delete</button>
        </form>{% endif %}
      </td>
    </tr>
    {% endfor %}
  </table></div>
  {% else %}
  <p class="muted">{{ "No papers match your search." if q else "No papers saved yet." }}</p>
  {% endif %}
</div>
{% endblock %}
"""

PAPER_EDIT_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<p><a href="/dashboard/papers">← Back to Papers</a></p>
<h1>{{ "Paper" if is_guest else "Edit Paper" }}</h1>

<form method="post" action="/dashboard/papers/{{ paper.id }}/edit">
  <div class="card">
    <div class="field"><label>Title</label><input type="text" name="title" value="{{ paper.title }}" required></div>
    <div class="field"><label>Authors (one per line)</label><textarea name="authors" rows="3">{{ paper.authors|join("\\n") }}</textarea></div>
    <div class="field"><label>Published</label><input type="date" name="published" value="{{ paper.published or '' }}"></div>
    <div class="field"><label>Topic</label><input type="text" value="{{ paper.topic_label or 'Not yet computed' }}" disabled></div>
    <p class="muted">To rename this paper's topic, do it from the <a href="/dashboard/topics">Topics</a> page - it applies to every paper sharing the topic.</p>
  </div>
  <div class="card">
    <div class="field"><label>Problem</label><textarea name="problem" rows="4">{{ paper.problem or "" }}</textarea></div>
    <div class="field"><label>Method</label><textarea name="method" rows="4">{{ paper.method or "" }}</textarea></div>
    <div class="field"><label>Result</label><textarea name="result" rows="4">{{ paper.result or "" }}</textarea></div>
  </div>
  {% if not is_guest %}<button class="btn" type="submit">Save Changes</button>{% endif %}
</form>

{% if not is_guest %}
<form method="post" action="/dashboard/papers/{{ paper.id }}/delete" onsubmit="return confirm('Delete this paper permanently?')" style="margin-top: 14px;">
  <button class="btn btn-danger" type="submit">Delete This Paper</button>
</form>
{% endif %}
{% endblock %}
"""

TOPICS_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<h1>Topics</h1>
<p class="page-sub">Discovered by NMF topic modeling over the bibliography, then labeled by Claude.</p>

<div class="card">
  {% if topics %}
  {% for t in topics %}
  <div class="topic-row">
    <div style="flex: 1;">
      <form method="post" action="/dashboard/topics/{{ t.topic_id }}/rename" style="display: flex; gap: 8px; align-items: center;">
        <input type="text" name="label" value="{{ t.topic_label }}" style="max-width: 320px;"{{ " disabled" if is_guest }}>
        {% if not is_guest %}<button class="btn btn-secondary btn-sm" type="submit">Rename</button>{% endif %}
      </form>
      <div class="muted" style="margin-top: 4px;">{{ t.topic_keywords }}</div>
    </div>
    <div class="muted" style="white-space: nowrap;">{{ t.count }} paper{{ "s" if t.count != 1 }}</div>
  </div>
  {% endfor %}
  {% else %}
  <p class="muted">No topics computed yet.</p>
  {% endif %}
</div>

<form method="post" action="/dashboard/topics/recompute">
  <button class="btn" type="submit">Recompute Topics</button>
</form>
{% endblock %}
"""

REVIEW_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<h1>Literature Review</h1>

{% if review %}
<p class="muted">
  {% if review.edited %}<span class="badge badge-edited">Manually edited</span>{% endif %}
  Generated {{ review.generated_at or "—" }} from {{ review.paper_count }} papers.
  {% if review.edited_at %}Last edited {{ review.edited_at }}.{% endif %}
</p>
{% endif %}

<form method="post" action="/dashboard/review/save">
  <div class="card">
    <textarea name="content" rows="24" style="font-family: JetBrains Mono, ui-monospace, monospace; font-size: 13px;"{{ " readonly" if is_guest }}>{{ review.content if review else "" }}</textarea>
  </div>
  {% if not is_guest %}<button class="btn" type="submit">Save Edits</button>{% endif %}
</form>

<form method="post" action="/dashboard/review/regenerate" onsubmit="{{ 'return confirm(\\'This will discard your manual edits. Continue?\\')' if review and review.edited else '' }}" style="margin-top: 14px;">
  <button class="btn btn-secondary" type="submit">{{ "Regenerate" if review else "Generate" }} Review</button>
</form>
{% endblock %}
"""

env = Environment(
    loader=DictLoader({
        "base.html": BASE_TEMPLATE,
        "login.html": LOGIN_TEMPLATE,
        "shell.html": SHELL_TEMPLATE,
        "overview.html": OVERVIEW_TEMPLATE,
        "papers.html": PAPERS_TEMPLATE,
        "paper_edit.html": PAPER_EDIT_TEMPLATE,
        "topics.html": TOPICS_TEMPLATE,
        "review.html": REVIEW_TEMPLATE,
    }),
    autoescape=select_autoescape(["html"]),
)
