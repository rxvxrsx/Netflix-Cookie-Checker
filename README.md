
# 🎬 Netflix Cookie Checker

**Check Netflix cookies for validity — fast, multi-threaded, with full proxy support.**

> ⚠️ *Education purpose only.*
>
> ![Logo](images/netflix_logo.jpg)


<p align="center">
   <img src="https://img.shields.io/badge/language-python-blue?style=flat&logo=python">
   <img src="https://img.shields.io/github/stars/rxvxrsx/Netflix-Cookie-Checker?style=flat">
   <img src="https://img.shields.io/github/last-commit/rxvxrsx/Netflix-Cookie-Checker?style=flat">
   <img src="https://img.shields.io/github/license/rxvxrsx/Netflix-Cookie-Checker?style=flat">
</p>

---

### 🔥 Forked from [matheeshapathirana/Netflix-Cookie-Checker](https://github.com/matheeshapathirana/Netflix-cookie-checker)

This fork adds:
- 🔄 **Auto proxy rotation** — switches to next proxy on failure automatically
- 💾 **Failed cookie recovery** — network-failed cookies saved to `failed_cookies/` for retry
- 📊 **Proxy validation progress** — live progress in terminal title bar
- 🛡️ **No abandoned cookies** — network errors never discard your cookies
- 👥 **Upgraded Profile & PIN Lock detection** — supports Netflix's updated client-side UI and GraphQL cache to fix profiles showing as 0, listing locked profile names
- 📝 **Auto-log saving** — automatically saves all working console output logs to `working_log.txt` upon completion

# 🆕 What's New
 
> **Latest update** brings full proxy support with automatic validation, automatic proxy rotation on failure, network-failed cookie recovery, a native file picker UI, reliable account data extraction, upgraded profile count & PIN-lock detection, and automated working logs saving.
 
<details open>
<summary><b>Latest Updates</b></summary>
 
### ✨ New Features
- **Proxy support** — HTTP, HTTPS, SOCKS4, and SOCKS5 proxies now fully supported
- **Automatic proxy validation** — dead proxies are filtered out before checking begins, so no time is wasted
- **Automatic proxy rotation** — when a request fails, the next proxy is automatically used for retry (up to 3 attempts)
- **Network-failed cookie recovery** — cookies that fail due to network errors are saved to `failed_cookies/` so you can retry them later instead of losing them
- **Native file picker** — a Tkinter dialog window lets you browse and select your proxy list instead of editing config files
- **Profiles & PIN Lock detection** — upgraded to extract detailed profile counts and locked profile names directly from the `/ProfilesGate` page and client-side GraphQL cache (`models.graphql`)
- **Automated working logs saving** — automatically writes working cookie logs to `working_log.txt` when checking finishes

### 🔧 Fixes
- **Profile count 0 fixed** — now accurately resolves profile counts and PIN locks by querying `/ProfilesGate` and parsing React's GraphQL cache
- **Expired cookie detection improved** — accounts with cancelled/expired memberships (no active plan) are now correctly flagged as expired instead of showing `[Unknown]` country/plan with `[✔️] Working`
- **Email extraction rewritten** — now reads directly from Netflix's embedded `reactContext` JSON instead of relying on a CSS selector that no longer exists on live pages
- **Plan extraction fixed** — regex cleanup no longer mangles plan names; `\xNN` and `\uNNNN` escape sequences are decoded correctly
- **Country extraction** — `countryOfSignup` is now read reliably from the same JSON blob, with a proper `"Unknown"` fallback
 </details>

# Installation

```cmd
  git clone https://github.com/rxvxrsx/Netflix-Cookie-Checker.git
  cd Netflix-Cookie-Checker
  pip install -r requirements.txt
```
# Usage

1. Run [cookie_converter.py](cookie_converter.py) to convert Netscape cookies to JSON format.
2. Edit the number of threads in `main.py` (line 49: `num_threads = 5`).
3. Run `main.py`.

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

---

## 🙏 Credits

Original project by **[matheeshapathirana](https://github.com/matheeshapathirana/Netflix-cookie-checker)**

Fork maintained by **[rxvxrsx](https://github.com/rxvxrsx)** with improvements:
- Automatic proxy rotation on connection failure
- Network-failed cookie recovery (`failed_cookies/`)
- Live proxy validation progress in terminal title
- Improved error handling — cookies never silently discarded

MIT License — see [LICENSE](LICENSE)
