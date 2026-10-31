# Durability and Monopoly Revisited, Simulating Coase (1972)

*Technical companion to the essay in the [README](../README.md). Brendyn Beasley.*

## Abstract

Coase (1972) argued that a monopolist selling a perfectly durable good cannot charge the monopoly price. Buyers expect it to keep cutting the price after each round of sales, so the price falls to the competitive level, and does so almost instantly if selling is costless. Coase also proposed ways out: commitment, leasing and reduced durability. This study formalises the argument in two standard models and computes the results.

In an infinite-horizon game with uniform valuations, the seller's opening price is √(1−δ)/(1+√(1−δ)). It falls to cost as the time between price cuts shrinks. With a 10% annual interest rate, profit drops from 47% of the monopoly level with yearly price changes to 0.7% with hourly changes.

In a two-period model, leasing restores the full monopoly profit (0.50 against 0.45 from selling). A selling monopolist that can choose durability builds an inefficiently short-lived good whenever unit production cost is below 0.2, while a lessor and a social planner choose full durability. All four of Coase's main claims hold in these models. The durability result holds only when production is cheap.

## 1. Introduction

Coase's note is eight pages long, contains no equations and has two diagrams. Its argument is simple. A landowner owns all the land in a country, and the textbook monopoly rule says to sell the quantity OM where marginal revenue is zero, at price OA (Figure I). But after OM is sold, the owner still holds MQ and can make more money by selling some of it. The resulting price fall lands on those who already bought. Repeating this logic, the owner ends up selling the entire stock OQ. Buyers who understand this will not pay more than the competitive price OB. In Coase's words, a monopolist of a durable good faces a demand schedule that is "infinitely elastic at the competitive price."

The problem is one of commitment, or time inconsistency. The monopolist would like to promise to restrict supply, but the promise is not credible once the first sales are made. Coase lists several remedies, namely a contractual promise not to sell more, a buy-back guarantee, leasing instead of selling, donating the surplus stock, and making the good less durable.

This study asks whether Coase's claims survive when the argument is written as an explicit game and solved numerically. We answer with three exercises, all reproducible with the code in this repository.

## 2. Model A: the Coase conjecture

**Setup.** A unit mass of buyers has valuations v ~ U[0, 1], where v is the present value of the services of one unit. Each buyer wants at most one unit. The seller has constant marginal cost c, normalised to 0 without loss of generality: the c > 0 case is a rescaling. Prices are set at t = 0, 1, 2, … and both sides discount by δ per period. The seller cannot commit to future prices.

**Equilibrium.** High-valuation buyers buy first, so the state is the highest remaining valuation x. We look for the stationary linear equilibrium (Stokey 1981; Gul, Sonnenschein & Wilson 1986):

- the seller moves the cutoff from x to y = λx and charges p = γx;
- the marginal buyer y is indifferent between buying now and next period:
  y − p = δ(y − γy), which gives p = (1 − δ + δγ)·y;
- the seller's value is W(x) = w·x², and its first-order condition pins down λ.

Solving the three conditions gives λ = 1/(1+√(1−δ)), an opening price p₀ = 1 − λ, and profit p₀/2. The code solves the system numerically and checks it against this closed form (agreement to 1e-9). It also checks by brute-force value iteration that the seller has no profitable deviation.

**Results.** As δ → 1, meaning the seller can cut prices ever more often, the opening price and profit go to zero, which is the competitive outcome (Figure 2A). To give δ a real-world meaning, we set δ = e^(−rΔ) with r = 10% per year and vary the period length Δ:

| Time between price cuts | δ | Opening price | Profit as % of monopoly |
|---|---|---|---|
| 1 year | 0.9048 | 0.236 | 47.2% |
| 1 quarter | 0.9753 | 0.136 | 27.2% |
| 1 month | 0.9917 | 0.084 | 16.7% |
| 1 week | 0.9981 | 0.042 | 8.4% |
| 1 day | 0.9997 | 0.016 | 3.3% |
| 1 hour | 0.99999 | 0.003 | 0.7% |

This is the formal version of Coase's "twinkling of an eye." Figure 3 shows the skimming path. With weekly price changes, about 90% of the eventual buyers are served within a year, at prices far below the monopoly price of 0.5.

**Commitment and leasing.** If the seller can commit (or, equivalently here, offers a buy-back guarantee at the monopoly price), it charges 0.5 and earns 0.25 regardless of δ. A lessor sets a rental price of (1−δ)/2 each period and earns the same present value, 0.25. This confirms Coase's claim that these arrangements restore monopoly power.

