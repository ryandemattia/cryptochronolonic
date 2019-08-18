import random
import sys, os
from functools import partial
from itertools import product   
# Libs
import numpy as np
from hist_service import HistWorker
from crypto_evolution import CryptoFolio
from random import randint, shuffle
# Local
import neat.nn
import _pickle as pickle
from pureples.shared.substrate import Substrate
from pureples.shared.visualize import draw_net
from pureples.es_hyperneat.es_hyperneat import ESNetwork, nDimensionTree
# Local
class PurpleTrader:

    #needs to be initialized so as to allow for 62 outputs that return a coordinate

    # ES-HyperNEAT specific parameters.
    params = {"initial_depth": 3,
            "max_depth": 4,
            "variance_threshold": 0.00013,
            "band_threshold": 0.0000013,
            "iteration_level": 3,
            "division_threshold": 0.00013,
            "max_weight": 8.0,
            "activation": "tanh"}


    # Config for CPPN.
    config = neat.config.Config(neat.genome.DefaultGenome, neat.reproduction.DefaultReproduction,
                                neat.species.DefaultSpeciesSet, neat.stagnation.DefaultStagnation,
                                'config_trader')

    start_idx = 0
    highest_returns = 0
    portfolio_list = []



    in_shapes = []
    out_shapes = []
    def __init__(self, hist_depth):
        self.hs = HistWorker()
        self.hs.combine_polo_usd_frames()
        self.hd = hist_depth
        print(self.hs.currentHists.keys())
        # set our ending idx, the length of our training data set
        self.end_idx = len(self.hs.hist_shaped[0])
        self.but_target = .1
        self.inputs = self.hs.hist_shaped[0].shape[1]
        self.outputs = 1
        sign = 1
        for ix in range(1,self.inputs+1):
            sign = sign *-1
            self.in_shapes.append((0.0-(sign*.005*ix), -1.0, 0.0+(sign*.005*ix)))
        self.out_shapes.append((0.0, 1.0, 0.0))
        self.subStrate = Substrate(self.in_shapes, self.out_shapes)
        self.epoch_len = 255
        #self.node_names = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'weight']
        self.leaf_names = []
        #self.initial_depth_tree = nDimensionTree([0.0,0.0,0.0], 1.0, 0)
        #nDimensionTree.divide_to_depth(self.initial_depth_tree, self.initial_depth_tree.lvl, self.params["initial_depth"])
        for l in range(len(self.in_shapes[0])):
            self.leaf_names.append('leaf_one_'+str(l))
            self.leaf_names.append('leaf_two_'+str(l))
        #self.leaf_names.append('bias')
    def set_portfolio_keys(self, folio):
        for k in self.hs.currentHists.keys():
            folio.ledger[k] = 0

    def get_one_epoch_input(self,end_idx):
        master_active = []
        for x in range(0, self.hd):
            active = []
            #print(self.outputs)
            for y in range(0, self.outputs):
                try:
                    sym_data = self.hs.hist_shaped[y][end_idx-x]
                    #print(len(sym_data))
                    active += sym_data.tolist()
                except:
                    print('error')
            master_active.append(active)
        #print(active)
        return master_active

    def get_single_symbol_epoch(self, end_idx, symbol_idx):
        master_active = []
        try:
            sym_data = self.hs.hist_shaped[symbol_idx][end_idx]
            #print(len(sym_data))
            master_active = sym_data.tolist()
        except:
            print('error')
        return master_active


    def get_single_symbol_epoch_recurrent(self, end_idx, symbol_idx):
        master_active = []
        for x in range(0, self.hd):
            try:
                sym_data = self.hs.hist_shaped[symbol_idx][end_idx-x]
                #print(len(sym_data))
                master_active.append(sym_data.tolist())
            except:
                print('error')
        return master_active

    def evaluate(self, network, rand_start, g, verbose=False):
        portfolio_start = 500
        portfolio = CryptoFolio(portfolio_start, self.hs.coin_dict, "USDT")
        end_prices = {}
        buys = 0
        sells = 0
        if(len(g.connections) > 0.0):
            for z in range(rand_start, rand_start+self.epoch_len):
                for x in range(len(self.hs.coin_dict)):
                    sym = self.hs.coin_dict[x]
                    active = self.get_single_symbol_epoch_recurrent(z, x)
                    network.reset()
                    for n in range(1, self.hd+1):
                        out = network.activate(active[self.hd-n])
                    if(out[0] < -.5):
                        #print("selling")
                        portfolio.sell_coin(sym, self.hs.currentHists[sym]['close'][z])
                        #print("bought ", sym)
                    elif(out[0] > .5):
                        #print("buying")
                        portfolio.buy_coin(sym, self.hs.currentHists[sym]['close'][z])
                        #print("sold ", sym)
                    #skip the hold case because we just dont buy or sell hehe
                    end_prices[sym] = self.hs.currentHists[sym]['close'][self.epoch_len+rand_start]
            result_val = portfolio.get_total_btc_value(end_prices)
            print(result_val[0], "buys: ", result_val[1], "sells: ", result_val[2])
            if(result_val[1] == 0):
                ft = portfolio_start/2
            else:
                ft = result_val[0]
        else:
            ft = 0.0
        return ft

    def solve(self, network):
        return self.evaluate(network) >= self.highest_returns

    def eval_fitness(self, genomes, config):
        r_start = randint(0+self.hd, self.hs.hist_full_size - self.epoch_len)
        fitter = genomes[0]
        fitter_val = 0.0 
        for idx, g in genomes:
            cppn = neat.nn.FeedForwardNetwork.create(g, config)
            network = ESNetwork(self.subStrate, cppn, self.params)
            net = network.create_phenotype_network_nd()
            g.fitness = self.evaluate(net, r_start, g)
            if(g.fitness > fitter_val):
                fitter = g
                fitter_val = g.fitness
        with open('./champs/perpetual_champion_'+str(fitter.key)+'.pkl', 'wb') as output:
            pickle.dump(fitter, output)
        print("latest_saved")
# Create the population and run the XOR task by providing the above fitness function.
def run_pop(task, gens):
    pop = neat.population.Population(task.config)
    stats = neat.statistics.StatisticsReporter()
    pop.add_reporter(stats)
    pop.add_reporter(neat.reporting.StdOutReporter(True))

    winner = pop.run(task.eval_fitness, gens)
    with open('./champs/champ_pop.pkl', 'wb') as output:
        pickle.dump(pop, output)
    print("es trade god summoned")
    return winner, stats


# If run as script.
if __name__ == '__main__':
    task = PurpleTrader(13)
    #print(task.trial_run())
    winner = run_pop(task, 89)[0]
    print('\nBest genome:\n{!s}'.format(winner))

    # Verify network output against training data.
    print('\nOutput:')
    cppn = neat.nn.FeedForwardNetwork.create(winner, task.config)
    network = ESNetwork(task.subStrate, cppn, task.params)
    with open('es_trade_god_cppn_3d.pkl', 'wb') as output:
        pickle.dump(winner, output)
    #draw_net(cppn, filename="es_trade_god")
    winner_net = network.create_phenotype_network_nd('dabestest.png')  # This will also draw winner_net.

    # Save CPPN if wished reused and draw it to file.
    draw_net(cppn, filename="es_trade_god")

