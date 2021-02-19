#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib import parse
import configparser
import datetime
import requests
import base64
import re

class ADPDocument():
  def __init__(self, adpworld, document_element):
    columns = document_element.find_all("td")
    self.company_id = columns[1].text
    self.employee_nr = columns[2].text
    self.type = columns[3].text
    self.long_name = columns[4].text
    self.date = datetime.datetime.strptime(columns[5].text, '%d.%m.%Y')
    self.pages = columns[6].text
    self.size = columns[7].text
    url_path = columns[8].find("a").get("href")
    self.url = parse.urlunparse((adpworld.ADPWORLD_URL.scheme, adpworld.ADPWORLD_URL.netloc, url_path, "", "", ""))

  @property
  def estimated_filename(self):
    file_date = self.date.strftime('%Y%m%d')
    return "{}_{}_{}_{}.pdf".format(file_date, self.company_id, self.employee_nr, self.type)


class ADPWorld():
  def __init__(self):
    self.ADPWORLD_URL = parse.urlparse("https://www.adpworld.de") # All URLs are based on this
    self.websession = requests.session()
    self.credentials = self.get_credentials()
    pass

  @property
  def logged_in(self):
    # If we have a session cookie we can assume the login worked
    if "SMSESSION" in self.websession.cookies:
      return True
    else:
      return False # Login failed

  def get_credentials(self):
    credentials = {}
    config = configparser.ConfigParser()
    config.read("config.ini")
    try: # Try to read and parse the config file
      for key in ["company", "username", "passwordb64"]:
        credentials[key] = config["credentials"][key]
      encoded_pw = credentials.pop("passwordb64")
      credentials["password"] = base64.b64decode(encoded_pw.encode("utf-8"))
    except KeyError: # If the credentials are not complete in the config, ask the user interactively
      credentials["credentials"]["company"] = input("Company Code: ")
      credentials["credentials"]["username"] = input("Username: ")
      credentials["credentials"]["password"] = getpass.getpass()
    return credentials

  def login(self):
    login_endpoint = parse.urlunparse((self.ADPWORLD_URL.scheme, self.ADPWORLD_URL.netloc, "/ipclogin/5/loginform.fcc", "", "", ""))
    index_quoted = parse.quote(parse.urlunparse((self.ADPWORLD_URL.scheme, self.ADPWORLD_URL.netloc, "/index.html", "", "", "")), safe="")
    target_param = "-SM-{}".format(index_quoted)
    login_params = {"COMPANY": self.credentials["company"], "USER": self.credentials["username"], "PASSWORD": self.credentials["password"], "TARGET": target_param}
    
    req = self.websession.post(login_endpoint, data=login_params)
    if self.logged_in == False:
      return False
    
    # Handle redirection after login
    soup = BeautifulSoup(req.text, 'html.parser')
    redirect = soup.find("meta", attrs={"http-equiv": "refresh"})
    meta_attrs = redirect["content"].split(";")
    target_attr = list(filter(lambda x: "URL" in x, meta_attrs))[0] # Target URL in the HTML meta tag
    target_path = target_attr.split("=")[1]
    self.dashboard_url = parse.urlunparse((self.ADPWORLD_URL.scheme, self.ADPWORLD_URL.netloc, target_path, "", "", ""))
    return True


class PayslipApplication():
  def __init__(self, adpworld):
    self.adpworld = adpworld
    self.init()

  def init(self):
    if self.adpworld.logged_in:
      # Request and parse the main dashboard to find the path to the ePayslip app
      req = self.adpworld.websession.get(self.adpworld.dashboard_url)
      soup = BeautifulSoup(req.text, 'html.parser')
      payslip_param = list(filter(lambda x: "ePayslip" in x.text,soup.find_all("a")))
      payslip_url = payslip_param[0].get("href")
      url = parse.urlunparse((self.adpworld.ADPWORLD_URL.scheme, self.adpworld.ADPWORLD_URL.netloc, payslip_url, "", "", ""))
      
      # Access the ePayslip app to read out a few parameters and the total amount of stored payslips
      req = self.adpworld.websession.get(url)
      self.epayslip_soup = BeautifulSoup(req.text, 'html.parser')
    else:
      raise Exception("Not logged in. Call ADPWorld.login() first.")

  @property
  def documents(self):
    all_documents = []
    # Iterate over all pages until we have all documents collected
    while len(all_documents) < self.total_payslips:
      new_documents = self.paginator_xhr(len(all_documents), 99) # 99 documents seems to be the maximum we can request at once
      all_documents += new_documents
    return all_documents

  @property
  def total_payslips(self):
    paginator_text = self.epayslip_soup.find("table").find("span", {"class": "ui-paginator-current"}).text
    total_payslips = int(re.match(".*?([0-9]*)$", paginator_text).group(1))
    return total_payslips

  def paginator_xhr(self, first=0, rows=20):
    form_inputs = list(self.epayslip_soup.find_all("input")) # All inputs inside the form. Some of them we need to submit
  
    # Main form containing all payslip links
    all_forms = list(self.epayslip_soup.find_all("form"))
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
    xhr_link = parse.urlunparse((self.adpworld.ADPWORLD_URL.scheme, self.adpworld.ADPWORLD_URL.netloc, javax_faces_encodedURL, "", "", ""))
    req = self.adpworld.websession.post(xhr_link, data=data, headers={"Faces-Request": "partial/ajax"})
  
    # The beauty of java on web requires us now to parse XML which contains HTML
    root = ET.fromstring(req.text)
    changes = root.find("./changes/update[@id='{}']".format(magic_application_id)) # Node containing HTML
    soup = BeautifulSoup(changes.text, "html.parser")
    page_documents = []
    for row in soup.find_all("tr"):
      page_documents.append(ADPDocument(self.adpworld, row))
  
    new_ViewState = root.find("./changes/update[@id='javax.faces.ViewState']").text # Is maybe useful for the future
    return page_documents
