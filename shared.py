import os
import paramiko
import time
import subprocess
import json
import math
import asyncio
import random
from collections import OrderedDict

PASSWD = "yourpasswd"
MINBYTES = 300000
MAXBYTES = 30000000
CLT_TIMEOUT = 480


linestyles = OrderedDict(
    [('solid',               (0, ())),
     ('loosely dotted',      (0, (1, 10))),
     ('dotted',              (0, (1, 5))),
     ('densely dotted',      (0, (1, 1))),

     ('loosely dashed',      (0, (5, 10))),
     ('dashed',              (0, (5, 5))),
     ('densely dashed',      (0, (5, 1))),

     ('loosely dashdotted',  (0, (3, 10, 1, 10))),
     ('dashdotted',          (0, (3, 5, 1, 5))),
     ('densely dashdotted',  (0, (3, 1, 1, 1))),

     ('loosely dashdotdotted', (0, (3, 10, 1, 10, 1, 10))),
     ('dashdotdotted',         (0, (3, 5, 1, 5, 1, 5))),
     ('densely dashdotdotted', (0, (3, 1, 1, 1, 1, 1)))])

def prepare_mapago(ctx):
    print("Preparing mapago")


def netem_reset(ctx, hostname, interfaces):
    print('\nReset netem on interfaces {} at {}'.format(
        interfaces, ctx.config[hostname]['ip-ctrl']))
    for interface in interfaces:
        cmd = 'sudo tc qdisc del dev {} root'.format(interface)
        # print("\nexecuting cmd: {}".format(cmd))
        stdout, stderr = ssh_execute(ctx, hostname, cmd, 10)
        print(stdout, stderr)


