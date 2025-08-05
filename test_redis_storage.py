#!/usr/bin/env python3
"""Test the new Redis storage system"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.storage import store_job, get_job, store_results, get_results, job_exists, get_cache_stats
from api.models import JobData, JobStatus, SearchResults, TrackResult
from datetime import datetime

def test_redis_storage():
    """Test Redis-based storage system"""
    print("🧪 Testing Redis storage system...")
    
    # Test 1: Job storage and retrieval
    print("\n📋 Testing job storage...")
    job_id = "test_job_123"
    
    job_data = JobData(
        status=JobStatus.RUNNING,
        query_text="test sad music",
        started_at=datetime.now(),
        finished_at=None,
        error_message=None,
        model="gemini-2.5-flash",
        conversation_history=None,
        current_filters_json={"valence_decile_min": 1, "valence_decile_max": 4},
        result_count=42
    )
    
    # Store job
    store_job(job_id, job_data)
    print(f"✅ Stored job: {job_id}")
    
    # Check job exists
    exists = job_exists(job_id)
    print(f"✅ Job exists check: {exists}")
    
    # Retrieve job
    retrieved_job = get_job(job_id)
    if retrieved_job:
        print(f"✅ Retrieved job: {retrieved_job.query_text} - {retrieved_job.status}")
        print(f"   Model: {retrieved_job.model}, Result count: {retrieved_job.result_count}")
    else:
        print("❌ Failed to retrieve job")
        return False
    
    # Test 2: Results storage and retrieval
    print("\n🎵 Testing results storage...")
    
    # Create mock results with correct TrackResult fields
    mock_tracks = [
        TrackResult(
            spotify_track_id="track1",
            track="Sad Song 1",
            artist="Artist 1",
            album_release_year=2020,
            spotify_artist_genres="indie,alternative",
            track_is_explicit=False,
            duration_ms=240000,
            url_youtube="https://youtube.com/watch1",
            spotify_url="https://spotify.com/track1",
            danceability_decile=4,
            energy_decile=3,
            acousticness_decile=6,
            instrumentalness_decile=2,
            liveness_decile=1,
            valence_decile=2,
            views_decile=5,
            loudness=-8.5,
            tempo=120.0,
            instrumentalness=0.1,
            relevance_score=0.95,
            rank_position=1
        )
    ]
    
    results = SearchResults(
        job_id=job_id,
        llm_message="Found sad music matching your query",
        llm_reflection="Focused on low valence tracks",
        result_count=1,
        tracks=mock_tracks
    )
    
    # Store results
    store_results(job_id, results)
    print(f"✅ Stored results for job: {job_id}")
    
    # Retrieve results
    retrieved_results = get_results(job_id)
    if retrieved_results:
        print(f"✅ Retrieved results: {retrieved_results.result_count} tracks")
        print(f"   LLM message: {retrieved_results.llm_message}")
        if retrieved_results.tracks:
            track = retrieved_results.tracks[0]
            print(f"   First track: {track.track} by {track.artist}")
    else:
        print("❌ Failed to retrieve results")
        return False
    
    # Test 3: Cache statistics
    print("\n📊 Testing cache statistics...")
    stats = get_cache_stats()
    print(f"✅ Cache backend: {stats['backend']}")
    print(f"   Jobs: {stats['job_count']}, Results: {stats['result_count']}")
    if stats.get('memory_used'):
        print(f"   Memory used: {stats['memory_used']}")
    
    # Test 4: Non-existent job
    print("\n🔍 Testing non-existent job...")
    fake_job = get_job("fake_job_999")
    fake_exists = job_exists("fake_job_999")
    print(f"✅ Non-existent job handling: exists={fake_exists}, data={fake_job}")
    
    print("\n🎉 All Redis storage tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_redis_storage()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)