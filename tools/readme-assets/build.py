"""Génère les visuels SVG du README de profil GitHub de Julien Gourmelen.

Même charte et même approche que le README de l'organisation wizops-cloud :
chaque SVG embarque un sous-ensemble des polices Sora / DM Sans (GitHub bloque
les polices externes dans <img>) et existe en variante -dark et -light.

Usage : python3 build.py ../../assets
"""
import base64
import io
import json
import random
import re
import sys
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).parent
FONTS = HERE.parent / "fonts"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
ICONS = json.loads((HERE / "icons.json").read_text())
LOGO = (HERE / "logo.svg").read_text()

# --------------------------------------------------------------------------- polices
FACES = {
    "sora700": ("Sora.ttf", {"wght": 700}),
    "sora600": ("Sora.ttf", {"wght": 600}),
    "dm400": ("DMSans.ttf", {"wght": 400, "opsz": 14}),
    "dm500": ("DMSans.ttf", {"wght": 500, "opsz": 14}),
    "dm700": ("DMSans.ttf", {"wght": 700, "opsz": 14}),
}
_static = {}


def static_font(face):
    if face not in _static:
        file, axes = FACES[face]
        _static[face] = instancer.instantiateVariableFont(TTFont(FONTS / file), axes)
    return _static[face]


def measure(s, face, size, ls=0):
    f = static_font(face)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = sum(hmtx[cmap.get(ord(ch)) or cmap.get(ord("?"))][0] for ch in s)
    return w * size / upm + ls * len(s)


def nbsp(s):
    """Espaces insécables : « x », 20 %, 10 000, ponctuation haute."""
    s = re.sub(r" ([%»:;?!])", "\u00a0\\1", s)
    s = re.sub(r"(«) ", "\\1\u00a0", s)
    return re.sub(r"(\d) (\d{3})", "\\1\u00a0\\2", s)


def wrap(s, face, size, maxw):
    s = nbsp(s)
    lines, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        if measure(t, face, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def font_css(used):
    css = []
    for face, chars in used.items():
        if not chars:
            continue
        src = io.BytesIO()
        static_font(face).save(src)
        src.seek(0)
        f = TTFont(src)
        opts = subset.Options()
        opts.flavor = "woff"
        opts.layout_features = ["kern", "liga"]
        opts.name_IDs = []
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)) + " ")
        sub.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:'{face}';src:url(data:font/woff;base64,{b64}) format('woff');}}")
    return "".join(css)


# --------------------------------------------------------------------------- thèmes
THEMES = {
    "dark": dict(
        card="#0E2531", card2="#112C3A", border="#1D4552", text="#ECF7F7", muted="#A3C2C5",
        accent="#F97316", petrol="#3FC1C9", petrol2="#14918F", tint="#14918F2E", soft="#3FC1C912",
        chip="#3FC1C91A", chipb="#3FC1C940",
    ),
    "light": dict(
        card="#FFFFFF", card2="#F4FBFB", border="#CFE9E8", text="#0B1F2A", muted="#46605F",
        accent="#EA580C", petrol="#0F6E72", petrol2="#14918F", tint="#14918F1A", soft="#14918F0B",
        chip="#14918F12", chipb="#14918F38",
    ),
}
BRAND = dict(night="#0B1F2A", deep="#071820", p950="#072B31", p800="#0F5D63", p600="#14918F",
             p400="#3FC1C9", orange="#F97316", ink="#ECF7F7", muted="#A9C9CB")


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.parts, self.defs = [], []
        self.used = {k: set() for k in FACES}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, face, size, fill, anchor="start", ls=0, opacity=1):
        self.used[face].update(s)
        extra = f' letter-spacing="{ls}"' if ls else ""
        op = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{face}" font-size="{size}" fill="{fill}"'
                 f' text-anchor="{anchor}"{extra}{op}>{escape(s)}</text>')

    def para(self, x, y, s, face, size, fill, maxw, lh=1.45, anchor="start"):
        lines = wrap(s, face, size, maxw)
        for i, line in enumerate(lines):
            self.text(x, y + i * size * lh, line, face, size, fill, anchor)
        return y + len(lines) * size * lh

    def icon(self, kind, name, x, y, size, color, stroke=None, fill=None):
        body = ICONS[kind][name]
        if stroke:
            body = body.replace('stroke-width="2"', f'stroke-width="{stroke}"')
        if fill:
            body = body.replace('fill="none"', f'fill="{fill}"')
        body = body.replace("currentColor", color)
        self.add(f'<g transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})">{body}</g>')

    def logo(self, x, y, size):
        inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", LOGO.strip())
        self.add(f'<g transform="translate({x} {y}) scale({size / 512:.4f})">{inner}</g>')

    def render(self, path):
        css = font_css(self.used)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
               f'<title>{escape(self.title)}</title><style>{css}</style>'
               f'<defs>{"".join(self.defs)}</defs>{"".join(self.parts)}</svg>')
        (OUT / path).write_text(svg)
        print(f"{path:34s} {len(svg) / 1024:6.1f} KB")


