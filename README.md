This script downloads payslips from [adpworld.de](https://www.adpworld.de)'s ePayslip application. It does not require any manual link extraction
and supports the download of all availible documents. Just configure you company, username and password, run the script and
find all downloads conveniently placed on you HDD.

**Note:** this script was developed with and for accounts [@SUSE](https://github.com/SUSE). If you do not work for SUSE be warned
that it might break and does not work at all. Feel free to try it anyway and report your findings as github issues :+1:.

# Installation

```
git clone https://github.com/nicksinger/adp_downloader.git
cd adp_downloader
mkdir downloads
```

**Note** for openSUSE users: Make sure you've installed `python3-requests` and `python3-beautifulsoup4`.

Alternatively and for development you can get all development requirements
with

```
pip install -r requirements-dev.txt
```

# Configuration

Create a config.ini in the same directory. The file has the following format:

```
[credentials]
company = yourcompanyname
username = yourusername
passwordb64 = base64_encoded_password
```

where "yourcompanyname" and "yourusername" are the separate company name and
user name without the "_" character, for example company "sus" and username
"johdoe".

The base64 encoding is purely to ease handling of special characters in your password and **DOES NOT** serve any protection or encryption. Only store your credentials on a well secured system which you trust. Adjust permissions to the config file accordingly.
To generate the base64 encoded password, you can use `echo -n "yourpassword" | base64`.

Make sure the `-n` parameter is present so echo doesn't add a "\n" at
the end of your password as it will break the login.

# Execution

Simply run `python downloader.py` and watch it fetch your documents.
By default the downloader will create a local sqlite database to remember already downloaded files. Each new execution of the downloader will only download newly added files to your disk. This allows you to easily run the downloader in a cron job.

## Contribute

This project lives in https://github.com/nicksinger/adp_downloader

Feel free to add issues in github or send pull requests.

### Rules for commits

* For git commit messages use the rules stated on
  [How to Write a Git Commit Message](http://chris.beams.io/posts/git-commit/) as
  a reference

If this is too much hassle for you feel free to provide incomplete pull
requests for consideration or create an issue with a code change proposal.
