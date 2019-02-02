#!/usr/bin/env python3

import os
import types
import json

from tests import msmt1
from tests import msmt2

CONFIG_NAME = 'network.conf'


def update_software(ctx):
    print("Dummy Func to update software on Mapago topology")

def config_load():
    root_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(root_dir, CONFIG_NAME)
    config = dict()
    exec(open(config_path).read(), config)
    config.pop("__builtins__")
    return config

def context_init():
    ctx = types.SimpleNamespace()
    ctx.config = config_load()

def main():
    ctx = context_init()
    update_software(ctx)
    msmt1.main(ctx)
    msmt2.main(ctx)


if __name__ == '__main__':
    main()
