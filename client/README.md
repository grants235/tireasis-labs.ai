# Secure Search Test Client

This test client demonstrates the complete secure similarity search workflow using mock encryption to verify that the database server is working correctly.

## Features

- **Mock Homomorphic Encryption**: Simulates encrypted embeddings for testing
- **LSH Hash Computation**: Real locality-sensitive hashing for similarity search
- **Comprehensive Testing**: Full workflow from initialization to search results
- **Rich UI**: Beautiful terminal output with progress bars and tables

## Quick Start

### 1. Install Dependencies

```bash
# From the client directory
pip install -r requirements.txt
```

### 2. Start Database Server

Make sure the Docker containers are running:

```bash
# From the app directory
docker-compose up -d
```

### 3. Run Test Script

```bash
python test_secure_search.py
```

## What the Test Does

1. **🔌 Server Connection**: Verifies the database server is healthy
2. **🚀 Client Initialization**: Establishes HE context with server
3. **📤 Embedding Upload**: Encrypts and uploads 25 test sentences 
4. **🔍 Similarity Search**: Performs 6 different search queries
5. **📊 Statistics Check**: Verifies client stats and usage metrics

## Test Data

The test uses 25 carefully crafted sentences across 5 categories:
- **Technology**: AI, machine learning, cryptography
- **Science**: Neuroscience, genetics, physics  
- **Business**: Entrepreneurship, marketing, finance
- **Health**: Wellness, mental health, telemedicine
- **Education**: E-learning, STEM, pedagogy

## Expected Output

```
🔐 SECURE SIMILARITY SEARCH - COMPREHENSIVE TEST
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔐 SECURE SIMILARITY SEARCH - COMPREHENSIVE TEST           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ Server is healthy and responding
✅ Client initialization successful
✅ Upload complete: 25 successful, 0 failed
✅ Search completed in 45.2ms
✅ Statistics retrieved successfully

🎉 ALL TESTS PASSED - Secure Search System Working Correctly! 🎉
```

## Architecture

The test client simulates a real secure search client by:

- **Generating mock encrypted vectors** using deterministic hashing
- **Computing real LSH hashes** for similarity search
- **Simulating decryption** of encrypted similarity scores
- **Testing all API endpoints** comprehensively

## Troubleshooting

### "Cannot connect to server"
- Ensure Docker containers are running: `docker-compose up -d`
- Check server health: `curl http://localhost:8001/health`

### "Import errors"
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: Python 3.8+ required

### "No results found"
- This is normal for unrelated queries
- Check that embeddings were uploaded successfully

## Files

- `test_secure_search.py` - Main test script
- `src/secure_search_client.py` - Client implementation  
- `data/test_sentences.json` - Test dataset
- `requirements.txt` - Python dependencies