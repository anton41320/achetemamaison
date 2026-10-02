"""Analyse de l'environnement d'une adresse (sources publiques françaises + OSM).

Pipeline : adresse → BAN → parcelle (apicarto) → IGN BD TOPO / altimétrie / CLC → GPU → Géorisques → OSM
→ calculs spatiaux (shapely / pyproj) → JSON consolidé et sourcé → rapport LLM (Gemini 3 Flash).
Chaque module de source est indépendant et remplaçable ; tout appel externe passe par `sources.fetch_json`
(cache Mongo `env_cache`, journalisation de la source et de la date de récupération).
"""
