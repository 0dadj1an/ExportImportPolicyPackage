import os
import sys
import tarfile
import time

from export_access_rulebase import export_access_rulebase
from export_objects import merge_data
from exporting.export_threat_rulebase import export_threat_rulebase
from lists_and_dictionaries import singular_to_plural_dictionary
from utils import debug_log, export_to_tar, create_tar_file, generate_export_error_report


def export_package(client, args):
    timestamp = time.strftime("%Y_%m_%d_%H_%M")
    debug_log("Checking existence of package [" + args.name + "]")
    show_package = client.api_call("show-package", {"name": args.name, "details-level": "full"})
    if not show_package.success:
        debug_log("No package named '" + args.name + "' found. Cannot export.", True, True)
        sys.exit(1)

    tar_file_name = args.output_file if args.output_file else "exported__package__" + args.name + "__" + timestamp
    tar_file = tarfile.open(tar_file_name + ".tar.gz", "w:gz")

    access = args.access
    threat = args.threat
    if args.all:
        access = True
        threat = True

    data_dict = {}
    unexportable_objects = {}

    if access:
        if show_package.data["access"]:
            debug_log("Exporting Access Control layers", True)
            for access_layer in show_package.data["access-layers"]:
                access_data_dict, access_unexportable_objects \
                    = export_access_rulebase(access_layer["name"], client, timestamp, tar_file)
                if not access_data_dict:
                    continue
                layer_tar_name = \
                    create_tar_file(access_layer, access_data_dict,
                                    timestamp, ["access-rule", "access-section"], client.api_version)
                merge_data(data_dict, access_data_dict)
                merge_data(unexportable_objects, access_unexportable_objects)
                tar_file.add(layer_tar_name)
                os.remove(layer_tar_name)

    if threat:
        if show_package.data["threat-prevention"]:
            debug_log("Exporting Threat-Prevention layers", True)
            for threat_layer in show_package.data["threat-layers"]:
                threat_data_dict, threat_unexportable_objects \
                    = export_threat_rulebase(threat_layer["name"], client)
                if not threat_data_dict:
                    continue
                layer_tar_name = \
                    create_tar_file(threat_layer, threat_data_dict,
                                    timestamp, ["threat-rule", "exception-group", "threat-exception"],
                                    client.api_version)
                merge_data(data_dict, threat_data_dict)
                merge_data(unexportable_objects, threat_unexportable_objects)
                tar_file.add(layer_tar_name)
                os.remove(layer_tar_name)

    for obj_type in data_dict:
        if obj_type not in singular_to_plural_dictionary[client.api_version]:
            singular_to_plural_dictionary[client.api_version][obj_type] = "generic-object"

    debug_log("Exporting general objects to TAR...")
    export_to_tar(data_dict, timestamp, tar_file, singular_to_plural_dictionary[client.api_version].keys(),
                  client.api_version,
                  ignore_list=["rule", "section", "threat-exception", "exception-group"])

    generate_export_error_report()

    tar_file.close()
