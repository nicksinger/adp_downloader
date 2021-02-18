#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib import parse
import configparser
import requests
import getpass
import base64
import pdb
import sys
import os
import re

def get_credentials():
  credentials = {}
  config = configparser.ConfigParser()
  config.read("config.ini")
  try:
    for key in ["company", "username", "passwordb64"]:
      credentials[key] = config["credentials"][key]
    encoded_pw = credentials.pop("passwordb64")
    credentials["password"] = base64.b64decode(encoded_pw.encode("utf-8"))
  except KeyError:
    print("config.ini or required entry not found. Asking for credentials now")
    credentials["credentials"]["company"] = input("Company Code: ")
    credentials["credentials"]["username"] = input("Username: ")
    credentials["credentials"]["password"] = getpass.getpass()

  return credentials

creds = get_credentials()
ADPWORLD_URL = parse.urlparse("https://www.adpworld.de")

print("Starting request session")
s = requests.session()

login_endpoint = parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, "/ipclogin/5/loginform.fcc", "", "", ""))
index_quoted = parse.quote(parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, "/index.html", "", "", "")), safe="")
target_param = "-SM-{}".format(index_quoted)
login_params = {"COMPANY": creds["company"], "USER": creds["username"], "PASSWORD": creds["password"], "TARGET": target_param}

print("Trying to login… ", end="")
req = s.post(login_endpoint, data=login_params)
if "SMSESSION" in s.cookies:
    print("success!")
else:
    print("FAIL. Please check your credentials.")
    sys.exit(1)

# Now parse the landing page to find the URL to the ePayslip application
soup = BeautifulSoup(req.text, 'html.parser')
payslip_param = list(filter(lambda x: "ePayslip" in x.text,soup.find_all("a")))
payslip_url = payslip_param[0].get("href")
url = "{}{}".format(req.url, payslip_url)

# Access the ePayslip app to read out a few parameters and the total amount of stored payslips
req = s.get(url)
soup = BeautifulSoup(req.text, 'html.parser')
paginator_text = soup.find("table").find("span", {"class": "ui-paginator-current"}).text
total_payslips = int(re.match(".*?([0-9]*)$", paginator_text).group(1))
#links = list(filter(lambda x: "DocDownload" in x.get("href"), soup.find_all("a")))
global epayslip_soup
epayslip_soup = soup

ADP_BASE_URL = parse.urlunparse(parse.urlparse(req.url)._replace(path=""))

def paginator_xhr(first=0, rows=20):
    global epayslip_soup
    metadata = list(epayslip_soup.find_all("input"))
    target_elements = list(epayslip_soup.find("form").find_all("div"))
    magic_application_id = list(filter(lambda x: "dataTable" in x.get("class"), target_elements))[0].get("id")
    javax_faces_encodedURL = list(filter(lambda x: x.get("name") == "javax.faces.encodedURL", metadata))[0].get("value")
    javax_faces_ViewState = list(filter(lambda x: x.get("name") == "javax.faces.ViewState", metadata))[0].get("value")
    SUBMIT = list(filter(lambda x: "SUBMIT" in x.get("name"), metadata))[0].get("name")
    data = {
        "javax.faces.partial.ajax": True,
        "javax.faces.source": magic_application_id,
        "javax.faces.partial.execute": magic_application_id,
        "javax.faces.partial.render": magic_application_id,
        magic_application_id: magic_application_id,
        magic_application_id + "_pagination": True,
        magic_application_id + "_first": first,
        magic_application_id + "_rows": rows,
        magic_application_id + "_encodeFeature": True,
        "javax.faces.encodedURL": javax_faces_encodedURL,
        SUBMIT: "1"
    }
    xhr_link = parse.urljoin(ADP_BASE_URL, javax_faces_encodedURL)
    req = s.post(xhr_link, data=data, headers={"Faces-Request": "partion/ajax"})
    root = ET.fromstring(req.text)
    changes = list(list(root)[0])
    soup = BeautifulSoup(changes[0].text, "html.parser")
    all_a = list(soup.find_all("a"))
    all_page_links = list(map(lambda x: parse.urljoin(ADP_BASE_URL, x.get("href")), all_a))
    new_ViewState = changes[1].text
    return all_page_links

def download_payslip(url):
    #print("Downloading {}".format(url))
    req = s.get(url)
    if (req.headers.get("Content-Type") != "application/pdf"):
        print("{} is not a PDF, skipping download. Please check manually".format(url))
        return
    cd_header = req.headers.get("Content-Disposition")
    pdf_filename = cd_header.split("\"")[1]
    assert not "/" in pdf_filename
    if os.path.isfile("downloads/" + pdf_filename):
        print("{} already exists, skipping download…".format(pdf_filename))
    else:
        print("Downloading {}… ".format(pdf_filename), end="")
        with open("downloads/" + pdf_filename, "wb") as fp:
            fp.write(req.content)

print("Collecting all payslip URLs via XHR. We expect {} in total.".format(total_payslips))
links = []
while len(links) < total_payslips:
    print("Fetching page 1. Payslip {}-{}… ".format(len(links), len(links)+99), end="")
    new_links = paginator_xhr(len(links), 99)
    links +=new_links
    print("Done.")
print("Successfuly fetched all payslip download URLs. Now downloading…")

for link in links:
    download_payslip(link)
print("All downloads succeeded. Done, exiting.")
