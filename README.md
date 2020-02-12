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

## Contribute

This project lives in https://github.com/nicksinger/adp_downloader

Feel free to add issues in github or send pull requests.

### Rules for commits

* For git commit messages use the rules stated on
  [How to Write a Git Commit Message](http://chris.beams.io/posts/git-commit/) as
  a reference

If this is too much hassle for you feel free to provide incomplete pull
requests for consideration or create an issue with a code change proposal.

## License

This project is licensed under the MIT license, see LICENSE file for details.
