# essstat - TP-Link Easy Smart Switch port statistics

Build as a prometheus exporter in a docker container.

## Usage

Run the container and provide the following environment variables:

```
TPLINK_HOST         # IP address or hostname of the switch
TPLINK_USERNAME     # The username for the switch's user interface
TPLINK_PASSWORD     # The password for the switch's user interface
PORT                # Optional, the TCP port to listen at
DEBUG               # Optional, enables more output if set
```

## Example `docker-compose.yml`

```
---
version: "3.9"
services:
  essstat-exporter:
    image: test1
    #image: ghcr.io/michz/essstat-prometheus-exporter:adjustments
    ports:
      - 9292:8000
    environment:
      TPLINK_HOST: 192.168.0.254
      TPLINK_USERNAME: admin
      TPLINK_PASSWORD: secret_change_me_please
    restart: on-failure
```

## Attributions

Based on work from Peter Smode at https://github.com/psmode/essstat
and from Justin Cichra at https://github.com/jrcichra/essstat

## License

GPLv3, see also [LICENSE](LICENSE).
