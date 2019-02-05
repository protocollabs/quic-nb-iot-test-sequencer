import os
import shared


def main(ctx):
    print('TEST: {}'.format(os.path.basename(__file__)[:-3]))

    # check that beta and gamma are reachable
    # TODO: check gamma aswell
    # CHECK functionality
    avail = shared.host_alive(ctx, 'beta')
    if not avail:
        pass

    # reset netem, don't know what was previouly configured
    beta_iface_to_alpha = ctx.config['beta']['netem-interfaces-to-alpha']
    beta_iface_to_gamma = ctx.config['beta']['netem-interfaces-to-gamma']
    interfaces = [beta_iface_to_alpha, beta_iface_to_gamma]
    shared.netem_reset(ctx, 'beta', interfaces=interfaces)

    # Note in this sceario we dont need to adjust netem to a specific setting

    cmd = "kill -9 mapago"
    shared.ssh_execute(ctx, 'gamma', cmd, background=False)

    # FIXME: probably $HOME is not expanded, please check!
    cmd = "$HOME/gobin/mapago-server"

    shared.ssh_execute(ctx, 'gamma', cmd, background=True)
    # this should run now (please login into gamma, and
    # call ps

    # ok, now start local client here. similar to other script
