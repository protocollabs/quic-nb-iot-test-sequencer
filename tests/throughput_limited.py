import os
import shared
import datetime
import matplotlib.pyplot as plt

# copy & paste from evaluation.py
def analyze_data(msmt_results):
    # min and max will at the end of the next loop contain
    # the real min and max values
    datetime_min = datetime.datetime(4000, 1, 1)
    datetime_max = datetime.datetime(1, 1, 1)

    # Keep in mind for all byte accounting here:
    # it is transmitted in a ABSOLUTE manner, no differences
    # are signaled via mapago
    bytes_rx = 0
    prev_datetime_max = datetime.datetime(1, 1, 1)
    prev_datetime_max_set = False

    # we store the data for plot, where just one overall
    # bandwith is not succiently,
    normalized = []

    # now find the youngest and oldest date
    for entry in msmt_results:
        bytes_measurement_point = 0

        # one entry can have multiple streams, so iterate over the
        # streams now
        for stream in entry:
            time = datetime.datetime.strptime(
                stream['ts-start'], '%Y-%m-%dT%H:%M:%S.%f')
        
            if time < datetime_min:
                datetime_min = time
            
                if prev_datetime_max_set == False:
                    prev_datetime_max = datetime_min
                    prev_datetime_max_set = True 

            time = datetime.datetime.strptime(
                stream['ts-end'], '%Y-%m-%dT%H:%M:%S.%f')
        
            if time > datetime_max:
                datetime_max = time

            bytes_measurement_point += int(stream['bytes'])

        # we got data from all streams of that entry
        curr_msmt_time = (datetime_max - datetime_min).total_seconds()
        bytes_per_period = bytes_measurement_point - bytes_rx
        mbits_per_period = (bytes_per_period * 8) / 10**6
        # bytes_rx == # bytes until now received
        bytes_rx = bytes_measurement_point

        # this works only if data is send immediately after prev_datetime_max
        # or we pay attention to a period where nothing is transmitted
        duration_of_period = (datetime_max - prev_datetime_max).total_seconds()
        prev_datetime_max = datetime_max
        throughput_of_period = mbits_per_period / duration_of_period
        normalized.append([curr_msmt_time, throughput_of_period])

    measurement_length = (datetime_max - datetime_min).total_seconds()
    bytes_sec = bytes_rx / measurement_length
    Mbits_sec = (bytes_sec * 8) / 10**6
    Kbits_sec = (bytes_sec * 8) / 10**3
    print('overall bandwith: {} bytes/sec'.format(bytes_sec))
    print('overall bandwith: {} Mbits/sec'.format(Mbits_sec))
    print('overall bandwith: {} Kbits/sec'.format(Kbits_sec))
    print('measurement length: {} sec]'.format(measurement_length))
    print('received: {} bytes]'.format(bytes_rx))

    # now plotting starts, not really fancy

    # normalize date to start with just 0 sec and not 2018-01-23 ...
    x = []
    y = []
    for i in normalized:
        x.append(i[0])
        y.append(i[1])

    fig = plt.figure()
    plt.plot(x, y)
    plt.ylabel('Throughput [MBits/s]')
    plt.xlabel('Time [seconds]')
    fig.savefig("./data/msmtResult.pdf", bbox_inches='tight')

def main(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
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

    analyze_data(msmt_results)



   
