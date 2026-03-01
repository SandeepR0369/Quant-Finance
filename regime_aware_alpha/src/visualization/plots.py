import matplotlib.pyplot as plt

def plot_equity_curve(cumulative_returns):
    plt.figure(figsize=(10,6))
    plt.plot(cumulative_returns)
    plt.title("Equity Curve")
    plt.show()

def plot_drawdown(drawdown):
    plt.figure(figsize=(10,6))
    plt.plot(drawdown)
    plt.title("Drawdown")
    plt.show()