#!/usr/bin/env python3

from tests import msmt1
from tests import msmt2


def update_software():
    print("Dummy Func to update software on Mapago topology")


def main():
    update_software()
    msmt1.main()
    msmt2.main()


if __name__ == '__main__':
    main()
