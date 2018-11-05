import csv
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import math

class ProcessedData(object):

    def __init__(self, datasets):
        self.data = self.parse_data(datasets)

    def parse_data(self, datasets):
        """
        Opens CSV fles and parses the data into a multidimensional array

        Parameters:
        datasets (array): array of links to datasets to be parsed

        Returns:
        Array: parsed CSV files
        """

        parsed = []
        for dset in datasets:
            with open(dset) as rawData:
                csv_reader = csv.DictReader(rawData)
                for i, row in enumerate(csv_reader):
                    parsed.append(row)
        return parsed

    def split_data(self, datasets, split=.75):
        """
        Splits data into training and testing sets 

        Parameters:
        datasets (array): collection of all data
        split (float): percent split training to testing, default is .75

        Returns:
        Array: training data
        Array: testing data
        """
        train = []
        test = []
        for dset in datasets:
            amount_of_training = math.floor(split * sum(1 for row in dset))
            for i, row in enumerate(dset):
                if i == 0:
                    continue
                if i > amount_of_training:
                    test.append(row)
                else:
                    train.append(row)
        return train, test

    def plotData(self):
        colors = ["red", "blue", "green", "yellow", "brown", "purple"]
        i = 0
        for var in self.dataPoints:
            sns.distplot(self.dataPoints[var], color=colors[i], label=var)
            i += 1
        plt.legend()
        plt.show()

    def calcSTDData(self):
        res = []
        for var in self.dataPoints:
            res.append([np.mean(self.dataPoints[var]),
                        np.std(self.dataPoints[var]), var])
        return res

    def calcBoundsData(self, stdData):
        for var in stdData:
            lb = var[0] - (var[1] / 2)
            ub = var[0] + (var[1] / 2)
            print(lb, ub, var[2])