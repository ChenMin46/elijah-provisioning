#!/usr/bin/env python 
#
# Elijah: Cloudlet Infrastructure for Mobile Computing
# Copyright (C) 2011-2012 Carnegie Mellon University
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as published
# by the Free Software Foundation.  A copy of the GNU General Public License
# should have been distributed along with this program in the file
# LICENSE.GPL.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

import lib_cloudlet as lib_cloudlet
import sys
import os
import time
from Configuration import Options
from optparse import OptionParser

def print_usage(commands):
    usage = "\n%prog command  [option] -- [qemu-options]\n"
    usage += "  EX) cloudlet.py base /path/to/disk.img\n\n"
    usage += "Command list:\n"
    MAX_SPACE = 20
    for (comm, desc) in commands.iteritems():
        space = ""
        if len(comm) < MAX_SPACE: 
            space = " " * (20-len(comm))
        usage += "  %s%s : %s\n" % (comm, space, desc)
    return usage


def get_database():
    from db.api import DBConnector
    dbconn = DBConnector()
    return dbconn


def process_command_line(argv, commands):
    VERSION = '%prog 0.7'
    DESCRIPTION = 'Cloudlet Overlay Generation & Synthesis'

    parser = OptionParser(usage=print_usage(commands), version=VERSION, description=DESCRIPTION)

    parser.add_option(
            '-t', '--no-trim', action='store_true', dest='disable_trim_support', default=False,
            help='This will disable TRIM Support, mainly for test purposes. \
                    Normal user does not need to care about this option')
    parser.add_option(
            '-m', '--extract-free-memory', action='store_true', dest='enable_free_support', default=False,
            help='This will ENABLE extracting Free memory, mainly for test purposes. \
                    We disable this feature in default because it requires agency within guest OS. \
                    Normal user does not need to care about this option')
    parser.add_option(
            '-d', '--disk', action='store_true', dest='disk_only', default=False,
            help='[overlay_creation] create only disk overlay only')
    parser.add_option(
            '-r', '--residue', action='store_true', dest='return_residue', default=False,
            help='[synthesis] return residue after using synthesized VM')
    settings, args = parser.parse_args(argv)

    if len(args) < 1:
        parser.error("Choose command :\n  %s" % " | ".join(commands))
        

    mode = str(args[0]).lower()
    if mode not in commands.keys():
        parser.error("Invalid Command, Choose among :\n  %s" % " | ".join(commands))
    
    valid_residue_condition = (mode == "synthesis") or (settings.return_residue != True) 
    if valid_residue_condition == False:
        parser.error("-r (return residue) should be used only at synthesis command")

    return mode, args[1:], settings


