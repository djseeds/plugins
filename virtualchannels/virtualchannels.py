#!/usr/bin/env python3
from pyln.client import Plugin

plugin = Plugin()

@plugin.method("hello")
def hello(plugin, name="world"):
    """This is the documentation string for the hello-function.

    It gets reported as the description when registering the function
    as a method with `lightningd`.

    """
    greeting = plugin.get_option('greeting')
    s = '{} {}'.format(greeting, name)
    plugin.log(s)
    return s


@plugin.init()
def init(options, configuration, plugin):
    plugin.log("Plugin helloworld.py initialized")


@plugin.subscribe("connect")
def on_connect(plugin, id, address):
    plugin.log("Received connect event for peer {}".format(id))


plugin.add_option('greeting', 'Hello', 'The greeting I should use.')
plugin.run()