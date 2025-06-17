#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from urllib import parse
import configparser
import http.client
import datetime
import base64
import getpass
import json
import re
import requests

from bs4 import BeautifulSoup

http.client._MAXHEADERS = 1000


class ADPDocument:
    def __init__(self, payslipapp, document_element):
        self._document_details = None
        self.payslipapp = payslipapp
        columns = document_element.find_all("td")
        self.company_id = columns[1].text
        self.employee_nr = columns[2].text
        self.type = columns[3].text
        self.subject = columns[4].text
        self.date = datetime.datetime.strptime(columns[5].text, "%d.%m.%Y")
        self.file_date = self.date.strftime("%Y%m%d")
        self.pages = columns[6].text
        self.size = columns[7].text
        url_path = columns[8].find("a").get("href")
        self.url = parse.urlunparse(
            (
                self.payslipapp.adpworld.ADPWORLD_URL.scheme,
                self.payslipapp.adpworld.ADPWORLD_URL.netloc,
                url_path,
                "",
                "",
                "",
            )
        )
        self.row_index = document_element.get("data-ri", "")
        self.row_key = document_element.get("data-rk", "")

    @property
    def upload_date(self):
        if not self._document_details:
            self._fetch_details()
        date_attribute = self._document_details["date attribute"]
        return datetime.datetime.strptime(date_attribute, "%y%m%d")

    def _fetch_details(self):
        self._document_details = {}
        details = self.payslipapp.fetch_row_details(self.row_index, self.row_key)
        all_details = details.find_all("label")
        for detail in all_details:
            parent = detail.parent
            label = parent.find("label").text.lower()
            value = parent.find("input").get("value")
            self._document_details.update({label: value})

    @property
    def estimated_filename(self):
        return "{}_{}_{}_{}.pdf".format(
            self.file_date, self.company_id, self.employee_nr, self.type
        )


class ADPWorld:
    def __init__(self):
        self.ADPWORLD_URL = parse.urlparse(
            "https://adpworld.adp.com"
        )  # All URLs are based on this
        self.websession = requests.session()
        self.credentials = self.get_credentials()

    @property
    def logged_in(self):
        try:
            req = self.websession.get(self.dashboard_url)
            soup = BeautifulSoup(req.text, "html.parser")
            return not ("sign in" in soup.title.text.lower())
        except Exception:
            pass
        return False

    def get_credentials(self):
        credentials = {}
        config = configparser.ConfigParser()
        config.read("config.ini")
        try:  # Try to read and parse the config file
            for key in ["company", "username", "passwordb64"]:
                credentials[key] = config["credentials"][key]
            encoded_pw = credentials.pop("passwordb64")
            credentials["password"] = base64.b64decode(encoded_pw.encode("utf-8"))
        except (
            KeyError
        ):  # If the credentials are not complete in the config, ask the user interactively
            pass

        try:  # Try to read and parse the config file
            credentials["cookie"] = config["credentials"]["cookie"]
        except (
            KeyError
        ):  # If the credentials are not complete in the config, ask the user interactively
            pass

        if len(credentials) <= 0:
            credentials["company"] = input("Company Code: ")
            credentials["username"] = input("Username: ")
            credentials["password"] = getpass.getpass()
        return credentials

    def cookie_login(self):
        self.websession.cookies.set("EMEASMSESSION", self.credentials["cookie"])
        login_endpoint = parse.urlunparse(
            (
                self.ADPWORLD_URL.scheme,
                self.ADPWORLD_URL.netloc,
                "/",
                "",
                "",
                "",
            )
        )
        redirect_req = self.websession.get(login_endpoint)
        self.dashboard_url = login_endpoint
        return True

    def login(self):
        if "cookie" in self.credentials:
            self.cookie_login()
            return self.logged_in
        return False


