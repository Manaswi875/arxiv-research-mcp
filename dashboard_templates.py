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
<html>
<head>
<title>{% block title %}ArXiv Research Assistant{% endblock %}</title>
<style>
  :root {
    --primary: #2a78d6; --primary-dark: #1d5aa8; --danger: #e34948;
    --bg: #f6f5f1; --card: #ffffff; --border: #e1e0d9; --text: #0b0b0b; --muted: #6b6a63;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    margin: 0; color: var(--text); background: var(--bg);
  }
  h1, h2, h3 { color: var(--text); margin-top: 0; }
  a { color: var(--primary); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 22px 26px; margin-bottom: 22px; box-shadow: 0 1px 3px rgb(0 0 0 / 0.04);
  }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: top; }
  th { color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.03em; }
  tr:hover td { background: #fafaf8; }
  .btn {
    background: var(--primary); color: white; border: none; padding: 9px 18px;
    border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; font-family: inherit;
  }
  .btn:hover { background: var(--primary-dark); }
  .btn-danger { background: var(--danger); }
  .btn-danger:hover { background: #b83231; }
  .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
  .btn-secondary:hover { background: #f2f1ec; }
  .btn-sm { padding: 5px 12px; font-size: 13px; }
  .muted { color: var(--muted); font-size: 13px; }
  input, textarea, select {
    width: 100%; padding: 9px 10px; border: 1px solid var(--border); border-radius: 7px;
    box-sizing: border-box; font-family: inherit; font-size: 14px; background: white; color: var(--text);
  }
  textarea { resize: vertical; }
  label { display: block; font-weight: 600; font-size: 13px; margin-bottom: 5px; color: var(--muted); }
  .field { margin-bottom: 16px; }
  .banner { border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; font-size: 14px; }
  .banner-error { background: #fdeceb; border-left: 4px solid var(--danger); color: #9c1f1e; }
  .banner-ok { background: #e9f7ef; border-left: 4px solid #1baf7a; color: #106b45; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .badge-edited { background: #fff3d6; color: #8a6100; }
  img { max-width: 100%; border-radius: 8px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
  .stat-tile { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; text-align: center; }
  .stat-tile .value { font-size: 28px; font-weight: 700; color: var(--primary); }
  .stat-tile .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 4px; }
  .row-actions { display: flex; gap: 8px; white-space: nowrap; }
  .topic-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
  .topic-row:last-child { border-bottom: none; }
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
<div style="display: flex; align-items: center; justify-content: center; min-height: 100vh;">
  <div class="card" style="max-width: 400px; width: 100%;">
    <h2>🎓 ArXiv Research Assistant</h2>
    <p class="muted">Enter the access token to view the dashboard.</p>
    <form method="post" action="/dashboard/login">
      <input type="hidden" name="next" value="{{ next }}">
      <div class="field">
        <input type="password" name="token" placeholder="Access token" required autofocus>
      </div>
      <button class="btn" style="width: 100%;" type="submit">Sign in</button>
    </form>
    {% if error %}<p style="color: #dc2626; margin-top: 12px;">{{ error }}</p>{% endif %}
  </div>
</div>
{% endblock %}
"""

SHELL_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div style="display: flex; min-height: 100vh;">
  <nav style="width: 220px; flex-shrink: 0; background: #1a1a1a; color: #d8d6cd; padding: 24px 0; position: sticky; top: 0; height: 100vh;">
    <div style="padding: 0 20px 20px; font-weight: 700; font-size: 16px; color: white;">🎓 ArXiv Assistant</div>
    {% for href, label, key in [("/", "Overview", "overview"), ("/dashboard/papers", "Papers", "papers"), ("/dashboard/topics", "Topics", "topics"), ("/dashboard/review", "Review", "review")] %}
    <a href="{{ href }}" style="display: block; padding: 11px 20px; color: {{ '#fff' if active == key else '#b3b1a6' }}; background: {{ 'rgba(255,255,255,0.08)' if active == key else 'transparent' }}; border-left: 3px solid {{ '#2a78d6' if active == key else 'transparent' }}; font-weight: {{ '600' if active == key else '400' }}; text-decoration: none;">{{ label }}</a>
    {% endfor %}
    <div style="padding: 20px; margin-top: 20px; border-top: 1px solid #333;">
      <a href="/dashboard/logout" style="color: #b3b1a6;">Sign out</a>
    </div>
  </nav>
  <main style="flex: 1; padding: 32px 40px; max-width: 1100px;">
    {% if error %}<div class="banner banner-error"><strong>Error:</strong> {{ error }}</div>{% endif %}
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
<p class="muted">A snapshot of your ArXiv research bibliography.</p>

<div class="stat-grid" style="margin: 24px 0;">
  <div class="stat-tile"><div class="value">{{ paper_count }}</div><div class="label">Papers Saved</div></div>
  <div class="stat-tile"><div class="value">{{ topic_count }}</div><div class="label">Topics Discovered</div></div>
  <div class="stat-tile"><div class="value">{{ review_status }}</div><div class="label">Literature Review</div></div>
</div>

<div class="card">
  <h3>Method Keyword Trends</h3>
  <img src="/dashboard/api/keyword-chart.png" alt="Method keyword chart">
</div>

<div class="card">
  <h3>Research Topics Over Time</h3>
  <img src="/dashboard/api/trends-chart.png" alt="Research trends chart">
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
      <td>{{ p.topic_label or "—" }}</td>
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
<h1>Papers ({{ papers|length }})</h1>

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
  <table>
    <tr><th>Title</th><th>Authors</th><th>Published</th><th>Topic</th><th>Problem</th><th></th></tr>
    {% for p in papers %}
    <tr>
      <td><a href="/dashboard/papers/{{ p.id }}/edit">{{ p.title }}</a></td>
      <td>{{ p.authors|join(", ") }}</td>
      <td>{{ p.published or "—" }}</td>
      <td>{{ p.topic_label or "—" }}</td>
      <td class="muted">{{ (p.problem or "—")[:100] }}{{ "…" if p.problem and p.problem|length > 100 }}</td>
      <td class="row-actions">
        <a href="/dashboard/papers/{{ p.id }}/edit" class="btn btn-secondary btn-sm">Edit</a>
        <form method="post" action="/dashboard/papers/{{ p.id }}/delete" onsubmit="return confirm('Delete this paper?')" style="display:inline;">
          <button class="btn btn-danger btn-sm" type="submit">Delete</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
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
<h1>Edit Paper</h1>

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
  <button class="btn" type="submit">Save Changes</button>
</form>

<form method="post" action="/dashboard/papers/{{ paper.id }}/delete" onsubmit="return confirm('Delete this paper permanently?')" style="margin-top: 14px;">
  <button class="btn btn-danger" type="submit">Delete This Paper</button>
</form>
{% endblock %}
"""

TOPICS_TEMPLATE = """
{% extends "shell.html" %}
{% block page %}
<h1>Topics</h1>
<p class="muted">Discovered by NMF topic modeling over your bibliography, then labeled by Claude.</p>

<div class="card">
  {% if topics %}
  {% for t in topics %}
  <div class="topic-row">
    <div style="flex: 1;">
      <form method="post" action="/dashboard/topics/{{ t.topic_id }}/rename" style="display: flex; gap: 8px; align-items: center;">
        <input type="text" name="label" value="{{ t.topic_label }}" style="max-width: 320px;">
        <button class="btn btn-secondary btn-sm" type="submit">Rename</button>
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
    <textarea name="content" rows="24" style="font-family: ui-monospace, monospace; font-size: 13px;">{{ review.content if review else "" }}</textarea>
  </div>
  <button class="btn" type="submit">Save Edits</button>
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
