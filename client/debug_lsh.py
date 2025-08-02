#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from secure_search_client import SecureSearchTestClient

def test_lsh_consistency():
    """Test if the same text produces the same LSH hashes"""
    
    # Create client
    client = SecureSearchTestClient("http://dummy", "test_api_key")
    
    # Initialize with dummy data (we just want to test LSH locally)
    client.client_id = "test-client"
    
    # Test text
    test_text = "Machine learning algorithms can automatically learn patterns from large datasets without explicit programming."
    
    print(f"Testing LSH consistency for: {test_text[:50]}...")
    
    # Compute LSH hashes multiple times
    for i in range(3):
        vector = client._text_to_vector(test_text)
        hashes = client._compute_lsh_hashes(vector)
        print(f"Attempt {i+1}: {hashes[:5]}")
    
    print("\nTesting similar texts:")
    similar_texts = [
        "Machine learning algorithms can automatically learn patterns from large datasets without explicit programming.",
        "artificial intelligence and machine learning",
        "machine learning and artificial intelligence", 
        "deep learning neural networks"
    ]
    
    vectors = []
    for text in similar_texts:
        vector = client._text_to_vector(text)
        vectors.append((text, vector))
        hashes = client._compute_lsh_hashes(vector)
        print(f"'{text[:30]}...': {hashes[:5]}")
    
    # Check vector similarities
    print("\nVector dot products (cosine similarities):")
    import numpy as np
    for i in range(len(vectors)):
        for j in range(i+1, len(vectors)):
            text1, vec1 = vectors[i]
            text2, vec2 = vectors[j]
            similarity = np.dot(vec1, vec2)
            print(f"'{text1[:20]}...' vs '{text2[:20]}...': {similarity:.3f}")

if __name__ == "__main__":
    test_lsh_consistency()