
# Netflix Cookie Checker

**Checks Cookies for validity.**

*<b>Education purpose only.</b>*<br><br>
![Logo](images/netflix_logo.jpg)


<p align= "center">
   <img src="https://img.shields.io/github/languages/top/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://img.shields.io/github/stars/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://img.shields.io/github/forks/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://github.com/matheeshapathirana/Netflix-cookie-checker/actions/workflows/codeql.yml/badge.svg?branch=master">
   <img src="https://github.com/matheeshapathirana/Netflix-cookie-checker/actions/workflows/dependabot/dependabot-updates/badge.svg">
   <br>
   <img src="https://img.shields.io/github/last-commit/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://img.shields.io/github/license/matheeshapathirana/Netflix-cookie-checker">
   <br>
   <img src="https://img.shields.io/github/issues/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://img.shields.io/github/issues-closed/matheeshapathirana/Netflix-cookie-checker">
   <img src="https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fmatheeshapathirana%2FNetflix-cookie-checker&label=Hits&icon=github&color=%23198754&message=&style=flat&tz=UTC">
   <br>
   <br>
   <img src="https://repobeats.axiom.co/api/embed/97888767d68bc2104aed23c14f34d310822b4bc8.svg">
</p>

# 🆕 What's New
 
> **Latest update** brings full proxy support with automatic validation, automatic proxy rotation on failure, network-failed cookie recovery, a native file picker UI, and more reliable account data extraction.
 
<details open>
<summary><b>Proxy Support — Latest</b></summary>
 
### ✨ New Features
- **Proxy support** — HTTP, HTTPS, SOCKS4, and SOCKS5 proxies now fully supported
- **Automatic proxy validation** — dead proxies are filtered out before checking begins, so no time is wasted
- **Automatic proxy rotation** — when a request fails, the next proxy is automatically used for retry (up to 3 attempts)
- **Network-failed cookie recovery** — cookies that fail due to network errors are saved to `failed_cookies/` so you can retry them later instead of losing them
- **Native file picker** — a Tkinter dialog window lets you browse and select your proxy list instead of editing config files

### 🔧 Fixes
- **Email extraction rewritten** — now reads directly from Netflix's embedded `reactContext` JSON instead of relying on a CSS selector that no longer exists on live pages
- **Plan extraction fixed** — regex cleanup no longer mangles plan names; `\xNN` and `\uNNNN` escape sequences are decoded correctly
- **Country extraction** — `countryOfSignup` is now read reliably from the same JSON blob, with a proper `"Unknown"` fallback
 </details>

# Installation

```cmd
  git clone https://github.com/matheeshapathirana/Netflix-cookie-checker.git
  cd Netflix-cookie-checker
  pip install -r requirements.txt
```
# Usage

1.  Run [cookie_converter.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/b82b684355a80e23f5648e6082090d9cd5332cc3/cookie_converter.py) to convert Netscape cookies to json format.
2. Edit the number of threads in [main.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/0627ae9af2c51276a7a1fa9880a4a82cf0e606d4/main.py).
   https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/0cbea047e4635c9f0ab6736755336a9b5315b9e3/main.py#L20
2. Run [main.py](https://github.com/matheeshapathirana/Netflix-cookie-checker/blob/5981527b46093775ecb027c73de0bcc6361eb5ea/main.py).

**make sure you have a good internet connection.**

| Network Speed | Recommended no. threads |
|---------------|-------------------------|
| < 5 Mbps      | 1-3                     |
| 5-20 Mbps     | 3-5                     |
| 20-100 Mbps   | 5-10                    |
| > 100 Mbps    | 10-20                   |

## [Try colab-version](https://github.com/matheeshapathirana/Netflix-cookie-checker/tree/colab-version)


# Proxy Support
 
### Proxy File Format
 
Your proxy file should be a plain `.txt` with one proxy per line. All common formats are supported:
 
```
# host:port
1.2.3.4:8080
 
# host:port:user:pass
1.2.3.4:8080:myuser:mypass
 
# user:pass@host:port
myuser:mypass@1.2.3.4:8080
```
 
Lines starting with `#` are ignored.

### How Proxy Rotation Works

Proxies are shared across all threads using **round-robin** (not 1 proxy per 1 cookie):

- Each thread picks the next available proxy from the pool
- When a request fails (connection error, timeout), the proxy is **automatically rotated** and the request is retried
- Retried up to 3 times with different proxies before giving up
- If all retries fail → cookie is saved to `failed_cookies/` instead of being lost


 
 
## Features
 
- ✅ Multi-threading
- ✅ JSON + Netscape cookie support
- ✅ Optional proxy support (HTTP / HTTPS / SOCKS4 / SOCKS5)
- ✅ Automatic proxy validation before use
- ✅ No rate limiting
- ✅ Super fast
- ✅ Identifies duplicate cookies
- ✅ Detects extra memberships
- ✅ Auto proxy rotation on failure (round-robin)
- ✅ Network-failed cookie recovery — saves to `failed_cookies/` for later retry


## Recovering network-failed cookies

If a cookie fails due to network errors (connection reset, proxy timeout, etc.), it will be saved to the `failed_cookies/` folder instead of being lost. To retry:

1. Move the JSON files from `failed_cookies/` → `json_cookies/`
2. Re-run `main.py` (preferably with better network/proxy)

> 💡 **Tip:** Network-failed cookies are **different** from expired cookies — they may still be valid accounts that just couldn't be checked due to connectivity issues!

# For any issues
<a href="https://discord.gg/RSCdKeKB5X"><img src="https://discord.com/api/guilds/1121457935822901278/widget.png?style=banner2"></a>

# Contributors
![GitHub Contributors Image](https://contrib.rocks/image?repo=matheeshapathirana/Netflix-cookie-checker)
 

# You can help me by Donating
  [![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/matheeshapathirana)
