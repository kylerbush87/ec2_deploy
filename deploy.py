import boto3
import yaml
import os
import time

with open(r'hosts.yml') as file:
    infraspec = yaml.full_load(file)
    for serv in infraspec:
        inf = {
            'instance_type'      :   infraspec["server"]["instance_type"]       ,
            'ami_type'           :   infraspec["server"]["ami_type"]            ,
            'architecture'       :   infraspec["server"]["architecture"]        ,
            'root_device_type'   :   infraspec["server"]["root_device_type"]    ,
            'virtualization_type':   infraspec["server"]["virtualization_type"] ,
            'min_count'          :   infraspec["server"]["min_count"]           ,
            'max_count'          :   infraspec["server"]["max_count"]           ,
        }

        num_of_drives = 0
        for vol in infraspec[serv]["volumes"]:
            if num_of_drives == 0 :
                bdm = [
                    {
                        'DeviceName'   :   vol["device"],
                        'Ebs'          :   { 'VolumeSize'  :   vol["size_gb" ], 'VolumeType'   :   'gp2'}
                    }
                ]
            else :
                bdm.append(
                    {
                        'DeviceName'    :   vol["device"],
                        'Ebs'           :   { 'VolumeSize'  :   vol["size_gb"], 'VolumeType'    :   'gp2'}
                    }
                )
            num_of_drives += 1

        num_of_users = 0
        for user in infraspec[serv]["users"]:
            user_key = "user_" + str(num_of_users)
            inf[user_key] = user
            num_of_users += 1

# I used the following aws cli command to get the latest linux ami
        ami_command = "aws ec2 describe-images --owners amazon --filters \"Name=name,Values={}-ami-hvm-2.0.????????.?-{}-gp2\" \"Name=state,Values=available\" --query \"reverse(sort_by(Images, &CreationDate))[:1].ImageId\" --output text".format(inf["ami_type"], inf["architecture"])
        stream = os.popen(ami_command)

        inf["image_id"] = stream.read().rstrip()
        print ("Making sure a suitable security group exists...")
        ec2 = boto3.client('ec2')
        response = ec2.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
        try:
            response = ec2.create_security_group(GroupName='ssh',
                                                 Description='allow ssh',
                                                 VpcId=vpc_id)
            security_group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

            data = ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])
            print('Ingress Successfully Set %s' % data)
        except Exception:
            pass

        print ("Creating EC2 instance...")
        inst = ec2.run_instances(
            ImageId=inf["image_id"],
            MinCount=inf["min_count"],
            MaxCount=inf["max_count"],
            InstanceType=inf["instance_type"],
            BlockDeviceMappings=bdm,
            KeyName='ec2-keypair',
            SecurityGroups=['ssh']
        )
        
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[inst["Instances"][0]["InstanceId"]], WaiterConfig={'Delay': 30, 'MaxAttempts': 60})
        print ("Waiting on instance to become available")
        response = ec2.describe_instances(InstanceIds=[inst["Instances"][0]["InstanceId"]])
        ip_addr = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
        print ("Setting up instance...")
        time.sleep(30)
        for vol in infraspec[serv]["volumes"]:
            if vol["mount"] == "/":
                continue
            else:
                fs_cmd = "./fs.sh %s %s %s" % (ip_addr, vol["device"], vol["mount"])
                os.system(fs_cmd)

        for user in infraspec[serv]["users"]:
            user_cmd = './users.sh %s %s "%s"' % (ip_addr, user["login"], user["ssh_key"] )
            os.system(user_cmd)

        print ("Finished...\nYou can login using\nssh -i ec2-keypair.pem user1@%s\nssh -i ec2-keypair.pem user2@%s" % (ip_addr, ip_addr))