import matplotlib.pyplot as plt
import pandas as pd  
from datetime import datetime
def pull_in_file(f_name):
    return pd.read_csv('./trade_hists/'+f_name)


if __name__ == '__main__':
    thist = pull_in_file('7893_hist.txt')
    print(list(thist))
    print(thist.head())
    plt.plot(thist['date'], thist['current_balance '])
    plt.show()
