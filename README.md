ovirt-guest-install.py
======================
virt-install like script for oVirt environment

### Preparation ###

1. install ovirt-engine-sdk-python
```
$ sudo yum install python3-ovirt-engine-sdk4
```
or
```
$ pip install ovirt-engine-sdk-python
```
2. (Optional) setup web server for delivering kickstart or preseed configuration file
3. (Optional) setup dhcp server for Debian/Ubuntu guest installation

### Install & Setup ###

1. Download script
```
$ git clone https://github.com/uskf/ovirt-guest-install.git
$ cd ovirt-guest-install
```
2. download engine certificate
```
$ curl -o ca.pem -k -S 'https://ENGINE_FQDN/ovirt-engine/services/pki-resource?resource=ca-certificate&format=X509-PEM-CA'
```
3. change variables in ovirt-guest-install.py
```
$ vi ovirt-guest-install.py
```

|Variable|Description|
|-|-|
|@ENGINE_FQDN@|oVirt Engine VM FQDN|
|@ENGINEPASS_BASE64@|base64 encoded 'admin@internal' user's password|
|@CA_PEM@|path to engine ca file|

```
$  sed -i \
      -e 's!@ENGINE_FQDN@!engine.example.com!' \
      -e 's!@ENGINEPASS_BASE64@!'`echo -n redhat123 | base64`'!' \
      -e 's!@CA_PEM@!ca.pem!' \
  ovirt-guest-install.py
```
3. Upload installer iso file to ISO Domain
4. Extract and upload installer's kernel and initrd to ISO Domain
 - CentOS/RHEL
```
/isolinux/initrd
/isolinux/vmlinuz
```
 - Debian
```
/install.amd/initrd.gz
/install.amd/vmlinuz
```
 - Ubuntu
```
/install/initrd.gz
/install/vmlinuz
```

### Usage ###
```
usage: ovirt-guest-install.py [-h] [--name NAME] [--memory MEMORY]
                              [--max-memory MAX_MEMORY]
                              [--guaranteed-memory GUARANTEED_MEMORY]
                              [--cpu CPU] [--vmnet NETWORKNAME]
                              [--vmdisk SD:SIZE:FORMAT] [--os OSNAME]
                              [--biostype BIOSTYPE]
                              [--type {server,desktop,high_performance}]
                              [--enable-memory-balloon]
                              [--disable-memory-balloon] [--enable-sound]
                              [--disable-sound] [--iso ISO]
                              [--template TEMPLATE] [--kernel KERNEL]
                              [--initrd INITRD] [--network NETWORK]
                              [--dns DNS] [--ks URI] [--ps URI] [--ai URI]

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           Virtual Machine Name.
  --memory MEMORY       Memory(MBytes) (Default:1024)
  --max-memory MAX_MEMORY
                        Max Memory(MBytes) (Default: double of memory)
  --guaranteed-memory GUARANTEED_MEMORY
                        Guaranteed Memory(MBytes) (Default: half of memory)
  --cpu CPU             Num(s) of CPU (Default:1)
  --vmnet NETWORKNAME   Virtual Machine Network(s). Ex: --vmnet ovirtmgmt
                        This option can be specified multiple times.
  --vmdisk SD:SIZE:FORMAT
                        Virtual Machine Disk(s).
                        SD=Storage Domain Name, SIZE=Disk Size(GB), FORMAT=RAW or COW.
                        Ex: --vmdisk DATA1:50:RAW
                        This option can be specified multiple times.(first disk marked as bootable)
  --os OSNAME           OS name being installed (Default:rhel8)
                        Shorthand:debian,rhel6,rhel7,rhel8,rhel9,ubuntu
  --biostype BIOSTYPE   Virtual Machine Chipset/Firmware type.
                        bios_i440fx: i440fx chipset with BIOS
                        bios_q35: q35 chipset with BIOS
                        uefi_q35: q35 chipset with UEFI
                        uefi_q35_secure: q35 chipset with UEFI with SecureBoot
                        default: inherit from cluster's default
  --type {server,desktop,high_performance}
                        Virtual Machine Type (Default:server)
  --enable-memory-balloon
                        force enable memory ballooning
  --disable-memory-balloon
                        force disable memory ballooning
  --enable-sound        force enable soundcard
  --disable-sound       force disable soundcard
  --iso ISO             Installer ISO filename. Ex: --iso CentOS.iso
  --template TEMPLATE   Virtual Machine Template (Default:Blank)
  --kernel KERNEL       Installer Kernel filename. Ex: --kernel vmlinuz
  --initrd INITRD       Installer initrd filename. Ex: --initrd initrd.img
  --network NETWORK     IP network duaring kickstart.
                        Ex: --network ip=192.168.1.10::192.168.1.254:24:localhost:ens3:none
  --dns DNS             DNS Server duaring kickstart. Ex: --dns 192.168.1.53
  --ks URI              RHEL/CentOS Kickstart file URI. Ex: --ks http://example.com/server.cfg
  --ps URI              Debian/Ubuntu preseed file URI. Ex: --ps http://example.com/server.seed
  --ai URI              Ubuntu autoinstall URI. Ex: --ai http://example.com/

```

### Usage Example ###
- CentOS8
```
$ ./ovirt-guest-install.py \
   --name centos8.local \
   --memory 2048 \
   --cpu 1 \
   --vmnet ovirtmgmt \
   --vmdisk data:30:RAW \
   --os rhel8 \
   --iso CentOS-8.1.1911-x86_64-dvd1.iso \
   --kernel vmlinuz-c81 \
   --initrd initrd-c81.img \
   --network ip=192.168.1.8::192.168.1.254:24:centos8.local:ens3:none \
   --dns 192.168.1.53 \
   --ks http://ks.example.com/centos8.local.cfg
```
- Ubuntu
```
$ ./ovirt-guest-install.py \
   --name ubuntu1804.local \
   --memory 2048 \
   --cpu 1 \
   --vmnet ovirtmgmt \
   --vmdisk data:30:COW \
   --os ubuntu \
   --iso ubuntu-18.04.3-server-amd64.iso \
   --kernel vmlinuz-u1804 \
   --initrd initrd-u1804.gz \
   --ps http://ps.example.com/ubuntu1804.local.seed
```
- Ubuntu with autoinstall
```
$ ./ovirt-guest-install.py \
   --name ubuntu2004.local \
   --memory 2048 \
   --cpu 1 \
   --vmnet ovirtmgmt \
   --vmdisk data:30:COW \
   --os ubuntu \
   --iso ubuntu-20.04.1-live-server-amd64.iso \
   --kernel vmlinuz-u2004 \
   --initrd initrd-u2004 \
   --ai http://ps.example.com/ubuntu2004/
```

