# EMMA: Enhanced Multimedia Mobile Alerts (Proof of Concept)

## Overview

EMMA simulates an end-to-end cell broadcast alert system with media attachments, using:
- CAP/eCAP alert generation (Python)
- LTE RAN+EPC simulation (ns-3)
- Multicast cell-broadcast delivery
- HTTP CDN fallback for media
- Android emulator client for alert reception and display
- Docker Compose orchestration

## Quick Start

### Prerequisites

- Ubuntu 20.04+ with Docker and Docker Compose
- ns-3 (for building the LTE sim)
- OpenSSL (for key generation)

### Build and Run

```sh
# Clone repo and cd into EMMA/
docker-compose up --build
```

### Components

- **cap-generator**: Generates CAP/eCAP XML and SMC zip with ECDSA signature.
- **ns3-sim**: Simulates LTE network, multicasts alert XML.
- **http-cdn**: Serves media zip over HTTP.
- **ue-emulator**: Android emulator, listens for alerts, fetches and displays media.

### Generating New Alerts

1. Place new media in `cap-generator/media/`.
2. Run `docker-compose run cap-generator`.
3. The new `alert123.xml`, `alert123.ecap.xml`, and `alert123.smc.zip` will be generated.

### Viewing Logs

- `docker-compose logs ns3-sim` — shows multicast delivery and UE reception timestamps.
- `docker-compose logs ue-emulator` — shows alert reception and UI display.

### Metrics

- **Latency**: Compare timestamps in ns3-sim and ue-emulator logs.
- **Bandwidth**: Check size of SMC zip and network logs.

### Extending CAP XML

- Add new `<parameter>` or custom `<ecap:Attachment>` elements in the Python template in `capgen.py`.
- Update the Android service to handle new tags as needed.

---

**This PoC is fully software-defined and reproducible on any Ubuntu host with Docker.** 