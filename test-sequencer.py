#!/usr/bin/env python3

import os
import types
import json
import argparse

from tests import throughput_max

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
    args = parser.parse_args()

    if args.config:
        ctx = context_init(args.config)
    else:
        ctx = context_init(None)

    # TODO: This should call go get github.com/.../mapago => improvement
    update_software(ctx)

    print("\nreturned conf {}".format(ctx))

    throughput_max.main(ctx)

if __name__ == '__main__':
    main()