# --------------------------------------------------------------------------- briques
def card_bg(svg, t, x, y, w, h, r=28, featured=False):
    gid = f"cg{len(svg.defs)}"
    svg.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
                    f'<stop offset="0" stop-color="{t["card2"]}"/><stop offset="1" stop-color="{t["card"]}"/></linearGradient>')
    svg.add(f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" rx="{r}" fill="url(#{gid})" '
            f'stroke="{t["petrol2"] if featured else t["border"]}" stroke-opacity="{.6 if featured else 1}" stroke-width="2"/>')


def icon_tile(svg, t, kind, name, x, y, s=76):
    svg.add(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{s * .26:.0f}" fill="{t["tint"]}"/>')
    svg.icon(kind, name, x + s * 0.22, y + s * 0.22, s * 0.56, t["petrol"], stroke=1.75)


def network_pattern(svg, w, h, seed=11, opacity=0.16):
    rnd = random.Random(seed)
    pts = [(rnd.uniform(0, w), rnd.uniform(0, h)) for _ in range(int(26 * w * h / (1600 * 600)) + 4)]
    g = []
    for i, (x1, y1) in enumerate(pts):
        for x2, y2 in pts[i + 1:]:
            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < 250 ** 2:
                g.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
    svg.add(f'<g stroke="{BRAND["p400"]}" stroke-opacity="{opacity}" stroke-width="1.5">{"".join(g)}</g>')
    for i, (x, y) in enumerate(pts):
        c = BRAND["orange"] if i % 5 == 0 else BRAND["p400"]
        svg.add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{4 if i % 5 == 0 else 3}" fill="{c}" fill-opacity="{opacity * 3:.2f}"/>')


def brand_bg(svg, w, h, r=32, seed=11):
    svg.defs.append('<linearGradient id="bb" x1="0" y1="0" x2="1" y2="1">'
                    f'<stop offset="0" stop-color="{BRAND["deep"]}"/><stop offset=".55" stop-color="{BRAND["night"]}"/>'
                    f'<stop offset="1" stop-color="{BRAND["p950"]}"/></linearGradient>'
                    '<radialGradient id="glow" cx=".85" cy=".05" r=".75">'
                    f'<stop offset="0" stop-color="{BRAND["p600"]}" stop-opacity=".5"/>'
                    f'<stop offset="1" stop-color="{BRAND["p600"]}" stop-opacity="0"/></radialGradient>'
                    '<radialGradient id="glow2" cx=".02" cy="1" r=".6">'
                    f'<stop offset="0" stop-color="{BRAND["orange"]}" stop-opacity=".10"/>'
                    f'<stop offset="1" stop-color="{BRAND["orange"]}" stop-opacity="0"/></radialGradient>'
                    f'<clipPath id="bc"><rect width="{w}" height="{h}" rx="{r}"/></clipPath>')
    svg.add(f'<g clip-path="url(#bc)"><rect width="{w}" height="{h}" fill="url(#bb)"/>'
            f'<rect width="{w}" height="{h}" fill="url(#glow)"/><rect width="{w}" height="{h}" fill="url(#glow2)"/>')
    network_pattern(svg, w, h, seed)
    svg.add("</g>")
    svg.add(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{r}" fill="none" stroke="{BRAND["p600"]}" '
            f'stroke-opacity=".45" stroke-width="2"/>')


def pill(svg, x, y, label, face="dm500", size=22, fg=None, bg=None, stroke=None, h=46, padx=22, icon=None):
    iw = size * 1.1 + 10 if icon else 0
    w = measure(label, face, size) + padx * 2 + iw
    svg.add(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{bg or "none"}"'
            + (f' stroke="{stroke}" stroke-width="2"' if stroke else "") + "/>")
    if icon:
        svg.icon(icon[0], icon[1], x + padx, y + (h - size * 1.1) / 2, size * 1.1, icon[2], stroke=2.2)
    svg.text(x + padx + iw, y + h / 2 + size * 0.36, label, face, size, fg)
    return w


def chips(svg, t, x, bottom, labels, maxw, size=21, h=40, gap=10):
    """Rangée(s) de pastilles techno, la dernière rangée posée sur `bottom`."""
    rows, cx = 1, x
    for lab in labels:
        w = measure(lab, "dm500", size) + 32
        if cx + w > x + maxw:
            rows, cx = rows + 1, x
        cx += w + gap
    cx, cy = x, bottom - rows * h - (rows - 1) * gap
    top = cy
    for lab in labels:
        w = measure(lab, "dm500", size) + 32
        if cx + w > x + maxw:
            cx, cy = x, cy + h + gap
        svg.add(f'<rect x="{cx:.1f}" y="{cy}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{t["chip"]}" '
                f'stroke="{t["chipb"]}" stroke-width="1.5"/>')
        svg.text(cx + w / 2, cy + h / 2 + size * 0.36, lab, "dm500", size, t["text"], "middle")
        cx += w + gap
    return top


def link_line(svg, t, x, y, label, size=23):
    svg.text(x, y, label, "dm700", size, t["accent"])
    svg.icon("lu", "arrow-right", x + measure(label + " ", "dm700", size), y - size * 0.86, size * 1.05,
             t["accent"], 2.4)


# --------------------------------------------------------------------------- bannière
def hero():
    W, H = 1600, 660
    s = Svg(W, H, "Julien Gourmelen — Ingénieur DevOps / SRE, fondateur de WizOps. "
                  "Je construis votre infrastructure Kubernetes & Cloud, puis je l'opère.")
    brand_bg(s, W, H)
    # monogramme
    s.defs.append('<linearGradient id="mg" x1="0" y1="0" x2="1" y2="1">'
                  f'<stop offset="0" stop-color="{BRAND["p400"]}"/><stop offset="1" stop-color="{BRAND["p800"]}"/></linearGradient>')
    cx, cy, r = 160, 168, 66
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r + 9}" fill="none" stroke="{BRAND["orange"]}" stroke-width="3" '
          f'stroke-dasharray="300 140" stroke-linecap="round" transform="rotate(-60 {cx} {cy})"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#mg)"/>')
    s.text(cx, cy + 17, "JG", "sora700", 48, "#FFFFFF", "middle")
    s.logo(cx + 34, cy + 30, 50)
    s.text(270, 160, "Julien Gourmelen", "sora700", 64, BRAND["ink"])
    s.text(272, 206, "INGÉNIEUR DEVOPS / SRE · FONDATEUR DE WIZOPS", "dm700", 21, BRAND["p400"], ls=3)
    s.text(96, 340, "Je construis votre infrastructure", "sora700", 64, BRAND["ink"])
    l2 = "Kubernetes & Cloud, "
    s.text(96, 418, l2, "sora700", 64, BRAND["ink"])
    s.text(96 + measure(l2, "sora700", 64), 418, "puis je l'opère.", "sora700", 64, BRAND["orange"])
    s.para(96, 482, "L'ingénieur qui l'a conçue est celui qui la fait tourner. 15+ ans de DevOps et de SRE, "
                    "du MVP à la flotte multi-cloud.", "dm400", 28, BRAND["muted"], 1180)
    x = 96
    for ic, label in [("cloud-cog", "Kubernetes & multi-cloud"), ("shield-check", "SecNumCloud · HDS"),
                      ("bot", "DevOps & IA"), ("map-pin", "Vannes · à distance")]:
        x += pill(s, x, 568, label, "dm500", 22, BRAND["ink"], "#FFFFFF0F", "#3FC1C950", h=50, padx=20,
                  icon=("lu", ic, BRAND["p400"])) + 14
    lab = "Supermalter · 100 % de satisfaction"
    w = measure(lab, "dm500", 21) + 40 + 33
    pill(s, W - 96 - w, 84, lab, "dm500", 21, BRAND["ink"], "#F973161A", "#F9731666", h=46, padx=20,
         icon=("lu", "star", BRAND["orange"]))
    s.render("hero.svg")


