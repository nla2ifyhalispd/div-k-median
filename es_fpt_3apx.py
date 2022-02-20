import time
import psutil
import sys
import numpy as np
import feasibility
from kmedkpm import k_median_k_partitions_3eps, get_binned_distances
from local_search import kmedian_local_search
from coresets import kmedian_coreset
from scipy.spatial.distance import cdist
from sklearn.datasets import make_blobs
import generator
import random

test = False

def es_fpt_3apx_complete(data, color_mat, rvec, k, logfile):
    ############################################################################
    # INPUT
    # data: N X d numpy array
    # color_mat: N*t numpy array representing groups' memberships
    # rvec: requirements vector of t size
    # k: number of clusters

    # OUTPUT
    # Object with stats, i.e, with "cost" that is a cost of the solution
    ############################################################################
    process = psutil.Process()

    (N, d) = data.shape
    return_solution = False
    command = 'all'
    
    tstart = time.time()
    time_buf = time.time()
    perf_stats_all = feasibility.calculate(k, rvec, color_mat, 
                                        command, return_solution,
                                        logfile)
    feasibility_time = time.time() - time_buf

    set_mappings = perf_stats_all["subset_map"]
    set_to_indices = {}

    for (idx, id) in enumerate(sorted(set_mappings.keys())):
        set_to_indices[idx] = id
    #end for

    total_cost = sys.maxsize
    all_solutions = perf_stats_all["solution"]

    time_buf = time.time()
    stats = kmedian_coreset(data, k, coreset_size=0.2)
    coreset = stats['coreset']
    weights = stats['weights']

    binned_distances = get_binned_distances(data, coreset, weights, k)
    binned_index = dict(zip(binned_distances, range(len(binned_distances))))
    coreset_time = time.time() - time_buf

    nof_solutions = len(all_solutions)
    np.random.shuffle(all_solutions)
    threshold = int(nof_solutions * (0.03 if nof_solutions > 600 else 0.05 if nof_solutions > 200 else 0.1) )

    time_buf = time.time()
    total_cost = sys.maxsize
    for (x, s) in enumerate(all_solutions[:threshold,:]):
        E = {}
        i = 0
        for (idx, e) in enumerate(s):
            for _ in range(e):
                E[i] = data[set_mappings[set_to_indices[idx]], :]
                i = i + 1
        #end for
        
        time_eps = time.time()
        _, S = k_median_k_partitions_3eps(E, coreset, weights, N, d, k, binned_distances, binned_index)
        actual_cost = cdist(data, S).min(axis=1).sum()/N
        total_cost = min(total_cost, actual_cost)
        print(x,"/",threshold,':', s, ':', total_cost, time.time()-time_eps)
        sys.stdout.flush()
    #end for
    fpt_3apx_time = time.time() - time_buf
    total_time = time.time() - tstart
    peak_memory = process.memory_info().rss/(1024*1024)
    virtual_memory = process.memory_info().vms/(1024*1024)

    logfile.write('ES+FPT-3APX: [%.2fs %.2fs %.2fs] [total-time: %.2fs] [cost: %f]\n'%\
                  (feasibility_time, coreset_time, fpt_3apx_time, total_time, total_cost))
    logfile.flush()

    perf_stats = {}
    opt_ls_cost = kmedian_local_search(data, k)["cost"]
    perf_stats['opt_ls_cost'] = opt_ls_cost
    perf_stats['total_time'] = total_time
    perf_stats['feasible_time'] = feasibility_time
    perf_stats['coreset_time'] = coreset_time
    perf_stats['fpt_3apx_time'] = fpt_3apx_time
    perf_stats['peak_memory'] = peak_memory
    perf_stats['virtual_memory'] = virtual_memory
    perf_stats['cost'] = float(total_cost)
    perf_stats['nof_solutions'] = nof_solutions
    perf_stats['threshold'] = threshold

    return perf_stats
#end es_3apx_complete()

def test_es_fpt_complete():
    #random number generator seeds
    gen_seed  = 12312321
    dist_matrix_seed = random.randint(1, int(pow(2, 32)-1))
    local_search_seed = random.randint(1, int(pow(2, 32)-1))

    #initialize
    logfile = sys.stdout
    n = 100
    t = 3
    k = 3
    d = 2
    r_max = 3
    r_min = 1
    max_freq = 3

    data, _ = make_blobs(n_samples=n, centers=k, n_features=d,
                            random_state=12312, cluster_std=0.8)

    #generate instance and time it
    time_buf = time.time()
    color_mat, rvec, _ = generator.get_feasible_instance(
                                        t,
                                        n,
                                        r_max,
                                        r_min,
                                        max_freq,
                                        k,
                                        gen_seed,
                                        unique=False)
    es_fpt_3apx_complete(data, color_mat, rvec, k, logfile)
#end es_fpt_3apx_complete_test()

################################################################################

if __name__ == '__main__':
    test_es_fpt_complete()