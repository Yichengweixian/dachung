"""Bounded real-coded GA with deterministic, ordered batch evaluations."""
import numpy as np

LOW=np.array([0.,5.]);HIGH=np.array([100.,50.])

def sbx(a,b,rng,eta=15,probability=.9):
    c=a.copy();d=b.copy()
    if rng.random()>probability:return c,d
    for j,(lo,hi) in enumerate(zip(LOW,HIGH)):
        if rng.random()>.5 or abs(a[j]-b[j])<=1e-14:continue
        x,y=sorted([a[j],b[j]]);u=rng.random()
        beta=1+2*(x-lo)/(y-x);alpha=2-beta**(-(eta+1))
        q=(u*alpha)**(1/(eta+1)) if u<=1/alpha else (1/(2-u*alpha))**(1/(eta+1))
        left=.5*(x+y-q*(y-x))
        beta=1+2*(hi-y)/(y-x);alpha=2-beta**(-(eta+1))
        q=(u*alpha)**(1/(eta+1)) if u<=1/alpha else (1/(2-u*alpha))**(1/(eta+1))
        right=.5*(x+y+q*(y-x))
        left=np.clip(left,lo,hi);right=np.clip(right,lo,hi)
        c[j],d[j]=(right,left) if rng.random()<.5 else (left,right)
    return c,d

def mutate(x,rng,eta=20,probability=.5):
    out=x.copy()
    for j,(lo,hi) in enumerate(zip(LOW,HIGH)):
        if rng.random()>probability:continue
        delta1=(out[j]-lo)/(hi-lo);delta2=(hi-out[j])/(hi-lo);u=rng.random();power=1/(eta+1)
        if u<=.5:
            delta=(2*u+(1-2*u)*(1-delta1)**(eta+1))**power-1
        else:
            delta=1-(2*(1-u)+2*(u-.5)*(1-delta2)**(eta+1))**power
        out[j]=np.clip(out[j]+delta*(hi-lo),lo,hi)
    return out

def run_ga(evaluate_batch,parameters,seed,progress=None):
    rng=np.random.default_rng(seed);size=parameters['population'];pop=rng.uniform(LOW,HIGH,size=(size,2))
    count=0;history=[];best_cost=np.inf;best=None
    def evaluate(candidates,generation):
        nonlocal count,best_cost,best
        phenotypes=np.asarray([([0.,0.] if x[0]<5 else x) for x in candidates])
        values=np.asarray(evaluate_batch(phenotypes,generation),dtype=float)
        if len(values)!=len(candidates) or not np.isfinite(values).all():raise ValueError('Invalid objective values')
        for x,value in zip(phenotypes,values):
            count+=1
            if value<best_cost:best_cost=float(value);best=x.copy()
            history.append(dict(evaluation=count,generation=generation,energy=float(x[0]),power=float(x[1]),cost=float(value),best_cost=best_cost))
        return values
    fitness=evaluate(pop,0)
    for generation in range(1,parameters['generations']+1):
        elite=int(np.argmin(fitness));children=[]
        def select():
            choices=rng.integers(0,size,2);return pop[choices[np.argmin(fitness[choices])]].copy()
        while len(children)<size-1:
            pair=sbx(select(),select(),rng,parameters['eta_c'],parameters['crossover_probability'])
            for child in pair:
                children.append(mutate(child,rng,parameters['eta_m'],parameters['mutation_probability']))
                if len(children)==size-1:break
        offspring=np.asarray(children);values=evaluate(offspring,generation)
        pop=np.vstack([pop[elite],offspring]);fitness=np.r_[fitness[elite],values]
        if progress:progress(generation,count,best_cost,history)
    return best,best_cost,history
