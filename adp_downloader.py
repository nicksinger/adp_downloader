#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib import parse
import configparser
import requests
import getpass
import base64
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

# Handle redirection after login
soup = BeautifulSoup(req.text, 'html.parser')
redirect = soup.find("meta", attrs={"http-equiv": "refresh"})
meta_attrs = redirect["content"].split(";")
target_attr = list(filter(lambda x: "URL" in x, meta_attrs))[0]
target_path = target_attr.split("=")[1]
target_url = parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, target_path, "", "", ""))

# Request and parse the main dashboard to find the path to the ePayslip app
req = s.get(target_url)
soup = BeautifulSoup(req.text, 'html.parser')
payslip_param = list(filter(lambda x: "ePayslip" in x.text,soup.find_all("a")))
payslip_url = payslip_param[0].get("href")
url = parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, payslip_url, "", "", ""))

# Access the ePayslip app to read out a few parameters and the total amount of stored payslips
req = s.get(url)
soup = BeautifulSoup(req.text, 'html.parser')
paginator_text = soup.find("table").find("span", {"class": "ui-paginator-current"}).text
total_payslips = int(re.match(".*?([0-9]*)$", paginator_text).group(1))
global epayslip_soup
epayslip_soup = soup

def paginator_xhr(first=0, rows=20):
    global epayslip_soup

    form_inputs = list(epayslip_soup.find_all("input")) # All inputs inside the form. Some of them we need to submit

    # Main form containing all payslip links
    all_forms = list(epayslip_soup.find_all("form"))
    epaylistform = list(filter(lambda x: "ePayListForm" in x.get("id", ""), all_forms))[0]

    # All elements of the main form. One of them contains the datatable we're interested in
    target_elements = list(epaylistform.find_all("div"))
    magic_application_id = list(filter(lambda x: "ui-datatable" in x.get("class", ""), target_elements))[0].get("id")

    # These properties need to be submitted for the paginator request to succeed
    javax_faces_encodedURL = list(filter(lambda x: x.get("name") == "javax.faces.encodedURL", form_inputs))[0].get("value")
    javax_faces_ViewState = list(filter(lambda x: x.get("name") == "javax.faces.ViewState", form_inputs))[0].get("value")
    SUBMIT = list(filter(lambda x: "SUBMIT" in x.get("name"), form_inputs))[0].get("name")

    # Now lets request the data from the paginator endpoint
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
    xhr_link = parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, javax_faces_encodedURL, "", "", ""))
    req = s.post(xhr_link, data=data, headers={"Faces-Request": "partial/ajax"})

    # The beauty of java on web requires us now to parse XML which contains HTML
    root = ET.fromstring(req.text)
    changes = root.find("./changes/update[@id='{}']".format(magic_application_id)) # Node containing HTML
    soup = BeautifulSoup(changes.text, "html.parser")
    all_a = list(soup.find_all("a"))
    all_page_links = list(map(lambda x: parse.urlunparse((ADPWORLD_URL.scheme, ADPWORLD_URL.netloc, x.get("href"), "", "", "")) , all_a))

    new_ViewState = root.find("./changes/update[@id='javax.faces.ViewState']").text # Is maybe useful for the future
    return all_page_links

def download_payslip(url):
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
    print("Fetching payslip {}-{}… ".format(len(links), len(links)+99), end="")
    new_links = paginator_xhr(len(links), 99)
    links +=new_links
    print("Done.")
print("Successfuly fetched all payslip download URLs. Now downloading…")

for link in links:
    download_payslip(link)
print("All downloads succeeded. Done, exiting.")
