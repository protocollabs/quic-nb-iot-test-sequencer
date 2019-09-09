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
    tcp = [0.84, 0.86, 0.84, 0.89]
    tls = [0.84, 0.89, 0.89, 0.72]
    quic = [0.21, 0.11, 0.33, 0.11]

    # 500 kbps resultds
    tcp = [0.95, 0.95, 0.95, 0.92]
    tls = [0.91, 0.93, 0.88, 0.89]
    quic = [0.90, 0.90, 0.89, 0.87]
    '''

    plot_data_bar_plot(quic, tls, tcp)


def plot_data_bar_plot(quic_result, tls_result, tcp_result):
    print("\n\nquic res: ", quic_result)
    print("\n\ntls res: ", tls_result)
    print("\n\ntls res: ", tls_result)


    ind = np.arange(0, len(quic_result) * 0.25, 0.25)  # the x locations for the groups
    # width = 0.35  # the width of the bars
    width = 0.05  # the width of the bars

    fig = plt.figure(figsize=(15, 10))
    ay1 = plt.subplot(211) 

    print("\nquic result", quic_result)
    print("\ntcp result", tls_result)

    rects1 = plt.bar(ind - 3.5 * width/3, quic_result, width, color='#ff7f00', label="QUIC")
    rects2 = plt.bar(ind, tls_result, width, color='#4daf4a', label="TCP/TLS")
    rects3 = plt.bar(ind + 3.5 * width/3, tcp_result, width, color='#377eb8', label="TCP")



    plt.ylabel('Goodput/rate [%]', fontsize=15)
    plt.xticks(ind)

    ay1.set_xticklabels(('10 ms', '50 ms', '250 ms', '1000 ms'), fontsize=15)
    
    plt.yticks(yticks_list)
    # plt.xlabel(('500', '250', '50'), fontsize=15)
    # plt.legend()
    legend = plt.legend()
    
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    autolabel(ay1, rects1, "left")
    autolabel(ay1, rects2, "center")
    autolabel(ay1, rects3, "right")

    # second plot

    '''
    ay2 = plt.subplot(212) 

    rects3 = plt.bar(ind - width/2, tcp_result[0], width, color='#377eb8', label='TCP/TLS1')
    rects4 = plt.bar(ind + width/2, tcp_result[1], width, color='#4daf4a', label='TCP/TLS2')


    plt.ylabel('Goodput/rate [%]', fontsize=15)
    plt.title('TCP + TLS', fontsize=15)
    plt.xticks(ind)
    ay2.set_xticklabels(('500', '250 KBit/s', '50 KBit/s'), fontsize=15)
    plt.yticks(yticks_list)
    # plt.xlabel(('500', '250', '50'), fontsize=15)
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    autolabel(ay2, rects3, "left")
    autolabel(ay2, rects4, "right")
    '''
    ax = plt.gca()
    ax.set_facecolor('white')
    plt.setp(ax.spines.values(), color='black')
    legend = plt.legend(loc="best", bbox_to_anchor=(0.15,0.7))
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor('white')

    plt.subplots_adjust(hspace = 0.5)
    msmt_name = os.path.basename(__file__)[:-3]
    result_file = shared.prepare_result(msmt_name)
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    # fig.suptitle("Measurement module: Loss analysis\n {}".format(r'(Rate steps = 4, Loss steps = 4,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    # iot fig.suptitle("Summary: Impact of Delay on NB-IoT (32.4 KBit/s)\n")
    # fig.suptitle("Summary: Impact of Delay for 500 KBit/s\n")
    

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


# this is outdated
def plot_data_smoothing_total(gp_avg, protocol):
    zero_x_axis_conn1 = []
    zero_x_axis_conn2 = []
    zero_y_axis_conn1 = []
    zero_y_axis_conn2 = []
    zero_xticks_list = []

    one_x_axis_conn1 = []
    one_x_axis_conn2 = []
    one_y_axis_conn1 = []
    one_y_axis_conn2 = []
    one_xticks_list = []


    two_x_axis_conn1 = []
    two_x_axis_conn2 = []
    two_y_axis_conn1 = []
    two_y_axis_conn2 = []
    two_xticks_list = []


    three_x_axis_conn1 = []
    three_x_axis_conn2 = []
    three_y_axis_conn1 = []
    three_y_axis_conn2 = []
    three_xticks_list = []

    rate = []
    for key, value in gp_avg.items():
        # key is now the specific rate
        # and value is the corresponding total_result

        if key == analyzing_rates[0]:
            print("plotting intra fairness for rate: ", key)
            zero_x_axis_conn1 = value[0][0]
            zero_x_axis_conn2 = value[0][1]

            zero_y_axis_conn1 = value[1][0]

            zero_y_axis_conn2 = value[1][1] 
            
            last_x_conn1 = zero_x_axis_conn1[-1]
            last_x_conn2 = zero_x_axis_conn2[-1]
            
            if last_x_conn1 >= last_x_conn2:
                last_x = last_x_conn1
            else:
                last_x = last_x_conn2

            current_x = 0
            zero_xticks_list.append(current_x)
            
            while current_x < last_x:
                current_x = current_x + 20
                zero_xticks_list.append(current_x)            


        elif key == analyzing_rates[1]:
            print("plotting intra fairness for rate: ", key)

            one_x_axis_conn1 = value[0][0]
            one_x_axis_conn2 = value[0][1]

            one_y_axis_conn1 = value[1][0]

            one_y_axis_conn2 = value[1][1] 

            
            last_x_conn1 = one_x_axis_conn1[-1]
            last_x_conn2 = one_x_axis_conn2[-1]
            
            if last_x_conn1 >= last_x_conn2:
                last_x = last_x_conn1
            else:
                last_x = last_x_conn2

            current_x = 0
            one_xticks_list.append(current_x)
            
            while current_x < last_x:
                current_x = current_x + 20
                one_xticks_list.append(current_x)    

        elif key == analyzing_rates[2]:
            print("plotting intra fairness for rate: ", key)

            two_x_axis_conn1 = value[0][0]
            two_x_axis_conn2 = value[0][1]

            two_y_axis_conn1 = value[1][0]

            two_y_axis_conn2 = value[1][1] 

            
            last_x_conn1 = two_x_axis_conn1[-1]
            last_x_conn2 = two_x_axis_conn2[-1]
            
            if last_x_conn1 >= last_x_conn2:
                last_x = last_x_conn1
            else:
                last_x = last_x_conn2

            current_x = 0
            two_xticks_list.append(current_x)
            
            while current_x < last_x:
                current_x = current_x + 20
                two_xticks_list.append(current_x)    

        ''' that wont work
        elif key == analyzing_rates[3]:
            print("plotting intra fairness for rate: ", key)
            
            three_x_axis_conn1 = value[0][0]
            three_x_axis_conn2 = value[0][1]

            three_y_axis_conn1 = value[1][0]

            three_y_axis_conn2 = value[1][1] 

            
            last_x_conn1 = three_x_axis_conn1[-1]
            last_x_conn2 = three_x_axis_conn2[-1]
            
            if last_x_conn1 >= last_x_conn2:
                last_x = last_x_conn1
            else:
                last_x = last_x_conn2

            current_x = 0
            three_xticks_list.append(current_x)
            
            while current_x < last_x:
                current_x = current_x + 20
                three_xticks_list.append(current_x) 
        '''

    # plot  the stuff


    # first plot
    fig = plt.figure(figsize=(11, 9))
    ay1 = plt.subplot(411) 

    plt.plot(zero_x_axis_conn1, zero_y_axis_conn1, marker='v', markersize=4, color='#377eb8', label="QUIC1")
    plt.plot(zero_x_axis_conn2, zero_y_axis_conn2, marker='v', markersize=4, color='#4daf4a', label="QUIC2")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('time [s]', labelpad=0)
    plt.xticks(zero_xticks_list)
    plt.yticks(yticks_list)
    
    
    plt.legend()

    
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(500))




    plt.subplot(412) 

    plt.plot(one_x_axis_conn1, one_y_axis_conn1, marker='v', markersize=4, color='#377eb8', label="QUIC1")
    plt.plot(one_x_axis_conn2, one_y_axis_conn2, marker='v', markersize=4, color='#4daf4a', label="QUIC2")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('time [s]', labelpad=0)
    plt.xticks(one_xticks_list)
    plt.yticks(yticks_list)
    
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(250))


    plt.subplot(413) 



    plt.plot(two_x_axis_conn1, two_y_axis_conn1, marker='v', markersize=4, color='#377eb8', label="QUIC1")
    plt.plot(two_x_axis_conn2, two_y_axis_conn2, marker='v', markersize=4, color='#4daf4a', label="QUIC2")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('time [s]', labelpad=0)
    plt.xticks(two_xticks_list)
    plt.yticks(yticks_list)
    

    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(50))



    ''' wont work atm
    plt.subplot(414) 


    plt.plot(3_x_axis_conn1, 3_y_axis_conn1, marker='v', markersize=4, color='#377eb8', label="QUIC1")
    plt.plot(3_x_axis_conn2, 3_y_axis_conn2, marker='v', markersize=4, color='#4daf4a', label="QUIC2")

    plt.ylabel('Goodput/rate [%]')
    plt.xlabel('time [s]', labelpad=0)
    plt.xticks(3_xticks_list)
    plt.yticks(yticks_list)
    
    plt.legend()
    # we dont need that plt.gca().invert_xaxis()
    plt.grid(color='darkgray', linestyle=':')
    plt.title('Rate: {} KBit/s'.format(5))

    '''





    plt.subplots_adjust(hspace = 0.5)
    msmt_name = os.path.basename(__file__)[:-3] + "{}".format(protocol)
    result_file = shared.prepare_result(msmt_name)
    # fig.suptitle(r'Rate limitation: Critical threshold analysis \n (Steps = 4, Iterations = 4, $\alpha_i > \beta_i$)', fontsize=14)
    # fig.suptitle("Measurement module: Loss analysis\n {}".format(r'(Rate steps = 4, Loss steps = 4,  Iterations = 4, $t_{deadline} = 60s$)'), fontsize=14)
    fig.suptitle("Intra-Protocol-Fairness: {}\n".format(protocol))
    
    fig.savefig(result_file, bbox_inches='tight')

def main(ctx):
    run_test(ctx)
    
