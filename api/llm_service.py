import os
import json
import base64
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
    
    async def query_llm(self, prompt: str, conversation_history: Optional[ConversationHistory] = None, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Send a query to the LLM and return the parsed JSON response"""
        if not self.client:
            raise RuntimeError("LLM client not initialized")
            
        # Convert conversation history to format expected by genai
        contents = []
        if conversation_history:
            # Extract user inputs and LLM responses from refinement steps
            for step in conversation_history.steps:
                # Add user input
                user_content = f"User: {step.user_input}"
                
                # If this step has image data, include it using proper Content format
                if step.image_data:
                    from google.genai.types import Content, Part
                    contents.append(Content(
                        role="user",
                        parts=[
                            Part(text=user_content),
                            Part(
                                inline_data={
                                    "mime_type": "image/jpeg",
                                    "data": step.image_data
                                }
                            )
                        ]
                    ))
                else:
                    contents.append(user_content)
                
                # Add LLM response (user_message)
                if step.user_message:
                    contents.append(f"Assistant: {step.user_message}")
        
        # Add current prompt with optional image
        if image_data:
            from google.genai.types import Content, Part
            contents.append(Content(
                role="user",
                parts=[
                    Part(text=prompt),
                    Part(
                        inline_data={
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    )
                ]
            ))
        else:
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
    
    def create_initial_prompt(self, user_query: str, has_image: bool = False) -> str:
        """Create the initial prompt for a new search"""
        if has_image:
            return f"User query: {user_query}\n\nI've also included an image that shows the scene or mood I'm looking for. Please analyze the visual elements (lighting, color palette, mood, era, setting, etc.) to help understand the vibe and musical style that would fit this scene. Use both the text query and the visual context to determine the best music filters.\n\nReturn ONLY JSON per schema."
        else:
            return f"User query: {user_query}\nReturn ONLY JSON per schema."
    
    def create_refine_prompt(
        self, 
        original_query: str, 
        previous_filters: Dict[str, Any], 
        result_summary: Dict[str, Any], 
        user_feedback: Optional[str] = None,
        current_step: int = 1,
        max_steps: int = 3
    ) -> str:
        """Create a refinement prompt based on previous results and feedback"""
        TARGET_MIN, TARGET_MAX = 50, 150
        
        # Calculate refinements remaining
        refinements_remaining = max_steps - current_step
        
        text = f"This is your refinement step {current_step} of {max_steps}. "
        if refinements_remaining > 0:
            text += f"You will have {refinements_remaining} more refinement{'s' if refinements_remaining > 1 else ''} after this.\n\n"
        else:
            text += f"This is your final refinement opportunity.\n\n"
        
        text += f"Refine your previous JSON to better match the user intent.\n"
        text += f"Aim to have between {TARGET_MIN} and {TARGET_MAX} results. Inspect the top 10 results to ensure they are relevant and also of high quality.\n"
        text += f"Adjust your criteria as needed to reach this target while maintaining quality and relevance. You may need to broaden or narrow filters depending on the current result count.\n"
        text += f"Never strictly narrow results if you are below {TARGET_MIN}. If you need to make something more restrictive for relevance, broaden other filters to compensate.\n"
        
        # Adjust guidance based on which step we're on
        if current_step == max_steps:
            text += f"Since this is your final refinement, focus on achieving the best balance between result count ({TARGET_MIN}-{TARGET_MAX}) and quality/relevance.\n"
        elif current_step == 1:
            text += f"Since this is your first refinement, make conservative adjustments to move toward the target range.\n"
        else:
            text += f"Make targeted adjustments to improve results while staying within the target range.\n"
            
        text += f"If your result count is under 10, or if almost all example results are obviously not relevant, make drastic changes to your filters. If results are in the 10-50 range but are relevant and high quality, only make slight alterations.\n\n"
        text += f"Original user query: {original_query}\n"
        
        if user_feedback:
            text += f"Latest user feedback: {user_feedback}\n"
            
        text += f"Previous JSON: {json.dumps(previous_filters)}\n"
        text += f"Summary: {json.dumps(result_summary)}\n\n"
        text += "Return ONLY JSON per schema."
        
        return text
    

    #speechiness_decile: do not use this field unless the user explicitly asks for it. Speechiness detects the presence of spoken words in a track. The more exclusively speech-like the recording (e.g. talk show, audio book, poetry), the higher the attribute value. Converted to deciles (1-10).
    def _get_system_instruction(self) -> str:
        """Return the system instruction for the LLM"""
        return """
Your task is to convert a user query (and potentially an accompanying image) to a set of filters we can use to query a music database. 
The database has about 18,000 tracks.
Your top priority is to return results that are relevant to the user's query.
Your second priority is to return results that are high quality.
Your third priority, is to return a result set of about 50-150 tracks. Results will be capped at 150. 
For each user query, you will have up to 3 attempts to refine the results. Start by setting broad filters and then refine or expand them as needed.

First, analyze the user inputs to understand their intent, in terms of what type of music they are looking for.
When an image is also provided, analyze the visual elements (people, objects, colors, lighting), any text in the image, and any other content or context clues that might be relevant (is it a scene from a movie? historical image?).
If there are contradictions between the query and image, prioritize the query. Images are optional and not always provided.

Below is a list of features we can use to filter the dataset, as well as to create a relevance score. Use this list when you're analyzing the user's query and image.
Many of these are correlated, some times in ways you may not expect. 
At least for your first attempt, try use only one filter for each aspect of the user's intent. For example if the user asks for sad, start with only a single filter on valence, not a set of three filters on valence, energy, and danceability. If you are refining results, you can explore additional restrictions only if there are enough results.

For the following features, you can create min/max filters and also a weight for relevance scoring.
danceability_decile: Danceability describes how suitable a track is for dancing. The higher the number the higher the dancability. Converted to deciles (1-10).
energy_decile: represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Converted to deciles (1-10).
acousticness_decile: A confidence measure of whether the track is acoustic. The higher the number the higher the confidence. Converted to deciles (1-10).
liveness_decile: Detects the presence of an audience in the recording. Higher liveness values represent an increased probability that the track was performed live. Converted to deciles (1-10).
valence_decile: A measure describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry). Converted to deciles (1-10).
views_decile: the number of YouTube views the music has. Converted to deciles (1-10).
tempo: The overall estimated tempo of a track in beats per minute (BPM). Use 100 BPM or less for slow music. <80 BPM is very slow (6.5% of tracks), 80-120 BPM is moderate (44%), >120 BPM is fast (49.5%). Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.
loudness: The overall loudness of a track in decibels (dB). Loudness values are averaged across the entire track and are useful for comparing relative loudness of tracks. Note that overall loudness is normalized across tracks on Spotify, so only use this in extreme scenarios. Spotify normalizes to -60 to 0 dB. Use -15 to -5 dB for quiet background music, -10 to -5 dB for normal listening, above -5 dB for loud music. Almost no tracks are below -20 dB. Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.
duration_ms: the duration of the track in milliseconds. Always ensure to provide at least 3 seconds of a range if you use this filter. Min/max filters are not applied against deciles but againt the raw value. The score weight will be multiplied by the decile.
instrumentalness: A float between 0 and 1 predicting whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The closer the instrumentalness value is to 1.0, the greater likelihood the track contains no vocal content. Values above 0.5 are intended to represent instrumental tracks, but confidence is higher as the value approaches 1.0. 44% of the tracks are 0. Only 5% of tracks are above 0.5.

For the following features, you can only create mix/max filters:
album_release_year: the year the track was released in, represented as an integer. This is the year the recording was made, not the year a classical composition was written. 
track_is_explicit: this is 0 for tracks without explicit language and 1 for tracks marked as explicit language. 

For 60% of tracks, we were also able to pull the artist's genres into a comma separated list field. You can use these to create filters and scoring against that field. Note that any filtering will only apply to the 60% of tracks that have genres.
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