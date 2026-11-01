# Does Durability Weaken Monopoly? Testing Coase (1972) on U.S. Manufacturing

Ronald Coase argued in 1972 that a firm selling a durable good cannot hold a monopoly price for long, because it ends up competing with the units it has already sold and with the price cuts its buyers expect it to make. If he was right, market concentration should do less to raise prices in industries that make long-lived goods than in industries whose products are used up. This repository tests that prediction on every U.S. manufacturing industry in the five Economic Censuses from 2002 to 2022, with controls for import competition, advertising and R&D, and pairs the test with simulations of the underlying theory. Everything runs from public data with one command.

The answer depends on which comparison you make. **Across industries, the prediction holds clearly.** In nondurable industries, higher concentration goes with higher price-cost margins, the pattern Joe Bain documented in 1951. In industries making long-lived goods bought by households and equipment investors, the relationship is flat. The gap between the two slopes is −0.11 (p = 0.03), rises to −0.16 (p = 0.01) once import penetration, advertising and R&D are controlled for, and is negative in every census year and in all 18 cross-industry specifications. **Within industries over time, it does not hold.** When an industry's own concentration rises between censuses, its margin rises at least as much in long-lived durable industries as in nondurable ones. A continuous measure of product service life also shows no effect within the durable group. The evidence is consistent with Coase's mechanism operating as a persistent feature of durable-goods markets, but it cannot rule out fixed industry differences that I have not measured.

![Concentration and margins by product type](figures/fig5_concentration_margins.png)

## Research question and hypotheses

Coase's argument is about commitment. A monopolist that sells a good lasting forever would like to restrict supply, but once the first buyers have paid, it gains by selling more, and buyers who anticipate this refuse to pay the monopoly price. The simulations in this repository show the effect is large. A seller who can change its price once a month keeps only 17 percent of the monopoly profit, and one who can change it weekly keeps 8 percent (see [the theory section](#the-theory-behind-the-test)). The empirical question is whether this shows up in industry data.

- **H1 (Bain).** Among nondurable industries, more concentrated industries earn higher price-cost margins.
- **H2 (Coase).** The concentration-margin slope is flatter for durable-goods industries.
- **H3.** The flattening is strongest for long-lived goods held by final owners, which is the case Coase described, and grows with the product's service life.

## Data

| Source | Years | What it provides |
|---|---|---|
| Census Bureau, Economic Census, concentration tables | 2002, 2007, 2012, 2017, 2022 | Share of sales held by the 4, 8, 20 and 50 largest firms, HHI, number of firms, by 6-digit NAICS |
| Census Bureau, Economic Census, manufacturing statistics | 2002–2022 | Shipments, payroll, benefits, value added, gross depreciable assets, advertising expense |
| Census Bureau, Related Party Trade files | 2007–2022 | Imports and domestic exports by 6-digit NAICS, for import penetration |
| NSF, Business Enterprise R&D Survey, table 17 | 2017, 2022 | R&D as a share of domestic sales, by industry (3- to 6-digit NAICS) |
| BEA, 2017 detailed Use table | 2017 | Where each product goes, which identifies goods bought by final owners |
| BEA, PEQ and PCE bridge tables, fixed-asset accounts | 2017 | Service life of the equipment and consumer durables each product is sold into |

The panel has 2,014 industry-years, of which 1,982 have complete data for the baseline specification, covering $27 trillion of shipments over the five censuses. All files are downloaded directly from government servers with no API key. Their SHA-256 hashes are recorded in [`data/processed/manifest.json`](data/processed/manifest.json), and the processed panel is committed, so the results can be reproduced even if an agency later revises a file.

## Method

The outcome is the Collins-Preston price-cost margin.

$$\text{PCM} = \frac{\text{value added} - \text{payroll}}{\text{shipments}}$$

Industries are sorted into three groups. *Nondurable* and *durable* follow the Census Bureau's M3 definitions by 3-digit NAICS. A durable industry is *durable final* when at least half of its domestic use goes to household consumption or equipment investment, according to the BEA Use table. The remaining durable industries are *durable intermediate*.

The main specification pools all five censuses and estimates a separate concentration slope for each group,

$$\text{PCM}_{it} = \alpha_g + \beta_g\,\text{CR4}_{it} + \gamma\,\frac{K}{S}_{it} + \delta \log S_{it} + \theta' X_{it} + \tau_t + \varepsilon_{it}$$

where *K/S* is gross depreciable assets over shipments, *S* is shipments, τ is a census-year effect, and *X* holds the additional controls.

| Control | Definition | Coverage |
|---|---|---|
| Import penetration | imports / (shipments + imports − exports), capped at 1 | 2007–2022 |
| Advertising intensity | advertising expense / shipments | all years, 95% of industries |
| R&D intensity | NSF R&D-to-sales ratio for the industry, averaged over 2017 and 2022 and held fixed | all years |

Standard errors are clustered by industry. H2 and H3 predict β for durable final goods to be below β for nondurables.

