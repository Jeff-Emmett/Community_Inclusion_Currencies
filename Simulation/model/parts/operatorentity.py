
import numpy as np
import pandas as pd
from cadCAD.configuration.utils import access_block
from .initialization import *
from .supportingFunctions import *
from collections import OrderedDict

# Parameters
FrequencyOfAllocation = 45 # every two weeks
idealFiat = 5000
idealCIC = 200000
varianceCIC = 50000
varianceFiat = 1000
unadjustedPerAgent = 50




agentAllocation = {'a':[1,1],'b':[1,1],'c':[1,1], # agent:[centrality,allocationValue]
                   'd':[1,1],'e':[1,1],'f':[1,1],
                   'g':[1,1],'h':[1,1],'i':[1,1],
                   'j':[1,1],'k':[1,1],'l':[1,1],
                   'm':[1,1],'o':[1,1],'p':[1,1]}

# Behaviors
def disbursement_to_agents(params, step, sL, s):
    '''
    Distribute every FrequencyOfAllocation days to agents based off of centrality allocation metric
    '''
    fiatBalance = s['operatorFiatBalance']
    cicBalance = s['operatorCICBalance']
    timestep = s['timestep']

    division =  timestep % FrequencyOfAllocation  == 0

    if division == True:
        agentDistribution ={} # agent: amount distributed
        for i,j in agentAllocation.items():
            agentDistribution[i] = unadjustedPerAgent * agentAllocation[i][1]
        distribute = 'Yes'
        
    else:
        agentDistribution = 0
        distribute = 'No'


    return {'distribute':distribute,'amount':agentDistribution}


def inventory_controller(params, step, sL, s):
    '''
    Monetary policy hysteresis conservation allocation between fiat and cic reserves.
    
    # TODO: If scarcity on both sides, add feedback to reduce percentage able to withdraw, frequency you can redeem, or redeem at less than par. 
    '''
    fiatBalance = s['operatorFiatBalance']
    cicBalance = s['operatorCICBalance']
    timestep = s['timestep']
    fundsInProcess = s['fundsInProcess']


    updatedCIC = cicBalance
    updatedFiat = fiatBalance

    #decision,amt = mint_burn_logic_control(idealCIC,updatedCIC,variance,updatedFiat)
    decision,amt = mint_burn_logic_control(idealCIC,updatedCIC,varianceCIC,updatedFiat,varianceFiat,idealFiat)

    if decision == 'burn':
        try:
            deltaR, realized_price = withdraw(amt,updatedFiat,updatedCIC, V0, kappa)
            # update state
            # fiatBalance = fiatBalance - deltaR
            # cicBalance = cicBalance - amt
            fiatChange = abs(deltaR)
            cicChange = amt

        except:
            print('Not enough to burn')

            fiatChange = 0
            cicChange = 0
        
    elif decision == 'mint':
        try:
            deltaS, realized_price = mint(amt,updatedFiat,updatedCIC, V0, kappa)
            # update state
            # fiatBalance = fiatBalance + amt
            # cicBalance = cicBalance + deltaS
            fiatChange = amt
            cicChange = abs(deltaS)

        except:
            print('Not enough to mint')
            fiatChange = 0
            cicChange = 0

    else:
        fiatChange = 0
        cicChange = 0
        decision = 'none'
        pass

    if decision == 'mint':
        fundsInProcess['timestep'].append(timestep + process_lag)
        fundsInProcess['decision'].append(decision)
        fundsInProcess['cic'].append(fiatChange)
        fundsInProcess['shilling'].append(cicChange)
    elif decision == 'burn':
        fundsInProcess['timestep'].append(timestep +process_lag)
        fundsInProcess['decision'].append(decision)
        fundsInProcess['cic'].append(fiatChange)
        fundsInProcess['shilling'].append(cicChange)
    else:
        pass
    
    return {'decision':decision,'fiatChange':fiatChange,'cicChange':cicChange,'fundsInProcess':fundsInProcess}



