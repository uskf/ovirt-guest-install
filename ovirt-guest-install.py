#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import base64
import sys
import time

import ovirtsdk4 as sdk
import ovirtsdk4.types as types


def option_parser():

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--name",
        help="Virtual Machine Name.")
    parser.add_argument(
        "--memory",
        type=int,
        default=1024,
        help="Memory(MBytes) (Default:%(default)s)")
    parser.add_argument(
        "--max-memory",
        type=int,
        help="Max Memory(MBytes) (Default: double of memory)")
    parser.add_argument(
        "--guaranteed-memory",
        type=int,
        help="Guaranteed Memory(MBytes) (Default: half of memory)")
    parser.add_argument(
        "--cpu",
        type=int,
        default=1,
        help="Num(s) of CPU (Default:%(default)s)")
    parser.add_argument(
        "--vmnet",
        action="append",
        metavar="NETWORKNAME",
        help="Virtual Machine Network(s). Ex: --vmnet ovirtmgmt\nThis option can be specified multiple times.")
    parser.add_argument(
        "--vmdisk",
        action="append",
        metavar="SD:SIZE:FORMAT",
        help="Virtual Machine Disk(s).\nSD=Storage Domain Name, SIZE=Disk Size(GB), FORMAT=RAW or COW.\nEx: --vmdisk DATA1:50:RAW\nThis option can be specified multiple times.(first disk marked as bootable)")
    parser.add_argument(
        "--os",
        metavar="OSNAME",
        default="rhel8",
        help='OS name being installed (Default:%(default)s)\nShorthand:debian,rhel6,rhel7,rhel8,ubuntu')
    parser.add_argument(
        "--type",
        choices=['server','desktop','high_performance'],
        default="server",
        help='Virtual Machine Type (Default:%(default)s)')
    parser.add_argument(
        "--enable-memory-balloon",
        default=0,
        action="store_const",
        const=1,
        dest="balloon",
        help="force enable memory ballooning")
    parser.add_argument(
        "--disable-memory-balloon",
        default=0,
        action="store_const",
        const=-1,
        dest="balloon",
        help="force disable memory ballooning")
    parser.add_argument(
        "--enable-sound",
        default=0,
        action="store_const",
        const=1,
        dest="sound",
        help="force enable soundcard")
    parser.add_argument(
        "--disable-sound",
        default=0,
        action="store_const",
        const=-1,
        dest="sound",
        help="force disable soundcard")
    parser.add_argument(
        "--iso",
        help="Installer ISO filename. Ex: --iso CentOS.iso")
    parser.add_argument(
        "--template",
        default="Blank",
        help='Virtual Machine Template (Default:%(default)s)')
    parser.add_argument("--kernel",
        help="Installer Kernel filename. Ex: --kernel vmlinuz")
    parser.add_argument("--initrd",
        help="Installer initrd filename. Ex: --initrd initrd.img")
    parser.add_argument("--network",
        help="IP network duaring kickstart.\nEx: --network ip=192.168.1.10::192.168.1.254:24:localhost:ens3:none")
    parser.add_argument("--dns",
        help="DNS Server duaring kickstart. Ex: --dns 192.168.1.53")
    parser.add_argument("--ks",
        metavar="URI",
        help="RHEL/CentOS Kickstart file URI. Ex: --ks http://example.com/server.cfg")
    parser.add_argument("--ps",
        metavar="URI",
        help="Debian/Ubuntu preseed file URI. Ex: --ps http://example.com/server.seed")
    parser.add_argument("--ai",
        metavar="URI",
        help="Ubuntu autoinstall URI. Ex: --ai http://example.com/")

    return parser


def is_int(s):

    try:
        int(s)
    except:
        return False

    return True

def calc_netmask(p):
    m=0
    for i in range((31-p),31):
        m+=2<<i

    return("{0}.{1}.{2}.{3}".format(
                                 (m>>24 & 0b11111111),
                                 (m>>16 & 0b11111111),
                                 (m>>8  & 0b11111111),
                                 (m     & 0b11111111)))

def early_option_check(args):

    if args.name == None:
        print("virtual machine name is not specified,abort")
        return False

    if args.max_memory == None:
        args.max_memory = args.memory*2
    else:
        if not args.memory <= args.max_memory:
            print("Max memory must be equal or grater than memory,abort")
            return False

    if args.guaranteed_memory == None:
        args.guaranteed_memory = int(args.memory/2)
    else:
        if args.memory < args.guaranteed_memory:
            print("Guaranteed memory must be equal or smaller than memory,abort")
            return False

    if args.vmdisk == None:
        print("virtual disk is not specified,abort")
        return False

    for d in args.vmdisk:
        if len(d.split(':')) != 3:
            print("Invalid virtual disk parameter {0},abort".format(d))
            return False

        if not is_int(d.split(':')[1]):
            print("Specified disk size \"{0}\" is not integer,abort".format(d.split(':')[1]))
            return False

        if not d.split(':')[2] in ['RAW','COW']:
            print("Specified disk format \"{0}\" is not valid,abort".format(d.split(':')[2]))
            return False

    if args.ks != None or args.ps != None:
        if args.iso == None:
            print("ISO filename is not specified,abort")
            return False

        if args.kernel == None:
            print("Installer kernel filename is not specified,abort")
            return False

        if args.initrd == None:
            print("Installer initrd filename is not specified,abort")
            return False

        if args.vmnet == None:
            print("virtual machine network is not specified,abort")
            return False

    if args.os.startswith("rhel") and args.ks != None and args.network == None:
        print("Installer network is not specified,abort")
        return False

    if args.ks != None and args.ps != None:
        print("Both of kickstart and pressed are specified,abort")
        return False

    return True


