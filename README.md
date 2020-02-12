This script downloads payslips from [adpworld.de](https://www.adpworld.de)'s ePayslip application. It does not require any manual link extraction
and supports the download of all availible documents. Just configure you company, username and password, run the script and
find all Downloads conveniently placed on you HDD.

**Note:** this script was developed with and for accounts [@SUSE](https://github.com/SUSE). If you do not work for SUSE be warned
that it might break and does not work at all. Feel free to try it anyway and report you findings as Issue :+1:.

# Installation

```
git clone https://github.com/nicksinger/adp_downloader.git
cd adp_downloader
mkdir downloads
python adp_downloader.py
```

**Note** for openSUSE users: Make sure you've installed `python3-requests` and `python3-beautifulsoup4`.

# Configuration

Currently the only way to statically configure your company/username/password is by editing the script itself.
This might change in the future.
