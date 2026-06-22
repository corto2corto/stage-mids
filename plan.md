# Plan

## Phase 1

- [ ] for the beginning, I think it's better to start with simple, 1d time series. E.g. we explore the appearance of one word/concept/ngram in the corpus, typically $x_t=$ some metric related to the appearance of the concept in (say) Le monde at date $t$, or in all the corpus, etc. 

Ideas of metrics : 
- The raw occurences living in $\mathbb{N}$
- The increments $\delta_t = x_{t} - x_{t-1}$, living in $\mathbb{Z}$
- Same but we could vary the time span (what's the right scale : every day, every 2 days, every week ?)
- number of papers having at least one occurrence of the concept (more robust to outliers)
- if $N_t$ is the total number of concepts at time $t$ then we could maybe use the relative frequency $x_t/N_t$ ?


We need to explore the histogram of $x_t$. 
- plotting the 4 moments (mean/var/skew/kurt)
- fitting a distribution to it (candidates: Poisson, Negative Binomial, Zipf) or mixtures 
- fitting a time series like $x_t \sim P(N_t \lambda_t)$ with $\lambda_t$ an AR process ? 

###  Burst detection

There’s a good old reference https://www.cs.cornell.edu/home/kleinber/bhs.pdf for detecting activity bursts across time. Might be worth looking at it. 

Other possibility: once we have fitted a distribution to whatevere $x_t$ is, we select the $t$ such that $x_t$ is in the top 1% or 5% percentile. 

### Wavelets

Scattering etc. 


## Phase 2


1. Select words for which there is an activity burst across all the corpus of the J = 16 journals
2. Study the multivariate time series $X_t = (x^1_t, …, x^J_t)$ where $x^j_t = $ time series for the use of this concept in journal $j$
3. modify the scattering transform to capture at the same time the activity shape of $x^j_t$ and its correlations with $x^k_t$ for $j,k$. 


## List of concepts

changement climatique

réchauffement

nucléaire

vigilance 

vague de chaleur 

canicule 

climatisation

mathématiques

recherche fondamentale

oqtf

immigration

ultradroite vs extrême droite 

islamo-gauchisme

woke, wokisme, wokiste

ultralibéralisme

sionisme

Palestine

mots liés aux religions : Jésus, Évangile, Coran, Mahomet, Synagogue, Mosquée, Église, Évangélistes, Pape…


## List of Nouns

Bolloré, Stérin, Pigasse, Niel

Noms de personnalités mortes depuis longtemps : De Gaulle, Monet, Marie Curie, Jaurès, Barrès, Poincaré, etc

Lieux : Dubaï, Moscou, Monaco…

Affaires liées à Médiapart : Benalla, Perdriau, Cahuzac, Baupin, Ramadan

Grivaux