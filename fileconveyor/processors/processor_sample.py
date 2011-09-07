import sys
import os
import os.path
import time
import logging.handlers
sys.path.append(os.path.abspath('..'))


from processor import *
import filename
import image_optimizer
import link_updater
import unique_filename
import yui_compressor


if __name__ == "__main__":
    # Set up a logger.
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("processor.log")
    logger.addHandler(handler)

    def callback(input_file, output_file):
        print """"CALLBACK FIRED:
                   input_file='%s'
                   output_file='%s'""" % (input_file, output_file)

    def error_callback(input_file):
       print """"ERROR_CALLBACK FIRED:
                  input_file='%s'""" % (input_file)

    # Use a ProcessorChainFactory.
    document_root = "/htdocs/example.com/subsite"
    base_path = "/subsite/"
    processors = [
        "image_optimizer.KeepFilename",
        "unique_filename.Mtime",
        "link_updater.CSSURLUpdater",
        "yui_compressor.YUICompressor"
    ]
    factory = ProcessorChainFactory("test")
    chain = factory.make_chain_for("test.jpg", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.png", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.css", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.js", processors, document_root, base_path, callback, error_callback)
    chain.run()