Service life is measured from BEA's fixed-asset accounts. For each equipment and consumer-durable category, depreciation divided by the average net stock gives the geometric depreciation rate *d*, and 1/*d* is the mean service life. Each product's service life is the average over the categories it is sold into, weighted by sales in the PEQ and PCE bridge tables. Values range from about 1 year for vehicle parts to 19 years for electrical transformers.

## Results

### Across industries

| | Baseline | + Import penetration | + Advertising | + R&D | + All controls |
|---|---|---|---|---|---|
| Nondurable slope | 0.121 (0.042) | 0.134 (0.052) | 0.117 (0.042) | 0.123 (0.043) | 0.143 (0.052) |
| Durable intermediate slope | 0.035 (0.027) | 0.025 (0.033) | 0.040 (0.029) | 0.027 (0.027) | 0.033 (0.034) |
| Durable final slope | 0.012 (0.028) | −0.008 (0.032) | 0.007 (0.027) | 0.001 (0.029) | −0.014 (0.031) |
| **Final minus nondurable** | **−0.109 (p = 0.032)** | **−0.142 (p = 0.019)** | **−0.110 (p = 0.028)** | **−0.122 (p = 0.018)** | **−0.157 (p = 0.010)** |
| N | 1,982 | 1,353 | 1,920 | 1,982 | 1,318 |

To put the slopes in context, moving a nondurable industry from a four-firm share of 20 percent to 80 percent is associated with a margin about 7 percentage points higher. The same move in a long-lived durable industry is associated with no change. The controls matter in the direction one would hope. Long-lived durable industries face much more import competition than nondurable ones (median import penetration 0.37 against 0.16), which could have explained flat margins, but controlling for it makes the gap larger rather than smaller.

A permutation test that randomly reassigns the three product types across industries 2,000 times produces a gap as negative as the observed one in 1.8 percent of draws.

### Bain's 70 percent test, by product type

| Group | Margin gap, CR8 ≥ 70% vs. < 70% (SE) |
|---|---|
| Nondurable | +4.3 points (1.1) |
| Durable intermediate | +1.3 points (0.9) |
| Durable final (long-lived) | −0.1 points (0.9) |

![Bain split](figures/fig7_bain_split.png)

### Across industries versus within industries

The cross-industry gap is negative in every census year, from −0.05 in 2002 to −0.19 in 2022. The within-industry evidence points the other way. With industry fixed effects the durable-final slope is larger than the nondurable one (gap +0.08, p = 0.33), and in stacked changes between consecutive censuses it is clearly larger (+0.18, p = 0.01). The reversal comes from 2002–2017 and is strongest over 2007–2012, the period of the Great Recession. In 2017–2022 the within-industry gap is negative.

![Between versus within](figures/fig9_between_within.png)

These two results answer different questions. The cross-industry comparison asks whether durable-goods markets with high concentration earn less than one would expect from concentration alone, which is the long-run, structural form of Coase's argument. The within-industry comparison asks how margins respond when an industry's concentration changes over five years. Demand for durable goods swings with the business cycle far more than demand for nondurables, and downturns push out weaker firms while squeezing margins, so short-run changes in concentration and margins can move together for reasons that have nothing to do with Coase. That interpretation is plausible but not something the data can prove. The honest summary is that the Coase pattern is a robust feature of the cross-section, and that it is not identified from within-industry variation.

### Service life

Among durable industries, the concentration slope does not vary with the product's service life (interaction −0.0008 per year of life, SE 0.0061, p = 0.90). A good that lasts 15 years shows the same flat relationship as one that lasts 4. What separates the groups is whether a durable good is held by its final owner or used up inside another product, not how many years it lasts. This part of H3 is not supported.

### Robustness

![Robustness](figures/fig6_slopes_by_specification.png)

Across 18 cross-industry specifications, the gap is negative in every one, significant at 5 percent in 12 and at 10 percent in 14. It is weakest with 3-digit subsector fixed effects (−0.012, p = 0.78), which compare only industries within the same subsector and remove most of the difference between durable and nondurable goods, and with shipment weights (−0.114, p = 0.33), which put most of the weight on a few very large industries such as petroleum refining and motor vehicles. Full tables are in [`results/empirics/summary.md`](results/empirics/summary.md).

## Who controls the concentrated durable markets

Census data identifies industries rather than firms, but it shows where control is concentrated. These are the most concentrated long-lived durable industries in 2022, using the private-buyer definition.

| Industry | Top-4 share | Firms | Shipments ($bn) | Margin |
|---|---|---|---|---|
| Ammunition (except small arms) | 87% | 37 | 4.2 | 0.51 |
| Computer storage devices | 84% | 38 | 4.7 | 0.21 |
| Aircraft | 84% | 234 | 92.8 | 0.24 |
| Motor homes | 83% | 58 | 7.4 | 0.22 |
| Heavy duty trucks | 76% | 84 | 33.1 | 0.18 |
| Small arms ammunition | 75% | 151 | 5.8 | 0.40 |
| Burial caskets | 75% | 62 | 0.7 | 0.33 |
| Travel trailers and campers | 71% | 575 | 27.6 | 0.24 |
| Major household appliances | 70% | 123 | 23.7 | 0.38 |
| Batteries | 69% | 234 | 28.2 | 0.39 |

