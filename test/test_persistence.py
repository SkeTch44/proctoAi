
import os
import sys
import requests
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000/api"

def test_persistence():
    # 1. Login as Admin
    logger.info("Logging in as Admin...")
    response = requests.post(f"{BASE_URL}/login", json={
        "username": "admin_ver",
        "password": "password123"
    })
    
    if response.status_code != 200:
        logger.error("Login failed")
        return
        
    token = response.json().get('token')
    headers = {"Authorization": f"Bearer {token}"}
    logger.info("Login successful. Token acquired.")

    # 2. Upload Document
    logger.info("Uploading document...")
    files = {'file': ('test_persistence_doc.docx', open('test/sample_test.docx', 'rb'))}
    
    upload_res = requests.post(
        f"{BASE_URL}/upload_document", 
        files=files, 
        headers=headers
    )
    
    if upload_res.status_code != 200:
        logger.error(f"Upload failed: {upload_res.text}")
        return

    data = upload_res.json()
    doc_id = data.get('doc_id')
    logger.info(f"Upload successful. Doc ID: {doc_id}")
    
    if not doc_id:
        logger.error("No Doc ID returned. RAG persistence likely failed.")
        return

    # 3. Verify Persistence (Get Documents)
    logger.info("Verifying persistence via /api/documents...")
    docs_res = requests.get(f"{BASE_URL}/documents", headers=headers)
    
    if docs_res.status_code != 200:
        logger.error(f"Failed to fetch documents: {docs_res.text}")
        return
        
    documents = docs_res.json()
    found = False
    for doc in documents:
        if doc['doc_id'] == doc_id:
            found = True
            logger.info(f"✓ Document found in DB: {doc['filename']} (ID: {doc['doc_id']})")
            break
            
    if not found:
        logger.error("✗ Document NOT found in DB list!")
    else:
        logger.info("✅ PERSISTENCE TEST PASSED")

if __name__ == "__main__":
    test_persistence()
