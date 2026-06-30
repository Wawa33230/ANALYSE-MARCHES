"""Generation du tableau de bord HTML autonome (un seul fichier, ouvrable hors-ligne).

Le fichier produit contient les donnees + le style + une petite logique JavaScript
pour la recherche, le tri par colonne et les filtres (Prioritaires / Cette semaine...).
Aucune connexion internet n'est requise pour le consulter.
"""

from __future__ import annotations

import datetime
import json
import os

CATEGORY_LABEL = {
    "prioritaire": "Cible prioritaire",
    "a_regarder": "A regarder",
    "hors_cible": "Hors cible",
}


def _stats(tenders: list) -> dict:
    prio = sum(1 for t in tenders if t.category == "prioritaire")
    look = sum(1 for t in tenders if t.category == "a_regarder")
    urgent = sum(1 for t in tenders if t.days_left is not None and 0 <= t.days_left <= 7)
    return {"total": len(tenders), "prio": prio, "look": look, "urgent": urgent}


def render(tenders: list, output_path: str) -> str:
    tenders = sorted(
        tenders,
        key=lambda t: (-t.score, t.days_left if t.days_left is not None else 9999),
    )
    rows = [t.to_dict() for t in tenders]
    stats = _stats(tenders)
    generated = datetime.datetime.now().strftime("%d/%m/%Y a %H:%M")

    html = _TEMPLATE.format(
        data=json.dumps(rows, ensure_ascii=False),
        labels=json.dumps(CATEGORY_LABEL, ensure_ascii=False),
        generated=generated,
        total=stats["total"],
        prio=stats["prio"],
        look=stats["look"],
        urgent=stats["urgent"],
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veille appels d'offres - Salle de bain / Accessibilite</title>
<style>
  :root {{
    --vert:#1b9e4b; --vert-bg:#e7f6ed;
    --orange:#d98300; --orange-bg:#fdf1e0;
    --rouge:#c0392b; --rouge-bg:#fbeae8;
    --bleu:#1f4e79; --gris:#566;
  }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; margin:0;
         background:#f4f6f8; color:#1c2733; }}
  header {{ background:var(--bleu); color:#fff; padding:18px 24px; }}
  header h1 {{ margin:0; font-size:20px; }}
  header .sub {{ opacity:.85; font-size:13px; margin-top:4px; }}
  .stats {{ display:flex; gap:14px; flex-wrap:wrap; padding:16px 24px; }}
  .card {{ background:#fff; border-radius:10px; padding:14px 18px; min-width:140px;
          box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .card .n {{ font-size:26px; font-weight:700; }}
  .card .l {{ font-size:12px; color:var(--gris); text-transform:uppercase; letter-spacing:.4px; }}
  .toolbar {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center;
             padding:6px 24px 16px; }}
  .toolbar input {{ flex:1; min-width:220px; padding:10px 12px; border:1px solid #cdd5dd;
                   border-radius:8px; font-size:14px; }}
  .btn {{ border:1px solid #cdd5dd; background:#fff; border-radius:20px; padding:8px 14px;
         cursor:pointer; font-size:13px; }}
  .btn.active {{ background:var(--bleu); color:#fff; border-color:var(--bleu); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; }}
  th, td {{ padding:10px 12px; text-align:left; font-size:13px; border-bottom:1px solid #eef1f4;
           vertical-align:top; }}
  th {{ position:sticky; top:0; background:#fff; cursor:pointer; user-select:none;
       border-bottom:2px solid #dfe5ea; white-space:nowrap; }}
  th:hover {{ color:var(--bleu); }}
  tr.t:hover {{ background:#fafcff; }}
  .score {{ font-weight:700; border-radius:6px; padding:3px 8px; display:inline-block; min-width:34px;
           text-align:center; }}
  .prioritaire .score {{ background:var(--vert-bg); color:var(--vert); }}
  .a_regarder .score {{ background:var(--orange-bg); color:var(--orange); }}
  .hors_cible .score {{ background:var(--rouge-bg); color:var(--rouge); }}
  .obj {{ font-weight:600; color:#13202e; cursor:pointer; }}
  .obj:hover {{ text-decoration:underline; }}
  .ref {{ font-family:Consolas,Menlo,monospace; font-size:12px; background:#eef3f8;
         color:#1f4e79; padding:2px 6px; border-radius:4px; white-space:nowrap;
         user-select:all; }}
  .tag {{ display:inline-block; background:#eef1f4; color:#445; border-radius:5px;
         padding:2px 7px; font-size:11px; margin:2px 3px 0 0; }}
  .tag.warn {{ background:var(--orange-bg); color:var(--orange); }}
  .tag.bad {{ background:var(--rouge-bg); color:var(--rouge); }}
  .tag.ok {{ background:var(--vert-bg); color:var(--vert); }}
  .days {{ font-weight:700; }}
  .d-urgent {{ color:var(--rouge); }}
  .d-soon {{ color:var(--orange); }}
  .d-ok {{ color:var(--vert); }}
  .lien a {{ color:var(--bleu); text-decoration:none; font-weight:600; white-space:nowrap; }}
  .detail {{ display:none; background:#f8fafc; }}
  .detail td {{ padding:14px 18px; color:#33414e; }}
  .empty {{ padding:40px; text-align:center; color:var(--gris); }}
  footer {{ padding:18px 24px; color:var(--gris); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Veille appels d'offres &mdash; Remplacement baignoire/douche &amp; accessibilite PMR</h1>
  <div class="sub">Genere le {generated} &middot; tri par pertinence decroissante</div>
</header>

<div class="stats">
  <div class="card"><div class="n">{total}</div><div class="l">Marches detectes</div></div>
  <div class="card" style="border-left:4px solid var(--vert)"><div class="n">{prio}</div><div class="l">Cibles prioritaires</div></div>
  <div class="card" style="border-left:4px solid var(--orange)"><div class="n">{look}</div><div class="l">A regarder</div></div>
  <div class="card" style="border-left:4px solid var(--rouge)"><div class="n">{urgent}</div><div class="l">Limite &lt; 7 jours</div></div>
</div>

<div class="toolbar">
  <input id="q" placeholder="Rechercher (objet, acheteur, departement, source)...">
  <button class="btn active" data-f="tous">Tous</button>
  <button class="btn" data-f="prioritaire">Prioritaires</button>
  <button class="btn" data-f="a_regarder">A regarder</button>
  <button class="btn" data-f="semaine">Cette semaine (&lt;7j)</button>
</div>

<table id="tbl">
  <thead><tr>
    <th data-k="score">Score</th>
    <th data-k="title">Objet</th>
    <th data-k="reference">Reference</th>
    <th data-k="buyer">Acheteur</th>
    <th data-k="department">Dpt</th>
    <th data-k="market_type">Type</th>
    <th data-k="publication_date">Publie</th>
    <th data-k="deadline">Limite</th>
    <th data-k="days_left">Jours</th>
    <th data-k="source">Source</th>
    <th>Lien</th>
  </tr></thead>
  <tbody id="body"></tbody>
</table>
<div id="empty" class="empty" style="display:none">Aucun marche ne correspond a ce filtre.</div>

<footer>
  Outil interne de veille &middot; sources : BOAMP, TED (UE), flux plateformes.<br>
  Verifie toujours l'avis officiel via le lien avant de t'engager. Les scores sont indicatifs.
</footer>

<script>
const DATA = {data};
const LABELS = {labels};
let state = {{ filter:"tous", q:"", sortKey:"score", sortDir:-1 }};

function daysClass(d) {{
  if (d===null||d===undefined) return "";
  if (d<0) return "d-urgent"; if (d<=7) return "d-urgent";
  if (d<=14) return "d-soon"; return "d-ok";
}}
function daysText(d) {{
  if (d===null||d===undefined) return "&mdash;";
  if (d<0) return "echu"; return d + " j";
}}
function esc(s) {{ return (s||"").replace(/[&<>]/g, c=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c])); }}

function tags(t) {{
  let h="";
  (t.flags||[]).forEach(f=>{{
    let cls="tag"; const lf=f.toLowerCase();
    if (lf.includes("carrelage")||lf.includes("hors metier")||lf.includes("echu")) cls="tag bad";
    else if (lf.includes("amiante")||lf.includes("autres lots")) cls="tag warn";
    else if (lf.includes("bailleur")||lf.includes("accord")) cls="tag ok";
    h += `<span class="${{cls}}">${{esc(f)}}</span>`;
  }});
  return h;
}}

function matchFilter(t) {{
  if (state.filter==="prioritaire" && t.category!=="prioritaire") return false;
  if (state.filter==="a_regarder" && t.category!=="a_regarder") return false;
  if (state.filter==="semaine" && !(t.days_left!==null && t.days_left>=0 && t.days_left<=7)) return false;
  if (state.q) {{
    const blob = (t.title+" "+t.reference+" "+t.buyer+" "+t.department+" "+t.source+" "+(t.matched||[]).join(" ")).toLowerCase();
    if (!blob.includes(state.q.toLowerCase())) return false;
  }}
  return true;
}}

function render() {{
  let rows = DATA.filter(matchFilter);
  const k = state.sortKey, dir = state.sortDir;
  rows.sort((a,b)=>{{
    let va=a[k], vb=b[k];
    if (va===null||va===undefined) va = (typeof vb==="number")? -1 : "";
    if (vb===null||vb===undefined) vb = (typeof va==="number")? -1 : "";
    if (typeof va==="number" && typeof vb==="number") return (va-vb)*dir;
    return String(va).localeCompare(String(vb))*dir;
  }});
  const body = document.getElementById("body");
  body.innerHTML = "";
  rows.forEach((t,i)=>{{
    const tr = document.createElement("tr");
    tr.className = "t " + t.category;
    tr.innerHTML = `
      <td><span class="score">${{t.score}}</span></td>
      <td><span class="obj" onclick="toggle(${{i}})">${{esc(t.title)}}</span><div>${{tags(t)}}</div></td>
      <td class="ref" title="Reference a rechercher sur le site">${{esc(t.reference)||"&mdash;"}}</td>
      <td>${{esc(t.buyer)||"&mdash;"}}</td>
      <td>${{esc(t.department)||"&mdash;"}}</td>
      <td>${{esc(t.market_type)||"&mdash;"}}</td>
      <td>${{esc(t.publication_date)||"&mdash;"}}</td>
      <td>${{esc(t.deadline)||"&mdash;"}}</td>
      <td class="days ${{daysClass(t.days_left)}}">${{daysText(t.days_left)}}</td>
      <td>${{esc(t.source)}}</td>
      <td class="lien">${{t.url?`<a href="${{t.url}}" target="_blank">Ouvrir &#8599;</a>`:"&mdash;"}}</td>`;
    body.appendChild(tr);
    const det = document.createElement("tr");
    det.className = "detail"; det.id = "det"+i;
    det.innerHTML = `<td colspan="11">
       <b>Reference :</b> <span class="ref">${{esc(t.reference)||"non precisee"}}</span> &nbsp;|&nbsp; <b>Identifiant :</b> ${{esc(t.id)}}<br><br>
       <b>Mots-cles detectes :</b> ${{(t.matched||[]).map(m=>`<span class="tag">${{esc(m)}}</span>`).join("")||"&mdash;"}}<br><br>
       <b>Categorie :</b> ${{LABELS[t.category]||t.category}} &nbsp;|&nbsp; <b>CPV :</b> ${{(t.cpv||[]).join(", ")||"non precise"}}<br><br>
       <b>Description :</b> ${{esc(t.description)||"&mdash;"}}</td>`;
    body.appendChild(det);
  }});
  document.getElementById("empty").style.display = rows.length? "none":"block";
}}

function toggle(i) {{
  const d = document.getElementById("det"+i);
  d.style.display = d.style.display==="table-row"? "none":"table-row";
}}

document.getElementById("q").addEventListener("input", e=>{{ state.q=e.target.value; render(); }});
document.querySelectorAll(".btn").forEach(b=>b.addEventListener("click", ()=>{{
  document.querySelectorAll(".btn").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); state.filter=b.dataset.f; render();
}}));
document.querySelectorAll("th[data-k]").forEach(th=>th.addEventListener("click", ()=>{{
  const k=th.dataset.k;
  state.sortDir = (state.sortKey===k)? -state.sortDir : (k==="score"||k==="days_left"? -1:1);
  state.sortKey=k; render();
}}));
render();
</script>
</body>
</html>"""
