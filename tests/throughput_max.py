import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np


def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}
    supported_protocols = [
        "quic-throughput",
        "tcp-throughput",
        "tcp-tls-throughput",
        "udp-throughput"
        ]

    # TODO maybe as program parameters
    start_cores = 1
    stop_cores = 8
    step_rate = 1
    analyzing_cores = list(
        range(
            start_cores,
            stop_cores +
            step_rate,
            step_rate))
    num_iterations = 1
    iterations = list(range(num_iterations))

    for host in remoteHosts:
        avail = shared.host_alive(ctx, host)

        if not avail:
            raise Exception("Host {} not available".format(host))

    beta_iface_to_alpha = ctx.config['beta']['netem-interfaces-to-alpha']
    beta_iface_to_gamma = ctx.config['beta']['netem-interfaces-to-gamma']
    interfaces = [beta_iface_to_alpha, beta_iface_to_gamma]

    srv_params['-uc-listen-addr'] = '192.186.23.3'
    srv_params['-port'] = '64321'

    clt_params['-control-addr'] = '192.186.23.3'
    clt_params['-control-protocol'] = 'tcp'
    clt_params['-addr'] = '192.186.25.2'
    clt_params['-bytes'] = '140000000'
    clt_params['-deadline'] = '60'
    clt_params['-buffer-length'] = '1400'
    clt_params['-update-interval'] = '1'

    clt_bytes = int(clt_params['-bytes'])
    total_results = {}

    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))
        # TODO: move mapago_reset, prepare_server, netem_reset up
        shared.mapago_reset(ctx, 'gamma')
        shared.prepare_server(ctx, srv_params)
        shared.netem_reset(ctx, 'beta', interfaces=interfaces)

        x = []
        y = []

        for core in analyzing_cores:
            print("\n------ configuring cores to: {} --------".format(core))
            # stores all iteration results regarding a specific core
            kbits_per_core = []

            for iteration in iterations:
                print("\n -------- {}. iteration -------".format(iteration))

                clt_params['-module'] = '{}'.format(protocol)
                print("\n starting module: {}".format(clt_params['-module']))
                clt_params['-streams'] = '{}'.format(core)
                msmt_results = shared.prepare_client(ctx, clt_params)
                kbits_iter = analyze_data(msmt_results, protocol, clt_bytes)
                kbits_per_core.append(kbits_iter)

            kbits_per_core_normalized = 0

            # account all iters
            for kbits_iter in kbits_per_core:
                kbits_per_core_normalized += kbits_iter

            kbits_per_core_normalized = kbits_per_core_normalized / num_iterations
            print("\n mean kbits per core: {}".format(
                kbits_per_core_normalized))

            # future x axis (cores)
            x.append(core)

            # future y axis (throughput)
            y.append(kbits_per_core_normalized)

        # we are with this protocol finished add to total results
        total_results[protocol] = (x, y)
        print(total_results)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")

    plot_data(total_results)


def analyze_data(msmt_results, protocol, clt_bytes):
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

                if not prev_datetime_max_set:
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
        prev_datetime_max = datetime_max

    measurement_length = (datetime_max - datetime_min).total_seconds()
    bytes_sec = bytes_rx / measurement_length
    Mbits_sec = (bytes_sec * 8) / 10**6
    Kbits_sec = (bytes_sec * 8) / 10**3
    print('overall bandwith: {} bytes/sec'.format(bytes_sec))
    print('overall bandwith: {} Mbits/sec'.format(Mbits_sec))
    print('overall bandwith: {} Kbits/sec'.format(Kbits_sec))
    print('measurement length: {} sec]'.format(measurement_length))
    print('received: {} bytes]'.format(bytes_rx))

    # check if msmt failed
    if protocol == 'tcp-throughput' or protocol == 'quic-throughput' or protocol == 'tcp-tls-throughput':
        print("we have to check if msmt did not crash")
        if bytes_rx < clt_bytes:
            print(
                "\nmsmt has failed/crashed! Nothing transmitted within this iter! Try next iter!")
            return 0

    return Mbits_sec


def plot_data(total_results):
    fig = plt.figure()

    x_tcp = total_results["tcp-throughput"][0]
    y_tcp = total_results["tcp-throughput"][1]

    x_tcp_tls = total_results["tcp-tls-throughput"][0]
    y_tcp_tls = total_results["tcp-tls-throughput"][1]

    # print(x_tcp)
    # print(y_tcp)

    x_udp = total_results["udp-throughput"][0]
    y_udp = total_results["udp-throughput"][1]

    x_quic = total_results["quic-throughput"][0]
    y_quic = total_results["quic-throughput"][1]

    plt.plot(x_tcp, y_tcp, 'b-', label="TCP")
    plt.plot(x_tcp_tls, y_tcp_tls, 'g-', label="TCPTLS")
    plt.plot(x_udp, y_udp, 'y-', label="UDP")
    plt.plot(x_quic, y_quic, 'r-', label="QUIC")

    plt.ylabel('Throughput [MBits/s]')
    plt.xlabel('cores [#]')

    plt.xticks(np.arange(min(x_tcp), max(x_tcp) + 1, 1.0))
    plt.legend()

    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    fig.savefig(result_file, bbox_inches='tight')

def main(ctx):
    run_test(ctx)
