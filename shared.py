import os
import paramiko
import time
import subprocess
import json

PASSWD = "yourpasswd"

def prepare_mapago(ctx):
    print("Preparing mapago")

def netem_reset(ctx, hostname, interfaces):
    print('\nReset netem on interfaces {} at {}'.format(interfaces, ctx.config[hostname]['ip-ctrl']))
    for interface in interfaces:
        cmd = 'sudo tc qdisc del dev {} root'.format(interface)
        # print("\nexecuting cmd: {}".format(cmd))
        stdout, stderr = ssh_execute(ctx, hostname, cmd, 10)
        print(stdout, stderr)


def netem_configure(ctx, hostname, interfaces=[], netem_params={'rate' : '100kbit'}):
    qdisc_id = 10
    netem_used = False
  
    # 0. sweep through interfaces
    for interface in interfaces:
        # 1. configure rate with tbf qdisc
        tbf_cmd = 'sudo tc qdisc add dev {} root handle {} tbf rate {} burst {} limit {}'.format(interface, qdisc_id, netem_params['rate'], '1540', '1540000')
        netem_cmd = 'sudo tc qdisc add dev {} parent {}: handle {} netem'.format(interface, qdisc_id, qdisc_id + 1) 

        # 2. sweep through desired params
        for param in netem_params:
            if param == 'rate':
                continue
            elif param == 'loss':
                netem_used = True
                netem_cmd += " loss {}%".format(netem_params[param])
            elif param == 'delay':
                netem_used = True
                netem_cmd += " delay {}ms".format(netem_params[param])
                ### check for future params ###
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

    print("\nargs of client", args)
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
