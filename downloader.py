#!/usr/bin/env python3
from adp import ADPWorld, PayslipApplication
import getpass
import base64
import sys
import os

class Downloader():
  def __init__(self, adpworld):
    self.adpworld = adpworld

  def download(self, adpdocument):
      req = self.adpworld.websession.get(adpdocument.url)
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

if __name__ == "__main__":
    adpworld = ADPWorld()
    if adpworld.login():
      print("Login succeeded")
    else:
      print("Login failed… Please check your credentials")
      sys.exit(1)

    payslips = PayslipApplication(adpworld)
    downloader = Downloader(adpworld)
    for document in payslips.documents:
      downloader.download(document)
    print("All downloads succeeded. Done, exiting.")
