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
    --bg: #07080d; --bg-2: #0d0f17; --card: rgba(255,255,255,0.035); --card-hover: rgba(255,255,255,0.06);
    --border: rgba(255,255,255,0.08); --border-strong: rgba(255,255,255,0.16);
    --text: #eef0f6; --muted: #8b90a3; --primary: #7c5cff; --primary-2: #22d3ee;
    --danger: #ff5c7a; --ok: #34d399; --warn: #fbbf24;
    --grad: linear-gradient(135deg, #7c5cff 0%, #22d3ee 100%);
  }
  * { box-sizing: border-box; }
  html { -webkit-font-smoothing: antialiased; }
  body {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0; color: var(--text); background: var(--bg); min-height: 100vh;
    background-image:
      radial-gradient(900px 500px at 10% -10%, rgba(124,92,255,0.18), transparent 60%),
      radial-gradient(700px 400px at 100% 0%, rgba(34,211,238,0.10), transparent 60%);
    background-attachment: fixed;
  }
  h1, h2, h3 { color: var(--text); margin-top: 0; letter-spacing: -0.02em; }
  h1 { font-size: 30px; font-weight: 800; margin-bottom: 6px; }
  h3 { font-size: 16px; font-weight: 600; }
  a { color: #a99bff; text-decoration: none; transition: color .15s; }
  a:hover { color: #c9c0ff; }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 16px;
    padding: 22px 24px; margin-bottom: 20px; backdrop-filter: blur(12px);
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 40px -24px rgba(0,0,0,0.6);
  }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 12px 10px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: top; }
  th { color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; }
  tr:last-child td { border-bottom: none; }
  tbody tr, table tr { transition: background .15s; }
  tr:hover td { background: rgba(255,255,255,0.025); }
  .table-wrap { overflow-x: auto; }
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    background: var(--grad); color: white; border: none; padding: 10px 20px;
    border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600; font-family: inherit;
    box-shadow: 0 8px 24px -8px rgba(124,92,255,0.6); transition: transform .15s, box-shadow .15s, filter .15s;
    text-decoration: none;
  }
  .btn:hover { transform: translateY(-1px); filter: brightness(1.08); box-shadow: 0 12px 30px -8px rgba(124,92,255,0.75); color: white; }
  .btn:active { transform: translateY(0); }
  .btn-danger { background: rgba(255,92,122,0.12); color: var(--danger); border: 1px solid rgba(255,92,122,0.3); box-shadow: none; }
  .btn-danger:hover { background: rgba(255,92,122,0.2); color: #ff8299; box-shadow: none; }
  .btn-secondary { background: rgba(255,255,255,0.05); color: var(--text); border: 1px solid var(--border-strong); box-shadow: none; }
  .btn-secondary:hover { background: rgba(255,255,255,0.1); color: var(--text); box-shadow: none; }
  .btn-sm { padding: 6px 12px; font-size: 13px; border-radius: 8px; }
  .btn-lg { padding: 14px 26px; font-size: 16px; border-radius: 12px; }
  .muted { color: var(--muted); font-size: 13px; line-height: 1.55; }
  input, textarea, select {
    width: 100%; padding: 10px 12px; border: 1px solid var(--border-strong); border-radius: 10px;
    font-family: inherit; font-size: 14px; background: rgba(0,0,0,0.3); color: var(--text);
    transition: border-color .15s, box-shadow .15s;
  }
  input:focus, textarea:focus, select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(124,92,255,0.25); }
  input:disabled { opacity: .6; }
  select option { background: var(--bg-2); }
  textarea { resize: vertical; line-height: 1.6; }
  label { display: block; font-weight: 600; font-size: 12px; margin-bottom: 6px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .field { margin-bottom: 16px; }
  .banner { border-radius: 12px; padding: 13px 16px; margin-bottom: 18px; font-size: 14px; border: 1px solid; backdrop-filter: blur(8px); }
  .banner-error { background: rgba(255,92,122,0.08); border-color: rgba(255,92,122,0.3); color: #ffb3c1; }
  .banner-info { background: rgba(124,92,255,0.08); border-color: rgba(124,92,255,0.3); color: #cfc6ff; }
  .banner-ok { background: rgba(52,211,153,0.08); border-color: rgba(52,211,153,0.3); color: #a7f3d0; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .badge-edited { background: rgba(251,191,36,0.12); color: var(--warn); border: 1px solid rgba(251,191,36,0.3); }
  .chip { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; background: rgba(124,92,255,0.12); color: #c4b8ff; border: 1px solid rgba(124,92,255,0.25); }
  img { max-width: 100%; border-radius: 10px; }
  .chart { background: #ffffff; border-radius: 12px; padding: 10px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
  .stat-tile { position: relative; overflow: hidden; background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 22px; }
  .stat-tile::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 2px; background: var(--grad); opacity: .8; }
  .stat-tile .value { font-size: 32px; font-weight: 800; letter-spacing: -0.03em; background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .stat-tile .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }
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
  .hero-inner { max-width: 760px; width: 100%; text-align: center; }
  .pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: 13px; color: #cfc6ff; background: rgba(124,92,255,0.1); border: 1px solid rgba(124,92,255,0.3); margin-bottom: 26px; }
  .pill .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 10px var(--ok); animation: pulse 2s infinite; }
  @keyframes pulse { 50% { opacity: .4; } }
  .hero h1 { font-size: clamp(36px, 6vw, 60px); line-height: 1.05; font-weight: 800; letter-spacing: -0.04em; margin-bottom: 18px; }
  .grad-text { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .hero .lead { font-size: 18px; color: var(--muted); line-height: 1.6; max-width: 580px; margin: 0 auto 34px; }
  .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 48px 0 36px; text-align: left; }
  .feature { padding: 16px; border-radius: 14px; background: var(--card); border: 1px solid var(--border); transition: border-color .2s, transform .2s; }
  .feature:hover { border-color: rgba(124,92,255,0.4); transform: translateY(-2px); }
  .feature .ico { font-size: 20px; margin-bottom: 8px; }
  .feature .t { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
  .feature .d { font-size: 12.5px; color: var(--muted); line-height: 1.5; }
  .owner { max-width: 360px; margin: 0 auto; }
  .owner summary { list-style: none; cursor: pointer; color: var(--muted); font-size: 13px; }
  .owner summary::-webkit-details-marker { display: none; }
  .owner summary:hover { color: var(--text); }
  .stack { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 18px; }
</style>
<div class="hero">
  <div class="hero-inner">
    <div class="pill"><span class="dot"></span> Live MCP server · powered by Claude</div>
    <h1>Your AI research<br><span class="grad-text">assistant for arXiv</span></h1>
    <p class="lead">Search papers, extract key findings, discover hidden research topics with NMF, and generate cited literature reviews - all from one MCP server.</p>
    <form method="post" action="/dashboard/demo">
      <button class="btn btn-lg" type="submit">Explore the live demo &rarr;</button>
    </form>
    <div class="stack">
      <span class="chip">Python</span><span class="chip">MCP</span><span class="chip">Claude API</span><span class="chip">Postgres</span><span class="chip">scikit-learn</span><span class="chip">Vercel</span>
    </div>
    <div class="features">
      <div class="feature"><div class="ico">🔎</div><div class="t">arXiv search</div><div class="d">Query papers by topic, straight from your AI client.</div></div>
      <div class="feature"><div class="ico">🧠</div><div class="t">Key findings</div><div class="d">Problem, method, and result extracted by Claude.</div></div>
      <div class="feature"><div class="ico">🧭</div><div class="t">Topic discovery</div><div class="d">NMF topic modeling with AI-written labels.</div></div>
      <div class="feature"><div class="ico">📝</div><div class="t">Literature review</div><div class="d">A cited narrative synthesis of your bibliography.</div></div>
    </div>
    <details class="owner"{% if error %} open{% endif %}>
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
  .side { width: 240px; flex-shrink: 0; padding: 22px 14px; position: sticky; top: 0; height: 100vh; border-right: 1px solid var(--border); background: rgba(7,8,13,0.6); backdrop-filter: blur(16px); display: flex; flex-direction: column; }
  .brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 26px; font-weight: 700; font-size: 15px; }
  .brand .logo { width: 30px; height: 30px; border-radius: 9px; background: var(--grad); display: grid; place-items: center; font-size: 16px; box-shadow: 0 6px 18px -6px rgba(124,92,255,0.7); }
  .nav a { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 4px; border-radius: 10px; color: var(--muted); font-size: 14px; font-weight: 500; transition: background .15s, color .15s; }
  .nav a:hover { background: rgba(255,255,255,0.05); color: var(--text); }
  .nav a.active { background: rgba(124,92,255,0.14); color: #fff; box-shadow: inset 0 0 0 1px rgba(124,92,255,0.3); }
  .side-foot { margin-top: auto; padding: 14px 12px 0; border-top: 1px solid var(--border); font-size: 13px; }
  .side-foot a { color: var(--muted); }
  .main { flex: 1; min-width: 0; padding: 36px 44px; max-width: 1140px; }
  @media (max-width: 760px) {
    .layout { flex-direction: column; }
    .side { width: 100%; height: auto; position: sticky; flex-direction: row; align-items: center; padding: 10px 12px; border-right: none; border-bottom: 1px solid var(--border); z-index: 10; overflow-x: auto; }
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
<h1>Overview</h1>
<p class="page-sub">A snapshot of the research bibliography.</p>

<div class="stat-grid" style="margin: 24px 0;">
  <div class="stat-tile"><div class="value">{{ paper_count }}</div><div class="label">Papers Saved</div></div>
  <div class="stat-tile"><div class="value">{{ topic_count }}</div><div class="label">Topics Discovered</div></div>
  <div class="stat-tile"><div class="value">{{ review_status }}</div><div class="label">Literature Review</div></div>
</div>

<div class="card">
  <h3>Method Keyword Trends</h3>
  <img class="chart" src="/dashboard/api/keyword-chart.png" alt="Method keyword chart">
</div>

<div class="card">
  <h3>Research Topics Over Time</h3>
  <img class="chart" src="/dashboard/api/trends-chart.png" alt="Research trends chart">
</div>

<div class="card">
  <h3>Recently Saved</h3>
  {% if recent_papers %}
  <table>
    <tr><th>Title</th><th>Published</th><th>Topic</th></tr>
    {% for p in recent_papers %}
    <tr>
      <td><a href="/dashboard/papers/{{ p.id }}/edit">{{ p.title }}</a></td>
      <td>{{ p.published or "—" }}</td>
      <td>{% if p.topic_label %}<span class="chip">{{ p.topic_label }}</span>{% else %}—{% endif %}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <p class="muted">No papers saved yet. Ask your assistant to search ArXiv and save some.</p>
  {% endif %}
</div>
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
