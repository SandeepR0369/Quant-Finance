# Regime-Aware Multi-Factor Alpha Model with Walk-Forward Optimization and Portfolio Risk Budgeting

## Capstone Project  
Author: Sandeep Reddy  
Program: Quantitative Finance  

---

## 1. Project Overview

This capstone project develops a systematic quantitative investment framework that integrates:

- Multi-factor alpha modeling  
- Market regime detection  
- Walk-forward optimization  
- Portfolio risk budgeting  

The objective is to design and evaluate a robust, risk-aware equity allocation strategy that adapts to changing market conditions while minimizing overfitting bias.

---

## 2. Problem Statement

Traditional factor models often assume static market conditions and fixed parameters.  
However, financial markets exhibit regime shifts (bull, bear, high volatility, low volatility) that influence factor performance.

This project addresses the following:

- Can factor performance improve under regime-aware allocation?
- Does walk-forward optimization reduce overfitting risk?
- Can portfolio risk budgeting improve drawdown control?
- Does the proposed framework outperform benchmark indices on a risk-adjusted basis?

---

## 3. Key Components of the Framework

### 3.1 Data Layer
- NSE equities (via Zerodha Kite API)
- Global benchmark data (via Yahoo Finance)
- Daily OHLCV data
- Risk-free rate assumptions

### 3.2 Factor Construction
Primary factors include:
- Momentum (12-month trailing return)
- Volatility (rolling standard deviation)
- Moving Average Distance
- Beta (optional advanced extension)

Factors are standardized cross-sectionally and combined into a composite alpha score.

---

### 3.3 Regime Detection

Market regimes are identified using rule-based methods such as:

- 200-day moving average filter
- Volatility threshold classification

Markets are labeled into:
- Bull regime
- Bear regime
- High volatility regime

Factor weights may vary across regimes.

---

### 3.4 Walk-Forward Optimization

To prevent lookahead bias:

- Rolling training windows are used
- Out-of-sample validation is performed
- Parameters are re-optimized periodically

This simulates realistic live deployment conditions.

---

### 3.5 Portfolio Construction & Risk Budgeting

Portfolio allocation techniques explored:

- Equal-weight allocation
- Mean-variance optimization
- Risk parity allocation
- Risk contribution budgeting

Objective:
- Improve drawdown control
- Balance risk across holdings
- Enhance stability of returns

---

## 4. Evaluation Metrics

The strategy is evaluated using:

- CAGR
- Annualized volatility
- Sharpe ratio
- Maximum drawdown
- Sortino ratio
- Rolling performance metrics
- Turnover and transaction cost impact

Benchmark comparisons include:
- Nifty 50 Index
- Equal-weight portfolio baseline

---

## 5. Avoiding Bias

The project explicitly controls for:

- Lookahead bias
- Data snooping bias
- Overfitting risk
- Survivorship bias (discussed in limitations)

---

## 6. Project Structure

```
regime_aware_alpha/
├── config/
├── data/
├── src/
│   ├── analytics/
│   ├── data/
│   ├── portfolio/
│   ├── visualization/
│   └── utils/
├── tests/
├── notebooks/
├── requirements.txt
└── main.py
```

The structure is modular and production-oriented, allowing future extension to live trading systems.

---

## 7. Expected Contributions

This project demonstrates:

- Practical implementation of factor investing
- Regime-aware adaptive modeling
- Institutional-grade backtesting discipline
- Risk-based portfolio construction
- Professional research documentation

---

## 8. Limitations

- Survivorship bias in index constituents
- Transaction cost assumptions may vary in reality
- Regime classification is rule-based (non-ML)
- No live slippage modeling

Future enhancements may include:
- Hidden Markov Model regime detection
- Machine learning factor blending
- Intraday extension
- Real-time signal generation

---

## 9. Tools & Technologies

- Python
- Pandas / NumPy
- Matplotlib / Seaborn
- SciPy / Statsmodels
- Scikit-learn
- Zerodha Kite API
- Yahoo Finance API

---

## 10. Conclusion

This project bridges academic quantitative finance concepts with practical systematic portfolio implementation.  
It emphasizes robustness, risk management, and realistic validation techniques over pure in-sample optimization.

The framework is extensible and can be adapted to live systematic trading environments.

