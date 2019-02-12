import os
import paramiko
import time
import subprocess
import json
import datetime
import matplotlib.pyplot as plt

yourPw = "yourpasswd"

def prepare_mapago(ctx):
    print("Preparing mapago")

def netem_reset(ctx, hostname, interfaces):
    print('\nReset netem on interfaces {} at {}'.format(interfaces, ctx.config[hostname]['ip-ctrl']))
    for interface in interfaces:
        cmd = 'sudo tc qdisc del dev {} root'.format(interface)
        # print("\nexecuting cmd: {}".format(cmd))
        stdout, stderr = ssh_execute(ctx, hostname, cmd, 10)
        print(stdout, stderr)


# All Interfaces must be configured to rate 
def netem(ctx, hostname, interfaces=[], rate='100kbit', loss='0', delay='0'):
    netem_reset(ctx, hostname, interfaces)
    ip_ctrl = ctx.config[hostname]['ip-ctrl']
    for interface in interfaces:
        # TODO: format elements missing
        cmd = 'sudo tc qdisc add dev {} root netem rate {}'
        cmd = cmd.format(interface, rate)
        out, err = ssh_execute(ctx, hostname, cmd, 10)
        print(out)
        print(err)

def mapago_reset(ctx, hostname):
    print('\nReseting mapago on {}'.format(ctx.config[hostname]['ip-ctrl']))
    cmd = "ps -ef | grep \"mapago-server\" | grep -v grep | awk \'{print $2}\'"

    stdout, stderr = ssh_execute(ctx, 'gamma', cmd, background=False)
    # debug print("running mapagos have pid: {}".format(stdout))

    if stdout:
        for pid in stdout:
            print("\nkilling mapago with pid: {}".format(pid))
            cmd = "kill -9 " + pid
            stdout, stderr = ssh_execute(ctx, 'gamma', cmd, background=False)
            print(stdout, stderr)
    else: 
        print("\nNo mapago-servers to kill!")

def prepare_server(ctx, params):
    print("\nPreparing server")

    # determine gobin
    stdout, stderr = ssh_execute(ctx, 'gamma', "source /etc/profile; echo $GOBIN", background=False)

    if stdout:
        cmd_str = stdout[0].rstrip() + '/mapago-server'
       # debug print("starting server binary. pwd is: {}".format(cmd_str))
        param_str = ''

        for param in params:
            param_str += param + ' ' + params[param] + ' '

        cmd_str += ' '
        cmd_str += param_str

        ssh_execute(ctx, 'gamma', cmd_str, background=True)
    else:
        raise Exception('\nCould not determine GOBIN')


def prepare_client(ctx, params):
    print("\nPreparing client")

    args = []
    msmt_db = []
    cmd_str = os.environ['GOBIN'] + '/mapago-client'

    args.append(cmd_str)

    for param in params:
        args.append(param)
        args.append(params[param])

    popen = subprocess.Popen(tuple(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    popen.wait()
    output_stdout = popen.stdout.read()
    output_stderr = popen.stderr.read()

    if len(output_stderr) is not 0: 
        raise Exception('\nMapago-client return STDERR! Somethings broken!')        

    lines_json = output_stdout.decode("utf-8")
    for line_json in lines_json.splitlines():
        msmt_db.append(json.loads(line_json))        

    if len(msmt_db) < 1:
        raise Exception('\nWe need at least 1 msmt point')        

    return msmt_db

# copy & paste from evaluation.py
def analyze_data(msmt_results):
    print("\nDUMMY: Calling matplotlib to analyze msmt results")
    print("\nmsmt_res are: {}".format(msmt_results))

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
            
                if prev_datetime_max_set == False:
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
        duration_of_period = (datetime_max - prev_datetime_max).total_seconds()
        prev_datetime_max = datetime_max
        throughput_of_period = mbits_per_period / duration_of_period
        normalized.append([curr_msmt_time, throughput_of_period])

    measurement_length = (datetime_max - datetime_min).total_seconds()
    bytes_sec = bytes_rx / measurement_length
    Mbits_sec = (bytes_sec * 8) / 10**6
    Kbits_sec = (bytes_sec * 8) / 10**3
    print('overall bandwith: {} bytes/sec'.format(bytes_sec))
    print('overall bandwith: {} Mbits/sec'.format(Mbits_sec))
    print('overall bandwith: {} Kbits/sec'.format(Kbits_sec))
    print('measurement length: {} sec]'.format(measurement_length))
    print('received: {} bytes]'.format(bytes_rx))

    # now plotting starts, not really fancy

    # normalize date to start with just 0 sec and not 2018-01-23 ...
    x = []
    y = []
    for i in normalized:
        x.append(i[0])
        y.append(i[1])

    fig = plt.figure()
    plt.plot(x, y)
    plt.ylabel('Throughput [MBits/s]')
    plt.xlabel('Time [seconds]')
    fig.savefig("./data/msmtResult.pdf", bbox_inches='tight')
   

def host_alive(ctx, hostname):
    print("\nChecking host {} with addr {}".format(hostname, ctx.config[hostname]['ip-ctrl']))

    cmd = 'hostname'
    stdout, stderr = ssh_execute(ctx, hostname, cmd)
    print(stdout, stderr)
    
    return True


def ssh_execute(ctx, hostname, command, timeout=10, background=False):
    if hostname not in ('alpha', 'beta', 'gamma'):
        raise Exception('hostname not allowed')

    ssh = None
    key = None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        keyfilepath = ctx.config['ssh']['keyfilepath']
        password = ctx.config['ssh']['keypassword']

        # this creates the private key, assume it is encrypted
        pkey = paramiko.RSAKey.from_private_key_file(
            keyfilepath, password=password)

        host = ctx.config[hostname]['ip-ctrl']
        port = ctx.config['ssh']['port']
        username = ctx.config['ssh']['username']

        # NOTE: the passphrase/password has to be handed over or we cant unlock it
        # ...still we get an authentication error
        # ssh.connect(host, int(port), username, password, pkey=pkey, timeout=1.0)
        # use temporarily user/pwd not certificate
        ssh.connect(host, int(port), username, yourPw)

        if background:
            transport = ssh.get_transport()
            channel = transport.open_session()

            # what does this
            command = '{} > /dev/null 2>&1 &'.format(command)
            channel.exec_command(command)
            
            return None, None


        else:
            stdin, stdout, stderr = ssh.exec_command(command)
            # Wait for the command to terminate
            while not stdout.channel.exit_status_ready() and not stdout.channel.recv_ready():
                time.sleep(1)
                timeout -= 1
                if timeout <= 0:
                    break

            stdoutstring = stdout.readlines()
            stderrstring = stderr.readlines()
            return stdoutstring, stderrstring

    finally:
        if ssh is not None:
            # Close client connection.
            ssh.close()