def get_data_domains(conn):

    dom = []
    sds_service = conn.system_service().storage_domains_service()

    for sd in sds_service.list():
        if sd.type == types.StorageDomainType.DATA:
            dom.append(sd.name)
    return dom


def get_vm_network(conn):

    vmnet = []
    nws_service = conn.system_service().networks_service()
    nws = nws_service.list()
    for nw in nws:
        if types.NetworkUsage.VM in nw.usages:
            vmnet.append(nw.name)

    return vmnet


def get_iso_domain_files(conn):

    dcs_service = conn.system_service().data_centers_service()
    dc_service = dcs_service.data_center_service(dcs_service.list()[0].id)
    attached_sds_service = dc_service.storage_domains_service()
    iso_files = []

    for sd in attached_sds_service.list():
        if(sd.type == types.StorageDomainType.ISO):
            if(sd.status == types.StorageDomainStatus.ACTIVE):
                files_service = conn.system_service().storage_domains_service().storage_domain_service(sd.id).files_service()
                for f in files_service.list():
                    iso_files.append(f.name)
                return iso_files
            else:
                print("ISO Storage Domain \"{0}\" is not Active,abort".format(sd.name))
                return False

    print("There is no active ISO Domain in datacenter,abort")
    return False


def later_option_check(args,conn):

    # Check Disk Info
    data_domains = get_data_domains(conn)
    for d in args.vmdisk:
        if not d.split(':')[0] in data_domains:
            print("Specified storage domain \"{0}\" is not exist,abort"
                  .format(d.split(':')[0]))
            return False

    # Check VM network
    vm_networks = get_vm_network(conn)
    for vmn in args.vmnet:
        if not vmn in vm_networks:
            print("Specified virtual machine network \"{0}\" is not exist or vm network,abort"
                  .format(vmn))
            return False

    # Check ISO domain status and ISO/kernel/initrd files exist
    iso_domain_files = get_iso_domain_files(conn)
    if not iso_domain_files:
        return False

    if args.kernel != None and args.kernel not in iso_domain_files:
        print("Specified kernel \"{0}\" is not exist in iso domain,abort".format(args.kernel))
        return False

    if args.initrd != None and args.initrd not in iso_domain_files:
        print("Specified initrd \"{0}\" is not exist in iso domain,abort".format(args.initrd))
        return False

    if args.iso != None and args.iso not in iso_domain_files:
        print("Specified iso file \"{0}\" is not exist in iso domain,abort".format(args.iso))
        return False

    # Check VM Template
    templates_service = conn.system_service().templates_service()
    if not templates_service.list(search='name=%s' % args.template):
        print("Specified VM Template \"{0}\" is not exist,abort".format(args.template))
        return False

    return True


