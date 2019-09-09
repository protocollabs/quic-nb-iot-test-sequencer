import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

# debug analyzing_rates = [5, 50, 250, 500]
analyzing_rates = [32.4]
analyzing_loss = [2, 5, 10, 20]
yticks_list = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


# copy & paste from evaluation.py
def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}

    supported_protocols = [
        "quic-throughput",
        "tcp-tls-throughput",
        "tcp-throughput"
        ]


    print("rate: ", analyzing_rates)

    num_iterations = 10
    timeout_ctr_limit = 1

    sim_dur = shared.calc_simulation_time(supported_protocols, num_iterations, timeout_ctr_limit, analyzing_rates, analyzing_loss)
    print("simulation duration is: {}".format(sim_dur))

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
    clt_params['-deadline'] = '120'
    clt_params['-buffer-length'] = '1400'
    clt_params['-update-interval'] = '1'

    # goodput_rate_avg for all protocols
    total_goodput_rate_avg = {}
    total_results_debug = {}

    # 1. iterate over protocols
    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))

        visited_rate = []
        visited_loss = []
        quotients_all_rates_over_losses = []
        kbits_normalized = []

        # 2. iterate over rate
        for rate in analyzing_rates:
            print("\n------ configuring rate to: {} --------".format(rate))

            # 3. determine bytes for transmission regarding rate
            clt_bytes = int(shared.calc_clt_bytes(rate))
            clt_params['-bytes'] = str(clt_bytes)

            quotients_single_rate_over_losses = []
            analyzed_loss_per_rate = []

            # 4. deepest for-loop: iterate over loss
            for loss in analyzing_loss:
                print("\n------ configuring loss to: {} --------".format(loss))

                # holds results of ALL iters per single loss and rate tuple
                kbits_per_loss = []

                for iteration in iterations:
                    print("\n -------- {}. iteration -------".format(iteration))

                    # ensures we dont get stuck in a popen.wait(deadline) deadlock
                    timeout_ctr = 0

                    # reset queue at netem middlebox
                    shared.netem_reset(ctx, 'beta', interfaces=interfaces)

                    # 5. we know everything: so configure!
                    shared.netem_configure(
                    ctx, 'beta', interfaces=interfaces, netem_params={
                        'rate': '{}kbit'.format(rate), 'loss': '{}'.format(loss)})

                    # ensure server is running "fresh" per iter => no saved crypto cookies
                    # note: using this we cant get "ssh" debug data
                    # due to background cmd
                    # we could implement a logging routine in mapago writing to a log file on srv...
                    shared.mapago_reset(ctx, 'gamma')
                    shared.prepare_server(ctx, srv_params)

                    # ensures client mapago creation does not happen before server is ready
                    sleep(5)

                    clt_params['-module'] = '{}'.format(protocol)
                    print("\n starting module: {}".format(clt_params['-module']))

                    msmt_results = []

                    while len(msmt_results) < 1 and timeout_ctr < timeout_ctr_limit:
                        print("\nIssueing prepare_client!\n")
                        msmt_results = shared.prepare_client(ctx, clt_params)

                        if len(msmt_results) < 1:
                            print("\n!!!!!!Error!!!!!! Client NOT terminated! reissue until client terminates!")
                            timeout_ctr += 1

                    if timeout_ctr >= timeout_ctr_limit:
                        print("\nTimeout ctr limit reached! Iteration failed")
                        kbits_iter = 0
                    else:
                        kbits_iter = analyze_data(msmt_results, protocol, clt_bytes)

                    # kbits results of each iteration
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
                # for rate = 10 this holds the quotient values obtained for loss = [0,2,5,10 etc.]
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
    
    '''
    QUIC thesis results:
    - These results were obtained in the context of the measurement
    - Used this line for verifying the result

    total_goodput_rate_avg = {"tcp-tls-throughput": [[5, 50, 250, 500], [[2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20]], [[0.8891597466365523, 0.5787979494113162, 0.5979660648372906, 0.3421079203388403], [0.9360035942747428, 0.9344168006073792, 0.9020467869612119, 0.16925741828600896], [0.9371780129587632, 0.9309863983243959, 0.8191898148169389, 0.0], [0.936217360714619, 0.9169866165571696, 0.6900162243265879, 0.0]]], "tcp-throughput": [[5, 50, 250, 500], [[2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20]], [[0.7040478165359718, 0.5390127685375943, 0.5284654160370966, 0.06925536416031812], [
        0.9542509815803836, 0.945899790324797, 0.9070645305200603, 0.3012243408314037], [0.9566427584762381, 0.9496644967205237, 0.8187110321349055, 0.0], [0.9546542587711807, 0.9333090469513092, 0.7274759028379314, 0.0]]], "quic-throughput": [[5, 50, 250, 500], [[2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20], [2, 5, 10, 20]], [[0.0, 0.0, 0.08176505523901122, 0.0], [0.8875427154152246, 0.8957596165244399, 0.8842340464649212, 0.885437328984199], [0.9017941658628309, 0.8984700685214866, 0.8021639236522952, 0.44032593378946266], [0.9003184822783175, 0.8932963945690138, 0.7895173026470327, 0.5315150275732123]]]}
    
    '''

    plot_data(total_goodput_rate_avg)


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


