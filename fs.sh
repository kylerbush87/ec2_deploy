#!/bin/bash

ip=$1
device=$2
mount=$3

ssh -i ec2-keypair.pem -o StrictHostKeyChecking=no ec2-user@${ip} <<EOF
    sudo mkfs.ext4 ${device}
    sudo mkdir ${mount}
    sudo mount ${device} ${mount}
    sudo chmod a+w ${mount}
    sudo chmod a+w /
    echo "${device} ${mount} auto noatime 0 0" | sudo tee -a /etc/fstab
EOF