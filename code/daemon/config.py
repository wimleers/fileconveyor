"""config.py Parse the daemon config file"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import xml.etree.ElementTree as etree


class Config(object):
    def __init__(self):
        self.sources = {}
        self.servers = {}
        self.rules   = {}


    def load(self, filename):
        doc = etree.parse(filename)
        root = doc.getroot()
        self.__parse_sources(root)
        self.__parse_servers(root)
        self.__parse_rules(root)


    def __parse_sources(self, root):
        sources = root.find("sources")
        for source in sources:
            name      = source.get("name")
            directory = source.get("directory")
            self.sources[name] = directory


    def __parse_servers(self, root):
        servers = root.find("servers")
        for server in servers:
            settings = {}
            name        = server.get("name")
            transporter = server.get("transporter")
            for setting in server.getchildren():
                settings[setting.tag] = setting.text
            self.servers[name] = {
                "transporter" : transporter,
                "settings"    : settings,
            }


    def __parse_rules(self, root):
        rules = root.find("rules")
        for rule in rules:
            for_source = rule.get("for")
            label      = rule.get("label")

            # 1: filter (required)
            filterNode = rule.find("filter")
            conditions = self.__parse_filter(filterNode)

            # 2: processorChain (optional)
            processorChain = None
            processorChainNode = rule.find("processorChain")
            if not processorChainNode is None:
                processorChain = self.__parse_processorChain(processorChainNode)

            # 3: destination (optional)
            destination = None
            destinationNode = rule.find("destination")
            if not destinationNode is None:
                destination = self.__parse_destination(destinationNode)

            if not self.rules.has_key(for_source):
                self.rules[for_source] = []
            self.rules[for_source].append({
                "label"          : label,
                "filter"         : conditions,
                "processorChain" : processorChain,
                "destination"    : destination,
            })


    def __parse_filter(self, filterNode):
        conditions = {}
        for conditionNode in filterNode.getchildren():
            conditions[conditionNode.tag] = conditionNode.text
        return conditions


    def __parse_processorChain(self, processorChainNode):
        processorChain = []
        for processorNode in processorChainNode.getchildren():
            processorChain.append(processorNode.get("name"))
        return processorChain


    def __parse_destination(self, destinationNode):
        settings = {}
        for settingNode in destinationNode.getchildren():
            settings[settingNode.tag] = settingNode.text
        return settings


if __name__ == '__main__':
    config = Config()
    config.load("config.sample.xml")
    print "sources", config.sources
    print "servers", config.servers
    print "rules",   config.rules
