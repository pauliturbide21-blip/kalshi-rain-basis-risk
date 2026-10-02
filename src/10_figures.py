"""The three figures of the paper, drawn from results/ and data/.
Comments in the code are in French."""
import os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{HERE}/figures"; os.makedirs(OUT, exist_ok=True)
INK = "#1a1a1a"; MID = "#6b6b6b"; LIGHT = "#d9d9d9"; BLUE = "#1f5fa8"; ORANGE = "#d4531c"; RED = "#b8322a"; W = 6.5
plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix", "font.size": 8.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MID, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.titlesize": 8.5, "axes.titleweight": "bold", "legend.frameon": False, "figure.facecolor": "white", "pdf.fonttype": 42})
def save(name): plt.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight"); plt.savefig(f"{OUT}/{name}.png", dpi=220, bbox_inches="tight"); plt.close(); print("saved", name)

# ------------------------------------------------------------------ fig 1
cal = pd.read_csv(f"{HERE}/results/calibration.csv"); cal = cal[cal.ville == "NYC"] if "ville" in cal else cal
h1 = pd.read_csv(f"{HERE}/results/trigger.csv"); h1 = h1[h1.ville == "NYC"].iloc[0]
fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw={"width_ratios": [1.0, 1.0], "wspace": 0.38})
a.plot([0, 1], [0, 1], ls=(0, (4, 3)), color=MID, lw=0.9, label="Perfect calibration")
for src, mk, col, mfc, lab in (("kalshi_veille_12h", "o", BLUE, BLUE, "Kalshi price"), ("mos_nbs", "s", ORANGE, "white", "NWS forecast")):
    s = cal[cal.source == src]
    if len(s):
        a.errorbar(s.prix_moyen, s.frequence, yerr=[s.frequence - s.freq_ic_bas, s.freq_ic_haut - s.frequence], fmt=mk, color=col, mfc=mfc, ms=4, capsize=2, lw=0.8, label=f"{lab} ($n$ = {int(s.n.sum())})")
a.set_xlim(0, 1); a.set_ylim(0, 1.02); a.set_xlabel("Announced probability (decile mean), day before at noon"); a.set_ylabel("Observed frequency of Yes settlement")
a.set_title("(a) The price is well calibrated", loc="left"); a.legend(loc="upper left", fontsize=7.2); a.grid(color="#eeeeee", lw=0.6); a.set_axisbelow(True)
groups = [("A", "pays\nlost", h1.paye_perte, h1.paye_perte_ic_bas, h1.paye_perte_ic_haut, INK, None),
          ("B", "pays\nnot lost", h1.paye_sans_perte, h1.paye_sans_perte_ic_bas, h1.paye_sans_perte_ic_haut, "white", "///"),
          ("C", "silent\nlost", h1.perte_non_payee, 0, 0, "white", None),
          ("D", "silent\nnot lost", h1.sec, h1.sec_ic_bas, h1.sec_ic_haut, LIGHT, None)]
for i, (g, lab, v, lo, hi, fc, ht) in enumerate(groups):
    b.bar(i, v * 100, color=fc, edgecolor=INK, hatch=ht, lw=0.9, width=0.62)
    if hi > 0: b.errorbar(i, v * 100, yerr=[[(v - lo) * 100], [(hi - v) * 100]], color=INK, capsize=2.5, lw=0.8)
    b.text(i, v * 100 + (hi - v) * 100 + 1.8, f"{v*100:.1f}%", ha="center", fontsize=8)
b.set_xticks(range(4)); b.set_xticklabels([f"{g[0]}\n{g[1]}" for g in groups], fontsize=7.8); b.set_ylim(0, 70); b.set_ylabel(f"Share of season days ($n$ = {int(h1.n)})  (%)")
b.set_title("(b) The contract pays on the wrong evenings", loc="left")
b.text(0.5, 52, f"False payouts:\nB / (A + B) = {h1.FP*100:.0f}%", fontsize=8, ha="center")
save("fig1_calibration_trigger")

# ------------------------------------------------------------------ fig 2
cp = pd.read_csv(f"{HERE}/data/season_paths.csv", parse_dates=["date"]); cal_ = pd.read_csv(f"{HERE}/data/calendar.csv", parse_dates=["date"])
gro = cal_[(cal_.nom == "230 Fifth") & (cal_.saison == 2026)][["date", "grosse", "K", "R"]]
def nights(c):
    g = cp[(cp.nom == "230 Fifth") & (cp.contrat == c)].sort_values("date").copy()
    g["sans"] = g.cum_sans.diff().fillna(g.cum_sans); g["avec"] = g.cum_avec.diff().fillna(g.cum_avec)
    return g.merge(gro, on="date").query("grosse == 1").reset_index(drop=True)
