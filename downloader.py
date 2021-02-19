#!/usr/bin/env python3
from adp import ADPWorld, PayslipApplication
import getpass
import base64
import sys
import os

if __name__ == "__main__":
    adpworld = ADPWorld()
    if adpworld.login():
      print("Login succeeded")
    else:
      print("Login failed… Please check your credentials")
      sys.exit(1)
    payslips = PayslipApplication(adpworld)

    print("Collecting all payslip URLs via XHR. We expect {} in total.".format(payslips.total_payslips))
    links = []
    while len(links) < payslips.total_payslips:
        print("Fetching payslip {}-{}… ".format(len(links), len(links)+99), end="")
        new_links = payslips.paginator_xhr(len(links), 99)
        links +=new_links
        print("Done.")
    print("Successfuly fetched all payslip download URLs. Now downloading…")

    for link in links:
        link.download(adpworld)
    print("All downloads succeeded. Done, exiting.")
