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
pip install -r requirements.txt
```

# Configuration

Create a config.ini in the same directory. The file has the following format:

```
[credentials]
cookie = your_emeasmsession_cookie
```

where "your_emeasmsession_cookie" corresponds to the `EMEASMSESSION`-cookie set by the web application after you logged in.
You can use your browsers developer tools or an extension like [cookies.txt](https://addons.mozilla.org/de/firefox/addon/cookies-txt/) to extract it.

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

### Local testing

There are currently some limited automatic tests available. Call

```
make test
```

to execute all tests.

## License

This project is licensed under the MIT license, see LICENSE file for details.
