import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

analyzing_rates = [2, 5, 10, 15, 20, 25, 30, 40, 50]


# copy & paste from evaluation.py
def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}

    supported_protocols = [
        "tcp-throughput",
        "tcp-tls-throughput",
        "quic-throughput"
        ]
    
    '''
    use: start, stop interval or predefined msmt points 
    start_rate = 2
    stop_rate = 60
    step_rate = 2
    analyzing_rates = list(range(start_rate, stop_rate + step_rate, step_rate))
    '''

    print("rate: ", analyzing_rates)
    num_iterations = 10 

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
    #clt_params['-buffer-length'] = '1400'
    clt_params['-buffer-length'] = '1400'
    clt_params['-update-interval'] = '1'

    total_goodput_rate_avg = {}
    total_goodput_rate_max = {}
    total_goodput_rate_min = {}
    total_results_debug = {}

    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))
        # uncomment for debugability
        # shared.mapago_reset(ctx, 'gamma')
        # shared.prepare_server(ctx, srv_params)

        x = []
        # goodput_rate_avg
        goodput_rate_avg = []

        # goodput_rate_max
        goodput_rate_max = []

        # goodput_rate_min
        goodput_rate_min = []

        kbits_normalized = []

        for rate in analyzing_rates:
            print("\n------ configuring rate to: {} --------".format(rate))

            shared.netem_reset(ctx, 'beta', interfaces=interfaces)
            shared.netem_configure(
                ctx, 'beta', interfaces=interfaces, netem_params={
                    'rate': '{}kbit'.format(rate)})
            
            clt_bytes = int(shared.calc_clt_bytes(rate))
            clt_params['-bytes'] = str(clt_bytes)

            kbits_per_rate = []
            kbits_min = 0
            kbits_max = 0
            kbits_min_rate = 0
            kbits_max_rate = 0

            for iteration in iterations:
                print("\n -------- {}. iteration -------".format(iteration))

                clt_params['-module'] = '{}'.format(protocol)
                print("\n starting module: {}".format(clt_params['-module']))
                
                msmt_results = []

                while len(msmt_results) < 1:
                    msmt_results = shared.prepare_client(ctx, clt_params)
                    
                    if len(msmt_results) < 1:
                        print("\nClient NOT terminated! reissue until client terminates!")

                kbits_iter = analyze_data(msmt_results, protocol, clt_bytes)

                # 1. used to calculate AVG
                kbits_per_rate.append(kbits_iter)

                # 2. MAX: evaluate if current kbits_iter > max value until now
                if kbits_max == 0 and kbits_max_rate == 0:
                    kbits_max = kbits_iter
                    kbits_max_rate = rate

                if kbits_iter > kbits_max:
                    kbits_max = kbits_iter
                    kbits_max_rate = rate

                # 3. MIN: evaluate if current kbits_iter < min value until now
                if kbits_min == 0 and kbits_min_rate == 0:
                    kbits_min = kbits_iter
                    kbits_min_rate = rate

                if kbits_iter < kbits_min:
                    kbits_min = kbits_iter
                    kbits_min_rate = rate

            kbits_per_rate_normalized = 0

            # 4. Calculate AVG
            for kbits_iter in kbits_per_rate:
                kbits_per_rate_normalized += kbits_iter
            #
            kbits_per_rate_normalized = kbits_per_rate_normalized / num_iterations
            print("\n mean kbits per rate: {}".format(
                kbits_per_rate_normalized))

            goodput_rate_quotient_avg = float(kbits_per_rate_normalized / rate)

            # future x axis (rates)
            x.append(rate)

            # future goodput_rate_avg axis (throughput)
            goodput_rate_avg.append(goodput_rate_quotient_avg)

            # 5. Calculate / add MAX
            goodput_rate_quotient_max = kbits_max / kbits_max_rate
            goodput_rate_max.append(goodput_rate_quotient_max)

            # 6. Calculate / add MIN
            goodput_rate_quotient_min = kbits_min / kbits_min_rate
            goodput_rate_min.append(goodput_rate_quotient_min)

            # debug stuff
            kbits_normalized.append(kbits_per_rate_normalized)

        # we are with this protocol finished add to total results
        total_goodput_rate_avg[protocol] = (x, goodput_rate_avg)
        total_results_debug[protocol] = (x, kbits_normalized)

        total_goodput_rate_max[protocol] = (x, goodput_rate_max)
        total_goodput_rate_min[protocol] = (x, goodput_rate_min)

        print("goodput quotient avg for protocol: ", goodput_rate_avg)
        print("goodput quotient max for protocol: ", goodput_rate_max)
        print("goodput quotient min for protocol: ", goodput_rate_min)
        print("\ntotal_results_debug: ", total_results_debug)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")


    # plot_data(goodput_rate_avg, goodput_rate_max, goodput_rate_min)
    plot_data(total_goodput_rate_avg, total_goodput_rate_max, total_goodput_rate_min)


