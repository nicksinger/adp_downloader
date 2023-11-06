#!/usr/bin/env python3
from adp import ADPWorld, PayslipApplication
import datetime
import getpass
import sqlite3
import base64
import sys
import os


class Downloader:
    def __init__(self, adpworld):
        self.adpworld = adpworld
        self.db = DB()

    def download(self, adpdocument):
        if not self.db.document_present(adpdocument):
            self.db.persist(adpdocument)
            req = self.adpworld.websession.get(adpdocument.url)
            if req.headers.get("Content-Type") != "application/pdf":
                print(
                    "{} is not a PDF, skipping download. Please check manually".format(
                        url
                    )
                )
            cd_header = req.headers.get("Content-Disposition")
            pdf_filename = cd_header.split('"')[1]
            assert not "/" in pdf_filename
            with open("downloads/" + pdf_filename, "wb") as fp:
                fp.write(req.content)
            return True
        else:
            return False


class DB:
    def __init__(self):
        self.connection = sqlite3.connect("download_history.db")
        c = self.connection.cursor()
        c.execute("""PRAGMA foreign_keys = ON""")
        c.execute(
            """CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY AUTOINCREMENT, company text NOT NULL, UNIQUE(company))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS persons (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_number text NOT NULL, UNIQUE(staff_number))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS document_types (id INTEGER PRIMARY KEY AUTOINCREMENT, type text NOT NULL, UNIQUE(type))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS documents (company_id INTEGER, person_id INTEGER, document_type INTEGER, document_date TEXT, download_date TEXT, FOREIGN KEY(company_id) REFERENCES companies(id), FOREIGN KEY(person_id) REFERENCES persons(id), FOREIGN KEY(document_type) REFERENCES document_types(id), UNIQUE(company_id, person_id, document_type, document_date))"""
        )
        self.connection.commit()

    def persist(self, adpdocument):
        c = self.connection.cursor()
        c.execute(
            """INSERT OR IGNORE INTO companies(company) VALUES(?)""",
            (adpdocument.company_id,),
        )
        c.execute(
            """INSERT OR IGNORE INTO persons(staff_number) VALUES(?)""",
            (adpdocument.employee_nr,),
        )
        c.execute(
            """INSERT OR IGNORE INTO document_types(type) VALUES(?)""",
            (adpdocument.type,),
        )
        company_id, employee_id, type_id = self.query_indices(
            adpdocument.company_id, adpdocument.employee_nr, adpdocument.type
        )
        c.execute(
            """INSERT OR IGNORE INTO documents (company_id, person_id, document_type, document_date, download_date) VALUES (?, ?, ?, DATE(?), DATETIME(?));""",
            (
                company_id,
                employee_id,
                type_id,
                adpdocument.date.strftime("%Y-%m-%d"),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        self.connection.commit()

    def query_indices(self, company_id, employee_nr, document_type):
        c = self.connection.cursor()
        try:
            c.execute("""SELECT id FROM companies WHERE company=?""", (company_id,))
            company_id = c.fetchone()[0]
            c.execute("""SELECT id FROM persons WHERE staff_number=?""", (employee_nr,))
            employee_id = c.fetchone()[0]
            c.execute(
                """SELECT id FROM document_types WHERE type=?""", (document_type,)
            )
            type_id = c.fetchone()[0]
            return (company_id, employee_id, type_id)
        except TypeError:
            raise Exception("Indices not present")

    def document_present(self, adpdocument):
        c = self.connection.cursor()
        try:
            company_id, employee_id, type_id = self.query_indices(
                adpdocument.company_id, adpdocument.employee_nr, adpdocument.type
            )
            result = c.execute(
                """SELECT download_date FROM documents WHERE person_id = ? AND document_type = ? AND company_id = ? AND document_date = ?""",
                (
                    employee_id,
                    type_id,
                    company_id,
                    adpdocument.date.strftime("%Y-%m-%d"),
                ),
            )
            if len(result.fetchall()) > 0:
                return True
            else:
                return False
        except Exception:
            return False


if __name__ == "__main__":
    print("Welcome! Starting up the adpworld.de scraper.")
    adpworld = ADPWorld()
    print("Trying to log in… ", end="")
    if adpworld.login():
        print("Success!")
    else:
        print("Failed…")
        print("Please check your credentials!")
        sys.exit(1)

    print("Fetching all available payslips…", end="")
    payslips = PayslipApplication(adpworld)
    downloader = Downloader(adpworld)
    print(" Done.")
    print("Starting to download new payslips:")
    for document in payslips.documents:
        print("\tDownloading {}…".format(document.estimated_filename), end="")
        download_was_done = downloader.download(document)
        if download_was_done:
            print(" done.")
        else:
            print(" skipped.")
    print("All downloads succeeded. Done, exiting.")
