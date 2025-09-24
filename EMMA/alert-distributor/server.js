const express = require('express');
const WebSocket = require('ws');
const redis = require('redis');
const cors = require('cors');
const morgan = require('morgan');
const compression = require('compression');
const { v4: uuidv4 } = require('uuid');

class AlertDistributor {
    constructor() {
        this.app = express();
        this.server = null;
        this.wss = null;
        this.redisClient = null;
        this.subscriber = null;
        this.connections = new Map(); // UE ID -> WebSocket connection
        this.connectionStats = {
            totalConnections: 0,
            activeConnections: 0,
            alertsDistributed: 0,
            totalBytesTransferred: 0
        };
        
        this.setupMiddleware();
        this.setupRoutes();
    }
    
    setupMiddleware() {
        this.app.use(compression());
        this.app.use(cors());
        this.app.use(morgan('combined'));
        this.app.use(express.json());
    }
    
    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                connections: this.connectionStats.activeConnections,
                alertsDistributed: this.connectionStats.alertsDistributed
            });
        });
        
        // Statistics endpoint
        this.app.get('/stats', (req, res) => {
            res.json({
                ...this.connectionStats,
                connectedUEs: Array.from(this.connections.keys()),
                timestamp: new Date().toISOString()
            });
        });
        
        // Manual alert distribution (for testing)
        this.app.post('/distribute-alert', async (req, res) => {
            try {
                const alertData = req.body;
                const distributed = await this.distributeAlert(alertData);
                
                res.json({
                    success: true,
                    distributed,
                    alertId: alertData.identifier || 'unknown',
                    timestamp: new Date().toISOString()
                });
            } catch (error) {
                console.error('Error distributing manual alert:', error);
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });
        
        // Get connected UEs
        this.app.get('/ues', (req, res) => {
            const ueList = Array.from(this.connections.entries()).map(([ueId, ws]) => ({
                ueId,
                connected: ws.readyState === WebSocket.OPEN,
                lastSeen: ws.lastSeen || null,
                location: ws.location || null
            }));
            
            res.json({
                totalUEs: ueList.length,
                activeUEs: ueList.filter(ue => ue.connected).length,
                ues: ueList
            });
        });
    }
    
    async setupRedis() {
        try {
            const redisHost = process.env.REDIS_HOST || 'redis';
            const redisPort = process.env.REDIS_PORT || 6379;
            
            // Main Redis client
            this.redisClient = redis.createClient({
                url: `redis://${redisHost}:${redisPort}`
            });
            
            // Subscriber client
            this.subscriber = redis.createClient({
                url: `redis://${redisHost}:${redisPort}`
            });
            
            await this.redisClient.connect();
            await this.subscriber.connect();
            
            console.log('✅ Connected to Redis successfully');
            
            // Subscribe to alert channels
            await this.subscriber.subscribe('emma:alerts', (message) => {
                this.handleAlertMessage(message);
            });
            
            await this.subscriber.subscribe('emma:network_alerts', (message) => {
                this.handleNetworkAlert(message);
            });
            
            console.log('✅ Subscribed to Redis channels');
            
        } catch (error) {
            console.error('❌ Failed to connect to Redis:', error);
            throw error;
        }
    }
    
    setupWebSocket() {
        const wsPort = process.env.WS_PORT || 8080;
        
        this.wss = new WebSocket.Server({ 
            port: wsPort,
            perMessageDeflate: {
                zlibDeflateOptions: {
                    level: 3,
                    chunkSize: 1024
                },
                threshold: 1024,
                concurrencyLimit: 10
            }
        });
        
        this.wss.on('connection', (ws, req) => {
            const connectionId = uuidv4();
            ws.connectionId = connectionId;
            ws.isAlive = true;
            ws.lastSeen = new Date().toISOString();
            
            this.connectionStats.totalConnections++;
            this.connectionStats.activeConnections++;
            
            console.log(`📱 New WebSocket connection: ${connectionId}`);
            
            // Handle messages from UE
            ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleUEMessage(ws, message);
                } catch (error) {
                    console.error('Invalid message from UE:', error);
                    ws.send(JSON.stringify({
                        type: 'error',
                        message: 'Invalid message format'
                    }));
                }
            });
            
            // Handle connection close
            ws.on('close', () => {
                this.handleUEDisconnect(ws);
            });
            
            // Handle errors
            ws.on('error', (error) => {
                console.error(`WebSocket error for ${ws.ueId || connectionId}:`, error);
                this.handleUEDisconnect(ws);
            });
            
            // Pong handler for heartbeat
            ws.on('pong', () => {
                ws.isAlive = true;
                ws.lastSeen = new Date().toISOString();
            });
            
            // Send welcome message
            ws.send(JSON.stringify({
                type: 'welcome',
                connectionId,
                timestamp: new Date().toISOString(),
                message: 'Connected to EMMA Alert Distributor'
            }));
        });
        
        // Setup heartbeat interval
        const heartbeatInterval = setInterval(() => {
            this.wss.clients.forEach((ws) => {
                if (!ws.isAlive) {
                    console.log(`💔 Terminating dead connection: ${ws.ueId || ws.connectionId}`);
                    this.handleUEDisconnect(ws);
                    return ws.terminate();
                }
                
                ws.isAlive = false;
                ws.ping();
            });
        }, 30000); // 30 second heartbeat
        
        this.wss.on('close', () => {
            clearInterval(heartbeatInterval);
        });
        
        console.log(`🌐 WebSocket server listening on port ${wsPort}`);
    }
    
    handleUEMessage(ws, message) {
        switch (message.type) {
            case 'register':
                this.registerUE(ws, message);
                break;
                
            case 'heartbeat':
                ws.lastSeen = new Date().toISOString();
                ws.send(JSON.stringify({
                    type: 'heartbeat_ack',
                    timestamp: new Date().toISOString()
                }));
                break;
                
            case 'alert_ack':
                this.handleAlertAck(ws, message);
                break;
                
            case 'location_update':
                this.handleLocationUpdate(ws, message);
                break;
                
            default:
                console.log(`Unknown message type from UE ${ws.ueId}: ${message.type}`);
        }
    }
    
    async registerUE(ws, message) {
        const { ueId, location, capabilities } = message;
        
        if (!ueId) {
            ws.send(JSON.stringify({
                type: 'error',
                message: 'UE ID is required for registration'
            }));
            return;
        }
        
        // Store UE information
        ws.ueId = ueId;
        ws.location = location;
        ws.capabilities = capabilities || {};
        ws.registeredAt = new Date().toISOString();
        
        // Add to connections map
        this.connections.set(ueId, ws);
        
        // Store in Redis
        try {
            await this.redisClient.hSet('emma:ue_store', ueId, JSON.stringify({
                ueId,
                location,
                capabilities,
                connectionStatus: 'connected',
                lastSeen: new Date().toISOString(),
                alertsReceived: 0
            }));
            
            await this.redisClient.sAdd('emma:active_ues', ueId);
            
            // Publish UE registration event
            await this.redisClient.publish('emma:ue_status', JSON.stringify({
                action: 'register',
                ueId,
                location,
                timestamp: new Date().toISOString()
            }));
            
        } catch (error) {
            console.error('Failed to store UE registration:', error);
        }
        
        // Send registration confirmation
        ws.send(JSON.stringify({
            type: 'registration_confirmed',
            ueId,
            timestamp: new Date().toISOString(),
            message: 'Successfully registered with EMMA system'
        }));
        
        console.log(`📱 Registered UE: ${ueId} at ${location ? `${location.lat},${location.lon}` : 'unknown location'}`);
    }
    
    handleUEDisconnect(ws) {
        if (ws.ueId) {
            this.connections.delete(ws.ueId);
            
            // Update Redis
            this.redisClient.sRem('emma:active_ues', ws.ueId).catch(console.error);
            
            // Update UE status
            this.redisClient.hGet('emma:ue_store', ws.ueId)
                .then(data => {
                    if (data) {
                        const ueData = JSON.parse(data);
                        ueData.connectionStatus = 'disconnected';
                        ueData.lastSeen = new Date().toISOString();
                        
                        return this.redisClient.hSet('emma:ue_store', ws.ueId, JSON.stringify(ueData));
                    }
                })
                .catch(console.error);
            
            // Publish disconnection event
            this.redisClient.publish('emma:ue_status', JSON.stringify({
                action: 'unregister',
                ueId: ws.ueId,
                timestamp: new Date().toISOString()
            })).catch(console.error);
            
            console.log(`📱 UE disconnected: ${ws.ueId}`);
        }
        
        this.connectionStats.activeConnections = Math.max(0, this.connectionStats.activeConnections - 1);
    }
    
    handleAlertMessage(message) {
        try {
            const alertData = JSON.parse(message);
            console.log(`🚨 Received alert: ${alertData.identifier}`);
            this.distributeAlert(alertData);
        } catch (error) {
            console.error('Error handling alert message:', error);
        }
    }
    
    handleNetworkAlert(message) {
        try {
            const alertData = JSON.parse(message);
            console.log(`📡 Received network alert: ${alertData.identifier || 'unknown'}`);
            this.distributeAlert(alertData);
        } catch (error) {
            console.error('Error handling network alert:', error);
        }
    }
    
    async distributeAlert(alertData) {
        let distributed = 0;
        const alertMessage = {
            type: 'emergency_alert',
            alert: alertData,
            timestamp: new Date().toISOString(),
            distributorId: 'emma-alert-distributor'
        };
        
        const messageString = JSON.stringify(alertMessage);
        const messageSize = Buffer.byteLength(messageString, 'utf8');
        
        // Distribute to all connected UEs
        for (const [ueId, ws] of this.connections.entries()) {
            if (ws.readyState === WebSocket.OPEN) {
                try {
                    ws.send(messageString);
                    distributed++;
                    this.connectionStats.totalBytesTransferred += messageSize;
                    
                    // Update UE statistics
                    const ueData = await this.redisClient.hGet('emma:ue_store', ueId);
                    if (ueData) {
                        const ue = JSON.parse(ueData);
                        ue.alertsReceived = (ue.alertsReceived || 0) + 1;
                        ue.lastAlertReceived = new Date().toISOString();
                        await this.redisClient.hSet('emma:ue_store', ueId, JSON.stringify(ue));
                    }
                    
                } catch (error) {
                    console.error(`Failed to send alert to UE ${ueId}:`, error);
                }
            }
        }
        
        this.connectionStats.alertsDistributed++;
        
        console.log(`📤 Alert ${alertData.identifier || 'unknown'} distributed to ${distributed} UEs`);
        
        // Store distribution metrics
        await this.redisClient.hSet('emma:distribution_log', 
            new Date().toISOString(),
            JSON.stringify({
                alertId: alertData.identifier,
                distributedTo: distributed,
                totalConnections: this.connections.size,
                timestamp: new Date().toISOString()
            })
        );
        
        return distributed;
    }
    
    handleAlertAck(ws, message) {
        const { alertId, received, displayed } = message;
        console.log(`✅ Alert acknowledgment from UE ${ws.ueId}: ${alertId} (received: ${received}, displayed: ${displayed})`);
        
        // Store acknowledgment in Redis
        this.redisClient.hSet('emma:alert_acks', 
            `${alertId}:${ws.ueId}`,
            JSON.stringify({
                ueId: ws.ueId,
                alertId,
                received,
                displayed,
                timestamp: new Date().toISOString()
            })
        ).catch(console.error);
    }
    
    handleLocationUpdate(ws, message) {
        const { location } = message;
        if (location && ws.ueId) {
            ws.location = location;
            
            // Update location in Redis
            this.redisClient.hGet('emma:ue_store', ws.ueId)
                .then(data => {
                    if (data) {
                        const ueData = JSON.parse(data);
                        ueData.location = location;
                        ueData.lastSeen = new Date().toISOString();
                        
                        return this.redisClient.hSet('emma:ue_store', ws.ueId, JSON.stringify(ueData));
                    }
                })
                .catch(console.error);
                
            console.log(`📍 Location update from UE ${ws.ueId}: ${location.lat}, ${location.lon}`);
        }
    }
    
    async start() {
        try {
            // Start HTTP server
            const httpPort = process.env.HTTP_PORT || 3001;
            this.server = this.app.listen(httpPort, () => {
                console.log(`🌐 Alert Distributor HTTP server running on port ${httpPort}`);
            });
            
            // Setup Redis connection
            await this.setupRedis();
            
            // Setup WebSocket server
            this.setupWebSocket();
            
            console.log('🚀 Alert Distributor started successfully');
            
        } catch (error) {
            console.error('❌ Failed to start Alert Distributor:', error);
            process.exit(1);
        }
    }
    
    async stop() {
        console.log('🛑 Shutting down Alert Distributor...');
        
        // Close WebSocket server
        if (this.wss) {
            this.wss.close();
        }
        
        // Close HTTP server
        if (this.server) {
            this.server.close();
        }
        
        // Close Redis connections
        if (this.redisClient) {
            await this.redisClient.quit();
        }
        if (this.subscriber) {
            await this.subscriber.quit();
        }
        
        console.log('✅ Alert Distributor stopped');
    }
}

// Start the service
const distributor = new AlertDistributor();

// Graceful shutdown
process.on('SIGTERM', async () => {
    await distributor.stop();
    process.exit(0);
});

process.on('SIGINT', async () => {
    await distributor.stop();
    process.exit(0);
});

// Start the service
distributor.start().catch(error => {
    console.error('Failed to start Alert Distributor:', error);
    process.exit(1);
});

module.exports = AlertDistributor;