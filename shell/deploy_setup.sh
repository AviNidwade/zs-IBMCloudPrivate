#!/bin/bash
if [ -f '/etc/redhat-release' ]; then
	sudo yum install -y epel-release
	sudo yum install -y python-pip
	sudo yum install -y yum-utils device-mapper-persistent-data lvm2
	sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
	sudo yum install -y docker-ce-18.03.0.ce
	sudo systemctl start docker
	sudo systemctl enable docker
	sudo docker pull ibmcom/icp-inception:3.1.0
	sudo mkdir /opt/ibm-cloud-private-ce-3.1.0
	cd /opt/ibm-cloud-private-ce-3.1.0
	sudo docker run -e LICENSE=accept -v "$(pwd)":/data ibmcom/icp-inception:3.1.0 cp -r cluster /data
	sudo pip install docker-compose
else
	sudo apt-get update -y
	sudo apt-get install apt-transport-https ca-certificates curl software-properties-common -y
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	sudo apt-key fingerprint 0EBFCD88
	sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
	sudo apt-get update -y
	sudo apt-get install docker-ce=18.03.0~ce-0~ubuntu
	sudo service docker start
	sudo docker pull ibmcom/icp-inception:3.1.0
	sudo mkdir /opt/ibm-cloud-private-ce-3.1.0
	cd /opt/ibm-cloud-private-ce-3.1.0
	sudo docker run -e LICENSE=accept -v "$(pwd)":/data ibmcom/icp-inception:3.1.0 cp -r cluster /data
	sudo apt install -y docker-compose
fi
sudo su
echo -e 'password\npassword\n' | passwd root
