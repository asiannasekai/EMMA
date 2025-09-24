const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const redis = require('redis');
const cors = require('cors');
const morgan = require('morgan');
const compression = require('compression');
const helmet = require('helmet');
const path = require('path');

class EmmaDashboard {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server, {
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        this.redisClient = null;
        this.subscriber = null;
        this.connectedClients = new Set();
        
        this.systemMetrics = {
            totalAlerts: 0,
            activeUEs: 0,
            alertsInLast24h: 0,
            averageDeliveryTime: 0,
            systemStatus: 'initializing',
            componentStatus: {
                'cap-generator': 'unknown',
                'http-cdn': 'unknown',
                'alert-distributor': 'unknown',
                'ns3-simulator': 'unknown',
                'redis': 'unknown'
            }
        };
        
        this.setupMiddleware();
        this.setupRoutes();
        this.setupSocketHandlers();
    }
    
    setupMiddleware() {
        this.app.use(helmet({
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    styleSrc: ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"],
                    scriptSrc: ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"],
                    connectSrc: ["'self'", "ws:", "wss:"]
                }
            }
        }));
        this.app.use(compression());
        this.app.use(cors());
        this.app.use(morgan('combined'));
        this.app.use(express.json());
        this.app.use(express.static(path.join(__dirname, 'public')));
    }
    
    setupRoutes() {
        // Main dashboard
        this.app.get('/', (req, res) => {
            res.sendFile(path.join(__dirname, 'public', 'index.html'));
        });
        
        // API routes
        this.app.get('/api/metrics', async (req, res) => {
            try {
                const metrics = await this.getCurrentMetrics();
                res.json(metrics);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        this.app.get('/api/alerts', async (req, res) => {
            try {
                const alerts = await this.getRecentAlerts();
                res.json(alerts);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        this.app.get('/api/ues', async (req, res) => {
            try {
                const ues = await this.getConnectedUEs();
                res.json(ues);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        this.app.get('/api/system-status', async (req, res) => {
            try {
                const status = await this.getSystemStatus();
                res.json(status);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                connectedClients: this.connectedClients.size
            });
        });
    }
    
    setupSocketHandlers() {
        this.io.on('connection', (socket) => {
            console.log(`📊 Dashboard client connected: ${socket.id}`);
            this.connectedClients.add(socket);
            
            // Send initial data
            this.sendMetricsUpdate(socket);
            
            socket.on('disconnect', () => {
                console.log(`📊 Dashboard client disconnected: ${socket.id}`);
                this.connectedClients.delete(socket);
            });
            
            socket.on('request-update', async () => {
                await this.sendMetricsUpdate(socket);
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
            
            console.log('✅ Dashboard connected to Redis');
            
            // Subscribe to system events
            await this.subscriber.subscribe('emma:alerts', (message) => {
                this.handleAlertUpdate(message);
            });
            
            await this.subscriber.subscribe('emma:ue_status', (message) => {
                this.handleUEStatusUpdate(message);
            });
            
            await this.subscriber.subscribe('emma:metrics', (message) => {
                this.handleMetricsUpdate(message);
            });
            
            console.log('✅ Dashboard subscribed to Redis channels');
            
        } catch (error) {
            console.error('❌ Failed to setup Redis:', error);
            throw error;
        }
    }
    
    async getCurrentMetrics() {
        try {
            // Get basic counts
            const alertStore = await this.redisClient.hGetAll('emma:alert_store');
            const activeUEs = await this.redisClient.sMembers('emma:active_ues');
            
            // Calculate alerts in last 24h
            const now = new Date();
            const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            
            let alertsIn24h = 0;
            for (const alertJson of Object.values(alertStore)) {
                try {
                    const alert = JSON.parse(alertJson);
                    const alertTime = new Date(alert.sent || alert.created_at);
                    if (alertTime > yesterday) {
                        alertsIn24h++;
                    }
                } catch (e) {
                    // Skip invalid alert data
                }
            }
            
            // Get system status
            const systemStatus = await this.getSystemStatus();
            
            this.systemMetrics = {
                totalAlerts: Object.keys(alertStore).length,
                activeUEs: activeUEs.length,
                alertsInLast24h: alertsIn24h,
                averageDeliveryTime: await this.calculateAverageDeliveryTime(),
                systemStatus: systemStatus.overallStatus,
                componentStatus: systemStatus.components,
                lastUpdated: new Date().toISOString()
            };
            
            return this.systemMetrics;
            
        } catch (error) {
            console.error('Error getting current metrics:', error);
            return this.systemMetrics;
        }
    }
    
    async getRecentAlerts(limit = 50) {
        try {
            const alertStore = await this.redisClient.hGetAll('emma:alert_store');
            const alerts = [];
            
            for (const [alertId, alertJson] of Object.entries(alertStore)) {
                try {
                    const alert = JSON.parse(alertJson);
                    alerts.push({
                        id: alertId,
                        headline: alert.headline || alert.event,
                        severity: alert.severity,
                        urgency: alert.urgency,
                        sent: alert.sent || alert.created_at,
                        status: alert.status,
                        category: alert.category
                    });
                } catch (e) {
                    console.error(`Error parsing alert ${alertId}:`, e);
                }
            }
            
            // Sort by sent time (newest first)
            alerts.sort((a, b) => new Date(b.sent) - new Date(a.sent));
            
            return alerts.slice(0, limit);
            
        } catch (error) {
            console.error('Error getting recent alerts:', error);
            return [];
        }
    }
    
    async getConnectedUEs() {
        try {
            const ueStore = await this.redisClient.hGetAll('emma:ue_store');
            const ues = [];
            
            for (const [ueId, ueJson] of Object.entries(ueStore)) {
                try {
                    const ue = JSON.parse(ueJson);
                    ues.push({
                        id: ueId,
                        status: ue.connectionStatus,
                        location: ue.location,
                        lastSeen: ue.lastSeen,
                        alertsReceived: ue.alertsReceived || 0
                    });
                } catch (e) {
                    console.error(`Error parsing UE ${ueId}:`, e);
                }
            }
            
            return ues;
            
        } catch (error) {
            console.error('Error getting connected UEs:', error);
            return [];
        }
    }
    
    async getSystemStatus() {
        const components = {
            'redis': 'unknown',
            'cap-generator': 'unknown',
            'http-cdn': 'unknown',
            'alert-distributor': 'unknown',
            'ns3-simulator': 'unknown'
        };
        
        // Test Redis
        try {
            await this.redisClient.ping();
            components['redis'] = 'healthy';
        } catch (e) {
            components['redis'] = 'unhealthy';
        }
        
        // Test other services via HTTP health checks
        const healthChecks = [
            { service: 'http-cdn', url: 'http://http-cdn:3000/health' },
            { service: 'alert-distributor', url: 'http://alert-distributor:3001/health' }
        ];
        
        for (const { service, url } of healthChecks) {
            try {
                const response = await fetch(url, { timeout: 5000 });
                components[service] = response.ok ? 'healthy' : 'unhealthy';
            } catch (e) {
                components[service] = 'unhealthy';
            }
        }
        
        // Determine overall status
        const healthyCount = Object.values(components).filter(status => status === 'healthy').length;
        const totalCount = Object.keys(components).length;
        
        let overallStatus;
        if (healthyCount === totalCount) {
            overallStatus = 'healthy';
        } else if (healthyCount > totalCount / 2) {
            overallStatus = 'degraded';
        } else {
            overallStatus = 'unhealthy';
        }
        
        return {
            overallStatus,
            components,
            healthyComponents: healthyCount,
            totalComponents: totalCount
        };
    }
    
    async calculateAverageDeliveryTime() {
        try {
            const distributionLog = await this.redisClient.hGetAll('emma:distribution_log');
            if (Object.keys(distributionLog).length === 0) return 0;
            
            let totalTime = 0;
            let count = 0;
            
            for (const logJson of Object.values(distributionLog)) {
                try {
                    const log = JSON.parse(logJson);
                    if (log.deliveryTime) {
                        totalTime += log.deliveryTime;
                        count++;
                    }
                } catch (e) {
                    // Skip invalid log entries
                }
            }
            
            return count > 0 ? (totalTime / count) : 0;
            
        } catch (error) {
            console.error('Error calculating average delivery time:', error);
            return 0;
        }
    }
    
    handleAlertUpdate(message) {
        try {
            const alert = JSON.parse(message);
            console.log(`📨 Alert update: ${alert.identifier}`);
            
            // Broadcast to all connected clients
            this.io.emit('alert-update', {
                type: 'new-alert',
                alert: {
                    id: alert.identifier,
                    headline: alert.headline || alert.event,
                    severity: alert.severity,
                    urgency: alert.urgency,
                    sent: alert.sent || alert.created_at,
                    category: alert.category
                }
            });
            
            // Update metrics
            this.updateMetricsAndBroadcast();
            
        } catch (error) {
            console.error('Error handling alert update:', error);
        }
    }
    
    handleUEStatusUpdate(message) {
        try {
            const update = JSON.parse(message);
            console.log(`📱 UE status update: ${update.ueId} - ${update.action}`);
            
            // Broadcast to all connected clients
            this.io.emit('ue-update', update);
            
            // Update metrics
            this.updateMetricsAndBroadcast();
            
        } catch (error) {
            console.error('Error handling UE status update:', error);
        }
    }
    
    handleMetricsUpdate(message) {
        try {
            const metrics = JSON.parse(message);
            console.log('📊 Metrics update received');
            
            // Broadcast to all connected clients
            this.io.emit('metrics-update', metrics);
            
        } catch (error) {
            console.error('Error handling metrics update:', error);
        }
    }
    
    async updateMetricsAndBroadcast() {
        try {
            const metrics = await this.getCurrentMetrics();
            this.io.emit('metrics-update', metrics);
        } catch (error) {
            console.error('Error updating and broadcasting metrics:', error);
        }
    }
    
    async sendMetricsUpdate(socket) {
        try {
            const [metrics, alerts, ues, systemStatus] = await Promise.all([
                this.getCurrentMetrics(),
                this.getRecentAlerts(20),
                this.getConnectedUEs(),
                this.getSystemStatus()
            ]);
            
            socket.emit('initial-data', {
                metrics,
                alerts,
                ues,
                systemStatus
            });
            
        } catch (error) {
            console.error('Error sending metrics update:', error);
        }
    }
    
    async start() {
        try {
            const port = process.env.PORT || 3002;
            
            // Setup Redis connection
            await this.setupRedis();
            
            // Start HTTP server
            this.server.listen(port, () => {
                console.log(`📊 EMMA Monitoring Dashboard running on port ${port}`);
                console.log(`🌐 Dashboard URL: http://localhost:${port}`);
            });
            
            // Start periodic metrics updates
            setInterval(() => {
                this.updateMetricsAndBroadcast();
            }, 10000); // Update every 10 seconds
            
            console.log('🚀 Dashboard started successfully');
            
        } catch (error) {
            console.error('❌ Failed to start dashboard:', error);
            process.exit(1);
        }
    }
    
    async stop() {
        console.log('🛑 Shutting down dashboard...');
        
        if (this.server) {
            this.server.close();
        }
        
        if (this.redisClient) {
            await this.redisClient.quit();
        }
        
        if (this.subscriber) {
            await this.subscriber.quit();
        }
        
        console.log('✅ Dashboard stopped');
    }
}

// Start the dashboard
const dashboard = new EmmaDashboard();

// Graceful shutdown
process.on('SIGTERM', async () => {
    await dashboard.stop();
    process.exit(0);
});

process.on('SIGINT', async () => {
    await dashboard.stop();
    process.exit(0);
});

// Start the service
dashboard.start().catch(error => {
    console.error('Failed to start dashboard:', error);
    process.exit(1);
});

module.exports = EmmaDashboard;