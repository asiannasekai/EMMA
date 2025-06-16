# EMMA (Enhanced Multimedia Mobile Alerts)

A fully software-defined proof-of-concept for emergency alert distribution over LTE networks with multimedia support.

## Project Structure

```
EMMA/
├── cap-generator/     # Python-based CAP/eCAP generator
├── ns3-sim/          # ns-3 LTE network simulator
├── http-cdn/         # Node.js media server
├── ue-emulator/      # Android client emulator
└── docker-compose.yml
```

## Prerequisites

- Docker and Docker Compose
- Ubuntu 20.04 or later
- At least 8GB RAM
- 20GB free disk space

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/EMMA.git
   cd EMMA
   ```

2. Build and start all services:
   ```bash
   docker-compose up --build
   ```

3. Generate a test alert:
   ```bash
   docker-compose exec cap-generator python3 cap_generator.py
   ```

## Components

### CAP Generator

The CAP generator creates Common Alerting Protocol (CAP) messages with optional multimedia attachments.

- Generates both text-only CAP and extended CAP (eCAP) XML files
- Creates Secure Media Containers (SMC) for attachments
- Signs media with ECDSA
- Outputs: `alert123.xml` and `alert123.smc.zip`

### NS-3 Simulator

The ns-3 simulator creates a virtual LTE network environment.

- Simulates one eNodeB and 10 UE nodes
- Configures multicast group 239.255.0.1:5000
- Streams CAP XML payloads
- Logs reception timestamps

### HTTP CDN

A simple Node.js server for media distribution.

- Serves static files from `/alerts`
- Provides CORS support
- Includes health check and metrics endpoints
- Runs on port 3000

### UE Emulator

An Android-based client that receives and displays alerts.

- Listens for multicast alerts
- Verifies media signatures
- Displays text and media content
- Runs in a Docker container with Android emulator

## Testing

### Unit Tests

Run tests for each component:

```bash
# CAP Generator tests
docker-compose exec cap-generator pytest

# HTTP CDN tests
docker-compose exec http-cdn npm test
```

### Integration Tests

1. Generate a test alert:
   ```bash
   docker-compose exec cap-generator python3 cap_generator.py
   ```

2. Monitor the UE emulator logs:
   ```bash
   docker-compose logs -f ue-emulator
   ```

3. Check HTTP CDN metrics:
   ```bash
   curl http://localhost:3000/metrics
   ```

## Extending the CAP Schema

To add new attachment types:

1. Modify `cap_generator.py` to support new media types
2. Update the Android client's media handling
3. Add appropriate MIME type support in the HTTP CDN

## Monitoring

- HTTP CDN metrics: `http://localhost:3000/metrics`
- NS-3 traces: Check `ns3-sim/traces/`
- UE emulator logs: `docker-compose logs ue-emulator`

## Troubleshooting

1. If the Android emulator fails to start:
   ```bash
   docker-compose down
   docker system prune
   docker-compose up --build
   ```

2. If multicast isn't working:
   - Ensure host network mode is enabled
   - Check firewall settings
   - Verify network interface supports multicast

3. If media isn't displaying:
   - Check HTTP CDN logs
   - Verify file permissions in the alerts directory
   - Check Android emulator logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 