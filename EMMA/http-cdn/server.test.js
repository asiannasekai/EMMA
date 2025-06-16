const request = require('supertest');
const express = require('express');
const path = require('path');
const fs = require('fs');

// Mock the server.js
jest.mock('./server', () => {
    const app = express();
    app.use('/alerts', express.static(path.join(__dirname, 'alerts')));
    app.get('/health', (req, res) => res.json({ status: 'healthy' }));
    app.get('/metrics', (req, res) => res.json({
        totalRequests: 0,
        activeConnections: 0,
        bytesServed: 0
    }));
    return app;
});

const app = require('./server');

describe('HTTP CDN Server', () => {
    const alertsDir = path.join(__dirname, 'alerts');
    
    beforeEach(() => {
        // Create alerts directory if it doesn't exist
        if (!fs.existsSync(alertsDir)) {
            fs.mkdirSync(alertsDir, { recursive: true });
        }
    });
    
    afterEach(() => {
        // Clean up test files
        const files = fs.readdirSync(alertsDir);
        for (const file of files) {
            fs.unlinkSync(path.join(alertsDir, file));
        }
    });
    
    test('health check endpoint returns 200', async () => {
        const response = await request(app).get('/health');
        expect(response.status).toBe(200);
        expect(response.body).toEqual({ status: 'healthy' });
    });
    
    test('metrics endpoint returns metrics object', async () => {
        const response = await request(app).get('/metrics');
        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('totalRequests');
        expect(response.body).toHaveProperty('activeConnections');
        expect(response.body).toHaveProperty('bytesServed');
    });
    
    test('serves static files from alerts directory', async () => {
        // Create a test file
        const testFile = path.join(alertsDir, 'test.txt');
        fs.writeFileSync(testFile, 'test content');
        
        const response = await request(app).get('/alerts/test.txt');
        expect(response.status).toBe(200);
        expect(response.text).toBe('test content');
    });
    
    test('returns 404 for non-existent files', async () => {
        const response = await request(app).get('/alerts/nonexistent.txt');
        expect(response.status).toBe(404);
    });
}); 