def button(name, label, primary, icon=None):
    face, size, h = "sora600", 26, 76
    lead = 40 if icon else 0
    w = int(measure(label, face, size) + 80 + 34 + lead)
    s = Svg(w, h, label)
    if primary:
        s.defs.append('<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FB8A3C"/>'
                      '<stop offset="1" stop-color="#EA580C"/></linearGradient>')
        s.add(f'<rect width="{w}" height="{h}" rx="{h / 2}" fill="url(#bg)"/>')
        fg = "#FFFFFF"
    else:
        s.add(f'<rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="{(h - 3) / 2}" fill="{BRAND["night"]}" '
              f'stroke="{BRAND["p400"]}" stroke-width="3"/>')
        fg = BRAND["ink"]
    if icon:
        s.icon(icon[0], icon[1], 36, h / 2 - 14, 28, fg, stroke=2.2)
    s.text(40 + lead, h / 2 + size * 0.36, label, face, size, fg)
    s.icon("lu", "arrow-right", w - 40 - 26, h / 2 - 13, 26, fg, stroke=2.5)
    s.render(name)


# --------------------------------------------------------------------------- chiffres
STATS = [("15+", "Années d'expérience", "Cloud, DevOps & SRE"),
         ("100+", "Projets réalisés", "De la startup au grand compte"),
         ("100 %", "Satisfaction client", "46 avis positifs sur Malt"),
         ("10 000+", "Abonnés LinkedIn", "Cloud, Kubernetes, DevOps"),
         ("300+", "Articles de blog", "sur wizops.fr/blog")]