# Mechanisms 
def update_agent_tokens(params,step,sL,s,_input):
    '''
    '''
    y = 'network'
    network = s['network']

    distribute = _input['distribute']
    amount = _input['amount']

    if distribute == 'Yes':
        for i in agents:
            network.nodes[i]['tokens'] = network.nodes[i]['tokens'] + amount[i]
    else:
        pass

    return (y,network)

def update_operator_FromDisbursements(params,step,sL,s,_input):
    '''
    '''
    y = 'operatorCICBalance'
    x = s['operatorCICBalance']
    timestep = s['timestep']
    
    distribute = _input['distribute']
    amount = _input['amount'] 

    if distribute == 'Yes':
        totalDistribution = []
        for i,j in amount.items():
            totalDistribution.append(j)
        
        totalDistribution = sum(totalDistribution)
        x = x - totalDistribution

    else:
        pass

    return (y,x)

def update_totalDistributedToAgents(params,step,sL,s,_input):
    '''
    '''
    y = 'totalDistributedToAgents'
    x = s['totalDistributedToAgents']
    timestep = s['timestep']
    
    distribute = _input['distribute']
    amount = _input['amount'] 

    if distribute == 'Yes':
        totalDistribution = []
        for i,j in amount.items():
            totalDistribution.append(j)
        
        totalDistribution = sum(totalDistribution)
        x = x + totalDistribution
    else:
        pass

    return (y,x)

def update_operator_fiatBalance(params,step,sL,s,_input):
    '''
    '''
    y = 'operatorFiatBalance'
    x = s['operatorFiatBalance']
    fundsInProcess = s['fundsInProcess']
    timestep = s['timestep']
    if _input['fiatChange']:
        try:
            if fundsInProcess['timestep'][0] == timestep + 1:
                if fundsInProcess['decision'][0] == 'mint':
                    x = x - abs(fundsInProcess['shilling'][0])
                elif fundsInProcess['decision'][0] == 'burn':
                    x = x + abs(fundsInProcess['shilling'][0])
            else:
                pass
        except:
            pass
    else:
        pass


    return (y,x)

def update_operator_cicBalance(params,step,sL,s,_input):
    '''
    '''
    y = 'operatorCICBalance'
    x = s['operatorCICBalance']
    fundsInProcess = s['fundsInProcess']
    timestep = s['timestep']

    if _input['cicChange']:
        try:
            if fundsInProcess['timestep'][0] == timestep + 1:
                if fundsInProcess['decision'][0] == 'mint':
                    x = x + abs(fundsInProcess['cic'][0])
                elif fundsInProcess['decision'][0] == 'burn':
                    x = x - abs(fundsInProcess['cic'][0])
            else:
                pass
        except:
            pass
    else:
        pass

    return (y,x)

def update_totalMinted(params,step,sL,s,_input):
    '''
    '''
    y = 'totalMinted'
    x = s['totalMinted']
    timestep = s['timestep']
    try:
        if _input['fundsInProcess']['decision'][0] == 'mint':
            x = x + abs(_input['fundsInProcess']['cic'][0])
        elif _input['fundsInProcess']['decision'][0] == 'burn':
            pass
    except:
        pass


    return (y,x)

def update_totalBurned(params,step,sL,s,_input):
    '''
    '''
    y = 'totalBurned'
    x = s['totalBurned']
    timestep = s['timestep']
    try:
        if _input['fundsInProcess']['decision'][0] == 'burn':
            x = x + abs(_input['fundsInProcess']['cic'][0])
        elif _input['fundsInProcess']['decision'][0] == 'mint':
            pass
    except:
        pass

    return (y,x)

def update_fundsInProcess(params,step,sL,s,_input):
    '''
    '''
    y = 'fundsInProcess'
    x = _input['fundsInProcess']
    timestep = s['timestep']

    if _input['fundsInProcess']:
        try:
            if x['timestep'][0] == timestep:
                del x['timestep'][0]
                del x['decision'][0]
                del x['cic'][0]
                del x['shilling'][0]
            else:
                pass
        except:
            pass
    else:
        pass

    return (y,x)
