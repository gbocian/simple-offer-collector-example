#!/usr/bin/env python3
import requests
import sys
import json
from lxml import etree
from io import StringIO

APP_CONFIG = {
    "DOMAIN": "https://www.pracuj.pl",
    "START_URL": "/praca/it;kw/krakow;wp/ostatnich%203%20dni;p,3?rd=30",
    "UA": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.48 Safari/537.36",
    "CONTENT_STRING": r"window.__INITIAL_STATE__ = ",
    "SEPARATOR": "};",
    "END_MARK": "}",
    "TAG_STRING": "//script/text()",
    "JSON_CHAIN": "#",
    "OFFER_LOCATION": "offers"
}

PAGE_CONFIG = {
    "DISCOVERED": {
        "K": "offersTotalCount",
        "V": None
    },
    "ITEMS_PAGE": {
        "K": "offersCounts#offersPageCount",
        "V": None
    },
    "MAX_PAGE": {
        "K": "pagination#maxPages",
        "V": None
    },
    "NEXT_PAGE": {
        "K": "pagination#nextPageUrl",
        "V": None
    },
    "NEXT_PAGE_ACTIVE": {
        "K": "pagination#nextPageLinkVisible",
        "V": None
    }
}

OFFERS = {}


def offers_view():
    global OFFERS

    print("[+] Offers collected:")

    for i in OFFERS:
        print(f"   [i] Page: {i+1} | Size: {len(OFFERS[i])}")
        for offer in OFFERS[i]:
            print(f"      {offer}")


def offers_save(page_no, json_response):
    global OFFERS

    OFFERS[page_no] = json_response.get(app_config_get("OFFER_LOCATION"))


def app_config_get(key):
    global APP_CONFIG
    tmp_val = APP_CONFIG.get(key, None)
    if tmp_val is None:
        print(f"[!] Unable to get app config value for: {key}")
        sys.exit(1)
    return tmp_val


def page_config_get(key):
    global PAGE_CONFIG
    tmp_val = PAGE_CONFIG.get(key, {"V": None}).get("V")
    if tmp_val is None:
        print(f"[!] Unable to get page config value for: {key}")
        sys.exit(1)
    return tmp_val


def page_config_update(json_response):
    global PAGE_CONFIG

    for config in PAGE_CONFIG:
        tmp_config = PAGE_CONFIG.get(config)
        if app_config_get("JSON_CHAIN") in tmp_config.get("K"):
            tmp_nested = tmp_config.get("K").split(app_config_get("JSON_CHAIN"))
            if len(tmp_nested) == 2:
                PAGE_CONFIG[config]["V"] = json_response.get(tmp_nested[0], []).get(tmp_nested[1], None)
            else:
                print(f"[!] Unknown config - TODO: change logic | {tmp_config.get('K')}")
        else:
            PAGE_CONFIG[config]["V"] = json_response.get(tmp_config.get("K"), None)


def extract_content(all_html_tags):
    tmp_content = None

    for tag in all_html_tags:
        if app_config_get("CONTENT_STRING") in tag:
            for tmp_split in tag.split(app_config_get("SEPARATOR")):
                if app_config_get("CONTENT_STRING") in tmp_split:
                    try:
                        tmp_content = json.loads(
                            tmp_split.replace(app_config_get("CONTENT_STRING"), "") + app_config_get("END_MARK")
                        )
                    except json.decoder.JSONDecodeError as err:
                        print(f"[!] Error parsing JSON | msg: {err.msg}")

    if tmp_content is None:
        print("[!] Collected data error")
        sys.exit(1)

    page_config_update(tmp_content)

    return tmp_content


def requester(request_url):

    with requests.Session() as s:
        s.headers.update({"User-Agent": app_config_get("UA")})
        tmp_data = s.get(url=request_url)
        print(f"[+] Requesting data for {tmp_data.url} | Response code: {tmp_data.status_code}")

        tmp_html = etree.parse(StringIO(tmp_data.text), etree.HTMLParser())
        tmp_all_script_tag = tmp_html.xpath(app_config_get("TAG_STRING"))

        return extract_content(tmp_all_script_tag)


def collector():
    for i in range(1, int(page_config_get("MAX_PAGE")) + 1):
        if page_config_get("NEXT_PAGE_ACTIVE") is False:
            print("[i] Stop, nothing more to download")
            break

        tmp_req_url = app_config_get("DOMAIN") + page_config_get("NEXT_PAGE")

        collected_data = requester(tmp_req_url)
        offers_save(i, collected_data)


def discovery():
    print("[i] Collecting first page / data")
    collected_data = requester(app_config_get("DOMAIN") + app_config_get("START_URL"))
    offers_save(0, collected_data)
    print(f"[!] Offers discovered: {page_config_get('DISCOVERED')} on {page_config_get('MAX_PAGE')} pages")


def main():
    discovery()
    collector()
    offers_view()


if __name__ == "__main__":
    main()
    sys.exit(0)
