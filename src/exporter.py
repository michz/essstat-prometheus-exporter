#!/usr/bin/env -S python3 -u
# coding: utf-8

# Based on original work from Peter Smode at https://github.com/psmode/essstat
# and from Justin Cichra at https://github.com/jrcichra/essstat
__license__ = "GPL 3.0"

import os, pprint, re, requests, sys, signal
from bs4 import BeautifulSoup
from prometheus_client import start_http_server
from prometheus_client.core import CollectorRegistry, GaugeMetricFamily, REGISTRY

TPLuser = os.environ["TPLINK_USERNAME"]
TPLpswd = os.environ["TPLINK_PASSWORD"]
PORT = int(os.getenv("PORT", 8000))
BASE_URL = "http://" + os.environ["TPLINK_HOST"]
TPLdebug = (bool)("DEBUG" in os.environ)


class Collector:
    def collect(self):
        gauge_tx_good_pkt = GaugeMetricFamily(
            "tplink_tx_good_pkt", "tplink tx good packets", labels=["target", "port"]
        )
        gauge_tx_bad_pkt = GaugeMetricFamily(
            "tplink_tx_bad_pkt", "tplink tx bad packets", labels=["target", "port"]
        )
        gauge_rx_good_pkt = GaugeMetricFamily(
            "tplink_rx_good_pkt", "tplink rx good packets", labels=["target", "port"]
        )
        gauge_rx_bad_pkt = GaugeMetricFamily(
            "tplink_rx_bad_pkt", "tplink rx bad packets", labels=["target", "port"]
        )
        gauge_link_status = GaugeMetricFamily(
            "tplink_link_status", "tplink link status", labels=["target", "port"]
        )
        gauge_state = GaugeMetricFamily(
            "tplink_state", "tplink state", labels=["target", "port"]
        )

        if TPLdebug:
            print(f"Username: {TPLuser}")
            print(f"Base URL: {BASE_URL}")

        s = requests.Session()

        data = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
        headers = {"Referer": f"{BASE_URL}/Logout.htm"}
        try:
            r = s.post(f"{BASE_URL}/logon.cgi", data=data, headers=headers, timeout=5)
        except requests.exceptions.Timeout as errt:
            sys.exit("ERROR: Timeout Error at login")
        except requests.exceptions.RequestException as err:
            sys.exit("ERROR: General error at login: " + str(err))

        headers = {
            "Referer": f"{BASE_URL}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }
        r = s.get(f"{BASE_URL}/PortStatisticsRpm.htm", headers=headers, timeout=6)

        soup = BeautifulSoup(r.text, "html.parser")
        if TPLdebug:
            from bs4 import __version__ as bs4__version__

            print("BeautifulSoup4 version: " + bs4__version__)
            print(r)

        convoluted = (
            soup.script == soup.head.script
        )  # TL-SG1016DE and TL-SG108E models have a script before the HEAD block
        if TPLdebug:
            pprint.pprint(convoluted)

        if TPLdebug:
            if convoluted:
                # This is the 24 port TL-SG1024DE model with the stats in a different place (and convoluted coding)
                pprint.pprint(soup.head.find_all("script"))
                pprint.pprint(soup.body.script)
            else:
                # This should be a TL-SG1016DE or a TL-SG108E
                pprint.pprint(soup.script)

        if str(r) != "<Response [200]>":
            sys.exit("ERROR: Login failure - bad credential?")

        pattern = re.compile(r"var (max_port_num) = (.*?);$", re.MULTILINE)

        if TPLdebug:
            if convoluted:
                print(pattern.search(str(soup.head.find_all("script"))).group(0))
                print(pattern.search(str(soup.head.find_all("script"))).group(1))
                print(pattern.search(str(soup.head.find_all("script"))).group(2))
            else:
                print(pattern.search(str(soup.script)).group(0))
                print(pattern.search(str(soup.script)).group(1))
                print(pattern.search(str(soup.script)).group(2))

        if convoluted:
            max_port_num = int(
                pattern.search(str(soup.head.find_all("script"))).group(2)
            )
        else:
            max_port_num = int(pattern.search(str(soup.script)).group(2))

        if convoluted:
            i1 = (
                re.compile(r'tmp_info = "(.*?)";$', re.MULTILINE | re.DOTALL)
                .search(str(soup.body.script))
                .group(1)
            )
            i2 = (
                re.compile(r'tmp_info2 = "(.*?)";$', re.MULTILINE | re.DOTALL)
                .search(str(soup.body.script))
                .group(1)
            )
            # We simulate bug for bug the way the variables are loaded on the "normal" switch models. In those, each
            # data array has two extra 0 cells at the end. To remain compatible with the balance of the code here,
            # we need to add in these redundant entries so they can be removed later. (smh)
            script_vars = (
                "tmp_info:[" + i1.rstrip() + " " + i2.rstrip() + ",0,0]"
            ).replace(" ", ",")
        else:
            script_vars = (
                re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL)
                .search(str(soup.script))
                .group(1)
            )

        if TPLdebug:
            print(script_vars)

        entries = re.split(",?\n+", script_vars)

        if TPLdebug:
            pprint.pprint(entries)

        edict = {}
        drop2 = re.compile(r"\[(.*),0,0]")
        for entry in entries:
            e2 = re.split(":", entry)
            edict[str(e2[0])] = drop2.search(e2[1]).group(1)

        if TPLdebug:
            pprint.pprint(edict)

        if convoluted:
            e3 = {}
            e4 = {}
            e5 = {}
            ee = re.split(",", edict["tmp_info"])
            for x in range(0, max_port_num):
                e3[x] = ee[(x * 6)]
                e4[x] = ee[(x * 6) + 1]
                e5[(x * 4)] = ee[(x * 6) + 2]
                e5[(x * 4) + 1] = ee[(x * 6) + 3]
                e5[(x * 4) + 2] = ee[(x * 6) + 4]
                e5[(x * 4) + 3] = ee[(x * 6) + 5]
        else:
            e3 = re.split(",", edict["state"])
            e4 = re.split(",", edict["link_status"])
            e5 = re.split(",", edict["pkts"])

        pdict = {}
        jlist = []
        for x in range(1, max_port_num + 1):
            # print(x, ((x-1)*4), ((x-1)*4)+1, ((x-1)*4)+2, ((x-1)*4)+3 )
            pdict[x] = {}
            pdict[x]["state"] = e3[x - 1]
            pdict[x]["link_status"] = e4[x - 1]
            pdict[x]["TxGoodPkt"] = e5[((x - 1) * 4)]
            pdict[x]["TxBadPkt"] = e5[((x - 1) * 4) + 1]
            pdict[x]["RxGoodPkt"] = e5[((x - 1) * 4) + 2]
            pdict[x]["RxBadPkt"] = e5[((x - 1) * 4) + 3]

            if x == max_port_num:
                myend = "\n"

            z = {**{"port": x}, **pdict[x]}
            jlist.append(z)
        for dict in jlist:
            for key in dict:
                dict[key] = int(dict[key])
        if TPLdebug:
            pprint.pprint(pdict)
        for row in jlist:
            # extract
            port = str(row["port"])
            state = row["state"]
            link_status = row["link_status"]
            tx_good_pkt = row["TxGoodPkt"]
            tx_bad_pkt = row["TxBadPkt"]
            rx_good_pkt = row["RxGoodPkt"]
            rx_bad_pkt = row["RxBadPkt"]

            # apply
            gauge_tx_good_pkt.add_metric([os.environ["TPLINK_HOST"], port], tx_good_pkt)
            gauge_tx_bad_pkt.add_metric([os.environ["TPLINK_HOST"], port], tx_bad_pkt)
            gauge_rx_good_pkt.add_metric([os.environ["TPLINK_HOST"], port], rx_good_pkt)
            gauge_rx_bad_pkt.add_metric([os.environ["TPLINK_HOST"], port], rx_bad_pkt)
            gauge_link_status.add_metric([os.environ["TPLINK_HOST"], port], link_status)
            gauge_state.add_metric([os.environ["TPLINK_HOST"], port], state)

            yield gauge_tx_good_pkt
            yield gauge_tx_bad_pkt
            yield gauge_rx_good_pkt
            yield gauge_rx_bad_pkt
            yield gauge_link_status
            yield gauge_state


if __name__ == "__main__":
    collector_registry = CollectorRegistry()
    collector_registry.register(Collector())
    start_http_server(PORT, registry=collector_registry)
    print(f"Serving metrics on port {PORT}...")
    signal.pause()  # sleep until a signal