def main(argv):
    if not lib_cloudlet.validate_congifuration():
        sys.stderr.write("failed to validate configuration\n")
        sys.exit(1)

    CMD_BASE_CREATION       = "base"
    CMD_OVERLAY_CREATION    = "overlay"
    CMD_SYNTEHSIS           = "synthesis"
    CMD_LIST_BASE           = "list_base"
    CMD_DEL_BASE            = "del_base"
    CMD_ADD_BASE            = "add_base"
    CMD_LIST_SESSION        = "list_session"
    CMD_CLEAR_SESSION       = "clear_session"
    CMD_LIST_OVERLAY        = "list_overlay"

    commands = {
            CMD_BASE_CREATION: "create new base VM",
            CMD_OVERLAY_CREATION: "create new overlay VM on top of base VM",
            CMD_SYNTEHSIS: "test created overlay using command line",
            CMD_LIST_BASE: "show all base VM at this machine",
            CMD_ADD_BASE: "add existing base vm to DB",
            CMD_DEL_BASE: "delete base vm at database",
            }
    mode, left_args, settings = process_command_line(sys.argv[1:], commands)

    if mode == CMD_BASE_CREATION:
        # creat base VM
        if len(left_args) < 1:
            sys.stderr.write("Error, Need to path to VM disk\n")
            sys.exit(1)
        if len(left_args) > 1 :
            sys.stderr("Warning, qemu argument won't be applied to creating base vm")
        disk_image_path = left_args[0] 
        disk_path, mem_path = lib_cloudlet.create_baseVM(disk_image_path)
        print "Base VM is created from %s" % disk_image_path
        print "Disk: %s" % disk_path
        print "Mem: %s" % mem_path
    elif mode == CMD_OVERLAY_CREATION:
        # create overlay
        if len(left_args) < 1:
            sys.stderr.write("Error, Need to path to VM disk\n")
            sys.exit(1)
        disk_image_path = left_args[0] 
        qemu_args = left_args[1:]
        options = Options()
        options.TRIM_SUPPORT = not settings.disable_trim_support
        options.FREE_SUPPORT = settings.enable_free_support
        options.DISK_ONLY = settings.disk_only

        overlay = lib_cloudlet.VM_Overlay(disk_image_path, options, qemu_args)
        overlay.start()
        overlay.join()
        print "[INFO] overlay metafile (%ld) : %s" % \
                (os.path.getsize(overlay.overlay_metafile), overlay.overlay_metafile)
        for overlay_file in overlay.overla_files:
            print "[INFO] overlay (%ld) : %s" % \
                    (os.path.getsize(overlay_file), overlay_file)
    elif mode == CMD_SYNTEHSIS:
        if len(left_args) < 2:
            sys.stderr.write("Synthesis requires path to VM disk and overlay-meta\n \
                    Ex) ./cloudlet synthesis [VM disk] /path/to/precise.overlay-meta [options]\n")
            sys.exit(1)
        disk_image_path = left_args[0] 
        meta = left_args[1]
        qemu_args = left_args[2:]
        lib_cloudlet.synthesis(disk_image_path, meta, \
                               disk_only=settings.disk_only, \
                               return_residue=settings.return_residue, \
                               qemu_args=qemu_args)
    elif mode == CMD_LIST_BASE:
        from db.table_def import BaseVM
        dbconn = get_database()

        basevm_list = dbconn.list_item(BaseVM)
        sys.stdout.write("hash value" + "\t\t\t\t\t" + "path\n")
        sys.stdout.write("-"*90 + "\n")
        for item in basevm_list:
            sys.stdout.write(item.hash_value + "\t" + item.disk_path + "\n")
        sys.stdout.write("-"*90 + "\n")
    elif mode == CMD_ADD_BASE:
        from db.table_def import BaseVM
        dbconn = get_database()

        if len(left_args) < 2:
            sys.stderr.write("Add existing base vm requires: \n \
                    1) base path\n \
                    2) hash value of the base\n \
                    Ex) ./cloudlet add_base /path/to/base_disk.img 4304c473a9f98480c7d6387f01158881d3440bb81c8a9452b1abdef794e51111\n")
            sys.exit(1)
        basedisk_path = os.path.abspath(left_args[0])
        base_hashvalue = left_args[1]
        if not os.path.isfile(basedisk_path):
            sys.stderr.write("Not valid file: %s\n" % basedisk_path)
            sys.exit(1)

        new_basevm = BaseVM(basedisk_path, base_hashvalue)
        dbconn.add_item(new_basevm)
    elif mode == CMD_DEL_BASE:
        from db.table_def import BaseVM
        dbconn = get_database()

        if len(left_args) < 1:
            sys.stderr.write("delete base vm requires base path\n \
                    Ex) ./cloudlet del_base /path/to/base_disk.img \n")
            sys.exit(1)
        basedisk_path = os.path.abspath(left_args[0])
        basevm_list = dbconn.list_item(BaseVM)
        deleting_base = None
        for item in basevm_list:
            if basedisk_path == item.disk_path: 
                deleting_base = item
                break

        if deleting_base:
            dbconn.del_item(item)
        else: 
            sys.stderr.write("Cannot find matching base disk\n")
            sys.exit(1)
    elif mode == CMD_LIST_SESSION:
        from db.table_def import Session
        dbconn = get_database()

        session_list = dbconn.list_item(Session)
        sys.stdout.write("session_id\t\tassociated_time\t\t\tdisassociated_time\t\tstatus\n")
        sys.stdout.write("-"*95 + "\n")
        for item in session_list:
            sys.stdout.write(str(item) + "\n")
        sys.stdout.write("-"*95 + "\n")
    elif mode == CMD_CLEAR_SESSION:
        from db.table_def import Session
        dbconn = get_database()

        session_list = dbconn.list_item(Session)
        for item in session_list:
            dbconn.session.delete(item)
        dbconn.session.commit()
    elif mode == CMD_LIST_OVERLAY:
        from db.table_def import OverlayVM
        dbconn = get_database()

        overlay_list = dbconn.list_item(OverlayVM)
        sys.stdout.write("id\tsession_id\t\tbasevm_path\t\t\t\t\t\tstatus\n")
        sys.stdout.write("-"*95 + "\n")
        for item in overlay_list:
            sys.stdout.write(str(item) + "\n")
        sys.stdout.write("-"*95 + "\n")
    else:
        sys.stdout.write("Invalid command: %s\n" % mode)
        sys.exit(1)

    return 0

if __name__ == "__main__":
    status = main(sys.argv)
    sys.exit(status)
