"""Extrait les icônes utilisées par build.py depuis les paquets @iconify-json (Lucide, Simple Icons).

Usage : python3 make_icons.py <dossier node_modules/@iconify-json>
"""
import json
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
WANT = {
    "si": "kubernetes helm argo docker amazonwebservices microsoftazure googlecloud ovh scaleway terraform ansible "
          "githubactions gitlab jenkins grafana prometheus opentelemetry datadog vault falco trivy python go gnubash "
          "postgresql mongodb linkedin github",
    "lu": "arrow-right cloud-cog code-xml arrow-right-left shield-check activity piggy-bank bot headset check quote "
          "zap graduation-cap ear message-square-text clock heart-handshake calendar-days newspaper map-pin star "
          "shield-half heart-pulse globe landmark hospital building-2 git-branch",
}
PACK = {"si": "simple-icons", "lu": "lucide"}
out = {}
for k, names in WANT.items():
    icons = json.loads((SRC / PACK[k] / "icons.json").read_text())["icons"]
    out[k] = {n: icons[n]["body"] for n in names.split()}
(Path(__file__).parent / "icons.json").write_text(json.dumps(out, ensure_ascii=False))
print({k: len(v) for k, v in out.items()})
