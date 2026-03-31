import threading
import logging
import time
from typing import Dict, Any, Optional

# Try to import requests; if not available, disable sync gracefully
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config import PB_URL, PB_EMAIL, PB_PASSWORD, PB_COLLECTIONS, PB_SYNC_ENABLED

# Set up logging for sync failures
# We use a specific logger to avoid cluttering the main output unless necessary
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncManager")

class SyncManager:
    """
    Handles data synchronization with PocketBase.
    Designed to be non-blocking, fault-tolerant, and fail-safe.
    """
    _token = None
    _auth_lock = threading.Lock()
    _session = None

    @classmethod
    def _get_api_url(cls, path: str = "") -> str:
        """Normalizes and joins the base URL with a path."""
        base = PB_URL.rstrip('/')
        if not base.endswith('/api'):
            base += '/api'
        
        path = path.lstrip('/')
        # Prevent double /api/
        if path.startswith('api/'):
            path = path[4:]
            
        return f"{base}/{path}".rstrip('/')

    @classmethod
    def _get_session(cls):
        """Returns a reusable requests Session."""
        if cls._session is None and REQUESTS_AVAILABLE:
            cls._session = requests.Session()
        return cls._session

    @classmethod
    def get_token(cls) -> Optional[str]:
        """Authenticates with PocketBase and returns the auth token."""
        if not REQUESTS_AVAILABLE:
            return None
            
        if cls._token:
            return cls._token
        
        with cls._auth_lock:
            if cls._token:
                return cls._token
            
            session = cls._get_session()
            if not session:
                return None

            try:
                # Try Superuser auth (PB v0.23+)
                auth_url = cls._get_api_url("/collections/_superusers/auth-with-password")
                response = session.post(
                    auth_url, 
                    json={"identity": PB_EMAIL, "password": PB_PASSWORD},
                    timeout=10
                )
                
                # Fallback to standard users or legacy admins
                if response.status_code != 200:
                    for alt_path in ["/collections/users/auth-with-password", "/admins/auth-with-password"]:
                        alt_url = cls._get_api_url(alt_path)
                        response = session.post(
                            alt_url,
                            json={"identity": PB_EMAIL, "password": PB_PASSWORD},
                            timeout=10
                        )
                        if response.status_code == 200: break

                if response.status_code == 200:
                    cls._token = response.json().get("token")
                    return cls._token
                else:
                    logger.warning(f"PB Auth failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"PB Connection error during auth: {e}")
        return None

    @classmethod
    def sync_data(cls, collection_key: str, data: Dict[str, Any], record_id: Optional[str] = None):
        """Triggers an asynchronous sync operation."""
        if not PB_SYNC_ENABLED or not REQUESTS_AVAILABLE:
            return

        thread = threading.Thread(
            target=cls._perform_sync,
            args=(collection_key, data, record_id),
            daemon=True
        )
        thread.start()

    @classmethod
    def delete_record(cls, collection_key: str, record_id: str):
        """Triggers an asynchronous delete operation."""
        if not PB_SYNC_ENABLED or not REQUESTS_AVAILABLE:
            return

        thread = threading.Thread(
            target=cls._perform_delete,
            args=(collection_key, record_id),
            daemon=True
        )
        thread.start()

    @classmethod
    def _perform_delete(cls, collection_key: str, record_id: str):
        """Internal method to perform the actual HTTP DELETE request."""
        try:
            token = cls.get_token()
            if not token: return

            collection_name = PB_COLLECTIONS.get(collection_key)
            if not collection_name: return

            session = cls._get_session()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Find the record ID in PB first
            search_query = f"(local_id='{record_id}')"
            if collection_key == "projects": search_query = f"(project_name='{record_id}')"
            
            search_url = cls._get_api_url(f"/collections/{collection_name}/records?filter={search_query}")
            search_res = session.get(search_url, headers=headers, timeout=10)
            
            if search_res.status_code == 200:
                items = search_res.json().get("items", [])
                for item in items:
                    pb_id = item['id']
                    del_url = cls._get_api_url(f"/collections/{collection_name}/records/{pb_id}")
                    session.delete(del_url, headers=headers, timeout=10)
                    
        except Exception as e:
            logger.warning(f"PB Delete background error: {e}")

    @classmethod
    def pull_all(cls) -> Optional[Dict[str, list]]:
        """Fetches all records from all ff_ collections. Returns None on failure."""
        if not PB_SYNC_ENABLED or not REQUESTS_AVAILABLE:
            return None

        token = cls.get_token()
        if not token:
            return None

        session = cls._get_session()
        headers = {"Authorization": f"Bearer {token}"}
        result: Dict[str, list] = {"projects": [], "tasks": [], "sessions": []}

        try:
            for key in ["projects", "tasks", "sessions"]:
                collection_name = PB_COLLECTIONS.get(key)
                if not collection_name:
                    continue

                page, total_pages = 1, 1
                while page <= total_pages:
                    url = cls._get_api_url(
                        f"/collections/{collection_name}/records?perPage=500&page={page}"
                    )
                    r = session.get(url, headers=headers, timeout=15)
                    if r.status_code != 200:
                        logger.warning(f"PB Pull failed for {key}: {r.status_code}")
                        break
                    data = r.json()
                    result[key].extend(data.get("items", []))
                    total_pages = data.get("totalPages", 1)
                    page += 1

            return result
        except Exception as e:
            logger.warning(f"PB Pull error: {e}")
            return None

    @classmethod
    def _perform_sync(cls, collection_key: str, data: Dict[str, Any], record_id: Optional[str]):
        """Internal method to perform the actual HTTP request."""
        try:
            token = cls.get_token()
            if not token: return

            collection_name = PB_COLLECTIONS.get(collection_key)
            if not collection_name: return

            session = cls._get_session()
            headers = {"Authorization": f"Bearer {token}"}
            pb_data = data.copy()
            
            if record_id:
                pb_data['local_id'] = record_id
                search_query = f"(local_id='{record_id}')"
                if collection_key == "projects": search_query = f"(project_name='{record_id}')"

                search_url = cls._get_api_url(f"/collections/{collection_name}/records?filter={search_query}")
                search_res = session.get(search_url, headers=headers, timeout=10)
                
                if search_res.status_code == 200:
                    items = search_res.json().get("items", [])
                    if items:
                        pb_id = items[0]['id']
                        update_url = cls._get_api_url(f"/collections/{collection_name}/records/{pb_id}")
                        session.patch(update_url, json=pb_data, headers=headers, timeout=10)
                        return

            create_url = cls._get_api_url(f"/collections/{collection_name}/records")
            session.post(create_url, json=pb_data, headers=headers, timeout=10)

        except Exception as e:
            logger.warning(f"PB Sync background error: {e}")
