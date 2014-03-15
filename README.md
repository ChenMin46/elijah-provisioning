Elijah: Cloudlet Infrastructure for Mobile Computing
========================================================
A cloudlet is a new architectural element that arises from the convergence of
mobile computing and cloud computing. It represents the middle tier of a
3-tier hierarchy:  mobile device - cloudlet - cloud.   A cloudlet can be
viewed as a "data center in a box" whose  goal is to "bring the cloud closer".

Copyright (C) 2011-2012 Carnegie Mellon University
This is a developing project and some features might not be stable yet.
Please visit our website at [Elijah page](http://elijah.cs.cmu.edu/).



License
----------

All source code, documentation, and related artifacts associated with the
cloudlet open source project are licensed under the [Apache License, Version
2.0](http://www.apache.org/licenses/LICENSE-2.0.html).



Before you start
-----------------

This code is about **Virtual Machine Synthesis** that aimed to provide 
**Rapid provisioning of a custom virtual machine**. This does not include any
codes for mobile applications, rather it provides functions to create
**VM overlay** and perform **VM Synthesis** that will rapidly reconstruct 
your custom VM at an arbitrary computer.

Please read [Just-in-Time Provisioning for Cyber Foraging](http://www.cs.cmu.edu/~satya/docdir/ha-mobisys-vmsynthesis-2013.pdf)
to understand what we do here and find the detail techniques.


The key to rapid provisioning is the recognition that a large part of
a VM image is devoted to the guest OS, software libraries, and
supporting software packages. The customizations of a base system
needed for a particular application are usually relatively small.
Therefore, if the ``base VM`` already exists on the cloudlet, only
its difference relative to the desired custom VM, called a ``VM overlay``,
needs to be transferred. Our approach of using VM overlays
to provision cloudlets is called ``VM synthesis``.  A good analogy is
a QCOW2 file with a backing file. You can consider ``VM overlay`` as
a QCOW2 file and ``Base VM`` as a backing file. The main difference 
is that ``VM synthesis`` includes both disk and memory state and 
it is much more efficient in generating diff and reconstructing
suspended state.



Installing
----------

You will need:

* qemu-kvm
* libvirt-bin
* gvncviewer
* python-libvirt
* python-xdelta3
* python-dev (for message pack)
* liblzma-dev (for pyliblzma)
* Java JRE (for UPnP server)
* apparmor-utils (for disable apparmor for libvirt)
* libc6-i386 (for extracting free memory of 32 bit vm)
* libxml2-dev libxslt1-dev (for overlay packaging)
* python library
    - bson
	- pyliblzma
	- psutil
	- SQLAlchemy
	- fabric
	- dateutil


To install, you either 

* run a installation script::

		> $ sudo apt-get install fabric openssh-server  
		> $ fab localhost install

* install manually:
	- install required package  

			> $ sudo apt-get install qemu-kvm libvirt-bin gvncviewer python-libvirt python-xdelta3 python-dev openjdk-6-jre liblzma-dev apparmor-utils libc6-i386 python-pip libxml2-dev libxslt1-dev
			> $ sudo pip install bson pyliblzma psutil sqlalchemy python-dateutil requests lxml

	- Disable security module. This is for allowing custom KVM. Example at Ubuntu 12  

			> $ sudo aa-complain /usr/sbin/libvirtd  

	- Add current user to kvm, libvirtd group.  

			> $ sudo adduser [your_account_name] kvm  
			> $ sudo adduser [your_account_name] libvirtd  

	- Change permission of the fuse access (The qemu-kvm library changes fuse access permission while it's being installed, and the permission is
		recovered if you reboot the host.  We believe this is a bug in qemu-kvm
		installation script, so you can either reboot the machine to have valid
		permission of just revert the permission manually as bellow).

			> $ sudo chmod 644 /etc/fuse.conf  
			> $ sod sed -i 's/#user_allow_other/user_allow_other/g' /etc/fuse.conf  
	
  - Finally, install cloudlet package using python setup tool

			> $ sudo python setup.py install



Tested platforms
---------------------

We have tested at __Ubuntu 12.04 LTS 64-bit__ and it's derivatives such as Kubuntu.

This version of Cloudlet has several dependencies on other projects for further
optimization, and currently we include this dependency as a binary.  Therefore,
we recommend you to use __Ubuntu 12.04 LTS 64-bit__. Later after solving all
license issues, we'll provide relevant binaries.



How to use
--------------			

1. Creating ``base VM``.  

	You will first create or import ``base VM``. Here we provide methods for both
	importing ``base VM`` and creating your own ``base VM``.

	1) We provide __sample base VM__ of Ubuntu 12.04 32bit server for easy
	bootstrapping. You first need to download preconfigured ``base VM`` at:

	[Base VM for Ubuntu-12.04.01-i386-Server](https://storage.cmusatyalab.org/cloudlet-basevm-ubuntu-12.04.01-i386/ubuntu-12.04.01-i386-server.tar.gz)
	(Account: cloudlet, password: cloudlet)

	Untar the downloaded file into a specific directory (e.g. ~/base_VM/) and
	you can import it to the cloudlet DB by

		> $ cloudlet add-base [path/to/base_disk] [hash value]
	
	For example,

		> $ cd ~/base_VM/
		> $ tar xvf ubuntu-12.04.01-i386-server.tar.gz
		> $ cloudlet add-base ./ubuntu-12.04.01-i386-server/precise.raw 32854753f684c10e8ab8553315c7bf6ada2ab93a27c36f9bbb164514b96d516a
	
	You can find the hash value for the base VM from base VM hash file you just
	downloaded(e.g. precise.base-hash). You can check import result by

		> $ cloudlet list-base
	
	Later, we will provide more golden images for ``base VM`` such as vanilla
	Ubuntu 12.04 LTS 64bit and Fedora 19. It would be similar with [Ubuntu
	Cloud Image](http://cloud-images.ubuntu.com/).  We expect that typical
	users import these ``base VMs`` rather than generating his own.
	

	2) You can also create your own __base VM__ from a regular VM disk image.
	Here the _regular VM disk image_ means a raw format virtual disk image
	you normaly use for KVM/QEMU or Xen. 

        > $ cloudlet base /path/to/base_disk.img
        > % Use raw file format virtual disk
        
	This will launch GUI (VNC) connecting to your guest OS and the code will
	start creating ``base VM`` when you close VNC window. So, please close the
	GUI window when you think it's right point to snapshot the VM as a base VM
	(typically you close it after booting up).  Then, it will generate snapshot
	of the current states for both memory and disk and save that information
	to DB. You can check list of ``base VM`` by

    	> $ cloudlet list-base
	

2. Creating ``VM overlay`` using ``base VM``.  
    Now you can create your customized VM based on top of ``base VM``  
  
        > $ cloudlet overlay /path/to/base_disk.img
        > % Path to base_disk is the path for virtual disk you used earlier
        > % You can check the path by "cloudlet list-base"

	This will launch VNC again with resumed ``base VM``. Now you can start making
	any customizations on top of this ``base VM``. For example, if you're a
	developer of ``face recognition`` backend server, we will install required
	libraries, binaries and finally start your face recognition server. 
	After closing the GUI windows, cloudlet will capture only the change portion
	between your customization and ``base VM`` to generate ``VM overlay`` that
	is a minimal binary for reconstructing your customized VM.

	``VM overlay`` is composed of 2 files; 1) ``overlay-meta file`` ends with
	.overlay-meta, 2) compressed ``overlay blob files`` ends with .xz


	Note: if your application need specific port and you want to make a port
	forwarding host to VM, you can use -redir parameter as below. 

        > $ cloudlet overlay /path/to/base_disk.img -- -redir tcp:2222::22 -redir tcp:8080::80

	This will forward client connection at host port 2222 to VM's 22 and 8080
	to 80, respectively.


	### Note

	If you have experience kernel panic error like
	[this](https://github.com/cmusatyalab/elijah-cloudlet/issues/1), You should
	follow workaround of this link. It happens at a machine that does not have
	enough memory with EPT support, and you can avoid this problem by disabling
	EPT support. We're current suspicious about kernel bug, and we'll report
	this soon.  
    

3. Synthesizing custom VM using ``VM overlay``  

	Here, we'll show 3 different ways to perform VM synthesis using ``overlay
	vm`` that you just generated; 1) verifying integrity of VM overlay using command line
	interface, 2) synthesize over network using desktop client, and 3)
	synthesize over network using an Android client.  

    1) Command line interface: You can synthesize your ``VM overlay`` using 

        > $ cloudlet synthesis /path/to/base_disk.img /path/to/overlay-meta
    
    2) Network client (python version)  

	We have a synthesis server that received ``VM synthesis`` request from
	mobile client and you can start the server as below.
  
        > $ synthesis_server
    
	You can test this server using the client. You also need to copy the
	overlay that you like to reconstruct to the other machine when you execute
	this client.
    
        > $ synthesis_client -s [cloudlet ip address] -o [/path/to/overlay-meta]

    3) Network client (Android version)

	We have source codes for a Android client at ./android/android and you can
	import it to ``Eclipse`` as an Android project. This client program will
	automatically find nearby Cloudlet using UPnP if both client and Cloudlet
	are located in same broadcasting domain (e.g. sharing WiFi access point)

	Once installing application at your mobile device, you should copy your
	VM overlay (both overlay-meta and xz file) to Android phone. You can copy
	it to /sdcard/Cloudlet/overlay/ directory creating your overlay directory
	name.  For example, you can copy your ``VM overlay for face recognition`` to
	/sdcard/Cloudlet/overlay/face/ directory. This directory name will be
	appeared to your Android application when you're asked to select ``overlay vm``.
	Right directory name is important since the directory name will be
	saved as appName in internal data structure and being used to launch
	associated mobile application after finishing ``VM synthesis``. Recall that
	this VM synthesis client is for reconstructing your custom VM at arbitrary 
	computer and you need to launch your mobile application after finishing VM
	thesis that will communicate with the server you just launched. To launch
	mobile application after VM synthesis, we use Android Activity launch and
	the directory name is used as an index to point out associated mobile
	application. See more details at handleSucessSynthesis() method at 
	CloudletConnector.java file.



Compiling external library that Cloudlet uses
----------------------------------------------

You will need:

* qemu-kvm 1.1.1 (for Free memory and TRIM support)
* libc6-dev-i386 (for Free memory support)


Related research works
--------------------------

* [The Case for VM-based Cloudlets in Mobile Computing](https://github.com/cmusatyalab/elijah-cloudlet/blob/master/doc/papers/satya-ieeepvc-cloudlets-2009.pdf?raw=true)
* [The Impact of Mobile Multimedia Applications on Data Center Consolidation](https://github.com/cmusatyalab/elijah-cloudlet/blob/master/doc/papers/kiryong-ic2e-latency.pdf?raw=true)
* [Just-in-Time Provisioning for Cyber Foraging](https://github.com/cmusatyalab/elijah-cloudlet/blob/master/doc/papers/kiryong-mobisys-vmsynthesis.pdf?raw=true)
* [Scalable Crowd-Sourcing of Video from Mobile Devices](http://reports-archive.adm.cs.cmu.edu/anon/2012/CMU-CS-12-147.pdf)

