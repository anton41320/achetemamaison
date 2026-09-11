"""Diagnostic: hedonic vs comparables bias by type on recent real sales."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient

import hedonic
from estimator import NoDataError, estimate


async def main(n=120):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    model = await hedonic.load_model(db)
    rows = {"maison": [], "appartement": []}
    for t in rows:
        sample = await db.dvf_sales.aggregate([{"$match": {"type": t, "year": {"$gte": 2025}}}, {"$sample": {"size": n}}]).to_list(n)
        for s in sample:
            lon, lat = s["location"]["coordinates"]
            try:
                est = await estimate(db, lat=lat, lon=lon, code_commune=s["code_commune"], ptype=t, surface=s["surface"],
                                     condition="correct", year_built=None, land_surface=s.get("land_surface") if t == "maison" else None,
                                     exclude_mutation_id=s["mutation_id"])
            except NoDataError:
                continue
            local = await hedonic.local_effect(db, model, lat=lat, lon=lon, ptype=t)
            h = hedonic.explain(model, local=local, surface=s["surface"], rooms=s.get("rooms") or 3, land=s.get("land_surface"), ptype=t,
                                code_commune=s["code_commune"], commune=s["commune"], dept=s["dept"], condition_pct=0, condition_label="",
                                year_pct=0, year_label=None, comparables_value=est.value)
            rows[t].append((s["price"], est.value, h.value, s["code_commune"] in model["commune_effects"]))
    for t, r in rows.items():
        a = np.array([[p, c, h] for p, c, h, _ in r], dtype=float)
        eff = np.array([e for *_, e in r])
        print(t, len(a))
        print("  comparables: median log-ratio %.3f  medAPE %.1f%%" % (np.median(np.log(a[:, 1] / a[:, 0])), np.median(np.abs(a[:, 1] - a[:, 0]) / a[:, 0]) * 100))
        print("  hedonic    : median log-ratio %.3f  medAPE %.1f%%" % (np.median(np.log(a[:, 2] / a[:, 0])), np.median(np.abs(a[:, 2] - a[:, 0]) / a[:, 0]) * 100))
        print("  median |log(hed/comp)| %.3f ; agree<10%% %.0f%%" % (np.median(np.abs(np.log(a[:, 2] / a[:, 1]))), (np.abs(a[:,2]/a[:,1]-1)<0.10).mean()*100))
        print("  hedonic/comp median ratio %.3f ; with commune effect %d/%d" % (np.median(a[:, 2] / a[:, 1]), eff.sum(), len(eff)))
        for flag in (True, False):
            m = eff == flag
            if m.sum():
                print("   commune_eff=%s: hed/comp %.3f hed medAPE %.1f comp medAPE %.1f" % (flag, np.median(a[m, 2] / a[m, 1]),
                      np.median(np.abs(a[m, 2] - a[m, 0]) / a[m, 0]) * 100, np.median(np.abs(a[m, 1] - a[m, 0]) / a[m, 0]) * 100))


asyncio.run(main())
