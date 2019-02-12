import os
import paramiko
import time

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

    cmd = "pidof ./mapago-server"
    stdout, stderr = ssh_execute(ctx, 'gamma', cmd, background=False)
    # debug print(stdout, stderr)

    pid = stdout[0]
    cmd = "kill -9 " + pid
    # print("\nexecuting cmd: {}".format(cmd))

    stdout, stderr = ssh_execute(ctx, 'gamma', cmd, background=False)
    print(stdout, stderr)

def prepare_server(ctx):
    print("Preparing server")


def prepare_client(ctx):
    print("Preparing client")


def analyze_data(ctx):
    print("Calling matplotlib to analyze msmt results")

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
            cmd = '{} > /dev/null 2>&1 &'.format(cmd)
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
