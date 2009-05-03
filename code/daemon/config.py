"""config.py Parse the daemon config file"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import os.path
import xml.etree.ElementTree as etree
import logging

from filter import *


# Define exceptions.
class ConfigError(Exception): pass
class SourceDoesNotExist(ConfigError): pass


class Config(object):
    def __init__(self, parent_logger):
        self.sources = {}
        self.servers = {}
        self.rules   = {}
        self.logger  = logging.getLogger(".".join([parent_logger, "Config"]))
        self.errors  = 0


    def load(self, filename):
        doc = etree.parse(filename)
        root = doc.getroot()
        self.logger.info("Parsing sources.")
        self.__parse_sources(root)
        self.logger.info("Parsing servers.")
        self.__parse_servers(root)
        self.logger.info("Parsing rules.")
        self.__parse_rules(root)
        return self.errors


    def __parse_sources(self, root):
        sources = root.find("sources")
        for source in sources:
            name      = source.get("name")
            directory = source.get("directory")
            if not os.path.exists(directory):
                self.logger.error("The %s directory ('%s') does not exist." % (name, directory))
                self.errors += 1
            self.sources[name] = directory


    def __parse_servers(self, root):
        servers = root.find("servers")
        for server in servers:
            settings = {}
            name           = server.get("name")
            transporter    = server.get("transporter")
            maxConnections = server.get("maxConnections")
            for setting in server.getchildren():
                settings[setting.tag] = setting.text
            self.servers[name] = {
                "maxConnections" : maxConnections,
                "transporter"    : transporter,
                "settings"       : settings,
            }


    def __parse_rules(self, root):
        rules = root.find("rules")
        for rule in rules:
            for_source = rule.get("for")
            label      = rule.get("label")

            # 1: filter (required)
            filter_node = rule.find("filter")
            conditions = self.__parse_filter(filter_node, label)

            # 2: processorChain (optional)
            processor_chain = None
            processor_chain_node = rule.find("processorChain")
            if not processor_chain_node is None:
                processor_chain = self.__parse_processor_chain(processor_chain_node, label)

            # 3: destination (optional)
            destination = None
            destination_node = rule.find("destination")
            if not destination_node is None:
                destination = self.__parse_destination(destination_node, label)

            if processor_chain_node is None and destination_node is None:
                self.logger.error("In rule '%s': either a processChain or a destination must be configured, but neither is." % (label))
                self.errors += 1

            if not self.rules.has_key(for_source):
                self.rules[for_source] = []
            self.rules[for_source].append({
                "label"           : label,
                "filterConditions": conditions,
                "processorChain"  : processor_chain,
                "destination"     : destination,
            })


    def __parse_filter(self, filter_node, rule_label):
        conditions = {}
        for condition_node in filter_node.getchildren():
            if condition_node.tag == "size":
                conditions[condition_node.tag] = {
                    "conditionType" : condition_node.get("conditionType"),
                    "treshold"      : condition_node.text,
                }
            else:
                conditions[condition_node.tag] = condition_node.text

        # Validate the conditions by trying to create a Filter object with it.
        try:
            f = Filter(conditions)
        except FilterError, e:
            message = e.message
            if message == "":
                message = "none"
            self.logger.error("In rule '%s': invalid filter condition: %s (details: \"%s\")." % (rule_label, e.__class__.__name__, message))
            self.errors += 1

        return conditions


    def __parse_processor_chain(self, processor_chain_node, rule_label):
        processor_chain = []
        for processor_node in processor_chain_node.getchildren():
            processor_chain.append(processor_node.get("name"))
        return processor_chain


    def __parse_destination(self, destination_node, rule_label):
        destination = {}
        destination["settings"] = {}
        destination["server"] = destination_node.get("server")
        for setting_node in destination_node.getchildren():
            destination["settings"][setting_node.tag] = setting_node.text

        # Validate "server" attribute.
        if destination["server"] is None:
            self.logger.error("In rule '%s': invalid destination: 'server' attribute is missing." % (rule_label))
            self.errors += 1
        elif destination["server"] not in self.servers.keys():
            self.logger.error("In rule '%s': invalid destination: 'server' attribute references a non-existing source." % (rule_label))
            self.errors += 1

        return destination


if __name__ == '__main__':
    import logging.handlers

    # Set up logging.
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("config.log")
    logger.addHandler(handler)

    # Use the Config class.
    config = Config("test")
    config.load("config.sample.xml")
    print "sources", config.sources
    print "servers", config.servers
    print "rules",   config.rules
