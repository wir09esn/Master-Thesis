# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:13:52 2015

@author: Clemens
"""

'''
import nesessary modules
'''

from pyomo.environ import *
from pyomo.opt import SolverFactory
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn

'''
define aditional functions and figures used within the model
'''

year = range(1, 8761)
week = range(1, 169)
day = range(9,17)
work_week = {k*24 + d for k in range(5) for d in day}
working_week = list(set(week) - set(work_week))
working_year = {k*168 + w for k in range(53) for w in work_week}
driving_pattern_year = list(set(year)-set(working_year))
       
'''
formulate model
'''
        
m = AbstractModel()
opt = SolverFactory ("glpk")

m.T = Set(ordered=True, doc='Timesteps')
m.x_Total = Var(m.T, within=NonNegativeReals, doc='Total Energy via Grid')
m.x_Home = Var(m.T, within=NonNegativeReals, doc='Energy from Grid to Home')
m.x_PV_to_Home = Var(m.T, within=NonNegativeReals, doc='Energy from PV to Home')
m.x_PV_in_Grid = Var(m.T, within=NonNegativeReals, doc='Energy from PV to Grid')
m.soc_EV = Var(m.T, within=NonNegativeReals, doc='State of charge of the EV')
m.x_in_EV = Var(m.T, within=NonNegativeReals, doc='Energy from Grid to EEV')
m.x_in_PV_EV = Var(m.T, within=NonNegativeReals, doc='Energy from PV to EV')


m.P = Param(m.T, doc='Spot Market Energy Price')
m.DemandHome = Param(m.T, doc='Demand of the Home')
m.PV = Param(m.T, doc='PV Production')
m.P_PV = Param(m.T, doc='Price for the PV Energy')
m.COST_PV = Param(m.T, doc='LCOE for PV')
m.SOC_min = Param(m.T, doc='minimal State of Charge')
m.SOC_mid = Param(m.T, doc='medium State of Charge')
m.EV_out = Param(m.T, doc='Energy Outflow EV through driving')
m.SOC_max_EV = Param(m.T, doc='maximal State of Charge of the EV')
m.Eff = Param(m.T, doc='Energy Efficency')



'''
define constraints and the objective
'''

def obj_rule(m):
    return sum(m.x_Total[t] * m.P[t] + m.PV[t] * m.COST_PV[t] - m.x_PV_in_Grid[t] * m.P_PV[t] for t in m.T) 
m.obj = Objective(rule=obj_rule, sense = minimize)
    
def con1_rule(m, t):
    return m.x_Total[t] == m.x_Home[t] + m.x_in_EV[t]   
m.con1 = Constraint(m.T, rule=con1_rule)
    
def con2_rule(m, t):
    return m.x_Home[t] + m.x_PV_to_Home[t] == m.DemandHome[t]
m.con2 = Constraint(m.T, rule=con2_rule)
  
def con3_rule(m,t):
    return m.x_PV_to_Home[t] + m.x_PV_in_Grid[t] + m.x_in_PV_EV[t] == m.PV[t]
m.con3 = Constraint(m.T, rule=con3_rule)

def con4_rule(m, t):
    if t == m.T[1]:
        return m.soc_EV[t] == m.SOC_min[t]
    #elif t == m.T[-1]: 
    #    return m.soc[t] >= m.SOCmin[t]
    else:
        return m.soc_EV[t] == m.soc_EV[t-1] + m.x_in_EV[t] + m.x_in_PV_EV[t] \
         - m.EV_out[t]
m.con4 = Constraint(m.T, rule=con4_rule)
               
def con5_rule(m, t):
    return m.SOC_min[t] <= m.soc_EV[t] <= m.SOC_max_EV[t]
m.con5 = Constraint(m.T, rule=con5_rule)
           
def con6_rule(m,t):
    if t in driving_pattern_year:
        return m.x_in_EV[t] <= m.SOC_mid[t] 
    else:
        return m.x_in_EV[t] == m.SOC_min[t]
m.con6 = Constraint(m.T, rule=con6_rule)

def con7_rule(m,t):
    if t in driving_pattern_year:
        return m.x_in_PV_EV[t] <= m.SOC_mid[t] 
    else:
        return m.x_in_PV_EV[t] == m.SOC_min[t]
m.con7 = Constraint(m.T, rule=con7_rule)

           
'''
load the data from csv files
'''

data = DataPortal()
data.load(filename='Set.csv', set=m.T)
data.load(filename='Param_DemandHome.csv', param=m.DemandHome)
data.load(filename='Param_P.csv', param=m.P)
data.load(filename='Param_PV.csv', param=m.PV)
data.load(filename='Param_P_PV.csv', param=m.P_PV)
data.load(filename='Param_SOC_min.csv', param=m.SOC_min)
data.load(filename='Param_SOC_max_EV.csv', param=m.SOC_max_EV)
data.load(filename='Param_EV_out.csv', param=m.EV_out)
data.load(filename='Param_SOC_mid.csv', param=m.SOC_mid)
data.load(filename='Param_COST_PV.csv', param=m.COST_PV)
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
#instance.x_in_PV_EV.pprint()

 
#instance.P.pprint()
#instance.con6.pprint()
data = pd.DataFrame({   ' x_total_from_Grid ' : [instance.x_Total[t].value for t in instance.T],
                        ' Price ' : [instance.P[t] for t in instance.T],
                        ' x to Home ' : [instance.x_Home[t].value for t in instance.T],
                        ' Demand Home ' : [instance.DemandHome[t] for t in instance.T],
                        ' PV to Home ' : [instance.x_PV_to_Home[t].value for t in instance.T],
                        ' Costs' : [instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.COST_PV[t] for t in instance.T],
                        ' PV to Grid[t] ' : [instance.x_PV_in_Grid[t].value for t in instance.T],
                        ' SOC EV ' : [instance.soc_EV[t].value for t in instance.T],
                        ' x to EV ' : [instance.x_in_EV[t].value for t in instance.T],
                        ' x PV to EV ' : [instance.x_in_PV_EV[t].value for t in instance.T],
                        ' Revenues ' : [instance.x_PV_in_Grid[t].value * instance.P_PV[t] for t in instance.T],
                        ' EV out ' : [instance.EV_out[t] for t in instance.T],
                        ' FIT ' : [instance.P_PV[t] for t in instance.T],
                        ' PV LCOE ' : [instance.COST_PV[t] for t in instance.T],
                        ' PV Production ' : [instance.PV[t] for t in instance.T]})
                        
#print(data)
data.to_excel('M4_Home_PV_EV.xlsx', sheet_name = 'Sheet1')

print " Total Costs: ", (sum(instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.COST_PV[t] - instance.x_PV_in_Grid[t].value * instance.P_PV[t]  for t in instance.T))
print " Self-Consumption: ", (sum(instance.x_PV_to_Home[t].value + instance.x_in_PV_EV[t].value for t in instance.T) / sum(instance.PV[t] for t in instance.T) ) * 100, "%"
print " Share of PV produced energy EV : ", sum(instance.x_in_PV_EV[t].value for t in instance.T) / (sum(instance.PV[t] for t in instance.T))*100, "%"
print "Costs:", (sum(instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.COST_PV[t]  for t in instance.T))
print "Revenues:", (sum(instance.x_PV_in_Grid[t].value * instance.P_PV[t]  for t in instance.T))
print " Self-Sufficiency:", (sum(instance.x_PV_to_Home[t].value + instance.x_in_PV_EV[t].value for t in instance.T) / sum(instance.DemandHome[t] + instance.EV_out[t] for t in instance.T) ) * 100, "%"

'''
produce graph to show results
'''
 
y = [instance.T[t] for t in instance.T]
w = [instance.x_Total[t].value for t in instance.T]
u = [instance.DemandHome[t] for t in instance.T]
v = [instance.P[t] for t in instance.T]
q = [instance.PV[t] for t in instance.T]
o = [instance.x_Total[t].value * instance.P[t] for t in instance.T]
l = [instance.x_in_PV_EV[t].value for t in instance.T]

fig, ax = plt.subplots(nrows = 1, ncols = 1)
plt.plot(y, w, "r--", label ='Total Energy from Grid')
plt.plot(y, q, "m:", label = 'PV')
plt.plot(y, l, "g-", label = 'Energy PV to EV')
plt.ylabel("kwh", fontsize = 16)
plt.ylim((0,10))
plt.xlim((3000,3200))
plt.grid(True)
plt.xlabel("Timesteps", fontsize = 16)
plt.title("Total Energy from Grid in t", fontsize = 18)
plt.legend()

plt.show()
