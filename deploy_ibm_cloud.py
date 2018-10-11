import __future__
import os
import sys
import requests
import shutil
import subprocess
import json
import pprint
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

zsbuname = raw_input("Please enter an IBM Cloud Business Unit name: ")
username = raw_input("Please enter an IBM Cloud Business Unit Admin name: ")
password = raw_input("Please enter the admin password, CAUTION: This is in plain text: ")
email = raw_input("Please enter the IBM Cloud BU admin email: ")
#imagename = raw_input("Please enter a valid OS image name from your image library: ")

auth_username = os.getenv('OS_USERNAME',None)
auth_password = os.getenv('OS_PASSWORD',None)
auth_url = os.getenv('OS_AUTH_URL',None)
project_name = os.getenv('OS_PROJECT_NAME',None)
user_domain_name = os.getenv('OS_USER_DOMAIN_NAME',None)
project_domain_name = os.getenv('OS_PROJECT_DOMAIN_NAME',None)
cacert = os.getenv('OS_CACERT',None)
user_region = os.getenv('OS_REGION',None)

if(auth_username == None or auth_password == None or auth_url == None or \
   project_name == None or user_region == None or user_domain_name == None or \
   project_domain_name == None or cacert == None):
    print "Export the Zerostack RC file, or explicitly define authentication environment variables."
    sys.exit(1)

if(user_region == None):
    print "Add user region variable OS_REGION to the Zerostack rc file and re-export, or export OS_REGION as an environment variable."
    sys.exit(1)

#get the region ID
regionsplit = auth_url.split('/')
region_id = regionsplit[6]

#get the base url
baseurl = auth_url[:-12]

#get the login token
try:
    body = '{"auth":{"identity":{"methods":["password"],"password":{"user":{"domain":{"name":"%s"},"name":"%s","password":"%s"}}},"scope":{"domain":{"name":"%s"}}}}' \
           %(project_domain_name,auth_username,auth_password,project_domain_name)
    #headers={"content-type":"application/json"}
    token_url = auth_url+'/auth/tokens'
    trequest = requests.post(token_url,verify = False,data = body,headers={"content-type":"application/json"})
    jtoken = json.loads(trequest.text)
    admin_user_id = jtoken['token']['user']['id']
    token = trequest.headers.get('X-Subject-Token')
except Exception as e:
    print e
    sys.exit(1)

print "Looking for the default image"
image_id = None
try:
    send_url = baseurl + '/glance/v2/images?visibility=public'
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    images = json.loads(r.text)
    count = 0
    im = []
    for image in images['images']:
        im.append({'count':count,'imagename':image['name'],'imageid':image['id']})
        count += 1
except Exception as e:
    print e
    sys.exit(1)

for i in im:
    print "ID: %s   Name: %s"%(i['count'],i['imagename'])

try:
    imid = raw_input('Enter the ID of the image to use: ')
    for i in im:
        if(i['count'] == int(imid)):
            image_id = i['imageid']
            break
except Exception as e:
    print e
    sys.exit(1)


#Create a new BU
domain_id = None
print "\n\nCreating IBM Cloud Business Unit: %s"%(zsbuname)
try:
    send_url = auth_url + '/domains'
    data = '{"domain":{"name":"%s","description":"BU created on by %s.","ldapSet":false}}'%(zsbuname,auth_username)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    if(r.status_code == 409):
        print "BU %s already exists."%(zsbuname)
        sys.exit(1)
    j = json.loads(r.text)
    #get the domain id
    domain_id = j['domain']['id']
except Exception as e:
    print e
    sys.exit(1)
print "%s business unit has been created, ID: %s.\n\n"%(zsbuname,domain_id)

#get the roles and find the Admin role ID
admin_id = None
print "Gathering the available roles."
try:
    send_url = auth_url + '/roles'
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    for role in j['roles']:
        if(role['name'] == 'admin'):
            admin_id = role['id']
except Exception as e:
    print e
    sys.exit(1)
print "Found the admin role ID: %s\n\n"%(admin_id)


#Create a BU admin
print "Creating the IBM Cloud BU Admin account for %s."%(username)
user_id = None
try:
    send_url = auth_url + '/users'
    data = '{"user":{"email":"%s","enabled":true,"name":"%s","domain_id":"%s","password":"%s"}}'%(email,username,domain_id,password)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    user_id = j['user']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created IBM Cloud BU Admin with ID: %s.\n\n"%(user_id)

