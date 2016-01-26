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

m.soc = Var(m.T, within=NonNegativeReals, doc='State of Charge of the Storage')
m.x_out_storage = Var(m.T, within=NonNegativeReals, doc='Energy from Storage to Home')
m.x_in_storage = Var(m.T, within=NonNegativeReals, doc='Energy from Grid to Storage')

m.x_PV_to_Home = Var(m.T, within=NonNegativeReals, doc='Energy from PV to Home')
m.x_PV_in_storage = Var(m.T, within=NonNegativeReals, doc='Energy from PV to Storage')
m.x_PV_in_Grid = Var(m.T, within=NonNegativeReals, doc='Energy from PV to Grid')
m.R = Param(m.T, doc='share of maximum power output ruled by regulation')

m.soc_EV = Var(m.T, within=NonNegativeReals, doc='State of charge of the EV')
m.x_in_EV = Var(m.T, within=NonNegativeReals, doc='Energy from Grid to EEV')
m.x_in_PV_EV = Var(m.T, within=NonNegativeReals, doc='Energy from PV to EV')
m.x_Storage_in_EV = Var(m.T, within=NonNegativeReals, doc='Energy from Storage to EV')

#m.XEVout = Param(m.T)
m.P = Param(m.T, doc='Spot Market Energy Price')
m.DemandHome = Param(m.T, doc='Demand of the Home')
m.SOC_max = Param(m.T, doc='maximal State of Charge')
m.SOC_min = Param(m.T, doc='minimal State of Charge')
m.PV = Param(m.T, doc='PV Production')
m.P_PV = Param(m.T, doc='Price for the PV Energy')
m.COST_PV = Param(m.T, doc='LCOE for PV')
m.SOC_mid = Param(m.T, doc='medium State of Charge')
#m.EV = Param(m.T, doc='Dummy')
m.EV_out = Param(m.T, doc='Energy Outflow EV through driving')
m.SOC_max_EV = Param(m.T, doc='maximal State of Charge of the EV')
m.Eff = Param(m.T, doc='Energy Efficency')
m.P_Bat = Param(m.T, doc='Costs Battery')

'''
define constraints and the objective
'''

def obj_rule(m):
    return sum(m.x_Total[t] * m.P[t] + (m.x_PV_to_Home[t]  + m.x_in_PV_EV[t] + m.x_PV_in_storage[t]+ m.x_PV_in_Grid[t]) * m.COST_PV[t] + (m.x_PV_in_storage[t] + m.x_in_storage[t] ) * m.P_Bat[t] - m.x_PV_in_Grid[t] * m.P_PV[t] for t in m.T)
m.obj = Objective(rule=obj_rule, sense = minimize)

def con1_rule(m, t):
    return m.x_Total[t] == m.x_in_storage[t] + m.x_in_EV[t] + m.x_Home[t]
m.con1 = Constraint(m.T, rule=con1_rule)

def con2_rule(m, t):
    return m.x_Home[t] + m.x_out_storage[t] + m.x_PV_to_Home[t] == m.DemandHome[t]
m.con2 = Constraint(m.T, rule=con2_rule)

def con3_rule(m,t):
    return m.x_PV_to_Home[t] + m.x_PV_in_storage[t]+ m.x_in_PV_EV[t] \
    + m.x_PV_in_Grid[t] == m.PV[t]
m.con3 = Constraint(m.T, rule=con3_rule)

def con4_rule(m, t):
    if t == m.T[1]:
        return m.soc_EV[t] == m.SOC_min[t]
    #elif t == m.T[-1]:
    #    return m.soc[t] >= m.SOCmin[t]
    else:
        return m.soc_EV[t] == m.soc_EV[t-1] + m.x_in_EV[t] + m.x_in_PV_EV[t] \
        + m.x_Storage_in_EV[t] - m.EV_out[t]
m.con4 = Constraint(m.T, rule=con4_rule)

def con5_rule(m, t):
    return m.SOC_min[t] <= m.soc_EV[t] <= m.SOC_max_EV[t]
m.con5 = Constraint(m.T, rule=con5_rule)

def con6_rule(m, t):
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


