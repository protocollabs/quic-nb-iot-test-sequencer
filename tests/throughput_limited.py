import os
import shared

def main(ctx):
    print('current test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}

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

    # Here we need to adjust the scenario
    shared.netem_configure(ctx, 'beta', interfaces=interfaces, netem_params={'rate' : '100kbit', 'loss' : '0', 'delay' : '100'})


    shared.mapago_reset(ctx, 'gamma')

    srv_params['-uc-listen-addr'] = '127.0.0.1'
    srv_params['-port'] = '64321'
    shared.prepare_server(ctx, srv_params)


    clt_params['-ctrl-addr'] = '127.0.0.1'
    clt_params['-ctrl-protocol'] = 'tcp'
    clt_params['-module'] = 'udp-throughput'
    clt_params['-streams'] = '1'
    clt_params['-addr'] = '127.0.0.1'
    clt_params['-msmt-time'] = '15'
    clt_params['-buffer-length'] = '1400'
    msmt_results = shared.prepare_client(ctx, clt_params)

    shared.analyze_data(msmt_results)
   
