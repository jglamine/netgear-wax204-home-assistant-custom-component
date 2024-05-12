# Netgear WAX204

_Home assistant integration for Netgear WAX204 router._

Provides a device tracker for devices connected to the router. Works by scraping the router's web UI.

# Details

Note that the WAX204 has an odd limitation - only one user can be signed into the web UI at a time. This poses a challenge for our automation - if we scrape the web UI every 30 seconds you will be locked out from manually
using the web UI.

Our solution is to detect when someone starts using the web UI (by noticing that we were signed out)
and wait 10 minutes before signing in again and continuing to scrape. This means that if you manually sign
into the router web UI, the device tracker will pause for 10 minutes and device status won't update.

# Installation

Install with HACS as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/).

## Configuration is done in the Home Assistant UI

`Settings` -> `Devices and Services` -> `Add integration` -> `Netgear WAX204`

# Development

Open the project with visual studio code as a devcontainer. You can use the container to start home assistant and manually test the integration.

## Start home assistant

Run this command to start home assistant and test the extension:
```
> scripts/develop
```

Or in vscode choose `cmd + shift + p` -> `Tasks: Run Task` -> `Run Home Assistant on port 8123`

### Attaching a debugger

Home Assistant listens for a `debugpy` debugger on port `5678`.

Attach using vscode's built-in debugger:

`Run and Debug` (play arrow on left menu) -> `Python: Attach to Home Assistant`

## Run tests

Run tests using pytest:
```
> pytest
```

### Set router host and password

Some of the tests connect to the router and read the router host and password from a file. Create this file and set to your router's hostname and password:

`test/test-data.properties`
```
router_host=192.168.1.1
router_password=hunter2

```

## Updating home assistant version
* `requirements.txt` - Upgrade `homeassistant`
* `requirements-dev.txt` - Upgrade `pytest-homeassistant-custom-component` to the version which matches your `homeassistant` version
* `hacs.json` - If the minimum required home assistant version changed, update `homeassistant`