def con8_rule(m, t):
    if t == m.T[1]:
        return m.soc[t] == m.SOC_min[t]
    #elif t == m.T[-1]:
    #    return m.soc[t] >= m.SOCmin[t]
    else:
        return m.soc[t] == m.soc[t-1] + m.Eff[t] * m.x_in_storage[t] \
        + m.Eff[t] * m.x_PV_in_storage[t] - m.x_Storage_in_EV[t] - m.x_out_storage[t]
m.con8 = Constraint(m.T, rule=con8_rule)

def con9_rule(m, t):
    return m.SOC_min[t] <= m.soc[t] <= m.SOC_mid[t]
m.con9 = Constraint(m.T, rule=con9_rule)

def con10_rule(m, t):
    return m.x_in_storage[t] <= m.SOC_mid[t]
m.con10 = Constraint(m.T, rule=con10_rule)

def con11_rule(m,t):
    if t in driving_pattern_year:
        return m.x_Storage_in_EV[t] <= m.SOC_mid[t]
    else:
        return m.x_Storage_in_EV[t] == m.SOC_min[t]
m.con11 = Constraint(m.T, rule=con11_rule)

def con12_rule(m, t):
    return m.x_Home[t] <= m.SOC_mid[t]
m.con12 = Constraint(m.T, rule=con12_rule)

def con13_rule(m,t):
    if t == m.T[1]:
        return m.x_out_storage[t] == m.SOC_min[t]
    else:
        return Constraint.Skip
m.con13 = Constraint(m.T, rule=con13_rule)

def con14_rule(m,t):
        return m.x_PV_in_Grid[t] <= m.R[t] * m.SOC_mid[t]
m.con14 = Constraint(m.T, rule=con14_rule)


'''
load the data from csv files
'''

data = DataPortal()
data.load(filename='Set.csv', set=m.T)
data.load(filename='Param_DemandHome.csv', param=m.DemandHome)
data.load(filename='Param_SOC_max.csv', param=m.SOC_max)
data.load(filename='Param_SOC_min.csv', param=m.SOC_min)
data.load(filename='Param_PV.csv', param=m.PV)
data.load(filename='Param_P_PV_plus20.csv', param=m.P_PV)
data.load(filename='Param_COST_PV.csv', param=m.COST_PV)
data.load(filename='Param_SOC_max_EV.csv', param=m.SOC_max_EV)
data.load(filename='Param_P_plus20.csv', param=m.P)
data.load(filename='Param_EV_out.csv', param=m.EV_out)
data.load(filename='Param_SOC_mid.csv', param=m.SOC_mid)
data.load(filename='Param_Eff.csv', param=m.Eff)
data.load(filename='Param_P_Bat_plus20.csv', param=m.P_Bat)
data.load(filename='Param_R.csv', param=m.R)
'''
execute model
'''

#m.pprint()
instance = m.create_instance(data, """report_timing=True""")
#instance.pprint()
#instance.con9.pprint()

results = opt.solve(instance)

#print results

instance.solutions.load_from(results)


'''
Print results in excel
'''

data = pd.DataFrame({   ' x_total_from_Grid ' : [instance.x_Total[t].value for t in instance.T],
                        ' Price ' : [instance.P[t] for t in instance.T],
                        ' x to Storage ' : [instance.x_in_storage[t].value for t in instance.T],
                        ' x to Home ' : [instance.x_Home[t].value for t in instance.T],
                        ' SOC ' : [instance.soc[t].value for t in instance.T],
                        ' x Storage to Home ' : [instance.x_out_storage[t].value for t in instance.T],
                        ' Demand Home ' : [instance.DemandHome[t] for t in instance.T],
                        ' PV to Storage ' : [instance.x_PV_in_storage[t].value for t in instance.T],
                        ' PV to Home ' : [instance.x_PV_to_Home[t].value for t in instance.T],
                        ' Costs' : [instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.P_PV[t]  for t in instance.T],
                        ' Revenues ' : [instance.x_PV_in_Grid[t].value * instance.P_PV[t] for t in instance.T],
                        ' FIT ' : [instance.P_PV[t] for t in instance.T],
                        ' PV to Grid[t] ' : [instance.x_PV_in_Grid[t].value for t in instance.T],
                        ' x Storage to EV ' : [instance.x_Storage_in_EV[t].value for t in instance.T],
                        ' SOC EV ' : [instance.soc_EV[t].value for t in instance.T],
                        ' x to EV ' : [instance.x_in_EV[t].value for t in instance.T],
                        ' x PV to EV ' : [instance.x_in_PV_EV[t].value for t in instance.T],
                        ' EV out ' : [instance.EV_out[t] for t in instance.T],
                        ' PV LCOE ' : [instance.COST_PV[t] for t in instance.T],
                        ' PV Production ' : [instance.PV[t] for t in instance.T],
                        ' PV Production ' : [instance.PV[t] for t in instance.T]})
