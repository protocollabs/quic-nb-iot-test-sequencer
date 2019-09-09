import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

analyzing_rates = [5, 32, 50, 100, 200,
                   300, 400, 500, 600, 700, 800, 900, 1000]


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

    print("rate: ", analyzing_rates)
    print("num rates: ", len(analyzing_rates))

    num_iterations = 1
    timeout_ctr_limit = 1

    null_list = []

    sim_dur = shared.calc_simulation_time(
        supported_protocols, num_iterations, timeout_ctr_limit, analyzing_rates, null_list)
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

    total_results = {}
    total_results_debug = {}

    for protocol in supported_protocols:
        print("\n-------- analyzing: {} --------".format(protocol))

        x = []
        y = []
        kbits_normalized = []

        for rate in analyzing_rates:

            print("\n------ configuring rate to: {} --------".format(rate))

            clt_bytes = int(shared.calc_clt_bytes(rate))
            clt_params['-bytes'] = str(clt_bytes)

            kbits_per_rate = []

            for iteration in iterations:
                print("\n -------- {}. iteration -------".format(iteration))

                # ensures we dont get stuck in a popen.wait(deadline) deadlock
                timeout_ctr = 0

                shared.netem_reset(ctx, 'beta', interfaces=interfaces)

                shared.netem_configure(
                    ctx, 'beta', interfaces=interfaces, netem_params={
                        'rate': '{}kbit'.format(rate)})

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
                    print("\n\n!!!!!msmt_results are: ", msmt_results)

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

                kbits_per_rate.append(kbits_iter)

            kbits_per_rate_normalized = 0

            # account all iters
            for kbits_iter in kbits_per_rate:
                kbits_per_rate_normalized += kbits_iter

            kbits_per_rate_normalized = kbits_per_rate_normalized / num_iterations
            print("\n mean kbits per rate: {}".format(
                kbits_per_rate_normalized))

            # future x axis (rates)
            x.append(rate)

            goodput_rate_quotient = float(kbits_per_rate_normalized / rate)

            y.append(goodput_rate_quotient)
            kbits_normalized.append(kbits_per_rate_normalized)

        # we are with this protocol finished add to total results
        total_results[protocol] = (x, y)
        total_results_debug[protocol] = (x, kbits_normalized)
        print("goodput quotient for protocol: ", total_results)
        print("total_results_debug: ", total_results_debug)

        print("\nsleeping")
        sleep(5)
        print("\n next protocol")

    shared.save_raw_data(os.path.basename(__file__)[:-3], total_results)

    '''
    QUIC thesis results:
    - These results were obtained in the context of the measurement
    - Used this line for verifying the result

    total_results = {"quic-throughput": [[5, 10, 20, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000], [0.0, 0.0, 0.17472884612877984, 0.8701315313138502, 0.900674430137314, 0.8836232531438641, 0.9043438018408252, 0.9022970027368329, 0.9053202021144364, 0.9044266928868566, 0.9008601035756769, 0.8985781609879805, 0.8943688647685196, 0.8992099515581424, 0.8902051941776182, 0.9015261336798543, 0.9058510182810863, 0.9057869343757721, 0.9050223156050907, 0.9032431781756476, 0.9051188376465524, 0.9050972275878517, 0.9050213390406222]], "tcp-throughput": [[5, 10, 20, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000], [0.8997701942954309, 0.8481074849558826, 0.8735907563598297, 0.8552261157967564, 0.9555107303559349, 0.9552738066492426, 0.9465471361024512, 0.9487338370074273, 0.9560421518607741, 0.9563940715030865, 0.9564988367867315, 0.9564834349293552, 0.9564825408930998, 0.9564917785679427, 0.9564819430889135, 0.9564907010522428, 0.9564421050180923, 0.9564794204319842, 0.9564824754034514, 0.9564766921799631, 0.9564299231987449, 0.9564786378672557, 0.9564434363039512]], "tcp-tls-throughput": [[5, 10, 20, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000], [0.7524717869949266, 0.8885877242546745, 0.8625586137854138, 0.9364819720725567, 0.9365588852951474, 0.8845108963462857, 0.8741516075082751, 0.8936189013963933, 0.9208561994822891, 0.8893634715552303, 0.8918363754524067, 0.9263790318759653, 0.9150373509042751, 0.8774321559646711, 0.8919243475510181, 0.9125466936755275, 0.9133800873634771, 0.9092377243066316, 0.9015370029063486, 0.9195073104152476, 0.936451377991284, 0.9036112216391563, 0.9074145729243243]], "udp-throughput": [[5, 10, 20, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000], [0.9764753600864811, 0.9776803677881084, 0.9758944122037387, 0.9728942356771316, 0.9719206171999734, 0.9718542400619999, 0.9718548571432192, 0.9718562791327233, 0.9718542895185779, 0.9718536949767261, 0.9718537755667209, 0.9718533834222277, 0.9718527503029111, 0.9718518877354061, 0.971869042069788, 0.971851337927054, 0.971865132715147, 0.9718478311959186, 0.971847794874218, 0.9718469611224552, 0.9718443395739362, 0.9718426299926222, 0.9718521383176837]]}
    '''

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
    fig = plt.figure(figsize=(10, 6), facecolor='w')

    x_tcp = total_results["tcp-throughput"][0]
    y_tcp = total_results["tcp-throughput"][1]

    x_tcp_tls = total_results["tcp-tls-throughput"][0]
    y_tcp_tls = total_results["tcp-tls-throughput"][1]

    #x_udp = total_results["udp-throughput"][0]
    #y_udp = total_results["udp-throughput"][1]

    x_quic = total_results["quic-throughput"][0]
    y_quic = total_results["quic-throughput"][1]

    plt.plot(x_tcp, y_tcp, linestyle=':', marker='v',
             markersize=4, color='#377eb8', label="TCP")
    plt.plot(x_tcp_tls, y_tcp_tls, linestyle='-.', marker='^',
             markersize=4, color='#4daf4a', label="TCP/TLS")
    # plt.plot(x_udp, y_udp, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(x_quic, y_quic, linestyle=shared.linestyles['densely dashdotted'],
             marker='s', markersize=4, color='#ff7f00', label="QUIC")

    '''
    V0

    plt.axvline(x=32.4, color='grey', label='NB-IoT', linestyle='-')

    plt.axvline(x=800, color='grey', label='eMTC FDD', linestyle='-')

    plt.axvline(x=750, color='grey', label='eMTC TDD', linestyle='-')
    '''

    # V1
    plt.arrow(800.00, 0.75, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=20, head_length=0.05, label="eMTC")
    plt.text(880.0, 0.7, 'LTE-M FDD FD', color="#e41a1c")

    plt.arrow(300.00, 0.75, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=20, head_length=0.05, label="eMTC")
    plt.text(380.0, 0.7, 'LTE-M FDD HD', color="#e41a1c")

    plt.arrow(32.40, 0.0, 0.0, 0.05, fc="#e41a1c", ec="#e41a1c",
              head_width=20, head_length=0.05, label="eMTC")
    plt.text(72.4, -0.04, 'NB-IoT', color="#e41a1c")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('rate [KBit/s]')

    '''
    plt.text(880.0, -0.2, 'eMTC FDD FD', color="#e41a1c")
    plt.text(380.0, -0.2, 'eMTC FDD HD', color="#e41a1c")


    plt.text(72.4, -0.2, 'NB-IoT', color="#e41a1c")



    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('rate [KBit/s]')
    '''

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

    legend = plt.legend()
    # check alternatives
    # that sucks plt.ylim(bottom=0, top=1.0)

    plt.gca().invert_xaxis()
    # grid properties
    # plt.rc('grid', linestyle=":", color='black')
    plt.grid(color='darkgray', linestyle=':')
    # plt.box(on=True)
    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')

    xticks = ax.xaxis.get_major_ticks()
    xticks[1].label1.set_visible(False)

    # ax.get_xticklabels()[5].set_color("red")

    # ax.get_xticklabels()[10].set_color("red")
    # ax.get_xticklabels()[1].set_color("red")

    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    # fig.suptitle("Rate limitation: Large interval analysis\n {}".format(r'(Steps = 23, Iterations = 10, $t_{deadline} = 60s$)'), fontsize=10)

    fig.savefig(result_file, bbox_inches='tight')


def main(ctx):
    run_test(ctx)
