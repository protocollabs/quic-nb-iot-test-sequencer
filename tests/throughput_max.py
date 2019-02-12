import os
import shared

def main(ctx):
    print('current test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    client_params = {}

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
    shared.mapago_reset(ctx, 'gamma')

    srv_params['-uc-listen-addr'] = '127.0.0.1'
    srv_params['-port'] = '64321'
    shared.prepare_server(ctx, srv_params)

    # this should run now (please login into gamma, and
    # call ps

    # ok, now start local client here. similar to other script