Aircraft, heavy trucks and motor homes all have four-firm shares above 75 percent and margins well below the manufacturing average of about 0.33. Ammunition is a reminder that the official durable classification is imperfect, since Census counts it as durable even though it is used up.

## Limitations

1. **Correlation, not causation.** The cross-industry gap could reflect fixed industry characteristics other than durability. The within-industry results show this possibility is real.
2. **The price-cost margin is an accounting measure.** It includes returns to capital, advertising and R&D, which the controls address only in part.
3. **National concentration ratios ignore imports and regional markets.** Import penetration is now controlled for, but geographic market definition is not.
4. **Measurement choices.**
   - R&D intensity is available only at a coarse industry level and only from 2015, so it is treated as a fixed industry trait.
   - Import penetration is unavailable for 2002.
   - 2002 capital intensity is carried back from 2007, because the 2002 census did not publish assets.
   - The durable classification inherits quirks such as ammunition counting as durable.
5. **NAICS codes change between censuses.** Industries are matched across years by identical codes, and BEA measures are matched by NAICS prefix.

## The theory behind the test

The `src/coase/dynamic.py` and `src/coase/durability.py` modules solve two standard models of durable-goods monopoly.

| Result | Value |
|---|---|
| Profit of a durable monopolist relative to one that can commit, with yearly / monthly / weekly price changes (10% interest) | 47% / 17% / 8% |
| Two-period profit from selling vs. leasing a fully durable good (Bulow 1982) | 0.45 vs. 0.50 |
| Durability chosen by a selling monopolist when unit cost is low (c < 0.2) | Below the efficient level |

![Coase conjecture](figures/fig2_coase_conjecture.png)

The formal derivations and the full empirical section are in [`paper/technical-paper.md`](paper/technical-paper.md). A plain-language essay on the paper, the industries involved and what is at stake is in [`docs/essay.md`](docs/essay.md).

## Reproduce

Requires Python 3.10 or later. Exact package versions are pinned in `requirements-lock.txt`.

```bash
git clone https://github.com/brendynbeasley/coase-durability-monopoly.git
cd coase-durability-monopoly
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt && pip install -e .
make all
```

`make all` downloads the raw files (about 150 MB), builds `data/processed/industry_panel.csv`, runs the simulations and the empirical analysis, writes every table and figure, and runs the tests. The analysis takes under a minute after the download. Because the processed panel is committed, `make results` and `make test` work without downloading anything.

## Repository layout

```
src/coase/
  data.py          downloads and builds the industry panel (Census, BEA, NSF, trade)
  empirics.py      hypotheses, regressions, robustness, permutation and within-industry tests
  dynamic.py       infinite-horizon durable-goods monopoly (Coase conjecture)
  durability.py    two-period selling vs. leasing and choice of durability
  static.py        Coase's Figures I and II
scripts/
  build_data.py        raw files -> data/processed/industry_panel.csv
  run_empirics.py      empirical tables and figures 5-9
  run_experiments.py   theory tables and figures 1-4
data/processed/    industry panel and manifest of source files with hashes
results/           theory results and results/empirics/
figures/           all charts
paper/             technical paper
docs/essay.md      plain-language essay
tests/             model and data tests
```

## References

- Bain, J. S. (1951). Relation of Profit Rate to Industry Concentration: American Manufacturing, 1936–1940. *Quarterly Journal of Economics*, 65(3), 293–324.
- Bulow, J. (1982). Durable-Goods Monopolists. *Journal of Political Economy*, 90(2), 314–332.
- Bulow, J. (1986). An Economic Theory of Planned Obsolescence. *Quarterly Journal of Economics*, 101(4), 729–749.
- Coase, R. H. (1972). Durability and Monopoly. *Journal of Law & Economics*, 15(1), 143–149. [JSTOR](https://www.jstor.org/stable/725018)
- Collins, N. R., & Preston, L. E. (1969). Price-Cost Margins and Industry Structure. *Review of Economics and Statistics*, 51(3), 271–286.
- Gul, F., Sonnenschein, H., & Wilson, R. (1986). Foundations of Dynamic Monopoly and the Coase Conjecture. *Journal of Economic Theory*, 39(1), 155–190.
- Stokey, N. (1981). Rational Expectations and Durable Goods Pricing. *Bell Journal of Economics*, 12(1), 112–128.
- National Center for Science and Engineering Statistics. Business Enterprise Research and Development Survey, 2017 and 2022. https://ncses.nsf.gov
- U.S. Bureau of Economic Analysis. Input-Output Accounts and Fixed Assets Accounts. https://www.bea.gov
- U.S. Census Bureau. Economic Census, 2002–2022, and Related Party Trade. https://www.census.gov

The original Coase paper is not included because it is under copyright.

## License

Code is released under the MIT License. Census, BEA and NSF data are public domain.
