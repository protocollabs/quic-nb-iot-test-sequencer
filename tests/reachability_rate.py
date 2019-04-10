import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

analyzing_rates = [2, 5, 10, 15, 20, 25, 30]


# copy & paste from evaluation.py
def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}
    supported_protocols = [
        "tcp-throughput",
        "tcp-tls-throughput",
        # "udp-throughput",
        "quic-throughput"]
    # TODO maybe as program parameters
    
    
    '''
    use: start, stop interval or predefined msmt points 
    start_rate = 2
    stop_rate = 60
    step_rate = 2
    analyzing_rates = list(range(start_rate, stop_rate + step_rate, step_rate))
    '''
    print("analyzing rates: ", analyzing_rates)
    num_iterations = 5


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
    clt_params['-streams'] = '1'
    clt_params['-addr'] = '192.186.25.2'
    clt_params['-deadline'] = '60'
    clt_params['-buffer-length'] = '1400'
    clt_params['-update-interval'] = '1'
    total_results = {}

    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))
        # TODO: move mapago_reset, prepare_server, netem_reset up
        # shared.mapago_reset(ctx, 'gamma')
        # shared.prepare_server(ctx, srv_params)

        x = []
        y = []

        for rate in analyzing_rates:
            print("\n------ configuring rate to: {} --------".format(rate))

            shared.netem_reset(ctx, 'beta', interfaces=interfaces)
            shared.netem_configure(
                ctx, 'beta', interfaces=interfaces, netem_params={
                    'rate': '{}kbit'.format(rate)})

            clt_bytes = int(shared.calc_clt_bytes(rate))
            print("\nclt sends: {} bytes".format(clt_bytes))
            clt_params['-bytes'] = str(clt_bytes)

            success_total = []
            measurements_succeeded = 0

            for iteration in iterations:
                print("\n -------- {}. iteration -------".format(iteration))

                # ensure server is running per iter
                # note: using this we cant get "ssh" debug data
                # due to background cmd
                # we could implement a logging routine in mapago writing to a log file on srv...
                shared.mapago_reset(ctx, 'gamma')
                shared.prepare_server(ctx, srv_params)


                clt_params['-module'] = '{}'.format(protocol)
                print("\n starting module: {}".format(clt_params['-module']))
               
                msmt_results = []

                while len(msmt_results) < 1:
                    msmt_results = shared.prepare_client(ctx, clt_params)
                    
                    if len(msmt_results) < 1:
                        print("\nClient NOT terminated! reissue until client terminates!")

                success_iter = analyze_data(msmt_results, protocol, clt_bytes)
                # add success_value to list
                success_total.append(success_iter)
           
            # future x axis (rates)
            x.append(rate)

            # calculate "success value"
            if len(success_total) != num_iterations:
                raise Exception("list of success values does not math number of iterations!")

            for success_value in success_total:
                if success_value == 1:
                    measurements_succeeded += 1

            print("From {} finished {} successfully: ".format(num_iterations, measurements_succeeded))
            success_rate = int(float(measurements_succeeded / num_iterations) * 100)

            # future y axis (throughput)
            y.append(success_rate)

        # we are with this protocol finished add to total results
        total_results[protocol] = (x, y)
        shared.save_raw_data(os.path.basename(__file__)[:-3], total_results)   

        print(total_results)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")

    plot_data(total_results)


def analyze_data(msmt_results, protocol, clt_bytes):
    datetime_min = datetime.datetime(4000, 1, 1)
    datetime_max = datetime.datetime(1, 1, 1)

    bytes_rx = 0
    prev_datetime_max = datetime.datetime(1, 1, 1)
    prev_datetime_max_set = False

    for entry in msmt_results:
        bytes_measurement_point = 0

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

        # bytes_rx == # bytes until now received
        bytes_rx = bytes_measurement_point
        
        # this works only if data is send immediately after prev_datetime_max
        # or we pay attention to a period where nothing is transmitted
        prev_datetime_max = datetime_max

    # ok until here

    measurement_length = (datetime_max - datetime_min).total_seconds()
    if measurement_length == 0:
        print("\n timestamps identical. no data transmitted")
        return 0

    print('measurement length: {} sec]'.format(measurement_length))
    print('received: {} bytes]'.format(bytes_rx))

    # check if msmt failed: add tcp-tls-throughput
    if protocol == 'tcp-throughput' or protocol == 'quic-throughput' or protocol == 'tcp-tls-throughput':
        print("we have to check if msmt did not crash")
        if bytes_rx < clt_bytes:
            print(
                "\nmsmt has failed/crashed! Nothing transmitted within this iter! Try next iter!")
            return 0

    # this iteration is success == 1
    return 1



def plot_data(total_results):
    fig = plt.figure()

    x_tcp = total_results["tcp-throughput"][0]
    y_tcp = total_results["tcp-throughput"][1]

    x_tcp_tls = total_results["tcp-tls-throughput"][0]
    y_tcp_tls = total_results["tcp-tls-throughput"][1]

    x_quic = total_results["quic-throughput"][0]
    y_quic = total_results["quic-throughput"][1]

    plt.plot(x_tcp, y_tcp, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(x_tcp_tls, y_tcp_tls, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(x_quic, y_quic, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#984ea3', label="QUIC")

    plt.ylabel('reachability [%]')
    plt.xlabel('rate [KBit/s]')

    '''
    create tick intervals or use predefined list
    tick_interval = (max(x_quic) - min(x_quic)) / 10
    tick_interval_rounded = shared.round_xticks(tick_interval)

    # create ticks accordingly
    ticks = np.arange(min(x_tcp), max(x_tcp) + tick_interval_rounded, tick_interval_rounded)
    # debug print("created ticks: ", ticks)

    for tick in ticks:
        if len(str(tick)) >= 3:
            tick_index = np.where(ticks == tick)
            tick_rounded = round(tick, -2)
            ticks[tick_index] = tick_rounded
    
    
    # plt.xticks(ticks)
    '''

    plt.xticks(analyzing_rates)
   
    plt.legend()
    plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    fig.suptitle("Rate limitation: Large interval analysis\n {}".format(r'(Steps = 23, Iterations = 10, $t_{deadline} = 60s$)'), fontsize=10)
    fig.savefig(result_file, bbox_inches='tight')

def main(ctx):
    run_test(ctx)