#!/usr/bin/env python3
import datetime
import sqlite3
import sys
import argparse
from pathlib import Path

from adp import ADPWorld, PayslipApplication


class Downloader:
    def __init__(self, adpworld, download_duplicates=False):
        self.adpworld = adpworld
        self.download_duplicates = download_duplicates
        self.db = DB()

    def _get_filename(self, filename):
        index = 0
        file = Path(filename)
        (name, ext) = filename.split(".")
        while file.exists():
            index += 1
            file = Path(name + "_" + str(index) + "." + ext)
        return file.name

    def download(self, adpdocument):
        if self.db.document_present(adpdocument) and not self.download_duplicates:
            return False
        self.db.persist(adpdocument)
        req = self.adpworld.websession.get(adpdocument.url)
        if req.headers.get("Content-Type") != "application/pdf":
            print(
                "{} is not a PDF, skipping download. Please check manually".format(
                    adpdocument.url
                )
            )
        # Ignore Content-Disposition header because the filenames are not unique
        # cd_header = req.headers.get("Content-Disposition")
        # pdf_filename = cd_header.split('"')[1]
        pdf_filename = "{}_{}_{}_{}_{}_{}.pdf".format(
            adpdocument.file_date,
            adpdocument.company_id,
            adpdocument.employee_nr,
            adpdocument.type,
            adpdocument.subject,
            adpdocument.upload_date.strftime("%Y%m%d"),
        )

        assert "/" not in pdf_filename
        Path("downloads").mkdir(exist_ok=True)
        target_filename = self._get_filename("downloads/" + pdf_filename)
        with open("downloads/" + target_filename, "wb") as fp:
            fp.write(req.content)
        return True


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
            """CREATE TABLE IF NOT EXISTS document_subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, subject text NOT NULL, UNIQUE(subject))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS documents (company_id INTEGER, person_id INTEGER, document_type INTEGER, document_subject INTEGER, document_date TEXT, download_date TEXT, upload_date TEXT, FOREIGN KEY(company_id) REFERENCES companies(id), FOREIGN KEY(person_id) REFERENCES persons(id), FOREIGN KEY(document_type) REFERENCES document_types(id), FOREIGN KEY(document_subject) REFERENCES document_subjects(id), UNIQUE(company_id, person_id, document_type, document_subject, document_date))"""
        )
        self.connection.commit()

    def supports_upload_date(self):
        c = self.connection.cursor()
        c.execute(
            """SELECT COUNT(*) FROM pragma_table_info('documents') WHERE name='upload_date';"""
        )
        return bool(c.fetchone()[0])

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
        c.execute(
            """INSERT OR IGNORE INTO document_subjects(subject) VALUES(?)""",
            (adpdocument.subject,),
        )
        company_id, employee_id, type_id, subject_id = self.query_indices(
            adpdocument.company_id,
            adpdocument.employee_nr,
            adpdocument.type,
            adpdocument.subject,
        )
        c.execute(
            """INSERT OR IGNORE INTO documents (company_id, person_id, document_type, document_subject, document_date, download_date, upload_date) VALUES (?, ?, ?, ?, DATE(?), DATETIME(?), DATE(?));""",
            (
                company_id,
                employee_id,
                type_id,
                subject_id,
                adpdocument.date.strftime("%Y-%m-%d"),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                adpdocument.upload_date.strftime("%Y-%m-%d"),
            ),
        )
        self.connection.commit()

    def query_indices(self, company_id, employee_nr, document_type, document_subject):
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
            c.execute(
                """SELECT id FROM document_subjects WHERE subject=?""",
                (document_subject,),
            )
            subject_id = c.fetchone()[0]
            return (company_id, employee_id, type_id, subject_id)
        except TypeError:

            class TableIndexError(Exception):
                pass

            raise TableIndexError("Indices not present")

    def document_present(self, adpdocument):
        c = self.connection.cursor()
        try:
            company_id, employee_id, type_id, subject_id = self.query_indices(
                adpdocument.company_id,
                adpdocument.employee_nr,
                adpdocument.type,
                adpdocument.subject,
            )
            result = c.execute(
                """SELECT download_date FROM documents WHERE person_id = ? AND document_type = ? AND company_id = ? AND document_date = ? AND document_subject = ? AND upload_date = ?""",
                (
                    employee_id,
                    type_id,
                    company_id,
                    adpdocument.date.strftime("%Y-%m-%d"),
                    subject_id,
                    adpdocument.upload_date.strftime("%Y-%m-%d"),
                ),
            )
            return len(result.fetchall()) > 0
        except Exception:
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="adpworld.de scraper")
    parser.add_argument(
        "--download-all",
        default=False,
        action="store_true",
        help="Download all files, including those with filenames matching already downloaded files",
    )
    args = parser.parse_args()
    print("Welcome! Starting up the adpworld.de scraper.")
    adpworld = ADPWorld()
    downloader = Downloader(adpworld, args.download_all)
    if not downloader.db.supports_upload_date():
        print(
            "Database does not support document upload date to avoid duplicates. Please backup your old download_history.db-file and move it to a different place. Do the same with your downloads folder to avoid a mix of old and new file(names)."
        )
        sys.exit(1)
    print("Trying to log in… ", end="")
    if adpworld.login():
        print("Success!")
    else:
        print("Failed.")
        print("Please check your credentials!")
        sys.exit(1)

    if args.download_all:
        print(
            "Will download all documents, including those with duplicate file names. Duplicate files will have a numeric index before the file extension"
        )
    else:
        print("Will skip download of documents with the same file name")

    print("Fetching all available payslips…", end="")
    payslips = PayslipApplication(adpworld)
    print(" Done.")
    print("Starting to download new payslips:")
    for document in payslips.documents:
        pdf_filename = "{}_{}_{}_{}_{}_{}.pdf".format(
            document.file_date,
            document.company_id,
            document.employee_nr,
            document.type,
            document.subject,
            document.upload_date.strftime("%Y%m%d"),
        )
        print("\tDownloading {}…".format(pdf_filename), end="")
        download_was_done = downloader.download(document)
        if download_was_done:
            print(" done.")
        else:
            print(" skipped.")
    print("All downloads succeeded. Done, exiting.")
