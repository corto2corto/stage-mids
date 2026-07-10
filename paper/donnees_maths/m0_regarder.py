"""Module 0 — regarder la serie 'gouvernement' (Le Monde, 2023-2024)."""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("paper/donnees_maths/gouvernement_lemonde.csv")
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df["f_t"] = df["X_t"] / df["N_t"]

# --- quelques chiffres ---
print("jours          :", len(df))
print("X_t  moyenne   :", round(df["X_t"].mean(), 1))
print("X_t  variance  :", round(df["X_t"].var(), 1))
print("N_t  moyenne   :", round(df["N_t"].mean(), 0))
print("f_t  moyenne   :", round(df["f_t"].mean(), 6))
print("correlation X_t vs N_t :", round(df["X_t"].corr(df["N_t"]), 2))

# --- 3 graphes ---
fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
ax[0].plot(df["date"], df["X_t"], lw=.7); ax[0].set_ylabel("X_t (compte brut)")
ax[1].plot(df["date"], df["N_t"], lw=.7, color="gray"); ax[1].set_ylabel("N_t (total mots/jour)")
ax[2].plot(df["date"], df["f_t"], lw=.7, color="C1"); ax[2].set_ylabel("f_t = X_t / N_t")
ax[2].set_xlabel("date")
fig.suptitle("« gouvernement » — Le Monde 2023-2024")
fig.tight_layout()
fig.savefig("paper/donnees_maths/m0_regarder.png", dpi=110)
print("\n-> graphe : paper/donnees_maths/m0_regarder.png")