#print(data)
data.to_excel('M6_Home_PV_EV_Storage_5kw_5kwh_4h_12h.xlsx', sheet_name = 'Sheet1')

print "Total Costs:", (sum(instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.COST_PV[t] + (instance.x_PV_in_storage[t].value + instance.x_in_storage[t].value ) * instance.P_Bat[t] - instance.x_PV_in_Grid[t].value * instance.P_PV[t]  for t in instance.T))
print "Costs:", (sum(instance.x_Total[t].value * instance.P[t] + instance.PV[t] * instance.COST_PV[t] + (instance.x_PV_in_storage[t].value + instance.x_in_storage[t].value ) * instance.P_Bat[t]  for t in instance.T))
print "Revenues:", (sum(instance.x_PV_in_Grid[t].value * instance.P_PV[t]  for t in instance.T))
print "Total Battery charging", (sum(instance.x_in_storage[t].value \
+ instance.x_PV_in_storage[t].value for t in instance.T ))
#rint "EV Usage", (sum(instance.EV_out[t] for t in instance.T ))
print "EV loading", (sum(instance.x_in_EV[t].value + instance.x_in_PV_EV[t].value + instance.x_Storage_in_EV[t].value for t in instance.T))
print "Self-Consumption:", (sum(instance.x_PV_to_Home[t].value + instance.x_in_PV_EV[t].value + instance.x_PV_in_storage[t].value for t in instance.T) / sum(instance.PV[t] for t in instance.T) ) * 100, "%"
print " Self-Sufficiency:", (sum(instance.x_PV_to_Home[t].value + instance.x_out_storage[t].value + instance.x_in_PV_EV[t].value + instance.x_Storage_in_EV[t].value - instance.x_in_storage[t].value  for t in instance.T) / sum(instance.DemandHome[t] + instance.EV_out[t] for t in instance.T) ) * 100, "%"
print "Share of PV produced energy EV : ", sum(instance.x_in_PV_EV[t].value + (instance.x_PV_in_storage[t].value + instance.x_in_storage[t].value - instance.x_out_storage[t].value) for t in instance.T) / (sum(instance.PV[t] for t in instance.T))*100, "%"

'''
produce graph to show results


z = [instance.soc[t].value for t in instance.T]
y = [instance.T[t] for t in instance.T]
w = [instance.x_Total[t].value for t in instance.T]
v = [instance.x_in_storage[t].value for t in instance.T]
u = [instance.DemandHome[t] for t in instance.T]
v = [instance.P[t] for t in instance.T]
q = [instance.PV[t] for t in instance.T]
o = [instance.x_Total[t].value * instance.P[t] for t in instance.T]
r = [instance.soc_EV[t].value for t in instance.T]

fig, ax = plt.subplots(nrows = 1, ncols = 1)
plt.plot(y, z, "r--", label ='SOC Bat')
#plt.plot(y, u, "b-", label = 'Demand Home')
#plt.plot(y, v, "g-", label = 'Price')
#plt.plot(y, t, "m:", label = 'Costs')
#plt.plot(y, q, "m:", label = 'PV')
plt.plot(y, r, "b-", label = 'SOC EV')
plt.ylabel("kwh and euros", fontsize = 16)
plt.ylim((1,15))
plt.xlim((1,8760))
plt.grid(True)
plt.xlabel("Timesteps", fontsize = 16)
plt.title("SOC/Total Demand/Price in t", fontsize = 18)
plt.legend()

fig2, ax = plt.subplots(nrows = 1, ncols = 1)
plt.plot(y, w, "g--", label = 'Energy from Grid')
plt.plot(y, q, "m:", label = 'PV')
plt.plot(y, u, "b-", label = 'Demand Home')
plt.xlabel('Timesteps', fontsize = 16)
plt.ylabel('Total Energy from grid', fontsize = 16)
plt.legend()
plt.show()
'''