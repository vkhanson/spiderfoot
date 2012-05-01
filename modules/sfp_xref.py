#-------------------------------------------------------------------------------
# Name:         sfp_xref
# Purpose:      SpiderFoot plug-in for scanning links identified from the
#               spidering process, and for external links, fetching them to
#               see if those sites link back to the original site, indicating a
#               potential relationship between the external sites.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin

# SpiderFoot standard lib (must be initialized in __init__)
sf = None

class sfp_xref(SpiderFootPlugin):
    # Default options
    opts = {
        # These must always be set
        '_debug':       True,
        '_debugfilter': '',
        'forcebase':    True, # Check the base URL for a link back to the seed
                              # domain in order to be considered a valid xref
        'checkbase':    True, # Only check the base URL for a relationship if
                              # the link provided contains no xref
        'checksimilar': True  # Check similar domains for an xref
    }

    # Internal results tracking
    results = dict()
    fetched = list()

    # URL this instance is working on
    seedUrl = None
    baseDomain = None # calculated from the URL in __init__

    def __init__(self, url, userOpts=dict()):
        global sf
        self.seedUrl = url

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        # For error reporting, debug, etc.
        sf = SpiderFoot(self.opts)

        # Extract the 'meaningful' part of the FQDN from the URL
        self.baseDomain = sf.urlBaseDom(self.seedUrl)
        sf.debug('Base Domain: ' + self.baseDomain)

    # What events is this module interested in for input
    def watchedEvents(self):
        arr = list("URL")
        if self.opts['checksimilar']:
            arr.append("SIMILARDOMAIN")
        return arr

    # Handle events sent to this module
    # In this module's case, eventData will be the URL or a domain which
    # was found in some content somewhere.
    def handleEvent(self, srcModuleName, eventName, eventSource, eventData):
        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData in self.fetched:
            sf.debug("Ignoring " + eventData + " as already tested")
            return

        # The SIMILARDOMAIN event supplies domains, not URLs. Assume HTTP.
        if eventName == 'SIMILARDOMAIN':
            eventData = 'http://'+ eventData

        # We are only interested in external sites for the xref
        if sf.urlBaseDom(eventData) == self.baseDomain:
            sf.debug("Ignoring " + eventData + " as not external")
            return None

        # If forcebase is set, we don't bother checking the URL from the event,
        # just it's base URL.
        if self.opts['forcebase']:
            url = sf.urlBaseUrl(eventData)
        else:
            url = eventData

        sf.debug("Testing for affiliation: " + url)
        res = sf.fetchUrl(url)

        if res['content'] == None:
            sf.debug("Ignoring " + url + " as no data returned")
            return None

        # Search for mentions of our domain in the external site's data
        matches = re.findall("(" + self.baseDomain + ")", res['content'], re.IGNORECASE)

        if not self.opts['forcebase'] and len(matches) > 0 and self.opts['checkbase']:
            # Check the base url to see if there is an affiliation
            url = sf.urlBaseUrl(eventData)
            res = sf.fetchUrl(url)
            matches = re.findall("(" + self.baseDomain + ")", res['content'], re.IGNORECASE)

        if len(matches) > 0:
            if self.results.has_key(url):
                return None

            self.results[url] = True
            sf.debug("Found affiliate: " + url)
            self.notifyListeners("AFFILIATE", eventSource, url)

        return None

# End of sfp_xref class

if __name__ == '__main__':
    print "This module cannot be run stand-alone."
    exit(-1)