def analyze_data(msmt_results, protocol, clt_bytes):
    # min and max will at the end of the next loop contain
    # the real min and max values
    datetime_min = datetime.datetime(4000, 1, 1)
    datetime_max = datetime.datetime(1, 1, 1)

    # Keep in mind for all byte accounting here:
    # it is transmitted in a ABSOLUTE manner, no differences
    # are signaled via mapago
    bytes_rx = 0
    # prev_bytes_rx = 0
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
        # prev_bytes_rx = bytes_rx

        # this works only if data is send immediately after prev_datetime_max
        # or we pay attention to a period where nothing is transmitted
        prev_datetime_max = datetime_max

    measurement_length = (datetime_max - datetime_min).total_seconds()
    if measurement_length == 0:
        print("\n timestamps identical. no data transmitted")
        return 0


    bytes_sec = bytes_rx / measurement_length
    Mbits_sec = (bytes_sec * 8) / 10**6
    Kbits_sec = (bytes_sec * 8) / 10**3
    print('overall bandwith: {} bytes/sec'.format(bytes_sec))
    print('overall bandwith: {} Mbits/sec'.format(Mbits_sec))
    print('overall bandwith: {} Kbits/sec'.format(Kbits_sec))
    print('measurement length: {} sec]'.format(measurement_length))
    print('received: {} bytes]'.format(bytes_rx))

    # check if msmt failed: add tcp-tls-throughput
    if protocol == 'tcp-throughput' or protocol == 'quic-throughput' or protocol == 'tcp-tls-throughput':
        print("we have to check if msmt did not crash")
        if bytes_rx < clt_bytes:
            print(
                "\nmsmt has failed/crashed! Nothing transmitted within this iter! Try next iter!")
            return 0

    # we have to check for socket termination

    return Kbits_sec



def plot_data(gp_avg, gp_max, gp_min):
    tcp_rate = gp_avg["tcp-throughput"][0]
    tcp_avg = gp_avg["tcp-throughput"][1]
    tcp_max = gp_max["tcp-throughput"][1]
    tcp_min = gp_min["tcp-throughput"][1]

    tls_rate = gp_avg["tcp-tls-throughput"][0]
    tls_avg = gp_avg["tcp-tls-throughput"][1]
    tls_max = gp_max["tcp-tls-throughput"][1]
    tls_min = gp_min["tcp-tls-throughput"][1]

    quic_rate = gp_avg["quic-throughput"][0]
    quic_avg = gp_avg["quic-throughput"][1]
    quic_max = gp_max["quic-throughput"][1]
    quic_min = gp_min["quic-throughput"][1]


    fig = plt.figure(figsize=(11, 9))
    # fig = plt.figure(figsize=(13, 11))


    ay1 = plt.subplot(311) 

    plt.plot(tcp_rate, tcp_avg, linestyle='-', marker='v', color='#377eb8', label="Average")
    plt.plot(tcp_rate, tcp_max, linestyle='-', marker='o', color='#4daf4a', label="Maximum")
    plt.plot(tcp_rate, tcp_min, linestyle='-', marker='s', color='#984ea3', label="Minimum")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('rate [KBit/s]', labelpad=0)
    plt.xticks(analyzing_rates)
    plt.legend()
    plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('TCP')




    plt.subplot(312, sharey=ay1) 

    plt.plot(tls_rate, tls_avg, linestyle='-', marker='v', color='#377eb8', label="Average")
    plt.plot(tls_rate, tls_max, linestyle='-', marker='o', color='#4daf4a', label="Maximum")
    plt.plot(tls_rate, tls_min, linestyle='-', marker='s', color='#984ea3', label="Minimum")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('rate [KBit/s]', labelpad=0)
    plt.xticks(analyzing_rates)
    plt.legend()
    plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('TCP/TLS')


    plt.subplot(313, sharey=ay1)

    plt.plot(quic_rate, quic_avg, linestyle='-', marker='v', color='#377eb8', label="Average")
    plt.plot(quic_rate, quic_max, linestyle='-', marker='o', color='#4daf4a', label="Maximum")
    plt.plot(quic_rate, quic_min, linestyle='-', marker='s', color='#984ea3', label="Minimum")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('rate [KBit/s]', labelpad=0)
    plt.xticks(analyzing_rates)
    plt.legend()
    plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')

    plt.title('QUIC')


    plt.subplots_adjust(hspace = 0.5)
    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    fig.suptitle("Rate limitation: Critical threshold analysis\n {}".format(r'(Steps = 10, Iterations = 10, $t_{deadline} = 60s$)'), fontsize=14)
    fig.savefig(result_file, bbox_inches='tight')
    
def main(ctx):
    run_test(ctx)