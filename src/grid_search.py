"""Grid-search layer; dispatch and evaluation remain shared functions."""
from .study_runtime import evaluate_case

def generate_candidates(energies, powers):
    if list(energies)!=list(range(0,101,10)) or list(powers)!=list(range(5,51,5)):
        raise ValueError('Expected frozen 101-candidate grid')
    return [(0,0)]+[(e,p) for e in energies if e>0 for p in powers]

def evaluate_candidate(data,base_storage,thermal,economics,energy,power):
    if energy<0 or power<0:raise ValueError('Capacities must be nonnegative')
    storage=dict(base_storage,energy_capacity_MWh=float(energy),power_capacity_MW=float(power))
    return evaluate_case(data,storage,thermal,economics)
