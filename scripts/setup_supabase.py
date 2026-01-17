#!/usr/bin/env python3
"""
Supabase Setup Helper for FixionMail

This script helps verify your Supabase connection and provides
instructions for running migrations.

Usage:
    python scripts/setup_supabase.py

Requirements:
    - Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables
    - Or create a .env file with these values
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

def check_supabase_connection():
    """Test the Supabase connection."""
    from supabase import create_client, Client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("\n❌ Missing Supabase credentials!")
        print("\nSet these environment variables:")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_SERVICE_KEY=eyJhbGci...")
        return False

    print(f"\n🔗 Connecting to: {url}")

    try:
        client: Client = create_client(url, key)

        # Try a simple query to verify connection
        result = client.table("users").select("id").limit(1).execute()
        print("✅ Connected to Supabase successfully!")
        print(f"   Users table exists: Yes")
        return True
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            print("✅ Connected to Supabase successfully!")
            print("   ⚠️  Tables not created yet - run migrations first")
            return True
        else:
            print(f"❌ Connection failed: {e}")
            return False

def check_tables():
    """Check which tables exist in Supabase."""
    from supabase import create_client, Client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    client: Client = create_client(url, key)

    required_tables = [
        "users",
        "stories",
        "story_jobs",
        "scheduled_deliveries",
        "character_names",
        "conversations",
        "credit_transactions",
        "hallucinations"
    ]

    print("\n📋 Checking required tables:")

    missing = []
    for table in required_tables:
        try:
            client.table(table).select("*").limit(1).execute()
            print(f"   ✅ {table}")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"   ❌ {table} (missing)")
                missing.append(table)
            else:
                print(f"   ⚠️  {table} (error: {e})")

    return missing

def print_migration_instructions():
    """Print instructions for running migrations."""
    print("\n" + "=" * 60)
    print("📚 MIGRATION INSTRUCTIONS")
    print("=" * 60)
    print("""
1. Go to your Supabase Dashboard:
   https://supabase.com/dashboard/project/YOUR_PROJECT_ID

2. Navigate to: SQL Editor (left sidebar)

3. Run migrations IN ORDER (copy/paste each file):

   Option A - Fresh Install (recommended):
   ----------------------------------------
   a) Run: supabase/migrations/999_ensure_all_tables.sql
   b) Run: supabase/migrations/005_seed_character_names.sql

   Option B - Step by Step:
   ------------------------
   a) supabase/migrations/001_initial_schema.sql
   b) supabase/migrations/002_add_story_jobs_table.sql
   c) supabase/migrations/003_add_scheduled_deliveries.sql
   d) supabase/migrations/004_add_character_names.sql
   e) supabase/migrations/005_seed_character_names.sql
   f) supabase/migrations/006_fix_duplicate_deliveries.sql
   g) supabase/migrations/007_add_job_locking.sql

4. After running migrations, run this script again to verify.
""")

def print_env_template():
    """Print the environment variables needed."""
    print("\n" + "=" * 60)
    print("🔧 REQUIRED ENVIRONMENT VARIABLES")
    print("=" * 60)
    print("""
# Supabase (from your Supabase Dashboard > Settings > API)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_KEY=eyJhbGci...
SUPABASE_JWT_SECRET=your-jwt-secret

# Get JWT Secret from: Settings > API > JWT Settings > JWT Secret
""")

def main():
    print("=" * 60)
    print("🚀 FixionMail - Supabase Setup Helper")
    print("=" * 60)

    # Load .env if exists
    load_env()

    # Check connection
    connected = check_supabase_connection()

    if not connected:
        print_env_template()
        return 1

    # Check tables
    missing = check_tables()

    if missing:
        print(f"\n⚠️  Missing {len(missing)} table(s)")
        print_migration_instructions()
        return 1
    else:
        print("\n✅ All tables exist!")
        print("\nYour Supabase database is ready for FixionMail.")

        # Check for character names
        from supabase import create_client, Client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        client: Client = create_client(url, key)

        try:
            result = client.table("character_names").select("id", count="exact").execute()
            count = result.count if hasattr(result, 'count') else len(result.data)
            if count == 0:
                print("\n⚠️  Character names table is empty!")
                print("   Run: supabase/migrations/005_seed_character_names.sql")
            else:
                print(f"   Character names seeded: {count} names")
        except:
            pass

        return 0

if __name__ == "__main__":
    sys.exit(main())
