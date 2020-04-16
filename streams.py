"""
Interfaces to web radio stations and podcasts
"""

from bs4 import BeautifulSoup
import requests


def _latest_episode_from_xml(url):
    try:
        pod_xml = requests.get(url)
        doc = BeautifulSoup(pod_xml.content)
        episode = doc.find("item")
        link = episode.find("enclosure")["url"]
        return link
    except Exception as e:
        print(str(e))
        return None


def ndr_mikado_latest():
    """
    Latest episode of NDR Mikado (updated every Sun)
    """
    return _latest_episode_from_xml(
        "https://www.ndr.de/nachrichten/info/sendungen/mikado/mikado_am_morgen/podcast4223.xml"
    )


def br_klaro_latest():
    """
    Latest episode of BR Klaro Nachrichten fuer Kinder (usually updated every Fri)
    """
    return _latest_episode_from_xml(
        "https://feeds.br.de/klaro-nachrichten-fuer-kinder/feed.xml"
    )


def br_betthupferl():
    """
    Latest episode of BR Betthupferl (updated daily)
    """
    return _latest_episode_from_xml("https://feeds.br.de/betthupferl/feed.xml")


def br_geschichten_fuer_kinder():
    """
    Latest episode of BR Geschichten fuer Kinder (updated approx every 2nd day)
    """
    return _latest_episode_from_xml(
        "https://feeds.br.de/geschichten-fuer-kinder/feed.xml"
    )


def br_radio_mikro():
    """
    Latest episode of BR Radio Mikro - Wissen fuer Kinder (usually updated Sat or Sun)
    """
    return _latest_episode_from_xml("https://feeds.br.de/radiomikro/feed.xml")


def br_do_re_mikro():
    """
    Latest episode of BR Do Re Mikro - Klassik für Kinder (updated every Sat/Sun)
    """
    return _latest_episode_from_xml("https://feeds.br.de/do-re-mikro-die-musiksendung-fuer-kinder/feed.xml")


def dr_kinderhoerspiel():
    """
    Latest episode of Deutschlandradio Kultur Kinderhoerspiel (updated daily)
    """
    return _latest_episode_from_xml("http://www.kakadu.de/podcast-kinderhoerspiel.3420.de.podcast.xml")