def stats(theme):
    t = THEMES[theme]
    W, H = 1600, 260
    s = Svg(W, H, "Chiffres clés : " + ", ".join(f"{a} {b.lower()}" for a, b, _ in STATS))
    card_bg(s, t, 0, 0, W, H)
    cw = W / len(STATS)
    for i, (n, l1, l2) in enumerate(STATS):
        cx = cw * i + cw / 2
        if i:
            s.add(f'<line x1="{cw * i}" y1="64" x2="{cw * i}" y2="{H - 64}" stroke="{t["border"]}" stroke-width="2"/>')
        s.text(cx, 122, n, "sora700", 60, t["accent"], "middle")
        s.text(cx, 170, l1, "dm700", 26, t["text"], "middle")
        s.text(cx, 206, l2, "dm400", 22, t["muted"], "middle")
    s.render(f"stats-{theme}.svg")


# --------------------------------------------------------------------------- savoir-faire
def featured(theme):
    t = THEMES[theme]
    W, H = 1600, 480
    s = Svg(W, H, "Build puis run : celui qui conçoit la plateforme est celui qui l'opère")
    card_bg(s, t, 0, 0, W, H, featured=True)
    lab = "MA FAÇON DE TRAVAILLER"
    pw = measure(lab, "dm700", 18, ls=2.2) + 44
    s.add(f'<rect x="64" y="60" width="{pw:.0f}" height="42" rx="21" fill="{t["accent"]}1F"/>')
    s.text(64 + 22, 88, lab, "dm700", 18, t["accent"], ls=2.2)
    icon_tile(s, t, "lu", "headset", 64, 134, 96)
    s.text(190, 178, "Build puis run", "sora700", 50, t["text"])
    s.text(190, 220, "Un seul interlocuteur, du premier commit au run.", "dm500", 25, t["muted"])
    s.para(64, 296, "Celui qui conçoit la plateforme est celui qui l'opère. Tout est documenté : "
                    "réversibilité garantie, aucune dépendance à moi.", "dm400", 25, t["muted"], 720)
    bullets = ["Audit express : risques, coûts, plan d'action", "Build ou reprise de l'infra, tout en code",
               "Run : supervision 24/7, SLA 99,5 %, PRA testé", "Patchs, sécurité, FinOps, rapport mensuel"]
    for i, b in enumerate(bullets):
        y = 140 + i * 64
        s.add(f'<circle cx="890" cy="{y + 20}" r="20" fill="{t["tint"]}"/>')
        s.icon("lu", "check", 878, y + 8, 24, t["petrol"], stroke=2.6)
        s.text(930, y + 29, b, "dm500", 26, t["text"])
    link_line(s, t, 64, H - 46, "L'infogérance WizOps")
    s.render(f"build-run-{theme}.svg")


SKILLS = [
    ("kubernetes", "si", "kubernetes", "Kubernetes & platform engineering", "Des plateformes prêtes pour la prod",
     "Plateformes Kubernetes construites de zéro, en GitOps avec Argo CD et Helm, jusqu'à une flotte de 7 clusters "
     "sur 4 clouds.", ["EKS", "AKS", "GKE", "OVH MKS", "Helm", "Argo CD"]),
    ("cloud", "lu", "cloud-cog", "Cloud multi-provider & souverain", "Le bon cloud pour vos contraintes",
     "Infrastructure Kubernetes SecNumCloud construite de zéro sur Outscale, plateforme HDS sur le cloud souverain S3NS.",
     ["AWS", "Azure", "GCP", "OVHcloud", "Scaleway", "Outscale"]),
    ("iac", "lu", "code-xml", "Infrastructure as Code & CI/CD", "100 % en code, versionné et revu",
     "CI avec OIDC, sans clé statique. Création d'un environnement ramenée de 2 jours à 30 minutes.",
     ["Terraform", "Terragrunt", "Ansible", "GitHub Actions", "GitLab CI"]),
    ("migration", "lu", "arrow-right-left", "Migration & reprise", "Migrer sans perdre de données",
     "Vers Kubernetes, entre clouds, vers le souverain ou après un rachat : près de 180 plateformes clientes "
     "migrées sans perte de données.", ["Swarm → Kubernetes", "GCP → AWS", "Post-acquisition"]),
    ("devsecops", "lu", "shield-check", "DevSecOps & conformité", "La sécurité intégrée par défaut",
     "Durcissement Kubernetes, NetworkPolicies, RBAC, secrets, WAF et SIEM. SecNumCloud, HDS, Défense, "
     "ISO 27001 / 27701.", ["Vault", "External Secrets", "Falco", "Wazuh", "Trivy"]),
    ("observabilite", "lu", "activity", "Observabilité & SRE", "Voir les incidents avant vos clients",
     "Alerting, runbooks et PRA testé. Migration de Graylog / Elasticsearch vers la stack Grafana, sans coût "
     "de licence.", ["Grafana", "Prometheus", "Loki", "Mimir", "Tempo"]),
    ("finops", "lu", "piggy-bank", "FinOps", "Des coûts cloud suivis au quotidien",
     "Suivi des coûts multi-cloud et refacturation par client. −20 % de coûts d'infrastructure sur une "
     "plateforme SaaS, plus de 30 % d'économies sur la CI.", ["Rightsizing", "Instances Spot", "Refacturation"]),
    ("aiops", "lu", "bot", "DevOps & IA (AIOps)", "L'IA qui investigue vos alertes",
     "Agent IA qui investigue les alertes de production et poste la cause racine dans Slack. IaC assistée "
     "par IA, toujours revue et testée.", ["HolmesGPT", "Claude", "AWS Bedrock", "LLM"]),
]


