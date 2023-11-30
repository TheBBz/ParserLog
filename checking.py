import pstats

p = pstats.Stats('profile_results.pstat')
p.sort_stats('cumulative').print_stats(10)
