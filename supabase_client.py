# supabase_client.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pkojtqwatctncuerilub.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_zGqm7NV1PbsGOeFGGOOs-Q_bA63DyJP")

_client: Client = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
