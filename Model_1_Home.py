# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:13:52 2015

@author: Clemens
"""

'''
import necessary modules
'''

from pyomo.environ import *
from pyomo.opt import SolverFactory
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn

'''
define aditional functions used within the model
'''


       

'''
formulate model
'''
        
m = AbstractModel()
opt = SolverFactory ("glpk")

m.T = Set(ordered=True, doc='Timesteps')
m.x_Total = Var(m.T, within=NonNegativeReals, doc='Total Energy via Grid')
m.x_Home = Var(m.T, within=NonNegativeReals, doc='Energy from Grid to Home')

#m.XEVout = Param(m.T)
m.P = Param(m.T, doc='Spot Market Energy Price')
m.DemandHome = Param(m.T, doc='Demand of the Home')

'''
define constraints and the objective
'''

def obj_rule(m):
    return sum(m.x_Total[t] * m.P[t] for t in m.T) 
m.obj = Objective(rule=obj_rule, sense = minimize)

def con1_rule(m, t):
    return m.x_Total[t] == m.x_Home[t]
m.con1 = Constraint(m.T, rule=con1_rule)  

def con2_rule(m, t):
    return m.x_Home[t] == m.DemandHome[t]
m.con2 = Constraint(m.T, rule=con2_rule) 


'''
load the data from csv files
'''

data = DataPortal()
data.load(filename='Set.csv', set=m.T)
data.load(filename='Param_DemandHome.csv', param=m.DemandHome)
data.load(filename='Param_P.csv', param=m.P)

'''
execute model
'''

#m.pprint()
instance = m.create_instance(data, "report_timing=True")
#instance.pprint()

results = opt.solve(instance)

#print results

instance.solutions.load_from(results)

'''
Print results in excel
'''

data = pd.DataFrame({   ' x_total_from_Grid ' : [instance.x_Total[t].value for t in instance.T],
                        ' Price ' : [instance.P[t] for t in instance.T],
                        ' Demand Home ' : [instance.DemandHome[t] for t in instance.T],
                        ' Costs' : [instance.x_Total[t].value * instance.P[t] for t in instance.T]} )

#print(data)
data.to_excel('M1_Home.xlsx', sheet_name = 'Sheet1')

print "Total Costs:", (sum(instance.x_Total[t].value * instance.P[t] for t in instance.T))

'''
produce graph to show results
'''
 
y = [instance.T[t] for t in instance.T]
w = [instance.x_Total[t].value for t in instance.T]
u = [instance.DemandHome[t] for t in instance.T]



fig, ax = plt.subplots(nrows = 1, ncols = 1)
plt.plot(y, w, "r--", label ='Total Energy from Grid')

plt.ylabel("kwh", fontsize = 16)
plt.ylim((0,5))
plt.xlim((1,168))
plt.grid(True)
plt.xlabel("Timesteps", fontsize = 16)
#plt.title("SOC/Total Demand/Price in t", fontsize = 18)
plt.legend()
plt.show()
