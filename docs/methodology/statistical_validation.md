# Statistical Validation & Multiple Testing Correction

## 1. Backtest Overfitting Risk

In quantitative strategy research with limited historical days (typically 3–5 trading days per round), iterative backtesting on the same dataset inevitably discovers spurious patterns—a phenomenon known as **data snooping** or **backtest overfitting**.

## 2. Mathematical Corrections

### A. Deflated Sharpe Ratio (DSR)
When $N$ independent parameter combinations are tested, the expected maximum Sharpe ratio under the null hypothesis of zero skill ($H_0: \text{SR} = 0$) scales as:
$$\mathbb{E}[\max_{n=1,\dots,N} \widehat{\text{SR}}_n] \approx \sqrt{2 \ln N} \left(1 - \frac{\gamma}{\sqrt{2 \ln N}}\right) \sigma_{\widehat{\text{SR}}}$$
where $\gamma \approx 0.5772$ (Euler-Mascheroni constant) and $\sigma_{\widehat{\text{SR}}}$ is the standard deviation of trial Sharpe ratios.

The **Deflated Sharpe Ratio (DSR)** adjusts the observed Sharpe ratio $\widehat{\text{SR}}$ for non-normality (skewness $S$, kurtosis $K$) and the number of trials $N$:
$$\text{DSR} = \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T - 1}}{\sqrt{1 - S \widehat{\text{SR}} + \frac{K - 1}{4} \widehat{\text{SR}}^2}} \right)$$
where $\Phi(\cdot)$ is the standard normal cumulative distribution function and $\text{SR}^* = \mathbb{E}[\max_N \widehat{\text{SR}}]$.

### B. Combinatorial Symmetric Cross-Validation (CSCV)
We apply CSCV to partition historical time slices into $S$ combinations, measuring the **Probability of Backtest Overfitting (PBO)**:
$$\text{PBO} = \mathbb{P}(\text{SR}_{\text{OOS}} \le 0 \mid \text{SR}_{\text{IS}} = \max_n \text{SR}_{\text{IS}, n})$$
A robust strategy requires $\text{PBO} < 0.15$.
