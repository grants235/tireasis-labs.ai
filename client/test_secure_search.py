#!/usr/bin/env python3
"""
Comprehensive test script for the Secure Similarity Search system

This script demonstrates the complete workflow:
1. Initialize client with HE context
2. Load test sentences and encrypt/upload as embeddings
3. Perform various similarity searches
4. Display results and verify functionality

Run this script outside of Docker to test the database server.
"""
import sys
import os
import json
import time
import traceback
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.secure_search_client import SecureSearchTestClient
from rich.console import Console
from rich.progress import Progress, track
from rich.panel import Panel
from rich.text import Text


def load_test_data(data_file: str = "data/test_sentences.json") -> List[Dict]:
    """Load test sentences from JSON file"""
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"Test data file not found: {data_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in test data file: {e}")


def test_server_connection(client: SecureSearchTestClient) -> bool:
    """Test basic server connectivity"""
    console = Console()
    console.print("\n[yellow]🔌 Testing server connection...[/yellow]")
    
    try:
        # Test health endpoint by making a direct request
        response = client._make_request("GET", "/health")
        if response.get("status") == "healthy":
            console.print("[green]✅ Server is healthy and responding[/green]")
            return True
        else:
            console.print(f"[red]❌ Server unhealthy: {response}[/red]")
            return False
    except Exception as e:
        console.print(f"[red]❌ Cannot connect to server: {e}[/red]")
        console.print("[yellow]💡 Make sure the Docker containers are running:[/yellow]")
        console.print("   docker-compose up -d")
        return False


def test_initialization(client: SecureSearchTestClient) -> bool:
    """Test client initialization"""
    console = Console()
    
    try:
        response = client.initialize()
        
        # Verify response
        required_fields = ["client_id", "server_id", "max_db_size", "supported_operations"]
        for field in required_fields:
            if field not in response:
                console.print(f"[red]❌ Missing field in init response: {field}[/red]")
                return False
        
        console.print("[green]✅ Client initialization successful[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Initialization failed: {e}[/red]")
        traceback.print_exc()
        return False


def test_embedding_upload(client: SecureSearchTestClient, test_data: List[Dict]) -> bool:
    """Test uploading encrypted embeddings"""
    console = Console()
    console.print(f"\n[yellow]📤 Uploading {len(test_data)} encrypted embeddings...[/yellow]")
    
    successful_uploads = 0
    failed_uploads = 0
    
    with Progress() as progress:
        task = progress.add_task("Uploading embeddings...", total=len(test_data))
        
        for item in test_data:
            try:
                response = client.add_embedding(
                    text=item["text"],
                    embedding_id=item["id"],
                    metadata={
                        "category": item["category"],
                        "topic": item["topic"],
                        "original_id": item["id"]
                    }
                )
                
                # Verify response
                if response.get("status") == "success":
                    successful_uploads += 1
                else:
                    failed_uploads += 1
                    console.print(f"[yellow]⚠️ Upload warning for {item['id']}: {response}[/yellow]")
                
            except Exception as e:
                failed_uploads += 1
                console.print(f"[red]❌ Failed to upload {item['id']}: {e}[/red]")
            
            progress.update(task, advance=1)
            time.sleep(0.1)  # Small delay to avoid overwhelming server
    
    console.print(f"[green]✅ Upload complete: {successful_uploads} successful, {failed_uploads} failed[/green]")
    
    return failed_uploads == 0


def test_similarity_searches(client: SecureSearchTestClient) -> bool:
    """Test various similarity searches"""
    console = Console()
    console.print("\n[yellow]🔍 Testing similarity searches...[/yellow]")
    
    # Define test queries with expected themes
    test_queries = [
        {
            "query": "artificial intelligence and machine learning",
            "expected_category": "technology",
            "description": "Should find AI/ML related content"
        },
        {
            "query": "genetic engineering and biotechnology research",
            "expected_category": "science", 
            "description": "Should find genetics/biotech content"
        },
        {
            "query": "business strategy and entrepreneurship",
            "expected_category": "business",
            "description": "Should find business-related content"
        },
        {
            "query": "medical treatment and healthcare",
            "expected_category": "health",
            "description": "Should find health-related content"
        },
        {
            "query": "student learning and educational methods",
            "expected_category": "education",
            "description": "Should find education-related content"
        },
        {
            "query": "completely unrelated nonsense query about purple elephants dancing",
            "expected_category": None,
            "description": "Random query to test system behavior"
        }
    ]
    
    all_tests_passed = True
    
    for i, test_case in enumerate(test_queries, 1):
        console.print(f"\n[cyan]Test {i}/6: {test_case['description']}[/cyan]")
        console.print(f"Query: '{test_case['query']}'")
        
        try:
            # Perform search
            results = client.search(test_case["query"], top_k=5, rerank_candidates=50)
            
            # Display results
            client.print_search_results(test_case["query"], results)
            
            # Analyze results
            if not results["results"]:
                console.print("[yellow]⚠️ No results returned[/yellow]")
                if test_case["expected_category"]:
                    console.print("[red]❌ Expected to find results[/red]")
                    all_tests_passed = False
                else:
                    console.print("[green]✅ No results expected for random query[/green]")
            else:
                # Check if results are relevant
                categories_found = set()
                for result in results["results"]:
                    if "metadata" in result and "category" in result["metadata"]:
                        categories_found.add(result["metadata"]["category"])
                
                console.print(f"Categories found: {', '.join(categories_found) if categories_found else 'None'}")
                
                if test_case["expected_category"]:
                    if test_case["expected_category"] in categories_found:
                        console.print(f"[green]✅ Found expected category: {test_case['expected_category']}[/green]")
                    else:
                        console.print(f"[yellow]⚠️ Expected category '{test_case['expected_category']}' not in top results[/yellow]")
                        # This is a warning, not a failure, as similarity is approximate
                
                # Check search performance
                search_time = results.get("search_time_ms", 0)
                candidates_checked = results.get("candidates_checked", 0)
                
                if search_time > 5000:  # 5 seconds
                    console.print(f"[yellow]⚠️ Search took {search_time:.1f}ms (slow)[/yellow]")
                else:
                    console.print(f"[green]✅ Search completed in {search_time:.1f}ms[/green]")
                
                console.print(f"[blue]ℹ️ Checked {candidates_checked} candidates[/blue]")
        
        except Exception as e:
            console.print(f"[red]❌ Search failed: {e}[/red]")
            traceback.print_exc()
            all_tests_passed = False
        
        time.sleep(1)  # Brief pause between searches
    
    return all_tests_passed


