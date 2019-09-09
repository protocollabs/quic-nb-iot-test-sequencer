import os
import shared
import datetime
import matplotlib.pyplot as plt
from time import sleep
from operator import add
import numpy as np
from collections import OrderedDict

analyzing_rates = [500, 250, 50]
yticks_list = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def run_test(ctx):
    print('running test: {}'.format(os.path.basename(__file__)[:-3]))
    remoteHosts = ['beta', 'gamma']
    srv_params = {}
    clt_params = {}

    '''
    QUIC thesis results:
    - These results were obtained in the context of the measurement
    - Used this line for verifying the result

    # nb-iot result
    total_result = {"tcp-tls-throughput": [[32.4], [[2, 5, 10, 20]], [[0.89, 0.91, 0.90, 0.09]]], "quic-throughput": [[32.4], [[2, 5, 10, 20]], [[0.89, 0.87, 0.86, 0.88]]], "tcp-throughput": [[32.4], [[2, 5, 10, 20]], [[0.89, 0.93, 0.92, 0.0]]]}
    
    # 500 kbps resultds
    total_result = {"tcp-tls-throughput": [[500.0], [[2, 5, 10, 20]], [[0.93, 0.92, 0.71, 0.0]]], "quic-throughput": [[500.0], [[2, 5, 10, 20]], [[0.90, 0.89, 0.88, 0.67]]], "tcp-throughput": [[500.0], [[2, 5, 10, 20]], [[0.95, 0.93, 0.69, 0.0]]]}
    '''
    quic_res = []
    tls_res = []
    tcp_res = []

    # sanatize data
    for key, value in total_result.items():
        if key == "quic-throughput":
            quic_res = value[2][0]
        elif key == "tcp-tls-throughput":
            tls_res = value[2][0]
        elif key == "tcp-throughput":
            tcp_res = value[2][0]
        else:
            raise Exception('\n protocol {} not supported!'.format(key))

    print("quic res: ", quic_res)
    print("tls res: ", tls_res)
    print("tcp res: ", tcp_res)

    plot_data_bar_plot(quic_res, tls_res, tcp_res)


def plot_data_bar_plot(quic_result, tls_result, tcp_result):
    print("\n\nquic res: ", quic_result)
    print("\n\ntcp res: ", tcp_result)

    # CHANGES THE SPACE BETWEEN CLUSTERS
    # the x locations for the groups
    ind = np.arange(0, len(quic_result) * 0.25, 0.25)
    # width = 0.35  # the width of the bars
    width = 0.05  # the width of the bars

    fig = plt.figure(figsize=(15, 10))
    ay1 = plt.subplot(211)
    rects_quic = plt.bar(ind - 3.5 * width/3, quic_result,
                         width, color='#ff7f00', label='QUIC')
    rects_tls = plt.bar(ind, tls_result, width,
                        color='#4daf4a', label='TCP/TLS')
    rects_tcp = plt.bar(ind + 3.5 * width/3, tcp_result,
                        width, color='#377eb8', label='TCP')

    plt.ylabel('Goodput/rate [%]', fontsize=15)
    plt.xticks(ind)
    ay1.set_xticklabels(('2 % mean-PER', '5 % mean-PER',
                         '10 % mean-PER', '20 % mean-PER'), fontsize=15)
    plt.yticks(yticks_list)
    #plt.xlabel(('500', '250', '50'), fontsize=15)
    # plt.legend()
    legend = plt.legend()
    frame = legend.get_frame()
    frame.set_facecolor('white')

    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')

    autolabel(ay1, rects_quic, "left")
    autolabel(ay1, rects_tls, "center")
    autolabel(ay1, rects_tcp, "right")

    plt.subplots_adjust(hspace=0.5)

    plt.grid(color='darkgray', linestyle=':')
    # plt.box(on=True)
    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')

    msmt_name = os.path.basename(__file__)[:-3]
    result_file = shared.prepare_result(msmt_name)
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    # fig.suptitle("Measurement module: Loss analysis\n {}".format(r'(Rate steps = 4, Loss steps = 4,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    #fig.suptitle("Summary: Independent, random loss for 500 KBit/s\n")

    fig.savefig(result_file, bbox_inches='tight')


def autolabel(ax, rects, xpos='center'):
    """
    Attach a text label above each bar in *rects*, displaying its height.

    *xpos* indicates which side to place the text w.r.t. the center of
    the bar. It can be one of the following {'center', 'right', 'left'}.
    """

    xpos = xpos.lower()  # normalize the case of the parameter
    ha = {'center': 'center', 'right': 'left', 'left': 'right'}
    offset = {'center': 0.5, 'right': 0.57, 'left': 0.43}  # x_txt = x + w*off

    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()*offset[xpos], 1.01*height,
                '{}'.format(height), ha=ha[xpos], va='bottom')


def main(ctx):
    run_test(ctx)
