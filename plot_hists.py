import matplotlib.pyplot as plt
import pandas as pd  
from datetime import datetime
def pull_in_file(f_name):
    return pd.read_csv('./trade_hists/'+f_name)


if __name__ == '__main__':
    thist = pull_in_file('kraken/88_hist.txt')
    print(list(thist))
    print(thist)
    thist['date'] = thist['date'].str[:-6]
    plt.plot(thist['date'], thist['current_balance '])
    plt.xticks(rotation=90)
    plt.show()
