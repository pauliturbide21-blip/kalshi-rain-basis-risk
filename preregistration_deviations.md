# Deviations from the pre-registration

The pre-registration (`preregistration.md`, time-stamped 16 September 2026, 19:11 UTC) fixed the definitions of the contract payout (Y), the lost evening (D), the price and fees, the trigger and price diagnostics, and the sensitivity grids. Every deviation is listed here.

1. **Season length.** A first run used 59 days per season, the average number of observed days per year. The pre-registration defines the season as the 153 days from May 1 to September 30; the final version uses 153. The conclusions do not change.
2. **Check that maximum effectiveness equals the squared correlation.** The identity holds exactly at the daily level for a payout at constant price (difference of 10^-4). At the season level, with the actual profit and loss, effectiveness at the optimal ratio is 0.144 instead of 0.225: the gap is the quantified effect of the varying purchase price, not a failure of the check.
3. **Insurer's time window.** The sensitivity grid declared noon to midnight; this window was added to the day table after a first run that used the calendar day as an upper bound. Both versions are reported.
4. **2022 threshold markets.** 126 contracts with other thresholds (for example "more than 0.05 inch") are excluded, as they are not the contract studied. The rule is applied on the ticker name.
5. **Forecast cycle.** The MOS archive time-stamps cycles at 13Z before 2026 and 12Z afterwards; both are read as the previous day's cycle.
6. **Bid-ask spread.** Estimated from hourly candles (ask minus bid of the last candle before purchase), not from trades.
7. **Analyses added after the pre-registration.** The ten-venue panel, the search over 132 hedging settings and the three counterfactuals (perfect contract, informed manager, optimal program) were designed after the pre-registration. They are exploratory.