def netem_configure(
    ctx,
    hostname,
    interfaces=[],
    netem_params={
        'rate': '100kbit'}):
    qdisc_id = 10
    netem_used = False

    # 0. sweep through interfaces
    for interface in interfaces:
        # 1. configure rate with tbf qdisc
        tbf_cmd = 'sudo tc qdisc add dev {} root handle {} tbf rate {} burst {} limit {}'.format(
            interface, qdisc_id, netem_params['rate'], '1540', '1540000')


        netem_cmd = 'sudo tc qdisc add dev {} parent {}: handle {} netem'.format(
            interface, qdisc_id, qdisc_id + 1)

        # 2. sweep through desired params
        for param in netem_params:
            if param == 'rate':
                continue
            elif param == 'loss':
                netem_used = True
                netem_cmd += " loss {}%".format(netem_params[param])
            elif param == 'simpleGilbertLoss':
                netem_used = True
                netem_cmd += " loss gemodel {}".format(netem_params[param])
            elif param == 'delay':
                netem_used = True
                netem_cmd += " delay {}ms".format(netem_params[param])
                ### check for future params ###
            elif param == 'delay+jitter':
                netem_used = True
                netem_cmd += " delay {}".format(netem_params[param])

            else:
                raise Exception('\nParam {} not supported!'.format(param))

        # send tbf cmd
        stdout, stderr = ssh_execute(ctx, hostname, tbf_cmd, 10)
        print(stdout, stderr)

        # send netem cmd
        if netem_used:
            stdout, stderr = ssh_execute(ctx, hostname, netem_cmd, 10)
            print(stdout, stderr)

        # increment handle for next interface
        qdisc_id = qdisc_id + 10


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
    stdout, stderr = ssh_execute(
        ctx, 'gamma', "source /etc/profile; echo $GOBIN", background=False)

    if stdout:
        # we have to source the profile again or mapago-server wont find the
        # envs
        cmd_str = 'source /etc/profile; ' + \
            stdout[0].rstrip() + '/mapago-server'
        param_str = ''

        for param in params:
            param_str += param + ' ' + params[param] + ' '

        cmd_str += ' '
        cmd_str += param_str

        # debug print("\nPrepare server: executing on server cmd:
        # {}".format(cmd_str))

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

    print("Debug output: Shared / args of client {}".format(args))

    popen = subprocess.Popen(
        tuple(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    
    try:
        print("Debug output: Shared / wait for process to terminate")
        popen.wait(timeout=CLT_TIMEOUT)

    except subprocess.TimeoutExpired:
        # cleanup
        print("Debug output: Shared / process NOT terminated. raise exception and return")
        popen.kill()
        return msmt_db

    print("Debug output: Shared / process terminated. contiuning")

    output_stdout = popen.stdout.read()
    output_stderr = popen.stderr.read()

    print("Debug output: Shared / process terminated. Right after reading stdout stderr")


    if len(output_stderr) is not 0:
        # debugging
        print(output_stderr)
        raise Exception('\nMapago-client return STDERR! Somethings broken!')

    lines_json = output_stdout.decode("utf-8")

    for line_json in lines_json.splitlines():
        msmt_db.append(json.loads(line_json))

    if len(msmt_db) < 1:
        raise Exception('\nWe need at least 1 msmt point')

    return msmt_db

async def aprepare_client(ctx, params):
    args = []
    msmt_db = []
    cmd_str = os.environ['GOBIN'] + '/mapago-client'

    args.append(cmd_str)

    for param in params:
        args.append(param)
        args.append(params[param])

    cmd = ' '.join(args)
    print("cmd is: ", cmd)

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    if stdout:
        print("\n\nstdout is: ", stdout.decode())
    if stderr:
        print("\n\nstdout is: ", stderr.decode())

    if len(stderr) is not 0:
        print(stderr)
        raise Exception('\nMapago-client return STDERR! Somethings broken!')

    lines_json = stdout.decode("utf-8")

    for line_json in lines_json.splitlines():
        msmt_db.append(json.loads(line_json))

    if len(msmt_db) < 1:
        raise Exception('\nWe need at least 1 msmt point')

    return msmt_db

async def rand_aprepare_client(ctx, params):
    args = []
    msmt_db = []
    cmd_str = os.environ['GOBIN'] + '/mapago-client'

    args.append(cmd_str)

    for param in params:
        args.append(param)
        args.append(params[param])

    cmd = ' '.join(args)

    sleep_time = random.uniform(0.0, 0.01)
    await asyncio.sleep(sleep_time)

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    if stdout:
        print("\ncorresponding cmd: ", cmd)
    if stderr:
        pass

    if len(stderr) is not 0:
        print(stderr)
        raise Exception('\nMapago-client return STDERR! Somethings broken!')

    lines_json = stdout.decode("utf-8")

    for line_json in lines_json.splitlines():
        msmt_db.append(json.loads(line_json))

    if len(msmt_db) < 1:
        raise Exception('\nWe need at least 1 msmt point')

    return msmt_db

def host_alive(ctx, hostname):
    print("\nChecking host {} with addr {}".format(
        hostname, ctx.config[hostname]['ip-ctrl']))

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
        ssh.connect(host, int(port), username, PASSWD)

        if background:
            transport = ssh.get_transport()
            channel = transport.open_session()

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

def prepare_result(msmt_name):
    path = "./data/" + msmt_name
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # TODO: We could also add a identifier to take series of plots
    result_file = path + "/" + msmt_name + ".pdf"
    return result_file 

def calc_clt_bytes(current_rate):
    clt_min_kbits = MINBYTES * 8 / (10**3)
    clt_max_kbits = MAXBYTES * 8 / (10**3)
    clt_min_kbits_s = 10
    clt_max_kbits_s = 1000 

    current_kbits = clt_min_kbits + ((clt_max_kbits - clt_min_kbits) / (clt_max_kbits_s - clt_min_kbits_s)) * (current_rate - clt_min_kbits_s)
    current_bytes = current_kbits * (10**3) / 8
    return current_bytes

def round_xticks(xtick):
    return int(math.ceil(xtick / 10.0)) * 10

def save_raw_data(msmt_name, msmt_data):
    path = "./data/" + msmt_name

    if not os.path.exists(path):
        os.makedirs(path)

    raw_result_file = path + "/" + msmt_name + ".txt"

    with open(raw_result_file, 'a') as f:
        data = json.dumps(msmt_data)
        f.write(data)
        
    if f.closed is True:
        print("File closed successfully!")
    else:
        print("file not closed")


def calc_simulation_time(protocols, iterations, timeout_limit, tbf_param, netem_params):
    num_protos = len(protocols)
    num_rates = len(tbf_param)
    num_netem_param = len(netem_params)
    iteration_dur_min = 240
    iteration_dur_max = CLT_TIMEOUT

    if len(netem_params) > 0:
        max_sim_time = num_protos * iterations * num_rates * num_netem_param * timeout_limit * iteration_dur_max
        min_sim_time = num_protos * iterations * num_rates * num_netem_param * iteration_dur_min
    else:
        max_sim_time = num_protos * iterations * num_rates * timeout_limit * iteration_dur_max
        min_sim_time = num_protos * iterations * num_rates * iteration_dur_min

    min_sim_time_h = float(min_sim_time) / 3600
    max_sim_time_h = float(max_sim_time) / 3600

    return (min_sim_time_h, max_sim_time_h)