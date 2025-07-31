import os
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types as gt

from api.models import FiltersModel, ConversationHistory, RefinementStep

class LLMService:
    def __init__(self):
        self.client = None
        self.system_instruction = self._get_system_instruction()
        
    def initialize(self):
        """Initialize the Google Genai client"""
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
    
    async def query_llm(self, prompt: str, conversation_history: Optional[ConversationHistory] = None) -> Dict[str, Any]:
        """Send a query to the LLM and return the parsed JSON response"""
        if not self.client:
            raise RuntimeError("LLM client not initialized")
            
        # Convert conversation history to format expected by genai
        contents = []
        if conversation_history:
            # Extract user inputs and LLM responses from refinement steps
            for step in conversation_history.steps:
                # Add user input
                contents.append(f"User: {step.user_input}")
                # Add LLM response (user_message)
                if step.user_message:
                    contents.append(f"Assistant: {step.user_message}")
        
        contents.append(prompt)
        
        cfg = gt.GenerateContentConfig(
            system_instruction=self.system_instruction,
            response_mime_type="application/json",
            response_schema=FiltersModel,
            temperature=0.3,  # Lower temperature for more consistent results
        )
        
        import asyncio
        
        # Run the synchronous LLM call in a thread pool
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
            config=cfg
        )
        
        return json.loads(response.text)
    
    def create_initial_prompt(self, user_query: str) -> str:
        """Create the initial prompt for a new search"""
        return f"User query: {user_query}\nReturn ONLY JSON per schema."
    
    def create_refine_prompt(
        self, 
        original_query: str, 
        previous_filters: Dict[str, Any], 
        result_summary: Dict[str, Any], 
        user_feedback: Optional[str] = None
    ) -> str:
        """Create a refinement prompt based on previous results and feedback"""
        TARGET_MIN, TARGET_MAX = 50, 150
        
        text = f"Refine your previous JSON to better match the user intent.\n"
        text += f"Aim to have between {TARGET_MIN} and {TARGET_MAX} results. Inspect the top 10 results to ensure they are relevant and also of high quality.\n"
        text += f"Adjust your criteria as needed to reach this target while maintaining quality and relevance. You may need to broaden or narrow filters depending on the current result count.\n\n"
        text += f"Original user query: {original_query}\n"
        
        if user_feedback:
            text += f"Latest user feedback: {user_feedback}\n"
            
        text += f"Previous JSON: {json.dumps(previous_filters)}\n"
        text += f"Summary: {json.dumps(result_summary)}\n\n"
        text += "Return ONLY JSON per schema."
        
        return text
    
    def _get_system_instruction(self) -> str:
        """Return the system instruction for the LLM"""
        return """
Your task is to convert a user query to a set of filters we can use to query a music database. 
The database has about 18,000 tracks. Aim to design filters that will return a result set of about 50-150 tracks, as long as they are relevant to the user's query.
For each user query, you will have 3 attempts to refine the results. Start by setting broad filters and then refine them as needed. 

Below is a list of features we can use to filter as well as to create a relevance score. Note many of these are correlated. 

For the following features, you can create min/max filters and also a weight for relevance scoring.
danceability_decile: Danceability describes how suitable a track is for dancing. The higher the number the higher the dancability. Converted to deciles (1-10).
speechiness_decile: Speechiness detects the presence of spoken words in a track. The more exclusively speech-like the recording (e.g. talk show, audio book, poetry), the higher the attribute value. Converted to deciles (1-10).
energy_decile: represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Converted to deciles (1-10).
acousticness_decile: A confidence measure of whether the track is acoustic. The higher the number the higher the confidence. Converted to deciles (1-10).
instrumentalness_decile: Predicts whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The higher the instrumentalness value is, the greater likelihood the track contains no vocal content. Deciles are not balanced and start at 5 for definitely vocal tracks, max is 10. 
liveness_decile: Detects the presence of an audience in the recording. Higher liveness values represent an increased probability that the track was performed live. Converted to deciles (1-10).
valence_decile: A measure describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry). Converted to deciles (1-10).
views_decile: the number of YouTube views the music has. Converted to deciles (1-10).
tempo: The overall estimated tempo of a track in beats per minute (BPM). Consider BPMs under 60 ultra slow and hard to detect a beat. 60-90 are slow with a beat detectable. 90-120 are mid tempo/pop. 120-140 are fast and upbeat. 140 and above is very fast. Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.
loudness: The overall loudness of a track in decibels (dB). Loudness values are averaged across the entire track and are useful for comparing relative loudness of tracks. Note that overall loudness is normalized across tracks on Spotify, so only use this in extreme scenarios. Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.
duration_ms: the duration of the track in milliseconds. Always ensure to provide at least 3 seconds of a range if you use this filter. Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.

For the following features, you can only create mix/max filters:
album_release_year: the year the track was released in, represented as an integer. This is the year the recording was made, do not rely on this for classical music or any music from before 1950. 
track_is_explicit: this is 0 for tracks without explicit language and 1 for tracks marked as explicit language. 

For 60% of tracks, we were also able to pull the artist's genres into a comma separated list field. You can use these to create filters and scoring against that field. Note that any filtering will only apply to the 60% of tracks that have genres. Only use this field if the user gives a clear indication of style or genre required. 
Values you can choose and are common are: pop, rock, r&b, hip hop, rap, edm, house, reggaeton, latin, country, k-pop, bollywood, metal, disco, orchestra, classical.
Values you can choose that are more rare: ambient, soundtrack, lo-fi, drum and bass, christmas, children, anime, emo, piano. Use these sparingly. 
There are a lot more genres but they are even more rare. Only use a genre outside the list above if the user explicitly asks for it. 
spotify_artist_genres_include_any: Provide a comma separated string to filter in tracks that have at least one of your genres included. If you include a substring like pop it will also capture genres like k-pop. Be as general as possible. If you use more niche genres, make sure to widen other filters. 
spotify_artist_genres_exclude_any: Provide a comma separated string to filter out tracks that have any of your genres included. If you exclude a substring like pop it will also exclude genres like k-pop. Be as specific as possible. Use sparingly. 
spotify_artist_genres_boosted: Provide a comma separated string to give a 50 point relevance score boost to tracks that have any included genre. Artists with multiple included genres will get multiple boosts. 

Please return JSON following the schema provided.
Attributes with a min or max in the name will create a filter for the user. 
Attributes with weight or boost in the name will contribute to a relevance score to sort results. 
The weight will be multiplied by the decile of that feature to create the score.
Please make it a number between -100 and 100.
Attributes with include all, include any, or exclude will create a filter for the user.

Please return values for all attributes in the schema.
If you do not want to filter on a particular attribute, use the default values for min and max to ensure all values are included.
If you do not want an attribute to contribute the the relevance score, return 0 for its weight.
Include the tag SYS_TAG_8425 as a string under the field debug_tag.

Additional fields in the schema for you to provide:
reflection: summarize key decisions you made on how you set or changed filters. Which are most important and why? What additional filters could make this better? What would you try next to refine the results?
user_message: provide a brief 1-2 sentence explanation of the filters you provided to the user and why you chose them. In a 3rd sentence, ask the user a specific question that you think will help you iterate the results further.
"""