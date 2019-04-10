import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

analyzing_rates = [5, 50, 250, 500]
analyzing_loss = [2, 5, 10, 20]

# copy & paste from evaluation.py
def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}
 
    supported_protocols = [
        "tcp-throughput",
        "tcp-tls-throughput",
        "udp-throughput",
        "quic-throughput"]
 
    '''
    use: start, stop interval or predefined msmt points 
    start_rate = 10
    stop_rate = 1000
    step_rate = 10
    analyzing_rates = list(range(start_rate, stop_rate + step_rate, step_rate))
    '''

    print("rate: ", analyzing_rates)

    # debug num_iterations = 10
    num_iterations = 4


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

    # goodput_rate_avg for all protocols
    total_goodput_rate_avg = {}
    total_results_debug = {}

    # 1. iterate over protocols
    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))
        # uncomment for debugability
        # shared.mapago_reset(ctx, 'gamma')
        # shared.prepare_server(ctx, srv_params)

        visited_rate = []
        visited_loss = []
        # goodput_rate_avg = []
        quotients_all_rates_over_losses = []

        kbits_normalized = []

        # 2. iterate over rate
        for rate in analyzing_rates:
            print("\n------ configuring rate to: {} --------".format(rate))

            shared.netem_reset(ctx, 'beta', interfaces=interfaces)

            
            # 3. determine bytes for transmission regarding rate
            clt_bytes = int(shared.calc_clt_bytes(rate))
            clt_params['-bytes'] = str(clt_bytes)

            quotients_single_rate_over_losses = []
            analyzed_loss_per_rate = []

            # 4. deepest for loop: iterate over loss
            for loss in analyzing_loss:
                print("\n------ configuring loss to: {} --------".format(loss))

                shared.netem_reset(ctx, 'beta', interfaces=interfaces)

                # 5. we know everything: so configure!
                # loss param needs no % => will be added
                shared.netem_configure(
                    ctx, 'beta', interfaces=interfaces, netem_params={
                        'rate': '{}kbit'.format(rate), 'loss': '{}'.format(loss)})
                
                # holds results of ALL iters per single loss and rate tuple
                kbits_per_loss = []

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
                        print("\nIssueing prepare_client!\n")
                        msmt_results = shared.prepare_client(ctx, clt_params)
                    
                        if len(msmt_results) < 1:
                            print("\n!!!!!!Error!!!!!! Client NOT terminated! reissue until client terminates!")

                    kbits_iter = analyze_data(msmt_results, protocol, clt_bytes)

                    kbits_per_loss.append(kbits_iter)

                kbits_per_loss_normalized = 0
                
                # account all iters
                for kbits_iter in kbits_per_loss:
                    kbits_per_loss_normalized += kbits_iter


                kbits_per_loss_normalized = kbits_per_loss_normalized / num_iterations
                print("\n mean kbits per loss: {}".format(
                    kbits_per_loss_normalized))

                # 6. calculate for single loss and rate tuple our goodput_rate_quotient
                # i.e. rate  = 5, loss = 2; rate = 5, loss = 5; rate = 5, loss = 10
                # "red"
                goodput_rate_quotient_avg = kbits_per_loss_normalized / rate

                # 7. add to list of quietnts for single rate iver losses
                quotients_single_rate_over_losses.append(goodput_rate_quotient_avg)

                # 7.5 add los to list
                analyzed_loss_per_rate.append(loss)



            # 8. ok: we got all quoient for a given SINGLE rate and all LOSSES
            # add it to the list: where we store all RATES and the corresponding list 
            # for the SINGLE rate and all LOSSES
            quotients_all_rates_over_losses.append(quotients_single_rate_over_losses)
            visited_rate.append(rate)
            visited_loss.append(analyzed_loss_per_rate)



        # 9. we got the list of lists for a single protocol complete: add it
        total_goodput_rate_avg[protocol] = (visited_rate, visited_loss, quotients_all_rates_over_losses)
        shared.save_raw_data(os.path.basename(__file__)[:-3], total_goodput_rate_avg)   
    

        print("\n visited_rate: ", visited_rate)
        print("\n visited_loss: ", visited_loss)
        print("\n total_goodput_rate_avg: ", total_goodput_rate_avg)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")

    # plot_data(total_results)


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

    return Kbits_sec


def plot_data(total_results):
    fig = plt.figure()

    x_tcp = total_results["tcp-throughput"][0]
    y_tcp = total_results["tcp-throughput"][1]

    x_tcp_tls = total_results["tcp-tls-throughput"][0]
    y_tcp_tls = total_results["tcp-tls-throughput"][1]

    x_udp = total_results["udp-throughput"][0]
    y_udp = total_results["udp-throughput"][1]

    x_quic = total_results["quic-throughput"][0]
    y_quic = total_results["quic-throughput"][1]

    plt.plot(x_tcp, y_tcp, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(x_tcp_tls, y_tcp_tls, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(x_udp, y_udp, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(x_quic, y_quic, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
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
    # check alternatives 
    # that sucks plt.ylim(bottom=0, top=1.0)
    
    plt.gca().invert_xaxis()
    # grid properties
    # plt.rc('grid', linestyle=":", color='black')
    plt.grid(color='darkgray', linestyle=':')


    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    fig.suptitle("Rate limitation: Large interval analysis\n {}".format(r'(Steps = 23, Iterations = 10, $t_{deadline} = 60s$)'), fontsize=10)
    fig.savefig(result_file, bbox_inches='tight')


def main(ctx):
    run_test(ctx)
    