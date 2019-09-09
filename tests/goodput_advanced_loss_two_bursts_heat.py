import seaborn as sns
import os
import shared
import datetime
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
import numpy as np
np.random.seed(0)
sns.set()


analyzing_rates = [500, 250, 50, 5]
analyzing_mean_loss_bursts = [2, 4, 8, 16]
analyzing_mean_good_bursts = [100, 50, 25]
yticks_list = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


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

    sim_dur = shared.calc_simulation_time(
        supported_protocols, num_iterations, timeout_ctr_limit, analyzing_rates, analyzing_mean_loss_bursts)
    print("simulation duration for single per is: {}".format(sim_dur))
    print("simulation duration for {} good_bursts is: {}".format(
        len(analyzing_mean_good_bursts), len(analyzing_mean_good_bursts) * sim_dur[0]))

    '''
    QUIC thesis results:
    - These results were obtained in the context of the measurement
    - Used this line for verifying the result
    '''
    total_goodput_rate_avg_over_mean_per = {"25": {"tcp-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.3616450580977332, 0.0, 0.0, 0.0], [0.7234947141190292, 0.0, 0.0, 0.0], [0.9278888981614432, 0.5996304493905685, 0.0, 0.0], [0.8922310802098178, 0.2780643542771529, 0.0, 0.0]]], "tcp-tls-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.20886972200480453, 0.0, 0.0, 0.0], [0.7356625688614528, 0.0, 0.0, 0.0], [0.9169528368319088, 0.5024409361258316, 0.0, 0.0], [0.6833873917879962, 0.15321988407061807, 0.0, 0.0]]], "quic-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.7481241153171786, 0.34033798138246135, 0.0, 0.0], [0.897155362287013, 0.4813757475480597, 0.0, 0.0], [0.7450584883114868, 0.869712028761885, 0.5534287329464594, 0.0], [0.0, 0.0, 0.0, 0.0]]]}, "50": {"tcp-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.8332938324305929, 0.0, 0.0, 0.0], [0.9522346712010926, 0.37311149478163663, 0.0, 0.0], [0.9346601075656121, 0.7139442966051202, 0.2279162701541853, 0.0], [0.7352887142936739, 0.3036182771879675, 0.2731531575174177, 0.15353118933526913]]], "tcp-tls-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.8371767520031044, 0.0, 0.0, 0.0], [0.9197378416767897, 0.45035891136918105, 0.0, 0.0], [0.9250451750032288, 0.9165682532416928, 0.0, 0.0], [
        0.5861799456745075, 0.7485430119229288, 0.27744199130139224, 0.1528655752716819]]], "quic-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.8958718303327223, 0.7262371290095782, 0.0, 0.0], [0.899704914444364, 0.735718315752719, 0.11044326101851897, 0.0], [0.8993799611784086, 0.8961340219135785, 0.3007580842235445, 0.13454097718073696], [0.0, 0.0, 0.0, 0.0]]]}, "100": {"tcp-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.9515523382062098, 0.41353804612863443, 0.0, 0.0], [0.953372772177897, 0.7425003502736932, 0.2703997540235107, 0.0], [0.7305014429039499, 0.730493209215142, 0.6045949998468568, 0.0], [0.7585419095585217, 0.7093557385597014, 0.44193353159976345, 0.15301336038833968]]], "tcp-tls-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.9318681644972888, 0.571726416633851, 0.0, 0.0], [0.9352538049424096, 0.9369171724827207, 0.6430219681774378, 0.0], [0.9086096430202438, 0.8927189108374337, 0.700087880812091, 0.14565182529065013], [0.9056127208435207, 0.4505387172922034, 0.3029285170292169, 0.30213224793107224]]], "quic-throughput": [[500, 250, 50, 5], [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]], [[0.9000998879227554, 0.8885332409102622, 0.5087302354727139, 0.0], [0.9031369912931142, 0.9019036503250342, 0.7435758681218976, 0.4418874201949945], [0.8961946400188338, 0.9000579365061248, 0.883997947061482, 0.45129026826316043], [0.0, 0.0, 0.0, 0.0]]]}}

    plot_data(total_goodput_rate_avg_over_mean_per)


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

    print("processing data: ", gp_avg)

    quic500 = []
    tcp500 = []
    tls500 = []

    quic250 = []
    tcp250 = []
    tls250 = []

    quic50 = []
    tcp50 = []
    tls50 = []

    quic5 = []
    tcp5 = []
    tls5 = []

    analyzing_mean_good_bursts = [100, 50, 25]
    analyzing_mean_bad_bursts_inverted = [16, 8, 4, 2]

    # analyze good_bursts step by step
    for good_burst in analyzing_mean_good_bursts:

        for gb, proto_dict in gp_avg.items():

            # select a good_burst
            if gb == str(good_burst):

                # select śtep by step a protocol and process
                for proto, msmt_data in proto_dict.items():
                    print("\nanalyzing proto: ", proto)

                    # select a rate out of the rate list
                    for rate in msmt_data[0]:
                        print("\nanalyzing rate: ", rate)

                        # get index to get further data
                        index = msmt_data[0].index(rate)

                        # select corresponding bad bursts
                        bad_bursts = msmt_data[1][index]

                        # select result for good_burst, bad_bursts and rate
                        results = msmt_data[2][index]

                        # create tuples
                        for bad_burst in bad_bursts:
                            print("creating tuple for bad_burst: ", bad_burst)
                            index = bad_bursts.index(bad_burst)
                            result = results[index]

                            surface_tuple = (good_burst, bad_burst, result)
                            print("msmt_pt is: ", surface_tuple)

                            if rate == 500:
                                if proto == "tcp-throughput":
                                    tcp500.append(surface_tuple)
                                elif proto == "tcp-tls-throughput":
                                    tls500.append(surface_tuple)
                                elif proto == "quic-throughput":
                                    quic500.append(surface_tuple)
                                else:
                                    raise Exception('\nproto not supported!')

                            elif rate == 250:
                                if proto == "tcp-throughput":
                                    tcp250.append(surface_tuple)
                                elif proto == "tcp-tls-throughput":
                                    tls250.append(surface_tuple)
                                elif proto == "quic-throughput":
                                    quic250.append(surface_tuple)
                                else:
                                    raise Exception('\nproto not supported!')

                            elif rate == 50:
                                if proto == "tcp-throughput":
                                    tcp50.append(surface_tuple)
                                elif proto == "tcp-tls-throughput":
                                    tls50.append(surface_tuple)
                                elif proto == "quic-throughput":
                                    quic50.append(surface_tuple)
                                else:
                                    raise Exception('\nproto not supported!')

                            elif rate == 5:
                                if proto == "tcp-throughput":
                                    tcp5.append(surface_tuple)
                                elif proto == "tcp-tls-throughput":
                                    tls5.append(surface_tuple)
                                elif proto == "quic-throughput":
                                    quic5.append(surface_tuple)
                                else:
                                    raise Exception('\nproto not supported!')
                            else:
                                raise Exception('\nrate not supported!')

    print("\n\ntcp 500: ", tcp500)
    print("\n\nquic 500: ", quic500)
    print("\n\ntls 500: ", tls500)

    ### 500 kbits heatmaps ###

    quic500_values = []
    tcp500_values = []
    tls500_values = []

    # get quic values
    for tup in quic500:
        quic500_values.append(tup[2])

    # get tcp values
    for tup in tcp500:
        tcp500_values.append(tup[2])

    # get tcp values
    for tup in tls500:
        tls500_values.append(tup[2])

    # first plot
    fig = plt.figure(figsize=(35, 10))
    sns.set(font_scale=2.6)
    plt.subplot(131)

    np_array = np.array(quic500_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("QUIC", fontsize=35)

    plt.subplot(132)

    np_array = np.array(tls500_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP/TLS", fontsize=35)

    plt.subplot(133)

    np_array = np.array(tcp500_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues")

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP", fontsize=35)

    plt.subplots_adjust(wspace=0.5)
    msmt_name = os.path.basename(__file__)[:-3] + "HeatRate{}".format(500)
    result_file = shared.prepare_result(msmt_name)

    #fig.suptitle("Impact of varying the good burst / bad burst ratio for rate = {} KBit/s\n".format(500), fontsize=35)
    fig.savefig(result_file, bbox_inches='tight')

    ### 250 kbits heatmaps ###

    quic250_values = []
    tcp250_values = []
    tls250_values = []

    # get quic values
    for tup in quic250:
        quic250_values.append(tup[2])

    # get tcp values
    for tup in tcp250:
        tcp250_values.append(tup[2])

    # get tcp values
    for tup in tls250:
        tls250_values.append(tup[2])

    # first plot
    fig = plt.figure(figsize=(35, 10))
    plt.subplot(131)

    np_array = np.array(quic250_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("QUIC", fontsize=35)

    plt.subplot(132)

    np_array = np.array(tls250_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP/TLS", fontsize=35)

    plt.subplot(133)

    np_array = np.array(tcp250_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues")

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP", fontsize=35)

    plt.subplots_adjust(wspace=0.5)
    msmt_name = os.path.basename(__file__)[:-3] + "HeatRate{}".format(250)
    result_file = shared.prepare_result(msmt_name)

    #fig.suptitle("Impact of varying the good burst / bad burst ratio for rate = {} KBit/s\n".format(250), fontsize=35)
    fig.savefig(result_file, bbox_inches='tight')

    ### 50 kbits heatmaps ###

    quic50_values = []
    tcp50_values = []
    tls50_values = []

    # get quic values
    for tup in quic50:
        quic50_values.append(tup[2])

    # get tcp values
    for tup in tcp50:
        tcp50_values.append(tup[2])

    # get tcp values
    for tup in tls50:
        tls50_values.append(tup[2])

    # first plot
    fig = plt.figure(figsize=(35, 10))
    plt.subplot(131)

    np_array = np.array(quic50_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("QUIC", fontsize=35)

    plt.subplot(132)

    np_array = np.array(tls50_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP/TLS", fontsize=35)

    plt.subplot(133)

    np_array = np.array(tcp50_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues")

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP", fontsize=35)

    plt.subplots_adjust(wspace=0.5)
    msmt_name = os.path.basename(__file__)[:-3] + "HeatRate{}".format(50)
    result_file = shared.prepare_result(msmt_name)

    #fig.suptitle("Impact of varying the good burst / bad burst ratio for rate = {} KBit/s\n".format(50), fontsize=35)
    fig.savefig(result_file, bbox_inches='tight')

    ### 5 kbits heatmaps ###

    quic5_values = []
    tcp5_values = []
    tls5_values = []

    # get quic values
    for tup in quic5:
        quic5_values.append(tup[2])

    # get tcp values
    for tup in tcp5:
        tcp5_values.append(tup[2])

    # get tcp values
    for tup in tls5:
        tls5_values.append(tup[2])

    # first plot
    fig = plt.figure(figsize=(35, 10))
    plt.subplot(131)

    np_array = np.array(quic5_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("QUIC", fontsize=35)

    plt.subplot(132)

    np_array = np.array(tls5_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues", cbar=False)

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP/TLS", fontsize=35)

    plt.subplot(133)

    np_array = np.array(tcp5_values).reshape(
        3, 4).swapaxes(-2, -1)[..., ::-1, :]
    #print("\n\n numpy quic values are: ", np_array)

    # alternative: viridis
    ax = sns.heatmap(np_array, xticklabels=analyzing_mean_good_bursts,
                     yticklabels=analyzing_mean_bad_bursts_inverted, vmin=0.0, vmax=1.0, cmap="Blues")

    ax.set_xlabel('mean good bursts [# packets]', fontsize=35)
    ax.set_ylabel('mean loss bursts [# packets]', fontsize=35)
    ax.set_title("TCP", fontsize=35)

    plt.subplots_adjust(wspace=0.5)
    msmt_name = os.path.basename(__file__)[:-3] + "HeatRate{}".format(5)
    result_file = shared.prepare_result(msmt_name)

    #fig.suptitle("Impact of varying the good burst / bad burst ratio for rate = {} KBit/s\n".format(5), fontsize=35)
    fig.savefig(result_file, bbox_inches='tight')


def main(ctx):
    run_test(ctx)
