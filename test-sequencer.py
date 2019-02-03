#!/usr/bin/env python3

import os
import types
import json

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

def context_init():
    ctx = types.SimpleNamespace()
    ctx.config = config_load()
    return ctx

def main():
    ctx = context_init()
    update_software(ctx)
    throughput_max.main(ctx)


if __name__ == '__main__':
    main()
