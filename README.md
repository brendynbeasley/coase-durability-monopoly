# Durability and Monopoly: a computational study of Coase (1972)

> Can a monopolist that sells a good that lasts forever actually charge a monopoly price?

R. H. Coase argued **no**. Once the monopolist has sold some units at the high price, it has every reason to sell more at a lower price, because the price cut hurts the earlier buyers, not the monopolist. Buyers see this coming and refuse to pay more than the competitive price. The monopolist ends up competing with its own future self.

This repository turns Coase's verbal argument into models you can run, recreates his two figures, and tests each of his main claims:

| Coase's claim | Model | Result here |
|---|---|---|
| Without commitment, price falls to the competitive level | Infinite-horizon dynamic game | ✅ Opening price → cost as price cuts become frequent |
| "In the twinkling of an eye" if selling is costless | Same, varying the time between price cuts | ✅ Profit falls from 47% (yearly cuts) to 0.7% (hourly) of monopoly profit |
| Leasing restores monopoly profit | Two-period model + infinite horizon | ✅ Leasing earns the full monopoly profit |
| Making the good less durable can raise profit | Two-period model with durability θ | ✅ but only when production is cheap (c < 0.2) |

![Figures I and II](figures/fig1_coase_figures.png)

## Key results

### 1. The Coase conjecture

Buyers have valuations uniform on [0, 1] and the seller can cut its price once per period. In the stationary equilibrium the seller "skims" down the demand curve. The opening price has a closed form:

$$p_0 = \frac{\sqrt{1-\delta}}{1+\sqrt{1-\delta}} \;\longrightarrow\; 0 \text{ (= cost) as } \delta \to 1$$

| Time between price cuts (r = 10%/yr) | Opening price | Profit as % of monopoly |
|---|---|---|
| 1 year | 0.236 | 47.2% |
| 1 quarter | 0.136 | 27.2% |
| 1 month | 0.084 | 16.7% |
| 1 week | 0.042 | 8.4% |
| 1 day | 0.016 | 3.3% |
| 1 hour | 0.003 | 0.7% |

The monopoly price, which a seller that could commit would charge, is 0.5.

![Coase conjecture](figures/fig2_coase_conjecture.png)
![Price paths](figures/fig3_price_paths.png)

### 2. Leasing and planned obsolescence

In a two-period model (after Bulow 1982), selling a fully durable good earns **0.45** against **0.50** from leasing. A leasing monopolist keeps the loss from any later price cut, so it has no reason to flood the market.

If the seller can choose durability θ, it builds a good that wears out too early whenever production is cheap. A leasing monopolist and a social planner both pick full durability.

| Unit cost c | θ chosen by seller | θ chosen by lessor | θ chosen by planner |
|---|---|---|---|
| 0.00 | 0.00 | 1.00 | 1.00 |
| 0.05 | 0.21 | 1.00 | 1.00 |
| 0.10 | 0.44 | 1.00 | 1.00 |
| 0.15 | 0.71 | 1.00 | 1.00 |
| ≥ 0.20 | 1.00 | 1.00 | 1.00 |

At c = 0 durability costs nothing, so the lessor and planner are indifferent between all θ. Ties are reported as θ = 1.

![Leasing and durability](figures/fig4_leasing_and_durability.png)

The full write-up is in [`paper/paper.md`](paper/paper.md).

## Repository layout

```
src/coase/
  static.py       Figures I and II (linear demand)
  dynamic.py      Infinite-horizon durable-goods monopoly (Coase conjecture)
  durability.py   Two-period selling vs leasing, choice of durability
scripts/
  run_experiments.py   Runs everything, writes figures/ and results/
tests/            23 tests: closed forms, Bulow's numbers, brute-force checks
figures/          Generated charts
results/          Generated CSVs and summary.md
paper/paper.md    Research write-up
```

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest
python scripts/run_experiments.py
```

The whole run takes about 15 seconds on a laptop.

## How the results are checked

- The dynamic equilibrium matches the known closed form λ = 1/(1+√(1−δ)) to 1e-9.
- A brute-force value iteration on a grid confirms the seller has no profitable deviation.
- The two-period model reproduces Bulow's (1982) published numbers: 0.45 for selling, 0.50 for leasing.
- With a good that lasts one period (θ = 0), selling and leasing coincide, as they should.

## Limitations and extensions

- The models use linear demand and uniform valuations. Other distributions would change the numbers but not the direction of the results.
- Coase's caveats about **rising marginal cost**, **reputation** and **growing demand** are not modelled yet. Each would make a natural extension:
  - Reputational equilibria (Ausubel & Deneckere 1989) can sustain prices near the monopoly level.
  - Growing demand or population entry (Sobel 1991) weakens the conjecture.
- The durability model has two periods. A multi-period version with depreciation would be a good next step.

## References

- Coase, R. H. (1972). Durability and Monopoly. *Journal of Law & Economics*, 15(1), 143–149. [JSTOR](https://www.jstor.org/stable/725018)
- Stokey, N. (1981). Rational Expectations and Durable Goods Pricing. *Bell Journal of Economics*, 12(1), 112–128.
- Bulow, J. (1982). Durable-Goods Monopolists. *Journal of Political Economy*, 90(2), 314–332.
- Bulow, J. (1986). An Economic Theory of Planned Obsolescence. *Quarterly Journal of Economics*, 101(4), 729–749.
- Gul, F., Sonnenschein, H., & Wilson, R. (1986). Foundations of Dynamic Monopoly and the Coase Conjecture. *Journal of Economic Theory*, 39(1), 155–190.
- Ausubel, L., & Deneckere, R. (1989). Reputation in Bargaining and Durable Goods Monopoly. *Econometrica*, 57(3), 511–531.
- Sobel, J. (1991). Durable Goods Monopoly with Entry of New Consumers. *Econometrica*, 59(5), 1455–1485.

The original paper is not included here because of copyright. It is available through JSTOR.

## License

Code is released under the MIT License (see `LICENSE`).