def skill(theme, key, kind, icon, label, punch, desc, tags):
    t = THEMES[theme]
    W, H = 784, 400
    s = Svg(W, H, f"{label} — {punch}. {desc} {', '.join(tags)}.")
    card_bg(s, t, 0, 0, W, H)
    icon_tile(s, t, kind, icon, 44, 44, 80)
    s.text(146, 78, label.upper(), "dm700", 19, t["petrol"], ls=1.6)
    s.text(146, 118, punch, "sora700", 31 if measure(punch, "sora700", 31) < W - 190 else 28, t["text"])
    end = s.para(44, 182, desc, "dm400", 25, t["muted"], W - 88)
    top = chips(s, t, 44, H - 44, tags, W - 88, size=21, h=42)
    assert end - 10 < top, (key, end, top)
    s.render(f"skill-{key}-{theme}.svg")


# --------------------------------------------------------------------------- savoir-être
QUALITIES = [
    ("zap", "Réactivité",
     "Julien a été très réactif, et nous a bien conseillé. Il a bien compris notre besoin et nos enjeux "
     "à court, moyen et long terme.", "Amaury", "F2R2"),
    ("graduation-cap", "Pédagogie",
     "Il est à la fois pro, réactif et pédagogue, ce qui rend les échanges sympas et efficaces.",
     "Antoine", "Caast.TV"),
    ("ear", "Écoute du besoin",
     "Il a bien compris notre problème alors même qu'il nous était difficile de bien l'exprimer. "
     "Il a su nous orienter, tout en prenant en compte les choix initiaux.", "Frédéric", "CTO · Process Metronome"),
    ("heart-handshake", "Transmission & pragmatisme",
     "[…] dans la transmission de la connaissance […]. Il est un expert dévoué, curieux, pragmatique "
     "qui saura apporter des solutions simples à des problèmes complexes.", "Gabriel", "CTO · Toha"),
    ("message-square-text", "Communication & documentation",
     "Agit rapidement et efficacement, communication fluide via notre Slack, le résultat est documenté […]",
     "Arnaud", "CTO · Didask"),
    ("clock", "Disponibilité",
     "Julien a très rapidement pris en main le dossier, a régulièrement effectué des points d'avancement "
     "et est resté très disponible sur toute la durée de la mission.", "Etienne", "Responsable Infra · Epiconcept"),
]