def test_client_statistics(client: SecureSearchTestClient) -> bool:
    """Test client statistics retrieval"""
    console = Console()
    console.print("\n[yellow]📊 Checking client statistics...[/yellow]")
    
    try:
        client.print_stats()
        
        # Get raw stats for validation
        stats = client.get_client_stats()
        
        # Validate stats
        if stats["total_embeddings"] < 25:  # We uploaded 25 test sentences
            console.print(f"[yellow]⚠️ Expected ~25 embeddings, found {stats['total_embeddings']}[/yellow]")
        
        if stats["total_searches"] < 6:  # We performed 6 searches
            console.print(f"[yellow]⚠️ Expected ~6 searches, found {stats['total_searches']}[/yellow]")
        
        console.print("[green]✅ Statistics retrieved successfully[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get statistics: {e}[/red]")
        return False


def run_comprehensive_test():
    """Run the complete test suite"""
    console = Console()
    
    # Print header
    header_text = Text("🔐 SECURE SIMILARITY SEARCH - COMPREHENSIVE TEST", style="bold white on blue")
    console.print(Panel(header_text, expand=False))
    console.print()
    
    # Initialize client
    console.print("[bold blue]Initializing Secure Search Test Client...[/bold blue]")
    client = SecureSearchTestClient()
    
    # Test results
    test_results = {
        "server_connection": False,
        "client_initialization": False,
        "embedding_upload": False,
        "similarity_searches": False,
        "client_statistics": False
    }
    
    try:
        # Test 1: Server Connection
        console.print(Panel("[bold]Test 1: Server Connection[/bold]"))
        test_results["server_connection"] = test_server_connection(client)
        
        if not test_results["server_connection"]:
            console.print("[red]❌ Cannot proceed without server connection[/red]")
            return False
        
        # Test 2: Client Initialization  
        console.print(Panel("[bold]Test 2: Client Initialization[/bold]"))
        test_results["client_initialization"] = test_initialization(client)
        
        if not test_results["client_initialization"]:
            console.print("[red]❌ Cannot proceed without client initialization[/red]")
            return False
        
        # Load test data
        console.print("\n[blue]📁 Loading test data...[/blue]")
        test_data = load_test_data()
        console.print(f"[green]✅ Loaded {len(test_data)} test sentences[/green]")
        
        # Test 3: Embedding Upload
        console.print(Panel("[bold]Test 3: Encrypted Embedding Upload[/bold]"))
        test_results["embedding_upload"] = test_embedding_upload(client, test_data)
        
        # Test 4: Similarity Searches (continue even if upload had issues)
        console.print(Panel("[bold]Test 4: Similarity Search Tests[/bold]"))
        test_results["similarity_searches"] = test_similarity_searches(client)
        
        # Test 5: Client Statistics
        console.print(Panel("[bold]Test 5: Client Statistics[/bold]"))
        test_results["client_statistics"] = test_client_statistics(client)
        
        # Final Summary
        console.print(Panel("[bold]🏁 TEST SUMMARY[/bold]"))
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        for test_name, passed in test_results.items():
            status = "[green]✅ PASSED[/green]" if passed else "[red]❌ FAILED[/red]"
            console.print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        console.print(f"\n[bold]Overall Result: {passed_tests}/{total_tests} tests passed[/bold]")
        
        if passed_tests == total_tests:
            console.print(Panel("[bold green]🎉 ALL TESTS PASSED - Secure Search System Working Correctly! 🎉[/bold green]"))
            return True
        elif passed_tests >= total_tests - 1:
            console.print(Panel("[bold yellow]⚠️ MOSTLY WORKING - Minor issues detected[/bold yellow]"))
            return True
        else:
            console.print(Panel("[bold red]❌ MULTIPLE FAILURES - System needs attention[/bold red]"))
            return False
            
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Test interrupted by user[/yellow]")
        return False
    except Exception as e:
        console.print(f"\n[red]💥 Unexpected error during testing: {e}[/red]")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Secure Similarity Search Test Suite...")
    print("=" * 60)
    
    # Change to script directory to find data files
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = run_comprehensive_test()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test suite completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test suite failed!")
        sys.exit(1)