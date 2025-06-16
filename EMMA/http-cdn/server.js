const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(morgan('combined'));

// Create alerts directory if it doesn't exist
const alertsDir = path.join(__dirname, 'alerts');
if (!fs.existsSync(alertsDir)) {
    fs.mkdirSync(alertsDir, { recursive: true });
}

// Serve static files from alerts directory
app.use('/alerts', express.static(alertsDir));

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
    const metrics = {
        totalRequests: app.locals.totalRequests || 0,
        activeConnections: app.locals.activeConnections || 0,
        bytesServed: app.locals.bytesServed || 0
    };
    res.json(metrics);
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        error: 'Internal Server Error',
        message: err.message
    });
});

// Start server
const server = app.listen(PORT, () => {
    console.log(`HTTP CDN server running on port ${PORT}`);
});

// Initialize metrics
app.locals.totalRequests = 0;
app.locals.activeConnections = 0;
app.locals.bytesServed = 0;

// Track metrics
app.use((req, res, next) => {
    app.locals.totalRequests++;
    app.locals.activeConnections++;
    
    // Track response size
    const oldWrite = res.write;
    const oldEnd = res.end;
    const chunks = [];
    
    res.write = function(chunk) {
        chunks.push(chunk);
        return oldWrite.apply(res, arguments);
    };
    
    res.end = function(chunk) {
        if (chunk) chunks.push(chunk);
        const body = Buffer.concat(chunks).toString('utf8');
        app.locals.bytesServed += body.length;
        app.locals.activeConnections--;
        oldEnd.apply(res, arguments);
    };
    
    next();
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
}); 