## 3. Model B: selling, leasing and durability

To study durability we use a two-period model in the spirit of Bulow (1982, 1986).

**Setup.** In each period, demand for the good's services is P = 1 − S, where S is the stock of services in use. A unit built in period 1 provides 1 unit of service in period 1 and θ ∈ [0, 1] units in period 2. θ = 1 is fully durable, θ = 0 lasts one period. Each new unit costs c to build. The discount factor is δ = 1.

- **Selling.** In period 2 the seller ignores the effect of new sales on the value of units already sold. It sells q₂ = max(0, (1 − θq₁ − c)/2). Period-1 buyers anticipate this, so a unit sells for (1 − q₁) + θ·p₂.
- **Leasing.** The seller keeps ownership and chooses the whole service path, so it absorbs any fall in value.
- **Planner.** Maximises total surplus.

**Results.**

1. *Leasing beats selling.* With θ = 1 and c = 0, selling earns 0.45 (q₁ = 0.4, q₂ = 0.3) while leasing earns 0.50. These are Bulow's (1982) numbers. Leasing weakly beats selling at every θ and c tested.
2. *A one-period good has no durability problem.* At θ = 0 selling and leasing give the same profit, because there is no old stock to devalue.
3. *Planned obsolescence.* When a selling monopolist chooses θ, it trades off two forces. Higher durability saves on production cost, which is efficient. Lower durability reduces the commitment problem, which is what Coase pointed to. The chosen θ* rises smoothly from 0 at c = 0 to 1 at c = 0.2 (Figure 4B). Over this range the selling monopolist builds a good that wears out too early, while the lessor and the planner choose θ = 1. For c ≥ 0.2 the production saving dominates and the seller also chooses full durability.

The third result refines Coase's claim. Reduced durability is a profitable escape only when building new units is cheap relative to what the monopolist loses from the commitment problem.

## 4. Discussion

The simulations support Coase's four main claims. Without commitment, a durable-goods monopolist's price falls toward the competitive level, and it falls faster the more often the seller can change its price. Leasing, commitment and buy-backs restore monopoly profit. Reduced durability can be profitable, though only under some cost conditions.

The models help explain several real business practices, including leasing by firms such as IBM and Xerox in the mid-20th century, buy-back guarantees, "limited editions" that promise a fixed quantity, and frequent new product versions that make old ones obsolete. They also bear on competition policy. A single seller of a durable good may have far less market power than its market share suggests, and practices that look anticompetitive, such as leasing-only contracts, may be the only way such a seller can earn monopoly profit.

The models use linear demand, uniform valuations, a stationary market and constant marginal cost. Coase himself flags three qualifications that are not modelled here. Rising marginal cost spreads production over time. Reputation may matter, since the seller may not want to disappoint buyers' expectations, and Ausubel and Deneckere (1989) show that reputational equilibria can support near-monopoly prices. Growing demand, in the form of new buyers arriving over time, weakens the conjecture (Sobel 1991).

Natural extensions would add a stream of new buyers to Model A, build a multi-period durability model with depreciation, use non-uniform valuation distributions including the "gap" case where cost is below the lowest valuation, and test the predictions on data, for example the speed of price declines for durable products sold by dominant firms.

## References

- Ausubel, L., & Deneckere, R. (1989). Reputation in Bargaining and Durable Goods Monopoly. *Econometrica*, 57(3), 511–531.
- Bulow, J. (1982). Durable-Goods Monopolists. *Journal of Political Economy*, 90(2), 314–332.
- Bulow, J. (1986). An Economic Theory of Planned Obsolescence. *Quarterly Journal of Economics*, 101(4), 729–749.
- Coase, R. H. (1972). Durability and Monopoly. *Journal of Law & Economics*, 15(1), 143–149.
- Gul, F., Sonnenschein, H., & Wilson, R. (1986). Foundations of Dynamic Monopoly and the Coase Conjecture. *Journal of Economic Theory*, 39(1), 155–190.
- Sobel, J. (1991). Durable Goods Monopoly with Entry of New Consumers. *Econometrica*, 59(5), 1455–1485.
- Stokey, N. (1981). Rational Expectations and Durable Goods Pricing. *Bell Journal of Economics*, 12(1), 112–128.

## Figures

![Figure 1](../figures/fig1_coase_figures.png)
![Figure 2](../figures/fig2_coase_conjecture.png)
![Figure 3](../figures/fig3_price_paths.png)
![Figure 4](../figures/fig4_leasing_and_durability.png)
