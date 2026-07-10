"""Module 0 — la variance de f_t depend de N_t (fiabilite variable)."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("paper/donnees_maths/gouvernement_lemonde.csv")
df["f_t"] = df["X_t"] / df["N_t"]

lam = df["f_t"].mean()  # estimation grossiere de lambda
print("lambda estime (freq moyenne) :", round(lam, 6))

# On coupe les jours en 2 groupes : petit volume vs gros volume
median_N = df["N_t"].median()
petit = df[df["N_t"] <= median_N]
gros  = df[df["N_t"] >  median_N]

print(f"\nJours PETIT volume (N_t <= {median_N:.0f}) : ecart-type de f_t = {petit['f_t'].std():.6f}")
print(f"Jours GROS  volume (N_t >  {median_N:.0f}) : ecart-type de f_t = {gros['f_t'].std():.6f}")
print("\n-> f_t varie plus quand N_t est petit : la fiabilite n'est PAS constante.")

# Ecart-type theorique de f_t attendu : sqrt(lambda / N_t)
df["ecart_theo_ft"] = np.sqrt(lam / df["N_t"])
fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(df["N_t"], df["f_t"], s=6, alpha=.4, label="f_t observe")
# bande theorique lambda +/- 2 ecarts-types
ordre = df.sort_values("N_t")
ax.plot(ordre["N_t"], lam + 2*ordre["ecart_theo_ft"], color="red", lw=1, label="lambda ± 2·sqrt(lambda/N_t)")
ax.plot(ordre["N_t"], lam - 2*ordre["ecart_theo_ft"], color="red", lw=1)
ax.axhline(lam, color="black", lw=.8, ls="--", label="lambda")
ax.set_xlabel("N_t (volume du jour)"); ax.set_ylabel("f_t")
ax.set_title("f_t se resserre autour de lambda quand N_t grandit")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("paper/donnees_maths/m0_fiabilite.png", dpi=110)
print("-> graphe : paper/donnees_maths/m0_fiabilite.png")
