import pandas as pd
import numpy as np
from typing import Dict, Any, List
from api.models import TrackResult, SearchResults

class MusicService:
    def __init__(self):
        self.main_df = None
        self.deciles_features_list = ['danceability', 'energy','acousticness', 'liveness', 'valence','views'] #, 'speechiness'
        self.direct_use_features = ['loudness','tempo','duration_ms','instrumentalness']
        self.minmax_only_features = ['album_release_year','track_is_explicit']
        
    def initialize(self, data_path: str = 'data/main_df.csv'):
        """Load and initialize the music dataset"""
        self.main_df = pd.read_csv(data_path)
        
    def search(self, filters_json: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters and scoring, return results and summary"""
        # Apply filters to get boolean mask
        combined_filter = self.llm_to_filters(filters_json)
        
        # Get scored results dataframe
        results_df = self.filters_to_results_df(combined_filter, filters_json)
        
        # Create summary for LLM refinement
        summary = self.make_summary(results_df)
        
        return {
            "results": results_df,
            "summary": summary
        }
    
    def llm_to_filters(self, response_json: Dict[str, Any]) -> pd.Series:
        """Convert LLM response to pandas boolean filter (from notebook)"""
        filters_object = response_json
        combined_filter = pd.Series(True, index=self.main_df.index)
        
        for feature in self.deciles_features_list:
            if filters_object[feature+'_min_decile'] is not None and filters_object[feature+'_max_decile'] is not None:
                combined_filter = combined_filter & \
                    (self.main_df[feature+'_decile'] >= filters_object[feature+'_min_decile']) & \
                    (self.main_df[feature+'_decile'] <= filters_object[feature+'_max_decile'])
        
        for feature in self.direct_use_features + self.minmax_only_features:
            if filters_object[feature+'_min'] is not None and filters_object[feature+'_max'] is not None:
                combined_filter = combined_filter & \
                    (self.main_df[feature] >= filters_object[feature+'_min']) & \
                    (self.main_df[feature] <= filters_object[feature+'_max'])

        if filters_object['spotify_artist_genres_include_any'] and len(filters_object['spotify_artist_genres_include_any']) > 0:
            included_terms = self._split_terms(filters_object['spotify_artist_genres_include_any'])
            if included_terms:
                combined_filter = combined_filter & \
                    self.main_df['spotify_artist_genres'].fillna("").apply(lambda g: any(term in g for term in included_terms))
        
        if filters_object['spotify_artist_genres_exclude_any'] and len(filters_object['spotify_artist_genres_exclude_any']) > 0:
            excluded_terms = self._split_terms(filters_object['spotify_artist_genres_exclude_any'])
            if excluded_terms:
                combined_filter = combined_filter & \
                    self.main_df['spotify_artist_genres'].fillna("").apply(lambda g: not any(term in g for term in excluded_terms))
        
        return combined_filter
    
    def filters_to_results_df(self, combined_filter: pd.Series, filters_object: Dict[str, Any]) -> pd.DataFrame:
        """Convert filters to results dataframe with relevance scoring (from notebook)"""
        GENRE_BOOST_POINTS = 50
        
        filtered_results = self.main_df[combined_filter].copy()

        # Build relevance score using deciles for scoring
        relevance_score = pd.Series(0, index=filtered_results.index)
        
        # Add decile-based scoring
        for feature in self.deciles_features_list:
            if filters_object[feature+'_decile_weight']:
                relevance_score += filtered_results[feature+'_decile'] * filters_object[feature+'_decile_weight']
        
        # Add direct use features scoring (using deciles for scoring)
        for feature in self.direct_use_features:
            if filters_object[feature+'_decile_weight']:
                relevance_score += filtered_results[feature+'_decile'] * filters_object[feature+'_decile_weight']
        
        filtered_results['relevance_score'] = relevance_score

        boost_terms = self._split_terms(filters_object.get('spotify_artist_genres_boosted',''))

        if boost_terms:
            filtered_results["genre_boost_hits"] = filtered_results["spotify_artist_genres"].fillna("").apply(
                lambda g: sum(term in g for term in boost_terms)
            )
            filtered_results["relevance_score"] += GENRE_BOOST_POINTS * filtered_results["genre_boost_hits"]
        
        return filtered_results
    
    def make_summary(self, df: pd.DataFrame, top_k: int = 5) -> Dict[str, Any]:
        """Create summary of results for refinement (exact copy from notebook)"""
        TOP_K = top_k
        EXAMPLE_COLS = [
            "spotify_track_id", "track", "artist","spotify_artist_genres",
            'danceability_decile', 'energy_decile', 'acousticness_decile', 'instrumentalness_decile', 'liveness_decile', 'valence_decile','views_decile', #'speechiness_decile',
            'loudness', "tempo", "instrumentalness",
            "album_release_year", "duration_ms", "track_is_explicit",
            "relevance_score",
            "url_youtube"
        ]
        
        top = df.sort_values("relevance_score", ascending=False).head(top_k).copy()
        if "description" in df.columns:
            top["description_short"] = top["description"].apply(self._truncate)

        summary = {}
        if int(len(df)) == 0:
            summary = {
                "result_count": int(len(df))
            }
        else:
            top_examples = top[EXAMPLE_COLS + (["description_short"] if "description_short" in top else [])] \
                .to_dict(orient="records")
            summary = {
                "result_count": int(len(df)),
                "top_examples": top_examples,
                "score_stats": {
                    "min": float(df["relevance_score"].min()),
                    "median": float(df["relevance_score"].median()),
                    "max": float(df["relevance_score"].max())
                },
                "year_range": {
                    "min": int(df["album_release_year"].min()),
                    "max": int(df["album_release_year"].max())
                },
                "top_genres_found": (
                    df["spotify_artist_genres"].str.split(",")
                      .explode()
                      .str.strip()
                      .value_counts()
                      .head(5)
                      .index.tolist()
                )
            }
        return summary
    
    def convert_to_api_results(self, results_df: pd.DataFrame, filters_json: Dict[str, Any], job_id: str) -> SearchResults:
        """Convert pandas results to API response format"""
        # Sort by relevance and take top 150 for API response
        top_results = results_df.sort_values("relevance_score", ascending=False).head(150)
        
        tracks = []
        for idx, (_, row) in enumerate(top_results.iterrows()):
            track = TrackResult(
                spotify_track_id=row["spotify_track_id"],
                track=row["track"],
                artist=row["artist"],
                album_release_year=int(row["album_release_year"]),
                spotify_artist_genres=str(row.get("spotify_artist_genres", "")) if pd.notna(row.get("spotify_artist_genres")) else "",
                track_is_explicit=bool(row["track_is_explicit"]),
                duration_ms=int(row["duration_ms"]),
                url_youtube=row.get("url_youtube"),
                spotify_url=f"https://open.spotify.com/track/{row['spotify_track_id']}",
                danceability_decile=int(row["danceability_decile"]),
                energy_decile=int(row["energy_decile"]),
                #speechiness_decile=int(row["speechiness_decile"]),
                acousticness_decile=int(row["acousticness_decile"]),
                instrumentalness_decile=int(row["instrumentalness_decile"]),
                liveness_decile=int(row["liveness_decile"]),
                valence_decile=int(row["valence_decile"]),
                views_decile=int(row["views_decile"]),
                views=int(row["views"]) if pd.notna(row.get("views")) else None,
                loudness=float(row["loudness"]),
                tempo=float(row["tempo"]),
                instrumentalness=float(row["instrumentalness"]),
                relevance_score=float(row["relevance_score"]),
                rank_position=idx + 1
            )
            tracks.append(track)
        
        return SearchResults(
            job_id=job_id,
            result_count=len(results_df),
            tracks=tracks,
            llm_message=filters_json.get("user_message"),
            llm_reflection=filters_json.get("reflection")
        )
    
    def _split_terms(self, s: str) -> List[str]:
        """Split comma-separated terms"""
        return [t.strip() for t in s.split(",")] if s else []
    
    def _truncate(self, s, n: int = 120):
        """Truncate string to n characters (from notebook)"""
        return (s[:n] + "…") if isinstance(s, str) and len(s) > n else s