#!/usr/bin/env python3

import os
import types
import json
import argparse

from tests import throughput_max
from tests import throughput_limited
from tests import throughput_limited_critical
from tests import reachability_rate
from tests import goodput_loss
from tests import goodput_delay
from tests import goodput_delay_critical
from tests import goodput_jitter
from tests import goodput_jitter_critical
from tests import goodput_advanced_loss_mean_per
from tests import goodput_advanced_loss_two_bursts_heat
from tests import intra_fairness_rate
from tests import intra_fairness_rate_rand_sleep
from tests import intra_fairness_rate_tcp
from tests import intra_fairness_rate_bar_plot
from tests import goodput_loss_bar_plot
from tests import goodput_advanced_loss_bar_plot
from tests import inter_fairness_rate
from tests import inter_fairness_rate_rand_sleep


CONFIG_NAME = 'network.conf'


def update_software(ctx):
    print("Dummy Func to update software on Mapago topology")


def config_subst_path(config):
    """ all path with ~ are substitured with the full path"""
    if 'ssh' in config and 'keyfilepath' in config['ssh']:
        path = os.path.expanduser(config['ssh']['keyfilepath'])
        config['ssh']['keyfilepath'] = path


def config_load():
    root_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(root_dir, CONFIG_NAME)
    config = dict()
    exec(open(config_path).read(), config)
    config.pop("__builtins__")
    config_subst_path(config)
    return config


def custom_config_load(custom_conf):
    if os.path.isabs(custom_conf) is not True:
        raise Exception('\nabs path needed! absolute path starts with /')

    config = dict()
    exec(open(custom_conf).read(), config)
    config.pop("__builtins__")
    config_subst_path(config)
    return config


def context_init(custom_conf):
    ctx = types.SimpleNamespace()

    if custom_conf is not None:
        ctx.config = custom_config_load(custom_conf)
    else:
        ctx.config = config_load()

    return ctx


def main():
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="append path to your own config")
    parser.add_argument(
        "--testcase",
        help="select testcase: throughput_max, throughput_limited, throughput_limited_critical, reachability_rate, goodput_loss")

    args = parser.parse_args()

    if args.config:
        ctx = context_init(args.config)
    else:
        ctx = context_init(None)

    if args.testcase == "throughput_max":
        throughput_max.main(ctx)
    elif args.testcase == "throughput_limited":
        throughput_limited.main(ctx)
    elif args.testcase == "throughput_limited_critical":
        throughput_limited_critical.main(ctx)
    elif args.testcase == "reachability_rate":
        reachability_rate.main(ctx)
    elif args.testcase == "goodput_loss":
        goodput_loss.main(ctx)
    elif args.testcase == "goodput_delay":
        goodput_delay.main(ctx)
    elif args.testcase == "goodput_delay_critical":
        goodput_delay_critical.main(ctx)
    elif args.testcase == "goodput_jitter":
        goodput_jitter.main(ctx)
    elif args.testcase == "goodput_jitter_critical":
        goodput_jitter_critical.main(ctx)
    elif args.testcase == "goodput_advanced_loss_mean_per":
        goodput_advanced_loss_mean_per.main(ctx)
    elif args.testcase == "goodput_advanced_loss_two_bursts_heat":
        goodput_advanced_loss_two_bursts_heat.main(ctx)
    elif args.testcase == "intra_fairness_rate":
        intra_fairness_rate.main(ctx)
    elif args.testcase == "intra_fairness_rate_rand_sleep":
        intra_fairness_rate_rand_sleep.main(ctx)
    elif args.testcase == "intra_fairness_rate_tcp":
        intra_fairness_rate_tcp.main(ctx)
    elif args.testcase == "intra_fairness_rate_bar_plot":
        intra_fairness_rate_bar_plot.main(ctx)
    elif args.testcase == "goodput_loss_bar_plot":
        goodput_loss_bar_plot.main(ctx)
    elif args.testcase == "goodput_advanced_loss_bar_plot":
        goodput_advanced_loss_bar_plot.main(ctx)
    elif args.testcase == "inter_fairness_rate_rand_sleep":
        inter_fairness_rate_rand_sleep.main(ctx)
    elif args.testcase == "inter_fairness_rate":
        inter_fairness_rate.main(ctx)
    elif args.testcase == "goodput_delay_playground":
        goodput_delay_playground.main(ctx)
    else:
        raise Exception('\nunknown testcase!')


if __name__ == '__main__':
    main()
