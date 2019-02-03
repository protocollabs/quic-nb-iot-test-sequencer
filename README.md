# QUIC Narrowband-IoT Test Sequencer

Can be used in combination with Mapago to evaluate and compare performance of
QUIC in NB-IoT


## Install Routine

This analyzer script uses paramiko for ssh handling.

```
aptitude install paramiko
```

## Preshared Keys

Please make sure you setuped every host and distributed the ssh keys.
Remember the password.

```
ssh-keygen -t rsa
```

Verify that everything works after key verification:

```
# ssh-agent should already be started
ssh-add
ssh hostname
```

## Sudo

Sudo must be configured to allow execution off all command without a password
prompt.

```
# /etc/sudoers file here FIXME
```

