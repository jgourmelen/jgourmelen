# Visuels du README de profil

`build.py` génère les SVG de `assets/` (variantes `-dark` et `-light`, plus la bannière, les boutons et l'appel à l'action), avec les polices Sora et DM Sans embarquées en sous-ensemble WOFF : GitHub bloque les polices externes dans `<img>`. Même charte et même approche que le README de l'organisation [wizops-cloud](https://github.com/wizops-cloud/.github).

```bash
pip install fonttools
mkdir -p ../fonts
curl -sfLo ../fonts/Sora.ttf "https://github.com/google/fonts/raw/main/ofl/sora/Sora%5Bwght%5D.ttf"
curl -sfLo ../fonts/DMSans.ttf "https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf"
python3 build.py ../../assets
```

Les textes (compétences, citations clients, parcours, missions) sont en dur dans `build.py` ; les textes alternatifs des images sont dans `README.md` à la racine. `icons.json` contient les icônes Lucide et Simple Icons utilisées ; pour en ajouter, complète `WANT` dans `make_icons.py` puis lance `python3 make_icons.py <node_modules/@iconify-json>`.