#createing the control project
print "Creating the IBM CLoud BU %s control project."%(zsbuname)
project_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/projects'%(region_id)
    data = '{"description":"IBM Cloud Project for %s BU.","domain_id":"%s","name":"IBM Cloud","finite_duration":false,\
           "metadata":{"templateId":"Large","custom_template":"true"},\
           "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
           "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
           "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(zsbuname,domain_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    project_id = j['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created IBM Cloud control project with ID: %s\n\n"%(project_id)

#add the admin
print "Adding the admin account to the IBM Cloud control project."
try:
    send_url = auth_url + '/projects/%s/users/%s/roles/%s'%(project_id,user_id,admin_id)
    r = requests.put(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
except Exception as e:
    print e
    sys.exit(1)
print "Admin user added.\n\n"

#add the basic security group
print "Creating a basic Security group for %s BU."%(zsbuname)
secgroup_id = None
try:
    send_url = baseurl + '/neutron/v2.0/security-groups'
    data = '{"security_group":{"name":"Basic","description":"security group Basic","tenant_id":"%s"}}'%(project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    secgroup_id = j['security_group']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the basic security group with ID: %s.\n\n"%(j['security_group']['id'])

#add the ports to the security group
ports = [{'icmp':'null'},{'tcp':'22'},{'tcp':'80'},{'tcp':'443'},{'tcp':'8443'},{'tcp':'8080'}]
for port in ports:
    try:
        send_url = baseurl + '/neutron/v2.0/security-group-rules'
        data = '{"security_group_rule":{"direction":"ingress","port_range_min":%s,"ethertype":"IPv4","port_range_max":%s,"protocol":"%s","security_group_id":"%s","tenant_id":"%s"}}'%(port.values()[0],port.values()[0],port.keys()[0],secgroup_id,project_id)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
        j = json.loads(r.text.encode('latin-1'))
    except Exception as e:
        print e
        sys.exit(1)
    print "Created the basic security group rule, ID: %s.\n\n"%(j['security_group_rule']['id'])


print "Creating a project scoped token for %s."%(username)
project_token = None
try:
    send_url = auth_url+"/auth/tokens"
    data = '{"auth":{"scope":{"project":{"id":"%s"}},"identity":{"methods":["token"],"token":{"id":"%s"}}}}'%(project_id,token)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    project_token = r.headers.get('X-Subject-Token')
except Exception as e:
    print e
    sys.exit(1)
print "Created project token key: %s.\n\n"%(project_token)


#Build the defult sec key
print "Creating default security keys, ibm_keypair, for IBM Cloud control project in the %s BU."%(zsbuname)
devops_key = "%s_keypair"%(zsbuname)
try:
    send_url = baseurl+"/nova/v2/%s/os-keypairs"%(project_id)
    data = '{"keypair":{"name":"%s_keypair"}}'%(zsbuname)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    keyinfo = json.loads(r.text.encode('latin-1'))
except Exception as e:
    print e
    sys.exit(1)
print "Created the security key ibm_keypair.\n\n"

time.sleep(2)
keypair = keyinfo['keypair']

#updateing the control project
print "Updateing the IBM Cloud BU %s control project."%(zsbuname)
try:
   send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s'%(region_id,project_id)
   data = '{"description":"IBM Cloud Control Project for %s BU.","domain_id":"%s","name":"DvOps Control","finite_duration":false,\
          "metadata":{"templateId":"Large","custom_template":"true","userName":"%s","user_id":"%s","fingerprint":"%s","keypairName":"%s","private_key":%s,"public_key":"%s"},\
          "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
          "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
          "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(zsbuname,domain_id,auth_username,admin_user_id,keypair['fingerprint'],keypair['name'],json.dumps(keypair['private_key']),keypair['public_key'])
   r = requests.patch(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
   j = json.loads(r.text)
   project_id = j['id']
except Exception as e:
    print e
    sys.exit(1)
print "Updated IBM Cloud control project with ID: %s\n\n"%(project_id)

print "Creating the IBM Cloud network in IBM CLoud control project."
network_id = None
subnet_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks'%(region_id)
    data = '{"admin_state_up":true,"name":"IBMCloud-network","subnets":[{"name":"Subnet1","enable_dhcp":true,"gateway_ip":"10.10.10.1","ip_version":4,"cidr":"10.10.10.0/24","allocation_pools":[{"start":"10.10.10.2","end":"10.10.10.254"}],"dns_nameservers":["8.8.8.8"],"tenant_id":"%s"}],"tenant_id":"%s","visibility":"buShared","visibility_scope":[{"domain_id":"%s"}],"project_id":"%s"}'%(project_id,project_id,region_id,project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
    network_id = j['id']
    subnet_id = j['subnet_details'][0]['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the IBM CLoud default network, ID: %s.\n\n"%(network_id)

#list the available external networks
ext_net_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks/?visibility=public&domain_id=%s&project_id=%s'%(region_id,domain_id,project_id)
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    nets = json.loads(r.text)
    for net in nets:
        if(net['provider:physical_network'] == 'external' and net['router:external'] == True and net['shared'] == True):
            ext_net_id = net['id']
except Exception as e:
    print e
    sys.exit(1)
print "Found external network with id: %s."%(ext_net_id)

#add the basic security group
print "Creating a router for IBM Cloud network."
router_id = None
try:
    send_url = baseurl + '/neutron/v2.0/routers'
    data = '{"router":{"name":"IBMCloudNet-Router","external_gateway_info":{"network_id":"%s"},"tenant_id":"%s"}}'%(ext_net_id,project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
    router_id = j['router']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the the default router.\n\n"

#add the router interface to the network subnet
print "Adding interface to router interface"
try:
    send_url = baseurl + '/neutron/v2.0/routers/%s/add_router_interface'%(router_id)
    data = '{"subnet_id":"%s"}'%(subnet_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Added network interface to the router, interface ID: %s\n\n"%(j['id'])

#add router gateway interface
print "Adding gateway interface to router."
try:
    send_url = baseurl + '/neutron/v2.0/routers/%s'%(router_id)
    data = '{"router":{"name":"IBMCloudNet-Router","external_gateway_info":{"network_id":"%s"},"admin_state_up":true}}'%(ext_net_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Added the gateway interface to the router, ID: %s, External IP: %s.\n\n"%(j['router']['id'],j['router']['external_gateway_info']['external_fixed_ips'][0]['ip_address'])


print "Updateing the network."
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks/%s'%(region_id,network_id)
    data = '{"name":"DevOps-network","router:external":false,"admin_state_up":true,"subnets":[{"id":"%s"}],"visibility":"buShared","visibility_scope":[{"domain_id":"%s"}]}'%(subnet_id,domain_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Updated the IBM Cloud default network, ID: %s.\n\n"%(network_id)

vms = [
   {'vm':'cloud_bootnode','code':None},
   {'vm':'worker','code':None},
   {'vm':'master','code':None},
   {'vm':'proxy','code':None},
   {'vm':'mgmt','code':None},
   {'vm':'va','code':None},
   {'vm':'etcd','code':None}
   ]

print "Creating IBM Cloud control instances in IBM Cloud control project"

for vm in vms:
   print "Building %s instance."%(vm['vm'])
   try:
       send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s/vm'%(region_id,project_id)
       data = '{"name":"%s","resources":{"server":{"type":"OS::Nova::Server","os_req":{"server":{"name":"%s","flavorRef":"4","block_device_mapping_v2":[{"device_type":"disk","disk_bus":"virtio","device_name":"/dev/vda","source_type":"volume","destination_type":"volume","delete_on_termination":true,"boot_index":"0","uuid":"{{.bootVol}}"}],"networks":[{"uuid":"%s"}],"security_groups":[{"name":"Basic"}],"metadata":{"created_by":"%s","owner":"DevOps Control","zs_internal_vm_ha":"false","delete_volume_on_termination":"true","isReservedFloatingIP":"false"},"user_data":"%s","delete_on_termination":true,"key_name":"%s"},"os:scheduler_hints":{"volume_id":"{{.bootVol}}"}}},"bootVol":{"type":"OS::Cinder::Volume","os_req":{"volume":{"availability_zone":null,"description":null,"size":20,"name":"bootVolume-ansible","volume_type":"relhighcap_type","disk_bus":"virtio","device_type":"disk","source_type":"image","device_name":"/dev/vda","bootable":true,"tenant_id":"%s","imageRef":"%s","enabled":true}}},"fip":{"type":"OS::Neutron::FloatingIP","os_req":{"floatingip":{"floating_network_id":"%s","tenant_id":"%s","port_id":"{{.port_id_0}}"}}}}}'%(vm['vm'],vm['vm'],network_id,username,vm['code'],devops_key,project_id,image_id,ext_net_id,project_id)
       r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
       #j = json.loads(r.text)
   except Exception as e:
      print e
      sys.exit(1)
   print "Built %s with ID: %s\n\n"%(vm['vm'],r.text)