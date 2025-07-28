# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Soundbymood is a demo project to showcase a new idea for music search/ranking/retrieval. Instead of searching for particular songs or artists, you can specify the mood or vibe you're going for and an LLM will help you filter a dataset that's sourced from Spotify API and Youtube data, including Spotify's audio analysis featureset for musical character. This could be helpful for content creators for film, TV, or video games, that need to find song selections to go with specific scenes.

## User flow
The user arrives on the landing page. The landing page is extremely minimal.

First the user can choose an example search query from a menu of 5. Show these as tabs in one row, each with an icon and label (Period drama, Millenial dance party, Brooding electro, OG rap, 1970s Nostalgia), plus a 6th tab that let's them write their own.

Next they can see the more full fledged prompt in the input box if they chose an example, or write their own in the input box. 

They click Submit, which triggers a request to the back end. On the back end the request is sent to an LLM for conversion to a filter set on the features in the dataset, the LLM can do up to 3 refinement passes to reach a target number of results, and then returns the results, including their features, spotify and youtube URLs.

The user can browse the results, and sort them by relevance, latest, popularity, and duration. Each result should have a title, subheader showing release date, genres in tags, and an explicit lyrics flag. Below, clear calls to action to visit Youtube and Spotify to listen with the appropriate links, and a Youtube video embed. Below, the user can see rankings/scores for key features. The user can then continue to chat with the LLM, to refine the results, or restart a new search.

## Folder structure
**soundbymood** - A new project with the following structure:
- `api/` - Backend Python API service. Uses FastAPI.
- `frontend/` - Frontend react application. Uses Vite for dev and build tooling. Use Tailwind css and tailwind icons.
- `data/` - Data files and datasets containing music metadata.
- `notebooks/` - Jupyter notebooks containing the original prototype/proof of concept.

## Architecture
The prototype Python notebook for this project is in the "notebooks" folder, titled music-exploration. It already provides code that does the core backend capability, and includes simple HTML to show results. Claude or AI should not make any changes to these files, but read them and use them as guides.

The API backend should be a Python FastAPI project. It should have a few endpoints:
POST /search: accept the user's initial search query, return a job_id, and then asyncronously kick off the LLM call and refinement passes
GET /jobs/{id}: return the status of the search job id, when it's processing return things like the refinement step, when it's complete return the LLM message and the results
POST /refine: enable the user to continue chatting with the LLM to refine results

Constraints: for now just store the jobs in a big JOB_STORE dictionary, and RESULT_STORE dictionary. We will add database persistence later.

JOB_STORE dictionary should have keys like:
{
    status: enum 'queued','running','done','error','canceled',
    query_text: string,
    message_history: array of strings,
    filters_json: json with filter set,
    result_count: integer,
    started_at: timestamp,
    finished_at: timestamp
}

RESULT_STORE dictionary should have keys like:
{
    search_job_id: uuid,
    rank_position: integer,
    track_id: string, foreign key to the spotify track id in the csv dataset,
    relevance: float,
}

The front end should be a react app, relying on vite for build/dev tooling, and using tailwind css and icons.
Component tree should be something like:
- Landing page
    - Prompt area
        - Example prompt tabs band
            - Example prompt tab
        - Prompt input text and submit button
    - Results area component
        - Search results and controls row
            - LLM message reply
            - Result count
            - Sort options
        - Results body
            - Result
    - Continued chat

## Development Commands

*To be populated once project is scaffolded*

