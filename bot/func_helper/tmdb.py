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