def main():

    parser=option_parser()
    args=parser.parse_args()

    if not early_option_check(args):
        sys.exit(-1)

    # Create the connection to the server:
    connection = sdk.Connection(
        url='https://@ENGINE_FQDN@/ovirt-engine/api',
        username='admin@internal',
        password=base64.b64decode('@ENGINEPASS_BASE64@'),
        ca_file='@CA_PEM@',
        debug=False,
    )

    vms_service = connection.system_service().vms_service()
    cluster = connection.system_service().clusters_service().list()[0]
    clustername = cluster.name
    dcs_service = connection.system_service().data_centers_service()
    dc = dcs_service.list(search='Clusters.name=%s' % cluster.name)[0]
    networks_service = dcs_service.service(dc.id).networks_service()
    profiles_service = connection.system_service().vnic_profiles_service()

    if not later_option_check(args,connection):
        connection.close()
        sys.exit(-1)

    shorthand={
        'rhel6': 'rhel_6x64',
        'rhel7': 'rhel_7x64',
        'rhel8': 'rhel_8x64',
        'ubuntu': 'ubuntu_14_04',
        'debian': 'debian_7',
    }

    vmtype={
        'server': types.VmType.SERVER,
        'desktop': types.VmType.DESKTOP,
        'high_performance': types.VmType.HIGH_PERFORMANCE
    }

    # Creating new virtual machine
    vm = types.Vm()
    vm.name = args.name
    vm.cluster = types.Cluster(name=clustername)
    vm.template = types.Template(name=args.template)
    if args.os in shorthand.keys():
        vm.os = types.OperatingSystem(type=shorthand[args.os])
    else:
        vm.os = types.OperatingSystem(type=args.os)
    vm.memory = args.memory*1024*1024
    if args.balloon == 0:
        vm.memory_policy = types.MemoryPolicy(
            max=args.max_memory*1024*1024,
            guaranteed=args.guaranteed_memory*1024*1024)
    else:
        vm.memory_policy = types.MemoryPolicy(
            max=args.max_memory*1024*1024,
            guaranteed=args.guaranteed_memory*1024*1024,
            ballooning = True if args.balloon == 1 else False)

    vm.cpu = types.Cpu()
    vm.cpu.architecture = types.Architecture.X86_64
    vm.cpu.topology = types.CpuTopology(
        cores=1, sockets=args.cpu, threads=1)
    if args.sound != 0:
        vm.soundcard_enabled = True if args.sound == 1 else False
    vm.type = vmtype[args.type]

    print("Creating New Virtual Machine:{0}".format(args.name))
    vm = vms_service.add(vm)

    while vms_service.list(search=args.name)[0].status != types.VmStatus.DOWN:
        time.sleep(1)

    # Attach network interface(s)
    nics_service = vms_service.vm_service(vm.id).nics_service()
    nicnum=0

    for netname in args.vmnet:
        network = next(
           (n for n in networks_service.list()
            if n.name == netname),
           None
        )
        profile_id = None
        for profile in profiles_service.list():
            if profile.name == netname:
                profile_id = profile.id
                break

        if profile_id != None:
            nicnum=nicnum+1
            print("Attaching nic{0}(Network:{1})".format(nicnum,netname))
            nics_service.add(
                types.Nic(
                    name="nic{0}".format(nicnum),
                    vnic_profile=types.VnicProfile(
                        id=profile_id,
                    ),
                ),
            )

    # Create and attach disk(s)
    disk_attachments_service = vms_service.vm_service(vm.id).disk_attachments_service()
    disks_service = connection.system_service().disks_service()
    disknum = 0
    for d in args.vmdisk:
        disknum+=1
        new_disk = types.DiskAttachment()
        new_disk.disk = types.Disk()
        new_disk.disk.name = "{0}_Disk{1}".format(args.name,disknum)
        new_disk.disk.provisioned_size = int(d.split(':')[1])*2**30
        new_disk.disk.storage_domains = [
            types.StorageDomain(name=d.split(':')[0])]
        if d.split(':')[2] == "RAW":
            new_disk.disk.format = types.DiskFormat.RAW
        else:
            new_disk.disk.format = types.DiskFormat.COW

        new_disk.interface = types.DiskInterface.VIRTIO_SCSI
        new_disk.active = True
        if disknum == 1:
            new_disk.bootable = True

        print("Attaching Disk{0}(Domain:{1}, Size:{2}GB, DiskFormat:{3})".format(
            disknum, d.split(':')[0], d.split(':')[1], d.split(':')[2]))
        disk_attachment = disk_attachments_service.add(new_disk)
        disk_service = disks_service.disk_service(disk_attachment.disk.id)
        # wait disk attach finish
        time.sleep(5)
        while disk_service.get().status != types.DiskStatus.OK:
            print("Waiting disk attach complete")
            time.sleep(5)

    if args.ks != None or args.ps != None or args.ai != None:
        # one-shot VM configuration for Kickstart/preseed
        one_vm = types.Vm()
        one_vm.os = types.OperatingSystem()
        one_vm.os.kernel = 'iso://'+args.kernel
        one_vm.os.initrd = 'iso://'+args.initrd
        one_vm.run_once = True
        one_vm.cdroms = list()
        one_vm.cdroms.append(types.Cdrom())
        one_vm.cdroms[0].file = types.File()
        one_vm.cdroms[0].file.id = args.iso
        if args.dns == None:
            args.dns = ""
        elif args.os == 'rhel6':
            args.dns = 'dns='+args.dns
        else:
            args.dns = 'nameserver='+args.dns

        if args.os == 'rhel6':
            ksdev = args.network.split(':')[5]
            ksip  = args.network.split(':')[0]
            ksnm  = calc_netmask(int(args.network.split(':')[3]))
            ksgw  = args.network.split(':')[2]
            args.network = "ksdevice={0} ip={1} netmask={2} gateway={3}".format(ksdev, ksip, ksnm, ksgw)

        if args.ks != None:
            if args.os == 'rhel6':
                one_vm.os.cmdline = args.network+" "+args.dns+" ks="+args.ks
            else:
                one_vm.os.cmdline = args.network+" "+args.dns+" inst.ks="+args.ks
        if args.ps != None:
            one_vm.os.cmdline = "auto=true url="+args.ps
        if args.ai != None:
            one_vm.os.cmdline = "autoinstall ds=nocloud-net;s="+args.ai

        vm_service = vms_service.vm_service(vm.id)
        print("Starting automatic OS installation on {0}".format(args.name))
        vm_service.start(vm=one_vm,volatile=True)

    # Close the connection to the server:
    connection.close()


if __name__ == '__main__':
    main()