def soft(theme):
    t = THEMES[theme]
    W = 1600
    m, gap = 48, 24
    cw = (W - 2 * m - gap) / 2
    ch = 290
    rows = (len(QUALITIES) + 1) // 2
    H = int(2 * m + rows * ch + (rows - 1) * gap)
    s = Svg(W, H, "Savoir-être, d'après les avis clients : " + " ; ".join(
        f"{q}, « {txt} » ({who}, {org})" for _, q, txt, who, org in QUALITIES))
    card_bg(s, t, 0, 0, W, H)
    for k, (ic, q, txt, who, org) in enumerate(QUALITIES):
        x, y = m + (k % 2) * (cw + gap), m + (k // 2) * (ch + gap)
        s.add(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="22" fill="{t["soft"]}" '
              f'stroke="{t["border"]}" stroke-width="1.5"/>')
        icon_tile(s, t, "lu", ic, x + 32, y + 32, 64)
        s.text(x + 116, y + 75, q, "sora700", 28, t["text"])
        s.icon("lu", "quote", x + cw - 32 - 36, y + 38, 36, t["accent"], 1.8)
        lines = wrap(f"« {txt} »", "dm400", 24, cw - 64)
        for i, line in enumerate(lines):
            s.text(x + 32, y + 136 + i * 35, line, "dm400", 24, t["text"])
        s.text(x + 32, y + ch - 30, who, "dm700", 21, t["petrol"])
        s.text(x + 32 + measure(who + "  ", "dm700", 21), y + ch - 30, org, "dm400", 21, t["muted"])
        assert len(lines) <= 3, (q, len(lines))
    s.render(f"soft-skills-{theme}.svg")


# --------------------------------------------------------------------------- missions
MISSIONS = [
    ("shield-half", "Défense", "KNDS, via UserAdgents",
     "Kubernetes durci sur OVHcloud, production-ready et reproductible à 100 % depuis le code.",
     ["OVH MKS", "Terraform", "OKMS"]),
    ("heart-pulse", "e-Santé", "Okeiro",
     "Plateforme FHIR sur GKE Autopilot, cloud souverain S3NS, en contexte de certification HDS.",
     ["GKE", "Helm", "HDS"]),
    ("globe", "Registre Internet", "F2R2",
     "Audit (82 actions, −19 % de budget projeté), AWS Organization de 5 comptes en IaC, puis infogérance.",
     ["AWS", "EKS", "Terragrunt"]),
    ("headset", "Infogérance", "Caast.TV",
     "Gestion et maintenance de l'infrastructure Kubernetes sur AWS, fiabilisation et automatisation des points critiques.",
     ["Kubernetes", "AWS", "Argo CD"]),
    ("hospital", "Santé publique", "Epiconcept",
     "Trois ans d'accompagnement : Ansible, puis déploiements on-premise hors ligne sur RHEL 8, en HA.",
     ["Ansible", "RHEL 8", "Docker"]),
    ("arrow-right-left", "Migration cloud", "Earny SA",
     "Migration complète de Google Cloud vers AWS EKS, GitOps Argo CD, CI par OIDC sans clé statique.",
     ["EKS", "Argo CD", "OIDC"]),
]


def missions(theme):
    t = THEMES[theme]
    W, m, gap = 1600, 48, 24
    cw = (W - 2 * m - gap) / 2
    ch = 300
    H = int(2 * m + 3 * ch + 2 * gap)
    s = Svg(W, H, "Missions marquantes : " + " ; ".join(f"{sec} ({c}) : {d}" for _, sec, c, d, _ in MISSIONS))
    card_bg(s, t, 0, 0, W, H)
    for k, (ic, sec, client, desc, tags) in enumerate(MISSIONS):
        x, y = m + (k % 2) * (cw + gap), m + (k // 2) * (ch + gap)
        s.add(f'<rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="{ch}" rx="22" fill="{t["soft"]}" '
              f'stroke="{t["border"]}" stroke-width="1.5"/>')
        icon_tile(s, t, "lu", ic, x + 32, y + 32, 68)
        s.text(x + 120, y + 60, sec.upper(), "dm700", 19, t["petrol"], ls=2)
        s.text(x + 120, y + 94, client, "sora700", 29, t["text"])
        lines = wrap(desc, "dm400", 25, cw - 64)
        assert len(lines) <= 2, (client, len(lines))
        for i, line in enumerate(lines):
            s.text(x + 32, y + 150 + i * 36, line, "dm400", 25, t["muted"])
        chips(s, t, x + 32, y + ch - 30, tags, cw - 64, size=20, h=40, gap=10)
    s.render(f"missions-{theme}.svg")


# --------------------------------------------------------------------------- parcours
CAREER = [
    ("2024 →", "WizStatus", "Fondateur & CTO",
     "SaaS de monitoring et de status pages sur cloud européen : sondes Go multi-cluster, analyse de cause "
     "racine des incidents par LLM.", True),
    ("2021 →", "Plateforme SaaS d'open innovation", "Senior SRE, Lead SRE, puis Principal Platform Engineer",
     "7 clusters Kubernetes sur 4 clouds, 80+ plateformes clientes, ~180 plateformes migrées après une "
     "acquisition, SecNumCloud pour la DGE, AIOps, ISO 27001.", True),
    ("2016 →", "WizOps", "Fondateur · consultant DevOps / SRE et formateur",
     "Défense, e-santé, santé publique, SaaS, e-commerce : audits, build, migrations et infogérance. "
     "Formations DevOps (La Capsule, Isoset).", True),
    ("2019", "Coopengo", "Ingénieur DevOps",
     "Kubernetes haute disponibilité sur AWS, Terraform, Helm v2 → v3, CI Jenkins sur Kubernetes et "
     "instances Spot : plus de 30 % d'économies.", False),
    ("→ 2019", "SFR", "Intégrateur logiciel embarqué, puis référent DevOps",
     "Firmware du décodeur TV sur Linux embarqué, puis monitoring Prometheus / Grafana, Docker Swarm et "
     "premier PoC Kubernetes.", False),
    ("2010", "Telecom Lille", "Ingénieur diplômé · Systèmes & Réseaux",
     "Des bases solides en architecture réseau et en infrastructure.", False),
]


def career(theme):
    t = THEMES[theme]
    W = 1600
    rowh, top = 172, 64
    H = top * 2 + rowh * (len(CAREER) - 1) + 100
    s = Svg(W, H, "Parcours : " + " ; ".join(f"{y} {org}, {role}" for y, org, role, _, _ in CAREER))
    card_bg(s, t, 0, 0, W, H)
    lx = 250
    s.add(f'<line x1="{lx}" y1="{top + 20}" x2="{lx}" y2="{H - top - 30}" stroke="{t["border"]}" stroke-width="3"/>')
    for i, (year, org, role, desc, now) in enumerate(CAREER):
        y = top + i * rowh
        s.text(lx - 44, y + 34, year, "sora700", 30, t["accent"] if now else t["petrol"], "end")
        s.add(f'<circle cx="{lx}" cy="{y + 24}" r="13" fill="{t["card"]}" stroke="{t["accent"] if now else t["petrol2"]}" stroke-width="4"/>')
        if now:
            s.add(f'<circle cx="{lx}" cy="{y + 24}" r="5" fill="{t["accent"]}"/>')
        x = lx + 48
        s.text(x, y + 36, org, "sora700", 31, t["text"])
        s.text(x + measure(org + "   ", "sora700", 31), y + 35, role, "dm500", 24, t["petrol"])
        lines = wrap(desc, "dm400", 24, W - x - 64)
        assert len(lines) <= 2, (org, len(lines))
        for j, line in enumerate(lines):
            s.text(x, y + 80 + j * 34, line, "dm400", 24, t["muted"])
        assert x + measure(org + "   ", "sora700", 31) + measure(role, "dm500", 24) < W - 48, org
    s.render(f"career-{theme}.svg")


# --------------------------------------------------------------------------- stack
STACK = [("Orchestration", [("kubernetes", "Kubernetes"), ("helm", "Helm"), ("argo", "Argo CD"), ("docker", "Docker")]),
         ("Cloud", [("amazonwebservices", "AWS"), ("microsoftazure", "Azure"), ("googlecloud", "GCP"),
                    ("ovh", "OVHcloud"), ("scaleway", "Scaleway")]),
         ("IaC & CI/CD", [("terraform", "Terraform"), ("ansible", "Ansible"), ("githubactions", "Actions"),
                          ("gitlab", "GitLab CI"), ("jenkins", "Jenkins")]),
         ("Observabilité", [("grafana", "Grafana"), ("prometheus", "Prometheus"), ("opentelemetry", "OpenTelemetry"),
                            ("datadog", "Datadog")]),
         ("Sécurité", [("vault", "Vault"), ("falco", "Falco"), ("trivy", "Trivy")]),
         ("Langages & data", [("python", "Python"), ("go", "Go"), ("gnubash", "Bash"), ("postgresql", "PostgreSQL"),
                              ("mongodb", "MongoDB")])]


def stack(theme):
    t = THEMES[theme]
    W, gap, m = 1600, 24, 48
    gw, gh = (W - 2 * m - gap) / 2, 236
    H = int(2 * m + 3 * gh + 2 * gap)
    s = Svg(W, H, "Stack technique : " + " ; ".join(f"{g} : {', '.join(l for _, l in it)}" for g, it in STACK))
    card_bg(s, t, 0, 0, W, H)
    for k, (title, items) in enumerate(STACK):
        x, y = m + (k % 2) * (gw + gap), m + (k // 2) * (gh + gap)
        s.add(f'<rect x="{x}" y="{y}" width="{gw}" height="{gh}" rx="22" fill="{t["soft"]}" stroke="{t["border"]}" stroke-width="1.5"/>')
        s.text(x + 30, y + 46, title.upper(), "dm700", 19, t["petrol"], ls=2.4)
        slot = min((gw - 40) / len(items), 165)
        x0 = x + (gw - slot * len(items)) / 2
        for j, (ic, label) in enumerate(items):
            cx = x0 + slot * j + slot / 2
            s.icon("si", ic, cx - 30, y + 76, 60, t["text"])
            s.text(cx, y + 186, label, "dm500", 22, t["muted"], "middle")
    s.render(f"stack-{theme}.svg")


# --------------------------------------------------------------------------- projets
def project(theme, key, icon, name, tag, desc, cta):
    t = THEMES[theme]
    W, H = 784, 366
    s = Svg(W, H, f"{name} — {tag}. {desc}")
    card_bg(s, t, 0, 0, W, H)
    if icon == "logo":
        s.logo(44, 44, 84)
    else:
        icon_tile(s, t, icon[0], icon[1], 44, 44, 84)
    s.text(152, 88, name, "sora700", 36 if measure(name, "sora700", 36) < W - 190 else 31, t["text"])
    s.text(152, 124, tag, "dm500", 22, t["petrol"])
    end = s.para(44, 188, desc, "dm400", 25, t["muted"], W - 88)
    assert end - 25 * 1.45 < H - 82, (key, end)
    link_line(s, t, 44, H - 42, cta, 22)
    s.render(f"proj-{key}-{theme}.svg")


PROJECTS = [
    ("wizops", "logo", "WizOps", "Infogérance Kubernetes & Cloud",
     "Ma société, fondée en 2016 : build ou reprise 100 % code, run 24/7, sécurité, FinOps et agents IA qui investiguent "
     "vos alertes.", "github.com/wizops-cloud"),
    ("wizstatus", ("lu", "activity"), "WizStatus", "Monitoring & status pages",
     "10+ types de checks, sondes Go multi-cluster, alerting multi-canal et analyse de cause racine par LLM.",
     "wizstatus.com"),
    ("mongoadmin", ("si", "mongodb"), "MongoAdmin", "Client MongoDB desktop",
     "Le client MongoDB desktop moderne, natif et écrit en Rust.", "mongoadmin.dev"),
    ("ovh-exporter", ("si", "prometheus"), "prometheus-ovh-exporter", "Open source · Go · Apache 2.0",
     "Exporter Prometheus pour OVHcloud : facturation, consommation, quotas, instances, stockage et savings plans.",
     "Voir sur GitHub"),
]


def blog(theme):
    t = THEMES[theme]
    W, H = 1600, 230
    s = Svg(W, H, "Blog : 300+ articles DevOps & Cloud sur wizops.fr/blog")
    card_bg(s, t, 0, 0, W, H)
    icon_tile(s, t, "lu", "newspaper", 56, 56, 96)
    s.text(188, 90, "BLOG · 300+ ARTICLES", "dm700", 19, t["petrol"], ls=2.2)
    s.text(188, 136, "Kubernetes, GitOps, Terraform, CI/CD, observabilité", "sora700", 34, t["text"])
    s.text(188, 180, "Retours de terrain et bonnes pratiques DevOps & Cloud, en français.", "dm400", 24, t["muted"])
    link_line(s, t, W - 56 - measure("wizops.fr/blog  ", "dm700", 23) - 26, 136, "wizops.fr/blog")
    s.render(f"blog-{theme}.svg")


def cta():
    W, H = 1600, 400
    s = Svg(W, H, "Une infra à construire, reprendre, sécuriser ou faire tourner sereinement ? "
                  "Réservez 30 minutes avec Julien.")
    brand_bg(s, W, H, seed=5)
    s.text(W / 2, 128, "Une infra à construire, reprendre,", "sora700", 52, BRAND["ink"], "middle")
    s.text(W / 2, 194, "sécuriser ou faire tourner sereinement ?", "sora700", 52, BRAND["ink"], "middle")
    s.text(W / 2, 248, "Premier échange gratuit et sans engagement.", "dm400", 28, BRAND["muted"], "middle")
    label = "Réserver 30 minutes avec moi"
    w = measure(label, "sora600", 28) + 122
    x = (W - w) / 2
    s.defs.append('<linearGradient id="cb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FB8A3C"/>'
                  '<stop offset="1" stop-color="#EA580C"/></linearGradient>')
    s.add(f'<rect x="{x}" y="288" width="{w}" height="74" rx="37" fill="url(#cb)"/>')
    s.icon("lu", "calendar-days", x + 38, 310, 30, "#FFFFFF", 2.2)
    s.text(x + 82, 335, label, "sora600", 28, "#FFFFFF")
    s.render("cta.svg")


hero()
cta()
button("btn-rdv.svg", "Prendre rendez-vous", True, ("lu", "calendar-days"))
button("btn-linkedin.svg", "LinkedIn", False, ("si", "linkedin"))
button("btn-site.svg", "wizops.fr", False, ("lu", "globe"))
for th in THEMES:
    stats(th)
    featured(th)
    for sk in SKILLS:
        skill(th, *sk)
    soft(th)
    missions(th)
    career(th)
    stack(th)
    for p in PROJECTS:
        project(th, *p)
    blog(th)
