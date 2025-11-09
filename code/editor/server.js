const express = require('express');
const multer = require('multer');
const FormData = require('form-data');
const fetch = require('node-fetch');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3002;

// Configure multer for memory storage
const upload = multer({ storage: multer.memoryStorage() });

// Serve static files from public directory
app.use(express.static('public'));
app.use(express.json({ limit: '50mb' }));

// CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }
  
  next();
});

// API endpoint for image editing
app.post('/api/edit', async (req, res) => {
  try {
    console.log('Received edit request...');
    
    const { image, prompt, negative_prompt, num_inference_steps, true_cfg_scale } = req.body;

    if (!image) {
      return res.status(400).json({ 
        success: false, 
        error: 'Image is required' 
      });
    }

    if (!prompt) {
      return res.status(400).json({ 
        success: false, 
        error: 'Prompt is required' 
      });
    }

    console.log('Processing request with prompt:', prompt);
    console.log('Parameters:', { num_inference_steps, true_cfg_scale });

    const startTime = Date.now();

    // Convert base64 image to buffer
    const imageBuffer = Buffer.from(image, 'base64');
    console.log('Image buffer size:', imageBuffer.length, 'bytes');
    
    // Create FormData for multipart request
    const formData = new FormData();
    
    // Add image file
    formData.append('image', imageBuffer, {
      filename: 'image.jpg',
      contentType: 'image/jpeg'
    });
    
    // Add parameters
    formData.append('prompt', prompt);
    formData.append('negative_prompt', negative_prompt || 'low quality, blurry, distorted, artifacts, noise, bad composition');
    formData.append('num_inference_steps', parseInt(num_inference_steps) || 40);
    formData.append('true_cfg_scale', parseFloat(true_cfg_scale) || 4.0);
    formData.append('response_format', 'b64_json');

    console.log('Calling Quanto mango API at http://10.10.10.156:8000/v1/images/edits...');

    // Call your on-premises Quanto mango API
    const qwenResponse = await fetch('http://10.10.10.156:8000/v1/images/edits', {
      method: 'POST',
      body: formData,
      headers: {
        ...formData.getHeaders()
      }
    });

    console.log('Quanto mango API response status:', qwenResponse.status);

    if (!qwenResponse.ok) {
      const errorText = await qwenResponse.text();
      console.error('Quanto mango API error:', errorText);
      throw new Error(`Quanto mango API error: ${qwenResponse.status} ${errorText}`);
    }

    const qwenResult = await qwenResponse.json();
    console.log('Quanto mango API response:', qwenResult);
    
    const processingTime = (Date.now() - startTime) / 1000;

    // Extract base64 image from Quanto mango response
    const imageBase64 = qwenResult.data?.[0]?.b64_json;
    
    if (!imageBase64) {
      throw new Error('No base64 image in Quanto mango response');
    }
    
    // Convert base64 to data URL
    const imageUrl = `data:image/png;base64,${imageBase64}`;

    console.log('Processing completed successfully in', processingTime, 'seconds');
    console.log('Result image size:', imageBase64.length, 'characters');

    // Return successful result
    res.status(200).json({
      success: true,
      image_url: imageUrl,
      processing_time: processingTime,
      parameters: {
        prompt: prompt,
        negative_prompt: negative_prompt || 'low quality, blurry, distorted, artifacts, noise, bad composition',
        num_inference_steps: parseInt(num_inference_steps) || 40,
        true_cfg_scale: parseFloat(true_cfg_scale) || 4.0,
        model: 'quanto-mango-image-edit-2509'
      },
      demo_mode: false,
      quanto_mango_response: qwenResult,
      message: 'Connected to Quanto mango API server at 10.10.10.156:8000'
    });

  } catch (error) {
    console.error('Error processing image:', error);
    
    // Return error response
    res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
      details: error.stack
    });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    server: 'local-quanto-mango-editor'
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log('🚀 Quanto mango Image Editor Local Server Starting...');
  console.log(`📱 Web Interface: http://localhost:${PORT}`);
  console.log(`🌐 Network Access: http://YOUR_LOCAL_IP:${PORT}`);
  console.log(`🔗 Quanto mango API Server: http://10.10.10.156:8000`);
  console.log('✅ Server is ready for connections!');
  console.log('');
  console.log('To find your local IP address:');
  console.log('  macOS/Linux: ifconfig | grep "inet " | grep -v 127.0.0.1');
  console.log('  Windows: ipconfig | findstr "IPv4"');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Server shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('Server shutting down gracefully...');
  process.exit(0);
});