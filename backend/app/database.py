"""Supabase client initialization."""

from functools import lru_cache

from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Return a cached Supabase client using the service role key.
    
    The service role key bypasses Row Level Security — use this
    only on the server side for admin operations.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_anon_client() -> Client:
    """
    Return a fresh Supabase client using the anon (public) key.
    
    This client respects Row Level Security and maintains an isolated
    session per call for user sign-in flows.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
