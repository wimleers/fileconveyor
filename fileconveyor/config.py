"""config.py Parse the daemon config file"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import os.path
import xml.etree.ElementTree as etree
from xml.parsers.expat import ExpatError
import re
import logging

from filter import *


# Define exceptions.
class ConfigError(Exception): pass
class SourceDoesNotExist(ConfigError): pass


class Config(object):
    def __init__(self, parent_logger):
        self.ignored_dirs = []
        self.sources      = {}
        self.servers      = {}
        self.rules        = {}
        self.logger       = logging.getLogger(".".join([parent_logger, "Config"]))
        self.errors       = 0

        self.source_name_regex = re.compile('^[a-zA-Z0-9-_]*$', re.UNICODE)


    @classmethod
    def __ensure_unicode(cls, string):
        # If the string is already in Unicode, there's nothing we need to do.
        if type(string) == type(u'.'):
            return string
        # Otherwise, decode it from UTF-8 (which is config.xml's encoding).
        elif type(string) == type('.'):
            return string.decode('utf-8')
        # Finally, we may not really be receiving a string.
        else:
            return string


    def load(self, filename):
        try:
            doc = etree.parse(filename)
            root = doc.getroot()
            self.logger.info("Parsing sources.")
            self.__parse_sources(root)
            self.logger.info("Parsing servers.")
            self.__parse_servers(root)
            self.logger.info("Parsing rules.")
            self.__parse_rules(root)
        except ExpatError, e:
            self.logger.error("The XML file is invalid; %s." % (e))
            self.errors += 1
        return self.errors


    def __parse_sources(self, root):
        sources = root.find("sources")

        # Globally ignored directories.
        self.ignored_dirs = Config.__ensure_unicode(sources.get("ignoredDirs", ""))

        # If set, validate the globally ignored directories by trying to
        # create a Filter object for it.
        if self.ignored_dirs != "":
            try:
                conditions = {"ignoredDirs" : self.ignored_dirs}
                f = Filter(conditions)
            except FilterError, e:
                message = e.message
                if message == "":
                    message = "none"
                self.logger.error("Invalid ignoredDirs attribute for the sources node: %s (details: \"%s\")." % (e.__class__.__name__, message))
                self.errors += 1

        for source in sources:
            name          = Config.__ensure_unicode(source.get("name"))
            scan_path     = Config.__ensure_unicode(source.get("scanPath"))
            document_root = Config.__ensure_unicode(source.get("documentRoot"))
            base_path     = Config.__ensure_unicode(source.get("basePath"))

            self.sources[name] = {
                "name"          : name,
                "scan_path"     : scan_path,
                "document_root" : document_root,
                "base_path"     : base_path,
            }

            # Validate.
            if not self.source_name_regex.match(name):
                self.logger.error("The name '%s' for a source is invalid. Only use alphanumeric characters, the dash and the underscore." % (name))
                self.errors += 1
            if scan_path is None:
                self.logger.error("The %s scan path is not configured." % (name))
                self.errors += 1                
            elif not os.path.exists(scan_path):
                self.logger.error("The %s scan path ('%s') does not exist." % (name, scan_path))
                self.errors += 1
            if not document_root is None and not os.path.exists(document_root):
                self.logger.error("The %s document root ('%s') does not exist." % (name, document_root))
                self.errors += 1
            if not base_path is None and (base_path[0] != "/" or base_path[-1] != "/"):
                self.logger.error("The %s base path ('%s') is invalid. It should have both leading and trailing slashes." % (name, base_path))
                self.errors += 1
            if not document_root is None and not base_path is None:
                site_path = os.path.join(document_root, base_path[1:])
                if not os.path.exists(site_path):
                    self.logger.warning("The %s site path (the base path within the document root, '%s') does not exist. It is assumed that this is a logical base path then, due to usage of symbolic links." % (name, site_path))


    def __parse_servers(self, root):
        servers_node = root.find("servers")
        for server_node in servers_node:
            settings = {}
            name           = Config.__ensure_unicode(server_node.get("name"))
            transporter    = Config.__ensure_unicode(server_node.get("transporter"))
            maxConnections = server_node.get("maxConnections", 0)
            for setting in server_node.getchildren():
                settings[setting.tag] = Config.__ensure_unicode(setting.text)
            self.servers[name] = {
                "maxConnections" : int(maxConnections),
                "transporter"    : transporter,
                "settings"       : settings,
            }


    def __parse_rules(self, root):
        rules_node = root.find("rules")
        for rule_node in rules_node:
            for_source = Config.__ensure_unicode(rule_node.get("for"))
            label      = Config.__ensure_unicode(rule_node.get("label"))

            # 1: filter (optional)
            conditions = None
            filter_node = rule_node.find("filter")
            if not filter_node is None:
                conditions = self.__parse_filter(filter_node, label)

            # 2: processorChain (optional)
            processor_chain = None
            processor_chain_node = rule_node.find("processorChain")
            if not processor_chain_node is None:
                processor_chain = self.__parse_processor_chain(processor_chain_node, label)

            # 3: destinations (required)
            destinations = {}
            destinations_node = rule_node.find("destinations")
            if destinations_node is None or len(destinations_node) == 0:
                self.logger.error("In rule '%s': at least one destination must be configured." % (label))
                self.errors += 1
            else:
                for destination_node in destinations_node:
                    destination = self.__parse_destination(destination_node, label)
                    destinations[destination["server"]] = {"path" : destination["path"]}

            if not self.rules.has_key(for_source):
                self.rules[for_source] = []
            self.rules[for_source].append({
                "label"           : Config.__ensure_unicode(label),
                "filterConditions": conditions,
                "processorChain"  : processor_chain,
                "destinations"    : destinations,
            })


    def __parse_filter(self, filter_node, rule_label):
        conditions = {}
        for condition_node in filter_node.getchildren():
            if condition_node.tag == "size":
                conditions[condition_node.tag] = {
                    "conditionType" : Config.__ensure_unicode(condition_node.get("conditionType")),
                    "treshold"      : Config.__ensure_unicode(condition_node.text),
                }
            else:
                conditions[condition_node.tag] = Config.__ensure_unicode(condition_node.text)

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
            processor_chain.append(Config.__ensure_unicode(processor_node.get("name")))
        return processor_chain


    def __parse_destination(self, destination_node, rule_label):
        destination = {}
        destination["server"] = Config.__ensure_unicode(destination_node.get("server"))
        destination["path"]   = Config.__ensure_unicode(destination_node.get("path", None))

        # Validate "server" attribute.
        if destination["server"] is None:
            self.logger.error("In rule '%s': invalid destination: 'server' attribute is missing." % (rule_label))
            self.errors += 1
        elif destination["server"] not in self.servers.keys():
            self.logger.error("In rule '%s': invalid destination: 'server' attribute references a non-existing server." % (rule_label))
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
    config.load("config.xml")
    print "ignoredDirs", config.ignored_dirs
    print "sources", config.sources
    print "servers", config.servers
    print "rules",   config.rules