nr, npf = nights("reel"), nights("parfait")
contrib_r = np.cumsum(nr.avec.values - nr.sans.values) / 1e3; contrib_p = np.cumsum(npf.avec.values - npf.sans.values) / 1e3
D = nr.D.values; x = np.arange(1, len(nr) + 1)
pay_r = np.diff(np.r_[0, contrib_r])[D == 1]; pay_p = np.diff(np.r_[0, contrib_p])[D == 1]
loss = (nr.R.values[D == 1] * 0.5) / 1e3
fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.3})
for xi in x[D == 1]: a.axvline(xi, color=RED, lw=0.7, alpha=0.5)
a.plot(x, contrib_r, color=BLUE, lw=1.5, marker="o", ms=2.6, label="Kalshi contract (pays on rain, midnight to midnight)")
a.plot(x, contrib_p, color=ORANGE, lw=1.5, ls=(0, (5, 2)), marker="s", ms=2.6, mfc="white", label="Perfect contract (pays on lost evening, 6 p.m.–1 a.m.)")
a.axhline(0, color=MID, lw=0.8); a.set_xlabel("Big nights of the 2026 season at 230 Fifth"); a.set_ylabel("Cumulative contribution of the hedge (k USD)")
a.set_title("(a) Cumulative contribution of the hedge", loc="left"); a.legend(loc="upper left", fontsize=7, bbox_to_anchor=(0.0, 1.0)); a.set_ylim(-110, 110); a.grid(color="#eeeeee", lw=0.6); a.set_axisbelow(True)
a.text(x[-1] + 0.5, contrib_r[-1], f"−{abs(contrib_r[-1]):.0f}k", color=BLUE, fontsize=8, va="center"); a.text(x[-1] + 0.5, contrib_p[-1], f"+{contrib_p[-1]:.0f}k", color=ORANGE, fontsize=8, va="center"); a.set_xlim(0, x[-1] + 5)
k = np.arange(len(pay_r)); w = 0.34
b.bar(k - w / 2, pay_r, w, color=BLUE, edgecolor=INK, lw=0.5, label="Kalshi contract"); b.bar(k + w / 2, pay_p, w, color="white", edgecolor=ORANGE, hatch="////", lw=0.9, label="Perfect contract")
b.axhline(loss.mean(), color=RED, ls=(0, (4, 3)), lw=1.0); b.text(len(k) - 0.4, loss.mean() + 1.5, f"loss per lost evening ≈ {loss.mean():.0f}k", color=RED, ha="right", fontsize=7.5)
b.set_xticks(k); b.set_xticklabels([str(i + 1) for i in k]); b.set_xlabel("Lost evenings, in order"); b.set_ylabel("Payout net of premium paid (k USD)"); b.set_ylim(0, 66)
b.set_title("(b) Payout on each lost evening", loc="left"); b.legend(loc="center left", bbox_to_anchor=(0.0, 0.62), fontsize=7); b.grid(axis="y", color="#eeeeee", lw=0.6); b.set_axisbelow(True)
save("fig2_pathways")
print("fig2 check: end contrib real", round(contrib_r[-1]), "perfect", round(contrib_p[-1]), "| lost-evening payouts real", np.round(pay_r).tolist(), "perfect", np.round(pay_p).tolist(), "| loss", np.round(loss).tolist())
print("fig2 check: sd across big nights real", round(nr.avec.std(ddof=0) / 1e3, 1), "perfect", round(npf.avec.std(ddof=0) / 1e3, 1), "n big nights", len(nr))

# ------------------------------------------------------------------ fig 3
sc = pd.read_csv(f"{HERE}/results/hedge_equal_coverage.csv")
sc["worst"] = (sc.pire5_avec - sc.pire5_sans) / sc.R_saison * 100; sc["e"] = sc.ederington_e * 100; sc["eng"] = sc.engagement / sc.R_saison * 100
real = sc[(sc.contrat == "reel") & (sc.seuil == 0.5) & (sc.chargement == 0)]; perf = sc[(sc.contrat == "parfait") & (sc.seuil == 0.2) & (sc.chargement == 0)]
order = real[real.execution == "mid"].sort_values("e", ascending=False).nom.tolist()
fig, axes = plt.subplots(1, 2, figsize=(W, 3.5), sharey=True, gridspec_kw={"wspace": 0.1})
series = ((real, "mid", "o", BLUE, BLUE, "Kalshi contract, mid-book"), (real, "quart_spread", "o", BLUE, "white", "Kalshi contract, quarter spread"),
          (perf, "mid", "s", ORANGE, ORANGE, "Perfect contract, mid-book"), (perf, "quart_spread", "s", ORANGE, "white", "Perfect contract, quarter spread"))
for ax, col, ttl, xl in ((axes[0], "worst", "(a) Worst-of-twenty season", "Gain (% of season revenue)"), (axes[1], "e", "(b) Variance reduction", "Hedging effectiveness (%)")):
    for df, ex, mk, c, mfc, lab in series:
        d = df[df.execution == ex].set_index("nom").loc[order]
        ax.scatter(d[col].values, np.arange(len(order))[::-1], marker=mk, s=26, color=c, facecolor=mfc, linewidths=1.1, label=lab if col == "worst" else None, zorder=3)
    ax.axvline(0, color=MID, lw=0.8); ax.set_xlabel(xl); ax.set_title(ttl, loc="left"); ax.grid(axis="x", color="#eeeeee", lw=0.6); ax.set_axisbelow(True)
axes[0].set_yticks(range(len(order))); axes[0].set_yticklabels(order[::-1], fontsize=7.8); axes[0].set_ylim(-0.7, len(order) - 0.3)
h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=2, fontsize=7.4, bbox_to_anchor=(0.5, -0.1))
save("fig3_venues")
for ex in ("mid", "quart_spread"):
    r_, p_ = real[real.execution == ex], perf[perf.execution == ex]
    print(f"fig3 check {ex}: real worst median {r_.worst.median():.2f} (#>0: {(r_.worst>0).sum()}) e {r_.e.median():.1f} eng {r_.eng.median():.2f} | perfect worst {p_.worst.median():.2f} (#>0: {(p_.worst>0).sum()}) e {p_.e.median():.1f} eng {p_.eng.median():.2f}")