def plot_data(gp_avg):

    tcp_gp_avg_first_rate = gp_avg["tcp-throughput"][2][0]
    tcp_gp_avg_second_rate = gp_avg["tcp-throughput"][2][1]
    tcp_gp_avg_third_rate = gp_avg["tcp-throughput"][2][2]
    tcp_gp_avg_fourth_rate = gp_avg["tcp-throughput"][2][3]

    tls_gp_avg_first_rate = gp_avg["tcp-tls-throughput"][2][0]
    tls_gp_avg_second_rate = gp_avg["tcp-tls-throughput"][2][1]
    tls_gp_avg_third_rate = gp_avg["tcp-tls-throughput"][2][2]
    tls_gp_avg_fourth_rate = gp_avg["tcp-tls-throughput"][2][3]

    '''
    udp_gp_avg_first_rate = gp_avg["udp-throughput"][2][0]
    udp_gp_avg_second_rate = gp_avg["udp-throughput"][2][1]
    udp_gp_avg_third_rate = gp_avg["udp-throughput"][2][2]
    udp_gp_avg_fourth_rate = gp_avg["udp-throughput"][2][3]
    '''

    quic_gp_avg_first_rate = gp_avg["quic-throughput"][2][0]
    quic_gp_avg_second_rate = gp_avg["quic-throughput"][2][1]
    quic_gp_avg_third_rate = gp_avg["quic-throughput"][2][2]
    quic_gp_avg_fourth_rate = gp_avg["quic-throughput"][2][3]

    # one can also use the other protocols loss values.
    # also ensures different loss values => add ons for future
    first_rate_loss_values = gp_avg["tcp-throughput"][1][0]
    second_rate_loss_values = gp_avg["tcp-throughput"][1][1]
    third_rate_loss_values = gp_avg["tcp-throughput"][1][2]
    fourth_rate_loss_values = gp_avg["tcp-throughput"][1][3]

    # first plot
    fig = plt.figure(figsize=(11, 9))
    plt.subplot(411)

    # here shoudl go the fourth rate

    plt.plot(fourth_rate_loss_values, tcp_gp_avg_fourth_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(fourth_rate_loss_values, tls_gp_avg_fourth_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    # plt.plot(fourth_rate_loss_values, udp_gp_avg_fourth_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(fourth_rate_loss_values, quic_gp_avg_fourth_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(fourth_rate_loss_values)
    plt.yticks(yticks_list)

    plt.legend()

    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][3]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend()
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.subplot(412)

    # here shoudl go the third rate

    plt.plot(third_rate_loss_values, tcp_gp_avg_third_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(third_rate_loss_values, tls_gp_avg_third_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    # plt.plot(third_rate_loss_values, udp_gp_avg_third_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(third_rate_loss_values, quic_gp_avg_third_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(third_rate_loss_values)
    plt.yticks(yticks_list)

    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][2]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend()
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.subplot(413)

    # here shoudl go the second rate
    plt.plot(second_rate_loss_values, tcp_gp_avg_second_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(second_rate_loss_values, tls_gp_avg_second_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    # plt.plot(second_rate_loss_values, udp_gp_avg_second_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(second_rate_loss_values, quic_gp_avg_second_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(second_rate_loss_values)
    plt.yticks(yticks_list)

    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][1]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend()
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.subplot(414)
    # here shoudl go the first rate
    plt.plot(first_rate_loss_values, tcp_gp_avg_first_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(first_rate_loss_values, tls_gp_avg_first_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    # plt.plot(first_rate_loss_values, udp_gp_avg_first_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(first_rate_loss_values, quic_gp_avg_first_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(first_rate_loss_values)
    plt.yticks(yticks_list)

    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][0]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend()
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.subplots_adjust(hspace=0.5)

    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    # fig.suptitle("Measurement module: Loss analysis\n {}".format(r'(Rate steps = 4, Loss steps = 4,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    #fig.suptitle("Impact of independent, random packet loss\n ")

    fig.savefig(result_file, bbox_inches='tight')


def main(ctx):
    run_test(ctx)
