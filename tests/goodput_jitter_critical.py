import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

analyzing_rates = [5, 50, 250, 500]
analyzing_delay = [0, 10, 50, 250, 1000, 10000]
jitter_ratio = 50
yticks_list = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


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

    print("rate: ", analyzing_rates)
    print("delay: ", analyzing_delay)

    num_iterations = 10
    timeout_ctr_limit = 3

    sim_dur = shared.calc_simulation_time(
        supported_protocols, num_iterations, timeout_ctr_limit, analyzing_rates, analyzing_delay)
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
        visited_delay = []
        quotients_all_rates_over_delays = []
        kbits_normalized = []

        # 2. iterate over rate
        for rate in analyzing_rates:
            print("\n------ configuring rate to: {} --------".format(rate))

            # 3. determine bytes for transmission regarding rate
            clt_bytes = int(shared.calc_clt_bytes(rate))
            clt_params['-bytes'] = str(clt_bytes)

            quotients_single_rate_over_delays = []
            analyzed_delay_per_rate = []

            # 4. deepest for loop: iterate over delay
            for delay in analyzing_delay:
                # holds results of ALL iters per single delay and rate tuple
                kbits_per_delay = []
                jitter = (float(delay) / 100) * jitter_ratio
                print("\nsetting jitter to: ", jitter)

                print(
                    "\n------ configuring delay and jitter to: {}, {} --------".format(delay, jitter))

                for iteration in iterations:
                    print("\n -------- {}. iteration -------".format(iteration))

                    # ensures we dont get stuck in a popen.wait(deadline) deadlock
                    timeout_ctr = 0

                    # reset queue at netem middlebox
                    shared.netem_reset(ctx, 'beta', interfaces=interfaces)

                    # 5. we know everything: so configure!
                    shared.netem_configure(
                        ctx, 'beta', interfaces=interfaces, netem_params={
                            'rate': '{}kbit'.format(rate), 'delay+jitter': '{}ms {}ms'.format(delay, jitter)})

                    # ensure server is running "fresh" per iter => no saved crypto cookies
                    # note: using this we cant get "ssh" debug data
                    # due to background cmd
                    # we could implement a logging routine in mapago writing to a log file on srv...
                    shared.mapago_reset(ctx, 'gamma')
                    shared.prepare_server(ctx, srv_params)

                    # ensures client mapago creation does not happen before server is ready
                    sleep(5)

                    clt_params['-module'] = '{}'.format(protocol)
                    print("\n starting module: {}".format(
                        clt_params['-module']))

                    msmt_results = []

                    while len(msmt_results) < 1 and timeout_ctr < timeout_ctr_limit:
                        print("\nIssueing prepare_client!\n")
                        msmt_results = shared.prepare_client(ctx, clt_params)

                        # check if client not terminated
                        if len(msmt_results) < 1:
                            print(
                                "\n!!!!!!Error!!!!!! Client NOT terminated! reissue until client terminates!")
                            timeout_ctr += 1

                    if timeout_ctr >= timeout_ctr_limit:
                        print("\nTimeout ctr limit reached! Iteration failed")
                        kbits_iter = 0
                    else:
                        kbits_iter = analyze_data(
                            msmt_results, protocol, clt_bytes)

                    kbits_per_delay.append(kbits_iter)

                kbits_per_delay_normalized = 0

                # account all iters
                for kbits_iter in kbits_per_delay:
                    kbits_per_delay_normalized += kbits_iter

                kbits_per_delay_normalized = kbits_per_delay_normalized / num_iterations
                print("\n mean kbits per delay: {}".format(
                    kbits_per_delay_normalized))

                # 6. calculate for single delay and rate tuple our goodput_rate_quotient
                # i.e. rate  = 5, delay = 2; rate = 5, delay = 5; rate = 5, delay = 10
                # "red"
                goodput_rate_quotient_avg = kbits_per_delay_normalized / rate

                # 7. add to list of quietnts for single rate iver losses
                quotients_single_rate_over_delays.append(
                    goodput_rate_quotient_avg)

                # 7.5 add los to list
                analyzed_delay_per_rate.append(delay)

            # 8. ok: we got all quoient for a given SINGLE rate and all LOSSES
            # add it to the list: where we store all RATES and the corresponding list
            # for the SINGLE rate and all LOSSES
            quotients_all_rates_over_delays.append(
                quotients_single_rate_over_delays)
            visited_rate.append(rate)
            visited_delay.append(analyzed_delay_per_rate)

        # 9. we got the list of lists for a single protocol complete: add it
        total_goodput_rate_avg[protocol] = (
            visited_rate, visited_delay, quotients_all_rates_over_delays)
        shared.save_raw_data(os.path.basename(__file__)[
                             :-3], total_goodput_rate_avg)

        print("\n visited_rate: ", visited_rate)
        print("\n visited_delay: ", visited_delay)
        print("\n total_goodput_rate_avg: ", total_goodput_rate_avg)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")

    '''
    QUIC thesis results:
    - These results were obtained in the context of the measurement
    - Used this line for verifying the result

    total_goodput_rate_avg = {"quic-throughput": [[5, 50, 250, 500], [[0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250]], [[0.0, 0.0, 0.0, 0.0], [0.80161227838563056, 0.8040652428144947, 0.8041416107786962, 0.7940765487525084], [0.8949120673581473, 0.8681223437939265, 0.8227633821170063, 0.0], [0.9020158717586202, 0.8678721881786707, 0.7935316913337243, 0.0]]], "tcp-throughput": [[5, 50, 250, 500], [[0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250]], [[0.8947504090914252, 0.6525793098184648, 0.7649036420047517, 0.8389996637955015], [0.9368367623192994, 0.7945618978868387, 0.8481709831094519, 0.8196944154301594], [0.9544446957447422, 0.9316989097856575, 0.924426515051143, 0.8985641638385886], [0.9563714427147644, 0.9561166758797403, 0.954858844154299, 0.9530127448208954]]], "tcp-tls-throughput": [[5, 50, 250, 500], [[0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250], [0, 10, 50, 250]], [[0.905965133648742, 0.625319284545624, 0.6197808646068161, 0.7395122680163873], [0.7789134555766118, 0.7740938538514139, 0.9094230363344891, 0.6078073032754268], [0.920490309867192, 0.7166749984938212, 0.7119296816954054, 0.8449847624341839], [0.8985949229726562, 0.8379584627409254, 0.7977987060452126, 0.7697167567685701]]]}
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

    quic_gp_avg_first_rate = gp_avg["quic-throughput"][2][0]
    quic_gp_avg_second_rate = gp_avg["quic-throughput"][2][1]
    quic_gp_avg_third_rate = gp_avg["quic-throughput"][2][2]
    quic_gp_avg_fourth_rate = gp_avg["quic-throughput"][2][3]

    # one can also use the other protocols loss values.
    # also ensures different loss values => add ons for future
    first_rate_delay_values = gp_avg["tcp-throughput"][1][0]
    second_rate_delay_values = gp_avg["tcp-throughput"][1][1]
    third_rate_delay_values = gp_avg["tcp-throughput"][1][2]
    fourth_rate_delay_values = gp_avg["tcp-throughput"][1][3]

    fig = plt.figure(figsize=(11, 9))
    ay1 = plt.subplot(411)

    plt.plot(fourth_rate_delay_values, tcp_gp_avg_fourth_rate,
             linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(fourth_rate_delay_values, tls_gp_avg_fourth_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    plt.plot(fourth_rate_delay_values, quic_gp_avg_fourth_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('mean delay [ms]', labelpad=0)
    plt.xticks(first_rate_delay_values)
    plt.yticks(yticks_list)
    plt.legend()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][3]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend(loc="center", bbox_to_anchor=(0.68, 0.4))
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.arrow(250.0, 0.5, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(600 UEs, Suburban)', xy=(250.0, 0.3),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(50.0, 0.3, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(200 UEs, Urban)', xy=(55.0, 0.05),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(10.0, 0.6, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('LTE-M \n(200 UEs, Urban)', xy=(10.0, 0.4),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.subplot(412)

    plt.plot(third_rate_delay_values, tcp_gp_avg_third_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(third_rate_delay_values, tls_gp_avg_third_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    plt.plot(third_rate_delay_values, quic_gp_avg_third_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('mean delay [ms]', labelpad=0)
    plt.xticks(first_rate_delay_values)
    plt.yticks(yticks_list)
    plt.legend()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][2]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend(loc="center", bbox_to_anchor=(0.68, 0.4))
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.arrow(250.0, 0.5, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(600 UEs, Suburban)', xy=(250.0, 0.3),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(50.0, 0.3, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(200 UEs, Urban)', xy=(55.0, 0.05),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(10.0, 0.4, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('LTE-M \n(200 UEs, Urban)', xy=(10.0, 0.2),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.subplot(413)

    plt.plot(second_rate_delay_values, tcp_gp_avg_second_rate,
             linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(second_rate_delay_values, tls_gp_avg_second_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    plt.plot(second_rate_delay_values, quic_gp_avg_second_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('mean delay [ms]', labelpad=0)
    plt.xticks(first_rate_delay_values)
    plt.yticks(yticks_list)
    plt.legend()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][1]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend(loc="center", bbox_to_anchor=(0.68, 0.4))
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.arrow(250.0, 0.4, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(600 UEs, Suburban)', xy=(250.0, 0.2),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(50.0, 0.3, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(200 UEs, Urban)', xy=(55.0, 0.05),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(10.0, 0.4, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('LTE-M \n(200 UEs, Urban)', xy=(10.0, 0.2),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.subplot(414)

    plt.plot(first_rate_delay_values, tcp_gp_avg_first_rate, linestyle=':',
             marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(first_rate_delay_values, tls_gp_avg_first_rate, linestyle='-.',
             marker='^', markersize=4, color='#4daf4a', label="TCP/TLS")
    plt.plot(first_rate_delay_values, quic_gp_avg_first_rate,
             linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('mean delay [ms]', labelpad=0)
    plt.xticks(first_rate_delay_values)
    plt.yticks(yticks_list)
    plt.legend()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][0]))

    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend(loc="center", bbox_to_anchor=(0.68, 0.4))
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.arrow(250.0, 0.5, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(600 UEs, Suburban)', xy=(250.0, 0.3),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(50.0, 0.3, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('NB-IoT \n(200 UEs, Urban)', xy=(55.0, 0.05),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.arrow(10.0, 0.4, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=3, head_length=0.1, label="NB-IoT 1")
    plt.annotate('LTE-M \n(200 UEs, Urban)', xy=(10.0, 0.2),
                 ha='center', fontsize=10, color="#e41a1c")

    plt.subplots_adjust(hspace=0.5)

    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    # fig.suptitle("Measurement campaign: Delay analysis \n {}".format(r'(Rate steps = 4, Delay steps = 6,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    #fig.suptitle("Impact of Jitter (50%): Microscopic analysis\n")
    fig.savefig(result_file, bbox_inches='tight')


def main(ctx):
    run_test(ctx)
