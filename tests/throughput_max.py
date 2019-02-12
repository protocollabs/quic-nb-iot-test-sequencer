import os
import shared

def main(ctx):
    print('current test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']

    # check that beta and gamma are reachable
    for host in remoteHosts:
        avail = shared.host_alive(ctx, host)

        if not avail:
            raise Exception("Host {} not available".format(host))

    # reset netem, don't know what was previouly configured
    beta_iface_to_alpha = ctx.config['beta']['netem-interfaces-to-alpha']
    beta_iface_to_gamma = ctx.config['beta']['netem-interfaces-to-gamma']
    interfaces = [beta_iface_to_alpha, beta_iface_to_gamma]
    
    shared.netem_reset(ctx, 'beta', interfaces=interfaces)

    # Note in this sceario we dont need to adjust netem to a specific setting
    shared.mapago_reset(ctx, 'gamma',)

    # FIXME: probably $HOME is not expanded, please check!
    cmd = "$HOME/gobin/mapago-server"

    shared.ssh_execute(ctx, 'gamma', cmd, background=True)
    # this should run now (please login into gamma, and
    # call ps

    # ok, now start local client here. similar to other script
