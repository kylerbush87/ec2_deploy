#!/bin/bash

ip=$1
login=$2
ssh_key=$3

ssh -i ec2-keypair.pem -o StrictHostKeyChecking=no ec2-user@${ip} <<EOF
    sudo adduser -m $login 
    sudo su - $login
    mkdir ~/.ssh
    echo $ssh_key >> ~/.ssh/authorized_keys
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/authorized_keys
EOF