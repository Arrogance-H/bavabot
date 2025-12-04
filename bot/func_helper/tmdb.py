"""
TMDB API helper module for movie and TV show search
"""
import aiohttp
import asyncio
from typing import List, Dict, Tuple, Optional
from bot import LOGGER, tmdb


class TMDBService:
    def __init__(self):
        self.api_key = tmdb.api_key
        self.base_url = tmdb.base_url
        self.image_base_url = tmdb.image_base_url
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request to TMDB"""
        if not self.api_key:
            LOGGER.error("TMDB API key not configured")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        default_params = {"api_key": self.api_key, "language": "zh-CN"}
        
        if params:
            default_params.update(params)
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=default_params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        LOGGER.error(f"TMDB API request failed: {response.status}")
                        return None
        except Exception as e:
            LOGGER.error(f"TMDB API request error: {str(e)}")
            return None

    async def search_multi(self, query: str, page: int = 1) -> Tuple[bool, List[Dict], Dict]:
        """
        Search for movies and TV shows
        Args:
            query: Search query
            page: Page number (default: 1)
        Returns:
            (success, results_list, pagination_info)
        """
        if not query or len(query.strip()) < 2:
            return False, [], {}
            
        params = {
            "query": query.strip(),
            "page": page,
            "include_adult": "false"
        }
        
        data = await self._make_request("search/multi", params)
        if not data:
            return False, [], {}
        
        # Extract pagination info from TMDB response
        pagination_info = {
            "page": data.get("page", 1),
            "total_pages": data.get("total_pages", 1),
            "total_results": data.get("total_results", 0)
        }
        
        results = []
        for item in data.get("results", []):
            media_type = item.get("media_type")
            
            # Skip person results, only keep movie and tv
            if media_type not in ["movie", "tv"]:
                continue
                
            # Format the result
            if media_type == "movie":
                result = {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "original_title": item.get("original_title", ""),
                    "release_date": item.get("release_date", ""),
                    "year": item.get("release_date", "")[:4] if item.get("release_date") else "",
                    "overview": item.get("overview", ""),
                    "poster_path": item.get("poster_path", ""),
                    "backdrop_path": item.get("backdrop_path", ""),
                    "vote_average": item.get("vote_average", 0),
                    "vote_count": item.get("vote_count", 0),
                    "popularity": item.get("popularity", 0),
                    "genre_ids": item.get("genre_ids", []),
                    "media_type": "movie",
                    "media_type_cn": "电影"
                }
            else:  # tv
                result = {
                    "id": item.get("id"),
                    "title": item.get("name", ""),
                    "original_title": item.get("original_name", ""),
                    "release_date": item.get("first_air_date", ""),
                    "year": item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                    "overview": item.get("overview", ""),
                    "poster_path": item.get("poster_path", ""),
                    "backdrop_path": item.get("backdrop_path", ""),
                    "vote_average": item.get("vote_average", 0),
                    "vote_count": item.get("vote_count", 0),
                    "popularity": item.get("popularity", 0),
                    "genre_ids": item.get("genre_ids", []),
                    "media_type": "tv",
                    "media_type_cn": "电视剧"
                }
            
            # Add full image URLs
            if result["poster_path"]:
                result["poster_url"] = f"{self.image_base_url}{result['poster_path']}"
            else:
                result["poster_url"] = ""
                
            if result["backdrop_path"]:
                result["backdrop_url"] = f"{self.image_base_url}{result['backdrop_path']}"
            else:
                result["backdrop_url"] = ""
                
            results.append(result)
        
        # Sort by popularity (descending)
        results.sort(key=lambda x: x["popularity"], reverse=True)
        
        LOGGER.info(f"TMDB search successful for '{query}': found {len(results)} results on page {page}")
        return True, results, pagination_info

    async def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed movie information"""
        data = await self._make_request(f"movie/{movie_id}")
        return data

    async def get_tv_details(self, tv_id: int) -> Optional[Dict]:
        """Get detailed TV show information"""
        data = await self._make_request(f"tv/{tv_id}")
        return data

    async def get_trending(self, time_window: str = "day", limit: int = 10) -> Tuple[bool, List[Dict]]:
        """
        Get trending movies and TV shows
        Args:
            time_window: Time window for trending (day or week)
            limit: Number of results to return (default: 10)
        Returns:
            (success, results_list)
        """
        data = await self._make_request(f"trending/all/{time_window}")
        if not data:
            return False, []
        
        results = []
        for item in data.get("results", [])[:limit]:
            media_type = item.get("media_type")
            
            # Skip person results
            if media_type not in ["movie", "tv"]:
                continue
            
            if media_type == "movie":
                result = {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "original_title": item.get("original_title", ""),
                    "release_date": item.get("release_date", ""),
                    "year": item.get("release_date", "")[:4] if item.get("release_date") else "",
                    "overview": item.get("overview", ""),
                    "poster_path": item.get("poster_path", ""),
                    "vote_average": item.get("vote_average", 0),
                    "popularity": item.get("popularity", 0),
                    "media_type": "movie",
                    "media_type_cn": "电影"
                }
            else:  # tv
                result = {
                    "id": item.get("id"),
                    "title": item.get("name", ""),
                    "original_title": item.get("original_name", ""),
                    "release_date": item.get("first_air_date", ""),
                    "year": item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                    "overview": item.get("overview", ""),
                    "poster_path": item.get("poster_path", ""),
                    "vote_average": item.get("vote_average", 0),
                    "popularity": item.get("popularity", 0),
                    "media_type": "tv",
                    "media_type_cn": "电视剧"
                }
            
            if result["poster_path"]:
                result["poster_url"] = f"{self.image_base_url}{result['poster_path']}"
            else:
                result["poster_url"] = ""
            
            results.append(result)
        
        LOGGER.info(f"TMDB trending fetched: {len(results)} results")
        return True, results

    async def get_popular(self, media_type: str = "all", limit: int = 10) -> Tuple[bool, List[Dict]]:
        """
        Get popular movies and TV shows (streaming)
        Args:
            media_type: Type of media (movie, tv, or all)
            limit: Number of results to return (default: 10)
        Returns:
            (success, results_list)
        """
        results = []
        
        if media_type in ["all", "movie"]:
            # Get popular movies
            movie_data = await self._make_request("movie/popular")
            if movie_data:
                movie_limit = limit if media_type == "movie" else limit // 2
                for item in movie_data.get("results", [])[:movie_limit]:
                    result = {
                        "id": item.get("id"),
                        "title": item.get("title", ""),
                        "original_title": item.get("original_title", ""),
                        "release_date": item.get("release_date", ""),
                        "year": item.get("release_date", "")[:4] if item.get("release_date") else "",
                        "overview": item.get("overview", ""),
                        "poster_path": item.get("poster_path", ""),
                        "vote_average": item.get("vote_average", 0),
                        "popularity": item.get("popularity", 0),
                        "media_type": "movie",
                        "media_type_cn": "电影"
                    }
                    if result["poster_path"]:
                        result["poster_url"] = f"{self.image_base_url}{result['poster_path']}"
                    else:
                        result["poster_url"] = ""
                    results.append(result)
        
        if media_type in ["all", "tv"]:
            # Get popular TV shows
            tv_data = await self._make_request("tv/popular")
            if tv_data:
                tv_limit = limit if media_type == "tv" else limit // 2
                for item in tv_data.get("results", [])[:tv_limit]:
                    result = {
                        "id": item.get("id"),
                        "title": item.get("name", ""),
                        "original_title": item.get("original_name", ""),
                        "release_date": item.get("first_air_date", ""),
                        "year": item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                        "overview": item.get("overview", ""),
                        "poster_path": item.get("poster_path", ""),
                        "vote_average": item.get("vote_average", 0),
                        "popularity": item.get("popularity", 0),
                        "media_type": "tv",
                        "media_type_cn": "电视剧"
                    }
                    if result["poster_path"]:
                        result["poster_url"] = f"{self.image_base_url}{result['poster_path']}"
                    else:
                        result["poster_url"] = ""
                    results.append(result)
        
        if not results:
            return False, []
        
        # Sort by popularity
        results.sort(key=lambda x: x["popularity"], reverse=True)
        
        LOGGER.info(f"TMDB popular fetched: {len(results)} results")
        return True, results[:limit]

    async def search_by_tmdb_id(self, tmdb_id: int, media_type: str = None) -> Tuple[bool, Optional[Dict]]:
        """
        Search for a movie or TV show by its TMDB ID
        Args:
            tmdb_id: TMDB ID (numeric)
            media_type: 'movie' or 'tv'. If None, try both starting with movie
        Returns:
            (success, formatted_result)
        """
        if not tmdb_id or not (0 < tmdb_id < 10000000):
            LOGGER.warning(f"Invalid TMDB ID: {tmdb_id}")
            return False, None
        
        try:
            # If media_type is specified, try that specific type
            if media_type:
                if media_type == "movie":
                    data = await self.get_movie_details(tmdb_id)
                elif media_type == "tv":
                    data = await self.get_tv_details(tmdb_id)
                else:
                    LOGGER.error(f"Invalid media_type: {media_type}")
                    return False, None
                    
                if data:
                    LOGGER.info(f"TMDB ID {tmdb_id} found as {media_type}: {data.get('title' if media_type == 'movie' else 'name', 'Unknown')}")
                    return True, self._format_tmdb_detail_result(data, media_type)
                else:
                    LOGGER.info(f"TMDB ID {tmdb_id} not found as {media_type}")
                    return False, None
            
            # If no media_type specified, try movie first, then TV
            # Try movie first
            movie_data = await self.get_movie_details(tmdb_id)
            if movie_data:
                LOGGER.info(f"TMDB ID {tmdb_id} found as movie: {movie_data.get('title', 'Unknown')}")
                return True, self._format_tmdb_detail_result(movie_data, "movie")
            
            # Try TV show
            tv_data = await self.get_tv_details(tmdb_id)
            if tv_data:
                LOGGER.info(f"TMDB ID {tmdb_id} found as TV show: {tv_data.get('name', 'Unknown')}")
                return True, self._format_tmdb_detail_result(tv_data, "tv")
            
            # Not found in either
            LOGGER.info(f"TMDB ID {tmdb_id} not found in either movies or TV shows")
            return False, None
            
        except Exception as e:
            LOGGER.error(f"Error searching TMDB ID {tmdb_id}: {str(e)}")
            return False, None
    
    def _format_tmdb_detail_result(self, data: Dict, media_type: str) -> Dict:
        """Format TMDB detail API response to match search result format"""
        if media_type == "movie":
            result = {
                "id": data.get("id"),
                "title": data.get("title", ""),
                "original_title": data.get("original_title", ""),
                "release_date": data.get("release_date", ""),
                "year": data.get("release_date", "")[:4] if data.get("release_date") else "",
                "overview": data.get("overview", ""),
                "poster_path": data.get("poster_path", ""),
                "backdrop_path": data.get("backdrop_path", ""),
                "vote_average": data.get("vote_average", 0),
                "vote_count": data.get("vote_count", 0),
                "popularity": data.get("popularity", 0),
                "genre_ids": [genre.get("id", 0) for genre in data.get("genres", [])],
                "genres": ", ".join([genre.get("name", "") for genre in data.get("genres", [])]),
                "runtime": data.get("runtime", 0),
                "media_type": "movie",
                "media_type_cn": "电影"
            }
        else:  # tv
            result = {
                "id": data.get("id"),
                "title": data.get("name", ""),
                "original_title": data.get("original_name", ""),
                "release_date": data.get("first_air_date", ""),
                "year": data.get("first_air_date", "")[:4] if data.get("first_air_date") else "",
                "overview": data.get("overview", ""),
                "poster_path": data.get("poster_path", ""),
                "backdrop_path": data.get("backdrop_path", ""),
                "vote_average": data.get("vote_average", 0),
                "vote_count": data.get("vote_count", 0),
                "popularity": data.get("popularity", 0),
                "genre_ids": [genre.get("id", 0) for genre in data.get("genres", [])],
                "genres": ", ".join([genre.get("name", "") for genre in data.get("genres", [])]),
                "number_of_seasons": data.get("number_of_seasons", 0),
                "number_of_episodes": data.get("number_of_episodes", 0),
                "media_type": "tv",
                "media_type_cn": "电视剧"
            }
        
        # Add full image URLs
        if result["poster_path"]:
            result["poster_url"] = f"{self.image_base_url}{result['poster_path']}"
        else:
            result["poster_url"] = ""
            
        if result["backdrop_path"]:
            result["backdrop_url"] = f"{self.image_base_url}{result['backdrop_path']}"
        else:
            result["backdrop_url"] = ""
        
        return result

    async def get_tv_seasons(self, tv_id: int) -> Tuple[bool, List[Dict]]:
        """
        Get all seasons for a TV series
        Args:
            tv_id: TMDB TV series ID
        Returns:
            (success, seasons_list)
        """
        data = await self._make_request(f"tv/{tv_id}")
        if not data:
            return False, []
        
        seasons = []
        for season in data.get("seasons", []):
            # Skip special seasons (season 0 usually contains specials)
            season_number = season.get("season_number", 0)
            if season_number == 0:
                continue
                
            season_info = {
                "id": season.get("id"),
                "season_number": season_number,
                "name": season.get("name", f"第 {season_number} 季"),
                "overview": season.get("overview", ""),
                "poster_path": season.get("poster_path", ""),
                "air_date": season.get("air_date", ""),
                "episode_count": season.get("episode_count", 0)
            }
            
            # Add full poster URL if available
            if season_info["poster_path"]:
                season_info["poster_url"] = f"{self.image_base_url}{season_info['poster_path']}"
            else:
                season_info["poster_url"] = ""
                
            seasons.append(season_info)
        
        # Sort by season number
        seasons.sort(key=lambda x: x["season_number"])
        
        LOGGER.info(f"Found {len(seasons)} seasons for TV series {tv_id}")
        return True, seasons

    @staticmethod
    def is_tmdb_id(query: str) -> bool:
        """Check if the query is a TMDB ID (numeric)"""
        try:
            tmdb_id = int(query.strip())
            # TMDB IDs should be positive and reasonable (< 10 million for safety)
            return 0 < tmdb_id < 10000000
        except (ValueError, TypeError):
            return False
    
    @staticmethod 
    def extract_tmdb_id(query: str) -> Optional[int]:
        """Extract TMDB ID from query string"""
        try:
            tmdb_id = int(query.strip())
            # Validate range
            if 0 < tmdb_id < 10000000:
                return tmdb_id
            return None
        except (ValueError, TypeError):
            return None

    def format_search_result_text(self, item: Dict, index: int) -> str:
        """Format TMDB search result for display"""
        title = item.get("title", "未知标题")
        original_title = item.get("original_title", "")
        year = item.get("year", "未知")
        media_type = item.get("media_type_cn", "未知")
        vote_average = item.get("vote_average", 0)
        vote_count = item.get("vote_count", 0)
        
        text = f"🎬 **编号**: `{index}`\n"
        text += f"📺 **类型**: {media_type}\n"
        text += f"🎭 **标题**: {title}\n"
        
        if original_title and original_title != title:
            text += f"🔤 **原名**: {original_title}\n"
            
        if year:
            text += f"📅 **年份**: {year}\n"
            
        if vote_average > 0:
            stars = "⭐" * min(int(vote_average/2), 5)
            text += f"⭐ **评分**: {vote_average:.1f}/10 {stars} ({vote_count}票)\n"
        
        return text


# Create global instance
tmdb_service = TMDBService()