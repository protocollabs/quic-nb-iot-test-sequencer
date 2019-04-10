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

    udp_gp_avg_first_rate = gp_avg["udp-throughput"][2][0]
    udp_gp_avg_second_rate = gp_avg["udp-throughput"][2][1]
    udp_gp_avg_third_rate = gp_avg["udp-throughput"][2][2]
    udp_gp_avg_fourth_rate = gp_avg["udp-throughput"][2][3]

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
    ay1 = plt.subplot(411) 

    plt.plot(first_rate_loss_values, tcp_gp_avg_first_rate, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(first_rate_loss_values, tls_gp_avg_first_rate, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(first_rate_loss_values, udp_gp_avg_first_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(first_rate_loss_values, quic_gp_avg_first_rate, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(first_rate_loss_values)
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][0]))




    plt.subplot(412, sharey=ay1) 

    plt.plot(second_rate_loss_values, tcp_gp_avg_second_rate, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(second_rate_loss_values, tls_gp_avg_second_rate, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(second_rate_loss_values, udp_gp_avg_second_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(second_rate_loss_values, quic_gp_avg_second_rate, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(second_rate_loss_values)
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][1]))


    plt.subplot(413, sharey=ay1) 

    plt.plot(third_rate_loss_values, tcp_gp_avg_third_rate, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(third_rate_loss_values, tls_gp_avg_third_rate, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(third_rate_loss_values, udp_gp_avg_third_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(third_rate_loss_values, quic_gp_avg_third_rate, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(third_rate_loss_values)
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][2]))




    plt.subplot(414, sharey=ay1) 

    plt.plot(fourth_rate_loss_values, tcp_gp_avg_fourth_rate, linestyle=':', marker='v', markersize=4, color='#377eb8', label="TCP")
    plt.plot(fourth_rate_loss_values, tls_gp_avg_fourth_rate, linestyle='-.', marker='^', markersize=4, color='#4daf4a', label="TCPTLS")
    plt.plot(fourth_rate_loss_values, udp_gp_avg_fourth_rate, linestyle='--', marker='o', markersize=4, color='#984ea3', label="UDP")
    plt.plot(fourth_rate_loss_values, quic_gp_avg_fourth_rate, linestyle=shared.linestyles['densely dashdotted'], marker='s', markersize=4, color='#ff7f00', label="QUIC")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('loss [%]', labelpad=0)
    plt.xticks(third_rate_loss_values)
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(gp_avg["tcp-throughput"][0][3]))



    plt.subplots_adjust(hspace = 0.5)
    result_file = shared.prepare_result(os.path.basename(__file__)[:-3])
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    fig.suptitle("Rate limitation: Critical threshold analysis\n {}".format(r'(Rate steps = 4, Loss steps = 4,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    fig.savefig(result_file, bbox_inches='tight')




def main(ctx):
    run_test(ctx)
    