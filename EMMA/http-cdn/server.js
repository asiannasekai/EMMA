const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 8080;

app.use(cors());
app.use('/alerts', express.static('alerts'));

app.listen(PORT, () => {
  console.log(`HTTP CDN running on port ${PORT}`);
}); 