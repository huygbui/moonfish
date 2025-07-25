"""alter the format enum - coffee_chat to conversation

Revision ID: 30939aedbccc
Revises: b3b225421fc7
Create Date: 2025-07-25 16:27:05.532961

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "30939aedbccc"
down_revision: Union[str, None] = "b3b225421fc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create new enum with desired values (without coffee_chat)
    op.execute("CREATE TYPE format_new AS ENUM ('interview', 'conversation', 'story', 'analysis')")

    # Safely migrate data: if coffee_chat exists, convert to conversation; otherwise keep existing value
    # This handles the case where coffee_chat might not be a valid enum value currently
    op.execute("""
        ALTER TABLE episode
        ALTER COLUMN format TYPE format_new
        USING CASE
            WHEN format::text = 'coffee_chat' THEN 'conversation'::format_new
            ELSE format::text::format_new
        END
    """)

    op.execute("""
        ALTER TABLE podcast
        ALTER COLUMN format TYPE format_new
        USING CASE
            WHEN format::text = 'coffee_chat' THEN 'conversation'::format_new
            ELSE format::text::format_new
        END
    """)

    # Drop old enum and rename new one
    op.execute("DROP TYPE format")
    op.execute("ALTER TYPE format_new RENAME TO format")


def downgrade() -> None:
    """Downgrade schema."""
    # No downgrade needed as requested
    pass