class PayslipApplication:
    def __init__(self, adpworld):
        self.adpworld = adpworld
        self.init()

    def init(self):
        if self.adpworld.logged_in:
            # Request and parse the main dashboard to find the path to the ePayslip app
            for _ in range(
                2
            ):  # The first request ends up in a redirect to exactly the same page so loading it two times sets all expected cookies and stuff
                req = self.adpworld.websession.get(self.adpworld.dashboard_url)
            soup = BeautifulSoup(req.text, "html.parser")
            payslip_param = list(
                filter(lambda x: "ePayslip" in x.text, soup.find_all("a"))
            )
            param = payslip_param[0].get("onclick")
            param_args = (
                param.split(";")[0]
                .split(".")[1]
                .split("(")[1]
                .split(")")[0]
                .split(",", 1)
            )
            json_arg = param_args[1].replace("\\", "").replace("'", '"')
            form_name = param_args[0].replace("'", "").replace('"', "")
            parsed_args = json.loads(json_arg)
            payslip_args = parsed_args
            form_inputs = list(soup.find("form", {"id": form_name}).find_all("input"))
            for form_input in form_inputs:
                payslip_args.update({form_input.get("name"): form_input.get("value")})
            url = self.adpworld.dashboard_url + "ADPWorld/faces/portal/index.xhtml"

            # Access the ePayslip app to read out a few parameters and the total amount of stored payslips
            req = self.adpworld.websession.post(url, params=payslip_args)
            self.epayslip_soup = BeautifulSoup(req.text, "html.parser")
        else:
            raise Exception("Not logged in. Call ADPWorld.login() first.")

    @property
    def documents(self):
        all_documents = []
        # Iterate over all pages until we have all documents collected
        while len(all_documents) < self.total_payslips:
            new_documents = self.paginator_xhr(
                len(all_documents), 50
            )  # 50 documents seems to be the maximum we can request at once
            all_documents += new_documents
        return all_documents

    @property
    def total_payslips(self):
        paginator_text = self.epayslip_soup.find(
            "span", {"class": "ui-paginator-current"}
        ).text
        total_payslips = int(re.match(".*?([0-9]*)$", paginator_text).group(1))
        return total_payslips

    def _call_xhr(self, name, parameter):
        form_inputs = list(
            self.epayslip_soup.find_all("input")
        )  # All inputs inside the form. Some of them we need to submit

        # Main form containing all payslip links
        all_forms = list(self.epayslip_soup.find_all("form"))
        epaylistform = list(
            filter(lambda x: "ePayListForm" in x.get("id", ""), all_forms)
        )[0]

        # All elements of the main form. One of them contains the datatable we're interested in
        target_elements = list(epaylistform.find_all("div"))
        magic_application_id = list(
            filter(lambda x: "ui-datatable" in x.get("class", ""), target_elements)
        )[0].get("id")

        # Extract the viewstate of the jakarta application
        viewstate_element = epaylistform.find_all(
            "input", {"name": "jakarta.faces.ViewState"}
        )[0]
        viewstate = {viewstate_element.get("name"): viewstate_element.get("value")}

        # Now lets assemble and request the data from the paginator endpoint
        data = {
            "jakarta.faces.partial.ajax": True,
            "jakarta.faces.source": magic_application_id,
            "jakarta.faces.partial.execute": magic_application_id,
            "jakarta.faces.partial.render": magic_application_id,
            magic_application_id: magic_application_id,
            magic_application_id + "_" + name: True,
            magic_application_id + "_encodeFeature": True,
        }
        for param_name in parameter.keys():
            param_value = parameter[param_name]
            data.update({magic_application_id + "_" + param_name: param_value})

        data.update(viewstate)
        xhr_link = parse.urlunparse(
            (
                self.adpworld.ADPWORLD_URL.scheme,
                self.adpworld.ADPWORLD_URL.netloc,
                "/ADPWorld/faces/apps/ePayslip/ePayslipList.xhtml",
                "",
                "",
                "",
            )
        )
        req = self.adpworld.websession.post(
            xhr_link, data=data, headers={"Faces-Request": "partial/ajax"}
        )

        # The beauty of java on web requires us now to parse XML which contains HTML
        root = ET.fromstring(req.text)
        changes = root.find(
            "./changes/update[@id='{}']".format(magic_application_id)
        )  # Node containing HTML
        soup = BeautifulSoup(changes.text, "html.parser")
        return soup

    def paginator_xhr(self, first=0, rows=20):
        soup = self._call_xhr("pagination", {"first": first, "rows": rows})
        page_documents = []
        for row in soup.find_all("tr"):
            page_documents.append(ADPDocument(self, row))

        return page_documents

    def fetch_row_details(self, row_index, row_key):
        soup = self._call_xhr(
            "rowExpansion", {"expandedRowIndex": row_index, "expandedRowKey": row_key}
        )
        return soup
