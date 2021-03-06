﻿### lesson from https://pandas.pydata.org/pandas-docs/stable/10min.html
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

serie = pd.Series([1,3,5,np.nan,6,8])
print(serie)
print('-'*80)
#generate dates
dates = pd.date_range('20180101', periods=10)
print(dates)
print('-'*80)
dataframe = pd.DataFrame(np.random.randn(10,5), index=dates, columns=list('ABCDE'))
print(dataframe)
print('-'*80)
dataframe2 = pd.DataFrame({ 'A' : 1.,
                            'B' : pd.Timestamp('20130102'),
                            'C' : pd.Series(1,index=list(range(4)),dtype='float32'),
                            'D' : np.array([3] * 4,dtype='int32'),
                            'E' : pd.Categorical(["test","train","test","train"]),
                            'F' : 'foo' })
print(dataframe2)
print('-'*80)
print(dataframe2.dtypes)
print('-'*80)
print(dataframe.head())
print('-'*80)
print(dataframe.tail(3))
print('-'*80)
print(dataframe.index)
print('-'*80)
print(dataframe.columns)
print('-'*80)
print(dataframe.describe())
print('-'*80)
print(dataframe.T)
print('-'*80)
print(dataframe.sort_values(by='B'))
print('-'*80)
print(dataframe['C'])
print('-'*80)
print(dataframe[0:3])
print('-'*80)
print(dataframe.loc[dates[0]])
print('-'*80)
print(dataframe.loc[:,['A','B']])
print('-'*80)
print(dataframe.loc['20180102':'20180104',['A','B']])
print('-'*80)
print(dataframe.loc[dates[0],'A'])
print('-'*80)
print(dataframe.at[dates[0],'A'])
print('-'*80)
print(dataframe.iloc[3])
print('-'*80)
print(dataframe.iloc[3:5,0:2])
print('-'*80)
print(dataframe.iloc[[1,2,4],[0,2]])
print('-'*80)
print(dataframe.iloc[[1,2,4],:])
print('-'*80)
print(dataframe.iloc[:,[0,2]])
print('-'*80)
print(dataframe.iloc[1,1])
print('-'*80)

print(dataframe[dataframe.A > 0])
print('-'*80)
print(dataframe[dataframe > 0])
print('-'*80)